import pytest
from api.workflows import ResearchWorkflow


class TestResearchWorkflow:
    def test_init(self, db_session):
        wf = ResearchWorkflow(db_session)
        assert wf.planner is not None
        assert wf.researcher is not None
        assert wf.writer is not None
        assert wf.reviewer is not None
