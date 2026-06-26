#!/usr/bin/env python3
"""
fetch_deploy_monitor.py — Deploy Watch data fetcher.

Reads a GitHub token from the environment ONLY, queries the "Build and deploy"
workflow (deploy.yml) runs via the read-only Actions REST API, and writes ONE
sanitized public report to data/deploy-monitor.json.

Stdlib only. See zola/scripts/fetch_deploy_monitor.py for full docstring history.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "deploy-monitor.json"
REPO = os.environ.get("GITHUB_REPOSITORY", "Banhang-Chogao/zola")
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
API = "https://api.github.com"

WORKFLOW_FILE = "deploy.yml"
MAX_RUNS = 30
TIMEOUT = 15

_PENDING = {"queued", "in_progress", "waiting", "requested", "pending"}
_PENDING_TTL_S = 2700
_STORM_WINDOW_S = 1200
_STORM_CANCELLED = 3

_STATE_ICON = {
    "running": "🔄", "queued": "⏳", "success": "✅",
    "failure": "❌", "cancelled": "⊘", "skipped": "⏭",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _short(sha: str) -> str:
    return (sha or "")[:7]


def _title(run: dict) -> str:
    t = run.get("display_title") or (run.get("head_commit") or {}).get("message", "") or ""
    return t.splitlines()[0][:90] if t else ""


def _state(status: str | None, conclusion: str | None) -> str:
    s = (status or "").lower()
    c = (conclusion or "").lower()
    if s in _PENDING:
        return "queued" if s in {"queued", "waiting", "requested", "pending"} else "running"
    if c == "success":
        return "success"
    if c in {"failure", "timed_out", "startup_failure"}:
        return "failure"
    if c == "cancelled":
        return "cancelled"
    if c == "skipped":
        return "skipped"
    return "running" if s != "completed" else "success"


def _commit_url(sha: str) -> str | None:
    return f"https://github.com/{REPO}/commit/{sha}" if sha else None


def fetch_runs() -> tuple[list[dict], str | None]:
    if not TOKEN:
        return [], "missing_token"
    url = f"{API}/repos/{REPO}/actions/workflows/{WORKFLOW_FILE}/runs?per_page={MAX_RUNS}"
    req = Request(url, headers={
        "authorization": f"Bearer {TOKEN}",
        "accept": "application/vnd.github+json",
        "user-agent": "deploy-monitor/1.0",
        "x-github-api-version": "2022-11-28",
    })
    try:
        with urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
    except HTTPError as e:
        return [], ("rate_limit" if e.code in (403, 429) else f"http_{e.code}")
    except (URLError, TimeoutError):
        return [], "network"
    except Exception:
        return [], "error"
    return (data.get("workflow_runs") or []), None


def build_report_from_runs(runs: list[dict], now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)

    success_shas = {
        r.get("head_sha")
        for r in runs
        if (r.get("status") or "").lower() == "completed"
        and (r.get("conclusion") or "").lower() == "success"
        and r.get("head_sha")
    }

    pending, expired, recent, durations = [], [], [], []
    cancelled_times, failed_recent, cancelled_recent = [], 0, 0
    prod = None
    fresh_shas: set[str] = set()

    for r in runs:
        status = (r.get("status") or "").lower()
        concl = (r.get("conclusion") or "").lower()
        started = _parse(r.get("run_started_at") or r.get("created_at"))
        updated = _parse(r.get("updated_at"))
        sha = r.get("head_sha", "")
        entry = {
            "sha_short": _short(sha),
            "title": _title(r),
            "status": status,
            "conclusion": concl or None,
            "created_at": r.get("created_at"),
            "run_number": r.get("run_number"),
            "run_url": r.get("html_url"),
        }
        if status != "completed":
            wait = int((now - started).total_seconds()) if started else None
            entry["waiting_s"] = wait
            entry["started_at"] = r.get("run_started_at") or r.get("created_at")
            stale_age = wait is not None and wait > _PENDING_TTL_S
            already = bool(sha) and sha in success_shas
            if stale_age or already:
                entry["expired"] = True
                entry["expired_reason"] = "already_deployed" if already else "ttl"
                expired.append(entry)
            else:
                pending.append(entry)
                if sha:
                    fresh_shas.add(sha)
            continue

        dur = int((updated - started).total_seconds()) if (started and updated) else None
        entry["duration_s"] = dur
        recent.append(entry)
        if concl == "success":
            if dur is not None and dur > 0:
                durations.append(dur)
            if prod is None:
                prod = (r, dur)
        elif concl == "failure":
            failed_recent += 1
        elif concl == "cancelled":
            cancelled_recent += 1
            if started:
                cancelled_times.append(started)

    storm = False
    cancelled_times.sort()
    for i in range(len(cancelled_times)):
        window = [t for t in cancelled_times if 0 <= (t - cancelled_times[i]).total_seconds() <= _STORM_WINDOW_S]
        if len(window) >= _STORM_CANCELLED:
            storm = True
            break

    avg = round(sum(durations) / len(durations)) if durations else None
    longest = max(durations) if durations else None

    for p in pending:
        w = p.get("waiting_s")
        p["eta_s"] = max(0, avg - w) if (avg is not None and w is not None) else None

    latest = runs[0] if runs else {}
    latest_status = (latest.get("status") or "").lower()
    latest_concl = (latest.get("conclusion") or "").lower()
    latest_sha = latest.get("head_sha", "")
    latest_fresh_pending = latest_status != "completed" and latest_sha in fresh_shas

    if pending or latest_fresh_pending:
        prod_status = "yellow"
    elif latest_status == "completed" and latest_concl == "failure":
        prod_status = "red"
    elif prod is not None:
        prod_status = "green"
    else:
        prod_status = "unknown"

    prod_run, _prod_dur = (prod or (None, None))

    def _rn(r: dict) -> int:
        return r.get("run_number") or 0

    max_success_rn = max(
        (_rn(r) for r in runs if _state(r.get("status"), r.get("conclusion")) == "success"),
        default=0,
    )
    feed: list[dict] = []
    for r in sorted(runs, key=_rn, reverse=True)[:12]:
        st = _state(r.get("status"), r.get("conclusion"))
        rn = r.get("run_number")
        sha = r.get("head_sha", "")
        started = _parse(r.get("run_started_at") or r.get("created_at"))
        updated = _parse(r.get("updated_at"))
        completed = (r.get("status") or "").lower() == "completed"
        feed.append({
            "run_number": rn,
            "run_url": r.get("html_url"),
            "sha_short": _short(sha),
            "commit_url": _commit_url(sha),
            "title": _title(r),
            "status": (r.get("status") or "").lower(),
            "conclusion": (r.get("conclusion") or "").lower() or None,
            "state": st,
            "icon": _STATE_ICON.get(st, "•"),
            "superseded": st in {"failure", "cancelled"} and rn is not None and rn < max_success_rn,
            "created_at": r.get("created_at"),
            "duration_s": int((updated - started).total_seconds()) if (completed and started and updated) else None,
        })

    running_runs = [f["run_number"] for f in feed if f["state"] in {"running", "queued"} and f["run_number"]]
    all_success = sorted(
        (r for r in runs if _state(r.get("status"), r.get("conclusion")) == "success" and r.get("run_number")),
        key=_rn, reverse=True,
    )
    last_success_run = all_success[0].get("run_number") if all_success else None
    last_success_sha_short = _short(all_success[0].get("head_sha", "")) if all_success else None
    superseded_failures = [f["run_number"] for f in feed
                           if f["state"] == "failure" and f["superseded"] and f["run_number"]]

    segs: list[str] = []
    if running_runs:
        segs.append(f"🔄 #{running_runs[0]} đang chạy")
    if last_success_run:
        segs.append(f"✅ last success #{last_success_run}")
    if superseded_failures:
        nums = "/".join(f"#{n}" for n in superseded_failures[:3])
        segs.append(f"❌ {nums} (đã superseded)")
    status_line = " · ".join(segs)

    return {
        "checked_at": _now(),
        "ok": True,
        "stale": bool(expired),
        "summary": {
            "prod_status": prod_status,
            "deploying": bool(pending),
            "prod_commit": (prod_run or {}).get("head_sha") if prod_run else None,
            "prod_commit_short": _short((prod_run or {}).get("head_sha", "")) if prod_run else None,
            "prod_deployed_at": (prod_run or {}).get("updated_at") if prod_run else None,
            "pending_count": len(pending),
            "expired_count": len(expired),
            "avg_deploy_s": avg,
            "longest_deploy_s": longest,
            "failed_recent": failed_recent,
            "cancelled_recent": cancelled_recent,
            "storm": storm,
            "running_runs": running_runs,
            "last_success_run": last_success_run,
            "last_success_sha_short": last_success_sha_short,
            "superseded_failures": superseded_failures,
            "status_line": status_line,
        },
        "feed": feed,
        "pending": pending[:10],
        "expired": expired[:10],
        "recent": recent[:12],
    }


def build_report() -> dict:
    runs, err = fetch_runs()
    if err or not runs:
        prev: dict = {}
        if OUTPUT.exists():
            try:
                prev = json.loads(OUTPUT.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                prev = {}
        prev = prev if isinstance(prev, dict) else {}
        prev["checked_at"] = _now()
        prev["ok"] = False
        prev["stale"] = True
        prev.setdefault("summary", {}).setdefault("prod_status", "unknown")
        prev.setdefault("error", err or "no_runs")
        prev.setdefault("feed", [])
        prev.setdefault("pending", [])
        prev.setdefault("expired", [])
        prev.setdefault("recent", [])
        return prev

    return build_report_from_runs(runs)


def _strip_volatile(rep: dict) -> str:
    clone = json.loads(json.dumps(rep))
    clone.pop("checked_at", None)
    for key in ("pending", "expired"):
        for p in clone.get(key, []) or []:
            p.pop("waiting_s", None)
            p.pop("eta_s", None)
    return json.dumps(clone, sort_keys=True, ensure_ascii=False)


def main() -> int:
    try:
        report = build_report()
    except Exception as e:
        print(f"[deploy-monitor] unexpected error: {type(e).__name__}", file=sys.stderr)
        return 0

    serialized = json.dumps(report, ensure_ascii=False)
    for env in ("GITHUB_TOKEN", "GH_TOKEN"):
        tok = (os.environ.get(env) or "").strip()
        if tok and tok in serialized:
            print("[deploy-monitor] FATAL: token leaked into report — aborting.", file=sys.stderr)
            return 2

    if OUTPUT.exists():
        try:
            old = json.loads(OUTPUT.read_text(encoding="utf-8"))
            if _strip_volatile(old) == _strip_volatile(report):
                print("[deploy-monitor] no meaningful change — keeping existing report.")
                return 0
        except (OSError, json.JSONDecodeError):
            pass

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    s = report.get("summary", {})
    print(f"[deploy-monitor] wrote {OUTPUT.relative_to(ROOT)} — status={s.get('prod_status')} "
          f"pending={s.get('pending_count')} avg={s.get('avg_deploy_s')}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())