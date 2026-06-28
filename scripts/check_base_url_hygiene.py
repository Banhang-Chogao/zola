#!/usr/bin/env python3
"""
Base URL hygiene checker — enforce SEOMONEY canonical production URL.

The live site is https://seomoney.org with root path "/".
The legacy /zola/ path is from old GitHub Pages project structure and must NOT appear in:
  * Production URLs in templates/scripts/dashboards
  * Generated content (dashboards, reports, verification URLs)
  * User-facing documentation and examples

Allowed: only if line contains one of: legacy, historical, old GitHub Pages, migration

Exit codes:
  0: clean (no violations or only historical references)
  1: warnings found (P2 — advisory only)
  2: P0/P1 violations found (FAIL — must fix before deploy)
"""

import os
import re
import sys
from pathlib import Path

# Root of repo
REPO_ROOT = Path(__file__).parent.parent

# Files/patterns to check
CHECK_PATTERNS = [
    (r"https://seomoney\.org/zola/", "active production URL with /zola/"),
    (r'href="/zola/', "href link starting with /zola/"),
    (r'src="/zola/', "src link starting with /zola/"),
    (r'url\("/zola/', "CSS url() with /zola/"),
]

# Exclude these directories
EXCLUDE_DIRS = {".git", "public", "node_modules", ".venv", ".pytest_cache", "sections-backup", "__pycache__"}

# Allowed labels (if a line has these, it's not a violation)
ALLOWED_LABELS = {
    "legacy",
    "historical",
    "old github pages",
    "migration",
    "deprecated",
    "V5b", "V10", "V19",  # Vaccine vaccine numbers
    "getzola/zola",  # Zola SSG repo (not production)
    "github.com/banhang-chogao/zola",  # GitHub repo name
    "github.com/Banhang-Chogao/zola",  # GitHub repo name (alt case)
}

# Files/paths that are allowed to have /zola/ references (already audited)
ALLOWED_FILES = {
    "services/vipzone/rum.py",
    "services/vipzone/comments.py",
    ".github/BRANCH-PROTECTION.md",
    ".github/CLOUDFLARE-DDOS-SETUP.md",
    "README.md",  # GitHub repo status badge
    "scripts/check_base_url_hygiene.py",  # This script itself (pattern definitions)
    "scripts/compliance_fix.py",  # Legacy link fixing patterns
    "scripts/test_fix_stale_zola_links.py",  # Test code with legacy URLs
    "zola/scripts/test_link_utils.py",  # Test code with legacy URL normalization
    "zola/scripts/test_link_normalization.py",  # Test code with legacy URL normalization
    "services/vipzone/test_rum.py",  # Test data with legacy URLs
}


def should_skip_file(path: Path) -> bool:
    """Check if file should be skipped."""
    # Skip directories
    if path.is_dir():
        return True

    # Skip if any parent is excluded
    for part in path.parts:
        if part in EXCLUDE_DIRS:
            return True

    # Skip allowed files
    rel_path = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    for allowed in ALLOWED_FILES:
        if rel_path.endswith(allowed) or rel_path == allowed:
            return True

    return False


def is_allowed_line(line: str) -> bool:
    """Check if a line is allowed (contains historical reference label)."""
    line_lower = line.lower()
    for label in ALLOWED_LABELS:
        if label in line_lower:
            return True
    return False


def check_file(path: Path) -> list[tuple[int, str, str]]:
    """Check a file for violations. Return list of (line_num, line, pattern_desc)."""
    violations = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            in_code_block = False
            for line_num, line in enumerate(f, start=1):
                # Track if we're in a code block (```...```
                if line.strip().startswith("```"):
                    in_code_block = not in_code_block
                    continue  # Skip code block markers

                # Skip lines inside code blocks (they're examples/docs)
                if in_code_block:
                    continue

                for pattern, desc in CHECK_PATTERNS:
                    if re.search(pattern, line):
                        # Check if this is an allowed reference
                        if is_allowed_line(line):
                            continue
                        violations.append((line_num, line.rstrip(), desc))
                        break  # Report only first match per line
    except Exception as e:
        print(f"[WARN] Could not read {path}: {e}", file=sys.stderr)
    return violations


def main():
    """Scan repo for base URL violations."""
    violations = []
    checked = 0

    # Scan all files
    for path in REPO_ROOT.rglob("*"):
        if should_skip_file(path):
            continue

        checked += 1
        file_violations = check_file(path)
        if file_violations:
            for line_num, line, desc in file_violations:
                rel_path = path.relative_to(REPO_ROOT)
                violations.append((str(rel_path), line_num, line, desc))

    # Report
    if violations:
        print(f"\n❌ Base URL Hygiene: Found {len(violations)} violation(s):")
        print("=" * 80)
        for path, line_num, line, desc in violations:
            print(f"\n{path}:{line_num}")
            print(f"  Issue: {desc}")
            print(f"  Line: {line[:100]}")
        print("\n" + "=" * 80)
        print("\nFix:")
        print("  1. Replace active /zola/ URLs with canonical root paths:")
        print("     /zola/changelog/ → /changelog/")
        print("     /zola/tools/... → /tools/...")
        print("  2. If referencing old path for historical/educational purpose,")
        print("     add label 'legacy' or 'historical' in a comment on the same line.")
        print("  3. For URLs in backend services (VIPZone), ensure they only")
        print("     *strip* incoming /zola/ paths, never *generate* them.")
        return 2
    else:
        print(f"✅ Base URL Hygiene: Clean ({checked} files checked, 0 violations)")
        return 0


if __name__ == "__main__":
    sys.exit(main())
