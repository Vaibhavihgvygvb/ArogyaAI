import datetime


def _get_doctor_id(client, token):
    resp = client.get("/doctors/me", headers={"Authorization": f"Bearer {token}"})
    return resp.json()["id"]


def _get_patient_id(client, token):
    resp = client.get("/patients/me", headers={"Authorization": f"Bearer {token}"})
    return resp.json()["id"]


def _create_appointment(client, token, doctor_id, patient_id, date="2099-06-20", time="10:30:00", reason="Test"):
    return client.post(
        "/appointments",
        json={
            "doctor_id": doctor_id,
            "patient_id": patient_id,
            "appointment_date": date,
            "appointment_time": time,
            "reason": reason,
        },
        headers={"Authorization": f"Bearer {token}"},
    )


def _update_appointment(client, token, appointment_id, **kwargs):
    return client.patch(
        f"/appointments/{appointment_id}",
        json=kwargs,
        headers={"Authorization": f"Bearer {token}"},
    )


def test_get_appointments_returns_empty_list(client, doctor_with_profile):
    response = client.get(
        "/appointments",
        headers={"Authorization": f"Bearer {doctor_with_profile}"},
    )
    assert response.status_code == 200
    assert response.json() == []


def test_create_appointment(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    response = _create_appointment(client, doctor_with_profile, doctor_id, patient_id)
    assert response.status_code == 201
    data = response.json()
    assert data["doctor_id"] == doctor_id
    assert data["patient_id"] == patient_id
    assert data["reason"] == "Test"
    assert data["status"] == "scheduled"
    assert "id" in data


def test_patient_can_create_appointment(client, patient_with_profile, doctor_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    response = _create_appointment(client, patient_with_profile, doctor_id, patient_id)
    assert response.status_code == 201


def test_get_appointment_by_id(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    create_resp = _create_appointment(client, doctor_with_profile, doctor_id, patient_id, reason="Follow-up")
    appointment_id = create_resp.json()["id"]
    response = client.get(
        f"/appointments/{appointment_id}",
        headers={"Authorization": f"Bearer {doctor_with_profile}"},
    )
    assert response.status_code == 200
    assert response.json()["reason"] == "Follow-up"


def test_patient_sees_only_own_appointments(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    _create_appointment(client, doctor_with_profile, doctor_id, patient_id)
    patient_list = client.get(
        "/appointments",
        headers={"Authorization": f"Bearer {patient_with_profile}"},
    )
    assert patient_list.status_code == 200
    assert len(patient_list.json()) == 1


def test_update_appointment(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    create_resp = _create_appointment(client, doctor_with_profile, doctor_id, patient_id, reason="Initial consult")
    appointment_id = create_resp.json()["id"]
    update_resp = _update_appointment(
        client, doctor_with_profile, appointment_id,
        status="confirmed", notes="Patient is doing well",
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["status"] == "confirmed"
    assert data["notes"] == "Patient is doing well"
    assert data["reason"] == "Initial consult"


def test_delete_appointment(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    create_resp = _create_appointment(client, doctor_with_profile, doctor_id, patient_id, reason="To be deleted")
    appointment_id = create_resp.json()["id"]
    delete_resp = client.delete(
        f"/appointments/{appointment_id}",
        headers={"Authorization": f"Bearer {doctor_with_profile}"},
    )
    assert delete_resp.status_code == 204
    get_resp = client.get(
        f"/appointments/{appointment_id}",
        headers={"Authorization": f"Bearer {doctor_with_profile}"},
    )
    assert get_resp.status_code == 404


# --- Rule 1: No past appointments ---

def test_create_appointment_past_date_returns_400(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    response = _create_appointment(
        client, doctor_with_profile, doctor_id, patient_id,
        date="2020-01-01", time="10:00:00",
    )
    assert response.status_code == 400
    assert "past" in response.json()["detail"].lower()


def test_reschedule_to_past_date_returns_400(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    create_resp = _create_appointment(client, doctor_with_profile, doctor_id, patient_id)
    appointment_id = create_resp.json()["id"]
    update_resp = _update_appointment(
        client, doctor_with_profile, appointment_id,
        appointment_date="2020-01-01",
    )
    assert update_resp.status_code == 400
    assert "past" in update_resp.json()["detail"].lower()


# --- Rule 2: Doctor double-booking ---

def test_create_appointment_double_booking_returns_409(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    _create_appointment(client, doctor_with_profile, doctor_id, patient_id)
    response = _create_appointment(
        client, doctor_with_profile, doctor_id, patient_id + 999,
        reason="Should conflict",
    )
    assert response.status_code == 409
    assert "already has an appointment" in response.json()["detail"].lower()


# --- Rule 3: Duplicate patient booking ---

def test_create_appointment_duplicate_patient_returns_409(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    _create_appointment(client, doctor_with_profile, doctor_id, patient_id)
    response = _create_appointment(
        client, doctor_with_profile, doctor_id, patient_id,
        reason="Should be duplicate",
    )
    assert response.status_code == 409
    assert "patient already has an appointment" in response.json()["detail"].lower()


# --- Rule 4: Completed appointments are immutable ---

def _walk_to_completed(client, token, appointment_id):
    _update_appointment(client, token, appointment_id, status="confirmed")
    _update_appointment(client, token, appointment_id, status="checked_in")
    _update_appointment(client, token, appointment_id, status="in_progress")
    _update_appointment(client, token, appointment_id, status="completed")


def test_update_completed_appointment_returns_409(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    create_resp = _create_appointment(client, doctor_with_profile, doctor_id, patient_id)
    appointment_id = create_resp.json()["id"]
    _walk_to_completed(client, doctor_with_profile, appointment_id)
    update_resp = _update_appointment(client, doctor_with_profile, appointment_id, notes="Should fail")
    assert update_resp.status_code == 409
    assert "completed" in update_resp.json()["detail"].lower()


def test_delete_completed_appointment_returns_409(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    create_resp = _create_appointment(client, doctor_with_profile, doctor_id, patient_id)
    appointment_id = create_resp.json()["id"]
    _walk_to_completed(client, doctor_with_profile, appointment_id)
    delete_resp = client.delete(
        f"/appointments/{appointment_id}",
        headers={"Authorization": f"Bearer {doctor_with_profile}"},
    )
    assert delete_resp.status_code == 409
    assert "completed" in delete_resp.json()["detail"].lower()


def test_status_change_on_completed_returns_409(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    create_resp = _create_appointment(client, doctor_with_profile, doctor_id, patient_id)
    appointment_id = create_resp.json()["id"]
    _walk_to_completed(client, doctor_with_profile, appointment_id)
    update_resp = _update_appointment(client, doctor_with_profile, appointment_id, status="cancelled")
    assert update_resp.status_code == 409
    assert "completed" in update_resp.json()["detail"].lower()


# --- Rule 5: Valid status transitions ---

def test_invalid_transition_scheduled_to_completed_returns_409(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    create_resp = _create_appointment(client, doctor_with_profile, doctor_id, patient_id)
    appointment_id = create_resp.json()["id"]
    update_resp = _update_appointment(client, doctor_with_profile, appointment_id, status="completed")
    assert update_resp.status_code == 409
    assert "transition" in update_resp.json()["detail"].lower()


def test_invalid_transition_confirmed_to_scheduled_returns_409(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    create_resp = _create_appointment(client, doctor_with_profile, doctor_id, patient_id)
    appointment_id = create_resp.json()["id"]
    _update_appointment(client, doctor_with_profile, appointment_id, status="confirmed")
    update_resp = _update_appointment(client, doctor_with_profile, appointment_id, status="scheduled")
    assert update_resp.status_code == 409
    assert "transition" in update_resp.json()["detail"].lower()


def test_invalid_transition_completed_to_scheduled_returns_409(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    create_resp = _create_appointment(client, doctor_with_profile, doctor_id, patient_id)
    appointment_id = create_resp.json()["id"]
    _walk_to_completed(client, doctor_with_profile, appointment_id)
    update_resp = _update_appointment(client, doctor_with_profile, appointment_id, status="scheduled")
    assert update_resp.status_code == 409


def test_valid_full_flow_through_all_states(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    create_resp = _create_appointment(client, doctor_with_profile, doctor_id, patient_id)
    appointment_id = create_resp.json()["id"]

    assert create_resp.json()["status"] == "scheduled"

    r = _update_appointment(client, doctor_with_profile, appointment_id, status="confirmed")
    assert r.status_code == 200 and r.json()["status"] == "confirmed"

    r = _update_appointment(client, doctor_with_profile, appointment_id, status="checked_in")
    assert r.status_code == 200 and r.json()["status"] == "checked_in"

    r = _update_appointment(client, doctor_with_profile, appointment_id, status="in_progress")
    assert r.status_code == 200 and r.json()["status"] == "in_progress"

    r = _update_appointment(client, doctor_with_profile, appointment_id, status="completed")
    assert r.status_code == 200 and r.json()["status"] == "completed"


def test_no_show_from_confirmed_allowed(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    create_resp = _create_appointment(client, doctor_with_profile, doctor_id, patient_id)
    appointment_id = create_resp.json()["id"]
    _update_appointment(client, doctor_with_profile, appointment_id, status="confirmed")
    r = _update_appointment(client, doctor_with_profile, appointment_id, status="no_show")
    assert r.status_code == 200
    assert r.json()["status"] == "no_show"


def test_cancel_from_scheduled_allowed(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    create_resp = _create_appointment(client, doctor_with_profile, doctor_id, patient_id)
    appointment_id = create_resp.json()["id"]
    r = _update_appointment(client, doctor_with_profile, appointment_id, status="cancelled")
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


# --- Rule 6: Cancel releases the slot ---

def test_cancel_and_rebook_same_slot(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    create_resp = _create_appointment(
        client, doctor_with_profile, doctor_id, patient_id,
        date="2099-07-01", time="14:00:00",
    )
    appointment_id = create_resp.json()["id"]
    _update_appointment(client, doctor_with_profile, appointment_id, status="cancelled")
    rebook_resp = _create_appointment(
        client, doctor_with_profile, doctor_id, patient_id,
        date="2099-07-01", time="14:00:00",
        reason="Rebook after cancel",
    )
    assert rebook_resp.status_code == 201


def test_completed_does_not_block_future_slot(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    create_resp = _create_appointment(
        client, doctor_with_profile, doctor_id, patient_id,
        date="2099-07-01", time="14:00:00",
    )
    appointment_id = create_resp.json()["id"]
    _walk_to_completed(client, doctor_with_profile, appointment_id)
    new_resp = _create_appointment(
        client, doctor_with_profile, doctor_id, patient_id,
        date="2099-07-01", time="14:00:00",
        reason="New booking after completion",
    )
    assert new_resp.status_code == 201


# --- Additional edge cases ---

def test_reschedule_to_valid_future_slot(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    create_resp = _create_appointment(
        client, doctor_with_profile, doctor_id, patient_id,
        date="2099-06-20", time="10:00:00",
    )
    appointment_id = create_resp.json()["id"]
    update_resp = _update_appointment(
        client, doctor_with_profile, appointment_id,
        appointment_date="2099-06-21", appointment_time="11:00:00",
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["appointment_date"] == "2099-06-21"
    assert data["appointment_time"] == "11:00:00"


def test_update_notes_only_no_validation_needed(client, doctor_with_profile, patient_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    create_resp = _create_appointment(client, doctor_with_profile, doctor_id, patient_id)
    appointment_id = create_resp.json()["id"]
    update_resp = _update_appointment(client, doctor_with_profile, appointment_id, notes="Just a note")
    assert update_resp.status_code == 200
    assert update_resp.json()["notes"] == "Just a note"


# --- Patient authorization ---

def test_patient_cancel_own_appointment(client, patient_with_profile, doctor_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    create_resp = _create_appointment(
        client, doctor_with_profile, doctor_id, patient_id,
        date="2099-06-20", time="10:30:00",
    )
    appointment_id = create_resp.json()["id"]
    cancel_resp = client.patch(
        f"/appointments/{appointment_id}",
        json={"status": "cancelled"},
        headers={"Authorization": f"Bearer {patient_with_profile}"},
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"


def test_patient_cannot_update_other_fields(client, patient_with_profile, doctor_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    create_resp = _create_appointment(
        client, doctor_with_profile, doctor_id, patient_id,
        date="2099-06-20", time="10:30:00",
    )
    appointment_id = create_resp.json()["id"]
    resp = client.patch(
        f"/appointments/{appointment_id}",
        json={"notes": "Trying to change notes"},
        headers={"Authorization": f"Bearer {patient_with_profile}"},
    )
    assert resp.status_code == 403


def test_patient_cannot_update_status_to_confirmed(client, patient_with_profile, doctor_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    create_resp = _create_appointment(
        client, doctor_with_profile, doctor_id, patient_id,
        date="2099-06-20", time="10:30:00",
    )
    appointment_id = create_resp.json()["id"]
    resp = client.patch(
        f"/appointments/{appointment_id}",
        json={"status": "confirmed"},
        headers={"Authorization": f"Bearer {patient_with_profile}"},
    )
    assert resp.status_code == 403


def test_patient_cannot_cancel_others_appointment(client, patient_with_profile, doctor_with_profile):
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    create_resp = _create_appointment(
        client, doctor_with_profile, doctor_id, patient_id,
        date="2099-06-20", time="10:30:00",
    )
    appointment_id = create_resp.json()["id"]
    other_patient_resp = client.post(
        "/auth/register",
        json={"email": "other_patient@test.com", "password": "testpass123", "role": "patient"},
    )
    other_login = client.post(
        "/auth/login",
        json={"email": "other_patient@test.com", "password": "testpass123"},
    )
    other_token = other_login.json()["access_token"]
    other_patient_resp = client.patch(
        f"/appointments/{appointment_id}",
        json={"status": "cancelled"},
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert other_patient_resp.status_code == 403


def test_patient_cannot_cancel_past_appointment(client, db, patient_with_profile, doctor_with_profile):
    from datetime import date, time
    from app.models.appointment import Appointment
    doctor_id = _get_doctor_id(client, doctor_with_profile)
    patient_id = _get_patient_id(client, patient_with_profile)
    create_resp = _create_appointment(
        client, doctor_with_profile, doctor_id, patient_id,
        date="2099-06-20", time="10:00:00",
    )
    appointment_id = create_resp.json()["id"]
    appt = db.get(Appointment, appointment_id)
    appt.appointment_date = date(2020, 1, 1)
    appt.appointment_time = time(10, 0, 0)
    db.commit()
    cancel_resp = client.patch(
        f"/appointments/{appointment_id}",
        json={"status": "cancelled"},
        headers={"Authorization": f"Bearer {patient_with_profile}"},
    )
    assert cancel_resp.status_code == 400
    assert "before they begin" in cancel_resp.json()["detail"].lower()
