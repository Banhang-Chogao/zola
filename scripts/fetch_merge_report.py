"""
Thu thập lịch sử merge vào main → data/merge-report.json.

Ghi từ POLICY_EFFECTIVE_DATE trở đi (auto-merge policy).
Chạy local:
  GITHUB_TOKEN=... python scripts/fetch_merge_report.py
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
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "merge-report.json"
REPO = os.environ.get("GITHUB_REPOSITORY", "Banhang-Chogao/zola")
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
API = "https://api.github.com"

# Chỉ ghi merge từ ngày bật auto-merge policy
POLICY_EFFECTIVE_AT = os.environ.get(
    "MERGE_REPORT_SINCE",
    "2026-06-17T00:00:00Z",
)
DEPLOY_WORKFLOW_FILE = "deploy.yml"
MAX_MERGES = 200


def _api_get(path: str) -> Any:
    if not TOKEN:
        raise RuntimeError("GITHUB_TOKEN chưa set")
    url = f"{API}{path}"
    req = Request(
        url,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "zola-merge-report",
        },
    )
    try:
        with urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"GitHub API {e.code}: {body}") from e
    except URLError as e:
        raise RuntimeError(f"GitHub API unreachable: {e}") from e


def _parse_ts(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def classify_change_type(title: str, head_branch: str = "") -> str:
    text = f"{title} {head_branch}".lower()
    rules = [
        ("fix", r"\bfix[(/:\s]|^fix/"),
        ("feature", r"\bfeat[(/:\s]|^feature/"),
        ("content", r"\bcontent/|bài viết|series|posting"),
        ("ci", r"\bci[(/:\s]|workflow|github actions|deploy"),
        ("chore", r"\bchore/|refresh|cập nhật data"),
        ("qa", r"\bqa/|compliance|gatekeeper"),
    ]
    for kind, pattern in rules:
        if re.search(pattern, text):
            return kind
    return "unknown"


def summarize_vi(title: str, body: str | None) -> str:
    title = (title or "").strip()
    if not body:
        return title[:200] if title else "Không có mô tả"
    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    for ln in lines:
        if ln.startswith("#"):
            continue
        if len(ln) > 20 and not ln.startswith("```"):
            return ln[:220]
    return title[:200]


def _find_deploy_run(merge_sha: str, merged_at: str) -> dict[str, Any]:
    owner, name = REPO.split("/", 1)
    try:
        workflows = _api_get(f"/repos/{REPO}/actions/workflows").get("workflows") or []
    except RuntimeError:
        return {}
    wf_id = None
    for wf in workflows:
        if (wf.get("path") or "").endswith(DEPLOY_WORKFLOW_FILE):
            wf_id = wf.get("id")
            break
    if not wf_id:
        return {}

    runs = _api_get(
        f"/repos/{REPO}/actions/workflows/{wf_id}/runs?branch=main&per_page=30",
    ).get("workflow_runs") or []

    merged_dt = _parse_ts(merged_at)
    for run in runs:
        if run.get("head_sha") == merge_sha:
            return {
                "build_run_number": run.get("run_number"),
                "build_url": run.get("html_url", ""),
                "build_conclusion": run.get("conclusion") or run.get("status", ""),
            }
    if merged_dt:
        for run in runs:
            created = _parse_ts(run.get("created_at") or "")
            if not created:
                continue
            delta = (created - merged_dt).total_seconds()
            if 0 <= delta <= 1800:
                return {
                    "build_run_number": run.get("run_number"),
                    "build_url": run.get("html_url", ""),
                    "build_conclusion": run.get("conclusion") or run.get("status", ""),
                }
    return {}


def fetch_merged_prs() -> list[dict]:
    owner, name = REPO.split("/", 1)
    since = _parse_ts(POLICY_EFFECTIVE_AT)
    items: list[dict] = []
    page = 1

    while len(items) < MAX_MERGES and page <= 10:
        batch = _api_get(
            f"/repos/{owner}/{name}/pulls?state=closed&base=main"
            f"&sort=updated&direction=desc&per_page=30&page={page}",
        )
        if not batch:
            break
        for pr in batch:
            if not pr.get("merged_at"):
                continue
            merged_at = pr["merged_at"]
            merged_dt = _parse_ts(merged_at)
            if since and merged_dt and merged_dt < since:
                return items
            number = pr["number"]
            title = pr.get("title") or ""
            body = pr.get("body") or ""
            head_branch = pr.get("head", {}).get("ref") or ""
            merge_sha = pr.get("merge_commit_sha") or ""
            labels = [lb.get("name", "") for lb in (pr.get("labels") or [])]
            merged_by = ""
            if pr.get("merged_by"):
                merged_by = pr["merged_by"].get("login") or ""

            build = _find_deploy_run(merge_sha, merged_at)
            items.append({
                "pr_number": number,
                "pr_title": title,
                "pr_url": pr.get("html_url", ""),
                "merged_at": merged_at,
                "merge_commit_sha": merge_sha,
                "merge_commit_short": merge_sha[:7] if merge_sha else "",
                "head_branch": head_branch,
                "summary_vi": summarize_vi(title, body),
                "change_type": classify_change_type(title, head_branch),
                "files_changed": None,
                "additions": None,
                "deletions": None,
                "merged_by": merged_by,
                "auto_merged": "auto-merged" in labels
                    or merged_by in ("github-actions[bot]",),
                "build_run_number": build.get("build_run_number"),
                "build_url": build.get("build_url", ""),
                "build_conclusion": build.get("build_conclusion", ""),
            })
        if len(batch) < 30:
            break
        page += 1

    # Enrich với stats PR (files/additions) — best effort
    for entry in items:
        num = entry["pr_number"]
        try:
            detail = _api_get(f"/repos/{owner}/{name}/pulls/{num}")
            entry["additions"] = detail.get("additions")
            entry["deletions"] = detail.get("deletions")
            entry["files_changed"] = detail.get("changed_files")
        except RuntimeError:
            pass

    items.sort(key=lambda m: m.get("merged_at") or "", reverse=True)
    return items[:MAX_MERGES]


def compute_stats(merges: list[dict]) -> dict:
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)

    by_type: dict[str, int] = {}
    today_n = week_n = month_n = 0
    auto_n = 0

    for m in merges:
        dt = _parse_ts(m.get("merged_at") or "")
        if dt:
            if dt >= today_start:
                today_n += 1
            if dt >= week_start:
                week_n += 1
            if dt >= month_start:
                month_n += 1
        ct = m.get("change_type") or "unknown"
        by_type[ct] = by_type.get(ct, 0) + 1
        if m.get("auto_merged"):
            auto_n += 1

    return {
        "total": len(merges),
        "today": today_n,
        "this_week": week_n,
        "this_month": month_n,
        "auto_merged": auto_n,
        "by_change_type": by_type,
    }


def main() -> int:
    print(f"Fetching merge report for {REPO} (since {POLICY_EFFECTIVE_AT})...", flush=True)
    try:
        merges = fetch_merged_prs()
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        if OUTPUT.exists():
            print("Giữ nguyên merge-report.json hiện có.", file=sys.stderr)
            return 0
        return 1

    owner, name = REPO.split("/", 1)
    payload = {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "policy_effective_at": POLICY_EFFECTIVE_AT,
        "source_repo": f"https://github.com/{owner}/{name}",
        "source_label": "GitHub Pull Requests",
        "stats": compute_stats(merges),
        "merges": merges,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(merges)} merges → {OUTPUT.relative_to(ROOT)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())