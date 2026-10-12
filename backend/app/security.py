from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request

from .extensions import db
from .models import User


def current_user():
    user_id = get_jwt_identity()
    if user_id is None:
        return None
    return db.session.get(User, int(user_id))


def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            role = claims.get("role")
            user = current_user()
            if not user or not user.is_active:
                return jsonify({"error": "Account is inactive or missing."}), 403
            if role not in roles:
                return jsonify({"error": "You do not have permission for this action."}), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator
