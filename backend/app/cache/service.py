import json
from typing import Any, Callable

from app.cache.base import CacheStats
from app.cache.deps import get_cache_provider
from app.core.config import settings


class CacheService:
    NAMESPACE_DASHBOARD = "dashboard"
    NAMESPACE_ANALYTICS = "analytics"
    NAMESPACE_SEARCH = "search"
    NAMESPACE_NOTIFICATION = "notification"
    NAMESPACE_MEDICINE = "medicine"
    NAMESPACE_FEATURE = "feature"

    _VERSION = "v1"

    @staticmethod
    def build_key(namespace: str, *parts: str) -> str:
        parts_str = ":".join(str(p) for p in parts if p is not None)
        return f"{settings.REDIS_PREFIX}:{CacheService._VERSION}:{namespace}:{parts_str}"

    @staticmethod
    def build_namespace_pattern(namespace: str) -> str:
        return f"{settings.REDIS_PREFIX}:{CacheService._VERSION}:{namespace}:*"

    @staticmethod
    def get(key: str) -> Any | None:
        provider = get_cache_provider()
        value = provider.get(key)
        if value is None:
            return None
        return CacheService._deserialize(value)

    @staticmethod
    def set(key: str, value: Any, ttl: int | None = None) -> None:
        provider = get_cache_provider()
        serialized = CacheService._serialize(value)
        provider.set(key, serialized, ttl)

    @staticmethod
    def delete(key: str) -> bool:
        provider = get_cache_provider()
        return provider.delete(key)

    @staticmethod
    def exists(key: str) -> bool:
        provider = get_cache_provider()
        return provider.exists(key)

    @staticmethod
    def get_or_set(
        key: str,
        ttl: int,
        func: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        provider = get_cache_provider()
        cached = provider.get(key)
        if cached is not None:
            return CacheService._deserialize(cached)
        result = func(*args, **kwargs)
        serialized = CacheService._serialize(result)
        provider.set(key, serialized, ttl)
        return result

    @staticmethod
    def invalidate_namespace(namespace: str) -> int:
        provider = get_cache_provider()
        pattern = CacheService.build_namespace_pattern(namespace)
        return provider.clear(pattern)

    @staticmethod
    def invalidate_key(key: str) -> bool:
        provider = get_cache_provider()
        return provider.delete(key)

    @staticmethod
    def clear_all() -> int:
        provider = get_cache_provider()
        return provider.clear()

    @staticmethod
    def get_stats() -> CacheStats:
        provider = get_cache_provider()
        return provider.get_stats()

    @staticmethod
    def get_many(keys: list[str]) -> dict[str, Any | None]:
        provider = get_cache_provider()
        raw = provider.get_many(keys)
        result = {}
        for k, v in raw.items():
            result[k] = CacheService._deserialize(v) if v is not None else None
        return result

    @staticmethod
    def _serialize(value: Any) -> Any:
        if hasattr(value, "model_dump_json"):
            return value.model_dump_json()
        if hasattr(value, "model_dump"):
            return json.dumps(value.model_dump(), default=str)
        return json.dumps(value, default=str)

    @staticmethod
    def _deserialize(value: Any) -> Any:
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        return value
