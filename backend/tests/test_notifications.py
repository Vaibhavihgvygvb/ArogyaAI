def _create_notification(client, token, **overrides):
    payload = {
        "user_id": 1,
        "title": "Test Notification",
        "message": "This is a test notification",
        "notification_type": "info",
        "priority": "medium",
    }
    payload.update(overrides)
    return client.post(
        "/notifications",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )


def _create_sample_notifications(client, admin_token, user_id: int, count: int = 3):
    ids = []
    for i in range(count):
        resp = _create_notification(
            client, admin_token,
            user_id=user_id,
            title=f"Notification {i}",
            message=f"Message {i}",
            notification_type="info" if i % 2 == 0 else "warning",
            priority="low" if i == 0 else ("medium" if i == 1 else "high"),
        )
        ids.append(resp.json()["id"])
    return ids


# --- CRUD ---

def test_create_notification(client, admin_token):
    response = _create_notification(client, admin_token, user_id=1)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Notification"
    assert data["message"] == "This is a test notification"
    assert data["notification_type"] == "info"
    assert data["priority"] == "medium"
    assert data["status"] == "unread"
    assert data["is_read"] is False
    assert data["user_id"] == 1


def test_create_notification_non_admin_fails(client, doctor_token, patient_token):
    response = _create_notification(client, doctor_token, user_id=1)
    assert response.status_code == 403

    response = _create_notification(client, patient_token, user_id=1)
    assert response.status_code == 403


def test_create_notification_user_not_found(client, admin_token):
    response = _create_notification(client, admin_token, user_id=9999)
    assert response.status_code == 404


def test_create_notification_duplicate(client, admin_token):
    _create_notification(client, admin_token, user_id=1)
    response = _create_notification(client, admin_token, user_id=1)
    assert response.status_code == 409


def test_get_notification(client, admin_token):
    create_resp = _create_notification(client, admin_token, user_id=1)
    notification_id = create_resp.json()["id"]

    response = client.get(
        f"/notifications/{notification_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == notification_id


def test_get_notification_not_found(client, admin_token):
    response = client.get(
        "/notifications/9999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


# --- Ownership ---

def test_patient_sees_own_notification(client, admin_token, patient_token):
    create_resp = _create_notification(client, admin_token, user_id=2)
    notification_id = create_resp.json()["id"]

    response = client.get(
        f"/notifications/{notification_id}",
        headers={"Authorization": f"Bearer {patient_token}"},
    )
    assert response.status_code == 200


def test_patient_cannot_see_other_notification(client, admin_token, patient_token, doctor_token):
    create_resp = _create_notification(client, admin_token, user_id=2)
    notification_id = create_resp.json()["id"]

    response = client.get(
        f"/notifications/{notification_id}",
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert response.status_code == 403


def test_admin_sees_all_notifications(client, admin_token, patient_token):
    create_resp = _create_notification(client, admin_token, user_id=2)
    notification_id = create_resp.json()["id"]

    response = client.get(
        f"/notifications/{notification_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200


# --- List / Pagination ---

def test_list_notifications_empty(client, doctor_token):
    response = client.get(
        "/notifications",
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_list_notifications_pagination(client, admin_token):
    user_id = 1
    ids = _create_sample_notifications(client, admin_token, user_id, count=5)

    response = client.get(
        "/notifications?skip=0&limit=2",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5


def test_list_notifications_filter_by_type(client, admin_token):
    user_id = 1
    _create_sample_notifications(client, admin_token, user_id, count=5)

    response = client.get(
        "/notifications?notification_type=warning",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    for item in data["items"]:
        assert item["notification_type"] == "warning"


def test_list_notifications_filter_by_priority(client, admin_token):
    user_id = 1
    _create_sample_notifications(client, admin_token, user_id, count=5)

    response = client.get(
        "/notifications?priority=high",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    for item in data["items"]:
        assert item["priority"] == "high"


# --- Mark as Read ---

def test_mark_notification_read(client, admin_token):
    create_resp = _create_notification(client, admin_token, user_id=1)
    notification_id = create_resp.json()["id"]

    response = client.patch(
        f"/notifications/{notification_id}/read",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "read"
    assert response.json()["is_read"] is True

    get_resp = client.get(
        f"/notifications/{notification_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_resp.json()["status"] == "read"


def test_mark_notification_read_unauthorized(client, admin_token, patient_token, doctor_token):
    create_resp = _create_notification(client, admin_token, user_id=2)
    notification_id = create_resp.json()["id"]

    response = client.patch(
        f"/notifications/{notification_id}/read",
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert response.status_code == 403


def test_mark_notification_read_not_found(client, admin_token):
    response = client.patch(
        "/notifications/9999/read",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


# --- Mark All Read ---

def test_mark_all_read(client, admin_token):
    user_id = 1
    _create_sample_notifications(client, admin_token, user_id, count=3)

    response = client.patch(
        "/notifications/read-all",
        json={},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["marked_read"] == 3

    count_resp = client.get(
        "/notifications/unread-count",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert count_resp.json()["unread_count"] == 0


# --- Unread Count ---

def test_unread_count(client, admin_token):
    user_id = 1
    _create_sample_notifications(client, admin_token, user_id, count=3)

    response = client.get(
        "/notifications/unread-count",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["unread_count"] == 3


def test_unread_count_after_read(client, admin_token):
    user_id = 1
    ids = _create_sample_notifications(client, admin_token, user_id, count=3)

    client.patch(
        f"/notifications/{ids[0]}/read",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    response = client.get(
        "/notifications/unread-count",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["unread_count"] == 2


# --- Archive ---

def test_archive_notification(client, admin_token):
    create_resp = _create_notification(client, admin_token, user_id=1)
    notification_id = create_resp.json()["id"]

    response = client.patch(
        f"/notifications/{notification_id}/archive",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "archived"


def test_archived_notification_cannot_be_read(client, admin_token):
    create_resp = _create_notification(client, admin_token, user_id=1)
    notification_id = create_resp.json()["id"]

    client.patch(
        f"/notifications/{notification_id}/archive",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    response = client.patch(
        f"/notifications/{notification_id}/read",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400


def test_patient_can_archive_own_notification(client, admin_token, patient_token):
    create_resp = _create_notification(client, admin_token, user_id=2)
    notification_id = create_resp.json()["id"]

    response = client.patch(
        f"/notifications/{notification_id}/archive",
        headers={"Authorization": f"Bearer {patient_token}"},
    )
    assert response.status_code == 200


def test_archive_notification_not_found(client, admin_token):
    response = client.patch(
        "/notifications/9999/archive",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


# --- Delete ---

def test_delete_notification_admin_only(client, admin_token, doctor_token):
    create_resp = _create_notification(client, admin_token, user_id=1)
    notification_id = create_resp.json()["id"]

    response = client.delete(
        f"/notifications/{notification_id}",
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert response.status_code == 403

    response = client.delete(
        f"/notifications/{notification_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204


def test_delete_notification_not_found(client, admin_token):
    response = client.delete(
        "/notifications/9999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


# --- Update ---

def test_update_notification_admin_only(client, admin_token, doctor_token):
    create_resp = _create_notification(client, admin_token, user_id=1)
    notification_id = create_resp.json()["id"]

    response = client.patch(
        f"/notifications/{notification_id}",
        json={"title": "Updated Title"},
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert response.status_code == 403

    response = client.patch(
        f"/notifications/{notification_id}",
        json={"title": "Updated Title"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Title"


def test_update_archived_notification_fails(client, admin_token):
    create_resp = _create_notification(client, admin_token, user_id=1)
    notification_id = create_resp.json()["id"]

    client.patch(
        f"/notifications/{notification_id}/archive",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    response = client.patch(
        f"/notifications/{notification_id}",
        json={"title": "Updated Title"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400


# --- Unauthenticated ---

def test_unauthorized_access_returns_401(client):
    response = client.get("/notifications")
    assert response.status_code == 401

    response = client.post("/notifications", json={})
    assert response.status_code == 401

    response = client.get("/notifications/1")
    assert response.status_code == 401


# --- Event Hooks (Service Level) ---

def test_notify_appointment_created_creates_notification(db, admin_token):
    from app.services.notification_service import NotificationService
    from app.schemas.notification import NotificationCreate
    from app.models.enums import NotificationType

    user_id = 1
    notification = NotificationService.notify_appointment_created(
        db, user_id, appointment_id=123
    )
    assert notification is not None
    assert notification.title == "Appointment Created"
    assert notification.notification_type == NotificationType.APPOINTMENT


def test_notify_appointment_cancelled_creates_notification(db, admin_token):
    from app.services.notification_service import NotificationService
    from app.models.enums import NotificationType

    notification = NotificationService.notify_appointment_cancelled(db, 1, appointment_id=123)
    assert notification is not None
    assert notification.title == "Appointment Cancelled"
    assert notification.notification_type == NotificationType.APPOINTMENT
    assert notification.priority.value == "high"


def test_notify_ai_alert_creates_notification(db, admin_token):
    from app.services.notification_service import NotificationService
    from app.models.enums import NotificationType

    notification = NotificationService.notify_ai_alert(
        db, 1, message="Critical lab value detected"
    )
    assert notification is not None
    assert notification.title == "AI Alert"
    assert notification.notification_type == NotificationType.AI


# --- Edge Cases ---

def test_create_notification_with_metadata(client, admin_token):
    response = _create_notification(
        client, admin_token,
        user_id=1,
        metadata_json='{"source": "test", "ref_id": 42}',
        action_url="/appointments/123",
    )
    assert response.status_code == 201
    data = response.json()
    assert data["metadata_json"] == '{"source": "test", "ref_id": 42}'
    assert data["action_url"] == "/appointments/123"
