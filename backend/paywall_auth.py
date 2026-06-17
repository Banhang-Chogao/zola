"""Auth helpers — admin token + reader unlock sessions."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone


def hash_code(code: str) -> str:
    return hashlib.sha256(code.strip().upper().encode("utf-8")).hexdigest()


def hash_email(email: str) -> str:
    return hashlib.sha256(email.lower().strip().encode("utf-8")).hexdigest()[:16]


def generate_approve_code(length: int = 12) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_trace_code() -> str:
    return secrets.token_hex(8).upper()


def generate_access_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def session_expires(hours: int | None = None) -> str:
    h = hours or int(os.getenv("PAYWALL_SESSION_HOURS", "4"))
    return (datetime.now(timezone.utc) + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_expired(iso_ts: str) -> bool:
    try:
        exp = datetime.strptime(iso_ts[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > exp
    except ValueError:
        return True


def verify_admin_token(authorization: str | None) -> bool:
    expected = os.getenv("PAYWALL_ADMIN_TOKEN", "")
    if not expected:
        return False
    if not authorization:
        return False
    token = authorization.removeprefix("Bearer ").strip()
    return hmac.compare_digest(token, expected)