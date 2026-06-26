import json
import logging
import re
from typing import Callable

from api.utils.llm import call_llm, get_embedding
from api.tools.qdrant_search import QdrantSearch
from api.tools.mcp_client import call_tool as mcp_call

logger = logging.getLogger(__name__)

RESEARCHER_PROMPT = """You are an investment research analyst. Based on the retrieved evidence and live market data, summarize findings for the given task.

Task: {task}

Evidence from documents:
{evidence}

{extra_context}

Return a JSON object:
{{
  "topic": "{task}",
  "summary": "Your concise summary based on evidence",
  "citations": ["list of key evidence points"]
}}

Return ONLY the JSON object, no other text."""


class ResearcherAgent:
    def __init__(self):
        self.name = "researcher"
        self.search = QdrantSearch()

    def _extract_companies(self, task: str) -> list[str]:
        known = ["rbc", "td", "bmo", "scotiabank", "cibc", "national bank",
                 "jpmorgan", "goldman sachs", "morgan stanley",
                 "bank of america", "citigroup", "wells fargo",
                 "microsoft", "apple", "google", "amazon", "meta",
                 "nvidia", "tesla", "walmart"]
        found = []
        task_lower = task.lower()
        for name in known:
            if name in task_lower:
                found.append(name)
        return found

    def _gather_mcp_context(self, task: str) -> str:
        companies = self._extract_companies(task)
        if not companies:
            return ""
        parts = []
        for company in companies[:2]:
            info = mcp_call("get_company_info", {"company": company})
            peers = mcp_call("get_peers", {"company": company})
            ticker = mcp_call("get_stock_ticker", {"company_name": company})
            for item in [info, peers, ticker]:
                try:
                    parsed = json.loads(item)
                    if "error" not in parsed:
                        parts.append(item)
                except Exception:
                    pass
        if parts:
            return "Live Market Data:\n" + "\n".join(parts)
        return ""

    def run(self, task: str,
            on_llm_start: Callable | None = None,
            on_llm_finish: Callable | None = None) -> dict:
        logger.info("ResearcherAgent: researching task=%s", task)

        vector = get_embedding(task)
        results = self.search.search(vector, top_k=5)
        evidence_text = "\n".join(
            [f"- {r['text'][:500]}" for r in results]
        )

        extra = self._gather_mcp_context(task)
        extra_context = extra if extra else "No additional market data available."

        prompt = RESEARCHER_PROMPT.format(
            task=task, evidence=evidence_text, extra_context=extra_context,
        )
        response = call_llm(prompt, on_start=on_llm_start, on_finish=on_llm_finish)
        try:
            finding = json.loads(response)
            if isinstance(finding, dict):
                logger.info("ResearcherAgent: completed task=%s", task)
                return finding
        except json.JSONDecodeError:
            logger.warning("ResearcherAgent: failed to parse JSON")
        return {"topic": task, "summary": response, "citations": []}
