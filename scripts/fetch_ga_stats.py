"""
Fetch Google Analytics 4 stats qua Data API, output data/ga-stats.json.

Service Account key: env GA_SERVICE_ACCOUNT_KEY (JSON string).
Property: 542421812 (GA4 'banhang-chogao' blog).

Output format (mở rộng — gồm 6 chỉ số cơ bản + 5 chỉ số nâng cao 30d):
{
  "updated_at": "2026-06-15T12:30:00Z",
  "today_users": 42,
  "today_pageviews": 87,
  "week_users": 312,
  "week_pageviews": 654,
  "month_users": 1205,
  "month_pageviews": 2847,
  "month_sessions": 1543,
  "month_new_users": 912,
  "month_bounce_rate_pct": 33,
  "month_avg_session_duration_str": "1m 23s",
  "month_engagement_rate_pct": 67,
  "top_country": "Vietnam",
  "top_device": "mobile",
  "channels": [
    {"channel": "Organic Search", "sessions": 820, "users": 610, "percent": 53},
    {"channel": "Direct", "sessions": 410, "users": 320, "percent": 27}
  ],
  "organic": {"sessions": 820, "users": 610, "percent": 53}
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
    OrderBy,
    RunReportRequest,
)
from google.oauth2 import service_account
from google.api_core.exceptions import PermissionDenied

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "ga-stats.json"
PROPERTY_ID = "542421812"


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


def fetch_extended_30d(client) -> dict:
    """5 chỉ số nâng cao cho 30 ngày: sessions, new users, bounce, avg duration, engagement."""
    req = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date="30daysAgo", end_date="today")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="newUsers"),
            Metric(name="bounceRate"),
            Metric(name="averageSessionDuration"),
            Metric(name="engagementRate"),
        ],
    )
    res = client.run_report(req)
    if not res.rows:
        return {
            "sessions": 0,
            "new_users": 0,
            "bounce_rate_pct": 0,
            "avg_session_duration_str": "0s",
            "engagement_rate_pct": 0,
        }
    v = res.rows[0].metric_values
    sessions = int(v[0].value)
    new_users = int(v[1].value)
    bounce_rate = float(v[2].value) if v[2].value else 0.0
    avg_dur_sec = float(v[3].value) if v[3].value else 0.0
    engagement = float(v[4].value) if v[4].value else 0.0
    return {
        "sessions": sessions,
        "new_users": new_users,
        "bounce_rate_pct": round(bounce_rate * 100),
        "avg_session_duration_str": format_duration(avg_dur_sec),
        "engagement_rate_pct": round(engagement * 100),
    }


def fetch_top_dimension(client, dim: str, start: str = "7daysAgo") -> str:
    """Lấy giá trị dimension top 1 (country / deviceCategory) trong 7 ngày."""
    req = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date=start, end_date="today")],
        dimensions=[Dimension(name=dim)],
        metrics=[Metric(name="activeUsers")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="activeUsers"), desc=True)],
        limit=1,
    )
    res = client.run_report(req)
    if not res.rows or not res.rows[0].dimension_values:
        return "—"
    val = res.rows[0].dimension_values[0].value
    return val or "—"


def fetch_channels(client, start: str = "30daysAgo", top_n: int = 6) -> dict:
    """Phân tích nguồn truy cập theo kênh (Organic Search, Direct, Referral…) 30 ngày.

    Trả về:
      {
        "channels": [ {channel, sessions, users, percent}, ... ] (top_n, sort desc),
        "organic":  {sessions, users, percent}  # riêng Organic Search
      }
    Dùng dimension `sessionDefaultChannelGroup` (GA4 default channel grouping).
    """
    req = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date=start, end_date="today")],
        dimensions=[Dimension(name="sessionDefaultChannelGroup")],
        metrics=[Metric(name="sessions"), Metric(name="activeUsers")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
        limit=25,
    )
    res = client.run_report(req)
    rows = []
    total_sessions = 0
    for row in res.rows:
        name = row.dimension_values[0].value or "(other)"
        sessions = int(row.metric_values[0].value)
        users = int(row.metric_values[1].value)
        total_sessions += sessions
        rows.append({"channel": name, "sessions": sessions, "users": users})

    # Tính phần trăm theo tổng phiên
    for r in rows:
        r["percent"] = round(r["sessions"] / total_sessions * 100) if total_sessions else 0

    organic = next(
        (r for r in rows if r["channel"].lower().startswith("organic search")),
        None,
    )
    organic_out = (
        {
            "sessions": organic["sessions"],
            "users": organic["users"],
            "percent": organic["percent"],
        }
        if organic
        else {"sessions": 0, "users": 0, "percent": 0}
    )
    return {"channels": rows[:top_n], "organic": organic_out}


def format_duration(seconds: float) -> str:
    """Format giây thành 'Xm Ys' (hoặc 'Ys' nếu <60s)."""
    total = int(round(seconds))
    if total < 60:
        return f"{total}s"
    m, s = divmod(total, 60)
    return f"{m}m {s}s"


def get_fallback_stats():
    """Fallback stats when GA permission denied or unavailable."""
    return {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "today_users": 0,
        "today_pageviews": 0,
        "week_users": 0,
        "week_pageviews": 0,
        "month_users": 0,
        "month_pageviews": 0,
        "month_sessions": 0,
        "month_new_users": 0,
        "month_bounce_rate_pct": 0,
        "month_avg_session_duration_str": "0s",
        "month_engagement_rate_pct": 0,
        "top_country": "—",
        "top_device": "—",
        "channels": [],
        "organic": {"sessions": 0, "users": 0, "percent": 0},
    }


def main():
    try:
        client = get_client()
    except SystemExit:
        # get_client() calls sys.exit(1) on missing/invalid key
        print(
            "WARN: GA_SERVICE_ACCOUNT_KEY not configured; using fallback stats",
            file=sys.stderr,
        )
        result = get_fallback_stats()
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Wrote {OUTPUT.relative_to(ROOT)} (fallback): {result}")
        return

    try:
        today = fetch_metric(client, "today", "today")
        week = fetch_metric(client, "7daysAgo", "today")
        month = fetch_metric(client, "30daysAgo", "today")
        ext = fetch_extended_30d(client)
    except PermissionDenied as e:
        print(
            f"ERROR: GA permission denied. Service account may lack access to property {PROPERTY_ID}.",
            file=sys.stderr,
        )
        print(
            "WARN: Check that service account email is added to GA4 property with Viewer role.",
            file=sys.stderr,
        )
        print(f"WARN: Using fallback stats; details: {e}", file=sys.stderr)
        result = get_fallback_stats()
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Wrote {OUTPUT.relative_to(ROOT)} (fallback): {result}")
        return
    except Exception as e:
        print(f"ERROR: Failed to fetch GA metrics: {e}", file=sys.stderr)
        print("WARN: Using fallback stats", file=sys.stderr)
        result = get_fallback_stats()
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Wrote {OUTPUT.relative_to(ROOT)} (fallback): {result}")
        return

    try:
        top_country = fetch_top_dimension(client, "country")
    except Exception as e:
        print(f"WARN: country fetch fail: {e}", file=sys.stderr)
        top_country = "—"
    try:
        top_device = fetch_top_dimension(client, "deviceCategory")
    except Exception as e:
        print(f"WARN: device fetch fail: {e}", file=sys.stderr)
        top_device = "—"
    try:
        channel_data = fetch_channels(client)
    except Exception as e:
        print(f"WARN: channels fetch fail: {e}", file=sys.stderr)
        channel_data = {"channels": [], "organic": {"sessions": 0, "users": 0, "percent": 0}}

    result = {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "today_users":      today["users"],
        "today_pageviews":  today["pageviews"],
        "week_users":       week["users"],
        "week_pageviews":   week["pageviews"],
        "month_users":      month["users"],
        "month_pageviews":  month["pageviews"],
        "month_sessions":                  ext["sessions"],
        "month_new_users":                 ext["new_users"],
        "month_bounce_rate_pct":           ext["bounce_rate_pct"],
        "month_avg_session_duration_str": ext["avg_session_duration_str"],
        "month_engagement_rate_pct":       ext["engagement_rate_pct"],
        "top_country":                     top_country,
        "top_device":                      top_device,
        "channels":                        channel_data["channels"],
        "organic":                         channel_data["organic"],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT.relative_to(ROOT)}: {result}")


if __name__ == "__main__":
    main()
