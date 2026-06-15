#!/usr/bin/env python3
"""
QA Gatekeeper — chạy trước commit local (pre-commit hook) và trên CI (GitHub Actions).

Kiểm tra:
  1. Conflict markers (<<<<<<<, =======, >>>>>>>) trong source files
  2. Hardcoded secrets (GitHub PAT, OpenAI key, AWS key, Slack token)
  3. SEO basic cho bài viết .md trong content/posting/:
     - Frontmatter có title + date hợp lệ
     - Body (sau strip markdown) >= 50 chars
     - Có ít nhất 1 tag hoặc category

Exit code:
  0 — pass (có thể vẫn có warning)
  1 — fail (>=1 error)

Usage:
  python3 qa_check.py                    # scan toàn repo
  python3 qa_check.py path/to/file ...   # scan files cụ thể

Stdlib only, không cần pip install gì.
"""

import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

# File extensions cần scan conflict + secrets
SOURCE_EXTS = {".js", ".html", ".scss", ".css", ".md", ".py", ".yml", ".yaml", ".toml", ".sh"}

# Thư mục skip toàn bộ (output build, vendor, etc.)
SKIP_DIRS = {".git", "public", "node_modules", "__pycache__", ".pytest_cache", "artifacts"}

# Regex secrets — high-confidence patterns. Mỗi pattern là (name, regex).
SECRET_PATTERNS = [
    ("GitHub PAT classic",      re.compile(r"ghp_[A-Za-z0-9]{36}")),
    ("GitHub PAT fine-grained", re.compile(r"github_pat_[A-Za-z0-9_]{82}")),
    ("OpenAI/Anthropic-style",  re.compile(r"sk-[A-Za-z0-9]{32,}")),
    ("AWS access key",          re.compile(r"AKIA[0-9A-Z]{16}")),
    ("Slack token",             re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("Private key block",       re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----")),
]

# Google API key (AIzaSy*) intentionally committed cho PageSpeed Insights API
# (rate-limited theo HTTP referer của domain) → skip pattern này.

CONFLICT_MARKERS = (
    re.compile(r"^<<<<<<<\s", re.MULTILINE),
    re.compile(r"^=======\s*$", re.MULTILINE),
    re.compile(r"^>>>>>>>\s", re.MULTILINE),
)

# ANSI colors — disable trên CI hoặc non-tty
USE_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
def _c(code, text):
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text
RED    = lambda s: _c("31", s)
YELLOW = lambda s: _c("33", s)
GREEN  = lambda s: _c("32", s)
BOLD   = lambda s: _c("1",  s)
DIM    = lambda s: _c("2",  s)


class Issue:
    __slots__ = ("level", "path", "line", "message")
    def __init__(self, level, path, line, message):
        self.level = level  # "error" | "warning"
        self.path = path
        self.line = line
        self.message = message

    def render(self):
        loc = f"{self.path}:{self.line}" if self.line else str(self.path)
        prefix = RED("✗") if self.level == "error" else YELLOW("⚠")
        return f"{prefix} {DIM(loc)}  {self.message}"


def iter_files(targets):
    """Yield Path objects cho mỗi file cần scan."""
    if targets:
        for t in targets:
            p = Path(t)
            if p.is_file():
                yield p
    else:
        for root, dirs, files in os.walk(REPO_ROOT):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for f in files:
                p = Path(root) / f
                if p.suffix.lower() in SOURCE_EXTS:
                    yield p


def check_conflicts(path, content):
    """Scan conflict markers. Return list[Issue]."""
    issues = []
    for pattern in CONFLICT_MARKERS:
        for m in pattern.finditer(content):
            line = content[:m.start()].count("\n") + 1
            issues.append(Issue("error", path, line,
                                f"Conflict marker còn sót: '{m.group().strip()}'"))
    return issues


def check_secrets(path, content):
    """Scan hardcoded secrets. Return list[Issue]."""
    # Skip chính file qa_check.py — chứa các regex pattern dễ false positive
    if path.name == "qa_check.py":
        return []
    issues = []
    for name, pattern in SECRET_PATTERNS:
        for m in pattern.finditer(content):
            line = content[:m.start()].count("\n") + 1
            # Mask hiển thị: chỉ show prefix + suffix
            matched = m.group()
            masked = matched[:6] + "..." + matched[-4:] if len(matched) > 14 else matched[:4] + "..."
            issues.append(Issue("error", path, line,
                                f"Possible {name}: {masked}"))
    return issues


# ============= SEO checks cho content/posting/*.md =============

FRONTMATTER_RE = re.compile(r"^\+\+\+\n(.*?)\n\+\+\+\n?(.*)$", re.DOTALL)
TOML_KV_RE = re.compile(r"^(\w+)\s*=\s*(.+)$", re.MULTILINE)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Strip markdown để đếm chars (sync với logic trong static/js/editor.js)
MD_STRIP_PATTERNS = [
    (re.compile(r"```[\s\S]*?```"),     ""),   # code blocks
    (re.compile(r"!\[[^\]]*\]\([^)]*\)"), ""), # images
    (re.compile(r"\[[^\]]*\]\([^)]*\)"),  ""), # links
    (re.compile(r"https?://\S+"),         ""), # raw URLs
    (re.compile(r"[#*_>`\-+|]"),          ""), # markdown markup
    (re.compile(r"\s+"),                  " "), # collapse whitespace
]
def strip_markdown(body):
    text = body
    for pat, rep in MD_STRIP_PATTERNS:
        text = pat.sub(rep, text)
    return text.strip()


def parse_frontmatter(content):
    """Trả về (fm_dict, body_str) hoặc (None, None) nếu không match."""
    m = FRONTMATTER_RE.match(content)
    if not m:
        return None, None
    fm_text, body = m.group(1), m.group(2)
    fm = {}
    section = "root"
    for line in fm_text.split("\n"):
        t = line.strip()
        if not t:
            continue
        if t == "[taxonomies]":
            section = "taxonomies"
            fm.setdefault("taxonomies", {})
            continue
        if t == "[extra]":
            section = "extra"
            fm.setdefault("extra", {})
            continue
        kv = TOML_KV_RE.match(t)
        if not kv:
            continue
        key, val = kv.group(1), kv.group(2).strip()
        # Lột quotes nếu string, parse array nếu []
        if val.startswith('"') and val.endswith('"'):
            val = val[1:-1]
        elif val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            val = [s.strip().strip('"\'') for s in inner.split(",") if s.strip()]
        elif val in ("true", "false"):
            val = (val == "true")
        target = fm if section == "root" else fm[section]
        target[key] = val
    return fm, body


def check_seo(path, content):
    """SEO basic checks cho .md trong content/posting/. Return list[Issue]."""
    # Skip _index.md (section index, không phải bài viết)
    if path.name.startswith("_"):
        return []
    if "content/posting" not in str(path).replace("\\", "/"):
        return []

    issues = []
    fm, body = parse_frontmatter(content)
    if fm is None:
        issues.append(Issue("error", path, 1,
                            "Frontmatter không hợp lệ (thiếu +++ ... +++)"))
        return issues

    # Title required
    title = fm.get("title", "")
    if not title or not str(title).strip():
        issues.append(Issue("error", path, 2, "SEO: thiếu 'title' trong frontmatter"))
    else:
        tlen = len(str(title))
        if tlen < 10:
            issues.append(Issue("warning", path, 2,
                                f"SEO: title quá ngắn ({tlen} chars, nên ≥10)"))
        elif tlen > 70:
            issues.append(Issue("warning", path, 2,
                                f"SEO: title quá dài ({tlen} chars, nên ≤70)"))

    # Date required + format
    date = fm.get("date", "")
    if not date:
        issues.append(Issue("error", path, 3, "SEO: thiếu 'date' trong frontmatter"))
    elif not DATE_RE.match(str(date)):
        issues.append(Issue("error", path, 3,
                            f"SEO: date '{date}' không đúng format YYYY-MM-DD"))

    # Body length sau strip markdown.
    # ERROR nếu body rỗng hoàn toàn (sẽ ảnh hưởng Zola summary extract).
    # WARNING nếu <50 chars (khuyến nghị, đồng bộ threshold editor.js).
    if body is None or not body.strip():
        issues.append(Issue("error", path, 1, "SEO: body rỗng — bài không có nội dung"))
    else:
        plain = strip_markdown(body)
        if len(plain) < 50:
            issues.append(Issue("warning", path, 1,
                                f"SEO: body chỉ {len(plain)} chars sau strip markdown "
                                f"(khuyến nghị ≥50 để có summary tốt cho SEO)"))

    # Có ít nhất 1 tag hoặc category
    tax = fm.get("taxonomies", {}) or {}
    cats = tax.get("categories", []) or []
    tags = tax.get("tags", []) or []
    if not cats and not tags:
        issues.append(Issue("warning", path, 1,
                            "SEO: bài viết không có category hoặc tag nào"))

    return issues


def main():
    targets = sys.argv[1:]
    all_issues = []
    scanned = 0

    for path in iter_files(targets):
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        scanned += 1
        try:
            rel = path.relative_to(REPO_ROOT) if path.is_absolute() else path
        except ValueError:
            # File ngoài REPO_ROOT (vd. test ad-hoc) — dùng absolute path
            rel = path
        all_issues.extend(check_conflicts(rel, content))
        all_issues.extend(check_secrets(rel, content))
        if path.suffix == ".md":
            all_issues.extend(check_seo(rel, content))

    print(f"{BOLD('[QA]')} Scanned {scanned} files\n")

    errors = [i for i in all_issues if i.level == "error"]
    warnings = [i for i in all_issues if i.level == "warning"]

    for issue in errors + warnings:
        print(issue.render())

    if all_issues:
        print()

    summary = f"Summary: {len(errors)} error(s), {len(warnings)} warning(s)"
    if errors:
        print(RED(BOLD(summary)))
        return 1
    if warnings:
        print(YELLOW(summary))
    else:
        print(GREEN(BOLD("✓ All QA checks passed")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
