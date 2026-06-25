#!/usr/bin/env python3
"""
Rewrite asset + site URLs for the Cloudflare R2 CDN + apex-domain migration.

Two independent, composable passes (pick with flags):

  --cdn       Point static MEDIA references at the CDN.
              Media roots (img / images / uploads / pdf / reports) become
              absolute CDN URLs:

                /zola/img/covers/x.webp                         ┐
                https://banhang-chogao.github.io/zola/img/x.png ┤→ https://cdn.seomoney.org/img/...
                /img/covers/x.svg                               ┘

              CDN URLs are domain-independent: they keep working whether the
              origin is GitHub Pages (/zola) or the apex domain.

  --domain    Remove the GitHub Pages "/zola" subpath + old origin host so the
              site can serve from the apex domain (config base_url):

                https://banhang-chogao.github.io/zola/posting/x/ → https://seomoney.org/posting/x/
                /zola/posting/x/                                  → /posting/x/
                /zola                                             → /

Both passes are idempotent and code-span-safe for markdown (URLs inside fenced
``` blocks or inline `code` are left untouched, matching scripts/
fix_site_prefix_links.py and the V10-LINKS invariant).

Targets: content/**.md, templates/**.html, static/** (html/js/json/xml/txt/svg),
sass/**.scss. config.toml and Python scripts are handled separately/manually
because their semantics are not pure text.

Usage
-----
    python3 scripts/rewrite_cdn_urls.py --cdn --dry-run
    python3 scripts/rewrite_cdn_urls.py --cdn
    python3 scripts/rewrite_cdn_urls.py --domain --dry-run
    python3 scripts/rewrite_cdn_urls.py --cdn --domain
    python3 scripts/rewrite_cdn_urls.py --cdn --cdn-base https://cdn.example.com \
        --old-host banhang-chogao.github.io --old-prefix /zola \
        --new-origin https://seomoney.org

Stdlib only. Reports to data/cdn-rewrite-report.json.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from link_utils import code_span_ranges, in_ranges  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
REPORT = REPO / "data" / "cdn-rewrite-report.json"

# Media roots that move to the CDN. Everything else stays on the origin.
MEDIA_ROOTS = ("img", "images", "uploads", "pdf", "reports")

# File globs to process.
TARGET_GLOBS = (
    ("content", "*.md"),
    ("templates", "*.html"),
    ("sass", "*.scss"),
    ("static", "*.html"),
    ("static", "*.js"),
    ("static", "*.json"),
    ("static", "*.xml"),
    ("static", "*.txt"),
    ("static", "*.svg"),
    ("static", "*.css"),
    ("static", "*.webmanifest"),
)

MEDIA_ALT = "|".join(MEDIA_ROOTS)


def build_patterns(cdn_base: str, old_host: str, old_prefix: str, new_origin: str):
    cdn = cdn_base.rstrip("/")
    new = new_origin.rstrip("/")
    pfx = old_prefix.rstrip("/")  # e.g. /zola
    host_re = re.escape(old_host)
    pfx_re = re.escape(pfx)

    cdn_rules: list[tuple[re.Pattern, str]] = [
        # absolute old-origin media -> CDN
        (re.compile(rf"https?://{host_re}{pfx_re}/(?P<root>{MEDIA_ALT})/",),
         f"{cdn}/" + r"\g<root>/"),
        # protocol-relative old-origin media -> CDN
        (re.compile(rf"//{host_re}{pfx_re}/(?P<root>{MEDIA_ALT})/"),
         f"{cdn}/" + r"\g<root>/"),
        # root-absolute /zola/img/... -> CDN
        (re.compile(rf"{pfx_re}/(?P<root>{MEDIA_ALT})/"),
         f"{cdn}/" + r"\g<root>/"),
        # bare root-absolute /img/... -> CDN  (only at a URL boundary char)
        (re.compile(rf"(?P<b>[\"'(\s=])/(?P<root>{MEDIA_ALT})/"),
         r"\g<b>" + f"{cdn}/" + r"\g<root>/"),
    ]

    domain_rules: list[tuple[re.Pattern, str]] = [
        # absolute old-origin non-media page -> new origin (drop /zola)
        (re.compile(rf"https?://{host_re}{pfx_re}/"), f"{new}/"),
        (re.compile(rf"https?://{host_re}{pfx_re}\b"), f"{new}"),
        # protocol-relative old-origin -> new origin
        (re.compile(rf"//{host_re}{pfx_re}/"), f"{new}/"),
        # root-absolute /zola/... -> /...
        (re.compile(rf"{pfx_re}/"), "/"),
        # bare /zola end-of-token -> /
        (re.compile(rf"{pfx_re}\b(?![\w-])"), "/"),
    ]
    return cdn_rules, domain_rules


def apply_rules(text: str, rules, code_safe: bool) -> tuple[str, int]:
    """Apply (pattern, repl) rules, skipping matches inside code spans if asked."""
    total = 0
    ranges = code_span_ranges(text) if code_safe else []
    for pat, repl in rules:
        def _repl(m: re.Match) -> str:
            nonlocal total
            if code_safe and in_ranges(m.start(), ranges):
                return m.group(0)
            total += 1
            return m.expand(repl)
        text = pat.sub(_repl, text)
        # Re-derive code spans after each rule (positions shift on markdown).
        if code_safe:
            ranges = code_span_ranges(text)
    return text, total


def iter_targets():
    for sub, pat in TARGET_GLOBS:
        base = REPO / sub
        if not base.is_dir():
            continue
        for fp in sorted(base.rglob(pat)):
            if fp.is_file():
                yield fp


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cdn", action="store_true", help="rewrite media -> CDN")
    ap.add_argument("--domain", action="store_true", help="strip /zola, switch origin")
    ap.add_argument("--cdn-base", default="https://cdn.seomoney.org")
    ap.add_argument("--old-host", default="banhang-chogao.github.io")
    ap.add_argument("--old-prefix", default="/zola")
    ap.add_argument("--new-origin", default="https://seomoney.org")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not (args.cdn or args.domain):
        ap.error("choose at least one pass: --cdn and/or --domain")

    cdn_rules, domain_rules = build_patterns(
        args.cdn_base, args.old_host, args.old_prefix, args.new_origin)

    # Order matters: CDN media first (so /zola/img/ becomes a CDN URL before the
    # generic /zola/ -> / domain rule would strip the prefix).
    rules = []
    if args.cdn:
        rules += cdn_rules
    if args.domain:
        rules += domain_rules

    changed_files: list[dict] = []
    total_subs = 0

    for fp in iter_targets():
        try:
            raw = fp.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        code_safe = fp.suffix == ".md"
        new, n = apply_rules(raw, rules, code_safe=code_safe)
        if n and new != raw:
            total_subs += n
            rel = fp.relative_to(REPO).as_posix()
            changed_files.append({"file": rel, "substitutions": n})
            if not args.dry_run:
                fp.write_text(new, encoding="utf-8")

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": args.dry_run,
        "passes": {"cdn": args.cdn, "domain": args.domain},
        "cdn_base": args.cdn_base,
        "new_origin": args.new_origin,
        "files_changed": len(changed_files),
        "total_substitutions": total_subs,
        "changes": changed_files,
    }
    try:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                          encoding="utf-8")
    except OSError:
        pass

    mode = "+".join(p for p, on in (("cdn", args.cdn), ("domain", args.domain)) if on)
    verb = "would change" if args.dry_run else "changed"
    print(f"[{mode}] {verb} {len(changed_files)} file(s), "
          f"{total_subs} substitution(s).")
    for c in changed_files[:30]:
        print(f"  {c['substitutions']:>4}  {c['file']}")
    if len(changed_files) > 30:
        print(f"  ... and {len(changed_files) - 30} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
