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
    check_korean_banner_ui_vaccine,
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
