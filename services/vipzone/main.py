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

Reports (admin báo cáo tổng kết — Authorization: Bearer <cms_sid>, supervip only):
  GET  /reports                         (list reports)
  GET  /reports/{filename}              (download report .md)
  POST /reports                         (save new report)
  DELETE /reports/{filename}            (delete report)
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any

import markdown
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from io import BytesIO
from pydantic import BaseModel, EmailStr, Field

from admin_guideline_pdf import generate_pdf_watermark
from catalog_loader import load_catalog, migrate_picks_sync
from picker_access import expand_items, items_to_map, migrate_picker_items, sparse_items
from cms_auth import BACKEND_URL, cms_profile_from_session, github_token_from_session, is_admin, is_commenter_only, router as auth_router, session_dep
from db import DEFAULT_DB, PLAN_DAYS, VipzoneDB
from gsc_kv import SqliteKV
from roles import ROLE_SUPERADMIN, ROLE_VIP, is_superadmin, resolve_role

CORS_ORIGIN = os.getenv("VIPZONE_CORS_ORIGIN", "https://seomoney.org")
BLOG_URL = os.getenv("VIPZONE_BLOG_URL", "https://seomoney.org").rstrip("/")
DB_PATH = os.getenv("VIPZONE_DB_PATH", "")


def _cors_allow_origins() -> list[str]:
    """Build the explicit CORS allowlist.

    Credentialed fetches (``credentials: "include"`` from the admin tools) forbid
    the ``*`` wildcard, so we keep an explicit list. The primary origin comes from
    ``VIPZONE_CORS_ORIGIN`` (or the seomoney.org default) and an optional
    comma-separated ``VIPZONE_CORS_ORIGINS`` adds more. We always include the
    www. variant, the legacy GitHub Pages origin and localhost so a custom-domain
    migration never silently breaks /auth/me (auth-vaccine A1)."""
    origins: list[str] = []

    def _add(o: str) -> None:
        o = (o or "").strip().rstrip("/")
        if o and o not in origins:
            origins.append(o)

    _add(CORS_ORIGIN)
    for extra in os.getenv("VIPZONE_CORS_ORIGINS", "").split(","):
        _add(extra)
    # www. twin of the primary custom domain (apex ↔ www both reach the API).
    if CORS_ORIGIN.startswith("https://") and "://www." not in CORS_ORIGIN:
        _add(CORS_ORIGIN.replace("https://", "https://www.", 1))
    _add("https://seomoney.org")
    _add("https://www.seomoney.org")
    _add("https://banhang-chogao.github.io")  # legacy GitHub Pages origin
    _add("http://127.0.0.1:1111")
    _add("http://localhost:1111")
    return origins

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
    allow_origins=_cors_allow_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)


# ============= Google Search Console (SEO Reality Check) =============
# The GSC router (gsc_routes.py) is part of vipzone and serves /gsc/* endpoints.
# config.toml points the SEO widget at vipzone_api_url, so /gsc/* must exist on THIS app.
# Frontend's "Kết nối GSC" → /gsc/oauth/start must return 200/401/403, never 404.
# Storage: SQLite KV (this service has no Redis); auth: VIPZone CMS session (supervip).
GSC_BACKEND_URL = (
    os.getenv("VIPZONE_BACKEND_URL") or os.getenv("BACKEND_URL") or BACKEND_URL
).rstrip("/")
_gsc_kv = SqliteKV(Path(DB_PATH) if DB_PATH else DEFAULT_DB)


async def _gsc_get_store() -> SqliteKV:
    return _gsc_kv


async def _gsc_require_supervip(authorization: str) -> dict[str, Any]:
    """String-form supervip guard for the GSC router (top-level nav passes Bearer sid)."""
    profile = await cms_profile_from_session(get_db(), authorization or "")
    if not is_superadmin(profile):
        raise HTTPException(403, "superadmin_required")
    return profile


async def _gsc_require_session(authorization: str) -> dict[str, Any]:
    return await cms_profile_from_session(get_db(), authorization or "")


def _gsc_build_blog_url(return_to: str, fragment: str = "") -> str:
    rt = return_to or "/"
    if not rt.startswith("/"):
        rt = "/" + rt
    return f"{BLOG_URL}{rt}" + (f"#{fragment}" if fragment else "")


try:
    from gsc_routes import configure as _configure_gsc, router as _gsc_router

    _configure_gsc(
        get_redis=_gsc_get_store,
        require_session=_gsc_require_session,
        require_supervip=_gsc_require_supervip,
        build_blog_url=_gsc_build_blog_url,
        backend_url=GSC_BACKEND_URL,
        blog_url=BLOG_URL,
    )
    app.include_router(_gsc_router)
    GSC_MOUNTED = True
except Exception as exc:  # pragma: no cover - defensive: keep the rest of the API up
    # If the Google client libs are unavailable the rest of VIPZone must still serve;
    # /gsc/* will be absent and the SEO widget shows its calm "not configured" state.
    GSC_MOUNTED = False
    print(f"[vipzone] GSC router not mounted: {exc!r}")

# Declare AI_WRITER_MOUNTED early so the health endpoint can refer to it.
AI_WRITER_MOUNTED: bool = bool(os.getenv("CONTENT_CREATOR_AI_API_KEY"))

# ============= CMS repo-write routes (save-post / bulk-delete / categories) =============
# The blog editor (static/js/editor.js) commits posts to GitHub via
# POST {AUTH_API}/cms/save-post. AUTH_API points at THIS deployed service, but the
# route historically lived only in services/visitor-counter (Redis service, not
# deployed) → production returned 404 {"detail":"Not Found"} for every save/edit.
# Serve it HERE, sourcing the GitHub OAuth token from the vipzone CMS session.
try:
    import cms_repo

    async def _cms_get_token(authorization: str, cookie_sid: str | None = None) -> str:
        from main import get_db

        return await github_token_from_session(
            get_db(), authorization or "", cookie_sid=cookie_sid
        )

    cms_repo.configure(get_token=_cms_get_token)
    app.include_router(cms_repo.router)
    CMS_REPO_MOUNTED = True
except Exception as exc:  # pragma: no cover - defensive: keep the rest of the API up
    CMS_REPO_MOUNTED = False
    print(f"[vipzone] CMS repo router not mounted: {exc!r}")


# ============= Private Calendar + 3M Whiteboard routes =============
# Personal/private tool at /tools/calendar/ — durable, owner-scoped storage behind
# the SAME GitHub OAuth admin guard the editor uses. Mounted like cms_repo so the
# db getter is injected without a circular import.
try:
    import personal_data

    personal_data.configure(get_db=get_db)
    app.include_router(personal_data.router)
    PERSONAL_MOUNTED = True
except Exception as exc:  # pragma: no cover - defensive: keep the rest of the API up
    PERSONAL_MOUNTED = False
    print(f"[vipzone] personal_data router not mounted: {exc!r}")


# ============= Native comments (Google-auth, moderated) =============
# Replaces GitHub-only Giscus with a Google-authenticated, AdSense-safe comment
# system. Public read of approved comments + authenticated submit + admin
# moderation. Mounted like personal_data so get_db is injected without a circular
# import. config.toml points the widget at vipzone_api_url / cms_auth_url.
try:
    import comments as comments_mod

    comments_mod.configure(get_db=get_db)
    app.include_router(comments_mod.router)
    COMMENTS_MOUNTED = True
except Exception as exc:  # pragma: no cover - defensive: keep the rest of the API up
    COMMENTS_MOUNTED = False
    print(f"[vipzone] comments router not mounted: {exc!r}")


# ============= Admin Reports (báo cáo tổng kết) =============
# Reports are markdown files created by admin via ?? shortcut in Claude Code.
# Stored in SQLite (same as the rest of VIPZone), served via /reports/* (admin-gated).
try:
    import reports as reports_mod

    reports_mod.configure(get_db=get_db)
    app.include_router(reports_mod.router)
    REPORTS_MOUNTED = True
except Exception as exc:  # pragma: no cover - defensive: keep the rest of the API up
    REPORTS_MOUNTED = False
    print(f"[vipzone] reports router not mounted: {exc!r}")


# Changelog router has been removed (reverted to file-based changelog.json on 2026-06-28)


# ============= Web Vitals RUM (anonymous field data → Speed Insights) =============
# Public pages POST web-vitals samples here so the Speed Insights dashboard shows
# real cross-visitor field data instead of a single browser's localStorage. Mounted
# like comments so get_db is injected without a circular import. Fully anonymous —
# no auth, no PII stored.
try:
    import rum as rum_mod

    rum_mod.configure(get_db=get_db)
    app.include_router(rum_mod.router)
    RUM_MOUNTED = True
except Exception as exc:  # pragma: no cover - defensive: keep the rest of the API up
    RUM_MOUNTED = False
    print(f"[vipzone] rum router not mounted: {exc!r}")


# ============= MoMo Links Admin (manage payment links) =============
try:
    import momo_links

    app.include_router(momo_links.router)
    MOMO_LINKS_MOUNTED = True
except Exception as exc:  # pragma: no cover - defensive: keep the rest of the API up
    MOMO_LINKS_MOUNTED = False
    print(f"[vipzone] momo_links router not mounted: {exc!r}")


# ============= Content Placement Admin (placement registry + content blocks) =============
# Admins (Google whitelist) manage editable content blocks bound to stable
# placement IDs; writes commit data/content-placements.json so deploy.yml rebuilds.
# The commit token prefers a service PAT (Google admins have no GitHub OAuth token)
# and falls back to the admin's GitHub OAuth token when present.
try:
    import content_placements

    async def _cp_get_token(authorization: str, cookie_sid: str | None = None) -> str:
        svc = (
            os.getenv("CONTENT_PLACEMENTS_GH_TOKEN")
            or os.getenv("ZOLA_GH_TOKEN")
            or os.getenv("WORKFLOW_BOT_PAT")
            or os.getenv("GH_PAT")
        )
        if svc:
            return svc
        from main import get_db

        return await github_token_from_session(
            get_db(), authorization or "", cookie_sid=cookie_sid
        )

    content_placements.configure(get_token=_cp_get_token)
    app.include_router(content_placements.router)
    CONTENT_PLACEMENTS_MOUNTED = True
except Exception as exc:  # pragma: no cover - defensive: keep the rest of the API up
    CONTENT_PLACEMENTS_MOUNTED = False
    print(f"[vipzone] content_placements router not mounted: {exc!r}")


async def require_admin(profile: dict[str, Any] = Depends(session_dep)) -> dict[str, Any]:
    # A public commenter session can never be an admin (defense-in-depth on top of
    # the is_admin/is_super checks, which are already false for them).
    if is_commenter_only(profile):
        raise HTTPException(403, "admin_only")
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


# Routes the production frontend (config.toml → vipzone_api_url) calls on THIS
# deployed service. If any returns 404 the static site ↔ backend has split-brain
# (V24): routes added only to the undeployed services/visitor-counter never serve.
CRITICAL_ROUTES = ("/health", "/gsc/status", "/gsc/oauth/start", "/cms/save-post")


def _registered_paths() -> set[str]:
    """Path templates currently mounted on the app (after include_router calls).

    FastAPI ≥0.138 wraps included routers in an ``_IncludedRouter`` whose own
    ``path`` is ``None`` (the real routes hang off ``original_router.routes``).
    Walk those wrappers so health/diagnostics see endpoints added via
    ``include_router`` (auth, GSC, cms_repo, personal_data, heartbeats)."""
    paths: set[str] = set()

    def _walk(routes: Any) -> None:
        for route in routes or []:
            p = getattr(route, "path", None)
            if isinstance(p, str):
                paths.add(p)
            included = getattr(route, "original_router", None)
            if included is not None:
                _walk(getattr(included, "routes", None))

    _walk(getattr(app, "routes", []))
    return paths


def _critical_routes_status() -> dict[str, bool]:
    """Map each critical route → whether it is actually mounted on this app."""
    mounted = _registered_paths()
    return {r: (r in mounted) for r in CRITICAL_ROUTES}


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
        # backend_sha is an alias of deployed_sha (V24 post-deploy checker reads it).
        "backend_sha": DEPLOYED_SHA,
        "premium_content": PRIVATE_CONTENT.is_dir(),
        "gsc_mounted": GSC_MOUNTED,
        "cms_mounted": CMS_REPO_MOUNTED,
        "personal_mounted": PERSONAL_MOUNTED,
        "comments_mounted": COMMENTS_MOUNTED,
        "reports_mounted": REPORTS_MOUNTED,
        "rum_mounted": RUM_MOUNTED,
        "ai_writer_mounted": AI_WRITER_MOUNTED,
        "ai_writer_configured": bool(os.getenv("CONTENT_CREATOR_AI_API_KEY")),
        "ai_writer_dispatch_mounted": AI_WRITER_DISPATCH_MOUNTED,
        "critical_routes": _critical_routes_status(),
        "gsc_configured": bool(os.getenv("GSC_CLIENT_ID") and os.getenv("GSC_CLIENT_SECRET")),
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


@app.get("/api/admin/operation-guideline.pdf")
async def admin_get_operation_guideline_pdf(
    _admin: dict[str, Any] = Depends(require_admin),
) -> FileResponse:
    """
    Protected PDF endpoint for Operation Guideline.
    Requires admin session (Bearer token with cms_sid).
    Generates PDF on-demand with watermark.
    """
    try:
        pdf_buffer = BytesIO()
        generate_pdf_watermark(pdf_buffer)
        pdf_buffer.seek(0)

        return FileResponse(
            iter([pdf_buffer.getvalue()]),
            media_type="application/pdf",
            headers={"Content-Disposition": "inline; filename=operation-guideline.pdf"},
        )
    except ImportError as e:
        # reportlab not installed - return error
        raise HTTPException(
            status_code=503,
            detail=f"PDF generation not available: {str(e)}"
        )

try:
    from .blog_heartbeat import router as blog_heartbeat_router
except ImportError:
    from blog_heartbeat import router as blog_heartbeat_router

app.include_router(blog_heartbeat_router)

try:
    from .wd_heartbeat import router as wd_heartbeat_router
except ImportError:
    from wd_heartbeat import router as wd_heartbeat_router

app.include_router(wd_heartbeat_router)

# ============= AI Blog Writer (content-creator /write-blog) =============
try:
    import ai_writer

    async def _ai_writer_get_token(authorization: str, cookie_sid: str | None = None) -> str:
        from main import get_db

        return await github_token_from_session(
            get_db(), authorization or "", cookie_sid=cookie_sid
        )

    ai_writer.configure(get_token=_ai_writer_get_token)
    app.include_router(ai_writer.router)
    AI_WRITER_MOUNTED = True
except Exception as exc:
    AI_WRITER_MOUNTED = False
    print(f"[vipzone] AI writer router not mounted: {exc!r}")

# ============= AI Writer Dispatch (repository_dispatch proxy) =============
# Lightweight endpoint that proxies content-creator write requests to GitHub
# repository_dispatch so the browser never handles a GitHub token. The actual AI
# work runs in a GitHub Actions workflow.
try:
    import ai_writer_dispatch

    async def _ai_dispatch_get_token(authorization: str, cookie_sid: str | None = None) -> str:
        from main import get_db

        return await github_token_from_session(
            get_db(), authorization or "", cookie_sid=cookie_sid
        )

    ai_writer_dispatch.configure(get_token=_ai_dispatch_get_token)
    app.include_router(ai_writer_dispatch.router)
    AI_WRITER_DISPATCH_MOUNTED = True
except Exception as exc:
    AI_WRITER_DISPATCH_MOUNTED = False
    print(f"[vipzone] AI writer dispatch router not mounted: {exc!r}")

