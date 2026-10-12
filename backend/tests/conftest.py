import pytest

from app import create_app
from app.config import TestConfig
from app.extensions import db
from app.models import ClassGroup, Enrollment, Subject, User


@pytest.fixture()
def app():
    application = create_app(TestConfig)
    with application.app_context():
        db.create_all()
        admin = User(full_name="Admin", email="admin@test.edu", role="admin", employee_id="A1")
        admin.set_password("Admin@12345")
        teacher = User(full_name="Teacher", email="teacher@test.edu", role="teacher", employee_id="T1")
        teacher.set_password("Teacher@12345")
        student = User(full_name="Student", email="student@test.edu", role="student", roll_number="R1")
        student.set_password("Student@12345")
        other = User(full_name="Other Student", email="other@test.edu", role="student", roll_number="R2")
        other.set_password("Student@12345")
        db.session.add_all([admin, teacher, student, other])
        db.session.commit()
        group = ClassGroup(name="SE-IT-A", year="SE", department="IT", division="A")
        db.session.add(group)
        db.session.commit()
        subject = Subject(code="214443", name="DSA", class_group_id=group.id, teacher_id=teacher.id)
        db.session.add(subject)
        db.session.commit()
        db.session.add(Enrollment(student_id=student.id, subject_id=subject.id))
        db.session.commit()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, email, password):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    data = response.get_json()
    return data["access_token"]


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}
