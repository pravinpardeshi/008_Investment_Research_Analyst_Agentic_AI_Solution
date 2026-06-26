import json
import logging
import threading
import time
from typing import Callable, Generator
from sqlalchemy.orm import Session

from api.agents import PlannerAgent, ResearcherAgent, RiskAnalystAgent, WriterAgent, ReviewerAgent
from api.memory import PostgresMemory
from api.utils.tracking import log_agent_step, log_research_run
from api.utils.langfuse_tracking import start_trace, end_trace, start_span, end_span, flush as lf_flush
from api.utils.llm import set_run_id
from config.settings import LLM_MODEL, FALLBACK_LLM_MODEL

logger = logging.getLogger(__name__)

_cancelled_runs: set[int] = set()
_cancel_lock = threading.Lock()


class WorkflowCancelled(Exception):
    pass


def cancel_run(run_id: int):
    with _cancel_lock:
        _cancelled_runs.add(run_id)
    logger.info("Cancellation requested for run_id=%d", run_id)


def is_cancelled(run_id: int) -> bool:
    with _cancel_lock:
        return run_id in _cancelled_runs


def clear_cancelled(run_id: int):
    with _cancel_lock:
        _cancelled_runs.discard(run_id)


class ResearchWorkflow:
    def __init__(self, db: Session):
        self.db = db
        self.memory = PostgresMemory(db)
        self.planner = PlannerAgent()
        self.researcher = ResearcherAgent()
        self.risk_analyst = RiskAnalystAgent()
        self.writer = WriterAgent()
        self.reviewer = ReviewerAgent()
        self._llm_model = LLM_MODEL
        self._llm_fallback = FALLBACK_LLM_MODEL

    def _make_llm_callbacks(self, run_id: int) -> tuple[Callable, Callable]:
        def on_start(model: str, prompt_len: int):
            logger.info("[run_id=%d] LLM start: model=%s prompt_len=%d", run_id, model, prompt_len)

        def on_finish(model: str, response_len: int, duration: float):
            logger.info(
                "[run_id=%d] LLM finish: model=%s response_len=%d duration=%.1fs",
                run_id, model, response_len, duration,
            )
            self._last_llm = {"model": model, "response_len": response_len, "duration": round(duration, 1)}

        return on_start, on_finish

    def run(self, question: str) -> int:
        run = self.memory.create_research_run(question)
        run_id = run.id
        self.memory.update_run_status(run_id, "running")
        set_run_id(run_id)
        start_trace(f"research_run_{run_id}", input=question)
        logger.info("Workflow: started run_id=%d", run_id)

        try:
            for _ in self._pipeline(question, run_id):
                pass
        except WorkflowCancelled:
            logger.info("Workflow: cancelled run_id=%d", run_id)
            self.memory.update_run_status(run_id, "cancelled")
            log_research_run(run_id, question, "cancelled")
        except Exception as e:
            logger.error("Workflow: failed run_id=%d error=%s", run_id, e)
            self.memory.update_run_status(run_id, "failed")
            log_research_run(run_id, question, "failed", metrics={"error": str(e)[:200]})
        else:
            log_research_run(run_id, question, "completed")

        end_trace()
        lf_flush()
        clear_cancelled(run_id)
        set_run_id(None)
        return run_id

    def run_async(self, question: str) -> int:
        """Start research in a background thread. Returns immediately with run_id."""
        run = self.memory.create_research_run(question)
        run_id = run.id
        self.memory.update_run_status(run_id, "running")
        logger.info("Workflow: async started run_id=%d", run_id)

        def _worker(q: str, rid: int):
            set_run_id(rid)
            start_trace(f"research_run_{rid}", input=q)
            try:
                for _ in self._pipeline(q, rid):
                    pass
            except WorkflowCancelled:
                logger.info("Workflow: cancelled run_id=%d", rid)
                self.memory.update_run_status(rid, "cancelled")
                log_research_run(rid, q, "cancelled")
            except Exception as e:
                logger.error("Workflow: failed run_id=%d error=%s", rid, e)
                self.memory.update_run_status(rid, "failed")
                log_research_run(rid, q, "failed", metrics={"error": str(e)[:200]})
            else:
                log_research_run(rid, q, "completed")
            finally:
                end_trace()
                lf_flush()
                clear_cancelled(rid)
                set_run_id(None)

        thread = threading.Thread(target=_worker, args=(question, run_id), daemon=True)
        thread.start()
        return run_id

    def run_stream(self, question: str) -> Generator[tuple[str, str], None, int]:
        run = self.memory.create_research_run(question)
        run_id = run.id
        self.memory.update_run_status(run_id, "running")
        set_run_id(run_id)
        start_trace(f"research_run_{run_id}", input=question)
        logger.info("Workflow: started run_id=%d", run_id)

        llm_info = json.dumps({"primary": self._llm_model, "fallback": self._llm_fallback})
        yield "config", llm_info
        yield "status", "Starting research workflow..."

        try:
            for step, msg in self._pipeline(question, run_id):
                yield step, msg
            log_research_run(run_id, question, "completed")
        except WorkflowCancelled:
            logger.info("Workflow: cancelled run_id=%d", run_id)
            self.memory.update_run_status(run_id, "cancelled")
            log_research_run(run_id, question, "cancelled")
            yield "cancelled", "Research cancelled by user"
        except Exception as e:
            logger.error("Workflow: failed run_id=%d error=%s", run_id, e)
            self.memory.update_run_status(run_id, "failed")
            log_research_run(run_id, question, "failed", metrics={"error": str(e)[:200]})
            yield "error", str(e)

        end_trace()
        lf_flush()
        clear_cancelled(run_id)
        set_run_id(None)
        return run_id

    def _check_cancelled(self, run_id: int):
        if is_cancelled(run_id):
            raise WorkflowCancelled()

    def _run_agent(self, name: str, run_id: int, fn: Callable, *args, **kwargs):
        self._check_cancelled(run_id)
        self._last_llm = None
        start_span(name, input={"run_id": run_id})
        yield "agent_start", json.dumps({"name": name, "model": self._llm_model})
        t0 = time.time()
        try:
            result = fn(*args, **kwargs, on_llm_start=self._make_llm_callbacks(run_id)[0],
                        on_llm_finish=self._make_llm_callbacks(run_id)[1])
            elapsed = round(time.time() - t0, 1)
            info = {"name": name, "duration": elapsed}
            if self._last_llm:
                info["llm"] = self._last_llm
            log_agent_step(name, elapsed, run_id, status="completed", metadata=self._last_llm)
            end_span()
            yield "agent_done", json.dumps(info)
            return result
        except WorkflowCancelled:
            end_span()
            raise
        except Exception as e:
            elapsed = round(time.time() - t0, 1)
            log_agent_step(name, elapsed, run_id, status="failed", metadata={"error": str(e)})
            end_span()
            yield "agent_error", json.dumps({"name": name, "error": str(e), "duration": elapsed})
            raise

    def _pipeline(self, question: str, run_id: int) -> Generator[tuple[str, str], None, None]:
        logger.info("Workflow: planning run_id=%d", run_id)
        yield "agent", "Planning research strategy..."

        tasks = yield from self._run_agent("Planner", run_id, self.planner.run, question)
        if tasks is None:
            return
        yield "status", f"Planned {len(tasks)} research tasks"
        self._check_cancelled(run_id)

        findings = []
        for i, task in enumerate(tasks):
            yield "agent", f"Researching task {i+1}/{len(tasks)}: {task[:60]}..."
            self._check_cancelled(run_id)
            finding = yield from self._run_agent("Researcher", run_id, self.researcher.run, task)
            if finding:
                self.memory.store_finding(run_id, finding.get("topic", task), finding.get("summary", ""))
                findings.append(finding)
            yield "status", f"Completed task {i+1}/{len(tasks)}"
            self._check_cancelled(run_id)

        yield "agent", "Analyzing risks..."
        self._check_cancelled(run_id)
        risks = yield from self._run_agent("RiskAnalyst", run_id, self.risk_analyst.run, findings)
        if risks is None:
            risks = []
        yield "status", f"Identified {len(risks)} risk factors"
        self._check_cancelled(run_id)

        yield "agent", "Writing report..."
        self._check_cancelled(run_id)
        report = yield from self._run_agent("Writer", run_id, self.writer.run, question, findings, risks)
        if report is None:
            return
        yield "status", "Report drafted"
        self._check_cancelled(run_id)

        for cycle in range(3):
            yield "agent", f"Reviewing report (cycle {cycle+1}/3)..."
            self._check_cancelled(run_id)
            review = yield from self._run_agent("Reviewer", run_id, self.reviewer.run, report)
            if review and review.get("approved"):
                yield "status", f"Report approved after cycle {cycle+1}"
                break
            yield "status", f"Revision requested, re-writing (cycle {cycle+1})..."
            self._check_cancelled(run_id)
            if cycle < 2:
                report = yield from self._run_agent("Writer", run_id, self.writer.run, question, findings, risks)
                if report is None:
                    return
                self._check_cancelled(run_id)

        self.memory.store_report(run_id, report or "")
        self.memory.update_run_status(run_id, "completed")

        self.memory.store_metric(run_id, "tasks_count", len(tasks))
        self.memory.store_metric(run_id, "findings_count", len(findings))
        self.memory.store_metric(run_id, "review_cycles", cycle + 1)

        logger.info("Workflow: completed run_id=%d", run_id)
        yield "done", str(run_id)
