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


class Fix:
    """Mechanical fix có thể apply lên content. apply_fn idempotent."""
    __slots__ = ("path", "description", "apply_fn")
    def __init__(self, path, description, apply_fn):
        self.path = path
        self.description = description
        self.apply_fn = apply_fn  # (content: str) -> str


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


# ============= SCSS/CSS Syntax Check =============
# Lightweight bracket/parens balance + empty-rule detection. KHÔNG full
# SCSS parser — chỉ catch lỗi mechanical phổ biến:
#   1. Unbalanced { vs } → bug PR #57 (block .editor-btn--success không có
#      body, mất `}`) → deploy fail
#   2. Unbalanced ( vs ) trong values (mismatched gradient/calc/var)
#   3. Empty rule body: 'selector { }' với KHÔNG declarations và KHÔNG
#      nested rules → có thể là edit hỏng nửa chừng
#
# Strip block comments /* ... */ + line comments // ... + string literals
# trước khi count để tránh false positive với { } trong content/url().

_SCSS_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_SCSS_LINE_COMMENT_RE  = re.compile(r"//[^\n]*")
_SCSS_STRING_RE        = re.compile(r'"(?:[^"\\]|\\.)*"' r"|'(?:[^'\\]|\\.)*'")


def _scss_strip_noise(content: str) -> str:
    """Remove comments + string literals → giữ structural tokens cho count."""
    content = _SCSS_BLOCK_COMMENT_RE.sub("", content)
    content = _SCSS_LINE_COMMENT_RE.sub("", content)
    content = _SCSS_STRING_RE.sub('""', content)
    return content


def check_scss_syntax(path, content):
    """
    Catch SCSS syntax errors trước khi Zola/Sass parser fail.
    Tập trung trên lỗi mechanical: thiếu '}', thiếu ')', empty rule body.
    """
    if path.suffix not in {".scss", ".css"}:
        return []
    issues = []
    stripped = _scss_strip_noise(content)

    # 1. Balance { vs }
    open_braces  = stripped.count("{")
    close_braces = stripped.count("}")
    if open_braces != close_braces:
        # Locate first unmatched: simple stack scan trên stripped
        depth = 0
        last_open_line = 0
        for i, ch in enumerate(stripped):
            if ch == "{":
                depth += 1
                last_open_line = stripped[:i].count("\n") + 1
            elif ch == "}":
                depth -= 1
                if depth < 0:
                    line = stripped[:i].count("\n") + 1
                    issues.append(Issue("error", path, line,
                        f"SCSS thừa '}}' close brace (depth âm). Có thể thiếu '{{' phía trên."))
                    depth = 0  # reset, tiếp tục scan
        if depth > 0:
            issues.append(Issue("error", path, last_open_line,
                f"SCSS thiếu '}}' (còn {depth} block chưa đóng — bắt đầu từ dòng {last_open_line})."))

    # 2. Balance ( vs ) — quan trọng cho gradient/calc/var values
    open_parens  = stripped.count("(")
    close_parens = stripped.count(")")
    if open_parens != close_parens:
        diff = abs(open_parens - close_parens)
        token = "(" if open_parens > close_parens else ")"
        issues.append(Issue("error", path, 1,
            f"SCSS unbalanced parens: thừa {diff} ký tự '{token}'."))

    # 3. Empty rule body — selector { } (chỉ whitespace bên trong) trong
    # original content (CHƯA strip comment). Có comment bên trong =
    # placeholder intentional, skip.
    empty_rule_re = re.compile(r"([^{};]+?)\{(\s*)\}")
    for m in empty_rule_re.finditer(content):
        sel = m.group(1).strip()
        inner = m.group(2)
        if not sel or len(sel) > 200:
            continue
        if sel.startswith(("@", "%", "0", "1", "/*", "//")):
            continue
        # Inner có comment / chỉ whitespace + comment → intentional placeholder
        if "/*" in inner or "//" in inner:
            continue
        # Inner whitespace only → flag warning (có thể edit hỏng nửa chừng)
        # Nhưng nếu match cùng line với inline comment ở dòng đó → skip
        line_start = content.rfind("\n", 0, m.start()) + 1
        line_end   = content.find("\n", m.end())
        line_text  = content[line_start: line_end if line_end >= 0 else len(content)]
        if "/*" in line_text:
            continue
        line = content[:m.start()].count("\n") + 1
        issues.append(Issue("warning", path, line,
            f"SCSS rule rỗng '{sel[:60]}{{...}}' — có thể edit hỏng nửa chừng?"))

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


# ============= SAFE FIXERS (mechanical only — không đoán nội dung) =============
# Mỗi fixer: nhận str content, return str content mới. IDEMPOTENT: chạy 2 lần
# trên cùng input → cùng output. An toàn khi chain với fix khác.

TAGS_LINE_RE = re.compile(r"^(tags\s*=\s*)\[(.*?)\]\s*$", re.MULTILINE)
CATEGORIES_LINE_RE = re.compile(r"^(categories\s*=\s*)\[(.*?)\]\s*$", re.MULTILINE)
ALIASES_LINE_RE = re.compile(r"^aliases\s*=", re.MULTILINE)
DATE_SLASH_RE = re.compile(r"^(date\s*=\s*)(\d{4})/(\d{2})/(\d{2})\s*$", re.MULTILINE)


def _normalize_taxonomy_array(items_text):
    """Parse '"Zola", "Web"' → ['zola', 'web'] lowercase + dedupe + sort."""
    items = [s.strip().strip('"\'') for s in items_text.split(",") if s.strip()]
    return sorted({t.lower().strip() for t in items if t.strip()})


def fix_normalize_tags(content):
    """Tags: lowercase + dedupe + sort. Skip nếu đã chuẩn."""
    def replacer(m):
        normalized = _normalize_taxonomy_array(m.group(2))
        return f'{m.group(1)}[{", ".join(f"{chr(34)}{t}{chr(34)}" for t in normalized)}]'
    return TAGS_LINE_RE.sub(replacer, content)


def fix_normalize_categories(content):
    """Categories: lowercase first char? Không — categories có thể là tên riêng
    (vd. 'Posting' là proper noun). Chỉ trim + dedupe, KHÔNG lowercase."""
    def replacer(m):
        items = [s.strip().strip('"\'') for s in m.group(2).split(",") if s.strip()]
        deduped = list(dict.fromkeys(items))  # preserve order, dedupe
        return f'{m.group(1)}[{", ".join(f"{chr(34)}{c}{chr(34)}" for c in deduped)}]'
    return CATEGORIES_LINE_RE.sub(replacer, content)


def fix_date_slash_to_dash(content):
    """date = 2026/06/14 → 2026-06-14."""
    return DATE_SLASH_RE.sub(r"\1\2-\3-\4", content)


def fix_trim_frontmatter_trailing(content):
    """Strip trailing whitespace trên mỗi dòng frontmatter."""
    m = FRONTMATTER_RE.match(content)
    if not m:
        return content
    fm_lines = [line.rstrip() for line in m.group(1).split("\n")]
    return f"+++\n{chr(10).join(fm_lines)}\n+++\n{m.group(2)}"


def fix_trailing_newline(content):
    """Đảm bảo file kết thúc bằng đúng 1 newline."""
    return content.rstrip("\n") + "\n"


def make_fix_add_aliases(slug):
    """Closure factory: thêm aliases line sau date nếu chưa có."""
    def fixer(content):
        if ALIASES_LINE_RE.search(content):
            return content
        # Insert sau dòng date trong frontmatter
        replacement = f'\\g<0>\naliases = ["/{slug}/"]'
        return re.sub(r"^date\s*=.*$", replacement, content, count=1, flags=re.MULTILINE)
    return fixer


def detect_safe_fixes(path, content, fm):
    """Detect các vấn đề mechanical có thể auto-fix safely. Return list[Fix]."""
    fixes = []

    # Tags: detect nếu khác bản normalized
    tax = fm.get("taxonomies", {}) or {}
    tags = tax.get("tags", []) or []
    if tags:
        normalized = sorted({t.lower().strip() for t in tags if isinstance(t, str) and t.strip()})
        if normalized != tags:
            fixes.append(Fix(path,
                f'Normalize tags {tags} → {normalized} (lowercase + dedupe + sort)',
                fix_normalize_tags))

    # Categories: detect duplicate
    cats = tax.get("categories", []) or []
    if cats:
        deduped = list(dict.fromkeys(c for c in cats if isinstance(c, str)))
        if deduped != cats:
            fixes.append(Fix(path,
                f'Dedupe categories {cats} → {deduped}',
                fix_normalize_categories))

    # Date slash format
    if DATE_SLASH_RE.search(content):
        fixes.append(Fix(path,
            "Date format: YYYY/MM/DD → YYYY-MM-DD",
            fix_date_slash_to_dash))

    # Trailing whitespace trong frontmatter
    m = FRONTMATTER_RE.match(content)
    if m:
        fm_text = m.group(1)
        if any(line != line.rstrip() for line in fm_text.split("\n")):
            fixes.append(Fix(path,
                "Trim trailing whitespace trong frontmatter",
                fix_trim_frontmatter_trailing))

    # Trailing newline
    if not content.endswith("\n") or content.endswith("\n\n\n"):
        fixes.append(Fix(path,
            "Đảm bảo file kết thúc bằng đúng 1 newline",
            fix_trailing_newline))

    # Aliases auto-fill (deterministic, không đoán nội dung — chỉ suy từ slug)
    if not ALIASES_LINE_RE.search(content) and fm.get("title"):
        slug = path.stem
        fixes.append(Fix(path,
            f'Add missing aliases ["/{slug}/"]',
            make_fix_add_aliases(slug)))

    return fixes


def apply_fixes(all_fixes):
    """Group fixes theo path, chain apply trên từng file. Return số file đã sửa."""
    from collections import defaultdict
    by_path = defaultdict(list)
    for fix in all_fixes:
        by_path[fix.path].append(fix)

    touched = 0
    for path, fixes in by_path.items():
        try:
            full_path = REPO_ROOT / path if not Path(path).is_absolute() else Path(path)
            original = full_path.read_text(encoding="utf-8")
        except OSError:
            continue
        content = original
        for fix in fixes:
            content = fix.apply_fn(content)
        if content != original:
            full_path.write_text(content, encoding="utf-8")
            touched += 1
            for fix in fixes:
                # In ra để workflow capture vào PR body
                print(f"FIXED: {fix.path}: {fix.description}")
    return touched


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="QA Gatekeeper — scan conflict markers, secrets, SEO basic.",
        epilog="Exit 0 = pass (có thể có warning), 1 = ≥1 error.",
    )
    parser.add_argument("--fix", nargs="?", const="safe", choices=["safe"],
                        help="Auto-fix mode (chỉ 'safe' — mechanical fixes, không đoán nội dung)")
    parser.add_argument("targets", nargs="*",
                        help="Files cụ thể để scan (default: toàn repo)")
    args = parser.parse_args()
    fix_mode = args.fix

    all_issues = []
    all_fixes = []
    scanned = 0

    for path in iter_files(args.targets):
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        scanned += 1
        try:
            rel = path.relative_to(REPO_ROOT) if path.is_absolute() else path
        except ValueError:
            rel = path
        all_issues.extend(check_conflicts(rel, content))
        all_issues.extend(check_secrets(rel, content))
        all_issues.extend(check_scss_syntax(rel, content))
        if path.suffix == ".md":
            all_issues.extend(check_seo(rel, content))
            # Detect fixable issues riêng cho posting
            if "content/posting" in str(rel).replace("\\", "/") and not path.name.startswith("_"):
                fm, _ = parse_frontmatter(content)
                if fm is not None:
                    all_fixes.extend(detect_safe_fixes(rel, content, fm))

    print(f"{BOLD('[QA]')} Scanned {scanned} files\n")

    # Apply fixes trước khi report — để summary phản ánh state sau fix
    fixed_count = 0
    if fix_mode and all_fixes:
        fixed_count = apply_fixes(all_fixes)
        print()

    errors = [i for i in all_issues if i.level == "error"]
    warnings = [i for i in all_issues if i.level == "warning"]

    for issue in errors + warnings:
        print(issue.render())

    if all_issues:
        print()

    if fix_mode:
        summary = f"Summary: {fixed_count} file(s) auto-fixed, {len(errors)} remaining error(s), {len(warnings)} warning(s)"
    else:
        summary = f"Summary: {len(errors)} error(s), {len(warnings)} warning(s)"

    if errors and not fix_mode:
        print(RED(BOLD(summary)))
        return 1
    if fix_mode:
        # --fix mode: luôn exit 0 nếu không có internal error → workflow tiếp tục
        # commit + PR. Errors còn lại sẽ được flag bởi non-fix CI run trên PR.
        print(GREEN(summary) if fixed_count else YELLOW(summary) if warnings else GREEN(BOLD("✓ Không có gì cần auto-fix")))
        return 0
    if warnings:
        print(YELLOW(summary))
    else:
        print(GREEN(BOLD("✓ All QA checks passed")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
