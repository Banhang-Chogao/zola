"""GitHub OAuth + CMS session store for VIPZone API (self-hosted auth)."""

from __future__ import annotations

import os
import secrets
from typing import Any, Literal
from urllib.parse import urlencode, urlparse

import httpx
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from db import VipzoneDB
from github_repo import check_repo_superadmin
from roles import resolve_role, username_is_superadmin

SESSION_COOKIE_NAME = os.getenv("VIPZONE_SESSION_COOKIE", "zola_cms_sid")

BLOG_URL = os.getenv("VIPZONE_BLOG_URL", "https://seomoney.org").rstrip("/")
BACKEND_URL = os.getenv(
    "VIPZONE_BACKEND_URL",
    os.getenv("BACKEND_URL", "https://blog-vipzone-api.onrender.com"),
).rstrip("/")
GH_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID") or os.getenv("GH_CLIENT_ID", "")
GH_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET") or os.getenv("GH_CLIENT_SECRET", "")
SESSION_TTL = int(os.getenv("VIPZONE_SESSION_TTL", str(8 * 3600)))

ADMIN_EMAILS = {
    e.strip().lower()
    for e in os.getenv("ADMIN_EMAILS", "292648126+banhang-chogao@users.noreply.github.com").split(",")
    if e.strip()
}
ADMIN_USERNAMES = {
    u.strip().lower()
    for u in os.getenv("ADMIN_USERNAMES", "banhang-chogao").split(",")
    if u.strip()
}

# ============= Auth provider rollout (GitHub → Google) =============
# AUTH_PROVIDER controls which login gateways are enabled:
#   "github" (default) — GitHub OAuth only (legacy behaviour, unchanged)
#   "dual"             — BOTH Google and GitHub (safe rollout)
#   "google"           — Google OAuth / OpenID Connect only
# Change the value on Render → restart, no code edit needed. Rollback = "github".
AUTH_PROVIDER = os.getenv("AUTH_PROVIDER", "github").strip().lower()
if AUTH_PROVIDER not in {"github", "google", "dual"}:
    AUTH_PROVIDER = "github"

# Google OAuth 2.0 / OpenID Connect (server-side flow). Create a "Web
# application" OAuth client in Google Cloud Console. The secret stays
# server-side only and is never exposed to the browser.
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
# redirect_uri must EXACTLY match the value registered in Google Cloud Console.
# Default derived from BACKEND_URL; override via env when the backend domain differs.
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI", f"{BACKEND_URL}/auth/google/callback"
).strip()
# Google OIDC endpoints (stable, safe to hardcode per the OIDC spec).
GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_TOKENINFO_ENDPOINT = "https://oauth2.googleapis.com/tokeninfo"
GOOGLE_ISS = {"https://accounts.google.com", "accounts.google.com"}

# Email allowlist for Google login — comma-separated. Kept SEPARATE from
# ADMIN_EMAILS (GitHub) so Google admins don't depend on the GitHub noreply
# email. Falls back to ADMIN_EMAILS when unset → avoids locking yourself out.
GOOGLE_ADMIN_EMAILS = {
    e.strip().lower()
    for e in os.getenv("GOOGLE_ADMIN_EMAILS", "").split(",")
    if e.strip()
} or set(ADMIN_EMAILS)

_BLOG_BASE_PATH = urlparse(BLOG_URL).path.rstrip("/")

router = APIRouter(tags=["auth"])


class AuthMeResponse(BaseModel):
    # Normalized fields (read by the dual-provider frontend).
    authenticated: bool = True
    provider: Literal["github", "google"] = "github"
    email: str | None = None
    name: str = ""
    avatar_url: str = ""
    # Legacy fields kept for GitHub editor.js / CMS compatibility.
    username: str = ""
    avatar: str = ""
    role: Literal["user", "vip", "superadmin"] = "user"
    is_super: bool = False
    is_admin: bool = False
    vip_plan: str | None = None
    vip_expires_at: str | None = None


def _github_enabled() -> bool:
    """GitHub login enabled when AUTH_PROVIDER is 'github' or 'dual'."""
    return AUTH_PROVIDER in {"github", "dual"}


def _google_enabled() -> bool:
    """Google login enabled when AUTH_PROVIDER is 'google' or 'dual'."""
    return AUTH_PROVIDER in {"google", "dual"}


def _google_email_allowed(email: str) -> bool:
    """A verified Google email must be in GOOGLE_ADMIN_EMAILS to reach the CMS."""
    return (email or "").strip().lower() in GOOGLE_ADMIN_EMAILS


def _truthy(v: Any) -> bool:
    """tokeninfo returns 'email_verified' as the string 'true'/'false' or a bool."""
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"true", "1", "yes"}


class LogoutResponse(BaseModel):
    ok: bool = True


def is_admin(email: str | None, username: str | None) -> bool:
    if username and username.lower() in ADMIN_USERNAMES:
        return True
    if email and email.lower() in ADMIN_EMAILS:
        return True
    return False


def normalize_return_to(return_to: str) -> str:
    rt = (return_to or "").strip()
    if not rt:
        return "/tools/vipzone-admin/"
    if rt.startswith("http://") or rt.startswith("https://"):
        parsed = urlparse(rt)
        blog = urlparse(BLOG_URL)
        if parsed.netloc != blog.netloc:
            return "/tools/vipzone-admin/"
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        return path
    if rt.startswith("/"):
        return rt
    return "/tools/vipzone-admin/"


def build_blog_url(
    return_to: str,
    fragment: str = "",
    *,
    extra_query: dict[str, str] | None = None,
) -> str:
    rt = normalize_return_to(return_to)
    if _BLOG_BASE_PATH and rt.startswith(_BLOG_BASE_PATH + "/"):
        rt = rt[len(_BLOG_BASE_PATH) :]
    if _BLOG_BASE_PATH and rt == _BLOG_BASE_PATH:
        rt = "/"
    if not rt.startswith("/"):
        rt = "/" + rt
    url = f"{BLOG_URL}{rt}"
    if extra_query:
        for key, val in extra_query.items():
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}{key}={val}"
    return url + (f"#{fragment}" if fragment else "")


def attach_session_cookie(response: Response, sid: str) -> None:
    """Edge/Safari cross-site session — SameSite=None requires Secure + HttpOnly."""
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=sid,
        max_age=SESSION_TTL,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        secure=True,
        samesite="none",
    )


def redirect_with_error(error: str, return_to: str = "/tools/vipzone-admin/") -> RedirectResponse:
    base = build_blog_url(return_to)
    sep = "&" if "?" in base else "?"
    return RedirectResponse(f"{base}{sep}auth_error={error}")


def resolve_sid(authorization: str = "", cookie_sid: str | None = None) -> str:
    if authorization and authorization.startswith("Bearer "):
        sid = authorization[7:].strip()
        if sid:
            return sid
    if cookie_sid and cookie_sid.strip():
        return cookie_sid.strip()
    raise HTTPException(
        401,
        "missing_token: authenticate via /auth/login first, "
        "then use the CMS 'Kết nối GSC' button or pass ?sid=<your_session_id> "
        "to /gsc/oauth/start",
    )


def extract_sid(authorization: str, cookie_sid: str | None = None) -> str:
    return resolve_sid(authorization, cookie_sid)


async def cms_profile_from_sid(db: VipzoneDB, sid: str) -> dict[str, Any]:
    session = db.get_cms_session(sid)
    if not session:
        raise HTTPException(401, "invalid_cms_session")
    email = session.get("email")
    username = session.get("username") or ""
    # is_super resolved at OAuth time via GitHub repo permission; fall back to the
    # env username whitelist for legacy sessions issued before this field existed.
    is_super = bool(session.get("is_super")) or username_is_superadmin(username)
    return {
        "provider": session.get("provider") or "github",
        "email": email,
        "username": username,
        "name": session.get("name") or username,
        "avatar": session.get("avatar") or "",
        "is_super": is_super,
    }


async def cms_profile_from_session(
    db: VipzoneDB,
    authorization: str = "",
    *,
    cookie_sid: str | None = None,
) -> dict[str, Any]:
    sid = resolve_sid(authorization, cookie_sid)
    return await cms_profile_from_sid(db, sid)


async def github_token_from_session(
    db: VipzoneDB,
    authorization: str = "",
    *,
    cookie_sid: str | None = None,
) -> str:
    """Resolve the GitHub OAuth access_token stored server-side for this session.

    Used by the CMS repo routes (save-post / bulk-delete / categories) to commit
    on behalf of the authenticated author. Raises 401 if the session is missing or
    predates token persistence (legacy session → re-login refreshes it).
    """
    sid = resolve_sid(authorization, cookie_sid)
    session = db.get_cms_session(sid)
    if not session:
        raise HTTPException(401, "invalid_cms_session")
    token = session.get("access_token")
    if not token:
        raise HTTPException(401, "no_access_token")
    return token


async def session_dep(
    authorization: str = Header(default=""),
    zola_cms_sid: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> dict[str, Any]:
    from main import get_db

    return await cms_profile_from_session(get_db(), authorization, cookie_sid=zola_cms_sid)


def session_role_payload(db: VipzoneDB, profile: dict[str, Any]) -> dict[str, Any]:
    email = profile.get("email") or ""
    username = profile.get("username") or ""
    is_super = bool(profile.get("is_super"))
    vip_row = db.get_active_vip(email)
    role = resolve_role(is_super, is_vip=vip_row is not None)
    avatar = profile.get("avatar") or ""
    out: dict[str, Any] = {
        "authenticated": True,
        "provider": profile.get("provider") or "github",
        "email": profile.get("email"),
        "username": username,
        "name": profile.get("name") or username,
        "avatar": avatar,
        "avatar_url": avatar,
        "role": role,
        "is_super": is_super,
        "is_admin": is_admin(email, username),
    }
    if vip_row:
        out["vip_plan"] = vip_row.get("plan")
        out["vip_expires_at"] = vip_row.get("expires_at")
    return out


@router.get(
    "/auth/login",
    summary="Start GitHub OAuth",
    response_class=RedirectResponse,
    responses={307: {"description": "Redirect to GitHub authorize"}, 503: {"description": "OAuth not configured"}},
)
async def auth_login(return_to: str = "/tools/vipzone-admin/") -> RedirectResponse:
    if not _github_enabled():
        return redirect_with_error("github_disabled", return_to)
    if not GH_CLIENT_ID or not GH_CLIENT_SECRET:
        raise HTTPException(503, "oauth_not_configured")
    from main import get_db

    db = get_db()
    rt = normalize_return_to(return_to)
    state = secrets.token_urlsafe(24)
    db.save_oauth_state(state, rt)
    params = urlencode({
        "client_id": GH_CLIENT_ID,
        "scope": "read:user user:email public_repo",
        "state": state,
        "redirect_uri": f"{BACKEND_URL}/auth/callback",
        "allow_signup": "false",
    })
    return RedirectResponse(f"https://github.com/login/oauth/authorize?{params}")


@router.get(
    "/auth/callback",
    summary="GitHub OAuth callback",
    response_class=RedirectResponse,
    responses={307: {"description": "Redirect back to blog with #sid= session fragment"}},
)
async def auth_callback(code: str = "", state: str = "") -> RedirectResponse:
    from main import get_db

    if not code or not state:
        return redirect_with_error("missing_params")
    db = get_db()
    return_to = db.pop_oauth_state(state) or ""
    if not return_to:
        return redirect_with_error("invalid_state")

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            token_res = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": GH_CLIENT_ID,
                    "client_secret": GH_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": f"{BACKEND_URL}/auth/callback",
                },
            )
        except httpx.HTTPError:
            return redirect_with_error("github_unreachable", return_to)

        token_data = token_res.json() if token_res.status_code == 200 else {}
        access_token = token_data.get("access_token")
        if not access_token:
            return redirect_with_error("token_exchange_failed", return_to)

        gh_headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        try:
            emails_res = await client.get("https://api.github.com/user/emails", headers=gh_headers)
            user_res = await client.get("https://api.github.com/user", headers=gh_headers)
        except httpx.HTTPError:
            return redirect_with_error("github_unreachable", return_to)

        if emails_res.status_code != 200 or user_res.status_code != 200:
            return redirect_with_error("github_profile_fetch_failed", return_to)

        emails = emails_res.json()
        user = user_res.json()
        verified_emails = {
            (e.get("email") or "").lower()
            for e in emails
            if e.get("verified") and e.get("email")
        }
        username = user.get("login", "")
        matched_email = next(iter(verified_emails), None)
        is_super = await check_repo_superadmin(client, access_token, username)

    sid = db.create_cms_session(
        {
            "provider": "github",
            "email": matched_email,
            "username": username,
            "name": user.get("name") or username,
            "avatar": user.get("avatar_url", ""),
            "is_super": is_super,
            "is_superadmin": is_super,
            # GitHub OAuth token (scope read:user user:email public_repo) — kept
            # server-side in the session payload so the CMS routes can commit posts
            # to the repo. cms_profile_from_sid() whitelists fields, so this token
            # never leaks through /auth/me or any profile response.
            "access_token": access_token,
        },
        SESSION_TTL,
    )
    response = RedirectResponse(
        build_blog_url(return_to, fragment=f"sid={sid}", extra_query={"auth": "success"}),
    )
    attach_session_cookie(response, sid)
    return response


@router.get("/auth/config", summary="Which login providers are enabled")
async def auth_config() -> dict[str, Any]:
    """Tell the frontend which login gateways are enabled so it renders the
    right buttons. Never exposes a secret — only the provider + enable/configured
    flags."""
    return {
        "provider": AUTH_PROVIDER,
        "github": {
            "enabled": _github_enabled(),
            "configured": bool(GH_CLIENT_ID),
        },
        "google": {
            "enabled": _google_enabled(),
            "configured": bool(GOOGLE_CLIENT_ID),
        },
    }


@router.get(
    "/auth/google/start",
    summary="Start Google OAuth/OIDC",
    response_class=RedirectResponse,
    responses={307: {"description": "Redirect to Google consent screen"}},
)
async def auth_google_start(return_to: str = "/tools/vipzone-admin/") -> RedirectResponse:
    """Begin Google OAuth 2.0 / OIDC: create a CSRF state, store it, redirect the
    user to the Google consent screen. Scope is openid/email/profile only — no
    Gmail API scope."""
    if not _google_enabled():
        return redirect_with_error("google_disabled", return_to)
    if not GOOGLE_CLIENT_ID:
        return redirect_with_error("google_not_configured", return_to)
    from main import get_db

    db = get_db()
    rt = normalize_return_to(return_to)
    state = secrets.token_urlsafe(24)
    # Prefix 'g:' to keep Google states distinct from GitHub states in the store.
    db.save_oauth_state(f"g:{state}", rt)
    params = urlencode({
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
        "include_granted_scopes": "true",
    })
    return RedirectResponse(f"{GOOGLE_AUTH_ENDPOINT}?{params}")


@router.get(
    "/auth/google/callback",
    summary="Google OAuth callback",
    response_class=RedirectResponse,
    responses={307: {"description": "Redirect back to blog with #sid= session fragment"}},
)
async def auth_google_callback(
    code: str = "", state: str = "", error: str = ""
) -> RedirectResponse:
    """Google redirects here after consent.
    1. Validate state (CSRF)
    2. Exchange code → tokens (includes the id_token JWT)
    3. Verify id_token server-side via Google tokeninfo (signature + exp), then
       check aud + iss + email_verified ourselves
    4. Require the email be in GOOGLE_ADMIN_EMAILS
    5. Create the same opaque session as GitHub → redirect to blog with #sid."""
    if error:
        # User clicked "Cancel" on the consent screen → error=access_denied.
        return redirect_with_error("google_consent_denied")
    if not code or not state:
        return redirect_with_error("missing_params")
    from main import get_db

    db = get_db()
    return_to = db.pop_oauth_state(f"g:{state}") or ""
    if not return_to:
        return redirect_with_error("invalid_state")
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return redirect_with_error("google_not_configured", return_to)

    async with httpx.AsyncClient(timeout=15.0) as client:
        # ---- Exchange authorization code → tokens ----
        try:
            token_res = await client.post(
                GOOGLE_TOKEN_ENDPOINT,
                headers={"Accept": "application/json"},
                data={
                    "code": code,
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uri": GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )
        except httpx.HTTPError:
            return redirect_with_error("google_unreachable", return_to)

        if token_res.status_code != 200:
            return redirect_with_error("token_exchange_failed", return_to)

        id_token = (token_res.json() or {}).get("id_token")
        if not id_token:
            return redirect_with_error("token_exchange_failed", return_to)

        # ---- Verify id_token server-side via Google tokeninfo ----
        # tokeninfo checks the signature + expiry; we check aud/iss/email_verified.
        try:
            info_res = await client.get(
                GOOGLE_TOKENINFO_ENDPOINT, params={"id_token": id_token}
            )
        except httpx.HTTPError:
            return redirect_with_error("google_unreachable", return_to)

        if info_res.status_code != 200:
            return redirect_with_error("id_token_invalid", return_to)

        claims = info_res.json() or {}

    # ---- Validate claims (do NOT log claims — they contain email/sub) ----
    if claims.get("aud") != GOOGLE_CLIENT_ID:
        return redirect_with_error("id_token_aud_mismatch", return_to)
    if claims.get("iss") not in GOOGLE_ISS:
        return redirect_with_error("id_token_iss_mismatch", return_to)

    email = (claims.get("email") or "").strip().lower()
    if not email:
        return redirect_with_error("email_missing", return_to)
    if not _truthy(claims.get("email_verified")):
        return redirect_with_error("email_not_verified", return_to)
    if not _google_email_allowed(email):
        return redirect_with_error("access_denied", return_to)

    # Google admins on the allowlist get superadmin (same admin gate as GitHub).
    is_super = email in ADMIN_EMAILS or _google_email_allowed(email)
    sid = db.create_cms_session(
        {
            "provider": "google",
            "email": email,
            "sub": claims.get("sub", ""),
            "username": email.split("@")[0],
            "name": claims.get("name") or email,
            "avatar": claims.get("picture", ""),
            "is_super": is_super,
            "is_superadmin": is_super,
            # Google flow has no GitHub access_token — CMS repo-commit routes that
            # need it will 401 for Google sessions (documented limitation).
        },
        SESSION_TTL,
    )
    response = RedirectResponse(
        build_blog_url(return_to, fragment=f"sid={sid}", extra_query={"auth": "success"}),
    )
    attach_session_cookie(response, sid)
    return response


@router.get("/auth/me", summary="Current OAuth session", response_model=AuthMeResponse)
async def auth_me(profile: dict[str, Any] = Depends(session_dep)) -> dict[str, Any]:
    from main import get_db

    return session_role_payload(get_db(), profile)


@router.post("/auth/logout", summary="Invalidate OAuth session", response_model=LogoutResponse)
async def auth_logout(
    response: Response,
    authorization: str = Header(default=""),
    zola_cms_sid: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> dict[str, bool]:
    from main import get_db

    try:
        sid = resolve_sid(authorization, zola_cms_sid)
        get_db().delete_cms_session(sid)
    except HTTPException:
        pass
    clear_session_cookie(response)
    return {"ok": True}