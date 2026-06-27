"""Real-User-Monitoring (RUM) Web Vitals for the VIPZone API.

Turns Speed Insights from a per-browser localStorage demo into a real,
cross-visitor field-data pipeline:

    web-vitals JS on public pages
      → POST /rum/web-vitals            (anonymous, sanitised, rate-limited)
      → store raw samples (bounded by retention)
      → GET  /rum/web-vitals/summary    (P75 / median / average / count per metric)
      → Speed Insights dashboard

Privacy / safety:
  * Fully anonymous — no login, no cookie, no email, no raw IP is ever stored.
    We keep only: metric name, value, rating, page path, a coarse device class,
    navigation type and a server timestamp.
  * The page path is canonicalised to a path-only string (scheme/host/query/hash
    stripped) and length-capped, so query strings can't smuggle PII in.
  * A light in-memory per-IP rate limit blocks floods; the IP itself is hashed
    and never persisted.
  * Reads are aggregate-only (P75/median/avg/count + distribution + slow pages) —
    individual samples are never exposed.

Routes:
  POST /rum/web-vitals                       (public — one event or {events:[...]})
  GET  /rum/web-vitals/summary?window=30d    (public — aggregated field data)
"""

from __future__ import annotations

import hashlib
import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

from fastapi import APIRouter, Query, Request

router = APIRouter(tags=["rum"])


# ============= Config (env-driven, no secrets) =============
def _truthy(v: str) -> bool:
    return (v or "").strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int, lo: int, hi: int) -> int:
    try:
        return max(lo, min(int(os.getenv(name, str(default))), hi))
    except ValueError:
        return default


RUM_ENABLED = _truthy(os.getenv("RUM_ENABLED", "true"))
RUM_RETENTION_DAYS = _int_env("RUM_RETENTION_DAYS", 90, 1, 730)
# Per-IP flood guard: at most N samples per rolling window (a single page load
# legitimately sends 5 metrics, so the default is generous).
RUM_RATE_WINDOW_SECONDS = _int_env("RUM_RATE_WINDOW", 60, 1, 3600)
RUM_RATE_MAX = _int_env("RUM_RATE_MAX", 120, 5, 100_000)
# Cap how many events one request may carry (the client batches all metrics for a
# page load into one beacon).
RUM_MAX_BATCH = _int_env("RUM_MAX_BATCH", 20, 1, 200)

# Metrics we accept. LCP/INP/CLS are the Core Web Vitals; FCP/TTFB are diagnostic.
CORE_METRICS = ("LCP", "INP", "CLS")
DIAGNOSTIC_METRICS = ("FCP", "TTFB")
VALID_METRICS = set(CORE_METRICS) | set(DIAGNOSTIC_METRICS)

# Google's standard "good / needs-improvement / poor" boundaries.
THRESHOLDS: dict[str, tuple[float, float]] = {
    "LCP": (2500.0, 4000.0),
    "INP": (200.0, 500.0),
    "CLS": (0.1, 0.25),
    "FCP": (1800.0, 3000.0),
    "TTFB": (800.0, 1800.0),
}

# Sane upper bounds so a bad client can't poison the aggregates with nonsense.
VALUE_CEILING: dict[str, float] = {
    "LCP": 600_000.0,   # 10 min
    "INP": 600_000.0,
    "FCP": 600_000.0,
    "TTFB": 600_000.0,
    "CLS": 100.0,       # CLS is unitless and tiny; 100 is already absurd
}

VALID_DEVICES = {"mobile", "tablet", "desktop", "unknown"}

WINDOWS = {"24h": 1, "7d": 7, "30d": 30}

_PATH_RE = re.compile(r"^/[A-Za-z0-9._~!$&'()*+,;=:@%/\-]*$")

# DB getter injected by configure() from the host app (mirrors comments.py).
_get_db: Optional[Callable[[], Any]] = None

# In-memory rate-limit buckets: ip_hash → [timestamps]. Reset on process restart;
# good enough for flood protection on a single dyno.
_rate_buckets: dict[str, list[float]] = {}


def configure(get_db: Callable[[], Any]) -> None:
    global _get_db
    _get_db = get_db


def _db() -> Any:
    if _get_db is None:  # pragma: no cover - configure() always called at mount
        raise RuntimeError("rum router not configured: call configure(get_db)")
    return _get_db()


# ============= helpers =============
def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _rate_limited(request: Request) -> bool:
    fwd = request.headers.get("x-forwarded-for", "")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "")
    key = hashlib.sha256((ip or "?").encode("utf-8")).hexdigest()
    now = time.monotonic()
    floor = now - RUM_RATE_WINDOW_SECONDS
    bucket = [t for t in _rate_buckets.get(key, []) if t >= floor]
    if len(bucket) >= RUM_RATE_MAX:
        _rate_buckets[key] = bucket
        return True
    bucket.append(now)
    _rate_buckets[key] = bucket
    # Opportunistic cleanup so the dict doesn't grow forever.
    if len(_rate_buckets) > 5000:
        for k in list(_rate_buckets.keys()):
            if not [t for t in _rate_buckets[k] if t >= floor]:
                _rate_buckets.pop(k, None)
    return False


def _normalize_path(raw: Any) -> str:
    p = str(raw or "/").strip()
    if "://" in p:
        p = p.split("://", 1)[1]
        p = "/" + p.split("/", 1)[1] if "/" in p else "/"
    p = p.split("?", 1)[0].split("#", 1)[0]
    if not p.startswith("/"):
        p = "/" + p
    # Drop a leading /zola base-path segment (site root is seomoney.org).
    if p == "/zola" or p.startswith("/zola/"):
        p = p[len("/zola"):] or "/"
    p = re.sub(r"/{2,}", "/", p)
    if len(p) > 300 or not _PATH_RE.match(p):
        return "/"
    return p


def _rate(metric: str, v: float) -> str:
    lo, hi = THRESHOLDS[metric]
    if v <= lo:
        return "good"
    if v <= hi:
        return "needs-improvement"
    return "poor"


def _clean_event(raw: Any) -> dict[str, Any] | None:
    """Validate + sanitise one incoming sample. Returns None if unusable."""
    if not isinstance(raw, dict):
        return None
    metric = str(raw.get("metric_name") or raw.get("metric") or raw.get("name") or "").upper().strip()
    if metric not in VALID_METRICS:
        return None
    try:
        value = float(raw.get("metric_value", raw.get("value")))
    except (TypeError, ValueError):
        return None
    if value < 0 or value != value:  # negative or NaN
        return None
    value = min(value, VALUE_CEILING.get(metric, 600_000.0))
    device = str(raw.get("device_type") or raw.get("device") or "unknown").lower().strip()
    if device not in VALID_DEVICES:
        device = "unknown"
    nav = str(raw.get("navigation_type") or "")[:24]
    return {
        "metric": metric,
        "value": round(value, 4),
        "rating": _rate(metric, value),
        "page_path": _normalize_path(raw.get("page_path") or raw.get("path")),
        "device": device,
        "navigation_type": nav,
    }


# ============= aggregation =============
def _percentile(sorted_vals: list[float], q: float) -> float | None:
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    idx = min(len(sorted_vals) - 1, int(round(q * (len(sorted_vals) - 1))))
    return sorted_vals[idx]


def _median(sorted_vals: list[float]) -> float | None:
    n = len(sorted_vals)
    if n == 0:
        return None
    mid = n // 2
    if n % 2:
        return sorted_vals[mid]
    return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2


def _aggregate_metric(metric: str, samples: list[dict[str, Any]]) -> dict[str, Any]:
    values = sorted(s["value"] for s in samples)
    count = len(values)
    if count == 0:
        return {
            "metric": metric,
            "count": 0,
            "p75": None,
            "median": None,
            "average": None,
            "rating": "none",
            "distribution": {"good": 0, "needs-improvement": 0, "poor": 0},
            "core": metric in CORE_METRICS,
        }
    p75 = _percentile(values, 0.75)
    dist = {"good": 0, "needs-improvement": 0, "poor": 0}
    for v in values:
        dist[_rate(metric, v)] += 1
    return {
        "metric": metric,
        "count": count,
        "p75": round(p75, 4) if p75 is not None else None,
        "median": round(_median(values), 4),
        "average": round(sum(values) / count, 4),
        "rating": _rate(metric, p75) if p75 is not None else "none",
        "distribution": dist,
        "core": metric in CORE_METRICS,
    }


def _slow_pages(samples: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    """Rank pages by LCP P75 (only pages with a meaningful sample count)."""
    by_page: dict[str, list[float]] = {}
    for s in samples:
        by_page.setdefault(s["page_path"], []).append(s["value"])
    ranked: list[dict[str, Any]] = []
    for path, vals in by_page.items():
        if len(vals) < 2:  # ignore single-hit noise
            continue
        vals.sort()
        p75 = _percentile(vals, 0.75)
        ranked.append({"path": path, "lcp_p75": round(p75, 1), "samples": len(vals)})
    ranked.sort(key=lambda r: r["lcp_p75"], reverse=True)
    return ranked[:limit]


# ============= routes =============
@router.post("/rum/web-vitals")
async def ingest(request: Request) -> dict[str, Any]:
    """Public RUM ingest. Accepts a single event or ``{"events": [...]}``.

    Always returns 200 with an ``accepted`` count — RUM beacons are fire-and-forget
    and must never surface an error to the visitor's page. Disabled / rate-limited /
    malformed payloads simply accept 0."""
    if not RUM_ENABLED:
        return {"ok": True, "accepted": 0, "reason": "disabled"}
    if _rate_limited(request):
        return {"ok": True, "accepted": 0, "reason": "rate_limited"}
    try:
        body = await request.json()
    except Exception:
        return {"ok": True, "accepted": 0, "reason": "invalid_json"}

    if isinstance(body, dict) and isinstance(body.get("events"), list):
        raw_events = body["events"]
    elif isinstance(body, list):
        raw_events = body
    elif isinstance(body, dict):
        raw_events = [body]
    else:
        raw_events = []

    accepted = 0
    for raw in raw_events[:RUM_MAX_BATCH]:
        ev = _clean_event(raw)
        if ev is None:
            continue
        try:
            _db().insert_web_vital(ev, retention_days=RUM_RETENTION_DAYS)
            accepted += 1
        except Exception:  # pragma: no cover - never fail a beacon on storage hiccup
            continue
    return {"ok": True, "accepted": accepted}


@router.get("/rum/web-vitals/summary")
async def summary(
    window: str = Query(default="30d"),
    device: str = Query(default="all"),
) -> dict[str, Any]:
    """Aggregated field data for the Speed Insights dashboard."""
    win = window if window in WINDOWS else "30d"
    dev = device if device in (VALID_DEVICES | {"all"}) else "all"
    if not RUM_ENABLED:
        return {
            "source": "vipzone-rum",
            "enabled": False,
            "window": win,
            "device": dev,
            "generated_at": _iso(_now()),
            "total_samples": 0,
            "metrics": {m: _aggregate_metric(m, []) for m in (*CORE_METRICS, *DIAGNOSTIC_METRICS)},
            "slow_pages": [],
            "last_updated": None,
        }

    since = _iso(_now() - timedelta(days=WINDOWS[win]))
    db = _db()
    metrics: dict[str, Any] = {}
    lcp_samples: list[dict[str, Any]] = []
    for m in (*CORE_METRICS, *DIAGNOSTIC_METRICS):
        samples = db.web_vitals_samples(m, since, device=dev)
        metrics[m] = _aggregate_metric(m, samples)
        if m == "LCP":
            lcp_samples = samples

    return {
        "source": "vipzone-rum",
        "enabled": True,
        "window": win,
        "device": dev,
        "generated_at": _iso(_now()),
        "total_samples": db.web_vitals_total(since),
        "metrics": metrics,
        "core_metrics": list(CORE_METRICS),
        "diagnostic_metrics": list(DIAGNOSTIC_METRICS),
        "slow_pages": _slow_pages(lcp_samples),
        "last_updated": db.web_vitals_last_updated(since),
    }
