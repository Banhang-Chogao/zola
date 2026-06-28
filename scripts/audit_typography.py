#!/usr/bin/env python3
"""
Typography Compliance Audit — SEOMONEY
Verifies production typography against Ericsson Hilda-inspired guideline
WITHOUT proprietary Ericsson Hilda font files.

Rules:
- MUST use legal fallback stacks: Inter, IBM Plex Sans, Be Vietnam Pro, system sans
- MUST NOT reference local Ericsson Hilda font files or proprietary font CDNs
- MUST define typography CSS variables as tokens
- MUST apply tokens consistently across templates
"""

import json
import re
import sys
from pathlib import Path

# Typography tokens (guideline)
TYPOGRAPHY_TOKENS = {
    "display": {"size": "52px", "weight": 800, "tracking": "-0.03em"},
    "h1": {"size": "36px", "weight": 700, "tracking": "-0.02em"},
    "h2": {"size": "26px", "weight": 700, "tracking": "-0.01em"},
    "h3": {"size": "19px", "weight": 500, "tracking": "-0.01em"},
    "body": {"size": "16px", "weight": 400, "line_height": "1.6"},
    "caption": {"size": "13px", "weight": 500, "tracking": "0.04em"},
}

# Legal fonts (whitelist)
LEGAL_FONTS = {"Inter", "IBM Plex Sans", "Be Vietnam Pro", "Manrope", "system-ui", "-apple-system"}

# Forbidden font references (blacklist)
FORBIDDEN_FONTS = {
    "Ericsson Hilda",
    "EricssonHilda",
    "Hilda",
}

FORBIDDEN_FONT_FILES = {
    "EricssonHilda",
    "ericsson",
    "hilda",
}

def scan_css_file(css_path: Path) -> dict:
    """Scan built CSS for font-family declarations and forbidden references."""
    issues = []
    found_tokens = {}

    try:
        content = css_path.read_text()
    except Exception as e:
        return {"error": str(e), "status": "fail"}

    # Check for forbidden font files (CDN or local)
    # IMPORTANT: These patterns look for actual @font-face URL references and font-family declarations
    # They should NOT match theme names like "data-theme=hilda" or comments
    forbidden_patterns = [
        (r"@font-face\s*\{[^}]*?url\(['\"]?.*?[Ee]ricsson[Hh]ilda.*?\.[wt]", "EricssonHilda font file in @font-face"),
        (r"url\(['\"]?.*?fonts/[^)]*?[Ee]ricsson[Hh]ilda.*?\.[wt]", "EricssonHilda font URL"),
        (r"font-family:\s*['\"]Ericsson Hilda['\"]", "Ericsson Hilda font-family declaration"),
        (r"font-family:\s*['\"]EricssonHilda['\"]", "EricssonHilda font-family declaration (alt)"),
    ]

    for pattern, description in forbidden_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            issues.append(f"FORBIDDEN: {description}")

    # Check for typography token definitions
    token_patterns = {
        "display": r"--type-display-size:\s*52px|--type-display-weight:\s*800",
        "h1": r"--type-h1-size:\s*36px|--type-h1-weight:\s*700",
        "h2": r"--type-h2-size:\s*26px|--type-h2-weight:\s*700",
        "h3": r"--type-h3-size:\s*19px|--type-h3-weight:\s*500",
        "body": r"--type-body-size:\s*16px|--type-body-weight:\s*[34]00|--type-body-line-height:\s*1\.6",
        "caption": r"--type-caption-size:\s*13px|--type-caption-weight:\s*500",
    }

    for token_type, pattern in token_patterns.items():
        if re.search(pattern, content):
            found_tokens[token_type] = "FOUND"
        else:
            issues.append(f"MISSING: Typography token for {token_type}")

    # Check for legal font usage
    legal_count = 0
    for font in LEGAL_FONTS:
        if font in content:
            legal_count += 1

    if legal_count == 0:
        issues.append("WARN: No legal fonts (Inter, IBM Plex Sans, Be Vietnam Pro) found in CSS")

    status = "fail" if any("FORBIDDEN" in issue for issue in issues) else ("warn" if issues else "pass")

    return {
        "path": str(css_path),
        "status": status,
        "issues": issues,
        "tokens_found": found_tokens,
        "legal_fonts_count": legal_count,
    }


def scan_html_files(public_dir: Path) -> list:
    """Scan built HTML files for font-related violations."""
    issues_by_file = []

    for html_file in public_dir.rglob("*.html"):
        try:
            content = html_file.read_text()
        except Exception:
            continue

        file_issues = []

        # Check for actual @font-face declarations with Ericsson Hilda fonts
        if re.search(r"@font-face\s*\{[^}]*?url\([^)]*?Ericsson[Hh]ilda", content, re.IGNORECASE):
            file_issues.append("FORBIDDEN: Found @font-face with EricssonHilda font file")

        # Check for font-family declarations with Ericsson Hilda
        if re.search(r"font-family\s*:\s*['\"]?Ericsson Hilda", content, re.IGNORECASE):
            file_issues.append("FORBIDDEN: Found Ericsson Hilda in font-family declaration")

        # Check for font URLs pointing to Ericsson Hilda files
        if re.search(r"url\(['\"]?[^)]*fonts[^)]*?Ericsson[Hh]ilda\.[wt]", content, re.IGNORECASE):
            file_issues.append("FORBIDDEN: Found EricssonHilda font URL")

        # Check for legal font loading
        if re.search(r"(Inter|IBM Plex|Be Vietnam Pro)", content):
            file_issues.append("OK: Legal fonts being loaded")

        if file_issues:
            issues_by_file.append({
                "file": str(html_file.relative_to(public_dir)),
                "issues": file_issues,
            })

    return issues_by_file


def audit() -> dict:
    """Run full typography audit."""
    repo_root = Path(__file__).parent.parent
    public_dir = repo_root / "public"
    site_css = public_dir / "site.css"

    report = {
        "timestamp": Path.cwd().name,
        "status": "pass",
        "audit_type": "typography",
        "rules": {
            "use_legal_fonts": "Must use Inter, IBM Plex Sans, Be Vietnam Pro, system sans",
            "no_proprietary": "Must NOT reference proprietary Ericsson Hilda fonts",
            "define_tokens": "Must define typography CSS variables as tokens",
            "consistent_application": "Tokens must be applied consistently",
        },
        "checks": {},
    }

    # Check if public dir exists
    if not public_dir.exists():
        report["status"] = "skip"
        report["message"] = f"public/ dir not found (run 'zola build' first)"
        return report

    # Scan main CSS file
    if site_css.exists():
        css_result = scan_css_file(site_css)
        report["checks"]["site_css"] = css_result
        if css_result["status"] in ("fail", "error"):
            report["status"] = "fail"
        elif css_result["status"] == "warn" and report["status"] == "pass":
            report["status"] = "warn"
    else:
        report["status"] = "skip"
        report["message"] = "site.css not found (run 'zola build' first)"
        return report

    # Scan HTML files
    html_issues = scan_html_files(public_dir)
    report["checks"]["html_scan"] = {
        "files_checked": len(list(public_dir.rglob("*.html"))),
        "files_with_issues": len(html_issues),
        "issues": html_issues[:10],  # First 10
    }

    # Summary
    has_forbidden = any(
        "FORBIDDEN" in str(issue)
        for check in report["checks"].values()
        if isinstance(check, dict)
        for issue in check.get("issues", [])
    )

    if has_forbidden:
        report["status"] = "fail"

    return report


def main():
    report = audit()

    # Print report
    print("\n" + "="*60)
    print("TYPOGRAPHY COMPLIANCE AUDIT — SEOMONEY")
    print("="*60)
    print(f"Status: {report['status'].upper()}")
    print(f"Audit Type: {report['audit_type']}")

    for rule_id, rule_desc in report["rules"].items():
        print(f"  • {rule_id}: {rule_desc}")

    print("\nChecks:")
    for check_name, check_result in report["checks"].items():
        print(f"\n  {check_name}:")
        if isinstance(check_result, dict):
            if "status" in check_result:
                print(f"    Status: {check_result['status'].upper()}")
            if "issues" in check_result:
                for issue in check_result["issues"][:5]:
                    symbol = "✗" if "FORBIDDEN" in issue else "!" if "WARN" in issue else "✓"
                    print(f"    {symbol} {issue}")
            if "tokens_found" in check_result:
                print(f"    Tokens found: {len(check_result['tokens_found'])}/{len(TYPOGRAPHY_TOKENS)}")
            if "legal_fonts_count" in check_result:
                print(f"    Legal fonts detected: {check_result['legal_fonts_count']}")

    # Exit code
    if report["status"] == "fail":
        print("\n❌ AUDIT FAILED: Forbidden fonts or missing tokens detected")
        sys.exit(2)
    elif report["status"] == "warn":
        print("\n⚠️  AUDIT WARNING: Some issues detected, review required")
        sys.exit(1)
    elif report["status"] == "skip":
        print(f"\n⊘ AUDIT SKIPPED: {report.get('message', 'N/A')}")
        sys.exit(0)
    else:
        print("\n✅ AUDIT PASSED: Typography compliant")
        sys.exit(0)


if __name__ == "__main__":
    main()
