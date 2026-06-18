def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


def test_auth_login(client):
    client.post(
        "/auth/register",
        json={
            "email": "logintest@test.com",
            "password": "testpass123",
            "role": "patient",
        },
    )
    response = client.post(
        "/auth/login",
        json={"email": "logintest@test.com", "password": "testpass123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_users_me(client, doctor_token):
    response = client.get("/users/me", headers={"Authorization": f"Bearer {doctor_token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "doctor@test.com"
    assert data["role"] == "doctor"


def test_doctors_me_without_profile_returns_404(client, doctor_token):
    response = client.get("/doctors/me", headers={"Authorization": f"Bearer {doctor_token}"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Doctor profile not found"


def test_doctors_me_with_profile(client, doctor_with_profile):
    response = client.get("/doctors/me", headers={"Authorization": f"Bearer {doctor_with_profile}"})
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Dr Test"
    assert data["specialization"] == "Cardiology"


def test_patients_me_without_profile_returns_404(client, patient_token):
    response = client.get("/patients/me", headers={"Authorization": f"Bearer {patient_token}"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Patient profile not found"


def test_patients_me_with_profile(client, patient_with_profile):
    response = client.get("/patients/me", headers={"Authorization": f"Bearer {patient_with_profile}"})
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Pat Test"


def test_get_visits_returns_empty_list(client, doctor_token):
    response = client.get("/visits", headers={"Authorization": f"Bearer {doctor_token}"})
    assert response.status_code == 200
    assert response.json() == []


def test_profile_complete_doctor(client):
    client.post(
        "/auth/register",
        json={
            "email": "profile_doc@test.com",
            "password": "testpass123",
            "role": "doctor",
        },
    )
    login_resp = client.post(
        "/auth/login",
        json={"email": "profile_doc@test.com", "password": "testpass123"},
    )
    token = login_resp.json()["access_token"]

    response = client.post(
        "/profile/complete",
        json={
            "full_name": "Dr Profile",
            "phone_number": "3333333333",
            "specialization": "Neurology",
            "clinic_name": "Neuro Clinic",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Dr Profile"
    assert data["specialization"] == "Neurology"


def test_profile_complete_patient(client):
    client.post(
        "/auth/register",
        json={
            "email": "profile_pat@test.com",
            "password": "testpass123",
            "role": "patient",
        },
    )
    login_resp = client.post(
        "/auth/login",
        json={"email": "profile_pat@test.com", "password": "testpass123"},
    )
    token = login_resp.json()["access_token"]

    response = client.post(
        "/profile/complete",
        json={
            "full_name": "Pat Profile",
            "phone_number": "4444444444",
            "date_of_birth": "1995-05-15",
            "gender": "male",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Pat Profile"
    assert data["gender"] == "male"


def test_profile_complete_duplicate_returns_409(client):
    client.post(
        "/auth/register",
        json={
            "email": "dup_test@test.com",
            "password": "testpass123",
            "role": "doctor",
        },
    )
    login_resp = client.post(
        "/auth/login",
        json={"email": "dup_test@test.com", "password": "testpass123"},
    )
    token = login_resp.json()["access_token"]

    client.post(
        "/profile/complete",
        json={
            "full_name": "Dr Dup",
            "phone_number": "5555555555",
            "specialization": "General",
            "clinic_name": "Dup Clinic",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.post(
        "/profile/complete",
        json={
            "full_name": "Dr Dup",
            "phone_number": "5555555555",
            "specialization": "General",
            "clinic_name": "Dup Clinic",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Profile already completed"
