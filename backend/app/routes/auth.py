from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token

from ..audit import log_action
from ..extensions import db, limiter
from ..models import User
from ..security import current_user, role_required

auth_bp = Blueprint("auth", __name__)


def _token_for(user: User):
    return create_access_token(identity=str(user.id), additional_claims={"role": user.role, "email": user.email})


@auth_bp.post("/login")
@limiter.limit("8 per minute")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Incorrect email or password."}), 401
    if not user.is_active:
        return jsonify({"error": "This account is deactivated. Contact the administrator."}), 403

    log_action(user.id, "login", f"{user.role} signed in")
    return jsonify({"access_token": _token_for(user), "user": user.to_dict()})


@auth_bp.get("/me")
@role_required("admin", "teacher", "student")
def me():
    user = current_user()
    if not user:
        return jsonify({"error": "User not found."}), 404
    return jsonify({"user": user.to_dict()})


@auth_bp.post("/change-password")
@role_required("admin", "teacher", "student")
def change_password():
    user = current_user()
    data = request.get_json(silent=True) or {}
    current = data.get("current_password") or ""
    new_password = data.get("new_password") or ""
    if len(new_password) < 8:
        return jsonify({"error": "New password must be at least 8 characters."}), 400
    if not user.check_password(current):
        return jsonify({"error": "Current password is incorrect."}), 400
    user.set_password(new_password)
    db.session.commit()
    log_action(user.id, "change_password", "Password updated")
    return jsonify({"message": "Password updated."})


@auth_bp.post("/logout")
@role_required("admin", "teacher", "student")
def logout():
    user = current_user()
    log_action(user.id, "logout", "Signed out")
    return jsonify({"message": "Signed out."})
