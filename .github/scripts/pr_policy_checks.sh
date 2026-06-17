#!/usr/bin/env bash
# pr_policy_checks.sh — PR Policy checks (pull_request + workflow_run relay).
# Env: ACTOR, PR_TITLE, PR_BODY, BASE_SHA, HEAD_SHA, HEAD_REF
set -euo pipefail

MIN_TITLE_LEN="${MIN_TITLE_LEN:-12}"
MIN_BODY_LEN="${MIN_BODY_LEN:-30}"

if [ "${HEAD_REF:-}" = "main" ]; then
  echo "::error::PR must originate from a feature branch, not main."
  exit 1
fi

case "${ACTOR:-}" in
  dependabot[bot]|renovate[bot]|github-advanced-security[bot])
    echo "::error::Bot PRs are forbidden: $ACTOR"
    exit 1
    ;;
esac

# Allow trusted internal bot; block other *-bot patterns (snyk, etc.)
case "${ACTOR:-}" in
  github-actions[bot]) ;;
  snyk-*|*-bot)
    echo "::error::Security/auto-update bot PRs are forbidden: $ACTOR"
    exit 1
    ;;
esac

if [ ${#PR_TITLE} -lt "${MIN_TITLE_LEN}" ]; then
  echo "::error::PR title must describe the functional change."
  exit 1
fi

body_compact=$(printf '%s' "$PR_BODY" | tr -d '[:space:]')
if [ ${#body_compact} -lt "${MIN_BODY_LEN}" ]; then
  echo "::error::PR body must include a clear functional description."
  exit 1
fi

if [ -z "${BASE_SHA:-}" ] || [ -z "${HEAD_SHA:-}" ]; then
  echo "::error::Missing base/head SHA for diff policy check."
  exit 1
fi

forbidden='.github/dependabot.yml .github/dependabot.yaml renovate.json renovate.json5 .renovaterc .renovaterc.json'
changed=$(git diff --name-only "$BASE_SHA" "$HEAD_SHA")
for path in $forbidden; do
  if echo "$changed" | grep -qx "$path"; then
    echo "::error::Forbidden auto-update config: $path"
    exit 1
  fi
done
if echo "$changed" | grep -Eqi 'dependabot|renovate'; then
  echo "::error::Forbidden dependabot/renovate auto-update config."
  exit 1
fi
for path in $changed; do
  case "$path" in
    .github/workflows/auto-merge.yml|.github/workflows/merge-report.yml|scripts/try_auto_merge.py|scripts/auto_merge_policy.py|scripts/fetch_merge_report.py|data/auto-merge-policy.json|data/auto-merge-loop-state.json)
      continue
      ;;
  esac
  if echo "$path" | grep -Eqi 'auto-merge'; then
    echo "::error::Forbidden auto-merge workflow (not whitelisted): $path"
    exit 1
  fi
done

echo "PR Policy checks passed (actor=$ACTOR, head=${HEAD_REF:-unknown})"