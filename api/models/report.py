from sqlalchemy import Column, Integer, String, Text, DateTime, func, ForeignKey

from api.database import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    research_run_id = Column(Integer, ForeignKey("research_runs.id"), nullable=False)
    report_text = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class EvaluationMetric(Base):
    __tablename__ = "evaluation_metrics"

    id = Column(Integer, primary_key=True, index=True)
    research_run_id = Column(Integer, ForeignKey("research_runs.id"), nullable=False)
    metric_name = Column(String, nullable=False)
    metric_value = Column(Integer, nullable=True)
