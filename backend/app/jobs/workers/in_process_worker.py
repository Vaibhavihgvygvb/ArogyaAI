import time
import traceback
from datetime import datetime, timezone

from app.jobs.base import JobResult, WorkerBase
from app.jobs.registry import JobRegistry


class InProcessWorker(WorkerBase):
    def execute(self, job_type: str, payload: str | None = None, job_id: int | None = None) -> JobResult:
        handler = JobRegistry.get_handler(job_type)
        if not handler:
            return JobResult(job_id=job_id, success=False, error=f"No handler registered for job type: {job_type}")

        start = time.time()
        try:
            result = handler(payload=payload, job_id=job_id)
            duration = int((time.time() - start) * 1000)
            return JobResult(job_id=job_id, success=True, result=result, duration_ms=duration)
        except Exception as e:
            duration = int((time.time() - start) * 1000)
            return JobResult(job_id=job_id, success=False, error=f"{type(e).__name__}: {e}", duration_ms=duration)
