"""
Crawler bài blog từ URL bất kỳ → extract metadata + render thành
HTML card theo design tokens momo style.

Stack:
- requests  : fetch HTML
- BeautifulSoup4 : parse HTML/CSS selectors
- (optional) playwright : fallback nếu site render bằng JS

Output JSON format:
{
  "title": "VssID là gì? Lợi ích, tiện ích nổi bật của VssID",
  "category": "Tài Chính - Bảo Hiểm",
  "timestamp": "2024-08-15T10:00:00",
  "thumbnail": "https://...",
  "excerpt": "Tìm hiểu VssID là gì..."
}

Usage:
    pip install -r scripts/requirements-crawler.txt
    python scripts/momo_crawler.py <URL>

Example:
    python scripts/momo_crawler.py https://www.momo.vn/blog/vssid-la-gi-c116dt2660
"""
import argparse
import json
import sys
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


def fetch_html(url: str, timeout: int = 15) -> str:
    """Fetch HTML từ URL với User-Agent giống browser thật."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "vi,en;q=0.9",
    }
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def extract_meta(soup: BeautifulSoup, name: str, prop: str = "name") -> str:
    """Đọc <meta name=X content=Y> hoặc <meta property=X content=Y>."""
    tag = soup.find("meta", {prop: name})
    return tag["content"].strip() if tag and tag.get("content") else ""


def extract_first_text(soup: BeautifulSoup, selectors: list) -> str:
    """Trả về text của selector đầu tiên match."""
    for sel in selectors:
        el = soup.select_one(sel)
        if el and el.get_text(strip=True):
            return el.get_text(strip=True)
    return ""


def extract_first_attr(soup: BeautifulSoup, selectors: list, attr: str) -> str:
    """Trả về attribute (href/src) của selector đầu tiên match."""
    for sel in selectors:
        el = soup.select_one(sel)
        if el and el.get(attr):
            return el[attr].strip()
    return ""


def parse_blog(html: str, base_url: str) -> dict:
    """Extract 5 fields từ HTML blog page.

    Cách hoạt động: ưu tiên Open Graph + Twitter Card meta (chuẩn chung
    của hầu hết blog modern). Fallback dùng selector tag <h1>, <article>.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Title — ưu tiên og:title, fallback <title> tag, fallback <h1>
    title = (
        extract_meta(soup, "og:title", "property")
        or extract_meta(soup, "twitter:title")
        or (soup.title.string.strip() if soup.title and soup.title.string else "")
        or extract_first_text(soup, ["h1", "article h1", "main h1"])
    )

    # Excerpt/description
    excerpt = (
        extract_meta(soup, "og:description", "property")
        or extract_meta(soup, "description")
        or extract_meta(soup, "twitter:description")
        or extract_first_text(soup, [
            "article > p:first-of-type",
            "main > p:first-of-type",
            ".excerpt", ".summary",
        ])
    )

    # Thumbnail
    thumbnail = (
        extract_meta(soup, "og:image", "property")
        or extract_meta(soup, "twitter:image")
        or extract_first_attr(soup, [
            "article img:first-of-type",
            "main img:first-of-type",
            ".thumbnail img",
            "img.featured",
        ], "src")
    )

    # Category — heuristic, đa số blog có breadcrumb hoặc tag
    category = extract_first_text(soup, [
        "[class*='category']",
        "[class*='Category']",
        "nav.breadcrumb a:last-child",
        ".tag", ".cat-tag",
        "[itemprop='articleSection']",
    ])

    # Timestamp — đa số dùng <time datetime>
    timestamp = extract_first_attr(soup, ["time[datetime]"], "datetime")
    if not timestamp:
        # fallback meta tag
        timestamp = (
            extract_meta(soup, "article:published_time", "property")
            or extract_meta(soup, "datePublished")
        )

    return {
        "url": base_url,
        "title": title,
        "category": category,
        "timestamp": timestamp,
        "thumbnail": thumbnail,
        "excerpt": excerpt,
    }


def render_card(data: dict) -> str:
    """Render dict thành HTML card theo momo design tokens.

    Cấu trúc HTML khớp với .momo-card SCSS class trong _momo-tokens.scss.
    Có thể paste trực tiếp vào trang Zola hoặc dùng làm component.
    """
    template = """<article class="momo-card">
    <a class="momo-card__image" href="{url}">
        <img src="{thumbnail}" alt="{title}" width="800" height="500"
             loading="lazy" decoding="async">
    </a>
    <div class="momo-card__body">
        {category_block}
        <span class="momo-card__insight">Insights khán giả</span>
        <h3 class="momo-card__title">
            <a href="{url}">{title}</a>
        </h3>
        <p class="momo-card__excerpt">{excerpt}</p>
        {meta_block}
    </div>
</article>"""

    category_block = (
        f'<span class="momo-card__cat">{data["category"]}</span>'
        if data.get("category") else ""
    )
    meta_block = (
        f'<div class="momo-card__meta"><time>{data["timestamp"][:10]}</time></div>'
        if data.get("timestamp") else ""
    )

    return template.format(
        url=data.get("url", "#"),
        title=data.get("title", "(no title)"),
        thumbnail=data.get("thumbnail", "https://picsum.photos/800/500"),
        excerpt=data.get("excerpt", "")[:200],
        category_block=category_block,
        meta_block=meta_block,
    )


def main():
    parser = argparse.ArgumentParser(description="Crawl blog metadata + render momo card")
    parser.add_argument("url", help="URL bài blog cần crawl")
    parser.add_argument("--render", action="store_true",
                        help="Render HTML card thay vì JSON")
    parser.add_argument("--output", "-o", help="Lưu output ra file")
    args = parser.parse_args()

    parsed = urlparse(args.url)
    if not parsed.scheme:
        print("ERROR: URL phải bắt đầu bằng http:// hoặc https://", file=sys.stderr)
        sys.exit(1)

    try:
        html = fetch_html(args.url)
    except requests.RequestException as e:
        print(f"ERROR: fetch failed — {e}", file=sys.stderr)
        print("Nếu site render bằng JS, cài playwright:", file=sys.stderr)
        print("  pip install playwright && playwright install chromium", file=sys.stderr)
        sys.exit(2)

    data = parse_blog(html, args.url)

    output = render_card(data) if args.render else json.dumps(data, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
