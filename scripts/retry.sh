#!/bin/bash
# Retry helper: runs a command with retry + exponential backoff.
# Usage: ./scripts/retry.sh [-n N] [-d DELAY] <command>
#   -n N     max attempts (default: 3)
#   -d DELAY initial delay in seconds (default: 5, doubled each retry)

set -euo pipefail

MAX_ATTEMPTS=3
DELAY=5

while getopts "n:d:h" opt; do
  case $opt in
    n) MAX_ATTEMPTS="$OPTARG" ;;
    d) DELAY="$OPTARG" ;;
    h) echo "Usage: $0 [-n attempts] [-d delay] <command>"; exit 0 ;;
    *) echo "Invalid option"; exit 1 ;;
  esac
done
shift $((OPTIND-1))

[ $# -eq 0 ] && { echo "Error: no command specified"; exit 1; }

ATTEMPT=1
while [ $ATTEMPT -le "$MAX_ATTEMPTS" ]; do
  echo "🔄 Attempt $ATTEMPT/$MAX_ATTEMPTS: $*"
  if eval "$@"; then
    echo "✅ Command succeeded (attempt $ATTEMPT)"
    exit 0
  fi
  if [ $ATTEMPT -lt "$MAX_ATTEMPTS" ]; then
    echo "⚠️ Attempt $ATTEMPT failed, retrying in ${DELAY}s..."
    sleep "$DELAY"
    DELAY=$((DELAY * 2))
  fi
  ATTEMPT=$((ATTEMPT + 1))
done

echo "❌ Command failed after $MAX_ATTEMPTS attempts"
exit 1
