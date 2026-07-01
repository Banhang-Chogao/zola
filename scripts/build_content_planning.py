#!/usr/bin/env python3
"""Generate data/content-planning.json from Ad-Report V2 + GA stats."""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA_DIR = ROOT / "data"

TZ_OFFSET = timedelta(hours=7)

def load_json(path):
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)

def build():
    ad_report = load_json(DATA_DIR / "ad-report-v2.json")
    ga_stats = load_json(DATA_DIR / "ga-stats.json")
    pagespeed = load_json(DATA_DIR / "pagespeed.json")

    if not ad_report:
        print("data/ad-report-v2.json not found — cannot build plan", file=sys.stderr)
        return 1

    generated_at = datetime.now(timezone(TZ_OFFSET)).isoformat()

    rev = ad_report.get("revenue_opportunities", {})
    top_cats = rev.get("top_categories", [])
    suggestions = ad_report.get("action_suggestions", {})
    immediate = suggestions.get("immediate_actions", [])
    rpm_boosters = ad_report.get("rpm_booster_suggestions", [])
    if isinstance(rpm_boosters, str):
        rpm_boosters = [rpm_boosters]
    scan_stats = ad_report.get("scan_stats", {})
    high_value = ad_report.get("high_value_keywords", [])

    monetization_score = ad_report.get("monetization_score", 0)
    mobile_perf = ad_report.get("pagespeed_snapshot", {}).get("mobile_performance", 0)
    lcp = ad_report.get("pagespeed_snapshot", {}).get("lcp", "N/A")
    site_seo_score = scan_stats.get("site_seo_score", 0)
    total_posts = scan_stats.get("total_posts", 0)

    ga_month_users = 0
    ga_month_bounce = 0
    ga_month_duration = "N/A"
    if ga_stats:
        ga_month_users = ga_stats.get("month_users", 0)
        ga_month_bounce = ga_stats.get("month_bounce_rate_pct", 0)
        ga_month_duration = ga_stats.get("month_avg_session_duration_str", "N/A")

    # Build priorities from categories sorted by RPM
    priorities = []
    low_volume_cats = [c for c in top_cats if c.get("post_count", 100) < 20]
    high_rpm_cats = sorted(top_cats, key=lambda c: c.get("avg_rpm_potential", 0), reverse=True)

    if high_rpm_cats:
        top = high_rpm_cats[0]
        priorities.append({
            "level": "🔴 Cao",
            "topic": f"{top['category']} — RPM {top['avg_rpm_potential']}",
            "reason": f"RPM potential cao nhất, hiện có {top['post_count']} bài",
            "action": f"Viết {min(3, max(2, 20 - top['post_count']))} bài mở rộng cluster"
        })

    if low_volume_cats:
        vol = low_volume_cats[0]
        priorities.append({
            "level": "🟡 Trung",
            "topic": f"{vol['category']} — {vol['post_count']} bài, RPM {vol['avg_rpm_potential']}",
            "reason": f"Content gap: chỉ {vol['post_count']} bài, cần mở rộng",
            "action": f"Tạo {min(3, 15 - vol['post_count'])} bài cluster"
        })

    if high_value:
        kw = high_value[0]
        priorities.append({
            "level": "🟢 Thấp",
            "topic": f"{kw['topic']} — {kw['mentions']} mentions",
            "reason": "Keyword coverage ổn định, duy trì tần suất",
            "action": "Duy trì tần suất hiện tại"
        })

    now = datetime.now(timezone(TZ_OFFSET))
    weekday = now.strftime("%A")
    weekday_vi = {"Monday": "Thứ Hai", "Tuesday": "Thứ Ba", "Wednesday": "Thứ Tư",
                  "Thursday": "Thứ Năm", "Friday": "Thứ Sáu", "Saturday": "Thứ Bảy",
                  "Sunday": "Chủ Nhật"}.get(weekday, weekday)

    today_suggestion = "Viết bài cluster Ngân hàng — RPM potential cao nhất"
    tomorrow_suggestion = "Bổ sung FAQ schema cho top posts"
    this_week_suggestions = []

    if immediate:
        for ia in immediate[:2]:
            detail = ia["detail"]
            if len(detail) > 60:
                detail = detail[:60] + "…"
            this_week_suggestions.append(f"{ia['action']} — {detail}")
    if rpm_boosters:
        for rb in rpm_boosters[:2]:
            if rb not in this_week_suggestions:
                this_week_suggestions.append(rb)

    # Content gaps
    content_gaps = []
    for c in low_volume_cats[:4]:
        needed = max(3, 15 - c.get("post_count", 0))
        gap = f"{c['category']}: chỉ {c['post_count']} bài, RPM {c['avg_rpm_potential']} — cần {needed} bài"
        content_gaps.append(gap)

    # Quick stats
    stats = []
    stats.append(f"Môn hóa điểm: {monetization_score}/100")
    if mobile_perf:
        stats.append(f"Mobile Performance: {mobile_perf}/100")
    if lcp:
        stats.append(f"LCP: {lcp}")
    if site_seo_score:
        stats.append(f"Site SEO: {site_seo_score}/100")
    stats.append(f"Tổng bài: {total_posts}")
    if ga_month_users:
        stats.append(f"Lượt truy cập tháng: {ga_month_users}")

    plan = {
        "generated_at": generated_at,
        "weekday": weekday_vi,
        "date": now.strftime("%d/%m/%Y"),
        "priorities": priorities,
        "schedule": {
            "today": today_suggestion,
            "tomorrow": tomorrow_suggestion,
            "this_week": this_week_suggestions
        },
        "content_gaps": content_gaps,
        "stats": stats
    }

    output_path = DATA_DIR / "content-planning.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)
    print(f"→ {output_path} ({len(json.dumps(plan, ensure_ascii=False))} bytes)")
    return 0

if __name__ == "__main__":
    sys.exit(build())
