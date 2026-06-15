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

import asyncio
import base64
import json
import os
import re
import secrets
from typing import Optional
from urllib.parse import urlencode, urljoin, urlparse

import feedparser
import httpx
from bs4 import BeautifulSoup
from fastapi import FastAPI, Header, HTTPException, Query, Request
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
# Base path component của BLOG_URL — vd "/zola". Dùng để strip khi return_to
# từ client đã có prefix này (do location.pathname trên GitHub Pages bao gồm
# subpath). Tránh URL kép kiểu /zola/zola/baochi/.
_BLOG_BASE_PATH = urlparse(BLOG_URL).path.rstrip("/")

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
    return json.loads(raw)


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

# Slug hợp lệ: a-z + 0-9 + dash, 2-80 ký tự. Khớp pattern Zola slug.
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,79}$")


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
    api_url = (
        f"https://api.github.com/repos/{CMS_REPO_OWNER}/{CMS_REPO_NAME}"
        f"/contents/{path}"
    )
    gh_headers = {
        "Authorization":         f"Bearer {access_token}",
        "Accept":                "application/vnd.github+json",
        "X-GitHub-Api-Version":  "2022-11-28",
        "User-Agent":            "zola-cms-publish",
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        # 1. GET hiện trạng để biết sha (cho update). 404 → file mới.
        existing_sha = None
        try:
            head = await client.get(
                api_url,
                params={"ref": CMS_REPO_BRANCH},
                headers=gh_headers,
            )
            if head.status_code == 200:
                existing_sha = head.json().get("sha")
            elif head.status_code not in (200, 404):
                raise HTTPException(502, f"github_check_failed: {head.status_code}")
        except httpx.HTTPError:
            raise HTTPException(502, "github_unreachable")

        # 2. PUT create or update
        payload = {
            "message": message[:200],
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            "branch":  CMS_REPO_BRANCH,
        }
        if existing_sha:
            payload["sha"] = existing_sha

        try:
            put_res = await client.put(api_url, headers=gh_headers, json=payload)
        except httpx.HTTPError:
            raise HTTPException(502, "github_unreachable")

        if put_res.status_code not in (200, 201):
            err_body = {}
            try:
                err_body = put_res.json()
            except json.JSONDecodeError:
                pass
            err_msg = err_body.get("message", "github_api_error")
            # 403 thường = scope thiếu (cần public_repo). 422 = sha conflict.
            raise HTTPException(
                put_res.status_code if put_res.status_code in (403, 422) else 502,
                f"github_api: {err_msg}",
            )

        data = put_res.json()
        return {
            "ok":         True,
            "action":     "updated" if existing_sha else "created",
            "path":       path,
            "commit_url": data.get("commit", {}).get("html_url", ""),
            "commit_sha": data.get("commit", {}).get("sha", ""),
            "deploy_eta": "1-2 phút (GitHub Actions auto-build + deploy)",
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
@app.get("/")
async def root():
    return {
        "service": "blog-backend",
        "version": "2.1.0",
        "features": {
            "visitor_counter": True,
            "github_oauth":    bool(GH_CLIENT_ID and GH_CLIENT_SECRET),
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
        },
    }
