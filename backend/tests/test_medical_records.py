from datetime import datetime, timezone


def _get_doctor_id(client, token):
    resp = client.get("/doctors/me", headers={"Authorization": f"Bearer {token}"})
    return resp.json()["id"]


def _get_patient_id(client, token):
    resp = client.get("/patients/me", headers={"Authorization": f"Bearer {token}"})
    return resp.json()["id"]


def _create_visit(client, token, doctor_id, patient_id):
    resp = client.post(
        "/visits",
        json={
            "doctor_id": doctor_id,
            "patient_id": patient_id,
            "visit_date": datetime.now(timezone.utc).isoformat(),
            "diagnosis": "Test diagnosis",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()["id"]


def _sample_record(visit_id, doctor_id, patient_id, **overrides):
    payload = {
        "visit_id": visit_id,
        "doctor_id": doctor_id,
        "patient_id": patient_id,
        "chief_complaint": "Headache and fever",
        "history_of_present_illness": "Onset 3 days ago",
        "past_medical_history": "None",
        "family_history": "None",
        "surgical_history": "None",
        "allergy_history": "No known allergies",
        "medication_history": "None",
        "social_history": "Non-smoker",
        "physical_examination": "BP normal, heart sounds normal",
        "assessment": "Likely viral infection",
        "diagnosis": "Viral fever",
        "treatment_plan": "Rest and hydration",
        "follow_up_instructions": "Return if symptoms worsen",
        "height": 170.0,
        "weight": 70.0,
        "bmi": 24.2,
        "blood_pressure": "120/80",
        "pulse": 72,
        "respiratory_rate": 16,
        "temperature": 37.5,
        "oxygen_saturation": 98.0,
        "notes": "Patient recovering well",
    }
    payload.update(overrides)
    return payload


def _create_record(client, token, visit_id, doctor_id, patient_id, **overrides):
    return client.post(
        "/medical-records",
        json=_sample_record(visit_id, doctor_id, patient_id, **overrides),
        headers={"Authorization": f"Bearer {token}"},
    )


def _create_record_and_return(client, token, visit_id, doctor_id, patient_id, **overrides):
    resp = _create_record(client, token, visit_id, doctor_id, patient_id, **overrides)
    return resp.json()["id"]


def _setup_visit_and_record(client, doctor_token, patient_token):
    doctor_id = _get_doctor_id(client, doctor_token)
    patient_id = _get_patient_id(client, patient_token)
    visit_id = _create_visit(client, doctor_token, doctor_id, patient_id)
    record_id = _create_record_and_return(client, doctor_token, visit_id, doctor_id, patient_id)
    return doctor_id, patient_id, visit_id, record_id


# --- CRUD ---

def test_list_medical_records_returns_empty_list(client, doctor_with_profile):
    response = client.get(
        "/medical-records",
        headers={"Authorization": f"Bearer {doctor_with_profile}"},
    )
    assert response.status_code == 200
    assert response.json() == []


def test_create_medical_record(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)

    response = _create_record(client, doctor_with_profile, visit_id, doctor_id, patient_id)
    assert response.status_code == 201
    data = response.json()
    assert data["visit_id"] == visit_id
    assert data["doctor_id"] == doctor_id
    assert data["patient_id"] == patient_id
    assert data["diagnosis"] == "Viral fever"
    assert data["chief_complaint"] == "Headache and fever"
    assert data["temperature"] == 37.5
    assert data["oxygen_saturation"] == 98.0
    assert data["blood_pressure"] == "120/80"
    assert "id" in data


def test_get_medical_record_by_id(client, doctor_with_profile, patient_with_profile):
    doctor_id, patient_id, visit_id, record_id = _setup_visit_and_record(
        client, doctor_with_profile, patient_with_profile
    )

    response = client.get(
        f"/medical-records/{record_id}",
        headers={"Authorization": f"Bearer {doctor_with_profile}"},
    )
    assert response.status_code == 200
    assert response.json()["diagnosis"] == "Viral fever"


def test_get_medical_record_by_visit(client, doctor_with_profile, patient_with_profile):
    doctor_id, patient_id, visit_id, record_id = _setup_visit_and_record(
        client, doctor_with_profile, patient_with_profile
    )

    response = client.get(
        f"/visits/{visit_id}/medical-record",
        headers={"Authorization": f"Bearer {doctor_with_profile}"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == record_id


def test_update_medical_record(client, doctor_with_profile, patient_with_profile):
    doctor_id, patient_id, visit_id, record_id = _setup_visit_and_record(
        client, doctor_with_profile, patient_with_profile
    )

    response = client.patch(
        f"/medical-records/{record_id}",
        json={"diagnosis": "Bacterial infection", "notes": "Updated notes"},
        headers={"Authorization": f"Bearer {doctor_with_profile}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["diagnosis"] == "Bacterial infection"
    assert data["notes"] == "Updated notes"
    assert data["chief_complaint"] == "Headache and fever"


def test_delete_medical_record(client, doctor_with_profile, patient_with_profile, admin_token):
    doctor_id, patient_id, visit_id, record_id = _setup_visit_and_record(
        client, doctor_with_profile, patient_with_profile
    )

    delete_resp = client.delete(
        f"/medical-records/{record_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert delete_resp.status_code == 204

    get_resp = client.get(
        f"/medical-records/{record_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_resp.status_code == 404


def test_record_not_found_returns_404(client, doctor_with_profile):
    response = client.get(
        "/medical-records/99999",
        headers={"Authorization": f"Bearer {doctor_with_profile}"},
    )
    assert response.status_code == 404


def test_record_by_visit_not_found_returns_404(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)

    response = client.get(
        f"/visits/{visit_id}/medical-record",
        headers={"Authorization": f"Bearer {doctor_with_profile}"},
    )
    assert response.status_code == 404


# --- Authorization ---

def test_doctor_can_create_record(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)

    response = _create_record(client, doctor_with_profile, visit_id, doctor_id, patient_id)
    assert response.status_code == 201


def test_patient_cannot_create_record(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)

    response = _create_record(client, patient_with_profile, visit_id, doctor_id, patient_id)
    assert response.status_code == 403


def test_patient_cannot_update_record(client, doctor_with_profile, patient_with_profile):
    doctor_id, patient_id, visit_id, record_id = _setup_visit_and_record(
        client, doctor_with_profile, patient_with_profile
    )

    response = client.patch(
        f"/medical-records/{record_id}",
        json={"notes": "Should fail"},
        headers={"Authorization": f"Bearer {patient_with_profile}"},
    )
    assert response.status_code == 403


def test_patient_cannot_delete_record(client, doctor_with_profile, patient_with_profile, patient_token):
    doctor_id, patient_id, visit_id, record_id = _setup_visit_and_record(
        client, doctor_with_profile, patient_with_profile
    )

    response = client.delete(
        f"/medical-records/{record_id}",
        headers={"Authorization": f"Bearer {patient_with_profile}"},
    )
    assert response.status_code == 403


def test_doctor_cannot_delete_record(client, doctor_with_profile, patient_with_profile):
    doctor_id, patient_id, visit_id, record_id = _setup_visit_and_record(
        client, doctor_with_profile, patient_with_profile
    )

    response = client.delete(
        f"/medical-records/{record_id}",
        headers={"Authorization": f"Bearer {doctor_with_profile}"},
    )
    assert response.status_code == 403


def test_admin_can_create_record(client, admin_token, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)

    response = _create_record(client, admin_token, visit_id, doctor_id, patient_id)
    assert response.status_code == 201


def test_unauthorized_access_returns_401(client):
    response = client.get("/medical-records")
    assert response.status_code == 401


# --- Ownership ---

def test_patient_reads_own_record(client, doctor_with_profile, patient_with_profile):
    doctor_id, patient_id, visit_id, record_id = _setup_visit_and_record(
        client, doctor_with_profile, patient_with_profile
    )

    response = client.get(
        f"/medical-records/{record_id}",
        headers={"Authorization": f"Bearer {patient_with_profile}"},
    )
    assert response.status_code == 200
    assert response.json()["patient_id"] == patient_id


def test_patient_cannot_read_other_patient_record(client, doctor_with_profile, patient_with_profile):
    doctor_id, patient_id, visit_id, record_id = _setup_visit_and_record(
        client, doctor_with_profile, patient_with_profile
    )

    register_resp = client.post(
        "/auth/register",
        json={"email": "other_patient@test.com", "password": "testpass123", "role": "patient"},
    )
    other_login = client.post(
        "/auth/login",
        json={"email": "other_patient@test.com", "password": "testpass123"},
    )
    other_token = other_login.json()["access_token"]

    client.post(
        "/profile/complete",
        json={
            "full_name": "Other Patient",
            "phone_number": "7777777777",
        },
        headers={"Authorization": f"Bearer {other_token}"},
    )

    response = client.get(
        f"/medical-records/{record_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code == 403


def test_doctor_cannot_create_for_other_doctor(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)

    other_register = client.post(
        "/auth/register",
        json={"email": "other_doc2@test.com", "password": "testpass123", "role": "doctor"},
    )
    other_login = client.post(
        "/auth/login",
        json={"email": "other_doc2@test.com", "password": "testpass123"},
    )
    other_token = other_login.json()["access_token"]

    client.post(
        "/profile/complete",
        json={
            "full_name": "Dr Other",
            "phone_number": "8888888888",
            "specialization": "General",
            "clinic_name": "Other Clinic",
        },
        headers={"Authorization": f"Bearer {other_token}"},
    )
    other_doctor_id = _get_doctor_id(client, other_token)

    response = _create_record(client, other_token, visit_id, other_doctor_id, patient_id)
    assert response.status_code == 403


# --- Validation ---

def test_create_record_visit_not_found_returns_404(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)

    response = _create_record(client, doctor_with_profile, visit_id=99999, doctor_id=doctor_id, patient_id=patient_id)
    assert response.status_code == 404
    assert "visit not found" in response.json()["detail"].lower()


def test_create_record_cancelled_visit_returns_400(client, doctor_with_profile, patient_with_profile, db):
    from app.models.visit import Visit

    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)

    visit = db.get(Visit, visit_id)
    visit.status = "cancelled"
    db.commit()

    response = _create_record(client, doctor_with_profile, visit_id, doctor_id, patient_id)
    assert response.status_code == 400
    assert "cancelled" in response.json()["detail"].lower()


def test_create_record_duplicate_returns_409(client, doctor_with_profile, patient_with_profile):
    doctor_id, patient_id, visit_id, record_id = _setup_visit_and_record(
        client, doctor_with_profile, patient_with_profile
    )

    response = _create_record(client, doctor_with_profile, visit_id, doctor_id, patient_id)
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


def test_create_record_empty_diagnosis_returns_422(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)

    response = _create_record(client, doctor_with_profile, visit_id, doctor_id, patient_id, diagnosis="")
    assert response.status_code == 422


def test_update_cannot_reassign_visit(client, doctor_with_profile, patient_with_profile):
    doctor_id, patient_id, visit_id, record_id = _setup_visit_and_record(
        client, doctor_with_profile, patient_with_profile
    )
    visit2_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)

    response = client.patch(
        f"/medical-records/{record_id}",
        json={"visit_id": visit2_id},
        headers={"Authorization": f"Bearer {doctor_with_profile}"},
    )
    assert response.status_code == 400
    assert "reassign" in response.json()["detail"].lower()


# --- Vitals Validation ---

def test_create_record_temperature_too_low_returns_422(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)

    response = _create_record(client, doctor_with_profile, visit_id, doctor_id, patient_id, temperature=30.0)
    assert response.status_code == 422


def test_create_record_temperature_too_high_returns_422(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)

    response = _create_record(client, doctor_with_profile, visit_id, doctor_id, patient_id, temperature=44.0)
    assert response.status_code == 422


def test_create_record_oxygen_saturation_too_high_returns_422(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)

    response = _create_record(client, doctor_with_profile, visit_id, doctor_id, patient_id, oxygen_saturation=101)
    assert response.status_code == 422


def test_create_record_blood_pressure_invalid_format_returns_422(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)

    response = _create_record(client, doctor_with_profile, visit_id, doctor_id, patient_id, blood_pressure="invalid")
    assert response.status_code == 422


def test_update_record_blood_pressure_invalid_returns_422(client, doctor_with_profile, patient_with_profile):
    doctor_id, patient_id, visit_id, record_id = _setup_visit_and_record(
        client, doctor_with_profile, patient_with_profile
    )

    response = client.patch(
        f"/medical-records/{record_id}",
        json={"blood_pressure": "bad"},
        headers={"Authorization": f"Bearer {doctor_with_profile}"},
    )
    assert response.status_code == 422


def test_create_record_negative_height_returns_422(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)

    response = _create_record(client, doctor_with_profile, visit_id, doctor_id, patient_id, height=-5)
    assert response.status_code == 422


# --- Role-based list scoping ---

def test_doctor_lists_only_own_records(client, doctor_with_profile, patient_with_profile):
    doctor_id, patient_id, visit_id, record_id = _setup_visit_and_record(
        client, doctor_with_profile, patient_with_profile
    )

    response = client.get(
        "/medical-records",
        headers={"Authorization": f"Bearer {doctor_with_profile}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_admin_lists_all_records(client, admin_token, doctor_with_profile, patient_with_profile):
    _setup_visit_and_record(client, doctor_with_profile, patient_with_profile)

    response = client.get(
        "/medical-records",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1


# --- Completed visit allowed ---

def test_create_record_creates_audit_log(client, doctor_with_profile, patient_with_profile, db):
    from app.models.audit_log import AuditLog
    from sqlalchemy import select
    import json

    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)

    _create_record(client, doctor_with_profile, visit_id, doctor_id, patient_id)

    logs = list(db.scalars(
        select(AuditLog).where(AuditLog.action == "CREATE_MEDICAL_RECORD")
    ).all())
    assert len(logs) >= 1
    log = logs[-1]
    assert log.resource.startswith("medical_record:")
    assert log.user_id is not None

    details = json.loads(log.details)
    assert details["action"] == "CREATE_MEDICAL_RECORD"
    assert details["visit_id"] == visit_id
    assert details["doctor_id"] == doctor_id
    assert details["patient_id"] == patient_id
    assert "new_values" in details
    assert details["new_values"]["diagnosis"] == "Viral fever"
    assert "changed_fields" in details
    assert "timestamp" in details


def test_update_record_creates_audit_log(client, doctor_with_profile, patient_with_profile, db):
    from app.models.audit_log import AuditLog
    from sqlalchemy import select
    import json

    doctor_id, patient_id, visit_id, record_id = _setup_visit_and_record(
        client, doctor_with_profile, patient_with_profile
    )

    client.patch(
        f"/medical-records/{record_id}",
        json={"diagnosis": "Updated diagnosis", "notes": "New notes"},
        headers={"Authorization": f"Bearer {doctor_with_profile}"},
    )

    logs = list(db.scalars(
        select(AuditLog).where(AuditLog.action == "UPDATE_MEDICAL_RECORD")
    ).all())
    assert len(logs) >= 1
    log = logs[-1]
    assert log.user_id is not None

    details = json.loads(log.details)
    assert details["action"] == "UPDATE_MEDICAL_RECORD"
    assert details["visit_id"] == visit_id
    assert "old_values" in details
    assert details["old_values"]["diagnosis"] == "Viral fever"
    assert details["new_values"]["diagnosis"] == "Updated diagnosis"
    assert details["new_values"]["notes"] == "New notes"
    assert sorted(details["changed_fields"]) == ["diagnosis", "notes"]


def test_delete_record_creates_audit_log(client, doctor_with_profile, patient_with_profile, admin_token, db):
    from app.models.audit_log import AuditLog
    from sqlalchemy import select
    import json

    doctor_id, patient_id, visit_id, record_id = _setup_visit_and_record(
        client, doctor_with_profile, patient_with_profile
    )

    client.delete(
        f"/medical-records/{record_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    logs = list(db.scalars(
        select(AuditLog).where(AuditLog.action == "DELETE_MEDICAL_RECORD")
    ).all())
    assert len(logs) >= 1
    log = logs[-1]
    assert log.user_id is not None
    assert str(record_id) in (log.resource or "")

    details = json.loads(log.details)
    assert details["action"] == "DELETE_MEDICAL_RECORD"
    assert details["visit_id"] == visit_id
    assert "old_values" in details
    assert details["old_values"]["diagnosis"] == "Viral fever"
    assert "new_values" not in details
    assert "timestamp" in details


def test_create_record_completed_visit_succeeds(client, doctor_with_profile, patient_with_profile, db):

    from app.models.visit import Visit

    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)

    visit = db.get(Visit, visit_id)
    visit.status = "completed"
    db.commit()

    response = _create_record(client, doctor_with_profile, visit_id, doctor_id, patient_id)
    assert response.status_code == 201


# --- BMI Auto-Calculation ---

def test_create_record_auto_calculates_bmi(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)

    response = _create_record(
        client, doctor_with_profile, visit_id, doctor_id, patient_id,
        height=170.0, weight=70.0, bmi=None,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["height"] == 170.0
    assert data["weight"] == 70.0
    assert data["bmi"] == 24.22


def test_create_record_bmi_not_calculated_without_height(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)

    response = _create_record(
        client, doctor_with_profile, visit_id, doctor_id, patient_id,
        height=None, weight=70.0,
    )
    assert response.status_code == 201
    assert response.json()["bmi"] is None


def test_create_record_bmi_not_calculated_without_weight(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)

    response = _create_record(
        client, doctor_with_profile, visit_id, doctor_id, patient_id,
        height=170.0, weight=None,
    )
    assert response.status_code == 201
    assert response.json()["bmi"] is None


def test_update_record_recalculates_bmi_on_height_change(client, doctor_with_profile, patient_with_profile):
    doctor_id, patient_id, visit_id, record_id = _setup_visit_and_record(
        client, doctor_with_profile, patient_with_profile
    )

    response = client.patch(
        f"/medical-records/{record_id}",
        json={"height": 180.0},
        headers={"Authorization": f"Bearer {doctor_with_profile}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["height"] == 180.0
    assert data["bmi"] == 21.6


def test_update_record_recalculates_bmi_on_weight_change(client, doctor_with_profile, patient_with_profile):
    doctor_id, patient_id, visit_id, record_id = _setup_visit_and_record(
        client, doctor_with_profile, patient_with_profile
    )

    response = client.patch(
        f"/medical-records/{record_id}",
        json={"weight": 80.0},
        headers={"Authorization": f"Bearer {doctor_with_profile}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["weight"] == 80.0
    expected = round(80.0 / ((170.0 / 100) ** 2), 2)
    assert data["bmi"] == expected


def test_update_record_bmi_unchanged_when_height_weight_not_modified(client, doctor_with_profile, patient_with_profile):
    doctor_id, patient_id, visit_id, record_id = _setup_visit_and_record(
        client, doctor_with_profile, patient_with_profile
    )

    response = client.patch(
        f"/medical-records/{record_id}",
        json={"diagnosis": "New diagnosis"},
        headers={"Authorization": f"Bearer {doctor_with_profile}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["bmi"] == 24.22


def test_create_record_zero_height_returns_422(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)

    response = _create_record(
        client, doctor_with_profile, visit_id, doctor_id, patient_id,
        height=0, weight=70,
    )
    assert response.status_code == 422


def test_create_record_zero_weight_returns_422(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)

    response = _create_record(
        client, doctor_with_profile, visit_id, doctor_id, patient_id,
        height=170, weight=0,
    )
    assert response.status_code == 422


def test_update_record_zero_height_returns_422(client, doctor_with_profile, patient_with_profile):
    doctor_id, patient_id, visit_id, record_id = _setup_visit_and_record(
        client, doctor_with_profile, patient_with_profile
    )

    response = client.patch(
        f"/medical-records/{record_id}",
        json={"height": 0},
        headers={"Authorization": f"Bearer {doctor_with_profile}"},
    )
    assert response.status_code == 422
