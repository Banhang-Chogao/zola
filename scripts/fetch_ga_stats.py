"""
Fetch Google Analytics 4 stats qua Data API, output data/ga-stats.json.

Service Account key: env GA_SERVICE_ACCOUNT_KEY (JSON string).
Property: 541698865 (GA4 'banhang-chogao' blog).

Output format:
{
  "updated_at": "2026-06-15T12:30:00Z",
  "today_users": 42,
  "today_pageviews": 87,
  "week_users": 312,
  "week_pageviews": 654,
  "month_users": 1205,
  "month_pageviews": 2847
}

Chạy local (debug):
  export GA_SERVICE_ACCOUNT_KEY=$(cat key.json)
  python scripts/fetch_ga_stats.py
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)
from google.oauth2 import service_account

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "ga-stats.json"
PROPERTY_ID = "541698865"


def get_client():
    key_str = os.environ.get("GA_SERVICE_ACCOUNT_KEY", "")
    if not key_str:
        print("ERROR: GA_SERVICE_ACCOUNT_KEY env không có", file=sys.stderr)
        sys.exit(1)
    try:
        info = json.loads(key_str)
    except json.JSONDecodeError as e:
        print(f"ERROR: GA_SERVICE_ACCOUNT_KEY không phải JSON: {e}", file=sys.stderr)
        sys.exit(1)
    creds = service_account.Credentials.from_service_account_info(
        info,
        scopes=["https://www.googleapis.com/auth/analytics.readonly"],
    )
    return BetaAnalyticsDataClient(credentials=creds)


def fetch_metric(client, start: str, end: str) -> dict:
    req = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date=start, end_date=end)],
        metrics=[Metric(name="activeUsers"), Metric(name="screenPageViews")],
    )
    res = client.run_report(req)
    if not res.rows:
        return {"users": 0, "pageviews": 0}
    row = res.rows[0]
    return {
        "users": int(row.metric_values[0].value),
        "pageviews": int(row.metric_values[1].value),
    }


def main():
    client = get_client()
    today = fetch_metric(client, "today", "today")
    week = fetch_metric(client, "7daysAgo", "today")
    month = fetch_metric(client, "30daysAgo", "today")

    result = {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "today_users":      today["users"],
        "today_pageviews":  today["pageviews"],
        "week_users":       week["users"],
        "week_pageviews":   week["pageviews"],
        "month_users":      month["users"],
        "month_pageviews":  month["pageviews"],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT.relative_to(ROOT)}: {result}")


if __name__ == "__main__":
    main()
