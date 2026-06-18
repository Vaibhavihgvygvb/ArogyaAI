import json
from typing import Any

import redis

from app.cache.base import CacheProvider, CacheStats, TTL


class RedisCacheProvider(CacheProvider):
    def __init__(self, redis_url: str, prefix: str = "arogyaai") -> None:
        self._client = redis.from_url(redis_url, decode_responses=True)
        self._prefix = prefix

    def _key(self, key: str) -> str:
        return f"{self._prefix}:{key}" if not key.startswith(f"{self._prefix}:") else key

    def get(self, key: str) -> Any | None:
        val = self._client.get(self._key(key))
        if val is None:
            return None
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return val

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        self._client.set(
            self._key(key),
            json.dumps(value, default=str),
            ex=ttl or TTL.MEDIUM,
        )

    def delete(self, key: str) -> bool:
        return bool(self._client.delete(self._key(key)))

    def exists(self, key: str) -> bool:
        return bool(self._client.exists(self._key(key)))

    def clear(self, pattern: str | None = None) -> int:
        if pattern is None:
            pattern = f"{self._prefix}:*"
        else:
            pattern = self._key(pattern)
        cursor = 0
        deleted = 0
        while True:
            cursor, keys = self._client.scan(cursor=cursor, match=pattern, count=1000)
            if keys:
                deleted += self._client.delete(*keys)
            if cursor == 0:
                break
        return deleted

    def get_stats(self) -> CacheStats:
        keys = self._client.keys(f"{self._prefix}:*")
        info = self._client.info("memory")
        used_memory = info.get("used_memory", 0)
        return CacheStats(
            size=len(keys),
            hits=0,
            misses=0,
            evictions=0,
            memory_estimate_bytes=used_memory,
        )

    def get_many(self, keys: list[str]) -> dict[str, Any | None]:
        redis_keys = [self._key(k) for k in keys]
        values = self._client.mget(redis_keys)
        result = {}
        for key, val in zip(keys, values):
            if val is None:
                result[key] = None
            else:
                try:
                    result[key] = json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    result[key] = val
        return result

    def set_many(self, mapping: dict[str, Any], ttl: int | None = None) -> None:
        pipe = self._client.pipeline()
        for key, value in mapping.items():
            pipe.set(
                self._key(key),
                json.dumps(value, default=str),
                ex=ttl or TTL.MEDIUM,
            )
        pipe.execute()
