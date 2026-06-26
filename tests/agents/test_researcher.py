import pytest
from api.agents import ResearcherAgent


class TestResearcherAgent:
    def test_init(self):
        agent = ResearcherAgent()
        assert agent.name == "researcher"
