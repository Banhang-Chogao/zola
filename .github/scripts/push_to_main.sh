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
  # 💉 VACCINE: stash pop có thể CONFLICT khi cùng data/*.json bị main regenerate
  # (vd data/merge-report.json) — trước đây `set -e` → exit 1 → bot đỏ giả.
  # Bot vừa regenerate data ở local = bản MỚI muốn publish → giữ bản stash (bot)
  # cho file conflict, drop stash, tiếp tục. Không để conflict kéo sập workflow.
  if ! git stash pop; then
    CONFLICTS="$(git diff --name-only --diff-filter=U || true)"
    echo "::warning::push_to_main: stash pop conflict — giữ bản bot vừa regenerate cho: ${CONFLICTS}"
    for cf in $CONFLICTS; do
      git checkout --theirs -- "$cf" 2>/dev/null || git checkout stash@{0} -- "$cf" 2>/dev/null || true
      git add -- "$cf"
    done
    git stash drop 2>/dev/null || true
  fi
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

# 💉 VACCINE: concurrent-push race — nhiều bot (changelog / heartbeat / compliance /
# merge-report…) push `main` song song. `git push` chạy 1 lần sẽ bị
# "! [rejected] HEAD -> main (fetch first)" khi remote vừa nhích lên → trước đây
# workflow đỏ và commit vừa tạo bị MẤT HẲN (vd entry changelog PR #945 sinh ra rồi
# biến mất). Retry tối đa 3 lần: TRƯỚC MỖI push luôn `git pull --rebase` để replay
# commit của ta lên main mới nhất, rồi push. Backoff 2/4s giữa các lần. Hầu hết race
# chạm file KHÁC (data/*.json) nên rebase sạch; nếu rebase conflict (cùng file) →
# abort để vòng sau fetch lại.
PUSH_OK=false
for attempt in 1 2 3; do
  # pull --rebase trước mỗi push: kéo các commit bot khác vừa vào main rồi đặt
  # commit của ta lên trên → push fast-forward, tránh "fetch first" rejection.
  if ! git pull --rebase "$REMOTE_URL" main; then
    echo "::warning::push_to_main: rebase conflict (attempt ${attempt}/3) — abort, thử lại"
    git rebase --abort 2>/dev/null || true
  fi
  if git push "$REMOTE_URL" HEAD:main; then
    PUSH_OK=true
    break
  fi
  echo "::warning::push_to_main: push bị từ chối (attempt ${attempt}/3) — main vừa nhích, rebase + thử lại"
  if [ "$attempt" -lt 3 ]; then
    sleep $((2 ** attempt))
  fi
done

if [ "$PUSH_OK" != "true" ]; then
  echo "::error::push_to_main: push thất bại sau 3 lần retry (concurrent-push race chưa giải quyết)"
  exit 1
fi

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