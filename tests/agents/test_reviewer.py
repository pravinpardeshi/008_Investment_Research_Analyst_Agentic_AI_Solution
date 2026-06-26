import pytest
from api.agents import ReviewerAgent


class TestReviewerAgent:
    def test_init(self):
        agent = ReviewerAgent()
        assert agent.name == "reviewer"

    def test_run_returns_dict(self, monkeypatch):
        def mock_llm(prompt, system=None, model=None, **kwargs):
            return '{"approved": true, "comments": [], "revision_requests": []}'

        monkeypatch.setattr("api.agents.reviewer.call_llm", mock_llm)
        agent = ReviewerAgent()
        review = agent.run("# Report text")
        assert isinstance(review, dict)
        assert review["approved"] is True
