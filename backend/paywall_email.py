"""SMTP email sender for Paywall approve codes."""

from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def _smtp_config() -> dict[str, str | int]:
    return {
        "host": os.getenv("SMTP_HOST", ""),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "user": os.getenv("SMTP_USER", ""),
        "password": os.getenv("SMTP_PASSWORD", ""),
        "from_addr": os.getenv("SMTP_FROM", os.getenv("SMTP_USER", "")),
    }


def build_email_body(
    *,
    post_title: str,
    post_url: str,
    approve_code: str,
    expires_at: str,
    blog_name: str = "Duy Nguyen Blog",
) -> str:
    return f"""Chào bạn,

Cảm ơn bạn đã thanh toán để đọc bài viết trả phí trên blog.

Bài viết: {post_title}
Link đọc bài: {post_url}

Approve code của bạn:
{approve_code}

Hướng dẫn:
1. Mở link bài viết.
2. Nhập email đã đăng ký.
3. Nhập approve code.
4. Bấm "Mở khóa bài viết".

Hiệu lực đến: {expires_at}

Lưu ý bản quyền:
Nội dung chỉ được đọc online cho mục đích cá nhân.
Không được tải về, sao chép, chia sẻ lại hoặc phân phối lại.
Nếu bạn in bài viết ra PDF/giấy, hệ thống sẽ tự động chèn watermark định danh gồm mã truy vết, email/hash và tên blog.

Cảm ơn bạn.
— {blog_name}
"""


def send_approve_email(
    *,
    to_email: str,
    post_title: str,
    post_url: str,
    approve_code: str,
    expires_at: str,
) -> None:
    cfg = _smtp_config()
    if not cfg["host"] or not cfg["user"] or not cfg["password"]:
        raise RuntimeError("SMTP chưa cấu hình (SMTP_HOST, SMTP_USER, SMTP_PASSWORD)")

    body = build_email_body(
        post_title=post_title,
        post_url=post_url,
        approve_code=approve_code,
        expires_at=expires_at,
    )

    msg = MIMEMultipart()
    msg["From"] = str(cfg["from_addr"])
    msg["To"] = to_email
    msg["Subject"] = f"Approve code — {post_title}"
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP(str(cfg["host"]), int(cfg["port"])) as server:
        server.starttls()
        server.login(str(cfg["user"]), str(cfg["password"]))
        server.sendmail(str(cfg["from_addr"]), [to_email], msg.as_string())