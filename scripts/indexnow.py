#!/usr/bin/env python3
"""Ping IndexNow để index nhanh trên Bing / Yandex / Seznam / Naver / DuckDuckGo.

Chạy tự động trong GitHub Actions mỗi khi bài viết thay đổi
(xem .github/workflows/indexnow.yml). KHÔNG ảnh hưởng tới Google: Google không
dùng IndexNow nhưng cũng không phạt — Google vẫn index qua sitemap như thường.

Cách hoạt động:
- Đọc base_url từ config.toml → suy ra host.
- Tìm IndexNow key qua file static/{key}.txt (nội dung == tên file).
- Gom URL bài viết (trang chủ + /posting/ + mọi bài trong posting/ & baochi/).
- POST danh sách lên https://api.indexnow.org/indexnow (1 endpoint fan-out mọi engine).

Best-effort: lỗi mạng / HTTP của IndexNow KHÔNG làm fail workflow.

Dùng:
    python3 scripts/indexnow.py            # gửi thật
    python3 scripts/indexnow.py --dry-run  # chỉ in payload, không gửi
"""
import glob
import json
import os
import re
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENDPOINT = "https://api.indexnow.org/indexnow"

# Section chứa bài viết thật (URL = {base}/{section}/{slug}/). KHÔNG đưa các
# section công cụ (editor, admin-author, stats…) hay pages/ (có path override).
POST_SECTIONS = ("posting", "baochi")


def read_base_url():
    with open(os.path.join(ROOT, "config.toml"), encoding="utf-8") as f:
        for line in f:
            m = re.match(r'\s*base_url\s*=\s*"([^"]+)"', line)
            if m:
                return m.group(1).rstrip("/")
    raise SystemExit("Không tìm thấy base_url trong config.toml")


def find_key():
    """IndexNow key file: static/{key}.txt với nội dung đúng bằng {key}."""
    for p in glob.glob(os.path.join(ROOT, "static", "*.txt")):
        stem = os.path.splitext(os.path.basename(p))[0]
        try:
            content = open(p, encoding="utf-8").read().strip()
        except OSError:
            continue
        if content == stem and re.fullmatch(r"[A-Za-z0-9\-]{8,128}", stem):
            return stem
    return None


def collect_urls(base):
    urls = [base + "/", base + "/posting/"]
    for section in POST_SECTIONS:
        for p in sorted(glob.glob(os.path.join(ROOT, "content", section, "*.md"))):
            name = os.path.basename(p)
            if name == "_index.md":
                continue
            urls.append(f"{base}/{section}/{name[:-3]}/")
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def main():
    dry = "--dry-run" in sys.argv
    base = read_base_url()
    host = urlparse(base).netloc
    key = find_key()
    urls = collect_urls(base)

    print(f"[IndexNow] host={host} key={'found' if key else 'MISSING'} urls={len(urls)}")
    for u in urls:
        print("  -", u)

    if not key:
        print("[IndexNow] Thiếu file static/{key}.txt → bỏ qua (không chặn).")
        return 0

    body = {
        "host": host,
        "key": key,
        "keyLocation": f"{base}/{key}.txt",
        "urlList": urls,
    }

    if dry:
        print("[IndexNow] DRY-RUN payload:")
        print(json.dumps(body, ensure_ascii=False, indent=2))
        return 0

    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "zola-indexnow",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            # 200 = OK, 202 = nhận, đang kiểm tra key.
            print(f"[IndexNow] OK HTTP {r.status}: {r.read().decode('utf-8', 'replace')[:300]}")
    except urllib.error.HTTPError as e:
        print(f"[IndexNow] HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}")
        print("[IndexNow] (cảnh báo — best-effort, không chặn deploy)")
    except Exception as e:  # noqa: BLE001 — best-effort, không bao giờ fail build
        print(f"[IndexNow] lỗi mạng: {e} (bỏ qua, không chặn)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
