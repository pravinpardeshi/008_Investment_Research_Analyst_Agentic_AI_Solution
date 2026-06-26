from sqlalchemy import Column, Integer, String, Text, ForeignKey


from api.database import Base


class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    research_run_id = Column(Integer, ForeignKey("research_runs.id"), nullable=False)
    topic = Column(String, nullable=False)
    content = Column(Text, nullable=True)
