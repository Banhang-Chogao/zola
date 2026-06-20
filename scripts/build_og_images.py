#!/usr/bin/env python3
"""Sinh ảnh social (og:image) dạng .webp từ các cover SVG.

Vì sao cần script này
---------------------
Mạng xã hội (Facebook, Threads, X, Zalo, LinkedIn…) **không render được SVG**
làm og:image. Blog dùng cover SVG tự sinh cho phần lớn bài viết, nên khi share
link, social bỏ qua SVG và rơi về banner chung `img/og-default.webp` — không phản
ánh đúng nội dung bài. (Xem CLAUDE.md — "Quy tắc Ảnh".)

Giải pháp: rasterize mỗi cover `static/img/**/*.svg` thành twin `*.og.webp`
(kích thước chuẩn OG **1200×630**). Template `base.html` sẽ ưu tiên twin này khi
`thumbnail` là `.svg`, nên social hiển thị đúng ảnh cover của từng bài.

Đặc tính
--------
- **Idempotent:** bỏ qua khi `.og.webp` mới hơn `.svg` nguồn (trừ `--force`).
- **Không bao giờ làm vỡ build:** thiếu `cairosvg`/`Pillow` hoặc lỗi render →
  in cảnh báo, `exit 0` (dựa vào file `.og.webp` đã commit sẵn trong repo).
- Chạy trong `deploy.yml` trước `zola build`; cũng có thể chạy tay.

Cách dùng
---------
    python3 scripts/build_og_images.py            # sinh các twin còn thiếu/cũ
    python3 scripts/build_og_images.py --force     # render lại toàn bộ
    python3 scripts/build_og_images.py --check      # CI: báo nếu thiếu twin (exit 2)
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
from pathlib import Path

# Thư mục chứa SVG cần rasterize (cover bài + placeholder thương hiệu).
REPO_ROOT = Path(__file__).resolve().parent.parent
IMG_ROOT = REPO_ROOT / "static" / "img"

# Kích thước chuẩn Open Graph / Twitter summary_large_image.
OG_WIDTH = 1200
OG_HEIGHT = 630
WEBP_QUALITY = 82
OG_SUFFIX = ".og.webp"

# Content-hash manifest: cho phép QA Vaccine Gate phát hiện twin .og.webp "stale"
# (SVG đã đổi nhưng twin chưa render lại) một cách TẤT ĐỊNH — không phụ thuộc
# mtime (không tin cậy trên fresh checkout) hay dep (cairosvg/Pillow). Mỗi entry
# = sha256 của SVG tại thời điểm twin được render/xác nhận khớp.
MANIFEST = IMG_ROOT / "og-manifest.json"


def _svg_sha(svg: Path) -> str:
    return hashlib.sha256(svg.read_bytes()).hexdigest()


def write_manifest(svgs: list[Path]) -> None:
    """Ghi sha256 của mọi SVG hiện có twin → manifest (idempotent).

    Twin vừa render hoặc đã tươi (không stale) ⇒ sha hiện tại của SVG khớp twin.
    Bỏ qua SVG chưa có twin. Ghi idempotent (nội dung không đổi → không ghi) để
    tránh churn/conflict runtime (V18). Lỗi I/O → bỏ qua, không vỡ build.
    """
    entries: dict[str, str] = {}
    for svg in svgs:
        if not target_for(svg).exists():
            continue
        try:
            rel = str(svg.relative_to(REPO_ROOT))
            entries[rel] = _svg_sha(svg)
        except Exception:
            continue
    payload = json.dumps(entries, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    try:
        if MANIFEST.exists() and MANIFEST.read_text(encoding="utf-8") == payload:
            return  # nội dung không đổi → không ghi (idempotent)
        MANIFEST.write_text(payload, encoding="utf-8")
    except OSError:
        pass


def find_svgs() -> list[Path]:
    """Mọi SVG dưới static/img (cover + placeholder)."""
    return sorted(p for p in IMG_ROOT.rglob("*.svg"))


def target_for(svg: Path) -> Path:
    """`x.svg` -> `x.og.webp` (cùng thư mục)."""
    return svg.with_suffix(OG_SUFFIX)


def is_stale(svg: Path, target: Path) -> bool:
    """Cần render lại khi twin chưa có hoặc cũ hơn nguồn."""
    if not target.exists():
        return True
    return svg.stat().st_mtime > target.stat().st_mtime


def render(svg: Path, target: Path) -> bool:
    """Render 1 SVG -> WebP 1200×630. Trả về True nếu ghi file thành công."""
    import cairosvg  # import trễ để có thể skip sạch khi thiếu dep
    from PIL import Image

    png_bytes = cairosvg.svg2png(
        url=str(svg), output_width=OG_WIDTH, output_height=OG_HEIGHT
    )
    im = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    im.save(target, "WEBP", quality=WEBP_QUALITY, method=6)
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true", help="render lại toàn bộ")
    ap.add_argument(
        "--check",
        action="store_true",
        help="chỉ kiểm tra: exit 2 nếu có twin thiếu/cũ (không render)",
    )
    args = ap.parse_args()

    svgs = find_svgs()
    if not svgs:
        print("build_og_images: không tìm thấy SVG nào trong static/img — bỏ qua.")
        return 0

    stale = [s for s in svgs if args.force or is_stale(s, target_for(s))]

    if args.check:
        missing = [s for s in svgs if is_stale(s, target_for(s))]
        if missing:
            print(f"build_og_images --check: {len(missing)} twin .og.webp thiếu/cũ:")
            for s in missing:
                print(f"  - {target_for(s).relative_to(IMG_ROOT.parent.parent)}")
            return 2
        print(f"build_og_images --check: OK — {len(svgs)} cover đều có twin .og.webp.")
        return 0

    if not stale:
        print(f"build_og_images: {len(svgs)} cover đã có twin .og.webp mới nhất — bỏ qua.")
        write_manifest(svgs)
        return 0

    # Import dep ở đây: thiếu thì cảnh báo + exit 0 (KHÔNG vỡ build — dùng file đã commit).
    try:
        import cairosvg  # noqa: F401
        from PIL import Image  # noqa: F401
    except Exception as exc:  # pragma: no cover - phụ thuộc môi trường CI
        print(
            "build_og_images: thiếu cairosvg/Pillow "
            f"({exc!r}) — bỏ qua render, dùng .og.webp đã commit. "
            "Cài: pip install cairosvg pillow"
        )
        return 0

    ok = 0
    failed = 0
    for svg in stale:
        target = target_for(svg)
        try:
            render(svg, target)
            ok += 1
            print(f"  ✓ {target.relative_to(IMG_ROOT.parent.parent)}")
        except Exception as exc:  # 1 file lỗi không được kéo sập cả build
            failed += 1
            print(f"  ✗ {svg.name}: {exc!r}")

    write_manifest(svgs)
    print(
        f"build_og_images: render {ok}/{len(stale)} twin .og.webp"
        + (f" ({failed} lỗi — giữ file cũ nếu có)" if failed else "")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
