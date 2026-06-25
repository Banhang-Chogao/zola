"""WD Heartbeat Stats backend — deploy telemetry ingest + stats API.

Companion to the calm-first ``.wd-heartbeat`` footer module. The footer renders
from a build-time JSON (static-site safe); this backend is the *live* source the
CI/CD pipeline can POST to and that richer clients can poll.

Endpoints:
- ``POST /api/heartbeat``         — ingest one deploy event (webhook-secret auth).
- ``GET  /api/heartbeat/stats``   — totals + 30-day heatmap (5-minute cache).

Storage: SQLite table ``wd_deployments`` (id, status, timestamp, commit_hash,
duration). Mirrors the aggregation contract of scripts/wd_heartbeat_stats.py so
the static and live payloads share one shape. Doctrine V27: never fake numbers —
an empty table returns ``configured: false`` with zeroed totals, not invented data.
"""
from __future__ import annotations

import hmac
import os
import sqlite3
import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

router = APIRouter(tags=["wd-heartbeat"])

ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = Path(os.getenv("WD_HEARTBEAT_DB", str(ROOT / "data" / "vipzone.db")))
WINDOW_DAYS = 30
CACHE_TTL = int(os.getenv("WD_HEARTBEAT_CACHE_TTL", "300"))  # 5 minutes
REPO = os.getenv("WD_HEARTBEAT_REPO", "Banhang-Chogao/zola")

FAILURE_STATUSES = {"failed", "failure", "timed_out", "startup_failure"}
SUCCESS_STATUSES = {"success", "succeeded"}

_CACHE: dict[str, Any] = {"payload": None, "until": 0.0}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_schema() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS wd_deployments (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                status      TEXT NOT NULL,
                timestamp   TEXT NOT NULL,
                commit_hash TEXT,
                duration    INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_wd_deploy_ts
                ON wd_deployments (timestamp);
            """
        )
        conn.commit()


_init_schema()


class DeployEvent(BaseModel):
    status: str = Field(..., description="'success' or 'failed' (or raw CI conclusion)")
    timestamp: str | None = Field(None, description="ISO-8601; defaults to now (UTC)")
    commit_hash: str | None = Field(None, max_length=64)
    duration: int = Field(0, ge=0, description="deploy duration in seconds")


def _normalize_status(raw: str) -> str:
    s = (raw or "").strip().lower()
    if s in SUCCESS_STATUSES:
        return "success"
    if s in FAILURE_STATUSES:
        return "failed"
    if s in {"cancelled", "skipped"}:
        return "cancelled"
    return s or "unknown"


def _parse_ts(value: str | None) -> datetime:
    if not value:
        return _now()
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return _now()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _level(count: int, busiest: int) -> int:
    if count <= 0 or busiest <= 0:
        return 0
    ratio = count / busiest
    level = 1
    for threshold in (0.25, 0.5, 0.75):
        if ratio > threshold:
            level += 1
    return min(level, 4)


def insert_event(event: DeployEvent) -> int:
    status = _normalize_status(event.status)
    ts = _iso(_parse_ts(event.timestamp))
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO wd_deployments (status, timestamp, commit_hash, duration)"
            " VALUES (?, ?, ?, ?)",
            (status, ts, event.commit_hash, int(event.duration or 0)),
        )
        conn.commit()
        return int(cur.lastrowid)


def build_stats(now: datetime | None = None) -> dict[str, Any]:
    now = now or _now()
    window_start = (now - timedelta(days=WINDOW_DAYS - 1)).date()

    buckets: "OrderedDict[str, dict[str, int]]" = OrderedDict()
    for offset in range(WINDOW_DAYS):
        day = (window_start + timedelta(days=offset)).isoformat()
        buckets[day] = {"count": 0, "success": 0, "failed": 0}

    with _connect() as conn:
        rows = conn.execute(
            "SELECT status, timestamp, commit_hash, duration FROM wd_deployments"
        ).fetchall()

    success = failed = cancelled = 0
    last_row: sqlite3.Row | None = None
    last_dt: datetime | None = None
    for row in rows:
        status = row["status"]
        dt = _parse_ts(row["timestamp"])
        if last_dt is None or dt > last_dt:
            last_dt, last_row = dt, row
        if status == "success":
            success += 1
        elif status == "failed":
            failed += 1
        elif status == "cancelled":
            cancelled += 1
            continue
        day = dt.date().isoformat()
        if day in buckets:
            buckets[day]["count"] += 1
            if status == "success":
                buckets[day]["success"] += 1
            elif status == "failed":
                buckets[day]["failed"] += 1

    counted = success + failed
    success_rate = round(success / counted * 100) if counted else 0
    busiest = max((b["count"] for b in buckets.values()), default=0)

    days = [
        {
            "date": day,
            "count": d["count"],
            "success": d["success"],
            "failed": d["failed"],
            "level": _level(d["count"], busiest),
        }
        for day, d in buckets.items()
    ]

    last_deploy = None
    if last_row is not None and last_dt is not None:
        last_deploy = {
            "status": last_row["status"],
            "at": _iso(last_dt),
            "sha": (last_row["commit_hash"] or "")[:7],
            "duration_s": int(last_row["duration"] or 0),
        }

    return {
        "schema_version": 1,
        "generated_at": _iso(now),
        "repository": REPO,
        "window_days": WINDOW_DAYS,
        "configured": counted > 0,
        "totals": {
            "total": counted,
            "success": success,
            "failed": failed,
            "cancelled": cancelled,
            "success_rate_pct": success_rate,
        },
        "last_deploy": last_deploy,
        "heatmap": {"max": busiest, "days": days},
    }


def _check_secret(provided: str | None) -> None:
    secret = os.getenv("WD_HEARTBEAT_SECRET", "")
    if not secret:
        # No secret configured → refuse writes rather than accept anonymous data.
        raise HTTPException(status_code=503, detail="heartbeat ingest not configured")
    if not provided or not hmac.compare_digest(provided, secret):
        raise HTTPException(status_code=401, detail="invalid heartbeat secret")


@router.post("/api/heartbeat")
def post_heartbeat(
    event: DeployEvent,
    x_heartbeat_secret: str | None = Header(default=None),
) -> JSONResponse:
    _check_secret(x_heartbeat_secret)
    row_id = insert_event(event)
    _CACHE["payload"] = None  # invalidate cache on write
    _CACHE["until"] = 0.0
    return JSONResponse(
        {"ok": True, "id": row_id, "status": _normalize_status(event.status)},
        headers={"Cache-Control": "no-store"},
    )


@router.get("/api/heartbeat/stats")
def get_heartbeat_stats(fresh: bool = False) -> JSONResponse:
    now = time.time()
    if not fresh and _CACHE.get("payload") and now < float(_CACHE.get("until") or 0):
        payload = dict(_CACHE["payload"])
        payload["cache_state"] = "warm"
        return JSONResponse(
            payload,
            headers={
                "Cache-Control": f"public, max-age={CACHE_TTL}",
                "Access-Control-Allow-Origin": "*",
            },
        )

    payload = build_stats()
    _CACHE["payload"] = payload
    _CACHE["until"] = now + CACHE_TTL
    payload = dict(payload)
    payload["cache_state"] = "cold"
    return JSONResponse(
        payload,
        headers={
            "Cache-Control": f"public, max-age={CACHE_TTL}",
            "Access-Control-Allow-Origin": "*",
        },
    )
