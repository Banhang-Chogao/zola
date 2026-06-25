#!/usr/bin/env python3
"""Daily PR Production Followup — chạy lúc 06:00 ICT (23:00 UTC).

Tự soát toàn bộ open PR trong repo, phân loại, fix conflict (V10/V12),
merge khi xanh, kiểm tra deploy lên production. Reuses:
  - scripts/autofix_conflicts.py  (conflict resolution)
  - scripts/try_auto_merge.py     (merge khi qa-check pass)
  - scripts/prod_smoke_check.py   (verify production)
  - scripts/failure_priority.py   (triage fail)

Output: reports/daily-pr-production-followup.md + data/daily-pr-followup.json
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
    _TZ = ZoneInfo("Asia/Ho_Chi_Minh")
except Exception:
    _TZ = timezone.utc

API = "https://api.github.com"
REPO = os.environ.get("GH_REPO") or os.environ.get("GITHUB_REPOSITORY", "Banhang-Chogao/zola")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
ROOT = Path(__file__).resolve().parent.parent
REPORT_MD = ROOT / "reports" / "daily-pr-production-followup.md"
REPORT_JSON = ROOT / "data" / "daily-pr-followup.json"


def _gh(path: str) -> dict | list:
    url = f"{API}/repos/{REPO}{path}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": str(e)}


def get_open_prs() -> list[dict]:
    prs = _gh("/pulls?state=open&per_page=50")
    if isinstance(prs, dict):
        return []
    return prs


def get_pr_checks(pr_number: int) -> dict:
    """Returns {qa_check: pass|fail|pending|missing, conflict: bool}."""
    checks = _gh(f"/pulls/{pr_number}")
    mergeable = checks.get("mergeable", None)
    conflict = mergeable == "CONFLICTING"

    # Get commit statuses / check runs
    sha = checks.get("head", {}).get("sha", "")
    if not sha:
        return {"qa_check": "missing", "conflict": conflict, "sha": ""}

    runs = _gh(f"/commits/{sha}/check-runs?per_page=50")
    qa_status = "missing"
    if isinstance(runs, dict) and "check_runs" in runs:
        for run in runs["check_runs"]:
            if run.get("name") == "qa-check":
                conclusion = run.get("conclusion") or ""
                status = run.get("status", "")
                if status == "completed":
                    qa_status = "pass" if conclusion == "success" else "fail"
                else:
                    qa_status = "pending"
                break

    return {"qa_check": qa_status, "conflict": conflict, "sha": sha,
            "mergeable": mergeable, "state": checks.get("state", "open")}


def classify_pr(pr: dict, checks: dict) -> str:
    """Returns: pending | conflict | qa_fail | qa_pass | merged | unknown."""
    if pr.get("state") == "closed" or checks.get("state") == "closed":
        return "merged"
    if checks["conflict"]:
        return "conflict"
    qa = checks["qa_check"]
    if qa == "pass":
        return "qa_pass"
    if qa == "fail":
        return "qa_fail"
    if qa == "pending":
        return "pending"
    return "unknown"


def fix_conflict(pr_number: int, branch: str) -> str:
    """Run autofix_conflicts.py for the branch."""
    script = ROOT / "scripts" / "autofix_conflicts.py"
    if not script.exists():
        return "autofix_conflicts.py not found"
    result = subprocess.run(
        [sys.executable, str(script), "--branch", branch],
        capture_output=True, text=True, timeout=120, cwd=ROOT
    )
    return result.stdout[-300:] + result.stderr[-300:]


def try_merge(pr_number: int) -> str:
    """Run try_auto_merge.py for a specific PR."""
    script = ROOT / "scripts" / "try_auto_merge.py"
    if not script.exists():
        return "try_auto_merge.py not found"
    env = {**os.environ, "INPUT_PR": str(pr_number), "EVENT_NAME": "workflow_dispatch"}
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True, text=True, timeout=60, cwd=ROOT, env=env
    )
    return (result.stdout + result.stderr)[-400:]


def check_deploy_status() -> dict:
    """Check latest deploy run on main."""
    runs = _gh("/actions/workflows/deploy.yml/runs?branch=main&per_page=3")
    if isinstance(runs, dict) and "workflow_runs" in runs:
        latest = runs["workflow_runs"][0] if runs["workflow_runs"] else {}
        return {
            "status": latest.get("status", "unknown"),
            "conclusion": latest.get("conclusion"),
            "sha": latest.get("head_sha", "")[:8],
            "created_at": latest.get("created_at", ""),
        }
    return {"status": "unknown"}


def main() -> None:
    now = datetime.now(_TZ)
    print(f"[daily-pr-followup] {now.strftime('%Y-%m-%d %H:%M %Z')}")

    if not TOKEN:
        print("ERROR: GITHUB_TOKEN missing — cannot call GitHub API")
        sys.exit(1)

    prs = get_open_prs()
    print(f"  Found {len(prs)} open PRs")

    results: list[dict] = []
    buckets: dict[str, list] = {
        "pending": [], "conflict": [], "qa_fail": [],
        "qa_pass": [], "merged": [], "unknown": [],
    }

    for pr in prs:
        number = pr["number"]
        title = pr["title"][:60]
        branch = pr["head"]["ref"]
        print(f"  PR#{number} [{branch}] …", end=" ", flush=True)

        checks = get_pr_checks(number)
        category = classify_pr(pr, checks)
        print(category)

        action_result = ""
        if category == "conflict":
            action_result = fix_conflict(number, branch)
        elif category == "qa_pass":
            action_result = try_merge(number)

        entry = {
            "number": number,
            "title": title,
            "branch": branch,
            "category": category,
            "qa_check": checks["qa_check"],
            "conflict": checks["conflict"],
            "action": action_result[:300] if action_result else "",
        }
        results.append(entry)
        buckets[category].append(f"#{number} {title}")

    deploy = check_deploy_status()

    # Write JSON report
    REPORT_JSON.parent.mkdir(exist_ok=True)
    report_data = {
        "run_at": now.isoformat(),
        "total_open": len(prs),
        "buckets": {k: len(v) for k, v in buckets.items()},
        "deploy": deploy,
        "prs": results,
    }
    REPORT_JSON.write_text(json.dumps(report_data, ensure_ascii=False, indent=2))

    # Write markdown report
    REPORT_MD.parent.mkdir(exist_ok=True)
    lines = [
        f"# Daily PR Production Followup — {now.strftime('%Y-%m-%d %H:%M ICT')}",
        "",
        f"**Open PRs:** {len(prs)} | "
        f"pending:{len(buckets['pending'])} | "
        f"conflict:{len(buckets['conflict'])} | "
        f"qa_fail:{len(buckets['qa_fail'])} | "
        f"qa_pass:{len(buckets['qa_pass'])}",
        "",
        f"**Deploy (main):** status={deploy['status']} conclusion={deploy.get('conclusion','?')} sha={deploy.get('sha','')}",
        "",
    ]
    for cat, prs_list in buckets.items():
        if prs_list:
            lines += [f"## {cat.upper()} ({len(prs_list)})", ""]
            for p in prs_list:
                lines.append(f"- {p}")
            lines.append("")

    REPORT_MD.write_text("\n".join(lines))
    print(f"\n  Report: {REPORT_MD.relative_to(ROOT)}")
    print(f"  JSON:   {REPORT_JSON.relative_to(ROOT)}")

    # Exit 1 if any conflict or qa_fail needs attention
    if buckets["conflict"] or buckets["qa_fail"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
