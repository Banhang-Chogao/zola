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
  GET  /api/vipzone/picker              (public access map)
  GET  /api/vipzone/admin/picker
  PUT  /api/vipzone/admin/picker

Session (CMS GitHub session — Authorization: Bearer <cms_sid>):
  GET  /api/vipzone/me
  GET  /api/vipzone/content/{post_id}   (VIP/supervip — premium full content)
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import markdown
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

from catalog_loader import load_catalog, migrate_picks_sync
from picker_access import expand_items, items_to_map, migrate_picker_items, sparse_items
from cms_auth import BACKEND_URL, is_admin, router as auth_router, session_dep
from db import DEFAULT_DB, PLAN_DAYS, VipzoneDB
from roles import ROLE_SUPERADMIN, ROLE_VIP, is_superadmin, resolve_role

CORS_ORIGIN = os.getenv("VIPZONE_CORS_ORIGIN", "https://seomoney.org")
BLOG_URL = os.getenv("VIPZONE_BLOG_URL", "https://seomoney.org").rstrip("/")
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

# Premium full-content bodies (git-tracked at repo root) — the SAME store the
# per-post paywall serves. The Render service checks out the whole repo, so the
# directory is two levels up from services/vipzone/.
PRIVATE_CONTENT = Path(__file__).resolve().parents[2] / "private_content"
# Commit SHA of the running backend. Render injects RENDER_GIT_COMMIT on the dyno;
# exposing it on /health lets `backend8` / `theodoi8` detect a static-site ↔ backend
# split-brain (V16) — never silently succeed when the backend lags `main`.
DEPLOYED_SHA = (os.getenv("RENDER_GIT_COMMIT") or os.getenv("VIPZONE_GIT_SHA") or "").strip()

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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)


async def require_admin(profile: dict[str, Any] = Depends(session_dep)) -> dict[str, Any]:
    if not is_admin(profile.get("email"), profile.get("username")) and not is_superadmin(profile):
        raise HTTPException(403, "admin_only")
    return profile


async def require_supervip(profile: dict[str, Any] = Depends(session_dep)) -> dict[str, Any]:
    if not is_superadmin(profile):
        raise HTTPException(403, "superadmin_required")
    return profile


def _role_payload(profile: dict[str, Any]) -> dict[str, Any]:
    email = profile.get("email") or ""
    username = profile.get("username") or ""
    is_super = is_superadmin(profile)
    vip_row = get_db().get_active_vip(email)
    role = resolve_role(is_super, is_vip=vip_row is not None)
    out: dict[str, Any] = {
        "email": profile.get("email"),
        "username": username,
        "name": profile.get("name"),
        "avatar": profile.get("avatar"),
        "role": role,
        "is_super": is_super,
        "is_admin": is_admin(email, username),
    }
    if vip_row:
        out["vip_plan"] = vip_row.get("plan")
        out["vip_expires_at"] = vip_row.get("expires_at")
    return out


async def require_vip(profile: dict[str, Any] = Depends(session_dep)) -> dict[str, Any]:
    """Authenticate the CMS session then require an active VIP (supervip bypasses).

    Reuses cms_profile_from_session (no duplicated auth) + db.get_active_vip
    (role check).
    """
    email = (profile.get("email") or "").lower().strip()
    if is_superadmin(profile):
        return {"email": email, "plan": "superadmin", "expires_at": "", "role": ROLE_SUPERADMIN}
    vip_row = get_db().get_active_vip(email)
    if not vip_row:
        raise HTTPException(403, "vip_required")
    return {
        "email": vip_row["email"],
        "plan": vip_row.get("plan"),
        "expires_at": vip_row.get("expires_at") or "",
        "role": ROLE_VIP,
    }


def _load_premium_html(post_id: str) -> str:
    """Map a premium_post_id to private_content/<id>.md and render markdown→HTML.

    Same convention + extensions the per-post paywall uses. The sanitiser blocks
    path traversal so only flat ids under private_content/ are reachable.
    """
    safe = re.sub(r"[^a-zA-Z0-9_-]", "", post_id or "")
    if not safe:
        raise HTTPException(400, "invalid_post_id")
    path = PRIVATE_CONTENT / f"{safe}.md"
    if not path.exists():
        raise HTTPException(404, "premium_content_unavailable")
    text = path.read_text(encoding="utf-8")
    return markdown.markdown(text, extensions=["extra", "nl2br", "sane_lists"])


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


class PickerItemIn(BaseModel):
    url: str
    access: str = Field(default="premium", pattern=r"^(public|premium|admin_only)$")


class PickerIn(BaseModel):
    items: list[PickerItemIn] = Field(default_factory=list)
    picks: list[str] | None = None  # legacy: URL list → premium


class VipContentOut(BaseModel):
    post_id: str
    html: str
    plan: str | None = None
    expires_at: str = ""
    deployed_sha: str = ""


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
        "deployed_sha": DEPLOYED_SHA,
        "premium_content": PRIVATE_CONTENT.is_dir(),
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
async def vipzone_me(profile: dict[str, Any] = Depends(session_dep)) -> dict[str, Any]:
    return _role_payload(profile)


@app.get("/api/vipzone/content/{post_id}", response_model=VipContentOut)
async def vipzone_content(post_id: str, vip: dict[str, Any] = Depends(require_vip)) -> VipContentOut:
    """Serve premium full content to an active VIP (or supervip) — "Premium gộp gói".

    session (CMS) → VIP role check → private_content lookup → rendered HTML.
    404 premium_content_unavailable means the backend lags `main` (split-brain,
    V16) — the frontend surfaces a "backend pending" notice instead of locking.
    """
    html = _load_premium_html(post_id)
    return VipContentOut(
        post_id=post_id,
        html=html,
        plan=vip.get("plan"),
        expires_at=vip.get("expires_at") or "",
        deployed_sha=DEPLOYED_SHA,
    )


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
    status: str | None = Query(default=None),
    _admin: dict[str, Any] = Depends(require_admin),
) -> list[dict[str, Any]]:
    return get_db().list_payment_requests(status)


@app.post("/api/vipzone/admin/requests/{request_id}/resolve")
async def admin_resolve_request(
    request_id: str,
    _admin: dict[str, Any] = Depends(require_admin),
):
    if not get_db().resolve_payment_request(request_id):
        raise HTTPException(404, "request_not_found")
    return {"ok": True}


@app.get("/api/vipzone/admin/codes")
async def admin_list_codes(_admin: dict[str, Any] = Depends(require_admin)) -> list[dict[str, Any]]:
    rows = get_db().list_codes()
    for r in rows:
        cid = r["id"]
        if cid in _pending_codes:
            r["code"] = _pending_codes[cid]
    return rows


@app.post("/api/vipzone/admin/codes")
async def admin_create_code(body: CodeIn, _admin: dict[str, Any] = Depends(require_admin)):
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
async def admin_list_users(_admin: dict[str, Any] = Depends(require_admin)) -> list[dict[str, Any]]:
    return get_db().list_vips()


@app.post("/api/vipzone/admin/users/{email}/deactivate")
async def admin_deactivate_user(email: str, _admin: dict[str, Any] = Depends(require_admin)):
    if not get_db().deactivate_vip(email):
        raise HTTPException(404, "vip_not_found")
    return {"ok": True}


@app.post("/api/vipzone/admin/users/{email}/activate")
async def admin_activate_user(
    email: str,
    body: ActivateIn,
    _admin: dict[str, Any] = Depends(require_admin),
):
    vip = get_db().activate_vip(email, body.plan)
    if not vip:
        raise HTTPException(400, "activate_failed")
    return {"ok": True, "vip": vip}


@app.get("/api/vipzone/admin/stats")
async def admin_stats(_admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    return get_db().get_stats()


@app.get("/api/vipzone/admin/picker/catalog")
async def admin_picker_catalog(_admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    return await load_catalog()


def _picker_body_to_raw(body: PickerIn) -> list[Any]:
    if body.items:
        return [{"url": i.url, "access": i.access} for i in body.items]
    if body.picks is not None:
        return list(body.picks)
    return []


@app.get("/api/vipzone/picker")
async def public_picker_config() -> dict[str, Any]:
    """Public access map for frontend gating (sparse — non-public only)."""
    catalog = await load_catalog()
    raw = get_db().get_picker()
    gated = sparse_items(migrate_picker_items(raw, catalog))
    if raw != gated:
        get_db().set_picker(gated)
    return {"items": gated, "access": items_to_map(gated)}


@app.get("/api/vipzone/admin/picker")
async def admin_get_picker(_admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    db = get_db()
    catalog = await load_catalog()
    raw = db.get_picker()
    sparse = sparse_items(migrate_picker_items(raw, catalog))
    if sparse != raw:
        db.set_picker(sparse)
    return {"items": expand_items(sparse, catalog)}


@app.put("/api/vipzone/admin/picker")
async def admin_set_picker(body: PickerIn, _admin: dict[str, Any] = Depends(require_admin)):
    catalog = await load_catalog()
    migrated = migrate_picker_items(_picker_body_to_raw(body), catalog)
    stored = get_db().set_picker(sparse_items(migrated))
    return {"ok": True, "items": expand_items(stored, catalog)}
