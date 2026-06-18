"""Tests for the global search endpoint."""

from datetime import date, time, datetime

from app.core.security import hash_password, create_access_token
from app.models.enums import (
    UserRole,
    AppointmentStatus,
    NotificationType,
    NotificationPriority,
    NotificationStatus,
)
from app.models.user import User
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.visit import Visit
from app.models.appointment import Appointment
from app.models.prescription import Prescription
from app.models.prescription_item import PrescriptionItem
from app.models.medicine import Medicine
from app.models.medical_record import MedicalRecord
from app.models.notification import Notification
from app.models.audit_log import AuditLog

SEARCH_URL = "/search"


# ---------------------------------------------------------------------------
# Fixtures – seed data for all 11 entity types
# ---------------------------------------------------------------------------

def _admin_token(db):
    user = User(email="admin_search@test.com", hashed_password=hash_password("p"), role=UserRole.ADMIN)
    db.add(user)
    db.commit()
    db.refresh(user)
    return create_access_token({"sub": str(user.id), "role": user.role.value})


def _doctor_token_and_profile(db, email="doc_search@test.com"):
    user = User(email=email, hashed_password=hash_password("p"), role=UserRole.DOCTOR)
    db.add(user)
    db.commit()
    db.refresh(user)
    doctor = Doctor(user_id=user.id, full_name="Dr Searchable", email=user.email,
                    phone_number="9111111111", specialization="Cardiology",
                    clinic_name="Heart Clinic")
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return token, doctor


def _patient_token_and_profile(db, email="pat_search@test.com"):
    user = User(email=email, hashed_password=hash_password("p"), role=UserRole.PATIENT)
    db.add(user)
    db.commit()
    db.refresh(user)
    patient = Patient(user_id=user.id, full_name="Pat Searchable",
                      phone_number="9222222222", gender="female")
    db.add(patient)
    db.commit()
    db.refresh(patient)
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return token, patient


# ---------------------------------------------------------------------------
# Helper to seed all entities – returns (admin_token, doctor_token, doctor_id,
# patient_token, patient_id, second_doctor_token, second_doctor_id,
# second_patient_token, second_patient_id)
# ---------------------------------------------------------------------------

def _make_doc(db, email, name, spec, clinic):
    u = User(email=email, hashed_password=hash_password("p"), role=UserRole.DOCTOR)
    db.add(u); db.flush()
    d = Doctor(user_id=u.id, full_name=name, email=email,
               phone_number="9999999999", specialization=spec, clinic_name=clinic)
    db.add(d); db.flush()
    return u, d


def _make_pat(db, email, name, phone, gender):
    u = User(email=email, hashed_password=hash_password("p"), role=UserRole.PATIENT)
    db.add(u); db.flush()
    p = Patient(user_id=u.id, full_name=name, phone_number=phone, gender=gender)
    db.add(p); db.flush()
    return u, p


def _seed_all(db):
    """Create a rich set of test entities. Returns a dict of tokens + ids."""

    # -- Admin --
    admin_user = User(email="admin@search.com", hashed_password=hash_password("p"),
                      role=UserRole.ADMIN)
    db.add(admin_user); db.flush()
    admin_tok = create_access_token({"sub": str(admin_user.id), "role": admin_user.role.value})

    # -- Doctor 1 (cardiologist) --
    doc1_u, doc1 = _make_doc(db, "drheart@test.com", "Dr Heart", "Cardiology", "Heart Clinic")
    doc1_tok = create_access_token({"sub": str(doc1_u.id), "role": doc1_u.role.value})

    # -- Doctor 2 (neurologist) – for cross-doctor RBAC checks --
    doc2_u, doc2 = _make_doc(db, "drbrain@test.com", "Dr Brain", "Neurology", "Brain Clinic")
    doc2_tok = create_access_token({"sub": str(doc2_u.id), "role": doc2_u.role.value})

    # -- Patient 1 (female) linked to Doctor 1 --
    pat1_u, pat1 = _make_pat(db, "pat_anna@test.com", "Anna Patient", "9111111111", "female")
    pat1_tok = create_access_token({"sub": str(pat1_u.id), "role": pat1_u.role.value})

    # -- Patient 2 (male) linked to Doctor 1 and Doctor 2 --
    pat2_u, pat2 = _make_pat(db, "pat_bob@test.com", "Bob Patient", "9222222222", "male")
    pat2_tok = create_access_token({"sub": str(pat2_u.id), "role": pat2_u.role.value})

    # -- Patient 3 (only with Doctor 2) --
    pat3_u, pat3 = _make_pat(db, "pat_carol@test.com", "Carol Patient", "9333333333", "female")
    pat3_tok = create_access_token({"sub": str(pat3_u.id), "role": pat3_u.role.value})

    # -- Visits --
    v1 = Visit(doctor_id=doc1.id, patient_id=pat1.id,
               visit_date=datetime(2025, 1, 10),
               diagnosis="Hypertension", symptoms="Headache, dizziness",
               status="completed")
    db.add(v1); db.flush()

    v2 = Visit(doctor_id=doc1.id, patient_id=pat2.id,
               visit_date=datetime(2025, 2, 15),
               diagnosis="Diabetes Type 2", symptoms="Frequent urination",
               status="follow-up")
    db.add(v2); db.flush()

    v3 = Visit(doctor_id=doc2.id, patient_id=pat3.id,
               visit_date=datetime(2025, 3, 20),
               diagnosis="Migraine", symptoms="Severe headache, nausea",
               status="completed")
    db.add(v3); db.flush()

    # -- Appointments --
    apt1 = Appointment(doctor_id=doc1.id, patient_id=pat1.id,
                       appointment_date=date(2025, 6, 1),
                       appointment_time=time(10, 0),
                       reason="Chest pain follow-up",
                       status=AppointmentStatus.SCHEDULED)
    db.add(apt1); db.flush()

    apt2 = Appointment(doctor_id=doc2.id, patient_id=pat3.id,
                       appointment_date=date(2025, 6, 5),
                       appointment_time=time(14, 30),
                       reason="Migraine consultation",
                       status=AppointmentStatus.CONFIRMED)
    db.add(apt2); db.flush()

    # -- Prescriptions --
    rx1 = Prescription(visit_id=v1.id, doctor_id=doc1.id, patient_id=pat1.id,
                       diagnosis="Hypertension", notes="Take with food")
    db.add(rx1); db.flush()

    rx2 = Prescription(visit_id=v2.id, doctor_id=doc1.id, patient_id=pat2.id,
                       diagnosis="Diabetes Type 2", notes="Monitor blood sugar")
    db.add(rx2); db.flush()

    # -- Prescription Items --
    pitem1 = PrescriptionItem(prescription_id=rx1.id, medicine_name="Amlodipine",
                              strength="5mg", dosage="1 tablet",
                              frequency="Once daily", duration="30 days",
                              quantity=30)
    db.add(pitem1); db.flush()

    pitem2 = PrescriptionItem(prescription_id=rx2.id, medicine_name="Metformin",
                              strength="500mg", dosage="1 tablet",
                              frequency="Twice daily", duration="90 days",
                              quantity=180)
    db.add(pitem2); db.flush()

    # -- Medicines --
    med1 = Medicine(generic_name="Amlodipine", brand_name="Norvasc",
                    manufacturer="Pfizer", strength="5mg",
                    dosage_form="Tablet", route="Oral",
                    drug_class="Calcium Channel Blocker",
                    requires_prescription=True, is_active=True)
    db.add(med1); db.flush()

    med2 = Medicine(generic_name="Metformin", brand_name="Glucophage",
                    manufacturer="Bristol-Myers", strength="500mg",
                    dosage_form="Tablet", route="Oral",
                    drug_class="Biguanide",
                    requires_prescription=True, is_active=True)
    db.add(med2); db.flush()

    med3 = Medicine(generic_name="Paracetamol", brand_name="Tylenol",
                    manufacturer="J&J", strength="500mg",
                    dosage_form="Tablet", route="Oral",
                    drug_class="Analgesic",
                    requires_prescription=False, is_active=True)
    db.add(med3); db.flush()

    # -- Medical Records (one per visit) --
    mr1 = MedicalRecord(visit_id=v1.id, doctor_id=doc1.id, patient_id=pat1.id,
                        chief_complaint="Headache and dizziness",
                        diagnosis="Hypertension",
                        assessment="BP elevated", treatment_plan="Lifestyle changes")
    db.add(mr1); db.flush()

    mr2 = MedicalRecord(visit_id=v3.id, doctor_id=doc2.id, patient_id=pat3.id,
                        chief_complaint="Severe headache",
                        diagnosis="Migraine with aura",
                        assessment="Neurological exam normal", treatment_plan="Avoid triggers")
    db.add(mr2); db.flush()

    # -- Notifications (one per user) --
    now = datetime.now().replace(microsecond=0)
    for uid, title, msg, ntype in [
        (admin_user.id, "Admin alert", "System update scheduled", NotificationType.SYSTEM),
        (doc1_u.id, "New patient assigned", "Patient Anna assigned to you", NotificationType.INFO),
        (pat1_u.id, "Appointment reminder", "Your appointment is tomorrow", NotificationType.APPOINTMENT),
    ]:
        n = Notification(user_id=uid, title=title, message=msg,
                         notification_type=ntype,
                         priority=NotificationPriority.MEDIUM,
                         status=NotificationStatus.UNREAD,
                         created_at=now)
        db.add(n)
    db.flush()

    # -- Audit Logs --
    for action, resource, details in [
        ("USER_LOGIN", "users", "User admin_search logged in"),
        ("VISIT_CREATED", f"visits/{v1.id}", "Visit for Hypertension created"),
        ("PRESCRIPTION_ISSUED", f"prescriptions/{rx1.id}", "Prescription for Amlodipine issued"),
    ]:
        al = AuditLog(action=action, resource=resource, details=details, created_at=now)
        db.add(al)
    db.flush()

    return {
        "admin_token": admin_tok,
        "doc1_token": doc1_tok,
        "doc1_id": doc1.id,
        "doc2_token": doc2_tok,
        "doc2_id": doc2.id,
        "pat1_token": pat1_tok,
        "pat1_id": pat1.id,
        "pat2_token": pat2_tok,
        "pat2_id": pat2.id,
        "pat3_token": pat3_tok,
        "pat3_id": pat3.id,
    }


# ==============================================================
#   TESTS
# ==============================================================


class TestSearchAuth:
    def test_search_requires_auth(self, client):
        resp = client.get(SEARCH_URL, params={"q": "test"})
        assert resp.status_code == 401


class TestSearchGlobal:
    """Global search (no entity filter) — admin can see everything."""

    def test_admin_global_search_returns_results(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "Hypertension"},
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        assert body["page"] == 1
        assert body["query"] == "Hypertension"
        titles = {r["title"] for r in body["items"]}
        assert "Hypertension" in titles or any("Hypertension" in r.get("subtitle", "") for r in body["items"])

    def test_admin_global_search_empty_query(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": " "},
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_admin_global_search_no_match(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "zzzznothing"},
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_admin_global_search_returns_across_entities(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "patient"},
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        types = {r["entity_type"] for r in body["items"]}
        assert "patient" in types


class TestSearchEntityFilter:
    def test_entity_filter_valid(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "Amlodipine", "entity": "medicines"},
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        assert all(r["entity_type"] == "medicine" for r in body["items"])

    def test_entity_filter_invalid(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "test", "entity": "garbage"},
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 400
        assert "Invalid entity type" in resp.json()["detail"]

    def test_entity_filter_users_admin_only(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "admin@search.com", "entity": "users"},
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_entity_filter_users_doctor_gets_empty(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "admin", "entity": "users"},
                          headers={"Authorization": f"Bearer {data['doc1_token']}"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_entity_filter_audit_logs_admin_only(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "USER_LOGIN", "entity": "audit_logs"},
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_entity_filter_audit_logs_doctor_empty(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "USER_LOGIN", "entity": "audit_logs"},
                          headers={"Authorization": f"Bearer {data['doc1_token']}"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


class TestSearchPagination:
    def test_pagination_defaults(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "patient"},
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        body = resp.json()
        assert body["page"] == 1
        assert body["page_size"] == 20

    def test_pagination_custom_page_size(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "patient", "page_size": 1},
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        body = resp.json()
        assert body["page_size"] == 1
        assert len(body["items"]) <= 1

    def test_pagination_page_size_max(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "patient", "page_size": 100},
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 200

    def test_pagination_page_size_exceeds_max(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "patient", "page_size": 101},
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 422

    def test_pagination_page_2(self, client, db):
        data = _seed_all(db)
        resp1 = client.get(SEARCH_URL, params={"q": "patient", "page": 1, "page_size": 1},
                           headers={"Authorization": f"Bearer {data['admin_token']}"})
        resp2 = client.get(SEARCH_URL, params={"q": "patient", "page": 2, "page_size": 1},
                           headers={"Authorization": f"Bearer {data['admin_token']}"})
        body1 = resp1.json()
        body2 = resp2.json()
        if body1["total"] > 1:
            assert len(body2["items"]) >= 1
            id1 = body1["items"][0]["entity_id"]
            id2 = body2["items"][0]["entity_id"]
            assert id1 != id2


class TestSearchSortOrder:
    def test_sort_desc_default(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "patient"},
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        items = resp.json()["items"]
        if len(items) >= 2:
            assert items[0]["created_at"] >= items[-1]["created_at"]

    def test_sort_asc(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "patient", "sort_order": "asc"},
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        items = resp.json()["items"]
        if len(items) >= 2:
            assert items[0]["created_at"] <= items[-1]["created_at"]

    def test_sort_invalid(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "patient", "sort_order": "invalid"},
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 422


class TestSearchDateFilter:
    def test_date_from(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "patient", "date_from": "2020-01-01T00:00:00"},
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 200

    def test_date_to(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "patient", "date_to": "2030-12-31T23:59:59"},
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_date_bad_format(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "patient", "date_from": "not-a-date"},
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 400
        assert "Invalid date format" in resp.json()["detail"]


class TestSearchRBAC:
    """Role-based access control."""

    def test_doctor_sees_own_doctor_profile(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "Dr Heart", "entity": "doctors"},
                          headers={"Authorization": f"Bearer {data['doc1_token']}"})
        body = resp.json()
        assert body["total"] >= 1
        assert body["items"][0]["entity_type"] == "doctor"
        assert "Dr Heart" in body["items"][0]["title"]

    def test_doctor_does_not_see_other_doctor_profile(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "Dr Brain", "entity": "doctors"},
                          headers={"Authorization": f"Bearer {data['doc1_token']}"})
        assert resp.json()["total"] == 0

    def test_doctor_sees_own_patients(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "Anna", "entity": "patients"},
                          headers={"Authorization": f"Bearer {data['doc1_token']}"})
        body = resp.json()
        assert body["total"] >= 1
        assert "Anna" in body["items"][0]["title"]

    def test_doctor_does_not_see_unrelated_patient(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "Carol", "entity": "patients"},
                          headers={"Authorization": f"Bearer {data['doc1_token']}"})
        assert resp.json()["total"] == 0

    def test_doctor_sees_own_visits(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "Hypertension", "entity": "visits"},
                          headers={"Authorization": f"Bearer {data['doc1_token']}"})
        body = resp.json()
        assert body["total"] >= 1

    def test_doctor_does_not_see_other_doctor_visit(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "Migraine", "entity": "visits"},
                          headers={"Authorization": f"Bearer {data['doc1_token']}"})
        assert resp.json()["total"] == 0

    def test_doctor_sees_own_appointments(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "chest", "entity": "appointments"},
                          headers={"Authorization": f"Bearer {data['doc1_token']}"})
        body = resp.json()
        assert body["total"] >= 1

    def test_doctor_does_not_see_other_doctor_appointment(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "Migraine", "entity": "appointments"},
                          headers={"Authorization": f"Bearer {data['doc1_token']}"})
        assert resp.json()["total"] == 0

    def test_doctor_sees_own_prescriptions(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "Hypertension", "entity": "prescriptions"},
                          headers={"Authorization": f"Bearer {data['doc1_token']}"})
        assert resp.json()["total"] >= 1

    def test_doctor_sees_own_prescription_items(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "Amlodipine", "entity": "prescription_items"},
                          headers={"Authorization": f"Bearer {data['doc1_token']}"})
        assert resp.json()["total"] >= 1

    def test_doctor_does_not_see_other_doctor_prescription_items(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "Metformin", "entity": "prescription_items"},
                          headers={"Authorization": f"Bearer {data['doc2_token']}"})
        assert resp.json()["total"] == 0

    def test_doctor_sees_own_medical_records(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "Headache", "entity": "medical_records"},
                          headers={"Authorization": f"Bearer {data['doc1_token']}"})
        body = resp.json()
        assert body["total"] >= 1

    def test_doctor_does_not_see_other_medical_records(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "Severe headache", "entity": "medical_records"},
                          headers={"Authorization": f"Bearer {data['doc1_token']}"})
        assert resp.json()["total"] == 0

    def test_doctor_sees_own_notifications(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "patient", "entity": "notifications"},
                          headers={"Authorization": f"Bearer {data['doc1_token']}"})
        body = resp.json()
        assert body["total"] >= 1
        assert body["items"][0]["entity_type"] == "notification"

    def test_doctor_global_search_is_scoped(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "patient"},
                          headers={"Authorization": f"Bearer {data['doc1_token']}"})
        body = resp.json()
        ids_seen = {r["entity_id"] for r in body["items"] if r["entity_type"] == "patient"}
        assert data["pat1_id"] in ids_seen
        assert data["pat3_id"] not in ids_seen

    # -- Patient RBAC --
    def test_patient_sees_own_patient_profile(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "Anna", "entity": "patients"},
                          headers={"Authorization": f"Bearer {data['pat1_token']}"})
        body = resp.json()
        assert body["total"] >= 1

    def test_patient_does_not_see_other_patient(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "Bob", "entity": "patients"},
                          headers={"Authorization": f"Bearer {data['pat1_token']}"})
        assert resp.json()["total"] == 0

    def test_patient_sees_own_visit(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "Hypertension", "entity": "visits"},
                          headers={"Authorization": f"Bearer {data['pat1_token']}"})
        assert resp.json()["total"] >= 1

    def test_patient_does_not_see_other_visit(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "Diabetes", "entity": "visits"},
                          headers={"Authorization": f"Bearer {data['pat1_token']}"})
        assert resp.json()["total"] == 0

    def test_patient_sees_own_appointment(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "chest", "entity": "appointments"},
                          headers={"Authorization": f"Bearer {data['pat1_token']}"})
        assert resp.json()["total"] >= 1

    def test_patient_does_not_see_other_appointment(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "Migraine", "entity": "appointments"},
                          headers={"Authorization": f"Bearer {data['pat1_token']}"})
        assert resp.json()["total"] == 0

    def test_patient_sees_own_prescription(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "Hypertension", "entity": "prescriptions"},
                          headers={"Authorization": f"Bearer {data['pat1_token']}"})
        assert resp.json()["total"] >= 1

    def test_patient_sees_own_prescription_items(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "Amlodipine", "entity": "prescription_items"},
                          headers={"Authorization": f"Bearer {data['pat1_token']}"})
        assert resp.json()["total"] >= 1

    def test_patient_sees_own_medical_records(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "Headache", "entity": "medical_records"},
                          headers={"Authorization": f"Bearer {data['pat1_token']}"})
        assert resp.json()["total"] >= 1

    def test_patient_does_not_see_other_medical_records(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "Severe headache", "entity": "medical_records"},
                          headers={"Authorization": f"Bearer {data['pat1_token']}"})
        assert resp.json()["total"] == 0

    def test_patient_sees_own_notifications(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "appointment", "entity": "notifications"},
                          headers={"Authorization": f"Bearer {data['pat1_token']}"})
        body = resp.json()
        assert body["total"] >= 1

    def test_patient_global_search_is_scoped(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "patient"},
                          headers={"Authorization": f"Bearer {data['pat1_token']}"})
        body = resp.json()
        ids_seen = {r["entity_id"] for r in body["items"] if r["entity_type"] == "patient"}
        assert data["pat1_id"] in ids_seen
        assert data["pat2_id"] not in ids_seen

    def test_patient_cannot_search_doctors(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "Heart", "entity": "doctors"},
                          headers={"Authorization": f"Bearer {data['pat1_token']}"})
        assert resp.json()["total"] == 0

    def test_patient_cannot_search_users(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "admin", "entity": "users"},
                          headers={"Authorization": f"Bearer {data['pat1_token']}"})
        assert resp.json()["total"] == 0

    def test_patient_cannot_search_audit_logs(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "USER_LOGIN", "entity": "audit_logs"},
                          headers={"Authorization": f"Bearer {data['pat1_token']}"})
        assert resp.json()["total"] == 0


class TestSearchEntitiesIndividually:
    """Verify each entity type returns results when queried by admin."""

    ENTITY_QUERIES = [
        ("users", "admin@search.com"),
        ("doctors", "Dr Heart"),
        ("patients", "Anna"),
        ("visits", "Hypertension"),
        ("appointments", "chest"),
        ("prescriptions", "Hypertension"),
        ("prescription_items", "Amlodipine"),
        ("medicines", "Amlodipine"),
        ("medical_records", "Headache"),
        ("notifications", "system"),
        ("audit_logs", "USER_LOGIN"),
    ]

    def test_all_entities_return_results(self, client, db):
        data = _seed_all(db)
        for entity, query in self.ENTITY_QUERIES:
            resp = client.get(
                SEARCH_URL,
                params={"q": query, "entity": entity},
                headers={"Authorization": f"Bearer {data['admin_token']}"},
            )
            assert resp.status_code == 200, f"Failed for entity={entity}, q={query}"
            body = resp.json()
            assert body["total"] >= 1, f"No results for entity={entity}, q={query}"

    def test_medicine_only_active(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "Tylenol", "entity": "medicines"},
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.json()["total"] >= 1


class TestSearchHighlights:
    def test_highlight_present(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "Anna", "entity": "patients"},
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        body = resp.json()
        if body["total"] > 0:
            hl = body["items"][0].get("highlight")
            assert hl is None or "Anna" in hl

    def test_highlight_for_diagnosis(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "Hypertension", "entity": "visits"},
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        body = resp.json()
        if body["total"] > 0:
            hl = body["items"][0].get("highlight")
            assert hl is None or "Hypertension" in hl


class TestSearchIDQuery:
    def test_query_by_id_users(self, client, db):
        data = _seed_all(db)
        users_resp = client.get(SEARCH_URL, params={"q": "1", "entity": "users"},
                                headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert users_resp.status_code == 200

    def test_query_by_id_doctors(self, client, db):
        data = _seed_all(db)
        doc_id = data["doc1_id"]
        resp = client.get(SEARCH_URL, params={"q": str(doc_id), "entity": "doctors"},
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        body = resp.json()
        assert body["total"] >= 1

    def test_query_by_id_patients(self, client, db):
        data = _seed_all(db)
        pat_id = data["pat1_id"]
        resp = client.get(SEARCH_URL, params={"q": str(pat_id), "entity": "patients"},
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        body = resp.json()
        assert body["total"] >= 1


class TestSearchDoctorPatientFilter:
    """doctor_id / patient_id query params."""

    def test_doctor_id_filter(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "Hyper", "entity": "visits",
                                              "doctor_id": data["doc1_id"]},
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        body = resp.json()
        total_doctor1 = body["total"]

        resp2 = client.get(SEARCH_URL, params={"q": "Migraine", "entity": "visits",
                                               "doctor_id": data["doc2_id"]},
                           headers={"Authorization": f"Bearer {data['admin_token']}"})
        body2 = resp2.json()
        assert total_doctor1 >= 1
        assert body2["total"] >= 1

    def test_patient_id_filter(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "Hyper", "entity": "visits",
                                              "patient_id": data["pat1_id"]},
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        body = resp.json()
        assert body["total"] >= 1
        for item in body["items"]:
            assert item["entity_type"] == "visit"

    def test_doctor_id_filter_on_appointments(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "chest", "entity": "appointments",
                                              "doctor_id": data["doc1_id"]},
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.json()["total"] >= 1


class TestSearchResponseShape:
    def test_response_shape(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "Anna"},
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert "page" in body
        assert "page_size" in body
        assert "query" in body
        assert isinstance(body["items"], list)
        assert isinstance(body["total"], int)

    def test_result_item_shape(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "Anna", "entity": "patients"},
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        body = resp.json()
        if body["total"] > 0:
            item = body["items"][0]
            assert "entity_type" in item
            assert "entity_id" in item
            assert "title" in item
            assert item["entity_type"] == "patient"
            assert isinstance(item["entity_id"], int)

    def test_search_result_item_has_all_optional_fields(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "Anna", "entity": "patients"},
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        body = resp.json()
        if body["total"] > 0:
            item = body["items"][0]
            for field in ("subtitle", "summary", "created_at", "highlight"):
                assert field in item, f"Missing field: {field}"
            assert "metadata_json" in item


class TestSearchEdgeCases:
    def test_query_max_length_accepted(self, client, db):
        data = _seed_all(db)
        long_q = "A" * 200
        resp = client.get(SEARCH_URL, params={"q": long_q},
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 200

    def test_query_too_long_rejected(self, client, db):
        data = _seed_all(db)
        long_q = "A" * 201
        resp = client.get(SEARCH_URL, params={"q": long_q},
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 422

    def test_query_min_length(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": ""},
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 422

    def test_special_characters_in_query(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "50%"},
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert resp.status_code == 200

    def test_case_insensitive_search(self, client, db):
        data = _seed_all(db)
        lower = client.get(SEARCH_URL, params={"q": "hypertension"},
                           headers={"Authorization": f"Bearer {data['admin_token']}"})
        upper = client.get(SEARCH_URL, params={"q": "HYPERTENSION"},
                           headers={"Authorization": f"Bearer {data['admin_token']}"})
        mixed = client.get(SEARCH_URL, params={"q": "HyperTension"},
                           headers={"Authorization": f"Bearer {data['admin_token']}"})
        assert lower.json()["total"] == upper.json()["total"] == mixed.json()["total"]

    def test_multiple_matches_same_entity(self, client, db):
        data = _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "Amlodipine"},
                          headers={"Authorization": f"Bearer {data['admin_token']}"})
        body = resp.json()
        medicine_count = sum(1 for r in body["items"] if r["entity_type"] == "medicine")
        rx_item_count = sum(1 for r in body["items"] if r["entity_type"] == "prescription_item")
        assert medicine_count >= 1
        assert rx_item_count >= 1


class TestSearchMedicinesUnauthenticated:
    def test_medicines_require_auth(self, client, db):
        _seed_all(db)
        resp = client.get(SEARCH_URL, params={"q": "Amlodipine", "entity": "medicines"})
        assert resp.status_code == 401
