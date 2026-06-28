#!/usr/bin/env python3
"""
build_production_dashboard.py — Production Deploy Dashboard.

Generates data/production-dashboard.json showing recent merged PRs, their deploy
status, and production verification. Combines git history, GitHub Actions API,
and GitHub Pages deployment status.

This data is read-only and consumed by templates/partials/changelog-prod-dashboard.html.
Browser never calls GitHub APIs — all data is static JSON.

Stdlib only. Exit 0 on non-critical errors (keeps prior snapshot).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "production-dashboard.json"
REPO = os.environ.get("GITHUB_REPOSITORY", "Banhang-Chogao/zola")
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
API = "https://api.github.com"
TZ = ZoneInfo("Asia/Ho_Chi_Minh")
TIMEOUT = 12


def _now_iso() -> str:
    return datetime.now(TZ).astimezone().isoformat()


def _fmt_display(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(TZ)
        return dt.strftime("%H:%M %d/%m/%Y")
    except ValueError:
        return "—"


def _short(sha: str | None) -> str:
    return (sha or "")[:7] if sha else "—"


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _git_commits(limit: int = 20) -> list[dict]:
    """Get recent commits with PR info."""
    commits = []
    try:
        # Get last N commits with metadata
        output = subprocess.run(
            [
                "git",
                "log",
                f"--max-count={limit}",
                "--pretty=format:%H|%h|%s|%b|%an|%ai",
                "HEAD",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
            cwd=ROOT,
        ).stdout.strip()

        for line in output.split("\n"):
            if not line:
                continue
            parts = line.split("|", 5)
            if len(parts) < 6:
                continue
            sha, short, subject, body, author, timestamp = parts

            # Extract PR number from subject (e.g., "fix: message (#1125)")
            pr_num = None
            if "#" in subject:
                try:
                    pr_part = subject.split("(#")[1].split(")")[0]
                    pr_num = f"#{pr_part}"
                except (IndexError, ValueError):
                    pass

            commits.append(
                {
                    "sha": sha,
                    "short": short,
                    "subject": subject,
                    "author": author,
                    "timestamp": timestamp,
                    "pr": pr_num,
                }
            )
    except (subprocess.SubprocessError, OSError):
        pass
    return commits


def _api_get(path: str) -> dict | list | None:
    if not TOKEN:
        return None
    req = Request(
        f"{API}{path}",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "prod-dashboard/1.0",
        },
    )
    try:
        with urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (HTTPError, URLError, OSError):
        return None


def _get_pr_info(pr_num: str) -> dict | None:
    """Fetch PR metadata from GitHub API."""
    if not pr_num or not TOKEN:
        return None
    pr_id = pr_num.lstrip("#")
    data = _api_get(f"/repos/{REPO}/pulls/{pr_id}")
    if data:
        return {
            "number": data.get("number"),
            "title": data.get("title"),
            "state": data.get("state"),
            "merged_at": data.get("merged_at"),
            "url": data.get("html_url"),
        }
    return None


def _get_main_sha() -> str | None:
    """Get latest main commit SHA."""
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
            cwd=ROOT,
        ).stdout.strip()
        return sha or None
    except (subprocess.SubprocessError, OSError):
        return None


def _get_deployed_sha() -> str | None:
    """Get latest GitHub Pages deployed SHA from deploy-monitor.json (source of truth)."""
    dm = _load_json(ROOT / "data" / "deploy-monitor.json")
    if dm:
        summary = dm.get("summary") or {}
        deployed = summary.get("prod_commit")
        if deployed:
            return deployed
    # Fallback: try GitHub Pages API
    pages = _api_get(f"/repos/{REPO}/pages")
    if pages:
        return pages.get("source", {}).get("sha")
    return None


def _get_deploy_runs(limit: int = 10) -> list[dict]:
    """Get recent deploy runs."""
    runs = []
    data = _api_get(
        f"/repos/{REPO}/actions/workflows/deploy.yml/runs?per_page={limit}"
    )
    if data and data.get("workflow_runs"):
        for run in data.get("workflow_runs", []):
            runs.append(
                {
                    "id": run.get("id"),
                    "run_number": run.get("run_number"),
                    "status": run.get("status"),
                    "conclusion": run.get("conclusion"),
                    "head_sha": run.get("head_sha"),
                    "head_commit": run.get("head_commit", {}).get("message", "—"),
                    "created_at": run.get("created_at"),
                    "updated_at": run.get("updated_at"),
                    "url": run.get("html_url"),
                }
            )
    return runs


def build_dashboard() -> dict:
    """Build production dashboard data."""
    main_sha = _get_main_sha()
    deployed_sha = _get_deployed_sha()
    commits = _git_commits(limit=15)
    deploy_runs = _get_deploy_runs(limit=10)
    dm = _load_json(ROOT / "data" / "deploy-monitor.json")
    dm_summary = (dm.get("summary") or {}) if dm else {}

    # Map commits to deploy status
    items = []
    deploy_run_map = {run["head_sha"]: run for run in deploy_runs}

    for commit in commits:
        pr_info = None
        if commit["pr"]:
            pr_info = _get_pr_info(commit["pr"])

        deploy_run = deploy_run_map.get(commit["sha"])

        # Determine deployment status
        deploy_status = "unknown"
        failed_reason = ""
        final_status = "unknown"

        if commit["sha"] == deployed_sha:
            deploy_status = "live"
            final_status = "production_verified"
        elif deploy_run:
            if deploy_run["status"] == "in_progress":
                deploy_status = "deploy_running"
                final_status = "deploy_running"
            elif deploy_run["conclusion"] == "success":
                deploy_status = "deployed"
                final_status = "deploy_success"
            elif deploy_run["conclusion"] == "failure":
                deploy_status = "deploy_failed"
                final_status = "needs_bugfix"
                failed_reason = deploy_run.get("head_commit", "Build or QA failed")
            elif deploy_run["conclusion"] == "cancelled":
                deploy_status = "deploy_cancelled"
                final_status = "deploy_retrying"
                failed_reason = "Cancelled by newer deploy run"
            elif deploy_run["conclusion"] == "skipped":
                deploy_status = "skipped"
                final_status = "unknown"
        else:
            deploy_status = "pending_deploy"
            final_status = "deploy_pending"

        # Determine merge status
        merge_status = "not_merged"
        if pr_info:
            merge_status = "merged" if pr_info["state"] == "closed" else "open"

        # Build PR URL (canonical, never HTML-escaped)
        pr_url = None
        if commit["pr"]:
            pr_num = commit["pr"].lstrip("#")
            pr_url = f"https://github.com/{REPO}/pull/{pr_num}"

        item = {
            "pr": commit["pr"],
            "pr_url": pr_url,
            "title": pr_info.get("title") if pr_info else commit["subject"],
            "commit": commit["short"],
            "commit_full": commit["sha"],
            "feature": commit["subject"],
            "merge_status": merge_status,
            "merged_at": pr_info.get("merged_at") if pr_info else None,
            "deploy_status": deploy_status,
            "deploy_run_url": deploy_run.get("url") if deploy_run else None,
            "failed_reason": failed_reason,
            "final_status": final_status,
            "last_checked": _now_iso(),
            "production_urls": (
                [f"https://seomoney.org/?v={commit['pr'].lstrip('#')}"]
                if commit["pr"]
                else ["https://seomoney.org/"]
            ),
        }
        items.append(item)

    # Determine overall status from deploy-monitor state
    overall_status = "unknown"
    if main_sha and deployed_sha:
        if main_sha == deployed_sha:
            overall_status = "live"
        elif dm_summary.get("deploying") or dm_summary.get("prod_status") == "yellow":
            overall_status = "deploying"
        else:
            overall_status = "stale_deploy"
    elif main_sha and not deployed_sha:
        overall_status = "stale_deploy"

    return {
        "generated_at": _now_iso(),
        "latest_main_sha": main_sha,
        "latest_main_short": _short(main_sha),
        "latest_deployed_sha": deployed_sha,
        "latest_deployed_short": _short(deployed_sha),
        "overall_status": overall_status,
        "items": items,
    }


def main() -> int:
    try:
        dashboard = build_dashboard()
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(dashboard, indent=2, ensure_ascii=False))
        print(f"✅ Wrote {OUTPUT}")
        return 0
    except Exception as e:
        print(f"⚠️  Error building dashboard: {e}", file=sys.stderr)
        # Keep prior snapshot on error
        return 0


if __name__ == "__main__":
    sys.exit(main())
