from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class RateLimitScope(str, Enum):
    GLOBAL = "global"
    USER = "user"
    IP = "ip"
    ROLE = "role"
    ENDPOINT = "endpoint"


@dataclass
class RateLimitRule:
    name: str
    limit: int
    window_seconds: int
    scope: RateLimitScope = RateLimitScope.GLOBAL
    burst_limit: int | None = None
    burst_window_seconds: int | None = None

    def key_for(self, identifier: str, endpoint: str = "") -> str:
        parts = ["ratelimit", self.scope.value, self.name, identifier]
        if endpoint:
            parts.append(endpoint)
        return ":".join(parts)


@dataclass
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    reset_at: datetime
    retry_after_seconds: int = 0

    @property
    def headers(self) -> dict[str, str]:
        h = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(self.remaining),
            "X-RateLimit-Reset": str(int(self.reset_at.timestamp())),
        }
        if not self.allowed and self.retry_after_seconds > 0:
            h["Retry-After"] = str(self.retry_after_seconds)
        return h


class RateLimiter(ABC):
    @abstractmethod
    def check(self, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        ...

    @abstractmethod
    def reset(self, key: str) -> None:
        ...

    @abstractmethod
    def get_remaining(self, key: str, limit: int, window_seconds: int) -> int:
        ...

    @abstractmethod
    def clear_all(self) -> int:
        ...
