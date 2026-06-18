"""Tests for the enterprise background job system."""

from datetime import datetime, timedelta, timezone

from app.core.security import hash_password, create_access_token
from app.models.enums import UserRole, JobStatus, JobType
from app.models.user import User
from app.models.job import Job

JOBS_URL = "/jobs"


# ------------------------------------------------------------------
#  Seed helpers
# ------------------------------------------------------------------

def _user(db, email, role, **kw):
    u = User(email=email, hashed_password=hash_password("p"), role=role, **kw)
    db.add(u); db.flush()
    return u


def _token(u):
    return create_access_token({"sub": str(u.id), "role": u.role.value})


def _seed_admin(db):
    admin_u = _user(db, "admin_jobs@test.com", UserRole.ADMIN)
    db.commit()
    return {"admin_token": _token(admin_u)}


def _seed_doctor(db):
    doc_u = _user(db, "doc_jobs@test.com", UserRole.DOCTOR)
    db.commit()
    return {"doctor_token": _token(doc_u)}


def _seed_patient(db):
    pat_u = _user(db, "pat_jobs@test.com", UserRole.PATIENT)
    db.commit()
    return {"patient_token": _token(pat_u)}


def _create_test_job(db, job_type=JobType.APPOINTMENT_REMINDER, status=JobStatus.PENDING):
    job = Job(job_type=job_type, status=status, payload='{"test": true}', max_retries=3)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


# ====================================================================
#  AUTH & AUTHORIZATION
# ====================================================================


class TestJobsAuth:
    ENDPOINTS = [
        ("POST", JOBS_URL),
        ("GET", JOBS_URL),
        ("GET", f"{JOBS_URL}/1"),
        ("DELETE", f"{JOBS_URL}/1"),
        ("POST", f"{JOBS_URL}/1/retry"),
        ("POST", f"{JOBS_URL}/1/cancel"),
        ("GET", f"{JOBS_URL}/health"),
    ]

    def test_requires_auth(self, client):
        for method, url in self.ENDPOINTS:
            resp = client.request(method, url)
            assert resp.status_code == 401, f"{method} {url} should require auth"

    def test_doctor_cannot_access_create(self, client, db):
        data = _seed_doctor(db)
        resp = client.post(JOBS_URL, json={"job_type": "appointment_reminder"},
                           headers={"Authorization": f"Bearer {data['doctor_token']}"})
        assert resp.status_code == 403

    def test_doctor_cannot_access_list(self, client, db):
        data = _seed_doctor(db)
        resp = client.get(JOBS_URL,
                          headers={"Authorization": f"Bearer {data['doctor_token']}"})
        assert resp.status_code == 403

    def test_patient_cannot_access_create(self, client, db):
        data = _seed_patient(db)
        resp = client.post(JOBS_URL, json={"job_type": "appointment_reminder"},
                           headers={"Authorization": f"Bearer {data['patient_token']}"})
        assert resp.status_code == 403

    def test_admin_can_access(self, client, db):
        data = _seed_admin(db)
        resp = client.post(JOBS_URL, json={"job_type": "appointment_reminder"},
                           headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 201

    def test_admin_can_list(self, client, db):
        data = _seed_admin(db)
        resp = client.get(JOBS_URL,
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 200


# ====================================================================
#  JOB CREATION
# ====================================================================


class TestJobCreation:
    def test_create_minimal_job(self, client, db):
        data = _seed_admin(db)
        resp = client.post(JOBS_URL, json={"job_type": "appointment_reminder"},
                           headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 201
        body = resp.json()
        assert body["job_type"] == "appointment_reminder"
        assert body["status"] in ("pending",)
        assert body["id"] >= 1

    def test_create_job_with_payload(self, client, db):
        data = _seed_admin(db)
        resp = client.post(JOBS_URL, json={
            "job_type": "medication_reminder",
            "payload": '{"patient_id": 1, "medication": "Amlodipine"}',
        }, headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 201
        body = resp.json()
        assert body["job_type"] == "medication_reminder"
        assert body["payload"] is not None

    def test_create_scheduled_job(self, client, db):
        data = _seed_admin(db)
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        resp = client.post(JOBS_URL, json={
            "job_type": "analytics_refresh",
            "scheduled_at": future,
        }, headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 201
        body = resp.json()
        assert body["status"] == "scheduled"

    def test_create_all_job_types(self, client, db):
        data = _seed_admin(db)
        for jt in JobType:
            resp = client.post(JOBS_URL, json={"job_type": jt.value},
                               headers={"Authorization": f"Bearer {data['admin_token']}"})
            assert resp.status_code == 201, f"Failed to create job type: {jt.value}"

    def test_create_job_too_many_retries(self, client, db):
        data = _seed_admin(db)
        resp = client.post(JOBS_URL, json={
            "job_type": "appointment_reminder",
            "max_retries": 50,
        }, headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 422

    def test_create_job_negative_retries(self, client, db):
        data = _seed_admin(db)
        resp = client.post(JOBS_URL, json={
            "job_type": "appointment_reminder",
            "max_retries": -1,
        }, headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 422


# ====================================================================
#  JOB LISTING & FILTERING
# ====================================================================


class TestJobListing:
    def test_list_empty(self, client, db):
        data = _seed_admin(db)
        resp = client.get(JOBS_URL,
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["jobs"] == []

    def test_list_with_jobs(self, client, db):
        data = _seed_admin(db)
        _create_test_job(db)
        _create_test_job(db, status=JobStatus.COMPLETED)
        resp = client.get(JOBS_URL,
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert len(body["jobs"]) == 2

    def test_list_filter_by_status(self, client, db):
        data = _seed_admin(db)
        _create_test_job(db, status=JobStatus.PENDING)
        _create_test_job(db, status=JobStatus.COMPLETED)
        resp = client.get(f"{JOBS_URL}?status=pending",
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["jobs"][0]["status"] == "pending"

    def test_list_filter_by_job_type(self, client, db):
        data = _seed_admin(db)
        _create_test_job(db, job_type=JobType.APPOINTMENT_REMINDER)
        _create_test_job(db, job_type=JobType.MEDICATION_REMINDER)
        resp = client.get(f"{JOBS_URL}?job_type=medication_reminder",
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["jobs"][0]["job_type"] == "medication_reminder"

    def test_list_pagination(self, client, db):
        data = _seed_admin(db)
        for _ in range(5):
            _create_test_job(db)
        resp = client.get(f"{JOBS_URL}?skip=0&limit=2",
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["jobs"]) == 2
        assert body["total"] == 5


# ====================================================================
#  JOB RETRIEVAL
# ====================================================================


class TestJobRetrieval:
    def test_get_job_by_id(self, client, db):
        data = _seed_admin(db)
        job = _create_test_job(db)
        resp = client.get(f"{JOBS_URL}/{job.id}",
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == job.id
        assert body["job_type"] == "appointment_reminder"

    def test_get_nonexistent_job(self, client, db):
        data = _seed_admin(db)
        resp = client.get(f"{JOBS_URL}/99999",
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 404

    def test_get_job_returns_all_fields(self, client, db):
        data = _seed_admin(db)
        job = _create_test_job(db)
        resp = client.get(f"{JOBS_URL}/{job.id}",
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        body = resp.json()
        expected = ["id", "job_type", "status", "payload", "result",
                     "error_message", "retry_count", "max_retries",
                     "scheduled_at", "started_at", "completed_at",
                     "created_by", "created_at", "updated_at"]
        for field in expected:
            assert field in body, f"Missing field: {field}"


# ====================================================================
#  JOB RETRY
# ====================================================================


class TestJobRetry:
    def test_retry_failed_job(self, client, db):
        data = _seed_admin(db)
        job = _create_test_job(db, status=JobStatus.FAILED)
        resp = client.post(f"{JOBS_URL}/{job.id}/retry",
                           headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] in ("retrying",)

    def test_retry_nonexistent_job(self, client, db):
        data = _seed_admin(db)
        resp = client.post(f"{JOBS_URL}/99999/retry",
                           headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 404

    def test_retry_exceeds_max_retries(self, client, db):
        data = _seed_admin(db)
        job = Job(job_type=JobType.APPOINTMENT_REMINDER, status=JobStatus.FAILED,
                  retry_count=3, max_retries=3)
        db.add(job); db.commit(); db.refresh(job)
        resp = client.post(f"{JOBS_URL}/{job.id}/retry",
                           headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "failed"
        assert body["error_message"] == "Max retries exceeded"

    def test_retry_with_max_retries_override(self, client, db):
        data = _seed_admin(db)
        job = _create_test_job(db, status=JobStatus.FAILED)
        resp = client.post(f"{JOBS_URL}/{job.id}/retry",
                           json={"max_retries": 5},
                           headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] in ("retrying",)


# ====================================================================
#  JOB CANCELLATION
# ====================================================================


class TestJobCancellation:
    def test_cancel_pending_job(self, client, db):
        data = _seed_admin(db)
        job = _create_test_job(db, status=JobStatus.PENDING)
        resp = client.post(f"{JOBS_URL}/{job.id}/cancel",
                           headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "cancelled"

    def test_cancel_nonexistent_job(self, client, db):
        data = _seed_admin(db)
        resp = client.post(f"{JOBS_URL}/99999/cancel",
                           headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 404

    def test_cancel_already_completed_job(self, client, db):
        data = _seed_admin(db)
        job = _create_test_job(db, status=JobStatus.COMPLETED)
        resp = client.post(f"{JOBS_URL}/{job.id}/cancel",
                           headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "completed"


# ====================================================================
#  JOB DELETION
# ====================================================================


class TestJobDeletion:
    def test_delete_job(self, client, db):
        data = _seed_admin(db)
        job = _create_test_job(db)
        resp = client.delete(f"{JOBS_URL}/{job.id}",
                             headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 204

    def test_delete_nonexistent_job(self, client, db):
        data = _seed_admin(db)
        resp = client.delete(f"{JOBS_URL}/99999",
                             headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 404

    def test_deleted_job_not_listed(self, client, db):
        data = _seed_admin(db)
        job = _create_test_job(db)
        client.delete(f"{JOBS_URL}/{job.id}",
                      headers={"Authorization": f"Bearer {data['admin_token']}"})
        resp = client.get(JOBS_URL,
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


# ====================================================================
#  JOB HEALTH
# ====================================================================


class TestJobHealth:
    def test_health_requires_auth(self, client):
        assert client.get(f"{JOBS_URL}/health").status_code == 401

    def test_health_admin_only(self, client, db):
        data = _seed_doctor(db)
        resp = client.get(f"{JOBS_URL}/health",
                          headers={"Authorization": f"Bearer {data['doctor_token']}"})
        assert resp.status_code == 403

    def test_health_returns_expected_fields(self, client, db):
        data = _seed_admin(db)
        resp = client.get(f"{JOBS_URL}/health",
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 200
        body = resp.json()
        expected = ["status", "total_jobs", "pending_jobs",
                     "running_jobs", "failed_jobs", "scheduler_running"]
        for field in expected:
            assert field in body, f"Missing field: {field}"
        assert body["status"] == "healthy"

    def test_health_counts_accurate(self, client, db):
        data = _seed_admin(db)
        _create_test_job(db, status=JobStatus.PENDING)
        _create_test_job(db, status=JobStatus.RUNNING)
        _create_test_job(db, status=JobStatus.FAILED)
        resp = client.get(f"{JOBS_URL}/health",
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        body = resp.json()
        assert body["total_jobs"] == 3
        assert body["pending_jobs"] == 1
        assert body["running_jobs"] == 1
        assert body["failed_jobs"] == 1


# ====================================================================
#  EDGE CASES
# ====================================================================


class TestJobsEdgeCases:
    def test_create_job_invalid_type(self, client, db):
        data = _seed_admin(db)
        resp = client.post(JOBS_URL, json={"job_type": "invalid_type"},
                           headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 422

    def test_list_with_skip_greater_than_total(self, client, db):
        data = _seed_admin(db)
        _create_test_job(db)
        resp = client.get(f"{JOBS_URL}?skip=100",
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["jobs"] == []
        assert body["total"] == 1

    def test_concurrent_jobs(self, client, db):
        data = _seed_admin(db)
        jobs = []
        for i in range(10):
            jt = list(JobType)[i % len(list(JobType))]
            resp = client.post(JOBS_URL, json={"job_type": jt.value},
                               headers={"Authorization": f"Bearer {data['admin_token']}"})
            assert resp.status_code == 201
            jobs.append(resp.json())
        assert len(jobs) == 10
        assert all(j["id"] >= 1 for j in jobs)

    def test_cancel_running_job(self, client, db):
        data = _seed_admin(db)
        job = _create_test_job(db, status=JobStatus.RUNNING)
        resp = client.post(f"{JOBS_URL}/{job.id}/cancel",
                           headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    def test_retry_pending_job(self, client, db):
        data = _seed_admin(db)
        job = _create_test_job(db, status=JobStatus.PENDING)
        resp = client.post(f"{JOBS_URL}/{job.id}/retry",
                           headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] in ("retrying",)


# ====================================================================
#  RESPONSE SHAPE
# ====================================================================


class TestJobsResponseShape:
    def test_list_response_shape(self, client, db):
        data = _seed_admin(db)
        _create_test_job(db)
        resp = client.get(JOBS_URL,
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        body = resp.json()
        assert "jobs" in body
        assert "total" in body
        assert isinstance(body["jobs"], list)
        assert isinstance(body["total"], int)

    def test_job_response_shape(self, client, db):
        data = _seed_admin(db)
        job = _create_test_job(db)
        resp = client.get(f"{JOBS_URL}/{job.id}",
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        body = resp.json()
        required = ["id", "job_type", "status", "retry_count", "max_retries",
                     "created_at", "payload", "result", "error_message",
                     "scheduled_at", "started_at", "completed_at", "created_by",
                     "updated_at"]
        for field in required:
            assert field in body, f"Missing field: {field}"

    def test_health_response_shape(self, client, db):
        data = _seed_admin(db)
        resp = client.get(f"{JOBS_URL}/health",
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        body = resp.json()
        required = ["status", "total_jobs", "pending_jobs",
                     "running_jobs", "failed_jobs", "scheduler_running"]
        for field in required:
            assert field in body, f"Missing field: {field}"
