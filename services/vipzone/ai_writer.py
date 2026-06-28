"""AI Blog Writer — generate & publish blog posts via AI provider.

POST /api/content-creator/write-blog
  Auth: admin CMS session (Bearer token or HttpOnly cookie).
  Input: prompt, topic, category, pricing, series_id, brief, ux_brief, watermark.
  Calls an OpenAI-compatible AI provider, validates the output,
  commits the post to a feature branch, creates a PR, returns the PR URL.

When the AI API key is unset (CONTENT_CREATOR_AI_API_KEY missing) the endpoint
returns a 501 with ``{ok:false, reason:"ai_not_configured"}`` — the frontend
falls back to the manual-copy flow without losing the user's prompt.
"""

from __future__ import annotations

import base64
import json
import os
import re
import random
import string
import time
from datetime import datetime, timezone
from typing import Any, Callable, Optional
from zoneinfo import ZoneInfo

import httpx
from fastapi import APIRouter, Cookie, Header, HTTPException, Request

router = APIRouter()

# ── Config ──────────────────────────────────────────────────────────────
AI_API_KEY = os.getenv("CONTENT_CREATOR_AI_API_KEY", "")
AI_API_URL = os.getenv(
    "CONTENT_CREATOR_AI_URL",
    "https://api.openai.com/v1/chat/completions",
)
AI_MODEL = os.getenv("CONTENT_CREATOR_AI_MODEL", "gpt-4o-mini")
# Fallback when no AI key — allows the endpoint to return a graceful 501.
# The frontend shows a friendly "API chưa được cấu hình" message.

CMS_REPO_OWNER = os.getenv("CMS_REPO_OWNER", "Banhang-Chogao")
CMS_REPO_NAME = os.getenv("CMS_REPO_NAME", "zola")
CMS_REPO_BRANCH = os.getenv("CMS_REPO_BRANCH", "main")
CMS_CONTENT_DIR = "content/posting"

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,79}$")
_FM_SPLIT_RE = re.compile(r"^\+\+\+\s*\n(.*?)\n\+\+\+\s*\n?(.*)", re.DOTALL)

# ── Auth injection (same pattern as cms_repo) ──────────────────────────
_get_token: Optional[Callable[[str, Optional[str]], Awaitable[str]]] = None


def configure(get_token: Callable[[str, Optional[str]], Awaitable[str]]) -> None:
    global _get_token
    _get_token = get_token


async def _token(authorization: str, cookie_sid: Optional[str] = None) -> str:
    if _get_token is None:
        raise HTTPException(503, "ai_writer_not_configured")
    return await _get_token(authorization, cookie_sid)


# ── GitHub helpers ─────────────────────────────────────────────────────
def _gh_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "zola-ai-writer",
    }


async def _gh_get_main_sha(client: httpx.AsyncClient, token: str) -> str:
    """Get the latest commit SHA of the main branch."""
    res = await client.get(
        f"https://api.github.com/repos/{CMS_REPO_OWNER}/{CMS_REPO_NAME}/git/ref/heads/{CMS_REPO_BRANCH}",
        headers=_gh_headers(token),
    )
    if res.status_code != 200:
        raise HTTPException(502, "github_ref_fetch_failed")
    obj = res.json().get("object") or {}
    return obj.get("sha", "")


async def _gh_create_branch(
    client: httpx.AsyncClient, branch: str, sha: str, token: str
) -> None:
    """Create a new branch from the given SHA."""
    res = await client.post(
        f"https://api.github.com/repos/{CMS_REPO_OWNER}/{CMS_REPO_NAME}/git/refs",
        headers=_gh_headers(token),
        json={"ref": f"refs/heads/{branch}", "sha": sha},
    )
    if res.status_code not in (201, 422):
        # 422 means branch already exists — acceptable.
        raise HTTPException(502, "github_branch_create_failed")


async def _gh_put_file(
    client: httpx.AsyncClient,
    path: str,
    content: str,
    branch: str,
    message: str,
    token: str,
) -> dict:
    """Create a file on the given branch via Contents API."""
    payload = {
        "message": message[:200],
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": branch,
    }
    res = await client.put(
        f"https://api.github.com/repos/{CMS_REPO_OWNER}/{CMS_REPO_NAME}/contents/{path}",
        headers=_gh_headers(token),
        json=payload,
    )
    if res.status_code not in (200, 201):
        err = {}
        try:
            err = res.json()
        except json.JSONDecodeError:
            pass
        raise HTTPException(
            res.status_code if res.status_code in (403, 422) else 502,
            f"github_api: {err.get('message', 'error')}",
        )
    return res.json()


async def _gh_create_pr(
    client: httpx.AsyncClient,
    branch: str,
    title: str,
    body: str,
    token: str,
) -> dict:
    """Create a PR from the branch to main."""
    res = await client.post(
        f"https://api.github.com/repos/{CMS_REPO_OWNER}/{CMS_REPO_NAME}/pulls",
        headers=_gh_headers(token),
        json={
            "title": title[:256],
            "head": branch,
            "base": CMS_REPO_BRANCH,
            "body": body[:65536],
        },
    )
    if res.status_code not in (200, 201):
        err = {}
        try:
            err = res.json()
        except json.JSONDecodeError:
            pass
        raise HTTPException(
            res.status_code if res.status_code in (403, 422) else 502,
            f"github_pr: {err.get('message', 'error')}",
        )
    return res.json()


# ── AI call ────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = """\
Bạn là cây viết SEO tiếng Việt chuyên nghiệp cho blog.

Viết bài blog hoàn chỉnh theo Zola markdown (TOML frontmatter giữa các dấu +++).

### Yêu cầu frontmatter (bắt buộc)
- title: ≤60 ký tự, tiếng Việt, chứa từ khoá chính
- description: ≤155 ký tự, chứa từ khoá
- date: hôm nay theo YYYY-MM-DD
- slug: URL-friendly, chữ thường không dấu, dùng gạch ngang
- draft = false
- template = "page.html"
- [taxonomies] categories = ["Tất cả", ...] (ít nhất "Tất cả")
- [taxonomies] tags = ["...", "..."] (ít nhất 3 tag)
- [extra] seo_keyword = "..."
- [extra] toc = true
- [[extra.faq]] với 3-8 câu hỏi, mỗi câu có q = "..." / a = "..."

### Yêu cầu nội dung
- ≥800 từ (bài chuẩn ≥1500 từ), đoạn ngắn, mobile-first
- Có H2, H3, bullet list, bảng nếu phù hợp
- Internal link (dạng /slug-cua-bai/) ≥3 cái
- External link uy tín ≥1 cái (Wikipedia, trang chính phủ, báo lớn)
- KHÔNG dùng ảnh ngoài (không URL http/https trong dấu ![]())
- FAQ cuối bài (3-8 câu)
- Kết luận + CTA cuối bài
- Giọng văn tự nhiên, blogger thật, không AI fluff
- Tuân thủ chuẩn SEO: từ khoá xuất hiện ở title, đoạn đầu, 1 H2, kết bài

### KHÔNG được
- Dùng ảnh từ URL ngoài
- Chèn script hay iframe
- Dùng từ khoá nhồi nhét
- Viết hoa tuỳ tiện
- Dùng cụm AI như "không chỉ… mà còn", "trong bối cảnh hiện nay"
"""


async def _call_ai(prompt: str) -> str:
    """Call the OpenAI-compatible AI provider and return the markdown string."""
    if not AI_API_KEY:
        raise HTTPException(
            501,
            "AI API chưa được cấu hình (CONTENT_CREATOR_AI_API_KEY). "
            "Hãy copy prompt thủ công.",
        )
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    payload = {
        "model": AI_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 8192,
    }
    timeout = httpx.Timeout(180.0, connect=15.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            res = await client.post(
                AI_API_URL,
                headers={
                    "Authorization": f"Bearer {AI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        except httpx.TimeoutException:
            raise HTTPException(504, "AI provider timeout — hãy thử lại sau.")
        except httpx.HTTPError as exc:
            raise HTTPException(502, f"AI provider unreachable: {exc.__class__.__name__}")

    if res.status_code == 429:
        raise HTTPException(
            429,
            "AI provider quota exceeded (429). Giữ prompt và thử lại sau, "
            "hoặc copy prompt để dùng tay.",
        )
    if res.status_code != 200:
        err_body = {}
        try:
            err_body = res.json()
        except json.JSONDecodeError:
            pass
        err_msg = err_body.get("error", {}).get("message", str(res.status_code))
        raise HTTPException(502, f"AI provider error: {err_msg}")

    choices = (res.json().get("choices") or [])
    if not choices:
        raise HTTPException(502, "AI trả về response rỗng — thử lại.")
    text = (choices[0].get("message") or {}).get("content", "").strip()
    if not text:
        raise HTTPException(502, "AI trả về nội dung rỗng — thử lại.")
    return text


# ── Validation & sanitization ──────────────────────────────────────────
def _extract_frontmatter(text: str) -> dict[str, Any]:
    """Parse Zola frontmatter from AI output. Returns {fields..., body}."""
    m = _FM_SPLIT_RE.search(text)
    if not m:
        raise HTTPException(422, "Thiếu frontmatter Zola (+++ ... +++). AI cần sinh đúng định dạng.")
    fm_raw = m.group(1).strip()
    body = m.group(2).strip()

    fields: dict[str, Any] = {"_raw_fm": fm_raw, "_body": body}

    # Extract TOML-like fields using regex (simple, no TOML parser dep).
    # title
    t = re.search(r'(?m)^title\s*=\s*"([^"]*)"', fm_raw)
    fields["title"] = t.group(1).strip() if t else ""

    # description
    d = re.search(r'(?m)^description\s*=\s*"([^"]*)"', fm_raw)
    fields["description"] = d.group(1).strip() if d else ""

    # slug
    s = re.search(r'(?m)^slug\s*=\s*"([^"]*)"', fm_raw)
    fields["slug"] = s.group(1).strip() if s else ""

    # date
    dt = re.search(r'(?m)^date\s*=\s*(\S+)', fm_raw)
    fields["date"] = dt.group(1).strip() if dt else ""

    # draft
    dr = re.search(r'(?m)^draft\s*=\s*(true|false)', fm_raw)
    fields["draft"] = dr.group(1) if dr else "false"

    # categories
    c = re.search(r'(?m)^categories\s*=\s*\[(.*?)\]', fm_raw)
    fields["categories"] = c.group(1).strip() if c else ""

    # tags
    tgs = re.search(r'(?m)^tags\s*=\s*\[(.*?)\]', fm_raw)
    fields["tags"] = tgs.group(1).strip() if tgs else ""

    # seo_keyword
    kw = re.search(r'(?m)^seo_keyword\s*=\s*"([^"]*)"', fm_raw)
    fields["seo_keyword"] = kw.group(1).strip() if kw else ""

    return fields


def _sanitize_content(text: str, fields: dict[str, Any]) -> str:
    """Sanitize AI output: fix common issues, ensure compliance."""
    # 1. Remove external image URLs (http/https in markdown images).
    text = re.sub(r"!\[([^\]]*)\]\(https?://[^)]+\)", "", text)
    # Also remove bare <img> tags with http src.
    text = re.sub(r'<img\s[^>]*src="https?://[^"]*"[^>]*>', "", text)

    # 2. Replace slug placeholder if missing.
    if not fields.get("slug"):
        slug = _slugify(fields.get("title", "bai-viet"))
        text = text.replace('slug = ""', f'slug = "{slug}"', 1)

    # 3. Ensure draft=false.
    text = re.sub(r'(?m)^draft\s*=\s*true\s*$', 'draft = false', text)

    # 4. Remove any script/iframe tags (security).
    text = re.sub(r'<script[\s>][^<]*</script>', '', text, flags=re.DOTALL)
    text = re.sub(r'<iframe[\s>][^<]*</iframe>', '', text, flags=re.DOTALL)

    # 5. Ensure at least "Tất cả" in categories.
    if '"Tất cả"' not in text and 'categories' in text:
        # Add "Tất cả" as first category.
        text = re.sub(
            r'(?m)^categories\s*=\s*\[(.*?)\]$',
            lambda m: f'categories = ["Tất cả", {m.group(1).strip().lstrip(",").strip()}]'
            if m.group(1).strip()
            else 'categories = ["Tất cả"]',
            text,
        )

    return text


# ── Slug helpers (stdlib-only) ─────────────────────────────────────────
def _slugify(text: str) -> str:
    """Simple slugify: remove diacritics, lowercase, replace spaces with dashes."""
    import unicodedata
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.replace("đ", "d").replace("Đ", "D")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:60] or "bai-viet"


# ── Branch naming ──────────────────────────────────────────────────────
def _branch_name(slug: str) -> str:
    """Generate a unique branch name for the AI writer PR."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    safe_slug = slug[:40]
    return f"ai-writer/{safe_slug}-{ts}-{rand}"


# ── Router ─────────────────────────────────────────────────────────────
@router.post("/api/content-creator/write-blog")
async def write_blog(
    request: Request,
    authorization: str = Header(default=""),
    cookie_sid: Optional[str] = Cookie(default=None, alias="zola_cms_sid"),
):
    """Generate a blog post via AI and publish via PR.

    Request body:
    {
        "prompt": "...",        // The full prompt from the content creator
        "topic": "...",         // Topic/subject of the post
        "category": "Tất cả",   // Primary category
        "pricing": "free",      // "free" or "paid"
        "series_id": "",        // Optional series ID
        "brief": "",            // User's brief
        "ux_brief": "",         // UX preferences
        "watermark": ""         // Trace code
    }
    """
    # 1. Authenticate (admin only).
    token = await _token(authorization, cookie_sid)

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

    # 3. Call AI provider.
    raw_content = await _call_ai(prompt)

    # 4. Validate and sanitize.
    fields = _extract_frontmatter(raw_content)
    safe_content = _sanitize_content(raw_content, fields)

    slug = fields.get("slug") or _slugify(topic)
    if not _SLUG_RE.match(slug):
        slug = _slugify(topic)
    if not _SLUG_RE.match(slug):
        slug = f"bai-viet-{int(time.time())}"
    title = fields.get("title") or topic

    # 5. Commit via PR to GitHub.
    file_path = f"{CMS_CONTENT_DIR}/{slug}.md"
    branch = _branch_name(slug)
    commit_msg = f"feat(ai-writer): {title}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 5a. Get latest main SHA.
        main_sha = await _gh_get_main_sha(client, token)

        # 5b. Create branch.
        await _gh_create_branch(client, branch, main_sha, token)

        # 5c. Commit the file.
        await _gh_put_file(client, file_path, safe_content, branch, commit_msg, token)

        # 5d. Create PR.
        pr_body = (
            f"## 🤖 AI Writer — {title}\n\n"
            f"**Chủ đề:** {topic}\n"
            f"**Slug:** `{slug}`\n"
            f"**Prompt:** {prompt[:500]}\n\n"
            f"---\n"
            f"*Bài viết được tạo tự động bởi AI Writer. "
            f"QA gate sẽ kiểm tra trước khi auto-merge.*"
        )
        pr_data = await _gh_create_pr(client, branch, commit_msg, pr_body, token)

    pr_url = (pr_data.get("html_url") or "")
    pr_number = pr_data.get("number") or 0

    return {
        "ok": True,
        "pr_url": pr_url,
        "pr_number": pr_number,
        "branch": branch,
        "slug": slug,
        "title": title,
        "file_path": file_path,
        "message": f"✅ Đã tạo PR #{pr_number} — {title}. QA sẽ kiểm tra trước khi merge.",
        "public_url": f"https://seomoney.org/{slug}/",
    }
