"""
Fetch Google Analytics 4 stats qua Data API, output data/ga-stats.json.

Service Account key: env GA_SERVICE_ACCOUNT_KEY (JSON string).
Property: 542421812 (GA4 stream cho tên miền seomoney.org — 2026-06-21).

Cache isolation: output LUÔN đóng dấu `property_id` + `measurement_id` + `site`.
Giao diện chỉ render số khi `property_id` khớp `config.extra.ga_property_id`,
nên số liệu property cũ (github.io) không bao giờ rò rỉ. Có thể override
property qua env GA_PROPERTY_ID (mặc định 542421812) để test mà không sửa code.

Output format (production-standard: base metrics + extended 30d + organic search + channel breakdown):
{
  "updated_at": "2026-06-15T12:30:00Z",
  "property_id": "542421812",
  "measurement_id": "G-SMTFZVC0XN",
  "site": "seomoney.org",
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
  "organic_users": 287,
  "organic_sessions": 312,
  "organic_pageviews": 654,
  "organic_pct_traffic": 24,
  "channel_breakdown": {
    "Organic Search": {"users": 287, "sessions": 312},
    "Direct": {"users": 256, "sessions": 278},
    "Referral": {"users": 185, "sessions": 201},
    "Social": {"users": 142, "sessions": 155}
  },
  "top_country": "Vietnam",
  "top_device": "mobile"
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
    Filter,
    FilterExpression,
    Metric,
    OrderBy,
    RunReportRequest,
)
from google.oauth2 import service_account

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "ga-stats.json"
# Canonical identity after the seomoney.org domain move (2026-06-21).
# Env override allows a test run against a sandbox property without a code edit.
PROPERTY_ID = os.environ.get("GA_PROPERTY_ID", "542421812")
MEASUREMENT_ID = os.environ.get("GA_MEASUREMENT_ID", "G-SMTFZVC0XN")
SITE = os.environ.get("GA_SITE", "seomoney.org")


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


def fetch_organic_search_30d(client) -> dict:
    """Organic Search metrics cho 30 ngày: users, sessions, pageviews từ sessionDefaultChannelGroup."""
    try:
        req = RunReportRequest(
            property=f"properties/{PROPERTY_ID}",
            date_ranges=[DateRange(start_date="30daysAgo", end_date="today")],
            dimensions=[Dimension(name="sessionDefaultChannelGroup")],
            metrics=[
                Metric(name="activeUsers"),
                Metric(name="sessions"),
                Metric(name="screenPageViews"),
            ],
            dimension_filter=FilterExpression(
                filter=Filter(
                    field_name="sessionDefaultChannelGroup",
                    value="Organic Search",
                )
            ),
        )
        res = client.run_report(req)
        if not res.rows:
            return {
                "organic_users": 0,
                "organic_sessions": 0,
                "organic_pageviews": 0,
            }
        v = res.rows[0].metric_values
        organic_users = int(v[0].value) if v[0].value else 0
        organic_sessions = int(v[1].value) if v[1].value else 0
        organic_pageviews = int(v[2].value) if v[2].value else 0
        return {
            "organic_users": organic_users,
            "organic_sessions": organic_sessions,
            "organic_pageviews": organic_pageviews,
        }
    except Exception as e:
        print(f"WARN: organic search fetch fail: {e}", file=sys.stderr)
        return {
            "organic_users": 0,
            "organic_sessions": 0,
            "organic_pageviews": 0,
        }


def fetch_channel_breakdown_30d(client) -> dict:
    """Channel breakdown (Organic Search, Direct, Referral, Social) cho 30 ngày."""
    try:
        req = RunReportRequest(
            property=f"properties/{PROPERTY_ID}",
            date_ranges=[DateRange(start_date="30daysAgo", end_date="today")],
            dimensions=[Dimension(name="sessionDefaultChannelGroup")],
            metrics=[
                Metric(name="activeUsers"),
                Metric(name="sessions"),
            ],
            order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="activeUsers"), desc=True)],
            limit=10,
        )
        res = client.run_report(req)
        channels = {}
        for row in res.rows:
            if row.dimension_values:
                channel = row.dimension_values[0].value or "Other"
                users = int(row.metric_values[0].value) if row.metric_values[0].value else 0
                sessions = int(row.metric_values[1].value) if row.metric_values[1].value else 0
                channels[channel] = {"users": users, "sessions": sessions}
        return channels
    except Exception as e:
        print(f"WARN: channel breakdown fetch fail: {e}", file=sys.stderr)
        return {}


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


def format_duration(seconds: float) -> str:
    """Format giây thành 'Xm Ys' (hoặc 'Ys' nếu <60s)."""
    total = int(round(seconds))
    if total < 60:
        return f"{total}s"
    m, s = divmod(total, 60)
    return f"{m}m {s}s"


def main():
    client = get_client()
    today = fetch_metric(client, "today", "today")
    week = fetch_metric(client, "7daysAgo", "today")
    month = fetch_metric(client, "30daysAgo", "today")
    ext = fetch_extended_30d(client)
    organic = fetch_organic_search_30d(client)
    channels = fetch_channel_breakdown_30d(client)

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

    # Calculate organic search percentage of total traffic.
    organic_pct = 0
    if month["users"] > 0:
        organic_pct = round((organic["organic_users"] / month["users"]) * 100)

    result = {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        # Identity stamp → cache isolation by property/domain (no old-property leak).
        "property_id":    PROPERTY_ID,
        "measurement_id": MEASUREMENT_ID,
        "site":           SITE,
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
        "organic_users":                   organic["organic_users"],
        "organic_sessions":                organic["organic_sessions"],
        "organic_pageviews":               organic["organic_pageviews"],
        "organic_pct_traffic":             organic_pct,
        "channel_breakdown":               channels,
        "top_country":                     top_country,
        "top_device":                      top_device,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT.relative_to(ROOT)}: {result}")


if __name__ == "__main__":
    main()
