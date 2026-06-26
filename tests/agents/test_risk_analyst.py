import pytest
from api.agents import RiskAnalystAgent


class TestRiskAnalystAgent:
    def test_init(self):
        agent = RiskAnalystAgent()
        assert agent.name == "risk_analyst"

    def test_run_returns_list(self, monkeypatch):
        def mock_llm(prompt, system=None, model=None, **kwargs):
            return '[{"risk_type": "regulatory", "description": "Test risk", "severity": "high"}]'

        monkeypatch.setattr("api.agents.risk_analyst.call_llm", mock_llm)
        agent = RiskAnalystAgent()
        risks = agent.run([{"topic": "profitability", "summary": "good"}])
        assert isinstance(risks, list)
        assert len(risks) == 1
