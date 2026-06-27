"""RUM — Real User Monitoring ingest for SEOMONEY (Core Web Vitals).

Receives Core Web Vitals (LCP, INP, CLS, FCP, TTFB) measured on real visitor
browsers and stores them for aggregate p75 reporting. Privacy + safety:

  * Public ingest (no auth) but STRICT validation — only the 5 known metrics,
    finite non-negative values, a safe path, capped string lengths.
  * No PII stored: only the page path (no query string), a coarse page_type, the
    metric, a truncated UA and a sha256 hash of the client IP (rate-limit only).
  * Fail-soft: never 500s the beacon. Bad payloads → 4xx; over-limit → silent 204
    (the client never retries). Backend issues never affect the frontend.
  * Body size capped; light per-IP-hash rate limit.

Routes:
  POST /rum/web-vitals            (public — ingest one metric sample)
  GET  /rum/web-vitals/summary    (admin — p75/count by metric and page_type)
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from cms_auth import is_admin, is_commenter_only, session_dep
from roles import is_superadmin

router = APIRouter(tags=["rum"])


# ============= Config (env-driven, no secrets) =============
def _truthy(v: str) -> bool:
    return (v or "").strip().lower() in {"1", "true", "yes", "on"}


RUM_ENABLED = _truthy(os.getenv("RUM_ENABLED", "true"))
# Max raw body bytes accepted on ingest (a single metric is well under 4KB).
try:
    RUM_MAX_BODY = int(os.getenv("RUM_MAX_BODY", "8192"))
except ValueError:
    RUM_MAX_BODY = 8192
RUM_MAX_BODY = max(1024, min(RUM_MAX_BODY, 65536))
# Per-IP-hash rate limit: at most N samples in the rolling window. A page load
# legitimately sends up to 5 metrics, so keep this generous.
try:
    RUM_RATE_WINDOW = int(os.getenv("RUM_RATE_WINDOW", "60"))
except ValueError:
    RUM_RATE_WINDOW = 60
try:
    RUM_RATE_MAX = int(os.getenv("RUM_RATE_MAX", "120"))
except ValueError:
    RUM_RATE_MAX = 120

METRICS = {"LCP", "INP", "CLS", "FCP", "TTFB"}
RATINGS = {"good", "needs-improvement", "poor", ""}
PAGE_TYPES = {
    "home", "article", "listing", "category", "tag", "taxonomy", "tool", "other",
}
# CLS is a unitless ratio; the rest are milliseconds. Cap at 1 hour of ms to
# reject absurd outliers while keeping every realistic value.
VALUE_MAX = 3_600_000.0
_PATH_RE = re.compile(r"^/[A-Za-z0-9._~!$&'()*+,;=:@%/\-]*$")
_ATTR_MAX = 1000  # cap serialized attribution length

# DB getter injected by configure() from the host app (mirrors comments/reports).
_get_db: Optional[Callable[[], Any]] = None


def configure(get_db: Callable[[], Any]) -> None:
    global _get_db
    _get_db = get_db


def _db() -> Any:
    if _get_db is None:  # pragma: no cover - configure() always called at mount
        raise HTTPException(503, "rum_not_configured")
    return _get_db()


# ============= helpers =============
def _hash(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else ""


def _iso_since(seconds: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _iso_since_days(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _normalize_path(raw: Any) -> str:
    """Canonicalise the page path: path-only, leading slash, no query/hash."""
    p = (raw or "").strip() if isinstance(raw, str) else ""
    if not p:
        raise ValueError("missing_path")
    if "://" in p:  # strip scheme/host if a full URL slipped through
        p = p.split("://", 1)[1]
        p = "/" + p.split("/", 1)[1] if "/" in p else "/"
    p = p.split("?", 1)[0].split("#", 1)[0]
    if not p.startswith("/"):
        p = "/" + p
    # Drop a leading /zola base-path segment if present (site root is seomoney.org).
    if p == "/zola" or p.startswith("/zola/"):
        p = p[len("/zola"):] or "/"
    p = re.sub(r"/{2,}", "/", p)[:300]
    if not _PATH_RE.match(p):
        raise ValueError("invalid_path")
    return p


# ============= payload schema (strict) =============
class WebVitalIn(BaseModel):
    """One Core Web Vitals sample. Unknown fields are ignored (forward-compatible)."""

    model_config = ConfigDict(extra="ignore")

    v: int = 1
    page_path: str
    page_type: str = "other"
    metric: str
    value: float
    rating: str = ""
    delta: float = 0.0
    id: str = ""
    nav_type: str = ""
    metric_nav: str = ""
    viewport_w: int = 0
    viewport_h: int = 0
    connection: str = ""
    save_data: bool = False
    ua: str = ""
    attribution: Optional[dict[str, Any]] = None

    @field_validator("metric")
    @classmethod
    def _v_metric(cls, v: str) -> str:
        m = (v or "").strip().upper()
        if m not in METRICS:
            raise ValueError("unknown_metric")
        return m

    @field_validator("value", "delta")
    @classmethod
    def _v_value(cls, v: float, info) -> float:
        if v is None or math.isnan(v) or math.isinf(v):
            raise ValueError("non_finite")
        if v < 0:
            # Metric values are non-negative → reject. delta can legitimately be
            # negative (e.g. CLS correction) → clamp magnitude instead of reject.
            if info.field_name == "value":
                raise ValueError("negative_value")
            v = max(v, -VALUE_MAX)
        if v > VALUE_MAX:
            raise ValueError("value_out_of_range")
        return float(v)

    @field_validator("page_path")
    @classmethod
    def _v_path(cls, v: str) -> str:
        return _normalize_path(v)

    @field_validator("page_type")
    @classmethod
    def _v_page_type(cls, v: str) -> str:
        t = (v or "").strip().lower()[:40]
        return t if t in PAGE_TYPES else "other"

    @field_validator("rating")
    @classmethod
    def _v_rating(cls, v: str) -> str:
        r = (v or "").strip().lower()
        return r if r in RATINGS else ""

    @field_validator("id", "nav_type", "metric_nav", "connection", "ua")
    @classmethod
    def _v_trim(cls, v: str) -> str:
        # Truncate (don't reject) over-long strings so real beacons are never dropped.
        return (v or "")[:200]

    @field_validator("viewport_w", "viewport_h")
    @classmethod
    def _v_viewport(cls, v: int) -> int:
        try:
            return max(0, min(int(v), 20000))
        except (TypeError, ValueError):
            return 0


def _attribution_json(item: WebVitalIn) -> str:
    if not item.attribution:
        return ""
    try:
        s = json.dumps(item.attribution, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError):
        return ""
    return s[:_ATTR_MAX]


# ============= auth dependency (summary only) =============
async def _require_admin(profile: dict[str, Any] = Depends(session_dep)) -> dict[str, Any]:
    """Admin gate for the summary endpoint (reuses CMS session / allowlist)."""
    if is_commenter_only(profile):
        raise HTTPException(403, "admin_only")
    if not is_admin(profile.get("email"), profile.get("username")) and not is_superadmin(profile):
        raise HTTPException(403, "admin_only")
    return profile


# ============= routes =============
@router.post("/rum/web-vitals")
async def ingest_web_vital(request: Request) -> Response:
    """Public ingest of one Core Web Vitals sample. Always 204 on accept/drop."""
    if not RUM_ENABLED:
        return Response(status_code=204)

    raw = await request.body()
    if len(raw) > RUM_MAX_BODY:
        raise HTTPException(413, "payload_too_large")
    try:
        data = json.loads(raw or b"{}")
    except Exception:
        raise HTTPException(400, "invalid_json")
    if not isinstance(data, dict):
        raise HTTPException(400, "invalid_body")

    try:
        item = WebVitalIn(**data)
    except ValidationError:
        raise HTTPException(422, "invalid_payload")

    ip_hash = _hash(_client_ip(request))
    # Over-limit → accept-but-drop (silent 204) so the beacon never retries/errors.
    if _db().count_recent_web_vitals_by_ip(ip_hash, _iso_since(RUM_RATE_WINDOW)) >= RUM_RATE_MAX:
        return Response(status_code=204)

    try:
        _db().insert_web_vital(
            {
                "page_path": item.page_path,
                "page_type": item.page_type,
                "metric": item.metric,
                "value": item.value,
                "rating": item.rating,
                "delta": item.delta,
                "metric_id": item.id,
                "nav_type": item.nav_type or item.metric_nav,
                "viewport_w": item.viewport_w,
                "viewport_h": item.viewport_h,
                "connection": item.connection,
                "save_data": item.save_data,
                "ua": item.ua,
                "attribution": _attribution_json(item),
                "ip_hash": ip_hash,
            }
        )
    except Exception:
        # Storage hiccup must never break the beacon — accept silently.
        return Response(status_code=204)

    return Response(status_code=204)


@router.get("/rum/web-vitals/summary")
async def web_vitals_summary(
    days: int = Query(7, ge=1, le=90),
    _admin: dict[str, Any] = Depends(_require_admin),
) -> dict[str, Any]:
    """Admin: p75 + count by metric and page_type over the last `days` days."""
    return _db().web_vitals_summary(_iso_since_days(days))
