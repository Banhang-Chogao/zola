#!/usr/bin/env python3
"""
scheduled_publish.py — Đẩy bài draft đã tới giờ hẹn lên production.

Cơ chế "viết trước, đăng sau" (phím tắt `bb9`):
  - Bài viết được lưu dạng draft: frontmatter có `draft = true` và
    `[extra] publish_at = "<ISO8601 có timezone>"` (vd "2026-06-19T20:00:00+07:00").
  - Zola build mặc định BỎ QUA draft → bài KHÔNG lên site cho tới khi được flip.
  - Script này (chạy bởi workflow cron buổi tối) quét content, bài nào có
    `publish_at <= bây giờ` (giờ Việt Nam) thì:
        * draft = true  -> draft = false
        * date          -> set bằng ngày publish (hiển thị đúng ngày đăng)
        * xoá dòng publish_at
    rồi để workflow commit + push lên main → deploy + QA gate.

stdlib-only (tomllib + zoneinfo). Idempotent. Exit code:
  0  : chạy xong (kể cả không có bài nào tới hạn)
  Nếu có bài được flip → in "PUBLISHED:" cho từng file để workflow biết có thay đổi.
"""
from __future__ import annotations

import re
import sys
import tomllib
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Ho_Chi_Minh")
CONTENT_DIR = Path("content")
FM_RE = re.compile(r"^\+\+\+\s*\n(.*?)\n\+\+\+", re.S)


def parse_frontmatter(text: str):
    m = FM_RE.search(text)
    if not m:
        return None, None
    try:
        data = tomllib.loads(m.group(1))
    except Exception:
        return None, None
    return data, m


def to_dt(value) -> datetime | None:
    """publish_at có thể là str ISO hoặc datetime (tomllib tự parse offset datetime)."""
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value)
        except ValueError:
            return None
    else:
        return None
    # Naive → coi như giờ VN
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    return dt


def flip_to_published(text: str, publish_dt: datetime) -> str:
    m = FM_RE.search(text)
    fm = m.group(1)

    # draft = true -> false
    fm = re.sub(r"(?m)^(\s*draft\s*=\s*)true\s*$", r"\1false", fm)
    # date = ... -> ngày publish (top-level, dòng đầu tiên match)
    date_str = publish_dt.strftime("%Y-%m-%d")
    if re.search(r"(?m)^\s*date\s*=", fm):
        fm = re.sub(r"(?m)^(\s*date\s*=\s*).*$", rf"\g<1>{date_str}", fm, count=1)
    # Xoá dòng publish_at (cả khi có comment trailing)
    fm = re.sub(r"(?m)^\s*publish_at\s*=.*\n?", "", fm)

    return text[: m.start(1)] + fm + text[m.end(1):]


def main() -> int:
    if not CONTENT_DIR.is_dir():
        print("scheduled_publish: không thấy thư mục content/.")
        return 0

    now = datetime.now(TZ)
    published = pending = 0

    for f in sorted(CONTENT_DIR.rglob("*.md")):
        text = f.read_text(encoding="utf-8")
        data, _ = parse_frontmatter(text)
        if not data or data.get("draft") is not True:
            continue
        publish_at = (data.get("extra") or {}).get("publish_at")
        if publish_at is None:
            continue
        dt = to_dt(publish_at)
        if dt is None:
            print(f"  ⚠ publish_at không hợp lệ, bỏ qua: {f}")
            continue
        if now >= dt:
            f.write_text(flip_to_published(text, dt), encoding="utf-8")
            published += 1
            print(f"PUBLISHED: {f} (hẹn {dt.isoformat()})")
        else:
            pending += 1
            print(f"  ⏳ chờ: {f} → {dt.isoformat()}")

    print(f"scheduled_publish: {published} bài đăng, {pending} bài còn chờ. now={now.isoformat()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
