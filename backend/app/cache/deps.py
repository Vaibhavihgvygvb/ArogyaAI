from app.cache.base import CacheProvider
from app.cache.providers.memory import MemoryCacheProvider
from app.core.config import settings

_provider: CacheProvider | None = None


def get_cache_provider() -> CacheProvider:
    global _provider
    if _provider is not None:
        return _provider
    if settings.CACHE_PROVIDER == "redis" and settings.REDIS_URL:
        from app.cache.providers.redis import RedisCacheProvider
        _provider = RedisCacheProvider(settings.REDIS_URL, settings.REDIS_PREFIX)
    else:
        _provider = MemoryCacheProvider()
    return _provider


def set_cache_provider(provider: CacheProvider) -> None:
    global _provider
    _provider = provider


def reset_cache_provider() -> None:
    global _provider
    _provider = None
