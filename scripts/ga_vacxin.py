#!/usr/bin/env python3
"""
GA Vacxin — hourly health bot for the Google Analytics module (seomoney.org).

Runs four connectivity/health checks and writes a small, public-safe report the
footer GA module renders. It is a *report-only* job (V7 philosophy): it NEVER
fabricates metrics, NEVER prints secrets, and NEVER exits non-zero on a degraded
state — a bad health result is data, not a CI failure. It is fully OFFLINE-SAFE:
with no Service Account key, no SDK, or no network it degrades to a clear
"pending/unknown" report and still exits 0.

Checks (per task brief):
  1. auth            — GA Data API auth: GA_SERVICE_ACCOUNT_KEY present + valid +
                       credentials build.
  2. property_access — read access to GA4 property 542421812 (a tiny runReport).
  3. recent_data     — recent rows exist (last 3 days) OR committed ga-stats.json
                       is fresh; distinguishes "new property, no data yet" from
                       a real outage.
  4. measurement     — site tag / Measurement ID connectivity: G-SMTFZVC0XN format
                       + config consistency + (best-effort) gtag present on the
                       live homepage.

Output: data/ga-vacxin-report.json + static/data/ga-vacxin-report.json
Overall status: healthy | degraded | error | pending

Env:
  GA_SERVICE_ACCOUNT_KEY  Service Account JSON (Viewer on the property)
  GA_PROPERTY_ID          override (default 542421812)
  GA_MEASUREMENT_ID       override (default G-SMTFZVC0XN)
  GA_SITE_DOMAIN          override (default seomoney.org)
  GA_VACXIN_NO_NETWORK    set to skip the homepage gtag probe

Local:
  python3 scripts/ga_vacxin.py            # writes report (offline → pending)
  python3 scripts/ga_vacxin.py --print    # also pretty-print the report
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_OUT = ROOT / "data" / "ga-vacxin-report.json"
STATIC_OUT = ROOT / "static" / "data" / "ga-vacxin-report.json"
GA_STATS = ROOT / "data" / "ga-stats.json"
CONFIG = ROOT / "config.toml"

VN_TZ = timezone(timedelta(hours=7))

# Canonical identity (env-overridable, but these are the seomoney.org defaults).
PROPERTY_ID = os.environ.get("GA_PROPERTY_ID", "542421812").strip() or "542421812"
MEASUREMENT_ID = os.environ.get("GA_MEASUREMENT_ID", "G-SMTFZVC0XN").strip() or "G-SMTFZVC0XN"
SITE_DOMAIN = os.environ.get("GA_SITE_DOMAIN", "seomoney.org").strip() or "seomoney.org"

# Status vocabulary.
OK, FAIL, SKIP = "ok", "fail", "skip"
HEALTHY, DEGRADED, ERROR, PENDING = "healthy", "degraded", "error", "pending"

# How fresh committed stats must be before we call them stale (recent_data).
STATS_STALE_HOURS = 6


def _dashboard_url() -> str:
    return f"https://analytics.google.com/analytics/web/#/p{PROPERTY_ID}/reports/intelligenthome"


def _fix_url() -> str:
    # Admin → data streams: where an operator verifies access / the web stream tag.
    return f"https://analytics.google.com/analytics/web/#/p{PROPERTY_ID}/admin/streams/table"


def _measurement_id_valid(mid: str) -> bool:
    if not mid or not mid.startswith("G-"):
        return False
    tail = mid[2:]
    return tail.isalnum() and 6 <= len(tail) <= 16


def _load_config() -> dict:
    """Read property/measurement/base_url from config.toml (tomllib, best-effort)."""
    out: dict = {}
    try:
        import tomllib  # py3.11+
        with CONFIG.open("rb") as fh:
            cfg = tomllib.load(fh)
        out["base_url"] = cfg.get("base_url", "")
        extra = cfg.get("extra", {}) or {}
        out["ga_measurement_id"] = extra.get("ga_measurement_id", "")
        out["ga_property_id"] = extra.get("ga_property_id", "")
    except Exception:
        # Degrade gracefully — config parse must never crash the bot.
        pass
    return out


def _check(check_id: str, label: str, status: str, detail: str) -> dict:
    return {"id": check_id, "label": label, "status": status, "detail": detail}


# --------------------------------------------------------------------------
# Individual checks
# --------------------------------------------------------------------------
def check_auth() -> tuple[dict, object | None]:
    """GA Data API auth. Returns (check_dict, client_or_None).

    Order matters: the SDK gates whether we can verify ONLINE at all. If the SDK
    is absent (local dev) we SKIP regardless of the key — a missing key is only a
    real config error in the CI runner where the SDK is installed. This keeps the
    committed/local report a neutral "pending", never a false "error".
    """
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.oauth2 import service_account
    except ImportError:
        return (
            _check("auth", "GA API auth", SKIP,
                   "SDK google-analytics-data chưa cài (offline) — không kiểm tra auth online được."),
            None,
        )
    key_str = os.environ.get("GA_SERVICE_ACCOUNT_KEY", "").strip()
    if not key_str:
        return (
            _check("auth", "GA API auth", FAIL,
                   "Thiếu GA_SERVICE_ACCOUNT_KEY — thêm GitHub Secret (Service Account JSON)."),
            None,
        )
    try:
        info = json.loads(key_str)
    except json.JSONDecodeError:
        return (
            _check("auth", "GA API auth", FAIL,
                   "GA_SERVICE_ACCOUNT_KEY không phải JSON hợp lệ."),
            None,
        )
    try:
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/analytics.readonly"]
        )
        client = BetaAnalyticsDataClient(credentials=creds)
        return (
            _check("auth", "GA API auth", OK,
                   f"Credentials OK · {_mask_email(info.get('client_email', ''))}"),
            client,
        )
    except Exception as exc:  # malformed key / lib error
        return (
            _check("auth", "GA API auth", FAIL,
                   f"Không tạo được credentials: {_short(exc)}"),
            None,
        )


def check_property_access(client) -> tuple[dict, int]:
    """Tiny runReport against the property. Returns (check_dict, recent_active_users)."""
    if client is None:
        return (
            _check("property_access", f"Truy cập property {PROPERTY_ID}", SKIP,
                   "Bỏ qua — chưa có client (auth chưa sẵn sàng)."),
            -1,
        )
    try:
        from google.analytics.data_v1beta.types import (
            DateRange, Metric, RunReportRequest,
        )
        req = RunReportRequest(
            property=f"properties/{PROPERTY_ID}",
            date_ranges=[DateRange(start_date="3daysAgo", end_date="today")],
            metrics=[Metric(name="activeUsers")],
        )
        res = client.run_report(req)
        users = 0
        if res.rows:
            try:
                users = int(res.rows[0].metric_values[0].value)
            except (ValueError, IndexError):
                users = 0
        return (
            _check("property_access", f"Truy cập property {PROPERTY_ID}", OK,
                   f"Đọc property thành công · {users} active users (3 ngày)."),
            users,
        )
    except Exception as exc:
        msg = _short(exc)
        low = msg.lower()
        if "permission" in low or "403" in low or "denied" in low:
            detail = (f"Service Account CHƯA có quyền Viewer trên property {PROPERTY_ID}. "
                      "Thêm SA email vào GA Admin → Property Access Management.")
        elif "404" in low or "not found" in low:
            detail = f"Property {PROPERTY_ID} không tồn tại / sai ID."
        else:
            detail = f"Lỗi gọi GA Data API: {msg}"
        return (_check("property_access", f"Truy cập property {PROPERTY_ID}", FAIL, detail), -1)


def check_recent_data(recent_users: int) -> dict:
    """Recent rows from the live query, else committed stats freshness."""
    # Authoritative: the live 3-day query (when available).
    if recent_users >= 0:
        if recent_users > 0:
            return _check("recent_data", "Dữ liệu gần đây", OK,
                          f"Có {recent_users} active users trong 3 ngày qua.")
        return _check("recent_data", "Dữ liệu gần đây", SKIP,
                      "Property đọc được nhưng chưa có dữ liệu (property mới / đang chờ traffic).")

    # Fallback: committed ga-stats.json freshness + property stamp.
    try:
        stats = json.loads(GA_STATS.read_text(encoding="utf-8"))
    except Exception:
        return _check("recent_data", "Dữ liệu gần đây", SKIP,
                      "Chưa đọc được data/ga-stats.json để đánh giá.")
    stamp = str(stats.get("property_id") or "")
    if stamp and stamp != PROPERTY_ID:
        return _check("recent_data", "Dữ liệu gần đây", FAIL,
                      f"data/ga-stats.json gắn property {stamp} ≠ {PROPERTY_ID} (cache cũ).")
    if stats.get("_status") == "waiting_for_refresh":
        return _check("recent_data", "Dữ liệu gần đây", SKIP,
                      "Đang chờ lần fetch đầu tiên từ property mới.")
    dt = _parse_iso(stats.get("updated_at"))
    if dt is None:
        return _check("recent_data", "Dữ liệu gần đây", SKIP,
                      "Không đọc được mốc updated_at trong ga-stats.json.")
    age_h = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
    if age_h > STATS_STALE_HOURS:
        return _check("recent_data", "Dữ liệu gần đây", FAIL,
                      f"ga-stats.json đã cũ {age_h:.0f}h (>{STATS_STALE_HOURS}h) — fetch hourly có thể đang lỗi.")
    return _check("recent_data", "Dữ liệu gần đây", OK,
                  f"ga-stats.json còn mới ({age_h:.0f}h) cho property {PROPERTY_ID}.")


def check_measurement(cfg: dict) -> dict:
    """Site tag / Measurement ID: format + config consistency + (best-effort) gtag probe."""
    cfg_mid = str(cfg.get("ga_measurement_id") or "")
    cfg_prop = str(cfg.get("ga_property_id") or "")
    problems: list[str] = []

    if not _measurement_id_valid(MEASUREMENT_ID):
        problems.append(f"Measurement ID '{MEASUREMENT_ID}' sai định dạng G-XXXXXXXXXX.")
    if cfg_mid and cfg_mid != MEASUREMENT_ID:
        problems.append(f"config.toml ga_measurement_id={cfg_mid} ≠ {MEASUREMENT_ID}.")
    if cfg_prop and cfg_prop != PROPERTY_ID:
        problems.append(f"config.toml ga_property_id={cfg_prop} ≠ {PROPERTY_ID}.")
    if problems:
        return _check("measurement", "Kết nối tag / Measurement ID", FAIL, " ".join(problems))

    # Best-effort live probe: is the gtag for this Measurement ID on the homepage?
    if os.environ.get("GA_VACXIN_NO_NETWORK"):
        return _check("measurement", "Kết nối tag / Measurement ID", OK,
                      f"{MEASUREMENT_ID} khớp config (probe homepage bỏ qua: GA_VACXIN_NO_NETWORK).")
    base = (cfg.get("base_url") or f"https://{SITE_DOMAIN}").rstrip("/")
    try:
        req = urllib.request.Request(base + "/", headers={"User-Agent": "ga-vacxin/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read(200_000).decode("utf-8", "ignore")
        if MEASUREMENT_ID in html:
            return _check("measurement", "Kết nối tag / Measurement ID", OK,
                          f"gtag {MEASUREMENT_ID} hiện diện trên {base}/.")
        return _check("measurement", "Kết nối tag / Measurement ID", FAIL,
                      f"KHÔNG thấy {MEASUREMENT_ID} trong HTML {base}/ — site tag chưa active?")
    except Exception as exc:
        # Network failure must NOT downgrade to fail — config already matched.
        return _check("measurement", "Kết nối tag / Measurement ID", SKIP,
                      f"{MEASUREMENT_ID} khớp config; probe homepage lỗi mạng ({_short(exc)}).")


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _mask_email(email: str) -> str:
    if not email or "@" not in email:
        return "(service account)"
    name, _, domain = email.partition("@")
    head = name[:3]
    return f"{head}…@{domain}"


def _short(exc: object, n: int = 160) -> str:
    s = str(exc).replace("\n", " ").strip()
    return s[:n]


def _parse_iso(raw) -> datetime | None:
    if not raw:
        return None
    s = str(raw).strip()
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _overall(checks: list[dict]) -> tuple[str, bool, str]:
    """Roll up per-check statuses into (status, ok, summary)."""
    by_id = {c["id"]: c for c in checks}
    # Hard errors first: no auth / no property access / property mismatch.
    for cid in ("auth", "property_access", "recent_data", "measurement"):
        c = by_id.get(cid)
        if c and c["status"] == FAIL:
            return ERROR, False, c["detail"]
    # No FAIL — decide healthy vs pending vs degraded from skips.
    skipped = [c for c in checks if c["status"] == SKIP]
    # If we never actually reached GA (auth skipped because SDK/key absent online).
    auth = by_id.get("auth", {})
    prop = by_id.get("property_access", {})
    if auth.get("status") == SKIP and prop.get("status") == SKIP:
        return PENDING, True, "Chưa kiểm tra online được (thiếu SDK/secret) — sẽ kiểm tra ở lần chạy CI."
    if skipped:
        # Reached GA but something benign was skipped (e.g. new property no data).
        return DEGRADED, True, "; ".join(c["detail"] for c in skipped)[:200]
    return HEALTHY, True, "Tất cả kiểm tra GA đạt — auth, property, dữ liệu, tag đều OK."


# --------------------------------------------------------------------------
# Build + write
# --------------------------------------------------------------------------
def build_report() -> dict:
    cfg = _load_config()
    auth_check, client = check_auth()
    prop_check, recent_users = check_property_access(client)
    recent_check = check_recent_data(recent_users)
    meas_check = check_measurement(cfg)
    checks = [auth_check, prop_check, recent_check, meas_check]
    status, ok, summary = _overall(checks)

    now = datetime.now(timezone.utc)
    return {
        "updated_at": now.isoformat(timespec="seconds"),
        "checked_at": now.isoformat(timespec="seconds"),
        "property_id": PROPERTY_ID,
        "measurement_id": MEASUREMENT_ID,
        "site_domain": SITE_DOMAIN,
        "status": status,
        "ok": ok,
        "summary": summary,
        "checks": checks,
        "dashboard_url": _dashboard_url(),
        "fix_url": _fix_url(),
        "interval": "hourly",
        "bot": "GA Vacxin",
    }


def write_report(report: dict) -> None:
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    DATA_OUT.parent.mkdir(parents=True, exist_ok=True)
    STATIC_OUT.parent.mkdir(parents=True, exist_ok=True)
    DATA_OUT.write_text(text, encoding="utf-8")
    STATIC_OUT.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="GA Vacxin — hourly GA health bot")
    ap.add_argument("--print", action="store_true", dest="do_print",
                    help="pretty-print the report to stdout")
    args = ap.parse_args(argv)

    try:
        report = build_report()
    except Exception as exc:  # absolute last-resort guard — never crash the job
        report = {
            "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "property_id": PROPERTY_ID,
            "measurement_id": MEASUREMENT_ID,
            "site_domain": SITE_DOMAIN,
            "status": PENDING,
            "ok": True,
            "summary": f"GA Vacxin gặp lỗi nội bộ (non-fatal): {_short(exc)}",
            "checks": [],
            "dashboard_url": _dashboard_url(),
            "fix_url": _fix_url(),
            "interval": "hourly",
            "bot": "GA Vacxin",
        }
    write_report(report)
    line = (f"GA Vacxin: status={report['status']} property={report['property_id']} "
            f"measurement={report['measurement_id']}")
    print(line)
    if args.do_print:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    # Report-only job: always exit 0 (a degraded health state is data, not a CI failure).
    return 0


if __name__ == "__main__":
    sys.exit(main())
