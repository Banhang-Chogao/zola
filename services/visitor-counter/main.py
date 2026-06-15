"""
Blog backend — visitor counter + GitHub OAuth gateway cho CMS.

Endpoints:
  Visitor counter:
    POST /track      → increment counter nếu UA không phải bot
    GET  /stats      → trả tổng count hiện tại

  GitHub OAuth (cổng đăng nhập CMS):
    GET  /auth/login           → redirect đến GitHub authorize page
    GET  /auth/callback        → GitHub callback, exchange code → check email →
                                 redirect blog với session_id trong URL fragment
    GET  /auth/me              → validate session (Header: Authorization: Bearer SID)
    POST /auth/logout          → xoá session khỏi Redis

  Misc:
    GET  /          → health check + endpoint discovery

Env vars (set Render/Railway dashboard):
  REDIS_URL          — redis://... (bắt buộc, dùng cho counter + session)
  CORS_ORIGIN        — origin được phép gọi API (default: blog GitHub Pages)
  COUNTER_KEY        — Redis key chứa counter (default: 'blog:visitors')

  GH_CLIENT_ID       — GitHub OAuth App Client ID
  GH_CLIENT_SECRET   — GitHub OAuth App Client Secret (NEVER expose client)
  BACKEND_URL        — URL public của service này (cho redirect_uri OAuth)
  BLOG_URL           — URL blog (để redirect về sau auth)
  ADMIN_EMAILS       — danh sách email được phép vào CMS, ngăn cách ',' (default
                       'tamsudev.com@gmail.com'). Thêm contributor: append email.
  SESSION_TTL        — session sống bao lâu giây (default 7200 = 2h). Redis
                       auto-expire session khi hết → admin idle 2h phải login lại.

Triết lý security:
  - client_secret CHỈ trên server, không bao giờ về client
  - access_token GitHub được giữ Redis-side, client chỉ có opaque session_id
  - session_id là URL-safe 32-byte random, không encode info → không brute-force được
  - Email whitelist server-side → client KHÔNG thể bypass
  - State param ngăn CSRF cho OAuth flow
"""

import json
import os
import re
import secrets
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
import redis.asyncio as redis


# ============= Configuration =============
REDIS_URL   = os.getenv("REDIS_URL", "redis://localhost:6379")
CORS_ORIGIN = os.getenv("CORS_ORIGIN", "https://banhang-chogao.github.io")
COUNTER_KEY = os.getenv("COUNTER_KEY", "blog:visitors")

GH_CLIENT_ID     = os.getenv("GH_CLIENT_ID", "")
GH_CLIENT_SECRET = os.getenv("GH_CLIENT_SECRET", "")
BACKEND_URL      = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
BLOG_URL         = os.getenv("BLOG_URL", "https://banhang-chogao.github.io/zola").rstrip("/")

# White-list email — comma-separated trong env. Strip + lowercase để so sánh
# robust với GitHub email (vốn được trả về lowercase nhưng phòng config typo).
ADMIN_EMAILS = {
    e.strip().lower()
    for e in os.getenv("ADMIN_EMAILS", "tamsudev.com@gmail.com").split(",")
    if e.strip()
}

SESSION_TTL = int(os.getenv("SESSION_TTL", "7200"))  # 2h default (idle timeout)


# ============= Bot Detection =============
BOT_PATTERNS = re.compile(
    r"bot|crawler|spider|crawl|slurp|mediapartners|preview|fetcher|"
    r"facebookexternalhit|whatsapp|telegram|twitterbot|linkedinbot|"
    r"discordbot|pingdom|uptime|monitor|headless|"
    r"curl|wget|python-requests|axios|node-fetch|java/|go-http-client",
    re.IGNORECASE,
)


def is_bot(user_agent: str) -> bool:
    if not user_agent or len(user_agent) < 10:
        return True
    return bool(BOT_PATTERNS.search(user_agent))


# ============= FastAPI App =============
app = FastAPI(
    title="Blog Backend (counter + CMS auth)",
    version="2.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# CORS allow blog origin only — auth endpoints chỉ trả JSON cho blog,
# OAuth redirect dùng full page navigation (không cần CORS).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[CORS_ORIGIN],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_redis_client: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


# ============= Visitor Counter Endpoints =============
@app.post("/track")
async def track(request: Request):
    ua = request.headers.get("user-agent", "")
    if is_bot(ua):
        return {"ok": True, "counted": False}

    r = await get_redis()
    new_count = await r.incr(COUNTER_KEY)
    return {"ok": True, "counted": True, "count": new_count}


@app.get("/stats")
async def stats():
    r = await get_redis()
    raw = await r.get(COUNTER_KEY)
    count = int(raw) if raw else 0
    return {"count": count}


# ============= GitHub OAuth — Auth Flow =============

def _redirect_with_error(error: str) -> RedirectResponse:
    """Redirect blog /editor/ với query ?error=... để JS hiển thị thông báo."""
    return RedirectResponse(f"{BLOG_URL}/editor/?auth_error={error}")


def _is_allowed_email(verified_emails: set) -> bool:
    """
    Kiểm tra ít nhất 1 email verified của user khớp white-list.

    Tách thành helper để dễ thay logic sau: ví dụ chuyển sang
    GitHub Collaborator API thay vì email check, chỉ cần sửa hàm này.
    """
    return bool(verified_emails & ADMIN_EMAILS)


@app.get("/auth/login")
async def auth_login(return_to: str = "/editor/"):
    """
    Bắt đầu OAuth: tạo state random (CSRF protect), lưu Redis 10 phút,
    redirect user đến GitHub authorize page.
    """
    if not GH_CLIENT_ID:
        raise HTTPException(500, "GH_CLIENT_ID chưa configure trên server")

    # Sanitize return_to: chỉ cho phép path tương đối, ngăn open redirect
    if not return_to.startswith("/"):
        return_to = "/editor/"

    state = secrets.token_urlsafe(24)
    r = await get_redis()
    await r.setex(f"oauth_state:{state}", 600, return_to)

    params = urlencode({
        "client_id": GH_CLIENT_ID,
        "scope": "read:user user:email",
        "state": state,
        "redirect_uri": f"{BACKEND_URL}/auth/callback",
        "allow_signup": "false",
    })
    return RedirectResponse(f"https://github.com/login/oauth/authorize?{params}")


@app.get("/auth/callback")
async def auth_callback(code: str = "", state: str = ""):
    """
    GitHub redirect tới đây sau khi user authorize.
    1. Verify state (CSRF)
    2. Exchange code → access_token
    3. Fetch user emails → check white-list
    4. Tạo session Redis (TTL 8h), redirect blog với sid trong URL fragment

    URL fragment (#sid=...) KHÔNG gửi server → an toàn hơn query string.
    """
    if not code or not state:
        return _redirect_with_error("missing_params")

    r = await get_redis()
    return_to = await r.getdel(f"oauth_state:{state}")
    if not return_to:
        return _redirect_with_error("invalid_state")

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Exchange code → access_token
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
            return _redirect_with_error("github_unreachable")

        token_data = token_res.json() if token_res.status_code == 200 else {}
        access_token = token_data.get("access_token")
        if not access_token:
            return _redirect_with_error("token_exchange_failed")

        gh_headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        # Fetch verified emails — required scope: user:email
        try:
            emails_res = await client.get("https://api.github.com/user/emails", headers=gh_headers)
            user_res   = await client.get("https://api.github.com/user",        headers=gh_headers)
        except httpx.HTTPError:
            return _redirect_with_error("github_unreachable")

        if emails_res.status_code != 200 or user_res.status_code != 200:
            return _redirect_with_error("github_profile_fetch_failed")

        emails = emails_res.json()
        # Chỉ chấp nhận email verified — GitHub có flag .verified cho mỗi email
        verified_emails = {
            (e.get("email") or "").lower()
            for e in emails
            if e.get("verified") and e.get("email")
        }

        if not _is_allowed_email(verified_emails):
            return _redirect_with_error("access_denied")

        user = user_res.json()

    # Tạo session opaque — sid là 43 ký tự URL-safe, không carry info,
    # không thể brute force trong thời gian session sống.
    sid = secrets.token_urlsafe(32)
    matched_email = next(iter(verified_emails & ADMIN_EMAILS), None)
    session = {
        "email":        matched_email,
        "username":     user.get("login", ""),
        "name":         user.get("name") or user.get("login", ""),
        "avatar":       user.get("avatar_url", ""),
        # access_token được lưu server-side cho tương lai (vd commit qua API).
        # KHÔNG bao giờ trả về client qua endpoint /auth/me.
        "access_token": access_token,
    }
    await r.setex(f"session:{sid}", SESSION_TTL, json.dumps(session))

    # URL fragment (#) — browser KHÔNG gửi # cho server, JS đọc rồi xoá hash.
    # An toàn hơn query string (?sid=...) vì query có thể leak qua referer header.
    return RedirectResponse(f"{BLOG_URL}{return_to}#sid={sid}")


def _extract_sid(authorization: str) -> str:
    """Bóc 'Bearer <sid>' header, raise 401 nếu sai format."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing_token")
    sid = authorization[7:].strip()
    if not sid:
        raise HTTPException(401, "missing_token")
    return sid


@app.get("/auth/me")
async def auth_me(authorization: str = Header(default="")):
    """
    Validate session, trả profile public (KHÔNG bao gồm access_token).
    Client gọi mỗi lần load /editor/ để check session còn valid.
    """
    sid = _extract_sid(authorization)
    r = await get_redis()
    raw = await r.get(f"session:{sid}")
    if not raw:
        raise HTTPException(401, "invalid_session")
    s = json.loads(raw)
    return {
        "email":    s.get("email"),
        "username": s.get("username"),
        "name":     s.get("name"),
        "avatar":   s.get("avatar"),
    }


@app.post("/auth/logout")
async def auth_logout(authorization: str = Header(default="")):
    """Xoá session khỏi Redis. Không lỗi nếu session đã hết hạn."""
    try:
        sid = _extract_sid(authorization)
    except HTTPException:
        return {"ok": True}
    r = await get_redis()
    await r.delete(f"session:{sid}")
    return {"ok": True}


# ============= Misc =============
@app.get("/")
async def root():
    return {
        "service": "blog-backend",
        "version": "2.0.0",
        "features": {
            "visitor_counter": True,
            "github_oauth":    bool(GH_CLIENT_ID and GH_CLIENT_SECRET),
        },
        "endpoints": {
            "POST /track":        "Visitor counter increment",
            "GET  /stats":        "Visitor counter total",
            "GET  /auth/login":   "Start GitHub OAuth flow",
            "GET  /auth/callback":"OAuth callback (GitHub uses this)",
            "GET  /auth/me":      "Validate session (Bearer)",
            "POST /auth/logout":  "Destroy session (Bearer)",
        },
    }
