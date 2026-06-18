import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any

from app.ratelimit.base import RateLimiter, RateLimitResult


class MemoryRateLimiter(RateLimiter):
    def __init__(self) -> None:
        self._buckets: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        now = time.time()
        bucket = self._buckets[key]

        while bucket and bucket[0] < now - window_seconds:
            bucket.popleft()

        if len(bucket) >= limit:
            oldest = bucket[0]
            retry_after = int(oldest + window_seconds - now) + 1
            reset_at = datetime.fromtimestamp(oldest + window_seconds, tz=timezone.utc)
            return RateLimitResult(
                allowed=False,
                limit=limit,
                remaining=0,
                reset_at=reset_at,
                retry_after_seconds=max(1, retry_after),
            )

        bucket.append(now)
        reset_at = datetime.fromtimestamp(now + window_seconds, tz=timezone.utc)
        return RateLimitResult(
            allowed=True,
            limit=limit,
            remaining=limit - len(bucket),
            reset_at=reset_at,
        )

    def reset(self, key: str) -> None:
        self._buckets.pop(key, None)

    def get_remaining(self, key: str, limit: int, window_seconds: int) -> int:
        now = time.time()
        bucket = self._buckets.get(key, deque())
        while bucket and bucket[0] < now - window_seconds:
            bucket.popleft()
        return max(0, limit - len(bucket))

    def clear_all(self) -> int:
        count = len(self._buckets)
        self._buckets.clear()
        return count
