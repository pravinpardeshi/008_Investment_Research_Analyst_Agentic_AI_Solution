import logging
from typing import Callable

from api.utils.llm import call_llm

logger = logging.getLogger(__name__)

WRITER_PROMPT = """You are an investment report writer. Create a professional investment research report based on the following findings and risk assessment.

Research Question: {question}

Findings:
{findings}

Risk Assessment:
{risks}

Write the report in Markdown with these sections:

# Investment Research Report

## Executive Summary

## Company Overview

## Financial Analysis

## Strategic Analysis

## Risk Analysis

## Investment Thesis

## Conclusion

Be objective, cite evidence where possible, and maintain a professional tone."""


class WriterAgent:
    def __init__(self):
        self.name = "writer"

    def run(self, question: str, findings: list[dict], risks: list[dict],
            on_llm_start: Callable | None = None,
            on_llm_finish: Callable | None = None) -> str:
        logger.info("WriterAgent: writing report")
        findings_text = "\n".join(
            [f"### {f.get('topic', 'Topic')}\n{f.get('summary', '')}" for f in findings]
        )
        risks_text = "\n".join(
            [f"- **{r.get('risk_type', 'Risk')}** ({r.get('severity', 'N/A')}): {r.get('description', '')}" for r in risks]
        )
        prompt = WRITER_PROMPT.format(
            question=question,
            findings=findings_text,
            risks=risks_text,
        )
        report = call_llm(prompt, on_start=on_llm_start, on_finish=on_llm_finish)
        logger.info("WriterAgent: report generated (%d chars)", len(report))
        return report
