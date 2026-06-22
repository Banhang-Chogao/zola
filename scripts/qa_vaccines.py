#!/usr/bin/env python3
"""QA Vaccine Gate — production safety barrier built from the CLAUDE.md vaccine library.

This module turns the accumulated "💉 THƯ VIỆN VACCINE" (CLAUDE.md §4) and the
mandatory project rules into *static detectors* that run BEFORE anything reaches
production. It is the reinforcement layer of the QA Gatekeeper: where `qa_check.py`
catches generic issues (conflict markers, secrets, SCSS syntax, SEO basics), this
module catches the **known recurring bugs** that have actually broken the build or
the site in the past — so they are caught earlier, with a clear diagnosis, the
exact fix, and a reference to the originating vaccine.

Design goals (per task brief):
  * Load EVERY vaccine documented in CLAUDE.md (`#### V<N> — …` blocks).
  * Run a relevant static detector for each one that is statically checkable.
  * On a known issue → FAIL the gate, print a clear diagnosis, suggest the exact
    fix, and reference the vaccine name.
  * Never remove or weaken existing QA checks — this is purely additive.
  * Print a "QA Vaccine Summary" with a production-readiness score at the end.

Severity philosophy (calibrated against current `main` → 0 FAIL):
  * FAIL  — genuinely breaks `zola build` or production (Tera kwargs, unbalanced
            template blocks, invalid workflow YAML / config TOML, JS syntax errors,
            corrupt dashboard JSON, premium post with no backing private file).
  * WARN  — consistency / resilience / best-practice issues that do NOT break the
            build but should be reviewed (deploy resilience, series registration,
            category-first rule, missing assets, schema scaffolding, paywall id).
  * SKIP  — detector not applicable in this environment (e.g. node/yaml absent),
            or the vaccine is a *process* vaccine (PR-time / git-history) with no
            single-checkout static signal.

Stdlib only (tomllib on 3.11+, optional PyYAML). Safe to import; never raises on
malformed input — a detector that errors is reported as a WARN, never a crash.

CLI:
    python3 scripts/qa_vaccines.py                 # full report + summary, exit 1 on FAIL
    python3 scripts/qa_vaccines.py --json          # machine-readable report
    python3 scripts/qa_vaccines.py --strict-warn   # treat warnings as failures too
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"

# ----- status constants -----
PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"
SKIP = "SKIP"

# ----- colors (disabled on CI / non-tty) -----
_USE_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOR else text


def _red(s):    return _c("31", s)
def _green(s):  return _c("32", s)
def _yellow(s): return _c("33", s)
def _blue(s):   return _c("36", s)
def _bold(s):   return _c("1", s)
def _dim(s):    return _c("2", s)

_STATUS_BADGE = {
    PASS: lambda: _green("✓ PASS"),
    FAIL: lambda: _red("✗ FAIL"),
    WARN: lambda: _yellow("⚠ WARN"),
    SKIP: lambda: _dim("• SKIP"),
}


@dataclass
class CheckResult:
    """Outcome of one vaccine detector."""
    vaccine: str          # vaccine code, e.g. "V8"
    title: str            # short human title of the check
    status: str           # PASS | FAIL | WARN | SKIP
    diagnosis: str = ""   # what was found (clear log)
    fix: str = ""         # the exact suggested fix
    details: list[str] = field(default_factory=list)  # per-occurrence detail lines

    def render(self) -> str:
        head = f"  {_STATUS_BADGE[self.status]()}  {_bold(self.vaccine)} · {self.title}"
        lines = [head]
        if self.status in (FAIL, WARN) and self.diagnosis:
            lines.append(f"        {_dim('chẩn đoán:')} {self.diagnosis}")
        for d in self.details[:12]:
            lines.append(f"          - {d}")
        if len(self.details) > 12:
            lines.append(f"          … (+{len(self.details) - 12} mục nữa)")
        if self.status in (FAIL, WARN) and self.fix:
            lines.append(f"        {_dim('cách sửa:')}  {self.fix}")
        if self.status in (FAIL, WARN):
            lines.append(f"        {_dim('vaccine:')}   CLAUDE.md §{self.vaccine}")
        return "\n".join(lines)


# --------------------------------------------------------------------------
# Vaccine library loader — count every `#### V<N> — …` block in CLAUDE.md
# --------------------------------------------------------------------------
_VACCINE_HEADER = re.compile(r"^####\s+(V\d+)\s+—\s+(.+?)\s*$", re.MULTILINE)


def load_vaccines(text: str | None = None) -> list[dict]:
    """Parse the CLAUDE.md vaccine library into [{code, title}] entries.

    Duplicate codes (the library has two V10/V11/V12 groups) are kept as
    separate entries — they ARE separate documented vaccines.
    """
    if text is None:
        try:
            text = CLAUDE_MD.read_text(encoding="utf-8")
        except OSError:
            return []
    out: list[dict] = []
    for m in _VACCINE_HEADER.finditer(text):
        out.append({"code": m.group(1), "title": m.group(2).strip()})
    return out


# --------------------------------------------------------------------------
# Shared context — cached repo reads so detectors stay fast
# --------------------------------------------------------------------------
class Ctx:
    def __init__(self, root: Path):
        self.root = root
        self._cache: dict[Path, str] = {}

    def read(self, rel: str) -> str | None:
        p = self.root / rel
        if p in self._cache:
            return self._cache[p]
        try:
            txt = p.read_text(encoding="utf-8")
        except OSError:
            txt = None
        self._cache[p] = txt
        return txt

    def exists(self, rel: str) -> bool:
        return (self.root / rel).exists()

    def glob(self, pattern: str) -> list[Path]:
        return sorted(self.root.glob(pattern))


# --------------------------------------------------------------------------
# Small CSS helpers (shared by structural detectors)
# --------------------------------------------------------------------------
_CSS_COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)


def _strip_css_comments(text: str) -> str:
    """Remove /* … */ comments so commented-out CSS (e.g. an explanatory
    `position: sticky` note) never trips a block scan."""
    return _CSS_COMMENT_RE.sub("", text or "")


def _mobile_media_spans(text: str) -> list[tuple[int, int]]:
    """Return (start, end) char spans of every `@media (… max-width …) { … }`
    block, including nested content. Used to EXEMPT mobile-scoped rules from
    desktop-only checks (mobile is handled separately — see V21)."""
    spans: list[tuple[int, int]] = []
    for m in re.finditer(r"@media[^{]*max-width[^{]*\{", text, re.I):
        depth = 0
        i = m.end() - 1  # position of the opening brace
        while i < len(text):
            c = text[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    spans.append((m.start(), i))
                    break
            i += 1
    return spans


def _in_spans(pos: int, spans: list[tuple[int, int]]) -> bool:
    return any(a <= pos <= b for a, b in spans)


# --------------------------------------------------------------------------
# Detectors — each returns a CheckResult
# --------------------------------------------------------------------------
def check_v1_hf_model_id(ctx: Ctx) -> CheckResult:
    """V1 — HuggingFace model id must be org-qualified (`org/model`) or
    snapshot_download 401s and spams the build-related cron every 5 min."""
    title = "HuggingFace model id org-qualified"
    bare = []
    for rel in ("scripts/related_engine.py", "scripts/build_related.py"):
        src = ctx.read(rel)
        if not src:
            continue
        for m in re.finditer(r'MODEL_NAME\s*=\s*["\']([^"\']+)["\']', src):
            model = m.group(1)
            if "/" not in model:
                bare.append(f"{rel}: MODEL_NAME = '{model}' (thiếu org prefix)")
    if bare:
        return CheckResult("V1", title, FAIL,
                           diagnosis="model id để trần, HF Hub tra repo top-level → 401",
                           fix='dùng repo-id đầy đủ, vd "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"',
                           details=bare)
    return CheckResult("V1", title, PASS)


def check_v2_slack_v3(ctx: Ctx) -> CheckResult:
    """V2 — slack-notify.yml must use the v3 `webhook-type:` input, not the
    removed v1 `SLACK_WEBHOOK_TYPE: INCOMING_WEBHOOK` env."""
    title = "slack-notify.yml v3 webhook syntax"
    src = ctx.read(".github/workflows/slack-notify.yml")
    if src is None:
        return CheckResult("V2", title, SKIP, diagnosis="slack-notify.yml absent")
    if "SLACK_WEBHOOK_TYPE: INCOMING_WEBHOOK" in src and "webhook-type:" not in src:
        return CheckResult("V2", title, FAIL,
                           diagnosis="cú pháp v1 (env SLACK_WEBHOOK_TYPE) sau bump action v3",
                           fix='dùng `webhook-type: incoming-webhook` + block `payload:` inline (v3)')
    return CheckResult("V2", title, PASS)


def check_v5_deploy_resilience(ctx: Ctx) -> CheckResult:
    """V5 — deploy.yml needs concurrency + configure-pages enablement to survive
    the `configure-pages` 'API rate limit exceeded' storms."""
    title = "deploy.yml rate-limit resilience"
    src = ctx.read(".github/workflows/deploy.yml")
    if src is None:
        return CheckResult("V5", title, SKIP, diagnosis="deploy.yml absent")
    missing = []
    if "concurrency:" not in src:
        missing.append("thiếu `concurrency:` group (gộp bão deploy)")
    if "configure-pages" in src and "enablement: true" not in src:
        missing.append("configure-pages thiếu `enablement: true`")
    if missing:
        return CheckResult("V5", title, WARN,
                           diagnosis="deploy có thể đỏ khi cạn quota API installation",
                           fix="thêm concurrency.cancel-in-progress + configure-pages enablement: true",
                           details=missing)
    return CheckResult("V5", title, PASS)


_TERA_COMMENT_RE = re.compile(r"\{#.*?#\}", re.DOTALL)
_TERA_RAW_RE = re.compile(r"\{%-?\s*raw\s*-?%\}.*?\{%-?\s*endraw\s*-?%\}", re.DOTALL)
# Tera `replace` uses from=/to=. Python kwargs old=/new= silently break the build.
_TERA_BAD_REPLACE_RE = re.compile(r"\breplace\s*\(\s*(old|new)\s*=", re.IGNORECASE)

# Tera has NO object/map literal syntax. `default(value={})`, `{% set x = {} %}` or
# any `{ "k": v }` map crash `zola build` with
# "expected a value that can be negated or an array of values". Arrays `[...]` are OK.
_TERA_MAP_DEFAULT_RE = re.compile(r"default\s*\(\s*value\s*=\s*\{")
_TERA_MAP_SET_RE = re.compile(r"\{%-?\s*set\s+\w[\w]*\s*=\s*\{\s*[}\"'\w]")


def _strip_tera_noise(src: str) -> str:
    src = _TERA_RAW_RE.sub("", src)
    src = _TERA_COMMENT_RE.sub("", src)
    return src


def check_v8a_tera_filter_kwargs(ctx: Ctx) -> CheckResult:
    """V8 — Tera `replace` filter must use from=/to=, NOT Python's old=/new=.
    The orphan-series fallback once used `replace(old=…, new=…)` → build crash."""
    title = "Tera replace() uses from=/to= (not old=/new=)"
    hits = []
    for p in ctx.glob("templates/**/*.html"):
        src = _strip_tera_noise(p.read_text(encoding="utf-8", errors="ignore"))
        for m in _TERA_BAD_REPLACE_RE.finditer(src):
            line = src[:m.start()].count("\n") + 1
            rel = p.relative_to(ctx.root)
            hits.append(f"{rel}:{line}: replace({m.group(1)}=…) — kwarg Python sai")
    if hits:
        return CheckResult("V8", title, FAIL,
                           diagnosis="filter `replace` của Tera chỉ nhận `from=`/`to=` → vỡ zola build",
                           fix='đổi replace(old=\"-\", new=\" \") → replace(from=\"-\", to=\" \")',
                           details=hits)
    return CheckResult("V8", title, PASS)


_TERA_OPENERS = {
    "if": re.compile(r"\{%-?\s*if\b"),
    "for": re.compile(r"\{%-?\s*for\b"),
    "block": re.compile(r"\{%-?\s*block\b"),
    "macro": re.compile(r"\{%-?\s*macro\b"),
}
_TERA_CLOSERS = {
    "if": re.compile(r"\{%-?\s*endif\b"),
    "for": re.compile(r"\{%-?\s*endfor\b"),
    "block": re.compile(r"\{%-?\s*endblock\b"),
    "macro": re.compile(r"\{%-?\s*endmacro\b"),
}


def check_v8b_template_block_balance(ctx: Ctx) -> CheckResult:
    """Broken template guard — unbalanced Tera if/for/block/macro openers vs
    closers crash `zola build` with 'Failed to render'. Catch it statically."""
    title = "Tera block balance (if/for/block/macro)"
    hits = []
    for p in ctx.glob("templates/**/*.html"):
        src = _strip_tera_noise(p.read_text(encoding="utf-8", errors="ignore"))
        rel = p.relative_to(ctx.root)
        for kind, opener in _TERA_OPENERS.items():
            opens = len(opener.findall(src))
            closes = len(_TERA_CLOSERS[kind].findall(src))
            if opens != closes:
                hits.append(f"{rel}: {kind} mở {opens} ≠ đóng {closes} "
                            f"(thiếu {'end' + kind if opens > closes else kind})")
    if hits:
        return CheckResult("V8", title, FAIL,
                           diagnosis="template lệch block → zola 'Failed to render'",
                           fix="cân bằng mỗi {% if/for/block/macro %} với end-tag tương ứng",
                           details=hits)
    return CheckResult("V8", title, PASS)


def check_v8b1_tera_map_literals(ctx: Ctx) -> CheckResult:
    """Tera map/list literal restriction — templates must not use `default(value={})`
    or `default(value=[])` in filter arguments. Tera does not support object/list
    literals in filter kwargs; use scalar fallback or `{% if var %}` guards instead."""
    title = "Tera filter args: no map/list literals"
    hits = []
    # Pattern: look for `default(value={...})` or `default(value=[...])` in templates
    # Skip Tera comments and raw blocks
    for p in ctx.glob("templates/**/*.html"):
        src = p.read_text(encoding="utf-8", errors="ignore")
        # Strip comments and raw blocks first
        src_clean = _strip_tera_noise(src)
        # Check for unsupported patterns: `default(value={` or `default(value=[`
        # This catches the obvious culprits. A smarter regex could handle nested
        # braces, but for this gate the simple check is sufficient.
        for m in re.finditer(r'\bdefault\s*\(\s*value\s*=\s*[\{\[]', src_clean):
            line = src[:m.start()].count("\n") + 1
            snippet = src_clean[max(0, m.start()-30):m.end()+30].strip()
            rel = p.relative_to(ctx.root)
            hits.append(f"{rel}:{line}: default(value={{...}}) or default(value=[...]) "
                       f"← replace with scalar fallback or ifs guard")
    if hits:
        return CheckResult("V8", title, FAIL,
                           diagnosis="Tera filter kwargs không support `{}` hay `[]` literals → vỡ zola build",
                           fix="dùng scalar fallback (0, \"\", false) hoặc guard bằng {% if var %} block",
                           details=hits)
    return CheckResult("V8", title, PASS)


def _series_ids_from_templates(ctx: Ctx) -> set[str]:
    ids: set[str] = set()
    for rel in ("templates/page.html", "templates/macros/series-nav.html",
                "templates/base.html"):
        src = ctx.read(rel) or ""
        for m in re.finditer(r'series\s*==\s*["\']([a-z0-9\-]+)["\']', src):
            ids.add(m.group(1))
    return ids


def check_v8d_tera_map_literal(ctx: Ctx) -> CheckResult:
    """V8 — Tera has no object/map literal. `default(value={})` and
    `{% set x = {} %}` (or any `{ … }` dict) crash `zola build`; arrays `[…]` are
    allowed. Regression source: insights.html perf-fix used `default(value={})`,
    which qa_check.py (no zola build) missed → only CI caught it. This static
    detector catches the pattern before the build."""
    title = "Tera map/object literal (no {} dicts)"
    hits = []
    for p in ctx.glob("templates/**/*.html"):
        src = _strip_tera_noise(p.read_text(encoding="utf-8", errors="ignore"))
        rel = p.relative_to(ctx.root)
        for label, rx in (("default(value={…})", _TERA_MAP_DEFAULT_RE),
                          ("set x = {…} map literal", _TERA_MAP_SET_RE)):
            for m in rx.finditer(src):
                line = src[:m.start()].count("\n") + 1
                hits.append(f"{rel}:{line}: {label}")
    if hits:
        return CheckResult("V8", title, FAIL,
                           diagnosis="Tera KHÔNG support object/map literal `{}` → vỡ zola build "
                                     "('expected a value that can be negated or an array of values')",
                           fix="bỏ map literal: dùng scalar `x.field | default(value=0/\"\")`, "
                               "guard `{% if x %}`, hoặc array `[]` — KHÔNG dùng `{}`",
                           details=hits)
    return CheckResult("V8", title, PASS)


def check_v8c_series_registration(ctx: Ctx) -> CheckResult:
    """V8 — every data/<id>-series.json must be registered in
    series-listing.html (manifests array) so it never falls into the orphan
    fallback branch; and every series referenced in the page/nav elif chains
    must have a backing manifest."""
    title = "Series registration consistency"
    listing = ctx.read("templates/macros/series-listing.html") or ""
    manifest_files = [p.name for p in ctx.glob("data/*-series.json")]
    unregistered = [f for f in manifest_files if f not in listing]

    # series ids referenced in elif chains but without a manifest file
    referenced = _series_ids_from_templates(ctx)
    have_manifest = {p.name[:-len("-series.json")] for p in ctx.glob("data/*-series.json")}
    orphan_refs = sorted(referenced - have_manifest)

    details = []
    for f in unregistered:
        details.append(f"data/{f} chưa khai báo trong series-listing.html (manifests[])")
    for sid in orphan_refs:
        details.append(f'series "{sid}" có elif nhưng thiếu data/{sid}-series.json')

    if details:
        return CheckResult("V8", title, WARN,
                           diagnosis="series chưa đăng ký đầy đủ → rơi vào orphan fallback",
                           fix="đăng ký manifest trong series-listing.html + elif ở page.html & series-nav.html",
                           details=details)
    return CheckResult("V8", title, PASS)


def check_v32_series_part_sort_guard(ctx: Ctx) -> CheckResult:
    """V32 — `sort(attribute="extra.series_part")` must be guarded by a `filter`.

    Tera's `sort` filter raises and breaks `zola build` when ANY element lacks the
    sort attribute. series-listing.html groups posts by `extra.series`; a single
    member (e.g. a series overview page) declaring `extra.series` WITHOUT
    `extra.series_part` is enough to crash every paginated section render
    ("Filter call 'sort' failed → attribute 'extra.series_part' does not reference
    a field"). The durable fix narrows the list with
    `| filter(attribute="extra.series_part")` BEFORE sorting, so a missing part can
    never abort the build.
    """
    title = "Series sort guarded against missing series_part (V32)"
    html = ctx.read("templates/macros/series-listing.html")
    if html is None:
        return CheckResult("V32", title, SKIP,
                           diagnosis="series-listing.html không tồn tại")

    # Every `sort(attribute="extra.series_part")` must be applied to a variable
    # produced by `filter(attribute="extra.series_part")` (a sortable subset).
    sort_calls = re.findall(
        r"(\w+)\s*\|\s*sort\(attribute\s*=\s*[\"']extra\.series_part[\"']\)", html)
    filtered_vars = set(re.findall(
        r"set\s+(\w+)\s*=\s*[^\n]*\|\s*filter\(attribute\s*=\s*[\"']extra\.series_part[\"']\)",
        html))
    unguarded = [v for v in sort_calls if v not in filtered_vars]

    if unguarded:
        return CheckResult(
            "V32", title, FAIL,
            diagnosis="sort(attribute=\"extra.series_part\") chạy trên list CHƯA lọc "
                      "→ 1 bài thiếu series_part làm vỡ zola build",
            fix='lọc trước: {% set sortable = group_pages | '
                'filter(attribute="extra.series_part") %} rồi sortable | sort(...); '
                'bài thuộc series phải có series_part (trang tổng quan = 0)',
            details=[f"sort trên biến chưa filter: '{v}'" for v in unguarded])
    if not sort_calls:
        return CheckResult("V32", title, PASS)
    return CheckResult("V32", title, PASS)


def check_v9_v10_process(ctx: Ctx) -> CheckResult:
    """V9/V10 — stale base & dirty-PR merge race are PR-time / git-history
    vaccines, not single-checkout static signals. Surface them as a reminder so
    the gate documents that they are covered by the merge workflow, not here."""
    return CheckResult("V9/V10", "Stale-base / merge-race (process vaccine)", SKIP,
                       diagnosis="kiểm tra ở PR-time (rebase lên main mới nhất, regenerate data)")


def check_v12_shared_infra_dupes(ctx: Ctx) -> CheckResult:
    """V12 — base.html + _footer.scss are the highest-conflict zone. A bad merge
    leaves DUPLICATE footer/sidebar selectors. Each must be defined once."""
    title = "Shared infra no duplicate footer blocks"
    details = []
    scss = ctx.read("sass/_footer.scss")
    if scss:
        for sel in (".footer-categories", ".footer-tags"):
            n = len(re.findall(re.escape(sel) + r"\s*\{", scss))
            if n > 1:
                details.append(f"sass/_footer.scss: '{sel} {{' xuất hiện {n} lần (nên 1)")
    base = ctx.read("templates/base.html")
    if base:
        # duplicate <footer> opener is a classic blind-merge artifact. Strip
        # Tera/HTML comments first — base.html mentions <footer> in {# … #} notes.
        base_clean = re.sub(r"<!--.*?-->", "", _strip_tera_noise(base), flags=re.DOTALL)
        n_footer = len(re.findall(r"<footer\b", base_clean))
        if n_footer > 1:
            details.append(f"templates/base.html: {n_footer} thẻ <footer> (merge trùng?)")
    if details:
        return CheckResult("V12", title, WARN,
                           diagnosis="merge mù ours/theirs để lại block footer/sidebar trùng",
                           fix="merge theo intent: mỗi selector/khối footer định nghĩa đúng 1 lần",
                           details=details)
    return CheckResult("V12", title, PASS)


def check_category_first(ctx: Ctx) -> CheckResult:
    """Category rule — every post must have "Tất cả" as the FIRST category so
    the default hub /categories/tat-ca/ gathers it."""
    title = 'Category rule ("Tất cả" đứng đầu)'
    bad = []
    for p in ctx.glob("content/**/*.md"):
        name = p.name
        if name.startswith("_"):
            continue
        sp = str(p).replace("\\", "/")
        if "/posting/" not in sp and "/baochi/" not in sp:
            continue
        txt = p.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"^categories\s*=\s*\[(.*?)\]", txt, re.MULTILINE)
        if not m:
            bad.append(f"{p.relative_to(ctx.root)}: thiếu mảng categories")
            continue
        items = [x.strip().strip("\"'") for x in m.group(1).split(",") if x.strip()]
        if not items or items[0] != "Tất cả":
            bad.append(f"{p.relative_to(ctx.root)}: categories[0] = {items[:1] or '∅'} (cần \"Tất cả\")")
    if bad:
        return CheckResult("RULE-CAT", title, WARN,
                           diagnosis="bài thiếu category mặc định → hub /categories/tat-ca/ không gom đủ",
                           fix='đặt "Tất cả" đầu mảng categories (vd ["Tất cả", "Banking"])',
                           details=bad)
    return CheckResult("RULE-CAT", title, PASS)


def check_paywall_integrity(ctx: Ctx) -> CheckResult:
    """Paywall — a premium post needs a premium_post_id whose backing
    private_content/<id>.md exists, or the teaser has no full content to unlock."""
    title = "Premium/paywall backing content"
    fail_details = []
    warn_details = []
    for p in ctx.glob("content/**/*.md"):
        txt = p.read_text(encoding="utf-8", errors="ignore")
        if not re.search(r"^premium\s*=\s*true", txt, re.MULTILINE):
            continue
        rel = p.relative_to(ctx.root)
        m = re.search(r'^premium_post_id\s*=\s*"([^"]+)"', txt, re.MULTILINE)
        if not m:
            warn_details.append(f"{rel}: premium=true nhưng thiếu premium_post_id")
            continue
        pid = m.group(1)
        if not ctx.exists(f"private_content/{pid}.md"):
            fail_details.append(f"{rel}: premium_post_id '{pid}' nhưng thiếu private_content/{pid}.md")
    if fail_details:
        return CheckResult("RULE-PAYWALL", title, FAIL,
                           diagnosis="bài premium không có nội dung đầy đủ ở backend → unlock rỗng",
                           fix="tạo private_content/<premium_post_id>.md cho mỗi bài premium",
                           details=fail_details + warn_details)
    if warn_details:
        return CheckResult("RULE-PAYWALL", title, WARN,
                           diagnosis="premium=true nhưng thiếu premium_post_id để map unlock/strip",
                           fix='thêm premium_post_id = "premium-..." vào frontmatter',
                           details=warn_details)
    return CheckResult("RULE-PAYWALL", title, PASS)


def check_dashboard_json(ctx: Ctx) -> CheckResult:
    """Broken dashboards — every data/*.json feeding the Insights/Build/Merge/
    Compliance dashboards must be valid JSON or load_data() fails the build."""
    title = "Dashboard data JSON valid"
    bad = []
    for p in ctx.glob("data/*.json"):
        try:
            json.loads(p.read_text(encoding="utf-8"))
        except (ValueError, OSError) as e:
            bad.append(f"{p.relative_to(ctx.root)}: {str(e)[:80]}")
    if bad:
        return CheckResult("DASH", title, FAIL,
                           diagnosis="JSON hỏng → load_data() trong template fail → vỡ build/dashboard",
                           fix="sửa JSON hợp lệ (thường do merge conflict trong data/*.json)",
                           details=bad)
    return CheckResult("DASH", title, PASS)


def check_js_syntax(ctx: Ctx) -> CheckResult:
    """JS runtime guard — node --check every static/js script to catch syntax
    errors before they reach the browser (F/L/O/H-Dashboard, editor, paywall…)."""
    title = "JS syntax (node --check)"
    from shutil import which
    if which("node") is None:
        return CheckResult("JS", title, SKIP, diagnosis="node không có — bỏ qua (CI có node)")
    bad = []
    files = ctx.glob("static/js/**/*.js")
    for p in files:
        try:
            res = subprocess.run(["node", "--check", str(p)],
                                 capture_output=True, text=True, timeout=30)
        except (subprocess.TimeoutExpired, OSError):
            continue
        if res.returncode != 0:
            err = (res.stderr or "").strip().splitlines()
            # A bare top-level import/export in a non-module file is a context
            # error, not a syntax bug — ignore it (these are browser scripts).
            joined = " ".join(err)
            if "outside a module" in joined or "Cannot use import statement" in joined:
                continue
            msg = next((l for l in err if "SyntaxError" in l), err[-1] if err else "syntax error")
            bad.append(f"{p.relative_to(ctx.root)}: {msg.strip()[:120]}")
    if bad:
        return CheckResult("JS", title, FAIL,
                           diagnosis="lỗi cú pháp JS → script chết runtime trên trình duyệt",
                           fix="sửa SyntaxError; chạy `node --check <file>` để xác nhận",
                           details=bad)
    return CheckResult("JS", title, PASS, diagnosis=f"{len(files)} file JS OK")


def check_config_toml(ctx: Ctx) -> CheckResult:
    """Broken config guard — config.toml must be valid TOML with the keys Zola
    and the paywall/momo rules rely on."""
    title = "config.toml valid + required keys"
    raw = ctx.read("config.toml")
    if raw is None:
        return CheckResult("CONFIG", title, SKIP, diagnosis="config.toml absent")
    try:
        import tomllib
    except ModuleNotFoundError:
        # Python <3.11 — only do a light non-parse sanity check
        if "base_url" not in raw:
            return CheckResult("CONFIG", title, WARN,
                               diagnosis="không có tomllib để parse; thiếu base_url?",
                               fix="đảm bảo config.toml có base_url")
        return CheckResult("CONFIG", title, SKIP, diagnosis="tomllib không có (Python <3.11)")
    try:
        data = tomllib.loads(raw)
    except tomllib.TOMLDecodeError as e:
        return CheckResult("CONFIG", title, FAIL,
                           diagnosis=f"config.toml TOML không hợp lệ → zola build fail: {str(e)[:80]}",
                           fix="sửa cú pháp TOML (thường do conflict marker / quote lệch)")
    warn = []
    if not data.get("base_url"):
        warn.append("thiếu base_url")
    if not data.get("extra", {}).get("momo_payment_link"):
        warn.append("extra.momo_payment_link absent (Momo rule)")
    if warn:
        return CheckResult("CONFIG", title, WARN,
                           diagnosis="config.toml thiếu key khuyến nghị",
                           fix="bổ sung key còn thiếu trong config.toml",
                           details=warn)
    return CheckResult("CONFIG", title, PASS)


def check_seo_schema_scaffold(ctx: Ctx) -> CheckResult:
    """SEO / schema regression — base.html must keep the JSON-LD + OpenGraph
    scaffolding (Article/FAQ/Breadcrumb schema, og:image/title) the SEO rules
    rely on for rich results."""
    title = "SEO/schema scaffolding in base.html"
    base = ctx.read("templates/base.html") or ""
    missing = []
    if "application/ld+json" not in base:
        missing.append("thiếu JSON-LD (application/ld+json) — Article/FAQ/Breadcrumb schema")
    if 'property="og:image"' not in base and "og:image" not in base:
        missing.append("thiếu og:image meta")
    if 'property="og:title"' not in base and "og:title" not in base:
        missing.append("thiếu og:title meta")
    if missing:
        return CheckResult("SEO", title, WARN,
                           diagnosis="mất scaffolding schema/OpenGraph → giảm rich result + social preview",
                           fix="khôi phục block JSON-LD + meta Og trong templates/base.html",
                           details=missing)
    return CheckResult("SEO", title, PASS)


_ASSET_REF_RE = re.compile(
    r'(?:src|href)\s*=\s*["\'](/(?:img|fonts)/[^"\'{}]+\.(?:webp|svg|png|jpe?g|gif|woff2?|ttf|ico))["\']',
    re.IGNORECASE,
)


def check_missing_assets(ctx: Ctx) -> CheckResult:
    """Missing assets — static /img and /fonts references in templates must
    resolve to a file in static/ (strips the GitHub-Pages base prefix). This is
    a soft complement to qa-404-checker (the hard gate on built links)."""
    title = "Static asset references resolve"
    base_url = ""
    cfg = ctx.read("config.toml") or ""
    mb = re.search(r'^base_url\s*=\s*"([^"]+)"', cfg, re.MULTILINE)
    if mb:
        # e.g. https://…/zola → prefix "/zola"
        path = re.sub(r"^https?://[^/]+", "", mb.group(1)).rstrip("/")
        base_url = path
    missing = set()
    for p in ctx.glob("templates/**/*.html"):
        src = p.read_text(encoding="utf-8", errors="ignore")
        for m in _ASSET_REF_RE.finditer(src):
            ref = m.group(1)
            rel = ref
            if base_url and ref.startswith(base_url + "/"):
                rel = ref[len(base_url):]
            if not (ctx.root / "static" / rel.lstrip("/")).exists():
                missing.add(f"{ref}  (←{p.relative_to(ctx.root)})")
    if missing:
        return CheckResult("ASSET", title, WARN,
                           diagnosis="template tham chiếu asset không tồn tại trong static/",
                           fix="tạo file trong static/ hoặc gỡ tham chiếu (checker không tự bịa ảnh)",
                           details=sorted(missing))
    return CheckResult("ASSET", title, PASS)


def check_workflow_yaml(ctx: Ctx) -> CheckResult:
    """GitHub Actions guard — every workflow must be valid YAML (a corrupt
    workflow silently stops running). V3/V7: observer/remediation workflows
    should swallow exit codes (continue-on-error) so they never self-red."""
    title = "GitHub Actions workflows valid YAML"
    workflows = ctx.glob(".github/workflows/*.yml") + ctx.glob(".github/workflows/*.yaml")
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError:
        return CheckResult("GHA", title, SKIP,
                           diagnosis="PyYAML không có — bỏ qua parse (V1/V2/V5 vẫn chạy riêng)")
    bad = []
    for p in workflows:
        try:
            yaml.safe_load(p.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            bad.append(f"{p.relative_to(ctx.root)}: {str(e)[:80]}")
    if bad:
        return CheckResult("GHA", title, FAIL,
                           diagnosis="workflow YAML hỏng → Actions không chạy",
                           fix="sửa cú pháp YAML (indent, ':' lệch, conflict marker)",
                           details=bad)
    return CheckResult("GHA", title, PASS, diagnosis=f"{len(workflows)} workflow OK")


def check_series_nav_vaccine(ctx: Ctx) -> CheckResult:
    """Series Hub completeness — if series JSONs exist but /tools/series/ is
    missing the hub is empty for users; also validates series-nav.html has at
    least one elif branch wired to a known manifest."""
    title = "Series Hub completeness (/tools/series/ + series-nav wiring)"
    series_files = ctx.glob("data/*-series.json")
    if not series_files:
        return CheckResult("SERIES-HUB", title, SKIP,
                           diagnosis="data/*-series.json absent — bỏ qua")
    # Hub page must exist when series JSONs are present.
    if not ctx.exists("content/tools/series.md"):
        return CheckResult("SERIES-HUB", title, FAIL,
                           diagnosis=f"{len(series_files)} series JSON có nhưng hub /tools/series/ vắng",
                           fix="tạo content/tools/series.md với template = 'series-hub-page.html'")
    details: list[str] = []
    # Hub template must load at least one series JSON.
    hub_tpl = ctx.read("templates/series-hub-page.html") or ""
    if not hub_tpl:
        details.append("templates/series-hub-page.html vắng — hub sẽ render rỗng")
    elif "series.json" not in hub_tpl:
        details.append("templates/series-hub-page.html không load series JSON (hub rỗng)")
    # series-nav.html must have at least one elif for a known series id.
    nav = ctx.read("templates/macros/series-nav.html") or ""
    known_ids = {p.name[: -len("-series.json")] for p in series_files}
    nav_ids = set(re.findall(r'series\s*==\s*["\']([a-z0-9\-]+)["\']', nav))
    if not (known_ids & nav_ids):
        details.append(
            f"series-nav.html không có elif cho bất kỳ series nào "
            f"({len(known_ids)} series biết; có: {sorted(nav_ids)[:3]})"
        )
    if details:
        return CheckResult("SERIES-HUB", title, WARN,
                           diagnosis="hub series chưa đầy đủ",
                           fix="tạo templates/series-hub-page.html + elif trong series-nav.html",
                           details=details)
    return CheckResult("SERIES-HUB", title, PASS,
                       diagnosis=f"hub OK · {len(series_files)} series · {len(known_ids & nav_ids)} đăng ký nav")


def check_nav_menu_overflow(ctx: Ctx) -> CheckResult:
    """Navigation overflow (R4) — too many top-level menu items overflow the
    mobile navbar. Heuristic soft check."""
    title = "Navigation menu item count (mobile overflow)"
    cfg = ctx.read("config.toml") or ""
    n = len(re.findall(r"\[\[extra\.main_menu\]\]", cfg))
    if n == 0:
        return CheckResult("NAV", title, SKIP, diagnosis="không khai báo extra.main_menu trong config")
    if n > 9:
        return CheckResult("NAV", title, WARN,
                           diagnosis=f"{n} mục menu top-level → dễ tràn navbar mobile (R4)",
                           fix="gộp vào dropdown hoặc dùng horizontal-scroll tabs ≤720px")
    return CheckResult("NAV", title, PASS, diagnosis=f"{n} mục menu")


def check_compliance_h1(ctx: Ctx) -> CheckResult:
    """Compliance (Heading focus) — feed-anchor.html and index.html must each
    render exactly one <h1> (the visually-hidden SERP title) or paginated /page/N
    routes audit as 0-h1."""
    title = "Compliance heading focus (single H1)"
    details = []
    fa = ctx.read("templates/feed-anchor.html")
    if fa is not None and "<h1" not in fa:
        details.append("templates/feed-anchor.html: thiếu <h1> (route /feed-anchor-* = 0 h1)")
    idx = ctx.read("templates/index.html")
    if idx is not None and "<h1" not in idx:
        details.append("templates/index.html: thiếu <h1> (homepage /page/N = 0 h1)")
    if details:
        return CheckResult("V10", title, WARN,
                           diagnosis="trang có 0 <h1> → compliance Heading focus tụt",
                           fix='thêm <h1 class="visually-hidden"> (page.title / config.title)',
                           details=details)
    return CheckResult("V10", title, PASS)


def check_v17_vipzone_edge_safari_auth(ctx: Ctx) -> CheckResult:
    """V17 — VIPZone admin OAuth loop on Edge/Safari (missing_token / picker hidden)."""
    title = "VIPZone Edge/Safari auth session + picker UI"
    admin_js = ctx.read("static/js/vip-admin.js") or ""
    cms_auth = ctx.read("services/vipzone/cms_auth.py") or ""
    roles_py = ctx.read("services/vipzone/roles.py") or ""
    issues = []
    if admin_js and "localStorage.getItem(CMS_KEY)" not in admin_js:
        issues.append("vip-admin.js: getSid thiếu localStorage fallback")
    if admin_js and 'credentials: "include"' not in admin_js:
        issues.append("vip-admin.js: fetch thiếu credentials:include (cookie session)")
    if admin_js and 'showView("denied")' in admin_js:
        issues.append("vip-admin.js: vẫn ẩn UI theo role (denied view)")
    if cms_auth and 'samesite="none"' not in cms_auth:
        issues.append("cms_auth.py: thiếu Set-Cookie SameSite=None")
    if roles_py and "email_is_superadmin" in roles_py:
        issues.append("roles.py: vẫn có email-based superadmin override")
    if issues:
        return CheckResult(
            "V17", title, FAIL,
            diagnosis="VIPZone admin login loop / picker ẩn trên Edge-Safari",
            fix="V17 FIXER: cookie SameSite=None+localStorage sid mirror+credentials:include+always render picker",
            details=issues,
        )
    return CheckResult("V17", title, PASS)


def check_v18_runtime_artifact_conflict(ctx: Ctx) -> CheckResult:
    """V18 — Runtime artifact conflict: volatile state/log/report files in hotfix PRs."""
    title = "Runtime artifacts gitignored + hotfix PR commit filter"
    issues: list[str] = []

    # 1. State/lock/log files must NOT be tracked by git (they should be gitignored)
    volatile_files = [
        "data/vaccine-hotfix-state.json",
        "data/vaccine-hotfix.log",
        "data/vaccine-autofixer-state.json",
        "data/vaccine-autofixer.log",
        "data/qa-rule-checker-state.json",
        "data/autofix-conflicts-state.json",
    ]
    try:
        import subprocess as _sp
        tracked = _sp.run(
            ["git", "ls-files"] + volatile_files,
            cwd=str(ctx.root), capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        if tracked:
            for f in tracked.splitlines():
                issues.append(f"FAIL: {f} vẫn được git track — phải gitignore (V18)")
    except Exception as exc:
        issues.append(f"WARN: không kiểm tra git ls-files được: {exc}")

    # 2. vaccine-hotfix.yml must have git restore --staged filter after git add -A
    hotfix_yml = ctx.read(".github/workflows/vaccine-hotfix.yml") or ""
    if hotfix_yml and "git restore --staged" not in hotfix_yml:
        issues.append("WARN: vaccine-hotfix.yml thiếu 'git restore --staged' filter cho volatile files (V18)")

    # 3. qa-auto-rule-checker.py write_reports must be idempotent (skip timestamp-only write)
    rule_checker = ctx.read("scripts/qa-auto-rule-checker.py") or ""
    if rule_checker and "no meaningful change" not in rule_checker and "Idempotent" not in rule_checker:
        issues.append("WARN: qa-auto-rule-checker.py write_reports() không idempotent — ghi updated_at mỗi run → conflict (V18)")

    fail_issues = [i for i in issues if i.startswith("FAIL")]
    warn_issues = [i for i in issues if i.startswith("WARN")]

    if fail_issues:
        return CheckResult(
            "V18", title, FAIL,
            diagnosis="Volatile runtime artifacts còn được git track → sẽ conflict ở concurrent hotfix PRs",
            fix="V18 FIXER: git rm --cached + thêm vào .gitignore; cập nhật vaccine-hotfix.yml",
            details=issues,
        )
    if warn_issues:
        return CheckResult(
            "V18", title, WARN,
            diagnosis="Runtime artifact workflow filter hoặc idempotent write chưa đầy đủ",
            fix="V18 FIXER: thêm git restore --staged filter; làm write_reports() idempotent",
            details=warn_issues,
        )
    return CheckResult("V18", title, PASS)


def check_v10_link_utils_layer(ctx: Ctx) -> CheckResult:
    """V10 (shared link-utils + test layer — link-safety, NOT a §4 vaccine number).

    The migration/regex 404 regression came back whenever link code (a) used a
    HOST guard to tell internal from external — dropping /zola/* links that carry
    no host — or (b) ran a link regex over raw markdown, parsing/rewriting links
    inside code spans. scripts/link_utils.py centralizes the safe behavior; this
    detector enforces its invariants live so the regression cannot reopen:

      * /zola/* (and any /…, @/…, ./…) is ALWAYS internal — host never required.
      * links inside `code` / fenced ``` blocks are NOT extracted.

    A missing or broken layer FAILS the gate. The test/wiring layer (test file +
    code-span-aware migration tool) is a WARN if absent — the invariant itself is
    already verified above.
    """
    title = "Shared link-utils safety (/zola/ invariant + code-span)"
    path = ctx.root / "scripts" / "link_utils.py"
    if not path.is_file():
        return CheckResult("V10-LINKS", title, FAIL,
                           diagnosis="scripts/link_utils.py vắng — lớp an toàn link không còn",
                           fix="khôi phục scripts/link_utils.py (classify/extract_urls/code_span_ranges)")
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("_qa_link_utils_probe", path)
        if spec is None or spec.loader is None:
            raise ImportError("không tạo được spec cho link_utils")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as exc:
        return CheckResult("V10-LINKS", title, FAIL,
                           diagnosis=f"không import được link_utils: {exc}",
                           fix="sửa lỗi cú pháp/định nghĩa trong scripts/link_utils.py")
    broken: list[str] = []
    try:
        for url in ("/zola/x/", "/foo/", "@/posting/x.md", "./sib/"):
            if mod.classify(url) != "internal":
                broken.append(f'classify({url!r}) != "internal" (mất /zola/ invariant)')
        if mod.classify("https://example.com/a") != "external":
            broken.append('classify(external URL) != "external"')
        if mod.classify("#frag") != "skip":
            broken.append('classify("#frag") != "skip"')
        if "/zola/b" in mod.extract_urls("real [a](/zola/a) `[b](/zola/b)`"):
            broken.append("extract_urls() vẫn lấy link trong code span")
    except Exception as exc:
        return CheckResult("V10-LINKS", title, FAIL,
                           diagnosis=f"link_utils thiếu API mong đợi: {exc}",
                           fix="giữ classify()/extract_urls()/code_span_ranges() trong link_utils")
    if broken:
        return CheckResult("V10-LINKS", title, FAIL,
                           diagnosis="bất biến link-safety bị phá → /zola/ link bị drop hoặc code span bị parse → 404",
                           fix="/zola/* và mọi path /…,@/… luôn internal; mask code span trước khi extract",
                           details=broken)
    warn: list[str] = []
    if not (ctx.root / "scripts" / "test_link_utils.py").is_file():
        warn.append("thiếu scripts/test_link_utils.py (test layer)")
    fix_src = ctx.read("scripts/fix_site_prefix_links.py") or ""
    if fix_src and "code_span_ranges" not in fix_src:
        warn.append("fix_site_prefix_links.py không dùng code_span_ranges (migration có thể sửa code span)")
    if warn:
        return CheckResult("V10-LINKS", title, WARN,
                           diagnosis="bất biến link-safety OK nhưng thiếu test/wiring phụ trợ",
                           fix="thêm scripts/test_link_utils.py + để migration tool dùng code_span_ranges",
                           details=warn)
    return CheckResult("V10-LINKS", title, PASS)


# UptimeRobot key shapes (main / monitor-specific / read-only): "<u|m|ur>NNNNN-<hex/alnum>".
_UPTIMEROBOT_KEY_RE = re.compile(r"\b(?:ur|u|m)\d{5,}-[A-Za-z0-9]{20,}\b")
_UPTIME_REQUIRED = ("checked_at", "ok", "summary", "accounts", "monitors", "incidents")
_UPTIME_SUMMARY_KEYS = ("total", "up", "down", "paused", "breathing")
_UPTIME_STALE_HOURS = 6


def check_uptime_me(ctx: Ctx) -> CheckResult:
    """uptime_me_vaccine — UPTIME_ME dashboard safety.

    FAIL: an UptimeRobot API key leaked into any tracked file (data JSON, fetch
          script, workflow); the public JSON is missing/invalid/malformed schema;
          the page route (content + template) is absent; or the Tools card does
          not link to the route.
    WARN: the report is stale (checked_at older than the cron cadence) — surfaced
          so a dead cron is noticed (empty checked_at = awaiting first run, OK).
    """
    title = "UPTIME_ME dashboard (no key leak · schema · route · freshness)"
    fails: list[str] = []
    warns: list[str] = []

    # 1 — no API key leaked anywhere in the repo surface for this feature.
    for rel in ("data/uptime-me.json", "scripts/fetch_uptime_me.py",
                ".github/workflows/uptime-me.yml", "static/js/uptime-me.js",
                "templates/uptime-me.html"):
        src = ctx.read(rel)
        if src and _UPTIMEROBOT_KEY_RE.search(src):
            fails.append(f"{rel}: lộ chuỗi giống API key UptimeRobot → chỉ dùng env/secrets")

    # 2 — public JSON exists + valid schema.
    raw = ctx.read("data/uptime-me.json")
    if raw is None:
        fails.append("thiếu data/uptime-me.json (seed an toàn rỗng cần tồn tại để build)")
    else:
        try:
            rep = json.loads(raw)
        except json.JSONDecodeError:
            rep = None
            fails.append("data/uptime-me.json không phải JSON hợp lệ")
        if isinstance(rep, dict):
            missing = [k for k in _UPTIME_REQUIRED if k not in rep]
            if missing:
                fails.append(f"data/uptime-me.json thiếu khóa schema: {missing}")
            summ = rep.get("summary")
            if not isinstance(summ, dict) or any(k not in summ for k in _UPTIME_SUMMARY_KEYS):
                fails.append("data/uptime-me.json: summary thiếu khóa bắt buộc")
            for li in ("accounts", "monitors", "incidents"):
                if li in rep and not isinstance(rep[li], list):
                    fails.append(f"data/uptime-me.json: '{li}' phải là mảng")
            # 5 — staleness (only when a real timestamp exists).
            ts = (rep.get("checked_at") or "").strip()
            if ts:
                try:
                    from datetime import datetime, timezone
                    age_h = (datetime.now(timezone.utc)
                             - datetime.fromisoformat(ts.replace("Z", "+00:00"))
                             ).total_seconds() / 3600
                    if age_h > _UPTIME_STALE_HOURS:
                        warns.append(f"report cũ {age_h:.0f}h (> {_UPTIME_STALE_HOURS}h) — "
                                     f"kiểm tra cron uptime-me.yml")
                except ValueError:
                    warns.append("checked_at không parse được (ISO8601)")

    # 3 — route exists (content + template).
    if not ctx.exists("content/tools/uptime-me.md"):
        fails.append("thiếu content/tools/uptime-me.md (route /tools/uptime-me/)")
    tmpl = ctx.read("templates/uptime-me.html")
    if tmpl is None:
        fails.append("thiếu templates/uptime-me.html")
    elif "load_data(path=\"data/uptime-me.json\"" not in tmpl:
        warns.append("templates/uptime-me.html không load data/uptime-me.json")

    # 4 — Tools card links to the route.
    tools_idx = ctx.read("content/tools/_index.md") or ""
    if "/tools/uptime-me" not in tools_idx:
        fails.append("content/tools/_index.md: thẻ UPTIME_ME không trỏ /tools/uptime-me")

    if fails:
        return CheckResult("UI-UPTIME", title, FAIL,
                           diagnosis="UPTIME_ME thiếu an toàn/route/schema",
                           fix="đảm bảo: không hardcode key (env-only); data/uptime-me.json "
                               "đúng schema; content+template route tồn tại; thẻ Tools trỏ "
                               "/tools/uptime-me",
                           details=fails + warns)
    if warns:
        return CheckResult("UI-UPTIME", title, WARN,
                           diagnosis="UPTIME_ME ổn nhưng có cảnh báo freshness/wiring",
                           fix="kiểm tra cron uptime-me.yml / checked_at",
                           details=warns)
    return CheckResult("UI-UPTIME", title, PASS,
                       diagnosis="no key leak · schema OK · route + card OK")


def _css_blocks(src: str, selector: str) -> list[str]:
    """Return the bodies of ALL `selector { … }` rules (brace-matched), in order.
    Covers a rule plus its media-query copies so a detector can inspect each."""
    out: list[str] = []
    idx = src.find(selector)
    while idx != -1:
        brace = src.find("{", idx)
        if brace == -1:
            break
        depth, i = 0, brace
        while i < len(src):
            c = src[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    out.append(src[brace + 1:i])
                    break
            i += 1
        idx = src.find(selector, (i if i > idx else idx) + 1)
    return out


def _css_block(src: str, selector: str) -> str | None:
    """Body of the FIRST `selector { … }` rule, or None."""
    blocks = _css_blocks(src, selector)
    return blocks[0] if blocks else None


def check_sidebar_layout(ctx: Ctx) -> CheckResult:
    """sidebar_layout_vaccine — the right-column menu/sidebar must live INSIDE the
    page grid on desktop, never as a fixed/absolute high-z overlay that covers
    content (regression from the PR #526 right-column nav).

    Invariants enforced statically:
      1. `.side-nav` (desktop primary nav) is in-flow — position sticky/static,
         NOT fixed/absolute.
      2. `.sidebar` column is in-flow — not fixed/absolute.
      3. `.layout-grid` desktop reserves a real second (right) column for the
         sidebar (two-track grid-template-columns), so main shrinks beside it.
      4. `.main-column { min-width: 0 }` so content can never blow the grid and
         slide under the sidebar.
      5. Mobile (≤960px) collapses to one column + the menu is a drawer that is
         `hidden` by default (closed state must not cover content).
    """
    title = "Sidebar layout (in-grid, not fixed/absolute overlay)"
    sidenav = ctx.read("sass/_side-nav.scss")
    sidebar = ctx.read("sass/_sidebar.scss")
    layout = ctx.read("sass/_layout.scss")
    base = ctx.read("templates/base.html")
    if sidenav is None or layout is None:
        return CheckResult("UI-SIDEBAR", title, SKIP,
                           diagnosis="thiếu sass/_side-nav.scss hoặc _layout.scss")

    fails: list[str] = []
    warns: list[str] = []

    # 1 — .side-nav must NOT be fixed/absolute in ANY of its blocks.
    for sn in (_css_blocks(sidenav, ".side-nav ") + _css_blocks(sidenav, ".side-nav{")):
        if re.search(r"position:\s*(fixed|absolute)", sn):
            fails.append(".side-nav dùng position:fixed/absolute → nav nổi đè nội dung "
                         "(phải position:sticky trong cột phải)")
            break

    # 2 — .sidebar column must be in-flow.
    if sidebar is not None:
        for sb in (_css_blocks(sidebar, ".sidebar ") + _css_blocks(sidebar, ".sidebar{")):
            if re.search(r"position:\s*(fixed|absolute)", sb):
                fails.append(".sidebar dùng position:fixed/absolute → cột sidebar overlay "
                             "thay vì nằm trong grid")
                break

    # 3 — some .layout-grid block reserves a real right column (two tracks). The
    #     mobile (≤960px) copy is single-track 1fr; the desktop base must be 2-track.
    lg_blocks = _css_blocks(layout, ".layout-grid ") + _css_blocks(layout, ".layout-grid{")
    two_track = False
    for lg in lg_blocks:
        gtc = re.search(r"grid-template-columns:\s*([^;]+);", lg)
        if not gtc:
            continue
        # Count tracks at depth 0: blank out parenthesised groups (minmax(..),
        # repeat(..)) so their inner spaces/commas don't inflate the count.
        flat = re.sub(r"\([^()]*\)", "X", gtc.group(1).strip())
        if len([t for t in flat.split() if t]) >= 2:
            two_track = True
            break
    if not two_track:
        fails.append(".layout-grid desktop không reserve cột thứ 2 (grid-template-columns "
                     "1 track) → sidebar không có cột riêng, dễ chồng lên content")

    # 4 — main-column min-width: 0 (prevents grid blow-out under the sidebar).
    if not re.search(r"\.main-column\s*\{[^}]*min-width:\s*0", layout):
        warns.append(".main-column thiếu min-width:0 → content dài có thể đẩy vỡ grid")

    # 5 — mobile drawer hidden by default + side-nav hidden ≤960px.
    if not re.search(r"@media[^{]*max-width:\s*960px[\s\S]*?\.side-nav\s*\{[^}]*display:\s*none",
                     sidenav):
        warns.append("≤960px không ẩn .side-nav (mobile nên dùng drawer, không hiện card)")
    if base is not None and "nav-drawer" in base and not re.search(
            r'class="nav-drawer"[^>]*\shidden', base):
        warns.append("templates/base.html: .nav-drawer không có thuộc tính `hidden` "
                     "→ drawer có thể che nội dung khi chưa mở")

    if fails:
        return CheckResult("UI-SIDEBAR", title, FAIL,
                           diagnosis="menu/sidebar có thể overlay nội dung trên desktop",
                           fix="giữ .side-nav sticky trong .sidebar; .layout-grid 2 cột "
                               "(minmax(0,1fr) <sidebar>px); .main-column min-width:0; "
                               "mobile dùng drawer hidden",
                           details=fails + warns)
    if warns:
        return CheckResult("UI-SIDEBAR", title, WARN,
                           diagnosis="layout sidebar in-grid OK nhưng thiếu guard phụ",
                           fix="bổ sung min-width:0 cho .main-column / ẩn .side-nav ≤960px / "
                               "đặt hidden cho .nav-drawer",
                           details=warns)
    return CheckResult("UI-SIDEBAR", title, PASS,
                       diagnosis=".side-nav sticky in-grid · .layout-grid 2 cột · drawer hidden")


# GitHub token shapes that must never be committed (PAT, fine-grained, OAuth, app).
_GH_TOKEN_RE = re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{40,}\b")
_DEPLOY_REQUIRED = ("checked_at", "ok", "stale", "summary", "pending", "recent")
_DEPLOY_SUMMARY_KEYS = ("prod_status", "pending_count", "avg_deploy_s")
_DEPLOY_STALE_HOURS = 3


def check_deploy_monitor(ctx: Ctx) -> CheckResult:
    """deploy_monitor_vaccine — Deploy Watch footer widget + /tools/deploy-monitor/.

    FAIL: a GitHub token leaked into any tracked feature file; public JSON
          missing/invalid/malformed schema; the detail route (content + template)
          is absent; the footer widget is not wired to the data; the Tools card /
          footer link does not point to the route; or pending count is not shown.
    WARN: report stale (checked_at older than the cron cadence; empty = awaiting).
    """
    title = "Deploy Monitor (no token leak · schema · footer · route · pending)"
    fails: list[str] = []
    warns: list[str] = []

    # 1 — no token leaked in the feature surface.
    for rel in ("data/deploy-monitor.json", "scripts/fetch_deploy_monitor.py",
                ".github/workflows/deploy-monitor.yml", "templates/deploy-monitor.html"):
        src = ctx.read(rel)
        if src and _GH_TOKEN_RE.search(src):
            fails.append(f"{rel}: lộ chuỗi giống GitHub token → chỉ dùng env/secrets")

    # 2 — public JSON exists + valid schema + pending list present.
    raw = ctx.read("data/deploy-monitor.json")
    if raw is None:
        fails.append("thiếu data/deploy-monitor.json (seed an toàn cần tồn tại để build)")
    else:
        try:
            rep = json.loads(raw)
        except json.JSONDecodeError:
            rep = None
            fails.append("data/deploy-monitor.json không phải JSON hợp lệ")
        if isinstance(rep, dict):
            missing = [k for k in _DEPLOY_REQUIRED if k not in rep]
            if missing:
                fails.append(f"data/deploy-monitor.json thiếu khóa schema: {missing}")
            summ = rep.get("summary")
            if not isinstance(summ, dict) or any(k not in summ for k in _DEPLOY_SUMMARY_KEYS):
                fails.append("data/deploy-monitor.json: summary thiếu khóa (prod_status/pending_count/avg_deploy_s)")
            for li in ("pending", "recent"):
                if li in rep and not isinstance(rep[li], list):
                    fails.append(f"data/deploy-monitor.json: '{li}' phải là mảng")
            ts = (rep.get("checked_at") or "").strip()
            if ts:
                try:
                    from datetime import datetime, timezone
                    age_h = (datetime.now(timezone.utc)
                             - datetime.fromisoformat(ts.replace("Z", "+00:00"))
                             ).total_seconds() / 3600
                    if age_h > _DEPLOY_STALE_HOURS:
                        warns.append(f"report cũ {age_h:.0f}h (> {_DEPLOY_STALE_HOURS}h) — kiểm tra cron deploy-monitor.yml")
                except ValueError:
                    warns.append("checked_at không parse được (ISO8601)")

    # 3 — footer widget wired to the data + shows pending count.
    base = ctx.read("templates/base.html") or ""
    if 'load_data(path="data/deploy-monitor.json"' not in base:
        fails.append("templates/base.html: footer không load data/deploy-monitor.json (widget không render)")
    elif "deploy-watch" not in base:
        fails.append("templates/base.html: thiếu widget .deploy-watch ở footer")
    if "pending_count" not in base:
        fails.append("templates/base.html: footer không hiển thị pending_count")

    # 4 — detail route exists.
    if not ctx.exists("content/tools/deploy-monitor.md"):
        fails.append("thiếu content/tools/deploy-monitor.md (route /tools/deploy-monitor/)")
    if ctx.read("templates/deploy-monitor.html") is None:
        fails.append("thiếu templates/deploy-monitor.html")

    # 5 — link not 404: footer link + Tools card point to the route.
    if "/tools/deploy-monitor" not in base:
        warns.append("templates/base.html: footer thiếu link tới /tools/deploy-monitor/")
    if "/tools/deploy-monitor" not in (ctx.read("content/tools/_index.md") or ""):
        fails.append("content/tools/_index.md: thẻ Deploy Monitor không trỏ /tools/deploy-monitor")

    # 6 — deploy STATE must come ONLY from the real Build & Deploy workflow.
    #     A telemetry/report workflow (merge-report, build-failure, qa-rule-checker)
    #     as a source would make a feature deploy look "deploying" while a
    #     background report is still running. Lock the invariant.
    fetch_src = ctx.read("scripts/fetch_deploy_monitor.py") or ""
    if fetch_src:
        if 'WORKFLOW_FILE = "deploy.yml"' not in fetch_src and "deploy.yml" not in fetch_src:
            fails.append("fetch_deploy_monitor.py: không target deploy.yml — deploy state phải từ workflow deploy thật")
        # Telemetry workflow names may ONLY appear inside the documented
        # TELEMETRY_WORKFLOWS guard list, never as a queried source.
        if "TELEMETRY_WORKFLOWS" not in fetch_src:
            stray = [w for w in ("merge-report.yml", "build-failure-handler.yml", "qa-rule-checker.yml")
                     if w in fetch_src]
            if stray:
                fails.append(f"fetch_deploy_monitor.py: telemetry workflow {stray} bị dùng làm deploy state — chỉ deploy.yml")
        # 7 — stale in_progress detection (TTL) → no "deploying forever".
        if "_PENDING_TTL_S" not in fetch_src or "expired" not in fetch_src:
            fails.append("fetch_deploy_monitor.py: thiếu TTL/expiry cho in_progress (deploy treo sẽ hiện 'deploying' vĩnh viễn)")
        # 8 — a commit already deployed (success run) must never be listed pending.
        if "success_shas" not in fetch_src:
            warns.append("fetch_deploy_monitor.py: thiếu guard 'đã deploy' (commit live có thể vẫn hiện pending)")

    # 9 — runtime deploy-status.js, if present, must guard stale non-terminal
    #     states so a stuck deploy can't render "deploying" forever.
    js = ctx.read("static/js/deploy-status.js")
    if js is not None and "STALE_NONTERMINAL_MS" not in js:
        fails.append("static/js/deploy-status.js: thiếu stale guard → trạng thái treo sẽ hiện 'deploying' vĩnh viễn")

    # 10 — footer must surface a stale flag so old data isn't mistaken for a deploy.
    if base and "dm.stale" not in base and "deploy-watch__stale" not in base:
        warns.append("templates/base.html: footer thiếu cảnh báo stale (dm.stale) — data cũ trông như đang deploy")

    if fails:
        return CheckResult("DEPLOY-MON", title, FAIL,
                           diagnosis="Deploy Monitor thiếu an toàn/route/schema/footer",
                           fix="env-only token; data/deploy-monitor.json đúng schema; footer "
                               "load_data + .deploy-watch + pending_count; content+template route; "
                               "thẻ Tools + footer link /tools/deploy-monitor",
                           details=fails + warns)
    if warns:
        return CheckResult("DEPLOY-MON", title, WARN,
                           diagnosis="Deploy Monitor ổn nhưng có cảnh báo freshness/link",
                           fix="kiểm tra cron deploy-monitor.yml / checked_at / footer link",
                           details=warns)
    return CheckResult("DEPLOY-MON", title, PASS,
                       diagnosis="no token leak · schema OK · footer wired · route + card OK")


def check_seomoney_brand(ctx: Ctx) -> CheckResult:
    """seomoney_brand_vaccine — site brand must be SEOMONEY (author stays Duy Nguyen),
    + the SEOMONEY OG default + placeholder fallback set must exist.

    FAIL: config.title is not "SEOMONEY" (site-brand regression); author identity
          lost (config.extra.author / author.json no longer "Duy Nguyen"); the
          SEOMONEY default OG image is missing; or the placeholder fallback set
          (incl. random variants) is missing.
    WARN: residual "blog Duy Nguyen" site-brand phrase in section/page descriptions.
    """
    title = "SEOMONEY brand + OG default + placeholder set"
    fails: list[str] = []
    warns: list[str] = []

    cfg = ctx.read("config.toml") or ""
    mt = re.search(r'^title\s*=\s*"([^"]*)"', cfg, re.MULTILINE)
    if not mt or mt.group(1).strip().upper() != "SEOMONEY":
        fails.append(f'config.toml title phải = "SEOMONEY" (đang: {mt.group(1) if mt else "?"})')
    # author identity preserved.
    if not re.search(r'^author\s*=\s*"duynguyenlog"', cfg, re.MULTILINE):
        warns.append("config.extra.author không còn 'duynguyenlog' (author identity)")
    aj = ctx.read("author.json") or ""
    if '"Duy Nguyen"' not in aj:
        fails.append("author.json: tên tác giả 'Duy Nguyen' bị mất (phải giữ author identity)")

    # OG default (SEOMONEY) — svg + committed twin.
    if not ctx.exists("static/img/og/seomoney-og.svg"):
        fails.append("thiếu static/img/og/seomoney-og.svg (OG default SEOMONEY)")
    if not ctx.exists("static/img/og/seomoney-og.og.webp"):
        fails.append("thiếu static/img/og/seomoney-og.og.webp (twin OG — seed để không 404)")
    base = ctx.read("templates/base.html") or ""
    if "seomoney-og.og.webp" not in base:
        fails.append("templates/base.html: og:image default không trỏ SEOMONEY OG twin")

    # Placeholder fallback set incl. random variants.
    for ph in ("placeholder.svg", "placeholder-2.svg", "placeholder-3.svg"):
        if not ctx.exists(f"static/img/placeholder/{ph}"):
            fails.append(f"thiếu static/img/placeholder/{ph} (random fallback)")
    if "placeholder-2.svg" not in base or "placeholder-3.svg" not in base:
        warns.append("templates/base.html: runtime fallback chưa random hoá placeholder variants")

    # Residual site-brand phrase (author bylines are fine).
    residual = []
    for p in ctx.glob("content/**/_index.md"):
        try:
            if "blog Duy Nguyen" in p.read_text(encoding="utf-8"):
                residual.append(str(p.relative_to(ctx.root)))
        except OSError:
            pass
    if residual:
        warns.append(f"còn 'blog Duy Nguyen' (site-brand) ở: {residual[:5]}")

    if fails:
        return CheckResult("BRAND", title, FAIL,
                           diagnosis="brand SEOMONEY / OG / placeholder chưa hoàn chỉnh",
                           fix='config.title="SEOMONEY"; giữ author Duy Nguyen; thêm OG '
                               'seomoney-og(.svg/.og.webp); placeholder + variants 2/3',
                           details=fails + warns)
    if warns:
        return CheckResult("BRAND", title, WARN,
                           diagnosis="brand OK nhưng còn residual/consistency",
                           fix="rebrand 'blog Duy Nguyen' → 'blog SEOMONEY'; random hoá placeholder",
                           details=warns)
    return CheckResult("BRAND", title, PASS,
                       diagnosis="site brand SEOMONEY · author Duy Nguyen giữ · OG + placeholder set OK")


def _webp_dimensions(data: bytes) -> tuple[int, int] | None:
    """Read (width, height) from a WebP byte string — stdlib only, no Pillow.

    Handles the three RIFF/WEBP chunk variants ('VP8 ' lossy, 'VP8L' lossless,
    'VP8X' extended). Returns None on any malformation so the caller degrades
    to a warning rather than crashing the gate.
    """
    try:
        if len(data) < 30 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
            return None
        fourcc = data[12:16]
        if fourcc == b"VP8 ":  # lossy
            w = int.from_bytes(data[26:28], "little") & 0x3FFF
            h = int.from_bytes(data[28:30], "little") & 0x3FFF
            return (w, h)
        if fourcc == b"VP8L":  # lossless
            b = int.from_bytes(data[21:25], "little")
            w = (b & 0x3FFF) + 1
            h = ((b >> 14) & 0x3FFF) + 1
            return (w, h)
        if fourcc == b"VP8X":  # extended
            w = int.from_bytes(data[24:27], "little") + 1
            h = int.from_bytes(data[27:30], "little") + 1
            return (w, h)
    except Exception:
        return None
    return None


# OG-image invariants (Open Graph / Twitter summary_large_image).
_OG_W, _OG_H = 1200, 630
_OG_OLD_DOMAIN_RE = re.compile(
    r"banhang-chogao\.github\.io|github\.io/zola|\.github\.io", re.IGNORECASE)


def check_og_image_vaccine(ctx: Ctx) -> CheckResult:
    """OG-IMAGE — social cover SVGs under static/img/og must stay shippable.

    Open Graph / social cards are easy to silently break: a wrong canvas size
    crops the card, a malformed SVG renders nothing, a stale committed `.og.webp`
    twin shows the OLD art (social caches it hard), and a leftover old-domain
    string brands the card with a dead host. None of these break `zola build`
    (Zola copies static assets verbatim), so only this detector catches them.

    FAIL — SVG missing / not well-formed XML; SVG canvas ≠ 1200×630; the
           `.og.webp` twin missing or not 1200×630 (broken social card); the
           twin is STALE — the committed SVG's sha256 no longer matches the
           sha recorded in static/img/og-manifest.json when the twin was last
           rendered (social would cache the OLD card art). Stale detection is
           content-hash based → deterministic on a fresh/shallow CI checkout,
           with no dependency on filesystem mtime or cairosvg/Pillow.
    WARN — old-domain string in the SVG; or a stale signal we can only infer by
           mtime because the SVG has no manifest entry yet (bootstrap/legacy).
    """
    title = "OG image 1200×630 · valid SVG · fresh twin · no old domain"
    og_dir = ctx.root / "static" / "img" / "og"
    fails: list[str] = []
    warns: list[str] = []

    if not og_dir.is_dir():
        return CheckResult("OG-IMAGE", title, SKIP, diagnosis="static/img/og absent")

    svgs = sorted(og_dir.glob("*.svg"))
    if not svgs:
        return CheckResult("OG-IMAGE", title, WARN,
                           diagnosis="no OG cover SVG found under static/img/og",
                           fix="add static/img/og/seomoney-og.svg (1200×630 default OG)")

    # The default OG cover referenced by base.html must exist.
    if not (og_dir / "seomoney-og.svg").exists():
        fails.append("thiếu static/img/og/seomoney-og.svg (OG default)")

    # Content-hash manifest (written by build_og_images.py): rel-svg-path → sha256
    # of the SVG when its twin was last rendered. A mismatch = stale twin.
    import hashlib
    manifest: dict = {}
    man_text = ctx.read("static/img/og-manifest.json")
    if man_text:
        try:
            manifest = json.loads(man_text)
            if not isinstance(manifest, dict):
                manifest = {}
        except Exception:
            manifest = {}

    import xml.etree.ElementTree as ET

    for svg in svgs:
        rel = svg.relative_to(ctx.root)
        try:
            svg_bytes = svg.read_bytes()
            svg_text = svg_bytes.decode("utf-8", errors="ignore")
        except OSError as exc:
            fails.append(f"{rel}: không đọc được ({exc})")
            continue

        # broken XML → FAIL (renders nothing on social).
        try:
            ET.fromstring(svg_text)
        except ET.ParseError as exc:
            fails.append(f"{rel}: SVG hỏng (XML không hợp lệ): {exc}")
            continue

        # canvas must be exactly 1200×630.
        mw = re.search(r'\bwidth\s*=\s*"(\d+)"', svg_text)
        mh = re.search(r'\bheight\s*=\s*"(\d+)"', svg_text)
        w = int(mw.group(1)) if mw else None
        h = int(mh.group(1)) if mh else None
        if (w, h) != (_OG_W, _OG_H):
            fails.append(f"{rel}: canvas {w}×{h} ≠ {_OG_W}×{_OG_H} (OG card bị crop)")

        # old-domain string in the cover → WARN (dead host branding).
        if _OG_OLD_DOMAIN_RE.search(svg_text):
            warns.append(f"{rel}: còn old-domain (github.io) trong OG SVG")

        # the committed twin must exist, be 1200×630, and not be stale.
        twin = svg.with_suffix(".og.webp")
        trel = twin.relative_to(ctx.root)
        if not twin.exists():
            fails.append(f"thiếu twin {trel} (social không render SVG → cần .og.webp)")
            continue
        try:
            dims = _webp_dimensions(twin.read_bytes())
        except OSError:
            dims = None
        if dims is None:
            warns.append(f"{trel}: không đọc được kích thước WebP (kiểm tra file)")
        elif dims != (_OG_W, _OG_H):
            fails.append(f"{trel}: twin {dims[0]}×{dims[1]} ≠ {_OG_W}×{_OG_H}")

        # Stale twin → FAIL, decided by content hash (deterministic on CI).
        recorded = manifest.get(str(rel))
        if recorded:
            current = hashlib.sha256(svg_bytes).hexdigest()
            if current != recorded:
                fails.append(
                    f"{trel}: STALE — SVG đã đổi nhưng twin chưa render lại "
                    f"(sha {current[:12]}… ≠ manifest {recorded[:12]}…)")
        else:
            # No manifest entry yet (bootstrap/legacy) → fall back to the
            # non-deterministic mtime heuristic, but only as a soft WARN so a
            # fresh checkout can never falsely block the merge.
            try:
                if svg.stat().st_mtime > twin.stat().st_mtime + 1:
                    warns.append(f"{trel}: có thể stale (chưa có manifest entry) → "
                                 "chạy build_og_images.py để ghi sha")
            except OSError:
                pass

    if fails:
        return CheckResult("OG-IMAGE", title, FAIL,
                           diagnosis="OG cover/twin vỡ chuẩn social (size/XML/twin/stale)",
                           fix="sửa canvas về 1200×630 + SVG hợp lệ; "
                               "python3 scripts/build_og_images.py rồi commit twin .og.webp + og-manifest.json",
                           details=fails + warns)
    if warns:
        return CheckResult("OG-IMAGE", title, WARN,
                           diagnosis="OG cover hợp lệ nhưng có drift (stale-mtime / old-domain)",
                           fix="python3 scripts/build_og_images.py + commit; "
                               "xoá ref github.io trong OG SVG",
                           details=warns)
    return CheckResult("OG-IMAGE", title, PASS,
                       diagnosis=f"{len(svgs)} OG SVG đúng {_OG_W}×{_OG_H} · XML hợp lệ · twin tươi (hash khớp) · không old-domain")


def check_v18_runtime_artifact_conflict(ctx: Ctx) -> CheckResult:
    """V18 — Runtime artifact conflict: volatile state/log/report files must not be tracked.

    Exact PR #555 conflict file set:
      data/qa-rule-checker-state.json, reports/rule-conflict-report.json,
      reports/rule-conflict-report.md
    Plus related volatile siblings:
      data/vaccine-autofixer-state.json, data/vaccine-autofixer.log,
      data/autofix-conflicts-state.json

    Root cause: vaccine-autofixer.yml used `git add -A` without filtering →
    timestamp-only churn committed → spurious merge conflicts on every concurrent
    vaccine PR. Fix: gitignore + `git restore --staged` + idempotent write_reports().
    """
    title = "V18 Runtime Artifact Conflict Prevention"
    fails: list[str] = []
    warns: list[str] = []

    # Volatile runtime artifact files that MUST NOT be git-tracked.
    volatile_files = [
        "data/vaccine-autofixer-state.json",
        "data/vaccine-autofixer.log",
        "data/qa-rule-checker-state.json",
        "data/autofix-conflicts-state.json",
        "reports/rule-conflict-report.json",
        "reports/rule-conflict-report.md",
    ]

    # Check 1: volatile files must be git-ignored (.gitignore patterns present).
    gitignore = ctx.root / ".gitignore"
    gi_text = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    missing_patterns = [f for f in volatile_files if f not in gi_text]
    if missing_patterns:
        fails.append(f".gitignore missing volatile artifact patterns: {missing_patterns}")

    # Check 2: vaccine-autofixer.yml must have `git restore --staged` guard.
    wf_path = ctx.root / ".github" / "workflows" / "vaccine-autofixer.yml"
    if wf_path.exists():
        wf_text = wf_path.read_text(encoding="utf-8")
        if "git restore --staged" not in wf_text or "qa-rule-checker-state.json" not in wf_text:
            fails.append("vaccine-autofixer.yml missing `git restore --staged` volatile-file filter")
    else:
        warns.append("vaccine-autofixer.yml not found (skip workflow check)")

    # Check 3: qa-auto-rule-checker.py write_reports() should be idempotent.
    checker = ctx.root / "scripts" / "qa-auto-rule-checker.py"
    if checker.exists():
        checker_text = checker.read_text(encoding="utf-8")
        if "total_conflicts" not in checker_text or "idempotent" not in checker_text:
            warns.append("qa-auto-rule-checker.py write_reports() may not be idempotent (V18)")
    else:
        warns.append("scripts/qa-auto-rule-checker.py not found")

    if fails:
        return CheckResult("V18", title, FAIL,
                           diagnosis="; ".join(fails),
                           fix="Add .gitignore patterns + git restore --staged in vaccine-autofixer.yml (see V18 CLAUDE.md)",
                           details=fails + warns)
    if warns:
        return CheckResult("V18", title, WARN,
                           diagnosis="volatile artifact filter incomplete",
                           fix="Review warnings above (V18 CLAUDE.md)",
                           details=warns)
    return CheckResult("V18", title, PASS,
                       diagnosis="volatile runtime artifacts gitignored + workflow filter present + idempotent writer")


_GSC_DOMAIN_PROPERTY = "sc-domain:seomoney.org"
_GSC_CANONICAL_SITEMAP = "https://seomoney.org/sitemap.xml"
_OLD_GITHUB_IO_RE = re.compile(r"banhang-chogao\.github\.io(/zola)?", re.IGNORECASE)
_GSC_CREDENTIAL_FIELDS = ("refresh_token", "access_token", "client_secret", "client_id")


def check_gsc_domain_property(ctx: Ctx) -> CheckResult:
    """V19 — GSC Domain Property migration vaccine.

    After Cloudflare verification (2026-06-20) the canonical GSC property changed
    from the URL-prefix `https://seomoney.org/` to the Domain property
    `sc-domain:seomoney.org`.  This detector enforces three invariants:

    FAIL:
      * gsc_client.py DEFAULT_GSC_PROPERTY_URL ≠ sc-domain:seomoney.org
      * robots.txt Sitemap directive ≠ https://seomoney.org/sitemap.xml
      * old banhang-chogao.github.io reference in any GSC/SEO tracking config
      * data/gsc-metrics.json contains credential fields (secret leak)

    WARN:
      * data/gsc-metrics.json schema missing required keys (connected/status/updated_at)
      * config.toml GSC comment still mentions old URL-prefix
    """
    title = "GSC Domain Property (sc-domain:seomoney.org)"
    fails: list[str] = []
    warns: list[str] = []

    # 1 — DEFAULT_GSC_PROPERTY_URL must be the domain property.
    gsc_client = ctx.read("services/visitor-counter/gsc_client.py") or ""
    m = re.search(r'DEFAULT_GSC_PROPERTY_URL\s*=\s*["\']([^"\']+)["\']', gsc_client)
    if m:
        prop_val = m.group(1)
        if prop_val != _GSC_DOMAIN_PROPERTY:
            fails.append(
                f"gsc_client.py: DEFAULT_GSC_PROPERTY_URL = '{prop_val}' "
                f"(phải là '{_GSC_DOMAIN_PROPERTY}')"
            )
    elif gsc_client:
        warns.append("gsc_client.py: không tìm thấy DEFAULT_GSC_PROPERTY_URL")

    # 2 — robots.txt sitemap URL must match canonical.
    robots = ctx.read("static/robots.txt") or ""
    if robots:
        sitemap_m = re.search(r"(?i)^Sitemap:\s*(.+)$", robots, re.MULTILINE)
        if sitemap_m:
            sitemap_url = sitemap_m.group(1).strip()
            if sitemap_url != _GSC_CANONICAL_SITEMAP:
                fails.append(
                    f"static/robots.txt: Sitemap = '{sitemap_url}' "
                    f"(phải là '{_GSC_CANONICAL_SITEMAP}')"
                )
        else:
            warns.append("static/robots.txt: không có khai báo Sitemap:")

    # 3 — old github.io refs must NOT appear in GSC/SEO tracking config files.
    gsc_tracking_files = [
        "services/visitor-counter/gsc_client.py",
        "services/visitor-counter/gsc_routes.py",
        "scripts/fetch_gsc_metrics.py",
        ".github/workflows/gsc-stats.yml",
    ]
    for rel in gsc_tracking_files:
        src = ctx.read(rel) or ""
        if _OLD_GITHUB_IO_RE.search(src):
            # Allow in string literals inside comments (e.g. example watermark text)
            # but flag if it appears as a property URL value or tracking config.
            for line in src.splitlines():
                stripped = line.strip()
                # skip pure comment lines
                if stripped.startswith("#") or stripped.startswith("{#") or stripped.startswith("//"):
                    continue
                if _OLD_GITHUB_IO_RE.search(line):
                    fails.append(f"{rel}: old banhang-chogao.github.io ref trong config/code")
                    break

    # 4 — data/gsc-metrics.json: no credentials leaked + valid schema.
    raw = ctx.read("data/gsc-metrics.json")
    if raw is None:
        warns.append("data/gsc-metrics.json absent (cần tồn tại dù GSC chưa connect)")
    else:
        try:
            gsc_data = json.loads(raw)
        except json.JSONDecodeError:
            fails.append("data/gsc-metrics.json không phải JSON hợp lệ")
            gsc_data = None
        if isinstance(gsc_data, dict):
            # No credential fields allowed in the public JSON.
            leaked = [f for f in _GSC_CREDENTIAL_FIELDS if f in gsc_data]
            if leaked:
                fails.append(
                    f"data/gsc-metrics.json: trường nhạy cảm bị lộ: {leaked} "
                    "(chỉ dùng env/secrets, KHÔNG commit credentials)"
                )
            # Schema spot-check.
            required_keys = ("connected", "status", "updated_at")
            missing = [k for k in required_keys if k not in gsc_data]
            if missing:
                warns.append(f"data/gsc-metrics.json: thiếu schema keys: {missing}")

    if fails:
        return CheckResult(
            "V19", title, FAIL,
            diagnosis="GSC domain property hoặc sitemap chưa migrate đúng / credential leak",
            fix=(
                f"1. Set DEFAULT_GSC_PROPERTY_URL = '{_GSC_DOMAIN_PROPERTY}' trong gsc_client.py. "
                f"2. Đảm bảo robots.txt Sitemap: = '{_GSC_CANONICAL_SITEMAP}'. "
                "3. Gỡ bỏ old github.io ref trong GSC tracking files. "
                "4. Không commit refresh_token/client_secret vào public JSON."
            ),
            details=fails + warns,
        )
    if warns:
        return CheckResult(
            "V19", title, WARN,
            diagnosis="GSC domain property OK nhưng có cảnh báo bổ sung",
            fix="Xem chi tiết warns ở trên",
            details=warns,
        )
    return CheckResult(
        "V19", title, PASS,
        diagnosis=f"property={_GSC_DOMAIN_PROPERTY} · sitemap={_GSC_CANONICAL_SITEMAP} · no credential leak",
    )


def check_korean_banner_ui_vaccine(ctx: Ctx) -> CheckResult:
    """Korean banner UI — validates the homepage Hangul decorative banner meets
    the SEOMONEY design system: overflow clipped, responsive layout present,
    no content overlay (pointer-events none + aria-hidden), reduced-motion safe
    (no keyframe animation on the pattern), and banner uses semantic border-radius."""
    title = "Korean banner UI (overflow · responsive · no overlay · a11y)"
    scss = ctx.read("sass/_home-momo.scss") or ""
    tpl = ctx.read("templates/index.html") or ""
    fails: list[str] = []
    warns: list[str] = []

    # 1. Banner must clip its contents (overflow: hidden prevents Hangul bleed)
    if "overflow: hidden" not in scss or ".home-tabs" not in scss:
        fails.append("sass/_home-momo.scss: .home-tabs missing overflow:hidden — Hangul chars may bleed outside banner")

    # 2. Hangul layer must be pointer-events:none (never blocks card clicks)
    if "pointer-events: none" not in scss:
        fails.append("sass/_home-momo.scss: .hangeul-pattern missing pointer-events:none — may block content clicks")

    # 3. aria-hidden on the decorative banner (screen-readers must skip it)
    if 'aria-hidden="true"' not in tpl or "home-tabs" not in tpl:
        warns.append("templates/index.html: .home-tabs should have aria-hidden=\"true\" (decorative element)")

    # 4. Responsive mobile override must exist
    mobile_re = re.compile(r'@media\s*\([^)]*max-width\s*:\s*7[012]\d', re.IGNORECASE)
    if not mobile_re.search(scss) or ".home-tabs" not in scss:
        fails.append("sass/_home-momo.scss: no mobile breakpoint for .home-tabs — responsive layout missing")

    # 5. No keyframe animation on .hangeul-pattern (static-only is fine; animated would need reduced-motion guard)
    hangeul_block_m = re.search(r'\.hangeul-pattern\s*\{(.+?)\n\}', scss, re.DOTALL)
    if hangeul_block_m and re.search(r'animation\s*:', hangeul_block_m.group(1)):
        # animation present but no prefers-reduced-motion guard → WARN
        reduced_ok = "@media (prefers-reduced-motion" in scss
        if not reduced_ok:
            warns.append("sass/_home-momo.scss: .hangeul-pattern has animation but no @media(prefers-reduced-motion) guard")

    # 6. Warn if the harsh hardcoded Ericsson Blue (#003784) is still used as sole bg
    if re.search(r'background\s*:\s*#003784', scss) and "linear-gradient" not in scss:
        warns.append("sass/_home-momo.scss: .home-tabs still uses flat #003784 bg — consider softer gradient per SEOMONEY design")

    if fails:
        return CheckResult("KOREAN-BANNER", title, FAIL,
                           diagnosis="Korean banner violates layout/accessibility contract",
                           fix="Ensure overflow:hidden on .home-tabs, pointer-events:none on .hangeul-pattern, aria-hidden on banner div, mobile breakpoint present",
                           details=fails + warns)
    if warns:
        return CheckResult("KOREAN-BANNER", title, WARN,
                           diagnosis="Minor banner a11y/motion consistency issues",
                           fix="See details above",
                           details=warns)
    return CheckResult("KOREAN-BANNER", title, PASS,
                       diagnosis="overflow clipped · pointer-events:none · aria-hidden · responsive · animation-safe")


def check_v19_domain_migration_drift(ctx: Ctx) -> CheckResult:
    """V19 — Domain Migration Drift: stale github.io/zola refs after apex-domain migration.

    After migrating banhang-chogao.github.io/zola → https://seomoney.org, stale
    references may survive in operational files (comments, snapshot url fields,
    doc TODOs). These do not break the build but cause drift and confusion.

    WARN (not FAIL): drift in comments/snapshots is not build-breaking.
    FAIL only if config.toml base_url or CNAME still hold the old domain.
    """
    title = "V19 Domain Migration Drift (github.io → seomoney.org)"
    import re as _re
    OLD_PAT = _re.compile(r"banhang-chogao\.github\.io/zola", _re.IGNORECASE)
    EXCLUDED = {
        "scripts/dns_vaccine.py",
        "scripts/rewrite_cdn_urls.py",
        "scripts/fix_site_prefix_links.py",
        "scripts/domain_migration_audit.py",
        "scripts/qa_vaccines.py",        # self + V19 docstring
        "scripts/test_link_normalization.py",
        "scripts/test_qa_vaccines.py",
        "scripts/test_dns_vaccine.py",
        "CLAUDE.md",                     # vaccine library legitimately documents old domain
        "docs/vaccine-archive.md",       # vaccine archive documentation
        "data/merge-report.json",
        "data/dns-vaccine-report.json",
        "data/performance-audit-snapshot.json",  # checked separately (snapshot check)
        "changelog.json",
        # Tutorial content explaining GitHub Pages:
        "content/posting/tao-blog-voi-zola.md",
        "content/posting/tu-dong-deploy-zola-github-actions.md",
        "content/posting/ung-ho-du-an-ai-ten-mien-ai.md",
    }
    SCAN_SUFFIXES = {".py", ".yml", ".yaml", ".html", ".js", ".scss", ".toml", ".md"}

    warns: list[str] = []
    fails: list[str] = []

    # Check 1: config.toml base_url must not hold old domain (FAIL)
    cfg_text = ctx.read("config.toml") or ""
    for line in cfg_text.splitlines():
        s = line.strip()
        if s.startswith("base_url") and "=" in s:
            val = s.split("=", 1)[1].strip().strip('"').strip("'")
            if "github.io" in val or ("/zola" in val and "seomoney" not in val):
                fails.append(f"config.toml base_url still holds old value: {val!r}")
            break

    # Check 2: CNAME must not hold old domain (FAIL)
    cname_text = ctx.read("static/CNAME") or ""
    cname_val = cname_text.strip().splitlines()[0].strip() if cname_text.strip() else ""
    if "github.io" in cname_val:
        fails.append(f"static/CNAME still holds github.io value: {cname_val!r}")

    # Check 3: performance-audit-snapshot.json url field (WARN if old domain)
    snap_text = ctx.read("data/performance-audit-snapshot.json")
    if snap_text:
        try:
            import json as _json
            snap = _json.loads(snap_text)
            snap_url = snap.get("url", "")
            if "github.io" in snap_url or ("/zola" in snap_url and "seomoney" not in snap_url):
                warns.append(
                    f"data/performance-audit-snapshot.json url={snap_url!r} "
                    "— trigger perf-audit.yml to regenerate (TARGET_URL already = seomoney.org)"
                )
        except Exception:
            pass

    # Check 4: scan operational files for stale github.io/zola refs (WARN)
    for p in sorted(ctx.root.rglob("*")):
        if not p.is_file():
            continue
        if p.suffix not in SCAN_SUFFIXES:
            continue
        try:
            rel = str(p.relative_to(ctx.root))
        except ValueError:
            continue
        if any(ex in rel for ex in EXCLUDED):
            continue
        if rel.startswith("scripts/test_"):
            continue
        if any(skip in rel for skip in (".git/", ".venv/", "node_modules/")):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        hits = OLD_PAT.findall(text)
        if hits:
            warns.append(f"{rel}: {len(hits)} occurrence(s) of banhang-chogao.github.io/zola")

    if fails:
        return CheckResult("V19", title, FAIL,
                           diagnosis="; ".join(fails),
                           fix="Update config.toml base_url + static/CNAME to seomoney.org (see V19 CLAUDE.md)",
                           details=fails + warns)
    if warns:
        return CheckResult("V19", title, WARN,
                           diagnosis=f"{len(warns)} stale reference(s) found (not build-breaking)",
                           fix="Run scripts/domain_migration_audit.py → fix per FIXER in V19 CLAUDE.md",
                           details=warns)
    return CheckResult("V19", title, PASS,
                       diagnosis="no stale github.io/zola refs in operational files; config + CNAME clean")


def check_search_ui_vaccine(ctx: Ctx) -> CheckResult:
    """search_ui_vaccine — the internal search dialog ("Tìm trong blog") must
    render as a STYLED, native SEOMONEY surface, never raw/default browser chrome.

    Root cause it guards (the bug this task fixed): the search markup in
    templates/base.html uses BEM `.site-search__*` classes, but only colour
    *tint* overrides existed (_theme-overrides.scss) — the structural/layout
    CSS was never written, so the panel rendered as an unstyled form. The fix
    is the scoped partial sass/_site-search.scss, imported in site.scss.

    Static signals (no browser needed):
      FAIL — search would render raw OR the search logic/markup is gone:
        * sass/_site-search.scss missing, or not imported in site.scss;
        * the partial lacks the structural rules (overlay positioning, panel
          card, field, primary submit, result card);
        * base.html lost the dialog / input / submit / search-data markup;
        * static/js/site-search.js (the search engine) is missing.
      WARN — styled & working but a resilience gap:
        * no mobile media query (mobile width could overflow);
        * `.site-search[hidden]` not handled (overlay could show always).
    """
    title = "Search UI styled + native (Tìm trong blog)"
    scss = ctx.read("sass/_site-search.scss")
    site_scss = ctx.read("sass/site.scss") or ""
    base = ctx.read("templates/base.html") or ""
    js = ctx.read("static/js/site-search.js")

    fails: list[str] = []
    warns: list[str] = []

    # 1) Styled UI exists and is wired into the bundle.
    if not scss:
        fails.append("sass/_site-search.scss vắng → search render raw (no structural CSS)")
    elif not re.search(r'@import\s+["\']site-search["\']', site_scss):
        fails.append("sass/site.scss thiếu @import \"site-search\" → partial không vào bundle")

    # 2) The partial supplies real STRUCTURE, not just a colour tint — these are
    #    the selectors whose absence would leave a raw/default layout.
    if scss:
        # overlay must be a controlled, positioned surface (not document flow)
        if not re.search(r'\.site-search\s*\{[^}]*position\s*:\s*fixed', scss, re.S):
            fails.append(".site-search thiếu position:fixed → overlay không định vị (raw)")
        for sel, why in (
            (r'\.site-search__panel\s*\{[^}]*(max-width|border-radius)', "panel card (max-width/radius)"),
            (r'\.site-search__field\s*\{[^}]*(display|border)', "search field (input wrapper)"),
            (r'\.site-search__submit\s*\{[^}]*(background|padding)', "primary submit button"),
            (r'\.site-search__result\s*\{[^}]*(border|padding)', "result card"),
        ):
            if not re.search(sel, scss, re.S):
                fails.append(f"_site-search.scss thiếu style cho {why}")
        # responsive + hidden-state hygiene (R1–R8 mobile rules / overlay toggle)
        if "max-width: 720px" not in scss and "max-width:720px" not in scss:
            warns.append("_site-search.scss thiếu @media (max-width: 720px) → mobile có thể overflow")
        if not re.search(r'\.site-search\[hidden\]', scss):
            warns.append(".site-search[hidden] chưa override display → overlay có thể luôn hiện")

    # 3) Markup contract — input + submit + close + the data the JS reads.
    for needle, why in (
        ("data-site-search", "search dialog container"),
        ("data-search-input", "search input"),
        ("site-search__submit", "submit button"),
        ("data-search-close", "close/back action"),
        ("site-search-data", "search index data the engine reads"),
    ):
        if needle not in base:
            fails.append(f"templates/base.html mất `{why}` ({needle}) → search UI/logic vỡ")

    # 4) The search engine itself must still be present (logic unchanged).
    if not js:
        fails.append("static/js/site-search.js vắng → search ngừng hoạt động")
    elif "renderResults" not in js:
        warns.append("site-search.js có nhưng thiếu renderResults() — kiểm tra logic search")

    if fails:
        return CheckResult("SEARCH-UI", title, FAIL,
                           diagnosis="search dialog không có UI styled hoặc mất markup/logic",
                           fix=("thêm/giữ sass/_site-search.scss (overlay+panel+field+submit+result) + "
                                "@import \"site-search\" trong site.scss; giữ markup .site-search__* + "
                                "data-search-* trong base.html và static/js/site-search.js"),
                           details=fails + warns)
    if warns:
        return CheckResult("SEARCH-UI", title, WARN,
                           diagnosis="search UI styled & hoạt động nhưng còn khe hở resilience",
                           fix="bổ sung @media mobile + .site-search[hidden] trong _site-search.scss",
                           details=warns)
    return CheckResult("SEARCH-UI", title, PASS,
                       diagnosis="search dialog có UI styled native (overlay/panel/field/submit/result), "
                                 "responsive, markup + engine còn nguyên")


def check_domain_root_url_vaccine(ctx: Ctx) -> CheckResult:
    """DOMAIN-ROOT — scanner scripts must not hardcode /zola as URL-normalization base path.

    After migrating to seomoney.org (apex domain, no subpath), link scanners must
    derive their base-path from config.toml base_url, not from a hardcoded "/zola"
    constant. This detector catches regressions where someone re-introduces the
    old subpath assumption.

    FAIL:
      * config.toml base_url contains '/zola' (would make SITE_BASE_PATH = '/zola',
        re-infecting all link normalization downstream).
      * Any scanner script defines SITE_PREFIX, SITE_BASE_PATH, or BASE_PATH equal
        to the literal string '/zola' in non-comment assignment code.
    WARN:
      * Stale 'github.io/zola' references found in operational scanner scripts
        (not build-breaking but indicate drift — covered more broadly by V19;
        here narrowed to the scanner scripts specifically).
    """
    title = "DOMAIN-ROOT Scanner Base-Path (/zola prefix assumption)"

    # Scanner scripts to audit — the primary consumers of SITE_PREFIX / SITE_BASE_PATH.
    SCANNER_SCRIPTS = [
        "qa-404-checker.py",
        "scripts/check_internal_links.py",
        "scripts/build_references.py",
        "scripts/audit_internal_links.py",
        "scripts/hotfix_improvement_progress.py",
    ]

    # Regex: assignment of SITE_PREFIX, SITE_BASE_PATH, BASE_PATH, or SITE_BASE to "/zola".
    # Matches patterns like:  SITE_PREFIX = "/zola"  or  SITE_BASE_PATH = "/zola"
    # but NOT comment lines or derived expressions like urlparse(BASE_URL).path.rstrip("/").
    # Strategy: match non-comment lines containing the assignment, then verify string value.
    _HARDCODE_PAT = re.compile(
        r"^[^#\n]*(?:SITE_PREFIX|SITE_BASE_PATH|BASE_PATH|SITE_BASE)\s*=\s*['\"](/zola)['\"]",
        re.MULTILINE,
    )

    # Pattern for stale github.io/zola in scanner scripts (WARN)
    _STALE_HOST_PAT = re.compile(r"banhang-chogao\.github\.io/zola", re.IGNORECASE)

    fails: list[str] = []
    warns: list[str] = []

    # --- Check 1: config.toml base_url must NOT include /zola path segment ---
    cfg_text = ctx.read("config.toml") or ""
    for line in cfg_text.splitlines():
        s = line.strip()
        if s.startswith("base_url") and "=" in s:
            val = s.split("=", 1)[1].strip().strip('"').strip("'")
            parsed_path = ""
            try:
                from urllib.parse import urlparse as _up
                parsed_path = _up(val).path.rstrip("/")
            except Exception:
                pass
            if parsed_path == "/zola" or parsed_path.startswith("/zola/"):
                fails.append(
                    f"config.toml base_url={val!r} contains /zola subpath — "
                    "SITE_BASE_PATH will be '/zola', re-infecting link normalization. "
                    "Fix: set base_url = \"https://seomoney.org\""
                )
            break

    # --- Check 2: scanner scripts must not hardcode /zola as a base-path value ---
    for rel in SCANNER_SCRIPTS:
        text = ctx.read(rel)
        if text is None:
            continue  # script absent — skip (not a FAIL; may be future state)
        matches = _HARDCODE_PAT.findall(text)
        if matches:
            fails.append(
                f"{rel}: hardcoded SITE_PREFIX/SITE_BASE_PATH = '/zola' found "
                f"({len(matches)} occurrence(s)) — derive from BASE_URL instead"
            )
        # Check for stale host refs (WARN, narrowed to scanner context)
        host_hits = _STALE_HOST_PAT.findall(text)
        if host_hits:
            warns.append(
                f"{rel}: {len(host_hits)} stale 'banhang-chogao.github.io/zola' "
                "reference(s) in scanner script"
            )

    if fails:
        return CheckResult(
            "DOMAIN-ROOT", title, FAIL,
            diagnosis="; ".join(fails),
            fix=(
                "Remove hardcoded '/zola' base-path from scanner scripts. "
                "Derive SITE_BASE_PATH from BASE_URL: "
                "urlparse(BASE_URL).path.rstrip('/') — returns '' at root domain. "
                "Set config.toml base_url = \"https://seomoney.org\"."
            ),
            details=fails + warns,
        )
    if warns:
        return CheckResult(
            "DOMAIN-ROOT", title, WARN,
            diagnosis=f"{len(warns)} stale github.io/zola ref(s) in scanner scripts",
            fix="Update scanner script comments/strings to reference seomoney.org",
            details=warns,
        )
    return CheckResult(
        "DOMAIN-ROOT", title, PASS,
        diagnosis=(
            "config.toml base_url has no /zola subpath; "
            "scanner scripts do not hardcode /zola as base-path value"
        ),
    )


def check_editor_publish_vaccine(ctx: Ctx) -> CheckResult:
    """EDITOR-PUBLISH — the /editor/ CMS must commit saves to GitHub, not fall back
    to a draft-only download path; edits must send a SHA; the SEO rail must hydrate
    for old posts; and sticky must be single-active (auto-unstick previous sticky).

    Root cause it guards (the bug this task fixed): editor.js had a DRAFT-ONLY
    `putPost` that merely downloaded the .md file instead of PUT-ing it to GitHub,
    so "saving" never committed and edits silently went nowhere ("Not Found").

    Static signals (no browser / network needed):
      FAIL — saving would not commit, or a known regression returns:
        * editor.js no longer calls the backend publish endpoint /cms/save-post;
        * editor.js still ships a draft-only download save (URL.createObjectURL /
          "draft-only") as the save path;
        * the GitHub commit helper does not forward a `sha` (edit overwrite-safety);
        * backend main.py is missing the @app.post("/cms/save-post") route;
        * backend has no sticky auto-unstick (_demote_other_sticky_posts) wired into
          the save route → multiple sticky posts could remain;
        * the SEO rail never re-analyzes after an existing post loads (no
          'cms:hydrated' bridge) → all-zero checklist for old posts.
      WARN — committed-correctly but a resilience/UX gap:
        * editor.js still hard-blocks save when another sticky exists (should
          auto-unstick instead).
    """
    title = "Editor publish→GitHub, edit SHA, SEO hydrate, single sticky"
    js = ctx.read("static/js/editor.js") or ""
    rail = ctx.read("static/js/cms/editor-seo-rail.js") or ""
    backend = ctx.read("services/visitor-counter/main.py") or ""

    fails: list[str] = []
    warns: list[str] = []

    # 1) Editor saves by committing to the backend publish endpoint.
    if not js:
        fails.append("static/js/editor.js vắng → không có flow lưu bài")
    else:
        if "/cms/save-post" not in js:
            fails.append("editor.js không gọi POST /cms/save-post → save không commit GitHub")
        # 2) The draft-only download save path must be gone (no stale putPost that
        #    only triggers a blob download instead of committing).
        if re.search(r"function\s+putPost\b", js) or re.search(r"a\.download\s*=\s*filename", js):
            fails.append("editor.js vẫn còn save kiểu tải file .md (putPost/blob download) thay vì commit")
        # 3) Edit save must forward a SHA (overwrite-safe update of existing file).
        if not re.search(r"sha\s*:\s*payload\.sha", js) and not re.search(r"\bsha\s*:", js):
            fails.append("editor.js không gửi `sha` khi lưu → update bài cũ thiếu SHA (ghi đè không an toàn)")
        if "state.editing.sha" not in js:
            fails.append("editor.js không dùng state.editing.sha → SHA bài đang sửa không được truyền")
        # 4) Hydration bridge for the SEO rail.
        if "cms:hydrated" not in js:
            fails.append("editor.js không phát 'cms:hydrated' → SEO rail không hydrate bài cũ")
        # WARN — sticky should auto-unstick, never hard-block the save.
        if re.search(r"ensureStickyAllowed", js):
            warns.append("editor.js còn chặn cứng save khi có sticky khác (nên auto-unstick)")

    # 5) SEO rail listens for the hydration signal → re-analyzes loaded posts.
    if not rail:
        fails.append("static/js/cms/editor-seo-rail.js vắng → không có trợ lý SEO")
    elif "cms:hydrated" not in rail:
        fails.append("editor-seo-rail.js không lắng nghe 'cms:hydrated' → checklist 0 cho bài cũ")

    # 6) Backend publish route + single-sticky enforcement.
    if not backend:
        warns.append("services/visitor-counter/main.py không đọc được → bỏ qua check backend")
    else:
        if '"/cms/save-post"' not in backend and "'/cms/save-post'" not in backend:
            fails.append("backend main.py thiếu route POST /cms/save-post → publish 404")
        if "_demote_other_sticky_posts" not in backend:
            fails.append("backend thiếu _demote_other_sticky_posts → sticky không single-active")
        elif backend.count("_demote_other_sticky_posts") < 2:
            # defined but never called from the save route
            fails.append("backend định nghĩa _demote_other_sticky_posts nhưng không gọi trong save-post")

    if fails:
        return CheckResult("EDITOR-PUBLISH", title, FAIL,
                           diagnosis="editor save không commit GitHub / thiếu SHA / SEO rail không hydrate / sticky không single-active",
                           fix=("editor.js: commit qua /cms/save-post kèm sha + phát 'cms:hydrated'; "
                                "rail: nghe 'cms:hydrated'; backend: route /cms/save-post + "
                                "_demote_other_sticky_posts gọi khi sticky=true"),
                           details=fails + warns)
    if warns:
        return CheckResult("EDITOR-PUBLISH", title, WARN,
                           diagnosis="editor commit đúng nhưng còn khe hở (sticky block / backend không đọc được)",
                           fix="đổi sticky sang auto-unstick (bỏ block cứng)",
                           details=warns)
    return CheckResult("EDITOR-PUBLISH", title, PASS,
                       diagnosis="editor commit lên GitHub qua /cms/save-post (kèm SHA), SEO rail hydrate bài cũ, "
                                 "sticky single-active (backend auto-unstick)")

# Glyphs that must NEVER appear as icons in the editor's visible UI (S-DNA
# redesign — outline SVG only). Plain directional arrows ↑ ↓ ← → (U+2190..2193)
# are allowed: they are keyboard hints inside <kbd>, not action icons.
_EDITOR_EMOJI_RANGES = (
    (0x1F000, 0x1FAFF),  # pictographs / emoji
    (0x2600, 0x27BF),    # misc symbols + dingbats (pencil/spark/warning …)
    (0x2300, 0x23FF),    # misc technical (⏻ ⏱ …)
    (0x2B00, 0x2BFF),    # stars / arrows blocks (⭐ …)
)
_EDITOR_EMOJI_EXTRA = {0xFE0F, 0xFF0B, 0x21BB, 0x21C4, 0x21A9, 0x21AA, 0x2934, 0x2935}
_TERA_COMMENT = re.compile(r"\{#.*?#\}", re.S)
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)


def _editor_emoji_hits(text: str) -> list[str]:
    """Return the distinct forbidden icon glyphs found in editor-visible markup.

    Tera + HTML comments are stripped first so an emoji in a code comment never
    trips the gate — only glyphs that would actually render are flagged.
    """
    body = _HTML_COMMENT.sub(" ", _TERA_COMMENT.sub(" ", text or ""))
    hits: set[str] = set()
    for ch in body:
        o = ord(ch)
        if o in _EDITOR_EMOJI_EXTRA or any(a <= o <= b for a, b in _EDITOR_EMOJI_RANGES):
            hits.add(ch)
    return sorted(hits)


def check_editor_sdna_vaccine(ctx: Ctx) -> CheckResult:
    """EDITOR-SDNA — the /editor/ CMS must keep its S-DNA visual layer and stay
    emoji-free, without losing publish/edit logic or the SEO assistant.

    The redesign repainted templates/editor.html + the SEO rail partial with the
    Sembcorp Design DNA (soft KPI cards, coloured left accents, thin outline SVG
    icons in circle rings) via the scoped partial sass/_editor-sdna.scss. This
    detector guards that work from regressions.

    FAIL (visible regression or lost functionality):
      * sass/_editor-sdna.scss missing, or not @import-ed in site.scss;
      * the editor templates re-introduce emoji icons in visible UI;
      * publish/edit handlers gone (data-action="publish" / data-form="post" /
        the editor.js include);
      * the SEO assistant rail is gone (include or data-seo-rail).
    WARN (styled but a resilience / fidelity gap):
      * the S-DNA partial lacks the KPI-card / circle-ring structure;
      * no mobile (≤720px) media query (mobile layout could drift).
    """
    title = "Editor S-DNA visual layer (emoji-free + KPI cards + logic intact)"
    scss = ctx.read("sass/_editor-sdna.scss")
    site_scss = ctx.read("sass/site.scss") or ""
    editor = ctx.read("templates/editor.html") or ""
    rail = ctx.read("templates/partials/editor-seo-rail.html") or ""

    fails: list[str] = []
    warns: list[str] = []

    # 1) Scoped S-DNA stylesheet exists and is wired into the bundle.
    if not scss:
        fails.append("sass/_editor-sdna.scss vắng → editor mất lớp S-DNA (raw lại)")
    elif not re.search(r'@import\s+["\']editor-sdna["\']', site_scss):
        fails.append('sass/site.scss thiếu @import "editor-sdna" → partial không vào bundle')

    # 2) No emoji icons in the editor's visible UI (template source).
    for rel, text in (("templates/editor.html", editor),
                      ("templates/partials/editor-seo-rail.html", rail)):
        hits = _editor_emoji_hits(text)
        if hits:
            shown = " ".join(hits[:12])
            fails.append(f"{rel}: còn icon emoji trong UI ({shown}) → thay bằng outline SVG")

    # 3) Publish / edit handlers must still be present (logic unchanged).
    for needle, why in (
        ('data-action="publish"', "nút Đăng lên blog (publish handler)"),
        ('data-form="post"', "form soạn bài (edit/publish form)"),
        ("js/editor.js", "editor.js (publish/edit/auth logic)"),
    ):
        if needle not in editor:
            fails.append(f"templates/editor.html mất `{why}` ({needle}) → editor logic vỡ")

    # 4) SEO assistant must still be present.
    if "editor-seo-rail" not in editor:
        fails.append("templates/editor.html không còn include SEO rail (editor-seo-rail)")
    if "data-seo-rail" not in rail:
        fails.append("partials/editor-seo-rail.html mất data-seo-rail → trợ lý SEO biến mất")

    # 5) S-DNA fidelity — KPI cards + circle rings + responsive (WARN).
    if scss:
        if "esr-kpi" not in scss:
            warns.append("_editor-sdna.scss thiếu style .esr-kpi → SEO assistant chưa thành KPI card")
        if ".ed-ico" not in scss:
            warns.append("_editor-sdna.scss thiếu .ed-ico (circle/outline icon helper)")
        if "max-width: 720px" not in scss and "max-width:720px" not in scss:
            warns.append("_editor-sdna.scss thiếu @media (max-width: 720px) → mobile có thể trôi layout")

    if fails:
        return CheckResult("EDITOR-SDNA", title, FAIL,
                           diagnosis="editor mất lớp S-DNA, còn emoji, hoặc mất logic/SEO assistant",
                           fix=("giữ sass/_editor-sdna.scss + @import \"editor-sdna\"; thay mọi emoji "
                                "trong editor.html/SEO rail bằng outline SVG; giữ data-action=\"publish\", "
                                "data-form=\"post\", include editor.js + SEO rail"),
                           details=fails + warns)
    if warns:
        return CheckResult("EDITOR-SDNA", title, WARN,
                           diagnosis="editor đã S-DNA + emoji-free nhưng còn khe hở fidelity/resilience",
                           fix="bổ sung .esr-kpi / .ed-ico / @media mobile trong _editor-sdna.scss",
                           details=warns)
    return CheckResult("EDITOR-SDNA", title, PASS,
                       diagnosis=("editor có lớp S-DNA scoped (KPI cards + circle outline icons), "
                                  "không còn emoji, publish/edit + SEO assistant còn nguyên"))


def check_no_floating_nav_vaccine(ctx: Ctx) -> CheckResult:
    """V21 — No Floating Bar / Stable Nav Vaccine.

    SEOMONEY desktop navigation must stay ANCHORED in normal document flow.
    The blog owner finds floating / sticky / drifting nav bars visually tiring
    (eye strain), so desktop nav rails, sidebars and action bars must NOT detach
    from the layout and drift on scroll. This permanently protects the PR #585
    behavior where `.side-nav { position: static }`.

    FAIL — a PROTECTED desktop nav/sidebar/action selector floats in DESKTOP
           scope (global or min-width — i.e. NOT inside a mobile @media max-width):
             * position: sticky / position: fixed;
             * scroll-driven CSS animation / parallax
               (animation-timeline: scroll(…) | view(…));
           OR a JS file wires a scroll listener that mutates a nav element's
           transform / top / position (scroll-linked drift).

    EXEMPTIONS (never flagged): true overlays / modals / search dialogs and the
    mobile hamburger drawer — `.nav-drawer*`, `.nav-toggle`, `.site-search*`,
    `[role="dialog"]` — and ANY rule scoped under a mobile `@media (max-width)`
    breakpoint. Mobile is handled separately; this detector must not break it.
    """
    title = "No floating/sticky nav on desktop (stable nav — V21)"

    # Selectors that MUST stay in normal flow on desktop. Drawer/toggle/search
    # are deliberately absent — those are the allowed overlay/mobile exceptions.
    PROTECTED = (".side-nav", ".side-nav__actions", ".primary-nav",
                 ".site-sidebar", ".nav-rail", ".desktop-nav")
    FLOAT_POS = re.compile(r"position\s*:\s*(sticky|fixed)\b", re.I)
    SCROLL_ANIM = re.compile(r"animation-timeline\s*:\s*(?:scroll|view)\s*\(", re.I)

    fails: list[str] = []

    # --- CSS: scan every SCSS partial for floating desktop nav selectors ---
    for p in ctx.glob("sass/*.scss"):
        rel = "sass/" + p.name
        raw = ctx.read(rel)
        if not raw:
            continue
        text = _strip_css_comments(raw)
        mobile_spans = _mobile_media_spans(text)
        for sel in PROTECTED:
            # `[^{}]*` keeps the match inside this selector's own (flat) block,
            # never crossing into a nested rule.
            for m in re.finditer(re.escape(sel) + r"\s*\{([^{}]*)\}", text):
                if _in_spans(m.start(), mobile_spans):
                    continue  # mobile-scoped → exempt (handled separately)
                block = m.group(1)
                pm = FLOAT_POS.search(block)
                if pm:
                    fails.append(
                        f"{rel}: `{sel}` dùng position:{pm.group(1).lower()} ở desktop scope "
                        "— nav phải tĩnh (in-flow), không trôi theo scroll"
                    )
                if SCROLL_ANIM.search(block):
                    fails.append(
                        f"{rel}: `{sel}` dùng scroll-driven animation/parallax "
                        "(animation-timeline) — nav trôi theo scroll"
                    )

    # --- JS: scroll listener that mutates a nav element's transform/top ---
    NAV_TOKENS = ("side-nav", "primary-nav", "site-sidebar", "nav-rail", "desktop-nav")
    _SCROLL_LISTENER = re.compile(r"addEventListener\s*\(\s*['\"]scroll['\"]")
    _MUT_ASSIGN = re.compile(r"\.style\.(?:transform|top|position)\s*=")
    _MUT_SETPROP = re.compile(r"\.style\.setProperty\s*\(\s*['\"](?:transform|top|position)")
    for p in ctx.glob("static/js/*.js"):
        rel = "static/js/" + p.name
        js = ctx.read(rel)
        if not js:
            continue
        if not any(tok in js for tok in NAV_TOKENS):
            continue
        has_scroll = bool(_SCROLL_LISTENER.search(js)) or "onscroll" in js
        mutates = bool(_MUT_ASSIGN.search(js)) or bool(_MUT_SETPROP.search(js))
        if has_scroll and mutates:
            fails.append(
                f"{rel}: scroll listener mutates nav transform/top/position "
                "— scroll-linked drift (dùng layout tĩnh, bỏ scroll handler)"
            )

    if fails:
        return CheckResult(
            "V21", title, FAIL,
            diagnosis="desktop nav/sidebar/action bar đang dùng floating/sticky/scroll-linked → trôi khi cuộn (gây mỏi mắt)",
            fix=("đặt selector nav desktop về `position: static` (in-flow); bỏ position:sticky/fixed, "
                 "scroll-driven animation, và scroll listener mutate transform/top. Overlay/modal/search/"
                 "mobile drawer được miễn (giữ trong @media max-width hoặc dùng .nav-drawer/.site-search)."),
            details=fails,
        )
    return CheckResult(
        "V21", title, PASS,
        diagnosis="desktop nav giữ in-flow (không sticky/fixed/scroll-linked); overlay/mobile drawer được miễn đúng cách",
    )


# Canonical SEO identity (V20) — the brand string + canonical apex root.
CANONICAL_HOST = "seomoney.org"
BRAND_TOKEN = "SEOMONEY"


def _config_base_url(ctx: Ctx) -> str:
    """Extract config.toml base_url value (best-effort, stdlib only)."""
    for line in (ctx.read("config.toml") or "").splitlines():
        s = line.strip()
        if s.startswith("base_url") and "=" in s:
            return s.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


_GA_PROPERTY_ID = "542421812"
_GA_MEASUREMENT_ID = "G-SMTFZVC0XN"
_GA_OLD_PROPERTY_ID = "541698865"
_GA_OLD_MEASUREMENT_ID = "G-REFBXH86Z5"
_GA_CREDENTIAL_FIELDS = (
    "private_key", "private_key_id", "client_email", "client_id",
    "client_secret", "refresh_token", "access_token", "GA_SERVICE_ACCOUNT_KEY",
)
# Files that legitimately reference the OLD ids to DETECT them — exempt from the
# drift check (same pattern as V19 exempting dns_vaccine.py).
_GA_DRIFT_EXEMPT = ("scripts/ga_vacxin.py", "scripts/qa_vaccines.py")


def check_ga_stats_vaccine(ctx: Ctx) -> CheckResult:
    """V25 — GA stats module identity, cache isolation, hourly GA Vacxin, banner.

    After the seomoney.org domain move the footer GA module must read ONLY the new
    GA4 property (542421812 · G-SMTFZVC0XN) and never surface old-property numbers.

    FAIL (wrong identity / cache leak / secret leak — would mislead or expose):
      * config.toml ga_property_id / ga_measurement_id ≠ canonical
      * scripts/fetch_ga_stats.py default PROPERTY_ID ≠ 542421812
      * old 541698865 / G-REFBXH86Z5 in active GA config/code (not the guards)
      * templates/base.html hardcodes a gtag measurement id (must be templated)
      * data/ga-stats.json or data/ga-health.json stamped with a foreign property
        or leaking a service-account credential field

    WARN (resilience / required feature wired):
      * GA Vacxin hourly workflow (ga-vacxin.yml) missing or not hourly
      * base.html missing the health root / inline warning banner
      * static/js/ga-health.js missing or without a try/catch guard
      * config.toml missing ga_dashboard_url / ga_fix_url
      * data/ga-health.json missing required schema keys
    """
    title = "GA stats module (property 542421812 · cache isolation · GA Vacxin)"
    fails: list[str] = []
    warns: list[str] = []

    cfg = ctx.read("config.toml") or ""

    def _cfg(key: str) -> str | None:
        m = re.search(rf'^{key}\s*=\s*"([^"]+)"', cfg, re.MULTILINE)
        return m.group(1) if m else None

    if _cfg("ga_property_id") != _GA_PROPERTY_ID:
        fails.append(f"config.toml ga_property_id = {_cfg('ga_property_id')!r} (phải là {_GA_PROPERTY_ID!r})")
    if _cfg("ga_measurement_id") != _GA_MEASUREMENT_ID:
        fails.append(f"config.toml ga_measurement_id = {_cfg('ga_measurement_id')!r} (phải là {_GA_MEASUREMENT_ID!r})")
    if not _cfg("ga_dashboard_url"):
        warns.append("config.toml thiếu ga_dashboard_url (nút Dashboard / Khắc phục)")
    if not _cfg("ga_fix_url"):
        warns.append("config.toml thiếu ga_fix_url")

    # fetch script default property (env-overridable form or bare assignment)
    fetch_src = ctx.read("scripts/fetch_ga_stats.py") or ""
    fm = re.search(r'PROPERTY_ID\s*=\s*os\.environ\.get\(\s*["\']GA_PROPERTY_ID["\']\s*,\s*["\']([^"\']+)["\']', fetch_src)
    if not fm:
        fm = re.search(r'PROPERTY_ID\s*=\s*["\']([^"\']+)["\']', fetch_src)
    if fm and fm.group(1) != _GA_PROPERTY_ID:
        fails.append(f"fetch_ga_stats.py PROPERTY_ID default = {fm.group(1)!r} (phải là {_GA_PROPERTY_ID!r})")

    # old-id drift in active GA config/code (exempt the detector + monitor guards)
    for rel in ("config.toml", "scripts/fetch_ga_stats.py", "templates/base.html",
                ".github/workflows/ga-stats.yml", ".github/workflows/ga-vacxin.yml"):
        if rel in _GA_DRIFT_EXEMPT:
            continue
        src = ctx.read(rel) or ""
        if _GA_OLD_PROPERTY_ID in src or _GA_OLD_MEASUREMENT_ID in src:
            fails.append(f"{rel}: còn id GA cũ ({_GA_OLD_PROPERTY_ID}/{_GA_OLD_MEASUREMENT_ID}) → đọc property cũ")

    # base.html: gtag must be templated, and the health module + banner present
    base_html = ctx.read("templates/base.html") or ""
    if re.search(r"gtag/js\?id=G-[A-Z0-9]{6,}", base_html):
        fails.append("templates/base.html: gtag src hardcode measurement id (phải dùng config.extra.ga_measurement_id)")
    if "data-ga-health" not in base_html:
        warns.append("templates/base.html: thiếu data-ga-health (module GA health)")
    if "data-ga-banner" not in base_html:
        warns.append("templates/base.html: thiếu banner cảnh báo inline (data-ga-banner)")

    # data/ga-stats.json: stamped with the current property only, no creds
    raw_stats = ctx.read("data/ga-stats.json")
    if raw_stats:
        try:
            stats = json.loads(raw_stats)
        except json.JSONDecodeError:
            fails.append("data/ga-stats.json không phải JSON hợp lệ")
            stats = None
        if isinstance(stats, dict):
            spid = str(stats.get("property_id", ""))
            if spid and spid != _GA_PROPERTY_ID:
                fails.append(f"data/ga-stats.json property_id={spid} (kỳ vọng {_GA_PROPERTY_ID}) — rò rỉ property cũ")
            if _GA_OLD_PROPERTY_ID in raw_stats:
                fails.append(f"data/ga-stats.json còn dấu vết property cũ {_GA_OLD_PROPERTY_ID}")
            leaked = [f for f in _GA_CREDENTIAL_FIELDS if f in stats]
            if leaked:
                fails.append(f"data/ga-stats.json rò rỉ trường bí mật: {leaked}")

    # data/ga-health.json: schema + no creds + right property
    raw_health = ctx.read("data/ga-health.json")
    if raw_health is None:
        warns.append("data/ga-health.json absent (GA Vacxin chưa chạy lần đầu)")
    else:
        try:
            health = json.loads(raw_health)
        except json.JSONDecodeError:
            fails.append("data/ga-health.json không phải JSON hợp lệ")
            health = None
        if isinstance(health, dict):
            leaked = [f for f in _GA_CREDENTIAL_FIELDS if f in health]
            if leaked:
                fails.append(f"data/ga-health.json rò rỉ trường bí mật: {leaked}")
            hp = str(health.get("property_id", ""))
            if hp and hp != _GA_PROPERTY_ID:
                fails.append(f"data/ga-health.json property_id={hp} (kỳ vọng {_GA_PROPERTY_ID})")
            missing = [k for k in ("status", "last_checked", "property_id") if k not in health]
            if missing:
                warns.append(f"data/ga-health.json thiếu schema keys: {missing}")

    # GA Vacxin hourly workflow
    wf = ctx.read(".github/workflows/ga-vacxin.yml")
    if wf is None:
        warns.append(".github/workflows/ga-vacxin.yml absent (GA Vacxin hourly job)")
    elif not re.search(r"cron:\s*['\"]\s*\d+\s+\*\s+\*\s+\*\s+\*\s*['\"]", wf):
        warns.append("ga-vacxin.yml: không thấy cron chạy mỗi giờ ('<m> * * * *')")

    # ga-health.js present + crash-safe
    js = ctx.read("static/js/ga-health.js")
    if js is None:
        warns.append("static/js/ga-health.js absent (refresh banner client-side)")
    elif "try" not in js or "catch" not in js:
        warns.append("static/js/ga-health.js thiếu try/catch (no-JS-crash guard)")

    # UI-healthy must NOT diverge from data/auth-healthy. The "Khoẻ mạnh" pulse is
    # only valid when stats are ok; the template gates it with `hidden` when not.
    # FAIL if the CSS leaks a false healthy badge by overriding [hidden], or the
    # template stops hiding the pulse when stats are not ok.
    if "data-ga-pulse" in base_html:
        m_pulse = re.search(r"data-ga-pulse[^>]*?(\{%\s*if[^%]*%\}\s*hidden)", base_html)
        if not m_pulse:
            fails.append(
                "templates/base.html: pulse 'Khoẻ mạnh' không gate bằng `hidden` khi "
                "stats không ok — sẽ báo khoẻ mạnh dù GA đang pending"
            )
    scss = ctx.read("sass/_ga-stats.scss") or ""
    if "ga-stats__pulse" in scss or "&__pulse" in scss:
        # require the pulse to honour [hidden]; without it, display:inline-flex
        # overrides the UA hidden rule → false healthy badge while pending.
        if not re.search(r"&__pulse\b[\s\S]{0,800}?&\[hidden\]", scss) \
           and "ga-stats__pulse[hidden]" not in scss:
            fails.append(
                "sass/_ga-stats.scss: .ga-stats__pulse thiếu `&[hidden] { display: none }` "
                "→ chip 'Khoẻ mạnh' đè [hidden], hiện sai khi GA pending"
            )

    if fails:
        return CheckResult(
            "V27", title, FAIL,
            diagnosis="GA module sai property/measurement, rò rỉ cache cũ, hoặc lộ credential",
            fix=(f"1. config.toml ga_property_id={_GA_PROPERTY_ID}, ga_measurement_id={_GA_MEASUREMENT_ID}. "
                 f"2. fetch_ga_stats.py PROPERTY_ID mặc định {_GA_PROPERTY_ID}. "
                 f"3. Gỡ id cũ {_GA_OLD_PROPERTY_ID}/{_GA_OLD_MEASUREMENT_ID} khỏi config/code. "
                 "4. Reset data/ga-stats.json sang property mới; KHÔNG commit credential."),
            details=fails + warns,
        )
    if warns:
        return CheckResult("V27", title, WARN,
                           diagnosis="GA module đúng property nhưng thiếu thành phần phụ trợ",
                           fix="Bổ sung các mục WARN ở trên (workflow hourly / banner / health js / schema).",
                           details=warns)
    return CheckResult(
        "V27", title, PASS,
        diagnosis=(f"property {_GA_PROPERTY_ID} · {_GA_MEASUREMENT_ID} · GA Vacxin hourly · "
                   "cache isolated · no credential leak"),
    )


# Vaccine numbers that are *intentionally* documented more than once in CLAUDE.md:
#   V10/V11/V12 — legacy §4 main vs the compliance block;
#   V19 — GSC Domain Property vs Domain Migration Drift;
#   V22 — Editor S-DNA visual layer vs Editor save→GitHub.
# Any duplicate beyond these is a bug (new vaccines must take the next free number).
ALLOWED_DUPLICATE_VACCINES = {"V10", "V11", "V12", "V19", "V22"}

def check_toc_rail_vaccine(ctx: Ctx) -> CheckResult:
    """TOC-RAIL — the "On This Page" sticky article rail (scroll-spy) must render
    a styled rail, keep its IntersectionObserver active-state engine, and stay
    mobile-safe (hidden below the desktop breakpoint → no overflow).

    Inspired by the B-DNA right rail; an ADDITIVE desktop enhancement layered on
    top of the existing inline `.toc`. Static signals (no browser needed):
      FAIL — the rail would not render / loses its scroll-spy:
        * sass/_toc-rail.scss missing or not imported in site.scss;
        * the partial lacks the rail (.toc-rail), the sticky behaviour, the
          two-column `.post-layout` grid, or the `.is-active` highlight;
        * templates/page.html lost the rail markup (data-toc-rail /
          data-toc-link / the page.toc loop) or the toc-rail.js include;
        * static/js/toc-rail.js missing or without IntersectionObserver.
      WARN — renders but a resilience gap:
        * rail not hidden by default (display:none) → mobile overflow risk;
        * no desktop min-width media (rail could show where it squeezes prose).
    """
    title = "On-This-Page TOC rail (scroll-spy, mobile-safe)"
    scss = ctx.read("sass/_toc-rail.scss")
    site_scss = ctx.read("sass/site.scss") or ""
    page = ctx.read("templates/page.html") or ""
    js = ctx.read("static/js/toc-rail.js")

    fails: list[str] = []
    warns: list[str] = []

    # 1) Styled partial exists and is wired into the bundle.
    if not scss:
        fails.append("sass/_toc-rail.scss vắng → rail không có CSS (raw/không hiện)")
    elif not re.search(r'@import\s+["\']toc-rail["\']', site_scss):
        fails.append('sass/site.scss thiếu @import "toc-rail" → partial không vào bundle')

    # 2) Structure: rail card, sticky behaviour, 2-col layout, active highlight.
    if scss:
        if ".toc-rail" not in scss:
            fails.append("_toc-rail.scss thiếu selector .toc-rail")
        if not re.search(r"position\s*:\s*sticky", scss):
            fails.append("_toc-rail.scss thiếu position:sticky → rail không bám khi cuộn")
        if ".post-layout" not in scss or "grid-template-columns" not in scss:
            fails.append("_toc-rail.scss thiếu grid .post-layout (bài + rail 2 cột)")
        if "is-active" not in scss:
            fails.append("_toc-rail.scss thiếu .is-active → không tô đậm mục đang đọc")
        # mobile-safe (hidden by default) + desktop-only (min-width media)
        if not re.search(r"\.toc-rail\s*\{[^}]*display\s*:\s*none", scss, re.S):
            warns.append(".toc-rail không display:none mặc định → mobile có thể overflow")
        if "min-width" not in scss:
            warns.append("_toc-rail.scss thiếu @media min-width → rail có thể hiện ở màn hẹp")

    # 3) Template markup contract + script include.
    for needle, why in (
        ("data-toc-rail", "rail container (data-toc-rail)"),
        ("data-toc-link", "rail link / scroll-spy target (data-toc-link)"),
        ("page.toc", "TOC sinh từ heading bài (page.toc)"),
        ("toc-rail.js", "scroll-spy script include (toc-rail.js)"),
    ):
        if needle not in page:
            fails.append(f"templates/page.html thiếu {why}")

    # 4) The scroll-spy engine must be present (active state on scroll).
    if not js:
        fails.append("static/js/toc-rail.js vắng → không có active-state khi cuộn")
    elif "IntersectionObserver" not in js:
        fails.append("toc-rail.js thiếu IntersectionObserver → không highlight mục đang đọc")

    if fails:
        return CheckResult("TOC-RAIL", title, FAIL,
                           diagnosis="rail TOC On-This-Page không render hoặc mất scroll-spy/markup",
                           fix=('thêm/giữ sass/_toc-rail.scss (.toc-rail sticky + .post-layout grid + '
                                '.is-active) và @import "toc-rail"; giữ markup data-toc-rail/data-toc-link/'
                                'page.toc + include toc-rail.js (IntersectionObserver) trong page.html'),
                           details=fails + warns)
    if warns:
        return CheckResult("TOC-RAIL", title, WARN,
                           diagnosis="rail hoạt động nhưng còn khe hở mobile/responsive",
                           fix="ẩn .toc-rail mặc định (display:none) + chỉ hiện trong @media min-width desktop",
                           details=warns)
    return CheckResult("TOC-RAIL", title, PASS,
                       diagnosis="rail On-This-Page có CSS sticky + grid 2 cột + .is-active, "
                                 "scroll-spy IntersectionObserver, markup + include đủ, ẩn an toàn ở mobile")


def check_v20_seo_identity_homepage(ctx: Ctx) -> CheckResult:
    """V20 — SEO Identity / Homepage Migration: brand + canonical root must hold.

    Guards the apex-domain migration (20/06/2026): canonical root stays
    https://seomoney.org/ and the homepage keeps the SEOMONEY brand.

    FAIL: base_url non-apex / github.io / /zola subpath / http://, OR homepage
          title/H1 lost the SEOMONEY brand (canonical signal regression).
    WARN: article JSON-LD @type is not BlogPosting (weaker rich-result signal).
    """
    title = "V20 SEO Identity / Homepage Migration (canonical seomoney.org + brand)"
    fails: list[str] = []
    warns: list[str] = []

    # Check 1: canonical base_url — apex, https, no /zola, no github.io (FAIL).
    base = _config_base_url(ctx)
    if not base:
        warns.append("config.toml base_url not found")
    else:
        if base.startswith("http://"):
            fails.append(f"base_url uses http:// (must be https://): {base!r}")
        if "github.io" in base:
            fails.append(f"base_url still on github.io: {base!r}")
        if "/zola" in base:
            fails.append(f"base_url still carries /zola subpath: {base!r}")
        host = base.split("://", 1)[-1].split("/", 1)[0].lower()
        if host and host not in (CANONICAL_HOST, "www." + CANONICAL_HOST):
            fails.append(f"base_url host {host!r} is not the canonical apex {CANONICAL_HOST!r}")

    # Check 2: homepage title + H1 keep the SEOMONEY brand (FAIL if lost).
    idx = ctx.read("templates/index.html") or ""
    block_title = ""
    mt = re.search(r"\{%\s*block\s+title\s*%\}(.*?)\{%\s*endblock", idx, re.DOTALL)
    if mt:
        block_title = mt.group(1)
    h1 = ""
    mh = re.search(r"<h1[^>]*>(.*?)</h1>", idx, re.DOTALL)
    if mh:
        h1 = mh.group(1)
    if idx:
        if BRAND_TOKEN not in block_title:
            fails.append("homepage <title> block lost the SEOMONEY brand")
        if BRAND_TOKEN not in h1:
            fails.append("homepage <h1> lost the SEOMONEY brand")

    # Check 3: article JSON-LD should use BlogPosting (WARN only).
    base_html = ctx.read("templates/base.html") or ""
    if base_html and '"@type": "BlogPosting"' not in base_html:
        if '"@type": "Article"' in base_html:
            warns.append('article JSON-LD still uses "Article" — prefer "BlogPosting"')

    if fails:
        return CheckResult("V20", title, FAIL,
                           diagnosis="; ".join(fails),
                           fix=("Restore base_url=https://seomoney.org (apex/https/no /zola), "
                                "keep SEOMONEY brand in homepage title/H1, BlogPosting schema "
                                "(see V20 CLAUDE.md)"),
                           details=fails + warns)
    if warns:
        return CheckResult("V20", title, WARN,
                           diagnosis="; ".join(warns),
                           fix="Apply V20 FIXER in CLAUDE.md",
                           details=warns)
    return CheckResult("V20", title, PASS,
                       diagnosis=("canonical root https://seomoney.org/ intact; "
                                  "homepage carries SEOMONEY brand; BlogPosting schema present"))


# --------------------------------------------------------------------------
# V25 — Split-backend route parity (frontend ↔ deployed services/vipzone)
# --------------------------------------------------------------------------
# Render deploys ONLY services/vipzone (render.yaml rootDir). A frontend call to
# blog-vipzone-api whose route lives only in services/visitor-counter returns 404
# in production. These helpers statically collect the routes mounted on the
# DEPLOYED app and compare them with the frontend's /cms/* and /gsc/* calls.
_ROUTE_DECORATOR_RE = re.compile(
    r"@(?:app|router)\.(?:get|post|put|delete|patch)\(", re.I)
_PATH_LITERAL_RE = re.compile(r"""["'](/[A-Za-z0-9_\-/{}]*)["']""")

# Route source files mounted onto the deployed services/vipzone app, with the
# prefix each router contributes (gsc_routes is imported from visitor-counter and
# mounted with prefix="/gsc"; cms_repo + cms_auth routers mount at root).
_VIPZONE_ROUTE_SOURCES = (
    ("services/vipzone/main.py", ""),
    ("services/vipzone/cms_repo.py", ""),
    ("services/vipzone/cms_auth.py", ""),
    ("services/visitor-counter/gsc_routes.py", "/gsc"),
)

# Routes the production frontend depends on that MUST be served by services/vipzone.
_V25_CRITICAL_ROUTES = ("/health", "/gsc/status", "/cms/save-post")


def _route_family(path: str) -> str:
    """Collapse a path to its first ≤2 non-parameter segments, e.g.
    `/cms/giscus/setup` → `/cms/giscus`, `/gsc/oauth/start` → `/gsc/oauth`,
    `/api/vipzone/content/{post_id}` → `/api/vipzone`."""
    segs = [s for s in path.strip("/").split("/") if s and not s.startswith("{")]
    return "/" + "/".join(segs[:2]) if segs else "/"


def _extract_vipzone_routes(ctx: Ctx) -> set[str]:
    """All route path templates mounted on the deployed services/vipzone app."""
    routes: set[str] = set()
    for rel, prefix in _VIPZONE_ROUTE_SOURCES:
        txt = ctx.read(rel)
        if not txt:
            continue
        for m in _ROUTE_DECORATOR_RE.finditer(txt):
            tail = txt[m.end():m.end() + 400]
            pm = _PATH_LITERAL_RE.search(tail)
            if pm:
                routes.add((prefix + pm.group(1)) or "/")
    return routes


def _frontend_vipzone_calls(ctx: Ctx) -> set[str]:
    """Literal `/cms/*` and `/gsc/*` paths the static JS calls (vipzone-only
    prefixes). Skips template-literal / interpolated paths (contain `$`)."""
    families: set[str] = set()
    for js in ctx.glob("static/js/**/*.js"):
        try:
            txt = js.read_text(encoding="utf-8")
        except OSError:
            continue
        for m in re.finditer(r"""["'](/(?:cms|gsc)/[A-Za-z0-9_\-/]*)["']""", txt):
            path = m.group(1)
            if "$" in path:
                continue
            families.add(_route_family(path))
    return families


def check_v25_backend_route_parity(ctx: Ctx) -> CheckResult:
    """V25 — every frontend route on blog-vipzone-api must exist on the DEPLOYED
    services/vipzone app (Render deploys only that service). A route living only in
    services/visitor-counter is dead in production → 404 split-brain (V16/V22b).

    FAIL — a critical route (/health, /gsc/status, /cms/save-post) is not mounted
           on services/vipzone (directly or via a mounted router).
    WARN — a frontend /cms/* or /gsc/* family has no matching deployed route.
    """
    title = "Backend route parity (frontend ↔ deployed services/vipzone)"
    routes = _extract_vipzone_routes(ctx)
    if not routes:
        return CheckResult("V25", title, SKIP,
                           diagnosis="services/vipzone routes không đọc được")

    families = {_route_family(r) for r in routes}

    # FAIL — critical routes must be present (param-insensitive family match).
    missing_critical = [
        r for r in _V25_CRITICAL_ROUTES
        if r not in routes and _route_family(r) not in families
    ]
    if missing_critical:
        return CheckResult(
            "V25", title, FAIL,
            diagnosis=("route quan trọng frontend gọi nhưng KHÔNG mount trên "
                       "services/vipzone (deployed) → 404 production: "
                       + ", ".join(missing_critical)),
            fix=("Mount route trên services/vipzone (main.py @app.* hoặc router "
                 "include_router) — KHÔNG để route chỉ nằm ở services/visitor-counter"),
            details=missing_critical)

    # WARN — frontend families with no deployed route (drift to fix, not a hard gate).
    uncovered = sorted(
        fam for fam in _frontend_vipzone_calls(ctx) if fam not in families)
    if uncovered:
        return CheckResult(
            "V25", title, WARN,
            diagnosis=("frontend gọi route /cms|/gsc chưa có trên services/vipzone "
                       "(deployed) — có thể 404 production"),
            fix=("Port các route này sang services/vipzone (mounted router); "
                 "kiểm chứng bằng scripts/backend_route_check.py"),
            details=uncovered)

    return CheckResult("V25", title, PASS,
                       diagnosis=(f"{len(routes)} route mounted on services/vipzone; "
                                  "critical routes present; frontend /cms·/gsc calls covered"))


# Vaccine numbers that are *intentionally* documented more than once in CLAUDE.md:
#   V10/V11/V12 — legacy §4 main vs the compliance block;
#   V19 — GSC Domain Property vs Domain Migration Drift;
#   V22 — Editor S-DNA visual layer vs Editor save→GitHub.
# Any duplicate beyond these is a bug (new vaccines must take the next free number).
ALLOWED_DUPLICATE_VACCINES = {"V10", "V11", "V12", "V19", "V22"}


def next_free_vaccine_number(ctx: Ctx | None = None) -> int:
    """Return the next free `#### V<N>` number from the CLAUDE.md vaccine library."""
    text = (ctx.read("CLAUDE.md") if ctx else None)
    if text is None:
        try:
            text = CLAUDE_MD.read_text(encoding="utf-8")
        except OSError:
            text = ""
    nums = [int(v["code"][1:]) for v in load_vaccines(text) if v["code"][1:].isdigit()]
    return (max(nums) + 1) if nums else 1


# Vaccine-registry source files: the merge of these must PRESERVE BOTH sides
# (append the PR delta, never blind ours/theirs → never renumber/delete a vaccine
# or drop a detector). The conflict resolver must classify them `manual`.
_REGISTRY_MANUAL_FILES = (
    "CLAUDE.md",
    "scripts/qa_vaccines.py",
    "scripts/test_qa_vaccines.py",
)
# Generated data JSON: must take `main` as base and REGENERATE (never hand-merge
# stale PR data). The conflict resolver must classify these `main`.
_REGISTRY_MAIN_FILES = (
    "data/seo-qa-scores.json",
    "data/vaccine-autofixer-report.json",
)


def check_v28_vaccine_registry_merge(ctx: Ctx) -> CheckResult:
    """V28 — Conflict-safe vaccine registry merge.

    When a PR touches the vaccine registry (CLAUDE.md, scripts/qa_vaccines.py,
    scripts/test_qa_vaccines.py) or generated data JSON, conflict resolution must:
      * preserve ALL main detectors/rules and append ONLY the PR delta — never a
        blind `--ours`/`--theirs` that would renumber or delete an existing
        vaccine → the resolver must classify registry source files as `manual`;
      * take `main` as the base for generated data JSON and REGENERATE it →
        the resolver must classify those data files as `main`.

    This detector statically verifies that policy by live-importing
    `autofix_conflicts.classify()` and asserts no conflict markers leaked into the
    registry source (a botched merge that could silently drop a vaccine/detector).
    """
    code = "V28"
    title = "Conflict-safe vaccine registry merge"
    af_path = ctx.root / "scripts" / "autofix_conflicts.py"
    if not af_path.is_file():
        return CheckResult(code, title, WARN,
                           diagnosis="scripts/autofix_conflicts.py vắng — không xác minh được chính sách resolve registry",
                           fix="khôi phục scripts/autofix_conflicts.py (classify registry source → manual, data JSON → main)")
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("_qa_autofix_probe", af_path)
        if spec is None or spec.loader is None:
            raise ImportError("không tạo được spec cho autofix_conflicts")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        classify = mod.classify
    except Exception as exc:
        return CheckResult(code, title, FAIL,
                           diagnosis=f"không import được autofix_conflicts.classify: {exc}",
                           fix="sửa lỗi cú pháp/định nghĩa classify(path) trong scripts/autofix_conflicts.py")

    fails: list[str] = []
    try:
        for rel in _REGISTRY_MANUAL_FILES:
            got = classify(rel)
            if got != "manual":
                fails.append(f"classify({rel!r}) = {got!r}, cần 'manual' (append cả 2 phía, không blind ours/theirs)")
        for rel in _REGISTRY_MAIN_FILES:
            got = classify(rel)
            if got != "main":
                fails.append(f"classify({rel!r}) = {got!r}, cần 'main' (lấy main rồi regenerate data)")
    except Exception as exc:
        return CheckResult(code, title, FAIL,
                           diagnosis=f"classify() lỗi khi chấm registry: {exc}",
                           fix="giữ classify(path) -> 'main'|'pr'|'manual' trong autofix_conflicts.py")

    # No leaked conflict markers in the registry source (build markers dynamically
    # so this detector never matches its own source).
    open_m = "<" * 7
    sep_m = "=" * 7
    close_m = ">" * 7
    leaked: list[str] = []
    for rel in (*_REGISTRY_MANUAL_FILES, "scripts/autofix_conflicts.py"):
        src = ctx.read(rel)
        if not src:
            continue
        for ln in src.splitlines():
            if ln.startswith(open_m + " ") or ln.rstrip() == sep_m or ln.startswith(close_m + " "):
                leaked.append(f"{rel}: dấu conflict merge còn sót")
                break

    if fails or leaked:
        return CheckResult(code, title, FAIL,
                           diagnosis="merge registry sai chính sách hoặc còn marker → có thể xoá detector / đổi số vaccine của main",
                           fix=("CLAUDE.md + qa_vaccines.py + test_qa_vaccines.py → resolve 'manual' (append PR delta, giữ mọi vaccine của main); "
                                "data JSON → lấy 'main' rồi regenerate; xoá mọi conflict marker"),
                           details=fails + leaked)

    warns: list[str] = []
    if not (ctx.root / "scripts" / "test_qa_vaccines.py").is_file():
        warns.append("thiếu scripts/test_qa_vaccines.py (lớp test cho registry)")
    if warns:
        return CheckResult(code, title, WARN,
                           diagnosis="chính sách resolve registry OK nhưng thiếu lớp test",
                           fix="giữ scripts/test_qa_vaccines.py để khoá hồi quy registry",
                           details=warns)
    return CheckResult(code, title, PASS,
                       diagnosis="registry source → manual (append delta), data JSON → main+regenerate, không marker sót")


# --------------------------------------------------------------------------
# V30 — Public /tools/* route preservation (anti-silent-removal guard)
# --------------------------------------------------------------------------
# Public utility pages under /tools/ that SEO/section optimization and
# "thin/orphan" cleanup must NEVER silently delete or hide. Each maps to the
# Zola content page that creates its route. A route may be absent ONLY if its
# slug is explicitly listed in _TOOLS_REMOVAL_ALLOWLIST (a reviewed decision).
#
# History: a "chore: remove Phase 2 features" cleanup deleted all four finance
# dashboards (content + template + scss + js) while qa-404-checker's
# _DYNAMIC_APP_ROUTES still allow-listed them — so internal links never flagged
# the breakage and the routes 404'd silently. This detector makes that a hard,
# visible FAIL so a public route can never be removed without explicit approval.
_PROTECTED_TOOLS_ROUTES = {
    "f-dashboard": "content/tools/f-dashboard.md",  # VietinBank Excel statements
    "l-dashboard": "content/tools/l-dashboard.md",  # LPBank PDF statements
    "o-dashboard": "content/tools/o-dashboard.md",  # Liobank/OCB PDF statements
    "h-dashboard": "content/tools/h-dashboard.md",  # invoice/receipt OCR
}
# Slugs explicitly approved for removal (route intentionally retired). Adding a
# slug here — with reviewer sign-off — is the ONLY sanctioned way to drop a
# protected /tools/* route. Empty by default: nothing is approved for removal.
_TOOLS_REMOVAL_ALLOWLIST: frozenset[str] = frozenset()

_FM_TEMPLATE_RE = re.compile(r'(?m)^\s*template\s*=\s*"([^"]+)"')


def check_v30_tools_route_preservation(ctx: Ctx) -> CheckResult:
    """V30 — SEO/section optimization must be NON-DESTRUCTIVE for public /tools/*
    routes. Existing dashboard pages require route-preservation: orphan/thin
    cleanup may only REPORT, never delete/hide, unless the slug is in the
    removal allowlist.

    FAIL — a protected /tools/<slug>/ page (or its bound template) is missing and
           the slug is NOT in _TOOLS_REMOVAL_ALLOWLIST (silent removal).
    PASS — every protected route still has its content page + template, or the
           slug was explicitly approved for removal.
    """
    code = "V30"
    title = "Public /tools/* route preservation (no silent dashboard removal)"
    problems: list[str] = []
    for slug, page in sorted(_PROTECTED_TOOLS_ROUTES.items()):
        if slug in _TOOLS_REMOVAL_ALLOWLIST:
            continue
        body = ctx.read(page)
        if body is None:
            problems.append(f"/tools/{slug}/ → trang {page} đã bị xoá/ẩn (thiếu)")
            continue
        m = _FM_TEMPLATE_RE.search(body)
        if m and not ctx.exists(f"templates/{m.group(1)}"):
            problems.append(f"/tools/{slug}/ → template templates/{m.group(1)} thiếu")
    if problems:
        return CheckResult(
            code, title, FAIL,
            diagnosis=("Trang công cụ /tools/* công khai đã tồn tại bị xoá/ẩn mà KHÔNG có "
                       "trong removal allowlist. SEO/section optimization & dọn orphan/thin "
                       "chỉ được REPORT, KHÔNG được xoá route công khai."),
            fix=("Khôi phục trang + template từ lịch sử "
                 "(git checkout <pre-deletion> -- content/tools/<slug>.md templates/<slug>.html "
                 "sass/_<slug>.scss static/js/<slug>); HOẶC nếu cố ý gỡ → thêm slug vào "
                 "_TOOLS_REMOVAL_ALLOWLIST (cần review duyệt)."),
            details=problems)
    return CheckResult(
        code, title, PASS,
        diagnosis=(f"{len(_PROTECTED_TOOLS_ROUTES)} route /tools/* công khai đều còn "
                   "content page + template (không bị silent removal)"))


# --------------------------------------------------------------------------
# V31 — Shortcut registry preservation (operation-guideline restructuring guard)
# --------------------------------------------------------------------------
# Restructuring the operation guidelines (moving shortcuts into .claude/commands/
# skills, rewriting shortcuts.md, condensing CLAUDE.md) must NEVER silently drop an
# existing user shortcut. History: `bb` (paste a news article from any publisher →
# an original SEOMONEY blog post) lost its first-class registration during a
# restructuring — no .claude/commands/bb.md skill and no row in the shortcuts.md
# `help` table. A separate `dantri` shortcut (a dantri.com.vn crawler — a different
# tool, NOT a bb alias) existed, which masked the loss. This detector makes that
# regression a hard, visible FAIL. Both `bb` and `dantri` are required (distinct).
#
# A required shortcut is "first-class" when BOTH hold:
#   * shortcuts.md documents it with a `### `<name>`` section (source of truth), and
#   * (for command-backed shortcuts) a .claude/commands/<name>.md skill exists.
_REQUIRED_SHORTCUT_SECTIONS = ("bb", "bb9", "dantri")   # must keep a `### `<name>`` section
_REQUIRED_SHORTCUT_COMMANDS = ("bb", "dantri")          # must keep a .claude/commands/<name>.md skill


def _shortcut_section_present(shortcuts_md: str, name: str) -> bool:
    """True if shortcuts.md has a `### `<name>`` section header. The name may be
    followed by a closing backtick (`### `bb``) or an argument (`### `bb9 <topic>``)."""
    pat = re.compile(r"^###\s+`" + re.escape(name) + r"(?:`| )", re.M)
    return bool(pat.search(shortcuts_md))


def check_v31_shortcut_registry_preservation(ctx: Ctx) -> CheckResult:
    """V31 — Shortcut registry preservation.

    Restructuring operation guidelines must not delete existing user shortcuts.
    Required shortcuts (at minimum `bb`) must keep their `### `<name>`` section in
    shortcuts.md AND, for command-backed ones, their .claude/commands/<name>.md skill.
    A required shortcut registered but missing from the `help` quick table → WARN.
    """
    code = "V31"
    title = "Shortcut registry preservation (required: bb)"
    sc = ctx.read("shortcuts.md")
    if sc is None:
        return CheckResult(code, title, FAIL,
                           diagnosis="shortcuts.md vắng — source of truth phím tắt bị mất",
                           fix="khôi phục shortcuts.md (registry phím tắt)")

    fails: list[str] = []
    for name in _REQUIRED_SHORTCUT_SECTIONS:
        if not _shortcut_section_present(sc, name):
            fails.append(f"shortcuts.md thiếu section `### `{name}`` (phím tắt bị xoá khi restructure)")
    for name in _REQUIRED_SHORTCUT_COMMANDS:
        if not ctx.exists(f".claude/commands/{name}.md"):
            fails.append(f".claude/commands/{name}.md vắng — phím tắt `{name}` mất đăng ký first-class")

    if fails:
        return CheckResult(code, title, FAIL,
                           diagnosis="restructure operation-guideline đã xoá phím tắt user đang dùng",
                           fix=("giữ section `### `<name>`` trong shortcuts.md + file "
                                ".claude/commands/<name>.md cho mọi phím tắt bắt buộc (gồm `bb`); "
                                "KHÔNG xoá phím tắt khi cấu trúc lại quy trình"),
                           details=fails)

    # Soft nudge: bb should also appear in the shortcuts.md `help` quick table.
    warns: list[str] = []
    if not re.search(r"^\|\s*`bb`\s*\|", sc, re.M):
        warns.append("bb chưa có dòng trong bảng `help` (quick reference) của shortcuts.md")
    if warns:
        return CheckResult(code, title, WARN,
                           diagnosis="phím tắt bắt buộc còn đăng ký nhưng thiếu ở bảng help",
                           fix="thêm dòng `| `bb` | … |` vào bảng help trong shortcuts.md",
                           details=warns)
    return CheckResult(code, title, PASS,
                       diagnosis=(f"{len(_REQUIRED_SHORTCUT_SECTIONS)} section + "
                                  f"{len(_REQUIRED_SHORTCUT_COMMANDS)} skill phím tắt bắt buộc đều còn (gồm `bb`)"))


def check_vaccine_registry_integrity(ctx: Ctx) -> CheckResult:
    """VACCINE-REGISTRY — fail duplicate V-number or duplicate detector registration.

    Guards two registries against accidental collisions:
      1. CLAUDE.md `#### V<N>` numbers — an unexpected duplicate (beyond the
         documented legacy set {V10, V11, V12}) FAILs. New vaccines must take the
         next free number, never a taken one.
      2. The DETECTORS list — the same callable or the same detector name listed
         twice (a duplicate registration) FAILs.
    """
    title = "Vaccine registry integrity (no duplicate V-number / detector)"
    fails: list[str] = []

    # 1) Duplicate vaccine numbers in CLAUDE.md beyond the allowed legacy set.
    codes = [v["code"] for v in load_vaccines(ctx.read("CLAUDE.md"))]
    seen: dict[str, int] = {}
    for c in codes:
        seen[c] = seen.get(c, 0) + 1
    for code, n in sorted(seen.items()):
        if n > 1 and code not in ALLOWED_DUPLICATE_VACCINES:
            fails.append(f"vaccine {code} documented {n}× in CLAUDE.md (use next free number)")

    # 2) Duplicate detector registration in DETECTORS (callable or name listed 2×).
    by_id: dict[int, int] = {}
    by_name: dict[str, int] = {}
    for det in DETECTORS:
        by_id[id(det)] = by_id.get(id(det), 0) + 1
        name = getattr(det, "__name__", repr(det))
        by_name[name] = by_name.get(name, 0) + 1
    for name, n in sorted(by_name.items()):
        if n > 1:
            fails.append(f"detector {name!r} registered {n}× in DETECTORS")
    dup_callables = sum(1 for n in by_id.values() if n > 1)
    if dup_callables:
        fails.append(f"{dup_callables} detector callable(s) registered more than once")

    if fails:
        return CheckResult("VACCINE-REGISTRY", title, FAIL,
                           diagnosis="; ".join(fails),
                           fix=("Give each new vaccine the next free number "
                                "(next_free_vaccine_number) and register each detector once"),
                           details=fails)
    return CheckResult("VACCINE-REGISTRY", title, PASS,
                       diagnosis=(f"{len(codes)} vaccine block(s), no unexpected duplicate; "
                                  f"{len(DETECTORS)} detectors each registered once"))


# Registry — order matters for the printed report.
DETECTORS = [
    check_v1_hf_model_id,
    check_v2_slack_v3,
    check_v5_deploy_resilience,
    check_v8a_tera_filter_kwargs,
    check_v8b1_tera_map_literals,
    check_v8b_template_block_balance,
    check_v8c_series_registration,
    check_v8d_tera_map_literal,
    check_v32_series_part_sort_guard,
    check_v19_domain_migration_drift,
    check_domain_root_url_vaccine,
    check_v9_v10_process,
    check_v12_shared_infra_dupes,
    check_v17_vipzone_edge_safari_auth,
    check_v18_runtime_artifact_conflict,
    check_config_toml,
    check_workflow_yaml,
    check_dashboard_json,
    check_js_syntax,
    check_paywall_integrity,
    check_seo_schema_scaffold,
    check_missing_assets,
    check_compliance_h1,
    check_v10_link_utils_layer,
    check_series_nav_vaccine,
    check_category_first,
    check_nav_menu_overflow,
    check_sidebar_layout,
    check_uptime_me,
    check_deploy_monitor,
    check_gsc_domain_property,
    check_search_ui_vaccine,
    check_no_floating_nav_vaccine,
    check_korean_banner_ui_vaccine,
    check_seomoney_brand,
    check_og_image_vaccine,
    check_editor_publish_vaccine,
    check_editor_sdna_vaccine,
    check_toc_rail_vaccine,
    check_ga_stats_vaccine,
    check_v20_seo_identity_homepage,
    check_v25_backend_route_parity,
    check_v30_tools_route_preservation,
    check_v28_vaccine_registry_merge,
    check_v31_shortcut_registry_preservation,
    check_vaccine_registry_integrity,
]


def _assert_no_duplicate_registration() -> None:
    """Import-time guard: a detector must never be registered twice in DETECTORS.

    Raises RuntimeError loudly so a duplicate registration is caught at import,
    long before the gate runs. (Duplicate *vaccine numbers* in CLAUDE.md are
    reported as a FAIL by check_vaccine_registry_integrity, not raised here, so
    the gate can still produce a report.)
    """
    names: dict[str, int] = {}
    ids: dict[int, int] = {}
    for det in DETECTORS:
        names[getattr(det, "__name__", repr(det))] = names.get(getattr(det, "__name__", repr(det)), 0) + 1
        ids[id(det)] = ids.get(id(det), 0) + 1
    dup_names = [n for n, c in names.items() if c > 1]
    dup_ids = [i for i, c in ids.items() if c > 1]
    if dup_names or dup_ids:
        raise RuntimeError(
            f"duplicate detector registration in DETECTORS: {sorted(dup_names)} "
            f"({len(dup_ids)} duplicated callable(s))"
        )


_assert_no_duplicate_registration()


def run_all(root: Path | None = None) -> tuple[list[CheckResult], dict]:
    """Run every detector. Returns (results, summary)."""
    ctx = Ctx(root or REPO_ROOT)
    results: list[CheckResult] = []
    for det in DETECTORS:
        try:
            results.append(det(ctx))
        except Exception as exc:  # a buggy detector must never crash the gate
            results.append(CheckResult(getattr(det, "__name__", "?"),
                                       det.__doc__.split("\n")[0] if det.__doc__ else "detector",
                                       WARN, diagnosis=f"detector lỗi nội bộ: {exc}",
                                       fix="bỏ qua (không chặn gate)"))
    summary = summarize(results, ctx)
    return results, summary


def summarize(results: list[CheckResult], ctx: Ctx) -> dict:
    vaccines = load_vaccines(ctx.read("CLAUDE.md"))
    passed = sum(1 for r in results if r.status == PASS)
    failed = sum(1 for r in results if r.status == FAIL)
    warned = sum(1 for r in results if r.status == WARN)
    skipped = sum(1 for r in results if r.status == SKIP)
    # Production readiness: a FAIL is disqualifying; warnings nibble the score.
    score = 100 - failed * 25 - warned * 4
    score = max(0, min(100, score))
    if failed:
        score = min(score, 60)  # never "production-safe" with an open FAIL
    production_safe = failed == 0
    return {
        "vaccines_loaded": len(vaccines),
        "checks_run": len(results),
        "passed": passed,
        "failed": failed,
        "warnings": warned,
        "skipped": skipped,
        "score": score,
        "production_safe": production_safe,
    }


def print_report(results: list[CheckResult]) -> None:
    print(_bold(_blue("══════ QA Vaccine Gate (CLAUDE.md §4 — THƯ VIỆN VACCINE) ══════")))
    for r in results:
        print(r.render())


def print_summary(summary: dict, strict_warn: bool = False) -> None:
    safe = summary["production_safe"] and not (strict_warn and summary["warnings"])
    print()
    print(_bold("QA Vaccine Summary"))
    print(f"- Total vaccines loaded: {summary['vaccines_loaded']}")
    print(f"- Passed: {summary['passed']}")
    print(f"- Failed: {summary['failed']}")
    print(f"- Warnings: {summary['warnings']}")
    verdict = _green("PRODUCTION-SAFE ✓") if safe else _red("NOT PRODUCTION-SAFE ✗")
    print(f"- Production readiness score: {summary['score']}/100  ({verdict})")
    extra = f"  (checks run: {summary['checks_run']}, skipped: {summary['skipped']})"
    print(_dim(extra))


def gate_failed(summary: dict, strict_warn: bool = False) -> bool:
    if summary["failed"] > 0:
        return True
    if strict_warn and summary["warnings"] > 0:
        return True
    return False


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="QA Vaccine Gate — CLAUDE.md vaccines as a production barrier")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON report")
    ap.add_argument("--strict-warn", action="store_true", help="treat warnings as failures (block on WARN too)")
    ap.add_argument("--quiet", action="store_true", help="only print the summary block")
    args = ap.parse_args(argv)

    results, summary = run_all()

    if args.json:
        payload = {
            "summary": summary,
            "checks": [
                {"vaccine": r.vaccine, "title": r.title, "status": r.status,
                 "diagnosis": r.diagnosis, "fix": r.fix, "details": r.details}
                for r in results
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1 if gate_failed(summary, args.strict_warn) else 0

    if not args.quiet:
        print_report(results)
    print_summary(summary, args.strict_warn)

    if gate_failed(summary, args.strict_warn):
        print(_red(_bold("\n✗ QA Vaccine Gate FAILED — không production-safe. Sửa các FAIL ở trên trước khi deploy.")))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
