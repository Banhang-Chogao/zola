"""SQLite persistence for ShortenSEA short links."""

from __future__ import annotations

import json
import secrets
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB = ROOT / "data" / "shortensea.db"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


class ShortenDB:
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
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    email TEXT,
                    username TEXT NOT NULL UNIQUE,
                    name TEXT,
                    avatar TEXT,
                    plan TEXT NOT NULL DEFAULT 'free',
                    plan_expires_at TEXT,
                    locked_until TEXT,
                    links_month_key TEXT,
                    links_month_count INTEGER NOT NULL DEFAULT 0,
                    custom_halves_used INTEGER NOT NULL DEFAULT 0,
                    is_super INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS links (
                    link_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    slug TEXT NOT NULL UNIQUE,
                    destination_url TEXT NOT NULL,
                    title TEXT,
                    tags TEXT,
                    domain TEXT NOT NULL,
                    utm_source TEXT,
                    utm_medium TEXT,
                    utm_campaign TEXT,
                    utm_term TEXT,
                    utm_content TEXT,
                    expires_at TEXT,
                    qr_enabled INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'active',
                    click_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS clicks (
                    click_id TEXT PRIMARY KEY,
                    link_id TEXT NOT NULL,
                    ts TEXT NOT NULL,
                    referrer TEXT,
                    device TEXT,
                    browser TEXT,
                    country TEXT,
                    city TEXT,
                    is_qr INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS approve_codes (
                    code_id TEXT PRIMARY KEY,
                    code_hash TEXT NOT NULL,
                    plan_type TEXT NOT NULL,
                    email TEXT,
                    user_id TEXT,
                    expiry_days INTEGER NOT NULL,
                    used INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    redeemed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS oauth_states (
                    state TEXT PRIMARY KEY,
                    return_to TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS payment_requests (
                    request_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    email TEXT NOT NULL,
                    plan_type TEXT NOT NULL,
                    payment_note TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    resolved_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_links_user ON links(user_id);
                CREATE INDEX IF NOT EXISTS idx_links_slug ON links(slug);
                CREATE INDEX IF NOT EXISTS idx_clicks_link ON clicks(link_id);
                CREATE INDEX IF NOT EXISTS idx_codes_hash ON approve_codes(code_hash);
                """
            )
            self._migrate_schema(conn)

    def _migrate_schema(self, conn: sqlite3.Connection) -> None:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "is_guest" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN is_guest INTEGER NOT NULL DEFAULT 0")

    def get_or_create_user(
        self,
        *,
        username: str,
        email: str | None,
        name: str | None,
        avatar: str | None,
        is_super: bool = False,
    ) -> dict[str, Any]:
        username = username.strip().lower()
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchone()
            now = _now()
            if row:
                user = dict(row)
                if is_super and not user["is_super"]:
                    conn.execute(
                        "UPDATE users SET is_super = 1, plan = 'super', plan_expires_at = NULL, updated_at = ? WHERE user_id = ?",
                        (now, user["user_id"]),
                    )
                    user["is_super"] = 1
                    user["plan"] = "super"
                    user["plan_expires_at"] = None
                self._apply_expiry_logic(conn, user["user_id"])
                return dict(
                    conn.execute(
                        "SELECT * FROM users WHERE user_id = ?", (user["user_id"],)
                    ).fetchone()
                )

            uid = str(uuid.uuid4())
            plan = "super" if is_super else "free"
            conn.execute(
                """
                INSERT INTO users
                (user_id, email, username, name, avatar, plan, links_month_key, created_at, updated_at, is_super)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    uid,
                    (email or "").lower() or None,
                    username,
                    name or username,
                    avatar,
                    plan,
                    datetime.now(timezone.utc).strftime("%Y-%m"),
                    now,
                    now,
                    1 if is_super else 0,
                ),
            )
            return dict(conn.execute("SELECT * FROM users WHERE user_id = ?", (uid,)).fetchone())

    def create_session(self, user_id: str, ttl_seconds: int) -> str:
        sid = secrets.token_urlsafe(32)
        exp = (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO sessions (session_id, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
                (sid, user_id, exp, _now()),
            )
        return sid

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT s.*, u.* FROM sessions s JOIN users u ON s.user_id = u.user_id WHERE s.session_id = ?",
                (session_id,),
            ).fetchone()
            if not row:
                return None
            data = dict(row)
            exp = _parse_dt(data.get("expires_at"))
            if exp and datetime.now(timezone.utc) > exp:
                conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
                return None
            self._apply_expiry_logic(conn, data["user_id"])
            return dict(
                conn.execute(
                    "SELECT s.session_id, u.* FROM sessions s JOIN users u ON s.user_id = u.user_id WHERE s.session_id = ?",
                    (session_id,),
                ).fetchone()
            )

    def delete_session(self, session_id: str) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))

    def _apply_expiry_logic(self, conn: sqlite3.Connection, user_id: str) -> None:
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            return
        user = dict(row)
        if user["is_super"] or user["plan"] in ("free", "super"):
            if user["plan"] == "super":
                return
            return

        now = datetime.now(timezone.utc)
        exp = _parse_dt(user.get("plan_expires_at"))
        locked = _parse_dt(user.get("locked_until"))

        if exp and now > exp:
            if not locked:
                lock_until = (exp + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
                conn.execute(
                    "UPDATE users SET locked_until = ?, plan = 'locked_premium', updated_at = ? WHERE user_id = ?",
                    (lock_until, _now(), user_id),
                )
            elif locked and now > locked:
                conn.execute(
                    "UPDATE users SET plan = 'free', locked_until = NULL, plan_expires_at = NULL, updated_at = ? WHERE user_id = ?",
                    (_now(), user_id),
                )

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        with self._conn() as conn:
            self._apply_expiry_logic(conn, user_id)
            row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            return dict(row) if row else None

    def upgrade_user(self, user_id: str, plan: str, days: int) -> dict[str, Any]:
        exp = (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE users SET plan = ?, plan_expires_at = ?, locked_until = NULL,
                custom_halves_used = 0, updated_at = ? WHERE user_id = ?
                """,
                (plan, exp, _now(), user_id),
            )
            row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            return dict(row)

    def reset_monthly_counter_if_needed(self, user: dict[str, Any]) -> dict[str, Any]:
        month_key = datetime.now(timezone.utc).strftime("%Y-%m")
        if user.get("links_month_key") == month_key:
            return user
        with self._conn() as conn:
            conn.execute(
                "UPDATE users SET links_month_key = ?, links_month_count = 0, updated_at = ? WHERE user_id = ?",
                (month_key, _now(), user["user_id"]),
            )
            row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user["user_id"],)).fetchone()
            return dict(row)

    def slug_exists(self, slug: str) -> bool:
        with self._conn() as conn:
            row = conn.execute("SELECT 1 FROM links WHERE slug = ?", (slug.lower(),)).fetchone()
            return row is not None

    def insert_link(self, data: dict[str, Any]) -> dict[str, Any]:
        lid = str(uuid.uuid4())
        now = _now()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO links
                (link_id, user_id, slug, destination_url, title, tags, domain,
                 utm_source, utm_medium, utm_campaign, utm_term, utm_content,
                 expires_at, qr_enabled, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
                """,
                (
                    lid,
                    data["user_id"],
                    data["slug"].lower(),
                    data["destination_url"],
                    data.get("title"),
                    json.dumps(data.get("tags") or []),
                    data["domain"],
                    data.get("utm_source"),
                    data.get("utm_medium"),
                    data.get("utm_campaign"),
                    data.get("utm_term"),
                    data.get("utm_content"),
                    data.get("expires_at"),
                    1 if data.get("qr_enabled") else 0,
                    now,
                    now,
                ),
            )
            conn.execute(
                "UPDATE users SET links_month_count = links_month_count + 1, updated_at = ? WHERE user_id = ?",
                (now, data["user_id"]),
            )
            if data.get("custom_slug"):
                conn.execute(
                    "UPDATE users SET custom_halves_used = custom_halves_used + 1, updated_at = ? WHERE user_id = ?",
                    (now, data["user_id"]),
                )
            row = conn.execute("SELECT * FROM links WHERE link_id = ?", (lid,)).fetchone()
            return dict(row)

    def list_links(self, user_id: str) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM links WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_link_by_slug(self, slug: str) -> dict[str, Any] | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM links WHERE slug = ?", (slug.lower(),)).fetchone()
            return dict(row) if row else None

    def get_link(self, link_id: str, user_id: str) -> dict[str, Any] | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM links WHERE link_id = ? AND user_id = ?",
                (link_id, user_id),
            ).fetchone()
            return dict(row) if row else None

    def update_link(self, link_id: str, user_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        now = _now()
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM links WHERE link_id = ? AND user_id = ?",
                (link_id, user_id),
            ).fetchone()
            if not row:
                return None
            conn.execute(
                """
                UPDATE links SET destination_url = ?, title = ?, tags = ?, status = ?,
                utm_source = ?, utm_medium = ?, utm_campaign = ?, utm_term = ?, utm_content = ?,
                expires_at = ?, qr_enabled = ?, updated_at = ? WHERE link_id = ?
                """,
                (
                    data.get("destination_url", row["destination_url"]),
                    data.get("title", row["title"]),
                    json.dumps(data.get("tags") if "tags" in data else json.loads(row["tags"] or "[]")),
                    data.get("status", row["status"]),
                    data.get("utm_source", row["utm_source"]),
                    data.get("utm_medium", row["utm_medium"]),
                    data.get("utm_campaign", row["utm_campaign"]),
                    data.get("utm_term", row["utm_term"]),
                    data.get("utm_content", row["utm_content"]),
                    data.get("expires_at", row["expires_at"]),
                    1 if data.get("qr_enabled", row["qr_enabled"]) else 0,
                    now,
                    link_id,
                ),
            )
            updated = conn.execute("SELECT * FROM links WHERE link_id = ?", (link_id,)).fetchone()
            return dict(updated)

    def delete_link(self, link_id: str, user_id: str) -> bool:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT link_id FROM links WHERE link_id = ? AND user_id = ?",
                (link_id, user_id),
            ).fetchone()
            if not row:
                return False
            conn.execute("DELETE FROM clicks WHERE link_id = ?", (link_id,))
            conn.execute("DELETE FROM links WHERE link_id = ?", (link_id,))
            return True

    def record_click(self, link_id: str, meta: dict[str, Any]) -> None:
        cid = str(uuid.uuid4())
        now = _now()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO clicks (click_id, link_id, ts, referrer, device, browser, country, city, is_qr)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cid,
                    link_id,
                    now,
                    meta.get("referrer"),
                    meta.get("device"),
                    meta.get("browser"),
                    meta.get("country"),
                    meta.get("city"),
                    1 if meta.get("is_qr") else 0,
                ),
            )
            conn.execute(
                "UPDATE links SET click_count = click_count + 1, updated_at = ? WHERE link_id = ?",
                (now, link_id),
            )

    def get_insights(self, user_id: str) -> dict[str, Any]:
        with self._conn() as conn:
            links = conn.execute(
                "SELECT link_id, slug, title, click_count FROM links WHERE user_id = ?",
                (user_id,),
            ).fetchall()
            link_ids = [r["link_id"] for r in links]
            total_clicks = sum(r["click_count"] for r in links) if links else 0

            clicks_by_link = [
                {"slug": r["slug"], "title": r["title"], "clicks": r["click_count"]}
                for r in sorted(links, key=lambda x: x["click_count"], reverse=True)
            ]

            if not link_ids:
                return {
                    "total_clicks": 0,
                    "clicks_by_link": [],
                    "clicks_by_day": [],
                    "referrers": [],
                    "devices": [],
                    "browsers": [],
                    "countries": [],
                    "top_links": [],
                    "qr_scans": 0,
                }

            placeholders = ",".join("?" * len(link_ids))
            clicks = conn.execute(
                f"SELECT * FROM clicks WHERE link_id IN ({placeholders})",
                link_ids,
            ).fetchall()

            by_day: dict[str, int] = {}
            referrers: dict[str, int] = {}
            devices: dict[str, int] = {}
            browsers: dict[str, int] = {}
            countries: dict[str, int] = {}
            qr_scans = 0

            for c in clicks:
                day = (c["ts"] or "")[:10]
                by_day[day] = by_day.get(day, 0) + 1
                ref = c["referrer"] or "(direct)"
                referrers[ref] = referrers.get(ref, 0) + 1
                dev = c["device"] or "unknown"
                devices[dev] = devices.get(dev, 0) + 1
                br = c["browser"] or "unknown"
                browsers[br] = browsers.get(br, 0) + 1
                co = c["country"] or "unknown"
                countries[co] = countries.get(co, 0) + 1
                if c["is_qr"]:
                    qr_scans += 1

            def top_items(d: dict[str, int], n: int = 10) -> list[dict[str, Any]]:
                return [{"name": k, "count": v} for k, v in sorted(d.items(), key=lambda x: -x[1])[:n]]

            return {
                "total_clicks": total_clicks,
                "clicks_by_link": clicks_by_link[:20],
                "clicks_by_day": [{"date": k, "clicks": v} for k, v in sorted(by_day.items())],
                "referrers": top_items(referrers),
                "devices": top_items(devices),
                "browsers": top_items(browsers),
                "countries": top_items(countries),
                "top_links": clicks_by_link[:10],
                "qr_scans": qr_scans,
            }

    def insert_approve_code(self, data: dict[str, Any]) -> str:
        cid = str(uuid.uuid4())
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO approve_codes
                (code_id, code_hash, plan_type, email, user_id, expiry_days, used, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?)
                """,
                (
                    cid,
                    data["code_hash"],
                    data["plan_type"],
                    data.get("email"),
                    data.get("user_id"),
                    data["expiry_days"],
                    _now(),
                ),
            )
        return cid

    def redeem_code(self, code_hash: str, user: dict[str, Any]) -> dict[str, Any] | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM approve_codes WHERE code_hash = ? AND used = 0",
                (code_hash,),
            ).fetchone()
            if not row:
                return None
            code = dict(row)
            if code.get("email") and user.get("email"):
                if code["email"].lower() != (user["email"] or "").lower():
                    return None
            if code.get("user_id") and code["user_id"] != user["user_id"]:
                return None
            conn.execute(
                "UPDATE approve_codes SET used = 1, redeemed_at = ? WHERE code_id = ?",
                (_now(), code["code_id"]),
            )
            return code

    def list_approve_codes(self) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT code_id, plan_type, email, user_id, expiry_days, used, created_at, redeemed_at FROM approve_codes ORDER BY created_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def save_oauth_state(self, state: str, return_to: str, ttl_seconds: int = 600) -> None:
        exp = (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO oauth_states (state, return_to, expires_at) VALUES (?, ?, ?)",
                (state, return_to, exp),
            )

    def pop_oauth_state(self, state: str) -> str | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT return_to, expires_at FROM oauth_states WHERE state = ?", (state,)
            ).fetchone()
            conn.execute("DELETE FROM oauth_states WHERE state = ?", (state,))
            if not row:
                return None
            exp = _parse_dt(row["expires_at"])
            if exp and datetime.now(timezone.utc) > exp:
                return None
            return row["return_to"]

    def create_guest_user(self) -> dict[str, Any]:
        uid = str(uuid.uuid4())
        username = f"guest-{uid[:12]}"
        now = _now()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO users
                (user_id, email, username, name, avatar, plan, links_month_key,
                 created_at, updated_at, is_super, is_guest)
                VALUES (?, NULL, ?, 'Khách', NULL, 'free', ?, ?, ?, 0, 1)
                """,
                (uid, username, datetime.now(timezone.utc).strftime("%Y-%m"), now, now),
            )
            return dict(conn.execute("SELECT * FROM users WHERE user_id = ?", (uid,)).fetchone())

    def insert_payment_request(self, data: dict[str, Any]) -> str:
        rid = str(uuid.uuid4())
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO payment_requests
                (request_id, user_id, email, plan_type, payment_note, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'pending', ?)
                """,
                (
                    rid,
                    data.get("user_id"),
                    data["email"].lower().strip(),
                    data["plan_type"],
                    (data.get("payment_note") or "").strip() or None,
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

    def resolve_payment_request(self, request_id: str, status: str = "resolved") -> bool:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT request_id FROM payment_requests WHERE request_id = ?", (request_id,)
            ).fetchone()
            if not row:
                return False
            conn.execute(
                "UPDATE payment_requests SET status = ?, resolved_at = ? WHERE request_id = ?",
                (status, _now(), request_id),
            )
            return True

    def list_users(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT user_id, email, username, name, plan, plan_expires_at, locked_until,
                       links_month_count, custom_halves_used, is_super, is_guest, created_at
                FROM users ORDER BY created_at DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def admin_override_plan(
        self, user_id: str, plan: str, days: int | None = None, is_super: bool | None = None
    ) -> dict[str, Any] | None:
        now = _now()
        with self._conn() as conn:
            row = conn.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if not row:
                return None
            if is_super is not None:
                conn.execute(
                    "UPDATE users SET is_super = ?, plan = ?, plan_expires_at = NULL, locked_until = NULL, updated_at = ? WHERE user_id = ?",
                    (1 if is_super else 0, "super" if is_super else plan, now, user_id),
                )
            elif plan == "free":
                conn.execute(
                    "UPDATE users SET plan = 'free', plan_expires_at = NULL, locked_until = NULL, updated_at = ? WHERE user_id = ?",
                    (now, user_id),
                )
            else:
                exp = None
                if days:
                    exp = (datetime.now(timezone.utc) + timedelta(days=days)).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    )
                conn.execute(
                    "UPDATE users SET plan = ?, plan_expires_at = ?, locked_until = NULL, updated_at = ? WHERE user_id = ?",
                    (plan, exp, now, user_id),
                )
            updated = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            return dict(updated) if updated else None

    def set_user_email(self, user_id: str, email: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE users SET email = ?, updated_at = ? WHERE user_id = ?",
                (email.lower().strip(), _now(), user_id),
            )