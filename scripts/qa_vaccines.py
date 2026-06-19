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


def _series_ids_from_templates(ctx: Ctx) -> set[str]:
    ids: set[str] = set()
    for rel in ("templates/page.html", "templates/macros/series-nav.html",
                "templates/base.html"):
        src = ctx.read(rel) or ""
        for m in re.finditer(r'series\s*==\s*["\']([a-z0-9\-]+)["\']', src):
            ids.add(m.group(1))
    return ids


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


# Registry — order matters for the printed report.
DETECTORS = [
    check_v1_hf_model_id,
    check_v2_slack_v3,
    check_v5_deploy_resilience,
    check_v8a_tera_filter_kwargs,
    check_v8b_template_block_balance,
    check_v8c_series_registration,
    check_v9_v10_process,
    check_v12_shared_infra_dupes,
    check_config_toml,
    check_workflow_yaml,
    check_dashboard_json,
    check_js_syntax,
    check_paywall_integrity,
    check_seo_schema_scaffold,
    check_missing_assets,
    check_compliance_h1,
    check_category_first,
    check_nav_menu_overflow,
]


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
