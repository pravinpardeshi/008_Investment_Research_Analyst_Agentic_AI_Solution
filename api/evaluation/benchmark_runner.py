import json
import logging
import time
from pathlib import Path

from api.workflows import ResearchWorkflow
from api.database import SessionLocal
from api.evaluation.judge import Judge
from api.evaluation.metrics import Metrics

logger = logging.getLogger(__name__)


class BenchmarkRunner:
    def __init__(self, tasks_file: str = "benchmarks/tasks.json"):
        self.tasks_file = Path(tasks_file)
        self.judge = Judge()

    def run_all(self) -> list[dict]:
        if not self.tasks_file.exists():
            logger.warning("Benchmark tasks file not found: %s", self.tasks_file)
            return []

        with open(self.tasks_file) as f:
            tasks = json.load(f)

        results = []
        for task in tasks:
            question = task.get("question", "")
            if not question:
                continue

            logger.info("Benchmark: running task=%s", question[:50])
            start = time.time()
            db = SessionLocal()
            try:
                workflow = ResearchWorkflow(db)
                run_id = workflow.run(question)
                duration = time.time() - start
                run = workflow.memory.get_run(run_id)
                report_obj = workflow.memory.get_report(run_id)
                report_text = report_obj.report_text if report_obj else ""
                completeness = Metrics.check_report_completeness(report_text)
                citations = Metrics.count_citations(report_text)
                scores = self.judge.evaluate(report_text)
                findings = workflow.memory.get_findings(run_id)
                chunks = Metrics.count_chunks_retrieved([{"citations": [f.id]} for f in findings])

                result = {
                    "question": question,
                    "run_id": run_id,
                    "duration_s": round(duration, 2),
                    "status": run.status if run else "unknown",
                    "citations": citations,
                    "chunks_retrieved": chunks,
                    "completeness": completeness,
                    "scores": scores,
                }
                results.append(result)
            finally:
                db.close()

        return results
