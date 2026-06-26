import pytest
from api.agents import WriterAgent


class TestWriterAgent:
    def test_init(self):
        agent = WriterAgent()
        assert agent.name == "writer"
