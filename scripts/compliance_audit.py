#!/usr/bin/env python3
"""
Compliance audit — SEO + site-quality signals for Zola blog.

Scans built HTML (public/) and source markdown (content/) with deterministic
checks. Writes generic results to data/compliance-score.json for /insights/.

Usage:
    zola build
    python3 scripts/compliance_audit.py
    python3 scripts/compliance_audit.py --stdout   # print summary only

Stdlib only. Internal scoring; public JSON uses neutral category labels.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parent.parent
PUBLIC = REPO / "public"
CONTENT = REPO / "content"
DATA = REPO / "data"
OUT_FILE = DATA / "compliance-score.json"

VN_TZ = timezone(timedelta(hours=7))
BASE_URL = "https://banhang-chogao.github.io/zola"

TITLE_MIN, TITLE_MAX = 10, 65
DESC_MIN, DESC_MAX = 50, 160
CONTENT_MIN_CHARS = 300
IMG_WARN_BYTES = 250_000
POST_DIRS = {"posting", "baochi", "du-lich", "topic"}

# Generic public labels — never expose AdSense/policy wording in JSON.
CATEGORIES = (
    ("metadata", "Metadata"),
    ("structure", "Structure"),
    ("media", "Media"),
    ("discovery", "Discovery"),
    ("content", "Content"),
    ("links", "Links"),
    ("access", "Access"),
)


class PageParser(HTMLParser):
    """Extract SEO/structure/media signals from one HTML page."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self._in_title = False
        self.metas: dict[str, str] = {}
        self.h_counts = Counter()
        self._heading = ""
        self.img_total = 0
        self.img_with_alt = 0
        self.has_jsonld = False
        self.is_redirect = False
        self.lang = ""
        self._skip_text = 0
        self.text_chars = 0
        self.links: list[str] = []
        self.has_main = False
        self.has_skip = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html" and a.get("lang"):
            self.lang = a["lang"]
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            if a.get("http-equiv", "").lower() == "refresh":
                self.is_redirect = True
            key = a.get("name") or a.get("property")
            if key and "content" in a:
                self.metas[key.lower()] = a["content"]
        elif tag == "link" and a.get("rel", "").lower() == "canonical":
            self.metas["__canonical__"] = a.get("href", "")
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.h_counts[tag] += 1
            self._heading = tag
        elif tag == "img":
            self.img_total += 1
            if a.get("alt", "").strip():
                self.img_with_alt += 1
        elif tag == "a" and a.get("href"):
            self.links.append(a["href"])
        elif tag == "main":
            self.has_main = True
        elif tag == "a" and a.get("href", "").startswith("#"):
            if "skip" in a.get("class", "").lower() or "skip" in a.get("id", "").lower():
                self.has_skip = True
        elif tag == "script":
            if a.get("type", "").lower() == "application/ld+json":
                self.has_jsonld = True
            self._skip_text += 1
        elif tag == "style":
            self._skip_text += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._heading = ""
        elif tag in ("script", "style") and self._skip_text > 0:
            self._skip_text -= 1

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._skip_text == 0:
            self.text_chars += len(data.strip())


def _status_from_ratio(ok: int, total: int, *, warn_below: float = 0.9) -> str:
    if total == 0:
        return "pass"
    ratio = ok / total
    if ratio >= warn_below:
        return "pass"
    if ratio >= 0.5:
        return "warn"
    return "fail"


def _score_from_status(status: str) -> float:
    return {"pass": 1.0, "warn": 0.5, "fail": 0.0}[status]


def _grade(score: float) -> str:
    if score >= 95:
        return "A+"
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def _mood(score: float) -> str:
    if score >= 85:
        return "good"
    if score >= 70:
        return "attention"
    return "needs_work"


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("+++"):
        return {}, text
    end = text.find("+++", 3)
    if end == -1:
        return {}, text
    block = text[3:end]
    body = text[end + 3 :].lstrip("\n")
    meta: dict = {}
    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" in line:
            continue
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            meta[key] = [] if not inner else [x.strip().strip('"').strip("'") for x in inner.split(",")]
        else:
            meta[key] = val
    return meta, body


def _strip_md(body: str) -> str:
    body = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
    body = re.sub(r"`[^`]+`", "", body)
    body = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", body)
    body = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", body)
    body = re.sub(r"#{1,6}\s+", "", body)
    body = re.sub(r"[*_~>|-]", "", body)
    return re.sub(r"\s+", " ", body).strip()


def _collect_articles() -> list[dict]:
    articles = []
    if not CONTENT.is_dir():
        return articles
    for md in sorted(CONTENT.rglob("*.md")):
        if md.name == "_index.md":
            continue
        rel = md.relative_to(CONTENT)
        parts = rel.parts
        if parts[0] not in POST_DIRS and parts[0] != "pages":
            continue
        try:
            raw = md.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        meta, body = _parse_frontmatter(raw)
        slug = md.stem
        articles.append({
            "path": str(rel),
            "slug": slug,
            "title": str(meta.get("title", "")).strip(),
            "date": str(meta.get("date", "")).strip(),
            "tags": meta.get("tags") or [],
            "categories": meta.get("categories") or meta.get("category") or [],
            "chars": len(_strip_md(body)),
            "is_post": parts[0] in POST_DIRS,
        })
    return articles


def _public_paths() -> set[str]:
    paths = set()
    if not PUBLIC.is_dir():
        return paths
    for f in PUBLIC.rglob("*"):
        if f.is_file():
            rel = "/" + f.relative_to(PUBLIC).as_posix()
            paths.add(rel)
            if rel.endswith("/index.html"):
                paths.add(rel[: -len("index.html")] or "/")
            if rel.endswith(".html"):
                paths.add(rel[: -len(".html")] + "/")
    return paths


def _normalize_href(href: str) -> str | None:
    href = href.strip()
    if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
        return None
    if href.startswith(BASE_URL):
        href = href[len(BASE_URL) :]
    parsed = urlparse(href)
    if parsed.scheme in ("http", "https"):
        return None
    path = parsed.path or "/"
    if not path.startswith("/"):
        path = "/" + path
    if path != "/" and not path.endswith("/") and "." not in Path(path).name:
        path += "/"
    return path.split("#")[0].split("?")[0] or "/"


def _scan_pages() -> list[tuple[str, PageParser]]:
    pages = []
    if not PUBLIC.is_dir():
        return pages
    for f in sorted(PUBLIC.rglob("*.html")):
        try:
            html = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        p = PageParser()
        try:
            p.feed(html)
        except Exception:
            pass
        if p.is_redirect:
            continue
        rel = "/" + f.relative_to(PUBLIC).as_posix()
        if rel.endswith("index.html"):
            rel = rel[: -len("index.html")] or "/"
        pages.append((rel, p))
    return pages


def _check_robots() -> tuple[str, str]:
    path = PUBLIC / "robots.txt"
    if not path.is_file():
        return "fail", "robots.txt missing"
    text = path.read_text(encoding="utf-8", errors="ignore").lower()
    if re.search(r"disallow\s*:\s*/\s*$", text, re.MULTILINE):
        return "fail", "robots blocks entire site"
    if "sitemap" not in text and (PUBLIC / "sitemap.xml").is_file():
        return "warn", "robots.txt has no sitemap hint"
    return "pass", "robots.txt OK"


def _image_stats() -> tuple[int, int, int]:
    heavy = 0
    legacy = 0
    total = 0
    for ext in ("*.jpg", "*.jpeg", "*.png", "*.gif", "*.webp", "*.svg"):
        for img in PUBLIC.rglob(ext):
            total += 1
            try:
                size = img.stat().st_size
            except OSError:
                continue
            if size > IMG_WARN_BYTES:
                heavy += 1
            if img.suffix.lower() in {".png", ".gif"} and size > 80_000:
                legacy += 1
    return total, heavy, legacy


def run_audit() -> dict:
    pages = _scan_pages()
    articles = _collect_articles()
    posts = [a for a in articles if a["is_post"]]
    pub_paths = _public_paths()

    cat_items: dict[str, list[dict]] = {cid: [] for cid, _ in CATEGORIES}

    # --- Metadata ---
    title_ok = desc_ok = canon_ok = 0
    for _, p in pages:
        t = p.title.strip()
        if TITLE_MIN <= len(t) <= TITLE_MAX:
            title_ok += 1
        d = p.metas.get("description", "").strip()
        if d and DESC_MIN <= len(d) <= DESC_MAX:
            desc_ok += 1
        if p.metas.get("__canonical__", "").strip():
            canon_ok += 1
    n = len(pages) or 1
    cat_items["metadata"].extend([
        {
            "label": "Page titles",
            "status": _status_from_ratio(title_ok, len(pages)),
            "detail": f"{title_ok}/{len(pages)} in range",
        },
        {
            "label": "Descriptions",
            "status": _status_from_ratio(desc_ok, len(pages)),
            "detail": f"{desc_ok}/{len(pages)} complete",
        },
        {
            "label": "Canonical URLs",
            "status": _status_from_ratio(canon_ok, len(pages)),
            "detail": f"{canon_ok}/{len(pages)} set",
        },
    ])

    # --- Structure ---
    h1_ok = lang_ok = viewport_ok = jsonld_ok = 0
    for _, p in pages:
        if p.h_counts.get("h1", 0) == 1:
            h1_ok += 1
        if p.lang:
            lang_ok += 1
        if p.metas.get("viewport"):
            viewport_ok += 1
        if p.has_jsonld:
            jsonld_ok += 1
    cat_items["structure"].extend([
        {
            "label": "Heading focus",
            "status": _status_from_ratio(h1_ok, len(pages)),
            "detail": f"{h1_ok}/{len(pages)} single H1",
        },
        {
            "label": "Document language",
            "status": _status_from_ratio(lang_ok, len(pages)),
            "detail": f"{lang_ok}/{len(pages)} with lang",
        },
        {
            "label": "Mobile viewport",
            "status": _status_from_ratio(viewport_ok, len(pages)),
            "detail": f"{viewport_ok}/{len(pages)} ready",
        },
        {
            "label": "Structured data",
            "status": _status_from_ratio(jsonld_ok, len(pages), warn_below=0.6),
            "detail": f"{jsonld_ok}/{len(pages)} pages",
        },
    ])

    # --- Media ---
    alt_ok_pages = 0
    for _, p in pages:
        if p.img_total == 0 or p.img_with_alt == p.img_total:
            alt_ok_pages += 1
    img_total, img_heavy, img_legacy = _image_stats()
    alt_status = _status_from_ratio(alt_ok_pages, len(pages))
    heavy_status = "pass" if img_heavy == 0 else ("warn" if img_heavy <= 3 else "fail")
    legacy_status = "pass" if img_legacy == 0 else ("warn" if img_legacy <= 5 else "fail")
    cat_items["media"].extend([
        {
            "label": "Image descriptions",
            "status": alt_status,
            "detail": f"{alt_ok_pages}/{len(pages)} pages covered",
        },
        {
            "label": "Image weight",
            "status": heavy_status,
            "detail": f"{img_heavy} large file(s)" if img_heavy else "within budget",
        },
        {
            "label": "Image formats",
            "status": legacy_status,
            "detail": f"{img_legacy} heavy PNG/GIF" if img_legacy else "formats OK",
        },
    ])

    # --- Discovery ---
    infra = {
        "robots.txt": (PUBLIC / "robots.txt").is_file(),
        "sitemap.xml": (PUBLIC / "sitemap.xml").is_file(),
        "atom.xml": (PUBLIC / "atom.xml").is_file(),
        "rss.xml": (PUBLIC / "rss.xml").is_file(),
    }
    robots_status, robots_detail = _check_robots()
    cat_items["discovery"].append({
        "label": "Crawler rules",
        "status": robots_status,
        "detail": robots_detail,
    })
    for key, label in (
        ("sitemap.xml", "Sitemap"),
        ("atom.xml", "Atom feed"),
        ("rss.xml", "RSS feed"),
    ):
        cat_items["discovery"].append({
            "label": label,
            "status": "pass" if infra[key] else "fail",
            "detail": "present" if infra[key] else "missing",
        })

    # --- Content ---
    dated = sum(1 for a in posts if a["date"])
    tagged = sum(1 for a in posts if a["tags"] or a["categories"])
    long_enough = sum(1 for a in posts if a["chars"] >= CONTENT_MIN_CHARS)
    titles = [a["title"] for a in articles if a["title"]]
    slugs = [a["slug"] for a in articles]
    dup_titles = len(titles) - len(set(titles))
    dup_slugs = len(slugs) - len(set(slugs))
    post_n = len(posts) or 1
    cat_items["content"].extend([
        {
            "label": "Publish dates",
            "status": _status_from_ratio(dated, len(posts)),
            "detail": f"{dated}/{len(posts)} articles",
        },
        {
            "label": "Taxonomies",
            "status": _status_from_ratio(tagged, len(posts)),
            "detail": f"{tagged}/{len(posts)} tagged",
        },
        {
            "label": "Article depth",
            "status": _status_from_ratio(long_enough, len(posts)),
            "detail": f"{long_enough}/{len(posts)} substantive",
        },
        {
            "label": "Unique titles",
            "status": "pass" if dup_titles == 0 else ("warn" if dup_titles <= 2 else "fail"),
            "detail": "no duplicates" if dup_titles == 0 else f"{dup_titles} duplicate(s)",
        },
        {
            "label": "Unique slugs",
            "status": "pass" if dup_slugs == 0 else "fail",
            "detail": "no duplicates" if dup_slugs == 0 else f"{dup_slugs} duplicate(s)",
        },
    ])

    # --- Links ---
    broken = 0
    checked = 0
    for _, p in pages:
        for href in p.links:
            norm = _normalize_href(href)
            if not norm:
                continue
            checked += 1
            if norm not in pub_paths:
                # allow root-relative without trailing slash variants
                alt = norm.rstrip("/") + "/"
                if alt not in pub_paths and norm + "index.html" not in pub_paths:
                    broken += 1
    link_status = "pass" if broken == 0 else ("warn" if broken <= 5 else "fail")
    cat_items["links"].append({
        "label": "Internal links",
        "status": link_status,
        "detail": "all valid" if broken == 0 else f"{broken} broken / {checked} checked",
    })

    # --- Access ---
    main_ok = skip_ok = 0
    for _, p in pages:
        if p.has_main:
            main_ok += 1
        if p.has_skip:
            skip_ok += 1
    cat_items["access"].extend([
        {
            "label": "Main landmarks",
            "status": _status_from_ratio(main_ok, len(pages)),
            "detail": f"{main_ok}/{len(pages)} pages",
        },
        {
            "label": "Skip navigation",
            "status": "pass" if skip_ok else ("warn" if skip_ok == 0 and len(pages) < 20 else "warn"),
            "detail": "detected" if skip_ok else "not detected in HTML",
        },
    ])

    # Aggregate categories + totals
    categories_out = []
    total_pass = total_warn = total_fail = 0
    weighted_sum = 0.0
    weight_total = 0.0

    for cid, clabel in CATEGORIES:
        items = cat_items[cid]
        if not items:
            continue
        c_pass = sum(1 for i in items if i["status"] == "pass")
        c_warn = sum(1 for i in items if i["status"] == "warn")
        c_fail = sum(1 for i in items if i["status"] == "fail")
        c_score = round(
            sum(_score_from_status(i["status"]) for i in items) / len(items) * 100, 1
        )
        categories_out.append({
            "id": cid,
            "label": clabel,
            "score": c_score,
            "pass": c_pass,
            "warn": c_warn,
            "fail": c_fail,
            "items": items,
        })
        total_pass += c_pass
        total_warn += c_warn
        total_fail += c_fail
        weighted_sum += c_score * len(items)
        weight_total += len(items)

    score = round(weighted_sum / weight_total, 1) if weight_total else 0.0

    highlights = []
    for cat in categories_out:
        for item in cat["items"]:
            if item["status"] == "fail":
                highlights.append({"type": "fail", "text": f"{cat['label']}: {item['label']}"})
            elif item["status"] == "warn":
                highlights.append({"type": "warn", "text": f"{cat['label']}: {item['label']}"})
    for cat in categories_out:
        for item in cat["items"]:
            if item["status"] == "pass" and len(highlights) < 6:
                highlights.append({"type": "pass", "text": f"{cat['label']}: {item['label']}"})
    highlights = highlights[:8]

    now = datetime.now(timezone.utc)
    return {
        "updated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "score": score,
        "grade": _grade(score),
        "mood": _mood(score),
        "stats": {
            "pass": total_pass,
            "warn": total_warn,
            "fail": total_fail,
            "total": total_pass + total_warn + total_fail,
        },
        "categories": categories_out,
        "highlights": highlights,
        "pages_scanned": len(pages),
        "articles_scanned": len(articles),
    }


def main() -> int:
    if not PUBLIC.is_dir():
        print("✗ Missing public/ — run `zola build` first.", file=sys.stderr)
        return 1

    result = run_audit()
    DATA.mkdir(exist_ok=True)
    OUT_FILE.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if "--stdout" in sys.argv:
        s = result["stats"]
        print(f"Compliance score: {result['score']}/100 ({result['grade']})")
        print(f"Checks: {s['pass']} pass · {s['warn']} warn · {s['fail']} fail")
    else:
        print(f"✓ Wrote {OUT_FILE.relative_to(REPO)} — {result['score']}/100 ({result['grade']})")

    return 0


if __name__ == "__main__":
    sys.exit(main())