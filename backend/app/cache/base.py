from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any


class TTL:
    SHORT: int = 60
    MEDIUM: int = 300
    LONG: int = 3600
    DAY: int = 86400
    WEEK: int = 604800


@dataclass
class CacheEntry:
    key: str
    value: Any
    ttl: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    hit_count: int = 0

    @property
    def is_expired(self) -> bool:
        elapsed = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        return elapsed > self.ttl

    @property
    def expires_at(self) -> datetime:
        return self.created_at + timedelta(seconds=self.ttl)


@dataclass
class CacheStats:
    size: int = 0
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    memory_estimate_bytes: int = 0


class CacheProvider(ABC):
    @abstractmethod
    def get(self, key: str) -> Any | None:
        ...

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        ...

    @abstractmethod
    def delete(self, key: str) -> bool:
        ...

    @abstractmethod
    def exists(self, key: str) -> bool:
        ...

    @abstractmethod
    def clear(self, pattern: str | None = None) -> int:
        ...

    @abstractmethod
    def get_stats(self) -> CacheStats:
        ...

    @abstractmethod
    def get_many(self, keys: list[str]) -> dict[str, Any | None]:
        ...

    @abstractmethod
    def set_many(self, mapping: dict[str, Any], ttl: int | None = None) -> None:
        ...
