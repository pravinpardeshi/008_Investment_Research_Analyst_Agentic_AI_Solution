import os
import logging

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

from config.settings import DATABASE_URL

logger = logging.getLogger(__name__)

_db_url = os.getenv("DATABASE_URL", DATABASE_URL)
engine = create_engine(_db_url)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    _run_migrations()


def _run_migrations():
    inspector = inspect(engine)
    try:
        columns = {c["name"] for c in inspector.get_columns("documents")}
    except Exception:
        columns = set()

    with engine.begin() as conn:
        if "status" not in columns:
            logger.info("Migration: adding column 'status' to documents")
            conn.execute(text("ALTER TABLE documents ADD COLUMN status VARCHAR DEFAULT 'pending'"))
        if "chunk_count" not in columns:
            logger.info("Migration: adding column 'chunk_count' to documents")
            conn.execute(text("ALTER TABLE documents ADD COLUMN chunk_count INTEGER DEFAULT 0"))

    try:
        columns = {c["name"] for c in inspector.get_columns("documents")}
    except Exception:
        columns = set()

    with engine.begin() as conn:
        if "error_message" not in columns:
            logger.info("Migration: adding column 'error_message' to documents")
            conn.execute(text("ALTER TABLE documents ADD COLUMN error_message VARCHAR"))
        if "processed_chunks" not in columns:
            logger.info("Migration: adding column 'processed_chunks' to documents")
            conn.execute(text("ALTER TABLE documents ADD COLUMN processed_chunks INTEGER DEFAULT 0"))

    with engine.begin() as conn:
        conn.execute(
            text("UPDATE documents SET status = 'pending' WHERE status NOT IN ('ready', 'failed', 'pending', 'cancelled')")
        )
