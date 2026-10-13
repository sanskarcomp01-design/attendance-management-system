import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    _db_url = os.getenv("DATABASE_URL", "sqlite:///attendance.db")
    if _db_url == "sqlite:///attendance.db":
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + (BACKEND_DIR / "attendance.db").as_posix()
    else:
        SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
    QR_TTL_SECONDS = int(os.getenv("QR_TTL_SECONDS", "20"))
    FACE_MATCH_THRESHOLD = float(os.getenv("FACE_MATCH_THRESHOLD", "0.363"))
    ATTENDANCE_ELIGIBILITY_PERCENT = float(os.getenv("ATTENDANCE_ELIGIBILITY_PERCENT", "75"))
    UPLOAD_FOLDER = BACKEND_DIR / "uploads"
    MODEL_FOLDER = BACKEND_DIR / "models"
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    SECRET_KEY = "test-secret-key-32-bytes-minimum!!"
    JWT_SECRET_KEY = "test-jwt-secret-32-bytes-minimum!"
    RATELIMIT_ENABLED = False
