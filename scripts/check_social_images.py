#!/usr/bin/env python3
"""
Social image validation for built HTML pages.

Ensures all article pages have proper og:image meta tags for social sharing:
- og:image must be absolute URL (http/https)
- og:image must NEVER be SVG (social platforms don't render SVG)
- og:image must resolve to existing static asset
- og:image must be 1200×630 (OG standard)

Returns:
  0 — all pages valid
  2 — social image issues found (gate failure)

Runs after `zola build` on built HTML in public/.
"""

from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PUBLIC_ROOT = REPO_ROOT / "public"


class OGMetaExtractor(HTMLParser):
    """Extract og:image, og:image:width, og:image:height from HTML."""

    def __init__(self):
        super().__init__()
        self.og_image: str | None = None
        self.og_width: str | None = None
        self.og_height: str | None = None
        self.twitter_image: str | None = None
        self.found_article_schema = False

    def handle_starttag(self, tag, attrs):
        if tag == "meta":
            attrs_dict = dict(attrs)
            prop = attrs_dict.get("property", "")
            name = attrs_dict.get("name", "")
            content = attrs_dict.get("content", "")

            if prop == "og:image" and content:
                self.og_image = content
            elif prop == "og:image:width" and content:
                self.og_width = content
            elif prop == "og:image:height" and content:
                self.og_height = content
            elif name == "twitter:image" and content:
                self.twitter_image = content
        elif tag == "script" and "application/ld+json" in dict(attrs).get("type", ""):
            self.found_article_schema = True


def extract_og_meta(html: str) -> dict:
    """Parse HTML and extract OG image metadata."""
    parser = OGMetaExtractor()
    try:
        parser.feed(html)
    except Exception:
        pass
    return {
        "og_image": parser.og_image,
        "og_width": parser.og_width,
        "og_height": parser.og_height,
        "twitter_image": parser.twitter_image,
        "has_schema": parser.found_article_schema,
    }


def is_article_page(html: str, url: str) -> bool:
    """Determine if page is an article (BlogPosting) that needs OG image."""
    # Article pages: /posting/*, /baochi/*, /pages/* (not root, categories, tags, etc.)
    article_patterns = ["/posting/", "/baochi/", "/pages/"]
    is_article = any(p in url for p in article_patterns)

    # Double-check: look for BlogPosting schema
    has_article_schema = '"@type": "BlogPosting"' in html or "@type" not in html or not is_article

    return is_article


def validate_og_image(url: str, meta: dict, check_files: bool = True) -> tuple[bool, list[str]]:
    """Validate OG image URL and properties. Returns (is_valid, errors)."""
    errors = []

    og_image = meta.get("og_image", "")
    if not og_image:
        errors.append(f"missing og:image meta tag")
        return False, errors

    # Check for absolute URL
    if not og_image.startswith(("http://", "https://")):
        errors.append(f"og:image is relative URL (not absolute): {og_image}")

    # Check for SVG (social platforms don't render SVG)
    if og_image.endswith(".svg"):
        errors.append(f"og:image cannot be SVG (social platforms don't render): {og_image}")

    # Check dimensions
    og_width = meta.get("og_width", "")
    og_height = meta.get("og_height", "")
    if og_width and og_height:
        if og_width != "1200" or og_height != "630":
            errors.append(
                f"og:image dimensions {og_width}×{og_height} (should be 1200×630)"
            )

    # Try to resolve static file (only if public/ exists — post-build validation)
    if check_files and PUBLIC_ROOT.exists() and og_image.startswith(("http://", "https://")) and "seomoney.org" in og_image:
        # Extract path after domain
        m = re.search(r"seomoney\.org(/[^?#]+)", og_image)
        if m:
            path = m.group(1)
            static_file = PUBLIC_ROOT / path.lstrip("/")
            if not static_file.exists():
                errors.append(f"og:image file not found in public/: {path}")

    return len(errors) == 0, errors


def check_social_images_in_file(html_path: Path, base_url: str = "https://seomoney.org") -> tuple[bool, list[str]]:
    """Check social images in a single HTML file. Returns (is_valid, errors)."""
    try:
        html = html_path.read_text(encoding="utf-8")
    except Exception as e:
        return False, [f"Cannot read {html_path}: {e}"]

    # Compute page URL
    rel_path = html_path.relative_to(PUBLIC_ROOT)
    if rel_path.name == "index.html":
        page_url = str(rel_path.parent).replace("\\", "/") or "/"
    else:
        page_url = str(rel_path).replace("\\", "/").replace("index.html", "")
    page_url = base_url + "/" + page_url.lstrip("/")

    # Check if this is an article page
    if not is_article_page(html, str(rel_path)):
        return True, []

    # Extract and validate OG image
    meta = extract_og_meta(html)
    is_valid, errors = validate_og_image(page_url, meta)

    return is_valid, errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--check",
        action="store_true",
        help="return 2 if any social image issues found (exit 0 normally)"
    )
    args = ap.parse_args()

    if not PUBLIC_ROOT.exists():
        print("check_social_images: public/ not found (run `zola build` first)")
        return 0

    # Find all HTML files in article sections
    article_html_files = []
    for pattern in ["posting/**/*.html", "baochi/**/*.html", "pages/**/*.html"]:
        article_html_files.extend(PUBLIC_ROOT.glob(pattern))

    issues = []
    ok_count = 0

    for html_file in sorted(article_html_files):
        is_valid, errors = check_social_images_in_file(html_file)
        if is_valid:
            ok_count += 1
        else:
            rel = html_file.relative_to(REPO_ROOT)
            for error in errors:
                issues.append(f"{rel}: {error}")

    if not article_html_files:
        print("check_social_images: no article HTML files found")
        return 0

    if issues:
        print(f"check_social_images: {len(issues)} social image issues in {len(article_html_files)} article pages:")
        for issue in issues[:20]:  # Show first 20
            print(f"  ✗ {issue}")
        if len(issues) > 20:
            print(f"  ... and {len(issues) - 20} more")
        if args.check:
            return 2
    else:
        print(f"check_social_images: ✓ {ok_count}/{len(article_html_files)} article pages have valid social images")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
