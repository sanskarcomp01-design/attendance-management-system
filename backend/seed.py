"""Create the sample college records using passwords from the root .env file."""

import argparse

from app import create_app
from app.extensions import db
from app.models import ClassGroup, Enrollment, Subject, User
from app.config import ROOT_DIR
import os

from dotenv import load_dotenv

load_dotenv(ROOT_DIR / ".env")


def get_or_create_user(reset_passwords=False, **kwargs):
    email = kwargs["email"].lower()
    password = kwargs.pop("password")
    user = User.query.filter_by(email=email).first()
    if user:
        if reset_passwords:
            user.set_password(password)
        return user
    user = User(**kwargs)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def _seed_passwords():
    keys = (
        "SEED_ADMIN_PASSWORD",
        "SEED_TEACHER_PASSWORD",
        "SEED_TEACHER2_PASSWORD",
        "SEED_STUDENT_PASSWORD",
        "SEED_STUDENT2_PASSWORD",
        "SEED_STUDENT3_PASSWORD",
        "SEED_STUDENT4_PASSWORD",
    )
    passwords = {key: os.getenv(key, "") for key in keys}
    missing = [key for key, value in passwords.items() if len(value) < 16]
    if missing:
        raise RuntimeError(
            "Set unique seed passwords of at least 16 characters in .env using: "
            + ", ".join(missing)
            + ". Run backend/scripts/initialize_secrets.py to generate them."
        )
    return passwords


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset-seed-passwords",
        action="store_true",
        help="Apply the current .env seed passwords to all accounts managed by this seed.",
    )
    args = parser.parse_args()
    passwords = _seed_passwords()

    app = create_app()
    with app.app_context():
        db.create_all()

        admin = get_or_create_user(
            reset_passwords=args.reset_seed_passwords,
            full_name="CEP Administrator",
            email=os.getenv("SEED_ADMIN_EMAIL", "admin@sbpcoe.edu"),
            password=passwords["SEED_ADMIN_PASSWORD"],
            role="admin",
            employee_id="ADM001",
        )
        teacher = get_or_create_user(
            reset_passwords=args.reset_seed_passwords,
            full_name="Prof. A. K. Deshmukh",
            email=os.getenv("SEED_TEACHER_EMAIL", "teacher@sbpcoe.edu"),
            password=passwords["SEED_TEACHER_PASSWORD"],
            role="teacher",
            employee_id="ITTCH01",
        )
        teacher2 = get_or_create_user(
            reset_passwords=args.reset_seed_passwords,
            full_name="Prof. S. P. Jadhav",
            email="teacher2@sbpcoe.edu",
            password=passwords["SEED_TEACHER2_PASSWORD"],
            role="teacher",
            employee_id="ITTCH02",
        )

        students = []
        demo_student = get_or_create_user(
            reset_passwords=args.reset_seed_passwords,
            full_name="Rohit Patil",
            email=os.getenv("SEED_STUDENT_EMAIL", "student@sbpcoe.edu"),
            password=passwords["SEED_STUDENT_PASSWORD"],
            role="student",
            roll_number="SEIT001",
        )
        students.append(demo_student)
        extras = [
            ("Sneha More", "sneha.more@sbpcoe.edu", "SEIT002", "SEED_STUDENT2_PASSWORD"),
            ("Aditya Kulkarni", "aditya.kulkarni@sbpcoe.edu", "SEIT003", "SEED_STUDENT3_PASSWORD"),
            ("Priya Shinde", "priya.shinde@sbpcoe.edu", "SEIT004", "SEED_STUDENT4_PASSWORD"),
        ]
        for name, email, roll, password_key in extras:
            students.append(
                get_or_create_user(
                    reset_passwords=args.reset_seed_passwords,
                    full_name=name,
                    email=email,
                    password=passwords[password_key],
                    role="student",
                    roll_number=roll,
                )
            )

        group = ClassGroup.query.filter_by(name="SE-IT-A").first()
        if not group:
            group = ClassGroup(
                name="SE-IT-A",
                year="SE",
                department="Information Technology",
                division="A",
            )
            db.session.add(group)
            db.session.commit()

        catalog = [
            ("214441", "Discrete Mathematics", teacher.id),
            ("214442", "Logic Design & Computer Organization", teacher2.id),
            ("214443", "Data Structures & Algorithms", teacher.id),
            ("214444", "Object Oriented Programming", teacher.id),
            ("214445", "Basics of Computer Network", teacher2.id),
        ]
        for code, name, teacher_id in catalog:
            subject = Subject.query.filter_by(code=code).first()
            if not subject:
                subject = Subject(
                    code=code,
                    name=name,
                    class_group_id=group.id,
                    teacher_id=teacher_id,
                    is_active=True,
                )
                db.session.add(subject)
                db.session.commit()
            for student in students:
                exists = Enrollment.query.filter_by(student_id=student.id, subject_id=subject.id).first()
                if not exists:
                    db.session.add(Enrollment(student_id=student.id, subject_id=subject.id))
        db.session.commit()
        print("Seed complete.")
        print(f"Admin   : {admin.email}")
        print(f"Teacher : {teacher.email}")
        print(f"Student : {demo_student.email}")
        print("Unique account passwords are stored only in the root .env file.")


if __name__ == "__main__":
    main()
