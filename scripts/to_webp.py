#!/usr/bin/env python3
"""
to_webp.py — Convert ảnh raster sang .webp (định dạng phát hành duy nhất).

Với mỗi ảnh .jpg/.jpeg/.png, tạo file .webp cùng tên. Dùng --replace để xoá
raster sau convert thành công (workflow optimize-images.yml).

- BỎ QUA .svg (ảnh vector, không nên rasterize) và .gif (giữ animation).
- BỎ QUA nếu .webp đã tồn tại và mới hơn file gốc (idempotent — chạy lại không tốn công).
- Ưu tiên Pillow; nếu không có thì fallback sang cli `cwebp`.

Dùng:
    python3 scripts/to_webp.py                 # quét mặc định static/img
    python3 scripts/to_webp.py static/img a.png # quét path tùy ý
    python3 scripts/to_webp.py --quality 82 static/img

Exit code: 0 luôn (kể cả không có gì để làm) — an toàn cho CI/pipeline bb.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

RASTER_EXT = {".jpg", ".jpeg", ".png"}
DEFAULT_TARGETS = ["static/img"]


def iter_images(targets: list[str]):
    for t in targets:
        p = Path(t)
        if p.is_file():
            if p.suffix.lower() in RASTER_EXT:
                yield p
        elif p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and f.suffix.lower() in RASTER_EXT:
                    yield f


def needs_update(src: Path, dst: Path) -> bool:
    if not dst.exists():
        return True
    # Regenerate nếu ảnh gốc mới hơn bản webp
    return src.stat().st_mtime > dst.stat().st_mtime


def convert_pillow(src: Path, dst: Path, quality: int) -> bool:
    try:
        from PIL import Image  # type: ignore
    except Exception:
        return False
    with Image.open(src) as im:
        # Giữ alpha cho PNG; JPEG -> RGB
        if im.mode in ("P", "LA"):
            im = im.convert("RGBA")
        elif im.mode == "CMYK":
            im = im.convert("RGB")
        im.save(dst, "WEBP", quality=quality, method=6)
    return True


def convert_cwebp(src: Path, dst: Path, quality: int) -> bool:
    exe = _which("cwebp")
    if not exe:
        return False
    res = subprocess.run(
        [exe, "-quiet", "-q", str(quality), str(src), "-o", str(dst)],
        capture_output=True,
    )
    return res.returncode == 0


def _which(name: str) -> str | None:
    from shutil import which

    return which(name)


def main() -> int:
    ap = argparse.ArgumentParser(description="Sinh .webp song song cho ảnh raster.")
    ap.add_argument("targets", nargs="*", default=DEFAULT_TARGETS,
                    help="File hoặc thư mục cần quét (mặc định: static/img)")
    ap.add_argument("--quality", type=int, default=82, help="Chất lượng webp (0-100)")
    ap.add_argument("--force", action="store_true", help="Convert lại kể cả khi đã có webp mới")
    ap.add_argument("--replace", action="store_true",
                    help="Xoá file raster gốc sau khi convert .webp thành công")
    args = ap.parse_args()

    targets = args.targets or DEFAULT_TARGETS
    images = list(iter_images(targets))
    if not images:
        print("to_webp: không tìm thấy ảnh raster nào để convert.")
        return 0

    have_pillow = False
    try:
        import PIL  # noqa: F401
        have_pillow = True
    except Exception:
        have_pillow = bool(_which("cwebp"))
    if not have_pillow and not _which("cwebp"):
        print("to_webp: THIẾU công cụ convert (cần Pillow hoặc cwebp). Bỏ qua, exit 0.")
        return 0

    converted = skipped = failed = 0
    for src in images:
        dst = src.with_suffix(".webp")
        if not args.force and not needs_update(src, dst):
            skipped += 1
            continue
        ok = convert_pillow(src, dst, args.quality) or convert_cwebp(src, dst, args.quality)
        if ok:
            converted += 1
            print(f"  ✓ {src} -> {dst.name}")
            if args.replace and src.exists():
                src.unlink()
                print(f"    − removed {src.name}")
        else:
            failed += 1
            print(f"  ✗ FAILED {src}")

    print(f"to_webp: {converted} convert, {skipped} bỏ qua (đã mới), {failed} lỗi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
