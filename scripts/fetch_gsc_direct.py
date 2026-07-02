#!/usr/bin/env python3
"""
Fetch Google Search Console data TRỰC TIẾP từ GSC API.
KHÔNG cần VIPZone backend — chỉ cần Google service account credentials.

Cách dùng:
  1. Tải credentials JSON từ Google Cloud Console
  2. Lưu vào: ~/.gsc-credentials.json (hoặc env GSC_CREDENTIALS_PATH)
  3. Chạy: python scripts/fetch_gsc_direct.py

Output: data/gsc-stats.json
"""
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    from google.auth.transport.requests import Request
    from google.oauth2.service_account import Credentials
    from google.auth.exceptions import GoogleAuthError
except ImportError:
    print("WARN: google-auth library not installed.")
    print("Install: pip install google-auth google-auth-oauthlib google-auth-httplib2")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "gsc-stats.json"

# Credentials file — ưu tiên từ env var, fallback ~/.gsc-credentials.json
CREDENTIALS_PATH = os.environ.get(
    "GSC_CREDENTIALS_PATH",
    Path.home() / ".gsc-credentials.json"
)

GSC_PROPERTY = os.environ.get("GSC_PROPERTY_URL", "sc-domain:seomoney.org")
SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]


def load_credentials():
    """Load service account credentials từ JSON file."""
    try:
        with open(CREDENTIALS_PATH) as f:
            creds_data = json.load(f)
        credentials = Credentials.from_service_account_info(creds_data, scopes=SCOPES)
        return credentials
    except FileNotFoundError:
        print(f"ERROR: Credentials file not found: {CREDENTIALS_PATH}")
        print("  1. Download từ https://console.cloud.google.com/iam-admin/serviceaccounts")
        print("  2. Lưu vào ~/.gsc-credentials.json")
        print("  Hoặc set env: export GSC_CREDENTIALS_PATH=/path/to/credentials.json")
        return None
    except (json.JSONDecodeError, KeyError) as e:
        print(f"ERROR: Invalid credentials file: {e}")
        return None


def fetch_gsc_data(credentials) -> dict | None:
    """Fetch GSC metrics từ Google Search Console API."""
    try:
        # Refresh token nếu cần
        request = Request()
        credentials.refresh(request)

        import httplib2
        from googleapiclient.discovery import build

        service = build("webmasters", "v3", credentials=credentials, cache_discovery=False)

        # Last 7 days
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=7)

        print(f"Fetching GSC data for {GSC_PROPERTY} ({start_date} to {end_date})...")

        # Query: aggregate metrics
        response = service.searchanalytics().query(
            siteUrl=GSC_PROPERTY,
            body={
                "startDate": start_date.isoformat(),
                "endDate": end_date.isoformat(),
                "dimensions": ["page"],
                "rowLimit": 10,
            }
        ).execute()

        rows = response.get("rows", [])
        if not rows:
            print("WARN: No GSC data returned (site may not be indexed yet)")
            return None

        # Aggregate totals
        total_clicks = sum(row.get("clicks", 0) for row in rows)
        total_impressions = sum(row.get("impressions", 0) for row in rows)
        total_ctr = sum(row.get("ctr", 0) for row in rows) / len(rows) if rows else 0
        avg_position = sum(row.get("position", 0) for row in rows) / len(rows) if rows else 0

        # Top page
        top_page = ""
        if rows:
            top_page_url = rows[0].get("keys", [None])[0]
            if top_page_url:
                top_page = top_page_url if top_page_url.startswith("/") else f"/{top_page_url}"

        return {
            "clicks": int(total_clicks),
            "impressions": int(total_impressions),
            "ctr": round(total_ctr, 4),
            "avg_position": round(avg_position, 1),
            "top_page": top_page,
            "rows_count": len(rows),
        }

    except GoogleAuthError as e:
        print(f"ERROR: Google Auth failed: {e}")
        return None
    except Exception as e:
        print(f"ERROR: GSC API call failed: {e}")
        return None


def transform(raw: dict) -> dict:
    """Transform raw GSC data → template schema."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if not raw:
        return {
            "updated_at": now,
            "status_note": "error",
            "totals": {
                "clicks": None,
                "impressions": None,
                "ctr_pct": None,
                "position": None,
            },
            "top_page": "",
        }

    ctr_pct = round(raw.get("ctr", 0) * 100, 2)

    return {
        "updated_at": now,
        "status": "connected",
        "totals": {
            "clicks": raw.get("clicks"),
            "impressions": raw.get("impressions"),
            "ctr_pct": ctr_pct,
            "position": raw.get("avg_position"),
        },
        "top_page": raw.get("top_page", ""),
    }


def main():
    credentials = load_credentials()
    if not credentials:
        sys.exit(1)

    raw = fetch_gsc_data(credentials)
    result = transform(raw)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    status = "success" if raw else "failed"
    clicks = result.get("totals", {}).get("clicks", "—")
    top_page = result.get("top_page", "—")
    print(f"✓ Wrote {OUTPUT.relative_to(ROOT)} (status={status}): {clicks} clicks, {top_page}")


if __name__ == "__main__":
    main()
