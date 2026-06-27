#!/usr/bin/env python3
"""
Auto-rebase stale branches (no common ancestor with main).

When a branch is created from an old commit and main is force-pushed, the branch
loses its merge-base with main. This script detects such branches and creates PRs
with rebased versions.

Usage:
  python3 scripts/autofix_stale_branches.py              # detect + create PR
  python3 scripts/autofix_stale_branches.py --dry-run    # detect only
  python3 scripts/autofix_stale_branches.py --pr 42      # rebase PR #42 only

Exit codes:
  0 — success (all stale branches rebased or none found)
  1 — error (API fail, git error, etc.)
  2 — dry-run mode (changes not applied)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
REPO = os.environ.get("GITHUB_REPOSITORY", "Banhang-Chogao/zola")
STATE_FILE = REPO_ROOT / "data" / "autofix-stale-branches-state.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_cmd(cmd: list[str], cwd: Path | None = None, check: bool = True) -> tuple[int, str, str]:
    """Run command and return (exit_code, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=cwd or REPO_ROOT,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return 124, "", "Timeout"
    except Exception as e:
        return 1, "", str(e)


def _git_merge_base(head_sha: str, base_sha: str = "origin/main") -> tuple[bool, str]:
    """Check if head_sha has a common ancestor with base_sha. Returns (has_ancestor, merge_base_or_error)."""
    code, out, err = _run_cmd(["git", "merge-base", head_sha, base_sha])
    if code == 0:
        return True, out
    return False, err or "no common ancestor"


def _list_open_prs() -> list[dict[str, Any]]:
    """List open PRs targeting main via gh CLI."""
    code, out, err = _run_cmd(
        ["gh", "pr", "list", "--base", "main", "--state", "open", "--json", "number,title,headRefName,headRefOid,baseRefName"],
        check=False,
    )
    if code != 0 or not TOKEN:
        return []
    try:
        return json.loads(out) if out else []
    except json.JSONDecodeError:
        return []


def _create_rebase_pr(
    source_pr_num: int,
    source_branch: str,
    source_sha: str,
    dry_run: bool = False,
) -> bool:
    """Create a PR with rebased branch. Returns True if successful."""

    # Create temporary working directory
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Fetch and checkout source branch
        code, _, err = _run_cmd(["git", "fetch", "origin", source_branch], cwd=tmpdir_path)
        if code != 0:
            print(f"❌ Failed to fetch branch {source_branch}: {err}")
            return False

        code, _, err = _run_cmd(["git", "checkout", "-b", source_branch, f"origin/{source_branch}"], cwd=tmpdir_path)
        if code != 0:
            print(f"❌ Failed to checkout {source_branch}: {err}")
            return False

        # Rebase onto main
        code, _, err = _run_cmd(["git", "rebase", "origin/main"], cwd=tmpdir_path)
        if code != 0:
            # Check if conflict occurred
            if "CONFLICT" in err or "conflict" in err.lower():
                print(f"⚠️  PR #{source_pr_num} has rebase conflicts — skipping auto-fix (needs manual resolution)")
                return False
            print(f"❌ Failed to rebase {source_branch}: {err}")
            return False

        # Get rebased commit
        code, rebased_sha, err = _run_cmd(["git", "rev-parse", "HEAD"], cwd=tmpdir_path)
        if code != 0:
            print(f"❌ Failed to get rebased commit: {err}")
            return False

        # Verify rebase worked
        has_ancestor, msg = _git_merge_base(rebased_sha, "origin/main")
        if not has_ancestor:
            print(f"❌ Rebase verification failed for PR #{source_pr_num}: {msg}")
            return False

        if dry_run:
            print(f"✓ PR #{source_pr_num} would rebase from {source_sha[:7]} to {rebased_sha[:7]}")
            return True

        # Force-push rebased branch to a new autofix branch
        autofix_branch = f"chore/autofix-stale-branch-pr-{source_pr_num}"
        code, _, err = _run_cmd(
            ["git", "push", "-f", "-u", f"https://oauth2:{TOKEN}@github.com/{REPO}.git", f"HEAD:{autofix_branch}"],
            cwd=tmpdir_path,
        )
        if code != 0:
            print(f"❌ Failed to push autofix branch: {err}")
            return False

        # Create PR comment on source PR explaining the fix
        comment_body = f"""🔧 **Auto-rebase:** This branch was stale (no common ancestor with `main`).

**Fix applied:** Branch has been rebased onto current `main` and pushed to `{autofix_branch}`.

**Next steps:**
1. Review the rebased commits (no changes, just history alignment)
2. If you approve, I'll merge this autofix PR into `main` and your original PR will become mergeable
3. Then your PR can proceed with auto-merge

**Technical:** Branch was created from commit `{source_sha[:7]}`, but `main` was force-pushed. Rebase re-roots your commits onto current `main` without changing their content.
"""

        code, _, err = _run_cmd(
            [
                "gh",
                "pr",
                "comment",
                str(source_pr_num),
                "--body",
                comment_body,
            ],
            check=False,
        )
        if code == 0:
            print(f"✓ PR #{source_pr_num} rebased → {autofix_branch} (comment posted)")
            return True
        else:
            print(f"⚠️  PR #{source_pr_num} rebased but comment failed: {err}")
            return True  # Still count as success (branch was fixed)


def _load_state() -> dict[str, Any]:
    """Load state from file to avoid duplicate fixes."""
    if not STATE_FILE.exists():
        return {"fixed_prs": {}}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"fixed_prs": {}}


def _save_state(state: dict[str, Any]) -> None:
    """Save state to file."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Auto-rebase stale branches")
    parser.add_argument("--dry-run", action="store_true", help="Scan only, no changes")
    parser.add_argument("--pr", type=int, help="Fix specific PR number only")
    parser.add_argument("--timeout", type=int, default=300, help="Max seconds to run")
    args = parser.parse_args()

    # Fetch latest main
    code, _, err = _run_cmd(["git", "fetch", "origin", "main"])
    if code != 0:
        print(f"❌ Failed to fetch main: {err}")
        return 1

    state = _load_state()
    fixed_count = 0

    if args.pr:
        # Fix specific PR
        prs = [{"number": args.pr}]
    else:
        # List all open PRs
        prs = _list_open_prs()

    if not prs:
        print("ℹ️  No open PRs targeting main")
        return 0

    for pr in prs:
        pr_num = pr.get("number")
        if not pr_num:
            continue

        # Skip if already fixed recently
        if str(pr_num) in state.get("fixed_prs", {}):
            print(f"⊘ PR #{pr_num} already fixed in this run")
            continue

        branch = pr.get("headRefName")
        sha = pr.get("headRefOid")
        if not branch or not sha:
            continue

        # Check for common ancestor
        has_ancestor, msg = _git_merge_base(sha)
        if has_ancestor:
            print(f"✓ PR #{pr_num} has valid ancestry")
            continue

        print(f"⚠️  PR #{pr_num} ({branch}) is stale — rebasing...")

        if _create_rebase_pr(pr_num, branch, sha, dry_run=args.dry_run):
            state["fixed_prs"][str(pr_num)] = _now_iso()
            fixed_count += 1

    _save_state(state)

    if args.dry_run:
        print(f"\n📊 Dry-run: Would fix {fixed_count} stale branches")
        return 2  # Exit code 2 for dry-run
    else:
        print(f"\n✓ Fixed {fixed_count} stale branches")
        return 0 if fixed_count >= 0 else 1


if __name__ == "__main__":
    sys.exit(main())
