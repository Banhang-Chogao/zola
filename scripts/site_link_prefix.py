"""Derive site runtime path prefix from config.toml base_url (stdlib only)."""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parent.parent
CONFIG = REPO / "config.toml"
LEGACY_GHP_PREFIX = "/zola"


def read_base_url(path: Path = CONFIG) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return "https://seomoney.org"
    m = re.search(r'^base_url\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
    return m.group(1) if m else "https://seomoney.org"


def runtime_prefix(base_url: str | None = None) -> str:
    """Root-absolute internal link prefix: '' (apex) or '/zola' (GitHub Pages subpath)."""
    path = urlparse(base_url or read_base_url()).path.rstrip("/")
    return path


def uses_legacy_zola_prefix() -> bool:
    return runtime_prefix() == LEGACY_GHP_PREFIX


def strip_stale_zola_path(path: str) -> str:
    """Drop legacy /zola segment when base_url no longer uses that subpath."""
    if uses_legacy_zola_prefix():
        return path
    if path in ("/zola", "/zola/"):
        return "/"
    if path.startswith("/zola/"):
        stripped = path[len(LEGACY_GHP_PREFIX) :]
        return stripped if stripped else "/"
    return path


def ensure_runtime_prefix(path: str) -> str:
    """Add runtime prefix to a root-absolute path (inverse of strip for GHP mode)."""
    prefix = runtime_prefix()
    if not path.startswith("/"):
        return path
    if prefix:
        if path.startswith(f"{prefix}/") or path == prefix:
            return path
        return f"{prefix}{path}"
    return strip_stale_zola_path(path)