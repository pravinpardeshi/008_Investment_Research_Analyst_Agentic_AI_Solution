import logging

from api.agents import ReviewerAgent
from api.utils.llm import call_llm

logger = logging.getLogger(__name__)


class ReviewWorkflow:
    def __init__(self):
        self.reviewer = ReviewerAgent()

    def run(self, report: str) -> dict:
        logger.info("ReviewWorkflow: reviewing report")
        review = self.reviewer.run(report)
        if not review.get("approved"):
            logger.info("ReviewWorkflow: report not approved, generating revision")
            prompt = f"Revise the following report based on review comments.\n\nReview Comments:\n{review.get('comments', [])}\n\nReport:\n{report}"
            revised = call_llm(prompt)
            return {"review": review, "revised_report": revised}
        return {"review": review, "revised_report": report}
