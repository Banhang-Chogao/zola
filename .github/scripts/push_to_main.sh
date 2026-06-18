#!/usr/bin/env bash
# push_to_main.sh — Commit và push thẳng lên main. Không branch, không PR.
#
# Usage:
#   push_to_main.sh <commit_message> <file1> [file2...]
#
# Env (optional):
#   WORKFLOW_BOT_PAT — PAT repo admin (khuyến nghị)
#   GH_TOKEN / GITHUB_TOKEN — fallback
#   SKIP_CHANGELOG_TAG — "false" để không thêm [skip changelog] (mặc định true cho bot)
set -euo pipefail

COMMIT_MSG="${1:?commit message required}"
shift
FILES=("$@")

if [ ${#FILES[@]} -eq 0 ]; then
  echo "push_to_main: no files — skip"
  exit 0
fi

REPO="${GITHUB_REPOSITORY:?GITHUB_REPOSITORY required}"
AUTH_TOKEN="${WORKFLOW_BOT_PAT:-${GH_TOKEN:-${GITHUB_TOKEN:-}}}"

if [ -z "$AUTH_TOKEN" ]; then
  echo "::error::push_to_main: missing WORKFLOW_BOT_PAT / GITHUB_TOKEN"
  exit 1
fi

export GH_TOKEN="$AUTH_TOKEN"

git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"

git fetch origin main
git checkout main

# Scripts often modify files before calling this helper; stash so pull --rebase succeeds.
STASHED=false
if ! git diff --quiet || ! git diff --cached --quiet; then
  git stash push -u -m "push_to_main: pre-pull"
  STASHED=true
fi

git pull --rebase origin main

if [ "$STASHED" = "true" ]; then
  git stash pop
fi

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
  echo "push_to_main: no staged changes — skip"
  exit 0
fi

if [ "${SKIP_CHANGELOG_TAG:-true}" = "true" ] && [[ "$COMMIT_MSG" != *"[skip changelog]"* ]]; then
  COMMIT_MSG="${COMMIT_MSG} [skip changelog]"
fi

git commit -m "$COMMIT_MSG"

REMOTE_URL="https://x-access-token:${AUTH_TOKEN}@github.com/${REPO}.git"
git push "$REMOTE_URL" HEAD:main

echo "✓ Pushed directly to main"

# KHÔNG còn tự dispatch deploy sau MỌI bot push — đây là nguồn chính của "cơn bão"
# deploy làm cạn GitHub API rate limit của installation (configure-pages đỏ).
#   - Data bot refresh (dashboard/trends/activity…): publish theo cron 6h trong
#     deploy.yml (không cần deploy tức thì).
#   - Nội dung (PR merge vào main): tự deploy qua push trigger của deploy.yml.
# Caller nào THỰC SỰ cần deploy ngay sau push → gọi với DISPATCH_DEPLOY=true.
if [ "${DISPATCH_DEPLOY:-false}" = "true" ] && [ -z "${WORKFLOW_BOT_PAT:-}" ]; then
  if command -v gh >/dev/null 2>&1 && gh workflow run deploy.yml --ref main; then
    echo "✓ Triggered deploy.yml (DISPATCH_DEPLOY=true)"
  else
    echo "::warning::push_to_main: không dispatch được deploy (kiểm tra gh / DISPATCH_DEPLOY)"
  fi
else
  echo "ℹ️ push_to_main: bỏ qua dispatch deploy — publish qua cron 6h hoặc content merge"
fi