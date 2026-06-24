#!/usr/bin/env bash
set -euo pipefail

echo "== Git whitespace check =="
git diff --check

echo "== Conflict marker scan =="
if git grep -n -E '^(<<<<<<<|=======|>>>>>>>)' -- . \
  ':!public' ':!public_test' ':!node_modules'
then
  echo "ERROR: conflict markers found"
  exit 1
fi

echo "QUICKCHECK PASS"
