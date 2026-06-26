from sqlalchemy import Column, Integer, String, DateTime, func

from api.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    company = Column(String, nullable=True)
    status = Column(String, default="pending")
    chunk_count = Column(Integer, default=0)
    processed_chunks = Column(Integer, default=0)
    error_message = Column(String, nullable=True)
    uploaded_at = Column(DateTime, server_default=func.now())
