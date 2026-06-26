"""Native SEOMONEY comment system for the VIPZone API.

A small, AdSense-safe, Google-authenticated comment surface that replaces the
GitHub-only Giscus widget. Visitors log in with their Google account (see
``cms_auth.auth_comment_start``) and may post comments; admins moderate.

Design / safety:
  * No anonymous comments — POST requires a valid session (401 otherwise).
  * Public reads expose ONLY display name + avatar + body. The raw email is never
    stored (a sha256 hash is) and never returned.
  * Bodies are sanitised (control chars + angle brackets stripped, length capped)
    on the way IN, and the frontend renders them as text — no HTML is ever
    interpreted.
  * New comments default to ``pending`` (configurable) so nothing public appears
    until an admin approves — keeps the page clean for AdSense review.
  * A light per-author rate limit blocks floods.

Routes:
  GET    /comments?path=/post-url/                 (public — approved comments)
  POST   /comments                                 (auth — submit, stored pending)
  GET    /admin/comments?status=pending            (admin — moderation list)
  POST   /admin/comments/{id}/approve              (admin)
  POST   /admin/comments/{id}/hide                 (admin)
  DELETE /admin/comments/{id}                      (admin)
"""

from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request

from cms_auth import is_admin, is_commenter_only, session_dep
from roles import is_superadmin

router = APIRouter(tags=["comments"])

# ============= Config (env-driven, no secrets) =============
def _truthy(v: str) -> bool:
    return (v or "").strip().lower() in {"1", "true", "yes", "on"}


COMMENTS_ENABLED = _truthy(os.getenv("COMMENTS_ENABLED", "true"))
COMMENTS_DEFAULT_STATUS = os.getenv("COMMENTS_DEFAULT_STATUS", "pending").strip().lower()
if COMMENTS_DEFAULT_STATUS not in {"pending", "approved"}:
    COMMENTS_DEFAULT_STATUS = "pending"
try:
    COMMENTS_MAX_LENGTH = int(os.getenv("COMMENTS_MAX_LENGTH", "1500"))
except ValueError:
    COMMENTS_MAX_LENGTH = 1500
COMMENTS_MAX_LENGTH = max(50, min(COMMENTS_MAX_LENGTH, 5000))
COMMENTS_MIN_LENGTH = 1

# Per-author rate limit: at most N comments in the rolling window.
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("COMMENTS_RATE_WINDOW", "60"))
RATE_LIMIT_MAX = int(os.getenv("COMMENTS_RATE_MAX", "3"))

VALID_STATUSES = {"pending", "approved", "hidden", "deleted"}

# DB getter injected by configure() from the host app (mirrors personal_data).
_get_db: Optional[Callable[[], Any]] = None


def configure(get_db: Callable[[], Any]) -> None:
    global _get_db
    _get_db = get_db


def _db() -> Any:
    if _get_db is None:  # pragma: no cover - configure() always called at mount
        raise HTTPException(503, "comments_not_configured")
    return _get_db()


# ============= sanitisation / hashing =============
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_ANGLE_RE = re.compile(r"[<>]")
_WS_RUN_RE = re.compile(r"[ \t]{3,}")
_NL_RUN_RE = re.compile(r"\n{4,}")
_PATH_RE = re.compile(r"^/[A-Za-z0-9._~!$&'()*+,;=:@%/\-]*$")


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hash(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()


def _normalize_path(raw: str) -> str:
    """Canonicalise a page path so GET and POST agree. Path-only, leading slash."""
    p = (raw or "").strip()
    if not p:
        raise HTTPException(400, "missing_path")
    # Keep only the path component (drop scheme/host/query/hash).
    if "://" in p:
        p = p.split("://", 1)[1]
        p = "/" + p.split("/", 1)[1] if "/" in p else "/"
    p = p.split("?", 1)[0].split("#", 1)[0]
    if not p.startswith("/"):
        p = "/" + p
    # Drop a leading /zola base-path segment if present (site root is seomoney.org).
    if p == "/zola" or p.startswith("/zola/"):
        p = p[len("/zola"):] or "/"
    p = re.sub(r"/{2,}", "/", p)
    if len(p) > 300 or not _PATH_RE.match(p):
        raise HTTPException(400, "invalid_path")
    return p


def _sanitize_body(raw: Any) -> str:
    """Strip control chars + angle brackets, collapse runs, enforce length.

    Comments are plain text; removing ``<``/``>`` means no markup can ever be
    reconstructed even if a consumer mistakenly used innerHTML."""
    if not isinstance(raw, str):
        raise HTTPException(400, "invalid_body")
    text = _CONTROL_RE.sub("", raw)
    text = _ANGLE_RE.sub("", text)
    text = _WS_RUN_RE.sub("  ", text)
    text = _NL_RUN_RE.sub("\n\n\n", text)
    text = text.strip()
    if len(text) < COMMENTS_MIN_LENGTH:
        raise HTTPException(400, "empty_comment")
    if len(text) > COMMENTS_MAX_LENGTH:
        raise HTTPException(400, f"comment_too_long_max_{COMMENTS_MAX_LENGTH}")
    return text


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else ""


# ============= auth dependencies =============
async def require_commenter(profile: dict[str, Any] = Depends(session_dep)) -> dict[str, Any]:
    """Any authenticated session may comment (commenter OR admin). session_dep
    already 401s anonymous callers — there are no anonymous comments."""
    return profile


async def require_admin(profile: dict[str, Any] = Depends(session_dep)) -> dict[str, Any]:
    """Moderation guard — admin only. Commenter sessions are explicitly fenced out
    (defense-in-depth; is_admin/is_super are already false for them)."""
    if is_commenter_only(profile):
        raise HTTPException(403, "admin_only")
    if not is_admin(profile.get("email"), profile.get("username")) and not is_superadmin(profile):
        raise HTTPException(403, "admin_only")
    return profile


# ============= public + authenticated routes =============
@router.get("/comments")
async def list_comments(path: str = Query(...)) -> dict[str, Any]:
    """Public: approved comments for a page. Never exposes email/ids."""
    if not COMMENTS_ENABLED:
        return {"enabled": False, "comments": [], "count": 0}
    page = _normalize_path(path)
    comments = _db().list_comments_for_page(page, status="approved")
    return {
        "enabled": True,
        "page_path": page,
        "comments": comments,
        "count": len(comments),
        "default_status": COMMENTS_DEFAULT_STATUS,
    }


@router.post("/comments", status_code=201)
async def create_comment(
    request: Request,
    profile: dict[str, Any] = Depends(require_commenter),
) -> dict[str, Any]:
    """Authenticated submit. Sanitises, rate-limits, stores (pending by default)."""
    if not COMMENTS_ENABLED:
        raise HTTPException(403, "comments_disabled")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "invalid_json")
    if not isinstance(body, dict):
        raise HTTPException(400, "invalid_body")

    page = _normalize_path(body.get("path") or body.get("page_path") or "")
    text = _sanitize_body(body.get("body") or body.get("comment") or "")

    email = (profile.get("email") or "").strip().lower()
    sub = profile.get("sub") or email or profile.get("username") or ""
    author_sub_hash = _hash(f"{profile.get('provider', 'google')}:{sub}")

    # Rate limit per author.
    since = (
        datetime.now(timezone.utc) - timedelta(seconds=RATE_LIMIT_WINDOW_SECONDS)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    if _db().count_recent_comments_by_author(author_sub_hash, since) >= RATE_LIMIT_MAX:
        raise HTTPException(429, "rate_limited")

    # Admins' own comments may auto-approve; everyone else follows the default.
    is_admin_user = (
        not is_commenter_only(profile)
        and (is_admin(email, profile.get("username")) or is_superadmin(profile))
    )
    status = "approved" if is_admin_user else COMMENTS_DEFAULT_STATUS

    saved = _db().insert_comment(
        {
            "page_path": page,
            "body_sanitized": text,
            "author_provider": profile.get("provider") or "google",
            "author_sub_hash": author_sub_hash,
            "author_display_name": (profile.get("name") or "").strip()[:120]
            or "Người dùng Google",
            "author_avatar_url": (profile.get("avatar") or "").strip()[:500],
            "author_email_hash": _hash(email) if email else "",
            "status": status,
            "ip_hash": _hash(_client_ip(request)),
            "user_agent_hash": _hash(request.headers.get("user-agent", "")),
        }
    )
    pending = saved["status"] == "pending"
    return {
        "ok": True,
        "status": saved["status"],
        "pending": pending,
        "message": (
            "Bình luận của bạn đang chờ duyệt."
            if pending
            else "Đã đăng bình luận."
        ),
        # Public projection only.
        "comment": {
            "id": saved["id"],
            "body": saved["body"],
            "author_name": saved["author_name"],
            "author_avatar": saved["author_avatar"],
            "created_at": saved["created_at"],
            "status": saved["status"],
        },
    }


# ============= admin moderation routes =============
@router.get("/admin/comments")
async def admin_list_comments(
    status: str | None = Query(default=None),
    _admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    if status and status not in VALID_STATUSES:
        raise HTTPException(400, "invalid_status")
    return {
        "comments": _db().list_all_comments(status),
        "stats": _db().get_comment_stats(),
    }


@router.post("/admin/comments/{comment_id}/approve")
async def admin_approve_comment(
    comment_id: str, _admin: dict[str, Any] = Depends(require_admin)
) -> dict[str, Any]:
    row = _db().set_comment_status(comment_id, "approved")
    if not row:
        raise HTTPException(404, "comment_not_found")
    return {"ok": True, "comment": row}


@router.post("/admin/comments/{comment_id}/hide")
async def admin_hide_comment(
    comment_id: str, _admin: dict[str, Any] = Depends(require_admin)
) -> dict[str, Any]:
    row = _db().set_comment_status(comment_id, "hidden")
    if not row:
        raise HTTPException(404, "comment_not_found")
    return {"ok": True, "comment": row}


@router.delete("/admin/comments/{comment_id}")
async def admin_delete_comment(
    comment_id: str, _admin: dict[str, Any] = Depends(require_admin)
) -> dict[str, Any]:
    if not _db().delete_comment(comment_id):
        raise HTTPException(404, "comment_not_found")
    return {"ok": True, "deleted": comment_id}
