#!/usr/bin/env python3
"""
watermark_blog_images.py — Global blog-image watermark rule (idempotent).

Every eligible raster *content* image on the blog gets a subtle, embedded
ownership watermark before production:

    <16-digit-hash>_seomoney.org        e.g. 4839201746382910_seomoney.org

The 16-digit hash is deterministic from (image repo-path + file bytes), so the
same image always yields the same watermark, and a *changed* image yields a new
one. The watermark is drawn small + low-opacity in a non-destructive bottom
corner so it never ruins thumbnails, layout or readability.

ELIGIBILITY (what counts as a "blog image")
    Roots scanned: static/img/  (+ any extra roots passed on the CLI).
    Extensions:    .jpg .jpeg .png .webp
    SKIPPED (not content images):
      - *.og.webp                      generated OG/social twins (build_og_images.py)
      - static/img/brand|og|placeholder|icons|flags/**   brand / UI / defaults
      - names containing favicon, apple-touch, logo, sprite, -mark,
        placeholder, og-default, author-avatar
      - .svg .gif .ico                 vector / animation / icon (never rasterized)
    => In practice this targets article/content images (static/img/posting/**)
       and standalone post covers (static/img/covers/*.webp, excluding *.og.webp).

IDEMPOTENCY (never stack a second watermark)
    - data/image-watermark-manifest.json maps  repo-path -> {hash16, watermark_text,
      source_sha256, watermarked_sha256, processed_at}.
    - A re-run skips an image whose current bytes already equal the recorded
      `watermarked_sha256` (manifest hit, no Pillow needed).
    - Each watermarked file ALSO carries an EXIF marker `seomoney-wm:<hash16>`
      (UserComment) that travels with the pixels, so a watermarked image is
      recognised even if the manifest is lost — and is never watermarked twice.
    - A genuinely *changed* image (new bytes, no marker, manifest stale) is
      re-watermarked with a fresh hash.

OPTIMIZE-IMAGES INTEGRATION
    to_webp.py converts .jpg/.png -> .webp (and `--replace` deletes the raster);
    it never touches existing .webp. Run this watermarker AFTER to_webp so the
    final production .webp is the thing that gets watermarked exactly once
    (optimize-images.yml does this). Body image references must already point at
    .webp (this script never edits Markdown).

USAGE
    python3 scripts/watermark_blog_images.py --apply     # watermark + update manifest
    python3 scripts/watermark_blog_images.py --check     # CI gate: fail if any eligible
                                                         #   image is un-watermarked / stale
    python3 scripts/watermark_blog_images.py --dry-run   # list what --apply would do
    python3 scripts/watermark_blog_images.py --apply static/img extra/uploads

EXIT CODES
    0  ok (apply done, or check passed, or dry-run)
    1  --check found eligible images missing a watermark / stale manifest
    (any unexpected error degrades safely; --check never crashes CI)

Pillow is required for --apply (drawing). --check works WITHOUT Pillow
(manifest sha256 comparison); it only uses Pillow as a bonus marker fallback.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
MANIFEST_PATH = DATA / "image-watermark-manifest.json"

WM_SUFFIX = "_seomoney.org"
WM_EXIF_PREFIX = "seomoney-wm:"
EXIF_USERCOMMENT_TAG = 0x9286

ELIGIBLE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
DEFAULT_ROOTS = ["static/img"]

# Directory segments (immediately under static/img) that are brand / UI / generated
# and must never receive a content watermark.
SKIP_DIR_SEGMENTS = {"brand", "og", "placeholder", "icons", "flags", "logos"}

# Filename substrings (case-insensitive) that mark brand / UI / default assets.
SKIP_NAME_SUBSTRINGS = (
    "favicon", "apple-touch", "logo", "sprite",
    "placeholder", "og-default", "author-avatar", "-mark",
)


# --------------------------------------------------------------------------- #
# Hashing
# --------------------------------------------------------------------------- #
def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def watermark_hash(rel_path: str, data: bytes) -> str:
    """Deterministic 16-digit numeric hash from (repo-relative path + file bytes).

    Same path+bytes -> same 16 digits; changed bytes -> different digits.
    """
    digest = hashlib.sha256(rel_path.encode("utf-8") + b"\x00" + data).digest()
    num = int.from_bytes(digest[:8], "big") % (10 ** 16)
    return f"{num:016d}"


def watermark_text(rel_path: str, data: bytes) -> str:
    return f"{watermark_hash(rel_path, data)}{WM_SUFFIX}"


# --------------------------------------------------------------------------- #
# Eligibility
# --------------------------------------------------------------------------- #
def is_eligible(path: Path) -> bool:
    """True if `path` is a watermark-eligible blog/content raster image."""
    name = path.name.lower()
    suffix = path.suffix.lower()
    if suffix not in ELIGIBLE_EXT:
        return False
    # Generated OG/social twins — never the human-facing body image.
    if name.endswith(".og.webp"):
        return False
    # Brand / UI / default assets by name.
    if any(sub in name for sub in SKIP_NAME_SUBSTRINGS):
        return False
    # Brand / UI / generated directories under static/img.
    try:
        rel_parts = path.resolve().relative_to(REPO).parts
    except ValueError:
        rel_parts = path.parts
    # rel_parts e.g. ("static", "img", "brand", "x.webp")
    seg_set = {p.lower() for p in rel_parts[:-1]}
    if seg_set & SKIP_DIR_SEGMENTS:
        return False
    return True


def iter_eligible(roots: list[str] | None = None) -> list[Path]:
    """Sorted list of eligible image paths under the given roots."""
    roots = roots or DEFAULT_ROOTS
    out: list[Path] = []
    for r in roots:
        base = (REPO / r) if not Path(r).is_absolute() else Path(r)
        if base.is_file():
            if is_eligible(base):
                out.append(base)
            continue
        if not base.is_dir():
            continue
        for f in base.rglob("*"):
            if f.is_file() and is_eligible(f):
                out.append(f)
    return sorted(set(out))


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO).as_posix()
    except ValueError:
        return path.as_posix()


# --------------------------------------------------------------------------- #
# Manifest
# --------------------------------------------------------------------------- #
def load_manifest() -> dict:
    if MANIFEST_PATH.is_file():
        try:
            data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("images", {})
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"images": {}}


def save_manifest(manifest: dict) -> None:
    DATA.mkdir(exist_ok=True)
    manifest["watermark_suffix"] = WM_SUFFIX
    manifest["count"] = len(manifest.get("images", {}))
    manifest["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    # Stable key order so re-runs produce minimal diffs.
    manifest["images"] = {k: manifest["images"][k] for k in sorted(manifest["images"])}
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


# --------------------------------------------------------------------------- #
# EXIF marker (best-effort; needs Pillow). Travels with the pixels.
# --------------------------------------------------------------------------- #
def read_marker(path: Path) -> str | None:
    """Return the embedded watermark hash if the image carries our marker, else None.

    Never raises (missing Pillow / unreadable EXIF -> None).
    """
    try:
        from PIL import Image
    except Exception:
        return None
    try:
        with Image.open(path) as im:
            # EXIF UserComment (jpg/webp)
            try:
                val = im.getexif().get(EXIF_USERCOMMENT_TAG)
            except Exception:
                val = None
            if isinstance(val, bytes):
                val = val.decode("utf-8", "ignore")
            if isinstance(val, str) and val.startswith(WM_EXIF_PREFIX):
                return val[len(WM_EXIF_PREFIX):].strip("\x00").strip()
            # PNG text chunk fallback
            txt = getattr(im, "text", None) or {}
            pv = txt.get("seomoney-wm") or im.info.get("seomoney-wm")
            if isinstance(pv, str) and pv:
                return pv.strip()
    except Exception:
        return None
    return None


# --------------------------------------------------------------------------- #
# Drawing
# --------------------------------------------------------------------------- #
def _font(size: int):
    from PIL import ImageFont
    for p in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _render_watermark(im, text: str):
    """Return a new RGBA image with a subtle bottom-right watermark drawn on `im`."""
    from PIL import Image, ImageDraw

    base = im.convert("RGBA")
    w, h = base.size
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Scale font to the image; keep it small but readable when zoomed.
    fs = max(11, int(w / 55))
    font = _font(fs)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    # Shrink if it would span more than 60% of the width.
    while tw > w * 0.6 and fs > 9:
        fs -= 1
        font = _font(fs)
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

    pad = max(6, int(w * 0.012))
    x = w - tw - pad
    y = h - th - pad - bbox[1]

    # Subtle: faint dark shadow for contrast + low-opacity white text.
    draw.text((x + 1, y + 1), text, font=font, fill=(0, 0, 0, 70))
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 115))

    return Image.alpha_composite(base, overlay)


def _save_with_marker(out_rgba, path: Path, hash16: str) -> bytes:
    """Save `out_rgba` to `path` in its original format with the EXIF/text marker.

    Returns the bytes written.
    """
    from PIL import Image

    ext = path.suffix.lower()
    marker = f"{WM_EXIF_PREFIX}{hash16}"

    if ext in (".jpg", ".jpeg"):
        exif = Image.Exif()
        exif[EXIF_USERCOMMENT_TAG] = marker
        out_rgba.convert("RGB").save(path, "JPEG", quality=88, exif=exif.tobytes())
    elif ext == ".webp":
        exif = Image.Exif()
        exif[EXIF_USERCOMMENT_TAG] = marker
        out_rgba.convert("RGBA").save(path, "WEBP", quality=90, method=6, exif=exif.tobytes())
    elif ext == ".png":
        from PIL.PngImagePlugin import PngInfo
        meta = PngInfo()
        meta.add_text("seomoney-wm", hash16)
        out_rgba.save(path, "PNG", optimize=True, pnginfo=meta)
    else:  # pragma: no cover - guarded by eligibility
        out_rgba.save(path)
    return path.read_bytes()


def apply_watermark(path: Path, text: str, hash16: str) -> bytes:
    """Draw the watermark onto `path` in place. Returns the new file bytes."""
    from PIL import Image

    with Image.open(path) as im:
        im.load()
        out = _render_watermark(im, text)
    return _save_with_marker(out, path, hash16)


# --------------------------------------------------------------------------- #
# Core: process (apply / dry-run) and check
# --------------------------------------------------------------------------- #
def process(roots: list[str] | None, apply: bool, dry_run: bool) -> dict:
    """Watermark eligible images. Returns a result summary dict."""
    manifest = load_manifest()
    images = manifest["images"]
    res = {"watermarked": [], "skipped": [], "would": [], "errors": []}
    changed = False

    for path in iter_eligible(roots):
        rel = _rel(path)
        try:
            data = path.read_bytes()
        except OSError as e:
            res["errors"].append((rel, str(e)))
            continue
        cur_sha = _sha256(data)
        entry = images.get(rel)

        # Already watermarked? (manifest hit, or embedded marker present)
        manifest_hit = bool(entry) and entry.get("watermarked_sha256") == cur_sha
        marker = read_marker(path)
        if manifest_hit or marker:
            # Backfill manifest if a marker exists but the record is missing/stale.
            if apply and not dry_run and not manifest_hit:
                h16 = marker or (entry or {}).get("hash16") or watermark_hash(rel, data)
                images[rel] = {
                    "hash16": h16,
                    "watermark_text": f"{h16}{WM_SUFFIX}",
                    "source_sha256": (entry or {}).get("source_sha256"),
                    "watermarked_sha256": cur_sha,
                    "processed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
                changed = True
            res["skipped"].append(rel)
            continue

        # Needs a watermark (new image, or genuinely changed content).
        h16 = watermark_hash(rel, data)
        text = f"{h16}{WM_SUFFIX}"
        if dry_run or not apply:
            res["would"].append((rel, text))
            continue
        try:
            new_bytes = apply_watermark(path, text, h16)
        except Exception as e:  # never abort the whole batch on one bad image
            res["errors"].append((rel, str(e)))
            continue
        images[rel] = {
            "hash16": h16,
            "watermark_text": text,
            "source_sha256": cur_sha,
            "watermarked_sha256": _sha256(new_bytes),
            "processed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        res["watermarked"].append(rel)
        changed = True

    # Only rewrite the manifest when something actually changed, so idempotent
    # re-runs (e.g. the daily optimize-images cron) produce no churn / no commit.
    if apply and not dry_run and changed:
        save_manifest(manifest)
    res["changed"] = changed
    res["manifest"] = manifest
    return res


def check_watermarks(roots: list[str] | None = None) -> tuple[bool, list[str], list[str]]:
    """CI gate. Returns (ok, missing, stale).

    Works WITHOUT Pillow: an image passes if the manifest records its current
    bytes as watermarked. Pillow (if present) adds the embedded-marker fallback.
    """
    manifest = load_manifest()
    images = manifest.get("images", {})
    missing: list[str] = []
    stale: list[str] = []
    for path in iter_eligible(roots):
        rel = _rel(path)
        try:
            data = path.read_bytes()
        except OSError:
            continue
        cur = _sha256(data)
        entry = images.get(rel)
        if entry and entry.get("watermarked_sha256") == cur:
            continue
        if read_marker(path):  # marker travels with the pixels
            continue
        (stale if entry else missing).append(rel)
    return (not missing and not stale), missing, stale


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description="Global blog-image watermark rule (idempotent).")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true",
                      help="Watermark eligible images and update the manifest.")
    mode.add_argument("--check", action="store_true",
                      help="CI gate: exit 1 if an eligible image is un-watermarked/stale.")
    mode.add_argument("--dry-run", action="store_true",
                      help="List what --apply would do; change nothing.")
    ap.add_argument("roots", nargs="*", default=None,
                    help="Override scan roots (default: static/img).")
    args = ap.parse_args(argv)
    roots = args.roots or None

    if args.check:
        ok, missing, stale = check_watermarks(roots)
        eligible = len(iter_eligible(roots))
        print(f"Watermark check — {eligible} eligible image(s) · "
              f"{len(missing)} missing · {len(stale)} stale")
        for m in missing:
            print(f"  ✗ MISSING watermark: {m}")
        for s in stale:
            print(f"  ✗ STALE (content changed, re-run --apply): {s}")
        if ok:
            print("✓ All eligible blog images are watermarked.")
            return 0
        print("✗ Run: python3 scripts/watermark_blog_images.py --apply")
        return 1

    # apply / dry-run (default to dry-run if nothing specified)
    dry = args.dry_run or not args.apply
    res = process(roots, apply=args.apply and not args.dry_run, dry_run=dry)
    if dry:
        print(f"DRY-RUN — would watermark {len(res['would'])}, "
              f"skip {len(res['skipped'])} already-watermarked:")
        for rel, text in res["would"]:
            print(f"  + {rel}  ->  {text}")
    else:
        print(f"✓ Watermarked {len(res['watermarked'])}, "
              f"skipped {len(res['skipped'])} already-watermarked, "
              f"{len(res['errors'])} error(s).")
        for rel in res["watermarked"]:
            print(f"  ✎ {rel}")
    for rel, err in res["errors"]:
        print(f"  ! {rel}: {err}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except SystemExit:
        raise
    except Exception as exc:  # never crash CI
        print(f"::warning::watermark_blog_images unexpected error: {exc}", file=sys.stderr)
        sys.exit(0)
