#!/usr/bin/env python3
"""Heartbeat Stats generator (WWDC26 calm-first footer module).

Aggregates deploy-run history into a build-time JSON consumed by the
``.wd-heartbeat`` footer partial (templates/partials/wd-heartbeat.html):

- total deploys + success / failed counts + success rate
- last deploy (status, time, commit, duration)
- a GitHub-style 30-day frequency heatmap (coloured by *count*, never by
  success/fail — calm, single-accent design)

Doctrine (V27 — GA stats module): build-time analytics, **never fake numbers**,
emit a ``configured: false`` *pending* payload when no real data is available.
Cancelled runs are NOT counted as failures (V5 — cancelled = superseded).

Data sources, in priority order:
  1. env ``WD_RUNS_JSON``  — output of ``gh run list --json …`` (CI).
  2. env ``WD_RUNS_FILE``  — path to the same JSON on disk.
  3. ``data/deploy-monitor.json`` ``feed`` (local seed / offline fallback).

Usage::

    python3 scripts/wd_heartbeat_stats.py            # write data/wd-heartbeat-stats.json
    python3 scripts/wd_heartbeat_stats.py --stdout    # print, do not write
    gh run list --workflow deploy.yml --branch main --limit 200 \
      --json databaseId,headSha,conclusion,status,createdAt,updatedAt \
      | WD_RUNS_JSON="$(cat)" python3 scripts/wd_heartbeat_stats.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO = os.getenv("WD_HEARTBEAT_REPO", "Banhang-Chogao/zola")
WINDOW_DAYS = 30
OUT_PATH = Path("data/wd-heartbeat-stats.json")
SEED_PATH = Path("data/deploy-monitor.json")

# Heatmap "level" thresholds as a fraction of the busiest day (GitHub-style 0–4).
LEVEL_FRACTIONS = (0.0, 0.25, 0.5, 0.75)

# Conclusions that count as a genuine failure (cancelled excluded by design).
FAILURE_CONCLUSIONS = {"failure", "timed_out", "startup_failure"}
SUCCESS_CONCLUSIONS = {"success"}
CANCELLED_CONCLUSIONS = {"cancelled", "skipped"}


def _parse_ts(value: Any) -> datetime | None:
    """Parse an ISO-8601 timestamp (``…Z`` or offset) into aware UTC datetime."""
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def normalize_run(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Normalise a run object from either ``gh`` or deploy-monitor schema."""
    conclusion = (raw.get("conclusion") or "").strip().lower()
    status = (raw.get("status") or "").strip().lower()
    created = _parse_ts(
        raw.get("createdAt")
        or raw.get("created_at")
        or raw.get("updatedAt")
        or raw.get("updated_at")
    )
    if created is None:
        return None
    sha = str(raw.get("headSha") or raw.get("head_sha") or raw.get("sha_short") or "")[:7]
    duration = raw.get("duration_s") or raw.get("duration_seconds") or 0
    try:
        duration = int(duration)
    except (TypeError, ValueError):
        duration = 0
    return {
        "conclusion": conclusion,
        "status": status,
        "created_at": created,
        "sha": sha,
        "duration_s": duration,
    }


def _level(count: int, busiest: int) -> int:
    """Map a daily count to a 0–4 intensity level relative to the busiest day."""
    if count <= 0 or busiest <= 0:
        return 0
    ratio = count / busiest
    level = 1
    for threshold in LEVEL_FRACTIONS[1:]:
        if ratio > threshold:
            level += 1
    return min(level, 4)


def aggregate(runs: list[dict[str, Any]], now: datetime, window_days: int = WINDOW_DAYS) -> dict[str, Any]:
    """Aggregate normalised runs into totals + last deploy + 30-day heatmap.

    Only *completed* runs (those with a conclusion) are counted. ``now`` is the
    UTC reference for the trailing window so output is deterministic in tests.
    """
    completed = [r for r in runs if r.get("conclusion")]
    window_start = (now - timedelta(days=window_days - 1)).date()

    # Per-day buckets across the window.
    buckets: dict[str, dict[str, int]] = {}
    for offset in range(window_days):
        day = (window_start + timedelta(days=offset)).isoformat()
        buckets[day] = {"count": 0, "success": 0, "failed": 0}

    success = failed = cancelled = 0
    for run in completed:
        concl = run["conclusion"]
        if concl in SUCCESS_CONCLUSIONS:
            success += 1
        elif concl in FAILURE_CONCLUSIONS:
            failed += 1
        elif concl in CANCELLED_CONCLUSIONS:
            cancelled += 1
            continue  # cancelled = superseded; do not chart as activity
        day = run["created_at"].date().isoformat()
        if day in buckets:
            buckets[day]["count"] += 1
            if concl in SUCCESS_CONCLUSIONS:
                buckets[day]["success"] += 1
            elif concl in FAILURE_CONCLUSIONS:
                buckets[day]["failed"] += 1

    counted = success + failed
    success_rate = round(success / counted * 100) if counted else 0
    busiest = max((b["count"] for b in buckets.values()), default=0)

    days = [
        {
            "date": day,
            "count": data["count"],
            "success": data["success"],
            "failed": data["failed"],
            "level": _level(data["count"], busiest),
        }
        for day, data in sorted(buckets.items())
    ]

    # Last completed deploy = most recent by timestamp.
    last_deploy = None
    if completed:
        latest = max(completed, key=lambda r: r["created_at"])
        concl = latest["conclusion"]
        last_deploy = {
            "status": "success" if concl in SUCCESS_CONCLUSIONS
            else ("failed" if concl in FAILURE_CONCLUSIONS else concl or "unknown"),
            "at": latest["created_at"].isoformat().replace("+00:00", "Z"),
            "sha": latest["sha"],
            "duration_s": latest["duration_s"],
        }

    return {
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


def pending_payload(now: datetime, reason: str) -> dict[str, Any]:
    """A calm 'waiting for data' payload — never fabricated numbers (V27)."""
    window_start = (now - timedelta(days=WINDOW_DAYS - 1)).date()
    days = [
        {
            "date": (window_start + timedelta(days=o)).isoformat(),
            "count": 0,
            "success": 0,
            "failed": 0,
            "level": 0,
        }
        for o in range(WINDOW_DAYS)
    ]
    return {
        "schema_version": 1,
        "generated_at": now.isoformat().replace("+00:00", "Z"),
        "repository": REPO,
        "window_days": WINDOW_DAYS,
        "configured": False,
        "pending_reason": reason,
        "totals": {"total": 0, "success": 0, "failed": 0, "cancelled": 0, "success_rate_pct": 0},
        "last_deploy": None,
        "heatmap": {"max": 0, "days": days},
    }


def build_payload(raw_runs: list[dict[str, Any]], now: datetime) -> dict[str, Any]:
    runs = [r for r in (normalize_run(x) for x in raw_runs) if r]
    if not any(r.get("conclusion") for r in runs):
        return pending_payload(now, "no completed deploy runs available")
    stats = aggregate(runs, now)
    return {
        "schema_version": 1,
        "generated_at": now.isoformat().replace("+00:00", "Z"),
        "repository": REPO,
        "window_days": WINDOW_DAYS,
        "configured": True,
        **stats,
    }


def _load_raw_runs() -> list[dict[str, Any]]:
    """Resolve raw run records from env or the deploy-monitor seed file."""
    blob = os.getenv("WD_RUNS_JSON")
    if not blob:
        path = os.getenv("WD_RUNS_FILE")
        if path and Path(path).is_file():
            blob = Path(path).read_text(encoding="utf-8")
    if blob:
        try:
            data = json.loads(blob)
            if isinstance(data, dict):
                data = data.get("workflow_runs") or data.get("runs") or []
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    # Offline / local seed: reuse the existing deploy-monitor feed (real data).
    if SEED_PATH.is_file():
        try:
            dm = json.loads(SEED_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        feed = dm.get("feed") or dm.get("recent") or []
        if isinstance(feed, list):
            return feed
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Heartbeat Stats JSON")
    parser.add_argument("--stdout", action="store_true", help="print JSON, do not write file")
    parser.add_argument("--out", default=str(OUT_PATH), help="output path")
    args = parser.parse_args(argv)

    now = datetime.now(timezone.utc)
    payload = build_payload(_load_raw_runs(), now)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    if args.stdout:
        sys.stdout.write(text)
        return 0

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    totals = payload["totals"]
    state = "configured" if payload["configured"] else "pending"
    print(
        f"wd-heartbeat-stats: {state} → {out} "
        f"(total={totals['total']} success={totals['success']} "
        f"failed={totals['failed']} rate={totals['success_rate_pct']}%)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
