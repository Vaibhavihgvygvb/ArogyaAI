from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import JobStatus, JobType


class JobCreate(BaseModel):
    job_type: JobType
    payload: str | None = None
    scheduled_at: datetime | None = None
    max_retries: int = Field(default=3, ge=0, le=10)
    created_by: int | None = None


class JobUpdate(BaseModel):
    status: JobStatus | None = None
    payload: str | None = None
    result: str | None = None
    error_message: str | None = None
    retry_count: int | None = None
    max_retries: int | None = None
    scheduled_at: datetime | None = None


class JobResponse(BaseModel):
    id: int
    job_type: JobType
    status: JobStatus
    payload: str | None = None
    result: str | None = None
    error_message: str | None = None
    retry_count: int = 0
    max_retries: int = 3
    scheduled_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class JobRetryRequest(BaseModel):
    max_retries: int | None = None


class JobListResponse(BaseModel):
    jobs: list[JobResponse]
    total: int


class JobHealthResponse(BaseModel):
    status: str
    total_jobs: int
    pending_jobs: int
    running_jobs: int
    failed_jobs: int
    scheduler_running: bool
