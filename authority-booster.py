#!/usr/bin/env python3
"""
Authority Booster Engine — trust score, topical authority, safe SEO PR patches.

Scans repo content + existing QA JSON. Outputs data/authority-report.json.
With --apply: conservative content fixes (internal links, refs, pillars, drafts).

Daily cron 06:00 GMT+7 via .github/workflows/authority-booster.yml → PR.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))

CONTENT_DIRS = (
    ROOT / "content" / "posting",
    ROOT / "content" / "baochi",
)
TOPIC_DIR = ROOT / "content" / "topic"
DATA_OUT = ROOT / "data" / "authority-report.json"
MANIFEST_OUT = ROOT / "data" / "authority-booster-manifest.json"
REPORTS_DIR = ROOT / "reports" / "authority-booster"
BASE_URL = "https://banhang-chogao.github.io/zola"

MAX_LINK_FIXES = 8
MAX_REF_FIXES = 5
MAX_FRESHNESS = 3
MAX_SERIES_DRAFTS = 1

PILLAR_TOPICS: dict[str, dict[str, Any]] = {
    "ngan-hang": {
        "title": "Ngân hàng & Fintech",
        "category_patterns": [r"ngân hàng", r"ngan-hang", r"bank", r"fintech"],
        "refs": [
            ("Ngân hàng Nhà nước Việt Nam", "https://www.sbv.gov.vn/"),
            ("VietinBank", "https://www.vietinbank.vn/"),
        ],
    },
    "bhxh": {
        "title": "BHXH & An sinh xã hội",
        "category_patterns": [r"bhxh", r"bảo hiểm", r"bao-hiem", r"bhyt"],
        "refs": [
            ("BHXH Việt Nam", "https://baohiemxahoi.gov.vn/"),
            ("Bộ Lao động – Thương binh và Xã hội", "https://molisa.gov.vn/"),
        ],
    },
    "tieng-han": {
        "title": "Tiếng Hàn",
        "category_patterns": [r"tiếng hàn", r"hoc-tieng-han", r"topik", r"hàn quốc"],
        "refs": [
            ("Từ điển Naver", "https://vi.dict.naver.com/"),
            ("TOPIK", "https://www.topik.go.kr/"),
        ],
    },
    "ai": {
        "title": "AI & Machine Learning",
        "category_patterns": [r"\bai\b", r"machine learning", r"llm", r"transformer"],
        "refs": [
            ("Google AI", "https://ai.google/"),
            ("Wikipedia — Artificial intelligence", "https://vi.wikipedia.org/wiki/Tr%C3%AD_tu%E1%BB%87_nh%C3%A2n_t%E1%BA%A1o"),
        ],
    },
    "cong-nghe": {
        "title": "Công nghệ & Dev",
        "category_patterns": [r"công nghệ", r"cong-nghe", r"github", r"zola", r"git"],
        "refs": [
            ("GitHub Docs", "https://docs.github.com/"),
            ("Zola Documentation", "https://www.getzola.org/documentation/"),
        ],
    },
    "khoa-hoc": {
        "title": "Khoa học",
        "category_patterns": [r"khoa học", r"khoa-hoc", r"uranium", r"vật lý"],
        "refs": [
            ("Wikipedia", "https://vi.wikipedia.org/"),
            ("IAEA", "https://www.iaea.org/"),
        ],
    },
}

TOPICAL_GAPS = [
    "BHXH thất nghiệp",
    "Hưu trí & lương hưu",
    "LPBank / LPBank số",
    "VietinBank iPay nâng cao",
    "Ngữ pháp tiếng Hàn nâng cao",
    "Prompt Engineering thực chiến",
    "Schema FAQ cho cluster ngân hàng",
    "Internal link orphan tiếng Hàn",
]

OFFICIAL_REF_POOL = [
    ("Wikipedia", "https://vi.wikipedia.org/"),
    ("Cổng thông tin Chính phủ", "https://chinhphu.vn/"),
    ("Bộ Lao động – TBXH", "https://molisa.gov.vn/"),
    ("BHXH Việt Nam", "https://baohiemxahoi.gov.vn/"),
    ("Ngân hàng Nhà nước", "https://www.sbv.gov.vn/"),
    ("Từ điển Naver", "https://vi.dict.naver.com/"),
]

_TITLE_RE = re.compile(r'^\s*title\s*=\s*"([^"]+)"', re.MULTILINE)
_DATE_RE = re.compile(r'^\s*date\s*=\s*"?(\d{4}-\d{2}-\d{2})"?', re.MULTILINE)
_EXTRA_REVISED_RE = re.compile(r'^\s*date_revised\s*=\s*"?(\d{4}-\d{2}-\d{2})"?', re.MULTILINE)
_CATS_RE = re.compile(r"categories\s*=\s*\[([^\]]+)\]", re.MULTILINE)
_TAGS_RE = re.compile(r"tags\s*=\s*\[([^\]]+)\]", re.MULTILINE)
_SERIES_RE = re.compile(r'^\s*series\s*=\s*"([^"]+)"', re.MULTILINE)
_LINK_RE = re.compile(r"\]\((/[^)#]+|https://[^)]+)\)")
_EXT_LINK_RE = re.compile(r"https?://[^\s)]+")


def _load_json(path: Path) -> Any:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _parse_list(raw: str) -> list[str]:
    return [x.strip().strip('"').strip("'") for x in raw.split(",") if x.strip()]


def _split_front_matter(text: str) -> tuple[str, str]:
    parts = text.split("---\n", 2)
    if len(parts) >= 3:
        return parts[1], parts[2]
    return "", text


def _word_count(body: str) -> int:
    return len(re.findall(r"\w+", body, flags=re.UNICODE))


def _internal_slugs(body: str) -> list[str]:
    slugs = []
    for url in _LINK_RE.findall(body):
        if "/posting/" in url or "/baochi/" in url:
            slug = url.rstrip("/").split("/")[-1]
            if slug:
                slugs.append(slug)
    return slugs


def scan_posts(manifest: dict) -> tuple[list[dict], dict[str, str], bool]:
    posts: list[dict] = []
    new_manifest: dict[str, str] = {}
    changed = False

    for folder in CONTENT_DIRS:
        if not folder.is_dir():
            continue
        for md in sorted(folder.glob("*.md")):
            if md.name.startswith("_"):
                continue
            text = md.read_text(encoding="utf-8", errors="ignore")
            rel = str(md.relative_to(ROOT))
            h = _file_hash(md)
            new_manifest[rel] = h
            if manifest.get(rel) != h:
                changed = True

            fm, body = _split_front_matter(text)
            title_m = _TITLE_RE.search(text)
            if not title_m:
                continue
            title = title_m.group(1)
            slug = md.stem
            section = folder.name
            cats = _parse_list(_CATS_RE.search(text).group(1)) if _CATS_RE.search(text) else []
            tags = _parse_list(_TAGS_RE.search(text).group(1)) if _TAGS_RE.search(text) else []
            series = (_SERIES_RE.search(text).group(1) if _SERIES_RE.search(text) else "") or None
            date_s = (_DATE_RE.search(text).group(1) if _DATE_RE.search(text) else "")
            revised_m = _EXTRA_REVISED_RE.search(fm)
            updated_s = (revised_m.group(1) if revised_m else "") or date_s
            words = _word_count(body)
            int_links = _internal_slugs(body)
            ext_count = len(_EXT_LINK_RE.findall(body))
            has_faq = "[[extra.faq]]" in fm or "[extra.faq]" in fm
            thin = words < 400
            blob = f"{title} {' '.join(cats)} {' '.join(tags)}".lower()

            topic_keys = []
            for key, cfg in PILLAR_TOPICS.items():
                for pat in cfg["category_patterns"]:
                    if re.search(pat, blob, re.I):
                        topic_keys.append(key)
                        break

            posts.append({
                "slug": slug,
                "title": title,
                "section": section,
                "path": rel,
                "url": f"{BASE_URL}/{section}/{slug}/",
                "categories": cats,
                "tags": tags,
                "series": series,
                "date": date_s,
                "updated": updated_s,
                "word_count": words,
                "internal_link_count": len(int_links),
                "internal_slugs": int_links,
                "external_link_count": ext_count,
                "has_faq": has_faq,
                "thin": thin,
                "topic_keys": topic_keys,
                "eeat_score": _eeat_item_score(has_faq, ext_count, len(int_links), cats, date_s),
            })

    incremental = bool(manifest) and not changed
    return posts, new_manifest, incremental


def _eeat_item_score(faq: bool, ext: int, internal: int, cats: list, date_s: str) -> int:
    s = 0
    if date_s:
        s += 20
    if cats:
        s += 20
    if internal >= 3:
        s += 25
    elif internal >= 1:
        s += 10
    if ext >= 1:
        s += 20
    if faq:
        s += 15
    return min(100, s)


def _category_authority(posts: list[dict]) -> list[dict]:
    buckets: dict[str, list[dict]] = defaultdict(list)
    for p in posts:
        for key in p["topic_keys"] or ["general"]:
            buckets[key].append(p)

    out = []
    for key, cfg in PILLAR_TOPICS.items():
        items = buckets.get(key, [])
        if not items:
            out.append({"category": cfg["title"], "slug": key, "coverage": 0, "score": 0.0})
            continue
        avg_eeat = sum(x["eeat_score"] for x in items) / len(items)
        avg_words = sum(x["word_count"] for x in items) / len(items)
        series_bonus = sum(1 for x in items if x["series"]) / len(items) * 10
        score = min(10.0, round((avg_eeat / 10 + min(avg_words / 300, 3) + series_bonus) / 1.2, 1))
        out.append({
            "category": cfg["title"],
            "slug": key,
            "coverage": len(items),
            "score": score,
        })
    out.sort(key=lambda x: (-x["score"], -x["coverage"]))
    return out


def _trust_score(posts: list[dict], orphans: list[str], audit: dict | None) -> dict:
    if not posts:
        return {"score": 0, "label": "New Site", "components": {}}
    n = len(posts)
    eeat_avg = sum(p["eeat_score"] for p in posts) / n
    link_ok = sum(1 for p in posts if p["internal_link_count"] >= 3) / n
    ext_ok = sum(1 for p in posts if p["external_link_count"] >= 1) / n
    thin_ratio = sum(1 for p in posts if p["thin"]) / n
    topic_breadth = len({k for p in posts for k in p["topic_keys"]}) / max(len(PILLAR_TOPICS), 1)
    orphan_penalty = min(15, len(orphans) * 0.5)
    now = datetime.now(timezone.utc)
    fresh = 0
    for p in posts:
        ds = p.get("updated") or p.get("date") or ""
        try:
            d = datetime.strptime(ds, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if (now - d).days <= 90:
                fresh += 1
        except ValueError:
            pass
    fresh_ratio = fresh / n

    raw = (
        eeat_avg * 0.35
        + link_ok * 25
        + ext_ok * 15
        + topic_breadth * 15
        + fresh_ratio * 10
        - thin_ratio * 12
        - orphan_penalty
    )
    score = int(max(0, min(100, round(raw))))

    if score >= 75:
        label = "Established Authority"
    elif score >= 58:
        label = "Growth Phase"
    elif score >= 40:
        label = "Discovery Phase"
    else:
        label = "Indexing Phase"

    return {
        "score": score,
        "label": label,
        "components": {
            "eeat_avg": round(eeat_avg, 1),
            "internal_link_coverage": round(link_ok * 100, 1),
            "external_ref_coverage": round(ext_ok * 100, 1),
            "topic_breadth": round(topic_breadth * 100, 1),
            "freshness_90d_pct": round(fresh_ratio * 100, 1),
            "thin_content_pct": round(thin_ratio * 100, 1),
            "orphan_pages": len(orphans),
        },
    }


def _orphans(posts: list[dict]) -> list[str]:
    all_slugs = {p["slug"] for p in posts}
    linked = set()
    for p in posts:
        linked.update(p["internal_slugs"])
    return sorted(all_slugs - linked - {"_index"})


def _series_status(posts: list[dict]) -> list[dict]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for p in posts:
        if p["series"]:
            groups[p["series"]].append(p)
    out = []
    for name, items in sorted(groups.items(), key=lambda x: -len(x[1])):
        out.append({
            "series": name,
            "count": len(items),
            "complete": len(items) >= 5,
            "needs": max(0, 5 - len(items)),
            "sample_title": items[0]["title"],
        })
    return out


def _link_suggestions(posts: list[dict], limit: int) -> list[dict]:
    by_slug = {p["slug"]: p for p in posts}
    weak = [p for p in posts if p["internal_link_count"] < 3 and not p["thin"]]
    weak.sort(key=lambda x: x["internal_link_count"])
    suggestions = []

    for p in weak:
        candidates = []
        for other in posts:
            if other["slug"] == p["slug"]:
                continue
            shared_cat = set(c.lower() for c in p["categories"]) & set(c.lower() for c in other["categories"])
            shared_tag = set(t.lower() for t in p["tags"]) & set(t.lower() for t in other["tags"])
            score = len(shared_cat) * 3 + len(shared_tag) + (2 if p["series"] and p["series"] == other["series"] else 0)
            if score > 0:
                candidates.append((score, other))
        candidates.sort(key=lambda x: -x[0])
        for _, target in candidates[:2]:
            if target["slug"] in p["internal_slugs"]:
                continue
            suggestions.append({
                "from_slug": p["slug"],
                "from_title": p["title"],
                "to_slug": target["slug"],
                "to_title": target["title"],
                "to_url": f"/posting/{target['slug']}/" if target["section"] == "posting" else f"/{target['section']}/{target['slug']}/",
            })
            if len(suggestions) >= limit:
                return suggestions
    return suggestions


def _backlink_opportunities(posts: list[dict]) -> list[dict]:
    ranked = sorted(posts, key=lambda p: (-p["eeat_score"], -p["word_count"]))[:15]
    channels = ["Reddit r/VietNam", "Quora tiếng Việt", "LinkedIn article", "Facebook Group fintech", "Medium mirror"]
    out = []
    for i, p in enumerate(ranked[:8]):
        ch = channels[i % len(channels)]
        out.append({
            "post": p["title"],
            "url": p["url"],
            "channel": ch,
            "reason": f"E-E-A-T {p['eeat_score']} · {p['word_count']} từ",
        })
    return out


def _forecast(posts: list[dict], trust: dict) -> dict:
    dates = []
    for p in posts:
        for ds in (p.get("date"), p.get("updated")):
            if not ds:
                continue
            try:
                dates.append(datetime.strptime(ds, "%Y-%m-%d").replace(tzinfo=timezone.utc))
            except ValueError:
                pass
    if len(dates) < 2:
        rate = 4.0
    else:
        dates.sort()
        span = max(1, (dates[-1] - dates[0]).days / 30)
        rate = len(posts) / span

    base = trust["score"]
    projections = {}
    for months, label in ((3, "3_months"), (6, "6_months"), (12, "12_months")):
        projected_posts = len(posts) + rate * months
        gain = min(25, months * 2 + rate * 0.5)
        proj_trust = int(min(100, base + gain))
        stage = "Established Authority" if proj_trust >= 75 else "Growth Phase" if proj_trust >= 55 else "Authority Phase"
        projections[label] = {
            "months": months,
            "projected_trust_score": proj_trust,
            "projected_stage": stage,
            "estimated_posts": int(projected_posts),
        }
    return {
        "publish_rate_per_month": round(rate, 1),
        "current_trust": base,
        "projections": projections,
    }


def build_report(*, force_full: bool = False) -> tuple[dict, dict[str, str]]:
    prev = _load_json(DATA_OUT) or {}
    manifest = _load_json(MANIFEST_OUT) or {}
    if force_full:
        manifest = {}

    posts, new_manifest, incremental = scan_posts(manifest if isinstance(manifest, dict) else {})
    audit = _load_json(ROOT / "data" / "audit-internal-links.json")
    orphans = _orphans(posts)
    trust = _trust_score(posts, orphans, audit)
    categories = _category_authority(posts)
    series = _series_status(posts)
    link_suggestions = _link_suggestions(posts, 30)
    report_number = int(prev.get("report_number") or 0) + 1
    now = datetime.now(timezone.utc)

    history = list(prev.get("history") or [])
    history.append({
        "report_number": report_number,
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "trust_score": trust["score"],
        "trust_label": trust["label"],
    })
    history = history[-30:]

    payload: dict[str, Any] = {
        "version": 1,
        "report_number": report_number,
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "trust_score": trust,
        "category_authority": categories,
        "topical_gaps": TOPICAL_GAPS,
        "orphan_pages": orphans[:40],
        "thin_content": [p["slug"] for p in posts if p["thin"]][:30],
        "series_status": series,
        "internal_link_suggestions": link_suggestions,
        "backlink_opportunities": _backlink_opportunities(posts),
        "authority_forecast": _forecast(posts, trust),
        "eeat_audit": {
            "avg_score": trust["components"].get("eeat_avg", 0),
            "weak_posts": [p["slug"] for p in posts if p["eeat_score"] < 50][:25],
        },
        "scan_stats": {
            "total_posts": len(posts),
            "incremental": incremental and not force_full,
        },
        "history": history,
        "growth_recommendation": _growth_note(trust),
    }
    return payload, new_manifest


def _growth_note(trust: dict) -> str:
    s = trust["score"]
    if s >= 75:
        return "Trust đủ để Google coi blog là nguồn tham khảo — duy trì freshness + cluster."
    if s >= 58:
        return "Đang ở Growth Phase — mở rộng internal links + pillar pages để lên Established."
    return "Technical SEO tốt nhưng authority thực còn yếu — ưu tiên cluster, refs chính thống, series ≥5 bài."


def _apply_internal_links(suggestions: list[dict], limit: int) -> int:
    applied = 0
    for sug in suggestions[:limit]:
        path = ROOT / "content" / "posting" / f"{sug['from_slug']}.md"
        if not path.is_file():
            path = ROOT / "content" / "baochi" / f"{sug['from_slug']}.md"
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        anchor = f"]({sug['to_url']})"
        if anchor in text or sug["to_slug"] in text:
            continue
        snippet = f"\n\n> **Xem thêm trong cụm:** [{sug['to_title']}]({sug['to_url']})\n"
        if "## Tài liệu tham khảo" in text:
            text = text.replace("## Tài liệu tham khảo", snippet + "\n## Tài liệu tham khảo", 1)
        else:
            text = text.rstrip() + snippet
        path.write_text(text, encoding="utf-8")
        applied += 1
    return applied


def _apply_external_refs(posts: list[dict], limit: int) -> int:
    applied = 0
    candidates = [p for p in posts if p["external_link_count"] == 0 and not p["thin"]]
    candidates.sort(key=lambda x: x["eeat_score"])
    for p in candidates[:limit]:
        path = ROOT / p["path"]
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if "## Tài liệu tham khảo" in text:
            continue
        refs = OFFICIAL_REF_POOL[:3]
        if p["topic_keys"]:
            cfg = PILLAR_TOPICS.get(p["topic_keys"][0], {})
            refs = cfg.get("refs", refs)[:3]
        block = "\n\n## Tài liệu tham khảo\n\n"
        for title, url in refs:
            block += f"- [{title}]({url})\n"
        path.write_text(text.rstrip() + block, encoding="utf-8")
        applied += 1
    return applied


def _apply_freshness(posts: list[dict], limit: int) -> int:
    """Set extra.date_revised — Zola reserves top-level `updated` as date array."""
    applied = 0
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    old = []
    for p in posts:
        if p["slug"].startswith("feed-anchor-"):
            continue
        ds = p.get("updated") or p.get("date") or ""
        try:
            d = datetime.strptime(ds, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - d).days > 90:
                old.append(p)
        except ValueError:
            old.append(p)
    old.sort(key=lambda x: x["eeat_score"], reverse=True)
    for p in old[:limit]:
        path = ROOT / p["path"]
        text = path.read_text(encoding="utf-8")
        if _EXTRA_REVISED_RE.search(text):
            text = _EXTRA_REVISED_RE.sub(f'date_revised = "{today}"', text, count=1)
        elif "[extra]" in text:
            text = text.replace("[extra]", f"[extra]\ndate_revised = \"{today}\"", 1)
        else:
            fm, body = _split_front_matter(text)
            text = f"---\n{fm.rstrip()}\n\n[extra]\ndate_revised = \"{today}\"\n---\n{body}"
        path.write_text(text, encoding="utf-8")
        applied += 1
    return applied


def _pillar_body(slug: str, cfg: dict, posts: list[dict]) -> str:
    related = [p for p in posts if slug in p["topic_keys"]]
    related.sort(key=lambda x: (-x["eeat_score"], -x["word_count"]))
    lines = [
        f"Pillar page cho cụm **{cfg['title']}** — hub nội bộ liên kết các bài liên quan.",
        "",
        "## Bài nổi bật",
        "",
    ]
    for p in related[:20]:
        lines.append(f"- [{p['title']}]({BASE_URL}/{p['section']}/{p['slug']}/)")
    lines.extend(["", "## Nguồn tham khảo", ""])
    for title, url in cfg.get("refs", [])[:4]:
        lines.append(f"- [{title}]({url})")
    return "\n".join(lines) + "\n"


def _ensure_pillar_pages(posts: list[dict]) -> int:
    TOPIC_DIR.mkdir(parents=True, exist_ok=True)
    index = TOPIC_DIR / "_index.md"
    if not index.is_file():
        index.write_text('+++\ntitle = "Topic Pillars"\nsort_by = "title"\n+++\n\nHub chủ đề — pillar pages cho topical authority.\n', encoding="utf-8")
    created = 0
    for slug, cfg in PILLAR_TOPICS.items():
        path = TOPIC_DIR / f"{slug}.md"
        body = _pillar_body(slug, cfg, posts)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        fm = f'''+++
title = "{cfg['title']}"
description = "Pillar page — {cfg['title']}. Auto-updated by authority-booster."
date = {today}
template = "page.html"
aliases = ["/topic/{slug}/"]

[extra]
seo_keyword = "{cfg['title']} pillar"
+++

'''
        if path.is_file():
            existing = path.read_text(encoding="utf-8")
            if "date =" not in existing or "Auto-updated by authority-booster" not in existing:
                path.write_text(fm + body, encoding="utf-8")
                created += 1
        else:
            path.write_text(fm + body, encoding="utf-8")
            created += 1
    return created


def _draft_series_continuation(series_status: list[dict], posts: list[dict]) -> int:
    incomplete = [s for s in series_status if not s["complete"]]
    if not incomplete:
        return 0
    target = incomplete[0]
    draft_dir = ROOT / "content" / "posting"
    draft_name = f"_authority-draft-{target['series'][:24].replace('/', '-')}.md"
    draft_path = draft_dir / draft_name
    if draft_path.is_file():
        return 0
    title = f"[DRAFT] {target['sample_title']} — phần tiếp theo"
    text = f'''+++
title = "{title}"
description = "Bản nháp do Authority Booster đề xuất — cần review trước khi publish."
date = {datetime.now(timezone.utc).strftime("%Y-%m-%d")}
draft = true

[taxonomies]
categories = ["Tất cả"]

[extra]
series = "{target['series']}"
authority_booster_draft = true
+++

> **Authority Booster** đề xuất mở rộng series `{target['series']}` (hiện {target['count']}/5 bài).

## Dàn ý đề xuất

1. Tóm tắt các phần trước (internal link về pillar).
2. Nội dung mới — FAQ + 2 nguồn chính thống.
3. Link chéo 2–3 bài cùng series.

## Tài liệu tham khảo

- [Wikipedia](https://vi.wikipedia.org/)
'''
    draft_path.write_text(text, encoding="utf-8")
    return 1


def _render_md(payload: dict) -> str:
    t = payload["trust_score"]
    lines = [
        f"# Authority Report #{payload['report_number']}",
        f"",
        f"**Trust Score:** {t['score']}/100 — **{t['label']}**",
        f"",
        f"## Category Authority",
        f"",
        f"| Category | Coverage | Score |",
        f"|----------|----------|-------|",
    ]
    for c in payload["category_authority"]:
        lines.append(f"| {c['category']} | {c['coverage']} bài | {c['score']} |")
    lines.extend(["", "## Topical Gaps", ""])
    for g in payload["topical_gaps"]:
        lines.append(f"- {g}")
    lines.extend(["", "## Forecast", ""])
    for k, v in payload["authority_forecast"]["projections"].items():
        lines.append(f"- **{v['months']} tháng:** trust {v['projected_trust_score']} → {v['projected_stage']}")
    return "\n".join(lines) + "\n"


def apply_safe_fixes(payload: dict, posts: list[dict]) -> dict[str, int]:
    suggestions = payload.get("internal_link_suggestions") or []
    stats = {
        "internal_links": _apply_internal_links(suggestions, MAX_LINK_FIXES),
        "external_refs": _apply_external_refs(posts, MAX_REF_FIXES),
        "freshness": _apply_freshness(posts, MAX_FRESHNESS),
        "pillar_pages": _ensure_pillar_pages(posts),
        "series_drafts": _draft_series_continuation(payload.get("series_status") or [], posts),
    }
    return stats


def write_outputs(payload: dict, manifest: dict[str, str]) -> Path:
    DATA_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MANIFEST_OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    day = payload["generated_at"][:10].replace("-", "")
    n = payload["report_number"]
    md_path = REPORTS_DIR / f"report-{n:03d}-{day}.md"
    md_path.write_text(_render_md(payload), encoding="utf-8")
    payload["latest_report_path"] = str(md_path.relative_to(ROOT))
    DATA_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Authority Booster Engine")
    parser.add_argument("--full", action="store_true", help="Force full rescan")
    parser.add_argument("--apply", action="store_true", help="Apply safe content fixes for PR")
    parser.add_argument("--dry-run", action="store_true", help="Report only, no writes")
    args = parser.parse_args()

    payload, manifest = build_report(force_full=args.full)
    posts, _, _ = scan_posts(manifest)

    if args.apply and not args.dry_run:
        stats = apply_safe_fixes(payload, posts)
        payload["last_apply_stats"] = stats
        print(f"apply: {stats}")

    if args.dry_run:
        print(json.dumps(payload["trust_score"], ensure_ascii=False, indent=2))
        return 0

    md_path = write_outputs(payload, manifest)
    print(
        f"authority-report #{payload['report_number']}: trust={payload['trust_score']['score']} "
        f"({payload['trust_score']['label']}) posts={payload['scan_stats']['total_posts']}"
    )
    print(f"→ {DATA_OUT}")
    print(f"→ {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())