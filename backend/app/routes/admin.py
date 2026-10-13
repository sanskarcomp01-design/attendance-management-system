from flask import Blueprint, jsonify, request

from ..audit import log_action
from ..extensions import db
from ..models import ClassGroup, Enrollment, Subject, User
from ..security import current_user, role_required

admin_bp = Blueprint("admin", __name__)


def _require_fields(data, fields):
    missing = [f for f in fields if not str(data.get(f) or "").strip()]
    return missing


@admin_bp.get("/stats")
@role_required("admin")
def stats():
    return jsonify(
        {
            "students": User.query.filter_by(role="student").count(),
            "teachers": User.query.filter_by(role="teacher").count(),
            "subjects": Subject.query.count(),
            "classes": ClassGroup.query.count(),
            "active_users": User.query.filter_by(is_active=True).count(),
        }
    )


@admin_bp.get("/users")
@role_required("admin")
def list_users():
    role = request.args.get("role")
    query = User.query
    if role:
        query = query.filter_by(role=role)
    users = query.order_by(User.full_name).all()
    return jsonify({"users": [u.to_dict() for u in users]})


@admin_bp.post("/users")
@role_required("admin")
def create_user():
    data = request.get_json(silent=True) or {}
    missing = _require_fields(data, ["full_name", "email", "password", "role"])
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
    role = data["role"].strip().lower()
    if role not in {"admin", "teacher", "student"}:
        return jsonify({"error": "Role must be admin, teacher, or student."}), 400
    email = data["email"].strip().lower()
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "A user with this email already exists."}), 409
    if len(data["password"]) < 8:
        return jsonify({"error": "Password must be at least 8 characters."}), 400

    user = User(
        full_name=data["full_name"].strip(),
        email=email,
        role=role,
        roll_number=(data.get("roll_number") or "").strip() or None,
        employee_id=(data.get("employee_id") or "").strip() or None,
        phone=(data.get("phone") or "").strip() or None,
        is_active=True,
    )
    user.set_password(data["password"])
    db.session.add(user)
    db.session.commit()
    log_action(current_user().id, "create_user", f"Created {role} {email}")
    return jsonify({"user": user.to_dict()}), 201


@admin_bp.patch("/users/<int:user_id>")
@role_required("admin")
def update_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404
    data = request.get_json(silent=True) or {}
    for field in ("full_name", "phone", "roll_number", "employee_id"):
        if field in data:
            value = (data.get(field) or "").strip() or None
            setattr(user, field, value if field != "full_name" else (value or user.full_name))
    if "email" in data and data["email"]:
        email = data["email"].strip().lower()
        clash = User.query.filter(User.email == email, User.id != user.id).first()
        if clash:
            return jsonify({"error": "Email already in use."}), 409
        user.email = email
    if "is_active" in data:
        user.is_active = bool(data["is_active"])
    if data.get("password"):
        if len(data["password"]) < 8:
            return jsonify({"error": "Password must be at least 8 characters."}), 400
        user.set_password(data["password"])
    db.session.commit()
    log_action(current_user().id, "update_user", f"Updated user {user.email}")
    return jsonify({"user": user.to_dict()})


@admin_bp.post("/users/<int:user_id>/deactivate")
@role_required("admin")
def deactivate_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404
    if user.id == current_user().id:
        return jsonify({"error": "You cannot deactivate your own account."}), 400
    user.is_active = False
    db.session.commit()
    log_action(current_user().id, "deactivate_user", f"Deactivated {user.email}")
    return jsonify({"user": user.to_dict()})


@admin_bp.get("/classes")
@role_required("admin")
def list_classes():
    groups = ClassGroup.query.order_by(ClassGroup.name).all()
    return jsonify({"classes": [g.to_dict() for g in groups]})


@admin_bp.post("/classes")
@role_required("admin")
def create_class():
    data = request.get_json(silent=True) or {}
    missing = _require_fields(data, ["name", "year", "division"])
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
    group = ClassGroup(
        name=data["name"].strip(),
        year=data["year"].strip(),
        department=(data.get("department") or "Information Technology").strip(),
        division=data["division"].strip(),
    )
    db.session.add(group)
    db.session.commit()
    log_action(current_user().id, "create_class", group.name)
    return jsonify({"class": group.to_dict()}), 201


@admin_bp.patch("/classes/<int:class_id>")
@role_required("admin")
def update_class(class_id):
    group = db.session.get(ClassGroup, class_id)
    if not group:
        return jsonify({"error": "Class not found."}), 404
    data = request.get_json(silent=True) or {}
    for field in ("name", "year", "department", "division"):
        if field not in data:
            continue
        value = str(data[field] or "").strip()
        if field != "department" and not value:
            return jsonify({"error": f"{field.replace('_', ' ').title()} cannot be empty."}), 400
        if field == "department" and not value:
            value = "Information Technology"
        if field == "name":
            duplicate = ClassGroup.query.filter(
                ClassGroup.name == value, ClassGroup.id != group.id
            ).first()
            if duplicate:
                return jsonify({"error": "A class with this name already exists."}), 409
        setattr(group, field, value)
    db.session.commit()
    log_action(current_user().id, "update_class", group.name)
    return jsonify({"class": group.to_dict()})


@admin_bp.get("/subjects")
@role_required("admin")
def list_subjects():
    subjects = Subject.query.order_by(Subject.code).all()
    return jsonify({"subjects": [s.to_dict() for s in subjects]})


@admin_bp.post("/subjects")
@role_required("admin")
def create_subject():
    data = request.get_json(silent=True) or {}
    missing = _require_fields(data, ["code", "name", "class_group_id"])
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
    code = data["code"].strip().upper()
    if Subject.query.filter_by(code=code).first():
        return jsonify({"error": "Subject code already exists."}), 409
    try:
        class_group_id = int(data["class_group_id"])
    except (TypeError, ValueError):
        return jsonify({"error": "Valid class_group_id is required."}), 400
    group = db.session.get(ClassGroup, class_group_id)
    if not group:
        return jsonify({"error": "Class not found."}), 404
    teacher_id = data.get("teacher_id")
    if teacher_id:
        try:
            teacher_id = int(teacher_id)
        except (TypeError, ValueError):
            return jsonify({"error": "Assigned teacher is invalid."}), 400
        teacher = db.session.get(User, teacher_id)
        if not teacher or teacher.role != "teacher":
            return jsonify({"error": "Assigned teacher is invalid."}), 400
    subject = Subject(
        code=code,
        name=data["name"].strip(),
        class_group_id=group.id,
        teacher_id=int(teacher_id) if teacher_id else None,
        is_active=True,
    )
    db.session.add(subject)
    db.session.commit()
    log_action(current_user().id, "create_subject", f"{code} {subject.name}")
    return jsonify({"subject": subject.to_dict()}), 201


@admin_bp.patch("/subjects/<int:subject_id>")
@role_required("admin")
def update_subject(subject_id):
    subject = db.session.get(Subject, subject_id)
    if not subject:
        return jsonify({"error": "Subject not found."}), 404
    data = request.get_json(silent=True) or {}
    if "code" in data:
        code = str(data["code"] or "").strip().upper()
        if not code:
            return jsonify({"error": "Subject code cannot be empty."}), 400
        duplicate = Subject.query.filter(Subject.code == code, Subject.id != subject.id).first()
        if duplicate:
            return jsonify({"error": "Subject code already exists."}), 409
        subject.code = code
    if "name" in data:
        name = str(data["name"] or "").strip()
        if not name:
            return jsonify({"error": "Subject name cannot be empty."}), 400
        subject.name = name
    if "class_group_id" in data:
        try:
            class_group_id = int(data["class_group_id"])
        except (TypeError, ValueError):
            return jsonify({"error": "Valid class_group_id is required."}), 400
        group = db.session.get(ClassGroup, class_group_id)
        if not group:
            return jsonify({"error": "Class not found."}), 404
        subject.class_group_id = group.id
    if "teacher_id" in data:
        teacher_id = data["teacher_id"]
        if teacher_id:
            try:
                teacher_id = int(teacher_id)
            except (TypeError, ValueError):
                return jsonify({"error": "Assigned teacher is invalid."}), 400
            teacher = db.session.get(User, teacher_id)
            if not teacher or teacher.role != "teacher":
                return jsonify({"error": "Assigned teacher is invalid."}), 400
            subject.teacher_id = teacher.id
        else:
            subject.teacher_id = None
    if "is_active" in data:
        if not isinstance(data["is_active"], bool):
            return jsonify({"error": "is_active must be a boolean."}), 400
        subject.is_active = data["is_active"]
    db.session.commit()
    log_action(current_user().id, "update_subject", subject.code)
    return jsonify({"subject": subject.to_dict()})


@admin_bp.get("/subjects/<int:subject_id>/enrollments")
@role_required("admin")
def list_enrollments(subject_id):
    subject = db.session.get(Subject, subject_id)
    if not subject:
        return jsonify({"error": "Subject not found."}), 404
    return jsonify({"enrollments": [e.to_dict() for e in subject.enrollments], "subject": subject.to_dict()})


@admin_bp.post("/subjects/<int:subject_id>/enroll")
@role_required("admin")
def enroll_student(subject_id):
    subject = db.session.get(Subject, subject_id)
    if not subject:
        return jsonify({"error": "Subject not found."}), 404
    data = request.get_json(silent=True) or {}
    try:
        student_id = int(data.get("student_id") or 0)
    except (TypeError, ValueError):
        return jsonify({"error": "Valid student_id is required."}), 400
    student = db.session.get(User, student_id)
    if not student or student.role != "student":
        return jsonify({"error": "Valid student_id is required."}), 400
    existing = Enrollment.query.filter_by(student_id=student.id, subject_id=subject.id).first()
    if existing:
        return jsonify({"error": "Student is already enrolled."}), 409
    enrollment = Enrollment(student_id=student.id, subject_id=subject.id)
    db.session.add(enrollment)
    db.session.commit()
    log_action(current_user().id, "enroll_student", f"{student.email} -> {subject.code}")
    return jsonify({"enrollment": enrollment.to_dict()}), 201


@admin_bp.delete("/subjects/<int:subject_id>/enroll/<int:student_id>")
@role_required("admin")
def unenroll_student(subject_id, student_id):
    enrollment = Enrollment.query.filter_by(subject_id=subject_id, student_id=student_id).first()
    if not enrollment:
        return jsonify({"error": "Enrollment not found."}), 404
    db.session.delete(enrollment)
    db.session.commit()
    log_action(current_user().id, "unenroll_student", f"student {student_id} from subject {subject_id}")
    return jsonify({"message": "Enrollment removed."})
