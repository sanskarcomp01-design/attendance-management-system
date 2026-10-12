from flask import Blueprint, jsonify

from ..services.face_service import models_ready

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "project": "AI-Powered Attendance Management System",
            "institution": "S. B. Patil College of Engineering, Indapur",
            "university": "Savitribai Phule Pune University",
            "face_models_ready": models_ready(),
        }
    )
