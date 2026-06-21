#!/usr/bin/env python3
"""
Build Open PRs report → static/data/open-prs.json

Fetches all currently open PRs against `main`, plus the check-runs for each
PR's head commit, and writes a public-safe JSON file consumed by
/tools/open-prs/.  No tokens, emails, paths, secrets, or raw CLI output are
written to the output file.

Anti-hang / graceful:
  - Missing token or network error → keep existing report if present, else
    write a seed "idle" payload.  ALWAYS exits 0 (never breaks the build).
  - Cap: ≤ 30 open PRs; ≤ 15 check-runs per PR.

Run locally:
  GITHUB_TOKEN=ghp_... python3 scripts/build_open_prs_report.py
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
STATIC_DATA = ROOT / "static" / "data"
FILENAME = "open-prs.json"
REPO = os.environ.get("GITHUB_REPOSITORY", "Banhang-Chogao/zola")
TOKEN = (
    os.environ.get("GITHUB_TOKEN")
    or os.environ.get("GH_TOKEN")
    or os.environ.get("ZOLA_GH_TOKEN")
    or ""
)
API = "https://api.github.com"
VN_TZ = timezone(timedelta(hours=7))
PR_URL = f"https://github.com/{REPO}/pulls"

MAX_PRS = 30
MAX_CHECKS = 15


# ── helpers ───────────────────────────────────────────────────────────────────

def _api(path: str, *, params: str = "") -> dict | list:
    url = f"{API}{path}"
    if params:
        url = f"{url}?{params}"
    req = Request(
        url,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "zola-open-prs",
        },
    )
    with urlopen(req, timeout=20) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def _fmt(iso: str | None) -> tuple[str, str]:
    """Return (iso_vn, 'HH:MM dd/mm/yyyy GMT+7')."""
    if iso:
        try:
            dt = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(VN_TZ)
        except (ValueError, TypeError):
            dt = datetime.now(VN_TZ)
    else:
        dt = datetime.now(VN_TZ)
    return dt.strftime("%Y-%m-%dT%H:%M:%S%z"), dt.strftime("%H:%M %d/%m/%Y")


def _elapsed(started: str | None, completed: str | None) -> tuple[int | None, str]:
    if not started:
        return None, ""
    try:
        t0 = datetime.fromisoformat(started.replace("Z", "+00:00"))
        t1 = (
            datetime.fromisoformat(completed.replace("Z", "+00:00"))
            if completed
            else datetime.now(timezone.utc)
        )
        secs = max(0, int((t1 - t0).total_seconds()))
        if secs >= 60:
            return secs, f"{secs // 60}m {secs % 60}s"
        return secs, f"{secs}s"
    except (ValueError, TypeError):
        return None, ""


def _norm_check(run: dict) -> dict:
    """Map a GitHub check-run object to a public-safe dict."""
    status = run.get("status", "")        # queued | in_progress | completed
    conclusion = run.get("conclusion")    # success|failure|cancelled|skipped|…|None
    elapsed_s, elapsed_disp = _elapsed(run.get("started_at"), run.get("completed_at"))

    if status in ("queued", "in_progress"):
        state = "pending"
    elif conclusion == "success":
        state = "success"
    elif conclusion in ("failure", "timed_out", "startup_failure", "action_required"):
        state = "failure"
    elif conclusion in ("cancelled",):
        state = "cancelled"
    elif conclusion in ("skipped", "neutral", "stale"):
        state = "skipped"
    else:
        state = "pending"

    return {
        "name": (run.get("name") or "")[:80],
        "state": state,
        "status": status,
        "conclusion": conclusion,
        "elapsed_s": elapsed_s,
        "elapsed_display": elapsed_disp,
        "url": run.get("html_url") or "",
    }


def _readiness(merge_state: str, is_draft: bool, checks: list[dict]) -> str:
    if is_draft:
        return "draft"
    if merge_state in ("dirty", "blocked") or merge_state.startswith("dirty"):
        if "dirty" in merge_state:
            return "conflict"
        return "needs_attention"
    states = {c["state"] for c in checks}
    if "failure" in states or merge_state == "blocked":
        return "needs_attention"
    if "pending" in states:
        return "pending"
    if merge_state == "clean" and (not states or states <= {"success", "skipped"}):
        return "ready"
    return "pending"


# ── main report builder ───────────────────────────────────────────────────────

def build_report() -> dict:
    raw_prs = _api(f"/repos/{REPO}/pulls", params=f"state=open&base=main&per_page={MAX_PRS}&sort=updated&direction=desc")
    if not isinstance(raw_prs, list):
        raw_prs = []

    pr_rows: list[dict] = []
    counts = {"ready": 0, "needs_attention": 0, "pending": 0, "conflict": 0, "draft": 0}

    for raw in raw_prs:
        number = raw.get("number")
        if not number:
            continue

        # Fetch individual PR to get mergeable_state (not in list payload)
        try:
            detail = _api(f"/repos/{REPO}/pulls/{number}")
            merge_state = (detail.get("mergeable_state") or "unknown").lower()
        except Exception:
            merge_state = "unknown"

        # Check runs for the PR's head commit
        head_sha = (raw.get("head") or {}).get("sha") or ""
        checks: list[dict] = []
        if head_sha:
            try:
                cr_data = _api(
                    f"/repos/{REPO}/commits/{head_sha}/check-runs",
                    params=f"per_page={MAX_CHECKS}",
                )
                for run in (cr_data.get("check_runs") or [])[:MAX_CHECKS]:
                    checks.append(_norm_check(run))
            except Exception:
                pass

        is_draft = bool(raw.get("draft"))
        readiness = _readiness(merge_state, is_draft, checks)
        counts[readiness] = counts.get(readiness, 0) + 1

        csums = {"success": 0, "failure": 0, "pending": 0, "skipped": 0, "cancelled": 0}
        for c in checks:
            csums[c["state"]] = csums.get(c["state"], 0) + 1
        csums["total"] = len(checks)

        updated_iso, updated_disp = _fmt(raw.get("updated_at"))
        _, now_disp = _fmt(None)
        pr_rows.append({
            "number": number,
            "title": (raw.get("title") or "")[:120],
            "url": raw.get("html_url") or f"{PR_URL}/{number}",
            "branch": (raw.get("head") or {}).get("ref") or "",
            "base": (raw.get("base") or {}).get("ref") or "main",
            "is_draft": is_draft,
            "merge_state": merge_state,
            "updated_at": updated_iso,
            "updated_at_display": updated_disp,
            "readiness": readiness,
            "checks_summary": csums,
            "checks": checks,
        })

    total = len(pr_rows)
    gen_iso, gen_disp = _fmt(datetime.now(timezone.utc).isoformat())
    return {
        "generated_at": gen_iso,
        "generated_at_display": gen_disp,
        "repo_url": f"https://github.com/{REPO}",
        "prs_url": PR_URL,
        "summary": {
            "total": total,
            "ready": counts.get("ready", 0),
            "needs_attention": counts.get("needs_attention", 0),
            "pending": counts.get("pending", 0),
            "conflict": counts.get("conflict", 0),
            "draft": counts.get("draft", 0),
        },
        "prs": pr_rows,
    }


def _seed() -> dict:
    gen_iso, gen_disp = _fmt(datetime.now(timezone.utc).isoformat())
    return {
        "generated_at": gen_iso,
        "generated_at_display": gen_disp,
        "repo_url": f"https://github.com/{REPO}",
        "prs_url": PR_URL,
        "summary": {"total": 0, "ready": 0, "needs_attention": 0, "pending": 0, "conflict": 0, "draft": 0},
        "prs": [],
    }


def _existing() -> dict | None:
    for p in (DATA / FILENAME, STATIC_DATA / FILENAME):
        if p.is_file():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
    return None


def _write(payload: dict) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    DATA.mkdir(parents=True, exist_ok=True)
    STATIC_DATA.mkdir(parents=True, exist_ok=True)
    (DATA / FILENAME).write_text(text, encoding="utf-8")
    (STATIC_DATA / FILENAME).write_text(text, encoding="utf-8")


def main() -> int:
    if not TOKEN:
        payload = _existing() or _seed()
        _write(payload)
        print(f"open-prs: no token → giữ/seed report ({payload['summary']['total']} PRs)")
        return 0
    try:
        payload = build_report()
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
        cached = _existing()
        if cached:
            print(f"open-prs: fetch lỗi ({exc}) → giữ report cũ")
            return 0
        payload = _seed()
        _write(payload)
        print(f"open-prs: fetch lỗi ({exc}) → seed empty")
        return 0
    _write(payload)
    s = payload["summary"]
    print(f"open-prs: {s['total']} PRs · ready={s['ready']} · pending={s['pending']} · failing={s['needs_attention']} · conflict={s['conflict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
