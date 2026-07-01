"""Operational CMS-V5 API: posts, media, taxonomy, analytics and publishing."""

from __future__ import annotations

import asyncio
import base64
import json
import mimetypes
import os
import re
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal
from urllib.parse import quote

import httpx
from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    File,
    Header,
    HTTPException,
    UploadFile,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from cms_auth import (
    BACKEND_URL,
    SESSION_COOKIE_NAME,
    cms_profile_from_session,
    github_token_from_session,
    is_admin,
    resolve_sid,
)
from db import VipzoneDB

router = APIRouter(prefix="/api/cms-v5", tags=["cms-v5"])

ROOT = Path(__file__).resolve().parents[2]
MEDIA_ROOT = Path(
    os.getenv("CMS_V5_MEDIA_PATH", "/var/data/cms-v5-media" if os.getenv("RENDER") else ROOT / "data" / "cms-v5-media")
)
MAX_UPLOAD_BYTES = int(os.getenv("CMS_V5_MAX_UPLOAD_BYTES", str(30 * 1024 * 1024)))
CMS_REPO_OWNER = os.getenv("CMS_REPO_OWNER", "Banhang-Chogao")
CMS_REPO_NAME = os.getenv("CMS_REPO_NAME", "zola")
CMS_REPO_BRANCH = os.getenv("CMS_REPO_BRANCH", "main")
BLOG_URL = os.getenv("VIPZONE_BLOG_URL", "https://seomoney.org").rstrip("/")

ALLOWED_MEDIA = {
    "image/jpeg": ("image", ".jpg"),
    "image/png": ("image", ".png"),
    "image/gif": ("image", ".gif"),
    "image/webp": ("image", ".webp"),
    "image/svg+xml": ("image", ".svg"),
    "video/mp4": ("video", ".mp4"),
    "video/webm": ("video", ".webm"),
    "audio/mpeg": ("audio", ".mp3"),
    "audio/mp4": ("audio", ".m4a"),
    "audio/ogg": ("audio", ".ogg"),
    "application/pdf": ("pdf", ".pdf"),
}
POST_STATUSES = {"draft", "review", "scheduled", "published"}
VISIBILITIES = {"public", "private"}
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,89}$")
SAFE_PATH_RE = re.compile(r"^/[A-Za-z0-9/_\-.]{0,300}$")
ARTICLE_SECTIONS = {
    "posting", "baochi", "am-thuc", "hoc-tieng-han", "seo",
    "world-cup-2026", "khoa-hoc", "the-gioi", "cong-nghe", "du-lich",
    "ngan-hang", "bao-hiem", "doi-song", "the-thao",
}

_get_db: Callable[[], VipzoneDB] | None = None
_scheduler_task: asyncio.Task | None = None


def configure(get_db: Callable[[], VipzoneDB]) -> None:
    global _get_db
    _get_db = get_db


def db() -> VipzoneDB:
    if _get_db is None:
        raise HTTPException(503, "cms_v5_not_configured")
    return _get_db()


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFD", value or "")
    value = "".join(c for c in value if unicodedata.category(c) != "Mn")
    value = value.replace("đ", "d").replace("Đ", "D").lower()
    return re.sub(r"(^-+|-+$)", "", re.sub(r"[^a-z0-9]+", "-", value))[:90]


def json_list(value: str) -> list:
    try:
        parsed = json.loads(value or "[]")
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def post_row(row: Any) -> dict[str, Any]:
    out = dict(row)
    out["blocks"] = json_list(out.pop("blocks_json", "[]"))
    out["tags"] = json_list(out.pop("tags_json", "[]"))
    out.pop("publisher_sid", None)
    return out


def media_row(row: Any) -> dict[str, Any]:
    out = dict(row)
    out.pop("storage_path", None)
    out.pop("stored_name", None)
    out["url"] = f"{BACKEND_URL}/api/cms-v5/media/{out['id']}/file"
    return out


async def require_github_admin(
    authorization: str = Header(default=""),
    cookie_sid: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> dict[str, Any]:
    profile = await cms_profile_from_session(db(), authorization, cookie_sid=cookie_sid)
    if profile.get("provider") != "github":
        raise HTTPException(403, "github_oauth_required")
    if not (is_admin(profile.get("email"), profile.get("username")) or profile.get("is_super")):
        raise HTTPException(403, "cms_admin_required")
    return profile


class Block(BaseModel):
    type: Literal["text", "heading", "quote", "list", "image"]
    text: str = Field(default="", max_length=100_000)
    media_id: str | None = Field(default=None, max_length=80)
    alt: str = Field(default="", max_length=300)


class PostPayload(BaseModel):
    id: str | None = None
    title: str = Field(min_length=1, max_length=220)
    slug: str = Field(default="", max_length=90)
    excerpt: str = Field(default="", max_length=500)
    blocks: list[Block] = Field(default_factory=list, max_length=500)
    category: str = Field(default="", max_length=100)
    tags: list[str] = Field(default_factory=list, max_length=50)
    featured_media_id: str | None = Field(default=None, max_length=80)
    status: Literal["draft", "review", "scheduled"] = "draft"
    visibility: Literal["public", "private"] = "public"
    scheduled_at: str | None = None


class TaxonomyPayload(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(default="", max_length=100)
    description: str = Field(default="", max_length=300)


class AnalyticsPayload(BaseModel):
    path: str = Field(default="/", max_length=320)
    metric: Literal["view", "interaction"] = "view"


def _validate_schedule(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise HTTPException(400, "invalid_scheduled_at") from exc
    if parsed <= datetime.now(timezone.utc):
        raise HTTPException(400, "scheduled_at_must_be_future")
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _seed_categories() -> None:
    with db()._conn() as conn:
        if conn.execute("SELECT COUNT(*) FROM cms_v5_categories").fetchone()[0]:
            return
        names: list[str] = []
        source = ROOT / "categories.json"
        try:
            raw = json.loads(source.read_text(encoding="utf-8"))
            names = raw.get("categories", []) if isinstance(raw, dict) else []
        except (OSError, json.JSONDecodeError):
            names = []
        stamp = now_iso()
        for name in names:
            if not isinstance(name, str) or not name.strip():
                continue
            slug = slugify(name)
            if not slug:
                continue
            conn.execute(
                """INSERT OR IGNORE INTO cms_v5_categories
                   (id, name, slug, description, created_at, updated_at)
                   VALUES (?, ?, ?, '', ?, ?)""",
                (f"cat_{uuid.uuid4().hex[:12]}", name.strip(), slug, stamp, stamp),
            )


def _content_snapshot() -> dict[str, Any]:
    """Read real checked-out Zola content for baseline post/taxonomy counts."""
    posts = 0
    today = 0
    categories: dict[str, int] = {}
    tags: dict[str, int] = {}
    slugs: set[str] = set()
    today_text = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for section in ARTICLE_SECTIONS:
        for path in (ROOT / "content" / section).glob("*.md"):
            if path.name.startswith("_"):
                continue
            try:
                head = path.read_text(encoding="utf-8", errors="ignore").split("+++", 2)[1]
            except (OSError, IndexError):
                continue
            posts += 1
            slugs.add(path.stem)
            date_match = re.search(r"(?m)^date\s*=\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", head)
            if date_match and date_match.group(1) == today_text:
                today += 1
            for key, target in (("categories", categories), ("tags", tags)):
                match = re.search(rf"(?m)^{key}\s*=\s*\[(.*?)\]", head)
                if not match:
                    continue
                for item in re.findall(r'"([^"]+)"', match.group(1)):
                    target[item] = target.get(item, 0) + 1
    return {
        "posts": posts,
        "today": today,
        "categories": categories,
        "tags": tags,
        "slugs": slugs,
    }


def _ensure_taxonomies(conn: Any, category: str, tags: list[str]) -> None:
    stamp = now_iso()
    category = category.strip()
    if category:
        conn.execute(
            """INSERT OR IGNORE INTO cms_v5_categories
               (id, name, slug, description, created_at, updated_at)
               VALUES (?, ?, ?, '', ?, ?)""",
            (f"cat_{uuid.uuid4().hex[:12]}", category, slugify(category), stamp, stamp),
        )
    for tag in tags:
        tag = tag.strip()
        if tag and slugify(tag):
            conn.execute(
                """INSERT OR IGNORE INTO cms_v5_tags
                   (id, name, slug, created_at, updated_at) VALUES (?, ?, ?, ?, ?)""",
                (f"tag_{uuid.uuid4().hex[:12]}", tag, slugify(tag), stamp, stamp),
            )


@router.get("/dashboard")
async def dashboard(_: dict = Depends(require_github_admin)):
    snapshot = _content_snapshot()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with db()._conn() as conn:
        cms_rows = conn.execute(
            "SELECT slug, status, created_at FROM cms_v5_posts"
        ).fetchall()
        cms_only = [
            row for row in cms_rows
            if row["status"] != "published" or row["slug"] not in snapshot["slugs"]
        ]
        cms_total = len(cms_only)
        cms_today = sum(1 for row in cms_only if row["created_at"].startswith(today))
        queue = conn.execute(
            """SELECT * FROM cms_v5_posts
               WHERE status IN ('draft','review','scheduled')
               ORDER BY updated_at DESC LIMIT 30"""
        ).fetchall()
        views_today = conn.execute(
            "SELECT COALESCE(SUM(count),0) FROM cms_v5_analytics WHERE day=? AND metric='view'",
            (today,),
        ).fetchone()[0]
        views_total = conn.execute(
            "SELECT COALESCE(SUM(count),0) FROM cms_v5_analytics WHERE metric='view'"
        ).fetchone()[0]
        interactions_today = conn.execute(
            "SELECT COALESCE(SUM(count),0) FROM cms_v5_analytics WHERE day=? AND metric='interaction'",
            (today,),
        ).fetchone()[0]
        interactions_total = conn.execute(
            "SELECT COALESCE(SUM(count),0) FROM cms_v5_analytics WHERE metric='interaction'"
        ).fetchone()[0]
        comments_today = conn.execute(
            "SELECT COUNT(*) FROM comments WHERE substr(created_at,1,10)=?", (today,)
        ).fetchone()[0]
        comments_total = conn.execute("SELECT COUNT(*) FROM comments").fetchone()[0]
        comments_pending = conn.execute(
            "SELECT COUNT(*) FROM comments WHERE status='pending'"
        ).fetchone()[0]
        categories_count = conn.execute("SELECT COUNT(*) FROM cms_v5_categories").fetchone()[0]
        tags_count = conn.execute("SELECT COUNT(*) FROM cms_v5_tags").fetchone()[0]
        media_count = conn.execute("SELECT COUNT(*) FROM cms_v5_media").fetchone()[0]
    return {
        "stats": {
            "posts_today": snapshot["today"] + cms_today,
            "posts_total": snapshot["posts"] + cms_total,
            "views_today": views_today,
            "views_total": views_total,
            "comments_today": comments_today,
            "comments_total": comments_total,
            "comments_pending": comments_pending,
            "interactions_today": interactions_today + comments_today,
            "interactions_total": interactions_total + comments_total,
        },
        "queue": [post_row(row) for row in queue],
        "counts": {
            "categories": max(categories_count, len(snapshot["categories"])),
            "tags": max(tags_count, len(snapshot["tags"])),
            "media": media_count,
        },
    }


@router.get("/posts")
async def list_posts(
    status: str | None = None,
    q: str | None = None,
    limit: int = 100,
    offset: int = 0,
    _: dict = Depends(require_github_admin),
):
    if limit < 1 or limit > 500:
        raise HTTPException(400, "invalid_limit")
    if offset < 0:
        raise HTTPException(400, "invalid_offset")
    with db()._conn() as conn:
        where = []
        params: list[str | int] = []
        if status:
            if status not in POST_STATUSES:
                raise HTTPException(400, "invalid_status")
            where.append("status=?")
            params.append(status)
        if q:
            where.append("(title LIKE ? OR slug LIKE ? OR excerpt LIKE ?)")
            like = f"%{q}%"
            params.extend([like, like, like])
        clause = ("WHERE " + " AND ".join(where)) if where else ""
        rows = conn.execute(
            f"SELECT * FROM cms_v5_posts {clause} ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (*params, limit, offset),
        ).fetchall()
        total = conn.execute(
            f"SELECT COUNT(*) FROM cms_v5_posts {clause}", params
        ).fetchone()[0]
    return {"posts": [post_row(row) for row in rows], "total": total}


@router.get("/posts/{post_id}")
async def get_post(post_id: str, _: dict = Depends(require_github_admin)):
    with db()._conn() as conn:
        row = conn.execute("SELECT * FROM cms_v5_posts WHERE id=?", (post_id,)).fetchone()
    if not row:
        raise HTTPException(404, "post_not_found")
    return post_row(row)


@router.post("/posts")
async def save_post(
    payload: PostPayload,
    profile: dict = Depends(require_github_admin),
    authorization: str = Header(default=""),
    cookie_sid: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
):
    post_id = payload.id or f"post_{uuid.uuid4().hex[:16]}"
    slug = slugify(payload.slug or payload.title)
    if not SLUG_RE.match(slug):
        raise HTTPException(400, "invalid_slug")
    if payload.status == "scheduled":
        if not payload.scheduled_at:
            raise HTTPException(400, "scheduled_at_required_for_scheduled_posts")
        scheduled_at = _validate_schedule(payload.scheduled_at)
    else:
        scheduled_at = None
    tags = list(dict.fromkeys(t.strip() for t in payload.tags if t.strip()))[:50]
    blocks_json = json.dumps([b.model_dump() for b in payload.blocks], ensure_ascii=False)
    stamp = now_iso()
    publisher_sid = resolve_sid(authorization, cookie_sid) if payload.status == "scheduled" else None
    with db()._conn() as conn:
        existing = conn.execute("SELECT id FROM cms_v5_posts WHERE id=?", (post_id,)).fetchone()
        try:
            conn.execute(
                """INSERT INTO cms_v5_posts
                   (id, slug, title, excerpt, blocks_json, category, tags_json,
                    featured_media_id, status, visibility, scheduled_at,
                    author_username, author_name, publisher_sid, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                    slug=excluded.slug, title=excluded.title, excerpt=excluded.excerpt,
                    blocks_json=excluded.blocks_json, category=excluded.category,
                    tags_json=excluded.tags_json, featured_media_id=excluded.featured_media_id,
                    status=excluded.status, visibility=excluded.visibility,
                    scheduled_at=excluded.scheduled_at, publisher_sid=excluded.publisher_sid,
                    updated_at=excluded.updated_at""",
                (
                    post_id, slug, payload.title.strip(), payload.excerpt.strip(),
                    blocks_json, payload.category.strip(), json.dumps(tags, ensure_ascii=False),
                    payload.featured_media_id, payload.status, payload.visibility, scheduled_at,
                    profile.get("username") or "", profile.get("name") or "",
                    publisher_sid, stamp, stamp,
                ),
            )
        except Exception as exc:
            if "UNIQUE constraint failed: cms_v5_posts.slug" in str(exc):
                raise HTTPException(409, "slug_already_exists") from exc
            raise
        _ensure_taxonomies(conn, payload.category, tags)
        row = conn.execute("SELECT * FROM cms_v5_posts WHERE id=?", (post_id,)).fetchone()
    return {"ok": True, "created": not bool(existing), "post": post_row(row)}


@router.delete("/posts/{post_id}")
async def delete_post(post_id: str, _: dict = Depends(require_github_admin)):
    with db()._conn() as conn:
        cur = conn.execute(
            "DELETE FROM cms_v5_posts WHERE id=? AND status!='published'", (post_id,)
        )
    if not cur.rowcount:
        raise HTTPException(404, "post_not_found_or_published")
    return {"ok": True}


def _media_by_id(conn: Any, media_id: str | None) -> dict[str, Any] | None:
    if not media_id:
        return None
    row = conn.execute("SELECT * FROM cms_v5_media WHERE id=?", (media_id,)).fetchone()
    return media_row(row) if row else None


def _toml(value: str) -> str:
    return '"' + (value or "").replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'


def _markdown_for_post(post: dict[str, Any], conn: Any) -> str:
    tags = post.get("tags", [])
    category = post.get("category") or "Tất cả"
    featured = _media_by_id(conn, post.get("featured_media_id"))
    date = (post.get("scheduled_at") or now_iso()).replace("Z", "+00:00")
    categories = ["Tất cả"] if category == "Tất cả" else ["Tất cả", category]
    lines = [
        "+++",
        f"title = {_toml(post['title'])}",
        f"date = {date}",
        f'aliases = ["/{post["slug"]}/", "/posting/{post["slug"]}/"]',
    ]
    if featured and featured["media_type"] == "image":
        lines.extend(
            [
                f"thumbnail = {_toml(featured['url'])}",
                f"image_alt = {_toml(featured.get('alt_text') or post['title'])}",
            ]
        )
    lines.extend(
        [
            "",
            "[taxonomies]",
            f"categories = {json.dumps(categories, ensure_ascii=False)}",
            f"tags = {json.dumps(tags, ensure_ascii=False)}",
            "[extra]",
            f"excerpt = {_toml(post.get('excerpt') or '')}",
            "+++",
            "",
        ]
    )
    for block in post.get("blocks", []):
        kind = block.get("type")
        text = (block.get("text") or "").strip()
        if kind == "image":
            media = _media_by_id(conn, block.get("media_id"))
            if media and media["media_type"] == "image":
                lines.extend([f"![{block.get('alt') or media.get('alt_text') or media['filename']}]({media['url']})", ""])
        elif kind == "heading" and text:
            lines.extend([f"## {text}", ""])
        elif kind == "quote" and text:
            lines.extend(["\n".join(f"> {line}" for line in text.splitlines()), ""])
        elif kind == "list" and text:
            items = [item.strip().lstrip("-•* ") for item in text.splitlines() if item.strip()]
            lines.extend(["\n".join(f"- {item}" for item in items), ""])
        elif text:
            lines.extend([text, ""])
    return "\n".join(lines).rstrip() + "\n"


async def _publish(post_id: str, token: str) -> dict[str, Any]:
    with db()._conn() as conn:
        row = conn.execute("SELECT * FROM cms_v5_posts WHERE id=?", (post_id,)).fetchone()
        if not row:
            raise HTTPException(404, "post_not_found")
        post = post_row(row)
        if post["visibility"] != "public":
            raise HTTPException(400, "private_post_cannot_publish")
        markdown = _markdown_for_post(post, conn)
    category_slug = slugify(post.get("category") or "")
    section = category_slug if category_slug in (ARTICLE_SECTIONS - {"posting"}) else "posting"
    repo_path = f"content/{section}/{post['slug']}.md"
    api_path = quote(repo_path, safe="/")
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "SEOMONEY-CMS-V5",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        current = await client.get(
            f"https://api.github.com/repos/{CMS_REPO_OWNER}/{CMS_REPO_NAME}/contents/{api_path}",
            params={"ref": CMS_REPO_BRANCH},
            headers=headers,
        )
        sha = current.json().get("sha") if current.status_code == 200 else None
        payload: dict[str, Any] = {
            "message": f"content(cms-v5): publish {post['slug']}",
            "content": base64.b64encode(markdown.encode("utf-8")).decode("ascii"),
            "branch": CMS_REPO_BRANCH,
        }
        if sha:
            payload["sha"] = sha
        result = await client.put(
            f"https://api.github.com/repos/{CMS_REPO_OWNER}/{CMS_REPO_NAME}/contents/{api_path}",
            headers=headers,
            json=payload,
        )
    if result.status_code not in {200, 201}:
        detail = "github_publish_failed"
        try:
            detail += f": {result.json().get('message', '')}"
        except json.JSONDecodeError:
            pass
        raise HTTPException(502, detail)
    response = result.json()
    commit = response.get("commit", {}).get("sha", "")
    published_url = f"{BLOG_URL}/{section}/{post['slug']}/"
    stamp = now_iso()
    with db()._conn() as conn:
        conn.execute(
            """UPDATE cms_v5_posts SET status='published', published_url=?,
               published_commit=?, published_at=?, updated_at=?, publisher_sid=NULL
               WHERE id=?""",
            (published_url, commit, stamp, stamp, post_id),
        )
    return {"ok": True, "url": published_url, "commit": commit, "path": repo_path}


@router.post("/posts/{post_id}/publish")
async def publish_post(
    post_id: str,
    _: dict = Depends(require_github_admin),
    authorization: str = Header(default=""),
    cookie_sid: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
):
    token = await github_token_from_session(db(), authorization, cookie_sid=cookie_sid)
    return await _publish(post_id, token)


@router.get("/media")
async def list_media(_: dict = Depends(require_github_admin)):
    with db()._conn() as conn:
        rows = conn.execute("SELECT * FROM cms_v5_media ORDER BY created_at DESC").fetchall()
        total = conn.execute("SELECT COALESCE(SUM(size_bytes),0) FROM cms_v5_media").fetchone()[0]
    return {"media": [media_row(row) for row in rows], "total_bytes": total}


@router.post("/media")
async def upload_media(
    files: list[UploadFile] = File(...),
    profile: dict = Depends(require_github_admin),
):
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    saved: list[dict[str, Any]] = []
    for upload in files[:20]:
        content_type = (upload.content_type or mimetypes.guess_type(upload.filename or "")[0] or "").lower()
        if content_type not in ALLOWED_MEDIA:
            raise HTTPException(415, f"unsupported_media_type: {content_type or 'unknown'}")
        content = await upload.read(MAX_UPLOAD_BYTES + 1)
        if not content or len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "file_too_large_or_empty")
        media_type, extension = ALLOWED_MEDIA[content_type]
        media_id = f"media_{uuid.uuid4().hex[:16]}"
        stored_name = f"{media_id}{extension}"
        path = MEDIA_ROOT / stored_name
        path.write_bytes(content)
        original = Path(upload.filename or stored_name).name[:255]
        with db()._conn() as conn:
            conn.execute(
                """INSERT INTO cms_v5_media
                   (id, filename, stored_name, content_type, media_type, size_bytes,
                    alt_text, storage_path, uploaded_by, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, '', ?, ?, ?)""",
                (
                    media_id, original, stored_name, content_type, media_type, len(content),
                    str(path), profile.get("username") or "", now_iso(),
                ),
            )
            row = conn.execute("SELECT * FROM cms_v5_media WHERE id=?", (media_id,)).fetchone()
        saved.append(media_row(row))
    return {"ok": True, "media": saved}


@router.get("/media/{media_id}/file")
async def media_file(media_id: str):
    with db()._conn() as conn:
        row = conn.execute("SELECT * FROM cms_v5_media WHERE id=?", (media_id,)).fetchone()
    if not row:
        raise HTTPException(404, "media_not_found")
    path = Path(row["storage_path"])
    try:
        path.relative_to(MEDIA_ROOT)
    except ValueError as exc:
        raise HTTPException(403, "invalid_media_path") from exc
    if not path.is_file():
        raise HTTPException(404, "media_file_missing")
    return FileResponse(
        path,
        media_type=row["content_type"],
        filename=row["filename"],
        content_disposition_type="inline",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@router.delete("/media/{media_id}")
async def delete_media(media_id: str, _: dict = Depends(require_github_admin)):
    with db()._conn() as conn:
        row = conn.execute("SELECT * FROM cms_v5_media WHERE id=?", (media_id,)).fetchone()
        if not row:
            raise HTTPException(404, "media_not_found")
        used = conn.execute(
            """SELECT COUNT(*) FROM cms_v5_posts
               WHERE featured_media_id=? OR blocks_json LIKE ?""",
            (media_id, f'%\"media_id\": \"{media_id}\"%'),
        ).fetchone()[0]
        if used:
            raise HTTPException(409, "media_is_in_use")
        conn.execute("DELETE FROM cms_v5_media WHERE id=?", (media_id,))
    Path(row["storage_path"]).unlink(missing_ok=True)
    return {"ok": True}


@router.get("/taxonomy")
async def get_taxonomy(_: dict = Depends(require_github_admin)):
    _seed_categories()
    snapshot = _content_snapshot()
    with db()._conn() as conn:
        categories = [dict(row) for row in conn.execute(
            "SELECT * FROM cms_v5_categories ORDER BY name COLLATE NOCASE"
        ).fetchall()]
        tags = [dict(row) for row in conn.execute(
            "SELECT * FROM cms_v5_tags ORDER BY name COLLATE NOCASE"
        ).fetchall()]
        posts = [post_row(row) for row in conn.execute(
            "SELECT * FROM cms_v5_posts"
        ).fetchall()]
    category_counts = dict(snapshot["categories"])
    tag_counts = dict(snapshot["tags"])
    for post in posts:
        if post["status"] == "published" and post["slug"] in snapshot["slugs"]:
            continue
        if post["category"]:
            category_counts[post["category"]] = category_counts.get(post["category"], 0) + 1
        for tag in post["tags"]:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    for item in categories:
        item["post_count"] = category_counts.get(item["name"], 0)
    known_tags = {item["name"] for item in tags}
    for name in tag_counts:
        if name not in known_tags:
            tags.append({"id": "", "name": name, "slug": slugify(name), "post_count": tag_counts[name]})
    for item in tags:
        item["post_count"] = tag_counts.get(item["name"], 0)
    return {"categories": categories, "tags": sorted(tags, key=lambda x: (-x["post_count"], x["name"].lower()))}


@router.post("/taxonomy/categories")
async def create_category(payload: TaxonomyPayload, _: dict = Depends(require_github_admin)):
    name = payload.name.strip()
    slug = slugify(payload.slug or name)
    if not slug:
        raise HTTPException(400, "invalid_slug")
    stamp = now_iso()
    item_id = f"cat_{uuid.uuid4().hex[:12]}"
    with db()._conn() as conn:
        try:
            conn.execute(
                """INSERT INTO cms_v5_categories
                   (id, name, slug, description, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (item_id, name, slug, payload.description.strip(), stamp, stamp),
            )
        except Exception as exc:
            if "UNIQUE constraint failed" in str(exc):
                raise HTTPException(409, "category_already_exists") from exc
            raise
    return {"ok": True, "id": item_id}


@router.post("/taxonomy/tags")
async def create_tag(payload: TaxonomyPayload, _: dict = Depends(require_github_admin)):
    name = payload.name.strip()
    slug = slugify(payload.slug or name)
    if not slug:
        raise HTTPException(400, "invalid_slug")
    stamp = now_iso()
    item_id = f"tag_{uuid.uuid4().hex[:12]}"
    with db()._conn() as conn:
        try:
            conn.execute(
                """INSERT INTO cms_v5_tags (id, name, slug, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (item_id, name, slug, stamp, stamp),
            )
        except Exception as exc:
            if "UNIQUE constraint failed" in str(exc):
                raise HTTPException(409, "tag_already_exists") from exc
            raise
    return {"ok": True, "id": item_id}


@router.delete("/taxonomy/{kind}/{item_id}")
async def delete_taxonomy(kind: str, item_id: str, _: dict = Depends(require_github_admin)):
    table = {"categories": "cms_v5_categories", "tags": "cms_v5_tags"}.get(kind)
    if not table:
        raise HTTPException(404, "taxonomy_not_found")
    with db()._conn() as conn:
        cur = conn.execute(f"DELETE FROM {table} WHERE id=?", (item_id,))
    if not cur.rowcount:
        raise HTTPException(404, "taxonomy_not_found")
    return {"ok": True}


@router.post("/analytics")
async def record_analytics(payload: AnalyticsPayload):
    path = payload.path.split("?", 1)[0]
    if not SAFE_PATH_RE.match(path) or path.startswith("/cms-"):
        raise HTTPException(400, "invalid_path")
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with db()._conn() as conn:
        conn.execute(
            """INSERT INTO cms_v5_analytics (day, page_path, metric, count)
               VALUES (?, ?, ?, 1)
               ON CONFLICT(day, page_path, metric)
               DO UPDATE SET count=count+1""",
            (day, path, payload.metric),
        )
    return {"ok": True}


async def process_scheduled_posts() -> int:
    stamp = now_iso()
    with db()._conn() as conn:
        due = conn.execute(
            """SELECT id, publisher_sid FROM cms_v5_posts
               WHERE status='scheduled' AND scheduled_at<=?
               ORDER BY scheduled_at LIMIT 10""",
            (stamp,),
        ).fetchall()
    published = 0
    for row in due:
        sid = row["publisher_sid"]
        if not sid:
            with db()._conn() as conn:
                conn.execute(
                    "UPDATE cms_v5_posts SET status='draft', updated_at=? WHERE id=?",
                    (stamp, row["id"]),
                )
            continue
        try:
            token = await github_token_from_session(db(), f"Bearer {sid}")
            if not token:
                with db()._conn() as conn:
                    conn.execute(
                        "UPDATE cms_v5_posts SET status='draft', updated_at=? WHERE id=?",
                        (stamp, row["id"]),
                    )
                continue
            await _publish(row["id"], token)
            published += 1
        except HTTPException as exc:
            if exc.status_code == 401:
                with db()._conn() as conn:
                    conn.execute(
                        "UPDATE cms_v5_posts SET status='draft', updated_at=? WHERE id=?",
                        (stamp, row["id"]),
                    )
            continue
        except Exception:
            continue
    return published


async def scheduler_loop() -> None:
    while True:
        await asyncio.sleep(60)
        await process_scheduled_posts()


def start_scheduler() -> None:
    global _scheduler_task
    if _scheduler_task is None or _scheduler_task.done():
        _scheduler_task = asyncio.create_task(scheduler_loop())


async def stop_scheduler() -> None:
    global _scheduler_task
    if _scheduler_task:
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass
        _scheduler_task = None
