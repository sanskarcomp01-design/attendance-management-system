import base64
import json

from app.models import ClassGroup, Subject
from app.services.qr_service import make_token, verify_token
from tests.conftest import auth_header, login


def test_student_cannot_open_admin_stats(client):
    token = login(client, "student@test.edu", "Student@12345")
    response = client.get("/api/admin/stats", headers=auth_header(token))
    assert response.status_code == 403


def test_teacher_can_open_and_close_session(client, app):
    token = login(client, "teacher@test.edu", "Teacher@12345")
    with app.app_context():
        subject_id = Subject.query.filter_by(code="214443").first().id
    opened = client.post("/api/teacher/sessions", json={"subject_id": subject_id}, headers=auth_header(token))
    assert opened.status_code == 201
    session_id = opened.get_json()["session"]["id"]
    qr = client.get(f"/api/teacher/sessions/{session_id}/qr", headers=auth_header(token))
    assert qr.status_code == 200
    assert qr.get_json()["token"]
    assert qr.get_json()["image_base64"]
    assert qr.get_json()["ttl_seconds"] > 0
    closed = client.post(f"/api/teacher/sessions/{session_id}/close", headers=auth_header(token))
    assert closed.status_code == 200
    assert closed.get_json()["session"]["is_open"] is False


def test_student_cannot_start_session(client, app):
    token = login(client, "student@test.edu", "Student@12345")
    with app.app_context():
        subject_id = Subject.query.filter_by(code="214443").first().id
    response = client.post("/api/teacher/sessions", json={"subject_id": subject_id}, headers=auth_header(token))
    assert response.status_code == 403


def test_qr_token_roundtrip(app):
    with app.app_context():
        token = make_token(42)
        ok, message, payload = verify_token(token)
        assert ok is True
        assert payload["session_id"] == 42
        assert message == "ok"


def test_qr_token_expires_outside_accepted_window(app, monkeypatch):
    import app.services.qr_service as qr_service

    with app.app_context():
        token = make_token(42, window=100)
        monkeypatch.setattr(qr_service, "current_window", lambda _ttl=None: 102)
        ok, message, payload = verify_token(token)
        assert ok is False
        assert message.startswith("This QR code has expired.")
        assert payload is None


def test_qr_token_accepts_previous_window_but_not_future_window(app, monkeypatch):
    import app.services.qr_service as qr_service

    with app.app_context():
        monkeypatch.setattr(qr_service, "current_window", lambda _ttl=None: 100)
        previous_ok, _, _ = verify_token(make_token(42, window=99))
        future_ok, future_message, _ = verify_token(make_token(42, window=101))
        assert previous_ok is True
        assert future_ok is False
        assert future_message.startswith("This QR code has expired.")


def test_qr_token_rejects_tampering(app):
    with app.app_context():
        token = make_token(42)
        ok, message, payload = verify_token(token + "tampered")
        assert ok is False
        assert payload is None
        assert message in {"This QR code is not valid.", "This QR code failed security checks."}


def test_qr_token_rejects_non_string_signature(app):
    payload = base64.urlsafe_b64encode(
        json.dumps({"sid": 42, "w": 100, "t": []}).encode("utf-8")
    ).decode("utf-8")
    with app.app_context():
        ok, message, decoded = verify_token(payload)
        assert ok is False
        assert message == "This QR code is not valid."
        assert decoded is None


def test_admin_creates_user(client):
    token = login(client, "admin@test.edu", "Admin@12345")
    response = client.post(
        "/api/admin/users",
        json={
            "full_name": "New Teacher",
            "email": "new.teacher@test.edu",
            "password": "Teacher@12345",
            "role": "teacher",
            "employee_id": "T9",
        },
        headers=auth_header(token),
    )
    assert response.status_code == 201
    assert response.get_json()["user"]["role"] == "teacher"


def test_admin_can_edit_class_and_subject(client, app):
    admin = login(client, "admin@test.edu", "Admin@12345")
    headers = auth_header(admin)
    with app.app_context():
        group_id = ClassGroup.query.filter_by(name="SE-IT-A").first().id
        subject_id = Subject.query.filter_by(code="214443").first().id

    class_response = client.patch(
        f"/api/admin/classes/{group_id}",
        json={"name": "SE-IT-B", "division": "B"},
        headers=headers,
    )
    assert class_response.status_code == 200
    assert class_response.get_json()["class"]["name"] == "SE-IT-B"
    assert class_response.get_json()["class"]["division"] == "B"

    subject_response = client.patch(
        f"/api/admin/subjects/{subject_id}",
        json={"code": "214999", "name": "Updated DSA", "class_group_id": group_id},
        headers=headers,
    )
    assert subject_response.status_code == 200
    assert subject_response.get_json()["subject"]["code"] == "214999"
    assert subject_response.get_json()["subject"]["name"] == "Updated DSA"


def test_non_admin_cannot_edit_class_or_subject(client, app):
    teacher = login(client, "teacher@test.edu", "Teacher@12345")
    with app.app_context():
        group_id = ClassGroup.query.first().id
        subject_id = Subject.query.first().id
    class_response = client.patch(
        f"/api/admin/classes/{group_id}",
        json={"name": "Not Allowed"},
        headers=auth_header(teacher),
    )
    subject_response = client.patch(
        f"/api/admin/subjects/{subject_id}",
        json={"name": "Not Allowed"},
        headers=auth_header(teacher),
    )
    assert class_response.status_code == 403
    assert subject_response.status_code == 403


def test_teacher_cannot_start_session_for_other_teachers_subject(client, app):
    token = login(client, "teacher@test.edu", "Teacher@12345")
    with app.app_context():
        unassigned = Subject(code="214441", name="Other Teacher Subject", class_group_id=1, teacher_id=None)
        from app.extensions import db

        db.session.add(unassigned)
        db.session.commit()
        subject_id = unassigned.id
    response = client.post(
        "/api/teacher/sessions",
        json={"subject_id": subject_id},
        headers=auth_header(token),
    )
    assert response.status_code == 403


def test_invalid_subject_class_id_is_reported(client, app):
    admin = login(client, "admin@test.edu", "Admin@12345")
    response = client.post(
        "/api/admin/subjects",
        json={"code": "219999", "name": "Invalid Class", "class_group_id": "not-a-number"},
        headers=auth_header(admin),
    )
    assert response.status_code == 400
