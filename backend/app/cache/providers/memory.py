import fnmatch
import sys
import threading
from typing import Any

from app.cache.base import CacheEntry, CacheProvider, CacheStats, TTL


class MemoryCacheProvider(CacheProvider):
    def __init__(self) -> None:
        self._store: dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None
            if entry.is_expired:
                del self._store[key]
                self._evictions += 1
                self._misses += 1
                return None
            entry.hit_count += 1
            self._hits += 1
            return entry.value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        effective_ttl = ttl
        if effective_ttl is None:
            effective_ttl = TTL.MEDIUM
        if effective_ttl <= 0:
            return
        with self._lock:
            self._store[key] = CacheEntry(
                key=key,
                value=value,
                ttl=effective_ttl,
            )

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    def exists(self, key: str) -> bool:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return False
            if entry.is_expired:
                del self._store[key]
                self._evictions += 1
                return False
            return True

    def clear(self, pattern: str | None = None) -> int:
        with self._lock:
            if pattern is None:
                count = len(self._store)
                self._store.clear()
                return count
            keys_to_delete = [k for k in self._store if fnmatch.fnmatch(k, pattern)]
            for k in keys_to_delete:
                del self._store[k]
            return len(keys_to_delete)

    def get_stats(self) -> CacheStats:
        with self._lock:
            size = len(self._store)
            mem_estimate = 0
            for k, v in self._store.items():
                mem_estimate += len(k) * 2
                mem_estimate += sys.getsizeof(v.value, 0)
            return CacheStats(
                size=size,
                hits=self._hits,
                misses=self._misses,
                evictions=self._evictions,
                memory_estimate_bytes=mem_estimate,
            )

    def get_many(self, keys: list[str]) -> dict[str, Any | None]:
        return {key: self.get(key) for key in keys}

    def set_many(self, mapping: dict[str, Any], ttl: int | None = None) -> None:
        for key, value in mapping.items():
            self.set(key, value, ttl)
