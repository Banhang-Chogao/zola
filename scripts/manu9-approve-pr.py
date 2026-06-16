#!/usr/bin/env python3
"""
manu9 - Claude PR Approval Shortcut
Auto-approve pending PRs created by Claude in banhang-chogao/zola
"""

import os
import sys
import json
import subprocess
from typing import Optional, List


class PRApprover:
    """Handle PR approval via GitHub CLI or API."""

    REPO = "banhang-chogao/zola"
    CLAUDE_AUTHORS = ["claude", "claude-web", "claude-opus", "claude-sonnet"]

    def __init__(self, github_token: Optional[str] = None):
        """Initialize PR approver."""
        self.github_token = github_token or os.environ.get("GITHUB_TOKEN")
        if not self.github_token:
            print("❌ Error: GITHUB_TOKEN not set")
            sys.exit(1)

    def get_pending_prs(self) -> List[dict]:
        """Get pending PRs created by Claude."""
        print("🔍 Searching for pending PRs created by Claude...\n")

        # Build search query
        authors_query = " ".join(f"author:{a}" for a in self.CLAUDE_AUTHORS)
        query = f"repo:{self.REPO} is:pr is:open {authors_query}"

        # Use gh CLI if available
        try:
            result = subprocess.run(
                [
                    "gh",
                    "pr",
                    "list",
                    "--repo",
                    self.REPO,
                    "--json",
                    "number,title,author,state",
                    "--search",
                    authors_query,
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            prs = json.loads(result.stdout)
            return prs

        except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
            print("⚠️  gh CLI not available or error occurred")
            return []

    def approve_pr(self, pr_number: int) -> bool:
        """Approve a specific PR."""
        try:
            result = subprocess.run(
                [
                    "gh",
                    "pr",
                    "review",
                    str(pr_number),
                    "--repo",
                    self.REPO,
                    "--approve",
                    "--body",
                    "✅ Approved by manu9 shortcut",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            print(f"✅ PR #{pr_number} approved")
            return True

        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to approve PR #{pr_number}: {e.stderr}")
            return False

    def run(self, pr_number: Optional[int] = None, approve_all: bool = False):
        """Main execution."""
        prs = self.get_pending_prs()

        if not prs:
            print("✅ No pending PRs found from Claude")
            return

        print(f"📋 Found {len(prs)} pending PR(s):\n")
        for pr in prs:
            print(f"  #{pr['number']}: {pr['title']}")
            print(f"     Author: {pr['author']['login']}\n")

        if pr_number:
            # Approve specific PR
            self.approve_pr(pr_number)

        elif approve_all:
            # Approve all
            print("🚀 Approving all pending PRs...\n")
            for pr in prs:
                self.approve_pr(pr["number"])

        else:
            # Show interactive menu
            print("Options:")
            print("  --approve-all    Approve all pending PRs")
            print("  --approve N      Approve specific PR number N")
            print("  (no args)        Show this list")


def main():
    """Entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Claude PR Approval Shortcut")
    parser.add_argument("--approve-all", action="store_true", help="Approve all pending PRs")
    parser.add_argument(
        "--approve", type=int, metavar="N", help="Approve specific PR number"
    )

    args = parser.parse_args()

    approver = PRApprover()
    approver.run(pr_number=args.approve, approve_all=args.approve_all)


if __name__ == "__main__":
    main()
