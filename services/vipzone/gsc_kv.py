"""SQLite-backed async key-value store for the GSC router on the VIPZone service.

The shared GSC router (services/visitor-counter/gsc_routes.py) was written against
a Redis async client (`get`/`set`/`setex`/`getdel`/`delete`). The VIPZone service —
the one actually deployed as `blog-vipzone-api` (render.yaml `rootDir: services/vipzone`)
— has no Redis, only the ephemeral SQLite DB. This shim exposes the exact subset of
the async Redis interface the GSC router needs, persisted in a `gsc_kv` table next to
the VIPZone tables so OAuth state + the metrics cache survive process restarts.

Durability note: on Render free tier the SQLite file lives at /tmp (lost on redeploy),
so the GSC refresh token also falls back to the GSC_REFRESH_TOKEN env var inside the
router (`_load_refresh_token`). The OAuth flow re-mints + persists a token here; for a
fully durable token set GSC_REFRESH_TOKEN in the service env (an existing GSC env).
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path


class SqliteKV:
    """Minimal async KV (str values) compatible with the GSC router's Redis calls."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS gsc_kv (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    expires_at REAL
                )
                """
            )

    def _conn(self):
        conn = sqlite3.connect(self.path, timeout=10)
        return conn

    @staticmethod
    def _fresh(row) -> bool:
        """A row is live when it has no expiry or the expiry is still in the future."""
        if row is None:
            return False
        expires_at = row[1]
        return expires_at is None or expires_at > time.time()

    async def get(self, key: str):
        with self._conn() as conn:
            row = conn.execute(
                "SELECT value, expires_at FROM gsc_kv WHERE key = ?", (key,)
            ).fetchone()
            if row is None:
                return None
            if not self._fresh(row):
                conn.execute("DELETE FROM gsc_kv WHERE key = ?", (key,))
                return None
            return row[0]

    async def set(self, key: str, value: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO gsc_kv (key, value, expires_at) VALUES (?, ?, NULL) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, expires_at = NULL",
                (key, str(value)),
            )

    async def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        expires_at = time.time() + max(1, int(ttl_seconds))
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO gsc_kv (key, value, expires_at) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
                "expires_at = excluded.expires_at",
                (key, str(value), expires_at),
            )

    async def getdel(self, key: str):
        with self._conn() as conn:
            row = conn.execute(
                "SELECT value, expires_at FROM gsc_kv WHERE key = ?", (key,)
            ).fetchone()
            conn.execute("DELETE FROM gsc_kv WHERE key = ?", (key,))
            return row[0] if self._fresh(row) else None

    async def delete(self, key: str) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM gsc_kv WHERE key = ?", (key,))
