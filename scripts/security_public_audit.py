#!/usr/bin/env python3
"""security_public_audit.py — Static-site public-surface security gate.

WHY THIS EXISTS
---------------
A static blog (Zola → GitHub Pages) serves **every published byte to anyone**.
There is no server to gate access. Hidden menu entries, client-side "auth",
and ``robots.txt`` are NOT access control — they only hint to polite crawlers.
The only real control on a static host is: *do not publish the secret/file.*

This gate treats the PUBLIC SURFACE as untrusted-by-default and FAILS the
build (exit 1) when that surface exposes private/internal material:

  * private/internal files by name      (CLAUDE.md, *.env, *.key, *.pem, …)
  * internal ops / operator docs        (cheat-sheets, runbooks, admin rules)
  * real secret VALUES                   (ghp_…, AKIA…, PRIVATE KEY blocks, …)
  * secret-looking assignments           (api_key = "…", password: "…", …)
  * local machine paths                  (/Users/<name>/, /home/<name>/, ~/…)

PUBLIC SURFACE  =  content/  +  static/  +  public/ (built)  +  sitemap.xml
                   +  config.toml menu links

CALIBRATION (important)
-----------------------
This blog is a real Vietnamese tech/SEO blog: articles legitimately *mention*
words like ``API_KEY`` / ``PASSWORD`` / ``TOKEN`` in prose and tutorials. So
keyword mentions are NEVER flagged. Only:
  - high-confidence secret *formats* (same regexes as ``qa_check.py``) — scanned
    everywhere, because a real token must never appear even inside a tutorial;
  - secret-looking *assignments* with a real value and local machine paths —
    scanned only in infrastructure files (static/ + built public/, not in
    ``content/*.md`` prose), where a real leak actually lands.

The gate is calibrated so the current ``main`` passes with zero errors; new
exposures fail it. Run standalone or via ``qa_check.py`` (QA Gatekeeper).
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------------- #
# Public surface definition
# --------------------------------------------------------------------------- #
# Directories whose contents are (or become) world-readable once deployed.
PUBLIC_SOURCE_DIRS = ("content", "static")
BUILT_OUTPUT_DIR = "public"

# Text file extensions we read for content/pattern scanning. Binary/image files
# are still name-checked but never decoded.
TEXT_EXTS = {
    ".md", ".markdown", ".html", ".htm", ".js", ".mjs", ".css", ".scss",
    ".json", ".txt", ".xml", ".svg", ".toml", ".yml", ".yaml", ".csv", ".map",
}

# Skip vendored / third-party trees inside the public surface: their contents
# are upstream code we don't author and would only add noise.
SKIP_DIR_NAMES = {".git", "node_modules", "__pycache__", ".pytest_cache", "vendor"}

# --------------------------------------------------------------------------- #
# Rule data
# --------------------------------------------------------------------------- #
# Exact private/internal basenames that must never be published (case-insensitive).
FORBIDDEN_BASENAMES = {
    "claude.md", "claude_private.md", "claude.md.save",
    "operation-guide.md", "operations-guide.md", "operations.md",
    "admin-rules.md", "admin_rules.md",
    "shortcut.md", "shortcuts.md",
    "manu9.md",
    ".env",
}

# Private/internal file extensions that must never be published.
FORBIDDEN_SUFFIXES = {
    ".env", ".key", ".pem", ".sqlite", ".sqlite3", ".db",
    ".bak", ".zip", ".kdbx", ".pfx", ".p12", ".keystore",
}

# Internal ops/operator documents have no place in the PUBLISHED asset dir
# (static/) or built output. Match by filename substring — these names never
# describe a legitimate public article asset. Restricted to static/+public/ so
# real article slugs in content/ (e.g. "keyboard-shortcuts") are never caught.
INTERNAL_DOC_SUBSTRINGS = (
    "cheat-sheet", "cheatsheet", "operation-guide", "operations-guide",
    "admin-rules", "admin-guide", "runbook", "ops-guide", "operator",
)

# dotenv variants: .env, .env.local, .env.production …
DOTENV_RE = re.compile(r"^\.env(\..+)?$", re.IGNORECASE)

# High-confidence secret VALUE formats — mirror of qa_check.py SECRET_PATTERNS
# so the security gate and the QA Gatekeeper agree on "what a real secret is".
# Scanned across the ENTIRE public surface (a real token must not appear even
# inside a tutorial code block).
SECRET_VALUE_PATTERNS = [
    ("GitHub PAT classic",      re.compile(r"ghp_[A-Za-z0-9]{36}")),
    ("GitHub PAT fine-grained", re.compile(r"github_pat_[A-Za-z0-9_]{82}")),
    ("OpenAI/Anthropic-style",  re.compile(r"sk-[A-Za-z0-9]{32,}")),
    ("AWS access key",          re.compile(r"AKIA[0-9A-Z]{16}")),
    ("Slack token",             re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("Google OAuth secret",     re.compile(r"GOCSPX-[A-Za-z0-9_-]{20,}")),
    ("Private key block",       re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----")),
]

# Secret-looking assignment: KEY = "value" / "key": "value". Scanned only in
# infra files (not content prose). The captured value is validated against the
# placeholder allowlist below to avoid flagging documented examples.
ASSIGNMENT_RE = re.compile(
    r"""(?ix)
    \b(
        api[_-]?key | secret(?:[_-]?key)? | access[_-]?token | auth[_-]?token |
        client[_-]?secret | private[_-]?key | refresh[_-]?token |
        webhook(?:[_-]?url)? | passwo?rd | passwd | pwd | token
    )\b
    \s* [:=] \s*
    ["']([^"']{6,})["']
    """,
)

# A captured assignment value is treated as a REAL secret only if it looks
# random/credential-like and is NOT an obvious placeholder/example.
PLACEHOLDER_TOKENS = (
    "xxx", "your", "my_", "example", "placeholder", "changeme", "change-me",
    "todo", "dummy", "sample", "test", "fake", "none", "null", "redacted",
    "<", "{", "$", "...", "***", "abc", "secret", "token", "password",
    "g-xxxx", "ca-pub-xxxx", "insert", "replace", "value", "here",
)

# Local machine paths leak the author's filesystem layout. The second path
# segment must look like a *personal* account dir; these generic/CI names are
# allowed (tutorials, CI runners, container defaults).
LOCAL_PATH_RE = re.compile(r"/(Users|home)/([A-Za-z0-9._-]+)/")
GENERIC_HOME_SEGMENTS = {
    "user", "users", "username", "runner", "root", "home", "you", "me",
    "name", "admin", "ubuntu", "ci", "github", "app", "vagrant", "node",
    "python", "www-data", "deploy", "container", "build", "work", "project",
    "demo", "test", "foo", "bar", "path", "to",
}
TILDE_PATH_RE = re.compile(r"~/[A-Za-z0-9._][A-Za-z0-9._/-]*")

# Infrastructure file types — real config/code where a leaked secret value, a
# secret-looking assignment, or a local machine path actually hides. Authored
# prose (markdown) and rendered HTML are deliberately EXCLUDED: a tech blog's
# tutorials legitimately show `~/.ssh`, `/home/user`, `password = "…"`. The
# looser heuristics therefore run ONLY on these types, and only under static/
# (the built public/ copies of them are identical, so we don't double-scan).
INFRA_EXTS = {".js", ".mjs", ".json", ".css", ".scss", ".txt", ".map",
              ".yml", ".yaml", ".csv", ".toml", ".ini", ".cfg", ".conf"}

# URL exposure (sitemap <loc> + menu links). HIGH precision: a published URL is
# an exposure only when its file segment is a forbidden type/name or a clear
# internal-doc file — NOT merely because a slug/tag contains a sensitive word
# (e.g. /tags/claude-md/ or /posting/javascript-operators/ are legitimate
# pages). Internal navigation to the private content store is also flagged.
URL_DOC_SUBSTRINGS = ("cheat-sheet", "cheatsheet")
URL_PRIVATE_PATHS = ("private_content",)


# --------------------------------------------------------------------------- #
# Finding model + small helpers
# --------------------------------------------------------------------------- #
class Finding:
    __slots__ = ("level", "path", "line", "rule", "message")

    def __init__(self, level, path, line, rule, message):
        self.level = level  # "error" | "warn"
        self.path = str(path)
        self.line = line
        self.rule = rule
        self.message = message

    def render(self, color=True):
        loc = f"{self.path}:{self.line}" if self.line else self.path
        mark = "✗" if self.level == "error" else "⚠"
        if color and sys.stdout.isatty() and os.environ.get("NO_COLOR") is None:
            c = "31" if self.level == "error" else "33"
            mark = f"\033[{c}m{mark}\033[0m"
            loc = f"\033[2m{loc}\033[0m"
        return f"{mark} [{self.rule}] {loc}  {self.message}"

    def as_dict(self):
        return {"level": self.level, "path": self.path, "line": self.line,
                "rule": self.rule, "message": self.message}


def _looks_like_real_secret(value: str) -> bool:
    """Heuristic: a credential-like value (mixed/random) vs a documented example."""
    v = value.strip()
    if len(v) < 8:
        return False
    low = v.lower()
    if any(tok in low for tok in PLACEHOLDER_TOKENS):
        return False
    if len(set(v)) <= 3:                       # "aaaaaaa", "--------"
        return False
    has_alpha = any(ch.isalpha() for ch in v)
    has_digit = any(ch.isdigit() for ch in v)
    # Require entropy-ish: letters+digits, OR clearly long opaque blob.
    return (has_alpha and has_digit) or (len(v) >= 24 and has_alpha)


def _line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


# --------------------------------------------------------------------------- #
# File iteration
# --------------------------------------------------------------------------- #
def iter_public_files(repo_root: Path, include_public: bool):
    """Yield (abspath, rel_posix) for every file on the public surface."""
    dirs = list(PUBLIC_SOURCE_DIRS)
    if include_public:
        dirs.append(BUILT_OUTPUT_DIR)
    for top in dirs:
        base = repo_root / top
        if not base.exists():
            continue
        for root, subdirs, files in os.walk(base):
            subdirs[:] = [d for d in subdirs if d not in SKIP_DIR_NAMES]
            for fn in files:
                ap = Path(root) / fn
                try:
                    rel = ap.relative_to(repo_root).as_posix()
                except ValueError:
                    rel = ap.as_posix()
                yield ap, rel


# --------------------------------------------------------------------------- #
# Individual checks
# --------------------------------------------------------------------------- #
def check_forbidden_name(rel: str) -> list[Finding]:
    name = rel.rsplit("/", 1)[-1]
    low = name.lower()
    suffix = ("." + low.rsplit(".", 1)[-1]) if "." in low else ""
    out = []
    if low in FORBIDDEN_BASENAMES or DOTENV_RE.match(low):
        out.append(Finding("error", rel, 0, "forbidden-file",
                            f"private/internal file published on public surface: {name}"))
    elif suffix in FORBIDDEN_SUFFIXES:
        out.append(Finding("error", rel, 0, "forbidden-ext",
                            f"private/internal file type '{suffix}' must not be published: {name}"))
    return out


def check_internal_doc(rel: str) -> list[Finding]:
    """Internal ops/operator docs dropped into static/ or built public/."""
    r = rel.replace("\\", "/")
    surface = r.split("/", 1)[0]
    if surface not in ("static", BUILT_OUTPUT_DIR):
        return []
    low = r.rsplit("/", 1)[-1].lower()
    for sub in INTERNAL_DOC_SUBSTRINGS:
        if sub in low:
            return [Finding("error", rel, 0, "internal-doc",
                            "internal ops/operator document exposed on public surface "
                            f"(matches '{sub}'); move it under ops/ or _private/")]
    return []


def check_secret_values(rel: str, text: str) -> list[Finding]:
    out = []
    for name, pat in SECRET_VALUE_PATTERNS:
        for m in pat.finditer(text):
            raw = m.group()
            masked = raw[:6] + "…" + raw[-4:] if len(raw) > 14 else raw[:4] + "…"
            out.append(Finding("error", rel, _line_of(text, m.start()),
                               "secret-value", f"possible {name} in public file: {masked}"))
    return out


def check_assignment_secrets(rel: str, text: str) -> list[Finding]:
    out = []
    for m in ASSIGNMENT_RE.finditer(text):
        key, value = m.group(1), m.group(2)
        if _looks_like_real_secret(value):
            masked = value[:4] + "…" + value[-2:] if len(value) > 10 else value[:2] + "…"
            out.append(Finding("error", rel, _line_of(text, m.start()),
                               "secret-assign",
                               f"secret-looking assignment {key}=\"{masked}\" in public file"))
    return out


def check_local_paths(rel: str, text: str) -> list[Finding]:
    out = []
    for m in LOCAL_PATH_RE.finditer(text):
        seg = m.group(2).lower()
        if seg in GENERIC_HOME_SEGMENTS:
            continue
        out.append(Finding("error", rel, _line_of(text, m.start()),
                           "local-path",
                           f"local machine path leaked in public file: {m.group()}"))
    for m in TILDE_PATH_RE.finditer(text):
        out.append(Finding("warn", rel, _line_of(text, m.start()),
                           "home-path",
                           f"home-relative path in public file: {m.group()[:40]}"))
    return out


def _url_exposes_private(url: str) -> str | None:
    """Return a reason string if a published URL exposes a private/internal
    resource, else None. Decides on the URL's *file segment* (last path part)
    so legitimate slugs/tags that merely contain a sensitive word pass."""
    low = url.lower()
    for p in URL_PRIVATE_PATHS:
        if p in low:
            return f"links into private store '{p}'"
    seg = low.split("?", 1)[0].split("#", 1)[0].rstrip("/").rsplit("/", 1)[-1]
    suffix = ("." + seg.rsplit(".", 1)[-1]) if "." in seg else ""
    if seg in FORBIDDEN_BASENAMES or DOTENV_RE.match(seg):
        return f"private file '{seg}'"
    if suffix in FORBIDDEN_SUFFIXES:
        return f"forbidden file type '{suffix}'"
    for sub in URL_DOC_SUBSTRINGS:
        if sub in seg:
            return f"internal document (matches '{sub}')"
    return None


def check_sitemap(repo_root: Path) -> list[Finding]:
    sm = repo_root / BUILT_OUTPUT_DIR / "sitemap.xml"
    if not sm.exists():
        return []
    try:
        text = sm.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    out = []
    for m in re.finditer(r"<loc>\s*(.*?)\s*</loc>", text):
        reason = _url_exposes_private(m.group(1))
        if reason:
            out.append(Finding("error", "public/sitemap.xml", _line_of(text, m.start()),
                               "sitemap-link", f"sitemap exposes {reason}: {m.group(1)}"))
    return out


def check_menu_links(repo_root: Path) -> list[Finding]:
    cfg = repo_root / "config.toml"
    if not cfg.exists():
        return []
    try:
        raw = cfg.read_text(encoding="utf-8")
    except OSError:
        return []
    menu = []
    try:
        import tomllib
        menu = tomllib.loads(raw).get("extra", {}).get("menu", []) or []
    except Exception:
        # Fallback: regex the url = "…" entries near a menu block.
        m = re.search(r"menu\s*=\s*\[(.*?)\]", raw, re.DOTALL)
        if m:
            menu = [{"url": u} for u in re.findall(r'url\s*=\s*"([^"]+)"', m.group(1))]
    out = []
    for item in menu:
        reason = _url_exposes_private(item.get("url") or "")
        if reason:
            out.append(Finding("error", "config.toml", 0, "menu-link",
                               f"public menu {reason}: {item.get('url')}"))
    return out


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def audit_public_surface(repo_root: Path = REPO_ROOT, include_public: bool = True) -> list[Finding]:
    findings: list[Finding] = []
    for ap, rel in iter_public_files(repo_root, include_public):
        findings.extend(check_forbidden_name(rel))
        findings.extend(check_internal_doc(rel))

        suffix = ap.suffix.lower()
        if suffix not in TEXT_EXTS:
            continue
        try:
            text = ap.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        # Real secret VALUE formats: scanned on every text file (a real token
        # must not appear even inside a rendered page or a tutorial code block).
        findings.extend(check_secret_values(rel, text))
        # Looser heuristics (secret-looking assignments, local machine paths)
        # would false-positive on authored prose / rendered tutorial HTML, so
        # they run ONLY on static/ infrastructure files (real config/code).
        if rel.startswith("static/") and suffix in INFRA_EXTS:
            findings.extend(check_assignment_secrets(rel, text))
            findings.extend(check_local_paths(rel, text))

    findings.extend(check_menu_links(repo_root))
    if include_public:
        findings.extend(check_sitemap(repo_root))
    return findings


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Static-site public-surface security gate "
                    "(content/ + static/ + public/ + sitemap + menu).",
        epilog="Exit 0 = clean (warnings allowed); 1 = ≥1 error → blocks build.",
    )
    ap.add_argument("--no-public", action="store_true",
                    help="Skip the built public/ tree + sitemap (source-only scan).")
    ap.add_argument("--json", action="store_true", help="Emit findings as JSON.")
    args = ap.parse_args(argv)

    include_public = not args.no_public and (REPO_ROOT / BUILT_OUTPUT_DIR).exists()
    findings = audit_public_surface(REPO_ROOT, include_public=include_public)
    errors = [f for f in findings if f.level == "error"]
    warns = [f for f in findings if f.level == "warn"]

    if args.json:
        import json
        print(json.dumps({"errors": len(errors), "warnings": len(warns),
                          "findings": [f.as_dict() for f in findings]}, indent=2))
    else:
        print("Security Public Audit")
        print(f"- Surface scanned: content/ static/"
              f"{' public/ sitemap.xml' if include_public else ''} + menu links")
        for f in errors + warns:
            print(f.render())
        print()
        if errors:
            print(f"✗ FAIL — {len(errors)} exposure(s), {len(warns)} warning(s). "
                  "Do not publish secrets/private docs on a static site. "
                  "See docs/security-static-blog.md")
        elif warns:
            print(f"✓ PASS (with {len(warns)} warning(s)) — no public exposure of "
                  "private/internal material.")
        else:
            print("✓ PASS — no public exposure of private/internal material.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
