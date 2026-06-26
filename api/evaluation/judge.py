import logging

from api.utils.llm import call_llm

logger = logging.getLogger(__name__)

JUDGE_PROMPT = """You are an evaluator of investment research reports. Score the following report on a scale of 1-10 for each criterion.

Report:
{report}

Criteria:
1. Completeness - covers all required sections
2. Evidence quality - uses specific data and citations
3. Logical consistency - arguments are coherent
4. Writing quality - professional and clear

Return a JSON object:
{{
  "completeness": 8,
  "evidence_quality": 7,
  "logical_consistency": 9,
  "writing_quality": 8,
  "overall": 8,
  "notes": "Brief assessment"
}}

Return ONLY the JSON object."""


class Judge:
    def __init__(self):
        self.name = "judge"

    def evaluate(self, report: str) -> dict:
        logger.info("Judge: evaluating report")
        prompt = JUDGE_PROMPT.format(report=report[:2000])
        response = call_llm(prompt)
        try:
            import json
            scores = json.loads(response)
            return scores
        except Exception:
            logger.warning("Judge: failed to parse scores")
            return {"overall": 5, "notes": "Evaluation failed"}
