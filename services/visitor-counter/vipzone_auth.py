"""Resolve VIPZone roles via CMS session + VIPZone API (no duplicated auth logic)."""

from __future__ import annotations

import os

import httpx
from fastapi import HTTPException

VIPZONE_API_URL = os.getenv("VIPZONE_API_URL", "https://blog-vipzone-api.onrender.com").rstrip("/")


async def fetch_vipzone_me(authorization: str) -> dict:
    """Call VIPZone /api/vipzone/me with the same CMS Bearer token."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing_token")
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.get(
                f"{VIPZONE_API_URL}/api/vipzone/me",
                headers={"Authorization": authorization},
            )
    except httpx.HTTPError:
        raise HTTPException(503, "vipzone_unreachable") from None
    if res.status_code == 401:
        raise HTTPException(401, "invalid_session")
    if res.status_code != 200:
        raise HTTPException(503, "vipzone_error")
    return res.json()


async def require_supervip(authorization: str, require_session) -> dict:
    """Validate CMS session and enforce role === supervip."""
    session = await require_session(authorization)
    profile = await fetch_vipzone_me(authorization)
    if profile.get("role") not in ("superadmin", "supervip"):
        raise HTTPException(403, "superadmin_required")
    return session