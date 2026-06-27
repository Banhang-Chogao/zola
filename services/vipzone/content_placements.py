"""
Content Placement Admin Routes — manage editable content blocks bound to stable
placement IDs (the placement registry) for the SEOMONEY blog.

Concept:  Placement Registry → Content Blocks → Render by placement_id
The registry (stable placement IDs) is the source of truth for *where* content
renders; a content block is the editable *what* (title/body/CTA/url) bound to a
placement_id. Templates render blocks via templates/macros/placement.html, which
reads data/content-placements.json at build time.

Data file: data/content-placements.json  { version, placements[], blocks[] }

Auth: admin-only (Google whitelist via the VIPZone CMS session). Writes commit
the JSON to GitHub (Contents API) so deploy.yml rebuilds the static site. The
commit uses a service token when configured; for a GitHub-login admin it can fall
back to the OAuth token. When no token is available the change is saved locally
and the response reports committed=false (graceful — never 500s the admin).

Endpoints (all under /admin, all admin-gated):
  GET    /admin/content-placements           registry + blocks
  GET    /admin/content-blocks               blocks only
  POST   /admin/content-blocks               create a block
  PATCH  /admin/content-blocks/{block_id}    update a block
  DELETE /admin/content-blocks/{block_id}    delete a block
  POST   /admin/content-blocks/reorder       set priority order within a placement
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

import httpx
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException
from pydantic import BaseModel

from cms_auth import (
    SESSION_COOKIE_NAME,
    cms_profile_from_session,
    is_admin,
    is_commenter_only,
)
from roles import is_superadmin

router = APIRouter(prefix="/admin", tags=["content-placements"])

DATA_PATH = Path(__file__).parents[2] / "data" / "content-placements.json"
REPO_RELATIVE = "data/content-placements.json"

ALLOWED_TYPES = {
    "momo_cta",
    "donate_box",
    "premium_cta",
    "notice",
    "banner",
    "html_safe",
    "link_card",
}
# Types that must carry a clickable CTA (url + button_text).
CTA_TYPES = {"momo_cta", "donate_box", "premium_cta", "link_card"}
# Types whose url must be a MoMo link.
MOMO_TYPES = {"momo_cta", "donate_box"}

_BLOCK_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,79}$")
_HTTPS_RE = re.compile(r"^https://[^\s\"'<>]+$")
# Obvious script-injection signatures rejected in html_safe bodies.
_UNSAFE_HTML_RE = re.compile(
    r"(?is)(<\s*script|</\s*script|javascript:|\son\w+\s*=|<\s*iframe|<\s*object|<\s*embed)"
)

TITLE_MAX = 200
BODY_MAX = 4000
BUTTON_MAX = 60
STYLE_RE = re.compile(r"^[a-z0-9_-]{1,24}$")

# Token getter injected by configure(): async (authorization, cookie_sid) -> token.
_get_token: Optional[Callable[[str, Optional[str]], Awaitable[str]]] = None


def configure(get_token: Callable[[str, Optional[str]], Awaitable[str]]) -> None:
    """Wire the GitHub-token resolver from the host app (vipzone main.py)."""
    global _get_token
    _get_token = get_token


# ============= Auth =============
async def require_cp_admin(
    authorization: str = Header(default=""),
    cookie_sid: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> dict[str, Any]:
    """Admin-only guard (mirrors momo_links.require_momo_admin)."""
    from main import get_db

    profile = await cms_profile_from_session(
        get_db(), authorization or "", cookie_sid=cookie_sid
    )
    if is_commenter_only(profile):
        raise HTTPException(403, "admin_only")
    if not (
        is_admin(profile.get("email"), profile.get("username"))
        or is_superadmin(profile)
    ):
        raise HTTPException(403, "admin_only")
    return profile


# ============= Storage =============
def _load() -> dict[str, Any]:
    if not DATA_PATH.exists():
        return {"version": 1, "placements": [], "blocks": []}
    try:
        data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except Exception:
        raise HTTPException(500, "content_placements_unreadable")
    data.setdefault("placements", [])
    data.setdefault("blocks", [])
    return data


def _placement_ids(data: dict[str, Any]) -> set[str]:
    return {p.get("id") for p in data.get("placements", []) if p.get("id")}


def _block_ids(data: dict[str, Any]) -> set[str]:
    return {b.get("id") for b in data.get("blocks", []) if b.get("id")}


async def _persist(
    data: dict[str, Any], message: str, authorization: str, cookie_sid: str | None
) -> dict[str, Any]:
    """Write the JSON locally (best-effort) and commit it to GitHub so deploy.yml
    rebuilds the site. Never raises on a missing token — reports committed=false."""
    content = json.dumps(data, ensure_ascii=False, indent=2) + "\n"

    # Best-effort local write (keeps GET consistent within this container).
    try:
        DATA_PATH.write_text(content, encoding="utf-8")
    except Exception:
        pass

    token = None
    if _get_token is not None:
        try:
            token = await _get_token(authorization or "", cookie_sid)
        except HTTPException:
            token = None
        except Exception:
            token = None

    if not token:
        return {
            "committed": False,
            "reason": "no_github_token",
            "note": "Đã lưu cục bộ. Cấu hình CONTENT_PLACEMENTS_GH_TOKEN (hoặc đăng nhập bằng GitHub) để tự commit + deploy.",
        }

    try:
        from cms_repo import _gh_get_file, _gh_put_file

        async with httpx.AsyncClient(timeout=20.0) as client:
            sha, _ = await _gh_get_file(client, REPO_RELATIVE, token)
            resp = await _gh_put_file(client, REPO_RELATIVE, content, sha, message, token)
        commit = resp.get("commit", {}) if isinstance(resp, dict) else {}
        return {
            "committed": True,
            "commit_sha": commit.get("sha", ""),
            "commit_url": commit.get("html_url", ""),
            "deploy_eta": "1-2 phút (GitHub Actions auto build + deploy)",
        }
    except HTTPException as exc:
        # Commit failed (e.g. token lacks repo scope) — keep the local write, report it.
        return {"committed": False, "reason": f"commit_failed:{exc.detail}"}


# ============= Validation =============
class BlockIn(BaseModel):
    id: str | None = None
    placement_id: str | None = None
    type: str | None = None
    enabled: bool | None = None
    title: str | None = None
    body: str | None = None
    button_text: str | None = None
    url: str | None = None
    style: str | None = None
    priority: int | None = None
    pages: list[str] | None = None
    exclude_pages: list[str] | None = None
    start_date: str | None = None
    end_date: str | None = None


class ReorderIn(BaseModel):
    placement_id: str
    order: list[str]


def _validate_url(url: str, block_type: str) -> None:
    if not _HTTPS_RE.match(url):
        raise HTTPException(400, "url_must_be_https")
    if block_type in MOMO_TYPES and not url.startswith("https://me.momo.vn/"):
        raise HTTPException(400, "momo_url_required")


def _validate_block(block: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    """Validate a fully-merged block dict. Returns the normalized block."""
    bid = (block.get("id") or "").strip()
    if not _BLOCK_ID_RE.match(bid):
        raise HTTPException(400, "invalid_block_id")

    placement_id = (block.get("placement_id") or "").strip()
    if placement_id not in _placement_ids(data):
        raise HTTPException(400, f"unknown_placement_id:{placement_id}")

    btype = (block.get("type") or "").strip()
    if btype not in ALLOWED_TYPES:
        raise HTTPException(400, f"invalid_type:{btype}")

    title = block.get("title") or ""
    body = block.get("body") or ""
    button = block.get("button_text") or ""
    if len(title) > TITLE_MAX:
        raise HTTPException(400, "title_too_long")
    if len(body) > BODY_MAX:
        raise HTTPException(400, "body_too_long")
    if len(button) > BUTTON_MAX:
        raise HTTPException(400, "button_text_too_long")

    if btype == "html_safe" and body and _UNSAFE_HTML_RE.search(body):
        raise HTTPException(400, "html_safe_blocked_script")

    url = (block.get("url") or "").strip()
    if url:
        _validate_url(url, btype)
    if btype in CTA_TYPES:
        if not url or not button:
            raise HTTPException(400, "cta_requires_url_and_button")

    style = (block.get("style") or "default").strip() or "default"
    if not STYLE_RE.match(style):
        raise HTTPException(400, "invalid_style")

    pages = block.get("pages")
    if pages is None:
        pages = ["*"]
    exclude = block.get("exclude_pages") or []
    if not isinstance(pages, list) or not isinstance(exclude, list):
        raise HTTPException(400, "pages_must_be_lists")

    priority = block.get("priority")
    if priority is None:
        priority = 100
    try:
        priority = int(priority)
    except (TypeError, ValueError):
        raise HTTPException(400, "invalid_priority")

    return {
        "id": bid,
        "placement_id": placement_id,
        "type": btype,
        "enabled": bool(block.get("enabled", False)),
        "title": title,
        "body": body,
        "button_text": button,
        "url": url,
        "style": style,
        "priority": priority,
        "pages": pages,
        "exclude_pages": exclude,
        "start_date": (block.get("start_date") or "") or None,
        "end_date": (block.get("end_date") or "") or None,
    }


# ============= Endpoints =============
@router.get("/content-placements")
async def get_content_placements(
    _admin: dict[str, Any] = Depends(require_cp_admin),
) -> dict[str, Any]:
    data = _load()
    # Annotate each placement with its current block count for the registry table.
    counts: dict[str, int] = {}
    for b in data.get("blocks", []):
        pid = b.get("placement_id")
        if pid:
            counts[pid] = counts.get(pid, 0) + 1
    for p in data.get("placements", []):
        p["block_count"] = counts.get(p.get("id"), 0)
    return {
        "version": data.get("version", 1),
        "updated_at": data.get("updated_at", ""),
        "placements": data.get("placements", []),
        "blocks": data.get("blocks", []),
    }


@router.get("/content-blocks")
async def list_content_blocks(
    _admin: dict[str, Any] = Depends(require_cp_admin),
) -> dict[str, Any]:
    data = _load()
    return {"blocks": data.get("blocks", [])}


@router.post("/content-blocks")
async def create_content_block(
    block: BlockIn,
    _admin: dict[str, Any] = Depends(require_cp_admin),
    authorization: str = Header(default=""),
    cookie_sid: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> dict[str, Any]:
    data = _load()
    incoming = block.model_dump(exclude_none=False)
    if (incoming.get("id") or "").strip() in _block_ids(data):
        raise HTTPException(409, "block_id_exists")
    normalized = _validate_block(incoming, data)
    data["blocks"].append(normalized)
    result = await _persist(
        data, f"content-placement: add block {normalized['id']}", authorization, cookie_sid
    )
    return {"ok": True, "block": normalized, **result}


@router.patch("/content-blocks/{block_id}")
async def update_content_block(
    block_id: str,
    block: BlockIn,
    _admin: dict[str, Any] = Depends(require_cp_admin),
    authorization: str = Header(default=""),
    cookie_sid: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> dict[str, Any]:
    data = _load()
    idx = next(
        (i for i, b in enumerate(data["blocks"]) if b.get("id") == block_id), None
    )
    if idx is None:
        raise HTTPException(404, "block_not_found")

    merged = dict(data["blocks"][idx])
    for key, val in block.model_dump(exclude_none=True).items():
        merged[key] = val
    merged["id"] = block_id  # id is immutable via PATCH
    normalized = _validate_block(merged, data)
    data["blocks"][idx] = normalized
    result = await _persist(
        data, f"content-placement: update block {block_id}", authorization, cookie_sid
    )
    return {"ok": True, "block": normalized, **result}


@router.delete("/content-blocks/{block_id}")
async def delete_content_block(
    block_id: str,
    _admin: dict[str, Any] = Depends(require_cp_admin),
    authorization: str = Header(default=""),
    cookie_sid: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> dict[str, Any]:
    data = _load()
    before = len(data["blocks"])
    data["blocks"] = [b for b in data["blocks"] if b.get("id") != block_id]
    if len(data["blocks"]) == before:
        raise HTTPException(404, "block_not_found")
    result = await _persist(
        data, f"content-placement: delete block {block_id}", authorization, cookie_sid
    )
    return {"ok": True, "deleted": block_id, **result}


@router.post("/content-blocks/reorder")
async def reorder_content_blocks(
    body: ReorderIn,
    _admin: dict[str, Any] = Depends(require_cp_admin),
    authorization: str = Header(default=""),
    cookie_sid: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> dict[str, Any]:
    data = _load()
    if body.placement_id not in _placement_ids(data):
        raise HTTPException(400, "unknown_placement_id")
    order_index = {bid: i for i, bid in enumerate(body.order)}
    for b in data["blocks"]:
        if b.get("placement_id") == body.placement_id and b.get("id") in order_index:
            b["priority"] = order_index[b["id"]] * 10
    result = await _persist(
        data, f"content-placement: reorder {body.placement_id}", authorization, cookie_sid
    )
    return {"ok": True, **result}
