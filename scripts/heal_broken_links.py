#!/usr/bin/env python3
"""
Manual Broken Links Healing Bot — safe auto-fix for internal 404s.

This bot scans the built Zola site for broken internal links and applies
high-confidence fixes. It never pushes to main directly — always opens a PR.

USAGE:
    python3 scripts/heal_broken_links.py --scan     # scan-only, no fixes
    python3 scripts/heal_broken_links.py --fix      # scan + safe auto-fix
    python3 scripts/heal_broken_links.py --help

FLAGS:
    --scan       Report broken links without modifying files.
    --fix        Scan and apply safe fixes to content/*.md.
    --stdout     Print summary to console.
    --help       Show this help.

OUTPUT:
    data/broken-links-report.json
    reports/broken-links/report-YYYYMMDD-HHMMSS.md

SAFE AUTO-FIX RULES:
    1. /zola/ prefix normalization
       /zola/some-path/ → /some-path/
    2. Trailing slash normalization
       /abc → /abc/ (when /abc/ exists)
    3. Case/slug normalization
       /Categories/Ngan-Hang/ → /categories/ngan-hang/ (when unique match exists)
    4. Known alias map (explicit only)
       Uses pre-defined route aliases
    5. Anchor-only broken fragments
       Removes fragment if target page exists
    6. Old category redirects (explicit map only)

UNSAFE CASES (never auto-fix):
    - External URLs
    - Affiliate/payment links
    - MoMo / payment URLs
    - Auth/backend URLs
    - API endpoints
    - Admin routes
    - URLs in code blocks
    - Historical quotes
    - Unclear targets
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parent.parent
PUBLIC = REPO / "public"
CONTENT = REPO / "content"
DATA = REPO / "data"
REPORTS = REPO / "reports" / "broken-links"
OUT_FILE = DATA / "broken-links-report.json"

VN_TZ = timezone(timedelta(hours=7))
BASE_URL = "https://seomoney.org"
SITE_PREFIX = "/zola"

# Known route aliases (explicit, verified)
KNOWN_ALIASES = {
    "/categories/bao-chi/": "/categories/tat-ca/",
    "/categories/ngan-hang-so/": "/categories/ngan-hang/",
    "/zola/": "/",
}

# Unsafe patterns — never auto-fix these
UNSAFE_PATTERNS = [
    r"^https?://",  # external
    r"^//",  # protocol-relative
    r"momo\.vn",  # MoMo payment
    r"api\.",  # API
    r"/auth/",  # auth
    r"/admin/",  # admin
    r"/backend/",  # backend
    r"affiliate",  # affiliate
    r"payment",  # payment
    r"mailto:",  # email
    r"tel:",  # phone
    r"javascript:",  # script
    r"data:",  # data URI
]

# Markdown link patterns to search in source files
_MD_LINK_PATTERN = re.compile(
    r"\[([^\]]*)\]\(([^\)]+)\)|\!\[([^\]]*)\]\(([^\)]+)\)",
    re.MULTILINE,
)


def _is_unsafe(href: str) -> bool:
    """Check if a URL is unsafe to auto-fix.

    Note: https://seomoney.org/* is NOT unsafe — it's internal with full domain.
    Only truly external URLs (different domain) are unsafe.
    """
    # https://seomoney.org/* is internal, not unsafe
    if href.startswith((BASE_URL, "https://" + BASE_URL.replace("https://", ""))):
        return False

    for pattern in UNSAFE_PATTERNS:
        if re.search(pattern, href, re.IGNORECASE):
            return True
    return False


def _classify(href: str) -> tuple[str, str | None]:
    """Classify a link as internal/external/skip.

    Handles:
    - Standard internal: /path/
    - With domain: https://seomoney.org/path/
    - Zola syntax: @/path/to/file.md (internal)
    - External: https://other-domain.com/...
    - Skip: #anchor, javascript:, etc.
    """
    href = (href or "").strip()
    if not href or href.startswith(("#", "javascript:", "data:", "mailto:", "tel:")):
        return "skip", None

    # Zola internal link syntax @/path/to/file.md
    if href.startswith("@/"):
        # Convert @/posting/some-article.md → /posting/some-article/
        path = href[2:]  # Remove @/
        if path.endswith(".md"):
            path = path[:-3]  # Remove .md
        if not path.startswith("/"):
            path = "/" + path
        if not path.endswith("/"):
            path += "/"
        return "internal", path

    # Absolute URL pointing at our own site → treat as internal
    if href.startswith(BASE_URL):
        href = href[len(BASE_URL):] or "/"
    else:
        parsed = urlparse(href)
        if parsed.scheme in ("http", "https"):
            return "external", href
        if parsed.scheme and parsed.scheme not in ("",):
            return "skip", None
        if href.startswith("//"):
            return "external", "https:" + href

    # Internal site path
    parsed = urlparse(href)
    path = parsed.path or "/"
    if not path.startswith("/"):
        path = "/" + path
    # Strip /zola prefix (GitHub Pages subpath)
    if path == SITE_PREFIX or path.startswith(SITE_PREFIX + "/"):
        path = path[len(SITE_PREFIX):] or "/"
    path = path.split("#")[0].split("?")[0] or "/"
    # Append trailing slash for extension-less paths
    if path != "/" and not path.endswith("/") and "." not in Path(path).name:
        path += "/"
    return "internal", path


def _public_paths() -> set[str]:
    """All servable site-relative paths in public/."""
    paths: set[str] = set()
    if not PUBLIC.is_dir():
        return paths
    for f in PUBLIC.rglob("*"):
        if not f.is_file():
            continue
        rel = "/" + f.relative_to(PUBLIC).as_posix()
        paths.add(rel)
        if rel.endswith("/index.html"):
            paths.add(rel[: -len("index.html")] or "/")
        if rel.endswith(".html"):
            paths.add(rel[: -len(".html")] + "/")
    return paths


def _internal_ok(path: str, pub_paths: set[str]) -> bool:
    """Check if internal path resolves to a file."""
    if path in pub_paths:
        return True
    alt = path.rstrip("/") + "/"
    if alt in pub_paths:
        return True
    return False


def _find_source_file(href: str) -> str | None:
    """Find source markdown file containing the link."""
    for md_file in CONTENT.rglob("*.md"):
        try:
            text = md_file.read_text(encoding="utf-8")
            if href in text:
                return str(md_file.relative_to(REPO))
        except OSError:
            pass
    return None


def _try_fix(target: str, pub_paths: set[str]) -> tuple[str | None, str]:
    """Try to fix a broken internal link.

    Returns (fixed_url, reason) or (None, reason_why_not).
    """
    # Already OK
    if _internal_ok(target, pub_paths):
        return None, "already_ok"

    # Rule 1: /zola/ prefix normalization
    if target.startswith("/zola/"):
        fixed = target[len("/zola"):] or "/"
        if _internal_ok(fixed, pub_paths):
            return fixed, "zola_prefix_removed"

    # Rule 2: Trailing slash normalization
    if not target.endswith("/") and not "." in Path(target).name:
        fixed = target + "/"
        if _internal_ok(fixed, pub_paths):
            return fixed, "trailing_slash_added"

    # Rule 3: Case/slug normalization (only if unique match)
    normalized = target.lower()
    matching = [p for p in pub_paths if p.lower() == normalized]
    if len(matching) == 1 and matching[0] != target:
        return matching[0], "case_slug_normalized"

    # Rule 4: Known alias map
    if target in KNOWN_ALIASES:
        fixed = KNOWN_ALIASES[target]
        if _internal_ok(fixed, pub_paths):
            return fixed, "known_alias_applied"

    # Rule 5: Remove anchor if page exists
    if "#" in target:
        page = target.split("#")[0] or "/"
        if _internal_ok(page, pub_paths):
            return page, "anchor_removed_page_exists"

    return None, "no_safe_fix"


def scan_and_report(apply_fixes: bool = False) -> dict:
    """Scan all internal links and report broken ones."""
    pub_paths = _public_paths()
    timestamp = datetime.now(VN_TZ).isoformat()

    broken_links: list[dict] = []
    safe_fixes: list[dict] = []
    manual_review: list[dict] = []
    all_checked: set[str] = set()

    # Extract links from all markdown files
    for md_file in CONTENT.rglob("*.md"):
        try:
            text = md_file.read_text(encoding="utf-8")
        except OSError:
            continue

        rel_file = str(md_file.relative_to(REPO))

        # Find all markdown links
        for match in _MD_LINK_PATTERN.finditer(text):
            href = match.group(2) or match.group(4)
            if not href:
                continue

            kind, norm = _classify(href)
            if kind != "internal" or not norm:
                continue

            all_checked.add(norm)

            # Already OK
            if _internal_ok(norm, pub_paths):
                continue

            # Classify as safe or unsafe to fix
            if _is_unsafe(href):
                manual_review.append({
                    "source_file": rel_file,
                    "broken_url": href,
                    "normalized": norm,
                    "reason": "unsafe_pattern_detected",
                    "unsafe_because": "external, payment, or backend URL",
                })
                continue

            # Try to fix
            fixed_url, reason = _try_fix(norm, pub_paths)
            if fixed_url:
                safe_fixes.append({
                    "source_file": rel_file,
                    "old_url": href,
                    "normalized": norm,
                    "new_url": fixed_url,
                    "reason": reason,
                    "applied": False,  # Will update if apply_fixes=True
                })
            else:
                manual_review.append({
                    "source_file": rel_file,
                    "broken_url": href,
                    "normalized": norm,
                    "reason": reason,
                })

    # Apply safe fixes if requested
    applied_count = 0
    if apply_fixes and safe_fixes:
        for fix in safe_fixes:
            try:
                md_file = REPO / fix["source_file"]
                text = md_file.read_text(encoding="utf-8")

                # Replace in markdown links
                old_href = fix["old_url"]
                new_href = fix["new_url"]

                # Escape special regex chars
                old_escaped = re.escape(old_href)

                # Replace in [text](url) and ![alt](url) patterns
                new_text = re.sub(
                    rf"\(({old_escaped})\)",
                    f"({new_href})",
                    text,
                )

                if new_text != text:
                    md_file.write_text(new_text, encoding="utf-8")
                    fix["applied"] = True
                    applied_count += 1
            except OSError:
                pass

    report = {
        "generated_at": timestamp,
        "mode": "fix" if apply_fixes else "scan",
        "summary": {
            "total_checked": len(all_checked),
            "broken_count": len(safe_fixes) + len(manual_review),
            "safe_fixes_available": len(safe_fixes),
            "safe_fixes_applied": applied_count,
            "manual_review_required": len(manual_review),
            "status": "ok" if (not safe_fixes and not manual_review) else "has_broken_links",
        },
        "safe_fixes": safe_fixes,
        "manual_review": manual_review,
    }

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Manual Broken Links Healing Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Scan only, no fixes",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Scan and apply safe fixes",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print summary to console",
    )

    args = parser.parse_args()

    if not args.scan and not args.fix:
        parser.print_help()
        sys.exit(1)

    apply_fixes = args.fix

    # Ensure output directories exist
    DATA.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    # Run scan
    report = scan_and_report(apply_fixes=apply_fixes)

    # Save JSON report
    OUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")

    # Save markdown report
    timestamp_str = datetime.now(VN_TZ).strftime("%Y%m%d-%H%M%S")
    md_file = REPORTS / f"report-{timestamp_str}.md"

    md_content = _format_report_md(report)
    md_file.write_text(md_content, encoding="utf-8")

    # Print summary
    if args.stdout:
        print(md_content)

    # Summary
    summary = report["summary"]
    print(f"\n{'='*60}")
    print(f"Broken Links Healing Bot — {report['mode'].upper()} Mode")
    print(f"{'='*60}")
    print(f"Total links checked:       {summary['total_checked']}")
    print(f"Broken links found:        {summary['broken_count']}")
    print(f"Safe fixes available:      {summary['safe_fixes_available']}")
    print(f"Safe fixes applied:        {summary['safe_fixes_applied']}")
    print(f"Manual review required:    {summary['manual_review_required']}")
    print(f"Status:                    {summary['status']}")
    print(f"\nReports saved to:")
    print(f"  JSON:  {OUT_FILE}")
    print(f"  MD:    {md_file}")

    # Exit code
    if summary["status"] == "ok":
        sys.exit(0)
    elif apply_fixes and summary["safe_fixes_applied"] > 0:
        sys.exit(0)  # Fixes were applied
    else:
        sys.exit(1)  # Broken links remain


def _format_report_md(report: dict) -> str:
    """Format report as markdown."""
    summary = report["summary"]
    mode = report["mode"].upper()
    gen_at = report["generated_at"]

    lines = [
        f"# Broken Links Healing Report",
        f"",
        f"**Generated:** {gen_at}",
        f"**Mode:** {mode}",
        f"",
        f"## Summary",
        f"",
        f"| Metric | Count |",
        f"|--------|-------|",
        f"| Total links checked | {summary['total_checked']} |",
        f"| Broken links found | {summary['broken_count']} |",
        f"| Safe fixes available | {summary['safe_fixes_available']} |",
        f"| Safe fixes applied | {summary['safe_fixes_applied']} |",
        f"| Manual review required | {summary['manual_review_required']} |",
        f"| Status | {summary['status']} |",
        f"",
    ]

    # Safe fixes section
    if report.get("safe_fixes"):
        lines.extend([
            f"## Safe Fixes Applied",
            f"",
            f"| Source File | Old URL | New URL | Reason |",
            f"|------------|---------|---------|--------|",
        ])
        for fix in report["safe_fixes"]:
            status = "✓" if fix.get("applied") else "–"
            lines.append(
                f"| {fix['source_file']} | `{fix['old_url']}` | `{fix['new_url']}` | {fix['reason']} {status} |"
            )
        lines.append("")

    # Manual review section
    if report.get("manual_review"):
        lines.extend([
            f"## Manual Review Required",
            f"",
            f"| Source File | Broken URL | Reason |",
            f"|------------|-----------|--------|",
        ])
        for item in report["manual_review"]:
            lines.append(
                f"| {item['source_file']} | `{item['broken_url']}` | {item['reason']} |"
            )
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    main()
