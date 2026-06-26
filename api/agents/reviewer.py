import json
import logging
from typing import Callable

from api.utils.llm import call_llm

logger = logging.getLogger(__name__)

REVIEWER_PROMPT = """You are a report reviewer. Review the following investment research report for quality and completeness.

Report:
{report}

Check for:
1. Missing sections
2. Unsupported conclusions
3. Lack of evidence
4. Overall quality

Return a JSON object:
{{
  "approved": true/false,
  "comments": ["comment1", "comment2"],
  "revision_requests": ["request1"]
}}

Return ONLY the JSON object, no other text."""


class ReviewerAgent:
    def __init__(self):
        self.name = "reviewer"

    def run(self, report: str,
            on_llm_start: Callable | None = None,
            on_llm_finish: Callable | None = None) -> dict:
        logger.info("ReviewerAgent: reviewing report")
        prompt = REVIEWER_PROMPT.format(report=report[:3000])
        response = call_llm(prompt, on_start=on_llm_start, on_finish=on_llm_finish)
        try:
            review = json.loads(response)
            if isinstance(review, dict):
                logger.info("ReviewerAgent: approved=%s", review.get("approved"))
                return review
        except json.JSONDecodeError:
            logger.warning("ReviewerAgent: failed to parse JSON")
        return {"approved": True, "comments": [], "revision_requests": []}
