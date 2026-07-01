from __future__ import annotations

import html
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from fastapi import APIRouter, Depends, Header, HTTPException, Cookie
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from cms_auth import BACKEND_URL, SESSION_COOKIE_NAME, cms_profile_from_session, is_admin
from db import VipzoneDB

router = APIRouter(prefix="/api/infographic-hoa", tags=["infographic-hoa"])

ROOT = Path(__file__).resolve().parents[2]
IMAGES_ROOT = Path(
    os.getenv("INFOGRAPHIC_MEDIA_PATH", "/var/data/infographic-hoa" if os.getenv("RENDER") else ROOT / "data" / "infographic-hoa")
)
CMS_V5_MEDIA_ROOT = Path(
    os.getenv("CMS_V5_MEDIA_PATH", "/var/data/cms-v5-media" if os.getenv("RENDER") else ROOT / "data" / "cms-v5-media")
)
BLOG_URL = os.getenv("VIPZONE_BLOG_URL", "https://seomoney.org").rstrip("/")

_get_db: Callable[[], VipzoneDB] | None = None


def configure(get_db: Callable[[], VipzoneDB]) -> None:
    global _get_db
    _get_db = get_db
    IMAGES_ROOT.mkdir(parents=True, exist_ok=True)


def db() -> VipzoneDB:
    assert _get_db is not None
    return _get_db()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def require_admin(
    authorization: str = Header(default=""),
    cookie_sid: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> dict[str, Any]:
    profile = await cms_profile_from_session(db(), authorization, cookie_sid=cookie_sid)
    if not (is_admin(profile.get("email"), profile.get("username")) or profile.get("is_super")):
        raise HTTPException(403, "admin_required")
    return profile


# ---- S-DNA Branding Palette ----
TEAL = "#00A7A0"
TEAL_SOFT = "#DDF4F2"
BLUE = "#5B9BD5"
BLUE_SOFT = "#DCEAF8"
PURPLE = "#9B8FD4"
PURPLE_SOFT = "#ECE7FA"
AMBER = "#E8A838"
AMBER_SOFT = "#FDF3E0"
GREEN = "#3FA66A"
GREEN_SOFT = "#E0F2E8"
WHITE = "#FFFFFF"
HEADING = "#111111"
BODY = "#555555"
MUTED = "#888888"
BORDER = "#E6E6E6"

FONT_FALLBACK = "system-ui, -apple-system, 'Segoe UI', sans-serif"
FONT_HEADING = f"'IBM Plex Sans', {FONT_FALLBACK}"
FONT_BODY = f"'Inter', {FONT_FALLBACK}"

PALETTES = [
    {"fill": TEAL_SOFT, "accent": TEAL, "label": "Năng lượng", "icon": "⚡"},
    {"fill": BLUE_SOFT, "accent": BLUE, "label": "Đô thị", "icon": "◇"},
    {"fill": PURPLE_SOFT, "accent": PURPLE, "label": "Nước", "icon": "○"},
    {"fill": GREEN_SOFT, "accent": GREEN, "label": "Tăng trưởng", "icon": "△"},
    {"fill": AMBER_SOFT, "accent": AMBER, "label": "Tiềm năng", "icon": "☀"},
]

W = 800
H = 600


class GenerateRequest(BaseModel):
    title: str = Field(default="", max_length=300)
    description: str = Field(default="", max_length=2000)
    content: str = Field(default="", max_length=20000)


class GenerateResponse(BaseModel):
    ok: bool
    images: list[dict[str, Any]]


def _esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def _wrap(text: str, width: int = 28, max_lines: int = 5) -> list[str]:
    words = text.split()
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
        lines[-1] = lines[-1].rstrip(".,;!?") + "…"
    return lines


def _extract_themes(content: str) -> list[str]:
    keywords = re.findall(r'#(\w+)', content)
    if not keywords:
        h2s = re.findall(r'^##\s+(.+)$', content, re.MULTILINE)
        keywords = [h.strip() for h in h2s[:5]]
    if not keywords:
        sentences = re.split(r'[.!?\n]', content)
        keywords = [s.strip() for s in sentences if len(s.strip()) > 20][:5]
    return keywords or ["Nội dung chính"]


def _build_cover_svg(title: str, palette: dict) -> str:
    lines = _wrap(title, width=20, max_lines=6)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
<stop offset="0%" stop-color="{palette['fill']}"/>
<stop offset="100%" stop-color="{WHITE}"/>
</linearGradient>
</defs>
<rect width="{W}" height="{H}" fill="url(#bg)" rx="4"/>
<rect x="0" y="0" width="8" height="{H}" fill="{palette['accent']}"/>
<rect x="{W-8}" y="0" width="8" height="{H}" fill="{palette['accent']}" opacity="0.3"/>
<circle cx="60" cy="60" r="28" fill="none" stroke="{palette['accent']}" stroke-width="2"/>
<text x="60" y="66" text-anchor="middle" font-size="20">{palette['icon']}</text>
<text x="100" y="55" font-family="{FONT_HEADING}" font-size="13" font-weight="700" fill="{MUTED}" letter-spacing="2" text-transform="uppercase">{_esc(palette['label'])}</text>
<text x="100" y="72" font-family="{FONT_HEADING}" font-size="10" font-weight="400" fill="{BODY}">INFographic hoá · SEOMONEY</text>
<line x1="60" y1="90" x2="{W-60}" y2="90" stroke="{BORDER}" stroke-width="1"/>
{f'<text x="60" y="140" font-family="{FONT_HEADING}" font-size="28" font-weight="800" fill="{HEADING}">{"".join(f"<tspan x=\"60\" dy=\"38\">{_esc(l)}</tspan>" for l in lines[:3])}</text>' if len(lines)<=3 else ''.join(f'<text x="60" y="{140+i*34}" font-family="{FONT_HEADING}" font-size="24" font-weight="800" fill="{HEADING}">{_esc(l)}</text>' for i,l in enumerate(lines[:4]))}
<rect x="60" y="{H-80}" width="180" height="36" rx="4" fill="{palette['accent']}" opacity="0.12"/>
<text x="66" y="{H-57}" font-family="{FONT_BODY}" font-size="12" font-weight="600" fill="{palette['accent']}">seomoney.org</text>
<text x="{W-60}" y="{H-57}" text-anchor="end" font-family="{FONT_BODY}" font-size="11" fill="{MUTED}">S-DNA ◈ Branded</text>
</svg>"""


def _build_quote_svg(quote: str, palette: dict) -> str:
    lines = _wrap(quote, width=25, max_lines=6)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<rect width="{W}" height="{H}" fill="{WHITE}" rx="4"/>
<rect x="0" y="0" width="8" height="{H}" fill="{palette['accent']}"/>
<circle cx="60" cy="60" r="28" fill="{palette['fill']}" stroke="{palette['accent']}" stroke-width="1.5"/>
<text x="60" y="66" text-anchor="middle" font-size="24" font-weight="bold" fill="{palette['accent']}">"</text>
<text x="100" y="55" font-family="{FONT_HEADING}" font-size="13" font-weight="700" fill="{MUTED}" letter-spacing="2">TRÍCH DẪN NỔI BẬT</text>
<text x="100" y="72" font-family="{FONT_HEADING}" font-size="10" fill="{BODY}">Từ nội dung phân tích</text>
<line x1="60" y1="90" x2="{W-60}" y2="90" stroke="{BORDER}" stroke-width="1"/>
<text x="60" y="150" font-family="{FONT_HEADING}" font-size="22" font-weight="700" fill="{HEADING}" font-style="italic">“</text>
{f''.join(f'<text x="80" y="{150+i*36}" font-family="{FONT_BODY}" font-size="18" font-weight="500" fill="{BODY}">{_esc(l)}</text>' for i,l in enumerate(lines[:4]))}
<text x="{80+len(lines[-1])*9 if lines else 80}" y="{150+min(len(lines),4)*36}" font-family="{FONT_HEADING}" font-size="22" font-weight="700" fill="{HEADING}" font-style="italic">”</text>
<rect x="60" y="{H-80}" width="160" height="36" rx="4" fill="{palette['accent']}" opacity="0.12"/>
<text x="66" y="{H-57}" font-family="{FONT_BODY}" font-size="12" font-weight="600" fill="{palette['accent']}">seomoney.org</text>
</svg>"""


def _build_insight_svg(themes: list[str], palette: dict) -> str:
    items = themes[:4] if themes else ["Nội dung chính"]
    item_svgs = ""
    for i, theme in enumerate(items):
        item_svgs += f"""
<rect x="60" y="{200+i*70}" width="{W-120}" height="60" rx="10" fill="{palette['fill']}" stroke="{BORDER}" stroke-width="1"/>
<rect x="60" y="{200+i*70}" width="4" height="60" fill="{palette['accent']}" rx="2"/>
<circle cx="85" cy="{230+i*70}" r="14" fill="none" stroke="{palette['accent']}" stroke-width="1.5"/>
<text x="85" y="235" text-anchor="middle" font-size="12">{palette['icon']}</text>
<text x="110" y="{227+i*70}" font-family="{FONT_HEADING}" font-size="14" font-weight="700" fill="{HEADING}">{_esc(_wrap(theme, width=35, max_lines=2)[0])}</text>
"""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<rect width="{W}" height="{H}" fill="{WHITE}" rx="4"/>
<rect x="0" y="0" width="8" height="{H}" fill="{palette['accent']}"/>
<circle cx="60" cy="60" r="28" fill="none" stroke="{palette['accent']}" stroke-width="2"/>
<text x="60" y="66" text-anchor="middle" font-size="20">{palette['icon']}</text>
<text x="100" y="55" font-family="{FONT_HEADING}" font-size="13" font-weight="700" fill="{MUTED}" letter-spacing="2">PHÂN TÍCH NỘI DUNG</text>
<text x="100" y="72" font-family="{FONT_HEADING}" font-size="10" fill="{BODY}">Chủ đề chính · {len(items)} điểm</text>
<line x1="60" y1="90" x2="{W-60}" y2="90" stroke="{BORDER}" stroke-width="1"/>
<rect x="60" y="120" width="80" height="26" rx="4" fill="{palette['accent']}"/>
<text x="68" y="137" font-family="{FONT_HEADING}" font-size="11" font-weight="700" fill="{WHITE}">CHỦ ĐỀ</text>
{item_svgs}
<rect x="60" y="{H-70}" width="180" height="36" rx="4" fill="{palette['accent']}" opacity="0.12"/>
<text x="66" y="{H-47}" font-family="{FONT_BODY}" font-size="12" font-weight="600" fill="{palette['accent']}">seomoney.org · INFographic hoá</text>
</svg>"""


def _build_summary_svg(title: str, palette: dict) -> str:
    lines = _wrap(title, width=22, max_lines=4)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs>
<linearGradient id="sum-bg" x1="0" y1="0" x2="0" y2="1">
<stop offset="0%" stop-color="{palette['fill']}"/>
<stop offset="100%" stop-color="{WHITE}"/>
</linearGradient>
</defs>
<rect width="{W}" height="{H}" fill="url(#sum-bg)" rx="4"/>
<rect x="0" y="0" width="8" height="{H}" fill="{palette['accent']}"/>
<circle cx="{W//2}" cy="80" r="40" fill="{palette['fill']}" stroke="{palette['accent']}" stroke-width="2"/>
<text x="{W//2}" y="88" text-anchor="middle" font-size="32">{palette['icon']}</text>
<text x="{W//2}" y="145" text-anchor="middle" font-family="{FONT_HEADING}" font-size="14" font-weight="700" fill="{MUTED}" letter-spacing="3">TỔNG KẾT</text>
{f'<text x="{W//2}" y="200" text-anchor="middle" font-family="{FONT_HEADING}" font-size="26" font-weight="800" fill="{HEADING}">{"".join(f"<tspan x=\"{W//2}\" dy=\"36\">{_esc(l)}</tspan>" for l in lines[:3])}</text>' if len(lines)<=3 else ''.join(f'<text x="{W//2}" y="{200+i*32}" text-anchor="middle" font-family="{FONT_HEADING}" font-size="22" font-weight="800" fill="{HEADING}">{_esc(l)}</text>' for i,l in enumerate(lines[:4]))}
<rect x="{W//2-100}" y="{H-80}" width="200" height="40" rx="4" fill="{palette['accent']}"/>
<text x="{W//2}" y="{H-54}" text-anchor="middle" font-family="{FONT_BODY}" font-size="13" font-weight="700" fill="{WHITE}">seomoney.org</text>
<text x="{W//2}" y="{H-20}" text-anchor="middle" font-family="{FONT_BODY}" font-size="10" fill="{MUTED}">Branded by S-DNA ◈</text>
</svg>"""


def _build_banner_svg(title: str, palette: dict) -> str:
    lines = _wrap(title, width=30, max_lines=2)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H//3}" viewBox="0 0 {W} {H//3}">
<rect width="{W}" height="{H//3}" fill="{palette['fill']}" rx="4"/>
<rect x="0" y="0" width="6" height="{H//3}" fill="{palette['accent']}"/>
<circle cx="32" cy="{H//6}" r="16" fill="none" stroke="{palette['accent']}" stroke-width="1.5"/>
<text x="32" y="{H//6+6}" text-anchor="middle" font-size="14">{palette['icon']}</text>
<text x="60" y="{H//6+5}" font-family="{FONT_HEADING}" font-size="14" font-weight="700" fill="{HEADING}">{_esc(lines[0]) if lines else ''}</text>
{f'<text x="60" y="{H//6+28}" font-family="{FONT_BODY}" font-size="11" fill="{MUTED}">{_esc(lines[1])}</text>' if len(lines) > 1 else ''}
<text x="{W-20}" y="{H//6+5}" text-anchor="end" font-family="{FONT_BODY}" font-size="9" fill="{MUTED}">seomoney.org</text>
</svg>"""


TEMPLATES = [
    ("cover", _build_cover_svg),
    ("quote", _build_quote_svg),
    ("insight", _build_insight_svg),
    ("summary", _build_summary_svg),
    ("banner", _build_banner_svg),
]


def _generate_images(title: str, description: str, content: str) -> list[dict[str, Any]]:
    themes = _extract_themes(content or description or title)
    images: list[dict[str, Any]] = []

    for i, (tpl_name, tpl_fn) in enumerate(TEMPLATES):
        palette = PALETTES[i % len(PALETTES)]

        if tpl_name == "cover":
            svg = tpl_fn(title or "Nội dung chưa có tiêu đề", palette)
            alt = f"{title} - Anh bia infographic" if title else "Anh bia infographic"
        elif tpl_name == "quote":
            quote = description or content[:200] or title
            svg = tpl_fn(quote, palette)
            alt = f"{title} - Trich dan noi bat" if title else "Trich dan noi bat"
        elif tpl_name == "insight":
            svg = tpl_fn(themes, palette)
            alt = f"{title} - Phan tich chu de" if title else "Phan tich noi dung"
        elif tpl_name == "summary":
            svg = tpl_fn(title or "Tong ket", palette)
            alt = f"{title} - Tong ket infographic" if title else "Tong ket infographic"
        else:
            svg = tpl_fn(title or "Banner", palette)
            alt = f"{title} - Banner infographic" if title else "Banner infographic"

        image_id = f"infographic_{uuid.uuid4().hex[:16]}"
        stored_name = f"{image_id}.svg"
        webp_name = f"{image_id}.webp"

        path = IMAGES_ROOT / stored_name
        path.write_text(svg, encoding="utf-8")

        webp_path = IMAGES_ROOT / webp_name
        _rasterize_svg_to_webp(svg, webp_path)

        alt_text = alt.lower().replace(" ", "-").replace("--", "-").strip("-")
        alt_text = re.sub(r"[^a-z0-9-]", "", alt_text)[:80]

        images.append({
            "id": image_id,
            "alt_text": alt,
            "alt_slug": alt_text,
            "type": tpl_name,
            "svg_url": f"{BLOG_URL}/api/infographic-hoa/images/{image_id}/file",
            "webp_url": f"{BLOG_URL}/api/infographic-hoa/images/{image_id}/webp",
            "palette": palette["label"],
            "created_at": now_iso(),
        })

    return images


def _rasterize_svg_to_webp(svg: str, webp_path: Path) -> None:
    try:
        import io
        import cairosvg
        from PIL import Image

        png_bytes = cairosvg.svg2png(bytestring=svg.encode("utf-8"), output_width=W, output_height=H)
        img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
        img.save(webp_path, "WEBP", quality=85)
    except Exception:
        if webp_path.exists():
            webp_path.unlink(missing_ok=True)


def _register_in_cms5_media(image: dict[str, Any], profile_name: str) -> str | None:
    webp_path = IMAGES_ROOT / f"{image['id']}.webp"
    if not webp_path.exists():
        return None

    media_id = f"media_{uuid.uuid4().hex[:16]}"
    stored_name = f"{media_id}.webp"
    dest = CMS_V5_MEDIA_ROOT / stored_name

    try:
        CMS_V5_MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy2(webp_path, dest)

        size = webp_path.stat().st_size
        with db()._conn() as conn:
            conn.execute(
                """INSERT INTO cms_v5_media
                   (id, filename, stored_name, content_type, media_type, size_bytes,
                    alt_text, storage_path, uploaded_by, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    media_id,
                    f"{image['alt_slug']}.webp",
                    stored_name,
                    "image/webp",
                    "image",
                    size,
                    image["alt_text"],
                    str(dest),
                    profile_name,
                    now_iso(),
                ),
            )
        return media_id
    except Exception:
        return None


# ---- API Endpoints ----


@router.post("/generate")
async def generate_images(
    req: GenerateRequest,
    profile: dict = Depends(require_admin),
):
    if not req.title and not req.description and not req.content:
        raise HTTPException(400, "require at least one of title / description / content")

    images = _generate_images(req.title, req.description, req.content)
    profile_name = profile.get("username") or profile.get("email", "unknown")

    for img in images:
        cms_media_id = _register_in_cms5_media(img, profile_name)
        img["cms_media_id"] = cms_media_id

    with db()._conn() as conn:
        now = now_iso()
        gen_id = f"gen_{uuid.uuid4().hex[:12]}"
        conn.execute(
            """INSERT INTO infographic_generations
               (id, title, image_count, created_by, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (gen_id, req.title[:200], len(images), profile_name, now),
        )
        for img in images:
            conn.execute(
                """INSERT INTO infographic_images
                   (id, generation_id, image_type, alt_text, alt_slug,
                    palette_label, cms_media_id, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    img["id"], gen_id, img["type"],
                    img["alt_text"], img["alt_slug"],
                    img["palette"], img["cms_media_id"], now,
                ),
            )

    return GenerateResponse(ok=True, images=images)


@router.get("/images")
async def list_images():
    with db()._conn() as conn:
        rows = conn.execute(
            """SELECT g.id as gen_id, g.title, g.created_at as gen_created_at,
                      i.id, i.image_type, i.alt_text, i.alt_slug, i.palette_label,
                      i.cms_media_id, i.created_at
               FROM infographic_generations g
               JOIN infographic_images i ON i.generation_id = g.id
               ORDER BY g.created_at DESC, i.created_at ASC
               LIMIT 200"""
        ).fetchall()

    grouped: list[dict[str, Any]] = []
    current_gen: dict[str, Any] | None = None

    for row in rows:
        gen_key = row["gen_id"]
        if not current_gen or current_gen["id"] != gen_key:
            current_gen = {
                "id": gen_key,
                "title": row["title"],
                "created_at": row["gen_created_at"],
                "images": [],
            }
            grouped.append(current_gen)

        webp_url = f"{BLOG_URL}/api/infographic-hoa/images/{row['id']}/webp"
        svg_url = f"{BLOG_URL}/api/infographic-hoa/images/{row['id']}/file"
        cms_url = f"{BACKEND_URL}/api/cms-v5/media/{row['cms_media_id']}/file" if row["cms_media_id"] else None

        current_gen["images"].append({
            "id": row["id"],
            "type": row["image_type"],
            "alt_text": row["alt_text"],
            "alt_slug": row["alt_slug"],
            "palette": row["palette_label"],
            "cms_media_id": row["cms_media_id"],
            "webp_url": webp_url,
            "svg_url": svg_url,
            "cms_url": cms_url,
            "created_at": row["created_at"],
        })

    return {"ok": True, "generations": grouped, "total": sum(len(g["images"]) for g in grouped)}


@router.get("/images/{image_id}/file")
async def image_file(image_id: str):
    path = IMAGES_ROOT / f"{image_id}.svg"
    if not path.is_file():
        raise HTTPException(404, "image_not_found")
    return FileResponse(
        path,
        media_type="image/svg+xml",
        filename=f"{image_id}.svg",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get("/images/{image_id}/webp")
async def image_webp(image_id: str):
    webp_path = IMAGES_ROOT / f"{image_id}.webp"
    if webp_path.is_file():
        return FileResponse(
            webp_path,
            media_type="image/webp",
            filename=f"{image_id}.webp",
            headers={"Cache-Control": "public, max-age=86400"},
        )
    svg_path = IMAGES_ROOT / f"{image_id}.svg"
    if svg_path.is_file():
        return FileResponse(
            svg_path,
            media_type="image/svg+xml",
            filename=f"{image_id}.svg",
            headers={"Cache-Control": "public, max-age=86400"},
        )
    raise HTTPException(404, "image_not_found")
