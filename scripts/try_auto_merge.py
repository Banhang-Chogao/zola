"""
Auto-merge PR vào main khi required CI checks pass (FULLY AUTOMATED OPERATIONS).

Policy: scripts/auto_merge_policy.py + data/auto-merge-policy.json

Chạy từ workflow auto-merge.yml hoặc local:
  GITHUB_TOKEN=... python scripts/try_auto_merge.py --pr 313
  GITHUB_TOKEN=... python scripts/try_auto_merge.py --scan-open
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from auto_merge_policy import (
    LOOP_STATE_FILE,
    PrContext,
    evaluate,
    is_bot_actor,
    parse_compliance_score_from_paths,
)

REPO = os.environ.get("GITHUB_REPOSITORY", "Banhang-Chogao/zola")
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
API = "https://api.github.com"

BLOCKED_ACTORS = frozenset({
    "dependabot[bot]",
    "renovate[bot]",
    "github-advanced-security[bot]",
})
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


def _merge_pr(number: int, method: str = "squash") -> dict:
    owner, name = REPO.split("/", 1)
    return _api(
        "PUT",
        f"/repos/{owner}/{name}/pulls/{number}/merge",
        {"merge_method": method},
    )


def _delete_branch(ref: str) -> None:
    if not ref or ref == "main":
        return
    owner, name = REPO.split("/", 1)
    try:
        _api("DELETE", f"/repos/{owner}/{name}/git/refs/heads/{ref}")
    except RuntimeError:
        pass


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
        if SKIP_COMMENT_MARKER in (c.get("body") or ""):
            return True
    return False


def post_skip_comment(number: int, reason: str, *, force: bool = False) -> None:
    if not force and _has_skip_comment(number):
        return
    body = (
        f"{SKIP_COMMENT_MARKER}\n"
        f"**Auto-merge skip** — PR #{number}\n\n"
        f"- **Lý do:** {reason}\n"
        f"- **Policy:** `FULLY AUTOMATED OPERATIONS` — chỉ protected domain cần review tay.\n"
        f"- **Override:** gắn label `no-auto-merge` hoặc `manual-review`.\n"
        f"- **Doc:** `data/auto-merge-policy.json`, `.github/ACTIONS-PERMISSIONS.md`\n"
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


def _fetch_file_at_ref(path: str, ref: str) -> str | None:
    owner, name = REPO.split("/", 1)
    try:
        data = _api("GET", f"/repos/{owner}/{name}/contents/{path}?ref={ref}")
        content = data.get("content")
        if not content:
            return None
        return base64.b64decode(content).decode("utf-8")
    except RuntimeError:
        return None


def _fetch_pr_checks(number: int, pr: dict) -> list[dict[str, str]]:
    owner, name = REPO.split("/", 1)
    head_sha = (pr.get("head") or {}).get("sha") or ""
    if not head_sha:
        return []
    checks = _api(
        "GET",
        f"/repos/{owner}/{name}/commits/{head_sha}/check-runs?per_page=100",
    )
    return [
        {"name": c.get("name"), "conclusion": (c.get("conclusion") or "").upper()}
        for c in (checks.get("check_runs") or [])
    ]


def _build_context(pr: dict, number: int) -> PrContext:
    paths = _fetch_pr_files(number)
    head_ref = pr.get("headRefName") or (pr.get("head") or {}).get("ref") or ""
    head_sha = (pr.get("head") or {}).get("sha") or ""
    labels = {lb.get("name", "") for lb in (pr.get("labels") or [])}
    checks = _fetch_pr_checks(number, pr)

    def loader(p: str) -> str | None:
        return _fetch_file_at_ref(p, head_sha)

    compliance = parse_compliance_score_from_paths(paths, loader)

    return PrContext(
        number=number,
        title=pr.get("title") or "",
        body=pr.get("body") or "",
        head_ref=head_ref,
        actor=(pr.get("user") or {}).get("login") or "",
        labels=labels,
        paths=paths,
        checks=checks,
        compliance_score=compliance,
    )


def _blocked_actor(actor: str) -> str | None:
    if actor in BLOCKED_ACTORS:
        return f"Actor bị chặn: {actor}"
    if actor.endswith("[bot]") and not is_bot_actor(actor):
        return f"Actor bot không tin cậy: {actor}"
    return None


def _record_merge_event(ctx: PrContext) -> None:
    state_path = LOOP_STATE_FILE
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        state = {"events": [], "blocked_patterns": []}
    events = state.setdefault("events", [])
    events.append({
        "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pr": ctx.number,
        "signature": ctx.title.strip().lower()[:80],
        "head_ref": ctx.head_ref,
    })
    window = 24
    state["events"] = events[-window:]
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return
    try:
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass


def evaluate_pr(pr: dict, *, number: int | None = None) -> tuple[bool, str]:
    pr_num = number or pr.get("number")
    if not pr_num:
        return False, "Thiếu PR number"

    if pr.get("isDraft"):
        return False, "PR là draft"
    if pr.get("headRefName") == "main" or (pr.get("head") or {}).get("ref") == "main":
        return False, "Head branch là main"

    actor = (pr.get("user") or {}).get("login") or ""
    actor_block = _blocked_actor(actor)
    if actor_block:
        return False, actor_block

    if pr.get("mergeable") is False:
        return False, "PR không mergeable (conflict?)"
    state = (pr.get("mergeable_state") or pr.get("mergeStateStatus") or "").lower()
    if state in ("dirty", "blocked"):
        return False, f"mergeable_state={state}"

    ctx = _build_context(pr, int(pr_num))
    ready, reason, _category = evaluate(ctx)
    return ready, reason


def try_merge_pr(number: int, *, dry_run: bool = False) -> int:
    owner, name = REPO.split("/", 1)
    pr_data = _api("GET", f"/repos/{owner}/{name}/pulls/{number}")

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

    ctx = _build_context(pr_data, number)
    result = _merge_pr(number)
    if result.get("merged"):
        print(f"  merged — sha {result.get('sha', '')[:7]}")
        _label_pr(number, "auto-merged")
        _delete_branch(ctx.head_ref)
        _record_merge_event(ctx)
        return 0
    print(f"  merge failed: {result}")
    return 1


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
            ctx = _build_context(pr, number)
            result = _merge_pr(number)
            if result.get("merged"):
                print(f"PR #{number}: merged ✓")
                _label_pr(number, "auto-merged")
                _delete_branch(ctx.head_ref)
                _record_merge_event(ctx)
            else:
                print(f"PR #{number}: merge failed — {result}")
                exit_code = 1
        except RuntimeError as e:
            print(f"PR #{number}: error — {e}")
            exit_code = 1
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description="Auto-merge PR khi CI pass (FULLY AUTOMATED)")
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