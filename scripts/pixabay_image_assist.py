#!/usr/bin/env python3
"""
pixabay_image_assist.py — No-API, source-safe Pixabay image-assist cho luồng tạo bài.

Mục tiêu
--------
Gợi ý 3–5 ứng viên ảnh cover/OG từ Pixabay **mà KHÔNG dùng API/API key**, an toàn
pháp lý + an toàn AdSense, và **không bao giờ tự đăng**. Quy trình:

    suggest  →  (người duyệt thủ công)  →  confirm + download  →  metadata bắt buộc

Nguyên tắc bất biến (xem docs/pixabay-image-assist.md)
-----------------------------------------------------
- Chỉ **gợi ý** 3–5 ứng viên landscape; KHÔNG tải/dùng khi chưa được xác nhận thủ công.
- Bị chặn / không có ứng viên / chưa xác nhận → giữ nguyên OG fallback/placeholder hiện
  có; việc tạo bài **không được fail**.
- Tôn trọng robots.txt, rate-limit, chỉ trang public; KHÔNG login/CAPTCHA/endpoint riêng
  tư/mass-scrape. Bị disallow → dừng êm (graceful), trả "blocked", không raise.
- Ảnh Pixabay (bên thứ ba) lưu vào thư mục **third-party** `static/img/third-party/pixabay/`
  — KHÔNG nằm trong owned-roots nên **không bị đóng watermark** (xem watermark_blog_images.py).
- Mỗi ảnh dùng phải có **metadata nguồn/giấy phép** (sidecar + frontmatter). KHÔNG ảnh
  nào được dùng nếu thiếu metadata bắt buộc.

Stdlib-only cho phần khám phá/parse/metadata. Pillow (tuỳ chọn) chỉ dùng khi convert .webp.

CLI
---
    # 1) Gợi ý ứng viên (ghi data/pixabay-suggestions/<slug>.json — volatile, gitignored)
    python3 scripts/pixabay_image_assist.py suggest --slug my-post \\
        --title "Tiêu đề bài" --keyword "seo onpage" --category "Công nghệ" --tags "seo,onpage"

    # 2) Sau khi NGƯỜI duyệt 1 ứng viên: tải về (bắt buộc --yes + --commercial-ok)
    python3 scripts/pixabay_image_assist.py confirm --slug my-post --index 0 \\
        --yes --commercial-ok --article content/posting/my-post.md

    # 3) Xem trạng thái gợi ý
    python3 scripts/pixabay_image_assist.py status --slug my-post

Exit code: 0 ở mọi đường "an toàn" (gợi ý/blocked/no-candidate). confirm thiếu xác nhận
hoặc thiếu metadata → exit 2 (từ chối, không tải).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.robotparser import RobotFileParser

REPO = Path(__file__).resolve().parent.parent
THIRD_PARTY_ROOT = REPO / "static" / "img" / "third-party" / "pixabay"
SUGGEST_DIR = REPO / "data" / "pixabay-suggestions"

PIXABAY_HOST = "https://pixabay.com"
USER_AGENT = "SEOMONEY-image-assist/1.0 (+https://seomoney.org; respectful, no-API)"
FETCH_TIMEOUT = 8  # giây — môi trường chặn egress sẽ fail nhanh → degrade "blocked"
RATE_LIMIT_SECONDS = 1.5  # nghỉ giữa 2 request public → không burst, tôn trọng máy chủ
MAX_QUERIES = 4
DEFAULT_LIMIT = 5
MIN_CANDIDATES = 3

LICENSE_NOTE = (
    "Pixabay Content License — free for commercial use, no attribution required; "
    "verify per-image terms at https://pixabay.com/service/license-summary/"
)

# Trường metadata BẮT BUỘC trước khi 1 ảnh được dùng (sidecar + frontmatter).
MANDATORY_META_FIELDS = (
    "image_source",
    "image_author",
    "image_url",
    "image_license_note",
    "image_downloaded_at",
    "image_verified_manually",
    "image_commercial_use_checked",
)

# --------------------------------------------------------------------------- #
# Legal / AdSense safety screening
# --------------------------------------------------------------------------- #
# Từ khoá KHÔNG dùng cho trang AdSense (adult/bạo lực/thù ghét/rủi ro y tế-tài chính/
# nhạy cảm). Query khớp → bỏ; ứng viên có alt khớp → đánh dấu rejected.
UNSAFE_TERMS = {
    # adult / sexual
    "nude", "nudity", "sex", "sexy", "porn", "erotic", "lingerie", "nsfw",
    # violence / weapons / gore
    "gun", "weapon", "blood", "gore", "violence", "war", "corpse", "knife attack",
    # hate / extremism
    "nazi", "swastika", "terrorist", "isis", "kkk",
    # medical risk / shock
    "surgery", "wound", "injury", "drug", "cocaine", "heroin", "syringe",
    # financial-risk / misleading
    "get rich quick", "guaranteed profit", "forex signal", "casino", "gambling", "lottery",
    # sensitive
    "funeral", "accident scene", "suicide", "self harm",
}

# Nhãn hiệu/logo phổ biến → KHÔNG dùng làm cover trừ khi người duyệt xác nhận
# context-safe (đánh dấu needs_brand_review, không tự loại nhưng cảnh báo rõ).
TRADEMARK_HINTS = {
    "logo", "brand", "trademark", "apple", "google", "facebook", "meta", "microsoft",
    "nike", "adidas", "coca cola", "pepsi", "samsung", "iphone", "android logo",
    "windows logo", "youtube logo", "visa", "mastercard", "paypal",
}


def _now_iso(now: datetime | None = None) -> str:
    return (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.replace("đ", "d").replace("Đ", "d").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:60] or "bai-viet"


def _norm(text: str) -> str:
    """Hạ dấu + lower để so khớp từ khoá an toàn không phụ thuộc dấu tiếng Việt."""
    text = unicodedata.normalize("NFD", text or "")
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text.replace("đ", "d").replace("Đ", "d").lower()


# --------------------------------------------------------------------------- #
# Search queries từ title / keyword / category / tags
# --------------------------------------------------------------------------- #
def build_search_queries(
    *, title: str = "", keyword: str = "", category: str = "", tags=None
) -> list[str]:
    """Sinh danh sách query ưu tiên (dedupe, đã lọc unsafe), tối đa MAX_QUERIES."""
    tags = tags or []
    if isinstance(tags, str):
        tags = [t.strip() for t in re.split(r"[,\n]", tags) if t.strip()]

    raw: list[str] = []
    if keyword:
        raw.append(keyword)
    # title rút gọn còn cụm 2–5 từ "sạch" (bỏ ký tự đặc biệt) làm query ảnh.
    if title:
        words = re.sub(r"[^\w\sÀ-ỹ]", " ", title).split()
        if words:
            raw.append(" ".join(words[:5]))
    if tags:
        raw.append(" ".join(str(t) for t in tags[:2]))
    if category and category.lower() not in ("tất cả", "tat ca", "all", ""):
        raw.append(category)

    out: list[str] = []
    seen: set[str] = set()
    for q in raw:
        q = re.sub(r"\s+", " ", str(q).strip())
        if not q:
            continue
        ok, _ = is_query_safe(q)
        if not ok:
            continue
        key = _norm(q)
        if key in seen:
            continue
        seen.add(key)
        out.append(q)
        if len(out) >= MAX_QUERIES:
            break
    return out


def is_query_safe(query: str) -> tuple[bool, str]:
    """False nếu query chứa từ khoá unsafe (adult/bạo lực/rủi ro…)."""
    n = _norm(query)
    for term in UNSAFE_TERMS:
        if _norm(term) in n:
            return False, f"unsafe term: {term}"
    return True, ""


def _alt_flags(alt: str) -> dict:
    """Cờ an toàn cho 1 ứng viên dựa trên alt/title text."""
    n = _norm(alt)
    unsafe = next((t for t in UNSAFE_TERMS if _norm(t) in n), None)
    brand = next((t for t in TRADEMARK_HINTS if _norm(t) in n), None)
    return {
        "adsense_unsafe": bool(unsafe),
        "unsafe_reason": unsafe or "",
        "needs_brand_review": bool(brand),
        "brand_hint": brand or "",
    }


# --------------------------------------------------------------------------- #
# robots.txt (tôn trọng — mặc định bảo thủ)
# --------------------------------------------------------------------------- #
def robots_allows(url: str, fetcher=None) -> bool:
    """True nếu robots.txt CHO PHÉP crawl `url` với UA của ta.

    Bảo thủ: KHÔNG đọc được robots.txt (mạng chặn/đường dẫn lỗi) → trả False để dừng êm.
    `fetcher(url)->str` có thể inject trong test để khỏi chạm mạng.
    """
    parsed = urllib.parse.urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        if fetcher is not None:
            txt = fetcher(robots_url)
        else:
            txt = _http_get_text(robots_url)
        if not txt:
            return False
        rp = RobotFileParser()
        rp.parse(txt.splitlines())
        return rp.can_fetch(USER_AGENT, url)
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# HTTP (chỉ GET public page, có UA + timeout; không cookie/login)
# --------------------------------------------------------------------------- #
def _http_get_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:  # noqa: S310 (public GET)
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, "replace")


def _http_get_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:  # noqa: S310
        return resp.read()


def search_page_url(query: str) -> str:
    """URL trang tìm kiếm public của Pixabay, ép orientation=horizontal (landscape)."""
    q = urllib.parse.quote(query.strip().lower().replace(" ", "-"))
    return f"{PIXABAY_HOST}/photos/search/{q}/?orientation=horizontal"


# --------------------------------------------------------------------------- #
# Parse trang kết quả public → ứng viên landscape
# --------------------------------------------------------------------------- #
_PHOTO_HREF = re.compile(r'href="(/photos/([a-z0-9\-]+?)-(\d+)/)"', re.I)
_IMG_TAG = re.compile(r"<img\b[^>]*>", re.I)
_ATTR = lambda name: re.compile(rf'{name}="([^"]*)"', re.I)  # noqa: E731
_USER_HREF = re.compile(r'href="(/users/[a-z0-9\-]+-\d+/)"', re.I)


def parse_candidates(html: str, query: str, now: datetime | None = None) -> list[dict]:
    """Bóc ứng viên từ HTML trang search public. Tolerant: HTML lạ/rỗng → []."""
    if not html:
        return []
    ts = _now_iso(now)
    out: list[dict] = []
    seen_ids: set[str] = set()

    # Mỗi result = 1 anchor /photos/<slug>-<id>/ ; tìm <img> gần nhất sau anchor.
    for m in _PHOTO_HREF.finditer(html):
        photo_path, slug_part, photo_id = m.group(1), m.group(2), m.group(3)
        if photo_id in seen_ids:
            continue
        window = html[m.end(): m.end() + 600]
        img_m = _IMG_TAG.search(window)
        alt = src = ""
        if img_m:
            tag = img_m.group(0)
            alt_m = _ATTR("alt").search(tag)
            alt = (alt_m.group(1).strip() if alt_m else "")
            # ưu tiên src https thật; nếu lazyload (data-lazy/srcset) thì lấy URL đầu.
            for attr in ("src", "data-lazy-src", "data-src"):
                sm = _ATTR(attr).search(tag)
                if sm and sm.group(1).startswith("http"):
                    src = sm.group(1)
                    break
            if not src:
                ss = _ATTR("srcset").search(tag) or _ATTR("data-lazy-srcset").search(tag)
                if ss:
                    first = ss.group(1).split(",")[0].strip().split(" ")[0]
                    if first.startswith("http"):
                        src = first
        if not alt:
            alt = slug_part.replace("-", " ").strip()

        # author (best-effort): link /users/ gần anchor
        author = "Unknown (Pixabay contributor)"
        um = _USER_HREF.search(window)
        if um:
            uslug = um.group(1).rstrip("/").rsplit("/", 1)[-1]
            uname = re.sub(r"-\d+$", "", uslug).replace("-", " ").strip()
            if uname:
                author = uname

        seen_ids.add(photo_id)
        cand = {
            "id": photo_id,
            "title": alt,
            "alt": alt,
            "author": author,
            "source_url": f"{PIXABAY_HOST}{photo_path}",
            "preview_url": src if src.startswith("https://") else "",
            "license_note": LICENSE_NOTE,
            "orientation": "landscape",
            "matched_query": query,
            "crawled_at": ts,
        }
        cand.update(_alt_flags(alt))
        out.append(cand)
    return out


# --------------------------------------------------------------------------- #
# Discovery — gợi ý 3–5 ứng viên (không bao giờ raise)
# --------------------------------------------------------------------------- #
def discover_candidates(
    *,
    title: str = "",
    keyword: str = "",
    category: str = "",
    tags=None,
    limit: int = DEFAULT_LIMIT,
    html_by_query: dict | None = None,
    fetcher=None,
    robots_check=None,
    now: datetime | None = None,
    sleep=time.sleep,
) -> dict:
    """Trả về dict {status, candidates, queries, note}. KHÔNG raise, KHÔNG fail build.

    Tham số test-friendly:
      - html_by_query: {query_or_url: html} → bỏ qua mạng, parse trực tiếp.
      - fetcher(url)->str: nguồn HTML thật/giả; mặc định urllib GET (timeout ngắn).
      - robots_check(url)->bool: ghi đè kiểm tra robots (mặc định robots_allows).
    """
    limit = max(MIN_CANDIDATES, min(int(limit or DEFAULT_LIMIT), 5))
    queries = build_search_queries(
        title=title, keyword=keyword, category=category, tags=tags
    )
    result = {
        "status": "no_candidates",
        "candidates": [],
        "queries": queries,
        "note": "",
        "generated_at": _now_iso(now),
    }
    if not queries:
        result["note"] = "Không sinh được query an toàn từ title/keyword/category/tags."
        return result

    robots_fn = robots_check or (lambda u: robots_allows(u, fetcher=fetcher))
    seen_ids: set[str] = set()
    candidates: list[dict] = []
    blocked_any = False

    for i, q in enumerate(queries):
        url = search_page_url(q)
        # 1) Lấy HTML: ưu tiên injected (test), rồi fetcher, rồi mạng thật.
        html = None
        if html_by_query is not None:
            html = html_by_query.get(q) or html_by_query.get(url)
            if html is None:
                continue
        else:
            # 2) Tôn trọng robots TRƯỚC khi chạm trang search.
            if not robots_fn(url):
                blocked_any = True
                continue
            if i > 0 and sleep:
                sleep(RATE_LIMIT_SECONDS)  # rate-limit: không burst
            try:
                html = (fetcher or _http_get_text)(url)
            except Exception:
                blocked_any = True
                continue

        for cand in parse_candidates(html, q, now=now):
            if cand["id"] in seen_ids:
                continue
            if cand.get("adsense_unsafe"):
                continue  # loại ảnh không AdSense-safe khỏi gợi ý
            seen_ids.add(cand["id"])
            candidates.append(cand)
            if len(candidates) >= limit:
                break
        if len(candidates) >= limit:
            break

    if candidates:
        result["status"] = "ok"
        result["candidates"] = candidates[:limit]
        flagged = sum(1 for c in candidates if c.get("needs_brand_review"))
        result["note"] = (
            f"{len(result['candidates'])} ứng viên (landscape). "
            "CHƯA tải — cần người duyệt thủ công."
            + (f" {flagged} ứng viên có dấu hiệu logo/brand → soi kỹ trước khi dùng." if flagged else "")
        )
    elif blocked_any:
        result["status"] = "blocked"
        result["note"] = (
            "Bị chặn (robots.txt disallow hoặc không truy cập được trang public). "
            "Dừng êm — giữ nguyên OG fallback/placeholder."
        )
    else:
        result["note"] = "Không tìm thấy ứng viên phù hợp — giữ nguyên OG fallback/placeholder."
    return result


# --------------------------------------------------------------------------- #
# Suggestions sidecar (volatile — gitignored)
# --------------------------------------------------------------------------- #
def suggestions_path(slug: str) -> Path:
    return SUGGEST_DIR / f"{slug}.json"


def save_suggestions(slug: str, result: dict) -> Path:
    SUGGEST_DIR.mkdir(parents=True, exist_ok=True)
    payload = dict(result)
    payload["slug"] = slug
    path = suggestions_path(slug)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def load_suggestions(slug: str) -> dict | None:
    path = suggestions_path(slug)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


# --------------------------------------------------------------------------- #
# Metadata bắt buộc + frontmatter
# --------------------------------------------------------------------------- #
def build_metadata(candidate: dict, *, verified_manually: bool,
                   commercial_use_checked: bool, now: datetime | None = None) -> dict:
    """Dựng metadata nguồn/giấy phép cho 1 ảnh đã xác nhận."""
    return {
        "image_source": "Pixabay",
        "image_author": candidate.get("author") or "Unknown (Pixabay contributor)",
        "image_url": candidate.get("source_url", ""),
        "image_license_note": candidate.get("license_note") or LICENSE_NOTE,
        "image_downloaded_at": _now_iso(now),
        "image_verified_manually": bool(verified_manually),
        "image_commercial_use_checked": bool(commercial_use_checked),
        "image_preview_url": candidate.get("preview_url", ""),
        "image_alt": candidate.get("alt", ""),
        "image_crawled_at": candidate.get("crawled_at", ""),
    }


def validate_metadata(meta: dict) -> tuple[bool, list[str]]:
    """(ok, missing). Thiếu field bắt buộc HOẶC chưa verify/commercial-check → not ok."""
    missing = [f for f in MANDATORY_META_FIELDS if f not in meta or meta.get(f) in (None, "")]
    # nguồn + url là tối thiểu tuyệt đối
    if not meta.get("image_url"):
        if "image_url" not in missing:
            missing.append("image_url")
    if meta.get("image_verified_manually") is not True:
        missing.append("image_verified_manually!=true")
    if meta.get("image_commercial_use_checked") is not True:
        missing.append("image_commercial_use_checked!=true")
    return (not missing), missing


def frontmatter_lines(meta: dict, thumbnail_rel: str | None = None) -> list[str]:
    """TOML lines để chèn vào [extra] của bài (chỉ field nguồn/giấy phép + thumbnail)."""
    def b(v):  # bool TOML
        return "true" if v else "false"

    def s(v):  # string TOML
        return '"' + str(v).replace("\\", "\\\\").replace('"', '\\"') + '"'

    lines = []
    if thumbnail_rel:
        lines.append(f"thumbnail = {s(thumbnail_rel)}")
    lines += [
        f"image_source = {s(meta['image_source'])}",
        f"image_author = {s(meta['image_author'])}",
        f"image_url = {s(meta['image_url'])}",
        f"image_license_note = {s(meta['image_license_note'])}",
        f"image_downloaded_at = {s(meta['image_downloaded_at'])}",
        f"image_verified_manually = {b(meta['image_verified_manually'])}",
        f"image_commercial_use_checked = {b(meta['image_commercial_use_checked'])}",
    ]
    return lines


def inject_extra_fields(text: str, lines: list[str]) -> str:
    """Chèn `lines` vào block [extra] của frontmatter TOML (+++ … +++).

    - Có [extra] → thêm ngay sau header (không trùng key đã có: key cũ thắng).
    - Chưa có [extra] → tạo block [extra] cuối frontmatter.
    - Không có frontmatter +++ → trả nguyên văn (không phá bài).
    """
    if not text.startswith("+++"):
        return text
    end = text.find("\n+++", 3)
    if end == -1:
        return text
    fm = text[3:end]
    body = text[end + 4:]  # sau "\n+++"

    existing_keys = set(re.findall(r"^\s*([a-zA-Z_][\w]*)\s*=", fm, re.M))
    new_lines = [ln for ln in lines if ln.split("=", 1)[0].strip() not in existing_keys]
    if not new_lines:
        return text

    block = "\n".join(new_lines)
    if re.search(r"^\[extra\]\s*$", fm, re.M):
        fm = re.sub(r"(^\[extra\]\s*$)", r"\1\n" + block, fm, count=1, flags=re.M)
    else:
        fm = fm.rstrip("\n") + "\n\n[extra]\n" + block + "\n"
    return "+++" + fm + "\n+++" + body


# --------------------------------------------------------------------------- #
# Ownership guard — Pixabay images PHẢI nằm ngoài owned/watermark roots
# --------------------------------------------------------------------------- #
def assert_third_party(path: Path) -> None:
    """Raise nếu đường lưu nằm trong thư mục owned/watermark (posting/, owned/)."""
    rel = path.resolve()
    try:
        rel_str = rel.relative_to(REPO).as_posix()
    except ValueError:
        rel_str = rel.as_posix()
    owned = ("static/img/posting/", "static/img/owned/")
    if any(rel_str.startswith(o) for o in owned):
        raise ValueError(
            f"REFUSED: Pixabay (third-party) image must NOT be saved into an owned/"
            f"watermark folder: {rel_str}"
        )
    if "static/img/third-party/" not in rel_str:
        raise ValueError(
            f"REFUSED: Pixabay image must be saved under static/img/third-party/: {rel_str}"
        )


def _repo_rel(path: Path) -> str:
    """Repo-relative posix nếu nằm trong REPO; ngoài REPO (test tmp) → absolute posix."""
    p = path.resolve()
    try:
        return p.relative_to(REPO).as_posix()
    except ValueError:
        return p.as_posix()


def _static_rel(path: Path) -> str:
    """URL bắt đầu từ sau 'static/' (vd /img/third-party/pixabay/x/cover.webp)."""
    parts = path.resolve().as_posix().split("/static/", 1)
    return "/" + parts[1] if len(parts) == 2 else path.as_posix()


def _ext_from_url(url: str, default: str = ".jpg") -> str:
    path = urllib.parse.urlparse(url).path
    ext = Path(path).suffix.lower()
    return ext if ext in (".jpg", ".jpeg", ".png", ".webp") else default


def _maybe_webp(src_path: Path, quality: int = 82) -> Path | None:
    """Convert sang .webp nếu Pillow có; trả path .webp hoặc None nếu không thể."""
    if src_path.suffix.lower() == ".webp":
        return src_path
    try:
        from PIL import Image  # type: ignore
    except Exception:
        return None
    dst = src_path.with_suffix(".webp")
    try:
        with Image.open(src_path) as im:
            if im.mode in ("P", "LA"):
                im = im.convert("RGBA")
            elif im.mode == "CMYK":
                im = im.convert("RGB")
            im.save(dst, "WEBP", quality=quality, method=6)
        return dst
    except Exception:
        return None


def confirm_download(
    *,
    candidate: dict,
    slug: str,
    verified_manually: bool,
    commercial_use_checked: bool,
    dest_root: Path | None = None,
    fetcher=None,
    to_webp: bool = True,
    article: Path | None = None,
    now: datetime | None = None,
) -> dict:
    """Tải ĐÚNG ảnh đã được xác nhận thủ công vào thư mục third-party + ghi metadata.

    BẮT BUỘC: verified_manually và commercial_use_checked = True, có image_url.
    Thiếu → status 'refused', KHÔNG tải.
    Trả: {status, image_path, sidecar_path, metadata, thumbnail}.
    """
    res: dict = {"status": "refused", "image_path": None, "sidecar_path": None,
                 "metadata": None, "thumbnail": None, "errors": []}

    meta = build_metadata(
        candidate,
        verified_manually=verified_manually,
        commercial_use_checked=commercial_use_checked,
        now=now,
    )
    ok, missing = validate_metadata(meta)
    if not ok:
        res["errors"].append("metadata bắt buộc thiếu hoặc chưa xác nhận: " + ", ".join(missing))
        res["status"] = "refused"
        return res
    if candidate.get("adsense_unsafe"):
        res["errors"].append(f"ứng viên không AdSense-safe: {candidate.get('unsafe_reason')}")
        return res

    download_url = candidate.get("preview_url") or candidate.get("download_url")
    if not download_url or not download_url.startswith("https://"):
        res["errors"].append("không có preview_url https an toàn để tải (chỉ trang public).")
        return res

    dest_root = Path(dest_root) if dest_root else THIRD_PARTY_ROOT
    folder = dest_root / slug
    ext = _ext_from_url(download_url)
    img_path = folder / f"cover{ext}"
    try:
        assert_third_party(img_path)  # KHÔNG bao giờ ghi vào owned/watermark folder
    except ValueError as e:
        res["errors"].append(str(e))
        return res

    folder.mkdir(parents=True, exist_ok=True)
    try:
        data = (fetcher or _http_get_bytes)(download_url)
    except Exception as e:
        res["errors"].append(f"tải ảnh thất bại (giữ OG fallback): {e}")
        res["status"] = "blocked"
        return res
    if not data:
        res["errors"].append("ảnh rỗng — giữ OG fallback.")
        res["status"] = "blocked"
        return res
    img_path.write_bytes(data)

    final = img_path
    if to_webp:
        webp = _maybe_webp(img_path)
        if webp and webp != img_path:
            if img_path.exists():
                img_path.unlink()
            final = webp

    meta["image_file"] = _repo_rel(final)
    thumb_rel = _static_rel(final)  # URL dùng cho thumbnail, vd /img/third-party/pixabay/...
    meta["image_thumbnail"] = thumb_rel

    sidecar = final.with_suffix(final.suffix + ".source.json")
    sidecar.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if article:
        article = Path(article)
        if article.is_file():
            txt = article.read_text(encoding="utf-8")
            txt2 = inject_extra_fields(txt, frontmatter_lines(meta, thumbnail_rel=thumb_rel))
            if txt2 != txt:
                article.write_text(txt2, encoding="utf-8")
                res["article_updated"] = True

    res.update({
        "status": "downloaded",
        "image_path": _repo_rel(final),
        "sidecar_path": _repo_rel(sidecar),
        "metadata": meta,
        "thumbnail": thumb_rel,
    })
    return res


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _cmd_suggest(args) -> int:
    result = discover_candidates(
        title=args.title, keyword=args.keyword, category=args.category,
        tags=args.tags, limit=args.limit,
    )
    slug = args.slug or slugify(args.title or args.keyword or "bai-viet")
    path = save_suggestions(slug, result)
    print(f"PIXABAY-SUGGEST:{path.relative_to(REPO)}")
    print(f"status={result['status']} · {result['note']}")
    for i, c in enumerate(result["candidates"]):
        flag = " ⚠ brand-review" if c.get("needs_brand_review") else ""
        print(f"  [{i}] {c['title'][:60]} — {c['author']} — {c['source_url']}{flag}")
    print("→ Duyệt thủ công rồi chạy: confirm --slug %s --index <i> --yes --commercial-ok" % slug)
    return 0  # luôn 0 — không bao giờ làm fail luồng tạo bài


def _cmd_confirm(args) -> int:
    data = load_suggestions(args.slug)
    if not data or not data.get("candidates"):
        print(f"✗ Không có gợi ý cho slug '{args.slug}'. Chạy `suggest` trước.", file=sys.stderr)
        return 2
    if args.index < 0 or args.index >= len(data["candidates"]):
        print(f"✗ index {args.index} ngoài phạm vi (0..{len(data['candidates'])-1}).", file=sys.stderr)
        return 2
    if not (args.yes and args.commercial_ok):
        print("✗ Từ chối: cần --yes (xác nhận thủ công) VÀ --commercial-ok "
              "(đã kiểm tra quyền dùng thương mại).", file=sys.stderr)
        return 2
    cand = data["candidates"][args.index]
    res = confirm_download(
        candidate=cand, slug=args.slug,
        verified_manually=True, commercial_use_checked=True,
        article=Path(args.article) if args.article else None,
        to_webp=not args.no_webp,
    )
    if res["status"] == "downloaded":
        print(f"✓ Đã tải: {res['image_path']}")
        print(f"  sidecar: {res['sidecar_path']}")
        print(f"  thumbnail: {res['thumbnail']}")
        if res.get("article_updated"):
            print("  ✎ Đã chèn frontmatter image_* vào bài.")
        return 0
    print(f"✗ {res['status']}: " + "; ".join(res["errors"]), file=sys.stderr)
    return 2


def _cmd_status(args) -> int:
    data = load_suggestions(args.slug)
    if not data:
        print(f"(chưa có gợi ý cho '{args.slug}')")
        return 0
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="No-API Pixabay image-assist (suggest → confirm).")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sg = sub.add_parser("suggest", help="Gợi ý 3–5 ứng viên (không tải).")
    sg.add_argument("--slug", default="")
    sg.add_argument("--title", default="")
    sg.add_argument("--keyword", default="")
    sg.add_argument("--category", default="")
    sg.add_argument("--tags", default="")
    sg.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    sg.set_defaults(func=_cmd_suggest)

    cf = sub.add_parser("confirm", help="Tải ảnh đã xác nhận thủ công (--yes --commercial-ok).")
    cf.add_argument("--slug", required=True)
    cf.add_argument("--index", type=int, required=True)
    cf.add_argument("--yes", action="store_true", help="Xác nhận đã duyệt thủ công.")
    cf.add_argument("--commercial-ok", action="store_true", help="Đã kiểm tra quyền dùng thương mại.")
    cf.add_argument("--article", default="", help="Đường dẫn bài .md để chèn frontmatter.")
    cf.add_argument("--no-webp", action="store_true", help="Không convert .webp.")
    cf.set_defaults(func=_cmd_confirm)

    st = sub.add_parser("status", help="In gợi ý đã lưu.")
    st.add_argument("--slug", required=True)
    st.set_defaults(func=_cmd_status)
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # không bao giờ kéo sập luồng tạo bài
        print(f"::warning::pixabay_image_assist unexpected error: {exc}", file=sys.stderr)
        sys.exit(0)
