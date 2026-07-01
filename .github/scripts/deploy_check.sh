#!/usr/bin/env bash
set -euo pipefail

# deploy_check.sh — Check if production deploy is already in progress.
# Used by auto-merge.yml to avoid piling up merges that each trigger deploy.
#
# Outputs: deploy_busy=true/false via GITHUB_OUTPUT

DEPLOY_BUSY=false

IN_PROGRESS=$(gh run list \
  --workflow=deploy.yml \
  --branch=main \
  --limit=5 \
  --json status,conclusion \
  --jq '[.[] | select(.conclusion == null and (.status == "in_progress" or .status == "queued" or .status == "pending" or .status == "waiting"))] | length' 2>/dev/null || echo 0)

if [[ "$IN_PROGRESS" -gt 0 ]]; then
  DEPLOY_BUSY=true
  echo "⏳ Found $IN_PROGRESS deploy(s) in progress."
fi

echo "deploy_busy=$DEPLOY_BUSY" >> "$GITHUB_OUTPUT"
