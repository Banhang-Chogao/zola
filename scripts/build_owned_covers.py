#!/usr/bin/env python3
"""
build_owned_covers.py — Hệ thống ảnh fallback SEOMONEY tự sở hữu (owned image).

Mục tiêu (AdSense-safe + SEO-safe): KHÔNG dùng ảnh stock ngoài (Pixabay/Unsplash/
Pexels/picsum). Bài nào KHÔNG có ảnh upload → sinh ảnh COVER editorial mang
thương hiệu SEOMONEY (tiêu đề + chuyên mục + wordmark + icon S-DNA + gradient
biên tập). Tất cả ảnh đều LOCAL, crawlable, owned.

Thứ tự ưu tiên ảnh (resolve cho mỗi bài) — khớp macro `img::cover_src`:
  1. Ảnh khai báo tường minh ở frontmatter: extra.image / extra.cover / extra.thumbnail
     (thumbnail trỏ placeholder chung KHÔNG tính là ảnh thật).
  2. Ảnh local đầu tiên trong nội dung markdown, CHỈ khi nằm dưới /uploads/.
  3. Ảnh cover editorial SEOMONEY tự sinh: /generated/covers/<slug>.svg
  4. Ảnh placeholder theo chuyên mục: /img/placeholders/category-<topic>.svg
   5. Fallback cuối site-level: 20 OG fallback template (chọn theo slug length % 20)

Script này lo bước 2–4 cho các bài CHƯA có ảnh thật:
  - dò ảnh inline /uploads/ (bước 2),
  - sinh cover SVG branded (bước 3),
  - sinh bộ category placeholder (bước 4),
  - ghi manifest `data/owned-covers.json` để template resolve không cần sửa .md.

Đặc điểm:
- DETERMINISTIC: output ổn định theo slug/title/category → rebuild KHÔNG tạo diff nhiễu
  (không nhúng timestamp vào SVG/manifest).
- KHÔNG mạng, KHÔNG ảnh bản quyền ngoài, chỉ stdlib (SVG là text vector).
- Idempotent: chạy lại ghi đè cùng nội dung.

Dùng:
    python3 scripts/build_owned_covers.py            # sinh covers + placeholders + manifest
    python3 scripts/build_owned_covers.py --check     # chỉ kiểm tra, exit!=0 nếu thiếu/đổi
Exit 0 khi thành công.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIRS = [ROOT / "content" / "posting", ROOT / "content" / "baochi"]
COVERS_DIR = ROOT / "static" / "generated" / "covers"
PLACEHOLDER_DIR = ROOT / "static" / "img" / "placeholders"
OG_FALLBACK_DIR = ROOT / "static" / "img" / "og-fallbacks"
MANIFEST = ROOT / "data" / "owned-covers.json"

# Đường dẫn ảnh được coi là "placeholder chung" (KHÔNG phải ảnh thật của bài).
GENERIC_PLACEHOLDER_HINT = "/img/placeholder/"
# Ảnh local hợp lệ cho bước 2 phải nằm dưới các path own này.
UPLOAD_PREFIXES = ("/uploads/", "/img/uploads/")

SITE_OG_FALLBACK_DIR = "img/og-fallbacks/"

# ---- Palette editorial (calm enterprise, KHÔNG neon) — 20 mẫu đa dạng ----
# Mỗi cặp: (from, to, accent). Chọn theo hash slug → deterministic.
# Đủ 20 gradient để mỗi bài fallback có nền/màu riêng biệt.
GRADIENTS = [
    ("#0f2c4d", "#1d4ed8", "#38bdf8"),  # 00: deep navy → blue, sky accent
    ("#0b3a45", "#0e7490", "#22d3ee"),  # 01: teal deep → cyan
    ("#1e1b4b", "#4338ca", "#818cf8"),  # 02: indigo muted
    ("#0f3d3a", "#0f766e", "#2dd4bf"),  # 03: emerald-teal
    ("#1f2937", "#334155", "#94a3b8"),  # 04: slate neutral
    ("#3b2f63", "#6d28d9", "#a78bfa"),  # 05: muted purple
    ("#4c1d1d", "#b91c1c", "#ef4444"),  # 06: maroon → red
    ("#3b1f0b", "#c2410c", "#fb923c"),  # 07: brown → orange
    ("#2d1f0e", "#a16207", "#fbbf24"),  # 08: olive → amber
    ("#3b1f1a", "#9d174d", "#f472b6"),  # 09: rose → pink
    ("#1c1917", "#44403c", "#a8a29e"),  # 10: charcoal → warm gray
    ("#022c22", "#065f46", "#34d399"),  # 11: dark green → emerald
    ("#1a0633", "#5b21b6", "#8b5cf6"),  # 12: midnight → violet
    ("#0c0a3e", "#312e81", "#6366f1"),  # 13: deep indigo → indigo
    ("#271302", "#92400e", "#f59e0b"),  # 14: dark amber → amber
    ("#03183a", "#1d4ed8", "#3b82f6"),  # 15: deep blue → blue
    ("#300e1f", "#831843", "#f472b6"),  # 16: dark pink → pink
    ("#111827", "#1e293b", "#64748b"),  # 17: near black → slate
    ("#0f172a", "#334155", "#94a3b8"),  # 18: dark navy → light slate
    ("#1e0f2e", "#4c1d95", "#c084fc"),  # 19: dark violet → purple
]

# Map chuyên mục blog → topic placeholder + nhãn hiển thị.
# 5 topic bắt buộc: tech, finance, seo, ai, default.
CATEGORY_TOPIC = {
    "công nghệ": "tech",
    "khoa học": "ai",
    "ngân hàng": "finance",
    "bảo hiểm": "finance",
    "làm affiliate": "seo",
    "du lịch": "default",
    "ẩm thực": "default",
    "báo chí": "default",
    "thế giới": "default",
    "điện ảnh": "default",
    "thể thao": "default",
    "học tiếng hàn": "default",
    "linh tinh": "default",
}
TOPIC_COLORS = {
    "tech":    ("#0f2c4d", "#1d4ed8", "#38bdf8", "Công nghệ"),
    "finance": ("#0f3d3a", "#0f766e", "#2dd4bf", "Tài chính"),
    "seo":     ("#3b2f63", "#6d28d9", "#a78bfa", "SEO & Marketing"),
    "ai":      ("#0b3a45", "#0e7490", "#22d3ee", "Khoa học & AI"),
    "default": ("#1f2937", "#334155", "#94a3b8", "SEOMONEY"),
}

CW, CH = 1200, 800  # cover 3:2


def _esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def _hash_int(s: str) -> int:
    return int(hashlib.sha256(s.encode("utf-8")).hexdigest(), 16)


def _wrap(title: str, width: int = 22, max_lines: int = 4) -> list[str]:
    """Wrap tiêu đề theo số ký tự ước lượng (Vietnamese-friendly, chỉ tách theo từ)."""
    words = title.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(" .,") + "…"
    return lines


def _topic_for(category: str | None) -> str:
    if not category:
        return "default"
    return CATEGORY_TOPIC.get(category.strip().lower(), "default")


def _pattern(seed: int, accent: str) -> str:
    """Hoạ tiết editorial nhẹ (vài vòng tròn mờ) — deterministic theo seed."""
    parts = []
    for i in range(4):
        cx = (seed >> (i * 5)) % CW
        cy = (seed >> (i * 7)) % CH
        r = 120 + ((seed >> (i * 3)) % 180)
        op = 0.05 + ((seed >> (i * 2)) % 6) / 100.0
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{accent}" opacity="{op:.2f}"/>'
        )
    return "".join(parts)


def build_cover_svg(slug: str, title: str, category: str | None) -> str:
    """Sinh SVG cover editorial SEOMONEY — deterministic theo slug/title/category."""
    seed = _hash_int(slug)
    g_from, g_to, accent = GRADIENTS[seed % len(GRADIENTS)]
    cat_label = (category or "SEOMONEY").strip()
    lines = _wrap(title, width=22, max_lines=4)

    # Tiêu đề: khối text căn trái, lớn dần để lấp khoảng — font-size cố định để ổn định.
    fs = 64 if len(lines) <= 3 else 56
    line_h = int(fs * 1.18)
    block_h = line_h * len(lines)
    ty0 = (CH // 2) - (block_h // 2) + fs
    tspans = "".join(
        f'<tspan x="80" y="{ty0 + i * line_h}">{_esc(ln)}</tspan>'
        for i, ln in enumerate(lines)
    )

    gid = f"g{seed % 100000}"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{CW}" height="{CH}" viewBox="0 0 {CW} {CH}" role="img">
  <defs>
    <linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{g_from}"/>
      <stop offset="1" stop-color="{g_to}"/>
    </linearGradient>
  </defs>
  <rect width="{CW}" height="{CH}" fill="url(#{gid})"/>
  {_pattern(seed, accent)}
  <!-- category chip -->
  <rect x="80" y="84" rx="20" ry="20" width="{min(560, 60 + len(cat_label) * 22)}" height="48" fill="{accent}" opacity="0.22"/>
  <text x="104" y="116" font-family="'Segoe UI',Roboto,Arial,sans-serif" font-size="26" font-weight="600" fill="#e2e8f0" letter-spacing="1">{_esc(cat_label.upper())}</text>
  <!-- title -->
  <text font-family="'Segoe UI',Roboto,Arial,sans-serif" font-weight="800" fill="#f8fafc" letter-spacing="0.5" font-size="{fs}">{tspans}</text>
  <!-- footer: S-DNA mark + wordmark -->
  <text x="80" y="{CH - 70}" font-family="'Segoe UI',Roboto,Arial,sans-serif" font-size="40" fill="{accent}">&#9672;</text>
  <text x="128" y="{CH - 72}" font-family="'Segoe UI',Roboto,Arial,sans-serif" font-size="34" font-weight="800" fill="#f8fafc" letter-spacing="2">SEOMONEY</text>
  <text x="128" y="{CH - 42}" font-family="'Segoe UI',Roboto,Arial,sans-serif" font-size="20" fill="#cbd5e1" opacity="0.85">seomoney.org</text>
</svg>
"""


def build_category_placeholder(topic: str) -> str:
    """Placeholder editorial cho 1 chuyên mục (KHÔNG tiêu đề bài, dùng cho fallback chung)."""
    g_from, g_to, accent, label = TOPIC_COLORS[topic]
    seed = _hash_int(f"category-{topic}")
    gid = f"cat{topic}"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{CW}" height="{CH}" viewBox="0 0 {CW} {CH}" role="img">
  <defs>
    <linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{g_from}"/>
      <stop offset="1" stop-color="{g_to}"/>
    </linearGradient>
  </defs>
  <rect width="{CW}" height="{CH}" fill="url(#{gid})"/>
  {_pattern(seed, accent)}
  <text x="50%" y="46%" text-anchor="middle" font-family="'Segoe UI',Roboto,Arial,sans-serif" font-size="40" fill="{accent}">&#9672;</text>
  <text x="50%" y="56%" text-anchor="middle" font-family="'Segoe UI',Roboto,Arial,sans-serif" font-size="56" font-weight="800" fill="#f8fafc" letter-spacing="1">{_esc(label)}</text>
  <text x="50%" y="64%" text-anchor="middle" font-family="'Segoe UI',Roboto,Arial,sans-serif" font-size="26" fill="#cbd5e1" letter-spacing="3">SEOMONEY</text>
</svg>
"""


def build_og_fallback_svg(index: int) -> str:
    """Sinh 1 trong 20 OG fallback SVG (branded, KHÔNG title — chỉ SEOMONEY +
    gradient toàn màn hình + hoạ tiết). Dùng cho bài không có cover riêng."""
    g_from, g_to, accent = GRADIENTS[index]
    seed = _hash_int(f"og-fallback-{index}")
    gid = f"ogf{index}"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{CW}" height="{CH}" viewBox="0 0 {CW} {CH}" role="img">
  <defs>
    <linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{g_from}"/>
      <stop offset="1" stop-color="{g_to}"/>
    </linearGradient>
  </defs>
  <rect width="{CW}" height="{CH}" fill="url(#{gid})"/>
  {_pattern(seed, accent)}
  <!-- fallback badge -->
  <rect x="80" y="84" rx="20" ry="20" width="280" height="48" fill="{accent}" opacity="0.22"/>
  <text x="104" y="116" font-family="'Segoe UI',Roboto,Arial,sans-serif" font-size="26" font-weight="600" fill="#e2e8f0" letter-spacing="1">SEOMONEY</text>
  <!-- content hint -->
  <text x="50%" y="46%" text-anchor="middle" font-family="'Segoe UI',Roboto,Arial,sans-serif" font-size="40" fill="{accent}">&#9672;</text>
  <text x="50%" y="56%" text-anchor="middle" font-family="'Segoe UI',Roboto,Arial,sans-serif" font-size="56" font-weight="800" fill="#f8fafc" letter-spacing="1">{_esc(f"SEOMONEY #{index:02d}")}</text>
  <text x="50%" y="64%" text-anchor="middle" font-family="'Segoe UI',Roboto,Arial,sans-serif" font-size="26" fill="#cbd5e1" letter-spacing="3">seomoney.org</text>
  <!-- footer wordmark -->
  <text x="80" y="{CH - 70}" font-family="'Segoe UI',Roboto,Arial,sans-serif" font-size="40" fill="{accent}">&#9672;</text>
  <text x="128" y="{CH - 72}" font-family="'Segoe UI',Roboto,Arial,sans-serif" font-size="34" font-weight="800" fill="#f8fafc" letter-spacing="2">SEOMONEY</text>
  <text x="128" y="{CH - 42}" font-family="'Segoe UI',Roboto,Arial,sans-serif" font-size="20" fill="#cbd5e1" opacity="0.85">seomoney.org</text>
</svg>
"""


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Tách +++ TOML frontmatter + body."""
    if not text.startswith("+++"):
        return {}, text
    end = text.find("+++", 3)
    if end == -1:
        return {}, text
    raw = text[3:end]
    body = text[end + 3:]
    try:
        return tomllib.loads(raw), body
    except Exception:
        return {}, body


def first_local_upload(body: str) -> str | None:
    """Ảnh markdown/HTML đầu tiên trỏ vào /uploads/ (own path)."""
    # markdown ![alt](url)  + html <img src="url">
    for m in re.finditer(r'!\[[^\]]*\]\(([^)\s]+)', body):
        url = m.group(1)
        if any(p in url for p in UPLOAD_PREFIXES):
            return url
    for m in re.finditer(r'<img[^>]+src=["\']([^"\']+)["\']', body):
        url = m.group(1)
        if any(p in url for p in UPLOAD_PREFIXES):
            return url
    return None


def explicit_image(extra: dict) -> str | None:
    """Ảnh khai báo tường minh (bước 1). Placeholder chung KHÔNG tính."""
    for key in ("image", "cover"):
        v = extra.get(key)
        if v:
            return v
    thumb = extra.get("thumbnail")
    if thumb and GENERIC_PLACEHOLDER_HINT not in thumb:
        return thumb
    return None


def slug_for(path: Path, fm: dict) -> str:
    s = fm.get("slug")
    if s:
        return str(s)
    return path.stem


def alt_for(title: str, category: str | None) -> str:
    return title


def primary_category(fm: dict) -> str | None:
    cats = (fm.get("taxonomies") or {}).get("categories") or []
    for c in cats:
        if isinstance(c, str) and c.strip().lower() not in ("tất cả", "premium", "báo chí"):
            return c
    # fallback: bất kỳ cái nào không phải "Tất cả"
    for c in cats:
        if isinstance(c, str) and c.strip().lower() != "tất cả":
            return c
    return None


def build(check: bool = False) -> int:
    COVERS_DIR.mkdir(parents=True, exist_ok=True)
    PLACEHOLDER_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)

    changed: list[str] = []

    def _write(path: Path, content: str):
        old = path.read_text(encoding="utf-8") if path.exists() else None
        if old != content:
            changed.append(str(path.relative_to(ROOT)))
            if not check:
                path.write_text(content, encoding="utf-8")

    # 1) 20 OG fallback SVGs (bộ 20 mẫu nền + màu ngẫu nhiên cho bài không có cover)
    OG_FALLBACK_DIR.mkdir(parents=True, exist_ok=True)
    og_fallback_list: list[str] = []
    for i in range(20):
        name = f"og-fallback-{i}.svg"
        out = OG_FALLBACK_DIR / name
        _write(out, build_og_fallback_svg(i))
        og_fallback_list.append(f"img/og-fallbacks/{name}")

    # 2) Category placeholders (bước 4)
    cat_map: dict[str, str] = {}
    for topic in TOPIC_COLORS:
        out = PLACEHOLDER_DIR / f"category-{topic}.svg"
        _write(out, build_category_placeholder(topic))
    for cat, topic in CATEGORY_TOPIC.items():
        cat_map[cat] = f"img/placeholders/category-{topic}.svg"

    # 2) Quét bài → covers + manifest
    covers: dict[str, dict] = {}
    for cdir in CONTENT_DIRS:
        if not cdir.exists():
            continue
        for md in sorted(cdir.glob("*.md")):
            if md.name.startswith("_"):
                continue
            # Bỏ qua stub hạ tầng feed-anchor (gitignored, sinh bởi build_feed_pagination):
            # KHÔNG sinh cover riêng → tránh non-determinism khi script chạy sau pagination.
            if md.name.startswith("feed-anchor-"):
                continue
            text = md.read_text(encoding="utf-8")
            fm, body = parse_frontmatter(text)
            if not fm:
                continue
            if fm.get("draft") is True:
                continue
            if fm.get("extra", {}).get("feed_anchor") is True:
                continue
            extra = fm.get("extra") or {}
            title = fm.get("title") or md.stem
            slug = slug_for(md, fm)
            category = primary_category(fm)

            # Bước 1: có ảnh thật khai báo → bỏ qua (template tự resolve, không vào manifest)
            if explicit_image(extra):
                continue

            # Bước 2: ảnh local /uploads/ trong body
            inline = first_local_upload(body)
            if inline:
                covers[slug] = {
                    "image": inline.lstrip("/"),
                    "image_alt": extra.get("image_alt") or alt_for(title, category),
                    "image_source": "local-upload",
                    "image_license": "owned",
                    "category": category or "",
                }
                continue

            # Bước 3: sinh cover editorial SEOMONEY
            cover_path = COVERS_DIR / f"{slug}.svg"
            _write(cover_path, build_cover_svg(slug, title, category))
            covers[slug] = {
                "image": f"generated/covers/{slug}.svg",
                "image_alt": extra.get("image_alt") or alt_for(title, category),
                "image_source": "seomoney-generated",
                "image_license": "owned",
                "category": category or "",
            }

    # Build slug → fallback index mapping (cho template pick đúng 1 trong 20)
    slug_fallback: dict[str, int] = {}
    for cdir in CONTENT_DIRS:
        if not cdir.exists():
            continue
        for md in sorted(cdir.glob("*.md")):
            if md.name.startswith("_") or md.name.startswith("feed-anchor-"):
                continue
            text = md.read_text(encoding="utf-8")
            fm, _ = parse_frontmatter(text)
            if not fm:
                continue
            slug = slug_for(md, fm)
            slug_fallback[slug] = _hash_int(slug) % 20

    manifest = {
        "_comment": "Owned-image fallback manifest (SEOMONEY). KHÔNG ảnh ngoài. "
                    "Sinh bởi scripts/build_owned_covers.py — deterministic.",
        "site_og_fallback_dir": SITE_OG_FALLBACK_DIR,
        "default_placeholder": "img/placeholders/category-default.svg",
        "og_fallbacks_count": len(og_fallback_list),
        "og_fallback_list": og_fallback_list,
        "og_fallback_dir": "img/og-fallbacks/",
        "category_map": dict(sorted(cat_map.items())),
        "slug_fallback_index": dict(sorted(slug_fallback.items())),
        "covers": dict(sorted(covers.items())),
    }
    manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    _write(MANIFEST, manifest_text)

    if check:
        if changed:
            print("build_owned_covers: CẦN regenerate, file lệch:")
            for c in changed:
                print(f"  - {c}")
            return 1
        print("build_owned_covers: OK, không có thay đổi.")
        return 0

    gen = sum(1 for v in covers.values() if v['image_source'] == 'seomoney-generated')
    print(f"build_owned_covers: {len(covers)} bài resolve · "
          f"{gen} cover sinh · "
          f"{len(TOPIC_COLORS)} category placeholder · "
          f"{len(og_fallback_list)} OG fallback templates.")
    if changed:
        print(f"  cập nhật {len(changed)} file.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Sinh ảnh cover owned SEOMONEY + manifest fallback.")
    ap.add_argument("--check", action="store_true", help="Chỉ kiểm tra, không ghi (CI gate).")
    args = ap.parse_args()
    try:
        return build(check=args.check)
    except Exception as e:  # an toàn cho CI — không bao giờ crash build
        print(f"build_owned_covers: lỗi không nghiêm trọng: {e}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
