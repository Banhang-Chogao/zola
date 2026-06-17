#!/usr/bin/env python3
"""
Build GitHub Activity data for /insights/ → data/github-activity.json.

Sources (build-time only, no frontend tokens):
  - git log — daily commits (always available in CI)
  - GitHub REST API — PRs, issues, pull request reviews (GITHUB_TOKEN)
  - changelog.json — PR dates fallback when API unavailable

Local:
  python3 scripts/build_github_activity.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "github-activity.json"
CHANGELOG = ROOT / "changelog.json"
REPO = os.environ.get("GITHUB_REPOSITORY", "Banhang-Chogao/zola")
REPO_URL = f"https://github.com/{REPO}"
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
API = "https://api.github.com"
PERIOD_DAYS = 365
MONTH_LABELS = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)
WEEKDAY_LABELS = ("Mon", "Wed", "Fri")


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso_date(value: str) -> date | None:
    if not value:
        return None
    try:
        if "T" in value:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _period_bounds(today: date | None = None) -> tuple[date, date]:
    end = today or datetime.now(timezone.utc).date()
    start = end - timedelta(days=PERIOD_DAYS - 1)
    return start, end


def _empty_day_counts(start: date, end: date) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    cur = start
    while cur <= end:
        key = cur.isoformat()
        counts[key] = {
            "commits": 0,
            "pull_requests": 0,
            "issues": 0,
            "reviews": 0,
        }
        cur += timedelta(days=1)
    return counts


def _api_get(path: str) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "zola-github-activity",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = Request(f"{API}{path}", headers=headers)
    try:
        with urlopen(req, timeout=45) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"GitHub API {e.code}: {body}") from e
    except URLError as e:
        raise RuntimeError(f"GitHub API unreachable: {e}") from e


def _paginate_list(path: str, limit: int = 500) -> list[dict]:
    items: list[dict] = []
    page = 1
    while len(items) < limit:
        sep = "&" if "?" in path else "?"
        batch = _api_get(f"{path}{sep}per_page=100&page={page}")
        if not isinstance(batch, list) or not batch:
            break
        items.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return items[:limit]


def _git_log_commits(start: date, end: date) -> tuple[dict[str, int], str | None, str | None]:
    since = start.isoformat()
    until = (end + timedelta(days=1)).isoformat()
    fmt = "%aI"
    try:
        out = subprocess.run(
            ["git", "log", f"--since={since}", f"--until={until}", f"--pretty=format:{fmt}"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
            timeout=120,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        raise RuntimeError(f"git log failed: {e}") from e

    per_day: dict[str, int] = defaultdict(int)
    authors: dict[str, int] = defaultdict(int)
    latest: str | None = None

    for line in out.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        d = _parse_iso_date(line)
        if not d or d < start or d > end:
            continue
        key = d.isoformat()
        per_day[key] += 1
        if latest is None or line > latest:
            latest = line

    try:
        auth_out = subprocess.run(
            [
                "git", "log", f"--since={since}", f"--until={until}",
                "--pretty=format:%an",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
            timeout=120,
        )
        for name in auth_out.stdout.splitlines():
            name = name.strip()
            if name:
                authors[name] += 1
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        authors = {}

    top_author = None
    if authors:
        human = {k: v for k, v in authors.items() if "[bot]" not in k.lower()}
        pool = human or authors
        top_author = max(pool, key=lambda k: pool[k])

    return dict(per_day), top_author, latest


def _changelog_prs(start: date, end: date) -> dict[str, int]:
    if not CHANGELOG.is_file():
        return {}
    try:
        data = json.loads(CHANGELOG.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    per_day: dict[str, int] = defaultdict(int)
    for item in data.get("items") or []:
        if not item.get("pr"):
            continue
        d = _parse_iso_date(str(item.get("date", "")))
        if not d or d < start or d > end:
            continue
        per_day[d.isoformat()] += 1
    return dict(per_day)


def _fetch_api_activity(start: date, end: date) -> tuple[dict[str, int], dict[str, int], dict[str, int], str | None]:
    """Returns (prs_by_day, issues_by_day, reviews_by_day, latest_iso)."""
    prs: dict[str, int] = defaultdict(int)
    issues: dict[str, int] = defaultdict(int)
    reviews: dict[str, int] = defaultdict(int)
    latest: str | None = None

    owner, name = REPO.split("/", 1)
    pulls = _paginate_list(f"/repos/{owner}/{name}/pulls?state=all&sort=updated&direction=desc", 300)
    for pr in pulls:
        created = pr.get("created_at") or pr.get("updated_at")
        d = _parse_iso_date(str(created))
        if not d or d < start or d > end:
            continue
        key = d.isoformat()
        prs[key] += 1
        if latest is None or str(created) > latest:
            latest = str(created)

        pr_number = pr.get("number")
        if pr_number and TOKEN:
            try:
                revs = _paginate_list(
                    f"/repos/{owner}/{name}/pulls/{pr_number}/reviews?sort=updated&direction=desc",
                    50,
                )
            except RuntimeError:
                revs = []
            for rev in revs:
                submitted = rev.get("submitted_at")
                rd = _parse_iso_date(str(submitted))
                if not rd or rd < start or rd > end:
                    continue
                reviews[rd.isoformat()] += 1
                if latest is None or str(submitted) > latest:
                    latest = str(submitted)

    raw_issues = _paginate_list(f"/repos/{owner}/{name}/issues?state=all&sort=updated&direction=desc", 300)
    for issue in raw_issues:
        if issue.get("pull_request"):
            continue
        created = issue.get("created_at") or issue.get("updated_at")
        d = _parse_iso_date(str(created))
        if not d or d < start or d > end:
            continue
        issues[d.isoformat()] += 1
        if latest is None or str(created) > latest:
            latest = str(created)

    return dict(prs), dict(issues), dict(reviews), latest


def contribution_level(count: int, max_count: int) -> int:
    if count <= 0:
        return 0
    if max_count <= 0:
        return 1
    ratio = count / max_count
    if ratio <= 0.25:
        return 1
    if ratio <= 0.5:
        return 2
    if ratio <= 0.75:
        return 3
    return 4


def build_heatmap_weeks(
    start: date,
    end: date,
    day_totals: dict[str, int],
) -> dict[str, Any]:
    max_count = max(day_totals.values()) if day_totals else 0

    # GitHub columns start on Sunday (row 0 = Sun … row 6 = Sat).
    grid_start = start - timedelta(days=(start.weekday() + 1) % 7)
    last_week_start = end - timedelta(days=(end.weekday() + 1) % 7)
    weeks: list[dict[str, Any]] = []
    cur_sunday = grid_start
    labeled_months: set[int] = set()

    while cur_sunday <= last_week_start:
        days_col: list[dict[str, Any] | None] = []
        month_label = ""
        in_range_months: list[int] = []

        for offset in range(7):
            d = cur_sunday + timedelta(days=offset)
            if d < start or d > end:
                days_col.append(None)
                continue
            key = d.isoformat()
            count = day_totals.get(key, 0)
            in_range_months.append(d.month)
            if d.day == 1:
                month_label = MONTH_LABELS[d.month - 1]
                labeled_months.add(d.month)
            days_col.append({
                "date": key,
                "count": count,
                "level": contribution_level(count, max_count),
            })

        if not month_label and in_range_months:
            for m in sorted(set(in_range_months)):
                if m not in labeled_months:
                    month_label = MONTH_LABELS[m - 1]
                    labeled_months.add(m)
                    break

        weeks.append({"month_label": month_label, "days": days_col})
        cur_sunday += timedelta(days=7)

    return {
        "weekday_labels": list(WEEKDAY_LABELS),
        "weeks": weeks,
        "max_count": max_count,
    }


def _breakdown(counts: dict[str, dict[str, int]]) -> dict[str, Any]:
    totals = {
        "commits": 0,
        "pull_requests": 0,
        "issues": 0,
        "reviews": 0,
    }
    for bucket in counts.values():
        for key in totals:
            totals[key] += bucket[key]

    grand = sum(totals.values())
    pct = {}
    for key, val in totals.items():
        pct[key] = round(val / grand * 100) if grand else 0

    # Fix rounding drift so sum = 100
    if grand:
        drift = 100 - sum(pct.values())
        if drift:
            dominant = max(totals, key=lambda k: totals[k])
            pct[dominant] += drift

    return {
        "commits": totals["commits"],
        "pull_requests": totals["pull_requests"],
        "issues": totals["issues"],
        "reviews": totals["reviews"],
        "commits_pct": pct["commits"],
        "pull_requests_pct": pct["pull_requests"],
        "issues_pct": pct["issues"],
        "reviews_pct": pct["reviews"],
    }


def build_activity(today: date | None = None, use_api: bool = True) -> dict[str, Any]:
    start, end = _period_bounds(today)
    day_counts = _empty_day_counts(start, end)

    commits_by_day, contributor, git_latest = _git_log_commits(start, end)
    for key, n in commits_by_day.items():
        if key in day_counts:
            day_counts[key]["commits"] = n

    api_error: str | None = None
    prs_by_day: dict[str, int] = {}
    issues_by_day: dict[str, int] = {}
    reviews_by_day: dict[str, int] = {}
    api_latest: str | None = None

    if use_api:
        try:
            prs_by_day, issues_by_day, reviews_by_day, api_latest = _fetch_api_activity(start, end)
        except RuntimeError as e:
            api_error = str(e)
            prs_by_day = _changelog_prs(start, end)

    if not prs_by_day:
        prs_by_day = _changelog_prs(start, end)

    for key, n in prs_by_day.items():
        if key in day_counts:
            day_counts[key]["pull_requests"] = n
    for key, n in issues_by_day.items():
        if key in day_counts:
            day_counts[key]["issues"] = n
    for key, n in reviews_by_day.items():
        if key in day_counts:
            day_counts[key]["reviews"] = n

    day_totals: dict[str, int] = {}
    days_list: list[dict[str, Any]] = []
    total_contributions = 0
    cur = start
    while cur <= end:
        key = cur.isoformat()
        bucket = day_counts[key]
        count = sum(bucket.values())
        day_totals[key] = count
        total_contributions += count
        days_list.append({
            "date": key,
            "count": count,
            **bucket,
        })
        cur += timedelta(days=1)

    latest_activity = git_latest
    for candidate in (api_latest,):
        if candidate and (latest_activity is None or candidate > latest_activity):
            latest_activity = candidate

    source = "git+api" if use_api and not api_error else "git"
    if api_error and prs_by_day:
        source = "git+changelog"

    return {
        "updated_at": _iso_now(),
        "source": source,
        "stale": bool(api_error),
        "fetch_error": api_error or "",
        "repository": REPO,
        "repository_url": REPO_URL,
        "contributor": contributor or "",
        "period_days": PERIOD_DAYS,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "total_contributions": total_contributions,
        "latest_activity_at": latest_activity or "",
        "days": days_list,
        "breakdown": _breakdown(day_counts),
        "heatmap": build_heatmap_weeks(start, end, day_totals),
    }


def load_existing() -> dict[str, Any] | None:
    if not OUTPUT.is_file():
        return None
    try:
        return json.loads(OUTPUT.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def write_output(payload: dict[str, Any]) -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    existing = load_existing()
    try:
        payload = build_activity()
        write_output(payload)
    except Exception as e:
        if existing:
            existing["stale"] = True
            existing["fetch_error"] = str(e)[:300]
            write_output(existing)
            print(f"Giữ github-activity.json cache — {e}", file=sys.stderr)
            return 0
        try:
            payload = build_activity(use_api=False)
            payload["stale"] = True
            payload["fetch_error"] = str(e)[:300]
            write_output(payload)
            print(f"Fallback git-only — {e}", file=sys.stderr)
            return 0
        except Exception as inner:
            print(f"build_github_activity failed: {inner}", file=sys.stderr)
            return 1

    print(
        f"github-activity: {payload['total_contributions']} contributions "
        f"({payload['source']}) → {OUTPUT.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())