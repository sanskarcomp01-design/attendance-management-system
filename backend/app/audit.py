from flask import request

from .extensions import db
from .models import AuditLog


def log_action(actor_id, action, details=""):
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    entry = AuditLog(actor_id=actor_id, action=action, details=details, ip_address=ip)
    db.session.add(entry)
    db.session.commit()
    return entry
