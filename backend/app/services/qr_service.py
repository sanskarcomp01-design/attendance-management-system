import base64
import hashlib
import hmac
import io
import json
import time
from typing import Optional

import qrcode
from flask import current_app


def _secret() -> bytes:
    return current_app.config["SECRET_KEY"].encode("utf-8")


def current_window(ttl: Optional[int] = None) -> int:
    ttl = ttl or current_app.config["QR_TTL_SECONDS"]
    return int(time.time() // ttl)


def make_token(session_id: int, window: Optional[int] = None) -> str:
    window = current_window() if window is None else window
    message = f"{session_id}:{window}".encode("utf-8")
    digest = hmac.new(_secret(), message, hashlib.sha256).hexdigest()
    payload = {"sid": session_id, "w": window, "t": digest}
    return base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")


def verify_token(token: str, ttl: Optional[int] = None) -> tuple[bool, str, Optional[dict]]:
    ttl = ttl or current_app.config["QR_TTL_SECONDS"]
    try:
        raw = base64.urlsafe_b64decode(token.encode("utf-8"))
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError
        session_id = int(payload["sid"])
        window = int(payload["w"])
        digest = payload["t"]
        if not isinstance(digest, str):
            raise ValueError
    except (KeyError, ValueError, json.JSONDecodeError, TypeError):
        return False, "This QR code is not valid.", None

    now = current_window(ttl)
    if window < now - 1 or window > now:
        return False, "This QR code has expired. Ask the teacher to show a fresh code.", None

    expected = hmac.new(_secret(), f"{session_id}:{window}".encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, digest):
        return False, "This QR code failed security checks.", None

    return True, "ok", {"session_id": session_id, "window": window}


def token_to_png_base64(token: str) -> str:
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
    qr.add_data(token)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0b1f3a", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")
