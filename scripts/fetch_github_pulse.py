#!/usr/bin/env python3
"""
Fetch GitHub Pulse weekly data → data/github-pulse-weekly.json

Lấy dữ liệu từ GitHub REST API (GITHUB_TOKEN) để hiển thị trên /insights/
giống trang GitHub Pulse gốc:
  https://github.com/Banhang-Chogao/zola/pulse?period=weekly

Dữ liệu thu thập:
  - Active PRs + issues
  - Merged PRs, open PRs, closed issues, new issues
  - Changed files, additions, deletions (on main)
  - Top committers (by commit count)

Chạy local:
  GITHUB_TOKEN=ghp_... python scripts/fetch_github_pulse.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "github-pulse-weekly.json"
REPO = os.environ.get("GITHUB_REPOSITORY", "Banhang-Chogao/zola")
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
API = "https://api.github.com"


def _api_get(path: str) -> Any:
    """Call GitHub API with Bearer token."""
    if not TOKEN:
        raise RuntimeError("GITHUB_TOKEN required for GitHub API")
    url = f"{API}{path}"
    req = Request(
        url,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "zola-pulse",
        },
    )
    try:
        with urlopen(req, timeout=45) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"GitHub API {e.code}: {body}") from e
    except URLError as e:
        raise RuntimeError(f"GitHub API unreachable: {e}") from e


def _paginate(path: str, key: str, limit: int = 100) -> list:
    """Paginate GitHub API results."""
    items: list = []
    page = 1
    while len(items) < limit:
        sep = "&" if "?" in path else "?"
        url = f"{path}{sep}per_page=100&page={page}"
        data = _api_get(url)
        batch = data.get(key) if isinstance(data, dict) else data
        if not batch:
            break
        if isinstance(batch, list):
            items.extend(batch)
            if len(batch) < 100:
                break
        else:
            break
        page += 1
    return items[:limit]


def _get_date_range_weekly() -> tuple[str, str]:
    """Return (start, end) ISO dates for weekly range (last 7 days)."""
    now = datetime.now(timezone.utc).date()
    start = (now - timedelta(days=7)).isoformat()
    end = now.isoformat()
    return start, end


def _fetch_active_prs(owner: str, repo: str) -> int:
    """Count active (open) pull requests."""
    data = _api_get(f"/repos/{owner}/{repo}/pulls?state=open&per_page=1")
    # Extract total count from Link header if available, else count items
    if isinstance(data, list):
        return len(data)
    return data.get("total_count", 0) if isinstance(data, dict) else 0


def _fetch_active_issues(owner: str, repo: str) -> int:
    """Count active (open) issues (excluding pull requests)."""
    data = _api_get(f"/repos/{owner}/{repo}/issues?state=open&per_page=1")
    if isinstance(data, list):
        return len(data)
    return data.get("total_count", 0) if isinstance(data, dict) else 0


def _fetch_merged_prs_week(owner: str, repo: str, since: str, until: str) -> int:
    """Count merged PRs in the last week."""
    # GitHub API: merged:2026-06-20..2026-06-27
    query = f"repo:{owner}/{repo} is:pr is:merged merged:{since}..{until}"
    encoded_query = quote(query)
    data = _api_get(f"/search/issues?q={encoded_query}&per_page=1")
    return data.get("total_count", 0) if isinstance(data, dict) else 0


def _fetch_open_prs(owner: str, repo: str) -> int:
    """Count currently open pull requests."""
    query = f"repo:{owner}/{repo} is:pr is:open"
    encoded_query = quote(query)
    data = _api_get(f"/search/issues?q={encoded_query}&per_page=1")
    return data.get("total_count", 0) if isinstance(data, dict) else 0


def _fetch_closed_issues_week(owner: str, repo: str, since: str, until: str) -> int:
    """Count closed issues (excluding PRs) in the last week."""
    # is:issue: exclude PRs
    query = f"repo:{owner}/{repo} is:issue is:closed closed:{since}..{until}"
    encoded_query = quote(query)
    data = _api_get(f"/search/issues?q={encoded_query}&per_page=1")
    return data.get("total_count", 0) if isinstance(data, dict) else 0


def _fetch_new_issues_week(owner: str, repo: str, since: str, until: str) -> int:
    """Count newly created issues (excluding PRs) in the last week."""
    query = f"repo:{owner}/{repo} is:issue created:{since}..{until}"
    encoded_query = quote(query)
    data = _api_get(f"/search/issues?q={encoded_query}&per_page=1")
    return data.get("total_count", 0) if isinstance(data, dict) else 0


def _fetch_commits_main_week(owner: str, repo: str, since: str, until: str) -> dict:
    """Fetch commits on main branch in the last week: count + stats."""
    # Use commit search API for simple count
    query = f"repo:{owner}/{repo} committer-date:{since}..{until} branch:main"
    encoded_query = quote(query)
    data = _api_get(f"/search/commits?q={encoded_query}&per_page=1")
    count = data.get("total_count", 0) if isinstance(data, dict) else 0
    return {"count": count, "authors": []}


def _fetch_changed_files_main_week(owner: str, repo: str, since: str, until: str) -> dict:
    """Fetch file stats for main branch: changed files, additions, deletions."""
    # Compare base vs head to get diff stats
    # Since we want week-over-week, we'll use commit history
    try:
        # Get commits on main in the last week
        commits_data = _api_get(
            f"/repos/{owner}/{repo}/commits?"
            f"since={since}T00:00:00Z&until={until}T23:59:59Z&sha=main"
        )

        if not isinstance(commits_data, list):
            return {"changed_files": 0, "additions": 0, "deletions": 0}

        total_changed = 0
        total_additions = 0
        total_deletions = 0

        for commit in commits_data:
            if "commit" in commit:
                stats = commit.get("stats", {})
                total_additions += stats.get("additions", 0)
                total_deletions += stats.get("deletions", 0)
                # Count unique files affected
                files = commit.get("files", [])
                if files:
                    total_changed += len(files)

        return {
            "changed_files": total_changed,
            "additions": total_additions,
            "deletions": total_deletions,
        }
    except Exception:
        return {"changed_files": 0, "additions": 0, "deletions": 0}


def _fetch_authors_count(owner: str, repo: str, since: str, until: str) -> int:
    """Count unique authors who committed in the last week (excluding merges)."""
    try:
        commits_data = _api_get(
            f"/repos/{owner}/{repo}/commits?"
            f"since={since}T00:00:00Z&until={until}T23:59:59Z&sha=main"
        )

        if not isinstance(commits_data, list):
            return 1

        authors = set()
        for commit in commits_data:
            if "author" in commit and commit["author"]:
                login = commit["author"].get("login")
                if login:
                    authors.add(login)

        return len(authors) if authors else 1
    except Exception:
        return 1


def _fetch_top_committers(owner: str, repo: str, since: str, until: str, limit: int = 5) -> list:
    """Fetch top N committers in the last week."""
    try:
        commits_data = _api_get(
            f"/repos/{owner}/{repo}/commits?"
            f"since={since}T00:00:00Z&until={until}T23:59:59Z&sha=main&per_page=100"
        )

        if not isinstance(commits_data, list):
            return []

        committers: dict = {}
        for commit in commits_data:
            if "author" in commit and commit["author"]:
                author = commit["author"]
                login = author.get("login", "Unknown")
                avatar_url = author.get("avatar_url", "")

                if login not in committers:
                    committers[login] = {
                        "login": login,
                        "avatar_url": avatar_url,
                        "commits": 0,
                    }
                committers[login]["commits"] += 1

        # Sort by commit count descending
        sorted_committers = sorted(
            committers.values(), key=lambda x: x["commits"], reverse=True
        )

        return sorted_committers[:limit]
    except Exception:
        return []


def fetch_pulse_data() -> dict:
    """Fetch all GitHub Pulse weekly data."""
    owner, repo = REPO.split("/", 1)
    since, until = _get_date_range_weekly()

    print(f"Fetching GitHub Pulse data for {REPO}...")
    print(f"  Period: {since} to {until}")

    try:
        active_prs = _fetch_active_prs(owner, repo)
        active_issues = _fetch_active_issues(owner, repo)
        merged_prs = _fetch_merged_prs_week(owner, repo, since, until)
        open_prs = _fetch_open_prs(owner, repo)
        closed_issues = _fetch_closed_issues_week(owner, repo, since, until)
        new_issues = _fetch_new_issues_week(owner, repo, since, until)

        commits_data = _fetch_commits_main_week(owner, repo, since, until)
        commits_count = commits_data["count"]

        files_data = _fetch_changed_files_main_week(owner, repo, since, until)

        authors_count = _fetch_authors_count(owner, repo, since, until)
        top_committers = _fetch_top_committers(owner, repo, since, until)

        print("  ✓ Fetched all metrics")

        return {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "repository": REPO,
            "repository_url": f"https://github.com/{REPO}",
            "source_url": f"https://github.com/{REPO}/pulse?period=weekly",
            "period": "weekly",
            "period_start": since,
            "period_end": until,
            "fetch_error": "",
            "metrics": {
                "active_pull_requests": active_prs,
                "active_issues": active_issues,
                "merged_pull_requests": merged_prs,
                "open_pull_requests": open_prs,
                "closed_issues": closed_issues,
                "new_issues": new_issues,
                "commits_on_main": commits_count,
                "changed_files_on_main": files_data["changed_files"],
                "additions_on_main": files_data["additions"],
                "deletions_on_main": files_data["deletions"],
                "unique_authors": authors_count,
            },
            "top_committers": top_committers,
        }
    except Exception as e:
        print(f"  ✗ Error: {e}", file=sys.stderr)
        return {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "repository": REPO,
            "repository_url": f"https://github.com/{REPO}",
            "source_url": f"https://github.com/{REPO}/pulse?period=weekly",
            "period": "weekly",
            "period_start": since,
            "period_end": until,
            "fetch_error": str(e),
            "metrics": {},
            "top_committers": [],
        }


def main():
    """Main entry point."""
    data = fetch_pulse_data()

    # Write to output file
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✓ Wrote {OUTPUT}")

    if data.get("fetch_error"):
        print(f"⚠ Fetch error: {data['fetch_error']}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
