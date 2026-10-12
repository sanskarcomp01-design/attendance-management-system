from io import BytesIO

from app.extensions import db
from app.models import AttendanceRecord, AttendanceSession, Enrollment, FaceProfile, Subject, User
from app.services.face_service import FaceServiceError
from app.services.qr_service import make_token
from tests.conftest import auth_header, login


def _open_session(client, app):
    teacher_token = login(client, "teacher@test.edu", "Teacher@12345")
    with app.app_context():
        subject_id = Subject.query.filter_by(code="214443").first().id
        student_id = User.query.filter_by(email="student@test.edu").first().id
    response = client.post(
        "/api/teacher/sessions",
        json={"subject_id": subject_id},
        headers=auth_header(teacher_token),
    )
    assert response.status_code == 201
    return response.get_json()["session"]["id"], student_id


def _add_face_profile(app, student_id):
    with app.app_context():
        db.session.add(FaceProfile(user_id=student_id, embedding=b"test-embedding"))
        db.session.commit()


def _mark(client, student_token, session_id):
    with client.application.app_context():
        token = make_token(session_id)
    challenge = client.post(
        "/api/student/attendance/challenge",
        json={"token": token},
        headers=auth_header(student_token),
    )
    if challenge.status_code != 200:
        return challenge
    return client.post(
        "/api/student/attendance/mark",
        data={
            "token": token,
            "challenge_id": challenge.get_json()["challenge_id"],
            "neutral_image": (BytesIO(b"neutral-image"), "neutral.jpg"),
            "turned_image": (BytesIO(b"turned-image"), "turned.jpg"),
        },
        headers=auth_header(student_token),
        content_type="multipart/form-data",
    )


def test_face_enrollment_saves_embedding(client, app, monkeypatch):
    from app.services import face_service

    monkeypatch.setattr(face_service, "extract_embedding", lambda _image: b"vector")
    monkeypatch.setattr(face_service, "embedding_to_bytes", lambda _vector: b"stored-embedding")
    student = login(client, "student@test.edu", "Student@12345")
    response = client.post(
        "/api/student/face/enroll",
        data={"image": (BytesIO(b"test-image"), "selfie.jpg")},
        headers=auth_header(student),
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    assert response.get_json()["user"]["has_face_enrolled"] is True
    with app.app_context():
        profile = FaceProfile.query.one()
        assert profile.embedding == b"stored-embedding"


def test_face_enrollment_reports_image_validation_error(client, monkeypatch):
    from app.services import face_service

    def reject_image(_image):
        raise FaceServiceError("No face found.")

    monkeypatch.setattr(face_service, "extract_embedding", reject_image)
    student = login(client, "student@test.edu", "Student@12345")
    response = client.post(
        "/api/student/face/enroll",
        data={"image": (BytesIO(b"invalid-image"), "selfie.jpg")},
        headers=auth_header(student),
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "No face found."


def test_matching_face_marks_attendance_and_duplicate_is_rejected(client, app, monkeypatch):
    from app.services import face_service

    session_id, student_id = _open_session(client, app)
    _add_face_profile(app, student_id)
    monkeypatch.setattr(face_service, "verify_face_liveness", lambda *_args: (True, 0.91, True))
    student = login(client, "student@test.edu", "Student@12345")

    first = _mark(client, student, session_id)
    assert first.status_code == 200
    assert first.get_json()["record"]["method"] == "qr_face"
    assert first.get_json()["face_score"] == 0.91

    duplicate = _mark(client, student, session_id)
    assert duplicate.status_code == 409
    assert duplicate.get_json()["error"] == "Attendance already marked for this session."
    with app.app_context():
        assert AttendanceRecord.query.filter_by(session_id=session_id, student_id=student_id).count() == 1


def test_attendance_requires_face_enrollment(client, app):
    session_id, _student_id = _open_session(client, app)
    student = login(client, "student@test.edu", "Student@12345")
    response = _mark(client, student, session_id)
    assert response.status_code == 400
    assert response.get_json()["error"] == "Enroll your face first from the student dashboard."


def test_nonmatching_face_does_not_mark_attendance(client, app, monkeypatch):
    from app.services import face_service

    session_id, student_id = _open_session(client, app)
    _add_face_profile(app, student_id)
    monkeypatch.setattr(face_service, "verify_face_liveness", lambda *_args: (False, 0.21, True))
    student = login(client, "student@test.edu", "Student@12345")

    response = _mark(client, student, session_id)
    assert response.status_code == 403
    assert response.get_json()["face_score"] == 0.21
    with app.app_context():
        assert AttendanceRecord.query.filter_by(session_id=session_id, student_id=student_id).count() == 0


def test_face_service_error_does_not_mark_attendance(client, app, monkeypatch):
    from app.services import face_service

    session_id, student_id = _open_session(client, app)
    _add_face_profile(app, student_id)

    def fail_verification(*_args):
        raise FaceServiceError("No face found.")

    monkeypatch.setattr(face_service, "verify_face_liveness", fail_verification)
    student = login(client, "student@test.edu", "Student@12345")

    response = _mark(client, student, session_id)
    assert response.status_code == 400
    assert response.get_json()["error"] == "No face found."
    with app.app_context():
        assert AttendanceRecord.query.filter_by(session_id=session_id, student_id=student_id).count() == 0


def test_liveness_failure_does_not_mark_attendance(client, app, monkeypatch):
    from app.services import face_service

    session_id, student_id = _open_session(client, app)
    _add_face_profile(app, student_id)
    monkeypatch.setattr(face_service, "verify_face_liveness", lambda *_args: (True, 0.91, False))
    student = login(client, "student@test.edu", "Student@12345")

    response = _mark(client, student, session_id)
    assert response.status_code == 403
    assert "Head movement" in response.get_json()["error"]
    with app.app_context():
        assert AttendanceRecord.query.filter_by(session_id=session_id, student_id=student_id).count() == 0


def test_liveness_challenge_is_bound_to_student_and_single_use(client, app, monkeypatch):
    from app.services import face_service

    session_id, student_id = _open_session(client, app)
    _add_face_profile(app, student_id)
    with app.app_context():
        other_student_id = User.query.filter_by(email="other@test.edu").one().id
        subject_id = db.session.get(AttendanceSession, session_id).subject_id
        db.session.add(FaceProfile(user_id=other_student_id, embedding=b"other-test-embedding"))
        db.session.add(Enrollment(student_id=other_student_id, subject_id=subject_id))
        db.session.commit()
    monkeypatch.setattr(face_service, "verify_face_liveness", lambda *_args: (True, 0.91, True))
    student = login(client, "student@test.edu", "Student@12345")
    other_student = login(client, "other@test.edu", "Student@12345")

    with app.app_context():
        token = make_token(session_id)
    issued = client.post(
        "/api/student/attendance/challenge",
        json={"token": token},
        headers=auth_header(student),
    )
    assert issued.status_code == 200
    challenge_id = issued.get_json()["challenge_id"]

    def post_mark(auth_token):
        return client.post(
            "/api/student/attendance/mark",
            data={
                "token": token,
                "challenge_id": challenge_id,
                "neutral_image": (BytesIO(b"neutral"), "neutral.jpg"),
                "turned_image": (BytesIO(b"turned"), "turned.jpg"),
            },
            headers=auth_header(auth_token),
            content_type="multipart/form-data",
        )

    other_attempt = post_mark(other_student)
    assert other_attempt.status_code == 400

    first = post_mark(student)
    assert first.status_code == 200
    with app.app_context():
        db.session.delete(AttendanceRecord.query.filter_by(session_id=session_id, student_id=student_id).one())
        db.session.commit()

    replay = post_mark(student)
    assert replay.status_code == 409
    assert "already used" in replay.get_json()["error"]


def test_liveness_check_requires_the_randomized_head_turn(app, monkeypatch):
    from app.services import face_service

    class FakeRecognizer:
        def alignCrop(self, image, _face):
            return image

        def feature(self, _image):
            return [0.1, 0.2]

    poses = iter(
        [
            (object(), object(), 0.01),
            (object(), object(), -0.14),
            (object(), object(), 0.01),
            (object(), object(), 0.14),
            (object(), object(), 0.01),
            (object(), object(), 0.02),
        ]
    )
    monkeypatch.setattr(face_service, "_face_pose", lambda _image: next(poses))
    monkeypatch.setattr(face_service, "_recognizer", FakeRecognizer())
    monkeypatch.setattr(face_service, "bytes_to_embedding", lambda _blob: [0.1, 0.2])
    monkeypatch.setattr(face_service, "compare", lambda *_args: 0.9)

    with app.app_context():
        left_result = face_service.verify_face_liveness(b"neutral", b"turned", "left", b"enrolled")
        right_result = face_service.verify_face_liveness(b"neutral", b"turned", "right", b"enrolled")
        still_result = face_service.verify_face_liveness(b"neutral", b"turned", "left", b"enrolled")

    assert left_result == (True, 0.9, True)
    assert right_result == (True, 0.9, True)
    assert still_result == (True, 0.9, False)
