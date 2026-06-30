#!/usr/bin/env python3
"""
Auto-add a deploy milestone to data/theme-log.json on every production deploy.

Runs in deploy.yml after theme_audit.py. Detects current commit, PR number,
and deduplicates by commit SHA. Never exits non-zero (non-blocking).

Usage:
  python3 scripts/auto_add_milestone_deploy.py
  python3 scripts/auto_add_milestone_deploy.py --dry-run

CI env vars used:
  GITHUB_SHA, GITHUB_REPOSITORY, GITHUB_TOKEN (optional, for PR detection)
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA_FILE = REPO / "data" / "theme-log.json"
TZ_VN = timezone(timedelta(hours=7))


def _run(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return r.stdout.strip(), r.returncode
    except Exception:
        return "", -1


def get_commit_sha():
    sha = os.environ.get("GITHUB_SHA", "")
    if sha:
        return sha[:7]
    out, _ = _run(["git", "rev-parse", "--short=7", "HEAD"])
    return out or "unknown"


def get_commit_subject():
    out, _ = _run(["git", "log", "-1", "--format=%s"])
    return out or "Deploy"


def get_pr_number(commit_subject):
    """Try to detect PR number from commit message or gh CLI."""
    m = re.match(r"Merge pull request #(\d+)", commit_subject)
    if m:
        return m.group(1)

    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if token and repo:
        out, _ = _run([
            "gh", "pr", "list",
            "--repo", repo,
            "--state", "merged",
            "--head", os.environ.get("GITHUB_REF_NAME", ""),
            "--json", "number",
            "--jq", ".[0].number",
            "--limit", "1",
        ])
        if out:
            return out

    return ""


def detect_risk(commit_subject, files_changed):
    keywords_high = {"rollback", "revert", "migration", "refactor", "redesign"}
    if any(k in commit_subject.lower() for k in keywords_high):
        return "medium"
    return "low"


def main():
    dry_run = "--dry-run" in sys.argv

    sha = get_commit_sha()
    subject = get_commit_subject()
    pr = get_pr_number(subject)
    pr_str = f"#{pr}" if pr else ""
    date_str = datetime.now(TZ_VN).isoformat(timespec="seconds")

    title = subject[:80]
    if len(subject) > 80:
        title += "..."

    entry_id_date = date_str[:10].replace("-", "")
    title_slug = re.sub(r"[^a-z0-9]+", "-", title.lower())[:30].strip("-")
    raw_id = f"deploy-{title}-{sha}"
    id_hash = hashlib.sha256(raw_id.encode()).hexdigest()[:6]
    entry_id = f"milestone-{entry_id_date}-deploy-{title_slug}-{id_hash}"

    entry = {
        "id": entry_id,
        "type": "deploy",
        "title": title,
        "summary": f"Auto milestone — production deploy at {date_str}",
        "commit": sha,
        "merge_commit": "",
        "pr": pr_str,
        "branch": os.environ.get("GITHUB_REF_NAME", ""),
        "date": date_str,
        "status": "live",
        "scope": f"production deploy — {subject}",
        "routes": ["//*"],
        "files": [],
        "restore_mode": "cherry-pick-files",
        "restore_hint": "",
        "qa": {"zola_build": "ci-only", "qa_check": "ci-only", "qa_404": "ci-only"},
        "risk": "low",
        "notes": f"Auto-generated on deploy. Commit: {sha}. PR: {pr_str}.",
    }

    if dry_run:
        print(json.dumps(entry, ensure_ascii=False, indent=2))
        print("\n[DRY RUN] Not written.", file=sys.stderr)
        return

    if not DATA_FILE.exists():
        print("[SKIP] theme-log.json not found", file=sys.stderr)
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "milestones" not in data:
        data["milestones"] = []

    for m in data["milestones"]:
        if m.get("commit") == sha:
            print(f"[SKIP] Commit {sha} already has a milestone", file=sys.stderr)
            return

    data["milestones"].insert(0, entry)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"[OK] Added deploy milestone for commit {sha}: {subject}", file=sys.stderr)


if __name__ == "__main__":
    import hashlib
    try:
        main()
    except Exception as exc:
        print(f"::warning::auto_add_milestone_deploy error: {exc}", file=sys.stderr)
