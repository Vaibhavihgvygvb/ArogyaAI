from app.jobs.registry import JobRegistry
from app.jobs.base import JobPriority


def appointment_reminder(payload: str | None = None, job_id: int | None = None) -> dict:
    return {"task": "appointment_reminder", "status": "simulated", "job_id": job_id}


def medication_reminder(payload: str | None = None, job_id: int | None = None) -> dict:
    return {"task": "medication_reminder", "status": "simulated", "job_id": job_id}


def unread_notification_reminder(payload: str | None = None, job_id: int | None = None) -> dict:
    return {"task": "unread_notification_reminder", "status": "simulated", "job_id": job_id}


def analytics_refresh(payload: str | None = None, job_id: int | None = None) -> dict:
    return {"task": "analytics_refresh", "status": "simulated", "job_id": job_id}


def dashboard_cache_refresh(payload: str | None = None, job_id: int | None = None) -> dict:
    return {"task": "dashboard_cache_refresh", "status": "simulated", "job_id": job_id}


def search_index_refresh(payload: str | None = None, job_id: int | None = None) -> dict:
    return {"task": "search_index_refresh", "status": "simulated", "job_id": job_id}


def audit_cleanup(payload: str | None = None, job_id: int | None = None) -> dict:
    return {"task": "audit_cleanup", "status": "simulated", "job_id": job_id}


def expired_notification_cleanup(payload: str | None = None, job_id: int | None = None) -> dict:
    return {"task": "expired_notification_cleanup", "status": "simulated", "job_id": job_id}


def temp_file_cleanup(payload: str | None = None, job_id: int | None = None) -> dict:
    return {"task": "temp_file_cleanup", "status": "simulated", "job_id": job_id}


def database_maintenance(payload: str | None = None, job_id: int | None = None) -> dict:
    return {"task": "database_maintenance", "status": "simulated", "job_id": job_id}


def register_health_tasks() -> None:
    JobRegistry.register("appointment_reminder", appointment_reminder,
                         description="Send reminders for upcoming appointments",
                         max_retries=3, priority=JobPriority.HIGH, idempotent=True)

    JobRegistry.register("medication_reminder", medication_reminder,
                         description="Send medication adherence reminders",
                         max_retries=3, priority=JobPriority.HIGH, idempotent=True)

    JobRegistry.register("unread_notification_reminder", unread_notification_reminder,
                         description="Remind users about unread notifications",
                         max_retries=2, priority=JobPriority.LOW, idempotent=True)

    JobRegistry.register("analytics_refresh", analytics_refresh,
                         description="Refresh analytics aggregation data",
                         max_retries=2, priority=JobPriority.MEDIUM, idempotent=True)

    JobRegistry.register("dashboard_cache_refresh", dashboard_cache_refresh,
                         description="Refresh dashboard cache",
                         max_retries=2, priority=JobPriority.MEDIUM, idempotent=True)

    JobRegistry.register("search_index_refresh", search_index_refresh,
                         description="Refresh search index",
                         max_retries=2, priority=JobPriority.LOW, idempotent=True)

    JobRegistry.register("audit_cleanup", audit_cleanup,
                         description="Clean up old audit log entries",
                         max_retries=1, priority=JobPriority.LOW, idempotent=True)

    JobRegistry.register("expired_notification_cleanup", expired_notification_cleanup,
                         description="Remove expired notifications",
                         max_retries=1, priority=JobPriority.LOW, idempotent=True)

    JobRegistry.register("temp_file_cleanup", temp_file_cleanup,
                         description="Remove temporary files older than 24 hours",
                         max_retries=1, priority=JobPriority.LOW, idempotent=True)

    JobRegistry.register("database_maintenance", database_maintenance,
                         description="Run database maintenance (VACUUM, ANALYZE)",
                         max_retries=1, priority=JobPriority.LOW, idempotent=True)
