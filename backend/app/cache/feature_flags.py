from app.cache.deps import get_cache_provider
from app.cache.service import CacheService
from app.core.config import settings


class FeatureFlags:
    _FLAG_NAMESPACE = "feature"
    _TTL = settings.CACHE_TTL_FEATURE_FLAG

    @staticmethod
    def is_enabled(flag_name: str) -> bool:
        key = CacheService.build_key(FeatureFlags._FLAG_NAMESPACE, flag_name)
        provider = get_cache_provider()
        cached = provider.get(key)
        if cached is not None:
            return bool(cached)
        return False

    @staticmethod
    def enable(flag_name: str, ttl: int | None = None) -> None:
        key = CacheService.build_key(FeatureFlags._FLAG_NAMESPACE, flag_name)
        provider = get_cache_provider()
        provider.set(key, True, ttl or FeatureFlags._TTL)

    @staticmethod
    def disable(flag_name: str) -> None:
        key = CacheService.build_key(FeatureFlags._FLAG_NAMESPACE, flag_name)
        provider = get_cache_provider()
        provider.delete(key)

    @staticmethod
    def clear_all_flags() -> int:
        provider = get_cache_provider()
        pattern = CacheService.build_namespace_pattern(FeatureFlags._FLAG_NAMESPACE)
        return provider.clear(pattern)
