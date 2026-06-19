import threading

from app.ai.vector.exceptions.exceptions import VectorStoreError
from app.ai.vector.interfaces.interfaces import VectorStoreProvider
from app.ai.vector.utils.utils import cosine_similarity


class MemoryVectorStore(VectorStoreProvider):
    def __init__(self):
        self._vectors: dict[str, list[float]] = {}
        self._metadata: dict[str, dict] = {}
        self._lock = threading.Lock()

    async def add(self, embedding_id: str, vector: list[float], metadata: dict | None = None) -> str:
        if not vector:
            raise VectorStoreError("Cannot add empty vector")
        with self._lock:
            self._vectors[embedding_id] = vector
            self._metadata[embedding_id] = metadata or {}
        return embedding_id

    async def add_batch(self, vectors: list[tuple[str, list[float], dict | None]]) -> list[str]:
        ids = []
        for emb_id, vec, meta in vectors:
            await self.add(emb_id, vec, meta)
            ids.append(emb_id)
        return ids

    async def search(
        self,
        query_vector: list[float],
        top_k: int = 10,
        filters: dict | None = None,
    ) -> list[dict]:
        with self._lock:
            items = list(self._vectors.items())

        scored = []
        for emb_id, vec in items:
            if filters:
                meta = self._metadata.get(emb_id, {})
                if not self._matches_filters(meta, filters):
                    continue
            score = cosine_similarity(query_vector, vec)
            scored.append((emb_id, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:top_k]

        results = []
        for emb_id, score in top:
            meta = dict(self._metadata.get(emb_id, {}))
            results.append({
                "embedding_id": emb_id,
                "chunk_id": meta.pop("chunk_id", None),
                "knowledge_id": meta.pop("knowledge_id", None),
                "score": round(score, 6),
                "metadata": meta,
                "vector": list(self._vectors[emb_id]),
            })
        return results

    async def delete(self, embedding_id: str) -> bool:
        with self._lock:
            if embedding_id in self._vectors:
                del self._vectors[embedding_id]
                self._metadata.pop(embedding_id, None)
                return True
            return False

    async def delete_by_filter(self, filters: dict) -> int:
        to_delete = []
        with self._lock:
            for emb_id, meta in self._metadata.items():
                if self._matches_filters(meta, filters):
                    to_delete.append(emb_id)
            for emb_id in to_delete:
                del self._vectors[emb_id]
                del self._metadata[emb_id]
        return len(to_delete)

    async def count(self) -> int:
        with self._lock:
            return len(self._vectors)

    async def clear(self) -> None:
        with self._lock:
            self._vectors.clear()
            self._metadata.clear()

    def provider_name(self) -> str:
        return "memory"

    def _matches_filters(self, metadata: dict, filters: dict) -> bool:
        for key, value in filters.items():
            if key == "$and":
                if not all(self._matches_filters(metadata, cond) for cond in value):
                    return False
                continue
            if key == "$or":
                if not any(self._matches_filters(metadata, cond) for cond in value):
                    return False
                continue
            if key not in metadata:
                return False
            meta_val = metadata[key]
            if isinstance(value, dict):
                for op, op_val in value.items():
                    if op == "$gt" and not (meta_val > op_val):
                        return False
                    if op == "$gte" and not (meta_val >= op_val):
                        return False
                    if op == "$lt" and not (meta_val < op_val):
                        return False
                    if op == "$lte" and not (meta_val <= op_val):
                        return False
                    if op == "$ne" and not (meta_val != op_val):
                        return False
                    if op == "$in" and meta_val not in op_val:
                        return False
            elif isinstance(value, list):
                if meta_val not in value:
                    return False
            elif meta_val != value:
                return False
        return True
