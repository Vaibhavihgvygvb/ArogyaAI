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


def _create_prescription(client, token, visit_id, doctor_id, patient_id):
    resp = client.post(
        "/prescriptions",
        json={
            "visit_id": visit_id,
            "doctor_id": doctor_id,
            "patient_id": patient_id,
            "diagnosis": "Test diagnosis",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()["id"]


def _create_item(client, token, prescription_id, **overrides):
    payload = {
        "medicine_name": "Amoxicillin",
        "strength": "500mg",
        "dosage": "1 tablet",
        "frequency": "Three times daily",
        "duration": "7 days",
        "quantity": 21,
        "route": "Oral",
        "instructions": "Take after meals",
    }
    payload.update(overrides)
    return client.post(
        f"/prescriptions/{prescription_id}/items",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )


def _create_item_and_return(client, token, prescription_id):
    resp = _create_item(client, token, prescription_id)
    return resp.json()["id"]


def test_get_items_returns_empty_list(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)
    prescription_id = _create_prescription(client, doctor_with_profile, visit_id, doctor_id, patient_id)

    response = client.get(
        f"/prescriptions/{prescription_id}/items",
        headers={"Authorization": f"Bearer {doctor_with_profile}"},
    )
    assert response.status_code == 200
    assert response.json() == []


def test_create_item(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)
    prescription_id = _create_prescription(client, doctor_with_profile, visit_id, doctor_id, patient_id)

    response = _create_item(client, doctor_with_profile, prescription_id)
    assert response.status_code == 201
    data = response.json()
    assert data["medicine_name"] == "Amoxicillin"
    assert data["strength"] == "500mg"
    assert data["dosage"] == "1 tablet"
    assert data["frequency"] == "Three times daily"
    assert data["duration"] == "7 days"
    assert data["quantity"] == 21
    assert data["route"] == "Oral"
    assert data["instructions"] == "Take after meals"
    assert data["prescription_id"] == prescription_id
    assert "id" in data


def test_get_item_by_id(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)
    prescription_id = _create_prescription(client, doctor_with_profile, visit_id, doctor_id, patient_id)
    item_id = _create_item_and_return(client, doctor_with_profile, prescription_id)

    response = client.get(
        f"/prescriptions/items/{item_id}",
        headers={"Authorization": f"Bearer {doctor_with_profile}"},
    )
    assert response.status_code == 200
    assert response.json()["medicine_name"] == "Amoxicillin"
    assert response.json()["id"] == item_id


def test_list_items(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)
    prescription_id = _create_prescription(client, doctor_with_profile, visit_id, doctor_id, patient_id)
    _create_item_and_return(client, doctor_with_profile, prescription_id)
    _create_item(client, doctor_with_profile, prescription_id, medicine_name="Paracetamol")

    response = client.get(
        f"/prescriptions/{prescription_id}/items",
        headers={"Authorization": f"Bearer {doctor_with_profile}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_update_item(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)
    prescription_id = _create_prescription(client, doctor_with_profile, visit_id, doctor_id, patient_id)
    item_id = _create_item_and_return(client, doctor_with_profile, prescription_id)

    response = client.patch(
        f"/prescriptions/items/{item_id}",
        json={"dosage": "2 tablets", "instructions": "Take before meals"},
        headers={"Authorization": f"Bearer {doctor_with_profile}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["dosage"] == "2 tablets"
    assert data["instructions"] == "Take before meals"
    assert data["medicine_name"] == "Amoxicillin"


def test_delete_item(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)
    prescription_id = _create_prescription(client, doctor_with_profile, visit_id, doctor_id, patient_id)
    item_id = _create_item_and_return(client, doctor_with_profile, prescription_id)

    delete_resp = client.delete(
        f"/prescriptions/items/{item_id}",
        headers={"Authorization": f"Bearer {doctor_with_profile}"},
    )
    assert delete_resp.status_code == 204

    get_resp = client.get(
        f"/prescriptions/items/{item_id}",
        headers={"Authorization": f"Bearer {doctor_with_profile}"},
    )
    assert get_resp.status_code == 404


def test_patient_cannot_create_item(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)
    prescription_id = _create_prescription(client, doctor_with_profile, visit_id, doctor_id, patient_id)

    response = _create_item(client, patient_with_profile, prescription_id)
    assert response.status_code == 403


def test_patient_cannot_update_item(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)
    prescription_id = _create_prescription(client, doctor_with_profile, visit_id, doctor_id, patient_id)
    item_id = _create_item_and_return(client, doctor_with_profile, prescription_id)

    response = client.patch(
        f"/prescriptions/items/{item_id}",
        json={"dosage": "2 tablets"},
        headers={"Authorization": f"Bearer {patient_with_profile}"},
    )
    assert response.status_code == 403


def test_patient_cannot_delete_item(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)
    prescription_id = _create_prescription(client, doctor_with_profile, visit_id, doctor_id, patient_id)
    item_id = _create_item_and_return(client, doctor_with_profile, prescription_id)

    response = client.delete(
        f"/prescriptions/items/{item_id}",
        headers={"Authorization": f"Bearer {patient_with_profile}"},
    )
    assert response.status_code == 403


def test_item_not_found_returns_404(client, doctor_with_profile):
    response = client.get(
        "/prescriptions/items/99999",
        headers={"Authorization": f"Bearer {doctor_with_profile}"},
    )
    assert response.status_code == 404


def test_create_item_empty_medicine_name_returns_400(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)
    prescription_id = _create_prescription(client, doctor_with_profile, visit_id, doctor_id, patient_id)

    response = _create_item(client, doctor_with_profile, prescription_id, medicine_name="")
    assert response.status_code == 422


def test_create_item_prescription_not_found_returns_404(client, doctor_with_profile):
    response = _create_item(client, doctor_with_profile, prescription_id=99999)
    assert response.status_code == 404


def test_patient_reads_own_item(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)
    prescription_id = _create_prescription(client, doctor_with_profile, visit_id, doctor_id, patient_id)
    item_id = _create_item_and_return(client, doctor_with_profile, prescription_id)

    response = client.get(
        f"/prescriptions/items/{item_id}",
        headers={"Authorization": f"Bearer {patient_with_profile}"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == item_id


def test_patient_lists_own_items(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)
    prescription_id = _create_prescription(client, doctor_with_profile, visit_id, doctor_id, patient_id)
    _create_item_and_return(client, doctor_with_profile, prescription_id)

    response = client.get(
        f"/prescriptions/{prescription_id}/items",
        headers={"Authorization": f"Bearer {patient_with_profile}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_doctor_cannot_access_other_doctors_item(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)
    prescription_id = _create_prescription(client, doctor_with_profile, visit_id, doctor_id, patient_id)
    item_id = _create_item_and_return(client, doctor_with_profile, prescription_id)

    client.post(
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
        f"/prescriptions/items/{item_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code == 403


def test_admin_can_access_any_item(client, admin_token, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)
    prescription_id = _create_prescription(client, doctor_with_profile, visit_id, doctor_id, patient_id)
    item_id = _create_item_and_return(client, doctor_with_profile, prescription_id)

    response = client.get(
        f"/prescriptions/items/{item_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == item_id


def test_admin_can_create_item(client, admin_token, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)
    prescription_id = _create_prescription(client, doctor_with_profile, visit_id, doctor_id, patient_id)

    response = _create_item(client, admin_token, prescription_id)
    assert response.status_code == 201


def test_admin_can_delete_item(client, admin_token, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)
    prescription_id = _create_prescription(client, doctor_with_profile, visit_id, doctor_id, patient_id)
    item_id = _create_item_and_return(client, doctor_with_profile, prescription_id)

    response = client.delete(
        f"/prescriptions/items/{item_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204


def test_unauthorized_access_returns_401(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    visit_id = _create_visit(client, doctor_with_profile, doctor_id, patient_id)
    prescription_id = _create_prescription(client, doctor_with_profile, visit_id, doctor_id, patient_id)

    response = client.get(
        f"/prescriptions/{prescription_id}/items",
    )
    assert response.status_code == 401
