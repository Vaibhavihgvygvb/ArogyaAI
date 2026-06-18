import time
from datetime import datetime, timezone

import redis

from app.ratelimit.base import RateLimiter, RateLimitResult


class RedisRateLimiter(RateLimiter):
    def __init__(self, redis_url: str, prefix: str = "arogyaai") -> None:
        self._client = redis.from_url(redis_url, decode_responses=True)
        self._prefix = prefix

    def _key(self, key: str) -> str:
        return f"{self._prefix}:{key}"

    def check(self, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        now = time.time()
        window_start = now - window_seconds
        redis_key = self._key(key)

        pipe = self._client.pipeline()
        pipe.zremrangebyscore(redis_key, "-inf", window_start)
        pipe.zadd(redis_key, {str(now): now})
        pipe.zcard(redis_key)
        pipe.expire(redis_key, window_seconds * 2)
        _, _, count, _ = pipe.execute()

        count = count or 0

        if count > limit:
            oldest = self._client.zrange(redis_key, 0, 0, withscores=True)
            if oldest:
                retry_after = int(oldest[0][1] + window_seconds - now) + 1
            else:
                retry_after = 1
            reset_at = datetime.fromtimestamp(now + window_seconds, tz=timezone.utc)
            return RateLimitResult(
                allowed=False,
                limit=limit,
                remaining=0,
                reset_at=reset_at,
                retry_after_seconds=max(1, retry_after),
            )

        reset_at = datetime.fromtimestamp(now + window_seconds, tz=timezone.utc)
        return RateLimitResult(
            allowed=True,
            limit=limit,
            remaining=limit - count,
            reset_at=reset_at,
        )

    def reset(self, key: str) -> None:
        self._client.delete(self._key(key))

    def get_remaining(self, key: str, limit: int, window_seconds: int) -> int:
        now = time.time()
        window_start = now - window_seconds
        redis_key = self._key(key)

        pipe = self._client.pipeline()
        pipe.zremrangebyscore(redis_key, "-inf", window_start)
        pipe.zcard(redis_key)
        pipe.expire(redis_key, window_seconds * 2)
        _, count, _ = pipe.execute()

        return max(0, limit - (count or 0))

    def clear_all(self) -> int:
        cursor = 0
        deleted = 0
        pattern = f"{self._prefix}:ratelimit:*"
        while True:
            cursor, keys = self._client.scan(cursor=cursor, match=pattern, count=1000)
            if keys:
                deleted += self._client.delete(*keys)
            if cursor == 0:
                break
        return deleted
