"""
Fetch Google Search Console stats via VIPZone backend API → data/gsc-stats.json.

Calls the public /gsc/metrics endpoint on the VIPZone backend (which caches
real GSC API responses). Transforms the response to match the template schema
in templates/partials/google-snapshot.html.

Output schema:
{
  "updated_at": "ISO timestamp",
  "totals": {
    "clicks": 1234,
    "impressions": 56789,
    "ctr_pct": 2.17,
    "position": 18.5
  },
  "top_page": "/some-article-slug/"
}

Chạy:
  python scripts/fetch_gsc_stats.py
  # env GSC_API_URL tuỳ chọn (mặc định backend Render)
"""
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "gsc-stats.json"
BACKEND = os.environ.get(
    "GSC_API_URL",
    "https://blog-vipzone-api.onrender.com/gsc/metrics",
)
TIMEOUT = 15  # seconds


def fetch_from_backend() -> dict | None:
    """Call VIPZone /gsc/metrics — returns parsed JSON or None."""
    try:
        req = urllib.request.Request(BACKEND, method="GET")
        req.add_header("Accept", "application/json")
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"WARN: Backend returned HTTP {e.code}: {e.read().decode(errors='replace')}", file=sys.stderr)
        return None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"WARN: Backend request failed: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"WARN: Backend response not JSON: {e}", file=sys.stderr)
        return None


def transform(raw: dict) -> dict:
    """Transform backend response → template schema.

    Backend returns:
      { clicks: 1234, impressions: 56789, ctr: 0.0217,
        avg_position: 18.5, top_pages: [{page: "/slug/", ...}], ... }

    Template expects:
      { totals: { clicks, impressions, ctr_pct, position }, top_page: "/slug/" }
    """
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if not raw or raw.get("connected") is False or raw.get("status") in (
        "not_connected", "not_configured", "token_expired", "error"
    ):
        return _fallback(now, raw.get("status", "disconnected") if raw else "empty")

    # Extract totals
    clicks = raw.get("clicks")
    impressions = raw.get("impressions")
    ctr_raw = raw.get("ctr")          # decimal like 0.0217
    avg_pos = raw.get("avg_position")

    # ctr_pct = ctr * 100, rounded to 2 decimal
    ctr_pct = round(ctr_raw * 100, 2) if ctr_raw is not None else None

    # Top page
    top_pages = raw.get("top_pages", [])
    top_page = ""
    if top_pages and len(top_pages) > 0:
        page_url = top_pages[0].get("page", "")
        # Normalise: ensure leading slash, strip trailing slash for consistency
        if page_url:
            page_url = "/" + page_url.lstrip("/").rstrip("/") + "/"
            top_page = page_url

    return {
        "updated_at": now,
        "totals": {
            "clicks": clicks,
            "impressions": impressions,
            "ctr_pct": ctr_pct,
            "position": round(avg_pos, 1) if avg_pos is not None else None,
        },
        "top_page": top_page,
    }


def _fallback(now: str, reason: str = "disconnected") -> dict:
    return {
        "updated_at": now,
        "status_note": reason,
        "totals": {
            "clicks": None,
            "impressions": None,
            "ctr_pct": None,
            "position": None,
        },
        "top_page": "",
    }


def main():
    raw = fetch_from_backend()
    result = transform(raw)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    status = raw.get("status", "unknown") if raw else "unreachable"
    print(
        f"Wrote {OUTPUT.relative_to(ROOT)} "
        f"(status={status}): "
        f"{result.get('totals', {}).get('clicks', '—')} clicks, "
        f"{result.get('top_page', '—')} top page"
    )


if __name__ == "__main__":
    main()
