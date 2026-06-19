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
                       '292648126+Banhang-Chogao@users.noreply.github.com'). Thêm contributor: append email.
  SESSION_TTL        — session sống bao lâu giây (default 7200 = 2h). Redis
                       auto-expire session khi hết → admin idle 2h phải login lại.

Triết lý security:
  - client_secret CHỈ trên server, không bao giờ về client
  - access_token GitHub được giữ Redis-side, client chỉ có opaque session_id
  - session_id là URL-safe 32-byte random, không encode info → không brute-force được
  - Email whitelist server-side → client KHÔNG thể bypass
  - State param ngăn CSRF cho OAuth flow
"""

import asyncio
import base64
import json
import os
import re
import secrets
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlencode, urljoin, urlparse

import feedparser
import httpx
from bs4 import BeautifulSoup
from fastapi import FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
import redis.asyncio as redis

from gsc_routes import configure as configure_gsc, router as gsc_router
from vipzone_auth import fetch_vipzone_me, require_supervip as _require_supervip_impl


# ============= Configuration =============
REDIS_URL   = os.getenv("REDIS_URL", "redis://localhost:6379")
CORS_ORIGIN = os.getenv("CORS_ORIGIN", "https://banhang-chogao.github.io")
COUNTER_KEY = os.getenv("COUNTER_KEY", "blog:visitors")

GH_CLIENT_ID     = os.getenv("GH_CLIENT_ID", "")
GH_CLIENT_SECRET = os.getenv("GH_CLIENT_SECRET", "")
BACKEND_URL      = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
BLOG_URL         = os.getenv("BLOG_URL", "https://banhang-chogao.github.io/zola").rstrip("/")
# Base path component của BLOG_URL — vd "/zola". Dùng để strip khi return_to
# từ client đã có prefix này (do location.pathname trên GitHub Pages bao gồm
# subpath). Tránh URL kép kiểu /zola/zola/baochi/.
_BLOG_BASE_PATH = urlparse(BLOG_URL).path.rstrip("/")

# White-list email — comma-separated trong env. Strip + lowercase để so sánh
# robust với GitHub email (vốn được trả về lowercase nhưng phòng config typo).
ADMIN_EMAILS = {
    e.strip().lower()
    for e in os.getenv(
        "ADMIN_EMAILS",
        "292648126+Banhang-Chogao@users.noreply.github.com",
    ).split(",")
    if e.strip()
}
ADMIN_USERNAMES = {
    u.strip().lower()
    for u in os.getenv("ADMIN_USERNAMES", "banhang-chogao").split(",")
    if u.strip()
}

# Session TTL: 30 ngày mặc định + sliding (refresh mỗi request) → super admin đã
# đăng nhập GitHub một lần thì không phải login lại dù đóng trình duyệt / xoá cache
# (sid được lưu localStorage client-side, server gia hạn TTL khi còn dùng).
SESSION_TTL = int(os.getenv("SESSION_TTL", str(30 * 24 * 3600)))  # 30d sliding


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

def _redirect_with_error(error: str, return_to: str = "/editor/") -> RedirectResponse:
    """Redirect về trang gốc (return_to) với ?auth_error=... để JS hiển thị thông báo."""
    rt = return_to if return_to.startswith("/") else "/editor/"
    base = _build_blog_url(rt)
    sep = "&" if "?" in base else "?"
    return RedirectResponse(f"{base}{sep}auth_error={error}")


def _build_blog_url(return_to: str, fragment: str = "") -> str:
    """
    Compose URL về blog, strip duplicate base path nếu client gửi đầy đủ
    (vd '/zola/baochi/' khi BLOG_URL đã có '/zola' suffix → kéo về '/baochi/').
    """
    rt = return_to or "/"
    if _BLOG_BASE_PATH and rt.startswith(_BLOG_BASE_PATH + "/"):
        rt = rt[len(_BLOG_BASE_PATH):]
    if _BLOG_BASE_PATH and rt == _BLOG_BASE_PATH:
        rt = "/"
    if not rt.startswith("/"):
        rt = "/" + rt
    return f"{BLOG_URL}{rt}" + (f"#{fragment}" if fragment else "")


def _is_allowed_email(verified_emails: set) -> bool:
    """
    Kiểm tra ít nhất 1 email verified của user khớp white-list.

    Tách thành helper để dễ thay logic sau: ví dụ chuyển sang
    GitHub Collaborator API thay vì email check, chỉ cần sửa hàm này.
    """
    return bool(verified_emails & ADMIN_EMAILS)


def _is_allowed_user(username: str) -> bool:
    """Fallback whitelist theo GitHub login (vd banhang-chogao)."""
    return (username or "").strip().lower() in ADMIN_USERNAMES


def is_super_session(session: dict) -> bool:
    """Superadmin from OAuth-time GitHub repo permission (stored in session) or username env fallback."""
    if session.get("is_superadmin") or session.get("is_super"):
        return True
    from github_repo import username_env_fallback

    return username_env_fallback(session.get("username"))


async def _touch_session(r, sid: str) -> None:
    """Sliding session — gia hạn TTL mỗi lần dùng để admin không bị logout giữa chừng."""
    try:
        await r.expire(f"session:{sid}", SESSION_TTL)
    except Exception:
        pass


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

    # Scope public_repo cần để PUT file content qua /repos/.../contents/{path}
    # khi user đăng bài trực tiếp lên blog từ /editor/. read:user + user:email
    # phục vụ check whitelist + lấy profile.
    params = urlencode({
        "client_id": GH_CLIENT_ID,
        "scope": "read:user user:email public_repo",
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

        # Fetch verified emails — required scope: user:email
        try:
            emails_res = await client.get("https://api.github.com/user/emails", headers=gh_headers)
            user_res   = await client.get("https://api.github.com/user",        headers=gh_headers)
        except httpx.HTTPError:
            return _redirect_with_error("github_unreachable", return_to)

        if emails_res.status_code != 200 or user_res.status_code != 200:
            return _redirect_with_error("github_profile_fetch_failed", return_to)

        emails = emails_res.json()
        user = user_res.json()
        # Chỉ chấp nhận email verified — GitHub có flag .verified cho mỗi email
        verified_emails = {
            (e.get("email") or "").lower()
            for e in emails
            if e.get("verified") and e.get("email")
        }

        username = user.get("login", "")
        if not _is_allowed_email(verified_emails) and not _is_allowed_user(username):
            return _redirect_with_error("access_denied", return_to)

        from github_repo import check_repo_superadmin

        is_super = await check_repo_superadmin(client, access_token, username)

    # Tạo session opaque — sid là 43 ký tự URL-safe, không carry info,
    # không thể brute force trong thời gian session sống.
    sid = secrets.token_urlsafe(32)
    matched_email = next(iter(verified_emails & ADMIN_EMAILS), None)
    session = {
        "email":        matched_email,
        "username":     user.get("login", ""),
        "name":         user.get("name") or user.get("login", ""),
        "avatar":       user.get("avatar_url", ""),
        "is_super":     is_super,
        "is_superadmin": is_super,
        # access_token được lưu server-side cho tương lai (vd commit qua API).
        # KHÔNG bao giờ trả về client qua endpoint /auth/me.
        "access_token": access_token,
    }
    await r.setex(f"session:{sid}", SESSION_TTL, json.dumps(session))

    # URL fragment (#) — browser KHÔNG gửi # cho server, JS đọc rồi xoá hash.
    # An toàn hơn query string (?sid=...) vì query có thể leak qua referer header.
    return RedirectResponse(_build_blog_url(return_to, fragment=f"sid={sid}"))


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
    Role (user · vip · supervip) resolved via VIPZone API when available.
    """
    sid = _extract_sid(authorization)
    r = await get_redis()
    raw = await r.get(f"session:{sid}")
    if not raw:
        raise HTTPException(401, "invalid_session")
    await _touch_session(r, sid)  # sliding: mỗi lần check session → gia hạn TTL
    s = json.loads(raw)
    out = {
        "email":    s.get("email"),
        "username": s.get("username"),
        "name":     s.get("name"),
        "avatar":   s.get("avatar"),
        "role":     "user",
        # Quyền cao nhất: GitHub login whitelisted (chủ blog) → super admin.
        "is_super": is_super_session(s),
    }
    try:
        vz = await fetch_vipzone_me(authorization)
        out["role"] = vz.get("role") or "user"
        if vz.get("vip_expires_at"):
            out["vip_expires_at"] = vz["vip_expires_at"]
    except HTTPException:
        pass
    if out["is_super"] and out["role"] not in ("superadmin", "supervip"):
        out["role"] = "superadmin"
    return out


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


# ============= Authentication Helper =============
async def require_session(authorization: str) -> dict:
    """
    Validate Bearer sid, trả session dict hoặc raise 401. Dùng cho mọi
    endpoint cần authenticated user. NEVER log session content vì có
    chứa access_token.
    """
    sid = _extract_sid(authorization)
    r = await get_redis()
    raw = await r.get(f"session:{sid}")
    if not raw:
        raise HTTPException(401, "invalid_session")
    await _touch_session(r, sid)  # sliding: gia hạn TTL khi session còn được dùng
    return json.loads(raw)


async def require_supervip(authorization: str) -> dict:
    """GSC destructive actions — VIPZone role must be supervip."""
    return await _require_supervip_impl(authorization, require_session)


configure_gsc(
    get_redis=get_redis,
    require_session=require_session,
    require_supervip=require_supervip,
    build_blog_url=_build_blog_url,
)
app.include_router(gsc_router)


# ============= DEBUG — Trip.com scrape diagnostic =============
@app.get("/api/debug/trip")
async def debug_trip_scrape():
    """
    Diagnostic endpoint cho Trip.com scrape — trả thông tin chi tiết để biết
    tại sao primary scraper return empty: curl_cffi available? status code?
    HTML length? __NEXT_DATA__ tồn tại? walker tìm được item nào?

    KHÔNG cache, mỗi call fetch tươi. Public để dễ test.
    """
    feed_cfg = CURATED_FEEDS.get("du-lich") or {}
    primary = feed_cfg.get("primary") or feed_cfg
    url = primary.get("url", "")

    info = {
        "url":                  url,
        "curl_cffi_available":  _CURL_CFFI_AVAILABLE,
        "step":                 "init",
    }

    if not url:
        info["error"] = "no_url_configured"
        return info

    if not _CURL_CFFI_AVAILABLE:
        info["error"] = "curl_cffi_not_installed"
        info["hint"] = "Check Render build logs — curl-cffi wheel có thể fail install"
        return info

    def _sync_fetch():
        return curl_requests.get(
            url,
            impersonate="chrome131",
            headers={
                "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Referer": "https://www.trip.com/",
            },
            timeout=25,
        )

    info["step"] = "fetching"
    try:
        res = await asyncio.to_thread(_sync_fetch)
    except Exception as e:
        info["error"] = "fetch_exception"
        info["exception_type"] = type(e).__name__
        info["exception_msg"]  = str(e)[:300]
        return info

    info["status_code"]   = res.status_code
    info["content_type"]  = res.headers.get("content-type", "")[:100]
    info["html_length"]   = len(res.text)
    info["step"]          = "parsing"

    # Detect Cloudflare challenge page
    txt_lower = res.text[:5000].lower()
    info["cloudflare_signs"] = any(s in txt_lower for s in [
        "cf-chl-", "challenge-platform", "ray id:", "checking your browser",
        "cloudflare", "just a moment",
    ])

    # Page title — confirm real content vs challenge
    m_title = re.search(r'<title>(.*?)</title>', res.text, re.DOTALL | re.IGNORECASE)
    info["page_title"] = (m_title.group(1).strip()[:200] if m_title else "")

    # __NEXT_DATA__ presence
    m_next = re.search(
        r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        res.text, re.DOTALL,
    )
    info["has_next_data"] = bool(m_next)
    if m_next:
        info["next_data_length"] = len(m_next.group(1))
        try:
            nd_json = json.loads(m_next.group(1))
            # Walk top-level keys để xem structure
            if isinstance(nd_json, dict):
                info["next_data_top_keys"] = list(nd_json.keys())[:10]
                # Common Next.js path: props.pageProps.*
                pp = (nd_json.get("props") or {}).get("pageProps") or {}
                if pp:
                    info["page_props_keys"] = list(pp.keys())[:20]
        except json.JSONDecodeError:
            info["next_data_parse_error"] = True

    # Generic application/json scripts (alternate)
    json_scripts = re.findall(
        r'<script[^>]+type=["\']application/json["\'][^>]*>(.*?)</script>',
        res.text, re.DOTALL,
    )
    info["json_script_count"]    = len(json_scripts)
    info["json_script_lengths"]  = [len(s) for s in json_scripts[:5]]

    # Run actual walker
    info["step"] = "walking"
    try:
        items = await _scrape_trip_via_curl_cffi(url)
        info["items_extracted"] = len(items)
        if items:
            info["sample_item_keys"] = list(items[0].keys())
            info["sample_titles"]    = [it.get("title", "")[:80] for it in items[:3]]
    except Exception as e:
        info["walker_exception"] = f"{type(e).__name__}: {str(e)[:200]}"

    info["step"] = "done"
    return info


# ============= IMDB (via public scraper proxy) =============
# Walker linh hoạt parse mọi JSON shape — không lock vào schema cụ thể.
# Schema thực tế từ imdb.iamidiotareyoutoo.com:
#   {ok: true, description: [{#TITLE, #YEAR, #IMDB_ID, #IMDB_URL,
#    #IMG_POSTER, #ACTORS, #AKA, #RANK, ...}], error_code: 200}
# Keys prefix '#' uppercase — đã add vào synonym list.
_IMDB_TITLE_KEYS  = ("#TITLE", "title", "Title", "name", "originalTitle",
                     "imdbTitle", "displayName", "l")
_IMDB_LINK_KEYS   = ("#IMDB_URL", "link", "url", "imdbUrl", "#IMDB_ID",
                     "imdbId", "id", "imdbID")
# #ACTORS (string cast) làm summary fallback — không có plot/overview trong
# search response. #AKA fallback nữa.
_IMDB_DESC_KEYS   = ("description", "plot", "Plot", "summary", "synopsis",
                     "overview", "#ACTORS", "#AKA", "intro", "s")
_IMDB_POSTER_KEYS = ("#IMG_POSTER", "image", "poster", "Poster", "imageUrl",
                     "image_url", "primaryImage", "thumbnail", "i", "img")
_IMDB_RATING_KEYS = ("rating", "imdbRating", "imDbRating", "Rating", "score",
                     "averageRating", "aggregateRating", "vote_average", "r")
_IMDB_DATE_KEYS   = ("#YEAR", "year", "Year", "releaseDate", "release_date",
                     "datePublished", "y")


def _first_str(obj: dict, keys) -> str:
    for k in keys:
        v = obj.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
        if isinstance(v, (int, float)):
            return str(v)
    return ""


def _first_image(obj: dict, base_url: str) -> str:
    """Image có thể là string URL, dict {url|imageUrl}, hoặc nested object."""
    for k in _IMDB_POSTER_KEYS:
        v = obj.get(k)
        if isinstance(v, str) and v.strip():
            return _normalize_link(v.strip(), base_url)
        if isinstance(v, dict):
            url = v.get("url") or v.get("imageUrl") or v.get("src") or ""
            if isinstance(url, str) and url.strip():
                return _normalize_link(url.strip(), base_url)
    return ""


def _imdb_link_for(obj: dict) -> str:
    """Compose IMDB URL từ id 'tt0123456' nếu chưa có link full."""
    raw = _first_str(obj, _IMDB_LINK_KEYS)
    if not raw:
        return ""
    if raw.startswith(("http://", "https://")):
        return raw
    if raw.startswith("/"):
        return "https://www.imdb.com" + raw
    # IMDB ID format 'tt0123456' → construct URL
    if re.match(r"^tt\d{6,}$", raw):
        return f"https://www.imdb.com/title/{raw}/"
    return ""


def _imdb_nested_title(obj: dict) -> str:
    """
    IMDB GraphQL data có pattern nested: titleText.text, primaryTitle.text.
    Check trước flat key, sau đó nested {text|primaryText|originalText}.
    """
    direct = _first_str(obj, _IMDB_TITLE_KEYS)
    if direct:
        return direct
    for nk in ("titleText", "title", "originalTitleText", "primaryTitle", "name"):
        v = obj.get(nk)
        if isinstance(v, dict):
            t = (v.get("text") or v.get("primaryText") or v.get("plainText") or "")
            if isinstance(t, str) and t.strip():
                return t.strip()
        elif isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _imdb_nested_image(obj: dict, base_url: str) -> str:
    """IMDB primaryImage.url là nested object phổ biến cho poster."""
    direct = _first_image(obj, base_url)
    if direct:
        return direct
    for nk in ("primaryImage", "image", "poster", "thumbnail"):
        v = obj.get(nk)
        if isinstance(v, dict):
            url = v.get("url") or v.get("imageUrl") or ""
            if isinstance(url, str) and url.strip():
                return _normalize_link(url.strip(), base_url)
    return ""


def _imdb_nested_link(obj: dict) -> str:
    """tconst 'tt12345' có thể nằm ở obj.id hoặc obj.node.id."""
    direct = _imdb_link_for(obj)
    if direct:
        return direct
    # node wrapper (GraphQL connection edges)
    node = obj.get("node")
    if isinstance(node, dict):
        return _imdb_link_for(node)
    return ""


def _imdb_nested_date(obj: dict) -> str:
    direct = _first_str(obj, _IMDB_DATE_KEYS)
    if direct:
        return direct
    # releaseDate.year + month + day → string
    for nk in ("releaseDate", "releaseYear", "datePublished"):
        v = obj.get(nk)
        if isinstance(v, dict):
            y = v.get("year") or v.get("y") or ""
            m = v.get("month") or v.get("m") or ""
            d = v.get("day") or v.get("d") or ""
            parts = [str(p) for p in (y, m, d) if p]
            if parts:
                return "-".join(parts)
        elif isinstance(v, (int, str)) and v:
            return str(v)
    return ""


def _imdb_nested_rating(obj: dict) -> str:
    direct = _first_str(obj, _IMDB_RATING_KEYS)
    if direct:
        try:
            return f"{float(direct):.1f}"
        except (TypeError, ValueError):
            return direct[:5]
    # ratingsSummary.aggregateRating (GraphQL)
    for nk in ("ratingsSummary", "ratings", "rating"):
        v = obj.get(nk)
        if isinstance(v, dict):
            r = v.get("aggregateRating") or v.get("value") or v.get("ratingValue") or ""
            if r is not None and r != "":
                try:
                    return f"{float(r):.1f}"
                except (TypeError, ValueError):
                    return str(r)[:5]
    return ""


def _extract_imdb_items(node, items: list, base_url: str, depth: int = 0) -> None:
    """
    Walk JSON tìm objects có shape title+link → push items, cap 10.
    Hỗ trợ cả flat (proxy search response) và nested GraphQL (IMDB calendar
    __NEXT_DATA__) qua helper _imdb_nested_*.
    """
    if depth > 8 or len(items) >= 10:
        return

    if isinstance(node, list):
        for child in node:
            if isinstance(child, dict):
                # GraphQL connection edges wrapper: {node: {...real entry...}}
                effective = child.get("node") if isinstance(child.get("node"), dict) else child
                title = _imdb_nested_title(effective)
                link  = _imdb_nested_link(effective)
                if title and link and len(title) >= 2:
                    items.append({
                        "title":     title[:300],
                        "link":      link,
                        "summary":   _first_str(effective, _IMDB_DESC_KEYS)[:500],
                        "published": _imdb_nested_date(effective)[:50],
                        "thumbnail": _imdb_nested_image(effective, base_url),
                        "rating":    _imdb_nested_rating(effective),
                    })
                    if len(items) >= 10:
                        return
            _extract_imdb_items(child, items, base_url, depth + 1)
    elif isinstance(node, dict):
        # Ưu tiên array key phổ biến
        for prio_key in ("description", "results", "data", "items", "movies",
                          "titles", "edges", "list", "aboveTheFoldData",
                          "calendarTitles", "releases"):
            v = node.get(prio_key)
            if isinstance(v, list):
                _extract_imdb_items(v, items, base_url, depth + 1)
                if len(items) >= 10:
                    return
        # Walk các giá trị còn lại
        for k, v in node.items():
            if k in ("description", "results", "data", "items", "movies",
                     "titles", "edges", "list", "aboveTheFoldData",
                     "calendarTitles", "releases"):
                continue
            _extract_imdb_items(v, items, base_url, depth + 1)
            if len(items) >= 10:
                return


async def _fetch_imdb_html(url: str) -> tuple:
    """
    Fetch IMDB.com HTML với TLS impersonate Chrome → bypass bot detection.
    Trả tuple (html_text, status_code). Empty string nếu fail.
    """
    if not _CURL_CFFI_AVAILABLE:
        return "", 0

    def _sync():
        return curl_requests.get(
            url,
            impersonate="chrome131",
            headers={
                "Accept-Language": "en-US,en;q=0.9,vi-VN;q=0.8",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Referer": "https://www.imdb.com/",
                "Cache-Control": "no-cache",
            },
            timeout=25,
        )

    try:
        res = await asyncio.to_thread(_sync)
    except Exception:
        return "", 0
    return (res.text, res.status_code) if res.status_code == 200 else ("", res.status_code)


def _parse_next_data_items(html: str, base_url: str) -> list:
    """Extract __NEXT_DATA__ JSON từ HTML và walk tìm IMDB entries."""
    if not html:
        return []
    m = re.search(
        r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        html, re.DOTALL,
    )
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return []
    items: list = []
    _extract_imdb_items(data, items, base_url)
    return items[:10]


@app.get("/api/movies")
async def imdb_movies():
    """
    Trả tối đa 10 phim từ IMDB. URL configurable qua IMDB_API_URL env var.

    Dispatch theo URL host:
      - imdb.com → HTML scrape với curl_cffi TLS impersonate + parse
        __NEXT_DATA__ (Next.js). Calendar/title pages dùng GraphQL nested
        structure, walker đã handle qua _imdb_nested_*
      - khác → JSON fetch httpx, walker direct (proxy services trả JSON sạch)

    Redis cache 24h. Lỗi → graceful degrade items=[].
    """
    r = await get_redis()
    cache_key = f"imdb:movies:{hash(IMDB_API_URL) & 0xffffffff:x}"
    cached = await r.get(cache_key)
    if cached:
        try:
            data = json.loads(cached)
            if data.get("items"):
                data["from_cache"] = True
                return data
        except json.JSONDecodeError:
            pass

    parsed = urlparse(IMDB_API_URL)
    is_imdb_direct = "imdb.com" in (parsed.netloc or "").lower()

    items: list = []
    try:
        if is_imdb_direct:
            html, status = await _fetch_imdb_html(IMDB_API_URL)
            items = _parse_next_data_items(html, "https://www.imdb.com")
        else:
            async with httpx.AsyncClient(
                timeout=20.0,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                                  "Chrome/131.0.0.0 Safari/537.36",
                    "Accept": "application/json, */*;q=0.9",
                },
            ) as client:
                res = await client.get(IMDB_API_URL)
            res.raise_for_status()
            data = res.json()
            _extract_imdb_items(data, items, "https://www.imdb.com")
    except Exception:
        return {
            "source":     "IMDB",
            "title":      "Tin tức Điện ảnh — IMDB",
            "count":      0,
            "items":      [],
            "from_cache": False,
            "error":      "fetch_failed",
        }

    payload = {
        "source": "IMDB",
        "title":  "Tin tức Điện ảnh — IMDB",
        "count":  len(items),
        "items":  items,
    }
    ttl = IMDB_CACHE_TTL if items else 300
    await r.setex(cache_key, ttl, json.dumps(payload, ensure_ascii=False))
    payload["from_cache"] = False
    return payload


@app.get("/api/debug/imdb")
async def debug_imdb_scrape():
    """Diagnostic cho IMDB scrape — trả raw info để biết tại sao empty."""
    url = IMDB_API_URL
    parsed = urlparse(url)
    is_imdb_direct = "imdb.com" in (parsed.netloc or "").lower()

    info = {
        "url":                  url,
        "is_imdb_direct":       is_imdb_direct,
        "curl_cffi_available":  _CURL_CFFI_AVAILABLE,
    }

    if is_imdb_direct:
        if not _CURL_CFFI_AVAILABLE:
            info["error"] = "curl_cffi_not_installed"
            return info
        html, status = await _fetch_imdb_html(url)
        info["status_code"] = status
        info["html_length"] = len(html)
        if html:
            m_title = re.search(r'<title>(.*?)</title>', html, re.DOTALL | re.IGNORECASE)
            info["page_title"] = (m_title.group(1).strip()[:200] if m_title else "")
            m_next = re.search(
                r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
                html, re.DOTALL,
            )
            info["has_next_data"] = bool(m_next)
            if m_next:
                info["next_data_length"] = len(m_next.group(1))
                try:
                    nd = json.loads(m_next.group(1))
                    if isinstance(nd, dict):
                        info["top_keys"] = list(nd.keys())[:10]
                        pp = (nd.get("props") or {}).get("pageProps") or {}
                        if pp:
                            info["page_props_keys"] = list(pp.keys())[:20]
                except json.JSONDecodeError:
                    info["next_data_parse_error"] = True
            items = _parse_next_data_items(html, "https://www.imdb.com")
            info["items_extracted"] = len(items)
            info["sample_titles"]   = [it.get("title", "")[:80] for it in items[:5]]
    else:
        # JSON proxy mode
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get(url)
            info["status_code"]    = res.status_code
            info["content_type"]   = res.headers.get("content-type", "")[:100]
            data = res.json()
            info["json_top_type"] = type(data).__name__
            if isinstance(data, dict):
                info["json_top_keys"] = list(data.keys())[:10]
            items: list = []
            _extract_imdb_items(data, items, "https://www.imdb.com")
            info["items_extracted"] = len(items)
            info["sample_titles"]   = [it.get("title", "")[:80] for it in items[:5]]
        except Exception as e:
            info["exception"] = f"{type(e).__name__}: {str(e)[:200]}"
    return info


# ============= CMS — Publish Post to GitHub =============
# Cấu hình repo target — hiện chỉ phục vụ blog của owner. Mở rộng:
# read từ env nếu cần multi-repo.
CMS_REPO_OWNER  = os.getenv("CMS_REPO_OWNER",  "Banhang-Chogao")
CMS_REPO_NAME   = os.getenv("CMS_REPO_NAME",   "zola")
CMS_REPO_BRANCH = os.getenv("CMS_REPO_BRANCH", "main")
# Cố định path để giới hạn quyền: user không thể ghi file ra ngoài thư mục
# content. Đây là defense-in-depth — kể cả slug chứa '../' cũng bị regex
# validate chặn từ trước.
CMS_CONTENT_DIR = "content/posting"
# File lưu danh sách category dùng cho CMS dropdown. Sống trong repo →
# persist qua mọi Render restart, versioned trong git.
CMS_CATEGORIES_PATH = "categories.json"

# Slug hợp lệ: a-z + 0-9 + dash, 2-80 ký tự. Khớp pattern Zola slug.
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,79}$")
_CATEGORY_RE = re.compile(r"^[\wÀ-ſḀ-ỿ\s\-+&()]{1,100}$", re.UNICODE)


# ============= Helpers GitHub Contents API =============
async def _gh_get_file(client: httpx.AsyncClient, path: str, token: str) -> tuple:
    """GET file content qua Contents API. Return (sha, decoded_text) hoặc (None, None) nếu 404."""
    res = await client.get(
        f"https://api.github.com/repos/{CMS_REPO_OWNER}/{CMS_REPO_NAME}/contents/{path}",
        params={"ref": CMS_REPO_BRANCH},
        headers={
            "Authorization":        f"Bearer {token}",
            "Accept":               "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent":           "zola-cms",
        },
    )
    if res.status_code == 404:
        return None, None
    if res.status_code != 200:
        raise HTTPException(502, f"github_read_failed_{res.status_code}")
    data = res.json()
    try:
        decoded = base64.b64decode(data.get("content", "")).decode("utf-8")
    except Exception:
        decoded = ""
    return data.get("sha"), decoded


async def _gh_list_dir(client: httpx.AsyncClient, path: str, token: str) -> list:
    """GET directory listing qua Contents API. Return [] nếu directory thiếu."""
    res = await client.get(
        f"https://api.github.com/repos/{CMS_REPO_OWNER}/{CMS_REPO_NAME}/contents/{path}",
        params={"ref": CMS_REPO_BRANCH},
        headers={
            "Authorization":        f"Bearer {token}",
            "Accept":               "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent":           "zola-cms",
        },
    )
    if res.status_code == 404:
        return []
    if res.status_code != 200:
        raise HTTPException(502, f"github_read_failed_{res.status_code}")
    data = res.json()
    return data if isinstance(data, list) else []


async def _gh_get_sha(client: httpx.AsyncClient, path: str, token: str) -> Optional[str]:
    """Get sha của file. None nếu 404. Dùng cho binary file."""
    res = await client.get(
        f"https://api.github.com/repos/{CMS_REPO_OWNER}/{CMS_REPO_NAME}/contents/{path}",
        params={"ref": CMS_REPO_BRANCH},
        headers={
            "Authorization":        f"Bearer {token}",
            "Accept":               "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent":           "zola-cms",
        },
    )
    if res.status_code == 404:
        return None
    if res.status_code != 200:
        raise HTTPException(502, f"github_read_failed_{res.status_code}")
    return res.json().get("sha")


async def _gh_put_binary(client: httpx.AsyncClient, path: str, raw_bytes: bytes,
                          sha: Optional[str], message: str, token: str) -> dict:
    """PUT binary file qua Contents API. raw_bytes → base64."""
    payload = {
        "message": message[:200],
        "content": base64.b64encode(raw_bytes).decode("ascii"),
        "branch":  CMS_REPO_BRANCH,
    }
    if sha:
        payload["sha"] = sha
    res = await client.put(
        f"https://api.github.com/repos/{CMS_REPO_OWNER}/{CMS_REPO_NAME}/contents/{path}",
        headers={
            "Authorization":        f"Bearer {token}",
            "Accept":               "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent":           "zola-cms",
        },
        json=payload,
    )
    if res.status_code not in (200, 201):
        err = {}
        try: err = res.json()
        except json.JSONDecodeError: pass
        raise HTTPException(
            res.status_code if res.status_code in (403, 422) else 502,
            f"github_api: {err.get('message', 'error')}",
        )
    return res.json()


async def _gh_put_file(client: httpx.AsyncClient, path: str, content: str,
                        sha: Optional[str], message: str, token: str) -> dict:
    """PUT (create/update) file qua Contents API."""
    payload = {
        "message": message[:200],
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch":  CMS_REPO_BRANCH,
    }
    if sha:
        payload["sha"] = sha
    res = await client.put(
        f"https://api.github.com/repos/{CMS_REPO_OWNER}/{CMS_REPO_NAME}/contents/{path}",
        headers={
            "Authorization":        f"Bearer {token}",
            "Accept":               "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent":           "zola-cms",
        },
        json=payload,
    )
    if res.status_code not in (200, 201):
        err = {}
        try: err = res.json()
        except json.JSONDecodeError: pass
        raise HTTPException(
            res.status_code if res.status_code in (403, 422) else 502,
            f"github_api: {err.get('message', 'error')}",
        )
    return res.json()


async def _load_categories(client: httpx.AsyncClient, token: str) -> tuple:
    """Load categories.json từ repo. Default ['Posting'] nếu file thiếu/lỗi."""
    sha, text = await _gh_get_file(client, CMS_CATEGORIES_PATH, token)
    if not text:
        return sha, ["Posting"]
    try:
        data = json.loads(text)
        cats = data.get("categories", []) if isinstance(data, dict) else []
        cats = [c.strip() for c in cats if isinstance(c, str) and c.strip()]
        return sha, cats or ["Posting"]
    except json.JSONDecodeError:
        return sha, ["Posting"]


# ============= Categories Endpoints =============
@app.get("/api/categories/list")
async def categories_list(authorization: str = Header(default="")):
    """Trả danh sách category từ categories.json (auth required)."""
    session = await require_session(authorization)
    token = session.get("access_token")
    if not token:
        raise HTTPException(401, "no_access_token")
    async with httpx.AsyncClient(timeout=15.0) as client:
        _, cats = await _load_categories(client, token)
    return {"categories": cats}


@app.post("/api/categories/add")
async def categories_add(request: Request, authorization: str = Header(default="")):
    """
    Append 1 category mới vào categories.json. Idempotent — đã có thì trả
    {added: false}. Tạo file mới nếu chưa tồn tại.
    """
    session = await require_session(authorization)
    token = session.get("access_token")
    if not token:
        raise HTTPException(401, "no_access_token")

    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(400, "invalid_json")
    name = str(body.get("name", "")).strip()
    if not name or not _CATEGORY_RE.match(name):
        raise HTTPException(400, "invalid_name")

    async with httpx.AsyncClient(timeout=20.0) as client:
        sha, cats = await _load_categories(client, token)
        if name in cats:
            return {"ok": True, "categories": cats, "added": False}
        cats.append(name)
        new_text = json.dumps({"categories": cats}, ensure_ascii=False, indent=2) + "\n"
        await _gh_put_file(client, CMS_CATEGORIES_PATH, new_text, sha,
                           f"CMS: thêm category '{name}'", token)
    return {"ok": True, "categories": cats, "added": True}


# ============= CMS Helper: auto-add category khi save post =============
_CATEGORY_FRONTMATTER_RE = re.compile(
    r'\[taxonomies\][^\[]*?categories\s*=\s*\[\s*"([^"]+)"',
    re.DOTALL,
)
_EXTRA_BLOCK_RE = re.compile(r"(?ms)^(\[extra\]\s*\n)(.*?)(?=^\[|\Z)")
_FEATURED_TRUE_RE = re.compile(r"(?m)^featured\s*=\s*true\s*$")
_FEATURED_LINE_RE = re.compile(r"(?m)^featured\s*=\s*true\s*\n?")
_FEATURED_AT_LINE_RE = re.compile(r'(?m)^featured_at\s*=\s*"[^"]*"\s*\n?')


async def _ensure_category(client: httpx.AsyncClient, name: str, token: str) -> None:
    """
    Best-effort: nếu post có category chưa nằm trong categories.json,
    auto-append. KHÔNG raise — không block save flow nếu fail.
    """
    if not name or not _CATEGORY_RE.match(name):
        return
    try:
        sha, cats = await _load_categories(client, token)
        if name in cats:
            return
        cats.append(name)
        new_text = json.dumps({"categories": cats}, ensure_ascii=False, indent=2) + "\n"
        await _gh_put_file(client, CMS_CATEGORIES_PATH, new_text, sha,
                           f"CMS: auto-add category '{name}'", token)
    except HTTPException:
        return
    except Exception:
        return


def _frontmatter_forces_featured(content: str) -> bool:
    extra = _EXTRA_BLOCK_RE.search(content or "")
    return bool(extra and _FEATURED_TRUE_RE.search(extra.group(2)))


def _demote_featured_frontmatter(content: str) -> str:
    """Remove manual Featured override from a markdown file's [extra] block."""
    def replace_extra(match: re.Match) -> str:
        body = _FEATURED_LINE_RE.sub("", match.group(2))
        body = _FEATURED_AT_LINE_RE.sub("", body)
        return match.group(1) + body

    return _EXTRA_BLOCK_RE.sub(replace_extra, content or "", count=1)


async def _demote_other_featured_posts(
    client: httpx.AsyncClient,
    selected_path: str,
    selected_slug: str,
    token: str,
) -> int:
    """
    Force Featured semantics for CMS publish: when one post is selected, clear
    older manual overrides from every other post in the CMS content directory.
    """
    entries = await _gh_list_dir(client, CMS_CONTENT_DIR, token)
    demoted = 0

    for entry in entries:
        path = entry.get("path", "")
        if (
            entry.get("type") != "file"
            or not path.endswith(".md")
            or path.endswith("/_index.md")
            or path == selected_path
        ):
            continue

        sha, text = await _gh_get_file(client, path, token)
        if not sha or not _frontmatter_forces_featured(text):
            continue

        demoted_text = _demote_featured_frontmatter(text)
        if demoted_text == text:
            continue

        await _gh_put_file(
            client,
            path,
            demoted_text,
            sha,
            f"CMS: bỏ Featured cũ khi chọn '{selected_slug}'",
            token,
        )
        demoted += 1

    return demoted


@app.post("/cms/save-post")
async def cms_save_post(request: Request, authorization: str = Header(default="")):
    """
    Tạo hoặc cập nhật file .md trong content/posting/ qua GitHub Contents API
    với access_token user đã lưu Redis-side.

    Body JSON:
      slug    — tên file (sẽ thành content/posting/{slug}.md)
      content — toàn bộ markdown bao gồm frontmatter
      message — commit message (optional, default 'CMS: <slug>')

    Headers:
      Authorization: Bearer <sid>  — session từ OAuth login

    Security:
      - require_session check sid valid → có access_token Redis-side
      - Slug regex chặn path traversal (../ etc.)
      - Path cố định CMS_CONTENT_DIR → user KHÔNG ghi được ra ngoài
      - Content size cap 200KB tránh spam
      - PUT có sha if file tồn tại → tránh ghi đè concurrent

    Sau push: GitHub Actions auto-rebuild Zola + deploy Pages ~1-2 phút.
    """
    session = await require_session(authorization)
    access_token = session.get("access_token")
    if not access_token:
        raise HTTPException(401, "no_access_token")

    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(400, "invalid_json")

    slug    = str(body.get("slug", "")).strip().lower()
    content = body.get("content", "")
    message = str(body.get("message", "")).strip()

    if not _SLUG_RE.match(slug):
        raise HTTPException(400, "invalid_slug")
    if not isinstance(content, str) or not content.strip():
        raise HTTPException(400, "empty_content")
    if len(content) > 200_000:
        raise HTTPException(400, "content_too_large")
    if not message:
        message = f"CMS: {slug}"

    path = f"{CMS_CONTENT_DIR}/{slug}.md"
    force_featured = _frontmatter_forces_featured(content)

    async with httpx.AsyncClient(timeout=20.0) as client:
        # 1. Đọc sha hiện trạng cho update. 404 → file mới.
        try:
            existing_sha, _ = await _gh_get_file(client, path, access_token)
        except HTTPException:
            existing_sha = None

        # 2. PUT create/update file .md
        try:
            data = await _gh_put_file(
                client, path, content, existing_sha, message, access_token,
            )
        except HTTPException:
            raise

        # 3. Best-effort: nếu post có category mới (không trong categories.json),
        #    auto-append. Không block save flow nếu fail.
        cat_match = _CATEGORY_FRONTMATTER_RE.search(content)
        if cat_match:
            await _ensure_category(client, cat_match.group(1).strip(), access_token)

        # 4. Featured override: nếu bài này được chọn thủ công làm Featured,
        #    gỡ featured ở các bài khác để template/render không thể chọn nhầm.
        demoted_featured = 0
        if force_featured:
            demoted_featured = await _demote_other_featured_posts(
                client, path, slug, access_token,
            )

        return {
            "ok":         True,
            "action":     "updated" if existing_sha else "created",
            "path":       path,
            "commit_url": data.get("commit", {}).get("html_url", ""),
            "commit_sha": data.get("commit", {}).get("sha", ""),
            "demoted_featured": demoted_featured,
            "deploy_eta": "1-2 phút (GitHub Actions auto-build + deploy)",
        }


# ============= CMS — Author Management =============
CMS_AUTHOR_JSON_PATH  = "author.json"
CMS_AVATAR_PATH       = "static/img/author-avatar.webp"
_MAX_AVATAR_BYTES     = 5 * 1024 * 1024
_ALLOWED_AVATAR_MIMES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


@app.get("/cms/author")
async def cms_author_get(authorization: str = Header(default="")):
    """Đọc author.json (auth required)."""
    session = await require_session(authorization)
    token = session.get("access_token")
    if not token:
        raise HTTPException(401, "no_access_token")
    async with httpx.AsyncClient(timeout=15.0) as client:
        sha, text = await _gh_get_file(client, CMS_AUTHOR_JSON_PATH, token)
    if not text:
        return {"data": {"name": "", "url": "", "bio": "", "avatar_path": "/img/author-avatar.webp"}}
    try:
        return {"data": json.loads(text)}
    except json.JSONDecodeError:
        raise HTTPException(500, "author_json_corrupt")


@app.post("/cms/author")
async def cms_author_update(
    avatar: Optional[UploadFile] = File(None),
    name:   str = Form(""),
    url:    str = Form(""),
    bio:    str = Form(""),
    authorization: str = Header(default=""),
):
    """
    Multipart: avatar file (optional, max 5MB) + name/url/bio text.
    Avatar → upload static/img/author-avatar.webp.
    Metadata → merge vào author.json.
    """
    session = await require_session(authorization)
    token = session.get("access_token")
    if not token:
        raise HTTPException(401, "no_access_token")

    name = (name or "").strip()[:100]
    url  = (url  or "").strip()[:300]
    bio  = (bio  or "").strip()[:5000]

    commits = []
    updated_avatar = False
    updated_meta   = False

    async with httpx.AsyncClient(timeout=30.0) as client:
        if avatar is not None and avatar.filename:
            mime = (avatar.content_type or "").lower()
            if mime not in _ALLOWED_AVATAR_MIMES:
                raise HTTPException(400, f"invalid_mime_{mime}")
            raw = await avatar.read()
            if len(raw) > _MAX_AVATAR_BYTES:
                raise HTTPException(400, "avatar_too_large_5mb")
            if len(raw) < 100:
                raise HTTPException(400, "avatar_empty")
            try:
                sha = await _gh_get_sha(client, CMS_AVATAR_PATH, token)
            except HTTPException:
                sha = None
            data = await _gh_put_binary(
                client, CMS_AVATAR_PATH, raw, sha,
                "CMS: cập nhật author avatar", token,
            )
            commits.append({"type": "avatar", "url": data.get("commit", {}).get("html_url", "")})
            updated_avatar = True

        if any([name, url, bio]):
            sha_j, text = await _gh_get_file(client, CMS_AUTHOR_JSON_PATH, token)
            try:
                current = json.loads(text) if text else {}
            except json.JSONDecodeError:
                current = {}
            if not isinstance(current, dict):
                current = {}
            if name: current["name"] = name
            if url:  current["url"]  = url
            if bio:  current["bio"]  = bio
            current["avatar_path"] = "/img/author-avatar.webp"
            new_text = json.dumps(current, ensure_ascii=False, indent=2) + "\n"
            data = await _gh_put_file(
                client, CMS_AUTHOR_JSON_PATH, new_text, sha_j,
                "CMS: cập nhật author info", token,
            )
            commits.append({"type": "meta", "url": data.get("commit", {}).get("html_url", "")})
            updated_meta = True

    if not (updated_avatar or updated_meta):
        raise HTTPException(400, "nothing_to_update")

    return {
        "ok":             True,
        "updated_avatar": updated_avatar,
        "updated_meta":   updated_meta,
        "commits":        commits,
        "deploy_eta":     "1-2 phút (Pages auto-build)",
    }


# ============= CMS — Footer Countdown =============
CMS_COUNTDOWN_JSON_PATH = "data/footer-countdown.json"
_COUNTDOWN_DISPLAY_MODES = frozenset({"days", "days_hours_minutes", "full"})
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIME_RE = re.compile(r"^\d{2}:\d{2}$")


def _validate_countdown_payload(body: dict) -> dict:
    """Normalize + validate footer countdown config."""
    if not isinstance(body, dict):
        raise HTTPException(400, "invalid_json_body")
    enabled = bool(body.get("enabled", False))
    title = str(body.get("title", "")).strip()[:200]
    target_date = str(body.get("targetDate", "")).strip()
    target_time = str(body.get("targetTime", "00:00")).strip() or "00:00"
    timezone = str(body.get("timezone", "Asia/Ho_Chi_Minh")).strip()[:64] or "Asia/Ho_Chi_Minh"
    display_mode = str(body.get("displayMode", "days")).strip()
    prefix = str(body.get("footerTextPrefix", "Còn")).strip()[:50] or "Còn"
    suffix = str(body.get("footerTextSuffix", "nữa là tới")).strip()[:50] or "nữa là tới"

    if display_mode not in _COUNTDOWN_DISPLAY_MODES:
        raise HTTPException(400, "invalid_display_mode")
    if enabled:
        if not title:
            raise HTTPException(400, "title_required_when_enabled")
        if not target_date or not _DATE_RE.match(target_date):
            raise HTTPException(400, "invalid_target_date")
        if not _TIME_RE.match(target_time):
            raise HTTPException(400, "invalid_target_time")

    from datetime import datetime, timezone as dt_tz

    now = datetime.now(dt_tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "updated_at": now,
        "enabled": enabled,
        "title": title,
        "targetDate": target_date,
        "targetTime": target_time,
        "timezone": timezone,
        "displayMode": display_mode,
        "footerTextPrefix": prefix,
        "footerTextSuffix": suffix,
    }


@app.get("/cms/footer-countdown")
async def cms_footer_countdown_get(authorization: str = Header(default="")):
    """Đọc data/footer-countdown.json (auth required)."""
    session = await require_session(authorization)
    token = session.get("access_token")
    if not token:
        raise HTTPException(401, "no_access_token")
    async with httpx.AsyncClient(timeout=15.0) as client:
        _, text = await _gh_get_file(client, CMS_COUNTDOWN_JSON_PATH, token)
    if not text:
        return {"data": _validate_countdown_payload({"enabled": False})}
    try:
        return {"data": json.loads(text)}
    except json.JSONDecodeError:
        raise HTTPException(500, "countdown_json_corrupt")


@app.post("/cms/footer-countdown")
async def cms_footer_countdown_update(request: Request, authorization: str = Header(default="")):
    """Ghi data/footer-countdown.json từ admin UI."""
    session = await require_session(authorization)
    token = session.get("access_token")
    if not token:
        raise HTTPException(401, "no_access_token")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "invalid_json")
    payload = _validate_countdown_payload(body)
    new_text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    async with httpx.AsyncClient(timeout=30.0) as client:
        sha, _ = await _gh_get_file(client, CMS_COUNTDOWN_JSON_PATH, token)
        data = await _gh_put_file(
            client,
            CMS_COUNTDOWN_JSON_PATH,
            new_text,
            sha,
            "CMS: cập nhật footer countdown",
            token,
        )
    commit_url = data.get("commit", {}).get("html_url", "")
    return {
        "ok": True,
        "data": payload,
        "commit_url": commit_url,
        "deploy_eta": "1-2 phút (Pages auto-build)",
    }


# ============= CMS — Giscus Auto-Fetch IDs =============
@app.get("/cms/giscus/setup")
async def cms_giscus_setup(authorization: str = Header(default="")):
    """Fetch repo_id + discussion category IDs qua GraphQL → user khỏi vào giscus.app."""
    session = await require_session(authorization)
    token = session.get("access_token")
    if not token:
        raise HTTPException(401, "no_access_token")

    query = (
        "query { repository(owner: \"" + CMS_REPO_OWNER + "\", "
        "name: \"" + CMS_REPO_NAME + "\") { id "
        "discussionCategories(first: 25) { nodes { id name emoji } } } }"
    )
    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.post(
            "https://api.github.com/graphql",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "User-Agent": "zola-cms"},
            json={"query": query},
        )
    if res.status_code != 200:
        raise HTTPException(502, f"graphql_failed_{res.status_code}")
    data = res.json()
    if "errors" in data and data["errors"]:
        msg = data["errors"][0].get("message", "graphql_error")
        raise HTTPException(400, f"graphql: {msg}")
    repo = ((data.get("data") or {}).get("repository") or {})
    repo_id = repo.get("id", "")
    cats = ((repo.get("discussionCategories") or {}).get("nodes") or [])
    if not cats:
        raise HTTPException(400, "no_categories_check_discussions_enabled")
    suggested = next((c for c in cats if c.get("name") == "General"), cats[0])
    return {
        "repo_id": repo_id,
        "categories": [{"id": c.get("id"), "name": c.get("name"), "emoji": c.get("emoji")} for c in cats],
        "suggested": {
            "repo_id":     repo_id,
            "category_id": suggested.get("id"),
            "category":    suggested.get("name"),
        },
    }


# ============= CMS — Bulk Delete Posts =============
@app.post("/cms/posts/bulk-delete")
async def cms_bulk_delete(request: Request, authorization: str = Header(default="")):
    """
    Xoá hàng loạt posts trong 1 commit qua GraphQL createCommitOnBranch.
    Hiệu quả hơn REST DELETE từng file: 1 API call + 1 commit thay vì N.

    Body JSON: {slugs: ["slug1", "slug2", ...]} max 50 slugs/lần.

    Security:
    - require_session → có sid + access_token Redis-side
    - Mỗi slug validate qua _SLUG_RE (a-z0-9-) → chống path traversal
    - Path cố định content/posting/{slug}.md → user KHÔNG xoá ngoài thư mục
    - GraphQL parameterized variables → KHÔNG injection (giống prepared
      statement trong SQL: tách query khỏi data)
    """
    session = await require_session(authorization)
    token = session.get("access_token")
    if not token:
        raise HTTPException(401, "no_access_token")

    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(400, "invalid_json")

    slugs = body.get("slugs", [])
    if not isinstance(slugs, list) or len(slugs) == 0:
        raise HTTPException(400, "empty_slugs")
    if len(slugs) > 50:
        raise HTTPException(400, "too_many_slugs_max_50")

    # Validate + dedupe + build paths
    seen = set()
    paths = []
    for s in slugs:
        if not isinstance(s, str) or not _SLUG_RE.match(s):
            raise HTTPException(400, f"invalid_slug: {s[:50] if isinstance(s, str) else type(s).__name__}")
        if s in seen:
            continue
        seen.add(s)
        paths.append(f"{CMS_CONTENT_DIR}/{s}.md")

    gh_headers = {
        "Authorization":        f"Bearer {token}",
        "Accept":               "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent":           "zola-cms",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Fetch HEAD oid để pass expectedHeadOid (concurrent safety)
        try:
            sha_res = await client.get(
                f"https://api.github.com/repos/{CMS_REPO_OWNER}/{CMS_REPO_NAME}"
                f"/git/ref/heads/{CMS_REPO_BRANCH}",
                headers=gh_headers,
            )
        except httpx.HTTPError:
            raise HTTPException(502, "github_unreachable")
        if sha_res.status_code != 200:
            raise HTTPException(502, f"fetch_head_failed_{sha_res.status_code}")
        head_oid = (sha_res.json().get("object") or {}).get("sha", "")
        if not head_oid:
            raise HTTPException(502, "no_head_sha")

        # 2. GraphQL createCommitOnBranch — deletions array
        mutation = """
        mutation BulkDelete($input: CreateCommitOnBranchInput!) {
          createCommitOnBranch(input: $input) {
            commit { url oid }
          }
        }
        """
        variables = {
            "input": {
                "branch": {
                    "repositoryNameWithOwner": f"{CMS_REPO_OWNER}/{CMS_REPO_NAME}",
                    "branchName": CMS_REPO_BRANCH,
                },
                "message": {"headline": f"CMS: bulk xoá {len(paths)} bài viết"},
                "fileChanges": {"deletions": [{"path": p} for p in paths]},
                "expectedHeadOid": head_oid,
            }
        }
        try:
            gql_res = await client.post(
                "https://api.github.com/graphql",
                headers=gh_headers,
                json={"query": mutation, "variables": variables},
            )
        except httpx.HTTPError:
            raise HTTPException(502, "graphql_unreachable")

    if gql_res.status_code != 200:
        raise HTTPException(502, f"graphql_failed_{gql_res.status_code}")

    gql_data = gql_res.json()
    if "errors" in gql_data and gql_data["errors"]:
        err = gql_data["errors"][0].get("message", "graphql_error")
        # 422 = concurrent update (expectedHeadOid mismatch) — caller retry
        code = 422 if "expectedHeadOid" in err.lower() else 400
        raise HTTPException(code, f"graphql: {err}")

    commit_info = (((gql_data.get("data") or {}).get("createCommitOnBranch")) or {}).get("commit") or {}
    return {
        "ok":             True,
        "deleted_count":  len(paths),
        "deleted_slugs":  list(seen),
        "commit_url":     commit_info.get("url", ""),
        "commit_oid":     commit_info.get("oid", ""),
        "deploy_eta":     "1-2 phút (Pages auto-build)",
    }


# ============= RSS Checker =============
# Validate URL trước khi đưa cho feedparser — tránh SSRF qua scheme khác
# (file://, gopher://, internal IP). feedparser tự follow redirect, nên
# ngăn ngay từ input.
_VALID_URL_SCHEMES = {"http", "https"}
# Disallow internal/private hostnames — tránh SSRF tới Redis (127.0.0.1:6379)
# hoặc metadata service (169.254.169.254).
_BLOCKED_HOSTS = re.compile(
    r"^(localhost|127\.|10\.|172\.(1[6-9]|2\d|3[01])\.|192\.168\.|"
    r"169\.254\.|0\.|::1|fc|fd|fe80:)",
    re.IGNORECASE,
)


def _validate_rss_url(url: str) -> Optional[str]:
    """Return error message nếu URL không an toàn, None nếu OK."""
    if not url or len(url) > 2000:
        return "invalid_url"
    try:
        parsed = urlparse(url)
    except Exception:
        return "invalid_url"
    if parsed.scheme.lower() not in _VALID_URL_SCHEMES:
        return "invalid_scheme"
    host = (parsed.hostname or "").strip()
    if not host:
        return "invalid_host"
    if _BLOCKED_HOSTS.match(host):
        return "blocked_host"
    return None


@app.get("/api/check-rss")
async def check_rss(
    url: str = Query(..., description="RSS / Atom feed URL"),
    authorization: str = Header(default=""),
):
    """
    Parse RSS feed qua feedparser, trả 10 entry đầu (title + link).
    Yêu cầu session valid → chỉ admin đã login mới gọi được.

    Lưu ý privacy: KHÔNG log URL hoặc nội dung feed. Toàn bộ flow là
    in-memory, không write file, không Redis cache.
    """
    await require_session(authorization)

    err = _validate_rss_url(url)
    if err:
        raise HTTPException(400, err)

    # feedparser là sync API → chạy trong threadpool để không block event loop.
    # asyncio.to_thread tối thiểu vì feedparser có thể blocking 5-15s với
    # remote fetch + XML parse cho feed lớn.
    try:
        feed = await asyncio.wait_for(
            asyncio.to_thread(feedparser.parse, url),
            timeout=15.0,
        )
    except asyncio.TimeoutError:
        raise HTTPException(400, "timeout")
    except Exception:
        raise HTTPException(400, "parse_failed")

    # feedparser KHÔNG raise — trả object có .bozo=True khi malformed.
    # entries empty hoặc bozo + no entries → coi như fail (FE hiển thị
    # "không lấy được tin từ nguồn này").
    entries = getattr(feed, "entries", None) or []
    if not entries:
        raise HTTPException(400, "no_entries")

    items = []
    for e in entries[:10]:
        title = (e.get("title") or "").strip()
        link  = (e.get("link")  or "").strip()
        # Chỉ trả entry có cả title + link hợp lệ
        if title and link and link.startswith(("http://", "https://")):
            items.append({"title": title[:300], "link": link[:1000]})

    if not items:
        raise HTTPException(400, "no_valid_entries")

    # feed.feed.title cho title của source (vd "VnExpress - Tin nhanh")
    source_title = ""
    try:
        source_title = (feed.feed.get("title") or "").strip()[:200]
    except Exception:
        pass

    return {
        "source_title": source_title,
        "count":        len(items),
        "items":        items,
    }


# ============= Curated News Feeds (public, Redis cached) =============
# Map slug → source config. Type 'rss' dùng feedparser, type 'scrape'
# dùng BeautifulSoup. Thêm chuyên mục bằng cách append dict.
#
# ToS: scraping Trip.com nằm trong "vùng xám" — không thường vi phạm
# robots.txt nhưng có thể trái Terms of Service. Cache 24h để giảm số
# request tới source.
CURATED_FEEDS = {
    "du-lich": {
        # Chiến lược 2 lớp:
        #   1. Primary: Trip.com toplist Hàn Quốc (curl_cffi TLS-impersonate
        #      Chrome + parse __NEXT_DATA__). Content "cẩm nang/trải nghiệm"
        #      đúng phong cách user muốn.
        #   2. Fallback: VnExpress Du lịch RSS (feedparser) nếu Trip.com fail
        #      cho bất kỳ lý do gì → page vẫn có content.
        # Endpoint tự thử Trip.com trước, empty → switch sang RSS.
        "primary": {
            "url":    "https://www.trip.com/toplist/tripbest/south-korea-best-things-to-do-10070100042090/",
            "type":   "scrape_trip",
            "source": "Trip.com",
            "title":  "Top trải nghiệm Du lịch Hàn Quốc — Trip.com",
        },
        "fallback": {
            "url":    "https://vnexpress.net/rss/du-lich.rss",
            "type":   "rss",
            "source": "VnExpress",
            "title":  "Tin tức Du lịch — VnExpress",
        },
        "cache_ttl": 86400,  # 24h khi Trip.com OK, 30 phút khi fallback RSS
    },
}

NEWS_CACHE_TTL = int(os.getenv("NEWS_CACHE_TTL", "1800"))  # 30 phút default cho RSS

# IMDB scraper proxy (free public service) cho /api/movies.
# Docs: https://imdb.iamidiotareyoutoo.com/docs/index.html
# URL endpoint có thể đổi qua env mà không cần redeploy code.
# Default = search query 'trending' — nếu service có endpoint khác cho
# popular/top, set IMDB_API_URL trên Render.
IMDB_API_URL    = os.getenv(
    "IMDB_API_URL",
    # Default: IMDB calendar (upcoming releases). User có thể đổi qua env
    # sang proxy search như imdb.iamidiotareyoutoo.com/search?q=...
    "https://www.imdb.com/calendar/?ref_=tt_nv_menu",
)
IMDB_CACHE_TTL  = int(os.getenv("IMDB_CACHE_TTL", "86400"))  # 24h

# User-Agent giả lập browser thật. Trip.com block requests không có UA
# rõ ràng. KHÔNG fake quá nhiều header → một số site detect inconsistency.
SCRAPER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
}


def _extract_rss_thumbnail(entry) -> str:
    """
    RSS entry có thể có image ở nhiều field khác nhau:
    - <enclosure url=... type=image/*>
    - <media:content url=... medium=image>
    - <media:thumbnail url=...>
    - <img src=...> trong summary HTML (VnExpress style)
    """
    # 1. enclosures (RSS 2.0)
    for enc in entry.get("enclosures", []) or []:
        if isinstance(enc, dict):
            t = (enc.get("type") or "").lower()
            href = enc.get("href") or enc.get("url") or ""
            if t.startswith("image/") and href:
                return href
            if href and not t and href.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                return href

    # 2. media:content / media:thumbnail (MRSS)
    media = entry.get("media_content") or entry.get("media_thumbnail") or []
    if isinstance(media, list):
        for m in media:
            if isinstance(m, dict):
                url_v = m.get("url") or ""
                if url_v:
                    return url_v

    # 3. img src trong summary HTML — fallback nếu RSS không có media tag.
    # VnExpress nhúng <img> trong <description>.
    summary_html = entry.get("summary") or entry.get("description") or ""
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', summary_html, re.IGNORECASE)
    if m:
        return m.group(1)
    return ""


async def _fetch_and_parse_feed(url: str) -> list:
    """Fetch + parse RSS feed → list of dict {title, link, published, summary, thumbnail}."""
    feed = await asyncio.wait_for(
        asyncio.to_thread(feedparser.parse, url),
        timeout=15.0,
    )
    entries = getattr(feed, "entries", None) or []
    items = []
    for e in entries[:10]:
        title = (e.get("title") or "").strip()
        link  = (e.get("link")  or "").strip()
        if not (title and link and link.startswith(("http://", "https://"))):
            continue
        published = (
            e.get("published") or e.get("updated") or e.get("pubDate") or ""
        ).strip()
        summary = (e.get("summary") or e.get("description") or "").strip()
        thumbnail = _extract_rss_thumbnail(e)
        items.append({
            "title":     title[:300],
            "link":      link[:1000],
            "published": published[:50],
            "summary":   summary[:500],
            "thumbnail": thumbnail[:1000],
            "rating":    "",
        })
    return items


# ============= Web Scraper (Trip.com toplist) =============
def _truncate(text: str, n: int) -> str:
    return (text or "").strip()[:n]


def _normalize_link(href: str, base: str) -> str:
    """Resolve relative → absolute. Reject javascript:/data:/mailto: schemes."""
    if not href:
        return ""
    href = href.strip()
    if href.startswith(("javascript:", "data:", "mailto:")):
        return ""
    if href.startswith("//"):
        href = "https:" + href
    if href.startswith("/"):
        href = urljoin(base, href)
    if not href.startswith(("http://", "https://")):
        return ""
    return href


def _extract_jsonld_items(soup: BeautifulSoup, base_url: str) -> list:
    """
    Extract items từ JSON-LD ItemList schema — cách ổn định nhất.
    Trip.com embed ItemList structured data trong <script type="application/
    ld+json"> cho SEO. Selector này KHÔNG đổi theo CSS class lurng.
    """
    items = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        candidates = data if isinstance(data, list) else [data]
        for c in candidates:
            if not isinstance(c, dict):
                continue
            elements = c.get("itemListElement") or []
            for el in elements:
                if not isinstance(el, dict):
                    continue
                item = el.get("item") if isinstance(el.get("item"), dict) else el
                if not isinstance(item, dict):
                    continue
                title = _truncate(item.get("name"), 300)
                link  = _normalize_link(item.get("url") or "", base_url)
                if not (title and link):
                    continue
                # Image có thể là string, list, hoặc dict {url}
                img = item.get("image")
                if isinstance(img, dict):
                    img = img.get("url") or img.get("contentUrl") or ""
                elif isinstance(img, list) and img:
                    img = img[0] if isinstance(img[0], str) else ""
                if not isinstance(img, str):
                    img = ""
                rating = ""
                ar = item.get("aggregateRating")
                if isinstance(ar, dict):
                    rv = ar.get("ratingValue")
                    if rv is not None:
                        try:
                            rating = f"{float(rv):.1f}"
                        except (TypeError, ValueError):
                            rating = str(rv)[:5]
                items.append({
                    "title":       title,
                    "link":        link,
                    "summary":     _truncate(item.get("description"), 500),
                    "published":   "",
                    "thumbnail":   _normalize_link(img, base_url),
                    "rating":      rating,
                })
    return items


def _extract_fallback_items(soup: BeautifulSoup, base_url: str) -> list:
    """
    Fallback parser khi không có JSON-LD. Tìm <article>/<li>/<div> chứa
    heading + link. Less reliable nhưng đỡ phải fail hoàn toàn.
    """
    items = []
    seen_links = set()

    for tag in soup.find_all(["article", "li", "div"], limit=200):
        heading = tag.find(["h1", "h2", "h3", "h4"])
        link_tag = tag.find("a", href=True)
        if not (heading and link_tag):
            continue

        title = _truncate(heading.get_text(separator=" ", strip=True), 300)
        link  = _normalize_link(link_tag.get("href", ""), base_url)
        if not (title and link) or link in seen_links:
            continue
        if len(title) < 8 or title.lower() in {"home", "more", "next", "previous"}:
            continue
        seen_links.add(link)

        img_tag = tag.find("img")
        thumbnail = ""
        if img_tag:
            thumbnail = (
                img_tag.get("src") or img_tag.get("data-src")
                or img_tag.get("data-original") or ""
            )
            thumbnail = _normalize_link(thumbnail, base_url)

        summary = ""
        for p in tag.find_all(["p", "span", "div"], limit=5):
            if p == heading or heading in p.find_all():
                continue
            text = p.get_text(separator=" ", strip=True)
            if 20 <= len(text) <= 500:
                summary = _truncate(text, 500)
                break

        items.append({
            "title":     title,
            "link":      link,
            "summary":   summary,
            "published": "",
            "thumbnail": thumbnail,
            "rating":    "",
        })
        if len(items) >= 30:
            break
    return items


async def _scrape_toplist(url: str) -> list:
    """
    Fetch HTML via httpx với UA giả browser → parse BeautifulSoup (lxml).
    Ưu tiên JSON-LD → fallback HTML pattern. Trả tối đa 10 items.
    """
    async with httpx.AsyncClient(
        headers=SCRAPER_HEADERS,
        timeout=20.0,
        follow_redirects=True,
    ) as client:
        res = await client.get(url)
    if res.status_code != 200:
        return []

    soup = await asyncio.to_thread(BeautifulSoup, res.text, "lxml")

    items = _extract_jsonld_items(soup, url)
    if not items:
        items = _extract_fallback_items(soup, url)

    seen = set()
    unique = []
    for it in items:
        if it["link"] in seen:
            continue
        seen.add(it["link"])
        unique.append(it)
    return unique[:10]


# ============= Trip.com TLS-Impersonated Scrape =============
# httpx + BeautifulSoup thông thường thất bại với Trip.com vì:
#  1. Cloudflare/Akamai phát hiện TLS fingerprint của Python → block
#  2. Trang là Next.js SPA → HTML server-render chỉ là skeleton, content
#     bake vào <script id="__NEXT_DATA__"> JSON cần parse riêng
#
# Giải pháp: curl_cffi giả lập Chrome TLS exactly → vượt Cloudflare,
# rồi tìm __NEXT_DATA__ JSON trong HTML và walk recursive để extract items.

# Import lazy để tránh hard fail nếu curl_cffi không build được trên platform.
try:
    from curl_cffi import requests as curl_requests
    _CURL_CFFI_AVAILABLE = True
except ImportError:
    curl_requests = None
    _CURL_CFFI_AVAILABLE = False


def _walk_extract_toplist(node, base_url: str, items: list, depth: int = 0) -> None:
    """
    Walk recursive qua JSON tree tìm các array chứa entry với 'name|title' +
    'url|link' + 'description|summary'. Đây là pattern chung của toplist
    Trip.com bake trong __NEXT_DATA__.
    Cap depth=8 để không infinite loop với circular refs.
    """
    if depth > 8 or len(items) >= 30:
        return

    if isinstance(node, list):
        for child in node:
            # Detect entry-shape: dict có title-like + url-like
            if isinstance(child, dict):
                title = (
                    child.get("name") or child.get("title")
                    or child.get("productName") or child.get("poiName")
                    or child.get("displayName") or ""
                )
                link_raw = (
                    child.get("url") or child.get("link") or child.get("detailUrl")
                    or child.get("href") or child.get("productUrl") or ""
                )
                title = str(title).strip() if title else ""
                link = _normalize_link(str(link_raw), base_url) if link_raw else ""
                if title and link and len(title) >= 5:
                    img_raw = (
                        child.get("imageUrl") or child.get("image")
                        or child.get("cover") or child.get("pic") or ""
                    )
                    if isinstance(img_raw, dict):
                        img_raw = img_raw.get("url") or img_raw.get("dynamicUrl") or ""
                    img = _normalize_link(str(img_raw or ""), base_url)

                    desc = (
                        child.get("description") or child.get("intro")
                        or child.get("summary") or child.get("subtitle") or ""
                    )
                    rating_raw = (
                        child.get("rating") or child.get("score")
                        or child.get("commentScore") or child.get("avgScore") or ""
                    )
                    rating = ""
                    if rating_raw not in ("", None):
                        try:
                            rating = f"{float(rating_raw):.1f}"
                        except (TypeError, ValueError):
                            rating = str(rating_raw)[:5]

                    items.append({
                        "title":     title[:300],
                        "link":      link[:1000],
                        "summary":   str(desc).strip()[:500],
                        "published": "",
                        "thumbnail": img,
                        "rating":    rating,
                    })
            _walk_extract_toplist(child, base_url, items, depth + 1)
    elif isinstance(node, dict):
        for v in node.values():
            _walk_extract_toplist(v, base_url, items, depth + 1)


async def _scrape_trip_via_curl_cffi(url: str) -> list:
    """
    TLS-impersonated fetch + __NEXT_DATA__ extraction cho Trip.com.

    Flow:
      1. curl_cffi GET với impersonate=chrome131 → vượt Cloudflare TLS detect
      2. Tìm <script id="__NEXT_DATA__">{...}</script> trong HTML
      3. Parse JSON, walk recursive tìm array có entry shape title+link
      4. Dedupe theo link, trả tối đa 10

    Nếu curl_cffi không available (build fail), trả [] silent — fallback
    về _scrape_toplist (httpx + BS).
    """
    if not _CURL_CFFI_AVAILABLE:
        return []

    def _sync_fetch():
        # impersonate='chrome131' = full TLS fingerprint mới nhất (curl_cffi 0.7+)
        return curl_requests.get(
            url,
            impersonate="chrome131",
            headers={
                "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7,ko-KR;q=0.6",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Referer": "https://www.trip.com/",
                "Cache-Control": "no-cache",
            },
            timeout=25,
        )

    try:
        res = await asyncio.to_thread(_sync_fetch)
    except Exception:
        return []
    if res.status_code != 200:
        return []

    html = res.text

    # Tìm __NEXT_DATA__ — Next.js bake initial state ở script id này
    m = re.search(
        r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        html, re.DOTALL,
    )
    if not m:
        # Fallback: tìm bất kỳ <script application/json> nào lớn (>5KB)
        scripts = re.findall(
            r'<script[^>]+type=["\']application/json["\'][^>]*>(.*?)</script>',
            html, re.DOTALL,
        )
        scripts = [s for s in scripts if len(s) > 5000]
        if not scripts:
            return []
        # Try parse từng cái, dùng cái nào có items hợp lệ
        for s in scripts:
            try:
                data = json.loads(s)
            except json.JSONDecodeError:
                continue
            items: list = []
            _walk_extract_toplist(data, url, items)
            if items:
                # Dedupe by link, giữ thứ tự
                seen = set()
                unique = []
                for it in items:
                    if it["link"] in seen:
                        continue
                    seen.add(it["link"])
                    unique.append(it)
                return unique[:10]
        return []

    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return []

    items: list = []
    _walk_extract_toplist(data, url, items)

    seen = set()
    unique = []
    for it in items:
        if it["link"] in seen:
            continue
        seen.add(it["link"])
        unique.append(it)
    return unique[:10]


async def _fetch_for_config(cfg: dict) -> list:
    """Dispatch theo type. Wrap exception → trả [] để outer xử fallback."""
    try:
        t = cfg.get("type", "rss")
        if t == "rss":
            return await _fetch_and_parse_feed(cfg["url"])
        elif t == "scrape":
            return await _scrape_toplist(cfg["url"])
        elif t == "scrape_trip":
            return await _scrape_trip_via_curl_cffi(cfg["url"])
        else:
            return []
    except Exception:
        return []


@app.get("/api/news/{slug}")
async def curated_news(slug: str):
    """
    Trả tối đa 10 items từ curated source.

    Config có thể là:
      - Flat: {url, type, source, title, cache_ttl}
      - Layered: {primary: {...}, fallback: {...}, cache_ttl}
        → thử primary trước (Trip.com), empty → fallback (VnExpress RSS)

    Cache key bao gồm source ACTUAL trả → nếu fallback chạy, cache đúng nguồn.

    Lỗi/empty → trả 200 với error code, FE graceful degrade.
    """
    feed_cfg = CURATED_FEEDS.get(slug)
    if not feed_cfg:
        raise HTTPException(404, "feed_not_found")

    # Layered config check
    is_layered = "primary" in feed_cfg and "fallback" in feed_cfg

    r = await get_redis()

    # Cache key dùng slug + active source (sẽ biết sau khi fetch xong).
    # Cache lookup thử cả 2 source cho layered config.
    candidate_sources = []
    if is_layered:
        candidate_sources = [feed_cfg["primary"]["source"], feed_cfg["fallback"]["source"]]
    else:
        candidate_sources = [feed_cfg["source"]]

    for src in candidate_sources:
        source_id = re.sub(r"[^a-z0-9]+", "_", src.lower()).strip("_")
        cache_key = f"news_cache:{slug}:{source_id}"
        cached = await r.get(cache_key)
        if cached:
            try:
                data = json.loads(cached)
                if data.get("items"):  # chỉ dùng cache nếu có items thật
                    data["from_cache"] = True
                    return data
            except (json.JSONDecodeError, KeyError):
                continue

    # Cache miss → fetch
    if is_layered:
        primary_cfg = feed_cfg["primary"]
        items = await _fetch_for_config(primary_cfg)
        active_cfg = primary_cfg
        if not items:
            fallback_cfg = feed_cfg["fallback"]
            items = await _fetch_for_config(fallback_cfg)
            active_cfg = fallback_cfg
    else:
        items = await _fetch_for_config(feed_cfg)
        active_cfg = feed_cfg

    payload = {
        "source": active_cfg["source"],
        "title":  active_cfg["title"],
        "count":  len(items),
        "items":  items,
    }

    if not items:
        # Empty → cache 5 phút để tránh hammer source khi tạm down
        source_id = re.sub(r"[^a-z0-9]+", "_", active_cfg["source"].lower()).strip("_")
        await r.setex(
            f"news_cache:{slug}:{source_id}",
            300,
            json.dumps(payload, ensure_ascii=False),
        )
        payload["from_cache"] = False
        payload["error"] = "fetch_failed"
        return payload

    # Có items → cache theo TTL config (24h Trip.com, 30m RSS fallback)
    default_ttl = feed_cfg.get("cache_ttl") or NEWS_CACHE_TTL
    source_id = re.sub(r"[^a-z0-9]+", "_", active_cfg["source"].lower()).strip("_")
    await r.setex(
        f"news_cache:{slug}:{source_id}",
        default_ttl,
        json.dumps(payload, ensure_ascii=False),
    )
    payload["from_cache"] = False
    return payload


# ============= Misc =============
# ============= Secure Reports (Redis-stored, OAuth-gated) =============
# Report .md KHÔNG nằm trong repo public → chỉ tải được qua các endpoint dưới
# sau khi require_session pass (OAuth GitHub + email whitelist). Đây là chặn
# THẬT (khác UX-gate cũ). Lưu trong Redis:
#   report:doc:{filename}  → nội dung .md (string)
#   report:meta            → hash: field=filename, value=json{created_at,size,preview}
_REPORT_FILE_RE   = re.compile(r"^[a-z0-9][a-z0-9._-]{1,100}\.md$", re.IGNORECASE)
_REPORT_DOC_PREFIX = "report:doc:"
_REPORT_META_KEY   = "report:meta"
_MAX_REPORT_BYTES  = 500_000


def _valid_report_name(name: str) -> str:
    """Chặn path traversal: chỉ cho tên file .md an toàn, không '/' hay '..'."""
    name = (name or "").strip()
    if "/" in name or ".." in name or not _REPORT_FILE_RE.match(name):
        raise HTTPException(400, "invalid_filename")
    return name


@app.get("/reports")
async def reports_list(authorization: str = Header(default="")):
    """List metadata mọi report (auth required). KHÔNG trả nội dung đầy đủ."""
    await require_session(authorization)
    r = await get_redis()
    meta = await r.hgetall(_REPORT_META_KEY)
    items = []
    for fn, raw in meta.items():
        try:
            m = json.loads(raw)
        except json.JSONDecodeError:
            m = {}
        items.append({
            "filename":   fn,
            "created_at": m.get("created_at", ""),
            "size":       m.get("size", 0),
            "preview":    m.get("preview", ""),
        })
    items.sort(key=lambda x: x["created_at"], reverse=True)
    return {"reports": items, "count": len(items)}


@app.get("/reports/{filename}")
async def reports_get(filename: str, authorization: str = Header(default="")):
    """Trả nội dung .md của 1 report (auth required). 404 nếu không có."""
    await require_session(authorization)
    fn = _valid_report_name(filename)
    r = await get_redis()
    content = await r.get(_REPORT_DOC_PREFIX + fn)
    if content is None:
        raise HTTPException(404, "report_not_found")
    meta_raw = await r.hget(_REPORT_META_KEY, fn)
    meta = json.loads(meta_raw) if meta_raw else {}
    return {"filename": fn, "content": content, "created_at": meta.get("created_at", "")}


@app.post("/reports")
async def reports_put(request: Request, authorization: str = Header(default="")):
    """
    Tạo/ghi đè 1 report (auth required). Dùng cho phím tắt `??` đẩy báo cáo lên
    backend thay vì commit .md vào repo public.

    Body JSON: {filename, content, created_at?}
    """
    await require_session(authorization)
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(400, "invalid_json")

    fn = _valid_report_name(str(body.get("filename", "")))
    content = body.get("content", "")
    if not isinstance(content, str) or not content.strip():
        raise HTTPException(400, "empty_content")
    if len(content.encode("utf-8")) > _MAX_REPORT_BYTES:
        raise HTTPException(400, "content_too_large")

    created_at = str(body.get("created_at", "")).strip() or \
        datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    preview = re.sub(r"\s+", " ", content).strip()[:240]

    r = await get_redis()
    await r.set(_REPORT_DOC_PREFIX + fn, content)
    await r.hset(_REPORT_META_KEY, fn, json.dumps({
        "created_at": created_at,
        "size":       len(content.encode("utf-8")),
        "preview":    preview,
    }))
    return {"ok": True, "filename": fn, "created_at": created_at}


@app.post("/reports/delete")
async def reports_delete(request: Request, authorization: str = Header(default="")):
    """Xoá 1 report (auth required). POST (không DELETE) để khớp CORS allow-methods."""
    await require_session(authorization)
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(400, "invalid_json")
    fn = _valid_report_name(str(body.get("filename", "")))
    r = await get_redis()
    await r.delete(_REPORT_DOC_PREFIX + fn)
    await r.hdel(_REPORT_META_KEY, fn)
    return {"ok": True, "filename": fn}


@app.get("/")
async def root():
    return {
        "service": "blog-backend",
        "version": "2.2.0",
        "features": {
            "visitor_counter": True,
            "github_oauth":    bool(GH_CLIENT_ID and GH_CLIENT_SECRET),
            "gsc_oauth":       bool(os.getenv("GSC_CLIENT_ID") and os.getenv("GSC_CLIENT_SECRET")),
            "rss_checker":     True,
        },
        "endpoints": {
            "POST /track":        "Visitor counter increment",
            "GET  /stats":        "Visitor counter total",
            "GET  /auth/login":   "Start GitHub OAuth flow",
            "GET  /auth/callback":"OAuth callback (GitHub uses this)",
            "GET  /auth/me":      "Validate session (Bearer)",
            "POST /auth/logout":  "Destroy session (Bearer)",
            "GET  /api/check-rss":"Parse RSS feed (auth required)",
            "GET  /api/news/{slug}":"Curated news (Redis cached, public)",
            "POST /cms/save-post":"Publish post lên blog GitHub (auth required)",
            "GET  /api/categories/list":"Danh sách categories từ repo (auth required)",
            "POST /api/categories/add":"Thêm category mới (auth required)",
            "GET  /api/movies":"IMDB movies via scraper proxy (Redis cached 24h, public)",
            "GET  /reports":      "List report metadata (auth required)",
            "GET  /reports/{file}":"Download report .md content (auth required)",
            "POST /reports":      "Create/overwrite a report (auth required)",
            "POST /reports/delete":"Delete a report (auth required)",
            "GET  /gsc/metrics":  "Cached GSC metrics bundle (public, 20m cache)",
            "GET  /gsc/status":   "GSC connection status",
            "GET  /gsc/oauth/start":"Start Google GSC OAuth (auth required)",
            "GET  /gsc/properties":"List GSC site properties (auth required)",
            "POST /gsc/property": "Set active GSC property (auth required)",
            "POST /gsc/disconnect":"Revoke GSC connection (auth required)",
        },
    }
