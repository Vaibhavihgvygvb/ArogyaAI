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


def _create_prescription(client, token, visit_id, doctor_id, patient_id, diagnosis="Test prescription"):
    return client.post(
        "/prescriptions",
        json={
            "visit_id": visit_id,
            "doctor_id": doctor_id,
            "patient_id": patient_id,
            "diagnosis": diagnosis,
        },
        headers={"Authorization": f"Bearer {token}"},
    )


def _update_prescription(client, token, prescription_id, **kwargs):
    return client.patch(
        f"/prescriptions/{prescription_id}",
        json=kwargs,
        headers={"Authorization": f"Bearer {token}"},
    )


def test_get_prescriptions_returns_empty_list(client, doctor_with_profile):
    response = client.get(
        "/prescriptions",
        headers={"Authorization": f"Bearer {doctor_with_profile}"},
    )
    assert response.status_code == 200
    assert response.json() == []


def test_create_prescription(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)

    response = _create_prescription(client, doctor_with_profile, visit_id, doctor_id, patient_id)
    assert response.status_code == 201
    data = response.json()
    assert data["visit_id"] == visit_id
    assert data["doctor_id"] == doctor_id
    assert data["patient_id"] == patient_id
    assert data["diagnosis"] == "Test prescription"
    assert "id" in data


def test_get_prescription_by_id(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)
    create_resp = _create_prescription(client, doctor_with_profile, visit_id, doctor_id, patient_id, diagnosis="Follow-up Rx")
    prescription_id = create_resp.json()["id"]

    response = client.get(
        f"/prescriptions/{prescription_id}",
        headers={"Authorization": f"Bearer {doctor_with_profile}"},
    )
    assert response.status_code == 200
    assert response.json()["diagnosis"] == "Follow-up Rx"


def test_update_prescription(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)
    create_resp = _create_prescription(client, doctor_with_profile, visit_id, doctor_id, patient_id)
    prescription_id = create_resp.json()["id"]

    update_resp = _update_prescription(
        client, doctor_with_profile, prescription_id,
        diagnosis="Updated diagnosis", notes="Take with food",
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["diagnosis"] == "Updated diagnosis"
    assert data["notes"] == "Take with food"


def test_delete_prescription(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)
    create_resp = _create_prescription(client, doctor_with_profile, visit_id, doctor_id, patient_id)
    prescription_id = create_resp.json()["id"]

    delete_resp = client.delete(
        f"/prescriptions/{prescription_id}",
        headers={"Authorization": f"Bearer {doctor_with_profile}"},
    )
    assert delete_resp.status_code == 204

    get_resp = client.get(
        f"/prescriptions/{prescription_id}",
        headers={"Authorization": f"Bearer {doctor_with_profile}"},
    )
    assert get_resp.status_code == 404


def test_patient_sees_only_own_prescriptions(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)
    _create_prescription(client, doctor_with_profile, visit_id, doctor_id, patient_id)

    patient_list = client.get(
        "/prescriptions",
        headers={"Authorization": f"Bearer {patient_with_profile}"},
    )
    assert patient_list.status_code == 200
    assert len(patient_list.json()) == 1


def test_patient_cannot_create_prescription(client, patient_with_profile, doctor_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)

    response = _create_prescription(client, patient_with_profile, visit_id, doctor_id, patient_id)
    assert response.status_code == 403


def test_create_prescription_visit_not_found_returns_404(client, doctor_with_profile):
    response = _create_prescription(
        client, doctor_with_profile, visit_id=99999, doctor_id=1, patient_id=1,
    )
    assert response.status_code == 404
    assert "visit not found" in response.json()["detail"].lower()


def test_create_prescription_cancelled_visit_returns_400(client, doctor_with_profile, patient_with_profile, db):
    from app.models.visit import Visit
    from datetime import datetime, timezone

    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)

    visit = db.get(Visit, visit_id)
    visit.status = "cancelled"
    db.commit()

    response = _create_prescription(client, doctor_with_profile, visit_id, doctor_id, patient_id)
    assert response.status_code == 400
    assert "cancelled" in response.json()["detail"].lower()


def test_create_prescription_completed_visit_succeeds(client, doctor_with_profile, patient_with_profile, db):
    from app.models.visit import Visit

    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)

    visit = db.get(Visit, visit_id)
    visit.status = "completed"
    db.commit()

    response = _create_prescription(client, doctor_with_profile, visit_id, doctor_id, patient_id)
    assert response.status_code == 201


def test_patient_reads_own_prescription(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)
    create_resp = _create_prescription(client, doctor_with_profile, visit_id, doctor_id, patient_id)
    prescription_id = create_resp.json()["id"]

    response = client.get(
        f"/prescriptions/{prescription_id}",
        headers={"Authorization": f"Bearer {patient_with_profile}"},
    )
    assert response.status_code == 200
    assert response.json()["patient_id"] == patient_id


def test_doctor_cannot_access_other_doctors_prescription(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)
    create_resp = _create_prescription(client, doctor_with_profile, visit_id, doctor_id, patient_id)
    prescription_id = create_resp.json()["id"]

    other_doctor_register = client.post(
        "/auth/register",
        json={"email": "other_doc@test.com", "password": "testpass123", "role": "doctor"},
    )
    other_login = client.post(
        "/auth/login",
        json={"email": "other_doc@test.com", "password": "testpass123"},
    )
    other_token = other_login.json()["access_token"]

    client.post(
        "/profile/complete",
        json={
            "full_name": "Dr Other",
            "phone_number": "9999999999",
            "specialization": "General",
            "clinic_name": "Other Clinic",
        },
        headers={"Authorization": f"Bearer {other_token}"},
    )

    response = client.get(
        f"/prescriptions/{prescription_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code == 403


def test_update_prescription_notes_only(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)
    create_resp = _create_prescription(client, doctor_with_profile, visit_id, doctor_id, patient_id)
    prescription_id = create_resp.json()["id"]

    update_resp = _update_prescription(client, doctor_with_profile, prescription_id, notes="Additional instructions")
    assert update_resp.status_code == 200
    assert update_resp.json()["notes"] == "Additional instructions"
    assert update_resp.json()["diagnosis"] == "Test prescription"


def test_admin_can_access_all_prescriptions(client, admin_token, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)
    _create_prescription(client, doctor_with_profile, visit_id, doctor_id, patient_id)

    response = client.get(
        "/prescriptions",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1
