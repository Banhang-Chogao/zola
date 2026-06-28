#!/usr/bin/env bash
# Check whether the production deploy queue is busy.
# Safe behavior:
# - rate-limited / API error responses never crash the workflow
# - rate-limited responses defer auto-merge instead of being treated as code bugs
set -euo pipefail

REPO="${GITHUB_REPOSITORY:?GITHUB_REPOSITORY required}"
AUTH_TOKEN="${GITHUB_TOKEN:-${WORKFLOW_BOT_PAT:-${GH_TOKEN:-}}}"

if [ -z "$AUTH_TOKEN" ]; then
  echo "::error::deploy_check: missing GITHUB_TOKEN / WORKFLOW_BOT_PAT"
  exit 1
fi

export GH_TOKEN="$AUTH_TOKEN"

RATE_LIMITED=false
API_ERROR=false

write_output() {
  printf '%s\n' "$1" >> "$GITHUB_OUTPUT"
}

handle_rate_limit() {
  echo "⚠️ GitHub API rate limited; deferring deploy_check."
  write_output "deploy_busy=true"
  write_output "deploy_status=rate_limited"
  write_output "deploy_active=0"
  write_output "deploy_queued=0"
  exit 0
}

handle_api_error() {
  echo "⚠️ GitHub API response could not be trusted; deferring deploy_check."
  write_output "deploy_busy=true"
  write_output "deploy_status=unknown"
  write_output "deploy_active=0"
  write_output "deploy_queued=0"
  exit 0
}

count_runs() {
  local status="$1"
  local response body count

  response="$(gh api "repos/${REPO}/actions/workflows/deploy.yml/runs?status=${status}&per_page=3" --include 2>&1 || true)"
  response="$(printf '%s\n' "$response" | tr -d '\r')"

  if printf '%s\n' "$response" | grep -qiE 'API rate limit exceeded|rate limit exceeded'; then
    RATE_LIMITED=true
    echo "rate_limited"
    return 0
  fi

  body="$(printf '%s\n' "$response" | awk 'BEGIN{body=0} /^$/{body=1; next} body{print}')"
  if [ -z "$body" ] && printf '%s\n' "$response" | grep -q '^[[:space:]]*{'; then
    body="$response"
  fi

  count="$(
    printf '%s\n' "$body" |
      jq -r 'if (.workflow_runs? | type) == "array" then (.workflow_runs | length) else empty end' 2>/dev/null || true
  )"

  if [[ "$count" =~ ^[0-9]+$ ]]; then
    echo "$count"
  else
    API_ERROR=true
    echo "unknown"
  fi
}

echo "🔍 Checking if production deploy is active..."

ACTIVE="$(count_runs in_progress)"
if [ "$ACTIVE" = "rate_limited" ] || $RATE_LIMITED; then
  handle_rate_limit
fi
if [ "$ACTIVE" = "unknown" ] || $API_ERROR; then
  handle_api_error
fi

QUEUED="$(count_runs queued)"
if [ "$QUEUED" = "rate_limited" ] || $RATE_LIMITED; then
  handle_rate_limit
fi
if [ "$QUEUED" = "unknown" ] || $API_ERROR; then
  handle_api_error
fi

if ! [[ "$ACTIVE" =~ ^[0-9]+$ ]]; then
  ACTIVE=0
fi

if ! [[ "$QUEUED" =~ ^[0-9]+$ ]]; then
  QUEUED=0
fi

TOTAL=$(( ACTIVE + QUEUED ))

if [ "$TOTAL" -gt 0 ]; then
  echo "⏳ Production deploy is busy: ${ACTIVE} in_progress, ${QUEUED} queued"
  write_output "deploy_busy=true"
  write_output "deploy_status=busy"
else
  echo "✅ Production deploy queue is clear"
  write_output "deploy_busy=false"
  write_output "deploy_status=clear"
fi

write_output "deploy_active=${ACTIVE}"
write_output "deploy_queued=${QUEUED}"
