"""AI Writer Dispatch — routes write requests through GitHub repository_dispatch.

Frontend → POST /cms/ai-writer-dispatch (authenticated CMS session)
          → GitHub API repository_dispatch (event_type: ai_writer_create_post)
          → GitHub Actions workflow → AI generation → branch + PR.

Keeps the GitHub token server-side; the browser never sees it.
"""

from __future__ import annotations

import json
import os
from typing import Any, Awaitable, Callable, Optional

import httpx
from fastapi import APIRouter, Cookie, Header, HTTPException, Request

router = APIRouter()

CMS_REPO_OWNER = os.getenv("CMS_REPO_OWNER", "Banhang-Chogao")
CMS_REPO_NAME = os.getenv("CMS_REPO_NAME", "zola")

_get_token: Optional[Callable[[str, Optional[str]], Awaitable[str]]] = None


def configure(get_token: Callable[[str, Optional[str]], Awaitable[str]]) -> None:
    global _get_token
    _get_token = get_token


async def _github_token(authorization: str, cookie_sid: Optional[str] = None) -> str:
    if _get_token is None:
        raise HTTPException(503, "dispatch_not_configured")
    return await _get_token(authorization, cookie_sid)


@router.post("/cms/ai-writer-dispatch")
async def ai_writer_dispatch(
    request: Request,
    authorization: str = Header(default=""),
    cookie_sid: Optional[str] = Cookie(default=None, alias="zola_cms_sid"),
) -> dict[str, Any]:
    """Receive a write request from the frontend and forward it to GitHub Actions.

    Request body:
    {
        "prompt": "...",      // Full prompt from content creator (required)
        "topic": "...",       // Topic/subject (required)
        "category": "Tất cả",  // Primary category
        "pricing": "free",    // "free" or "paid"
        "brief": "",          // User's brief
        "ux_brief": "",       // UX preferences
        "series_id": ""       // Optional series ID
    }
    """
    # 1. Authenticate (admin only).
    token = await _github_token(authorization, cookie_sid)

    # 2. Parse request body.
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(400, "invalid_json")

    prompt = str(body.get("prompt", "")).strip()
    topic = str(body.get("topic", "")).strip()
    if not prompt:
        raise HTTPException(400, "Thiếu prompt — hãy bấm Lưu trước để sinh prompt.")
    if not topic:
        raise HTTPException(400, "Thiếu chủ đề bài viết.")

    # 3. Build client payload for the workflow.
    client_payload: dict[str, str] = {
        "prompt": prompt,
        "topic": topic,
        "category": str(body.get("category", "Tất cả")).strip(),
        "pricing": str(body.get("pricing", "free")).strip(),
        "brief": str(body.get("brief", "")).strip()[:2000],
        "ux_brief": str(body.get("ux_brief", "")).strip()[:1000],
        "series_id": str(body.get("series_id", "")).strip()[:60],
    }

    # 4. Dispatch to GitHub Actions via repository_dispatch API.
    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.post(
            f"https://api.github.com/repos/{CMS_REPO_OWNER}/{CMS_REPO_NAME}/dispatches",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "zola-ai-writer-dispatch",
            },
            json={
                "event_type": "ai_writer_create_post",
                "client_payload": client_payload,
            },
        )

    if res.status_code not in (200, 201, 204):
        err = {}
        try:
            err = res.json()
        except json.JSONDecodeError:
            pass
        detail = err.get("message", f"HTTP {res.status_code}")
        raise HTTPException(502, f"github_dispatch_failed: {detail}")

    return {
        "ok": True,
        "message": "Đã gửi yêu cầu viết bài, PR sẽ được tạo sau vài phút.",
    }
