#!/usr/bin/env bash
# resolve_open_bot_pr.sh [commit_sha]
# Resolve open bot maintenance PR head ref/sha for workflow_run relay.
# Outputs: head_ref, head_sha, actor, title, body, base_sha, skip
set -euo pipefail

SHA="${1:-}"
REPO="${GITHUB_REPOSITORY:?}"
OUT="${GITHUB_OUTPUT:-/dev/stdout}"

write_pr_outputs() {
  local pr="$1"
  {
    echo "skip=false"
    echo "head_ref=$(echo "$pr" | jq -r '.head.ref // .headRefName')"
    echo "head_sha=$(echo "$pr" | jq -r '.head.sha // .headRefOid')"
    echo "actor=$(echo "$pr" | jq -r '.author.login // .user.login // empty')"
    echo "title<<EOF"
    echo "$pr" | jq -r '.title'
    echo "EOF"
    echo "body<<EOF"
    echo "$pr" | jq -r '.body // ""'
    echo "EOF"
    echo "base_sha=$(echo "$pr" | jq -r '.base.sha // .baseRefOid')"
  } >> "$OUT"
}

if [ -n "$SHA" ]; then
  pr=$(gh api "repos/${REPO}/commits/${SHA}/pulls" --jq '.[0]' 2>/dev/null || echo "null")
  if [ -n "$pr" ] && [ "$pr" != "null" ]; then
    write_pr_outputs "$pr"
    exit 0
  fi
fi

pr=$(gh pr list --repo "$REPO" --state open --base main \
  --json headRefName,headRefOid,updatedAt,author,title,body,baseRefOid \
  --jq '[.[] | select(.headRefName | test("^(chore|qa|autofix|content)/")) | select((.author.login // .user.login) == "github-actions[bot]")] | sort_by(.updatedAt) | last')

if [ -z "$pr" ] || [ "$pr" = "null" ]; then
  echo "skip=true" >> "$OUT"
  echo "resolve_open_bot_pr: no maintenance PR found"
  exit 0
fi

write_pr_outputs "$pr"