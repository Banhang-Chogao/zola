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
                -- Private personal Calendar — durable server-side store (never a
                -- cookie / public static file). Rows are scoped by `owner` (the
                -- GitHub-verified email of the authenticated admin), so clearing
                -- cookies only drops the session: re-login restores every event.
                CREATE TABLE IF NOT EXISTS calendar_events (
                    id TEXT PRIMARY KEY,
                    owner TEXT NOT NULL,
                    title TEXT NOT NULL DEFAULT '',
                    start TEXT NOT NULL DEFAULT '',
                    end TEXT NOT NULL DEFAULT '',
                    all_day INTEGER NOT NULL DEFAULT 0,
                    color TEXT NOT NULL DEFAULT 'teal',
                    location TEXT NOT NULL DEFAULT '',
                    notes TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_calendar_owner ON calendar_events(owner);
                -- Private "3M Whiteboard" sticky notes — same durable, owner-scoped
                -- store. `order_index` keeps the pinned-note ordering stable.
                CREATE TABLE IF NOT EXISTS whiteboard_notes (
                    id TEXT PRIMARY KEY,
                    owner TEXT NOT NULL,
                    text TEXT NOT NULL DEFAULT '',
                    color TEXT NOT NULL DEFAULT 'yellow',
                    order_index INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_whiteboard_owner ON whiteboard_notes(owner);
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

    # ============= Private Calendar (owner-scoped, durable) =============
    @staticmethod
    def _event_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        """Map a DB row to the shape the frontend calendar app consumes directly."""
        return {
            "id": row["id"],
            "title": row["title"],
            "start": row["start"],
            "end": row["end"],
            "allDay": bool(row["all_day"]),
            "color": row["color"],
            "location": row["location"],
            "notes": row["notes"],
            "status": row["status"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }

    def list_calendar_events(self, owner: str) -> list[dict[str, Any]]:
        owner = (owner or "").lower().strip()
        if not owner:
            return []
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM calendar_events WHERE owner = ? ORDER BY start ASC",
                (owner,),
            ).fetchall()
        return [self._event_row_to_dict(r) for r in rows]

    def get_calendar_event(self, owner: str, event_id: str) -> dict[str, Any] | None:
        owner = (owner or "").lower().strip()
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM calendar_events WHERE owner = ? AND id = ?",
                (owner, event_id),
            ).fetchone()
        return self._event_row_to_dict(row) if row else None

    def create_calendar_event(self, owner: str, data: dict[str, Any]) -> dict[str, Any]:
        owner = (owner or "").lower().strip()
        eid = data.get("id") or f"ev_{uuid.uuid4().hex[:16]}"
        now = _now()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO calendar_events
                    (id, owner, title, start, end, all_day, color, location, notes, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    eid, owner,
                    data.get("title", ""), data.get("start", ""), data.get("end", ""),
                    1 if data.get("allDay") else 0,
                    data.get("color", "teal"), data.get("location", ""),
                    data.get("notes", ""), data.get("status", ""),
                    now, now,
                ),
            )
        return self.get_calendar_event(owner, eid)  # type: ignore[return-value]

    def update_calendar_event(
        self, owner: str, event_id: str, data: dict[str, Any]
    ) -> dict[str, Any] | None:
        owner = (owner or "").lower().strip()
        existing = self.get_calendar_event(owner, event_id)
        if not existing:
            return None
        merged = {**existing, **{k: v for k, v in data.items() if v is not None}}
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE calendar_events
                SET title = ?, start = ?, end = ?, all_day = ?, color = ?,
                    location = ?, notes = ?, status = ?, updated_at = ?
                WHERE owner = ? AND id = ?
                """,
                (
                    merged.get("title", ""), merged.get("start", ""), merged.get("end", ""),
                    1 if merged.get("allDay") else 0,
                    merged.get("color", "teal"), merged.get("location", ""),
                    merged.get("notes", ""), merged.get("status", ""),
                    _now(), owner, event_id,
                ),
            )
        return self.get_calendar_event(owner, event_id)

    def delete_calendar_event(self, owner: str, event_id: str) -> bool:
        owner = (owner or "").lower().strip()
        with self._conn() as conn:
            cur = conn.execute(
                "DELETE FROM calendar_events WHERE owner = ? AND id = ?",
                (owner, event_id),
            )
        return cur.rowcount > 0

    # ============= Private Whiteboard sticky notes (owner-scoped, durable) =============
    @staticmethod
    def _note_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "text": row["text"],
            "color": row["color"],
            "order": row["order_index"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }

    def list_whiteboard_notes(self, owner: str) -> list[dict[str, Any]]:
        owner = (owner or "").lower().strip()
        if not owner:
            return []
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM whiteboard_notes WHERE owner = ? ORDER BY order_index ASC, created_at ASC",
                (owner,),
            ).fetchall()
        return [self._note_row_to_dict(r) for r in rows]

    def get_whiteboard_note(self, owner: str, note_id: str) -> dict[str, Any] | None:
        owner = (owner or "").lower().strip()
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM whiteboard_notes WHERE owner = ? AND id = ?",
                (owner, note_id),
            ).fetchone()
        return self._note_row_to_dict(row) if row else None

    def create_whiteboard_note(self, owner: str, data: dict[str, Any]) -> dict[str, Any]:
        owner = (owner or "").lower().strip()
        nid = data.get("id") or f"note_{uuid.uuid4().hex[:16]}"
        now = _now()
        # Default new notes to the end of the board unless an order is given.
        order = data.get("order")
        if order is None:
            with self._conn() as conn:
                row = conn.execute(
                    "SELECT COALESCE(MAX(order_index), -1) + 1 AS nxt FROM whiteboard_notes WHERE owner = ?",
                    (owner,),
                ).fetchone()
            order = row["nxt"] if row else 0
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO whiteboard_notes
                    (id, owner, text, color, order_index, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    nid, owner, data.get("text", ""), data.get("color", "yellow"),
                    int(order), now, now,
                ),
            )
        return self.get_whiteboard_note(owner, nid)  # type: ignore[return-value]

    def update_whiteboard_note(
        self, owner: str, note_id: str, data: dict[str, Any]
    ) -> dict[str, Any] | None:
        owner = (owner or "").lower().strip()
        existing = self.get_whiteboard_note(owner, note_id)
        if not existing:
            return None
        merged = {**existing, **{k: v for k, v in data.items() if v is not None}}
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE whiteboard_notes
                SET text = ?, color = ?, order_index = ?, updated_at = ?
                WHERE owner = ? AND id = ?
                """,
                (
                    merged.get("text", ""), merged.get("color", "yellow"),
                    int(merged.get("order", 0)), _now(), owner, note_id,
                ),
            )
        return self.get_whiteboard_note(owner, note_id)

    def delete_whiteboard_note(self, owner: str, note_id: str) -> bool:
        owner = (owner or "").lower().strip()
        with self._conn() as conn:
            cur = conn.execute(
                "DELETE FROM whiteboard_notes WHERE owner = ? AND id = ?",
                (owner, note_id),
            )
        return cur.rowcount > 0