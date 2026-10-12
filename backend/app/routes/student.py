import secrets
import time

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from flask_limiter.util import get_remote_address
from sqlalchemy.exc import IntegrityError

from ..audit import log_action
from ..extensions import db, limiter
from ..models import AttendanceChallenge, AttendanceRecord, AttendanceSession, Enrollment, FaceProfile
from ..security import current_user, role_required
from ..services import face_service
from ..services.face_service import FaceServiceError
from ..services.qr_service import verify_token

student_bp = Blueprint("student", __name__)


def _student_rate_limit_key():
    identity = get_jwt_identity()
    return f"student:{identity}" if identity is not None else get_remote_address()


@student_bp.get("/subjects")
@role_required("student")
def my_subjects():
    enrollments = Enrollment.query.filter_by(student_id=current_user().id).all()
    subjects = [e.subject.to_dict() for e in enrollments if e.subject]
    return jsonify({"subjects": subjects})


@student_bp.get("/attendance")
@role_required("student")
def my_attendance():
    user = current_user()
    enrollments = Enrollment.query.filter_by(student_id=user.id).all()
    summary = []
    for enrollment in enrollments:
        subject = enrollment.subject
        sessions = AttendanceSession.query.filter_by(subject_id=subject.id).all()
        total = len(sessions)
        present = AttendanceRecord.query.filter(
            AttendanceRecord.student_id == user.id,
            AttendanceRecord.session_id.in_([s.id for s in sessions] or [0]),
            AttendanceRecord.status == "present",
        ).count()
        percent = round((present / total) * 100, 1) if total else 0.0
        summary.append(
            {
                "subject_id": subject.id,
                "subject_code": subject.code,
                "subject_name": subject.name,
                "total_sessions": total,
                "present": present,
                "percent": percent,
            }
        )
    total_sessions = sum(row["total_sessions"] for row in summary)
    total_present = sum(row["present"] for row in summary)
    overall_percent = round((total_present / total_sessions) * 100, 1) if total_sessions else 0.0
    records = (
        AttendanceRecord.query.filter_by(student_id=user.id)
        .order_by(AttendanceRecord.marked_at.desc())
        .limit(100)
        .all()
    )
    return jsonify(
        {
            "summary": summary,
            "records": [r.to_dict() for r in records],
            "overall": {
                "present": total_present,
                "total_sessions": total_sessions,
                "percent": overall_percent,
            },
        }
    )


@student_bp.post("/face/enroll")
@role_required("student")
def enroll_face():
    if "image" not in request.files:
        return jsonify({"error": "Upload a selfie as form field 'image'."}), 400
    image_bytes = request.files["image"].read()
    try:
        vector = face_service.extract_embedding(image_bytes)
        blob = face_service.embedding_to_bytes(vector)
    except FaceServiceError as exc:
        return jsonify({"error": str(exc)}), 400

    user = current_user()
    profile = user.face_profile
    if profile:
        profile.embedding = blob
    else:
        profile = FaceProfile(user_id=user.id, embedding=blob)
        db.session.add(profile)
    db.session.commit()
    log_action(user.id, "enroll_face", "Face template stored")
    return jsonify({"message": "Face enrolled successfully.", "user": user.to_dict()})


@student_bp.post("/attendance/mark")
@role_required("student")
@limiter.limit("10 per minute", key_func=_student_rate_limit_key)
def mark_attendance():
    user = current_user()
    token = request.form.get("token") or (request.get_json(silent=True) or {}).get("token")
    if not token:
        return jsonify({"error": "QR token is required."}), 400
    if "neutral_image" not in request.files or "turned_image" not in request.files:
        return jsonify({"error": "Both liveness-check camera frames are required."}), 400

    ok, message, payload = verify_token(token)
    if not ok:
        return jsonify({"error": message}), 400

    session = db.session.get(AttendanceSession, payload["session_id"])
    if not session or not session.is_open:
        return jsonify({"error": "This attendance session is closed or missing."}), 400

    enrolled = Enrollment.query.filter_by(student_id=user.id, subject_id=session.subject_id).first()
    if not enrolled:
        return jsonify({"error": "You are not enrolled in this subject."}), 403

    existing = AttendanceRecord.query.filter_by(session_id=session.id, student_id=user.id).first()
    if existing:
        return jsonify({"error": "Attendance already marked for this session.", "record": existing.to_dict()}), 409

    if not user.face_profile:
        return jsonify({"error": "Enroll your face first from the student dashboard."}), 400

    challenge_id = request.form.get("challenge_id", "")
    now = int(time.time())
    challenge = AttendanceChallenge.query.filter_by(
        id=challenge_id,
        user_id=user.id,
        session_id=session.id,
        qr_window=payload["window"],
    ).first()
    if not challenge:
        return jsonify({"error": "Liveness challenge is invalid. Start a new check."}), 400
    if challenge.consumed_at is not None:
        return jsonify({"error": "Liveness challenge was already used. Start a new check."}), 409
    if challenge.expires_at <= now:
        return jsonify({"error": "Liveness challenge expired. Start a new check."}), 400

    consumed = (
        AttendanceChallenge.query.filter_by(id=challenge.id, consumed_at=None)
        .filter(AttendanceChallenge.expires_at > now)
        .update({"consumed_at": now}, synchronize_session=False)
    )
    if consumed != 1:
        db.session.rollback()
        return jsonify({"error": "Liveness challenge was already used. Start a new check."}), 409
    db.session.commit()

    try:
        matched, score, live = face_service.verify_face_liveness(
            request.files["neutral_image"].read(),
            request.files["turned_image"].read(),
            challenge.direction,
            user.face_profile.embedding,
        )
    except FaceServiceError as exc:
        return jsonify({"error": str(exc)}), 400

    if not live:
        log_action(user.id, "liveness_failed", f"session {session.id}")
        return jsonify({"error": "Head movement did not match the prompt. Start a new check."}), 403

    if not matched:
        log_action(user.id, "face_mismatch", f"session {session.id} score {score:.4f}")
        return jsonify({"error": "Face did not match the enrolled photo. Proxy attendance blocked.", "face_score": round(score, 4)}), 403

    record = AttendanceRecord(
        session_id=session.id,
        student_id=user.id,
        status="present",
        method="qr_face",
        face_score=score,
        qr_window=payload["window"],
    )
    db.session.add(record)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        existing = AttendanceRecord.query.filter_by(session_id=session.id, student_id=user.id).first()
        if existing:
            return jsonify({"error": "Attendance already marked for this session.", "record": existing.to_dict()}), 409
        raise
    log_action(user.id, "mark_attendance", f"{session.subject.code} session {session.id}")
    return jsonify({"message": "Attendance marked present.", "record": record.to_dict(), "face_score": round(score, 4)})


@student_bp.post("/attendance/challenge")
@role_required("student")
@limiter.limit("5 per minute", key_func=_student_rate_limit_key)
def attendance_challenge():
    user = current_user()
    data = request.get_json(silent=True) or {}
    token = data.get("token")
    if not token:
        return jsonify({"error": "QR token is required."}), 400

    ok, message, payload = verify_token(token)
    if not ok:
        return jsonify({"error": message}), 400

    session = db.session.get(AttendanceSession, payload["session_id"])
    if not session or not session.is_open:
        return jsonify({"error": "This attendance session is closed or missing."}), 400
    if not Enrollment.query.filter_by(student_id=user.id, subject_id=session.subject_id).first():
        return jsonify({"error": "You are not enrolled in this subject."}), 403
    if AttendanceRecord.query.filter_by(session_id=session.id, student_id=user.id).first():
        return jsonify({"error": "Attendance already marked for this session."}), 409
    if not user.face_profile:
        return jsonify({"error": "Enroll your face first from the student dashboard."}), 400

    now = int(time.time())
    db.session.query(AttendanceChallenge).filter(AttendanceChallenge.expires_at <= now).delete()
    challenge = AttendanceChallenge(
        id=secrets.token_urlsafe(32),
        user_id=user.id,
        session_id=session.id,
        qr_window=payload["window"],
        direction=secrets.choice(("left", "right")),
        expires_at=now + 60,
    )
    db.session.add(challenge)
    db.session.commit()
    return jsonify(
        {
            "challenge_id": challenge.id,
            "direction": challenge.direction,
            "expires_in": 60,
        }
    )
