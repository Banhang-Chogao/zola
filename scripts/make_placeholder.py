#!/usr/bin/env python3
"""
make_placeholder.py — Sinh ảnh PLACEHOLDER cố định (brand gradient, KHÔNG chữ).

Mục đích: blog là Zola static, nhiều bài chưa có ảnh minh hoạ phù hợp. Thay vì
dùng ảnh random ngoài (picsum — nội dung không liên quan) hay nhúng chữ cứng lên
ảnh, ta dùng MỘT bộ ảnh placeholder thương hiệu (gradient xanh #38bdf8 → #1d4ed8,
vài hình tròn trang trí + 1 icon ảnh mờ ở giữa). Bài nào KHÔNG có thumbnail thì
template tự chèn placeholder này, alt text lấy từ tiêu đề/nội dung bài lúc đó.

Đặc điểm:
- KHÔNG có chữ baked cứng (khác các SVG cover cũ) → tái dùng cho mọi bài.
- SVG vector → 1 file scale mọi kích thước (img dùng object-fit: cover). Vẫn xuất
  ĐA DẠNG TỈ LỆ để bố cục hình tròn cân đối ở từng ngữ cảnh:
    * placeholder.svg        1200×800  (3:2)  — thumbnail mặc định / list / hero
    * placeholder-wide.svg   1600×900  (16:9) — ảnh trong nội dung bài, banner rộng
    * placeholder-square.svg  800×800  (1:1)  — avatar/khối vuông
- Không cần thư viện ngoài (chỉ stdlib). Chạy lại idempotent (ghi đè cùng nội dung).

Dùng:
    python3 scripts/make_placeholder.py            # sinh vào static/img/placeholder/
    python3 scripts/make_placeholder.py <out_dir>  # thư mục tuỳ ý

Exit code 0 luôn (an toàn cho CI / shortcut bb).
"""
from __future__ import annotations

import sys
from pathlib import Path

# Palette bám đúng các SVG cover hiện có để đồng bộ thương hiệu.
GRAD_FROM = "#38bdf8"   # sky-400
GRAD_TO = "#1d4ed8"     # blue-700
CIRCLE_SOFT = "#93c5fd"  # blue-300 (đốm sáng mờ)

DEFAULT_OUT = "static/img/placeholder"

# (tên file, width, height) — các tỉ lệ phục vụ thumbnail / content / square.
SIZES = [
    ("placeholder.svg", 1200, 800),
    ("placeholder-wide.svg", 1600, 900),
    ("placeholder-square.svg", 800, 800),
]


def _photo_icon(w: int, h: int) -> str:
    """Icon 'ảnh' tối giản, trắng mờ, canh giữa — báo hiệu đây là ô ảnh."""
    # Khung icon ~22% chiều rộng, đặt giữa khung.
    iw = round(w * 0.22)
    ih = round(iw * 0.72)
    x = (w - iw) // 2
    y = (h - ih) // 2
    r = max(6, round(iw * 0.05))
    # Toạ độ "núi" + "mặt trời" bên trong khung ảnh, theo tỉ lệ khung icon.
    sun_cx = x + round(iw * 0.30)
    sun_cy = y + round(ih * 0.32)
    sun_r = round(iw * 0.08)
    # Tam giác núi.
    m1 = f"{x + round(iw*0.12)},{y + ih - round(ih*0.12)}"
    m2 = f"{x + round(iw*0.45)},{y + round(ih*0.42)}"
    m3 = f"{x + round(iw*0.70)},{y + ih - round(ih*0.12)}"
    m4 = f"{x + round(iw*0.58)},{y + round(ih*0.55)}"
    m5 = f"{x + round(iw*0.88)},{y + ih - round(ih*0.12)}"
    return (
        f'  <g fill="none" stroke="#ffffff" stroke-width="{max(3, round(iw*0.025))}" '
        f'opacity="0.28" stroke-linejoin="round">\n'
        f'    <rect x="{x}" y="{y}" width="{iw}" height="{ih}" rx="{r}" ry="{r}"/>\n'
        f'  </g>\n'
        f'  <g opacity="0.28">\n'
        f'    <circle cx="{sun_cx}" cy="{sun_cy}" r="{sun_r}" fill="#ffffff"/>\n'
        f'    <polyline points="{m1} {m2} {m3} {m4} {m5}" fill="none" '
        f'stroke="#ffffff" stroke-width="{max(3, round(iw*0.025))}" '
        f'stroke-linejoin="round" stroke-linecap="round"/>\n'
        f'  </g>\n'
    )


def build_svg(w: int, h: int) -> str:
    """Dựng SVG gradient + hình tròn trang trí + icon ảnh. KHÔNG có text."""
    # Hình tròn trang trí canh theo góc phải (giống cover cũ), scale theo khung.
    c1_cx, c1_cy, c1_r = round(w * 0.83), round(h * 0.17), round(h * 0.48)
    c2_cx, c2_cy, c2_r = round(w * 0.94), round(h * 0.86), round(h * 0.31)
    c3_cx, c3_cy, c3_r = round(w * 0.10), round(h * 0.92), round(h * 0.22)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}" role="img" '
        f'aria-label="Ảnh minh hoạ mặc định của blog">\n'
        f'  <defs>\n'
        f'    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">\n'
        f'      <stop offset="0" stop-color="{GRAD_FROM}"/>\n'
        f'      <stop offset="1" stop-color="{GRAD_TO}"/>\n'
        f'    </linearGradient>\n'
        f'  </defs>\n'
        f'  <rect width="{w}" height="{h}" fill="url(#g)"/>\n'
        f'  <circle cx="{c1_cx}" cy="{c1_cy}" r="{c1_r}" fill="{CIRCLE_SOFT}" opacity="0.13"/>\n'
        f'  <circle cx="{c2_cx}" cy="{c2_cy}" r="{c2_r}" fill="#ffffff" opacity="0.06"/>\n'
        f'  <circle cx="{c3_cx}" cy="{c3_cy}" r="{c3_r}" fill="#ffffff" opacity="0.05"/>\n'
        f'{_photo_icon(w, h)}'
        f'</svg>\n'
    )


def main(argv: list[str]) -> int:
    out_dir = Path(argv[1]) if len(argv) > 1 else Path(DEFAULT_OUT)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, w, h in SIZES:
        path = out_dir / name
        path.write_text(build_svg(w, h), encoding="utf-8")
        print(f"✓ {path}  ({w}×{h})")
    print(f"\n💡 Dùng làm thumbnail mặc định: /img/placeholder/placeholder.svg")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
