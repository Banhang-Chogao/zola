"""
Google Search Console OAuth setup routes for the deployed VIPZone API.

WHY THIS LIVES HERE
-------------------
The Render service ``blog-vipzone-api`` runs ``services/vipzone`` (see
``render.yaml`` → ``rootDir: services/vipzone``). A full GSC client also exists
under ``services/visitor-counter`` but that service is NOT the one deployed, so
hitting ``https://blog-vipzone-api.onrender.com/gsc/oauth/start`` used to return
``{"detail":"Not Found"}`` — the router was never mounted on the running app.

These are the minimal routes needed to complete the one-time OAuth consent and
obtain a Search Console **refresh token**:

  GET /gsc/oauth/start     superadmin-gated → redirect to Google consent
  GET /gsc/oauth/callback  Google redirect target → exchange code → store refresh
  GET /gsc/status          configured/connected/property/redirect_uri (no secrets)
  GET /gsc/oauth/token     superadmin-gated → return refresh token once for env setup

EXACT callback URL (register this in the Google OAuth client):
  https://blog-vipzone-api.onrender.com/gsc/oauth/callback

Secrets (GSC_CLIENT_SECRET, the refresh token, the auth code) are never logged.
The refresh token is stored in the SQLite ``settings`` table; because the Render
free tier DB at ``/tmp`` is ephemeral, ``/gsc/oauth/token`` lets a superadmin copy
the token once into the durable ``GSC_REFRESH_TOKEN`` env var / GitHub secret.
"""

from __future__ import annotations

import os
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import RedirectResponse

router = APIRouter(prefix="/gsc", tags=["gsc"])

GSC_CLIENT_ID = os.getenv("GSC_CLIENT_ID", "").strip()
GSC_CLIENT_SECRET = os.getenv("GSC_CLIENT_SECRET", "").strip()
# Domain property (sc-domain:) — covers all subdomains/protocols (V19).
GSC_PROPERTY_URL = os.getenv("GSC_PROPERTY_URL", "sc-domain:seomoney.org").strip()
GSC_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"

# Same backend origin the rest of the service uses, so the redirect_uri here
# matches the value registered in the Google OAuth client exactly.
BACKEND_URL = os.getenv(
    "VIPZONE_BACKEND_URL",
    os.getenv("BACKEND_URL", "https://blog-vipzone-api.onrender.com"),
).rstrip("/")

GSC_REFRESH_SETTING = "gsc:refresh_token"
GSC_STATE_PREFIX = "gsc:"  # oauth_states share the cms table; namespacing avoids clashes


def _redirect_uri() -> str:
    return f"{BACKEND_URL}/gsc/oauth/callback"


def gsc_configured() -> bool:
    return bool(GSC_CLIENT_ID and GSC_CLIENT_SECRET)


def _get_db():
    # Lazy import mirrors cms_auth.py to avoid a circular import at module load.
    from main import get_db

    return get_db()


async def _require_superadmin(authorization: str, sid: str = "") -> dict:
    """Resolve the CMS session (header wins, ``sid`` query is the nav fallback)
    and require superadmin. The sid is never forwarded to Google."""
    from cms_auth import cms_profile_from_sid, resolve_sid
    from roles import is_superadmin

    if not authorization and sid:
        authorization = "Bearer " + sid
    token = resolve_sid(authorization)  # raises 401 if missing/blank
    profile = await cms_profile_from_sid(_get_db(), token)
    if not is_superadmin(profile):
        raise HTTPException(403, "superadmin_required")
    return profile


def _blog_redirect(fragment: str, return_to: str = "/tools/vipzone-admin/") -> RedirectResponse:
    from cms_auth import build_blog_url

    return RedirectResponse(build_blog_url(return_to or "/tools/vipzone-admin/", fragment=fragment))


@router.get("/status")
async def gsc_status() -> dict:
    """Public, secret-free diagnostics for the GSC OAuth wiring."""
    connected = bool(_get_db().get_setting(GSC_REFRESH_SETTING)) or bool(
        os.getenv("GSC_REFRESH_TOKEN", "").strip()
    )
    missing: list[str] = []
    if not GSC_CLIENT_ID:
        missing.append("GSC_CLIENT_ID")
    if not GSC_CLIENT_SECRET:
        missing.append("GSC_CLIENT_SECRET")
    if not connected:
        missing.append("GSC_REFRESH_TOKEN")
    return {
        "configured": gsc_configured(),
        "connected": connected,
        "property": GSC_PROPERTY_URL,
        "redirect_uri": _redirect_uri(),
        "oauth_scope": GSC_SCOPE,
        "missing_credentials": missing,
        "start_url": f"{BACKEND_URL}/gsc/oauth/start",
    }


@router.get("/oauth/start")
async def gsc_oauth_start(
    return_to: str = Query(default="/tools/vipzone-admin/"),
    sid: str = Query(default=""),
    authorization: str = Header(default=""),
) -> RedirectResponse:
    """Superadmin-gated → redirect to Google consent (offline, forces refresh token)."""
    if not gsc_configured():
        raise HTTPException(503, "GSC OAuth chưa cấu hình trên server (GSC_CLIENT_ID/SECRET)")
    await _require_superadmin(authorization, sid)
    if not return_to.startswith("/"):
        return_to = "/tools/vipzone-admin/"
    state = secrets.token_urlsafe(24)
    # Reuse the existing oauth_states table; namespace the state so it can never
    # collide with the GitHub login flow's states. The post-consent landing page
    # rides along as the stored value.
    _get_db().save_oauth_state(GSC_STATE_PREFIX + state, return_to)
    params = urlencode(
        {
            "client_id": GSC_CLIENT_ID,
            "redirect_uri": _redirect_uri(),
            "response_type": "code",
            "scope": GSC_SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": state,
        }
    )
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{params}")


@router.get("/oauth/callback")
async def gsc_oauth_callback(code: str = "", state: str = "") -> RedirectResponse:
    """Google redirect target — exchange code → refresh token, store it, never log it."""
    if not code or not state:
        return _blog_redirect("gsc_error=missing_params")
    if not gsc_configured():
        return _blog_redirect("gsc_error=not_configured")
    return_to = _get_db().pop_oauth_state(GSC_STATE_PREFIX + state)
    if not return_to:
        return _blog_redirect("gsc_error=invalid_state")

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            res = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": GSC_CLIENT_ID,
                    "client_secret": GSC_CLIENT_SECRET,
                    "redirect_uri": _redirect_uri(),
                    "grant_type": "authorization_code",
                },
            )
        except httpx.HTTPError:
            return _blog_redirect("gsc_error=google_unreachable")

    data = res.json() if res.status_code == 200 else {}
    refresh = data.get("refresh_token")
    if not refresh:
        # Google omits refresh_token when consent was already granted; prompt=consent
        # above forces it, but guard anyway. Do not log the response (may hold tokens).
        return _blog_redirect("gsc_error=no_refresh_token", return_to)

    _get_db().set_setting(GSC_REFRESH_SETTING, refresh)
    return _blog_redirect("gsc_connected=1", return_to)


@router.get("/oauth/token")
async def gsc_oauth_token(
    sid: str = Query(default=""),
    authorization: str = Header(default=""),
) -> dict:
    """Superadmin-only: return the stored refresh token ONCE for durable env setup.

    The Render free-tier SQLite at /tmp is wiped on redeploy, so the operator must
    copy this value into the ``GSC_REFRESH_TOKEN`` env var (Render) / GitHub secret.
    Gated behind superadmin; the token is never written to logs.
    """
    await _require_superadmin(authorization, sid)
    token = _get_db().get_setting(GSC_REFRESH_SETTING) or os.getenv("GSC_REFRESH_TOKEN", "").strip()
    if not token:
        raise HTTPException(404, "gsc_not_connected")
    return {
        "refresh_token": token,
        "property": GSC_PROPERTY_URL,
        "note": "Lưu vào env GSC_REFRESH_TOKEN (Render + GitHub secret) để bền vững — DB /tmp mất khi redeploy.",
    }
