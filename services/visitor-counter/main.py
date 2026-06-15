"""
Blog Visitor Counter — minimal FastAPI service backed by Redis.

Endpoints:
  POST /track   → increment counter if request là user thật (không phải bot)
  GET  /stats   → trả về tổng count hiện tại
  GET  /        → health check + endpoint discovery

Env vars (set trên Render/Railway dashboard):
  REDIS_URL     — redis://default:password@host:port (bắt buộc)
  CORS_ORIGIN   — origin được phép gọi API (default: blog GitHub Pages URL)
  COUNTER_KEY   — Redis key chứa count (default: 'blog:visitors')

Triết lý: stateless, async, single Redis key. Không database SQL, không
session. INCR là atomic op nên không cần lock — concurrent track requests
xử lý đúng cả khi cả triệu visitor cùng lúc.
"""

import os
import re
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis


# ============= Configuration =============
# Đọc từ env vars — KHÔNG hardcode credentials.
REDIS_URL   = os.getenv("REDIS_URL", "redis://localhost:6379")
CORS_ORIGIN = os.getenv("CORS_ORIGIN", "https://banhang-chogao.github.io")
COUNTER_KEY = os.getenv("COUNTER_KEY", "blog:visitors")


# ============= Bot Detection =============
# Common crawler/bot signatures. Regex single-pass cho hiệu năng.
# Coverage: search engines, social previews, monitors, scrapers, libraries.
BOT_PATTERNS = re.compile(
    r"bot|crawler|spider|crawl|slurp|mediapartners|preview|fetcher|"
    r"facebookexternalhit|whatsapp|telegram|twitterbot|linkedinbot|"
    r"discordbot|pingdom|uptime|monitor|headless|"
    r"curl|wget|python-requests|axios|node-fetch|java/|go-http-client",
    re.IGNORECASE,
)


def is_bot(user_agent: str) -> bool:
    """Detect common bot/crawler User-Agent. Empty/short UA cũng coi là bot."""
    if not user_agent or len(user_agent) < 10:
        return True
    return bool(BOT_PATTERNS.search(user_agent))


# ============= FastAPI App =============
app = FastAPI(
    title="Blog Visitor Counter",
    version="1.0.0",
    # Disable /docs + /redoc trong production — service public, không cần expose schema
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# CORS middleware — chỉ cho phép origin của blog gọi API.
# Tránh ai khác abuse API từ domain khác.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[CORS_ORIGIN],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Redis client — singleton, async, reuse connection pool.
_redis_client: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    """Lazy init Redis client. decode_responses=True → return str thay vì bytes."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


# ============= Endpoints =============
@app.post("/track")
async def track(request: Request):
    """
    Tăng visitor count nếu request từ user thật.
    Bot → silent skip (return 200 nhưng counted=False) để không tiết lộ
    detection logic cho scrapers.
    """
    ua = request.headers.get("user-agent", "")
    if is_bot(ua):
        return {"ok": True, "counted": False}

    r = await get_redis()
    new_count = await r.incr(COUNTER_KEY)
    return {"ok": True, "counted": True, "count": new_count}


@app.get("/stats")
async def stats():
    """Trả về count hiện tại. Key chưa tồn tại → 0."""
    r = await get_redis()
    raw = await r.get(COUNTER_KEY)
    count = int(raw) if raw else 0
    return {"count": count}


@app.get("/")
async def root():
    """Health check + endpoint discovery."""
    return {
        "service": "visitor-counter",
        "version": "1.0.0",
        "endpoints": {
            "POST /track": "Increment counter (bot filtered)",
            "GET /stats": "Get current count",
        },
    }
