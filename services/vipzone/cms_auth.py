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
from roles import build_identity, username_is_superadmin

SESSION_COOKIE_NAME = os.getenv("VIPZONE_SESSION_COOKIE", "zola_cms_sid")

BLOG_URL = os.getenv("VIPZONE_BLOG_URL", "https://banhang-chogao.github.io/zola").rstrip("/")
BACKEND_URL = os.getenv(
    "VIPZONE_BACKEND_URL",
    os.getenv("BACKEND_URL", "https://blog-vipzone-api.onrender.com"),
).rstrip("/")
GH_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID") or os.getenv("GH_CLIENT_ID", "")
GH_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET") or os.getenv("GH_CLIENT_SECRET", "")
SESSION_TTL = int(os.getenv("VIPZONE_SESSION_TTL", str(8 * 3600)))

_BLOG_BASE_PATH = urlparse(BLOG_URL).path.rstrip("/")

router = APIRouter(tags=["auth"])


class AuthMeResponse(BaseModel):
    email: str | None = None
    username: str = ""
    name: str = ""
    avatar: str = ""
    role: Literal["user", "vip", "admin", "superadmin"] = "user"
    is_super: bool = False
    is_admin: bool = False
    permissions: dict[str, bool] = {}
    vip_plan: str | None = None
    vip_expires_at: str | None = None


class LogoutResponse(BaseModel):
    ok: bool = True


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
    raise HTTPException(401, "missing_token")


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


async def session_dep(
    authorization: str = Header(default=""),
    zola_cms_sid: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> dict[str, Any]:
    from main import get_db

    return await cms_profile_from_session(get_db(), authorization, cookie_sid=zola_cms_sid)


def session_role_payload(db: VipzoneDB, profile: dict[str, Any]) -> dict[str, Any]:
    """Thin delegate to the SSoT — /auth/me returns the SAME identity as /api/vipzone/me."""
    email = profile.get("email") or ""
    return build_identity(profile, vip_row=db.get_active_vip(email))


@router.get(
    "/auth/login",
    summary="Start GitHub OAuth",
    response_class=RedirectResponse,
    responses={307: {"description": "Redirect to GitHub authorize"}, 503: {"description": "OAuth not configured"}},
)
async def auth_login(return_to: str = "/tools/vipzone-admin/") -> RedirectResponse:
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
            "email": matched_email,
            "username": username,
            "name": user.get("name") or username,
            "avatar": user.get("avatar_url", ""),
            "is_super": is_super,
            "is_superadmin": is_super,
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