#!/usr/bin/env python3
"""
Build the Open PR Monitor data → static/data/open-prs.json.

Source: `gh pr list --state open --limit 10 --json number,title,headRefName,
baseRefName,url,author,updatedAt,mergeable,reviewDecision,statusCheckRollup`.

The blog is a static Zola site on GitHub Pages — production cannot run `gh` in the
browser, so PR data is generated at BUILD/CI time (where `gh` + GITHUB_TOKEN exist)
and committed/published as a small sanitized JSON the footer widget fetches.

Safety / graceful degradation (BẮT BUỘC):
  * `gh` missing, unauthenticated, network/parse error, or no repo context
    → write `[]` and exit 0. The build NEVER fails because of this script.
  * Only a whitelist of fields is copied into the output — no tokens/secrets,
    no raw `author` object, no internal check ids — just what the UI renders.

Run locally:  GITHUB_TOKEN=ghp_... python3 scripts/build_open_prs.py
              (without gh installed it simply writes [])
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATIC_DATA = ROOT / "static" / "data"
FILENAME = "open-prs.json"
REPO = os.environ.get("GITHUB_REPOSITORY", "Banhang-Chogao/zola")
VN_TZ = timezone(timedelta(hours=7))
LIMIT = 10
GH_FIELDS = (
    "number,title,headRefName,baseRefName,url,author,"
    "updatedAt,mergeable,reviewDecision,statusCheckRollup"
)

# statusCheckRollup conclusions/states → pass | fail | pending buckets.
_FAIL = {"FAILURE", "TIMED_OUT", "CANCELLED", "STARTUP_FAILURE", "ACTION_REQUIRED",
         "STALE", "ERROR"}
_PASS = {"SUCCESS", "NEUTRAL", "SKIPPED"}


def _fmt_dt(iso: str | None) -> tuple[str, str]:
    """ISO updatedAt → (normalized ISO, 'HH:MM dd/mm/yyyy' GMT+7 display)."""
    if not iso:
        now = datetime.now(VN_TZ)
        return now.strftime("%Y-%m-%dT%H:%M:%S%z"), now.strftime("%H:%M %d/%m/%Y")
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00")).astimezone(VN_TZ)
    except (ValueError, TypeError):
        dt = datetime.now(VN_TZ)
    return dt.strftime("%Y-%m-%dT%H:%M:%S%z"), dt.strftime("%H:%M %d/%m/%Y")


def _check_state(item: dict) -> str:
    """Bucket a single statusCheckRollup entry into pass | fail | pending."""
    if not isinstance(item, dict):
        return "pending"
    concl = str(item.get("conclusion") or "").upper()
    if concl:
        if concl in _FAIL:
            return "fail"
        if concl in _PASS:
            return "pass"
        return "pending"
    state = str(item.get("state") or "").upper()
    if state:
        if state in _FAIL:
            return "fail"
        if state in _PASS:
            return "pass"
        return "pending"
    return "pending"  # in_progress / queued — no conclusion yet


def summarize_checks(rollup) -> dict:
    """Aggregate the CI check rollup into a compact, render-ready summary."""
    passed = failed = pending = 0
    for item in rollup or []:
        bucket = _check_state(item)
        if bucket == "pass":
            passed += 1
        elif bucket == "fail":
            failed += 1
        else:
            pending += 1
    total = passed + failed + pending
    if total == 0:
        state = "none"
    elif failed:
        state = "failure"
    elif pending:
        state = "pending"
    else:
        state = "success"

    parts = []
    if passed:
        parts.append(f"{passed} passed")
    if failed:
        parts.append(f"{failed} failed")
    if pending:
        parts.append(f"{pending} running")
    summary = " · ".join(parts) if parts else "Chưa có kiểm tra CI"
    return {
        "state": state,
        "passed": passed,
        "failed": failed,
        "pending": pending,
        "total": total,
        "summary": summary,
    }


def sanitize_pr(pr: dict) -> dict | None:
    """Copy ONLY whitelisted fields from a raw `gh` PR object — no secrets."""
    if not isinstance(pr, dict) or pr.get("number") is None:
        return None
    author = pr.get("author")
    login = ""
    if isinstance(author, dict):
        login = str(author.get("login") or "")
    iso, disp = _fmt_dt(pr.get("updatedAt"))
    title = str(pr.get("title") or "").strip()
    if len(title) > 160:
        title = title[:157].rstrip() + "…"
    return {
        "number": int(pr.get("number")),
        "title": title,
        "head": str(pr.get("headRefName") or ""),
        "base": str(pr.get("baseRefName") or ""),
        "url": str(pr.get("url") or ""),
        "author": login,
        "updated_at": iso,
        "updated_display": disp,
        "mergeable": str(pr.get("mergeable") or "UNKNOWN").upper(),
        "review_decision": str(pr.get("reviewDecision") or ""),
        "checks": summarize_checks(pr.get("statusCheckRollup")),
    }


def sanitize_prs(raw) -> list[dict]:
    """Sanitize a list of raw `gh` PR objects, newest-updated first, capped at LIMIT."""
    if not isinstance(raw, list):
        return []
    out = [c for c in (sanitize_pr(p) for p in raw) if c]
    out.sort(key=lambda c: c.get("updated_at", ""), reverse=True)
    return out[:LIMIT]


def fetch_raw_prs() -> list:
    """Run `gh pr list`. Any failure (missing/unauth/network) → [] (never raises)."""
    if not shutil.which("gh"):
        print("open-prs: gh not available → writing []")
        return []
    env = dict(os.environ)
    token = env.get("GITHUB_TOKEN") or env.get("GH_TOKEN") or env.get("ZOLA_GH_TOKEN")
    if token:
        env.setdefault("GH_TOKEN", token)
    cmd = [
        "gh", "pr", "list", "--repo", REPO,
        "--state", "open", "--limit", str(LIMIT), "--json", GH_FIELDS,
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60, env=env, check=False
        )
    except (OSError, subprocess.SubprocessError) as e:
        print(f"open-prs: gh invocation failed ({e}) → writing []")
        return []
    if proc.returncode != 0:
        err = (proc.stderr or "").strip().splitlines()
        print(f"open-prs: gh exit {proc.returncode} ({err[-1] if err else 'no stderr'}) → writing []")
        return []
    try:
        data = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as e:
        print(f"open-prs: bad gh JSON ({e}) → writing []")
        return []
    return data if isinstance(data, list) else []


def write(prs: list[dict]) -> None:
    STATIC_DATA.mkdir(parents=True, exist_ok=True)
    text = json.dumps(prs, ensure_ascii=False, indent=2) + "\n"
    (STATIC_DATA / FILENAME).write_text(text, encoding="utf-8")


def main() -> int:
    prs = sanitize_prs(fetch_raw_prs())
    write(prs)
    print(f"open-prs: wrote {len(prs)} open PR(s) → static/data/{FILENAME}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
