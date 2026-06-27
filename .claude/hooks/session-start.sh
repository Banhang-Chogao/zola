#!/bin/bash
# SessionStart hook — install the Zola CLI for Claude Code on the web.
#
# The remote/web container is ephemeral and rebuilt each session, so the Zola
# static-site generator (required to build/check this blog) must be reinstalled
# on startup. Pins the same version CI uses (.github/workflows/{deploy,qa}.yml).
set -euo pipefail

# Only the remote (web) container needs this; local machines manage their own Zola.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

ZOLA_VERSION="0.22.1"
ZOLA_TARBALL="zola-v${ZOLA_VERSION}-x86_64-unknown-linux-gnu.tar.gz"
ZOLA_URL="https://github.com/getzola/zola/releases/download/v${ZOLA_VERSION}/${ZOLA_TARBALL}"
INSTALL_DIR="/usr/local/bin"

log() { echo "[session-start] $*" >&2; }

# Idempotent: skip when the pinned version is already on PATH (cached container).
if command -v zola >/dev/null 2>&1 && zola --version 2>/dev/null | grep -q "${ZOLA_VERSION}"; then
  log "zola ${ZOLA_VERSION} already installed: $(command -v zola)"
  exit 0
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

# Prefer the tarball committed at the repo root (offline, fast); fall back to download.
if [ -f "${PROJECT_DIR}/${ZOLA_TARBALL}" ]; then
  log "Installing zola ${ZOLA_VERSION} from committed tarball..."
  tar -xzf "${PROJECT_DIR}/${ZOLA_TARBALL}" -C "$TMP_DIR" zola
else
  log "Committed tarball not found; downloading zola ${ZOLA_VERSION} from GitHub releases..."
  curl -sSfL "$ZOLA_URL" -o "${TMP_DIR}/${ZOLA_TARBALL}"
  tar -xzf "${TMP_DIR}/${ZOLA_TARBALL}" -C "$TMP_DIR" zola
fi

# Install to PATH (sudo only if the target dir is not directly writable).
if [ -w "$INSTALL_DIR" ]; then
  install -m 0755 "${TMP_DIR}/zola" "${INSTALL_DIR}/zola"
else
  sudo install -m 0755 "${TMP_DIR}/zola" "${INSTALL_DIR}/zola"
fi

log "Installed: $(zola --version)"
