"""
Google Search Console OAuth + cached metrics API for SEO Reality Check widget.
"""

from __future__ import annotations

import json
import os
import secrets
from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from fastapi.responses import RedirectResponse

from gsc_client import (
    CACHE_TTL_SECONDS,
    DEFAULT_GSC_PROPERTY_URL,
    disconnected_payload,
    fetch_metrics_bundle,
    list_site_properties,
    normalize_gsc_property_url,
    pick_preferred_property,
)

router = APIRouter(prefix="/gsc", tags=["gsc"])

GSC_CLIENT_ID = os.getenv("GSC_CLIENT_ID", "")
GSC_CLIENT_SECRET = os.getenv("GSC_CLIENT_SECRET", "")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
BLOG_URL = os.getenv("BLOG_URL", "https://seomoney.org").rstrip("/")

GSC_REFRESH_KEY = "gsc:refresh_token"
GSC_PROPERTY_KEY = "gsc:property"
GSC_CACHE_KEY = "gsc:metrics_cache"
GSC_CACHE_AT_KEY = "gsc:cache_at"
GSC_OAUTH_STATE_PREFIX = "gsc:oauth_state:"

# Injected from main.py
_get_redis = None
_require_session = None
_require_supervip = None
_build_blog_url = None


def configure(*, get_redis, require_session, require_supervip, build_blog_url):
    global _get_redis, _require_session, _require_supervip, _build_blog_url
    _get_redis = get_redis
    _require_session = require_session
    _require_supervip = require_supervip
    _build_blog_url = build_blog_url


def _gsc_configured() -> bool:
    return bool(GSC_CLIENT_ID and GSC_CLIENT_SECRET)


async def _load_refresh_token(r) -> str:
    token = await r.get(GSC_REFRESH_KEY)
    if token:
        return token
    return os.getenv("GSC_REFRESH_TOKEN", "").strip()


async def _load_property(r) -> str:
    prop = await r.get(GSC_PROPERTY_KEY)
    if prop:
        return normalize_gsc_property_url(prop)
    env_prop = os.getenv("GSC_PROPERTY_URL", DEFAULT_GSC_PROPERTY_URL).strip()
    return normalize_gsc_property_url(env_prop) if env_prop else ""


async def _cache_get(r) -> dict | None:
    raw = await r.get(GSC_CACHE_KEY)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


async def _cache_set(r, payload: dict) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    await r.set(GSC_CACHE_KEY, json.dumps(payload, ensure_ascii=False))
    await r.set(GSC_CACHE_AT_KEY, now)


async def _cache_stale(r) -> bool:
    at = await r.get(GSC_CACHE_AT_KEY)
    if not at:
        return True
    try:
        ts = datetime.strptime(at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return True
    age = (datetime.now(timezone.utc) - ts).total_seconds()
    return age >= CACHE_TTL_SECONDS


async def _refresh_metrics(r, *, force: bool = False) -> dict:
    refresh = await _load_refresh_token(r)
    prop = await _load_property(r)
    if not refresh or not prop:
        return disconnected_payload("not_connected")
    if not _gsc_configured():
        return disconnected_payload("not_configured")

    if not force and not await _cache_stale(r):
        cached = await _cache_get(r)
        if cached:
            return cached

    try:
        payload = fetch_metrics_bundle(refresh, GSC_CLIENT_ID, GSC_CLIENT_SECRET, prop)
        await _cache_set(r, payload)
        return payload
    except PermissionError:
        return disconnected_payload("token_expired")
    except RuntimeError as exc:
        if "quota" in str(exc).lower():
            cached = await _cache_get(r)
            if cached:
                cached = dict(cached)
                cached["status"] = "quota_warning"
                return cached
            return disconnected_payload("quota_exceeded")
        raise
    except Exception:
        cached = await _cache_get(r)
        if cached:
            cached = dict(cached)
            cached["status"] = "stale_cache"
            return cached
        return disconnected_payload("api_error")


@router.get("/status")
async def gsc_status():
    r = await _get_redis()
    connected = bool(await _load_refresh_token(r))
    prop = await _load_property(r)
    cache_at = await r.get(GSC_CACHE_AT_KEY)
    missing: list[str] = []
    if not GSC_CLIENT_ID:
        missing.append("GSC_CLIENT_ID")
    if not GSC_CLIENT_SECRET:
        missing.append("GSC_CLIENT_SECRET")
    if not connected:
        missing.append("GSC_REFRESH_TOKEN")
    return {
        "configured": _gsc_configured(),
        "connected": connected,
        "property": prop or DEFAULT_GSC_PROPERTY_URL,
        "default_property": DEFAULT_GSC_PROPERTY_URL,
        "redirect_uri": f"{BACKEND_URL}/gsc/oauth/callback",
        "oauth_scope": "https://www.googleapis.com/auth/webmasters.readonly",
        "missing_credentials": missing,
        "cache_updated_at": cache_at,
        "cache_ttl_seconds": CACHE_TTL_SECONDS,
    }


async def _background_refresh(r) -> None:
    """Refresh GSC cache without blocking the public metrics response."""
    try:
        await _refresh_metrics(r, force=True)
    except Exception:
        pass


@router.get("/metrics")
async def gsc_metrics_public(background_tasks: BackgroundTasks):
    """Public cached GSC bundle — no auth (aggregate search stats only)."""
    r = await _get_redis()
    cached = await _cache_get(r)
    stale = await _cache_stale(r)
    if cached and not stale:
        return cached
    if cached and stale:
        background_tasks.add_task(_background_refresh, r)
        out = dict(cached)
        if out.get("status") in (None, "ok"):
            out["status"] = "stale_cache"
        return out
    return await _refresh_metrics(r, force=True)


@router.get("/oauth/start")
async def gsc_oauth_start(
    return_to: str = "/",
    sid: str = "",
    authorization: str = Header(default=""),
):
    if not _gsc_configured():
        raise HTTPException(503, "GSC OAuth chưa cấu hình trên server")
    # A top-level browser navigation (the "Kết nối GSC" button / Enter key) cannot
    # set the Authorization header, so the admin session id may ride as a `sid`
    # query param. The header still wins when both are present. The sid is consumed
    # here and is never forwarded to Google in the redirect below.
    if not authorization and sid:
        authorization = "Bearer " + sid
    await _require_supervip(authorization)
    if not return_to.startswith("/"):
        return_to = "/"
    state = secrets.token_urlsafe(24)
    r = await _get_redis()
    await r.setex(GSC_OAUTH_STATE_PREFIX + state, 600, return_to)
    params = urlencode(
        {
            "client_id": GSC_CLIENT_ID,
            "redirect_uri": f"{BACKEND_URL}/gsc/oauth/callback",
            "response_type": "code",
            "scope": "https://www.googleapis.com/auth/webmasters.readonly",
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
    )
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{params}")


@router.get("/oauth/callback")
async def gsc_oauth_callback(code: str = "", state: str = ""):
    if not code or not state:
        return RedirectResponse(_build_blog_url("/", fragment="gsc_error=missing_params"))
    r = await _get_redis()
    return_to = await r.getdel(GSC_OAUTH_STATE_PREFIX + state)
    if not return_to:
        return RedirectResponse(_build_blog_url("/", fragment="gsc_error=invalid_state"))

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            res = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": GSC_CLIENT_ID,
                    "client_secret": GSC_CLIENT_SECRET,
                    "redirect_uri": f"{BACKEND_URL}/gsc/oauth/callback",
                    "grant_type": "authorization_code",
                },
            )
        except httpx.HTTPError:
            return RedirectResponse(_build_blog_url(return_to, fragment="gsc_error=google_unreachable"))
        data = res.json() if res.status_code == 200 else {}
        refresh = data.get("refresh_token")
        if not refresh:
            return RedirectResponse(_build_blog_url(return_to, fragment="gsc_error=no_refresh_token"))

    await r.set(GSC_REFRESH_KEY, refresh)
    props = []
    try:
        props = list_site_properties(
            __import__("gsc_client").build_credentials(refresh, GSC_CLIENT_ID, GSC_CLIENT_SECRET)
        )
    except Exception:
        pass
    preferred = pick_preferred_property(props)
    if preferred:
        await r.set(GSC_PROPERTY_KEY, normalize_gsc_property_url(preferred))
    elif len(props) == 1:
        await r.set(GSC_PROPERTY_KEY, normalize_gsc_property_url(props[0]))
    await r.delete(GSC_CACHE_KEY)
    await r.delete(GSC_CACHE_AT_KEY)
    return RedirectResponse(_build_blog_url(return_to, fragment="gsc_connected=1"))


@router.get("/properties")
async def gsc_properties(authorization: str = Header(default="")):
    await _require_supervip(authorization)
    r = await _get_redis()
    refresh = await _load_refresh_token(r)
    if not refresh:
        raise HTTPException(400, "GSC chưa kết nối")
    if not _gsc_configured():
        raise HTTPException(503, "GSC OAuth chưa cấu hình")
    from gsc_client import build_credentials

    creds = build_credentials(refresh, GSC_CLIENT_ID, GSC_CLIENT_SECRET)
    return {"properties": list_site_properties(creds)}


@router.post("/property")
async def gsc_set_property(request: Request, authorization: str = Header(default="")):
    await _require_supervip(authorization)
    try:
        request_body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(400, "invalid_json")
    site = normalize_gsc_property_url(
        str(request_body.get("siteUrl") or request_body.get("property") or "").strip()
    )
    if not site:
        raise HTTPException(400, "siteUrl required")
    expected = normalize_gsc_property_url(DEFAULT_GSC_PROPERTY_URL)
    if site.rstrip("/") != expected.rstrip("/"):
        raise HTTPException(400, f"Only property {DEFAULT_GSC_PROPERTY_URL} is allowed")
    r = await _get_redis()
    await r.set(GSC_PROPERTY_KEY, site)
    await r.delete(GSC_CACHE_KEY)
    await r.delete(GSC_CACHE_AT_KEY)
    payload = await _refresh_metrics(r, force=True)
    return {"ok": True, "property": site, "metrics": payload}


@router.post("/disconnect")
async def gsc_disconnect(authorization: str = Header(default="")):
    await _require_supervip(authorization)
    r = await _get_redis()
    refresh = await _load_refresh_token(r)
    if refresh and _gsc_configured():
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    "https://oauth2.googleapis.com/revoke",
                    params={"token": refresh},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
        except httpx.HTTPError:
            pass
    await r.delete(GSC_REFRESH_KEY)
    await r.delete(GSC_PROPERTY_KEY)
    await r.delete(GSC_CACHE_KEY)
    await r.delete(GSC_CACHE_AT_KEY)
    return {"ok": True, "connected": False}


@router.post("/refresh")
async def gsc_force_refresh(authorization: str = Header(default="")):
    await _require_supervip(authorization)
    r = await _get_redis()
    return await _refresh_metrics(r, force=True)


@router.post("/cache/clear")
async def gsc_clear_cache(authorization: str = Header(default="")):
    await _require_supervip(authorization)
    r = await _get_redis()
    await r.delete(GSC_CACHE_KEY)
    await r.delete(GSC_CACHE_AT_KEY)
    return {"ok": True, "cleared": True}


@router.get("/debug")
async def gsc_debug(authorization: str = Header(default="")):
    """SuperVIP diagnostics — connection, cache, credentials (no secrets)."""
    await _require_supervip(authorization)
    r = await _get_redis()
    connected = bool(await _load_refresh_token(r))
    prop = await _load_property(r)
    cache_at = await r.get(GSC_CACHE_AT_KEY)
    stale = await _cache_stale(r)
    cached = await _cache_get(r)
    return {
        "configured": _gsc_configured(),
        "connected": connected,
        "property": prop or DEFAULT_GSC_PROPERTY_URL,
        "cache_updated_at": cache_at,
        "cache_stale": stale,
        "cache_has_data": cached is not None,
        "cache_status": (cached or {}).get("status"),
    }