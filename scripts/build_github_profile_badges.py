#!/usr/bin/env python3
"""
Build archived GitHub Profile Badges for /insights/ → data/github-profile-badges.json.

Sources:
  - data/github-profile-badges.config.json (archived achievements + repo badges)
  - GitHub REST API (optional repo milestones — stars, forks, open issues)
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "data" / "github-profile-badges.config.json"
OUTPUT = ROOT / "data" / "github-profile-badges.json"
REPO = os.environ.get("GITHUB_REPOSITORY", "Banhang-Chogao/zola")
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
API = "https://api.github.com"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_config() -> dict[str, Any]:
    if not CONFIG.is_file():
        return {
            "profile": "Banhang-Chogao",
            "profile_url": "https://github.com/Banhang-Chogao",
            "repository": REPO,
            "repository_url": f"https://github.com/{REPO}",
            "badges": [],
        }
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def _api_get(path: str) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "zola-github-profile-badges",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = Request(f"{API}{path}", headers=headers)
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _repo_milestone_badges(repo_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Derive non-achievement repo badges from API stats (distinct ids)."""
    badges: list[dict[str, Any]] = []
    stars = int(repo_data.get("stargazers_count") or 0)
    forks = int(repo_data.get("forks_count") or 0)
    issues = int(repo_data.get("open_issues_count") or 0)
    now = _iso_now()

    if stars >= 1:
        badges.append({
            "id": "repo-stars",
            "title": f"{stars} Star{'s' if stars != 1 else ''}",
            "description": f"{REPO} has {stars} GitHub star{'s' if stars != 1 else ''}",
            "tier": "gold" if stars >= 25 else "silver" if stars >= 5 else "bronze",
            "icon": "🌟",
            "category": "repo_stat",
            "earned_at": now,
        })
    if forks >= 1:
        badges.append({
            "id": "repo-forks",
            "title": f"{forks} Fork{'s' if forks != 1 else ''}",
            "description": f"{forks} fork{'s' if forks != 1 else ''} on {REPO}",
            "tier": "default",
            "icon": "🍴",
            "category": "repo_stat",
            "earned_at": now,
        })
    if issues > 0:
        badges.append({
            "id": "repo-open-issues",
            "title": "Open Issues",
            "description": f"{issues} open issue{'s' if issues != 1 else ''} tracked on {REPO}",
            "tier": "default",
            "icon": "📋",
            "category": "repo_stat",
            "earned_at": now,
        })
    return badges


def _dedupe_badges(badges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for badge in badges:
        bid = str(badge.get("id", "")).strip()
        if not bid or bid in seen:
            continue
        seen.add(bid)
        out.append(badge)
    return out


def build_badges(use_api: bool = True) -> dict[str, Any]:
    cfg = _load_config()
    badges = list(cfg.get("badges") or [])
    api_error = ""
    source = "config"

    if use_api and TOKEN:
        try:
            owner, name = REPO.split("/", 1)
            repo_data = _api_get(f"/repos/{owner}/{name}")
            milestones = _repo_milestone_badges(repo_data)
            badges.extend(milestones)
            source = "config+api"
        except (HTTPError, URLError, RuntimeError, ValueError) as e:
            api_error = str(e)[:300]

    badges = _dedupe_badges(badges)

    return {
        "updated_at": _iso_now(),
        "source": source,
        "fetch_error": api_error,
        "profile": cfg.get("profile") or "Banhang-Chogao",
        "profile_url": cfg.get("profile_url") or "https://github.com/Banhang-Chogao",
        "repository": cfg.get("repository") or REPO,
        "repository_url": cfg.get("repository_url") or f"https://github.com/{REPO}",
        "badges": badges,
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
        payload = build_badges()
        write_output(payload)
    except Exception as e:
        if existing:
            existing["fetch_error"] = str(e)[:300]
            write_output(existing)
            print(f"Giữ github-profile-badges.json cache — {e}", file=sys.stderr)
            return 0
        print(f"build_github_profile_badges failed: {e}", file=sys.stderr)
        return 1

    print(
        f"github-profile-badges: {len(payload['badges'])} badges "
        f"({payload['source']}) → {OUTPUT.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())