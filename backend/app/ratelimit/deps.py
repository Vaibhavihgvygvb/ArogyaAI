from fastapi import Depends, HTTPException, Request, status

from app.core.config import settings
from app.ratelimit.base import RateLimiter
from app.ratelimit.base import RateLimitResult as RateLimitResult_

_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    global _limiter
    if _limiter is not None:
        return _limiter
    if settings.RATE_LIMIT_PROVIDER == "redis" and settings.REDIS_URL:
        from app.ratelimit.providers.redis import RedisRateLimiter
        _limiter = RedisRateLimiter(settings.REDIS_URL, settings.REDIS_PREFIX)
    else:
        from app.ratelimit.providers.memory import MemoryRateLimiter
        _limiter = MemoryRateLimiter()
    return _limiter


def set_rate_limiter(limiter: RateLimiter) -> None:
    global _limiter
    _limiter = limiter


def reset_rate_limiter() -> None:
    global _limiter
    _limiter = None


def rate_limit(limit: int, window_seconds: int):
    async def _rate_limit_dependency(
        request: Request,
        limiter: RateLimiter = Depends(get_rate_limiter),
    ):
        if not settings.RATE_LIMIT_ENABLED:
            return
        client_ip = request.client.host if request.client else "127.0.0.1"
        user = getattr(request.state, "user", None)
        identifier = str(user.id) if user else client_ip
        key = f"ratelimit:endpoint:{identifier}:{request.url.path}"
        result = limiter.check(key, limit, window_seconds)
        if not result.allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "message": "Too many requests",
                    "retry_after_seconds": result.retry_after_seconds,
                },
                headers=result.headers,
            )
    return _rate_limit_dependency
