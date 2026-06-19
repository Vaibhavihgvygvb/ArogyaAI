import time
from datetime import datetime, timezone

from app.ai.vector.exceptions.exceptions import VectorStoreError
from app.ai.vector.interfaces.interfaces import VectorStoreProvider
from app.ai.vector.providers.memory import MemoryVectorStore
from app.ai.vector.schemas.schemas import SearchResult, SearchResponse, VectorStats


class VectorService:
    def __init__(self, store: VectorStoreProvider | None = None):
        self._store = store or MemoryVectorStore()

    async def index_vector(
        self,
        embedding_id: str,
        vector: list[float],
        metadata: dict | None = None,
    ) -> str:
        return await self._store.add(embedding_id, vector, metadata)

    async def index_batch(
        self,
        vectors: list[tuple[str, list[float], dict | None]],
    ) -> list[str]:
        return await self._store.add_batch(vectors)

    async def search_by_vector(
        self,
        query_vector: list[float],
        top_k: int = 10,
        filters: dict | None = None,
        include_vectors: bool = False,
    ) -> SearchResponse:
        start = time.time()
        results = await self._store.search(
            query_vector=query_vector,
            top_k=top_k,
            filters=filters,
        )
        elapsed = round((time.time() - start) * 1000, 2)

        items = []
        for r in results:
            items.append(SearchResult(
                embedding_id=r["embedding_id"],
                chunk_id=r.get("chunk_id"),
                knowledge_id=r.get("knowledge_id"),
                score=r["score"],
                metadata=r.get("metadata", {}),
                vector=r.get("vector") if include_vectors else None,
            ))

        return SearchResponse(results=items, total=len(items), query_time_ms=elapsed)

    async def delete(self, embedding_id: str) -> bool:
        return await self._store.delete(embedding_id)

    async def delete_by_filter(self, filters: dict) -> int:
        return await self._store.delete_by_filter(filters)

    async def get_stats(self) -> VectorStats:
        total = await self._store.count()
        return VectorStats(
            total_vectors=total,
            provider=self._store.provider_name(),
        )

    async def clear(self) -> int:
        count = await self._store.count()
        await self._store.clear()
        return count

    @property
    def store(self) -> VectorStoreProvider:
        return self._store
