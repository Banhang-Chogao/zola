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

# Performance thresholds (bytes). Quá ngưỡng → warning để user review.
# Chọn ngưỡng theo budget recommended cho personal blog (web.dev/perf-budgets).
PERF_THRESHOLDS = {
    "js_warn":     50_000,    # 50KB unminified
    "css_warn":    50_000,
    "img_warn":    250_000,   # 250KB (gồm hero JPG ~150KB)
    "html_warn":   100_000,
}

# Image extensions cho perf scan.
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}

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


# ============= Performance Check =============
# Mục đích: phát hiện asset nặng (JS/CSS/ảnh quá ngưỡng), <img> thiếu
# lazy loading, external CDN nhiều. Output dạng warning để user review;
# fix_perf() áp dụng SAFE auto-fix (chỉ add attr loading/decoding).

_IMG_TAG_RE = re.compile(r'<img\b([^>]*)>', re.IGNORECASE)
_HAS_LOADING_RE  = re.compile(r'\bloading\s*=', re.IGNORECASE)
_HAS_DECODING_RE = re.compile(r'\bdecoding\s*=', re.IGNORECASE)
_HAS_FETCHPRIO_RE = re.compile(r'\bfetchpriority\s*=', re.IGNORECASE)
_CDN_LINK_RE = re.compile(
    r'(?:src|href)=["\']https?://([^/"\']+)',
    re.IGNORECASE,
)

# Comment Tera ({# #}) + HTML (<!-- -->). Phải BỎ QUA <img> nằm trong comment:
# perf-fix từng chèn nhầm loading/decoding vào ví dụ <img> và văn xuôi trong
# comment (vd "dùng <img> thường" → "<img loading=...> thường") → edit rác.
_COMMENT_SPAN_RE = re.compile(r"\{#.*?#\}|<!--.*?-->", re.DOTALL)


def _comment_spans(content):
    """Trả list (start, end) các vùng comment để loại trừ khi quét <img>."""
    return [(m.start(), m.end()) for m in _COMMENT_SPAN_RE.finditer(content)]


def _in_spans(pos, spans):
    """pos có nằm trong bất kỳ vùng (start, end) nào không."""
    return any(s <= pos < e for s, e in spans)


def check_perf_file_size(path, raw_bytes):
    """Check kích thước file. Trả issue warning nếu vượt ngưỡng."""
    issues = []
    size = len(raw_bytes)
    sfx = path.suffix.lower()
    kb = size // 1024

    if sfx == ".js" and size > PERF_THRESHOLDS["js_warn"]:
        issues.append(Issue("warning", path, 1,
            f"PERF: JS file {kb}KB > {PERF_THRESHOLDS['js_warn']//1024}KB — "
            f"tối ưu: tách module, minify production, defer load"))
    elif sfx in (".css", ".scss") and size > PERF_THRESHOLDS["css_warn"]:
        issues.append(Issue("warning", path, 1,
            f"PERF: CSS file {kb}KB > {PERF_THRESHOLDS['css_warn']//1024}KB — "
            f"tối ưu: split critical CSS, purge unused"))
    elif sfx in IMAGE_EXTS and sfx != ".svg" and size > PERF_THRESHOLDS["img_warn"]:
        issues.append(Issue("warning", path, 1,
            f"PERF: ảnh {kb}KB > {PERF_THRESHOLDS['img_warn']//1024}KB — "
            f"tối ưu: resize ≤1280px, convert webp, quality 80"))
    elif sfx == ".html" and size > PERF_THRESHOLDS["html_warn"]:
        issues.append(Issue("warning", path, 1,
            f"PERF: HTML {kb}KB > {PERF_THRESHOLDS['html_warn']//1024}KB — "
            f"tối ưu: tách content sections, lazy-load below-fold"))
    return issues


def check_perf_html(path, content):
    """Check HTML/template: <img> thiếu lazy, đếm external CDN."""
    issues = []
    if path.suffix not in {".html"}:
        return issues

    # 1. <img> thiếu loading + decoding (skip nếu có fetchpriority=high — LCP)
    spans = _comment_spans(content)
    for m in _IMG_TAG_RE.finditer(content):
        if _in_spans(m.start(), spans):
            continue  # <img> trong comment/văn xuôi — KHÔNG phải tag thật
        attrs = m.group(1)
        if _HAS_FETCHPRIO_RE.search(attrs):
            continue  # LCP image — KHÔNG cần lazy
        line = content[:m.start()].count("\n") + 1
        missing = []
        if not _HAS_LOADING_RE.search(attrs):
            missing.append('loading="lazy"')
        if not _HAS_DECODING_RE.search(attrs):
            missing.append('decoding="async"')
        if missing:
            issues.append(Issue("warning", path, line,
                f"PERF: <img> thiếu {' + '.join(missing)} — auto-fixable"))

    # 2. Đếm external CDN host (cần preconnect)
    cdn_hosts = set()
    for m in _CDN_LINK_RE.finditer(content):
        host = m.group(1).lower()
        # Self-host KHÔNG tính
        if host.endswith("github.io"):
            continue
        cdn_hosts.add(host)
    if len(cdn_hosts) > 5:
        issues.append(Issue("warning", path, 1,
            f"PERF: {len(cdn_hosts)} external CDN ({', '.join(sorted(cdn_hosts)[:5])}…) — "
            f"thêm <link rel=preconnect> cho top 3 domain"))
    return issues


def fix_perf_html(content):
    """SAFE auto-fix: add loading=lazy + decoding=async vào <img> thiếu.
       KHÔNG đè fetchpriority=high (LCP image). Trả (new_content, count_fixed)."""
    fix_count = 0
    spans = _comment_spans(content)
    def _patch(m):
        nonlocal fix_count
        if _in_spans(m.start(), spans):
            return m.group(0)  # <img> trong comment/văn xuôi — KHÔNG đụng
        attrs = m.group(1)
        if _HAS_FETCHPRIO_RE.search(attrs):
            return m.group(0)  # giữ nguyên LCP image
        if _HAS_LOADING_RE.search(attrs) and _HAS_DECODING_RE.search(attrs):
            return m.group(0)
        new_attrs = attrs.rstrip()
        if not _HAS_LOADING_RE.search(attrs):
            new_attrs += ' loading="lazy"'
        if not _HAS_DECODING_RE.search(attrs):
            new_attrs += ' decoding="async"'
        fix_count += 1
        return f"<img{new_attrs}>"
    new_content = _IMG_TAG_RE.sub(_patch, content)
    return new_content, fix_count


def _scss_strip_noise(content: str) -> str:
    """Remove comments + string literals → giữ structural tokens cho count."""
    # IMPORTANT: Strip strings FIRST to avoid matching // inside URLs as comments
    content = _SCSS_STRING_RE.sub('""', content)
    content = _SCSS_BLOCK_COMMENT_RE.sub("", content)
    content = _SCSS_LINE_COMMENT_RE.sub("", content)
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


def run_vaccine_gate(args):
    """Run the QA Vaccine Gate (scripts/qa_vaccines.py) and print its summary.

    This is the reinforcement layer: it turns the CLAUDE.md vaccine library
    (V1..V12 + compliance set) into static detectors that block known recurring
    bugs before production (Tera kwargs, unbalanced template blocks, broken
    workflow YAML / config TOML, corrupt dashboard JSON, JS syntax errors,
    premium posts with no backing private content, …).

    Returns True if the gate FAILED (≥1 vaccine FAIL, or any WARN under
    --strict-vaccines). Only runs on a full-repo scan (no explicit targets) and
    never raises — a gate that crashes must not block the pipeline.
    """
    if args.no_vaccines or args.targets:
        return False
    try:
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        import qa_vaccines as qv
    except Exception as e:  # module missing / import error → don't block
        print(YELLOW(f"⚠ QA Vaccine Gate bỏ qua (không nạp được module): {e}"))
        return False
    try:
        print()
        results, summary = qv.run_all(REPO_ROOT)
        qv.print_report(results)
        qv.print_summary(summary, strict_warn=args.strict_vaccines)
        failed = qv.gate_failed(summary, strict_warn=args.strict_vaccines)
        if failed:
            print(RED(BOLD(
                "\n✗ QA Vaccine Gate FAILED — chặn deploy. Sửa các FAIL ở trên trước khi merge.")))
        return failed
    except Exception as e:  # detector bug must never crash the gatekeeper
        print(YELLOW(f"⚠ QA Vaccine Gate bỏ qua (lỗi nội bộ, không chặn): {e}"))
        return False


def run_watermark_gate(args):
    """Gate: every eligible blog image must carry its ownership watermark.

    Enforces the global image-watermark rule (scripts/watermark_blog_images.py +
    data/image-watermark-manifest.json): a content image added/changed without a
    watermark cannot pass QA. Mirrors the vaccine gate — only on a full-repo scan,
    never raises (a gate that crashes must not block the pipeline).

    Returns True if the gate FAILED (≥1 eligible image missing watermark / stale).
    """
    if args.targets:
        return False
    try:
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        import watermark_blog_images as wm
    except Exception as e:  # module missing / import error → don't block
        print(YELLOW(f"⚠ Watermark Gate bỏ qua (không nạp được module): {e}"))
        return False
    try:
        ok, missing, stale = wm.check_watermarks()
        total = len(wm.iter_eligible())
        print()
        print(BOLD("Blog Image Watermark Gate"))
        print(f"- Eligible images:   {total}")
        print(f"- Missing watermark: {len(missing)}")
        print(f"- Stale (changed):   {len(stale)}")
        if ok:
            print(GREEN("✓ Mọi ảnh blog hợp lệ đã được đóng watermark."))
            return False
        for m in missing[:20]:
            print(RED(f"  ✗ MISSING: {m}"))
        for s in stale[:20]:
            print(RED(f"  ✗ STALE:   {s}"))
        print(RED(BOLD(
            "\n✗ Watermark Gate FAILED — chạy: python3 scripts/watermark_blog_images.py --apply")))
        return True
    except Exception as e:  # detector bug must never crash the gatekeeper
        print(YELLOW(f"⚠ Watermark Gate bỏ qua (lỗi nội bộ, không chặn): {e}"))
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="QA Gatekeeper — scan conflict markers, secrets, SEO basic + QA Vaccine Gate.",
        epilog="Exit 0 = pass (có thể có warning), 1 = ≥1 error hoặc vaccine FAIL.",
    )
    parser.add_argument("--fix", nargs="?", const="safe", choices=["safe", "perf"],
                        help="Auto-fix mode: 'safe' (frontmatter mechanical) hoặc 'perf' (HTML/template img lazy)")
    parser.add_argument("--perf", action="store_true",
                        help="Chạy thêm performance check (file size, lazy load, CDN count)")
    parser.add_argument("--no-vaccines", action="store_true",
                        help="Bỏ qua QA Vaccine Gate (mặc định BẬT khi scan toàn repo)")
    parser.add_argument("--strict-vaccines", action="store_true",
                        help="Coi vaccine WARNING như lỗi → chặn deploy ngay cả khi chỉ có warning")
    parser.add_argument("targets", nargs="*",
                        help="Files cụ thể để scan (default: toàn repo)")
    args = parser.parse_args()
    fix_mode = args.fix

    all_issues = []
    all_fixes = []
    scanned = 0
    perf_fix_count = 0
    perf_fixed_files = []

    # Perf scan mở rộng SOURCE_EXTS để bao gồm ảnh
    scan_exts = SOURCE_EXTS | IMAGE_EXTS if args.perf or args.fix == "perf" else SOURCE_EXTS

    for path in iter_files(args.targets):
        # Đọc bytes trước (perf scan dùng size). Decode UTF-8 chỉ cho text files.
        try:
            raw = path.read_bytes()
        except OSError:
            continue
        is_text = path.suffix.lower() in SOURCE_EXTS
        content = ""
        if is_text:
            try:
                content = raw.decode("utf-8")
            except UnicodeDecodeError:
                continue
        scanned += 1
        try:
            rel = path.relative_to(REPO_ROOT) if path.is_absolute() else path
        except ValueError:
            rel = path

        # Perf checks — chạy cả cho image files
        if args.perf:
            all_issues.extend(check_perf_file_size(rel, raw))
            if is_text:
                all_issues.extend(check_perf_html(rel, content))

        # Perf auto-fix HTML/template img tags
        if args.fix == "perf" and path.suffix == ".html":
            new_content, n = fix_perf_html(content)
            if n > 0:
                path.write_text(new_content, encoding="utf-8")
                perf_fix_count += n
                perf_fixed_files.append((str(rel), n))
            content = new_content

        if not is_text:
            continue

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

    # Apply content fixes CHỈ ở --fix safe mode (perf mode đã apply img
    # fixes inline trong loop ở trên, không touch content frontmatter)
    fixed_count = 0
    if fix_mode == "safe" and all_fixes:
        fixed_count = apply_fixes(all_fixes)
        print()

    errors = [i for i in all_issues if i.level == "error"]
    warnings = [i for i in all_issues if i.level == "warning"]

    for issue in errors + warnings:
        print(issue.render())

    if all_issues:
        print()

    if fix_mode == "perf":
        perf_msg = f", {perf_fix_count} <img> tags fixed in {len(perf_fixed_files)} file(s)" if perf_fix_count else ""
        summary = f"Summary: {len(errors)} error(s), {len(warnings)} warning(s){perf_msg}"
        for fpath, n in perf_fixed_files:
            print(GREEN(f"FIXED: {fpath} — {n} <img> tags add loading/decoding"))
    elif fix_mode:
        summary = f"Summary: {fixed_count} file(s) auto-fixed, {len(errors)} remaining error(s), {len(warnings)} warning(s)"
    else:
        summary = f"Summary: {len(errors)} error(s), {len(warnings)} warning(s)"

    if fix_mode:
        # --fix mode: luôn exit 0 nếu không có internal error → workflow tiếp tục
        # commit + PR. Errors còn lại sẽ được flag bởi non-fix CI run trên PR.
        # Vaccine Gate KHÔNG chạy ở fix mode (nó chỉ gate full-repo scan non-fix).
        print(GREEN(summary) if fixed_count else YELLOW(summary) if warnings else GREEN(BOLD("✓ Không có gì cần auto-fix")))
        return 0

    # ----- Non-fix mode: print the existing QA summary first… -----
    if errors:
        print(RED(BOLD(summary)))
    elif warnings:
        print(YELLOW(summary))
    else:
        print(GREEN(BOLD("✓ All QA checks passed")))

    # …then run the QA Vaccine Gate (full-repo scan only) so its summary prints
    # LAST — the mandatory production-safety barrier from the CLAUDE.md vaccines.
    vaccine_failed = run_vaccine_gate(args)

<<<<<<< HEAD
    # Public-surface security gate (source scan): no private/internal files or
    # secret VALUES on content/ + static/. The authoritative full scan (incl.
    # the built public/ + sitemap) runs as a dedicated qa.yml step after the
    # build; here we give local `python3 qa_check.py` the same early signal.
    # Fail-CLOSED on real findings; fail-OPEN only if the module can't load — a
    # tooling hiccup must not brick every push (the qa.yml step is the backstop).
    security_failed = False
    try:
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        import security_public_audit as spa
        sec_errors = [f for f in spa.audit_public_surface(REPO_ROOT, include_public=False)
                      if f.level == "error"]
        print()
        print(BOLD("Security Public Audit (source surface)"))
        for f in sec_errors:
            print(f.render())
        if sec_errors:
            print(RED(BOLD(f"✗ {len(sec_errors)} public exposure(s) — see docs/security-static-blog.md")))
            security_failed = True
        else:
            print(GREEN("✓ No private/internal files or secret values on the public source surface"))
    except Exception as e:  # tooling hiccup — the qa.yml audit step is the backstop
        print(YELLOW(f"⚠ security_public_audit skipped: {e}"))

    return 1 if (errors or vaccine_failed or security_failed) else 0
=======
    # …and the Blog Image Watermark Gate (global ownership-watermark rule).
    watermark_failed = run_watermark_gate(args)

    return 1 if (errors or vaccine_failed or watermark_failed) else 0
>>>>>>> origin/main


if __name__ == "__main__":
    sys.exit(main())
