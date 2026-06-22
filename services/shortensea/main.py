"""
ShortenSEA — S-DNA short URL manager API.

Endpoints:
  Auth (open GitHub OAuth — any verified user):
    GET  /auth/login, /auth/callback, /auth/me, POST /auth/logout

  Links:
    GET/POST /api/shortensea/links
    PUT/DELETE /api/shortensea/links/{link_id}
    GET /api/shortensea/resolve/{slug}  (public, for 404 redirect)
    GET /s/{slug}                       (public redirect + click log)

  Account:
    GET  /api/shortensea/account
    POST /api/shortensea/redeem-code

  Insights:
    GET  /api/shortensea/insights

  Admin:
    GET  /api/shortensea/admin/codes
    POST /api/shortensea/admin/codes
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode, urlparse, urlunparse

import httpx
from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from db import ShortenDB

# ============= Config =============
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("SHORTENSEA_CORS_ORIGIN", "https://seomoney.org,https://www.seomoney.org").split(",")
    if o.strip()
]
BLOG_URL = os.getenv("SHORTENSEA_BLOG_URL", "https://seomoney.org").rstrip("/")
BACKEND_URL = os.getenv("SHORTENSEA_BACKEND_URL", "http://localhost:8790").rstrip("/")
SHORTENSEA_AUTH_URL = os.getenv("SHORTENSEA_AUTH_URL", "https://blog-vipzone-api.onrender.com").rstrip("/")
GH_CLIENT_ID = os.getenv("GH_CLIENT_ID", "")
GH_CLIENT_SECRET = os.getenv("GH_CLIENT_SECRET", "")
SESSION_TTL = int(os.getenv("SHORTENSEA_SESSION_TTL", "86400"))
DB_PATH = os.getenv("SHORTENSEA_DB_PATH", "")
MOMO_LINK = os.getenv(
    "MOMO_PAYMENT_LINK",
    "https://me.momo.vn/G5T1CDFRuJFWfBCDiK/y5eVvzz2nlXXeEP",
)
SHORT_DOMAIN = os.getenv("SHORTENSEA_DOMAIN", "seomoney.org")

ADMIN_EMAILS = {
    e.strip().lower()
    for e in os.getenv("ADMIN_EMAILS", "292648126+Banhang-Chogao@users.noreply.github.com").split(",")
    if e.strip()
}
ADMIN_USERNAMES = {
    u.strip().lower()
    for u in os.getenv("ADMIN_USERNAMES", "banhang-chogao").split(",")
    if u.strip()
}

PLAN_LIMITS: dict[str, dict[str, Any]] = {
    "free": {
        "links_per_month": 10,
        "custom_halves": 0,
        "qr": False,
        "tags": False,
        "utm": False,
        "expiration": False,
        "basic_insights": True,
        "advanced_insights": False,
        "label": "Miễn phí",
    },
    "locked_premium": {
        "links_per_month": 10,
        "custom_halves": 0,
        "qr": False,
        "tags": False,
        "utm": False,
        "expiration": False,
        "basic_insights": True,
        "advanced_insights": False,
        "label": "Premium đã hết hạn (khóa 1 ngày)",
    },
    "monthly": {
        "links_per_month": 100,
        "custom_halves": 10,
        "qr": True,
        "tags": True,
        "utm": False,
        "expiration": False,
        "basic_insights": True,
        "advanced_insights": False,
        "label": "Gói Tháng",
    },
    "yearly": {
        "links_per_month": 1000,
        "custom_halves": 50,
        "qr": True,
        "tags": True,
        "utm": True,
        "expiration": True,
        "basic_insights": True,
        "advanced_insights": True,
        "label": "Gói Năm",
    },
    "super": {
        "links_per_month": 999999,
        "custom_halves": 999999,
        "qr": True,
        "tags": True,
        "utm": True,
        "expiration": True,
        "basic_insights": True,
        "advanced_insights": True,
        "label": "Super VIP",
    },
}

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{2,48}$", re.IGNORECASE)
URL_RE = re.compile(r"^https?://", re.IGNORECASE)

_pending_codes: dict[str, str] = {}
_BLOG_BASE_PATH = urlparse(BLOG_URL).path.rstrip("/")

app = FastAPI(title="ShortenSEA API", version="1.0.0", docs_url=None, redoc_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS + ["http://127.0.0.1:1111", "http://localhost:1111"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


def get_db() -> ShortenDB:
    return ShortenDB(DB_PATH or None)


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.strip().upper().encode()).hexdigest()


def _generate_code() -> str:
    return secrets.token_hex(4).upper()


def _generate_slug() -> str:
    return secrets.token_urlsafe(6).replace("-", "").replace("_", "")[:8].lower()


def _is_super(email: str | None, username: str | None) -> bool:
    if username and username.lower() in ADMIN_USERNAMES:
        return True
    if email and email.lower() in ADMIN_EMAILS:
        return True
    return False


def _extract_sid(authorization: str) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing_token")
    sid = authorization[7:].strip()
    if not sid:
        raise HTTPException(401, "missing_token")
    return sid


def _require_user(authorization: str = Header(default="")) -> dict[str, Any]:
    sid = _extract_sid(authorization)
    db = get_db()
    session = db.get_session(sid)
    if not session:
        raise HTTPException(401, "invalid_session")
    user = db.reset_monthly_counter_if_needed(session)
    return user


def _require_admin(user: dict[str, Any]) -> None:
    if not user.get("is_super"):
        raise HTTPException(403, "admin_only")


def _effective_plan(user: dict[str, Any]) -> str:
    if user.get("is_super"):
        return "super"
    return user.get("plan") or "free"


def _plan_limits(user: dict[str, Any]) -> dict[str, Any]:
    return PLAN_LIMITS.get(_effective_plan(user), PLAN_LIMITS["free"])


def _user_payload(user: dict[str, Any]) -> dict[str, Any]:
    plan = _effective_plan(user)
    limits = _plan_limits(user)
    remaining_links = max(0, limits["links_per_month"] - (user.get("links_month_count") or 0))
    remaining_halves = max(0, limits["custom_halves"] - (user.get("custom_halves_used") or 0))
    return {
        "user_id": user["user_id"],
        "email": user.get("email"),
        "username": user.get("username"),
        "name": user.get("name"),
        "avatar": user.get("avatar"),
        "plan": plan,
        "plan_label": limits["label"],
        "is_super": bool(user.get("is_super")),
        "plan_expires_at": user.get("plan_expires_at"),
        "locked_until": user.get("locked_until"),
        "remaining_links": remaining_links,
        "remaining_custom_halves": remaining_halves,
        "limits": limits,
        "momo_payment_link": MOMO_LINK,
        "short_domain": SHORT_DOMAIN,
    }


def _parse_ua(ua: str) -> tuple[str, str]:
    ua_l = (ua or "").lower()
    device = "desktop"
    if "mobile" in ua_l or "android" in ua_l or "iphone" in ua_l:
        device = "mobile"
    elif "tablet" in ua_l or "ipad" in ua_l:
        device = "tablet"

    browser = "other"
    if "edg/" in ua_l or "edge" in ua_l:
        browser = "Edge"
    elif "chrome" in ua_l and "chromium" not in ua_l:
        browser = "Chrome"
    elif "firefox" in ua_l:
        browser = "Firefox"
    elif "safari" in ua_l and "chrome" not in ua_l:
        browser = "Safari"
    elif "opera" in ua_l or "opr/" in ua_l:
        browser = "Opera"
    return device, browser


def _append_utm(url: str, link: dict[str, Any]) -> str:
    parsed = urlparse(url)
    params: dict[str, str] = {}
    if link.get("utm_source"):
        params["utm_source"] = link["utm_source"]
    if link.get("utm_medium"):
        params["utm_medium"] = link["utm_medium"]
    if link.get("utm_campaign"):
        params["utm_campaign"] = link["utm_campaign"]
    if link.get("utm_term"):
        params["utm_term"] = link["utm_term"]
    if link.get("utm_content"):
        params["utm_content"] = link["utm_content"]
    if not params:
        return url
    existing = parsed.query
    extra = urlencode(params)
    query = f"{existing}&{extra}" if existing else extra
    return urlunparse(parsed._replace(query=query))


def _link_payload(link: dict[str, Any], base_url: str = BLOG_URL) -> dict[str, Any]:
    tags = json.loads(link.get("tags") or "[]")
    return {
        "link_id": link["link_id"],
        "slug": link["slug"],
        "short_url": f"{base_url}/s/{link['slug']}",
        "destination_url": link["destination_url"],
        "title": link.get("title") or "",
        "tags": tags,
        "domain": link.get("domain"),
        "utm_source": link.get("utm_source"),
        "utm_medium": link.get("utm_medium"),
        "utm_campaign": link.get("utm_campaign"),
        "utm_term": link.get("utm_term"),
        "utm_content": link.get("utm_content"),
        "expires_at": link.get("expires_at"),
        "qr_enabled": bool(link.get("qr_enabled")),
        "status": link.get("status"),
        "click_count": link.get("click_count") or 0,
        "created_at": link.get("created_at"),
        "updated_at": link.get("updated_at"),
    }


def _build_blog_url(return_to: str = "/", fragment: str = "") -> str:
    """Compose blog URL, strip duplicate base path (e.g. /zola/zola/...)."""
    rt = return_to or "/"
    if _BLOG_BASE_PATH and rt.startswith(_BLOG_BASE_PATH + "/"):
        rt = rt[len(_BLOG_BASE_PATH):]
    if _BLOG_BASE_PATH and rt == _BLOG_BASE_PATH:
        rt = "/"
    if not rt.startswith("/"):
        rt = "/" + rt
    url = f"{BLOG_URL}{rt}"
    if fragment:
        url += f"#{fragment}"
    return url


def _redirect_with_error(err: str, return_to: str = "/shortensea/") -> RedirectResponse:
    base = _build_blog_url(return_to)
    sep = "&" if "?" in base else "?"
    return RedirectResponse(f"{base}{sep}auth_error={err}")


# ============= Models =============
class LinkIn(BaseModel):
    destination_url: str
    slug: str = ""
    title: str = ""
    tags: list[str] = Field(default_factory=list)
    domain: str = ""
    qr_enabled: bool = False
    utm_source: str = ""
    utm_medium: str = ""
    utm_campaign: str = ""
    utm_term: str = ""
    utm_content: str = ""
    expires_at: str = ""


class LinkUpdate(BaseModel):
    destination_url: str | None = None
    title: str | None = None
    tags: list[str] | None = None
    status: str | None = None
    qr_enabled: bool | None = None
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_term: str | None = None
    utm_content: str | None = None
    expires_at: str | None = None


class RedeemIn(BaseModel):
    approve_code: str


class CodeIn(BaseModel):
    plan_type: str
    email: str = ""
    user_id: str = ""
    code: str = ""


class PaymentRequestIn(BaseModel):
    email: str
    plan_type: str
    payment_note: str = ""


class AdminOverrideIn(BaseModel):
    plan: str
    days: int | None = None
    is_super: bool | None = None


# ============= Health =============
@app.get("/")
def health() -> dict[str, Any]:
    return {
        "service": "shortensea",
        "status": "ok",
        "blog_url": BLOG_URL,
        "momo_configured": bool(MOMO_LINK),
    }


# ============= OAuth =============
@app.get("/auth/login")
async def auth_login(return_to: str = "/shortensea/"):
    if not GH_CLIENT_ID or not GH_CLIENT_SECRET:
        raise HTTPException(503, "oauth_not_configured")
    if not return_to.startswith("/"):
        return_to = "/shortensea/"
    state = secrets.token_urlsafe(24)
    get_db().save_oauth_state(state, return_to)
    params = urlencode({
        "client_id": GH_CLIENT_ID,
        "scope": "read:user user:email",
        "state": state,
        "redirect_uri": f"{BACKEND_URL}/auth/callback",
    })
    return RedirectResponse(f"https://github.com/login/oauth/authorize?{params}")


@app.get("/auth/callback")
async def auth_callback(code: str = "", state: str = ""):
    if not code or not state:
        return _redirect_with_error("missing_params")
    return_to = get_db().pop_oauth_state(state) or ""
    if not return_to:
        return _redirect_with_error("invalid_state", "/shortensea/")

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
            return _redirect_with_error("github_unreachable", return_to)

        token_data = token_res.json() if token_res.status_code == 200 else {}
        access_token = token_data.get("access_token")
        if not access_token:
            return _redirect_with_error("token_exchange_failed", return_to)

        gh_headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        try:
            emails_res = await client.get("https://api.github.com/user/emails", headers=gh_headers)
            user_res = await client.get("https://api.github.com/user", headers=gh_headers)
        except httpx.HTTPError:
            return _redirect_with_error("github_unreachable", return_to)

        if emails_res.status_code != 200 or user_res.status_code != 200:
            return _redirect_with_error("github_profile_fetch_failed", return_to)

        emails = emails_res.json()
        user = user_res.json()
        verified = [
            (e.get("email") or "").lower()
            for e in emails
            if e.get("verified") and e.get("email")
        ]
        primary_email = verified[0] if verified else None
        username = user.get("login", "")
        is_super = _is_super(primary_email, username)

    db = get_db()
    db_user = db.get_or_create_user(
        username=username,
        email=primary_email,
        name=user.get("name") or username,
        avatar=user.get("avatar_url", ""),
        is_super=is_super,
    )
    sid = db.create_session(db_user["user_id"], SESSION_TTL)
    return RedirectResponse(_build_blog_url(return_to, fragment=f"ssid={sid}"))


@app.get("/auth/me")
def auth_me(authorization: str = Header(default="")):
    user = _require_user(authorization)
    return _user_payload(user)


@app.post("/auth/cms-bridge")
async def cms_bridge(authorization: str = Header(default="")):
    """Exchange valid CMS OAuth session for ShortenSEA session (admin whitelist)."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing_token")
    async with httpx.AsyncClient(timeout=12.0) as client:
        try:
            res = await client.get(
                f"{SHORTENSEA_AUTH_URL}/auth/me",
                headers={"Authorization": authorization},
            )
        except httpx.HTTPError:
            raise HTTPException(503, "cms_unreachable") from None
    if res.status_code != 200:
        raise HTTPException(401, "invalid_cms_session")
    profile = res.json()
    is_super = _is_super(profile.get("email"), profile.get("username"))
    db = get_db()
    db_user = db.get_or_create_user(
        username=profile.get("username", ""),
        email=profile.get("email"),
        name=profile.get("name") or profile.get("username", ""),
        avatar=profile.get("avatar", ""),
        is_super=is_super,
    )
    sid = db.create_session(db_user["user_id"], SESSION_TTL)
    fresh = db.get_user(db_user["user_id"]) or db_user
    return {"session_id": sid, "account": _user_payload(fresh)}


@app.post("/auth/logout")
def auth_logout(authorization: str = Header(default="")):
    try:
        sid = _extract_sid(authorization)
    except HTTPException:
        return {"ok": True}
    get_db().delete_session(sid)
    return {"ok": True}


@app.post("/api/shortensea/guest/session")
def guest_session():
    """Create anonymous guest session for public free-tier link creation."""
    db = get_db()
    guest = db.create_guest_user()
    sid = db.create_session(guest["user_id"], SESSION_TTL)
    return {"session_id": sid, "account": _user_payload(guest)}


# ============= Account =============
@app.get("/api/shortensea/account")
def get_account(authorization: str = Header(default="")):
    user = _require_user(authorization)
    return _user_payload(user)


@app.post("/api/shortensea/redeem-code")
def redeem_code(body: RedeemIn, authorization: str = Header(default="")):
    user = _require_user(authorization)
    code = body.approve_code.strip().upper()
    if not re.fullmatch(r"[A-Z0-9]{4,64}", code):
        raise HTTPException(400, "invalid_code_format")

    db = get_db()
    row = db.redeem_code(_hash_code(code), user)
    if not row:
        raise HTTPException(403, "invalid_or_used_code")

    plan = row["plan_type"]
    days = 30 if plan == "monthly" else 365 if plan == "yearly" else 30
    if row.get("email") and not user.get("email"):
        db.set_user_email(user["user_id"], row["email"])
    updated = db.upgrade_user(user["user_id"], plan, days)
    return {"ok": True, "account": _user_payload(updated)}


@app.post("/api/shortensea/payment-request")
def payment_request(body: PaymentRequestIn, authorization: str = Header(default="")):
    """Submit MoMo payment note — admin verifies manually (no auto-confirm)."""
    if body.plan_type not in ("monthly", "yearly"):
        raise HTTPException(400, "invalid_plan_type")
    email = body.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(400, "invalid_email")

    user_id = None
    if authorization.startswith("Bearer "):
        try:
            sid = _extract_sid(authorization)
            session = get_db().get_session(sid)
            if session:
                user_id = session["user_id"]
                get_db().set_user_email(user_id, email)
        except HTTPException:
            pass

    rid = get_db().insert_payment_request({
        "user_id": user_id,
        "email": email,
        "plan_type": body.plan_type,
        "payment_note": body.payment_note,
    })
    return {"ok": True, "request_id": rid, "message": "Đã gửi yêu cầu. Admin sẽ xác minh và gửi approve code qua email."}


# ============= Links =============
@app.get("/api/shortensea/links")
def list_links(authorization: str = Header(default="")):
    user = _require_user(authorization)
    db = get_db()
    links = db.list_links(user["user_id"])
    return [_link_payload(l) for l in links]


@app.post("/api/shortensea/links")
def create_link(body: LinkIn, authorization: str = Header(default="")):
    user = _require_user(authorization)
    limits = _plan_limits(user)
    user = get_db().reset_monthly_counter_if_needed(user)

    if (user.get("links_month_count") or 0) >= limits["links_per_month"]:
        raise HTTPException(403, "monthly_link_limit_reached")

    dest = body.destination_url.strip()
    if not URL_RE.match(dest):
        raise HTTPException(400, "invalid_destination_url")

    custom = bool(body.slug.strip())
    slug = body.slug.strip().lower() if custom else _generate_slug()

    if custom:
        if not limits["custom_halves"] or (user.get("custom_halves_used") or 0) >= limits["custom_halves"]:
            raise HTTPException(403, "custom_half_limit_reached")
        if not SLUG_RE.match(slug):
            raise HTTPException(400, "invalid_slug_format")

    if body.qr_enabled and not limits["qr"]:
        raise HTTPException(403, "qr_not_allowed")

    if body.tags and not limits["tags"]:
        raise HTTPException(403, "tags_not_allowed")

    utm_fields = [body.utm_source, body.utm_medium, body.utm_campaign, body.utm_term, body.utm_content]
    if any(utm_fields) and not limits["utm"]:
        raise HTTPException(403, "utm_not_allowed")

    if body.expires_at and not limits["expiration"]:
        raise HTTPException(403, "expiration_not_allowed")

    db = get_db()
    if db.slug_exists(slug):
        raise HTTPException(409, "slug_conflict")

    link = db.insert_link({
        "user_id": user["user_id"],
        "slug": slug,
        "destination_url": dest,
        "title": body.title.strip() or None,
        "tags": [t.strip() for t in body.tags if t.strip()],
        "domain": body.domain.strip() or SHORT_DOMAIN,
        "qr_enabled": body.qr_enabled,
        "utm_source": body.utm_source or None,
        "utm_medium": body.utm_medium or None,
        "utm_campaign": body.utm_campaign or None,
        "utm_term": body.utm_term or None,
        "utm_content": body.utm_content or None,
        "expires_at": body.expires_at or None,
        "custom_slug": custom,
    })
    return _link_payload(link)


@app.put("/api/shortensea/links/{link_id}")
def update_link(link_id: str, body: LinkUpdate, authorization: str = Header(default="")):
    user = _require_user(authorization)
    limits = _plan_limits(user)
    data: dict[str, Any] = {}
    if body.destination_url is not None:
        if not URL_RE.match(body.destination_url.strip()):
            raise HTTPException(400, "invalid_destination_url")
        data["destination_url"] = body.destination_url.strip()
    if body.title is not None:
        data["title"] = body.title
    if body.tags is not None:
        if body.tags and not limits["tags"]:
            raise HTTPException(403, "tags_not_allowed")
        data["tags"] = body.tags
    if body.status is not None:
        data["status"] = body.status
    if body.qr_enabled is not None:
        if body.qr_enabled and not limits["qr"]:
            raise HTTPException(403, "qr_not_allowed")
        data["qr_enabled"] = body.qr_enabled
    for field in ("utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "expires_at"):
        val = getattr(body, field)
        if val is not None:
            if field == "expires_at" and val and not limits["expiration"]:
                raise HTTPException(403, "expiration_not_allowed")
            if field.startswith("utm_") and val and not limits["utm"]:
                raise HTTPException(403, "utm_not_allowed")
            data[field] = val or None

    db = get_db()
    updated = db.update_link(link_id, user["user_id"], data)
    if not updated:
        raise HTTPException(404, "link_not_found")
    return _link_payload(updated)


@app.delete("/api/shortensea/links/{link_id}")
def delete_link(link_id: str, authorization: str = Header(default="")):
    user = _require_user(authorization)
    if not get_db().delete_link(link_id, user["user_id"]):
        raise HTTPException(404, "link_not_found")
    return {"ok": True}


@app.get("/api/shortensea/resolve/{slug}")
def resolve_slug(slug: str):
    db = get_db()
    link = db.get_link_by_slug(slug)
    if not link or link.get("status") != "active":
        raise HTTPException(404, "not_found")
    if link.get("expires_at"):
        try:
            exp = datetime.strptime(link["expires_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > exp:
                raise HTTPException(410, "link_expired")
        except ValueError:
            pass
    return {
        "slug": link["slug"],
        "destination_url": _append_utm(link["destination_url"], link),
        "title": link.get("title"),
    }


@app.get("/api/shortensea/insights")
def get_insights(authorization: str = Header(default="")):
    user = _require_user(authorization)
    limits = _plan_limits(user)
    data = get_db().get_insights(user["user_id"])
    data["plan"] = _effective_plan(user)
    data["basic_insights"] = limits["basic_insights"]
    data["advanced_insights"] = limits["advanced_insights"]
    if not limits["basic_insights"]:
        return {
            "total_clicks": data["total_clicks"],
            "clicks_by_link": [],
            "clicks_by_day": [],
            "referrers": [],
            "devices": [],
            "browsers": [],
            "countries": [],
            "top_links": [],
            "qr_scans": 0,
            "plan": data["plan"],
            "basic_insights": False,
            "advanced_insights": False,
            "locked": True,
        }
    if not limits["advanced_insights"]:
        data["referrers"] = data["referrers"][:5]
        data["devices"] = data["devices"][:3]
        data["browsers"] = data["browsers"][:3]
        data["countries"] = []
        data["locked_advanced"] = True
    return data


# ============= Redirect =============
@app.get("/s/{slug}")
async def redirect_slug(slug: str, request: Request, qr: int = Query(default=0)):
    db = get_db()
    link = db.get_link_by_slug(slug)
    if not link or link.get("status") != "active":
        raise HTTPException(404, "not_found")
    if link.get("expires_at"):
        try:
            exp = datetime.strptime(link["expires_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > exp:
                raise HTTPException(410, "link_expired")
        except ValueError:
            pass

    ua = request.headers.get("user-agent", "")
    device, browser = _parse_ua(ua)
    db.record_click(link["link_id"], {
        "referrer": request.headers.get("referer"),
        "device": device,
        "browser": browser,
        "country": request.headers.get("cf-ipcountry"),
        "city": None,
        "is_qr": bool(qr),
    })
    target = _append_utm(link["destination_url"], link)
    return RedirectResponse(target, status_code=302)


# ============= Admin =============
@app.get("/api/shortensea/admin/codes")
def admin_list_codes(authorization: str = Header(default="")):
    user = _require_user(authorization)
    _require_admin(user)
    return get_db().list_approve_codes()


@app.post("/api/shortensea/admin/codes")
def admin_create_code(body: CodeIn, authorization: str = Header(default="")):
    user = _require_user(authorization)
    _require_admin(user)
    if body.plan_type not in ("monthly", "yearly"):
        raise HTTPException(400, "invalid_plan_type")
    code = (body.code or _generate_code()).strip().upper()
    days = 30 if body.plan_type == "monthly" else 365
    db = get_db()
    cid = db.insert_approve_code({
        "code_hash": _hash_code(code),
        "plan_type": body.plan_type,
        "email": body.email.lower().strip() or None,
        "user_id": body.user_id or None,
        "expiry_days": days,
    })
    _pending_codes[cid] = code
    return {"code_id": cid, "approve_code": code, "plan_type": body.plan_type, "expiry_days": days}


@app.get("/api/shortensea/admin/users")
def admin_list_users(authorization: str = Header(default="")):
    user = _require_user(authorization)
    _require_admin(user)
    users = get_db().list_users()
    return [
        {
            "user_id": u["user_id"],
            "email": u.get("email"),
            "username": u.get("username"),
            "name": u.get("name"),
            "plan": u.get("plan"),
            "plan_expires_at": u.get("plan_expires_at"),
            "is_super": bool(u.get("is_super")),
            "is_guest": bool(u.get("is_guest")),
            "links_month_count": u.get("links_month_count"),
            "created_at": u.get("created_at"),
        }
        for u in users
    ]


@app.put("/api/shortensea/admin/users/{user_id}")
def admin_override_user(user_id: str, body: AdminOverrideIn, authorization: str = Header(default="")):
    admin = _require_user(authorization)
    _require_admin(admin)
    if body.plan not in ("free", "monthly", "yearly", "super", "locked_premium"):
        raise HTTPException(400, "invalid_plan")
    updated = get_db().admin_override_plan(
        user_id, body.plan, body.days, body.is_super
    )
    if not updated:
        raise HTTPException(404, "user_not_found")
    return {"ok": True, "account": _user_payload(updated)}


@app.get("/api/shortensea/admin/payment-requests")
def admin_list_payment_requests(
    authorization: str = Header(default=""),
    status: str | None = Query(default=None),
):
    user = _require_user(authorization)
    _require_admin(user)
    return get_db().list_payment_requests(status)


@app.post("/api/shortensea/admin/payment-requests/{request_id}/resolve")
def admin_resolve_payment_request(request_id: str, authorization: str = Header(default="")):
    user = _require_user(authorization)
    _require_admin(user)
    if not get_db().resolve_payment_request(request_id):
        raise HTTPException(404, "request_not_found")
    return {"ok": True}
