from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable


class JobPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class JobDefinition:
    job_type: str
    handler: Callable[..., Any]
    description: str = ""
    max_retries: int = 3
    priority: JobPriority = JobPriority.MEDIUM
    timeout_seconds: int = 300
    idempotent: bool = False


@dataclass
class JobResult:
    job_id: int | None = None
    success: bool = False
    result: Any = None
    error: str | None = None
    duration_ms: int = 0


class WorkerBase(ABC):
    @abstractmethod
    def execute(self, job_type: str, payload: str | None = None, job_id: int | None = None) -> JobResult:
        ...


class SchedulerProvider(ABC):
    @abstractmethod
    def start(self) -> None:
        ...

    @abstractmethod
    def stop(self) -> None:
        ...

    @abstractmethod
    def schedule_immediate(self, job_type: str, payload: str | None = None, job_id: int | None = None) -> str:
        ...

    @abstractmethod
    def schedule_delayed(self, job_type: str, run_at: datetime, payload: str | None = None, job_id: int | None = None) -> str:
        ...

    @abstractmethod
    def schedule_recurring(self, job_type: str, cron_expr: str, payload: str | None = None) -> str:
        ...

    @abstractmethod
    def cancel(self, scheduler_job_id: str) -> bool:
        ...

    @property
    @abstractmethod
    def is_running(self) -> bool:
        ...
