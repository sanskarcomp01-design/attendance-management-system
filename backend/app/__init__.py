from flask import Flask, jsonify
from flask_cors import CORS
from sqlalchemy import inspect, text

from .config import Config
from .extensions import db, jwt, limiter
from .models import User  # noqa: F401  # register models with SQLAlchemy


def create_app(config_class=None):
    app = Flask(__name__)
    app.config.from_object(config_class or Config)
    _validate_secrets(app)

    CORS(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=True,
    )
    db.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)

    from .routes.auth import auth_bp
    from .routes.admin import admin_bp
    from .routes.teacher import teacher_bp
    from .routes.student import student_bp
    from .routes.reports import reports_bp
    from .routes.health import health_bp

    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(teacher_bp, url_prefix="/api/teacher")
    app.register_blueprint(student_bp, url_prefix="/api/student")
    app.register_blueprint(reports_bp, url_prefix="/api/reports")

    @jwt.unauthorized_loader
    def missing_token(_reason):
        return jsonify({"error": "Login required."}), 401

    @jwt.invalid_token_loader
    def invalid_token(_reason):
        return jsonify({"error": "Invalid or expired session. Please log in again."}), 401

    @jwt.expired_token_loader
    def expired_token(_header, _payload):
        return jsonify({"error": "Session expired. Please log in again."}), 401

    @app.errorhandler(404)
    def not_found(_e):
        return jsonify({"error": "Not found."}), 404

    @app.errorhandler(429)
    def too_many(_e):
        return jsonify({"error": "Too many attempts. Wait a minute and try again."}), 429

    with app.app_context():
        db.create_all()
        _upgrade_sqlite_columns()

    return app


def _validate_secrets(app):
    if app.config.get("TESTING"):
        return
    values = []
    for name in ("SECRET_KEY", "JWT_SECRET_KEY"):
        value = app.config.get(name)
        if not isinstance(value, str) or len(value) < 32 or value.lower().startswith("change-this"):
            raise RuntimeError(
                f"{name} must be set to a random value of at least 32 characters in the root .env file."
            )
        values.append(value)
    if values[0] == values[1]:
        raise RuntimeError("SECRET_KEY and JWT_SECRET_KEY must use different random values.")


def _upgrade_sqlite_columns():
    """Add new columns to an existing SQLite file without wiping demo data."""
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    if "attendance_records" not in tables:
        return
    columns = {col["name"] for col in inspector.get_columns("attendance_records")}
    if "note" not in columns:
        db.session.execute(text("ALTER TABLE attendance_records ADD COLUMN note VARCHAR(200)"))
        db.session.commit()
