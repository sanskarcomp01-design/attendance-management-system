from io import BytesIO

from app.extensions import db
from app.models import Enrollment, FaceProfile, Subject, User
from app.services.qr_service import make_token
from tests.conftest import auth_header, login


def _open_session(client, app):
    token = login(client, "teacher@test.edu", "Teacher@12345")
    with app.app_context():
        subject_id = Subject.query.filter_by(code="214443").first().id
        student_id = User.query.filter_by(email="student@test.edu").first().id
    opened = client.post("/api/teacher/sessions", json={"subject_id": subject_id}, headers=auth_header(token))
    session_id = opened.get_json()["session"]["id"]
    return token, session_id, student_id, subject_id


def test_teacher_manual_mark_present(client, app):
    token, session_id, student_id, _subject_id = _open_session(client, app)
    response = client.post(
        f"/api/teacher/sessions/{session_id}/mark",
        json={"student_id": student_id, "status": "present", "reason": "Phone camera failed"},
        headers=auth_header(token),
    )
    assert response.status_code == 200
    body = response.get_json()["record"]
    assert body["status"] == "present"
    assert body["method"] == "manual"
    assert body["note"] == "Phone camera failed"

    roster = client.get(f"/api/teacher/sessions/{session_id}", headers=auth_header(token))
    row = next(r for r in roster.get_json()["roster"] if r["student_id"] == student_id)
    assert row["status"] == "present"
    assert row["method"] == "manual"


def test_teacher_session_shows_qr_and_manual_present_counts(client, app, monkeypatch):
    from app.services import face_service

    teacher, session_id, student_id, subject_id = _open_session(client, app)
    with app.app_context():
        other = User.query.filter_by(email="other@test.edu").first()
        db.session.add(Enrollment(student_id=other.id, subject_id=subject_id))
        db.session.add(FaceProfile(user_id=other.id, embedding=b"test-embedding"))
        db.session.commit()
        other_id = other.id

    manual = client.post(
        f"/api/teacher/sessions/{session_id}/mark",
        json={"student_id": student_id, "status": "present", "reason": "Teacher verified in class"},
        headers=auth_header(teacher),
    )
    assert manual.status_code == 200
    monkeypatch.setattr(face_service, "verify_face_liveness", lambda *_args: (True, 0.95, True))
    with app.app_context():
        qr_token = make_token(session_id)
    student_token = login(client, "other@test.edu", "Student@12345")
    challenge = client.post(
        "/api/student/attendance/challenge",
        json={"token": qr_token},
        headers=auth_header(student_token),
    )
    assert challenge.status_code == 200
    qr_response = client.post(
        "/api/student/attendance/mark",
        data={
            "token": qr_token,
            "challenge_id": challenge.get_json()["challenge_id"],
            "neutral_image": (BytesIO(b"neutral-image"), "neutral.jpg"),
            "turned_image": (BytesIO(b"turned-image"), "turned.jpg"),
        },
        headers=auth_header(student_token),
        content_type="multipart/form-data",
    )
    assert qr_response.status_code == 200

    detail = client.get(f"/api/teacher/sessions/{session_id}", headers=auth_header(teacher))
    session = detail.get_json()["session"]
    assert session["present_count"] == 2
    assert session["attendance_by_method"] == {"qr_face": 1, "manual": 1}
    roster = {row["student_id"]: row for row in detail.get_json()["roster"]}
    assert roster[student_id]["method"] == "manual"
    assert roster[other_id]["method"] == "qr_face"


def test_manual_mark_requires_reason(client, app):
    token, session_id, student_id, _subject_id = _open_session(client, app)
    response = client.post(
        f"/api/teacher/sessions/{session_id}/mark",
        json={"student_id": student_id, "status": "present", "reason": "no"},
        headers=auth_header(token),
    )
    assert response.status_code == 400


def test_manual_mark_rejects_non_numeric_student_id(client, app):
    token, session_id, _student_id, _subject_id = _open_session(client, app)
    response = client.post(
        f"/api/teacher/sessions/{session_id}/mark",
        json={"student_id": "not-a-number", "status": "present", "reason": "Phone camera failed"},
        headers=auth_header(token),
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "Valid student_id is required."


def test_student_cannot_manual_mark(client, app):
    _token, session_id, student_id, _subject_id = _open_session(client, app)
    student_token = login(client, "student@test.edu", "Student@12345")
    response = client.post(
        f"/api/teacher/sessions/{session_id}/mark",
        json={"student_id": student_id, "status": "present", "reason": "Trying to cheat"},
        headers=auth_header(student_token),
    )
    assert response.status_code == 403


def test_teacher_cannot_mark_unenrolled_student(client, app):
    token, session_id, _student_id, _subject_id = _open_session(client, app)
    with app.app_context():
        other_id = User.query.filter_by(email="other@test.edu").first().id
    response = client.post(
        f"/api/teacher/sessions/{session_id}/mark",
        json={"student_id": other_id, "status": "present", "reason": "Guest student"},
        headers=auth_header(token),
    )
    assert response.status_code == 400


def test_subject_report_eligibility_and_csv(client, app):
    token, session_id, student_id, subject_id = _open_session(client, app)
    client.post(
        f"/api/teacher/sessions/{session_id}/mark",
        json={"student_id": student_id, "status": "present", "reason": "Present in class"},
        headers=auth_header(token),
    )
    admin = login(client, "admin@test.edu", "Admin@12345")
    report = client.get(f"/api/reports/subject/{subject_id}", headers=auth_header(admin))
    assert report.status_code == 200
    data = report.get_json()
    assert data["eligibility_percent"] == 75
    row = next(r for r in data["rows"] if r["student_id"] == student_id)
    assert row["present"] == 1
    assert row["eligible"] is True

    csv_response = client.get(f"/api/reports/subject/{subject_id}/csv", headers=auth_header(admin))
    assert csv_response.status_code == 200
    assert "text/csv" in csv_response.headers["Content-Type"]
    text = csv_response.get_data(as_text=True)
    assert "full_name" in text
    assert "Student" in text
    assert "yes" in text


def test_subject_report_handles_no_sessions(client, app):
    admin = login(client, "admin@test.edu", "Admin@12345")
    with app.app_context():
        subject_id = Subject.query.filter_by(code="214443").first().id
        student_id = User.query.filter_by(email="student@test.edu").first().id
    response = client.get(f"/api/reports/subject/{subject_id}", headers=auth_header(admin))
    assert response.status_code == 200
    row = next(r for r in response.get_json()["rows"] if r["student_id"] == student_id)
    assert row["total_sessions"] == 0
    assert row["present"] == 0
    assert row["percent"] == 0
    assert row["eligible"] is False


def test_subject_report_marks_below_threshold_ineligible(client, app):
    teacher, session_id, student_id, subject_id = _open_session(client, app)
    present = client.post(
        f"/api/teacher/sessions/{session_id}/mark",
        json={"student_id": student_id, "status": "present", "reason": "Attended first lecture"},
        headers=auth_header(teacher),
    )
    assert present.status_code == 200
    client.post(f"/api/teacher/sessions/{session_id}/close", headers=auth_header(teacher))
    next_session = client.post(
        "/api/teacher/sessions",
        json={"subject_id": subject_id},
        headers=auth_header(teacher),
    )
    next_id = next_session.get_json()["session"]["id"]
    absent = client.post(
        f"/api/teacher/sessions/{next_id}/mark",
        json={"student_id": student_id, "status": "absent", "reason": "Missed second lecture"},
        headers=auth_header(teacher),
    )
    assert absent.status_code == 200

    admin = login(client, "admin@test.edu", "Admin@12345")
    response = client.get(f"/api/reports/subject/{subject_id}", headers=auth_header(admin))
    row = next(r for r in response.get_json()["rows"] if r["student_id"] == student_id)
    assert row["present"] == 1
    assert row["total_sessions"] == 2
    assert row["percent"] == 50.0
    assert row["eligible"] is False


def test_student_overall_attendance_is_weighted_across_subjects(client, app):
    teacher, first_session_id, student_id, first_subject_id = _open_session(client, app)
    first_present = client.post(
        f"/api/teacher/sessions/{first_session_id}/mark",
        json={"student_id": student_id, "status": "present", "reason": "Attended lecture one"},
        headers=auth_header(teacher),
    )
    assert first_present.status_code == 200
    client.post(f"/api/teacher/sessions/{first_session_id}/close", headers=auth_header(teacher))

    second_session = client.post(
        "/api/teacher/sessions",
        json={"subject_id": first_subject_id},
        headers=auth_header(teacher),
    )
    second_session_id = second_session.get_json()["session"]["id"]
    second_absent = client.post(
        f"/api/teacher/sessions/{second_session_id}/mark",
        json={"student_id": student_id, "status": "absent", "reason": "Absent from lecture two"},
        headers=auth_header(teacher),
    )
    assert second_absent.status_code == 200
    client.post(f"/api/teacher/sessions/{second_session_id}/close", headers=auth_header(teacher))

    with app.app_context():
        first_subject = db.session.get(Subject, first_subject_id)
        other_subject = Subject(
            code="214445",
            name="Computer Networks",
            class_group_id=first_subject.class_group_id,
            teacher_id=first_subject.teacher_id,
        )
        db.session.add(other_subject)
        db.session.flush()
        db.session.add(Enrollment(student_id=student_id, subject_id=other_subject.id))
        db.session.commit()
        other_subject_id = other_subject.id

    other_session = client.post(
        "/api/teacher/sessions",
        json={"subject_id": other_subject_id},
        headers=auth_header(teacher),
    )
    other_session_id = other_session.get_json()["session"]["id"]
    other_present = client.post(
        f"/api/teacher/sessions/{other_session_id}/mark",
        json={"student_id": student_id, "status": "present", "reason": "Attended network lecture"},
        headers=auth_header(teacher),
    )
    assert other_present.status_code == 200

    student = login(client, "student@test.edu", "Student@12345")
    response = client.get("/api/student/attendance", headers=auth_header(student))
    overall = response.get_json()["overall"]
    assert overall == {"present": 2, "total_sessions": 3, "percent": 66.7}
    percentages = {row["subject_id"]: row["percent"] for row in response.get_json()["summary"]}
    assert percentages[first_subject_id] == 50.0
    assert percentages[other_subject_id] == 100.0


def test_teacher_cannot_download_other_subject_csv(client, app):
    teacher = login(client, "teacher@test.edu", "Teacher@12345")
    with app.app_context():
        subject = Subject(code="214441", name="DM", class_group_id=1, teacher_id=None)
        from app.extensions import db

        db.session.add(subject)
        db.session.commit()
        other_id = subject.id
    response = client.get(f"/api/reports/subject/{other_id}/csv", headers=auth_header(teacher))
    assert response.status_code == 403
    report = client.get(f"/api/reports/subject/{other_id}", headers=auth_header(teacher))
    assert report.status_code == 403


def test_admin_can_edit_user(client):
    admin = login(client, "admin@test.edu", "Admin@12345")
    created = client.post(
        "/api/admin/users",
        json={
            "full_name": "Edit Me",
            "email": "edit.me@test.edu",
            "password": "Student@12345",
            "role": "student",
            "roll_number": "R9",
        },
        headers=auth_header(admin),
    )
    user_id = created.get_json()["user"]["id"]
    updated = client.patch(
        f"/api/admin/users/{user_id}",
        json={"full_name": "Edited Name", "phone": "9999999999"},
        headers=auth_header(admin),
    )
    assert updated.status_code == 200
    assert updated.get_json()["user"]["full_name"] == "Edited Name"
    assert updated.get_json()["user"]["phone"] == "9999999999"


def test_manual_mark_creates_audit(client, app):
    token, session_id, student_id, _subject_id = _open_session(client, app)
    client.post(
        f"/api/teacher/sessions/{session_id}/mark",
        json={"student_id": student_id, "status": "absent", "reason": "Left after break"},
        headers=auth_header(token),
    )
    admin = login(client, "admin@test.edu", "Admin@12345")
    logs = client.get("/api/reports/audit", headers=auth_header(admin))
    actions = [row["action"] for row in logs.get_json()["logs"]]
    assert "manual_mark" in actions
