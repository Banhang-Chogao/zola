"""GitHub OAuth + CMS session store for VIPZone API (self-hosted auth)."""

from __future__ import annotations

import os
import secrets
from typing import Any, Literal
from urllib.parse import parse_qsl, urlencode, urlparse, urlsplit, urlunsplit

import httpx
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from db import VipzoneDB
from github_repo import check_repo_superadmin
from roles import resolve_role, username_is_superadmin

SESSION_COOKIE_NAME = os.getenv("VIPZONE_SESSION_COOKIE", "zola_cms_sid")
CMS_V2_RETURN_TO = "https://seomoney.org/cms-v2/"
CMS_RETURN_TO_HOST = "seomoney.org"
CMS_GITHUB_RETURN_PATHS = ("/cms-v2", "/cms-v5", "/tools/infographic-hoa")

BLOG_URL = os.getenv("VIPZONE_BLOG_URL", "https://seomoney.org").rstrip("/")
_IS_PRODUCTION = os.getenv("ENVIRONMENT", "").strip().lower() == "production" or bool(
    os.getenv("RENDER")
)
BACKEND_URL = (
    os.getenv("PUBLIC_API_BASE")
    or os.getenv("AUTH_PUBLIC_BASE")
    or os.getenv("VIPZONE_BACKEND_URL")
    or os.getenv("BACKEND_URL")
    or (
        "https://api.seomoney.org"
        if _IS_PRODUCTION
        else "https://blog-vipzone-api.onrender.com"
    )
).rstrip("/")
GH_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID") or os.getenv("GH_CLIENT_ID", "")
GH_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET") or os.getenv("GH_CLIENT_SECRET", "")
# Admin session lifetime. Default 30 days so the editor stays logged in across
# days of work and across browser restarts — the persistent HttpOnly cookie
# (attach_session_cookie) uses this same value for Max-Age, and the server-side
# cms_sessions row expires at the same horizon, so cookie TTL == server TTL.
# Was 8h previously, which forced a re-login every working day. Override via the
# VIPZONE_SESSION_TTL env var (seconds). Clearing cookies/site data still logs
# out immediately regardless of TTL.
SESSION_TTL = int(os.getenv("VIPZONE_SESSION_TTL", str(30 * 24 * 3600)))

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

# ============= Debug logging control =============
# CMS_AUTH_DEBUG=true enables detailed OAuth callback traces.
# Default: false (production quiet). Set on Render when diagnosing auth issues.
CMS_AUTH_DEBUG = os.getenv("CMS_AUTH_DEBUG", "false").strip().lower() in {"true", "1", "yes"}

def _debug_log(msg: str) -> None:
    """Log only when CMS_AUTH_DEBUG is enabled. Never logs tokens, secrets, or session IDs."""
    if CMS_AUTH_DEBUG:
        print(msg)

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
# DEFAULT fallback: if neither GOOGLE_ADMIN_EMAILS nor ADMIN_EMAILS, allow ANY
# verified Google email from the admin's domain to unblock initial setup.
_google_admin_env = os.getenv("GOOGLE_ADMIN_EMAILS", "").strip()
if _google_admin_env:
    GOOGLE_ADMIN_EMAILS = {e.strip().lower() for e in _google_admin_env.split(",") if e.strip()}
elif ADMIN_EMAILS:
    GOOGLE_ADMIN_EMAILS = set(ADMIN_EMAILS)
else:
    # Fallback: no email allowlist set → log warning but do NOT allow all (security).
    # Owner MUST set GOOGLE_ADMIN_EMAILS or ADMIN_EMAILS on Render to enable Google login.
    GOOGLE_ADMIN_EMAILS = set()
    print("[cms_auth] WARNING: No email allowlist configured. Google login disabled.")
    print("[cms_auth] Set GOOGLE_ADMIN_EMAILS env var on Render to enable Google login.")

# ============= Comment auth (Google login for public commenters) =============
# A SEPARATE login surface from the admin/CMS Google flow. The admin flow keeps
# requiring GOOGLE_ADMIN_EMAILS; the comment flow admits ANY verified Google
# account (optionally restricted by COMMENTS_ALLOWED_DOMAINS) but assigns a
# strictly-limited `commenter` role that can NEVER reach the editor/CMS.
COMMENTS_AUTH_PROVIDER = os.getenv("COMMENTS_AUTH_PROVIDER", "google").strip().lower()
# Optional domain allowlist (comma-separated, e.g. "company.com"). Empty = any
# verified Google account may comment.
COMMENTS_ALLOWED_DOMAINS = {
    d.strip().lower().lstrip("@")
    for d in os.getenv("COMMENTS_ALLOWED_DOMAINS", "").split(",")
    if d.strip()
}
# Where a commenter returns to after Google login if no return_to is supplied.
COMMENTS_DEFAULT_RETURN = "/"

# Account-type markers stored in the session payload. `commenter` sessions are
# fenced out of every admin/CMS guard (defense-in-depth on top of is_admin/
# is_super already being false for them).
ACCOUNT_TYPE_ADMIN = "admin"
ACCOUNT_TYPE_COMMENTER = "commenter"


def _comment_email_allowed(email: str) -> bool:
    """Any verified Google email may comment unless a domain allowlist is set."""
    email = (email or "").strip().lower()
    if not email or "@" not in email:
        return False
    if not COMMENTS_ALLOWED_DOMAINS:
        return True
    return email.rsplit("@", 1)[-1] in COMMENTS_ALLOWED_DOMAINS


def is_commenter_only(profile: dict[str, Any] | None) -> bool:
    """True for a public commenter session (must be denied admin/CMS surfaces)."""
    if not profile:
        return False
    return (profile.get("account_type") or "") == ACCOUNT_TYPE_COMMENTER

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
    # Normalized account type for the comment system: "admin" (can moderate +
    # reach CMS) or "commenter" (comment-only, never CMS). Anonymous callers get a
    # 401 from /auth/me, so the frontend maps "no session" → anonymous itself.
    account_type: Literal["admin", "commenter"] = "commenter"
    comment_role: Literal["admin", "commenter"] = "commenter"


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
    """Normalize and validate return_to URL (same-origin only).

    Preserves fragment (#comments, #...) for safe anchors.
    Validates: no cross-site redirects, only internal paths allowed.
    """
    rt = (return_to or "").strip()
    if not rt:
        return "/editor/"

    # Extract fragment and validate it.
    fragment = ""
    if "#" in rt:
        rt, frag = rt.split("#", 1)
        # Only allow safe anchors: #comments (for comment login) or empty.
        # Prevent anchors to sensitive routes like #admin, #editor, etc.
        if frag in {"comments", "comment"}:
            fragment = "#" + frag
        # Silently drop unsafe fragments (e.g., #admin, #sidebar, malicious anchors).

    if rt.startswith("http://") or rt.startswith("https://"):
        parsed = urlparse(rt)
        blog = urlparse(BLOG_URL)
        if parsed.netloc != blog.netloc:
            return "/editor/"
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        return path + fragment

    if rt.startswith("/"):
        return rt + fragment

    return "/editor/"


def normalize_github_return_to(return_to: str) -> str:
    """Return an absolute allowlisted CMS URL for the GitHub OAuth round trip."""
    rt = (return_to or "").strip()
    if not rt:
        return CMS_V2_RETURN_TO

    parsed = urlparse(rt)
    if (
        parsed.scheme == "https"
        and parsed.netloc == CMS_RETURN_TO_HOST
        and parsed.hostname == CMS_RETURN_TO_HOST
        and any(parsed.path == base or parsed.path.startswith(base + "/") for base in CMS_GITHUB_RETURN_PATHS)
    ):
        return parsed._replace(fragment="").geturl()

    if (
        rt.startswith("/")
        and not rt.startswith("//")
        and any(parsed.path == base or parsed.path.startswith(base + "/") for base in CMS_GITHUB_RETURN_PATHS)
    ):
        return f"https://{CMS_RETURN_TO_HOST}{rt}"

    return CMS_V2_RETURN_TO


def github_success_return_to(return_to: str) -> str:
    """Build the allowlisted callback target and append success as a query."""
    safe_url = normalize_github_return_to(return_to)
    parsed = urlsplit(safe_url)
    query = parse_qsl(parsed.query, keep_blank_values=True)
    query.append(("success", "1"))
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), ""))


def require_github_oauth_env() -> None:
    """Fail clearly without exposing values or unrelated configuration."""
    missing = []
    if not GH_CLIENT_ID:
        missing.append("GITHUB_CLIENT_ID")
    if not GH_CLIENT_SECRET:
        missing.append("GITHUB_CLIENT_SECRET")
    if missing:
        raise HTTPException(500, detail=missing)


def build_blog_url(
    return_to: str,
    fragment: str = "",
    *,
    extra_query: dict[str, str] | None = None,
) -> str:
    rt = normalize_return_to(return_to)
    # Extract any fragment that normalize_return_to() already appended.
    fragment_from_return_to = ""
    if "#" in rt:
        rt, fragment_from_return_to = rt.split("#", 1)
        fragment_from_return_to = "#" + fragment_from_return_to

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
    # Prefer explicit fragment param; fall back to fragment from return_to.
    final_fragment = fragment or fragment_from_return_to
    return url + (f"#{final_fragment}" if final_fragment else "")


def attach_session_cookie(response: Response, sid: str) -> None:
    """Set a secure same-site production cookie; retain cross-site dev fallback."""
    api_host = (urlparse(BACKEND_URL).hostname or "").lower()
    same_site_api = api_host == CMS_RETURN_TO_HOST or api_host.endswith(
        f".{CMS_RETURN_TO_HOST}"
    )
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=sid,
        max_age=SESSION_TTL,
        httponly=True,
        secure=_IS_PRODUCTION or BACKEND_URL.startswith("https://"),
        samesite="lax" if same_site_api else "none",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    api_host = (urlparse(BACKEND_URL).hostname or "").lower()
    same_site_api = api_host == CMS_RETURN_TO_HOST or api_host.endswith(
        f".{CMS_RETURN_TO_HOST}"
    )
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        secure=_IS_PRODUCTION or BACKEND_URL.startswith("https://"),
        samesite="lax" if same_site_api else "none",
    )


def redirect_with_error(error: str, return_to: str = "/editor/") -> RedirectResponse:
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
        # Carried through so admin/CMS guards can fence out commenter sessions
        # (defense-in-depth; is_admin/is_super are already false for them).
        "account_type": session.get("account_type") or "",
        "sub": session.get("sub") or "",
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
    admin_flag = is_admin(email, username) or is_super
    # A commenter is anyone authenticated who is NOT an admin. Admins keep full
    # moderation rights. This normalized role is what the comment widget reads.
    comment_role = ACCOUNT_TYPE_ADMIN if admin_flag else ACCOUNT_TYPE_COMMENTER
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
        "account_type": comment_role,
        "comment_role": comment_role,
    }
    if vip_row:
        out["vip_plan"] = vip_row.get("plan")
        out["vip_expires_at"] = vip_row.get("expires_at")
    return out


@router.get(
    "/auth/login",
    summary="Start GitHub OAuth",
    response_class=RedirectResponse,
    responses={302: {"description": "Redirect to GitHub authorize"}, 500: {"description": "OAuth environment missing"}},
)
async def auth_login(return_to: str = CMS_V2_RETURN_TO) -> RedirectResponse:
    require_github_oauth_env()
    from main import get_db

    db = get_db()
    rt = normalize_github_return_to(return_to)
    state = secrets.token_urlsafe(24)
    db.save_oauth_state(state, rt)
    params = urlencode({
        "client_id": GH_CLIENT_ID,
        "scope": "read:user user:email public_repo",
        "state": state,
        "redirect_uri": f"{BACKEND_URL}/auth/callback",
        "allow_signup": "false",
    })
    return RedirectResponse(
        f"https://github.com/login/oauth/authorize?{params}",
        status_code=302,
    )


@router.get(
    "/auth/callback",
    summary="GitHub OAuth callback",
    response_class=RedirectResponse,
    responses={
        302: {"description": "Set the session cookie and redirect to return_to"},
        500: {"description": "OAuth environment missing"},
    },
)
async def auth_callback(code: str = "", state: str = "") -> RedirectResponse:
    from main import get_db

    require_github_oauth_env()
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
    # Include #sid= in the redirect fragment so the frontend can store the sid in
    # localStorage/sessionStorage and use Authorization: Bearer <sid> for all API
    # calls, rather than relying solely on the HttpOnly cookie (which can fail under
    # cross-origin restrictions or third-party cookie blocking).  The Google callback
    # already uses this pattern — this makes the GitHub flow consistent.
    safe_url = normalize_github_return_to(return_to)
    parsed = urlsplit(safe_url)
    query = parse_qsl(parsed.query, keep_blank_values=True)
    query.append(("success", "1"))
    redirect_url = urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, urlencode(query), f"sid={sid}")
    )
    response = RedirectResponse(redirect_url, status_code=302)
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
async def auth_google_start(return_to: str = "/editor/") -> RedirectResponse:
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
    "/auth/comment/start",
    summary="Start Google OAuth/OIDC for a public commenter",
    response_class=RedirectResponse,
    responses={307: {"description": "Redirect to Google consent screen"}},
)
async def auth_comment_start(return_to: str = COMMENTS_DEFAULT_RETURN) -> RedirectResponse:
    """Begin Google login for COMMENTING (not admin/CMS).

    Same OIDC client + redirect_uri as the admin flow (openid/email/profile only,
    no Gmail scope) but the state is tagged ``gc:`` so the shared callback knows to
    admit any verified Google account as a ``commenter`` instead of requiring the
    admin allowlist. Reuses the existing Google OAuth session boundaries."""
    if COMMENTS_AUTH_PROVIDER != "google":
        return redirect_with_error("comments_provider_disabled", return_to)
    if not GOOGLE_CLIENT_ID:
        return redirect_with_error("google_not_configured", return_to)
    from main import get_db

    db = get_db()
    rt = normalize_return_to(return_to)
    state = secrets.token_urlsafe(24)
    # 'gc:' prefix = Google COMMENT login (distinct from admin 'g:' states).
    db.save_oauth_state(f"gc:{state}", rt)
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
    # The callback is shared by the admin flow (state 'g:') and the comment flow
    # (state 'gc:'). Whichever state matches decides the mode + authorization rule.
    return_to = db.pop_oauth_state(f"g:{state}") or ""
    mode = "admin"
    if not return_to:
        return_to = db.pop_oauth_state(f"gc:{state}") or ""
        mode = "comment"
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

    is_admin_email = _google_email_allowed(email)
    # Debug logging for OAuth flow (safe — no tokens/secrets, only domains/counts/status)
    email_domain = email.split("@")[1] if "@" in email else "unknown"
    email_normalized = email.lower().strip()
    google_allowlist_count = len(GOOGLE_ADMIN_EMAILS) if GOOGLE_ADMIN_EMAILS else 0
    _debug_log(f"[cms_auth] Google OAuth callback START: mode={mode}")
    _debug_log(f"[cms_auth]   email_domain={email_domain} email_normalized={email_normalized[:3]}***@{email_domain}")
    _debug_log(f"[cms_auth]   GOOGLE_ADMIN_EMAILS configured={bool(GOOGLE_ADMIN_EMAILS)} count={google_allowlist_count}")
    _debug_log(f"[cms_auth]   email_allowed={is_admin_email}")

    # If GOOGLE_ADMIN_EMAILS is empty (fallback failed), block the login with a clear error.
    if not GOOGLE_ADMIN_EMAILS and not mode == "comment":
        _debug_log(f"[cms_auth] Google login blocked: admin mode requires email allowlist. Email domain: {email_domain}")
        return redirect_with_error("google_not_configured", return_to)

    if mode == "comment":
        # Comment login: admit any verified Google account (or only an allowed
        # domain when COMMENTS_ALLOWED_DOMAINS is set). An allowlisted admin who
        # happens to log in here still gets admin rights; everyone else is a
        # strictly comment-only account that can NEVER reach the editor/CMS.
        comment_domain_allowed = _comment_email_allowed(email)
        if not is_admin_email and not comment_domain_allowed:
            _debug_log(f"[cms_auth]   comment_domain_check=failed email_domain={email_domain}")
            return redirect_with_error("comment_domain_not_allowed", return_to)
        is_super = is_admin_email
        account_type = ACCOUNT_TYPE_ADMIN if is_admin_email else ACCOUNT_TYPE_COMMENTER
        _debug_log(f"[cms_auth]   mode=comment account_type={account_type} is_super={is_super}")
        session_payload = {
            "provider": "google",
            "email": email,
            "sub": claims.get("sub", ""),
            # Commenters get NO username → can never collide with ADMIN_USERNAMES
            # in is_admin(). Admins keep their email local-part for continuity.
            "username": email.split("@")[0] if is_admin_email else "",
            "name": claims.get("name") or email.split("@")[0],
            "avatar": claims.get("picture", ""),
            "is_super": is_super,
            "is_superadmin": is_super,
            "account_type": account_type,
        }
    else:
        # Admin/CMS login — UNCHANGED: the email MUST be on the admin allowlist.
        if not is_admin_email:
            _debug_log(f"[cms_auth]   mode=admin email_allowed=false → access_denied")
            return redirect_with_error("access_denied", return_to)
        is_super = email in ADMIN_EMAILS or is_admin_email
        _debug_log(f"[cms_auth]   mode=admin email_allowed=true is_super={is_super}")
        session_payload = {
            "provider": "google",
            "email": email,
            "sub": claims.get("sub", ""),
            "username": email.split("@")[0],
            "name": claims.get("name") or email,
            "avatar": claims.get("picture", ""),
            "is_super": is_super,
            "is_superadmin": is_super,
            "account_type": ACCOUNT_TYPE_ADMIN,
            # Google flow has no GitHub access_token — CMS repo-commit routes that
            # need it will 401 for Google sessions (documented limitation).
        }

    sid = db.create_cms_session(session_payload, SESSION_TTL)
    session_created = bool(sid)
    _debug_log(f"[cms_auth]   session_created={session_created} sid_length={len(sid) if sid else 0}")

    # Extract safe fragment from return_to (e.g., #comments) to preserve in redirect.
    safe_fragment = ""
    if return_to and "#" in return_to:
        _, frag = return_to.split("#", 1)
        if frag in {"comments", "comment"}:
            safe_fragment = frag
    # Build fragment: sid= always included for session; append safe_fragment if present.
    fragment_value = f"sid={sid}"
    if safe_fragment:
        fragment_value += f"&{safe_fragment}"

    redirect_url = build_blog_url(return_to, fragment=fragment_value, extra_query={"auth": "success"})
    response = RedirectResponse(redirect_url)
    attach_session_cookie(response, sid)
    _debug_log(f"[cms_auth]   cookie_attached=True cookie_name={SESSION_COOKIE_NAME} max_age={SESSION_TTL}")
    _debug_log(f"[cms_auth] Google OAuth callback COMPLETE: redirect_url={redirect_url}")
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
