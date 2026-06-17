#!/usr/bin/env bash
# trigger_bot_pr_ci.sh — Dispatch QA Gatekeeper on bot maintenance branch.
#
# Root cause: PRs opened via GITHUB_TOKEN do not trigger pull_request workflows.
# workflow_run relay also fails when source workflow runs on main (schedule/push).
# This script dispatches workflow_dispatch on the feature branch after push_via_pr.
#
# Usage: trigger_bot_pr_ci.sh <branch>
set -euo pipefail

BRANCH="${1:?branch name required}"
REPO="${GITHUB_REPOSITORY:?GITHUB_REPOSITORY required}"
AUTH_TOKEN="${WORKFLOW_BOT_PAT:-${GH_TOKEN:-${GITHUB_TOKEN:-}}}"

if [ -z "$AUTH_TOKEN" ]; then
  echo "::error::trigger_bot_pr_ci: missing token"
  exit 1
fi

export GH_TOKEN="$AUTH_TOKEN"

if [ -n "${WORKFLOW_BOT_PAT:-}" ]; then
  echo "trigger_bot_pr_ci: WORKFLOW_BOT_PAT set — pull_request CI runs natively; skip dispatch"
  exit 0
fi

echo "trigger_bot_pr_ci: waiting for PR head on ${BRANCH}…"
sleep 4

dispatch() {
  local wf_name="$1"
  if gh workflow run "$wf_name" --repo "$REPO" --ref "$BRANCH"; then
    echo "trigger_bot_pr_ci: dispatched ${wf_name} on ${BRANCH}"
  else
    echo "::warning::trigger_bot_pr_ci: failed to dispatch ${wf_name}"
    return 1
  fi
}

dispatch "QA Gatekeeper" || true
# Auto Merge chạy qua workflow_run sau QA — dispatch backup nếu relay chậm
dispatch "Auto Merge PRs" || true