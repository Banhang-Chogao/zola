#!/usr/bin/env python3
"""Domain Migration Audit — github.io/zola → https://seomoney.org

Scans the repo for post-migration drift: stale old-domain refs in operational
files, snapshot URL mismatch, open doc TODOs, and repo invariants (CNAME /
base_url / robots sitemap).

Strictly OFFLINE — no DNS or HTTP checks (use scripts/dns_vaccine.py --gate
for live checks). Stdlib only.

Usage
-----
    python3 scripts/domain_migration_audit.py          # full audit, exit 2 on FAIL
    python3 scripts/domain_migration_audit.py --json   # machine-readable to stdout
    python3 scripts/domain_migration_audit.py --gate   # exit 2 on any FAIL or WARN
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
VN_TZ = timezone(timedelta(hours=7))

OLD_HOST = "banhang-chogao.github.io"
OLD_SUBPATH = "/zola"
OLD_ORIGIN_PAT = re.compile(r"banhang-chogao\.github\.io/zola", re.IGNORECASE)
TYPO_PAT = re.compile(r"seomomey\.org|seommoney\.org|seomony\.org", re.IGNORECASE)

# Files / dirs that legitimately reference the old host (do NOT flag):
EXCLUDED_PATHS = {
    "scripts/dns_vaccine.py",           # PAGES_ORIGIN_HOST = correct www-CNAME target
    "scripts/rewrite_cdn_urls.py",      # migration-tool docstring examples
    "scripts/fix_site_prefix_links.py", # migration-tool docstring examples
    "scripts/domain_migration_audit.py",# self
    "scripts/qa_vaccines.py",           # V19 detector docstring + other vaccine descriptions
    "CLAUDE.md",                        # vaccine library legitimately documents old domain
    "data/merge-report.json",           # historical summaries
    "data/dns-vaccine-report.json",     # correct: www_cname = banhang-chogao.github.io
    "data/performance-audit-snapshot.json",  # checked separately (snapshot check)
    "changelog.json",                   # historical notes
    ".git",
    ".venv",
    "node_modules",
}
# Tutorial content explaining how GitHub Pages works — legitimate article text
EXCLUDED_CONTENT = {
    "content/posting/tao-blog-voi-zola.md",
    "content/posting/tu-dong-deploy-zola-github-actions.md",
    "content/posting/ung-ho-du-an-ai-ten-mien-ai.md",
}
# Test fixtures that use old domain to validate normalization logic
EXCLUDED_TEST_FIXTURES = re.compile(r"scripts/test_")

SCAN_SUFFIXES = {".py", ".yml", ".yaml", ".html", ".js", ".scss", ".toml", ".md", ".txt", ".json"}

PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"


@dataclass
class Finding:
    area: str
    issue: str
    fix: str
    status: str
    insight: str = ""
    details: list[str] = field(default_factory=list)


def _read_base_url() -> str:
    cfg = REPO / "config.toml"
    if not cfg.exists():
        return ""
    for line in cfg.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("base_url") and "=" in s:
            return s.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _read_cname() -> str:
    f = REPO / "static" / "CNAME"
    if not f.exists():
        return ""
    return f.read_text(encoding="utf-8").strip().splitlines()[0].strip()


def check_invariants() -> list[Finding]:
    findings: []
    findings = []
    base_url = _read_base_url()
    cname = _read_cname()

    # R1: CNAME exists
    if not cname:
        findings.append(Finding(
            area="CNAME", issue="static/CNAME missing",
            fix="Create static/CNAME with domain apex (e.g. seomoney.org)",
            status=FAIL, insight="GitHub Pages needs CNAME for custom domain"))
    elif "github.io" in cname:
        findings.append(Finding(
            area="CNAME", issue=f"static/CNAME still holds github.io value: {cname!r}",
            fix=f"Replace with apex domain in static/CNAME",
            status=FAIL, insight="Custom domain not configured"))
    else:
        findings.append(Finding(
            area="CNAME", issue="none", fix="—", status=PASS,
            insight=f"CNAME = {cname}"))

    # R2: base_url host matches CNAME
    if base_url:
        from urllib.parse import urlparse
        host = urlparse(base_url).netloc
        if host != cname and cname:
            findings.append(Finding(
                area="config.toml base_url", issue=f"host mismatch: base_url={host!r} ≠ CNAME={cname!r}",
                fix="Align config.toml base_url host with static/CNAME",
                status=FAIL, insight="drift causes broken canonical URLs"))
        elif "github.io" in base_url or "/zola" in urlparse(base_url).path:
            findings.append(Finding(
                area="config.toml base_url", issue=f"base_url still has old path: {base_url!r}",
                fix="Update config.toml base_url to https://seomoney.org",
                status=FAIL, insight="V14 fabricated links + V8 series would resurface"))
        else:
            findings.append(Finding(
                area="config.toml base_url", issue="none", fix="—", status=PASS,
                insight=f"base_url = {base_url}"))
    else:
        findings.append(Finding(
            area="config.toml base_url", issue="base_url not found in config.toml",
            fix="Add base_url to config.toml", status=FAIL, insight=""))

    # R3: robots.txt sitemap URL
    robots = REPO / "static" / "robots.txt"
    if robots.exists():
        txt = robots.read_text(encoding="utf-8")
        sitemap_line = next((l for l in txt.splitlines() if l.startswith("Sitemap:")), "")
        if "github.io" in sitemap_line or "/zola" in sitemap_line:
            findings.append(Finding(
                area="robots.txt Sitemap", issue=f"old sitemap URL: {sitemap_line.strip()}",
                fix="Update Sitemap: to https://seomoney.org/sitemap.xml",
                status=FAIL, insight="GSC may pick up stale sitemap"))
        else:
            findings.append(Finding(
                area="robots.txt Sitemap", issue="none", fix="—", status=PASS,
                insight=sitemap_line.strip()))
    else:
        findings.append(Finding(
            area="robots.txt", issue="static/robots.txt missing",
            fix="Create robots.txt with Sitemap directive", status=WARN, insight=""))

    return findings


def check_snapshot() -> list[Finding]:
    snap = REPO / "data" / "performance-audit-snapshot.json"
    if not snap.exists():
        return [Finding(area="perf-audit snapshot", issue="data/performance-audit-snapshot.json missing",
                        fix="Run perf-audit.yml workflow", status=WARN, insight="")]
    try:
        data = json.loads(snap.read_text(encoding="utf-8"))
        url = data.get("url", "")
    except Exception:
        return [Finding(area="perf-audit snapshot", issue="JSON parse error",
                        fix="Regenerate via perf-audit.yml", status=WARN, insight="")]

    base_url = _read_base_url().rstrip("/") + "/"
    if "github.io" in url or "/zola" in url:
        return [Finding(
            area="perf-audit snapshot",
            issue=f"url field still holds old origin: {url!r}",
            fix="Trigger perf-audit.yml (fetch_pagespeed.py TARGET_URL is already seomoney.org — next run auto-fixes)",
            status=WARN, insight="Stale cached snapshot; does not affect live site")]
    if url and url != base_url:
        return [Finding(
            area="perf-audit snapshot",
            issue=f"url {url!r} ≠ base_url {base_url!r}",
            fix="Trigger perf-audit.yml to regenerate snapshot",
            status=WARN, insight="Minor drift; next workflow run fixes")]
    return [Finding(area="perf-audit snapshot", issue="none", fix="—", status=PASS,
                    insight=f"url = {url}")]


def check_typos() -> list[Finding]:
    hits: list[str] = []
    for p in REPO.rglob("*"):
        if not p.is_file():
            continue
        rel = str(p.relative_to(REPO))
        if any(ex in rel for ex in EXCLUDED_PATHS) or rel in EXCLUDED_CONTENT:
            continue
        if p.suffix not in SCAN_SUFFIXES:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for m in TYPO_PAT.finditer(text):
            hits.append(f"{rel}: {m.group()!r}")
    if hits:
        return [Finding(
            area="domain typo",
            issue=f"{len(hits)} typo variants of seomoney.org found",
            fix="Correct spelling to seomoney.org",
            status=FAIL, insight="Typos break canonical URLs + GSC property",
            details=hits[:10])]
    return [Finding(area="domain typo", issue="none", fix="—", status=PASS,
                    insight="no seomomey/seommoney/seomony variants")]


def check_stale_github_io_refs() -> list[Finding]:
    """Find github.io/zola in operational files (not excluded)."""
    hits: list[str] = []
    for p in REPO.rglob("*"):
        if not p.is_file():
            continue
        rel = str(p.relative_to(REPO))
        if any(ex in rel for ex in EXCLUDED_PATHS):
            continue
        if rel in EXCLUDED_CONTENT:
            continue
        if EXCLUDED_TEST_FIXTURES.match(rel.replace("\\", "/")):
            continue
        if p.suffix not in SCAN_SUFFIXES:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if OLD_ORIGIN_PAT.search(line):
                hits.append(f"{rel}:{lineno}: {line.strip()[:100]}")
    if hits:
        return [Finding(
            area="stale github.io/zola refs",
            issue=f"{len(hits)} occurrence(s) in operational files",
            fix="Replace banhang-chogao.github.io/zola → seomoney.org or remove stale comments",
            status=WARN,
            insight="Drift does not break build but misleads humans + future scripts",
            details=hits[:12])]
    return [Finding(area="stale github.io/zola refs", issue="none", fix="—", status=PASS,
                    insight="no operational github.io/zola refs outside exclusions")]


def run_audit() -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(check_invariants())
    findings.extend(check_snapshot())
    findings.extend(check_typos())
    findings.extend(check_stale_github_io_refs())
    return findings


def _status_icon(s: str) -> str:
    return {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️"}.get(s, s)


def print_table(findings: list[Finding]) -> None:
    # Header
    cols = ("Area", "Issue found", "Fix applied / needed", "Status", "Insight")
    widths = [max(len(c), max(len(f.area) for f in findings)) for c in cols]
    widths[0] = max(widths[0], 28)
    widths[1] = max(40, max(len(f.issue) for f in findings))
    widths[2] = 55
    widths[3] = 6
    widths[4] = 50

    def row(*cells):
        parts = []
        for w, c in zip(widths, cells):
            parts.append(str(c).ljust(w))
        print("| " + " | ".join(parts) + " |")

    sep = "|" + "|".join("-" * (w + 2) for w in widths) + "|"
    row(*cols)
    print(sep)
    for f in findings:
        row(f.area, f.issue[:widths[1]], f.fix[:widths[2]],
            _status_icon(f.status), f.insight[:widths[4]])
        for d in f.details[:5]:
            row("", f"  ↳ {d}"[:widths[1]], "", "", "")


def main() -> int:
    ap = argparse.ArgumentParser(description="Domain migration audit: github.io → seomoney.org")
    ap.add_argument("--json", action="store_true", help="output JSON to stdout")
    ap.add_argument("--gate", action="store_true", help="exit 2 on any FAIL or WARN")
    args = ap.parse_args()

    findings = run_audit()
    fails = [f for f in findings if f.status == FAIL]
    warns = [f for f in findings if f.status == WARN]
    passes = [f for f in findings if f.status == PASS]

    now_vn = datetime.now(VN_TZ).strftime("%H:%M %d/%m/%Y")

    if args.json:
        out = {
            "generated_at": now_vn,
            "total": len(findings),
            "failed": len(fails),
            "warned": len(warns),
            "passed": len(passes),
            "findings": [
                {"area": f.area, "issue": f.issue, "fix": f.fix,
                 "status": f.status, "insight": f.insight, "details": f.details}
                for f in findings
            ],
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print("\n## Domain Migration Audit — github.io → seomoney.org\n")
        print_table(findings)
        print(f"\n**Total:** {len(findings)}  **FAIL:** {len(fails)}  "
              f"**WARN:** {len(warns)}  **PASS:** {len(passes)}")
        print(f"**Scanned at:** {now_vn} (GMT+7)\n")

        if fails:
            print("### ❌ FAIL — must fix before merging:")
            for f in fails:
                print(f"  • {f.area}: {f.issue}")
                for d in f.details[:5]:
                    print(f"      ↳ {d}")
        if warns:
            print("### ⚠️  WARN — cleanup recommended:")
            for f in warns:
                print(f"  • {f.area}: {f.issue}")
                for d in f.details[:5]:
                    print(f"      ↳ {d}")

    exit_code = 0
    if fails:
        exit_code = 2
    elif args.gate and warns:
        exit_code = 2
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
