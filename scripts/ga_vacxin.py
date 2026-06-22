#!/usr/bin/env python3
"""GA Vacxin — hourly Google Analytics 4 health monitor for the GA stats module.

After the seomoney.org domain move the GA stats footer module must read ONLY the
new GA4 property (542421812 · measurement G-SMTFZVC0XN) and never surface stale
numbers from the old github.io property. GA Vacxin is the watchdog that proves the
pipeline is wired correctly, every hour:

  1. config        — config.toml ga_property_id / ga_measurement_id match canon.
  2. auth          — GA_SERVICE_ACCOUNT_KEY present + a usable Data API client.
  3. property_access — a tiny live report against properties/542421812 succeeds.
  4. recent_data   — the property actually returned events in the last 7 days.
  5. site_tag      — the live site ships gtag.js for G-SMTFZVC0XN (best effort).
  6. cache_isolation — data/ga-stats.json is stamped with the new property only.

It writes a calm, public-safe health snapshot to:
  - data/ga-health.json          (Zola load_data at build → baked banner)
  - static/data/ga-health.json   (client ga-health.js auto-refresh)

Contract (UI reads this):
  status ∈ {ok, pending, disconnected, error}
    ok           → healthy: subtle chip + last-checked time
    pending      → not verified yet (no key / offline) — calm info note
    disconnected → auth/network failed — warning banner + fix link
    error        → wrong property/measurement or access denied — warning banner

Hard rules:
  * NEVER writes the service-account key, any credential field, OR the
    service-account identity (client_email / GCP project) into the JSON —
    _scrub() drops secret keys and masks `*.iam.gserviceaccount.com` anywhere.
  * NEVER raises — every failure becomes a recorded check; exit code is 0 unless
    --strict is passed (then exit 2 on a non-ok status, for an opt-in CI gate).
  * --offline skips every network call (status degrades to pending, never error).

Run:
  python3 scripts/ga_vacxin.py                 # full health check (needs key for live)
  python3 scripts/ga_vacxin.py --offline        # config/cache checks only, no network
  GA_SERVICE_ACCOUNT_KEY=$(cat key.json) python3 scripts/ga_vacxin.py
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_OUT = ROOT / "data" / "ga-health.json"
STATIC_OUT = ROOT / "static" / "data" / "ga-health.json"
CONFIG = ROOT / "config.toml"
GA_STATS = ROOT / "data" / "ga-stats.json"

# Canonical identity (fallbacks if config.toml can't be parsed).
EXPECTED_PROPERTY_ID = "542421812"
EXPECTED_MEASUREMENT_ID = "G-SMTFZVC0XN"
EXPECTED_SITE = "seomoney.org"
DEFAULT_DASHBOARD_URL = (
    "https://analytics.google.com/analytics/web/#/p542421812/reports/intelligenthome"
)
DEFAULT_FIX_URL = (
    "https://analytics.google.com/analytics/web/#/p542421812/admin/streams/table"
)
# Old identity that must never resurface (cache-isolation guard).
OLD_PROPERTY_ID = "541698865"
OLD_MEASUREMENT_ID = "G-REFBXH86Z5"

# Credential keys that must NEVER be written to the public health JSON.
SECRET_FIELDS = (
    "private_key", "private_key_id", "client_email", "client_id",
    "client_secret", "refresh_token", "access_token", "token",
    "GA_SERVICE_ACCOUNT_KEY",
)

# Service-account identity (e.g. ...@<project>.iam.gserviceaccount.com) reveals
# the GCP project — must never leak through a detail string either.
SA_EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.iam\.gserviceaccount\.com", re.IGNORECASE)

OK, WARN, FAIL, SKIP = "ok", "warn", "fail", "skip"


# --------------------------------------------------------------------------
# config.toml — single source of truth for the GA identity + deep links
# --------------------------------------------------------------------------
def load_config() -> dict:
    cfg = {
        "property_id": EXPECTED_PROPERTY_ID,
        "measurement_id": EXPECTED_MEASUREMENT_ID,
        "site": EXPECTED_SITE,
        "dashboard_url": DEFAULT_DASHBOARD_URL,
        "fix_url": DEFAULT_FIX_URL,
        "base_url": f"https://{EXPECTED_SITE}",
    }
    text = ""
    try:
        text = CONFIG.read_text(encoding="utf-8")
    except OSError:
        return cfg
    try:
        import tomllib  # Python 3.11+
        parsed = tomllib.loads(text)
        extra = parsed.get("extra", {}) if isinstance(parsed, dict) else {}
        cfg["base_url"] = (parsed.get("base_url") or cfg["base_url"]).rstrip("/")
        cfg["property_id"] = str(extra.get("ga_property_id") or cfg["property_id"])
        cfg["measurement_id"] = str(extra.get("ga_measurement_id") or cfg["measurement_id"])
        cfg["dashboard_url"] = str(extra.get("ga_dashboard_url") or cfg["dashboard_url"])
        cfg["fix_url"] = str(extra.get("ga_fix_url") or cfg["fix_url"])
    except Exception:
        # Regex fallback so a TOML quirk never blinds the monitor.
        for key, field in (
            ("ga_property_id", "property_id"),
            ("ga_measurement_id", "measurement_id"),
            ("ga_dashboard_url", "dashboard_url"),
            ("ga_fix_url", "fix_url"),
        ):
            m = re.search(rf'^{key}\s*=\s*"([^"]+)"', text, re.MULTILINE)
            if m:
                cfg[field] = m.group(1)
        mb = re.search(r'^base_url\s*=\s*"([^"]+)"', text, re.MULTILINE)
        if mb:
            cfg["base_url"] = mb.group(1).rstrip("/")
    host = re.sub(r"^https?://", "", cfg["base_url"]).split("/")[0]
    if host:
        cfg["site"] = host
    return cfg


def _check(cid: str, label: str, status: str, detail: str) -> dict:
    return {"id": cid, "label": label, "status": status, "detail": detail}


# --------------------------------------------------------------------------
# Individual health checks — each returns a check dict, never raises
# --------------------------------------------------------------------------
def check_config(cfg: dict) -> dict:
    label = "Cấu hình GA (property + measurement)"
    problems = []
    if cfg["property_id"] != EXPECTED_PROPERTY_ID:
        problems.append(
            f"ga_property_id = {cfg['property_id']} (phải là {EXPECTED_PROPERTY_ID})"
        )
    if cfg["measurement_id"] != EXPECTED_MEASUREMENT_ID:
        problems.append(
            f"ga_measurement_id = {cfg['measurement_id']} (phải là {EXPECTED_MEASUREMENT_ID})"
        )
    if cfg["property_id"] == OLD_PROPERTY_ID or cfg["measurement_id"] == OLD_MEASUREMENT_ID:
        problems.append("vẫn trỏ property/measurement CŨ (github.io)")
    if problems:
        return _check("config", label, FAIL, "; ".join(problems))
    return _check(
        "config", label, OK,
        f"property {cfg['property_id']} · {cfg['measurement_id']} · {cfg['site']}",
    )


def load_service_account(offline: bool) -> tuple[dict | None, dict]:
    """Return (key_info, auth_check). key_info=None when unavailable."""
    label = "Xác thực GA Data API"
    raw = os.environ.get("GA_SERVICE_ACCOUNT_KEY", "")
    if offline:
        return None, _check("auth", label, SKIP, "offline mode — bỏ qua xác thực")
    if not raw:
        return None, _check(
            "auth", label, FAIL,
            "thiếu secret GA_SERVICE_ACCOUNT_KEY → backend chưa kết nối GA",
        )
    try:
        info = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, _check("auth", label, FAIL, f"GA_SERVICE_ACCOUNT_KEY không phải JSON: {exc}")
    if not isinstance(info, dict) or "client_email" not in info:
        return None, _check("auth", label, FAIL, "service-account JSON thiếu client_email")
    # NEVER surface the service-account identity (client_email reveals the GCP
    # project) in the public health JSON — confirm validity without naming it.
    return info, _check(
        "auth", label, OK,
        "đã nạp khoá service account hợp lệ",
    )


def get_ga_client(info: dict):
    """Build a GA Data API client. Returns (client, error_str)."""
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.oauth2 import service_account
    except ImportError as exc:
        return None, f"thiếu SDK google-analytics-data ({exc})"
    try:
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/analytics.readonly"]
        )
        return BetaAnalyticsDataClient(credentials=creds), ""
    except Exception as exc:  # malformed key / clock skew / etc.
        return None, f"không tạo được client: {exc}"


def check_property_and_data(client, property_id: str) -> tuple[dict, dict]:
    """Live: tiny report against the property → (access_check, data_check)."""
    access_label = f"Truy cập property {property_id}"
    data_label = "Dữ liệu gần đây (7 ngày)"
    try:
        from google.analytics.data_v1beta.types import (
            DateRange, Metric, RunReportRequest,
        )
        req = RunReportRequest(
            property=f"properties/{property_id}",
            date_ranges=[DateRange(start_date="7daysAgo", end_date="today")],
            metrics=[Metric(name="activeUsers"), Metric(name="eventCount")],
        )
        res = client.run_report(req)
    except Exception as exc:
        msg = str(exc)
        low = msg.lower()
        if "has not been used" in low or "service_disabled" in low or "disabled" in low or "enable" in low:
            access = _check(
                "property_access", access_label, FAIL,
                "Google Analytics Data API chưa bật cho project của service account "
                "— bật API tại console.cloud.google.com → APIs & Services",
            )
        elif "permission" in low or "403" in low or "denied" in low:
            access = _check(
                "property_access", access_label, FAIL,
                f"service account chưa có quyền Viewer trên property {property_id}",
            )
        elif "not found" in low or "404" in low:
            access = _check(
                "property_access", access_label, FAIL,
                f"property {property_id} không tồn tại / sai id",
            )
        else:
            access = _check("property_access", access_label, FAIL, f"lỗi gọi API: {msg[:160]}")
        return access, _check("recent_data", data_label, SKIP, "không lấy được report")

    access = _check("property_access", access_label, OK, "report API trả về thành công")
    users = events = 0
    if res.rows:
        try:
            users = int(res.rows[0].metric_values[0].value)
            events = int(res.rows[0].metric_values[1].value)
        except (ValueError, IndexError):
            pass
    if events > 0 or users > 0:
        data = _check(
            "recent_data", data_label, OK,
            f"{users} users · {events} events trong 7 ngày",
        )
    else:
        data = _check(
            "recent_data", data_label, WARN,
            "0 sự kiện trong 7 ngày — kiểm tra gắn thẻ trên seomoney.org",
        )
    return access, data


def check_site_tag(cfg: dict, offline: bool) -> dict:
    """Best-effort: live site ships gtag.js for the expected measurement id."""
    label = "Thẻ đo trên site (gtag.js)"
    mid = cfg["measurement_id"]
    if offline:
        return _check("site_tag", label, SKIP, "offline mode — bỏ qua kiểm tra site")
    url = cfg["base_url"] or f"https://{EXPECTED_SITE}"
    try:
        req = urllib.request.Request(
            url + "/", headers={"User-Agent": "GA-Vacxin/1.0 (+seomoney.org)"}
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read(200_000).decode("utf-8", errors="ignore")
    except Exception as exc:
        return _check("site_tag", label, SKIP, f"không tải được trang chủ ({str(exc)[:80]})")
    if OLD_MEASUREMENT_ID in html and mid not in html:
        return _check(
            "site_tag", label, FAIL,
            f"site vẫn nhúng measurement CŨ {OLD_MEASUREMENT_ID}, thiếu {mid}",
        )
    if mid in html:
        return _check("site_tag", label, OK, f"trang chủ nhúng gtag {mid}")
    return _check(
        "site_tag", label, WARN,
        f"chưa thấy {mid} trên trang chủ (có thể chưa deploy / chặn bot)",
    )


def check_cache_isolation(cfg: dict) -> dict:
    """data/ga-stats.json must be stamped with the new property only, no creds."""
    label = "Cô lập cache theo property/domain"
    try:
        raw = GA_STATS.read_text(encoding="utf-8")
        stats = json.loads(raw)
    except OSError:
        return _check("cache_isolation", label, SKIP, "data/ga-stats.json chưa tồn tại")
    except json.JSONDecodeError as exc:
        return _check("cache_isolation", label, FAIL, f"ga-stats.json hỏng JSON: {exc}")
    problems = []
    pid = str(stats.get("property_id", ""))
    if pid and pid != cfg["property_id"]:
        problems.append(f"property_id={pid} (kỳ vọng {cfg['property_id']})")
    if OLD_PROPERTY_ID in raw:
        problems.append(f"còn dấu vết property cũ {OLD_PROPERTY_ID}")
    leaked = [f for f in SECRET_FIELDS if f in stats]
    if leaked:
        problems.append(f"rò rỉ trường bí mật: {leaked}")
    if problems:
        return _check("cache_isolation", label, FAIL, "; ".join(problems))
    return _check(
        "cache_isolation", label, OK,
        f"stats đóng dấu property {pid or cfg['property_id']} · không rò rỉ secret",
    )


# --------------------------------------------------------------------------
# Status roll-up + report writer
# --------------------------------------------------------------------------
def derive_status(checks: list[dict], offline: bool, had_key: bool) -> tuple[str, str]:
    by_id = {c["id"]: c for c in checks}

    if by_id.get("config", {}).get("status") == FAIL:
        return "error", "Cấu hình GA sai property/measurement — sửa config.toml."
    if by_id.get("cache_isolation", {}).get("status") == FAIL:
        return "error", "Cache GA chưa cô lập đúng property — số liệu cũ có thể rò rỉ."
    if offline or not had_key:
        return "pending", "Chưa xác minh kết nối GA (offline / thiếu service account)."
    if by_id.get("auth", {}).get("status") == FAIL:
        return "disconnected", "Backend chưa kết nối GA — kiểm tra GA_SERVICE_ACCOUNT_KEY."
    if by_id.get("property_access", {}).get("status") == FAIL:
        return "error", by_id["property_access"]["detail"]
    if by_id.get("site_tag", {}).get("status") == FAIL:
        return "error", by_id["site_tag"]["detail"]
    if by_id.get("recent_data", {}).get("status") == WARN:
        return "ok", "Kết nối GA ổn — chưa thấy sự kiện gần đây, đang theo dõi."
    return "ok", "GA hoạt động bình thường — số liệu cập nhật theo giờ."


def build_report(offline: bool) -> dict:
    cfg = load_config()
    checks: list[dict] = [check_config(cfg)]

    info, auth_check = load_service_account(offline)
    checks.append(auth_check)
    had_key = info is not None

    if info is not None:
        client, err = get_ga_client(info)
        if client is None:
            checks.append(_check("auth", "Xác thực GA Data API", FAIL, err))
            checks.append(_check("property_access", f"Truy cập property {cfg['property_id']}",
                                 SKIP, "không có client"))
            checks.append(_check("recent_data", "Dữ liệu gần đây (7 ngày)", SKIP, "không có client"))
            had_key = False
        else:
            access, data = check_property_and_data(client, cfg["property_id"])
            checks.append(access)
            checks.append(data)
    else:
        checks.append(_check("property_access", f"Truy cập property {cfg['property_id']}",
                             SKIP, "chưa xác thực"))
        checks.append(_check("recent_data", "Dữ liệu gần đây (7 ngày)", SKIP, "chưa xác thực"))

    checks.append(check_site_tag(cfg, offline))
    checks.append(check_cache_isolation(cfg))

    status, message = derive_status(checks, offline, had_key)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {
        "status": status,
        "message": message,
        "last_checked": now,
        "property_id": cfg["property_id"],
        "measurement_id": cfg["measurement_id"],
        "site": cfg["site"],
        "dashboard_url": cfg["dashboard_url"],
        "fix_url": cfg["fix_url"],
        "expected_property_id": EXPECTED_PROPERTY_ID,
        "expected_measurement_id": EXPECTED_MEASUREMENT_ID,
        "checks": checks,
        "summary": {
            "ok": sum(1 for c in checks if c["status"] == OK),
            "warn": sum(1 for c in checks if c["status"] == WARN),
            "fail": sum(1 for c in checks if c["status"] == FAIL),
            "skip": sum(1 for c in checks if c["status"] == SKIP),
        },
        "generator": "ga_vacxin",
    }


def _scrub(obj):
    """Defence in depth: drop secret-named keys AND mask any service-account
    identity that slipped into a string (e.g. a check detail), recursively,
    before the report is persisted or printed."""
    if isinstance(obj, dict):
        return {k: _scrub(v) for k, v in obj.items() if k not in SECRET_FIELDS}
    if isinstance(obj, list):
        return [_scrub(v) for v in obj]
    if isinstance(obj, str):
        return SA_EMAIL_RE.sub("[service-account]", obj)
    return obj


def write_report(report: dict) -> None:
    text = json.dumps(_scrub(report), ensure_ascii=False, indent=2) + "\n"
    for out in (DATA_OUT, STATIC_OUT):
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="GA Vacxin — hourly GA4 health monitor")
    ap.add_argument("--offline", action="store_true",
                    help="skip all network calls (config + cache checks only)")
    ap.add_argument("--strict", action="store_true",
                    help="exit 2 when status is not ok (opt-in CI gate)")
    ap.add_argument("--print", dest="show", action="store_true",
                    help="print the report JSON to stdout")
    args = ap.parse_args(argv)

    try:
        report = build_report(args.offline)
    except Exception as exc:  # the monitor must never crash a workflow
        report = {
            "status": "error",
            "message": f"GA Vacxin lỗi nội bộ: {exc}",
            "last_checked": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "property_id": EXPECTED_PROPERTY_ID,
            "measurement_id": EXPECTED_MEASUREMENT_ID,
            "site": EXPECTED_SITE,
            "dashboard_url": DEFAULT_DASHBOARD_URL,
            "fix_url": DEFAULT_FIX_URL,
            "checks": [],
            "summary": {"ok": 0, "warn": 0, "fail": 1, "skip": 0},
            "generator": "ga_vacxin",
        }

    try:
        write_report(report)
    except OSError as exc:
        print(f"GA Vacxin: write failed: {exc}", file=sys.stderr)

    print(
        f"GA Vacxin → status={report['status']} · "
        f"property={report['property_id']} · {report['message']}"
    )
    if args.show:
        print(json.dumps(_scrub(report), ensure_ascii=False, indent=2))

    if args.strict and report["status"] != "ok":
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
