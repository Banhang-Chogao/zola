"""
Google Search Console API client — OAuth refresh token, cached metrics bundle.

Uses official google-api-python-client. No mock data; callers must supply
real refresh_token + property siteUrl from OAuth or env secrets.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
CACHE_TTL_SECONDS = 20 * 60  # 20 minutes

# URL-prefix property in Search Console — must match siteUrl exactly in API calls.
DEFAULT_GSC_PROPERTY_URL = "https://seomoney.org/"

# Canonical Search Console property for production. A *domain* property
# (sc-domain:) covers http/https and every subdomain/path in one entry, so the
# deploy preflight requires exactly this value (see scripts/gsc_preflight.py).
EXPECTED_GSC_PROPERTY = "sc-domain:seomoney.org"

# Sitemap that must be registered against the property.
EXPECTED_SITEMAP_URL = "https://seomoney.org/sitemap.xml"


def normalize_gsc_property_url(site_url: str) -> str:
    """Normalize URL-prefix GSC properties; keep sc-domain: entries unchanged."""
    url = (site_url or "").strip()
    if not url or url.startswith("sc-domain:"):
        return url
    if not url.endswith("/"):
        url += "/"
    return url


def normalize_property_for_match(value: str) -> str:
    """Canonicalize a property id for equality checks (case-insensitive host)."""
    v = (value or "").strip()
    if v.startswith("sc-domain:"):
        host = v[len("sc-domain:") :].strip().lower().rstrip("/")
        return f"sc-domain:{host}"
    return normalize_gsc_property_url(v).lower()


def is_expected_property(value: str, expected: str = EXPECTED_GSC_PROPERTY) -> bool:
    """True only when ``value`` resolves to the canonical domain property."""
    return bool(value) and normalize_property_for_match(value) == normalize_property_for_match(expected)


def pick_preferred_property(properties: list[str]) -> str | None:
    """Select the blog property only — never fall back to another domain."""
    if not properties:
        return None
    target = normalize_gsc_property_url(DEFAULT_GSC_PROPERTY_URL)
    normalized = {normalize_gsc_property_url(p): p for p in properties}
    if target in normalized:
        return normalized[target]
    # Accept API variant without trailing slash, but only for this exact host/path.
    bare = target.rstrip("/")
    for prop in properties:
        if prop.rstrip("/") == bare:
            return prop
    return None


def _utc_today() -> date:
    return datetime.now(timezone.utc).date()


def _iso(d: date) -> str:
    return d.strftime("%Y-%m-%d")


def build_credentials(
    refresh_token: str,
    client_id: str,
    client_secret: str,
) -> Credentials:
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return creds


def build_service(creds: Credentials):
    return build("searchconsole", "v1", credentials=creds, cache_discovery=False)


def list_site_properties(creds: Credentials) -> list[str]:
    service = build_service(creds)
    res = service.sites().list().execute()
    entries = res.get("siteEntry") or []
    out: list[str] = []
    for e in entries:
        url = (e.get("siteUrl") or "").strip()
        if url and (e.get("permissionLevel") or "").lower() != "siteunverifieduser":
            out.append(url)
    return sorted(out)


def find_property_permission(creds, expected: str = EXPECTED_GSC_PROPERTY) -> tuple[bool, str | None]:
    """Return (verified, permissionLevel) for ``expected`` via sites.list().

    ``verified`` is True only when the property is present AND the account is not
    a mere ``siteUnverifiedUser``. Never returns credentials.
    """
    service = build_service(creds)
    res = service.sites().list().execute()
    want = normalize_property_for_match(expected)
    for e in res.get("siteEntry") or []:
        url = (e.get("siteUrl") or "").strip()
        perm = (e.get("permissionLevel") or "").strip()
        if normalize_property_for_match(url) == want:
            if perm.lower() == "siteunverifieduser":
                return False, perm
            return True, perm
    return False, None


def list_sitemap_paths(creds, site_url: str) -> list[str]:
    """Return submitted sitemap URLs (``path``) registered for ``site_url``."""
    service = build_service(creds)
    try:
        res = service.sitemaps().list(siteUrl=site_url).execute()
    except HttpError as exc:
        if exc.resp.status == 403:
            raise PermissionError(f"GSC sitemap permission denied for {site_url}") from exc
        raise
    return [(s.get("path") or "").strip() for s in (res.get("sitemap") or []) if s.get("path")]


def smoke_search_analytics(creds, site_url: str, days: int = 7) -> dict[str, float]:
    """Aggregate Search Analytics totals for the trailing ``days`` window.

    Used as a deploy preflight smoke test — confirms the Search Analytics
    endpoint answers for the property. Returns aggregated counts only.
    """
    service = build_service(creds)
    end = _utc_today() - timedelta(days=1)
    start = end - timedelta(days=max(1, days) - 1)
    rows = _query(service, site_url, start, end, dimensions=None, row_limit=1)
    return _aggregate_row((rows or [None])[0])


def _query(
    service,
    site_url: str,
    start: date,
    end: date,
    dimensions: list[str] | None = None,
    row_limit: int = 25,
) -> list[dict[str, Any]]:
    body: dict[str, Any] = {
        "startDate": _iso(start),
        "endDate": _iso(end),
        "rowLimit": row_limit,
    }
    if dimensions:
        body["dimensions"] = dimensions
    try:
        res = service.searchanalytics().query(siteUrl=site_url, body=body).execute()
    except HttpError as exc:
        if exc.resp.status == 403:
            raise PermissionError(f"GSC permission denied for {site_url}") from exc
        if exc.resp.status == 429:
            raise RuntimeError("GSC API quota exceeded") from exc
        raise
    return list(res.get("rows") or [])


def _aggregate_row(row: dict | None) -> dict[str, float]:
    if not row:
        return {"clicks": 0.0, "impressions": 0.0, "ctr": 0.0, "position": 0.0}
    clicks = float(row.get("clicks") or 0)
    impressions = float(row.get("impressions") or 0)
    ctr = float(row.get("ctr") or 0) * 100.0
    position = float(row.get("position") or 0)
    return {
        "clicks": clicks,
        "impressions": impressions,
        "ctr": round(ctr, 2),
        "position": round(position, 1),
    }


def _rows_to_pages(rows: list[dict]) -> list[dict]:
    out = []
    for row in rows:
        keys = row.get("keys") or []
        page = keys[0] if keys else ""
        agg = _aggregate_row(row)
        out.append(
            {
                "page": page,
                "clicks": int(agg["clicks"]),
                "impressions": int(agg["impressions"]),
                "ctr": agg["ctr"],
                "position": agg["position"],
            }
        )
    return out


def _rows_to_queries(rows: list[dict]) -> list[dict]:
    out = []
    for row in rows:
        keys = row.get("keys") or []
        query = keys[0] if keys else ""
        agg = _aggregate_row(row)
        out.append(
            {
                "query": query,
                "clicks": int(agg["clicks"]),
                "impressions": int(agg["impressions"]),
                "ctr": agg["ctr"],
                "position": agg["position"],
            }
        )
    return out


def _rows_to_trend(rows: list[dict]) -> list[dict]:
    out = []
    for row in rows:
        keys = row.get("keys") or []
        day = keys[0] if keys else ""
        agg = _aggregate_row(row)
        out.append(
            {
                "date": day,
                "clicks": int(agg["clicks"]),
                "impressions": int(agg["impressions"]),
            }
        )
    return sorted(out, key=lambda x: x["date"])


def _fetch_sitemaps(service, site_url: str) -> dict[str, Any]:
    try:
        res = service.sitemaps().list(siteUrl=site_url).execute()
    except HttpError:
        return {
            "status": "unknown",
            "submitted_pages": 0,
            "last_downloaded": None,
            "warnings": 0,
            "errors": 0,
        }
    sitemaps = res.get("sitemap") or []
    submitted = 0
    warnings = 0
    errors = 0
    last_dl: str | None = None
    status = "ok"
    for sm in sitemaps:
        for block in sm.get("contents") or []:
            submitted += int(block.get("submitted") or 0)
        warnings += int(sm.get("warnings") or 0)
        errors += int(sm.get("errors") or 0)
        dl = sm.get("lastDownloaded")
        if dl and (last_dl is None or dl > last_dl):
            last_dl = dl
    if errors:
        status = "error"
    elif warnings:
        status = "warning"
    elif not sitemaps:
        status = "missing"
    return {
        "status": status,
        "submitted_pages": submitted,
        "last_downloaded": last_dl,
        "warnings": warnings,
        "errors": errors,
    }


def _indexing_health(indexed: int, submitted: int, sitemap_status: str) -> str:
    if sitemap_status == "error":
        return "Problem"
    if submitted <= 0:
        return "Warning" if indexed > 0 else "Warning"
    ratio = indexed / submitted if submitted else 0
    if ratio >= 0.9 and sitemap_status == "ok":
        return "Excellent"
    if ratio >= 0.7:
        return "Good"
    if ratio >= 0.45:
        return "Warning"
    return "Problem"


def _executive_summary(
    current: dict[str, float],
    previous: dict[str, float],
    top_queries: list[dict],
    top_pages: list[dict],
) -> list[str]:
    lines: list[str] = []
    imp_prev, imp_now = previous["impressions"], current["impressions"]
    if imp_prev > 0:
        delta = round((imp_now - imp_prev) / imp_prev * 100)
        if delta > 0:
            lines.append(f"Traffic increased {delta}% over the last 28 days (impressions).")
        elif delta < 0:
            lines.append(f"Impressions decreased {abs(delta)}% over the last 28 days.")
    pos_prev, pos_now = previous["position"], current["position"]
    if pos_prev > 0 and pos_now > 0 and pos_now < pos_prev:
        lines.append(
            f"Average position improved from {pos_prev:.1f} to {pos_now:.1f}."
        )
    if top_queries:
        q0 = top_queries[0].get("query") or ""
        if q0:
            lines.append(f'Top query driving clicks: "{q0}".')
    if top_pages:
        p0 = top_pages[0].get("page") or ""
        if p0:
            short = p0.replace("https://seomoney.org", "") or p0
            lines.append(f"Strongest page: {short} ({top_pages[0].get('clicks', 0)} clicks).")
    if not lines:
        lines.append("Connected to Google Search Console — collecting performance baseline.")
    return lines[:4]


def fetch_metrics_bundle(
    refresh_token: str,
    client_id: str,
    client_secret: str,
    site_url: str,
) -> dict[str, Any]:
    """Pull full GSC metrics for seo-reality + gsc-metrics.json."""
    creds = build_credentials(refresh_token, client_id, client_secret)
    service = build_service(creds)
    today = _utc_today()
    end = today - timedelta(days=1)
    start_28 = end - timedelta(days=27)
    start_prev = start_28 - timedelta(days=28)
    end_prev = start_28 - timedelta(days=1)

    totals = _aggregate_row(
        (_query(service, site_url, start_28, end, dimensions=None, row_limit=1) or [None])[0]
    )
    prev_totals = _aggregate_row(
        (_query(service, site_url, start_prev, end_prev, dimensions=None, row_limit=1) or [None])[0]
    )

    top_pages = _rows_to_pages(
        _query(service, site_url, start_28, end, dimensions=["page"], row_limit=10)
    )
    top_queries = _rows_to_queries(
        _query(service, site_url, start_28, end, dimensions=["query"], row_limit=10)
    )
    daily = _rows_to_trend(
        _query(service, site_url, start_28, end, dimensions=["date"], row_limit=400)
    )

    page_rows = _query(service, site_url, start_28, end, dimensions=["page"], row_limit=2500)
    indexed_pages = len(page_rows)
    sitemap = _fetch_sitemaps(service, site_url)
    submitted = int(sitemap.get("submitted_pages") or 0)
    non_indexed = max(0, submitted - indexed_pages) if submitted else None
    health = _indexing_health(indexed_pages, submitted, sitemap.get("status") or "unknown")

    weekly: list[dict] = []
    monthly: list[dict] = []
    if daily:
        # aggregate by ISO week / month from daily rows
        w_map: dict[str, dict] = {}
        m_map: dict[str, dict] = {}
        for d in daily:
            ds = d["date"]
            try:
                dt = datetime.strptime(ds, "%Y-%m-%d").date()
            except ValueError:
                continue
            wk = f"{dt.isocalendar().year}-W{dt.isocalendar().week:02d}"
            mo = ds[:7]
            for key, bucket in ((wk, w_map), (mo, m_map)):
                if key not in bucket:
                    bucket[key] = {"period": key, "clicks": 0, "impressions": 0}
                bucket[key]["clicks"] += d["clicks"]
                bucket[key]["impressions"] += d["impressions"]
        weekly = [w_map[k] for k in sorted(w_map)]
        monthly = [m_map[k] for k in sorted(m_map)]

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    summary = _executive_summary(totals, prev_totals, top_queries, top_pages)

    return {
        "updated_at": now,
        "property": site_url,
        "connected": True,
        "status": "ok",
        "period_days": 28,
        "clicks": int(totals["clicks"]),
        "impressions": int(totals["impressions"]),
        "ctr": totals["ctr"],
        "avg_position": totals["position"],
        "indexed_pages": indexed_pages,
        "non_indexed_pages": non_indexed,
        "pages_waiting": non_indexed,
        "submitted_pages": submitted,
        "coverage_issues": int(sitemap.get("errors") or 0) + int(sitemap.get("warnings") or 0),
        "sitemap_status": sitemap.get("status"),
        "last_crawl": sitemap.get("last_downloaded"),
        "avg_index_delay_days": None,
        "index_health": health,
        "top_pages": top_pages,
        "top_queries": top_queries,
        "trend": {
            "daily": daily,
            "weekly": weekly,
            "monthly": monthly,
        },
        "executive_summary": summary,
        "previous_period": {
            "clicks": int(prev_totals["clicks"]),
            "impressions": int(prev_totals["impressions"]),
            "avg_position": prev_totals["position"],
        },
    }


def disconnected_payload(reason: str = "not_connected") -> dict[str, Any]:
    return {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "connected": False,
        "status": reason,
        "property": None,
        "clicks": None,
        "impressions": None,
        "ctr": None,
        "avg_position": None,
        "indexed_pages": None,
        "non_indexed_pages": None,
        "submitted_pages": None,
        "sitemap_status": None,
        "last_crawl": None,
        "index_health": None,
        "top_pages": [],
        "top_queries": [],
        "trend": {"daily": [], "weekly": [], "monthly": []},
        "executive_summary": [],
    }