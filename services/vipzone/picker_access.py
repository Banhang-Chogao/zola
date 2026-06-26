"""VIPZone Content Picker — access levels + legacy migration."""

from __future__ import annotations

from typing import Any

ACCESS_PUBLIC = "public"
ACCESS_PREMIUM = "premium"
ACCESS_ADMIN_ONLY = "admin_only"
ACCESS_LEVELS = frozenset({ACCESS_PUBLIC, ACCESS_PREMIUM, ACCESS_ADMIN_ONLY})

LEGACY_DROP_PICKS = frozenset({
    "/categories/premium/",
    "/categories/premium",
    "/insights/",
    "/insights",
})


def norm_url(url: str) -> str:
    x = (url or "").strip().replace("https://seomoney.org", "")
    if not x.startswith("/"):
        x = "/" + x
    return x if x.endswith("/") else x + "/"


def slug_from_path(path: str) -> str:
    s = path.strip("/")
    return s.split("/")[-1] if s else ""


def catalog_valid_urls(catalog: dict[str, Any]) -> set[str]:
    return {norm_url(i["url"]) for key in ("tools", "premium") for i in catalog.get(key) or [] if i.get("url")}


def catalog_slug_map(catalog: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key in ("tools", "premium"):
        for item in catalog.get(key) or []:
            if not item.get("url"):
                continue
            slug = item.get("slug") or slug_from_path(item["url"])
            if slug:
                out[slug] = norm_url(item["url"])
    return out


def normalize_access(value: str | None, *, default: str = ACCESS_PREMIUM) -> str:
    v = (value or "").strip().lower()
    return v if v in ACCESS_LEVELS else default


def normalize_item(raw: str | dict[str, Any], *, default_access: str = ACCESS_PREMIUM) -> dict[str, str] | None:
    if isinstance(raw, str):
        url = norm_url(raw)
        if url in LEGACY_DROP_PICKS:
            return None
        return {"url": url, "access": default_access}
    if not isinstance(raw, dict):
        return None
    url = norm_url(str(raw.get("url") or ""))
    if not url or url == "/":
        return None
    if url in LEGACY_DROP_PICKS:
        return None
    return {"url": url, "access": normalize_access(raw.get("access"), default=default_access)}


def migrate_picker_items(raw: list[Any] | None, catalog: dict[str, Any]) -> list[dict[str, str]]:
    """Normalize saved picker config; drop invalid; map legacy slug URLs."""
    valid = catalog_valid_urls(catalog)
    slug_map = catalog_slug_map(catalog)
    default_access = ACCESS_PREMIUM

    is_legacy_strings = bool(raw) and all(isinstance(x, str) for x in raw)
    out: list[dict[str, str]] = []
    seen: set[str] = set()

    for entry in raw or []:
        item = normalize_item(entry, default_access=default_access)
        if not item:
            continue
        url = item["url"]
        if url not in valid:
            mapped = slug_map.get(slug_from_path(url))
            if mapped:
                url = mapped
                item = {"url": url, "access": item["access"]}
            else:
                continue
        if url not in valid or url in seen:
            continue
        if is_legacy_strings and item["access"] == ACCESS_PUBLIC:
            item["access"] = ACCESS_PREMIUM
        seen.add(url)
        out.append(item)

    return out


def sparse_items(items: list[dict[str, str]]) -> list[dict[str, str]]:
    """Persist only gated entries (non-public)."""
    return [i for i in items if i.get("access") and i["access"] != ACCESS_PUBLIC]


def expand_items(sparse: list[dict[str, str]], catalog: dict[str, Any]) -> list[dict[str, str]]:
    """Merge sparse config with full catalog for admin UI."""
    access_map = items_to_map(sparse)
    expanded: list[dict[str, str]] = []
    for key in ("tools", "premium"):
        for item in catalog.get(key) or []:
            if not item.get("url"):
                continue
            url = norm_url(item["url"])
            expanded.append({"url": url, "access": access_map.get(url, ACCESS_PUBLIC)})
    return expanded


def items_to_map(items: list[dict[str, str]]) -> dict[str, str]:
    return {norm_url(i["url"]): normalize_access(i.get("access")) for i in items if i.get("url")}


def can_access_content(
    access: str,
    *,
    is_super: bool = False,
    is_admin: bool = False,
    is_vip: bool = False,
) -> bool:
    level = normalize_access(access, default=ACCESS_PUBLIC)
    if level == ACCESS_PUBLIC:
        return True
    if is_super or is_admin:
        return True
    if level == ACCESS_ADMIN_ONLY:
        return False
    if level == ACCESS_PREMIUM:
        return is_vip
    return True