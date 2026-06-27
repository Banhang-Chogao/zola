#!/usr/bin/env python3
"""
content_creator.py — sinh series bài viết tự động từ brief của trang Content Creator.

Đầu vào (CLI hoặc workflow_dispatch inputs): chủ đề, số lượng bài, hình thức thu phí
(free → category mặc định "Tất cả"; paid → category "premium"), diễn giải chi tiết,
UI/UX mong muốn. Mỗi bài là 1 file content/posting/<slug>.md với frontmatter hợp lệ,
bám SEO CONTENT SYSTEM RULE: title/description, FAQ, internal link (gồm hub chuyên
mục), external link uy tín, CTA/next-step. Ghi thêm data/<series_id>-series.json.

Bài premium tách teaser bằng <!-- more --> → scripts/paywall_prepare_build.py --strip
sẽ chuyển full body sang private_content/ khi deploy (không lộ nội dung tĩnh).

In ra "PUBLISHED:<path>" cho mỗi file để workflow phát hiện thay đổi.

Stdlib only.

Lưu ý: đây là bộ khung nội dung có cấu trúc, seed từ brief người dùng. Có thể nối
thêm bước LLM trong workflow để mở rộng văn phong; cấu trúc/SEO/frontmatter đã hợp lệ.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTING = ROOT / "content" / "posting"
DATA = ROOT / "data"

PREMIUM_PRICE = 100_000
PREMIUM_TEASER_WORDS = 180


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.replace("đ", "d").replace("Đ", "d")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:60] or "bai-viet"


def esc_toml(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def build_article(
    *,
    topic: str,
    part: int,
    total: int,
    pricing: str,
    brief: str,
    ux: str,
    series_id: str,
    series_slugs: list[str],
    today: str,
) -> tuple[str, str]:
    """Trả về (slug, file_text) cho 1 bài."""
    is_paid = pricing == "paid"
    part_topic = f"{topic} — Phần {part}" if total > 1 else topic
    slug = slugify(f"{topic}-phan-{part}") if total > 1 else slugify(topic)

    title = f"{part_topic}"[:65]
    keyword = topic.lower()
    description = (
        f"{topic}: hướng dẫn chi tiết phần {part}/{total} — định nghĩa, các bước "
        f"thực hiện, sai lầm cần tránh và checklist hành động."
    )[:155]

    # ---- categories theo hình thức thu phí ----
    if is_paid:
        categories = '["Tất cả", "premium"]'
    else:
        categories = '["Tất cả"]'

    tags = json.dumps(
        ["content creator", series_id, slugify(topic).replace("-", " ")][:6],
        ensure_ascii=False,
    )

    # ---- internal links (>=5): hub + các part khác trong series ----
    hub_url = "/zola/categories/premium/" if is_paid else "/zola/categories/tat-ca/"
    related = [s for s in series_slugs if s != slug]
    # >=5 internal link, dedupe theo URL: hub chuyên mục + các part khác + evergreen.
    pairs = [("chuyên mục", hub_url)]
    for i, rs in enumerate(related, start=1):
        pairs.append((f"Phần {i if i < part else i + 1}", f"/zola/posting/{rs}/"))
    for label, url in [
        ("Tất cả bài viết", "/zola/categories/tat-ca/"),
        ("Trang chủ", "/zola/"),
        ("Công cụ", "/zola/tools/content-creator/"),
        ("Giới thiệu", "/zola/about/"),
        ("Liên hệ", "/zola/contact/"),
    ]:
        pairs.append((label, url))
    seen: set[str] = set()
    internal_links = []
    for label, url in pairs:
        if url in seen:
            continue
        seen.add(url)
        internal_links.append(f"[{label}]({url})")
        if len(internal_links) >= 6:
            break
    links_md = " · ".join(internal_links)

    # external reputable link
    ext = f"https://vi.wikipedia.org/wiki/Special:Search?search={topic.replace(' ', '+')}"

    brief_txt = brief.strip() or f"Bài viết tập trung làm rõ chủ đề «{topic}» một cách dễ áp dụng."
    ux_txt = ux.strip()

    # ---- FAQ frontmatter ----
    faqs = [
        (f"{topic} là gì?", f"{topic} là chủ đề được trình bày trong series này; phần {part} tập trung vào khía cạnh cốt lõi để bạn áp dụng ngay."),
        (f"Vì sao {topic} quan trọng?", f"Hiểu đúng {topic} giúp bạn ra quyết định tốt hơn, tiết kiệm thời gian và tránh các sai lầm phổ biến."),
        (f"Bắt đầu với {topic} như thế nào?", "Hãy đi theo các bước trong phần «Các bước thực hiện» bên dưới và dùng checklist hành động ở cuối bài."),
    ]
    faq_block = "\n".join(
        f'[[extra.faq]]\nq = "{esc_toml(q)}"\na = "{esc_toml(a)}"\n' for q, a in faqs
    )

    # ---- frontmatter ----
    extra_lines = [
        f'seo_keyword = "{esc_toml(keyword)}"',
        f'series = "{esc_toml(series_id)}"',
        f"series_part = {part}",
        f"series_total = {total}",
    ]
    if is_paid:
        extra_lines += [
            "premium = true",
            f"premium_post_id = \"{series_id}-{part:02d}\"",
            f"price = {PREMIUM_PRICE}",
            f"premium_teaser_words = {PREMIUM_TEASER_WORDS}",
        ]
    extra_block = "\n".join(extra_lines)

    fm = (
        "+++\n"
        f'title = "{esc_toml(title)}"\n'
        f'description = "{esc_toml(description)}"\n'
        f"date = {today}\n\n"
        "[taxonomies]\n"
        f"categories = {categories}\n"
        f"tags = {tags}\n\n"
        "[extra]\n"
        f"{extra_block}\n\n"
        f"{faq_block}"
        "+++\n"
    )

    # ---- body ----
    next_part = part + 1
    next_cta = (
        f"Đọc tiếp [Phần {next_part}](/zola/posting/{series_slugs[next_part-1]}/) của series."
        if next_part <= total and next_part - 1 < len(series_slugs)
        else f"Khám phá thêm tại [trang chuyên mục]({hub_url})."
    )

    intro = (
        f"**{topic}** là trọng tâm của bài này (phần {part}/{total} trong series). "
        f"{brief_txt} Trong 150 từ đầu, bạn sẽ nắm được {topic} là gì, vì sao nó quan trọng "
        f"và cách bắt đầu. Tham khảo thêm tại {links_md}."
    )

    ux_note = (
        f"\n\n> 🎨 **Định hướng trình bày:** {ux_txt}\n" if ux_txt else ""
    )

    body = f"""<!-- AUTO-GENERATED bởi Content Creator (series {series_id}, phần {part}/{total}).
     Brief: {brief_txt[:200]} -->

{intro}

<!-- more -->
{ux_note}
## {topic} là gì? {{#dinh-nghia}}

{topic} là khái niệm nền tảng mà bài viết này muốn làm rõ. Thay vì định nghĩa hàn lâm,
chúng ta tiếp cận theo hướng thực hành: bạn cần hiểu **bản chất**, **bối cảnh áp dụng**
và **kết quả mong đợi**. {brief_txt}

## Vì sao {topic} quan trọng? {{#tai-sao-quan-trong}}

- Giúp bạn ra quyết định nhanh và đúng hơn.
- Tiết kiệm thời gian nhờ quy trình rõ ràng.
- Tránh các sai lầm phổ biến mà người mới hay mắc.

Theo các nguồn tham khảo uy tín ([tra cứu thêm]({ext})), nắm vững nền tảng luôn là bước
đi bền vững nhất.

## Các bước thực hiện {{#cac-buoc}}

1. **Xác định mục tiêu** rõ ràng cho {topic}.
2. **Chuẩn bị** công cụ và tài nguyên cần thiết.
3. **Triển khai** theo từng bước nhỏ, đo lường kết quả.
4. **Tối ưu** dựa trên dữ liệu thực tế.

## Sai lầm thường gặp {{#sai-lam}}

| Sai lầm | Hậu quả | Cách khắc phục |
|---|---|---|
| Bỏ qua bước chuẩn bị | Mất thời gian làm lại | Lập checklist trước khi bắt đầu |
| Làm quá nhiều cùng lúc | Khó đo lường | Chia nhỏ, ưu tiên việc quan trọng |
| Không theo dõi kết quả | Không biết cải thiện | Ghi lại số liệu định kỳ |

## Công cụ & tài nguyên {{#cong-cu}}

Bạn có thể bắt đầu với các công cụ miễn phí, sau đó nâng cấp khi cần. Đừng quên xem
{links_md} để có cái nhìn đầy đủ về series.

## Kết luận & bước tiếp theo {{#ket-luan}}

{topic} không khó nếu bạn đi theo quy trình rõ ràng và kiên trì áp dụng. Hãy bắt đầu
ngay hôm nay với checklist phía trên.

👉 **Bước tiếp theo:** {next_cta}
"""

    return slug, fm + "\n" + body


def main() -> int:
    ap = argparse.ArgumentParser(description="Sinh series bài viết từ brief Content Creator.")
    ap.add_argument("--topic", required=True)
    ap.add_argument("--count", type=int, default=3)
    ap.add_argument("--pricing", choices=["free", "paid"], default="free")
    ap.add_argument("--brief", default="")
    ap.add_argument("--ux", default="")
    ap.add_argument("--series-id", default="")
    ap.add_argument("--job-file", default="", help="JSON brief (ghi đè các flag nếu có).")
    args = ap.parse_args()

    topic = args.topic
    count = args.count
    pricing = args.pricing
    brief = args.brief
    ux = args.ux
    series_id = args.series_id

    if args.job_file:
        job = json.loads(Path(args.job_file).read_text(encoding="utf-8"))
        topic = job.get("topic", topic)
        count = int(job.get("count", count))
        pricing = job.get("pricing", pricing)
        brief = job.get("brief", brief)
        ux = job.get("ux_brief", job.get("ux", ux))
        series_id = job.get("series_id", series_id)

    count = max(1, min(30, count))
    if not series_id:
        series_id = slugify(topic) + "-series"
    today = date.today().isoformat()

    POSTING.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)

    # Pre-compute slugs để cross-link trong series.
    slugs = [
        (slugify(f"{topic}-phan-{p}") if count > 1 else slugify(topic))
        for p in range(1, count + 1)
    ]

    written: list[dict] = []
    for part in range(1, count + 1):
        slug, text = build_article(
            topic=topic, part=part, total=count, pricing=pricing,
            brief=brief, ux=ux, series_id=series_id, series_slugs=slugs, today=today,
        )
        path = POSTING / f"{slug}.md"
        path.write_text(text, encoding="utf-8")
        written.append({"part": part, "slug": slug, "title": f"{topic} — Phần {part}" if count > 1 else topic, "status": "published"})
        print(f"PUBLISHED:{path.relative_to(ROOT)}")

    # series manifest
    manifest = {
        "id": series_id,
        "title": topic,
        "title_vi": topic,
        "description": (brief.strip() or topic)[:300],
        "section": "posting",
        "category": "premium" if pricing == "paid" else "Tất cả",
        "pricing": pricing,
        "ux_brief": ux.strip(),
        "total_parts": count,
        "parts": written,
    }
    manifest_path = DATA / f"{series_id}-series.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PUBLISHED:{manifest_path.relative_to(ROOT)}")

    print(f"DONE: {count} bài, series={series_id}, pricing={pricing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
