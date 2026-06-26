import json
import logging
from typing import Callable

from api.utils.llm import call_llm

logger = logging.getLogger(__name__)

RISK_ANALYST_PROMPT = """You are a risk analyst specializing in financial institutions. Review the research findings and identify key risks.

Findings:
{findings}

Identify risks in these categories:
1. Regulatory risks
2. Market risks
3. Interest-rate risks
4. Credit risks

Return a JSON array:
[
  {{"risk_type": "regulatory", "description": "...", "severity": "high|medium|low"}},
  {{"risk_type": "market", "description": "...", "severity": "high|medium|low"}}
]

Return ONLY the JSON array, no other text."""


class RiskAnalystAgent:
    def __init__(self):
        self.name = "risk_analyst"

    def run(self, findings: list[dict],
            on_llm_start: Callable | None = None,
            on_llm_finish: Callable | None = None) -> list[dict]:
        logger.info("RiskAnalystAgent: analyzing %d findings", len(findings))
        findings_text = json.dumps(findings, indent=2)
        prompt = RISK_ANALYST_PROMPT.format(findings=findings_text)
        response = call_llm(prompt, on_start=on_llm_start, on_finish=on_llm_finish)
        try:
            risks = json.loads(response)
            if isinstance(risks, list):
                logger.info("RiskAnalystAgent: identified %d risks", len(risks))
                return risks
        except json.JSONDecodeError:
            logger.warning("RiskAnalystAgent: failed to parse JSON")
        return [{"risk_type": "unknown", "description": response, "severity": "medium"}]
