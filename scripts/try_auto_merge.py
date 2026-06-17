"""
Auto-merge PR vào main khi required CI checks pass.

Chạy từ workflow auto-merge.yml hoặc local:
  GITHUB_TOKEN=... python scripts/try_auto_merge.py --pr 313
  GITHUB_TOKEN=... python scripts/try_auto_merge.py --scan-open
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO = os.environ.get("GITHUB_REPOSITORY", "Banhang-Chogao/zola")
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
API = "https://api.github.com"

REQUIRED_CHECKS = frozenset({"QA Gatekeeper", "PR Policy"})
OK_CONCLUSIONS = frozenset({"success", "skipped", "neutral"})
BLOCKED_LABELS = frozenset({"no-auto-merge", "manual-review"})
BLOCKED_ACTORS = frozenset({
    "dependabot[bot]",
    "renovate[bot]",
    "github-advanced-security[bot]",
})
SENSITIVE_PATH_RE = re.compile(
    r"(^|/)\.github/workflows/|"
    r"(^|/)(services/paywall|backend/admin|private_content)(/|$)|"
    r"(paywall|payment|security|admin)",
    re.I,
)
SKIP_COMMENT_MARKER = "<!-- auto-merge-skip -->"


def _api(method: str, path: str, body: dict | None = None) -> Any:
    if not TOKEN:
        raise RuntimeError("GITHUB_TOKEN chưa set")
    url = f"{API}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "zola-auto-merge",
        },
        method=method,
    )
    try:
        with urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"GitHub API {e.code} {path}: {err}") from e
    except URLError as e:
        raise RuntimeError(f"GitHub API unreachable: {e}") from e


def _checks_green(pr: dict) -> tuple[bool, str]:
    rollup = pr.get("statusCheckRollup") or []
    if not rollup:
        return False, "Chưa có status check"

    seen: set[str] = set()
    for item in rollup:
        name = item.get("name") or ""
        conclusion = (item.get("conclusion") or "").lower()
        if name in REQUIRED_CHECKS:
            seen.add(name)
            if conclusion not in OK_CONCLUSIONS:
                return False, f"Check '{name}' = {conclusion or 'pending'}"

    missing = REQUIRED_CHECKS - seen
    if missing:
        return False, f"Thiếu checks: {', '.join(sorted(missing))}"

    return True, "CI xanh"


def _blocked(pr: dict) -> str | None:
    if pr.get("isDraft"):
        return "PR là draft"
    user = (pr.get("user") or {}).get("login") or ""
    if user in BLOCKED_ACTORS or user.endswith("[bot]") and user != "github-actions[bot]":
        return f"Actor bị chặn: {user}"
    if pr.get("headRefName") == "main":
        return "Head branch là main"
    labels = {lb.get("name", "") for lb in (pr.get("labels") or [])}
    hit = labels & BLOCKED_LABELS
    if hit:
        return f"Label chặn auto-merge: {', '.join(sorted(hit))}"
    return None


def _merge_pr(number: int, method: str = "squash") -> dict:
    owner, name = REPO.split("/", 1)
    return _api(
        "PUT",
        f"/repos/{owner}/{name}/pulls/{number}/merge",
        {"merge_method": method},
    )


def _label_pr(number: int, label: str) -> None:
    owner, name = REPO.split("/", 1)
    try:
        _api("POST", f"/repos/{owner}/{name}/issues/{number}/labels", {"labels": [label]})
    except RuntimeError:
        pass


def _comment_pr(number: int, body: str) -> None:
    owner, name = REPO.split("/", 1)
    try:
        _api("POST", f"/repos/{owner}/{name}/issues/{number}/comments", {"body": body})
    except RuntimeError:
        pass


def _has_skip_comment(number: int) -> bool:
    owner, name = REPO.split("/", 1)
    try:
        comments = _api(
            "GET",
            f"/repos/{owner}/{name}/issues/{number}/comments?per_page=30",
        )
    except RuntimeError:
        return False
    for c in comments or []:
        body = c.get("body") or ""
        if SKIP_COMMENT_MARKER in body:
            return True
    return False


def post_skip_comment(number: int, reason: str, *, force: bool = False) -> None:
    if not force and _has_skip_comment(number):
        return
    body = (
        f"{SKIP_COMMENT_MARKER}\n"
        f"**Auto-merge skip** — PR #{number}\n\n"
        f"- **Lý do:** {reason}\n"
        f"- **Cần làm:** Approve workflows trên PR (nếu CI = `action_required`), "
        f"hoặc gắn label `no-auto-merge` nếu cần review tay.\n"
        f"- Script: `scripts/try_auto_merge.py`"
    )
    _comment_pr(number, body)


def _fetch_pr_files(number: int) -> list[str]:
    owner, name = REPO.split("/", 1)
    paths: list[str] = []
    page = 1
    while page <= 5:
        batch = _api(
            "GET",
            f"/repos/{owner}/{name}/pulls/{number}/files?per_page=100&page={page}",
        )
        if not batch:
            break
        paths.extend(f.get("filename", "") for f in batch if f.get("filename"))
        if len(batch) < 100:
            break
        page += 1
    return paths


def _sensitive_paths(number: int) -> str | None:
    paths = _fetch_pr_files(number)
    if not paths:
        return None
    hits = [p for p in paths if SENSITIVE_PATH_RE.search(p)]
    if hits:
        return f"File nhạy cảm: {', '.join(sorted(hits)[:5])}"
    return None


def evaluate_pr(pr: dict, *, number: int | None = None) -> tuple[bool, str]:
    reason = _blocked(pr)
    if reason:
        return False, reason
    if pr.get("mergeable") is False:
        return False, "PR không mergeable (conflict?)"
    state = (pr.get("mergeable_state") or pr.get("mergeStateStatus") or "").lower()
    if state in ("dirty", "blocked"):
        return False, f"mergeable_state={state}"
    pr_num = number or pr.get("number")
    if pr_num:
        sensitive = _sensitive_paths(int(pr_num))
        if sensitive:
            return False, sensitive
    ok, msg = _checks_green(pr)
    if not ok:
        return False, msg
    return True, "Sẵn sàng auto-merge"


def try_merge_pr(number: int, *, dry_run: bool = False) -> int:
    owner, name = REPO.split("/", 1)
    pr_data = _api("GET", f"/repos/{owner}/{name}/pulls/{number}")
    pr_data = _fetch_pr_checks(number, pr_data)

    ready, reason = evaluate_pr(pr_data, number=number)
    title = pr_data.get("title", "")
    print(f"PR #{number}: {title}")
    if not ready:
        print(f"  skip — {reason}")
        if not dry_run:
            post_skip_comment(number, reason)
        return 0

    if dry_run:
        print("  dry-run — would merge")
        return 0

    result = _merge_pr(number)
    if result.get("merged"):
        print(f"  merged — sha {result.get('sha', '')[:7]}")
        _label_pr(number, "auto-merged")
        return 0
    print(f"  merge failed: {result}")
    return 1


def _fetch_pr_checks(number: int, pr: dict) -> dict:
    owner, name = REPO.split("/", 1)
    head_sha = (pr.get("head") or {}).get("sha") or ""
    if not head_sha:
        return pr
    checks = _api(
        "GET",
        f"/repos/{owner}/{name}/commits/{head_sha}/check-runs?per_page=100",
    )
    pr = dict(pr)
    pr["statusCheckRollup"] = [
        {"name": c.get("name"), "conclusion": (c.get("conclusion") or "").upper()}
        for c in (checks.get("check_runs") or [])
    ]
    return pr


def _paginate_open_prs() -> list[dict]:
    owner, name = REPO.split("/", 1)
    items: list[dict] = []
    page = 1
    while page <= 10:
        batch = _api(
            "GET",
            f"/repos/{owner}/{name}/pulls?state=open&base=main&per_page=30&page={page}",
        )
        if not batch:
            break
        items.extend(batch)
        if len(batch) < 30:
            break
        page += 1
    return items


def scan_open(*, dry_run: bool = False) -> int:
    prs = _paginate_open_prs()
    print(f"Scanning {len(prs)} open PR(s) → {REPO}")
    exit_code = 0
    for pr in prs:
        number = pr.get("number")
        if not number:
            continue
        pr = _fetch_pr_checks(number, pr)
        ready, reason = evaluate_pr(pr, number=number)
        if not ready:
            print(f"PR #{number}: skip — {reason}")
            if not dry_run:
                post_skip_comment(number, reason)
            continue
        if dry_run:
            print(f"PR #{number}: dry-run — would merge")
            continue
        try:
            result = _merge_pr(number)
            if result.get("merged"):
                print(f"PR #{number}: merged ✓")
                _label_pr(number, "auto-merged")
            else:
                print(f"PR #{number}: merge failed — {result}")
                exit_code = 1
        except RuntimeError as e:
            print(f"PR #{number}: error — {e}")
            exit_code = 1
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description="Auto-merge PR khi CI pass")
    parser.add_argument("--pr", type=int, help="Merge một PR cụ thể")
    parser.add_argument("--scan-open", action="store_true", help="Quét mọi PR open")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.pr:
        return try_merge_pr(args.pr, dry_run=args.dry_run)
    if args.scan_open:
        return scan_open(dry_run=args.dry_run)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())