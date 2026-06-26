"""Reports API — admin-gated markdown downloads (báo cáo tổng kết)."""

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
        raise RuntimeError("reports router not configured: call configure(get_db)")
    return _get_db()


async def _require_admin(profile: dict[str, Any] = Depends(session_dep)) -> dict[str, Any]:
    """Admin gate for report endpoints (checks ADMIN_EMAILS + ADMIN_USERNAMES)."""
    email = profile.get("email", "")
    username = profile.get("username", "")
    if not is_admin(email, username):
        raise HTTPException(403, "admin_only")
    return profile


class SaveReportIn(BaseModel):
    filename: str
    content: str
    preview: str = ""


class ReportOut(BaseModel):
    filename: str
    created_at: str
    preview: str


class ReportContentOut(BaseModel):
    filename: str
    content: str
    created_at: str


@router.get("/reports", response_model=dict[str, Any])
async def list_reports(_admin: dict[str, Any] = Depends(_require_admin)) -> dict[str, Any]:
    """List all reports (newest first). Admin-only."""
    db = get_db()
    reports = db.list_reports()
    return {"reports": reports}


@router.get("/reports/{filename}", response_model=ReportContentOut)
async def get_report(filename: str, _admin: dict[str, Any] = Depends(_require_admin)) -> dict[str, Any]:
    """Download a single report by filename. Admin-only."""
    db = get_db()
    report = db.get_report(filename)
    if not report:
        raise HTTPException(404, "report_not_found")
    return {
        "filename": report["filename"],
        "content": report["content"],
        "created_at": report["created_at"],
    }


@router.post("/reports", response_model=dict[str, Any])
async def save_report(
    body: SaveReportIn,
    _admin: dict[str, Any] = Depends(_require_admin),
) -> dict[str, Any]:
    """Save a new report. Admin-only.

    filename should be unique. If it already exists, updates it.
    """
    db = get_db()
    # Check if report exists
    existing = db.get_report(body.filename)
    if existing:
        # Delete old one first (SQLite doesn't have UPSERT for this schema)
        db.delete_report(body.filename)

    rid = db.insert_report({
        "filename": body.filename,
        "content": body.content,
        "preview": body.preview,
    })
    return {
        "id": rid,
        "filename": body.filename,
        "created_at": existing["created_at"] if existing else None,
    }


@router.delete("/reports/{filename}", response_model=dict[str, Any])
async def delete_report(
    filename: str,
    _admin: dict[str, Any] = Depends(_require_admin),
) -> dict[str, Any]:
    """Delete a report by filename. Admin-only."""
    db = get_db()
    if not db.delete_report(filename):
        raise HTTPException(404, "report_not_found")
    return {"ok": True}
