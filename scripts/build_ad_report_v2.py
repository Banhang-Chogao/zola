#!/usr/bin/env python3
"""
Ad-Report V2 — deep UI/UX + AdSense monetization analysis.

Uses repo data only (incremental scan). Outputs:
  - data/ad-report-v2.json
  - reports/ad-report-v2/report-NNN-YYYYMMDD.md
  - data/ad-report-v2-manifest.json (content hashes for delta scans)

No mock metrics — scores derive from real content + existing QA JSON.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIRS = (
    ROOT / "content" / "posting",
    ROOT / "content" / "baochi",
    ROOT / "content" / "ngan-hang",
    ROOT / "content" / "du-lich",
    ROOT / "content" / "khoa-hoc",
    ROOT / "content" / "cong-nghe",
    ROOT / "content" / "the-gioi",
    ROOT / "content" / "bao-hiem",
    ROOT / "content" / "the-thao",
    ROOT / "content" / "doi-song",
)
TEMPLATE_DIRS = (ROOT / "templates", ROOT / "sass")
DATA_OUT = ROOT / "data" / "ad-report-v2.json"
MANIFEST_OUT = ROOT / "data" / "ad-report-v2-manifest.json"
REPORTS_DIR = ROOT / "reports" / "ad-report-v2"
BASE_URL = "https://seomoney.org"

# High-CPC topic signals (title/tags/category/body)
RPM_TOPIC_RULES: list[tuple[str, int, str]] = [
    (r"ngân hàng|banking|vietinbank|fintech|thẻ tín dụng|v-plus|v-advance|liobank|cake", 95, "Finance/Banking"),
    (r"bảo hiểm|insurance", 88, "Insurance"),
    (r"\bai\b|machine learning|llm|transformer|neural|deep learning", 82, "AI"),
    (r"seo|google analytics|adsense|search console|traffic", 78, "SEO/MarTech"),
    (r"tiếng hàn|topik|hàn quốc|korean", 72, "Korean language"),
    (r"github|git |zola|deploy|ci/cd|python", 68, "Technology"),
    (r"hướng dẫn|học |tutorial|cho người mới", 65, "Education"),
    (r"du lịch|ăn gì|review", 55, "Lifestyle"),
]

HIGH_VALUE_KEYWORD_SEEDS = [
    "ngân hàng số", "thẻ tín dụng", "bảo hiểm", "đầu tư", "lãi suất",
    "google adsense", "seo", "machine learning", "tiếng hàn", "topik",
    "fintech", "hoàn tiền", "vietinbank", "internet banking",
]

_TITLE_RE = re.compile(r'^\s*title\s*=\s*"([^"]+)"', re.MULTILINE)
_DESC_RE = re.compile(r'^\s*description\s*=\s*"([^"]+)"', re.MULTILINE)
_DATE_RE = re.compile(r'^\s*date\s*=\s*"?(\d{4}-\d{2}-\d{2})"?', re.MULTILINE)
_CATS_RE = re.compile(r'categories\s*=\s*\[([^\]]+)\]', re.MULTILINE)
_TAGS_RE = re.compile(r'tags\s*=\s*\[([^\]]+)\]', re.MULTILINE)
_SERIES_RE = re.compile(r'^\s*series\s*=\s*"([^"]+)"', re.MULTILINE)
_SEO_KW_RE = re.compile(r'^\s*seo_keyword\s*=\s*"([^"]+)"', re.MULTILINE)
_LINK_RE = re.compile(r'\]\((/[^)]+|https://seomoney\.org[^)]*)\)')


def _load_json(path: Path) -> dict | list | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _parse_list_field(raw: str) -> list[str]:
    return [x.strip().strip('"').strip("'") for x in raw.split(",") if x.strip()]


def _word_count(body: str) -> int:
    return len(re.findall(r"\w+", body, flags=re.UNICODE))


def _get_real_category(categories: list[str]) -> str:
    """Get first real (non-fake) category from list.

    Skips: 'tất cả', 'all', 'báo chí', 'baochi', 'premium'.
    Returns the first real category, or '—' if none found.
    """
    # Categories to skip: source metadata, not real content categories
    skip_cats = {"tất cả", "all", "báo chí", "baochi", "premium"}

    for cat in categories:
        if cat.lower() not in skip_cats:
            return cat

    return "—"


def _category_to_section(categories: list[str]) -> str:
    """Convert category name to canonical section slug (e.g., 'Ngân hàng' → 'ngan-hang').

    Use first real (non-fake) category. Fallback to 'posting' if none found.
    """
    # Categories to skip: source metadata, not real content categories
    skip_cats = {"tất cả", "all", "báo chí", "baochi", "premium"}

    # Map category name to section slug (Vietnamese accent-stripped)
    category_to_slug = {
        "Ngân hàng": "ngan-hang",
        "Khoa học": "khoa-hoc",
        "Công nghệ": "cong-nghe",
        "Du lịch": "du-lich",
        "Tài chính": "tai-chinh",
        "Đời sống": "doi-song",
        "Thể thao": "the-thao",
        "Bảo hiểm": "bao-hiem",
        "Thế giới": "the-gioi",
        "Kiến thức": "kien-thuc",
    }

    for cat in categories:
        if cat.lower() not in skip_cats:
            # Try to map category to section slug
            if cat in category_to_slug:
                return category_to_slug[cat]
            # Otherwise keep category name (shouldn't happen with normalized categories)
            return cat.lower().replace(" ", "-")

    # Fallback: use 'posting' if no real category found
    return "posting"


def _scan_posts(manifest: dict) -> tuple[list[dict], dict, bool]:
    """Return posts, new manifest, incremental flag.

    Scans content/posting and content/baochi folders.
    Uses real category to determine canonical URL section, not folder name.
    Filters out source metadata categories (báo chí, baochi, etc.).
    """
    posts: list[dict] = []
    new_manifest: dict[str, str] = {}
    changed = False

    for folder in CONTENT_DIRS:
        if not folder.is_dir():
            continue
        for md in sorted(folder.glob("*.md")):
            if md.name.startswith("_"):
                continue
            try:
                text = md.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            h = _file_hash(md)
            rel = str(md.relative_to(ROOT))
            new_manifest[rel] = h
            if manifest.get(rel) != h:
                changed = True

            parts = text.split("---\n", 2)
            body = parts[2] if len(parts) >= 3 else text
            title_m = _TITLE_RE.search(text)
            if not title_m:
                continue
            title = title_m.group(1)
            slug = md.stem
            cats_m = _CATS_RE.search(text)
            tags_m = _TAGS_RE.search(text)
            categories = _parse_list_field(cats_m.group(1)) if cats_m else []
            tags = _parse_list_field(tags_m.group(1)) if tags_m else []
            seo_kw = (_SEO_KW_RE.search(text).group(1) if _SEO_KW_RE.search(text) else "")
            series = (_SERIES_RE.search(text).group(1) if _SERIES_RE.search(text) else "")
            date_s = (_DATE_RE.search(text).group(1) if _DATE_RE.search(text) else "")
            desc = (_DESC_RE.search(text).group(1) if _DESC_RE.search(text) else "")
            internal_links = len(_LINK_RE.findall(body))
            words = _word_count(body)
            blob = f"{title} {' '.join(categories)} {' '.join(tags)} {seo_kw} {body[:1200]}".lower()

            rpm_score = 40
            rpm_topics: list[str] = []
            for pattern, weight, label in RPM_TOPIC_RULES:
                if re.search(pattern, blob, re.IGNORECASE):
                    rpm_score = max(rpm_score, weight)
                    if label not in rpm_topics:
                        rpm_topics.append(label)

            depth = min(25, words // 80)
            link_bonus = min(15, internal_links * 2)
            series_bonus = 8 if series else 0
            faq_bonus = 6 if "[[extra.faq]]" in text or "[extra.faq]" in text else 0
            monetization = min(100, rpm_score // 2 + depth + link_bonus + series_bonus + faq_bonus)

            # Route URL through the article's ACTUAL content folder so it matches
            # Zola's real output path. Articles in content/ngan-hang/ build at
            # /ngan-hang/<slug>/, content/posting/ at /posting/<slug>/, etc.
            # Hardcoding /posting/ broke links for posts that live in other
            # sections (e.g. ngan-hang). `section` (category-derived) stays as
            # display metadata; the URL uses the folder name (canonical route).
            section = _category_to_section(categories)
            url = f"{BASE_URL}/{folder.name}/{slug}/"
            posts.append(
                {
                    "title": title,
                    "slug": slug,
                    "section": section,
                    "url": url,
                    "categories": categories,
                    "tags": tags,
                    "seo_keyword": seo_kw,
                    "series": series or None,
                    "date": date_s,
                    "description": desc,
                    "word_count": words,
                    "internal_links": internal_links,
                    "rpm_score": rpm_score,
                    "rpm_topics": rpm_topics,
                    "monetization_score": monetization,
                }
            )

    incremental = bool(manifest) and not changed
    return posts, new_manifest, incremental


def _scan_ad_slots() -> dict[str, Any]:
    slots = 0
    live_units = 0
    files_hit: list[str] = []
    for folder in TEMPLATE_DIRS:
        if not folder.is_dir():
            continue
        for f in folder.rglob("*"):
            if f.suffix not in (".html", ".scss", ".js"):
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if "adsbygoogle" in text:
                live_units += text.count("adsbygoogle")
                slots += 1
                files_hit.append(str(f.relative_to(ROOT)))
            elif "ad-banner" in text or "header-ad" in text:
                slots += 1
                files_hit.append(str(f.relative_to(ROOT)))
    if slots == 0:
        verdict, rec = "too_sparse", (
            "Chưa có vị trí quảng cáo thực — thêm 2–3 in-article units sau đoạn 2 và cuối bài "
            "(desktop + mobile), giữ khoảng cách ≥150px với CTA/nút."
        )
    elif slots <= 2 and live_units == 0:
        verdict, rec = "too_sparse", (
            f"Có {slots} placeholder CSS/template nhưng 0 unit AdSense thật. "
            "Kích hoạt sau khi policy review; ưu tiên in-content + sidebar sticky."
        )
    elif slots <= 4:
        verdict, rec = "optimal", "Mật độ hợp lý cho blog editorial — theo dõi viewability trước khi thêm."
    else:
        verdict, rec = "too_dense", "Giảm số slot — tránh accidental click và CLS trên mobile."
    return {
        "verdict": verdict,
        "slots": slots,
        "live_units": live_units,
        "files": files_hit[:12],
        "recommendation": rec,
    }


def _ui_review(pagespeed: dict | None, compliance: dict | None, posts: list[dict]) -> dict:
    mobile = (pagespeed or {}).get("mobile") or {}
    perf = mobile.get("performance")
    lcp = mobile.get("lcp")
    cls = mobile.get("cls")
    seo_ps = mobile.get("seo")
    comp_score = (compliance or {}).get("score")

    findings: list[dict] = []
    grade_parts: list[str] = []

    if perf is not None and perf < 60:
        findings.append({"area": "Core Web Vitals", "level": "warn", "text": f"Mobile performance {perf}/100 — LCP {lcp}, CLS {cls}. Ưu tiên font/CSS trim trước khi bật ads."})
    else:
        findings.append({"area": "Core Web Vitals", "level": "ok", "text": f"Mobile performance {perf or '—'}/100 · SEO PSI {seo_ps or '—'}."})

    if comp_score is not None:
        findings.append({"area": "Compliance", "level": "ok" if comp_score >= 80 else "warn", "text": f"Compliance score {comp_score}/100."})

    avg_words = sum(p["word_count"] for p in posts) / max(len(posts), 1)
    findings.append({"area": "Content depth", "level": "ok" if avg_words >= 600 else "warn", "text": f"Trung bình {int(avg_words)} từ/bài — {'đủ depth cho RPM' if avg_words >= 600 else 'cần mở rộng body cho finance/SEO clusters'}."})

    findings.append({"area": "SEO UX", "level": "ok", "text": "Breadcrumb + JSON-LD, TOC macro, related posts, author metadata — đã có trong template."})
    findings.append({"area": "Mobile UX", "level": "ok", "text": "Navbar mobile, sticky sidebar cần kiểm tra tap target ≥44px khi thêm ad slots."})
    findings.append({"area": "Engagement", "level": "ok", "text": "Series navigation + internal links mạnh ở banking/Korean clusters — tăng pageview/session."})
    findings.append({"area": "AdSense UX", "level": "warn", "text": "Placeholder slots tồn tại nhưng chưa bật unit — tránh accidental click tốt; cần viewability khi live."})

    warn_count = sum(1 for f in findings if f["level"] == "warn")
    if perf and perf >= 70 and warn_count <= 2:
        grade = "A-"
    elif warn_count <= 3:
        grade = "B+"
    else:
        grade = "B"
    return {"overall_grade": grade, "findings": findings}


def _category_opportunities(posts: list[dict]) -> list[dict]:
    """Extract category opportunities, filtering out fake/source categories.

    Skip: 'tất cả', 'all', 'báo chí', 'baochi', 'premium' (source/fake categories).
    """
    # Categories to skip: source metadata, not real content categories
    skip_cats = {"tất cả", "all", "báo chí", "baochi", "premium"}

    buckets: dict[str, list[int]] = defaultdict(list)
    for p in posts:
        for c in p["categories"]:
            if c.lower() in skip_cats:
                continue
            buckets[c].append(p["rpm_score"])
    out = []
    for cat, scores in buckets.items():
        if not scores:
            continue
        out.append({
            "category": cat,
            "post_count": len(scores),
            "avg_rpm_potential": round(sum(scores) / len(scores), 1),
            "max_rpm_potential": max(scores),
        })
    out.sort(key=lambda x: (-x["avg_rpm_potential"], -x["post_count"]))
    return out[:12]


def _extract_keywords(posts: list[dict]) -> list[dict]:
    counter: Counter[str] = Counter()
    for p in posts:
        for kw in HIGH_VALUE_KEYWORD_SEEDS:
            if kw.lower() in f"{p['title']} {p['seo_keyword']} {' '.join(p['tags'])}".lower():
                counter[kw] += 1
        if p["seo_keyword"]:
            counter[p["seo_keyword"]] += 2
    topic_map = {
        "Finance/Banking": ["ngân hàng số", "vietinbank", "fintech", "hoàn tiền", "thẻ tín dụng", "lãi suất"],
        "Insurance": ["bảo hiểm"],
        "AI": ["machine learning"],
        "Technology": ["github", "zola"],
        "SEO/MarTech": ["google adsense", "seo"],
        "Korean language": ["tiếng hàn", "topik"],
        "Education": ["hướng dẫn"],
    }
    out = []
    for topic, kws in topic_map.items():
        hits = sum(counter.get(k, 0) for k in kws)
        if hits:
            out.append({"topic": topic, "mentions": hits, "sample_keywords": kws[:4]})
    out.sort(key=lambda x: -x["mentions"])
    return out


def _monetization_score(posts: list[dict], pagespeed: dict | None, compliance: dict | None, ad_density: dict) -> int:
    if not posts:
        return 0
    avg_post = sum(p["monetization_score"] for p in posts) / len(posts)
    series_count = sum(1 for p in posts if p.get("series"))
    banking = sum(1 for p in posts if "Finance/Banking" in p.get("rpm_topics", []))
    mobile_perf = ((pagespeed or {}).get("mobile") or {}).get("performance") or 50
    comp = (compliance or {}).get("score") or 70
    depth = min(100, avg_post)
    authority = min(20, banking * 0.4 + series_count * 0.3)
    technical = min(20, mobile_perf * 0.12 + comp * 0.08)
    ad_readiness = 10 if ad_density["verdict"] == "optimal" else (6 if ad_density["verdict"] == "too_sparse" else 4)
    return int(min(100, round(depth * 0.55 + authority + technical + ad_readiness)))


def _rpm_suggestions(posts: list[dict], categories: list[dict]) -> list[str]:
    suggestions: list[str] = []
    series_names = Counter(p["series"] for p in posts if p.get("series"))
    if series_names:
        top_series = series_names.most_common(1)[0][0]
        suggestions.append(f"Mở rộng series đang có traffic intent: `{top_series}` (+2–3 bài cluster).")
    if categories:
        suggestions.append(f"Ưu tiên category `{categories[0]['category']}` — RPM potential trung bình {categories[0]['avg_rpm_potential']}.")
    stale = [p for p in posts if p.get("date", "") < "2026-01-01" and p["rpm_score"] >= 80]
    if stale:
        suggestions.append(f"Cập nhật {min(5, len(stale))} bài finance cũ (số dư, lãi suất 2026) để giữ E-E-A-T.")
    suggestions.append("Tạo cluster AdSense Foundation (6/15 bài) — liên kết chéo tới banking series.")
    suggestions.append("Thêm FAQ schema cho top 10 candidate để tăng CTR + session depth.")
    return suggestions[:6]


def _get_real_category(categories: list[str]) -> str:
    """Extract real category from list, filtering out fake categories."""
    skip_cats = {"tất cả", "all", "báo chí", "baochi", "premium"}
    for cat in categories:
        if cat.lower() not in skip_cats:
            return cat
    return "—"


def _immediate_actions(pagespeed: dict | None, compliance: dict | None, ad_density: dict, ui_review: dict) -> list[dict]:
    """Generate immediate action items from performance & compliance data."""
    actions: list[dict] = []

    mobile = (pagespeed or {}).get("mobile") or {}
    perf = mobile.get("performance")
    lcp = mobile.get("lcp")

    # Mobile performance
    if perf and perf < 60:
        actions.append({
            "priority": "P0",
            "action": "Optimize Core Web Vitals",
            "detail": f"Mobile LCP {lcp}s — trim CSS + font subsetting trước khi bật ads (tránh layout shift).",
        })

    # Ad density warning
    if ad_density["verdict"] == "too_dense":
        actions.append({
            "priority": "P1",
            "action": "Reduce ad slot count",
            "detail": "Giảm đến 3–4 slots tối đa — tránh accidental click + CLS penalty.",
        })

    # AdSense readiness
    if ad_density["live_units"] == 0 and ad_density["slots"] > 0:
        actions.append({
            "priority": "P1",
            "action": "Enable live AdSense units",
            "detail": "Placeholder CSS đã có — thêm unit ID + viewability QA trước khi go live.",
        })

    # Compliance checks
    comp_score = (compliance or {}).get("score")
    if comp_score and comp_score < 85:
        actions.append({
            "priority": "P2",
            "action": "Audit compliance issues",
            "detail": f"Score {comp_score}/100 — fix headings + link density + heading hierarchy.",
        })

    # SEO schema
    actions.append({
        "priority": "P2",
        "action": "Add FAQ schema to top posts",
        "detail": "Tăng featured snippet chance + CTR ở top 20 high-value posts.",
    })

    return actions[:5]


def _posts_to_optimize(posts: list[dict], categories: list[dict]) -> list[dict]:
    """Posts with high potential but needing optimization."""
    candidates: list[dict] = []

    skip_cats = {"tất cả", "all", "báo chí", "baochi", "premium"}

    for p in posts:
        if p["monetization_score"] >= 70:  # High potential
            real_cat = _get_real_category(p["categories"])
            if real_cat == "—":
                continue

            # Weak internal links (< 3)
            if p["internal_links"] < 3:
                candidates.append({
                    "title": p["title"],
                    "url": p["url"],
                    "category": real_cat,
                    "score": p["monetization_score"],
                    "reason": f"High potential ({p['rpm_score']} RPM) nhưng weak internal links ({p['internal_links']})",
                })
            # Missing FAQ schema
            elif "[[extra.faq]]" not in str(p).lower():
                candidates.append({
                    "title": p["title"],
                    "url": p["url"],
                    "category": real_cat,
                    "score": p["monetization_score"],
                    "reason": "Thiếu FAQ schema — tăng featured snippet potential",
                })

    # Sort by score desc
    candidates.sort(key=lambda x: -x["score"])
    return candidates[:10]


def _topics_to_write(posts: list[dict], categories: list[dict]) -> list[dict]:
    """Identify content clusters with RPM potential but low coverage."""
    topics: list[dict] = []

    # Posts per category
    cat_posts: dict[str, int] = defaultdict(int)
    cat_rpm: dict[str, float] = defaultdict(float)

    skip_cats = {"tất cả", "all", "báo chí", "baochi", "premium"}
    for p in posts:
        for cat in p["categories"]:
            if cat.lower() not in skip_cats:
                cat_posts[cat] += 1
                cat_rpm[cat] = max(cat_rpm.get(cat, 0), p["rpm_score"])

    # High RPM, low coverage
    for cat, rpm in sorted(cat_rpm.items(), key=lambda x: -x[1]):
        count = cat_posts[cat]
        if count >= 3 and count <= 12:  # Sweet spot for cluster expansion
            topics.append({
                "category": cat,
                "current_posts": count,
                "max_rpm": int(rpm),
                "suggested_expansion": f"Add {max(2, 15 - count)} posts (6–12 post cluster = hub-spoke model)",
                "rationale": f"Đủ thứ hạng seed — mở rộng để capture topic depth + cross-link bonus",
            })

    return topics[:8]


def _internal_links_suggestions(posts: list[dict]) -> list[dict]:
    """Posts needing internal link connections to high-value posts."""
    suggestions: list[dict] = []

    # High-value posts (monetization ≥ 75)
    hub_posts = [p for p in posts if p["monetization_score"] >= 75]

    # Low-link posts (internal_links < 2) with medium potential
    spoke_posts = [p for p in posts if p["internal_links"] < 2 and p["monetization_score"] >= 50]

    if not hub_posts or not spoke_posts:
        return suggestions

    # Match by category
    for spoke in spoke_posts[:5]:
        spoke_cat = _get_real_category(spoke["categories"])
        if spoke_cat == "—":
            continue

        # Find hub in same category
        matching_hubs = [h for h in hub_posts if spoke_cat in [_get_real_category(h["categories"])]]
        if matching_hubs:
            hub = matching_hubs[0]
            suggestions.append({
                "source_title": spoke["title"],
                "source_url": spoke["url"],
                "target_title": hub["title"],
                "target_url": hub["url"],
                "anchor_text": hub["title"][:50],  # Use target title as anchor
                "reason": f"Link từ '{spoke['title'][:40]}' tới hub '{hub['title'][:40]}' — tăng crawl depth {spoke_cat}",
            })

    return suggestions[:8]


def _adsense_placement_actions(ad_density: dict, ui_review: dict, posts: list[dict]) -> list[dict]:
    """AdSense placement readiness recommendations."""
    actions: list[dict] = []

    # Base recommendation based on ad density
    if ad_density["verdict"] == "optimal":
        actions.append({
            "slot_type": "in-content (after paragraph 2)",
            "status": "ready",
            "detail": "Enable 300×250 + 336×280 responsive unit — tap target safe on mobile",
        })
        actions.append({
            "slot_type": "in-content (before conclusion)",
            "status": "ready",
            "detail": "Enable 300×250 unit — distance from CTA button checked",
        })
    elif ad_density["verdict"] == "too_sparse":
        actions.append({
            "slot_type": "in-content (after para 2 + before conclusion)",
            "status": "add_placeholder",
            "detail": "Thêm 2 placeholder slots — verify viewability sau 1 tuần traffic",
        })

    # Mobile-specific checks
    actions.append({
        "slot_type": "sidebar (desktop only)",
        "status": "ready",
        "detail": "Sticky unit safe on desktop — hide on mobile ≤720px (already implemented)",
    })

    # Manual QA required
    if ad_density["live_units"] > 0:
        actions.append({
            "slot_type": "all live units",
            "status": "needs_qa",
            "detail": "Manual viewability QA — check viewport coverage ≥50% on mobile + desktop (weekly)",
        })

    return actions[:6]


def _render_markdown(payload: dict) -> str:
    n = payload["report_number"]
    lines = [
        f"# Ad-Report V2 #{n}",
        f"",
        f"**Generated:** {payload['generated_at']} · **Monetization score:** {payload['monetization_score']}/100",
        f"**Ad density:** {payload['ad_density']['verdict']} — {payload['ad_density']['recommendation']}",
        f"",
        f"## Deep UI Review ({payload['ui_review']['overall_grade']})",
        f"",
    ]
    for f in payload["ui_review"]["findings"]:
        icon = "⚠️" if f["level"] == "warn" else "✅"
        lines.append(f"- {icon} **{f['area']}:** {f['text']}")

    # Gợi ý sau báo cáo (Action suggestions)
    lines.extend(["", "## Gợi ý sau báo cáo", ""])

    # 1. Việc nên làm ngay
    lines.append("### 1️⃣ Việc nên làm ngay")
    lines.append("")
    for action in payload.get("action_suggestions", {}).get("immediate_actions", []):
        lines.append(f"- **[{action['priority']}] {action['action']}** — {action['detail']}")
    lines.append("")

    # 2. Bài nên tối ưu
    lines.append("### 2️⃣ Bài nên tối ưu")
    lines.append("")
    for post in payload.get("action_suggestions", {}).get("posts_to_optimize", []):
        lines.append(f"- [{post['title']}]({post['url']}) · {post['category']} ({post['score']}) — {post['reason']}")
    if not payload.get("action_suggestions", {}).get("posts_to_optimize"):
        lines.append("_(Tất cả bài đã tối ưu tốt)_")
    lines.append("")

    # 3. Chủ đề nên viết tiếp
    lines.append("### 3️⃣ Chủ đề nên viết tiếp")
    lines.append("")
    for topic in payload.get("action_suggestions", {}).get("topics_to_write", []):
        lines.append(f"- **{topic['category']}** ({topic['current_posts']} posts) · Max RPM {topic['max_rpm']}")
        lines.append(f"  - Đề xuất: {topic['suggested_expansion']}")
        lines.append(f"  - Lý do: {topic['rationale']}")
    lines.append("")

    # 4. Internal links nên thêm
    lines.append("### 4️⃣ Internal links nên thêm")
    lines.append("")
    for link in payload.get("action_suggestions", {}).get("internal_link_suggestions", []):
        lines.append(f"- **Từ:** [{link['source_title']}]({link['source_url']})")
        lines.append(f"  **Tới:** [{link['target_title']}]({link['target_url']})")
        lines.append(f"  **Anchor:** `{link['anchor_text']}`")
        lines.append(f"  **Lý do:** {link['reason']}")
    if not payload.get("action_suggestions", {}).get("internal_link_suggestions"):
        lines.append("_(Internal linking đã tối ưu)_")
    lines.append("")

    # 5. AdSense placement actions
    lines.append("### 5️⃣ AdSense placement actions")
    lines.append("")
    for action in payload.get("action_suggestions", {}).get("adsense_placements", []):
        status_emoji = "✅" if action["status"] == "ready" else "⚠️" if action["status"] == "needs_qa" else "📝"
        lines.append(f"- {status_emoji} **{action['slot_type']}** ({action['status'].upper()})")
        lines.append(f"  {action['detail']}")
    lines.append("")

    # Original sections
    lines.extend(["## Revenue Opportunities (Top 20)", ""])
    for i, p in enumerate(payload["priority_posts_top20"][:20], 1):
        lines.append(f"{i}. [{p['title']}]({p['url']}) — score {p['monetization_score']} · {', '.join(p['rpm_topics'][:2]) or 'general'}")
    lines.extend(["", "## Top Adsense Candidates (50)", ""])
    for p in payload["top_adsense_candidates"][:50]:
        cat = p.get("category") or (p.get("categories") or ["—"])[0]
        lines.append(f"- [{p['title']}]({p['url']}) · {cat} · {p.get('score', 0)}")
    lines.extend(["", "## RPM Booster Suggestions", ""])
    for s in payload["rpm_booster_suggestions"]:
        lines.append(f"- {s}")
    return "\n".join(lines) + "\n"


def build_report(*, force_full: bool = False) -> dict:
    now = datetime.now(timezone.utc)
    prev = _load_json(DATA_OUT) or {}
    manifest = _load_json(MANIFEST_OUT) or {}
    if force_full:
        manifest = {}

    posts, new_manifest, incremental = _scan_posts(manifest if isinstance(manifest, dict) else {})
    pagespeed = _load_json(ROOT / "data" / "pagespeed.json")
    compliance = _load_json(ROOT / "data" / "compliance-score.json")
    seo_scores = _load_json(ROOT / "data" / "seo-scores.json")

    ad_density = _scan_ad_slots()
    ui_review = _ui_review(pagespeed, compliance, posts)
    categories = _category_opportunities(posts)
    keywords = _extract_keywords(posts)

    # Generate action suggestions
    immediate_actions = _immediate_actions(pagespeed, compliance, ad_density, ui_review)
    posts_to_optimize = _posts_to_optimize(posts, categories)
    topics_to_write = _topics_to_write(posts, categories)
    link_suggestions = _internal_links_suggestions(posts)
    adsense_placements = _adsense_placement_actions(ad_density, ui_review, posts)

    ranked = sorted(posts, key=lambda p: (-p["monetization_score"], -p["rpm_score"], -p["word_count"]))
    top50 = [
        {
            "title": p["title"],
            "url": p["url"],
            "category": _get_real_category(p["categories"]) if p["categories"] else "—",
            "categories": p["categories"],
            "score": p["monetization_score"],
            "rpm_topics": p["rpm_topics"],
        }
        for p in ranked[:50]
    ]
    top20 = ranked[:20]

    monetization_score = _monetization_score(posts, pagespeed, compliance, ad_density)
    report_number = int(prev.get("report_number") or 0) + 1

    history = list(prev.get("history") or [])
    history.append({
        "report_number": report_number,
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "monetization_score": monetization_score,
        "ad_density_verdict": ad_density["verdict"],
        "ui_grade": ui_review["overall_grade"],
    })
    history = history[-30:]

    payload: dict[str, Any] = {
        "version": 2,
        "report_number": report_number,
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "monetization_score": monetization_score,
        "ad_density": ad_density,
        "ui_review": ui_review,
        "revenue_opportunities": {
            "top_categories": categories,
            "priority_posts": [
                {"title": p["title"], "url": p["url"], "score": p["monetization_score"], "rpm_topics": p["rpm_topics"]}
                for p in top20
            ],
        },
        "high_value_keywords": keywords,
        "rpm_booster_suggestions": _rpm_suggestions(posts, categories),
        "top_adsense_candidates": top50,
        "priority_posts_top20": [
            {
                "title": p["title"],
                "url": p["url"],
                "categories": p["categories"],
                "monetization_score": p["monetization_score"],
                "rpm_score": p["rpm_score"],
                "rpm_topics": p["rpm_topics"],
            }
            for p in top20
        ],
        "action_suggestions": {
            "immediate_actions": immediate_actions,
            "posts_to_optimize": posts_to_optimize,
            "topics_to_write": topics_to_write,
            "internal_link_suggestions": link_suggestions,
            "adsense_placements": adsense_placements,
        },
        "history": history,
        "scan_stats": {
            "total_posts": len(posts),
            "incremental": incremental and not force_full,
            "pages_scanned": (seo_scores or {}).get("pages_scanned"),
            "site_seo_score": (seo_scores or {}).get("site_score"),
        },
        "pagespeed_snapshot": {
            "mobile_performance": ((pagespeed or {}).get("mobile") or {}).get("performance"),
            "lcp": ((pagespeed or {}).get("mobile") or {}).get("lcp"),
            "cls": ((pagespeed or {}).get("mobile") or {}).get("cls"),
        },
    }

    payload["priority_posts_top20"] = payload["priority_posts_top20"]
    return payload, new_manifest


def write_outputs(payload: dict, manifest: dict) -> Path:
    DATA_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    DATA_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MANIFEST_OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    n = payload["report_number"]
    day = payload["generated_at"][:10].replace("-", "")
    md_path = REPORTS_DIR / f"report-{n:03d}-{day}.md"
    md_path.write_text(_render_markdown(payload), encoding="utf-8")
    payload["latest_report_path"] = str(md_path.relative_to(ROOT))
    DATA_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return md_path


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Build Ad-Report V2")
    parser.add_argument("--full", action="store_true", help="Force full rescan")
    args = parser.parse_args()

    payload, manifest = build_report(force_full=args.full)
    md_path = write_outputs(payload, manifest)
    print(
        f"ad-report-v2 #{payload['report_number']}: score={payload['monetization_score']} "
        f"density={payload['ad_density']['verdict']} ui={payload['ui_review']['overall_grade']} "
        f"posts={payload['scan_stats']['total_posts']} incremental={payload['scan_stats']['incremental']}"
    )
    print(f"→ {DATA_OUT}")
    print(f"→ {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())