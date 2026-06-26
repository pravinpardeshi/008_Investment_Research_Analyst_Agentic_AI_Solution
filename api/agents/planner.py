import json
import logging

from typing import Callable

from api.utils.llm import call_llm

logger = logging.getLogger(__name__)

PLANNER_PROMPT = """You are an investment research planner. Break down the user's question into a list of specific research tasks.

User Question: {question}

Return a JSON array of task strings. Example:
["Analyze profitability", "Analyze revenue growth", "Analyze capital strength", "Analyze strategic initiatives", "Analyze risks", "Generate conclusion"]

Return ONLY the JSON array, no other text."""


class PlannerAgent:
    def __init__(self):
        self.name = "planner"

    def run(self, question: str,
            on_llm_start: Callable | None = None,
            on_llm_finish: Callable | None = None) -> list[str]:
        logger.info("PlannerAgent: planning for question=%s", question)
        prompt = PLANNER_PROMPT.format(question=question)
        response = call_llm(prompt, on_start=on_llm_start, on_finish=on_llm_finish)
        try:
            tasks = json.loads(response)
            if isinstance(tasks, list):
                logger.info("PlannerAgent: generated %d tasks", len(tasks))
                return tasks
        except json.JSONDecodeError:
            logger.warning("PlannerAgent: failed to parse JSON, splitting on newlines")
            lines = [line.strip("- ").strip() for line in response.strip().split("\n") if line.strip()]
            if lines:
                return lines
        return ["Analyze the company's financial performance"]
