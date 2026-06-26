#!/usr/bin/env python3
"""
Audit MoMo links across the repo.

Scan sources:
  - config.toml: [extra].momo_payment_link, donate_momo_link
  - content/posting/*.md: frontmatter momo_payment_link (per-post override)
  - templates/**/*.html: hardcoded me.momo.vn references
  - .github/workflows/*.yml: env MOMO_PAYMENT_LINK, MOMO_SEMIANNUAL, etc.
  - render.yaml: env vars
  - docs/paywall.md: documentation references

Output: data/momo-links-audit.json
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, TypedDict


class MoMoLink(TypedDict):
    """A MoMo link entry in the audit."""
    url: str
    source: str  # "config.toml", "frontmatter", "template", "workflow", "render.yaml", "docs"
    detail: str  # file path or key name
    category: str  # "Premium default", "Donate", "Premium post", "Template/hardcoded", "Workflow/env", "Documentation"
    post_slug: str | None
    post_title: str | None
    locations: list[str]  # list of files/keys using this URL


class MoMoAudit(TypedDict):
    """Complete audit result."""
    generated_at: str
    sources: dict[str, Any]
    links_by_url: dict[str, MoMoLink]
    summary: dict[str, Any]


MOMO_PATTERN = r'https://me\.momo\.vn/[A-Za-z0-9/_-]+'
REPO_ROOT = Path(__file__).parent.parent


def extract_momo_urls(text: str) -> list[str]:
    """Extract all MoMo URLs from text."""
    matches = re.findall(MOMO_PATTERN, text)
    return sorted(set(matches))


def audit_config_toml() -> dict[str, MoMoLink]:
    """Scan config.toml for MoMo links."""
    result = {}
    config_path = REPO_ROOT / "config.toml"

    if not config_path.exists():
        return result

    content = config_path.read_text(encoding="utf-8")

    # Find [extra] section
    extra_match = re.search(r'\[extra\](.*?)(?:\n\[|$)', content, re.DOTALL)
    if not extra_match:
        return result

    extra_section = extra_match.group(1)

    # momo_payment_link
    momo_payment = re.search(r'momo_payment_link\s*=\s*"([^"]*)"', extra_section)
    if momo_payment:
        url = momo_payment.group(1)
        result[url] = {
            "url": url,
            "source": "config.toml",
            "detail": "[extra].momo_payment_link",
            "category": "Premium default",
            "post_slug": None,
            "post_title": None,
            "locations": ["config.toml:[extra].momo_payment_link"],
        }

    # donate_momo_link
    donate_momo = re.search(r'donate_momo_link\s*=\s*"([^"]*)"', extra_section)
    if donate_momo:
        url = donate_momo.group(1)
        if url not in result:
            result[url] = {
                "url": url,
                "source": "config.toml",
                "detail": "[extra].donate_momo_link",
                "category": "Donate",
                "post_slug": None,
                "post_title": None,
                "locations": ["config.toml:[extra].donate_momo_link"],
            }
        else:
            result[url]["category"] = "Donate (shared with Premium)"
            result[url]["locations"].append("config.toml:[extra].donate_momo_link")

    return result


def audit_content_frontmatter() -> dict[str, MoMoLink]:
    """Scan content/posting/*.md for per-post MoMo link overrides."""
    result = {}
    content_dir = REPO_ROOT / "content" / "posting"

    if not content_dir.exists():
        return result

    for md_file in sorted(content_dir.glob("*.md")):
        try:
            content = md_file.read_text(encoding="utf-8")

            # Parse TOML frontmatter (between +++ markers)
            if not content.startswith("+++"):
                continue

            end_marker = content.find("+++", 3)
            if end_marker == -1:
                continue

            frontmatter_str = content[3:end_marker].strip()

            # Extract title
            title_match = re.search(r'title\s*=\s*["\']([^"\']*)["\']', frontmatter_str)
            post_title = title_match.group(1) if title_match else md_file.stem

            # Extract [extra] section and look for momo_payment_link
            extra_match = re.search(r'\[extra\](.*?)(?:\n\[|$)', frontmatter_str, re.DOTALL)
            if not extra_match:
                continue

            extra_section = extra_match.group(1)
            momo_match = re.search(r'momo_payment_link\s*=\s*"([^"]*)"', extra_section)

            if not momo_match:
                continue

            momo_link = momo_match.group(1)
            post_slug = md_file.stem

            if momo_link not in result:
                result[momo_link] = {
                    "url": momo_link,
                    "source": "frontmatter",
                    "detail": f"content/posting/{md_file.name}",
                    "category": "Premium post custom",
                    "post_slug": post_slug,
                    "post_title": post_title,
                    "locations": [f"content/posting/{md_file.name}:[extra].momo_payment_link"],
                }
            else:
                result[momo_link]["locations"].append(f"content/posting/{md_file.name}:[extra].momo_payment_link")
                if not result[momo_link]["post_slug"]:
                    result[momo_link]["post_slug"] = post_slug
                    result[momo_link]["post_title"] = post_title
        except Exception as e:
            print(f"Warning: Failed to parse {md_file}: {e}", file=sys.stderr)

    return result


def audit_templates() -> dict[str, MoMoLink]:
    """Scan templates/**/*.html for hardcoded MoMo URLs."""
    result = {}
    templates_dir = REPO_ROOT / "templates"

    if not templates_dir.exists():
        return result

    for html_file in sorted(templates_dir.rglob("*.html")):
        try:
            content = html_file.read_text(encoding="utf-8")
            urls = extract_momo_urls(content)

            for url in urls:
                rel_path = html_file.relative_to(REPO_ROOT)
                if url not in result:
                    result[url] = {
                        "url": url,
                        "source": "template",
                        "detail": str(rel_path),
                        "category": "Template/hardcoded",
                        "post_slug": None,
                        "post_title": None,
                        "locations": [str(rel_path)],
                    }
                else:
                    if str(rel_path) not in result[url]["locations"]:
                        result[url]["locations"].append(str(rel_path))
        except Exception as e:
            print(f"Warning: Failed to scan {html_file}: {e}", file=sys.stderr)

    return result


def audit_workflows() -> dict[str, MoMoLink]:
    """Scan .github/workflows/*.yml for MOMO env vars."""
    result = {}
    workflows_dir = REPO_ROOT / ".github" / "workflows"

    if not workflows_dir.exists():
        return result

    for yml_file in sorted(workflows_dir.glob("*.yml")):
        try:
            content = yml_file.read_text(encoding="utf-8")
            urls = extract_momo_urls(content)

            for url in urls:
                rel_path = yml_file.relative_to(REPO_ROOT)
                if url not in result:
                    result[url] = {
                        "url": url,
                        "source": "workflow",
                        "detail": str(rel_path),
                        "category": "Workflow/env",
                        "post_slug": None,
                        "post_title": None,
                        "locations": [str(rel_path)],
                    }
                else:
                    if str(rel_path) not in result[url]["locations"]:
                        result[url]["locations"].append(str(rel_path))
        except Exception as e:
            print(f"Warning: Failed to scan {yml_file}: {e}", file=sys.stderr)

    return result


def audit_render_yaml() -> dict[str, MoMoLink]:
    """Scan render.yaml for MOMO env vars."""
    result = {}
    render_file = REPO_ROOT / "render.yaml"

    if not render_file.exists():
        return result

    try:
        content = render_file.read_text(encoding="utf-8")
        urls = extract_momo_urls(content)

        for url in urls:
            if url not in result:
                result[url] = {
                    "url": url,
                    "source": "render.yaml",
                    "detail": "render.yaml",
                    "category": "Workflow/env",
                    "post_slug": None,
                    "post_title": None,
                    "locations": ["render.yaml"],
                }
            else:
                if "render.yaml" not in result[url]["locations"]:
                    result[url]["locations"].append("render.yaml")
    except Exception as e:
        print(f"Warning: Failed to scan render.yaml: {e}", file=sys.stderr)

    return result


def audit_docs() -> dict[str, MoMoLink]:
    """Scan docs/ for MoMo references (documentation only, not runtime)."""
    result = {}
    docs_dir = REPO_ROOT / "docs"

    if not docs_dir.exists():
        return result

    for md_file in sorted(docs_dir.glob("*.md")):
        try:
            content = md_file.read_text(encoding="utf-8")
            urls = extract_momo_urls(content)

            for url in urls:
                rel_path = md_file.relative_to(REPO_ROOT)
                if url not in result:
                    result[url] = {
                        "url": url,
                        "source": "docs",
                        "detail": str(rel_path),
                        "category": "Documentation",
                        "post_slug": None,
                        "post_title": None,
                        "locations": [str(rel_path)],
                    }
                else:
                    if str(rel_path) not in result[url]["locations"]:
                        result[url]["locations"].append(str(rel_path))
        except Exception as e:
            print(f"Warning: Failed to scan {md_file}: {e}", file=sys.stderr)

    return result


def run_audit() -> MoMoAudit:
    """Run complete MoMo link audit."""
    from datetime import datetime, timezone

    audit_results = [
        audit_config_toml(),
        audit_content_frontmatter(),
        audit_templates(),
        audit_workflows(),
        audit_render_yaml(),
        audit_docs(),
    ]

    # Merge all results by URL
    links_by_url: dict[str, MoMoLink] = {}
    for results in audit_results:
        for url, link in results.items():
            if url not in links_by_url:
                links_by_url[url] = link
            else:
                # Merge locations
                for loc in link["locations"]:
                    if loc not in links_by_url[url]["locations"]:
                        links_by_url[url]["locations"].append(loc)

    # Sort locations
    for link in links_by_url.values():
        link["locations"].sort()

    summary = {
        "total_unique_urls": len(links_by_url),
        "premium_default": sum(1 for link in links_by_url.values() if "Premium default" in link["category"]),
        "donate": sum(1 for link in links_by_url.values() if "Donate" in link["category"]),
        "premium_post_custom": sum(1 for link in links_by_url.values() if "Premium post custom" in link["category"]),
        "template_hardcoded": sum(1 for link in links_by_url.values() if "Template/hardcoded" in link["category"]),
        "workflow_env": sum(1 for link in links_by_url.values() if "Workflow/env" in link["category"]),
        "documentation": sum(1 for link in links_by_url.values() if "Documentation" in link["category"]),
    }

    result: MoMoAudit = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "config.toml": "[extra].momo_payment_link, donate_momo_link",
            "content/posting/*.md": "frontmatter [extra].momo_payment_link (per-post override)",
            "templates/**/*.html": "hardcoded me.momo.vn",
            ".github/workflows/*.yml": "env vars MOMO_*",
            "render.yaml": "env vars",
            "docs/paywall.md": "documentation references",
        },
        "links_by_url": links_by_url,
        "summary": summary,
    }

    return result


if __name__ == "__main__":
    audit = run_audit()

    # Write to data/momo-links-audit.json
    data_dir = REPO_ROOT / "data"
    data_dir.mkdir(exist_ok=True)

    output_file = data_dir / "momo-links-audit.json"
    output_file.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✓ Audit complete: {output_file}")
    print(f"  Total URLs: {audit['summary']['total_unique_urls']}")
    print(f"  Premium default: {audit['summary']['premium_default']}")
    print(f"  Donate: {audit['summary']['donate']}")
    print(f"  Premium post custom: {audit['summary']['premium_post_custom']}")
    print(f"  Template/hardcoded: {audit['summary']['template_hardcoded']}")
    print(f"  Workflow/env: {audit['summary']['workflow_env']}")
    print(f"  Documentation: {audit['summary']['documentation']}")
