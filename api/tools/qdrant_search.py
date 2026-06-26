import logging
import time

from qdrant_client import QdrantClient
from qdrant_client.http import models

from config.settings import QDRANT_URL, QDRANT_COLLECTION, EMBEDDING_DIM

logger = logging.getLogger(__name__)


class QdrantSearch:
    def __init__(self):
        self.client = QdrantClient(url=QDRANT_URL)
        try:
            self._ensure_collection()
        except Exception as e:
            logger.warning("QdrantSearch: could not connect to Qdrant at %s: %s", QDRANT_URL, e)

    def _ensure_collection(self):
        collections = self.client.get_collections().collections
        if not any(c.name == QDRANT_COLLECTION for c in collections):
            self.client.create_collection(
                collection_name=QDRANT_COLLECTION,
                vectors_config=models.VectorParams(
                    size=EMBEDDING_DIM,
                    distance=models.Distance.COSINE,
                ),
            )

    def delete_by_filename(self, filename: str):
        try:
            self.client.delete(
                collection_name=QDRANT_COLLECTION,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="filename",
                                match=models.MatchValue(value=filename),
                            )
                        ]
                    )
                ),
            )
        except Exception as e:
            logger.warning("Qdrant delete failed for %s: %s", filename, e)

    def store_embeddings(self, points: list[dict]):
        self.client.upsert(
            collection_name=QDRANT_COLLECTION,
            points=[
                models.PointStruct(
                    id=p["id"],
                    vector=p["vector"],
                    payload=p.get("payload", {}),
                )
                for p in points
            ],
        )

    def search(self, vector: list[float], top_k: int = 5) -> list[dict]:
        results = self.client.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=vector,
            limit=top_k,
        )
        return [
            {
                "id": hit.id,
                "score": hit.score,
                "text": hit.payload.get("text", ""),
                "metadata": hit.payload,
            }
            for hit in results
        ]
