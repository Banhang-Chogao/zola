#!/usr/bin/env python3
"""
fetch_uptime_me.py — UPTIME_ME data fetcher.

Reads up to 3 UptimeRobot read-only API keys from the environment, calls the
read-only getMonitors endpoint for each account, normalizes everything into ONE
sanitized public report, and writes it to data/uptime-me.json.

SECURITY (hard rules):
  * API keys are read ONLY from env: UPTIMEROBOT_API_KEY_1/_2/_3.
  * Keys are NEVER printed, logged, or written to the output JSON. Before writing,
    the serialized report is scanned and the write is ABORTED if any key leaks.
  * The site is static → this runs in CI/cron, not the browser.

RESILIENCE:
  * Missing key / rate-limit / API error → that account is marked ok=false with a
    safe reason; the rest of the report is still produced (graceful degradation).
  * Any unexpected error never crashes the caller: a valid fallback JSON is kept.
  * "Meaningful change only": if the new report is identical to the existing one
    apart from the timestamp, the file is left untouched (no churn commit).

Stdlib only.

Output schema (data/uptime-me.json):
{
  "checked_at": "<ISO8601 UTC>",
  "ok": true,
  "summary": {"total","up","down","paused","overall_uptime_30d","avg_response_ms","breathing"},
  "accounts": [{"key_index","ok","monitor_count","error"}],
  "monitors": [{"name","host","status","uptime_24h","uptime_7d","uptime_30d",
                "avg_response_ms","response_times":[{"t","ms"}],
                "last_down","incidents":[{"start","reason","duration_s"}]}],
  "incidents": [{"monitor","start","reason","duration_s"}],
  "stale": false
}
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "uptime-me.json"
API_URL = "https://api.uptimerobot.com/v2/getMonitors"
ENV_KEYS = ("UPTIMEROBOT_API_KEY_1", "UPTIMEROBOT_API_KEY_2", "UPTIMEROBOT_API_KEY_3")
TIMEOUT = 15

# UptimeRobot status codes → our vocabulary.
_STATUS = {0: "paused", 1: "unknown", 2: "up", 8: "down", 9: "down"}

# This dashboard tracks ONE site: the canonical seomoney.org root (V23 — brand +
# canonical root must stay seomoney.org). The 3 UptimeRobot accounts each monitor
# extra infra (e.g. blog-visitor-api.onrender.com) that is irrelevant here and
# also report the same seomoney.org monitor more than once. We keep only allowed
# hosts and collapse duplicates so the page renders exactly one seomoney.org card.
ALLOWED_HOSTS = ("seomoney.org",)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _host(url: str) -> str:
    try:
        h = urlparse(url).netloc or url
        return h.replace("www.", "")
    except Exception:
        return url or "—"


def _norm_host(value: str) -> str:
    """Normalize a host/URL for comparison: lowercase, no scheme/path/www/slash."""
    h = (value or "").strip().lower()
    if "//" in h:
        h = h.split("//", 1)[1]
    h = h.split("/", 1)[0]  # drop any path or trailing slash
    if h.startswith("www."):
        h = h[4:]
    return h


def fetch_account(api_key: str) -> tuple[list[dict], str | None]:
    """Call getMonitors for one key. Returns (monitors, error). Never raises."""
    payload = urlencode({
        "api_key": api_key,
        "format": "json",
        "logs": "1",
        "logs_limit": "5",
        "response_times": "1",
        "response_times_limit": "12",
        "custom_uptime_ratios": "1-7-30",
    }).encode()
    req = Request(API_URL, data=payload, headers={
        "content-type": "application/x-www-form-urlencoded",
        "cache-control": "no-cache",
    })
    try:
        with urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
    except HTTPError as e:
        return [], f"http {e.code}"
    except (URLError, TimeoutError) as e:
        return [], "network"
    except Exception:
        return [], "error"
    if not isinstance(data, dict) or data.get("stat") != "ok":
        # UptimeRobot returns stat=fail with an error block (e.g. rate limit).
        err = "rate_limit" if "rate" in json.dumps(data).lower() else "api_fail"
        return [], err
    return data.get("monitors") or [], None


def normalize_monitor(m: dict) -> dict:
    ratios = str(m.get("custom_uptime_ratio") or "").split("-")

    def _r(i):
        try:
            return round(float(ratios[i]), 3)
        except (IndexError, ValueError):
            return None

    rts = []
    for rt in (m.get("response_times") or []):
        try:
            rts.append({"t": datetime.fromtimestamp(int(rt["datetime"]), timezone.utc).isoformat(),
                        "ms": int(rt["value"])})
        except (KeyError, ValueError, TypeError, OSError):
            continue
    incidents, last_down = [], None
    for log in (m.get("logs") or []):
        if int(log.get("type", 0)) == 1:  # 1 = down event
            try:
                start = datetime.fromtimestamp(int(log["datetime"]), timezone.utc).isoformat()
            except (KeyError, ValueError, TypeError, OSError):
                continue
            incidents.append({"start": start,
                              "reason": str(log.get("reason", {}).get("detail", "") if isinstance(log.get("reason"), dict) else log.get("reason", ""))[:120],
                              "duration_s": int(log.get("duration", 0) or 0)})
            last_down = last_down or start
    avg = rts and round(sum(r["ms"] for r in rts) / len(rts)) or (int(m.get("average_response_time") or 0) or None)
    return {
        "name": str(m.get("friendly_name", "monitor"))[:80],
        "host": _host(str(m.get("url", ""))),
        "status": _STATUS.get(int(m.get("status", 1)), "unknown"),
        "uptime_24h": _r(0),
        "uptime_7d": _r(1),
        "uptime_30d": _r(2),
        "avg_response_ms": avg,
        "response_times": rts,
        "last_down": last_down,
        "incidents": incidents,
    }


def breathing(up: int, total: int, uptime30: float | None) -> str:
    """Playful 'Website đang thở ổn không?' verdict."""
    if total == 0:
        return "chưa rõ"
    if up == total and (uptime30 is None or uptime30 >= 99.5):
        return "thở đều, khỏe re 😎"
    if up == total:
        return "vẫn thở ổn 🙂"
    if up >= total / 2:
        return "hơi hụt hơi 😮‍💨"
    return "đang ốm, cần xem ngay 🤒"


def select_monitors(monitors: list[dict]) -> list[dict]:
    """Keep only ALLOWED_HOSTS monitors, deduped by normalized host.

    The 3 accounts each return the seomoney.org monitor (so it shows up several
    times) plus unrelated infra such as blog-visitor-api.onrender.com. We render
    a single, deduplicated card per allowed host — never the extra infra.
    """
    allowed = {_norm_host(h) for h in ALLOWED_HOSTS}
    seen: set[str] = set()
    kept: list[dict] = []
    for m in monitors or []:
        host = _norm_host(str(m.get("host", "")))
        if host not in allowed or host in seen:
            continue
        seen.add(host)
        kept.append(m)
    return kept


def summarize(monitors: list[dict]) -> tuple[dict, list[dict]]:
    """Derive the summary block + flattened incident timeline from monitors."""
    up = sum(1 for m in monitors if m.get("status") == "up")
    down = sum(1 for m in monitors if m.get("status") == "down")
    paused = sum(1 for m in monitors if m.get("status") == "paused")
    u30 = [m["uptime_30d"] for m in monitors if m.get("uptime_30d") is not None]
    overall = round(sum(u30) / len(u30), 3) if u30 else None
    resp = [m["avg_response_ms"] for m in monitors if m.get("avg_response_ms")]
    avg_resp = round(sum(resp) / len(resp)) if resp else None
    incidents = sorted(
        ({"monitor": m["name"], **inc} for m in monitors for inc in (m.get("incidents") or [])),
        key=lambda x: x["start"], reverse=True)[:15]
    summary = {
        "total": len(monitors), "up": up, "down": down, "paused": paused,
        "overall_uptime_30d": overall, "avg_response_ms": avg_resp,
        "breathing": breathing(up, len(monitors), overall),
    }
    return summary, incidents


def build_report() -> dict:
    accounts, monitors = [], []
    for i, env in enumerate(ENV_KEYS, start=1):
        key = (os.environ.get(env) or "").strip()
        if not key:
            accounts.append({"key_index": i, "ok": False, "monitor_count": 0, "error": "missing"})
            continue
        mons, err = fetch_account(key)
        if err:
            accounts.append({"key_index": i, "ok": False, "monitor_count": 0, "error": err})
            continue
        norm = [normalize_monitor(m) for m in mons]
        monitors.extend(norm)
        accounts.append({"key_index": i, "ok": True, "monitor_count": len(norm), "error": None})

    # Render only the seomoney.org monitor (deduped); drop unrelated infra.
    monitors = select_monitors(monitors)
    summary, incidents = summarize(monitors)
    any_ok = any(a["ok"] for a in accounts)
    return {
        "checked_at": _now(),
        "ok": any_ok,
        "summary": summary,
        "accounts": accounts,
        "monitors": monitors,
        "incidents": incidents,
        "stale": False,
    }


def _strip_volatile(rep: dict) -> str:
    """Serialize a report for change-detection, ignoring the timestamp."""
    clone = json.loads(json.dumps(rep))
    clone.pop("checked_at", None)
    return json.dumps(clone, sort_keys=True, ensure_ascii=False)


def main() -> int:
    try:
        report = build_report()
    except Exception as e:  # never crash CI; keep any existing report
        print(f"[uptime-me] unexpected error: {type(e).__name__}", file=sys.stderr)
        return 0

    # SECURITY: abort if any key leaked into the serialized report.
    serialized = json.dumps(report, ensure_ascii=False)
    for env in ENV_KEYS:
        key = (os.environ.get(env) or "").strip()
        if key and key in serialized:
            print("[uptime-me] FATAL: API key leaked into report — aborting write.",
                  file=sys.stderr)
            return 2

    # Meaningful-change only: skip rewrite if nothing but the timestamp changed.
    if OUTPUT.exists():
        try:
            old = json.loads(OUTPUT.read_text(encoding="utf-8"))
            if _strip_volatile(old) == _strip_volatile(report):
                print("[uptime-me] no meaningful change — keeping existing report.")
                return 0
        except (OSError, json.JSONDecodeError):
            pass

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    s = report["summary"]
    print(f"[uptime-me] wrote {OUTPUT.relative_to(ROOT)} — "
          f"{s['up']}/{s['total']} up, breathing: {s['breathing']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
