#!/usr/bin/env python3
"""
Audit MoMo links public usage — map technical locations to public pages.

This script reads data/momo-links-audit.json (technical file paths) and maps each
MoMo link to actual public URLs where readers can see/click that link on the blog.

For each MoMo link, returns:
  - public_usages: list of public pages where the link is rendered
  - technical_usages: list of code/config locations (for collapsed section)

Public usage items include:
  - Public URL (https://seomoney.org/...)
  - Page title / label
  - Placement (where on the page)
  - Status (active, configured, legacy, not_found)

Output: data/momo-public-usage.json
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).parent.parent
BLOG_DOMAIN = "https://seomoney.org"  # prod domain


def load_audit_data() -> dict[str, Any]:
    """Load the raw audit data from momo-links-audit.json"""
    audit_file = REPO_ROOT / "data" / "momo-links-audit.json"
    if not audit_file.exists():
        return {}
    return json.loads(audit_file.read_text(encoding="utf-8"))


def load_content_placements() -> dict[str, Any]:
    """Load content placement blocks"""
    cp_file = REPO_ROOT / "data" / "content-placements.json"
    if not cp_file.exists():
        return {"blocks": [], "placements": []}
    return json.loads(cp_file.read_text(encoding="utf-8"))


def load_posting_urls() -> dict[str, dict[str, Any]]:
    """Load all posting slugs → title/category mapping.

    Scans content/posting/*.md to build a map of slug → {title, url, category}
    """
    posts = {}
    posting_dir = REPO_ROOT / "content" / "posting"

    if not posting_dir.exists():
        return posts

    for md_file in posting_dir.glob("*.md"):
        slug = md_file.stem
        try:
            content = md_file.read_text(encoding="utf-8")

            # Parse TOML frontmatter
            if not content.startswith("+++"):
                continue

            end_marker = content.find("+++", 3)
            if end_marker == -1:
                continue

            frontmatter = content[3:end_marker].strip()

            # Extract title
            title_match = re.search(r'title\s*=\s*["\']([^"\']*)["\']', frontmatter)
            title = title_match.group(1) if title_match else slug

            # Extract categories (default to "Tất cả")
            categories_match = re.search(r'categories\s*=\s*\[(.*?)\]', frontmatter, re.DOTALL)
            categories = []
            if categories_match:
                cat_str = categories_match.group(1)
                cat_items = re.findall(r'["\']([^"\']*)["\']', cat_str)
                categories = cat_items or ["Tất cả"]
            else:
                categories = ["Tất cả"]

            # Extract slug from path if different
            path_match = re.search(r'path\s*=\s*["\']([^"\']*)["\']', frontmatter)
            path = path_match.group(1) if path_match else f"/posting/{slug}/"

            # Normalize path
            if not path.startswith("/"):
                path = "/" + path
            if not path.endswith("/"):
                path = path + "/"

            posts[slug] = {
                "title": title,
                "url": f"{BLOG_DOMAIN}{path}",
                "categories": categories,
                "slug": slug,
            }
        except Exception as e:
            print(f"Error parsing {md_file}: {e}", file=__import__("sys").stderr)

    return posts


def get_public_usages(url: str, link_info: dict[str, Any], posts: dict[str, dict]) -> list[dict[str, Any]]:
    """Map technical locations to public usage pages.

    Args:
        url: The MoMo URL (e.g., https://me.momo.vn/...)
        link_info: Entry from audit_data["links_by_url"][url]
        posts: Mapping from slug to post info

    Returns:
        List of public usage items, each with:
        - public_url: Full URL (https://seomoney.org/...)
        - title: Page title
        - placement: Where on the page (e.g., "Header donate CTA")
        - status: "active", "configured", "template_level", "not_rendered", "legacy"
    """
    usages = []
    locations = link_info.get("locations", [])
    category = link_info.get("category", "Unknown")
    post_slug = link_info.get("post_slug")

    # Track which pages we've already added to avoid duplication
    added_urls = set()

    # ===== 1. Post-specific override (frontmatter momo_payment_link) =====
    if post_slug and post_slug in posts:
        post = posts[post_slug]
        post_url = post["url"]
        if post_url not in added_urls:
            usages.append({
                "title": post["title"],
                "public_url": post_url,
                "placement": "Premium paywall CTA",
                "status": "active",
                "source": "post_frontmatter",
            })
            added_urls.add(post_url)

    # ===== 2. Global donate link (donate_momo_link) =====
    if "donate_momo_link" in " ".join(locations):
        # Homepage
        home_url = BLOG_DOMAIN + "/"
        if home_url not in added_urls:
            usages.append({
                "title": "Trang chủ",
                "public_url": home_url,
                "placement": "Header donate CTA",
                "status": "configured",  # May render via shortcode/macro
                "source": "config_donate",
            })
            added_urls.add(home_url)

        # All posting pages can have donate CTA via shortcode
        if len(posts) > 0 and len(added_urls) < 5:  # Show first 5 as examples
            for slug, post in list(posts.items())[:5]:
                post_url = post["url"]
                if post_url not in added_urls:
                    usages.append({
                        "title": f"Bài viết: {post['title']}",
                        "public_url": post_url,
                        "placement": "Post footer donate CTA (shortcode)",
                        "status": "configured",
                        "source": "donate_shortcode_example",
                    })
                    added_urls.add(post_url)

            if len(posts) > 5:
                usages.append({
                    "title": f"…và {len(posts) - 5} bài viết khác",
                    "public_url": None,
                    "placement": "Tất cả bài viết có donate shortcode",
                    "status": "configured",
                    "source": "donate_all_posts",
                })

    # ===== 3. Global premium link (momo_payment_link) =====
    elif "momo_payment_link" in " ".join(locations) or category == "Premium default":
        # All premium posts
        premium_posts = [p for p in posts.values() if "Premium" in str(p.get("categories", []))]

        if premium_posts:
            # Show first 3
            for post in premium_posts[:3]:
                post_url = post["url"]
                if post_url not in added_urls:
                    usages.append({
                        "title": f"Bài Premium: {post['title']}",
                        "public_url": post_url,
                        "placement": "Premium paywall CTA",
                        "status": "active",
                        "source": "premium_paywall",
                    })
                    added_urls.add(post_url)

            if len(premium_posts) > 3:
                usages.append({
                    "title": f"…và {len(premium_posts) - 3} bài Premium khác",
                    "public_url": None,
                    "placement": "Các bài viết premium có paywall",
                    "status": "active",
                    "source": "premium_all",
                })
        else:
            # No premium posts yet, but configured
            usages.append({
                "title": "Bài viết Premium (chưa có)",
                "public_url": None,
                "placement": "Premium paywall CTA",
                "status": "configured",  # Configured but not in use yet
                "source": "premium_configured_unused",
            })

    # ===== 4. Template/hardcoded references =====
    elif "template" in category.lower():
        # General page locations where this might be rendered
        usages.append({
            "title": "Trang chủ",
            "public_url": BLOG_DOMAIN + "/",
            "placement": "Template-level placement",
            "status": "template_level",
            "source": "template",
        })

    # ===== 5. Content blocks (via content-placements.json) =====
    block_locations = [loc for loc in locations if loc.startswith("data/content-placements.json")]
    if block_locations:
        # Add info about content blocks
        for block_loc in block_locations[:3]:
            block_match = re.search(r'block:([^:]+)', block_loc)
            if block_match:
                block_id = block_match.group(1)
                usages.append({
                    "title": f"Content block: {block_id}",
                    "public_url": None,  # Blocks render on various pages
                    "placement": "Dynamic placement (content block)",
                    "status": "configured",
                    "source": "content_block",
                })

    # ===== 6. Fallback for unmapped locations =====
    if not usages:
        usages.append({
            "title": "Configuration detected",
            "public_url": None,
            "placement": "Link is configured globally",
            "status": "configured",
            "source": "unmapped",
        })

    return usages


def build_public_usage_data() -> dict[str, Any]:
    """Build complete public usage report."""
    audit_data = load_audit_data()
    cp_data = load_content_placements()
    posts = load_posting_urls()

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "blog_domain": BLOG_DOMAIN,
        "total_urls": 0,
        "links_with_public_usage": {},
    }

    links_by_url = audit_data.get("links_by_url", {})

    for url, link_info in links_by_url.items():
        public_usages = get_public_usages(url, link_info, posts)
        technical_usages = link_info.get("locations", [])

        report["links_with_public_usage"][url] = {
            "url": url,
            "category": link_info.get("category", "Unknown"),
            "post_slug": link_info.get("post_slug"),
            "post_title": link_info.get("post_title"),
            "public_usages": public_usages,  # For main modal view
            "technical_usages": technical_usages,  # For collapsed details
        }
        report["total_urls"] += 1

    return report


def main():
    """Generate and save public usage report."""
    try:
        data = build_public_usage_data()
        output_file = REPO_ROOT / "data" / "momo-public-usage.json"
        output_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✓ Generated {output_file.relative_to(REPO_ROOT)}")
        print(f"  Total URLs: {data['total_urls']}")
        return 0
    except Exception as e:
        print(f"✗ Error: {e}", file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    exit(main())
