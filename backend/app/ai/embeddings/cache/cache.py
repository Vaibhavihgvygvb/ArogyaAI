from datetime import datetime, timezone

from app.ai.embeddings.exceptions.exceptions import CacheError
from app.ai.embeddings.interfaces.interfaces import EmbeddingCache
from app.ai.embeddings.schemas.schemas import EmbeddingStatus, EmbeddingVector


class MemoryEmbeddingCache(EmbeddingCache):
    def __init__(self):
        self._cache: dict[str, EmbeddingVector] = {}
        self._hits: int = 0
        self._misses: int = 0

    def _key(self, content_hash: str, provider: str, model: str) -> str:
        return f"{provider}:{model}:{content_hash}"

    async def get(self, content_hash: str, provider: str, model: str) -> EmbeddingVector | None:
        key = self._key(content_hash, provider, model)
        result = self._cache.get(key)
        if result is not None:
            self._hits += 1
        else:
            self._misses += 1
        return result

    async def set(self, vector: EmbeddingVector) -> None:
        key = self._key(vector.content_hash, vector.provider.value, vector.model)
        self._cache[key] = vector

    async def has(self, content_hash: str, provider: str, model: str) -> bool:
        key = self._key(content_hash, provider, model)
        return key in self._cache

    async def clear(self) -> None:
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    async def invalidate(self, content_hash: str) -> None:
        keys = [k for k in self._cache if k.endswith(f":{content_hash}")]
        for k in keys:
            del self._cache[k]

    @property
    def hits(self) -> int:
        return self._hits

    @property
    def misses(self) -> int:
        return self._misses
