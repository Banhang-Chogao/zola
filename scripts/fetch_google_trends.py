#!/usr/bin/env python3
"""
Fetch trending searches for Vietnam from Google Trends.

Primary: Trends UI batchexecute (same data as trends.google.com/trending?geo=VN).
Fallback: official RSS feed (fewer items).
Cache: keeps previous data/google-trends-vn.json on total failure.

Run before `zola build` (deploy.yml) and hourly via .github/workflows/google-trends.yml.

Usage:
    python3 scripts/fetch_google_trends.py
    python3 scripts/fetch_google_trends.py --limit 25
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from http.cookiejar import CookieJar
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "google-trends-vn.json"
GEO = "VN"
HL = "vi"
LIMIT_DEFAULT = 25
SOURCE_PAGE = f"https://trends.google.com/trending?geo={GEO}"
RSS_URL = f"https://trends.google.com/trending/rss?geo={GEO}"
USER_AGENT = (
    "Mozilla/5.0 (compatible; ZolaBlogTrendsBot/1.0; +https://seomoney.org/)"
)
NS = {"ht": "https://trends.google.com/trending/rss"}


def format_volume(value: int | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    n = int(value)
    if n >= 1000:
        return f"{n // 1000}K+"
    return f"{n}+"


def search_url(keyword: str) -> str:
    q = urllib.parse.quote_plus(keyword)
    return f"https://www.google.com/search?q={q}&gl=vn&hl=vi"


def trends_explore_url(keyword: str) -> str:
    q = urllib.parse.quote(keyword)
    return f"https://trends.google.com/trends/explore?q={q}&geo={GEO}"


def _opener() -> urllib.request.OpenerDirector:
    cj = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    opener.addheaders = [("User-Agent", USER_AGENT)]
    return opener


def fetch_batchexecute(limit: int) -> list[dict]:
    """Trending now list via internal Trends UI RPC (i0OFE)."""
    opener = _opener()
    opener.open(urllib.request.Request(SOURCE_PAGE), timeout=30)

    payload = json.dumps(
        [[["i0OFE", json.dumps([None, None, GEO, 0, HL, 24, 1]), None, "generic"]]]
    )
    body = urllib.parse.urlencode({"f.req": payload}).encode()
    url = (
        "https://trends.google.com/_/TrendsUi/data/batchexecute"
        "?rpcids=i0OFE&source-path=%2Ftrending&hl=vi&rt=c"
    )
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded;charset=UTF-8")

    raw = opener.open(req, timeout=30).read().decode("utf-8", errors="replace")
    data_line = next(
        (ln for ln in raw.splitlines() if ln.strip().startswith("[[\"wrb.fr\",\"i0OFE\"")),
        "",
    )
    if not data_line:
        raise RuntimeError("batchexecute: missing i0OFE response line")

    outer = json.loads(data_line)
    inner = json.loads(outer[0][2])
    trends = inner[1] if inner and len(inner) > 1 and inner[1] else []

    items: list[dict] = []
    for idx, row in enumerate(trends[:limit], start=1):
        keyword = (row[0] or "").strip()
        if not keyword:
            continue
        volume = row[6] if len(row) > 6 else None
        items.append(
            {
                "rank": idx,
                "keyword": keyword,
                "volume": volume if isinstance(volume, int) else None,
                "volume_label": format_volume(volume),
                "search_url": search_url(keyword),
                "trends_url": trends_explore_url(keyword),
            }
        )
    if not items:
        raise RuntimeError("batchexecute: empty trend list")
    return items


def fetch_rss(limit: int) -> list[dict]:
    """Official Google Trends RSS — typically ~10 items."""
    req = urllib.request.Request(RSS_URL)
    req.add_header("User-Agent", USER_AGENT)
    xml_text = urllib.request.urlopen(req, timeout=30).read()
    root = ET.fromstring(xml_text)
    channel = root.find("channel")
    if channel is None:
        raise RuntimeError("rss: no channel")

    items: list[dict] = []
    for idx, item in enumerate(channel.findall("item")[:limit], start=1):
        title_el = item.find("title")
        keyword = (title_el.text or "").strip() if title_el is not None else ""
        if not keyword:
            continue
        traffic_el = item.find("ht:approx_traffic", NS)
        label = (traffic_el.text or "").strip() if traffic_el is not None else ""
        vol_match = re.search(r"(\d+)", label.replace(",", ""))
        volume = int(vol_match.group(1)) if vol_match else None
        items.append(
            {
                "rank": idx,
                "keyword": keyword,
                "volume": volume,
                "volume_label": label or format_volume(volume),
                "search_url": search_url(keyword),
                "trends_url": trends_explore_url(keyword),
            }
        )
    if not items:
        raise RuntimeError("rss: no items")
    return items


def load_cache() -> dict | None:
    if not OUTPUT.exists():
        return None
    try:
        return json.loads(OUTPUT.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"WARN: cannot read cache {OUTPUT}: {exc}", file=sys.stderr)
        return None


def build_document(items: list[dict], source: str, status: str, note: str = "") -> dict:
    return {
        "geo": GEO,
        "title": "Today hot search",
        "source_page": SOURCE_PAGE,
        "source_rss": RSS_URL,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": status,
        "source": source,
        "count": len(items),
        "note": note,
        "items": items,
    }


def fetch_trends(limit: int) -> dict:
    errors: list[str] = []

    try:
        items = fetch_batchexecute(limit)
        return build_document(items, "batchexecute", "ok")
    except Exception as exc:
        errors.append(f"batchexecute: {exc}")
        print(f"WARN: {errors[-1]}", file=sys.stderr)

    try:
        items = fetch_rss(limit)
        note = ""
        if len(items) < limit:
            note = f"RSS returned {len(items)} items (requested {limit})"
        return build_document(items, "rss", "partial", note)
    except Exception as exc:
        errors.append(f"rss: {exc}")
        print(f"WARN: {errors[-1]}", file=sys.stderr)

    cache = load_cache()
    if cache and cache.get("items"):
        cache = dict(cache)
        cache["status"] = "cached"
        cache["fetched_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        cache["note"] = "Using cached data; fetch failed: " + "; ".join(errors)
        print(f"WARN: using cache ({len(cache['items'])} items)", file=sys.stderr)
        return cache

    raise RuntimeError("All fetch methods failed and no cache: " + "; ".join(errors))


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Google Trends VN → data/google-trends-vn.json")
    parser.add_argument("--limit", type=int, default=LIMIT_DEFAULT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    doc = fetch_trends(args.limit)
    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"

    if args.dry_run:
        print(text)
        return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(text, encoding="utf-8")
    print(
        f"Wrote {OUTPUT} — {doc['count']} trends via {doc['source']} ({doc['status']})",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        # Do not fail deploy if cache exists — write stale cache marker
        cache = load_cache()
        if cache:
            print("WARN: exiting 0 with existing cache on disk", file=sys.stderr)
            raise SystemExit(0)
        raise SystemExit(1)