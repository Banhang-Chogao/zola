"""
FastAPI Paywall backend — unlock premium content, admin approve codes.

Run:
  uvicorn backend.paywall_app:app --reload --port 8787

Env:
  PAYWALL_ADMIN_TOKEN, PAYWALL_DB_PATH, PAYWALL_CORS_ORIGIN
  SMTP_* for email
  MOMO_PAYMENT_LINK (optional override)
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import markdown
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.paywall_auth import (
    generate_access_token,
    generate_approve_code,
    generate_trace_code,
    hash_code,
    hash_email,
    is_expired,
    session_expires,
    token_hash,
    verify_admin_token,
)
from backend.paywall_db import PaywallDB
from backend.paywall_email import send_approve_email
from backend.paywall_models import (
    AccessRequestIn,
    AccessRequestOut,
    ContentOut,
    GenerateCodeIn,
    GenerateCodeOut,
    SendEmailIn,
    UnlockIn,
    UnlockOut,
)

ROOT = Path(__file__).resolve().parent.parent
PRIVATE_CONTENT = ROOT / "private_content"
MOMO_LINK = os.getenv(
    "MOMO_PAYMENT_LINK",
    "https://me.momo.vn/G5T1CDFRuJFWfBCDiK/zPdywWy346xVaQr",
)
BLOG_DOMAIN = os.getenv("PAYWALL_BLOG_DOMAIN", "banhang-chogao.github.io")
BLOG_NAME = os.getenv("PAYWALL_BLOG_NAME", "Duy Nguyen Blog")

# In-memory plaintext codes until email sent (code_id -> code); not persisted
_pending_codes: dict[str, str] = {}

app = FastAPI(title="Zola Paywall API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("PAYWALL_CORS_ORIGIN", "https://banhang-chogao.github.io"),
        "http://127.0.0.1:1111",
        "http://localhost:1111",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db() -> PaywallDB:
    path = os.getenv("PAYWALL_DB_PATH", str(ROOT / "data" / "paywall.db"))
    return PaywallDB(path)


def require_admin(authorization: str | None = Header(default=None)) -> None:
    if not verify_admin_token(authorization):
        raise HTTPException(status_code=401, detail="Admin token không hợp lệ")


def _load_premium_html(post_id: str) -> str:
    path = PRIVATE_CONTENT / f"{post_id}.md"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Nội dung premium không tồn tại")
    text = path.read_text(encoding="utf-8")
    return markdown.markdown(text, extensions=["extra", "nl2br", "sane_lists"])


def _validate_session(authorization: str | None, post_id: str) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Thiếu access token")
    token = authorization.removeprefix("Bearer ").strip()
    db = get_db()
    sess = db.get_session(token_hash(token))
    if not sess or is_expired(sess["expires_at"]):
        raise HTTPException(status_code=401, detail="Session hết hạn — nhập lại approve code")
    if sess["post_id"] != post_id:
        raise HTTPException(status_code=403, detail="Token không áp dụng cho bài này")
    return sess


@app.get("/")
def health() -> dict:
    return {"service": "paywall", "status": "ok", "momo_configured": bool(MOMO_LINK)}


@app.post("/api/paywall/request-access", response_model=AccessRequestOut)
def request_access(body: AccessRequestIn) -> AccessRequestOut:
    db = get_db()
    rid = db.insert_request(
        {
            "post_id": body.post_id,
            "post_title": body.post_title,
            "post_url": body.post_url,
            "email": str(body.email),
            "payment_method": "momo",
            "payment_link": MOMO_LINK,
            "payment_note": body.payment_note,
        }
    )
    db.log_event("request_access", post_id=body.post_id, email_hash=hash_email(str(body.email)))
    return AccessRequestOut(request_id=rid, status="pending")


@app.get("/api/paywall/admin/requests")
def admin_list_requests(
    status: str | None = None,
    _: None = Depends(require_admin),
) -> list[dict]:
    return get_db().list_requests(status=status or "pending")


@app.post("/api/paywall/admin/generate-code", response_model=GenerateCodeOut)
def admin_generate_code(
    body: GenerateCodeIn,
    _: None = Depends(require_admin),
) -> GenerateCodeOut:
    code = (body.approve_code or generate_approve_code()).strip().upper()
    if not re.fullmatch(r"[A-Z0-9]{4,64}", code):
        raise HTTPException(status_code=400, detail="Approve code không hợp lệ")

    expires_at = PaywallDB.expires_from_days(body.expires_days)
    db = get_db()
    cid = db.insert_code(
        {
            "approve_code_hash": hash_code(code),
            "email": str(body.email),
            "post_id": body.post_id,
            "post_url": body.post_url,
            "expires_at": expires_at,
            "max_usage": body.max_usage,
        }
    )
    _pending_codes[cid] = code

    if body.request_id:
        db.update_request_status(body.request_id, "approved")

    db.log_event(
        "generate_code",
        post_id=body.post_id,
        email_hash=hash_email(str(body.email)),
        meta={"code_id": cid},
    )
    return GenerateCodeOut(code_id=cid, approve_code=code, expires_at=expires_at)


@app.post("/api/paywall/admin/send-code-email")
def admin_send_email(
    body: SendEmailIn,
    authorization: str | None = Header(default=None),
) -> dict:
    require_admin(authorization)
    db = get_db()
    row = db.get_code_by_id(body.code_id)
    if not row:
        raise HTTPException(status_code=404, detail="Code không tồn tại")

    plain = _pending_codes.get(body.code_id)
    if not plain:
        raise HTTPException(
            status_code=400,
            detail="Approve code plaintext không còn trong bộ nhớ — tạo code mới và gửi ngay",
        )

    try:
        send_approve_email(
            to_email=row["email"],
            post_title=body.post_title,
            post_url=body.post_url,
            approve_code=plain,
            expires_at=row["expires_at"],
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    del _pending_codes[body.code_id]
    db.log_event("send_email", post_id=row["post_id"], email_hash=hash_email(row["email"]))
    return {"sent": True, "to": row["email"]}


@app.post("/api/paywall/unlock", response_model=UnlockOut)
def unlock(body: UnlockIn) -> UnlockOut:
    db = get_db()
    email = str(body.email).lower().strip()
    code_plain = body.approve_code.strip().upper()
    code_h = hash_code(code_plain)

    rows = db.get_code_for_unlock(email, body.post_id)
    if not rows:
        raise HTTPException(status_code=403, detail="Email hoặc approve code không khớp bài này")

    matched = None
    for row in rows:
        if row["approve_code_hash"] == code_h:
            matched = row
            break

    if not matched:
        raise HTTPException(status_code=403, detail="Approve code sai")

    if is_expired(matched["expires_at"]):
        raise HTTPException(status_code=403, detail="Approve code đã hết hạn")

    if matched["usage_count"] >= matched["max_usage"]:
        raise HTTPException(status_code=403, detail="Approve code đã vượt lượt sử dụng")

    trace = generate_trace_code()
    reader_hash = hash_email(email)
    token = generate_access_token()
    exp = session_expires()

    db.increment_code_usage(matched["code_id"])
    db.insert_session(
        {
            "token_hash": token_hash(token),
            "email": email,
            "post_id": body.post_id,
            "trace_code": trace,
            "reader_email_hash": reader_hash,
            "expires_at": exp,
        }
    )
    db.log_event("unlock", post_id=body.post_id, email_hash=reader_hash, meta={"trace": trace})

    return UnlockOut(
        access_token=token,
        expires_at=exp,
        trace_code=trace,
        reader_email_hash=reader_hash,
    )


@app.get("/api/paywall/content/{post_id}", response_model=ContentOut)
def get_content(
    post_id: str,
    authorization: str | None = Header(default=None),
) -> ContentOut:
    sess = _validate_session(authorization, post_id)
    html = _load_premium_html(post_id)
    db = get_db()
    db.log_event("content_fetch", post_id=post_id, email_hash=sess["reader_email_hash"])
    return ContentOut(
        post_id=post_id,
        html=html,
        trace_code=sess["trace_code"],
        reader_email_hash=sess["reader_email_hash"],
    )


@app.post("/api/paywall/log-print")
def log_print(
    post_id: str,
    authorization: str | None = Header(default=None),
) -> dict:
    sess = _validate_session(authorization, post_id)
    watermark = f"{sess['trace_code']}_{BLOG_DOMAIN}"
    get_db().log_event(
        "print_attempt",
        post_id=post_id,
        email_hash=sess["reader_email_hash"],
        meta={"watermark": watermark},
    )
    return {"watermark": watermark, "blog_domain": BLOG_DOMAIN}