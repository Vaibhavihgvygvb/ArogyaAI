"""Tests for the enterprise dashboard aggregation layer."""

from datetime import date, time, datetime

from app.core.security import hash_password, create_access_token
from app.models.enums import UserRole, AppointmentStatus, NotificationType, NotificationPriority, NotificationStatus
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

DASH_DOCTOR_URL = "/dashboard/doctor"
DASH_PATIENT_URL = "/dashboard/patient"
DASH_ADMIN_URL = "/dashboard/admin"


# ------------------------------------------------------------------
#  Shared seed helpers
# ------------------------------------------------------------------

def _user(db, email, role, **kw):
    u = User(email=email, hashed_password=hash_password("p"), role=role, **kw)
    db.add(u); db.flush()
    return u


def _token(u):
    return create_access_token({"sub": str(u.id), "role": u.role.value})


def _doctor(db, user, full_name="Dr Test", spec="Cardiology", clinic="Heart Clinic"):
    d = Doctor(user_id=user.id, full_name=full_name, email=user.email,
               phone_number="9111111111", specialization=spec, clinic_name=clinic)
    db.add(d); db.flush()
    return d


def _patient(db, user, full_name="Pat Test", phone="9222222222", gender="female"):
    p = Patient(user_id=user.id, full_name=full_name, phone_number=phone, gender=gender)
    db.add(p); db.flush()
    return p


def _seed_doctor_with_data(db):
    """Create a doctor with appointments, visits, prescriptions, notifications."""
    doc_u = _user(db, "doc_dash@test.com", UserRole.DOCTOR)
    doc = _doctor(db, doc_u, "Dr Dashboard")
    pat_u = _user(db, "pat_dash@test.com", UserRole.PATIENT)
    pat = _patient(db, pat_u, "Pat Dashboard")

    visit = Visit(doctor_id=doc.id, patient_id=pat.id,
                  visit_date=datetime(2025, 1, 10),
                  diagnosis="Hypertension", symptoms="Headache",
                  status="completed")
    db.add(visit)
    db.flush()

    db.add(Appointment(doctor_id=doc.id, patient_id=pat.id,
                       appointment_date=date(2026, 12, 1),
                       appointment_time=time(10, 0),
                       reason="Follow-up", status=AppointmentStatus.SCHEDULED))
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

    db.add(Notification(user_id=doc_u.id, title="New patient", message="Anna assigned",
                        notification_type=NotificationType.INFO,
                        priority=NotificationPriority.MEDIUM,
                        status=NotificationStatus.UNREAD, is_read=False))
    db.flush()

    db.commit()

    return {
        "doc_token": _token(doc_u),
        "pat_token": _token(pat_u),
        "doc_id": doc.id,
        "pat_id": pat.id,
        "doc_user_id": doc_u.id,
        "pat_user_id": pat_u.id,
    }


def _seed_admin(db):
    """Create an admin user and some platform data."""
    admin_u = _user(db, "admin_dash@test.com", UserRole.ADMIN)
    _user(db, "u1@test.com", UserRole.DOCTOR)
    _user(db, "u2@test.com", UserRole.PATIENT)
    db.commit()
    return {"admin_token": _token(admin_u)}


# ====================================================================
#  DOCTOR DASHBOARD
# ====================================================================


class TestDoctorDashboardAuth:
    def test_requires_auth(self, client):
        assert client.get(DASH_DOCTOR_URL).status_code == 401

    def test_patient_cannot_access(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(DASH_DOCTOR_URL,
                          headers={"Authorization": f"Bearer {data['pat_token']}"})
        assert resp.status_code == 403

    def test_admin_cannot_access(self, client, db):
        data = _seed_admin(db)
        resp = client.get(DASH_DOCTOR_URL,
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 403

    def test_doctor_can_access(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(DASH_DOCTOR_URL,
                          headers={"Authorization": f"Bearer {data['doc_token']}"})
        assert resp.status_code == 200


class TestDoctorDashboardProfile:
    def test_profile_present(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(DASH_DOCTOR_URL,
                          headers={"Authorization": f"Bearer {data['doc_token']}"})
        body = resp.json()
        assert body["profile"] is not None
        assert body["profile"]["full_name"] == "Dr Dashboard"
        assert body["profile"]["specialization"] == "Cardiology"

    def test_no_profile_returns_empty(self, client, db):
        doc_u = _user(db, "doc_noprofile@test.com", UserRole.DOCTOR)
        tok = _token(doc_u)
        db.commit()
        resp = client.get(DASH_DOCTOR_URL,
                          headers={"Authorization": f"Bearer {tok}"})
        body = resp.json()
        assert body["profile"] is None
        assert body["summary_cards"] == []


class TestDoctorDashboardAppointments:
    def test_todays_appointments(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(DASH_DOCTOR_URL,
                          headers={"Authorization": f"Bearer {data['doc_token']}"})
        body = resp.json()
        assert isinstance(body["todays_appointments"], list)

    def test_upcoming_appointments(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(DASH_DOCTOR_URL,
                          headers={"Authorization": f"Bearer {data['doc_token']}"})
        body = resp.json()

    def test_appointment_counters(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(DASH_DOCTOR_URL,
                          headers={"Authorization": f"Bearer {data['doc_token']}"})
        body = resp.json()
        assert isinstance(body["completed_appointments"], int)
        assert isinstance(body["pending_appointments"], int)


class TestDoctorDashboardStats:
    def test_total_patients(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(DASH_DOCTOR_URL,
                          headers={"Authorization": f"Bearer {data['doc_token']}"})
        body = resp.json()
        assert body["total_patients"] >= 1

    def test_recent_visits(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(DASH_DOCTOR_URL,
                          headers={"Authorization": f"Bearer {data['doc_token']}"})
        body = resp.json()
        assert isinstance(body["recent_visits"], list)
        if body["recent_visits"]:
            v = body["recent_visits"][0]
            assert "id" in v and "patient_name" in v and "diagnosis" in v

    def test_recent_prescriptions(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(DASH_DOCTOR_URL,
                          headers={"Authorization": f"Bearer {data['doc_token']}"})
        body = resp.json()
        assert isinstance(body["recent_prescriptions"], list)

    def test_notifications(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(DASH_DOCTOR_URL,
                          headers={"Authorization": f"Bearer {data['doc_token']}"})
        body = resp.json()
        assert isinstance(body["notifications"], list)

    def test_medical_record_stats(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(DASH_DOCTOR_URL,
                          headers={"Authorization": f"Bearer {data['doc_token']}"})
        body = resp.json()
        mr_stats = body["medical_record_stats"]
        assert isinstance(mr_stats, dict)
        assert "total_records" in mr_stats

    def test_summary_cards(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(DASH_DOCTOR_URL,
                          headers={"Authorization": f"Bearer {data['doc_token']}"})
        body = resp.json()
        cards = body["summary_cards"]
        assert len(cards) >= 1
        card = cards[0]
        assert "label" in card and "value" in card


# ====================================================================
#  PATIENT DASHBOARD
# ====================================================================


class TestPatientDashboardAuth:
    def test_requires_auth(self, client):
        assert client.get(DASH_PATIENT_URL).status_code == 401

    def test_doctor_cannot_access(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(DASH_PATIENT_URL,
                          headers={"Authorization": f"Bearer {data['doc_token']}"})
        assert resp.status_code == 403

    def test_admin_cannot_access(self, client, db):
        data = _seed_admin(db)
        resp = client.get(DASH_PATIENT_URL,
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 403

    def test_patient_can_access(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(DASH_PATIENT_URL,
                          headers={"Authorization": f"Bearer {data['pat_token']}"})
        assert resp.status_code == 200


class TestPatientDashboardProfile:
    def test_profile_present(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(DASH_PATIENT_URL,
                          headers={"Authorization": f"Bearer {data['pat_token']}"})
        body = resp.json()
        assert body["profile"] is not None
        assert body["profile"]["full_name"] == "Pat Dashboard"

    def test_no_profile_returns_empty(self, client, db):
        pat_u = _user(db, "pat_noprofile@test.com", UserRole.PATIENT)
        tok = _token(pat_u)
        db.commit()
        resp = client.get(DASH_PATIENT_URL,
                          headers={"Authorization": f"Bearer {tok}"})
        body = resp.json()
        assert body["profile"] is None
        assert body["health_summary_cards"] == []


class TestPatientDashboardData:
    def test_upcoming_appointments(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(DASH_PATIENT_URL,
                          headers={"Authorization": f"Bearer {data['pat_token']}"})
        body = resp.json()
        assert isinstance(body["upcoming_appointments"], list)

    def test_medical_history_summary(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(DASH_PATIENT_URL,
                          headers={"Authorization": f"Bearer {data['pat_token']}"})
        body = resp.json()
        mhs = body["medical_history_summary"]
        assert "total_visits" in mhs
        assert "total_prescriptions" in mhs
        assert "total_medical_records" in mhs

    def test_prescriptions_list(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(DASH_PATIENT_URL,
                          headers={"Authorization": f"Bearer {data['pat_token']}"})
        body = resp.json()
        assert isinstance(body["prescriptions"], list)

    def test_active_medications(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(DASH_PATIENT_URL,
                          headers={"Authorization": f"Bearer {data['pat_token']}"})
        body = resp.json()
        assert isinstance(body["active_medications"], list)
        if body["active_medications"]:
            med = body["active_medications"][0]
            assert "medicine_name" in med

    def test_recent_visits(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(DASH_PATIENT_URL,
                          headers={"Authorization": f"Bearer {data['pat_token']}"})
        body = resp.json()
        assert isinstance(body["recent_visits"], list)

    def test_notifications(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(DASH_PATIENT_URL,
                          headers={"Authorization": f"Bearer {data['pat_token']}"})
        body = resp.json()
        assert isinstance(body["notifications"], list)

    def test_timeline_preview(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(DASH_PATIENT_URL,
                          headers={"Authorization": f"Bearer {data['pat_token']}"})
        body = resp.json()
        assert isinstance(body["timeline_preview"], list)
        if body["timeline_preview"]:
            ev = body["timeline_preview"][0]
            assert "type" in ev and "title" in ev

    def test_health_summary_cards(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(DASH_PATIENT_URL,
                          headers={"Authorization": f"Bearer {data['pat_token']}"})
        body = resp.json()
        cards = body["health_summary_cards"]
        assert len(cards) >= 1
        assert cards[0].get("label") and "value" in cards[0]


# ====================================================================
#  ADMIN DASHBOARD
# ====================================================================


class TestAdminDashboardAuth:
    def test_requires_auth(self, client):
        assert client.get(DASH_ADMIN_URL).status_code == 401

    def test_doctor_cannot_access(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(DASH_ADMIN_URL,
                          headers={"Authorization": f"Bearer {data['doc_token']}"})
        assert resp.status_code == 403

    def test_patient_cannot_access(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(DASH_ADMIN_URL,
                          headers={"Authorization": f"Bearer {data['pat_token']}"})
        assert resp.status_code == 403

    def test_admin_can_access(self, client, db):
        data = _seed_admin(db)
        resp = client.get(DASH_ADMIN_URL,
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 200


class TestAdminDashboardCounts:
    def test_entity_counts_present(self, client, db):
        data = _seed_admin(db)
        resp = client.get(DASH_ADMIN_URL,
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        body = resp.json()
        assert body["total_users"] >= 3
        assert body["total_doctors"] >= 0
        assert body["total_patients"] >= 0
        assert isinstance(body["total_appointments"], int)
        assert isinstance(body["total_visits"], int)
        assert isinstance(body["total_prescriptions"], int)
        assert isinstance(body["total_medical_records"], int)
        assert isinstance(body["total_medicines"], int)
        assert isinstance(body["total_notifications"], int)
        assert isinstance(body["total_audit_logs"], int)

    def test_system_stats(self, client, db):
        data = _seed_admin(db)
        resp = client.get(DASH_ADMIN_URL,
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        body = resp.json()
        ss = body["system_stats"]
        assert "doctor_to_patient_ratio" in ss
        assert "appointment_completion_rate" in ss
        assert "visit_with_diagnosis_pct" in ss

    def test_growth_metrics(self, client, db):
        data = _seed_admin(db)
        resp = client.get(DASH_ADMIN_URL,
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        body = resp.json()
        gm = body["growth_metrics"]
        assert "total_users" in gm
        assert "total_doctors" in gm
        assert "total_patients" in gm


class TestAdminDashboardRecent:
    def test_recent_registrations(self, client, db):
        data = _seed_admin(db)
        resp = client.get(DASH_ADMIN_URL,
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        body = resp.json()
        assert isinstance(body["recent_registrations"], list)
        if body["recent_registrations"]:
            r = body["recent_registrations"][0]
            assert "email" in r and "role" in r

    def test_recent_appointments(self, client, db):
        data = _seed_admin(db)
        resp = client.get(DASH_ADMIN_URL,
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        body = resp.json()
        assert isinstance(body["recent_appointments"], list)

    def test_recent_prescriptions(self, client, db):
        data = _seed_admin(db)
        resp = client.get(DASH_ADMIN_URL,
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        body = resp.json()
        assert isinstance(body["recent_prescriptions"], list)

    def test_platform_activity(self, client, db):
        data = _seed_admin(db)
        resp = client.get(DASH_ADMIN_URL,
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        body = resp.json()
        assert isinstance(body["platform_activity"], list)
        if body["platform_activity"]:
            pa = body["platform_activity"][0]
            assert "period" in pa and "label" in pa and "value" in pa

    def test_summary_cards(self, client, db):
        data = _seed_admin(db)
        resp = client.get(DASH_ADMIN_URL,
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        body = resp.json()
        cards = body["summary_cards"]
        assert len(cards) >= 1
        assert cards[0].get("label") and "value" in cards[0]


# ====================================================================
#  EDGE CASES
# ====================================================================


class TestDashboardEdgeCases:
    def test_doctor_dashboard_with_empty_data(self, client, db):
        doc_u = _user(db, "doc_empty@test.com", UserRole.DOCTOR)
        _doctor(db, doc_u, "Dr Empty")
        tok = _token(doc_u)
        db.commit()
        resp = client.get(DASH_DOCTOR_URL,
                          headers={"Authorization": f"Bearer {tok}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_patients"] == 0
        assert body["todays_appointments"] == []
        assert body["upcoming_appointments"] == []
        assert body["recent_visits"] == []
        assert body["recent_prescriptions"] == []

    def test_patient_dashboard_with_empty_data(self, client, db):
        pat_u = _user(db, "pat_empty@test.com", UserRole.PATIENT)
        _patient(db, pat_u, "Pat Empty")
        tok = _token(pat_u)
        db.commit()
        resp = client.get(DASH_PATIENT_URL,
                          headers={"Authorization": f"Bearer {tok}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["upcoming_appointments"] == []
        assert body["prescriptions"] == []
        assert body["active_medications"] == []
        assert body["recent_visits"] == []
        assert body["timeline_preview"] == []

    def test_admin_dashboard_with_minimal_data(self, client, db):
        admin_u = _user(db, "admin_min@test.com", UserRole.ADMIN)
        tok = _token(admin_u)
        db.commit()
        resp = client.get(DASH_ADMIN_URL,
                          headers={"Authorization": f"Bearer {tok}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_users"] == 1
        assert body["total_doctors"] == 0
        assert body["total_patients"] == 0

    def test_wrong_role_doctor(self, client, db):
        admin_u = _user(db, "admin_wrong@test.com", UserRole.ADMIN)
        tok = _token(admin_u)
        db.commit()
        resp = client.get(DASH_DOCTOR_URL,
                          headers={"Authorization": f"Bearer {tok}"})
        assert resp.status_code == 403

    def test_wrong_role_patient(self, client, db):
        doc_u = _user(db, "doc_wrong@test.com", UserRole.DOCTOR)
        tok = _token(doc_u)
        db.commit()
        resp = client.get(DASH_PATIENT_URL,
                          headers={"Authorization": f"Bearer {tok}"})
        assert resp.status_code == 403

    def test_wrong_role_admin(self, client, db):
        pat_u = _user(db, "pat_wrong@test.com", UserRole.PATIENT)
        tok = _token(pat_u)
        db.commit()
        resp = client.get(DASH_ADMIN_URL,
                          headers={"Authorization": f"Bearer {tok}"})
        assert resp.status_code == 403


# ====================================================================
#  RESPONSE SHAPE
# ====================================================================


class TestDashboardResponseShape:
    def test_doctor_response_fields(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(DASH_DOCTOR_URL,
                          headers={"Authorization": f"Bearer {data['doc_token']}"})
        body = resp.json()
        required = [
            "profile", "todays_appointments", "upcoming_appointments",
            "completed_appointments", "pending_appointments", "total_patients",
            "recent_visits", "recent_prescriptions", "notifications",
            "medical_record_stats", "summary_cards",
        ]
        for field in required:
            assert field in body, f"Missing field: {field}"

    def test_patient_response_fields(self, client, db):
        data = _seed_doctor_with_data(db)
        resp = client.get(DASH_PATIENT_URL,
                          headers={"Authorization": f"Bearer {data['pat_token']}"})
        body = resp.json()
        required = [
            "profile", "upcoming_appointments", "medical_history_summary",
            "prescriptions", "active_medications", "recent_visits",
            "notifications", "timeline_preview", "health_summary_cards",
        ]
        for field in required:
            assert field in body, f"Missing field: {field}"

    def test_admin_response_fields(self, client, db):
        data = _seed_admin(db)
        resp = client.get(DASH_ADMIN_URL,
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        body = resp.json()
        required = [
            "total_users", "total_doctors", "total_patients",
            "total_appointments", "total_visits", "total_prescriptions",
            "total_medical_records", "total_medicines",
            "total_notifications", "total_audit_logs",
            "system_stats", "platform_activity", "growth_metrics",
            "recent_registrations", "recent_appointments",
            "recent_prescriptions", "summary_cards",
        ]
        for field in required:
            assert field in body, f"Missing field: {field}"
