#!/usr/bin/env python3
"""
push_report.py — Đẩy 1 báo cáo .md lên backend (SQLite, OAuth-gated).

Từ khi report được chặn THẬT (không còn nằm trong static/ public), file .md tạo
qua phím tắt `??` phải đẩy lên backend qua endpoint POST /reports thay vì commit
vào repo. Script này là cầu nối: admin chạy local với session id (sid) của mình.

Lấy sid: đăng nhập /editor/ hoặc /bao-cao-tong-ket/ trên blog → mở DevTools →
  sessionStorage.getItem('zola-cms-session-id')

Dùng:
    python3 scripts/push_report.py <file.md> \
        --sid "<session_id>" \
        [--api https://blog-vipzone-api.onrender.com] \
        [--name bao-cao-YYYYMMDD-HHMMSS.md]

Env thay cho flag: REPORT_API_SID, REPORT_API_URL.
Exit 0 nếu OK, !=0 nếu lỗi (in message backend trả về).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_API = "https://blog-vipzone-api.onrender.com"


def extract_preview(content: str, max_chars: int = 500) -> str:
    """Extract preview text from markdown content (remove frontmatter + markdown syntax)."""
    # Strip frontmatter
    if content.startswith("+++"):
        match = re.search(r"^\+\+\+\n(.*?)\n\+\+\+\n(.*)$", content, re.DOTALL)
        if match:
            content = match.group(2)
    # Remove markdown syntax and limit length
    text = content.replace("#", "").replace("*", "").replace("[", "").replace("]", "")
    text = re.sub(r"\n\n+", " ", text).strip()
    return text[:max_chars]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Đẩy báo cáo .md lên backend OAuth-gated.")
    ap.add_argument("file", help="Đường dẫn file .md cần đẩy")
    ap.add_argument("--sid", default=os.getenv("REPORT_API_SID", ""), help="Session id (Bearer)")
    ap.add_argument("--api", default=os.getenv("REPORT_API_URL", DEFAULT_API), help="Backend URL")
    ap.add_argument("--name", default="", help="Tên file lưu (mặc định = tên file gốc)")
    args = ap.parse_args(argv[1:])

    path = Path(args.file)
    if not path.is_file():
        print(f"✗ Không thấy file: {path}", file=sys.stderr)
        return 2
    if not args.sid:
        print("✗ Thiếu --sid (hoặc env REPORT_API_SID).", file=sys.stderr)
        return 2

    filename = args.name.strip() or path.name
    content = path.read_text(encoding="utf-8")
    preview = extract_preview(content)

    payload = json.dumps({
        "filename": filename,
        "content": content,
        "preview": preview,
    }).encode("utf-8")

    req = urllib.request.Request(
        args.api.rstrip("/") + "/reports",
        data=payload,
        method="POST",
        headers={
            "Authorization": "Bearer " + args.sid,
            "Content-Type":  "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            body = json.loads(res.read().decode("utf-8"))
        created_at = body.get("created_at", "")
        print(f"✓ Đã đẩy '{filename}' lên backend ({created_at}).")
        print(json.dumps(body, ensure_ascii=False, indent=2))
        return 0
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        print(f"✗ Lỗi HTTP {e.code}: {detail}", file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"✗ Không kết nối được backend: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
