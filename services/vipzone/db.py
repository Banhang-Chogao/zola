"""SQLite persistence for VIPZone."""

from __future__ import annotations

import hashlib
import secrets
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB = ROOT / "data" / "vipzone.db"

PLAN_DAYS = {"monthly": 30, "semiannual": 180}
PLAN_PRICE = {"monthly": 250_000, "semiannual": 500_000}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _expires_from_plan(plan: str) -> str:
    days = PLAN_DAYS.get(plan, 30)
    exp = datetime.now(timezone.utc) + timedelta(days=days)
    return exp.strftime("%Y-%m-%dT%H:%M:%SZ")


class VipzoneDB:
    def __init__(self, path: Path | str = DEFAULT_DB) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS payment_requests (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL,
                    plan TEXT NOT NULL,
                    payment_note TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    resolved_at TEXT
                );
                CREATE TABLE IF NOT EXISTS approve_codes (
                    id TEXT PRIMARY KEY,
                    code_hash TEXT NOT NULL UNIQUE,
                    plan TEXT NOT NULL,
                    email TEXT,
                    used INTEGER NOT NULL DEFAULT 0,
                    used_at TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS vip_users (
                    email TEXT PRIMARY KEY,
                    plan TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    activated_at TEXT NOT NULL,
                    deactivated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS oauth_states (
                    state TEXT PRIMARY KEY,
                    return_to TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS cms_sessions (
                    sid TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );
                """
            )

    @staticmethod
    def hash_code(code: str) -> str:
        return hashlib.sha256(code.encode()).hexdigest()

    def insert_payment_request(self, data: dict[str, Any]) -> str:
        rid = data.get("id") or f"pay_{uuid.uuid4().hex[:12]}"
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO payment_requests (id, email, plan, payment_note, status, created_at)
                VALUES (?, ?, ?, ?, 'pending', ?)
                """,
                (
                    rid,
                    data["email"].lower().strip(),
                    data["plan"],
                    data.get("payment_note") or "",
                    _now(),
                ),
            )
        return rid

    def list_payment_requests(self, status: str | None = None) -> list[dict[str, Any]]:
        with self._conn() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM payment_requests WHERE status = ? ORDER BY created_at DESC",
                    (status,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM payment_requests ORDER BY created_at DESC"
                ).fetchall()
        return [dict(r) for r in rows]

    def resolve_payment_request(self, request_id: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute(
                """
                UPDATE payment_requests
                SET status = 'resolved', resolved_at = ?
                WHERE id = ? AND status = 'pending'
                """,
                (_now(), request_id),
            )
        return cur.rowcount > 0

    def insert_code(self, data: dict[str, Any]) -> str:
        cid = data.get("id") or f"code_{uuid.uuid4().hex[:12]}"
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO approve_codes (id, code_hash, plan, email, used, created_at)
                VALUES (?, ?, ?, ?, 0, ?)
                """,
                (
                    cid,
                    data["code_hash"],
                    data["plan"],
                    (data.get("email") or "").lower().strip() or None,
                    _now(),
                ),
            )
        return cid

    def list_codes(self) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, plan, email, used, used_at, created_at FROM approve_codes ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def find_unused_code(self, code: str) -> dict[str, Any] | None:
        h = self.hash_code(code)
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM approve_codes WHERE code_hash = ? AND used = 0",
                (h,),
            ).fetchone()
        return dict(row) if row else None

    def mark_code_used(self, code_id: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE approve_codes SET used = 1, used_at = ? WHERE id = ?",
                (_now(), code_id),
            )

    def upsert_vip(self, email: str, plan: str, expires_at: str) -> dict[str, Any]:
        email = email.lower().strip()
        now = _now()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO vip_users (email, plan, expires_at, active, activated_at, deactivated_at)
                VALUES (?, ?, ?, 1, ?, NULL)
                ON CONFLICT(email) DO UPDATE SET
                    plan = excluded.plan,
                    expires_at = excluded.expires_at,
                    active = 1,
                    activated_at = excluded.activated_at,
                    deactivated_at = NULL
                """,
                (email, plan, expires_at, now),
            )
            row = conn.execute("SELECT * FROM vip_users WHERE email = ?", (email,)).fetchone()
        return dict(row)

    def list_vips(self) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT email, plan, expires_at, active, activated_at FROM vip_users ORDER BY activated_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_active_vip(self, email: str) -> dict[str, Any] | None:
        email = email.lower().strip()
        if not email:
            return None
        with self._conn() as conn:
            row = conn.execute(
                "SELECT email, plan, expires_at, active, activated_at FROM vip_users WHERE email = ?",
                (email,),
            ).fetchone()
        if not row or not row["active"]:
            return None
        try:
            exp = datetime.strptime(row["expires_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            )
            if exp <= datetime.now(timezone.utc):
                return None
        except ValueError:
            pass
        return dict(row)

    def is_active_vip(self, email: str) -> bool:
        return self.get_active_vip(email) is not None

    def deactivate_vip(self, email: str) -> bool:
        email = email.lower().strip()
        with self._conn() as conn:
            cur = conn.execute(
                """
                UPDATE vip_users SET active = 0, deactivated_at = ?
                WHERE email = ? AND active = 1
                """,
                (_now(), email),
            )
        return cur.rowcount > 0

    def activate_vip(self, email: str, plan: str) -> dict[str, Any] | None:
        expires_at = _expires_from_plan(plan)
        return self.upsert_vip(email, plan, expires_at)

    def get_stats(self) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        with self._conn() as conn:
            pending = conn.execute(
                "SELECT COUNT(*) AS c FROM payment_requests WHERE status = 'pending'"
            ).fetchone()["c"]
            vips = conn.execute("SELECT email, plan, expires_at, active FROM vip_users").fetchall()
        active = 0
        revenue = 0
        for v in vips:
            if v["active"]:
                try:
                    exp = datetime.strptime(v["expires_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
                        tzinfo=timezone.utc
                    )
                    if exp > now:
                        active += 1
                except ValueError:
                    active += 1
            if v["plan"] in PLAN_PRICE:
                revenue += PLAN_PRICE[v["plan"]]
        return {"pending": pending, "active_vips": active, "revenue_estimate": revenue}

    def get_picker(self) -> list[Any]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = 'content_picker'"
            ).fetchone()
        if not row:
            return []
        import json

        try:
            data = json.loads(row["value"])
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []

    def set_picker(self, items: list[Any]) -> list[Any]:
        import json

        payload = json.dumps(items)
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO settings (key, value, updated_at) VALUES ('content_picker', ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (payload, _now()),
            )
        return items

    @staticmethod
    def gen_code16() -> str:
        return "".join(str(secrets.randbelow(10)) for _ in range(16))

    def save_oauth_state(self, state: str, return_to: str, ttl_seconds: int = 600) -> None:
        exp = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        expires_at = exp.strftime("%Y-%m-%dT%H:%M:%SZ")
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO oauth_states (state, return_to, expires_at) VALUES (?, ?, ?)",
                (state, return_to, expires_at),
            )

    def pop_oauth_state(self, state: str) -> str | None:
        now = _now()
        with self._conn() as conn:
            row = conn.execute(
                "SELECT return_to FROM oauth_states WHERE state = ? AND expires_at > ?",
                (state, now),
            ).fetchone()
            conn.execute("DELETE FROM oauth_states WHERE state = ?", (state,))
        return row["return_to"] if row else None

    def create_cms_session(self, profile: dict[str, Any], ttl_seconds: int) -> str:
        import json

        sid = secrets.token_urlsafe(32)
        exp = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        expires_at = exp.strftime("%Y-%m-%dT%H:%M:%SZ")
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO cms_sessions (sid, payload, expires_at) VALUES (?, ?, ?)",
                (sid, json.dumps(profile), expires_at),
            )
        return sid

    def get_cms_session(self, sid: str) -> dict[str, Any] | None:
        import json

        now = _now()
        with self._conn() as conn:
            row = conn.execute(
                "SELECT payload FROM cms_sessions WHERE sid = ? AND expires_at > ?",
                (sid, now),
            ).fetchone()
        if not row:
            return None
        try:
            return json.loads(row["payload"])
        except json.JSONDecodeError:
            return None

    def delete_cms_session(self, sid: str) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM cms_sessions WHERE sid = ?", (sid,))