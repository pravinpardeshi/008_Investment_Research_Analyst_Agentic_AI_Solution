import logging
import threading
import time
from pathlib import Path

from api.database import SessionLocal
from api.models import Document
from api.tools import DocumentLoader, QdrantSearch
from api.utils.llm import get_embedding

logger = logging.getLogger(__name__)


def index_document(document_id: int):
    thread = threading.Thread(
        target=_index_worker,
        args=(document_id,),
        daemon=True,
    )
    thread.start()


def _index_worker(document_id: int):
    time.sleep(1)
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            logger.warning("Document %d not found for indexing", document_id)
            return

        doc.status = "processing"
        doc.processed_chunks = 0
        doc.error_message = None
        db.commit()

        file_path = Path("data") / "annual_reports" / doc.filename
        if not file_path.exists():
            doc.status = "failed"
            doc.error_message = f"File not found: {file_path}"
            db.commit()
            logger.error("File not found: %s", file_path)
            return

        loader = DocumentLoader()
        chunks = loader.load(str(file_path))
        total = len(chunks)
        doc.chunk_count = total
        db.commit()
        logger.info("Indexing %d chunks for document %d (%s)", total, document_id, doc.filename)

        indexed = 0
        errors = []

        try:
            search = QdrantSearch()
            for i, chunk in enumerate(chunks):
                try:
                    vector = get_embedding(chunk["text"])
                    if any(v != 0.0 for v in vector):
                        search.store_embeddings([
                            {
                                "id": abs(hash(f"{doc.filename}_{i}")),
                                "vector": vector,
                                "payload": {
                                    "text": chunk["text"][:2000],
                                    "filename": doc.filename,
                                    "company": doc.company or "",
                                    "chunk_index": i,
                                },
                            }
                        ])
                        indexed += 1
                except Exception as e:
                    errors.append(f"chunk {i}: {e}")
                    logger.warning("Chunk %d/%d failed for document %d: %s", i + 1, total, document_id, e)

                doc.processed_chunks = i + 1
                db.commit()

        except Exception as e:
            logger.warning("Qdrant indexing error: %s", e)
            errors.append(f"qdrant: {e}")

        doc.status = "ready" if indexed > 0 else "failed"
        doc.chunk_count = indexed
        doc.processed_chunks = indexed
        doc.error_message = "; ".join(errors[:5]) if errors else None
        db.commit()
        logger.info(
            "Document %d (%s): %d/%d chunks indexed, status=%s",
            document_id, doc.filename, indexed, total, doc.status,
        )

    except Exception as e:
        logger.error("Indexing failed for document %d: %s", document_id, e)
        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.status = "failed"
                doc.error_message = str(e)[:500]
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
