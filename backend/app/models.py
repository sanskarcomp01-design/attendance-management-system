from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, index=True)  # admin, teacher, student
    roll_number = db.Column(db.String(40), unique=True)
    employee_id = db.Column(db.String(40), unique=True)
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    face_profile = db.relationship("FaceProfile", backref="user", uselist=False, cascade="all, delete-orphan")
    taught_subjects = db.relationship("Subject", backref="teacher", foreign_keys="Subject.teacher_id")
    enrollments = db.relationship("Enrollment", backref="student", cascade="all, delete-orphan")
    attendance_challenges = db.relationship("AttendanceChallenge", backref="user", cascade="all, delete-orphan")

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self, include_sensitive=False):
        data = {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "role": self.role,
            "roll_number": self.roll_number,
            "employee_id": self.employee_id,
            "phone": self.phone,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "has_face_enrolled": bool(self.face_profile),
        }
        if include_sensitive:
            data["password_hash"] = self.password_hash
        return data


class ClassGroup(db.Model):
    __tablename__ = "class_groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    year = db.Column(db.String(20), nullable=False)  # SE, TE, BE
    department = db.Column(db.String(80), nullable=False, default="Information Technology")
    division = db.Column(db.String(10), nullable=False)

    subjects = db.relationship("Subject", backref="class_group", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "year": self.year,
            "department": self.department,
            "division": self.division,
        }


class Subject(db.Model):
    __tablename__ = "subjects"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    class_group_id = db.Column(db.Integer, db.ForeignKey("class_groups.id"), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    enrollments = db.relationship("Enrollment", backref="subject", cascade="all, delete-orphan")
    sessions = db.relationship("AttendanceSession", backref="subject", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "class_group_id": self.class_group_id,
            "class_group": self.class_group.to_dict() if self.class_group else None,
            "teacher_id": self.teacher_id,
            "teacher_name": self.teacher.full_name if self.teacher else None,
            "is_active": self.is_active,
            "enrolled_count": len(self.enrollments),
        }


class Enrollment(db.Model):
    __tablename__ = "enrollments"
    __table_args__ = (db.UniqueConstraint("student_id", "subject_id", name="uq_student_subject"),)

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "student_name": self.student.full_name if self.student else None,
            "roll_number": self.student.roll_number if self.student else None,
            "subject_id": self.subject_id,
        }


class FaceProfile(db.Model):
    __tablename__ = "face_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    embedding = db.Column(db.LargeBinary, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class AttendanceSession(db.Model):
    __tablename__ = "attendance_sessions"

    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    started_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    closed_at = db.Column(db.DateTime)
    is_open = db.Column(db.Boolean, default=True, nullable=False)
    note = db.Column(db.String(200))

    teacher = db.relationship("User", foreign_keys=[teacher_id])
    records = db.relationship("AttendanceRecord", backref="session", cascade="all, delete-orphan")
    challenges = db.relationship("AttendanceChallenge", backref="session", cascade="all, delete-orphan")

    def to_dict(self, with_records=False):
        present_records = [record for record in self.records if record.status == "present"]
        data = {
            "id": self.id,
            "subject_id": self.subject_id,
            "subject_code": self.subject.code if self.subject else None,
            "subject_name": self.subject.name if self.subject else None,
            "teacher_id": self.teacher_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "is_open": self.is_open,
            "note": self.note,
            "present_count": len(present_records),
            "attendance_by_method": {
                "qr_face": sum(1 for record in present_records if record.method == "qr_face"),
                "manual": sum(1 for record in present_records if record.method == "manual"),
            },
        }
        if with_records:
            data["records"] = [r.to_dict() for r in self.records]
        return data


class AttendanceChallenge(db.Model):
    __tablename__ = "attendance_challenges"

    id = db.Column(db.String(64), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = db.Column(db.Integer, db.ForeignKey("attendance_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    qr_window = db.Column(db.Integer, nullable=False)
    direction = db.Column(db.String(5), nullable=False)
    expires_at = db.Column(db.Integer, nullable=False, index=True)
    consumed_at = db.Column(db.Integer)


class AttendanceRecord(db.Model):
    __tablename__ = "attendance_records"
    __table_args__ = (db.UniqueConstraint("session_id", "student_id", name="uq_session_student"),)

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("attendance_sessions.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.String(20), default="present", nullable=False)
    marked_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    method = db.Column(db.String(40), default="qr_face")
    face_score = db.Column(db.Float)
    qr_window = db.Column(db.Integer)
    note = db.Column(db.String(200))

    student = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "student_id": self.student_id,
            "student_name": self.student.full_name if self.student else None,
            "roll_number": self.student.roll_number if self.student else None,
            "status": self.status,
            "marked_at": self.marked_at.isoformat() if self.marked_at else None,
            "method": self.method,
            "face_score": round(self.face_score, 4) if self.face_score is not None else None,
            "note": self.note,
        }


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    action = db.Column(db.String(80), nullable=False)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(60))
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    actor = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "actor_id": self.actor_id,
            "actor_name": self.actor.full_name if self.actor else "system",
            "actor_email": self.actor.email if self.actor else None,
            "action": self.action,
            "details": self.details,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
