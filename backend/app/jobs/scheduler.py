from datetime import datetime
from typing import Any

from app.jobs.base import JobResult, SchedulerProvider
from app.jobs.registry import JobRegistry
from app.jobs.workers.in_process_worker import InProcessWorker

_scheduler_provider: SchedulerProvider | None = None


class APSchedulerProvider(SchedulerProvider):
    def __init__(self, worker: InProcessWorker | None = None):
        self._worker = worker or InProcessWorker()
        self._scheduler = None
        self._running = False
        self._scheduled_jobs: dict[str, Any] = {}

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False
        self._scheduled_jobs.clear()

    def schedule_immediate(self, job_type: str, payload: str | None = None, job_id: int | None = None) -> str:
        scheduler_id = f"{job_type}_{job_id or id(payload)}_{datetime.now().timestamp()}"
        self._worker.execute(job_type, payload, job_id)
        return scheduler_id

    def schedule_delayed(self, job_type: str, run_at: datetime, payload: str | None = None, job_id: int | None = None) -> str:
        scheduler_id = f"delayed_{job_type}_{job_id or id(payload)}_{run_at.timestamp()}"
        self._scheduled_jobs[scheduler_id] = {
            "job_type": job_type,
            "run_at": run_at,
            "payload": payload,
            "job_id": job_id,
        }
        return scheduler_id

    def schedule_recurring(self, job_type: str, cron_expr: str, payload: str | None = None) -> str:
        scheduler_id = f"recurring_{job_type}_{cron_expr}"
        self._scheduled_jobs[scheduler_id] = {
            "job_type": job_type,
            "cron": cron_expr,
            "payload": payload,
            "recurring": True,
        }
        return scheduler_id

    def cancel(self, scheduler_job_id: str) -> bool:
        return self._scheduled_jobs.pop(scheduler_job_id, None) is not None

    @property
    def is_running(self) -> bool:
        return self._running


def get_scheduler() -> SchedulerProvider:
    global _scheduler_provider
    if _scheduler_provider is None:
        _scheduler_provider = APSchedulerProvider()
    return _scheduler_provider


def set_scheduler_provider(provider: SchedulerProvider) -> None:
    global _scheduler_provider
    _scheduler_provider = provider
