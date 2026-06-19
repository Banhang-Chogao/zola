"""
VIPZone API — MoMo payment requests, 16-digit approve codes, VIP admin.

Public:
  GET  /
  GET  /health
  POST /api/vipzone/payment-request
  POST /api/vipzone/redeem

Auth (GitHub OAuth on this service — Authorization: Bearer <cms_sid>):
  GET  /auth/login?return_to=...
  GET  /auth/callback
  GET  /auth/me
  POST /auth/logout

Admin (CMS GitHub session — Authorization: Bearer <cms_sid>):
  GET  /api/vipzone/admin/requests
  POST /api/vipzone/admin/requests/{id}/resolve
  GET  /api/vipzone/admin/codes
  POST /api/vipzone/admin/codes
  GET  /api/vipzone/admin/users
  POST /api/vipzone/admin/users/{email}/deactivate
  POST /api/vipzone/admin/users/{email}/activate
  GET  /api/vipzone/admin/stats
  GET  /api/vipzone/admin/picker
  PUT  /api/vipzone/admin/picker

Session (CMS GitHub session — Authorization: Bearer <cms_sid>):
  GET  /api/vipzone/me
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

from catalog_loader import load_catalog, migrate_picks_sync
from cms_auth import BACKEND_URL, cms_profile_from_session, is_admin, router as auth_router
from db import DEFAULT_DB, PLAN_DAYS, VipzoneDB
from roles import is_supervip, resolve_role

CORS_ORIGIN = os.getenv("VIPZONE_CORS_ORIGIN", "https://banhang-chogao.github.io")
BLOG_URL = os.getenv("VIPZONE_BLOG_URL", "https://banhang-chogao.github.io/zola").rstrip("/")
DB_PATH = os.getenv("VIPZONE_DB_PATH", "")

ADMIN_EMAILS = {
    e.strip().lower()
    for e in os.getenv("ADMIN_EMAILS", "292648126+banhang-chogao@users.noreply.github.com").split(",")
    if e.strip()
}
ADMIN_USERNAMES = {
    u.strip().lower()
    for u in os.getenv("ADMIN_USERNAMES", "banhang-chogao").split(",")
    if u.strip()
}

MOMO_MONTHLY = os.getenv(
    "VIPZONE_MOMO_MONTHLY",
    "https://me.momo.vn/G5T1CDFRuJFWfBCDiK/MvbmqW94lpp0bYA",
)
MOMO_SEMIANNUAL = os.getenv(
    "VIPZONE_MOMO_SEMIANNUAL",
    "https://me.momo.vn/G5T1CDFRuJFWfBCDiK/lNbWPA9NgD64dyg",
)

_db: VipzoneDB | None = None
_pending_codes: dict[str, str] = {}


def get_db() -> VipzoneDB:
    global _db
    if _db is None:
        _db = VipzoneDB(Path(DB_PATH) if DB_PATH else DEFAULT_DB)
    return _db


app = FastAPI(title="VIPZone API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[CORS_ORIGIN, "http://127.0.0.1:1111", "http://localhost:1111"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)


async def require_admin(authorization: str = Header(default="")) -> dict[str, Any]:
    profile = await cms_profile_from_session(get_db(), authorization)
    if not is_admin(profile.get("email"), profile.get("username")):
        raise HTTPException(403, "admin_only")
    return profile


async def require_supervip(authorization: str = Header(default="")) -> dict[str, Any]:
    profile = await cms_profile_from_session(get_db(), authorization)
    if not is_supervip(profile.get("email"), profile.get("username")):
        raise HTTPException(403, "supervip_required")
    return profile


def _role_payload(profile: dict[str, Any]) -> dict[str, Any]:
    email = profile.get("email") or ""
    username = profile.get("username") or ""
    vip_row = get_db().get_active_vip(email)
    role = resolve_role(email, username, is_vip=vip_row is not None)
    out: dict[str, Any] = {
        "email": profile.get("email"),
        "username": username,
        "name": profile.get("name"),
        "avatar": profile.get("avatar"),
        "role": role,
    }
    if vip_row:
        out["vip_plan"] = vip_row.get("plan")
        out["vip_expires_at"] = vip_row.get("expires_at")
    return out


class PaymentRequestIn(BaseModel):
    email: EmailStr
    plan: str = Field(pattern=r"^(monthly|semiannual)$")
    payment_note: str = ""


class RedeemIn(BaseModel):
    code: str
    email: EmailStr | None = None


class CodeIn(BaseModel):
    plan: str = Field(pattern=r"^(monthly|semiannual)$")
    email: EmailStr | None = None


class ActivateIn(BaseModel):
    plan: str = Field(default="monthly", pattern=r"^(monthly|semiannual)$")


class PickerIn(BaseModel):
    picks: list[str] = Field(default_factory=list)


def _health_payload() -> dict[str, Any]:
    from cms_auth import GH_CLIENT_ID, GH_CLIENT_SECRET

    return {
        "service": "vipzone",
        "status": "ok",
        "blog_url": BLOG_URL,
        "cms_auth": BACKEND_URL,
        "vipzone_auth": BACKEND_URL,
        "oauth_configured": bool(GH_CLIENT_ID and GH_CLIENT_SECRET),
        "momo_configured": bool(MOMO_MONTHLY and MOMO_SEMIANNUAL),
    }


@app.get("/")
def root() -> dict[str, Any]:
    return _health_payload()


@app.get("/health")
def health() -> dict[str, Any]:
    return _health_payload()


@app.post("/api/vipzone/payment-request")
def payment_request(body: PaymentRequestIn) -> dict[str, Any]:
    db = get_db()
    rid = db.insert_payment_request(
        {
            "email": str(body.email),
            "plan": body.plan,
            "payment_note": body.payment_note,
        }
    )
    momo = MOMO_MONTHLY if body.plan == "monthly" else MOMO_SEMIANNUAL
    return {
        "request_id": rid,
        "status": "pending",
        "message": "Đã gửi yêu cầu kích hoạt.",
        "momo_link": momo,
    }


@app.get("/api/vipzone/me")
async def vipzone_me(authorization: str = Header(default="")) -> dict[str, Any]:
    profile = await cms_profile_from_session(get_db(), authorization)
    return _role_payload(profile)


@app.post("/api/vipzone/redeem")
def redeem(body: RedeemIn) -> dict[str, Any]:
    code = re.sub(r"\D", "", body.code or "")
    if len(code) != 16:
        raise HTTPException(400, "Mã phải đủ 16 chữ số.")
    db = get_db()
    row = db.find_unused_code(code)
    if not row:
        raise HTTPException(400, "Mã không hợp lệ hoặc đã dùng.")
    email = (str(body.email) if body.email else row.get("email") or "").lower().strip()
    if not email:
        raise HTTPException(400, "Thiếu email.")
    from datetime import datetime, timedelta, timezone

    days = PLAN_DAYS.get(row["plan"], 30)
    exp = datetime.now(timezone.utc) + timedelta(days=days)
    expires_at = exp.strftime("%Y-%m-%dT%H:%M:%SZ")
    db.mark_code_used(row["id"])
    vip = db.upsert_vip(email, row["plan"], expires_at)
    return {
        "email": vip["email"],
        "plan": vip["plan"],
        "activated_at": vip["activated_at"],
        "expires_at": vip["expires_at"],
    }


@app.get("/api/vipzone/admin/requests")
async def admin_requests(
    authorization: str = Header(default=""),
    status: str | None = Query(default=None),
) -> list[dict[str, Any]]:
    await require_admin(authorization)
    return get_db().list_payment_requests(status)


@app.post("/api/vipzone/admin/requests/{request_id}/resolve")
async def admin_resolve_request(request_id: str, authorization: str = Header(default="")):
    await require_admin(authorization)
    if not get_db().resolve_payment_request(request_id):
        raise HTTPException(404, "request_not_found")
    return {"ok": True}


@app.get("/api/vipzone/admin/codes")
async def admin_list_codes(authorization: str = Header(default="")) -> list[dict[str, Any]]:
    await require_admin(authorization)
    rows = get_db().list_codes()
    for r in rows:
        cid = r["id"]
        if cid in _pending_codes:
            r["code"] = _pending_codes[cid]
    return rows


@app.post("/api/vipzone/admin/codes")
async def admin_create_code(body: CodeIn, authorization: str = Header(default="")):
    await require_admin(authorization)
    db = get_db()
    code = db.gen_code16()
    cid = db.insert_code(
        {
            "code_hash": db.hash_code(code),
            "plan": body.plan,
            "email": str(body.email) if body.email else None,
        }
    )
    _pending_codes[cid] = code
    return {
        "code_id": cid,
        "code": code,
        "plan": body.plan,
        "email": str(body.email) if body.email else None,
    }


@app.get("/api/vipzone/admin/users")
async def admin_list_users(authorization: str = Header(default="")) -> list[dict[str, Any]]:
    await require_admin(authorization)
    return get_db().list_vips()


@app.post("/api/vipzone/admin/users/{email}/deactivate")
async def admin_deactivate_user(email: str, authorization: str = Header(default="")):
    await require_admin(authorization)
    if not get_db().deactivate_vip(email):
        raise HTTPException(404, "vip_not_found")
    return {"ok": True}


@app.post("/api/vipzone/admin/users/{email}/activate")
async def admin_activate_user(
    email: str,
    body: ActivateIn,
    authorization: str = Header(default=""),
):
    await require_admin(authorization)
    vip = get_db().activate_vip(email, body.plan)
    if not vip:
        raise HTTPException(400, "activate_failed")
    return {"ok": True, "vip": vip}


@app.get("/api/vipzone/admin/stats")
async def admin_stats(authorization: str = Header(default="")) -> dict[str, Any]:
    await require_admin(authorization)
    return get_db().get_stats()


@app.get("/api/vipzone/admin/picker/catalog")
async def admin_picker_catalog(authorization: str = Header(default="")) -> dict[str, Any]:
    await require_admin(authorization)
    return await load_catalog()


@app.get("/api/vipzone/admin/picker")
async def admin_get_picker(authorization: str = Header(default="")) -> dict[str, Any]:
    await require_admin(authorization)
    db = get_db()
    catalog = await load_catalog()
    raw = db.get_picker()
    picks = migrate_picks_sync(raw, catalog)
    if picks != raw:
        db.set_picker(picks)
    return {"picks": picks}


@app.put("/api/vipzone/admin/picker")
async def admin_set_picker(body: PickerIn, authorization: str = Header(default="")):
    await require_admin(authorization)
    catalog = await load_catalog()
    picks = migrate_picks_sync(body.picks, catalog)
    picks = get_db().set_picker(picks)
    return {"ok": True, "picks": picks}
