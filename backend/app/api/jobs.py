from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.enums import JobStatus, JobType, UserRole
from app.models.user import User
from app.schemas.job import (
    JobCreate,
    JobHealthResponse,
    JobListResponse,
    JobResponse,
    JobRetryRequest,
    JobUpdate,
)
from app.api.deps import get_current_user, require_roles
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new job",
    description="Create and optionally execute a background job. Admin only.",
    responses={
        201: {"description": "Job created"},
        403: {"description": "Admin access required"},
    },
)
def submit_job(
    job_data: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    job_data.created_by = current_user.id
    return JobService.submit_job(db, job_data)


@router.get(
    "",
    response_model=JobListResponse,
    summary="List jobs",
    description="List all background jobs with optional status and type filtering. Admin only.",
    responses={
        200: {"description": "List of jobs"},
        403: {"description": "Admin access required"},
    },
)
def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: JobStatus | None = Query(None),
    job_type: JobType | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    return JobService.list_jobs(db, skip, limit, status, job_type)


@router.get(
    "/health",
    response_model=JobHealthResponse,
    summary="Job system health",
    description="Check the health of the job scheduling system. Admin only.",
    responses={
        200: {"description": "Health status"},
        403: {"description": "Admin access required"},
    },
)
def job_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    return JobService.get_health(db)


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get job details",
    description="Retrieve a specific background job by ID. Admin only.",
    responses={
        200: {"description": "Job details"},
        404: {"description": "Job not found"},
        403: {"description": "Admin access required"},
    },
)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    job = JobService.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a job",
    description="Delete a background job record. Admin only.",
    responses={
        204: {"description": "Job deleted"},
        404: {"description": "Job not found"},
        403: {"description": "Admin access required"},
    },
)
def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    if not JobService.delete_job(db, job_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")


@router.post(
    "/{job_id}/retry",
    response_model=JobResponse,
    summary="Retry a job",
    description="Retry a failed or pending background job. Admin only.",
    responses={
        200: {"description": "Job retried"},
        404: {"description": "Job not found"},
        403: {"description": "Admin access required"},
    },
)
def retry_job(
    job_id: int,
    retry_data: JobRetryRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    job = JobService.retry_job(db, job_id, retry_data)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.post(
    "/{job_id}/cancel",
    response_model=JobResponse,
    summary="Cancel a job",
    description="Cancel a pending or running background job. Admin only.",
    responses={
        200: {"description": "Job cancelled"},
        404: {"description": "Job not found"},
        403: {"description": "Admin access required"},
    },
)
def cancel_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    job = JobService.cancel_job(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job
