from flask import Blueprint, jsonify, request

from ..audit import log_action
from ..extensions import db
from ..models import AttendanceRecord, AttendanceSession, Enrollment, Subject, User, utcnow
from ..security import current_user, role_required
from ..services.qr_service import current_window, make_token, token_to_png_base64

teacher_bp = Blueprint("teacher", __name__)


def _owned_subject(subject_id):
    user = current_user()
    subject = db.session.get(Subject, subject_id)
    if not subject or subject.teacher_id != user.id:
        return None
    return subject


@teacher_bp.get("/subjects")
@role_required("teacher")
def my_subjects():
    user = current_user()
    subjects = Subject.query.filter_by(teacher_id=user.id, is_active=True).all()
    return jsonify({"subjects": [s.to_dict() for s in subjects]})


@teacher_bp.post("/sessions")
@role_required("teacher")
def open_session():
    data = request.get_json(silent=True) or {}
    try:
        subject_id = int(data.get("subject_id") or 0)
    except (TypeError, ValueError):
        return jsonify({"error": "Valid subject_id is required."}), 400
    subject = _owned_subject(subject_id)
    if not subject:
        return jsonify({"error": "You can only start attendance for your assigned subjects."}), 403

    open_existing = AttendanceSession.query.filter_by(subject_id=subject.id, teacher_id=current_user().id, is_open=True).first()
    if open_existing:
        return jsonify({"error": "An attendance session is already open for this subject.", "session": open_existing.to_dict()}), 409

    session = AttendanceSession(
        subject_id=subject.id,
        teacher_id=current_user().id,
        note=(data.get("note") or "").strip() or None,
        is_open=True,
    )
    db.session.add(session)
    db.session.commit()
    log_action(current_user().id, "open_session", f"{subject.code} session {session.id}")
    return jsonify({"session": session.to_dict()}), 201


@teacher_bp.get("/sessions")
@role_required("teacher")
def list_sessions():
    sessions = (
        AttendanceSession.query.filter_by(teacher_id=current_user().id)
        .order_by(AttendanceSession.started_at.desc())
        .limit(50)
        .all()
    )
    return jsonify({"sessions": [s.to_dict() for s in sessions]})


@teacher_bp.get("/sessions/<int:session_id>")
@role_required("teacher")
def get_session(session_id):
    session = db.session.get(AttendanceSession, session_id)
    if not session or session.teacher_id != current_user().id:
        return jsonify({"error": "Session not found."}), 404
    enrolled = session.subject.enrollments
    records_by_student = {r.student_id: r for r in session.records}
    roster = []
    for enrollment in enrolled:
        student = enrollment.student
        record = records_by_student.get(student.id)
        roster.append(
            {
                "student_id": student.id,
                "full_name": student.full_name,
                "roll_number": student.roll_number,
                "status": record.status if record else "absent",
                "method": record.method if record else None,
                "note": record.note if record else None,
            }
        )
    return jsonify({"session": session.to_dict(with_records=True), "roster": roster})


@teacher_bp.get("/sessions/<int:session_id>/qr")
@role_required("teacher")
def session_qr(session_id):
    session = db.session.get(AttendanceSession, session_id)
    if not session or session.teacher_id != current_user().id:
        return jsonify({"error": "Session not found."}), 404
    if not session.is_open:
        return jsonify({"error": "This session is closed."}), 400
    from flask import current_app

    token = make_token(session.id)
    ttl = current_app.config["QR_TTL_SECONDS"]
    return jsonify(
        {
            "token": token,
            "image_base64": token_to_png_base64(token),
            "ttl_seconds": ttl,
            "window": current_window(ttl),
            "session_id": session.id,
        }
    )


@teacher_bp.post("/sessions/<int:session_id>/mark")
@role_required("teacher")
def manual_mark(session_id):
    session = db.session.get(AttendanceSession, session_id)
    if not session or session.teacher_id != current_user().id:
        return jsonify({"error": "Session not found."}), 404
    data = request.get_json(silent=True) or {}
    status = (data.get("status") or "").strip().lower()
    reason = (data.get("reason") or "").strip()
    try:
        student_id = int(data.get("student_id") or 0)
    except (TypeError, ValueError):
        return jsonify({"error": "Valid student_id is required."}), 400
    if status not in {"present", "absent"}:
        return jsonify({"error": "Status must be present or absent."}), 400
    if len(reason) < 3:
        return jsonify({"error": "Write a short reason (at least 3 characters) for the audit log."}), 400
    student = db.session.get(User, student_id)
    if not student or student.role != "student":
        return jsonify({"error": "Valid student_id is required."}), 400
    enrolled = Enrollment.query.filter_by(student_id=student.id, subject_id=session.subject_id).first()
    if not enrolled:
        return jsonify({"error": "That student is not enrolled in this subject."}), 400

    record = AttendanceRecord.query.filter_by(session_id=session.id, student_id=student.id).first()
    if record:
        record.status = status
        record.method = "manual"
        record.note = reason
        record.marked_at = utcnow()
        record.face_score = None
    else:
        record = AttendanceRecord(
            session_id=session.id,
            student_id=student.id,
            status=status,
            method="manual",
            note=reason,
        )
        db.session.add(record)
    db.session.commit()
    log_action(
        current_user().id,
        "manual_mark",
        f"{status} {student.email} session {session.id}: {reason}",
    )
    return jsonify({"record": record.to_dict(), "message": f"Marked {status} (manual)."})


@teacher_bp.post("/sessions/<int:session_id>/close")
@role_required("teacher")
def close_session(session_id):
    session = db.session.get(AttendanceSession, session_id)
    if not session or session.teacher_id != current_user().id:
        return jsonify({"error": "Session not found."}), 404
    session.is_open = False
    session.closed_at = utcnow()
    db.session.commit()
    log_action(current_user().id, "close_session", f"session {session.id}")
    return jsonify({"session": session.to_dict()})


@teacher_bp.get("/attendance")
@role_required("teacher")
def teacher_attendance():
    subject_id = request.args.get("subject_id", type=int)
    query = AttendanceRecord.query.join(AttendanceSession).filter(AttendanceSession.teacher_id == current_user().id)
    if subject_id:
        query = query.filter(AttendanceSession.subject_id == subject_id)
    records = query.order_by(AttendanceRecord.marked_at.desc()).limit(200).all()
    return jsonify({"records": [r.to_dict() for r in records]})
