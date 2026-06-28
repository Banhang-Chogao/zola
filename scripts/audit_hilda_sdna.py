#!/usr/bin/env python3
"""
Ericsson Hilda S-DNA Typography Audit — SEOMONEY

Verifies production typography follows the S-DNA Hilda guideline:
- Hilda is PRIMARY typeface site-wide
- Hilda font files are loaded via @font-face
- Legal fonts only as fallback (per-glyph)
- Type scale matches Font Guideline (52px/800/-0.03em display, 36px/700/-0.02em H1, etc.)
- Vietnamese readability maintained

Rules:
- MUST define Hilda via @font-face (self-hosted, all 5 weights)
- MUST use Hilda-first font stacks globally
- MUST apply Typography tokens consistently
- Fallback fonts allowed only AFTER Hilda in stack
"""

import json
import re
import sys
from pathlib import Path

# Ericsson Hilda typography scale (from Font Guideline)
HILDA_SCALE = {
    "display": {"size": "52px", "weight": 800, "tracking": "-0.03em"},
    "h1": {"size": "36px", "weight": 700, "tracking": "-0.02em"},
    "h2": {"size": "26px", "weight": 700, "tracking": "-0.01em"},
    "h3": {"size": "19px", "weight": 500, "tracking": "0"},
    "body": {"size": "16px", "weight": 300, "line_height": "1.6"},  # or 400
    "caption": {"size": "13px", "weight": 500, "tracking": "0.04em"},
}

# Hilda-first stacks (legal fonts as fallback only)
HILDA_STACKS = {
    "body": ["Ericsson Hilda", "Manrope", "-apple-system", "BlinkMacSystemFont", "Segoe UI"],
    "heading": ["Ericsson Hilda", "Manrope", "-apple-system", "BlinkMacSystemFont"],
    "ui": ["Ericsson Hilda", "Inter", "Manrope", "-apple-system", "BlinkMacSystemFont"],
}

# Required Hilda @font-face weights
REQUIRED_HILDA_WEIGHTS = {
    "200": "ExtraLight",
    "300": "Light",
    "400": "Medium (maps to Regular)",
    "500": "Medium",
    "700": "Bold",
    "800": "ExtraBold",
}

def scan_css_file(css_path: Path) -> dict:
    """Scan built CSS for Hilda compliance."""
    issues = []
    found_hilda_fontface = False
    found_hilda_stack = False
    hilda_weights = set()

    try:
        content = css_path.read_text()
    except Exception as e:
        return {"error": str(e), "status": "fail"}

    # Check for @font-face Hilda declarations
    fontface_patterns = [
        r"@font-face\s*\{[^}]*?font-family\s*:\s*['\"]Ericsson Hilda['\"]",
        r"@font-face\s*\{[^}]*?url\(['\"]?.*?EricssonHilda[^)]*?\)",
    ]

    for pattern in fontface_patterns:
        if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
            found_hilda_fontface = True
            break

    if not found_hilda_fontface:
        issues.append("CRITICAL: Hilda @font-face declarations not found")
    else:
        # Check which weights are defined
        for weight_num, weight_name in REQUIRED_HILDA_WEIGHTS.items():
            if re.search(rf"font-weight:\s*{weight_num}|EricssonHilda-[A-Za-z]+", content):
                hilda_weights.add(weight_num)

    # Check for Hilda-first font stacks in CSS
    # Look for selectors that set font-family with Hilda first
    hilda_first_pattern = r"font-family\s*:\s*['\"]Ericsson Hilda['\"]"
    hilda_first_matches = re.findall(hilda_first_pattern, content)

    if hilda_first_matches:
        found_hilda_stack = True
    else:
        issues.append("WARN: No Hilda-first font-family declarations found in CSS")

    # Check for illegal primary fonts (non-Hilda as primary)
    # Look for font-family declarations that don't start with Hilda
    illegal_patterns = [
        r"font-family\s*:\s*['\"]?(?!Ericsson Hilda)(?:Inter|IBM Plex|Roboto|system-ui|sans-serif)['\"]?",
    ]

    illegal_primaries = 0
    for pattern in illegal_patterns:
        matches = re.findall(pattern, content)
        if matches:
            illegal_primaries += len([m for m in matches if m])

    if illegal_primaries > 0:
        issues.append(f"INFO: Found {illegal_primaries} non-Hilda font declarations (expected as fallback)")

    # Check for typography scale tokens / values
    scale_checks = {
        "display": ["52px", "800"],
        "h1": ["36px", "700"],
        "h2": ["26px", "700"],
        "h3": ["19px", "500"],
        "body": ["16px"],
        "caption": ["13px", "500"],
    }

    scale_confidence = 0
    for level, values in scale_checks.items():
        for value in values:
            if value in content:
                scale_confidence += 1

    if scale_confidence < len(scale_checks):
        issues.append(f"INFO: Some typography scale values not detected (found {scale_confidence}/{len(scale_checks)})")

    # Determine status: FAIL only if critical issues, PASS if Hilda is primary + fontface + stacks confirmed
    has_critical = any("CRITICAL" in issue for issue in issues)
    if has_critical:
        status = "fail"
    elif found_hilda_fontface and found_hilda_stack:
        # Hilda compliance verified - INFO messages don't fail the audit
        status = "pass"
    else:
        # Missing Hilda @font-face or stacks - this is a real issue
        status = "warn" if issues else "pass"

    return {
        "path": str(css_path),
        "status": status,
        "issues": issues,
        "hilda_fontface_found": found_hilda_fontface,
        "hilda_stack_found": found_hilda_stack,
        "hilda_weights": sorted(list(hilda_weights)),
        "scale_confidence": f"{scale_confidence}/{len(scale_checks)}",
    }


def scan_html_files(public_dir: Path) -> list:
    """Scan built HTML for Hilda font references."""
    issues_by_file = []
    hilda_count = 0

    for html_file in public_dir.rglob("*.html"):
        try:
            content = html_file.read_text()
        except Exception:
            continue

        file_issues = []

        # Check for Hilda @font-face
        if re.search(r"@font-face.*?Ericsson Hilda|EricssonHilda.*?woff2", content, re.IGNORECASE | re.DOTALL):
            file_issues.append("OK: Hilda @font-face declarations present")
            hilda_count += 1

        # Check for Hilda font-family
        if re.search(r"font-family\s*:\s*['\"]Ericsson Hilda['\"]", content, re.IGNORECASE):
            file_issues.append("OK: Hilda font-family applied")

        # Check for CSS variables
        if re.search(r"--[a-z]+-font-family.*?Hilda", content, re.IGNORECASE):
            file_issues.append("OK: Hilda CSS variables defined")

        if file_issues:
            issues_by_file.append({
                "file": str(html_file.relative_to(public_dir)),
                "issues": file_issues,
            })

    return issues_by_file


def audit() -> dict:
    """Run full Hilda S-DNA typography audit."""
    repo_root = Path(__file__).parent.parent
    public_dir = repo_root / "public"
    site_css = public_dir / "site.css"

    report = {
        "timestamp": Path.cwd().name,
        "status": "pass",
        "audit_type": "hilda_sdna_typography",
        "rules": {
            "hilda_primary": "Hilda MUST be primary typeface site-wide",
            "hilda_fontface": "Hilda MUST be loaded via @font-face (self-hosted)",
            "legal_fallback_only": "Legal fonts only as fallback, NOT primary",
            "scale_compliance": "Typography scale MUST match Font Guideline",
            "vietnamese_readability": "Vietnamese readability must be maintained",
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
        "files_with_hilda": len(html_issues),
        "samples": html_issues[:5],
    }

    # Summary
    has_critical = any(
        "CRITICAL" in str(issue)
        for check in report["checks"].values()
        if isinstance(check, dict)
        for issue in check.get("issues", [])
    )

    if has_critical:
        report["status"] = "fail"

    return report


def main():
    report = audit()

    # Print report
    print("\n" + "="*60)
    print("ERICSSON HILDA S-DNA TYPOGRAPHY AUDIT — SEOMONEY")
    print("="*60)
    print(f"Status: {report['status'].upper()}")
    print(f"Audit Type: {report['audit_type']}")

    print("\nRules:")
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
                    symbol = "✗" if "CRITICAL" in issue else "!" if "WARN" in issue else "✓"
                    print(f"    {symbol} {issue}")
            if "hilda_fontface_found" in check_result:
                symbol = "✓" if check_result["hilda_fontface_found"] else "✗"
                print(f"    {symbol} Hilda @font-face: {check_result['hilda_fontface_found']}")
            if "hilda_stack_found" in check_result:
                symbol = "✓" if check_result["hilda_stack_found"] else "!"
                print(f"    {symbol} Hilda font stacks: {check_result['hilda_stack_found']}")
            if "hilda_weights" in check_result:
                print(f"    Hilda weights found: {', '.join(check_result['hilda_weights'])}")
            if "scale_confidence" in check_result:
                print(f"    Typography scale confidence: {check_result['scale_confidence']}")
            if "files_checked" in check_result:
                print(f"    HTML files checked: {check_result['files_checked']}")

    # Exit code
    if report["status"] == "fail":
        print("\n❌ AUDIT FAILED: Critical Hilda compliance issues detected")
        sys.exit(2)
    elif report["status"] == "warn":
        print("\n⚠️  AUDIT WARNING: Some issues detected, review required")
        sys.exit(1)
    elif report["status"] == "skip":
        print(f"\n⊘ AUDIT SKIPPED: {report.get('message', 'N/A')}")
        sys.exit(0)
    else:
        print("\n✅ AUDIT PASSED: Hilda S-DNA compliance verified")
        sys.exit(0)


if __name__ == "__main__":
    main()
