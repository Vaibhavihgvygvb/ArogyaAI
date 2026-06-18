"""Tests for the enterprise analytics layer."""

from datetime import date, time, datetime

from app.core.security import hash_password, create_access_token
from app.models.enums import UserRole, AppointmentStatus
from app.models.user import User
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.visit import Visit
from app.models.appointment import Appointment
from app.models.prescription import Prescription
from app.models.prescription_item import PrescriptionItem
from app.models.medical_record import MedicalRecord
from app.models.notification import Notification
from app.models.medicine import Medicine

PLATFORM_URL = "/analytics/platform"
DOCTOR_URL = "/analytics/doctor"
PATIENT_URL = "/analytics/patient"
SYSTEM_URL = "/analytics/system"
SUMMARY_URL = "/analytics/summary"


# ------------------------------------------------------------------
#  Shared seed helpers
# ------------------------------------------------------------------

def _user(db, email, role, **kw):
    u = User(email=email, hashed_password=hash_password("p"), role=role, **kw)
    db.add(u); db.flush()
    return u


def _token(u):
    return create_access_token({"sub": str(u.id), "role": u.role.value})


def _doctor(db, user, full_name="Dr Analytics", spec="Cardiology", clinic="Heart Clinic"):
    d = Doctor(user_id=user.id, full_name=full_name, email=user.email,
               phone_number="9111111111", specialization=spec, clinic_name=clinic)
    db.add(d); db.flush()
    return d


def _patient(db, user, full_name="Pat Analytics", phone="9222222222", gender="female"):
    p = Patient(user_id=user.id, full_name=full_name, phone_number=phone, gender=gender)
    db.add(p); db.flush()
    return p


def _seed_doctor_with_data(db):
    """Create a doctor with appointments, visits, prescriptions, medical records."""
    doc_u = _user(db, "doc_analytics@test.com", UserRole.DOCTOR)
    doc = _doctor(db, doc_u, "Dr Analytics")
    pat_u = _user(db, "pat_analytics@test.com", UserRole.PATIENT)
    pat = _patient(db, pat_u, "Pat Analytics")

    visit = Visit(doctor_id=doc.id, patient_id=pat.id,
                  visit_date=datetime(2026, 1, 10),
                  diagnosis="Hypertension", symptoms="Headache",
                  status="completed")
    db.add(visit); db.flush()

    db.add(Appointment(doctor_id=doc.id, patient_id=pat.id,
                       appointment_date=date(2026, 12, 1),
                       appointment_time=time(10, 0),
                       reason="Follow-up", status=AppointmentStatus.COMPLETED))
    db.flush()

    rx = Prescription(visit_id=visit.id, doctor_id=doc.id, patient_id=pat.id,
                      diagnosis="Hypertension", notes="Take with food")
    db.add(rx); db.flush()

    db.add(PrescriptionItem(prescription_id=rx.id, medicine_name="Amlodipine",
                            strength="5mg", dosage="1 tablet",
                            frequency="Once daily", duration="30 days",
                            quantity=30))
    db.flush()

    db.add(MedicalRecord(visit_id=visit.id, doctor_id=doc.id, patient_id=pat.id,
                         chief_complaint="Headache", diagnosis="Hypertension",
                         assessment="BP elevated", height=170, weight=70))
    db.flush()

    db.commit()

    return {
        "doc_token": _token(doc_u),
        "pat_token": _token(pat_u),
        "ad_token": _token(_user(db, "ad_analytics@test.com", UserRole.ADMIN)),
        "doc_id": doc.id,
        "pat_id": pat.id,
        "pat_user_id": pat_u.id,
    }


def _seed_admin(db):
    admin_u = _user(db, "admin_analytics@test.com", UserRole.ADMIN)
    _user(db, "u1_analytics@test.com", UserRole.DOCTOR)
    _user(db, "u2_analytics@test.com", UserRole.PATIENT)
    db.commit()
    return {"admin_token": _token(admin_u)}


# ====================================================================
#  PLATFORM ANALYTICS
# ====================================================================


class TestPlatformAnalyticsAuth:
    def test_requires_auth(self, client):
        assert client.get(PLATFORM_URL).status_code == 401

    def test_doctor_cannot_access(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(PLATFORM_URL,
                          headers={"Authorization": f"Bearer {data['doc_token']}"})
        assert resp.status_code == 403

    def test_patient_cannot_access(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(PLATFORM_URL,
                          headers={"Authorization": f"Bearer {data['pat_token']}"})
        assert resp.status_code == 403

    def test_admin_can_access(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(PLATFORM_URL,
                          headers={"Authorization": f"Bearer {data['ad_token']}"})
        assert resp.status_code == 200


class TestPlatformAnalyticsCounts:
    def test_entity_counts_present(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(PLATFORM_URL,
                          headers={"Authorization": f"Bearer {data['ad_token']}"})
        body = resp.json()
        assert "entity_counts" in body
        entities = {e["entity"]: e["total"] for e in body["entity_counts"]}
        assert entities.get("users", 0) >= 3
        assert entities.get("appointments", 0) >= 1
        assert entities.get("visits", 0) >= 1
        assert entities.get("prescriptions", 0) >= 1
        assert entities.get("medical_records", 0) >= 1

    def test_activity_trends(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(PLATFORM_URL,
                          headers={"Authorization": f"Bearer {data['ad_token']}"})
        body = resp.json()
        assert isinstance(body["daily_activity"], list)
        assert isinstance(body["weekly_activity"], list)
        assert isinstance(body["monthly_activity"], list)

    def test_growth_metrics_present(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(PLATFORM_URL,
                          headers={"Authorization": f"Bearer {data['ad_token']}"})
        body = resp.json()
        assert isinstance(body["growth_metrics"], list)
        if body["growth_metrics"]:
            gm = body["growth_metrics"][0]
            assert "metric" in gm
            assert "current" in gm
            assert "growth_pct" in gm


class TestPlatformAnalyticsDateFilter:
    def test_date_filter_future_range(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(
            PLATFORM_URL,
            params={"date_from": "2099-01-01", "date_to": "2099-12-31"},
            headers={"Authorization": f"Bearer {data['ad_token']}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        entities = {e["entity"]: e["total"] for e in body["entity_counts"]}
        assert entities.get("appointments", 0) == 0

    def test_date_filter_past_range(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(
            PLATFORM_URL,
            params={"date_from": "2025-01-01", "date_to": "2025-12-31"},
            headers={"Authorization": f"Bearer {data['ad_token']}"},
        )
        assert resp.status_code == 200


# ====================================================================
#  DOCTOR ANALYTICS
# ====================================================================


class TestDoctorAnalyticsAuth:
    def test_requires_auth(self, client):
        assert client.get(DOCTOR_URL).status_code == 401

    def test_patient_cannot_access(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(DOCTOR_URL,
                          headers={"Authorization": f"Bearer {data['pat_token']}"})
        assert resp.status_code == 403

    def test_admin_cannot_access(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(DOCTOR_URL,
                          headers={"Authorization": f"Bearer {data['ad_token']}"})
        assert resp.status_code == 403

    def test_doctor_can_access(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(DOCTOR_URL,
                          headers={"Authorization": f"Bearer {data['doc_token']}"})
        assert resp.status_code == 200


class TestDoctorAnalyticsData:
    def test_kpis_present(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(DOCTOR_URL,
                          headers={"Authorization": f"Bearer {data['doc_token']}"})
        body = resp.json()
        assert body["doctor_id"] >= 1
        assert body["doctor_name"] == "Dr Analytics"
        assert isinstance(body["appointments_completed"], int)
        assert isinstance(body["upcoming_appointments"], int)
        assert isinstance(body["patients_treated"], int)
        assert isinstance(body["visits_completed"], int)
        assert isinstance(body["prescriptions_written"], int)
        assert isinstance(body["medical_records_created"], int)

    def test_averages_float(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(DOCTOR_URL,
                          headers={"Authorization": f"Bearer {data['doc_token']}"})
        body = resp.json()
        assert isinstance(body["avg_appointments_per_day"], float)
        assert isinstance(body["avg_patients_per_week"], float)

    def test_recent_activity(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(DOCTOR_URL,
                          headers={"Authorization": f"Bearer {data['doc_token']}"})
        body = resp.json()
        assert isinstance(body["recent_activity"], list)

    def test_no_profile_returns_empty(self, client, db):
        doc_u = _user(db, "doc_analytics_empty@test.com", UserRole.DOCTOR)
        tok = _token(doc_u)
        db.commit()
        resp = client.get(DOCTOR_URL,
                          headers={"Authorization": f"Bearer {tok}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["doctor_id"] == 0
        assert body["doctor_name"] == ""


# ====================================================================
#  PATIENT ANALYTICS
# ====================================================================


class TestPatientAnalyticsAuth:
    def test_requires_auth(self, client):
        assert client.get(PATIENT_URL).status_code == 401

    def test_doctor_cannot_access(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(PATIENT_URL,
                          headers={"Authorization": f"Bearer {data['doc_token']}"})
        assert resp.status_code == 403

    def test_admin_cannot_access(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(PATIENT_URL,
                          headers={"Authorization": f"Bearer {data['ad_token']}"})
        assert resp.status_code == 403

    def test_patient_can_access(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(PATIENT_URL,
                          headers={"Authorization": f"Bearer {data['pat_token']}"})
        assert resp.status_code == 200


class TestPatientAnalyticsData:
    def test_kpis_present(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(PATIENT_URL,
                          headers={"Authorization": f"Bearer {data['pat_token']}"})
        body = resp.json()
        assert body["patient_id"] >= 1
        assert body["patient_name"] == "Pat Analytics"
        assert isinstance(body["total_visits"], int)
        assert isinstance(body["total_appointments"], int)
        assert isinstance(body["completed_appointments"], int)
        assert isinstance(body["cancelled_appointments"], int)
        assert isinstance(body["total_prescriptions"], int)
        assert isinstance(body["total_medical_records"], int)
        assert isinstance(body["medication_count"], int)

    def test_timeline_summary(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(PATIENT_URL,
                          headers={"Authorization": f"Bearer {data['pat_token']}"})
        body = resp.json()
        assert isinstance(body["timeline_summary"], list)

    def test_no_profile_returns_empty(self, client, db):
        pat_u = _user(db, "pat_analytics_empty@test.com", UserRole.PATIENT)
        tok = _token(pat_u)
        db.commit()
        resp = client.get(PATIENT_URL,
                          headers={"Authorization": f"Bearer {tok}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["patient_id"] == 0
        assert body["patient_name"] == ""


# ====================================================================
#  SYSTEM ANALYTICS
# ====================================================================


class TestSystemAnalyticsAuth:
    def test_requires_auth(self, client):
        assert client.get(SYSTEM_URL).status_code == 401

    def test_doctor_cannot_access(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(SYSTEM_URL,
                          headers={"Authorization": f"Bearer {data['doc_token']}"})
        assert resp.status_code == 403

    def test_patient_cannot_access(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(SYSTEM_URL,
                          headers={"Authorization": f"Bearer {data['pat_token']}"})
        assert resp.status_code == 403

    def test_admin_can_access(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(SYSTEM_URL,
                          headers={"Authorization": f"Bearer {data['ad_token']}"})
        assert resp.status_code == 200


class TestSystemAnalyticsData:
    def test_most_active_doctors(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(SYSTEM_URL,
                          headers={"Authorization": f"Bearer {data['ad_token']}"})
        body = resp.json()
        assert isinstance(body["most_active_doctors"], list)

    def test_registration_trends(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(SYSTEM_URL,
                          headers={"Authorization": f"Bearer {data['ad_token']}"})
        body = resp.json()
        assert isinstance(body["daily_registrations"], list)
        assert isinstance(body["monthly_registrations"], list)

    def test_utilization_rate(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(SYSTEM_URL,
                          headers={"Authorization": f"Bearer {data['ad_token']}"})
        body = resp.json()
        assert isinstance(body["appointment_utilization"], float)

    def test_trends_present(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(SYSTEM_URL,
                          headers={"Authorization": f"Bearer {data['ad_token']}"})
        body = resp.json()
        assert isinstance(body["prescription_trends"], list)
        assert isinstance(body["visit_trends"], list)
        assert isinstance(body["notification_trends"], list)

    def test_date_filter(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(
            SYSTEM_URL,
            params={"date_from": "2099-01-01", "date_to": "2099-12-31"},
            headers={"Authorization": f"Bearer {data['ad_token']}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["daily_registrations"] == []
        assert body["monthly_registrations"] == []


# ====================================================================
#  ANALYTICS SUMMARY
# ====================================================================


class TestAnalyticsSummaryAuth:
    def test_requires_auth(self, client):
        assert client.get(SUMMARY_URL).status_code == 401

    def test_doctor_cannot_access(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(SUMMARY_URL,
                          headers={"Authorization": f"Bearer {data['doc_token']}"})
        assert resp.status_code == 403

    def test_patient_cannot_access(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(SUMMARY_URL,
                          headers={"Authorization": f"Bearer {data['pat_token']}"})
        assert resp.status_code == 403

    def test_admin_can_access(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(SUMMARY_URL,
                          headers={"Authorization": f"Bearer {data['ad_token']}"})
        assert resp.status_code == 200


class TestAnalyticsSummaryData:
    def test_summary_cards_present(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(SUMMARY_URL,
                          headers={"Authorization": f"Bearer {data['ad_token']}"})
        body = resp.json()
        assert "summary_cards" in body
        assert len(body["summary_cards"]) >= 1
        card = body["summary_cards"][0]
        assert "label" in card
        assert "value" in card

    def test_counts_are_integers(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(SUMMARY_URL,
                          headers={"Authorization": f"Bearer {data['ad_token']}"})
        body = resp.json()
        for card in body["summary_cards"]:
            assert isinstance(card["value"], int)


# ====================================================================
#  EDGE CASES
# ====================================================================


class TestAnalyticsEdgeCases:
    def test_platform_empty_db(self, client, db):
        ad_u = _user(db, "ad_empty@test.com", UserRole.ADMIN)
        ad_tok = _token(ad_u)
        db.commit()
        resp = client.get(PLATFORM_URL,
                          headers={"Authorization": f"Bearer {ad_tok}"})
        assert resp.status_code == 200
        body = resp.json()
        for e in body["entity_counts"]:
            assert e["total"] >= 0

    def test_doctor_empty_db(self, client, db):
        doc_u = _user(db, "doc_ana_empty@test.com", UserRole.DOCTOR)
        _doctor(db, doc_u, "Dr Empty")
        tok = _token(doc_u)
        db.commit()
        resp = client.get(DOCTOR_URL,
                          headers={"Authorization": f"Bearer {tok}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["appointments_completed"] == 0
        assert body["visits_completed"] == 0
        assert body["prescriptions_written"] == 0

    def test_patient_empty_db(self, client, db):
        pat_u = _user(db, "pat_ana_empty@test.com", UserRole.PATIENT)
        _patient(db, pat_u, "Pat Empty")
        tok = _token(pat_u)
        db.commit()
        resp = client.get(PATIENT_URL,
                          headers={"Authorization": f"Bearer {tok}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_visits"] == 0
        assert body["total_appointments"] == 0
        assert body["total_prescriptions"] == 0

    def test_system_with_no_data(self, client, db):
        ad_u = _user(db, "ad_sys_empty@test.com", UserRole.ADMIN)
        ad_tok = _token(ad_u)
        db.commit()
        resp = client.get(SYSTEM_URL,
                          headers={"Authorization": f"Bearer {ad_tok}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["appointment_utilization"] == 0.0
        assert body["most_active_doctors"] == []

    def test_summary_empty_db(self, client, db):
        ad_u = _user(db, "ad_sum_empty@test.com", UserRole.ADMIN)
        ad_tok = _token(ad_u)
        db.commit()
        resp = client.get(SUMMARY_URL,
                          headers={"Authorization": f"Bearer {ad_tok}"})
        assert resp.status_code == 200
        body = resp.json()
        cards = body["summary_cards"]
        card_map = {c["label"]: c["value"] for c in cards}
        assert card_map.get("Total Users", 0) == 1
        assert card_map.get("Doctors", 0) == 0
        assert card_map.get("Patients", 0) == 0

    def test_invalid_date_format(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(
            PLATFORM_URL,
            params={"date_from": "invalid-date"},
            headers={"Authorization": f"Bearer {data['ad_token']}"},
        )
        assert resp.status_code == 422


# ====================================================================
#  RESPONSE SHAPE
# ====================================================================


class TestAnalyticsResponseShape:
    def test_platform_response_fields(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(PLATFORM_URL,
                          headers={"Authorization": f"Bearer {data['ad_token']}"})
        body = resp.json()
        required = ["entity_counts", "daily_activity", "weekly_activity",
                     "monthly_activity", "growth_metrics"]
        for field in required:
            assert field in body, f"Missing field: {field}"

    def test_doctor_response_fields(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(DOCTOR_URL,
                          headers={"Authorization": f"Bearer {data['doc_token']}"})
        body = resp.json()
        required = ["doctor_id", "doctor_name", "specialization",
                     "appointments_completed", "upcoming_appointments",
                     "patients_treated", "visits_completed",
                     "prescriptions_written", "medical_records_created",
                     "avg_appointments_per_day", "avg_patients_per_week",
                     "recent_activity"]
        for field in required:
            assert field in body, f"Missing field: {field}"

    def test_patient_response_fields(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(PATIENT_URL,
                          headers={"Authorization": f"Bearer {data['pat_token']}"})
        body = resp.json()
        required = ["patient_id", "patient_name", "total_visits",
                     "total_appointments", "completed_appointments",
                     "cancelled_appointments", "total_prescriptions",
                     "total_medical_records", "medication_count",
                     "timeline_summary"]
        for field in required:
            assert field in body, f"Missing field: {field}"

    def test_system_response_fields(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(SYSTEM_URL,
                          headers={"Authorization": f"Bearer {data['ad_token']}"})
        body = resp.json()
        required = ["most_active_doctors", "daily_registrations",
                     "monthly_registrations", "appointment_utilization",
                     "prescription_trends", "visit_trends",
                     "notification_trends"]
        for field in required:
            assert field in body, f"Missing field: {field}"

    def test_summary_response_fields(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(SUMMARY_URL,
                          headers={"Authorization": f"Bearer {data['ad_token']}"})
        body = resp.json()
        assert "summary_cards" in body
