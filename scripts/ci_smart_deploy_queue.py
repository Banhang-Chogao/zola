#!/usr/bin/env python3
"""
Smart Deploy Queue — preflight gate for deploy.yml.

Detects changed files in the current commit/run, classifies them as IMPORTANT
or LOW_VALUE, and checks whether a production deploy is already queued or
in_progress.  If the current change is LOW_VALUE and a deploy is already active,
the run should be skipped to preserve API quota.

Classification rules (IMPORTANT):
  - content/**, templates/**, static/** (except static/data/ generated files)
  - config.toml, themes/**
  - .github/workflows/deploy.yml, .github/workflows/qa.yml
  - Any hotfix commit (message matches hotfix pattern)
  - Anything that doesn't match LOW_VALUE patterns

LOW_VALUE patterns (generated data / reports / dashboards):
  - data/*-dashboard.json, data/merge-report.json
  - data/ga-*.json, data/google-trends-*.json
  - data/pagespeed.json, data/security.json
  - data/deploy-monitor.json, data/prod-snapshot.json
  - data/github-activity.json, data/github-profile-badges.json
  - data/compliance-*.json, data/vaccine-*.json
  - data/ad-report*.json, data/seo-rank-autofix*.json
  - data/build-dashboard.json, data/related.json, data/scores.json
  - data/related-qa-*.json, data/owned-covers.json
  - data/production-dashboard.json, data/theme-log.json
  - data/qa-*.json (QA-generated reports)
  - static/data/* (copies of generated data)
  - reports/** (report markdown files)

Usage (in CI):
    python3 scripts/ci_smart_deploy_queue.py
    echo "decision=${{ steps.smart_queue.outputs.decision }}"
    echo "reason=${{ steps.smart_queue.outputs.reason }}"

Output (GitHub Actions friendly):
    Sets outputs: decision, reason, classification
    decision: proceed | skip_low_value | skip_no_changes
    classification: important | low_value | unknown
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parent.parent

# ── LOW_VALUE file patterns (fnmatch-style) ──────────────────────────────
LOW_VALUE_PATTERNS: list[re.Pattern] = [
    re.compile(r"^data/.*dashboard.*\.json$"),
    re.compile(r"^data/merge-report.*\.json$"),
    re.compile(r"^data/ga-.*\.json$"),
    re.compile(r"^data/google-trends.*\.json$"),
    re.compile(r"^data/pagespeed.*\.json$"),
    re.compile(r"^data/security.*\.json$"),
    re.compile(r"^data/deploy-monitor.*\.json$"),
    re.compile(r"^data/prod-snapshot.*\.json$"),
    re.compile(r"^data/production-dashboard.*\.json$"),
    re.compile(r"^data/github-activity.*\.json$"),
    re.compile(r"^data/github-profile-badges.*\.json$"),
    re.compile(r"^data/compliance-.*\.json$"),
    re.compile(r"^data/vaccine-.*\.json$"),
    re.compile(r"^data/ad-report.*\.json$"),
    re.compile(r"^data/ad-report.*-manifest\.json$"),
    re.compile(r"^data/seo-rank-autofix.*\.json$"),
    re.compile(r"^data/build-dashboard.*\.json$"),
    re.compile(r"^data/related.*\.json$"),
    re.compile(r"^data/scores.*\.json$"),
    re.compile(r"^data/related-qa-.*\.json$"),
    re.compile(r"^data/owned-covers.*\.json$"),
    re.compile(r"^data/theme-log.*\.json$"),
    re.compile(r"^data/qa-.*\.json$"),
    re.compile(r"^data/auto-healing.*\.json$"),
    re.compile(r"^data/auto-merge-policy.*\.json$"),
    re.compile(r"^data/autofix-.*\.json$"),
    re.compile(r"^data/continuous-merge-validator.*\.json$"),
    re.compile(r"^data/healing-patterns.*\.json$"),
    re.compile(r"^static/data/.*\.json$"),
    re.compile(r"^reports/.*"),
    re.compile(r"^data/.*-report\.json$"),
    re.compile(r"^data/.*-state\.json$"),
]

HOTFIX_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bhotfix\b", re.IGNORECASE),
    re.compile(r"\bP0\b", re.IGNORECASE),
    re.compile(r"\bemergency\b", re.IGNORECASE),
    re.compile(r"\bcritical\b", re.IGNORECASE),
]


def _get_changed_files_push(before: str, after: str) -> list[str]:
    """Get changed files between two commit SHAs."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", before, after],
            capture_output=True, text=True, timeout=15, check=True,
        )
        return [f.strip() for f in result.stdout.splitlines() if f.strip()]
    except subprocess.SubprocessError:
        return []


def _get_changed_files_head() -> list[str]:
    """Get changed files compared to HEAD~1."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
            capture_output=True, text=True, timeout=15, check=True,
        )
        return [f.strip() for f in result.stdout.splitlines() if f.strip()]
    except subprocess.SubprocessError:
        return []


def _get_commit_message() -> str:
    """Get the latest commit message."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--pretty=%B"],
            capture_output=True, text=True, timeout=10, check=True,
        )
        return result.stdout.strip()
    except subprocess.SubprocessError:
        return ""


def _classify_files(changed_files: list[str], commit_msg: str) -> str:
    """Classify the change set. Returns 'important', 'low_value', or 'unknown'.

    - If ANY file is important → entire change is IMPORTANT.
    - If ALL files match LOW_VALUE patterns → LOW_VALUE.
    - If no files detected → UNKNOWN (conservative: treat as important).
    """
    if not changed_files:
        return "unknown"

    if any(p.search(commit_msg) for p in HOTFIX_PATTERNS):
        return "important"

    for f in changed_files:
        if not f:
            continue
        # Check if this file matches any LOW_VALUE pattern
        is_low = any(p.search(f) for p in LOW_VALUE_PATTERNS)
        if not is_low:
            return "important"

    return "low_value"


def _github_api_get(path: str, token: str) -> dict | None:
    """Call GitHub REST API and return parsed JSON."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ci-smart-deploy-queue/1.0",
    }
    req = Request(f"https://api.github.com{path}", headers=headers)
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (HTTPError, URLError, OSError):
        return None


def _check_active_deploy(repo: str, token: str) -> tuple[bool, str]:
    """Check if there's already a deploy in_progress or queued.

    Returns (is_active, description).
    """
    runs_data = _github_api_get(
        f"/repos/{repo}/actions/workflows/deploy.yml/runs"
        f"?status=in_progress&per_page=5",
        token,
    )
    queued_data = _github_api_get(
        f"/repos/{repo}/actions/workflows/deploy.yml/runs"
        f"?status=queued&per_page=5",
        token,
    )
    all_runs: list[dict] = []
    if runs_data:
        all_runs.extend(runs_data.get("workflow_runs") or [])
    if queued_data:
        all_runs.extend(queued_data.get("workflow_runs") or [])

    # Filter out the current run (it may also show as queued)
    current_run_id = os.environ.get("GITHUB_RUN_ID", "")
    other_runs = [
        r for r in all_runs
        if str(r.get("id", "")) != current_run_id
    ]

    if not other_runs:
        return False, "No active deploy queued or in_progress"

    statuses = [r.get("status", "unknown") for r in other_runs]
    run_numbers = [str(r.get("run_number", "?")) for r in other_runs]
    return (
        True,
        f"Active deploy(s) found: {', '.join(f'#{n} ({s})' for n, s in zip(run_numbers, statuses))}",
    )


def main() -> int:
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN", "")
    current_run_id = os.environ.get("GITHUB_RUN_ID", "")
    before = os.environ.get("BEFORE_SHA", "")
    after = os.environ.get("AFTER_SHA", "")

    # ── Detect changed files ──
    changed_files: list[str] = []
    if event_name == "push" and before and after:
        changed_files = _get_changed_files_push(before, after)
    elif event_name == "schedule":
        # Scheduled runs: no specific commit changes to check
        changed_files = []
    elif event_name in ("workflow_dispatch", "pull_request"):
        changed_files = _get_changed_files_head()

    commit_msg = _get_commit_message()

    # ── Classify ──
    classification = _classify_files(changed_files, commit_msg)

    # ── IMPORTANT: always proceed ──
    if classification == "important":
        decision = "proceed"
        reason = (
            f"IMPORTANT: {len(changed_files)} changed file(s) include content,"
            f" templates, config, or hotfix — always deploy"
        )
        _emit_outputs(decision, reason, classification)
        return 0

    # ── LOW_VALUE or UNKNOWN: check for active deploy ──
    has_active, active_desc = _check_active_deploy(repo, token)

    if classification == "low_value" and has_active:
        decision = "skip_low_value"
        reason = (
            f"LOW_VALUE: all {len(changed_files)} changed file(s) are generated"
            f" data/reports. {active_desc} — skipping to preserve quota."
        )
        _emit_outputs(decision, reason, classification)
        return 0

    if classification == "low_value":
        decision = "proceed"
        reason = (
            f"LOW_VALUE: {len(changed_files)} changed file(s) are generated data,"
            f" but no active deploy found — proceeding as cleanup deploy."
        )
        _emit_outputs(decision, reason, classification)
        return 0

    # classification == "unknown" (no files detected, e.g. schedule)
    if has_active:
        decision = "skip_low_value"
        reason = (
            f"UNKNOWN: no specific file changes detected (event={event_name})."
            f" {active_desc} — skipping to preserve quota."
        )
        _emit_outputs(decision, reason, classification)
        return 0

    decision = "proceed"
    reason = (
        f"UNKNOWN: no specific file changes detected (event={event_name}),"
        f" no active deploy — proceeding."
    )
    _emit_outputs(decision, reason, classification)
    return 0


def _emit_outputs(decision: str, reason: str, classification: str) -> None:
    """Emit GitHub Actions outputs and print summary."""
    # GitHub Actions: set output
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as fh:
            fh.write(f"decision={decision}\n")
            fh.write(f"reason={reason}\n")
            fh.write(f"classification={classification}\n")
    elif os.environ.get("GITHUB_STEP_SUMMARY"):
        pass

    # Always print for log visibility
    sep = "─" * min(60, max(40, len(reason)))
    print(f"\n{sep}")
    print(f"🔍 Smart Deploy Queue")
    print(f"   Decision:       {decision}")
    print(f"   Classification: {classification}")
    print(f"   Reason:         {reason}")
    print(f"{sep}\n")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"[ci_smart_deploy_queue] internal error: {exc}")
        print(f"::set-output name=decision::proceed")
        print(f"::set-output name=reason::internal error fallback — proceed to be safe")
        print(f"::set-output name=classification::unknown")
        sys.exit(0)
