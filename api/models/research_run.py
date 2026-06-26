from sqlalchemy import Column, Integer, String, DateTime, func

from api.database import Base


class ResearchRun(Base):
    __tablename__ = "research_runs"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(String, nullable=False)
    status = Column(String, default="pending")
    created_at = Column(DateTime, server_default=func.now())
