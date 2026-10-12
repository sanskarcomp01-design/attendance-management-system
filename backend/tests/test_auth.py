import pytest

from app import create_app
from tests.conftest import auth_header, login


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_login_success(client):
    response = client.post("/api/auth/login", json={"email": "admin@test.edu", "password": "Admin@12345"})
    assert response.status_code == 200
    body = response.get_json()
    assert "access_token" in body
    assert body["user"]["role"] == "admin"


def test_login_wrong_password(client):
    response = client.post("/api/auth/login", json={"email": "admin@test.edu", "password": "wrong"})
    assert response.status_code == 401


def test_me_requires_token(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_with_token(client):
    token = login(client, "student@test.edu", "Student@12345")
    response = client.get("/api/auth/me", headers=auth_header(token))
    assert response.status_code == 200
    assert response.get_json()["user"]["email"] == "student@test.edu"


def test_change_password_requires_current_password_and_updates_hash(client):
    token = login(client, "student@test.edu", "Student@12345")
    headers = auth_header(token)
    invalid = client.post(
        "/api/auth/change-password",
        json={"current_password": "incorrect", "new_password": "a-new-password"},
        headers=headers,
    )
    assert invalid.status_code == 400

    changed = client.post(
        "/api/auth/change-password",
        json={"current_password": "Student@12345", "new_password": "a-new-password"},
        headers=headers,
    )
    assert changed.status_code == 200
    assert client.post(
        "/api/auth/login",
        json={"email": "student@test.edu", "password": "a-new-password"},
    ).status_code == 200


def test_deactivated_user_cannot_change_password(client, app):
    token = login(client, "student@test.edu", "Student@12345")
    from app.extensions import db
    from app.models import User

    user = User.query.filter_by(email="student@test.edu").first()
    user.is_active = False
    db.session.commit()
    response = client.post(
        "/api/auth/change-password",
        json={"current_password": "Student@12345", "new_password": "a-new-password"},
        headers=auth_header(token),
    )
    assert response.status_code == 403
    assert client.get("/api/auth/me", headers=auth_header(token)).status_code == 403


def test_app_rejects_missing_or_short_signing_secrets():
    class WeakConfig:
        TESTING = False
        SECRET_KEY = "short"
        JWT_SECRET_KEY = "also-short"

    with pytest.raises(RuntimeError, match="SECRET_KEY must be set"):
        create_app(WeakConfig)


def test_app_rejects_reused_signing_secrets():
    class ReusedConfig:
        TESTING = False
        SECRET_KEY = "a" * 40
        JWT_SECRET_KEY = "a" * 40

    with pytest.raises(RuntimeError, match="must use different random values"):
        create_app(ReusedConfig)
