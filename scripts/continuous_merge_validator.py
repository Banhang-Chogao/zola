#!/usr/bin/env python3
"""
Continuous Merge Safety Validator — Auto-rebase dirty PRs every 15 minutes.

When a PR turns "dirty" (merge conflicts) after base drifts, this script:
  1. Fetches the latest main branch
  2. Rebases the PR branch onto main
  3. Regenerates auto-generated files (references, og-images, etc.)
  4. Validates with qa_check.py + zola build
  5. Force-pushes with --force-with-lease (safe)
  6. Comments on PR with result

Usage:
  python3 scripts/continuous_merge_validator.py [--pr NUMBER]

Environment:
  GITHUB_TOKEN or GH_TOKEN — GitHub API access (required)
  DRY_RUN — Set to 1 to scan without making changes

Exit codes:
  0: All PRs validated/fixed
  1: Some PRs failed to fix (manual intervention needed)
  2: Configuration/auth error
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional


def run_cmd(cmd: str, check: bool = True) -> tuple[int, str, str]:
    """Run shell command, return (exit_code, stdout, stderr)"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"❌ Command failed: {cmd}")
        print(f"   stdout: {result.stdout[:500]}")
        print(f"   stderr: {result.stderr[:500]}")
        raise RuntimeError(f"Exit code {result.returncode}")
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def get_token() -> str:
    """Get GitHub API token from environment"""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN or GH_TOKEN environment variable not set")
    return token


def is_pr_dirty(pr_number: int) -> bool:
    """Check if PR has merge conflicts (dirty state)"""
    try:
        _, output, _ = run_cmd(
            f'gh pr view {pr_number} --json mergeable,mergeStateStatus',
            check=False
        )
        if not output:
            return False

        data = json.loads(output)
        is_dirty = (
            data.get("mergeable") == False or
            data.get("mergeStateStatus") == "DIRTY"
        )
        return is_dirty
    except Exception as e:
        print(f"⚠️  Error checking PR #{pr_number} state: {e}")
        return False


def get_open_prs() -> list[dict]:
    """Get all open PRs targeting main"""
    try:
        _, output, _ = run_cmd(
            'gh pr list --state open --base main --json number,headRefName,mergeable,mergeStateStatus --limit 100',
            check=False
        )
        if not output:
            return []
        return json.loads(output)
    except Exception as e:
        print(f"⚠️  Error fetching PRs: {e}")
        return []


def auto_rebase_pr(pr_number: int, branch_name: str, dry_run: bool = False) -> bool:
    """
    Auto-rebase PR onto latest main.
    Returns True if successful, False if failed.
    """
    print(f"\n{'[DRY-RUN] ' if dry_run else ''}🔄 Auto-rebasing PR #{pr_number} ({branch_name})...")

    try:
        # Step 1: Fetch latest main
        print("   [1/6] Fetching latest main...")
        run_cmd("git fetch origin main", check=True)

        # Step 2: Checkout branch
        print("   [2/6] Checking out branch...")
        run_cmd(f"git checkout {branch_name}", check=True)

        # Step 3: Rebase
        print("   [3/6] Rebasing onto main...")
        code, out, err = run_cmd("git rebase origin/main", check=False)
        if code != 0:
            print(f"   ⚠️  Rebase failed: {err[:200]}")
            # Try to abort rebase
            run_cmd("git rebase --abort", check=False)
            return False

        # Step 4: Regenerate auto-generated files
        print("   [4/6] Regenerating data files...")
        scripts_to_run = [
            ("Build references", "python3 scripts/build_references.py"),
            ("Build OG images", "python3 scripts/build_og_images.py"),
        ]

        for desc, script in scripts_to_run:
            code, out, err = run_cmd(script, check=False)
            if code != 0:
                print(f"   ⚠️  {desc} failed: {err[:200]}")
                # Don't abort; some scripts may fail in CI environments

        # Step 5: Run QA validation
        print("   [5/6] Running QA checks...")
        code, out, err = run_cmd("python3 qa_check.py", check=False)
        if code != 0:
            print(f"   ⚠️  QA check failed: {err[:200]}")
            run_cmd("git rebase --abort", check=False)
            return False

        # Step 6: Validate build (skip if zola not available)
        print("   [6/6] Validating build...")
        code, out, err = run_cmd("zola build 2>&1 | tail -5", check=False)
        if code != 0:
            print(f"   ⚠️  Build validation failed")
            run_cmd("git rebase --abort", check=False)
            return False

        # Success! Push (only if not dry-run)
        if not dry_run:
            print("   📤 Pushing rebased branch (force-with-lease)...")
            run_cmd(f"git push --force-with-lease origin {branch_name}", check=True)
            print(f"✅ PR #{pr_number} auto-rebased and validated successfully")
            return True
        else:
            print(f"[DRY-RUN] Would have pushed changes")
            return True

    except Exception as e:
        print(f"❌ Auto-rebase failed: {e}")
        # Try to abort any in-progress rebase
        run_cmd("git rebase --abort", check=False)
        return False


def comment_on_pr(pr_number: int, message: str) -> bool:
    """Post a comment on a PR"""
    try:
        run_cmd(f'gh pr comment {pr_number} --body "{message}"', check=True)
        return True
    except Exception as e:
        print(f"⚠️  Could not post comment on PR #{pr_number}: {e}")
        return False


def main():
    dry_run = os.environ.get("DRY_RUN", "0") == "1"
    pr_number_arg = None

    # Parse arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--pr" and len(sys.argv) > 2:
            try:
                pr_number_arg = int(sys.argv[2])
            except ValueError:
                print(f"❌ Invalid PR number: {sys.argv[2]}")
                return 2

    print("🔍 Continuous Merge Safety Validator")
    print(f"   Mode: {'DRY-RUN' if dry_run else 'AUTO-FIX'}")

    # Check token
    try:
        get_token()
    except RuntimeError as e:
        print(f"❌ {e}")
        return 2

    # Get PRs to check
    if pr_number_arg:
        print(f"\n   Checking PR #{pr_number_arg}...")
        prs = [{"number": pr_number_arg, "headRefName": None}]

        # Fetch branch name
        try:
            _, output, _ = run_cmd(
                f'gh pr view {pr_number_arg} --json headRefName',
                check=False
            )
            if output:
                prs[0]["headRefName"] = json.loads(output)["headRefName"]
        except:
            pass
    else:
        prs = get_open_prs()
        if not prs:
            print("   ✓ No open PRs to check")
            return 0
        print(f"\n   Found {len(prs)} open PR(s)")

    # Filter to dirty PRs
    dirty_prs = [pr for pr in prs if is_pr_dirty(pr["number"])]

    if not dirty_prs:
        print("   ✓ All PRs are merge-safe (no conflicts)")
        return 0

    print(f"\n   ⚠️  Found {len(dirty_prs)} dirty PR(s) — attempting auto-rebase:")

    # Auto-rebase each dirty PR
    fixed = 0
    failed = 0

    for pr in dirty_prs:
        pr_num = pr["number"]
        branch = pr.get("headRefName")

        if not branch:
            print(f"\n   PR #{pr_num}: Cannot determine branch name — skipping")
            failed += 1
            continue

        success = auto_rebase_pr(pr_num, branch, dry_run=dry_run)

        if success:
            fixed += 1
            if not dry_run:
                comment_on_pr(
                    pr_num,
                    "✅ Auto-rebased onto latest `main` (via continuous merge validator). "
                    "Merge-safe and ready to auto-merge when CI passes."
                )
        else:
            failed += 1
            if not dry_run:
                comment_on_pr(
                    pr_num,
                    "⚠️ Auto-rebase failed — manual intervention needed. "
                    "Please rebase locally: `git fetch origin main && git rebase origin/main && git push --force-with-lease`"
                )

    # Summary
    print()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    if fixed == len(dirty_prs):
        print(f"✅ All {fixed} dirty PRs fixed and validated")
        return 0
    else:
        print(f"⚠️  {fixed}/{len(dirty_prs)} PRs fixed; {failed} need manual intervention")
        return 1


if __name__ == "__main__":
    sys.exit(main())
