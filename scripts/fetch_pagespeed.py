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
    "best_practices": 96,
    "seo": 100,
    "lcp": "1.8 s",
    "cls": "0.02",
    "fcp": "1.2 s",
    "tbt": "120 ms",
    "si": "2.4 s"
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


def fetch(strategy: str) -> dict:
    params = {
        "url": TARGET_URL,
        "strategy": strategy,
    }
    # category cần multiple values → tự manually serialize
    cats = ["performance", "accessibility", "best-practices", "seo"]
    qs = urlencode(params) + "&" + "&".join(f"category={c}" for c in cats)
    full = f"{API_BASE}?{qs}"

    # Optional API key qua env (cho rate limit cao)
    api_key = os.environ.get("PAGESPEED_API_KEY", "")
    if api_key:
        full += f"&key={api_key}"

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

    lhr = data.get("lighthouseResult", {})
    cats_res = lhr.get("categories", {})
    audits = lhr.get("audits", {})

    def pct(c):
        s = cats_res.get(c, {}).get("score")
        return round((s or 0) * 100) if s is not None else 0

    def audit_val(a):
        return audits.get(a, {}).get("displayValue", "—")

    return {
        "performance":     pct("performance"),
        "accessibility":   pct("accessibility"),
        "best_practices":  pct("best-practices"),
        "seo":             pct("seo"),
        "lcp":             audit_val("largest-contentful-paint"),
        "cls":             audit_val("cumulative-layout-shift"),
        "fcp":             audit_val("first-contentful-paint"),
        "tbt":             audit_val("total-blocking-time"),
        "si":              audit_val("speed-index"),
    }


def main():
    result = {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "url": TARGET_URL,
    }
    for strategy in ("mobile", "desktop"):
        result[strategy] = fetch(strategy)
        time.sleep(1)  # avoid burst rate
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT.relative_to(ROOT)}: mobile={result['mobile']['performance']}/100, "
          f"desktop={result['desktop']['performance']}/100")


if __name__ == "__main__":
    main()
