from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.jobs.base import SchedulerProvider
from app.jobs.registry import JobRegistry
from app.jobs.scheduler import get_scheduler
from app.jobs.tasks.health_tasks import register_health_tasks
from app.models.enums import JobStatus, JobType
from app.models.job import Job
from app.schemas.job import (
    JobCreate,
    JobHealthResponse,
    JobListResponse,
    JobResponse,
    JobRetryRequest,
    JobUpdate,
)

_registered = False


def ensure_tasks_registered() -> None:
    global _registered
    if not _registered:
        register_health_tasks()
        _registered = True


class JobService:

    @staticmethod
    def submit_job(
        db: Session,
        job_data: JobCreate,
        scheduler: SchedulerProvider | None = None,
    ) -> JobResponse:
        ensure_tasks_registered()
        definition = JobRegistry.get(job_data.job_type.value)
        status = JobStatus.PENDING if not job_data.scheduled_at else JobStatus.SCHEDULED

        job = Job(
            job_type=job_data.job_type,
            status=status,
            payload=job_data.payload,
            max_retries=job_data.max_retries,
            scheduled_at=job_data.scheduled_at,
            created_by=job_data.created_by,
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        if not job_data.scheduled_at and scheduler is None:
            scheduler = get_scheduler()

        if not job_data.scheduled_at:
            scheduler.schedule_immediate(job_data.job_type.value, job_data.payload, job.id)

        return JobResponse.model_validate(job)

    @staticmethod
    def get_job(db: Session, job_id: int) -> JobResponse | None:
        job = db.get(Job, job_id)
        if not job:
            return None
        return JobResponse.model_validate(job)

    @staticmethod
    def list_jobs(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        status: JobStatus | None = None,
        job_type: JobType | None = None,
    ) -> JobListResponse:
        stmt = select(Job)
        if status:
            stmt = stmt.where(Job.status == status)
        if job_type:
            stmt = stmt.where(Job.job_type == job_type)
        total = db.scalar(select(func.count(Job.id)).where(stmt.exists().where(True)))
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

        count_stmt = select(func.count(Job.id))
        if status:
            count_stmt = count_stmt.where(Job.status == status)
        if job_type:
            count_stmt = count_stmt.where(Job.job_type == job_type)
        total = db.scalar(count_stmt) or 0

        rows = db.scalars(stmt.order_by(Job.created_at.desc()).offset(skip).limit(limit)).all()
        return JobListResponse(
            jobs=[JobResponse.model_validate(r) for r in rows],
            total=total,
        )

    @staticmethod
    def update_job(db: Session, job_id: int, job_update: JobUpdate) -> JobResponse | None:
        job = db.get(Job, job_id)
        if not job:
            return None
        data = job_update.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(job, key, value)
        db.commit()
        db.refresh(job)
        return JobResponse.model_validate(job)

    @staticmethod
    def delete_job(db: Session, job_id: int) -> bool:
        job = db.get(Job, job_id)
        if not job:
            return False
        db.delete(job)
        db.commit()
        return True

    @staticmethod
    def retry_job(
        db: Session,
        job_id: int,
        retry_data: JobRetryRequest | None = None,
        scheduler: SchedulerProvider | None = None,
    ) -> JobResponse | None:
        job = db.get(Job, job_id)
        if not job:
            return None
        if job.retry_count >= job.max_retries:
            job.status = JobStatus.FAILED
            job.error_message = "Max retries exceeded"
            db.commit()
            db.refresh(job)
            return JobResponse.model_validate(job)

        job.status = JobStatus.RETRYING
        job.retry_count += 1
        if retry_data and retry_data.max_retries is not None:
            job.max_retries = retry_data.max_retries
        db.commit()
        db.refresh(job)

        if scheduler is None:
            scheduler = get_scheduler()
        scheduler.schedule_immediate(job.job_type.value, job.payload, job.id)

        return JobResponse.model_validate(job)

    @staticmethod
    def cancel_job(db: Session, job_id: int) -> JobResponse | None:
        job = db.get(Job, job_id)
        if not job:
            return None
        if job.status in (JobStatus.COMPLETED, JobStatus.CANCELLED):
            return JobResponse.model_validate(job)
        job.status = JobStatus.CANCELLED
        db.commit()
        db.refresh(job)
        return JobResponse.model_validate(job)

    @staticmethod
    def get_health(db: Session, scheduler: SchedulerProvider | None = None) -> JobHealthResponse:
        if scheduler is None:
            scheduler = get_scheduler()
        total = db.scalar(select(func.count(Job.id))) or 0
        pending = db.scalar(select(func.count(Job.id)).where(Job.status == JobStatus.PENDING)) or 0
        running = db.scalar(select(func.count(Job.id)).where(Job.status == JobStatus.RUNNING)) or 0
        failed = db.scalar(select(func.count(Job.id)).where(Job.status == JobStatus.FAILED)) or 0
        return JobHealthResponse(
            status="healthy",
            total_jobs=total,
            pending_jobs=pending,
            running_jobs=running,
            failed_jobs=failed,
            scheduler_running=scheduler.is_running,
        )

    @staticmethod
    def update_job_status(
        db: Session, job_id: int, status: JobStatus,
        result: str | None = None, error: str | None = None,
    ) -> None:
        job = db.get(Job, job_id)
        if not job:
            return
        job.status = status
        if result:
            job.result = result
        if error:
            job.error_message = error
        if status == JobStatus.RUNNING:
            job.started_at = datetime.now(timezone.utc)
        if status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            job.completed_at = datetime.now(timezone.utc)
        db.commit()
