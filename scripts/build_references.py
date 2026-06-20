"""
Build per-post reference index from markdown links (external + internal).

Scans content/posting, content/baochi, content/pages → data/references.json
for templates/macros/references.html at end of articles.

Run before `zola build` (deploy.yml, qa.yml, build-related.yml).
"""
from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path
from urllib.parse import urlparse, urlunparse

# Code-span-aware link masking (shared link-safety layer). Reusing this keeps the
# references builder from harvesting EXAMPLE links written inside `code spans` /
# ``` fenced blocks ``` — e.g. an article that documents `[text](/posting/slug/)`
# must NOT produce a real reference link to /posting/slug/ (the V14 / V10-LINKS
# class: never parse links inside code spans).
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from link_utils import mask_code_spans
except ImportError:  # pragma: no cover - degrade safely if the shared lib moves
    def mask_code_spans(text: str, fill: str = " ") -> str:
        return text

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "references.json"
BASE_URL = "https://seomoney.org"

CONTENT_DIRS = (
    ROOT / "content" / "posting",
    ROOT / "content" / "baochi",
    ROOT / "content" / "pages",
)

# Markdown links — exclude image syntax leading !
LINK_MD_RE = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)]+)\)")
LINK_HTML_RE = re.compile(
    r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>([^<]*)</a>',
    re.IGNORECASE,
)

SKIP_URL_PREFIXES = ("#", "mailto:", "tel:", "javascript:")
STATIC_ASSET_PREFIXES = ("/img/", "/js/", "/css/", "/fonts/")

OFFICIAL_DOMAIN_TITLES = {
    "developers.google.com": "Google Search Central",
    "search.google.com": "Google Search Central",
    "support.google.com": "Google AdSense Help",
    "adsense.google.com": "Google AdSense",
    "www.google.com": "Google",
    "docs.github.com": "GitHub Docs",
    "github.com": "GitHub",
    "developers.cloudflare.com": "Cloudflare Docs",
    "developer.mozilla.org": "Mozilla MDN",
    "mdn.mozilla.org": "Mozilla MDN",
    "web.dev": "web.dev",
    "www.getzola.org": "Zola Documentation",
    "english.visitkorea.or.kr": "Visit Korea",
    "affiliate.shopee.vn": "Shopee Affiliate Program",
    "guide.michelin.com": "Michelin Guide",
    "en.wikipedia.org": "Wikipedia",
    "www.iaea.org": "IAEA",
    "iaea.org": "IAEA",
}

GENERIC_LINK_TEXT = frozenset({
    "", "link", "here", "tại đây", "xem thêm", "đọc thêm", "nguồn", "source",
    "click here", "this", "này",
})


def parse_post(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    if text.startswith("+++"):
        m = re.match(r"^\+\+\+\s*\n(.*?)\n\+\+\+\s*\n?(.*)$", text, re.DOTALL)
        if not m:
            return {}, text
        try:
            return tomllib.loads(m.group(1)), m.group(2)
        except tomllib.TOMLDecodeError as exc:
            print(f"WARN: TOML parse fail {path.name}: {exc}", file=sys.stderr)
            return {}, m.group(2)
    return {}, text


def normalize_url(url: str) -> str:
    url = url.strip()
    if url.startswith("<") and url.endswith(">"):
        url = url[1:-1].strip()
    parsed = urlparse(url)
    if parsed.scheme in ("http", "https"):
        host = (parsed.hostname or "").lower()
        path = parsed.path.rstrip("/") or "/"
        # Drop tracking query
        return urlunparse((parsed.scheme, host + (f":{parsed.port}" if parsed.port else ""), path, "", "", ""))
    return url.rstrip("/")


def host_label(host: str) -> str:
    host = host.lower().removeprefix("www.")
    if host in OFFICIAL_DOMAIN_TITLES:
        return OFFICIAL_DOMAIN_TITLES[host]
    for domain, title in OFFICIAL_DOMAIN_TITLES.items():
        if host == domain or host.endswith("." + domain):
            return title
    parts = host.split(".")
    if len(parts) >= 2:
        return parts[-2].replace("-", " ").title() + " (" + host + ")"
    return host


def is_site_host(host: str | None) -> bool:
    if not host:
        return False
    h = host.lower()
    return h in ("seomoney.org", "localhost", "127.0.0.1")


def classify_url(url: str) -> str:
    """external | internal | skip"""
    if not url or url.startswith(SKIP_URL_PREFIXES):
        return "skip"
    if url.startswith("@/"):
        return "internal"
    if url.startswith("/"):
        if any(url.startswith(p) for p in STATIC_ASSET_PREFIXES):
            return "skip"
        if "/img/" in url or url.endswith((".webp", ".jpg", ".png", ".svg", ".gif")):
            return "skip"
        return "internal"
    parsed = urlparse(url)
    if parsed.scheme in ("http", "https"):
        if is_site_host(parsed.hostname):
            return "internal"
        return "external"
    return "skip"


def link_title(text: str, url: str, kind: str, slug_index: dict) -> str:
    t = (text or "").strip()
    if t and t.lower() not in GENERIC_LINK_TEXT and len(t) > 2:
        return t
    if kind == "internal":
        key = internal_lookup_key(url)
        if key and key in slug_index:
            return slug_index[key]["title"]
        if url.startswith("/"):
            seg = url.strip("/").split("/")[-1].replace("-", " ").title()
            return seg or url
    if kind == "external":
        host = urlparse(url).hostname or ""
        return host_label(host)
    return url


def internal_lookup_key(url: str) -> str | None:
    if url.startswith("@/"):
        return "content/" + url[2:].lstrip("/")
    if url.startswith("/"):
        # /zola/posting/slug/ or /posting/slug/ — strip base-url path prefix
        # (links across the blog are written with the /zola prefix).
        path = url.removeprefix("/zola")
        parts = [p for p in path.strip("/").split("/") if p]
        if len(parts) >= 2:
            section, slug = parts[0], parts[1]
            return f"content/{section}/{slug}.md"
        if len(parts) == 1:
            return f"content/pages/{parts[0]}.md"
    parsed = urlparse(url)
    if is_site_host(parsed.hostname):
        path = parsed.path.removeprefix("/zola").strip("/")
        parts = [p for p in path.split("/") if p]
        if len(parts) >= 2:
            return f"content/{parts[0]}/{parts[1]}.md"
    return None


def resolve_internal_url(url: str, slug_index: dict) -> str:
    key = internal_lookup_key(url)
    if key and key in slug_index:
        return slug_index[key]["permalink"]
    if url.startswith("@/"):
        # Fallback: map to site path
        rel = url[2:].replace(".md", "/").replace("content/", "")
        return f"{BASE_URL}/{rel}"
    if url.startswith("/"):
        # Strip the /zola base-url path before re-prefixing → avoid /zola/zola/.
        return BASE_URL + url.removeprefix("/zola")
    return url


def extract_links(body: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    # Mask code spans/fenced blocks first → example links inside `code` are not
    # harvested as real references (offset-preserving fill keeps regex spans valid).
    body = mask_code_spans(body)
    for m in LINK_MD_RE.finditer(body):
        found.append((m.group(1), m.group(2).strip()))
    for m in LINK_HTML_RE.finditer(body):
        found.append((m.group(2), m.group(1).strip()))
    return found


def build_slug_index() -> dict[str, dict]:
    index: dict[str, dict] = {}
    for content_dir in CONTENT_DIRS:
        if not content_dir.is_dir():
            continue
        section = content_dir.name
        for path in sorted(content_dir.glob("*.md")):
            if path.name.startswith("_"):
                continue
            meta, _ = parse_post(path)
            slug = meta.get("slug") or path.stem
            title = meta.get("title") or slug.replace("-", " ").title()
            rel = f"content/{section}/{path.name}"
            permalink = f"{BASE_URL}/{section}/{slug}/"
            if section == "pages":
                permalink = f"{BASE_URL}/{slug}/"
            index[rel] = {
                "title": title,
                "slug": slug,
                "section": section,
                "permalink": permalink,
            }
    return index


def merge_manual(meta: dict, bucket: list, key: str, slug_index: dict) -> None:
    extra = meta.get("extra") or {}
    for item in extra.get(key) or []:
        if not isinstance(item, dict):
            continue
        url = (item.get("url") or "").strip()
        title = (item.get("title") or "").strip()
        if not url:
            continue
        kind = classify_url(url)
        if kind == "skip":
            continue
        if kind == "internal":
            url = resolve_internal_url(url, slug_index)
        bucket.append({
            "title": title or link_title("", url, kind, slug_index),
            "url": normalize_url(url) if kind == "external" else url,
            "kind": kind,
        })


def dedupe_links(items: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for item in items:
        key = item["url"].lower().rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def sort_external(items: list[dict]) -> list[dict]:
    def rank(item: dict) -> tuple[int, str]:
        host = (urlparse(item["url"]).hostname or "").lower()
        official = 0 if any(host == d or host.endswith("." + d) for d in OFFICIAL_DOMAIN_TITLES) else 1
        return (official, item["title"].lower())

    return sorted(items, key=rank)


def default_copyright(external: list[dict]) -> str:
    if not external:
        return ""
    names = []
    for item in external[:6]:
        t = item["title"]
        if t and t not in names:
            names.append(t)
    if not names:
        return (
            "Một phần nội dung trong bài viết được tham khảo từ các nguồn bên ngoài "
            "được liệt kê ở trên. Mọi thương hiệu và tài liệu gốc thuộc quyền sở hữu "
            "của chủ sở hữu tương ứng. Bài viết mang tính trích dẫn, tổng hợp và phân tích."
        )
    joined = ", ".join(names[:-1]) + (" và " + names[-1] if len(names) > 1 else names[0])
    if len(names) == 1:
        joined = names[0]
    return (
        f"Một phần dữ liệu trong bài viết được tham khảo từ {joined}. "
        "Mọi thương hiệu, tên sản phẩm và tài liệu gốc thuộc quyền sở hữu của chủ "
        "sở hữu tương ứng. Bài viết chỉ trích dẫn, tổng hợp và phân tích — không "
        "nhằm thay thế tài liệu chính thức."
    )


def process_file(path: Path, slug_index: dict) -> dict | None:
    meta, body = parse_post(path)
    section = path.parent.name
    rel_key = f"content/{section}/{path.name}"

    if (meta.get("extra") or {}).get("references_skip"):
        return None

    external: list[dict] = []
    internal: list[dict] = []

    for text, raw_url in extract_links(body):
        kind = classify_url(raw_url)
        if kind == "skip":
            continue
        if kind == "external":
            url = normalize_url(raw_url)
            external.append({
                "title": link_title(text, url, kind, slug_index),
                "url": url,
                "kind": "external",
            })
        else:
            url = resolve_internal_url(raw_url, slug_index)
            internal.append({
                "title": link_title(text, url, kind, slug_index),
                "url": url,
                "kind": "internal",
            })

    merge_manual(meta, external, "references_external", slug_index)
    merge_manual(meta, internal, "references_internal", slug_index)

    external = sort_external(dedupe_links(external))
    internal = dedupe_links(internal)

    extra = meta.get("extra") or {}
    copyright_text = extra.get("references_copyright") or ""
    if not copyright_text and external and not extra.get("references_skip_copyright"):
        copyright_text = default_copyright(external)

    if not external and not internal and not copyright_text:
        return None

    return {
        "external": external,
        "internal": internal,
        "copyright": copyright_text,
        "external_count": len(external),
        "internal_count": len(internal),
    }


def main() -> int:
    slug_index = build_slug_index()
    result: dict[str, dict] = {}
    total = 0

    for content_dir in CONTENT_DIRS:
        if not content_dir.is_dir():
            continue
        for path in sorted(content_dir.glob("*.md")):
            if path.name.startswith("_"):
                continue
            rel_key = f"content/{content_dir.name}/{path.name}"
            data = process_file(path, slug_index)
            if data:
                result[rel_key] = data
                total += 1

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}: {total} posts with references")
    return 0


if __name__ == "__main__":
    sys.exit(main())