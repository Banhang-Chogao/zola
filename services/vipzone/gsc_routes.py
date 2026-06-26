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


def configure(
    *,
    get_redis,
    require_session,
    require_supervip,
    build_blog_url,
    backend_url: str | None = None,
    blog_url: str | None = None,
):
    """Wire the GSC router to a host service.

    `backend_url` / `blog_url` let a second host (e.g. the VIPZone service, which
    does not export BACKEND_URL/BLOG_URL under those exact env names) override the
    OAuth redirect origin + post-login blog origin without relying on module-level
    env defaults. When omitted the module env defaults (BACKEND_URL/BLOG_URL) win,
    preserving the original visitor-counter behaviour.
    """
    global _get_redis, _require_session, _require_supervip, _build_blog_url
    global BACKEND_URL, BLOG_URL
    _get_redis = get_redis
    _require_session = require_session
    _require_supervip = require_supervip
    _build_blog_url = build_blog_url
    if backend_url:
        BACKEND_URL = backend_url.rstrip("/")
    if blog_url:
        BLOG_URL = blog_url.rstrip("/")


def _gsc_configured() -> bool:
    return bool(GSC_CLIENT_ID and GSC_CLIENT_SECRET)


# Operator runbook surfaced after OAuth + by the export endpoint. The OAuth flow can
# re-mint a refresh token into the (ephemeral on Render free tier) KV store, but the
# ONLY durable home is the GSC_REFRESH_TOKEN env var. These steps tell the operator how
# to copy the acquired token there. Keep token OUT of any log line.
OPERATOR_PERSIST_INSTRUCTIONS = [
    "Copy the refresh_token (call GET /gsc/refresh-token?reveal=1 as superadmin).",
    "Set Render env GSC_REFRESH_TOKEN on blog-vipzone-api to that value.",
    "Manual Sync blog-vipzone-api (Render → Blueprints) so the env applies.",
    "Verify GET /gsc/status shows token_source=env.",
]


async def _kv_refresh_token(r) -> str:
    token = await r.get(GSC_REFRESH_KEY)
    return (token or "").strip()


def _env_refresh_token() -> str:
    return os.getenv("GSC_REFRESH_TOKEN", "").strip()


async def _load_refresh_token(r) -> str:
    """Resolve the active refresh token. The durable ENV value wins over the volatile
    KV copy so that once the operator persists the token (GSC_REFRESH_TOKEN) it is the
    source of truth even if a stale KV token lingers (survives Render redeploy)."""
    env_token = _env_refresh_token()
    if env_token:
        return env_token
    return await _kv_refresh_token(r)


async def _token_source(r) -> str:
    """Where the active refresh token comes from: env (durable) | kv (volatile) | none."""
    if _env_refresh_token():
        return "env"
    if await _kv_refresh_token(r):
        return "kv"
    return "none"


def _mask_refresh_token(token: str) -> str:
    """Show just enough to confirm identity; never the full secret by default."""
    if not token:
        return ""
    if len(token) <= 8:
        return "•" * len(token)
    return f"{token[:4]}…{token[-4:]} ({len(token)} chars)"


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
    token_source = await _token_source(r)
    has_refresh_token = token_source != "none"
    connected = has_refresh_token
    prop = await _load_property(r)
    cache_at = await r.get(GSC_CACHE_AT_KEY)
    missing: list[str] = []
    if not GSC_CLIENT_ID:
        missing.append("GSC_CLIENT_ID")
    if not GSC_CLIENT_SECRET:
        missing.append("GSC_CLIENT_SECRET")
    if not connected:
        missing.append("GSC_REFRESH_TOKEN")
    # PUBLIC-SAFE: this endpoint never returns the token itself — only whether one
    # exists and where it lives (env|kv|none). Token export is supervip-gated below.
    return {
        "configured": _gsc_configured(),
        "connected": connected,
        "has_refresh_token": has_refresh_token,
        "token_source": token_source,
        "property": prop or DEFAULT_GSC_PROPERTY_URL,
        "default_property": DEFAULT_GSC_PROPERTY_URL,
        "redirect_uri": f"{BACKEND_URL}/gsc/oauth/callback",
        "oauth_scope": "https://www.googleapis.com/auth/webmasters.readonly",
        "missing_credentials": missing,
        "cache_updated_at": cache_at,
        "cache_ttl_seconds": CACHE_TTL_SECONDS,
    }


@router.get("/refresh-token")
async def gsc_export_refresh_token(
    reveal: int = 0,
    sid: str = "",
    authorization: str = Header(default=""),
):
    """Supervip-only one-time export of the acquired refresh token so the operator can
    copy it into the durable Render env var GSC_REFRESH_TOKEN.

    Masked by default; the full secret is returned ONLY with explicit ?reveal=1 by a
    valid superadmin. The token is never logged. Denied (401/403) without a supervip sid.
    """
    # A top-level browser navigation cannot set the Authorization header, so accept the
    # session id as a `sid` query param too (header wins). Consumed here, never forwarded.
    if not authorization and sid:
        authorization = "Bearer " + sid
    await _require_supervip(authorization)
    r = await _get_redis()
    token = await _load_refresh_token(r)
    source = await _token_source(r)
    if not token:
        # Clear, non-leaky error: nothing to export, point at the OAuth flow.
        raise HTTPException(
            404,
            "no_refresh_token: connect GSC via /gsc/oauth/start first (access_type=offline, prompt=consent).",
        )
    revealed = bool(reveal)
    return {
        "has_refresh_token": True,
        "token_source": source,
        "masked": not revealed,
        "refresh_token": token if revealed else _mask_refresh_token(token),
        "env_var": "GSC_REFRESH_TOKEN",
        "service": "blog-vipzone-api",
        "already_persisted": source == "env",
        "instructions": OPERATOR_PERSIST_INSTRUCTIONS,
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
            # Force Google to return a refresh_token every time: offline access +
            # forced consent re-prompt (Google omits refresh_token on silent re-auth).
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
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
    # If the token is not yet persisted to the durable env var, tell the UI to surface
    # the operator runbook (copy token → set Render env → Manual Sync → verify env).
    fragment = "gsc_connected=1"
    if not _env_refresh_token():
        fragment += "&gsc_persist=1"
    return RedirectResponse(_build_blog_url(return_to, fragment=fragment))


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