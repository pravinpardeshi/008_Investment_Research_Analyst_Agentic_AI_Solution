import pytest
from api.agents import PlannerAgent


class TestPlannerAgent:
    def test_init(self):
        agent = PlannerAgent()
        assert agent.name == "planner"

    def test_run_returns_list(self, monkeypatch):
        def mock_llm(prompt, system=None, model=None, **kwargs):
            return '["Analyze profitability", "Analyze revenue growth"]'

        monkeypatch.setattr("api.agents.planner.call_llm", mock_llm)
        agent = PlannerAgent()
        tasks = agent.run("Compare RBC and TD Bank")
        assert isinstance(tasks, list)
        assert len(tasks) == 2
