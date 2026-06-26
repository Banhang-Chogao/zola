"""
Fetch Google PageSpeed Insights scores qua API v5, output data/pagespeed.json.

API public, không cần auth (free 25k queries/day). Chỉ cần URL blog.

Output format:
{
  "updated_at": "2026-06-15T14:30:00Z",
  "url": "https://banhang-chogao.github.io/zola/",
  "mobile": {
    "performance": 92,
    "accessibility": 100,
    ...
    "lcp": "1.8 s",
    "resource_weight": { "js": 120000, "css": 45000, "image": 800000, "total": 1200000 },
    "opportunities": [...]
  },
  "desktop": { ... }
}
"""
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "pagespeed.json"
TARGET_URL = "https://banhang-chogao.github.io/zola/"
API_BASE = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

# Lighthouse audit ids dùng cho performance QA checker.
DETAIL_AUDIT_IDS = (
    "largest-contentful-paint",
    "cumulative-layout-shift",
    "interaction-to-next-paint",
    "total-blocking-time",
    "first-contentful-paint",
    "speed-index",
    "total-byte-weight",
    "render-blocking-resources",
    "unused-css-rules",
    "unused-javascript",
    "uses-optimized-images",
    "modern-image-formats",
    "uses-responsive-images",
    "font-display",
    "bootup-time",
    "third-party-summary",
)


def build_api_url(strategy: str, api_key: str = "") -> str:
    params = {"url": TARGET_URL, "strategy": strategy}
    cats = ["performance", "accessibility", "best-practices", "seo"]
    qs = urlencode(params) + "&" + "&".join(f"category={c}" for c in cats)
    full = f"{API_BASE}?{qs}"
    if api_key:
        full += f"&key={api_key}"
    return full


def fetch_lighthouse(strategy: str, api_key: str = "") -> dict:
    """Gọi PageSpeed API, trả raw lighthouseResult."""
    full = build_api_url(strategy, api_key)
    print(f"GET {strategy}...", flush=True)
    try:
        with urlopen(full, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        print(f"  HTTPError {e.code}: {e.read().decode()[:200]}", file=sys.stderr)
        raise
    except URLError as e:
        print(f"  URLError: {e}", file=sys.stderr)
        raise
    return data.get("lighthouseResult", {})


def _pct(cats_res: dict, category: str) -> int:
    score = cats_res.get(category, {}).get("score")
    return round((score or 0) * 100) if score is not None else 0


def _audit_display(audits: dict, audit_id: str) -> str:
    return audits.get(audit_id, {}).get("displayValue", "—")


def _audit_numeric(audits: dict, audit_id: str):
    audit = audits.get(audit_id, {})
    if "numericValue" in audit:
        return audit["numericValue"]
    return None


def _extract_resource_weight(audits: dict) -> dict:
    """Parse resource-summary hoặc total-byte-weight details."""
    weight = {"js": 0, "css": 0, "image": 0, "font": 0, "document": 0, "other": 0, "total": 0}
    summary = audits.get("resource-summary", {})
    items = summary.get("details", {}).get("items", [])
    if items:
        for item in items:
            rtype = (item.get("resourceType") or item.get("label") or "other").lower()
            size = int(item.get("transferSize") or item.get("size") or 0)
            if "script" in rtype or rtype == "js":
                weight["js"] += size
            elif "stylesheet" in rtype or rtype == "css":
                weight["css"] += size
            elif "image" in rtype:
                weight["image"] += size
            elif "font" in rtype:
                weight["font"] += size
            elif "document" in rtype:
                weight["document"] += size
            else:
                weight["other"] += size
            weight["total"] += size
        return weight

    tbw = audits.get("total-byte-weight", {})
    weight["total"] = int(tbw.get("numericValue") or 0)
    return weight


def _extract_opportunities(audits: dict) -> list:
    """Trích các audit performance có score < 1 (cơ hội cải thiện)."""
    opps = []
    for audit_id in DETAIL_AUDIT_IDS:
        audit = audits.get(audit_id, {})
        score = audit.get("score")
        if score is None:
            continue
        if score < 1:
            opps.append({
                "id": audit_id,
                "title": audit.get("title", audit_id),
                "display": audit.get("displayValue", ""),
                "score": round(score * 100),
            })
    opps.sort(key=lambda x: x["score"])
    return opps


def _extract_render_blocking(audits: dict) -> list:
    audit = audits.get("render-blocking-resources", {})
    items = audit.get("details", {}).get("items", [])
    result = []
    for item in items[:15]:
        result.append({
            "url": item.get("url", ""),
            "total_bytes": item.get("totalBytes", 0),
            "wasted_ms": item.get("wastedMs", 0),
        })
    return result


def _extract_unused_assets(audits: dict) -> dict:
    unused = {}
    for key, audit_id in (("css", "unused-css-rules"), ("js", "unused-javascript")):
        audit = audits.get(audit_id, {})
        items = audit.get("details", {}).get("items", [])
        wasted = sum(int(i.get("wastedBytes", 0) or 0) for i in items)
        unused[key] = {
            "wasted_bytes": wasted,
            "display": audit.get("displayValue", "—"),
            "items": [
                {"url": i.get("url", ""), "wasted_bytes": i.get("wastedBytes", 0)}
                for i in items[:10]
            ],
        }
    return unused


def _extract_image_issues(audits: dict) -> list:
    issues = []
    for audit_id in ("uses-optimized-images", "modern-image-formats", "uses-responsive-images"):
        audit = audits.get(audit_id, {})
        if audit.get("score", 1) >= 1:
            continue
        issues.append({
            "id": audit_id,
            "title": audit.get("title", audit_id),
            "display": audit.get("displayValue", ""),
        })
    return issues


def parse_lighthouse_result(lhr: dict) -> dict:
    """Chuyển lighthouseResult → dict metrics cho dashboard / QA checker."""
    cats_res = lhr.get("categories", {})
    audits = lhr.get("audits", {})

    return {
        "performance": _pct(cats_res, "performance"),
        "accessibility": _pct(cats_res, "accessibility"),
        "best_practices": _pct(cats_res, "best-practices"),
        "seo": _pct(cats_res, "seo"),
        "lcp": _audit_display(audits, "largest-contentful-paint"),
        "lcp_ms": _audit_numeric(audits, "largest-contentful-paint"),
        "cls": _audit_display(audits, "cumulative-layout-shift"),
        "cls_value": _audit_numeric(audits, "cumulative-layout-shift"),
        "inp": _audit_display(audits, "interaction-to-next-paint"),
        "inp_ms": _audit_numeric(audits, "interaction-to-next-paint"),
        "fcp": _audit_display(audits, "first-contentful-paint"),
        "fcp_ms": _audit_numeric(audits, "first-contentful-paint"),
        "tbt": _audit_display(audits, "total-blocking-time"),
        "tbt_ms": _audit_numeric(audits, "total-blocking-time"),
        "si": _audit_display(audits, "speed-index"),
        "si_ms": _audit_numeric(audits, "speed-index"),
        "total_page_size": _audit_display(audits, "total-byte-weight"),
        "total_page_bytes": int(_audit_numeric(audits, "total-byte-weight") or 0),
        "resource_weight": _extract_resource_weight(audits),
        "render_blocking": _extract_render_blocking(audits),
        "unused_assets": _extract_unused_assets(audits),
        "image_issues": _extract_image_issues(audits),
        "opportunities": _extract_opportunities(audits),
    }


def fetch(strategy: str, api_key: str = "") -> dict:
    """Backward-compatible: fetch + parse metrics."""
    lhr = fetch_lighthouse(strategy, api_key)
    return parse_lighthouse_result(lhr)


def main():
    api_key = os.environ.get("PAGESPEED_API_KEY", "")
    result = {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "url": TARGET_URL,
    }
    for strategy in ("mobile", "desktop"):
        result[strategy] = fetch(strategy, api_key)
        time.sleep(1)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        f"Wrote {OUTPUT.relative_to(ROOT)}: "
        f"mobile={result['mobile']['performance']}/100, "
        f"desktop={result['desktop']['performance']}/100"
    )


if __name__ == "__main__":
    main()