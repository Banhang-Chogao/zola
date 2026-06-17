#!/usr/bin/env bash
# push_via_pr.sh — Commit lên feature branch + mở/cập nhật PR. KHÔNG BAO GIỜ push main.
#
# Usage:
#   push_via_pr.sh <branch> <commit_message> <file1> [file2...]
#
# Env (optional):
#   GH_TOKEN / GITHUB_TOKEN
#   PR_TITLE — tiêu đề PR (mặc định = commit message)
#   PR_BODY  — markdown body
#   FORCE_PUSH — "true" để force-push rolling branch (mặc định true)
set -euo pipefail

BRANCH="${1:?branch name required}"
COMMIT_MSG="${2:?commit message required}"
shift 2
FILES=("$@")

if [ ${#FILES[@]} -eq 0 ]; then
  echo "push_via_pr: no files — skip"
  exit 0
fi

git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"

HAS_CHANGE=false
for f in "${FILES[@]}"; do
  if [ -d "$f" ]; then
    if git status --porcelain -- "$f" | grep -q .; then
      HAS_CHANGE=true
      git add -A -- "$f"
    fi
  elif [ -e "$f" ] && git status --porcelain -- "$f" | grep -q .; then
    HAS_CHANGE=true
    git add -- "$f"
  fi
done

if [ "$HAS_CHANGE" = "false" ] || git diff --cached --quiet; then
  echo "push_via_pr: no staged changes — skip"
  exit 0
fi

git fetch origin main
git checkout -B "$BRANCH" origin/main
# Re-stage after checkout (working tree may differ)
for f in "${FILES[@]}"; do
  if [ -d "$f" ]; then
    git add -A -- "$f" 2>/dev/null || true
  elif [ -e "$f" ]; then
    git add -- "$f" 2>/dev/null || true
  fi
done
if git diff --cached --quiet; then
  echo "push_via_pr: nothing to commit after rebase onto main"
  exit 0
fi

git commit -m "$COMMIT_MSG"

# SAFETY: never push main
if [ "$BRANCH" = "main" ]; then
  echo "::error::Refusing to push branch named 'main'"
  exit 1
fi

if [ "${FORCE_PUSH:-true}" = "true" ]; then
  git push -f origin "$BRANCH"
else
  git push -u origin "$BRANCH"
fi

PR_TITLE="${PR_TITLE:-$COMMIT_MSG}"
PR_BODY="${PR_BODY:-**Automated update** — sẽ **auto-merge** vào \`main\` khi CI pass (QA Gatekeeper + PR Policy).

- Workflow: \`${GITHUB_WORKFLOW:-unknown}\`
- Branch: \`${BRANCH}\`
- Gắn label \`no-auto-merge\` nếu cần giữ PR chờ review tay}"

REPO="${GITHUB_REPOSITORY:?GITHUB_REPOSITORY required}"
existing=$(gh pr list --repo "$REPO" --head "$BRANCH" --base main --state open \
  --json number --jq '.[0].number' 2>/dev/null || true)

if [ -z "$existing" ] || [ "$existing" = "null" ]; then
  if ! gh pr create --repo "$REPO" --base main --head "$BRANCH" \
      --title "$PR_TITLE" --body "$PR_BODY"; then
    echo "⚠ Không tạo được PR — tạo tay: https://github.com/${REPO}/pull/new/${BRANCH}"
  fi
else
  echo "PR #${existing} đã mở — head cập nhật qua push"
  gh pr comment "$REPO" "$existing" --body "**Cập nhật** $(date -u +%FT%TZ): ${COMMIT_MSG}" || true
fi