"""Changelog API — admin-gated PR/commit history."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from cms_auth import is_admin, session_dep
from db import VipzoneDB

router = APIRouter()

# Injected at configure time
_get_db: callable | None = None


def configure(get_db: callable) -> None:
    global _get_db
    _get_db = get_db


def get_db() -> VipzoneDB:
    if _get_db is None:
        raise RuntimeError("changelog router not configured: call configure(get_db)")
    return _get_db()


async def _require_admin(profile: dict[str, Any] = Depends(session_dep)) -> dict[str, Any]:
    """Admin gate for changelog endpoints (checks ADMIN_EMAILS + ADMIN_USERNAMES)."""
    email = profile.get("email", "")
    username = profile.get("username", "")
    if not is_admin(email, username):
        raise HTTPException(403, "admin_only")
    return profile


class ChangelogEntryIn(BaseModel):
    title: str
    tag: str = "chore"
    date: str
    pr: int | None = None
    commit: str | None = None
    lines_added: int = 0
    lines_removed: int = 0
    highlights: list[str] = []


class ChangelogEntryOut(BaseModel):
    id: str
    title: str
    tag: str
    date: str
    pr: int | None
    commit: str | None
    lines_added: int
    lines_removed: int
    highlights: list[str]
    created_at: str


@router.get("/api/vipzone/changelog", response_model=dict[str, Any])
async def list_changelog_public() -> dict[str, Any]:
    """List all changelog entries (newest first). PUBLIC — no auth required."""
    db = get_db()
    entries = db.list_changelog()
    # Ensure only public-safe fields are returned
    public_entries = [
        {
            "id": e.get("id"),
            "title": e.get("title"),
            "tag": e.get("tag"),
            "date": e.get("date"),
            "pr": e.get("pr"),
            "commit": e.get("commit"),
            "lines_added": e.get("lines_added"),
            "lines_removed": e.get("lines_removed"),
            "highlights": e.get("highlights", []),
        }
        for e in entries
    ]
    return {"items": public_entries}


@router.get("/api/vipzone/admin/changelog", response_model=dict[str, Any])
async def list_changelog_admin(_admin: dict[str, Any] = Depends(_require_admin)) -> dict[str, Any]:
    """List all changelog entries (newest first). Admin-only."""
    db = get_db()
    entries = db.list_changelog()
    return {"items": entries}


@router.get("/api/vipzone/admin/changelog/{entry_id}", response_model=ChangelogEntryOut)
async def get_changelog(entry_id: str, _admin: dict[str, Any] = Depends(_require_admin)) -> dict[str, Any]:
    """Get a single changelog entry by ID. Admin-only."""
    db = get_db()
    entry = db.get_changelog_entry(entry_id)
    if not entry:
        raise HTTPException(404, "entry_not_found")
    return entry  # type: ignore[return-value]


@router.post("/api/vipzone/admin/changelog", response_model=dict[str, Any])
async def save_changelog(
    body: ChangelogEntryIn,
    _admin: dict[str, Any] = Depends(_require_admin),
) -> dict[str, Any]:
    """Save a new changelog entry (or update existing by date+title combo). Admin-only."""
    db = get_db()
    entry_data = {
        "title": body.title,
        "tag": body.tag,
        "date": body.date,
        "pr": body.pr,
        "commit": body.commit,
        "lines_added": body.lines_added,
        "lines_removed": body.lines_removed,
        "highlights": body.highlights,
    }
    cid = db.insert_changelog(entry_data)
    entry = db.get_changelog_entry(cid)
    return {
        "id": cid,
        "entry": entry,
    }


@router.delete("/api/vipzone/admin/changelog/{entry_id}", response_model=dict[str, Any])
async def delete_changelog(
    entry_id: str,
    _admin: dict[str, Any] = Depends(_require_admin),
) -> dict[str, Any]:
    """Delete a changelog entry by ID. Admin-only."""
    db = get_db()
    if not db.delete_changelog(entry_id):
        raise HTTPException(404, "entry_not_found")
    return {"ok": True}


@router.put("/api/vipzone/admin/changelog/{entry_id}", response_model=dict[str, Any])
async def update_changelog(
    entry_id: str,
    body: ChangelogEntryIn,
    _admin: dict[str, Any] = Depends(_require_admin),
) -> dict[str, Any]:
    """Update a changelog entry. Admin-only."""
    db = get_db()
    entry_data = {
        "title": body.title,
        "tag": body.tag,
        "date": body.date,
        "pr": body.pr,
        "commit": body.commit,
        "lines_added": body.lines_added,
        "lines_removed": body.lines_removed,
        "highlights": body.highlights,
    }
    entry = db.update_changelog(entry_id, entry_data)
    if not entry:
        raise HTTPException(404, "entry_not_found")
    return {"entry": entry}
