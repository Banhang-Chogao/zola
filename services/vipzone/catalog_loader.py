"""Load VIPZone picker catalog (local file or published JSON URL)."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import httpx

_cache: dict[str, Any] = {"at": 0.0, "data": None}
_CACHE_TTL = 300


def _catalog_paths() -> list[Path]:
    paths: list[Path] = []
    env_path = os.getenv("VIPZONE_CATALOG_PATH", "").strip()
    if env_path:
        paths.append(Path(env_path))
    here = Path(__file__).resolve().parent
    paths.append(here.parent.parent / "data" / "vipzone-picker-catalog.json")
    paths.append(here / "vipzone-picker-catalog.json")
    return paths


def _load_local() -> dict[str, Any] | None:
    for p in _catalog_paths():
        if p.is_file():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
    return None


async def _fetch_remote(url: str) -> dict[str, Any] | None:
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            res = await client.get(url)
        if res.status_code != 200:
            return None
        return res.json()
    except (httpx.HTTPError, json.JSONDecodeError):
        return None


async def load_catalog() -> dict[str, Any]:
    global _cache
    now = time.time()
    if _cache["data"] and now - _cache["at"] < _CACHE_TTL:
        return _cache["data"]

    data = _load_local()
    if not data:
        blog = os.getenv("VIPZONE_BLOG_URL", "https://banhang-chogao.github.io/zola").rstrip("/")
        url = os.getenv("VIPZONE_CATALOG_URL", f"{blog}/data/vipzone-picker-catalog.json")
        data = await _fetch_remote(url)

    if not data:
        data = {"updated_at": None, "tools": [], "premium": []}

    _cache["at"] = now
    _cache["data"] = data
    return data


def migrate_picks_sync(picks: list[str], catalog: dict[str, Any]) -> list[str]:
    """Inline migration (mirrors scripts/vipzone_picker_catalog.migrate_picks)."""

    def norm(u: str) -> str:
        x = (u or "").strip().replace("https://banhang-chogao.github.io/zola", "")
        if not x.startswith("/"):
            x = "/" + x
        return x if x.endswith("/") else x + "/"

    def slug(p: str) -> str:
        s = p.strip("/")
        return s.split("/")[-1] if s else ""

    legacy_drop = {
        "/categories/premium/",
        "/categories/premium",
        "/insights/",
        "/insights",
    }
    valid = {norm(i["url"]) for key in ("tools", "premium") for i in catalog.get(key) or []}
    slug_map = {
        (i.get("slug") or slug(i.get("url", ""))): norm(i["url"])
        for key in ("tools", "premium")
        for i in catalog.get(key) or []
        if i.get("url")
    }

    out: list[str] = []
    seen: set[str] = set()
    for raw in picks or []:
        p = norm(raw)
        if p in legacy_drop:
            continue
        if p in valid:
            if p not in seen:
                seen.add(p)
                out.append(p)
            continue
        mapped = slug_map.get(slug(p))
        if mapped and mapped not in seen:
            seen.add(mapped)
            out.append(mapped)
    return out