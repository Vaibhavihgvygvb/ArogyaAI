def _sample_medicine(**overrides):
    payload = {
        "generic_name": "Amoxicillin",
        "brand_name": "Amoxil",
        "manufacturer": "GSK",
        "strength": "500mg",
        "dosage_form": "Tablet",
        "route": "Oral",
        "drug_class": "Penicillin",
        "requires_prescription": True,
        "contraindications": "Allergy to penicillin",
        "side_effects": "Nausea, diarrhea",
        "drug_interactions": "Warfarin",
        "pregnancy_category": "B",
        "storage_information": "Store at room temperature",
        "description": "Broad-spectrum antibiotic",
        "is_active": True,
    }
    payload.update(overrides)
    return payload


def _create_medicine(client, token, **overrides):
    return client.post(
        "/medicines",
        json=_sample_medicine(**overrides),
        headers={"Authorization": f"Bearer {token}"},
    )


def _create_medicine_and_return(client, token, **overrides):
    resp = _create_medicine(client, token, **overrides)
    return resp.json()["id"]


# --- CRUD ---

def test_list_medicines_returns_empty_list(client, admin_token):
    response = client.get(
        "/medicines",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json() == []


def test_create_medicine(client, admin_token):
    response = _create_medicine(client, admin_token)
    assert response.status_code == 201
    data = response.json()
    assert data["generic_name"] == "Amoxicillin"
    assert data["brand_name"] == "Amoxil"
    assert data["strength"] == "500mg"
    assert data["dosage_form"] == "Tablet"
    assert data["route"] == "Oral"
    assert data["is_active"] is True
    assert "id" in data


def test_get_medicine_by_id(client, admin_token):
    medicine_id = _create_medicine_and_return(client, admin_token)

    response = client.get(
        f"/medicines/{medicine_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["generic_name"] == "Amoxicillin"


def test_update_medicine(client, admin_token):
    medicine_id = _create_medicine_and_return(client, admin_token)

    response = client.patch(
        f"/medicines/{medicine_id}",
        json={"strength": "250mg", "description": "Updated description"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["strength"] == "250mg"
    assert data["description"] == "Updated description"
    assert data["generic_name"] == "Amoxicillin"


def test_delete_medicine(client, admin_token):
    medicine_id = _create_medicine_and_return(client, admin_token)

    delete_resp = client.delete(
        f"/medicines/{medicine_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert delete_resp.status_code == 204

    get_resp = client.get(
        f"/medicines/{medicine_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_resp.status_code == 404


def test_medicine_not_found_returns_404(client, admin_token):
    response = client.get(
        "/medicines/99999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


# --- Authorization ---

def test_doctor_can_read_medicine(client, admin_token, doctor_token):
    medicine_id = _create_medicine_and_return(client, admin_token)

    response = client.get(
        f"/medicines/{medicine_id}",
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert response.status_code == 200


def test_patient_can_read_medicine(client, admin_token, patient_token):
    medicine_id = _create_medicine_and_return(client, admin_token)

    response = client.get(
        f"/medicines/{medicine_id}",
        headers={"Authorization": f"Bearer {patient_token}"},
    )
    assert response.status_code == 200


def test_doctor_can_list_medicines(client, admin_token, doctor_token):
    _create_medicine_and_return(client, admin_token)

    response = client.get(
        "/medicines",
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_doctor_cannot_create_medicine(client, doctor_token):
    response = _create_medicine(client, doctor_token)
    assert response.status_code == 403


def test_doctor_cannot_update_medicine(client, admin_token, doctor_token):
    medicine_id = _create_medicine_and_return(client, admin_token)

    response = client.patch(
        f"/medicines/{medicine_id}",
        json={"strength": "250mg"},
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert response.status_code == 403


def test_doctor_cannot_delete_medicine(client, admin_token, doctor_token):
    medicine_id = _create_medicine_and_return(client, admin_token)

    response = client.delete(
        f"/medicines/{medicine_id}",
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert response.status_code == 403


def test_patient_cannot_create_medicine(client, patient_token):
    response = _create_medicine(client, patient_token)
    assert response.status_code == 403


def test_unauthorized_access_returns_401(client):
    response = client.get("/medicines")
    assert response.status_code == 401


# --- Validation ---

def test_create_medicine_invalid_dosage_form(client, admin_token):
    response = _create_medicine(client, admin_token, dosage_form="InvalidForm")
    assert response.status_code == 400
    assert "Invalid dosage form" in response.json()["detail"]


def test_create_medicine_invalid_route(client, admin_token):
    response = _create_medicine(client, admin_token, route="InvalidRoute")
    assert response.status_code == 400
    assert "Invalid route" in response.json()["detail"]


def test_create_medicine_duplicate_returns_409(client, admin_token):
    _create_medicine_and_return(client, admin_token)

    response = _create_medicine(client, admin_token)
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_create_medicine_duplicate_different_strength_allowed(client, admin_token):
    _create_medicine_and_return(client, admin_token)

    response = _create_medicine(client, admin_token, strength="250mg")
    assert response.status_code == 201


def test_update_medicine_duplicate_returns_409(client, admin_token):
    _create_medicine_and_return(client, admin_token, generic_name="Paracetamol", strength="500mg", dosage_form="Tablet")
    med2_id = _create_medicine_and_return(client, admin_token, generic_name="Paracetamol", strength="250mg", dosage_form="Tablet")

    response = client.patch(
        f"/medicines/{med2_id}",
        json={"strength": "500mg"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 409


def test_update_inactive_medicine_returns_400(client, admin_token):
    medicine_id = _create_medicine_and_return(client, admin_token)

    client.patch(
        f"/medicines/{medicine_id}",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    response = client.patch(
        f"/medicines/{medicine_id}",
        json={"description": "Should fail"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400
    assert "inactive" in response.json()["detail"].lower()


def test_create_medicine_empty_generic_name_returns_422(client, admin_token):
    response = _create_medicine(client, admin_token, generic_name="")
    assert response.status_code == 422


# --- Search ---

def test_search_medicines_by_generic_name(client, admin_token):
    _create_medicine_and_return(client, admin_token)

    response = client.get(
        "/medicines/search?q=amoxi",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1
    assert response.json()[0]["generic_name"] == "Amoxicillin"


def test_search_medicines_by_brand_name(client, admin_token):
    _create_medicine_and_return(client, admin_token)

    response = client.get(
        "/medicines/search?q=amoxil",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_search_medicines_case_insensitive(client, admin_token):
    _create_medicine_and_return(client, admin_token)

    response = client.get(
        "/medicines/search?q=AMOXI",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_search_medicines_no_match_returns_empty(client, admin_token):
    response = client.get(
        "/medicines/search?q=nonexistent",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json() == []


def test_search_medicines_empty_query_returns_422(client, admin_token):
    response = client.get(
        "/medicines/search?q=",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


def test_doctor_can_search_medicines(client, admin_token, doctor_token):
    _create_medicine_and_return(client, admin_token)

    response = client.get(
        "/medicines/search?q=amoxi",
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert response.status_code == 200


# --- Filtering ---

def test_filter_medicines_by_generic_name(client, admin_token):
    _create_medicine_and_return(client, admin_token)
    _create_medicine_and_return(client, admin_token, generic_name="Paracetamol", brand_name="Tylenol", strength="500mg", dosage_form="Tablet", route="Oral")

    response = client.get(
        "/medicines?generic_name=amoxi",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["generic_name"] == "Amoxicillin"


def test_filter_medicines_by_manufacturer(client, admin_token):
    _create_medicine_and_return(client, admin_token)
    _create_medicine_and_return(client, admin_token, generic_name="Paracetamol", brand_name="Tylenol", manufacturer="J&J", strength="500mg", dosage_form="Tablet", route="Oral")

    response = client.get(
        "/medicines?manufacturer=J%26J",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_filter_medicines_by_drug_class(client, admin_token):
    _create_medicine_and_return(client, admin_token)

    response = client.get(
        "/medicines?drug_class=penicillin",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_filter_medicines_by_dosage_form(client, admin_token):
    _create_medicine_and_return(client, admin_token, dosage_form="Capsule")

    response = client.get(
        "/medicines?dosage_form=Capsule",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_filter_medicines_by_route(client, admin_token):
    _create_medicine_and_return(client, admin_token)

    response = client.get(
        "/medicines?route=Oral",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_filter_medicines_by_is_active(client, admin_token):
    _create_medicine_and_return(client, admin_token)

    response = client.get(
        "/medicines?is_active=true",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_filter_medicines_combination(client, admin_token):
    _create_medicine_and_return(client, admin_token)
    _create_medicine_and_return(client, admin_token, generic_name="Paracetamol", brand_name="Tylenol", strength="500mg", dosage_form="Tablet", route="Oral", drug_class="Analgesic")

    response = client.get(
        "/medicines?dosage_form=Tablet&route=Oral",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 2


# --- Pagination ---

def test_pagination_skip(client, admin_token):
    _create_medicine_and_return(client, admin_token, generic_name="MedicineA", brand_name="A", strength="10mg", dosage_form="Tablet", route="Oral")
    _create_medicine_and_return(client, admin_token, generic_name="MedicineB", brand_name="B", strength="20mg", dosage_form="Tablet", route="Oral")

    response = client.get(
        "/medicines?skip=1",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_pagination_limit(client, admin_token):
    _create_medicine_and_return(client, admin_token, generic_name="MedicineA", brand_name="A", strength="10mg", dosage_form="Tablet", route="Oral")
    _create_medicine_and_return(client, admin_token, generic_name="MedicineB", brand_name="B", strength="20mg", dosage_form="Tablet", route="Oral")

    response = client.get(
        "/medicines?limit=1",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_search_pagination(client, admin_token):
    _create_medicine_and_return(client, admin_token, generic_name="MedicineA", brand_name="BrandX", strength="10mg", dosage_form="Tablet", route="Oral")
    _create_medicine_and_return(client, admin_token, generic_name="MedicineB", brand_name="BrandX", strength="20mg", dosage_form="Tablet", route="Oral")

    response = client.get(
        "/medicines/search?q=BrandX&limit=1",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
