#!/usr/bin/env bash
set -euo pipefail

cd /workspaces/zola

echo "== Git status =="
git status -sb

echo
echo "== Recent main runs =="
gh run list --branch main --limit 10

echo
echo "== Open PRs =="
gh pr list --limit 20

echo
echo "== Blog Heart Beat =="
gh run list --workflow blog-heartbeat.yml --branch main --limit 5

echo
echo "== Deploy =="
gh run list --workflow deploy.yml --branch main --limit 5
