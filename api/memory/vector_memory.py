from api.tools.qdrant_search import QdrantSearch


class VectorMemory:
    def __init__(self):
        self.search_tool = QdrantSearch()

    def store(self, vector: list[float], payload: dict, point_id: int):
        self.search_tool.store_embeddings([
            {"id": point_id, "vector": vector, "payload": payload}
        ])

    def query(self, vector: list[float], top_k: int = 5) -> list[dict]:
        return self.search_tool.search(vector, top_k=top_k)
