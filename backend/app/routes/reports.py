import csv
import io

from flask import Blueprint, Response, current_app, jsonify, request
from flask_jwt_extended import get_jwt

from ..extensions import db
from ..models import AttendanceRecord, AttendanceSession, AuditLog, Subject
from ..security import current_user, role_required

reports_bp = Blueprint("reports", __name__)


def _load_subject_for_report(subject_id):
    subject = db.session.get(Subject, subject_id)
    if not subject:
        return None, (jsonify({"error": "Subject not found."}), 404)
    claims = get_jwt()
    if claims.get("role") == "teacher" and subject.teacher_id != current_user().id:
        return None, (jsonify({"error": "You can only view reports for your subjects."}), 403)
    return subject, None


def _subject_report_payload(subject):
    threshold = current_app.config["ATTENDANCE_ELIGIBILITY_PERCENT"]
    sessions = AttendanceSession.query.filter_by(subject_id=subject.id).order_by(AttendanceSession.started_at).all()
    rows = []
    for enrollment in subject.enrollments:
        student = enrollment.student
        present = 0
        for session in sessions:
            found = next((r for r in session.records if r.student_id == student.id and r.status == "present"), None)
            if found:
                present += 1
        total = len(sessions)
        percent = round((present / total) * 100, 1) if total else 0.0
        rows.append(
            {
                "student_id": student.id,
                "full_name": student.full_name,
                "roll_number": student.roll_number,
                "present": present,
                "total_sessions": total,
                "percent": percent,
                "eligible": percent >= threshold if total else False,
            }
        )
    return {
        "subject": subject.to_dict(),
        "sessions": [s.to_dict() for s in sessions],
        "rows": rows,
        "eligibility_percent": threshold,
    }


@reports_bp.get("/subject/<int:subject_id>")
@role_required("admin", "teacher")
def subject_report(subject_id):
    subject, error = _load_subject_for_report(subject_id)
    if error:
        return error
    return jsonify(_subject_report_payload(subject))


@reports_bp.get("/subject/<int:subject_id>/csv")
@role_required("admin", "teacher")
def subject_report_csv(subject_id):
    subject, error = _load_subject_for_report(subject_id)
    if error:
        return error
    payload = _subject_report_payload(subject)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["roll_number", "full_name", "present", "total_sessions", "percent", "eligible_75_percent", "subject_code", "subject_name"]
    )
    for row in payload["rows"]:
        writer.writerow(
            [
                row["roll_number"] or "",
                row["full_name"],
                row["present"],
                row["total_sessions"],
                row["percent"],
                "yes" if row["eligible"] else "no",
                payload["subject"]["code"],
                payload["subject"]["name"],
            ]
        )
    filename = f"{payload['subject']['code']}-attendance.csv"
    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@reports_bp.get("/attendance")
@role_required("admin")
def all_attendance():
    subject_id = request.args.get("subject_id", type=int)
    query = AttendanceRecord.query
    if subject_id:
        query = query.join(AttendanceSession).filter(AttendanceSession.subject_id == subject_id)
    records = query.order_by(AttendanceRecord.marked_at.desc()).limit(500).all()
    return jsonify({"records": [r.to_dict() for r in records]})


@reports_bp.get("/audit")
@role_required("admin")
def audit_logs():
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(300).all()
    return jsonify({"logs": [log.to_dict() for log in logs]})
