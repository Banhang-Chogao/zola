#!/usr/bin/env bash
set -euo pipefail

echo "== Quickcheck =="
bash scripts/quickcheck.sh

echo "== Zola build =="
zola build --force

echo "== QA check =="
python3 qa_check.py

if [ -f scripts/check_internal_links.py ]; then
  echo "== Internal links =="
  python3 scripts/check_internal_links.py
else
  echo "INFO: scripts/check_internal_links.py not found, skipped"
fi

echo "PREFLIGHT PASS"
