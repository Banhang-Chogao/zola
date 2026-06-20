"""
VIPZone Content Picker catalog — auto-discover tools + premium posts from Zola content.

Scans config.extra.menu (Công cụ), content/tools/, and premium-category posts.
"""

from __future__ import annotations

import re
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config.toml"
CONTENT = ROOT / "content"
BASE_URL = "https://seomoney.org"

MENU_TOOLS_NAME = "Công cụ"

EXCLUDE_SLUGS = frozenset({
    "vipzone-admin",
    "vipzone",
    "h-dashboard",
    "admin",
    "insights",
    "_index",
})

EXCLUDE_PATH_PREFIXES = (
    "/admin",
    "/admin-author",
    "/admin-countdown",
    "/insights",
    "/bao-cao-tong-ket",
    "/shortensea/admin",
    "/shortensea/insights",
    "/categories/",
)

EXCLUDE_PATH_SUBSTRINGS = (
    "vaccine-autofixer",
    "vaccine",
    "autofixer",
    "build-dashboard",
    "merge-report",
    "qa-404",
    "compliance-score",
    "qa-rule",
)

LEGACY_DROP_PICKS = frozenset({
    "/categories/premium/",
    "/categories/premium",
    "/insights/",
    "/insights",
})

PREMIUM_SCAN_DIRS = (
    CONTENT / "posting",
    CONTENT / "baochi",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("+++"):
        return {}
    m = re.match(r"^\+\+\+\s*\n(.*?)\n\+\+\+\s*\n?", text, re.DOTALL)
    if not m:
        return {}
    try:
        return tomllib.loads(m.group(1))
    except tomllib.TOMLDecodeError as exc:
        print(f"WARN: TOML parse fail {path}: {exc}", file=sys.stderr)
        return {}


def normalize_menu_url(url: str) -> str:
    u = (url or "").strip()
    u = u.replace("$BASE_URL", "").replace("https://seomoney.org", "")
    if not u.startswith("/"):
        u = "/" + u
    if not u.endswith("/"):
        u += "/"
    return u


def normalize_pick_url(url: str) -> str:
    u = (url or "").strip()
    u = u.replace("https://seomoney.org", "")
    if not u.startswith("/"):
        u = "/" + u
    if not u.endswith("/"):
        u += "/"
    return u


def slug_from_path(path: str) -> str:
    p = path.strip("/")
    if not p:
        return ""
    return p.split("/")[-1]


def is_excluded(path: str, slug: str) -> bool:
    path_norm = path.rstrip("/") or "/"
    path_lower = path_norm.lower()
    if slug in EXCLUDE_SLUGS:
        return True
    for prefix in EXCLUDE_PATH_PREFIXES:
        pl = prefix.rstrip("/")
        if path_lower == pl or path_lower.startswith(pl + "/"):
            return True
    for sub in EXCLUDE_PATH_SUBSTRINGS:
        if sub in path_lower:
            return True
    return False


def _flatten_menu_leaves(items: list[Any], out: list[dict[str, str]]) -> None:
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        url = item.get("url")
        children = item.get("children")
        if children:
            _flatten_menu_leaves(children, out)
        elif url:
            out.append({"name": name, "url": str(url)})


def load_menu_tools() -> list[dict[str, str]]:
    raw = CONFIG.read_text(encoding="utf-8")
    data = tomllib.loads(raw)
    menu = data.get("extra", {}).get("menu") or []
    for item in menu:
        if not isinstance(item, dict):
            continue
        if (item.get("name") or "").strip() == MENU_TOOLS_NAME:
            leaves: list[dict[str, str]] = []
            _flatten_menu_leaves(item.get("children") or [], leaves)
            return leaves
    return []


def path_to_content_file(path: str) -> Path | None:
    """Map site path to content markdown file if it exists."""
    p = path.strip("/")
    if not p:
        return None
    candidates = [
        CONTENT / f"{p}.md",
        CONTENT / p / "_index.md",
        CONTENT / "tools" / f"{slug_from_path(path)}.md",
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


def scan_content_tools() -> list[dict[str, str]]:
    tools_dir = CONTENT / "tools"
    if not tools_dir.is_dir():
        return []
    out: list[dict[str, str]] = []
    for md in sorted(tools_dir.glob("*.md")):
        slug = md.stem
        path = f"/tools/{slug}/"
        if is_excluded(path, slug):
            continue
        meta = parse_frontmatter(md)
        if meta.get("draft") is True:
            continue
        title = str(meta.get("title") or slug)
        out.append({"name": title, "url": path})
    return out


def scan_premium_posts() -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for base in PREMIUM_SCAN_DIRS:
        if not base.is_dir():
            continue
        section = base.name
        for md in sorted(base.rglob("*.md")):
            if md.name == "_index.md":
                continue
            meta = parse_frontmatter(md)
            if meta.get("draft") is True:
                continue
            cats = meta.get("taxonomies", {}).get("categories") or meta.get("categories") or []
            if isinstance(cats, str):
                cats = [cats]
            if "premium" not in [str(c).strip() for c in cats]:
                continue
            slug = md.stem
            path = f"/{section}/{slug}/"
            title = str(meta.get("title") or slug)
            items.append({"name": title, "url": path, "slug": slug})
    items.sort(key=lambda x: x["name"].lower())
    return items


def build_tool_entry(name: str, url: str) -> dict[str, str] | None:
    path = normalize_menu_url(url)
    slug = slug_from_path(path)
    if is_excluded(path, slug):
        return None
    title = name.strip() or slug
    content_path = path_to_content_file(path)
    if content_path:
        meta = parse_frontmatter(content_path)
        if meta.get("draft") is True:
            return None
        if meta.get("title"):
            title = str(meta["title"])
    return {"slug": slug, "title": title, "url": path}


def build_catalog() -> dict[str, Any]:
    seen_urls: set[str] = set()
    tools: list[dict[str, str]] = []

    for leaf in load_menu_tools():
        entry = build_tool_entry(leaf.get("name", ""), leaf.get("url", ""))
        if entry and entry["url"] not in seen_urls:
            seen_urls.add(entry["url"])
            tools.append(entry)

    for leaf in scan_content_tools():
        entry = build_tool_entry(leaf.get("name", ""), leaf.get("url", ""))
        if entry and entry["url"] not in seen_urls:
            seen_urls.add(entry["url"])
            tools.append(entry)

    tools.sort(key=lambda x: x["title"].lower())

    premium_raw = scan_premium_posts()
    premium = [
        {"slug": p["slug"], "title": p["name"], "url": normalize_pick_url(p["url"])}
        for p in premium_raw
    ]

    return {
        "updated_at": _now_iso(),
        "base_url": BASE_URL,
        "tools": tools,
        "premium": premium,
    }


def all_catalog_urls(catalog: dict[str, Any]) -> set[str]:
    urls: set[str] = set()
    for key in ("tools", "premium"):
        for item in catalog.get(key) or []:
            if item.get("url"):
                urls.add(normalize_pick_url(item["url"]))
    return urls


def migrate_picks(picks: list[str], catalog: dict[str, Any]) -> list[str]:
    """Normalize saved picks; drop legacy/invalid; map by slug when possible."""
    valid = all_catalog_urls(catalog)
    slug_to_url: dict[str, str] = {}
    for key in ("tools", "premium"):
        for item in catalog.get(key) or []:
            slug = item.get("slug") or slug_from_path(item.get("url", ""))
            if slug:
                slug_to_url[slug] = normalize_pick_url(item["url"])

    result: list[str] = []
    seen: set[str] = set()

    for raw in picks or []:
        p = normalize_pick_url(raw)
        if p in LEGACY_DROP_PICKS:
            continue
        if p in valid:
            if p not in seen:
                seen.add(p)
                result.append(p)
            continue
        slug = slug_from_path(p)
        mapped = slug_to_url.get(slug)
        if mapped and mapped not in seen:
            seen.add(mapped)
            result.append(mapped)

    return result