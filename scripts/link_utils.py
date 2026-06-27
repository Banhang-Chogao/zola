#!/usr/bin/env python3
"""link_utils.py — safe, reusable link extraction & classification (VACCINE).

Why this exists
---------------
Several scripts in this repo each re-implemented link handling with subtly
different regexes. Two recurring, build-breaking defects kept showing up:

  1. HOST guard drops internal links.
     Code like ``if HOST not in url: continue`` (or ``return SITE_HOST in url``)
     was used to tell internal from external links. Root-absolute internal
     links — ``/zola/foo`` or ``/foo`` — do NOT contain the host string, so they
     were wrongly skipped → missing links → 404s after a migration.

  2. Code spans parsed as links.
     Running a link regex over the RAW markdown string also matches ``](/x)``
     inside fenced code blocks / inline ``code`` examples. The migration tool
     then rewrote those code examples, and counters over-counted links.

This module centralizes the correct behavior so every caller shares one
battle-tested implementation:

  * ``/zola/*`` and any ``/…`` / ``@/…`` / ``./…`` path is ALWAYS internal —
    classification never depends on the host string.
  * code spans (fenced + inline) are masked out before extraction, and callers
    that rewrite text can ask which byte ranges are code and leave them alone.
  * regexes tolerate markdown wrappers + trailing prose punctuation.

Stdlib only. Every public function is crash-safe: on malformed input it returns
an empty result rather than raising, so it can never take down a build.
"""
from __future__ import annotations

import re

__all__ = [
    "classify",
    "is_internal",
    "is_external",
    "validate",
    "clean_url",
    "code_span_ranges",
    "in_ranges",
    "mask_code_spans",
    "extract_urls",
    "extract_link_pairs",
    "extract_bare_urls",
    "process",
    "LINK_REGEX",
]

# Schemes / fragments that are never broken-link candidates.
_SKIP_PREFIXES = ("#", "mailto:", "tel:", "javascript:", "data:", "sms:")

# Trailing punctuation that commonly trails a URL written in prose. Note: ``)``,
# ``]`` and ``}`` are deliberately excluded — the extractor regexes already stop
# before them, and stripping them here would corrupt URLs that legitimately end
# in those characters.
_TRAIL = ".,;:!?'\">"
_LEAD = "\"'<"

# Bare-URL regex (punctuation safe). Captures absolute http(s) URLs and
# root-absolute internal ``/zola/…`` paths appearing as plain text (not already
# inside markdown link syntax). ``(?<![\w@/])`` avoids matching inside an email
# or a longer token.
LINK_REGEX = re.compile(
    r"""(?<![\w@/])(https?://[^\s)\]}<>"']+|/zola/[^\s)\]}<>"']+)"""
)

# Markdown link URL (NOT image — negative lookbehind for ``!``). Captures the URL
# up to the first space or closing paren; tolerates an optional ``<…>`` wrapper
# and a trailing ``"title"``.
_MD_URL_RE = re.compile(r"""(?<!!)\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+[^)]*)?\)""")
_MD_PAIR_RE = re.compile(
    r"""(?<!!)\[([^\]]*)\]\(\s*<?([^)\s>]+)>?(?:\s+[^)]*)?\)"""
)
# HTML anchors only (skip <link>, <area> etc. — we count navigable links).
_HTML_URL_RE = re.compile(
    r"""<a\b[^>]*?\bhref\s*=\s*["']([^"']+)["']""", re.IGNORECASE | re.DOTALL
)
_HTML_PAIR_RE = re.compile(
    r"""<a\b[^>]*?\bhref\s*=\s*["']([^"']+)["'][^>]*>(.*?)</a>""",
    re.IGNORECASE | re.DOTALL,
)

# Fenced code block: ``` or ~~~ (3+), shortest span to the same marker.
_FENCE_RE = re.compile(r"(`{3,}|~{3,})[\s\S]*?\1")
# Inline code: matching run of backticks.
_INLINE_RE = re.compile(r"(`+)(?:.+?)\1")


# --------------------------------------------------------------------------- #
# Classification — host is NEVER required for an internal link.
# --------------------------------------------------------------------------- #
def is_internal(url: str) -> bool:
    """True for internal links. ``/zola/*`` and any ``/…`` are ALWAYS internal."""
    u = (url or "").strip()
    if not u or u.startswith(_SKIP_PREFIXES):
        return False
    if u.startswith("//"):  # protocol-relative → external
        return False
    return u.startswith(("/", "@/", "./", "../"))


def is_external(url: str) -> bool:
    """True for absolute http(s) (and protocol-relative) links."""
    u = (url or "").strip()
    return u.startswith(("http://", "https://", "//"))


def classify(url: str) -> str:
    """Return ``"internal"`` | ``"external"`` | ``"skip"`` for a URL."""
    u = (url or "").strip()
    if not u or u.startswith(_SKIP_PREFIXES):
        return "skip"
    if is_internal(u):
        return "internal"
    if is_external(u):
        return "external"
    return "skip"


def validate(url: str) -> str:
    """Decision label matching the V9 patch contract.

    ``KEEP_INTERNAL`` (internal — always valid, never probe the network),
    ``VALIDATE_EXTERNAL`` (external — caller may probe), or ``SKIP``.
    """
    kind = classify(url)
    if kind == "internal":
        return "KEEP_INTERNAL"
    if kind == "external":
        return "VALIDATE_EXTERNAL"
    return "SKIP"


def clean_url(url: str) -> str:
    """Strip trailing prose punctuation / wrapping quotes from a captured URL."""
    u = (url or "").strip()
    if u.startswith("<") and u.endswith(">"):
        u = u[1:-1].strip()
    u = u.lstrip(_LEAD).rstrip(_TRAIL)
    return u.strip()


# --------------------------------------------------------------------------- #
# Code-span awareness — never parse/rewrite links inside code.
# --------------------------------------------------------------------------- #
def code_span_ranges(text: str) -> list[tuple[int, int]]:
    """Return sorted ``(start, end)`` byte ranges covering code spans.

    Covers fenced blocks (``` / ~~~) and inline ``code``. Ranges are in the
    coordinates of ``text`` so a ``re.sub`` callback can test ``m.start()``
    against them (``re.sub`` reports match offsets against the original string).
    """
    if not text:
        return []
    ranges: list[tuple[int, int]] = []
    try:
        for m in _FENCE_RE.finditer(text):
            ranges.append((m.start(), m.end()))
        for m in _INLINE_RE.finditer(text):
            s = m.start()
            if any(fs <= s < fe for fs, fe in ranges):
                continue  # inside a fenced block already
            ranges.append((s, m.end()))
    except Exception:
        return []
    ranges.sort()
    return ranges


def in_ranges(pos: int, ranges: list[tuple[int, int]]) -> bool:
    """True if ``pos`` falls inside any ``(start, end)`` range."""
    return any(s <= pos < e for s, e in ranges)


def mask_code_spans(text: str, fill: str = " ") -> str:
    """Blank out code spans (length-preserving) so link regexes skip them."""
    ranges = code_span_ranges(text)
    if not ranges:
        return text
    chars = list(text)
    for s, e in ranges:
        for i in range(s, min(e, len(chars))):
            if chars[i] != "\n":
                chars[i] = fill
    return "".join(chars)


# --------------------------------------------------------------------------- #
# Extraction (code-span aware)
# --------------------------------------------------------------------------- #
def extract_urls(text: str) -> list[str]:
    """All link URLs from markdown ``](url)`` + HTML ``<a href>`` (code-safe).

    Order preserved; duplicates kept (callers count occurrences). Image links
    (``![alt](…)``) are excluded.
    """
    if not text:
        return []
    masked = mask_code_spans(text)
    out: list[str] = []
    for m in _MD_URL_RE.finditer(masked):
        u = clean_url(m.group(1))
        if u:
            out.append(u)
    for m in _HTML_URL_RE.finditer(masked):
        u = clean_url(m.group(1))
        if u:
            out.append(u)
    return out


def extract_link_pairs(text: str) -> list[tuple[str, str]]:
    """``(anchor_text, url)`` pairs from markdown + HTML anchors (code-safe)."""
    if not text:
        return []
    masked = mask_code_spans(text)
    out: list[tuple[str, str]] = []
    for m in _MD_PAIR_RE.finditer(masked):
        u = clean_url(m.group(2))
        if u:
            out.append((m.group(1).strip(), u))
    for m in _HTML_PAIR_RE.finditer(masked):
        u = clean_url(m.group(1))
        if u:
            out.append((re.sub(r"<[^>]+>", "", m.group(2)).strip(), u))
    return out


def extract_bare_urls(text: str) -> list[str]:
    """Bare http(s) / ``/zola/…`` URLs sitting in plain prose (code-safe)."""
    if not text:
        return []
    masked = mask_code_spans(text)
    return [clean_url(m.group(1)) for m in LINK_REGEX.finditer(masked)]


def process(text: str) -> list[str]:
    """V9 reference pipeline: extract → clean → keep internal+external, drop skip.

    Internal ``/zola/*`` links are always kept (never require a host).
    """
    return [u for u in extract_urls(text) if validate(u) != "SKIP"]


if __name__ == "__main__":  # tiny smoke CLI
    import sys

    src = " ".join(sys.argv[1:]) or "[a](/zola/x) [b](https://e.com/y) `[c](/z)`"
    for u in extract_urls(src):
        print(f"{classify(u):8} {u}")
