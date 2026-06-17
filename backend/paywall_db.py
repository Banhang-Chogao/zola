"""SQLite persistence for Paywall."""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "data" / "paywall.db"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class PaywallDB:
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
                CREATE TABLE IF NOT EXISTS access_requests (
                    request_id TEXT PRIMARY KEY,
                    post_id TEXT NOT NULL,
                    post_title TEXT NOT NULL,
                    post_url TEXT NOT NULL,
                    email TEXT NOT NULL,
                    payment_method TEXT NOT NULL DEFAULT 'momo',
                    payment_link TEXT NOT NULL,
                    payment_note TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS approve_codes (
                    code_id TEXT PRIMARY KEY,
                    approve_code_hash TEXT NOT NULL,
                    email TEXT NOT NULL,
                    post_id TEXT NOT NULL,
                    post_url TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    expires_at TEXT NOT NULL,
                    max_usage INTEGER NOT NULL,
                    usage_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS access_sessions (
                    token_hash TEXT PRIMARY KEY,
                    email TEXT NOT NULL,
                    post_id TEXT NOT NULL,
                    trace_code TEXT NOT NULL,
                    reader_email_hash TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS access_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event TEXT NOT NULL,
                    post_id TEXT,
                    email_hash TEXT,
                    meta TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_requests_status ON access_requests(status);
                CREATE INDEX IF NOT EXISTS idx_codes_post_email ON approve_codes(post_id, email);
                """
            )

    def insert_request(self, data: dict[str, Any]) -> str:
        rid = str(uuid.uuid4())
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO access_requests
                (request_id, post_id, post_title, post_url, email, payment_method,
                 payment_link, payment_note, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
                """,
                (
                    rid,
                    data["post_id"],
                    data["post_title"],
                    data["post_url"],
                    data["email"].lower().strip(),
                    data.get("payment_method", "momo"),
                    data["payment_link"],
                    data.get("payment_note", ""),
                    _now(),
                ),
            )
        return rid

    def list_requests(self, status: str | None = None) -> list[dict[str, Any]]:
        with self._conn() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM access_requests WHERE status = ? ORDER BY created_at DESC",
                    (status,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM access_requests ORDER BY created_at DESC"
                ).fetchall()
        return [dict(r) for r in rows]

    def update_request_status(self, request_id: str, status: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE access_requests SET status = ? WHERE request_id = ?",
                (status, request_id),
            )

    def insert_code(self, data: dict[str, Any]) -> str:
        cid = str(uuid.uuid4())
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO approve_codes
                (code_id, approve_code_hash, email, post_id, post_url, status,
                 expires_at, max_usage, usage_count, created_at)
                VALUES (?, ?, ?, ?, ?, 'active', ?, ?, 0, ?)
                """,
                (
                    cid,
                    data["approve_code_hash"],
                    data["email"].lower().strip(),
                    data["post_id"],
                    data["post_url"],
                    data["expires_at"],
                    data["max_usage"],
                    _now(),
                ),
            )
        return cid

    def get_code_for_unlock(
        self, email: str, post_id: str
    ) -> list[sqlite3.Row]:
        with self._conn() as conn:
            return conn.execute(
                """
                SELECT * FROM approve_codes
                WHERE email = ? AND post_id = ? AND status = 'active'
                ORDER BY created_at DESC
                """,
                (email.lower().strip(), post_id),
            ).fetchall()

    def increment_code_usage(self, code_id: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE approve_codes SET usage_count = usage_count + 1 WHERE code_id = ?",
                (code_id,),
            )

    def get_code_by_id(self, code_id: str) -> dict[str, Any] | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM approve_codes WHERE code_id = ?", (code_id,)
            ).fetchone()
        return dict(row) if row else None

    def insert_session(self, data: dict[str, Any]) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO access_sessions
                (token_hash, email, post_id, trace_code, reader_email_hash, expires_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["token_hash"],
                    data["email"],
                    data["post_id"],
                    data["trace_code"],
                    data["reader_email_hash"],
                    data["expires_at"],
                    _now(),
                ),
            )

    def get_session(self, token_hash: str) -> dict[str, Any] | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM access_sessions WHERE token_hash = ?",
                (token_hash,),
            ).fetchone()
        return dict(row) if row else None

    def log_event(
        self, event: str, *, post_id: str = "", email_hash: str = "", meta: dict | None = None
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO access_logs (event, post_id, email_hash, meta, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (event, post_id, email_hash, json.dumps(meta or {}), _now()),
            )

    @staticmethod
    def expires_from_days(days: int) -> str:
        if days >= 3650:
            return (datetime.now(timezone.utc) + timedelta(days=3650)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
        return (datetime.now(timezone.utc) + timedelta(days=days)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )