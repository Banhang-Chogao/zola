#!/usr/bin/env python3
"""content_direction.py — Content Intelligence / Direction engine.

Analyzes the whole blog corpus and emits a single static report consumed by the
S-DNA dashboard at `/tools/content-direction/`:

    static/data/content-direction/report.json

What it surfaces (all rule-based + reuse of already-computed semantic data, so it
runs in CI with no model download and never breaks the build):

  * topics & clusters            — distribution, pillar candidates, top tags
  * internal link gaps           — posts under the ≥5 internal-link SEO rule
  * orphan content               — posts no other post links to (0 inbound)
  * SEO weakness                 — low `seo_qa_checker` score / thin content
  * AdSense-safe direction       — flags policy-risky topics, confirms safe ones
  * Google helpful-content       — E-E-A-T / depth actions
  * keyword/content opportunities— thin clusters & missing categories to grow
  * next article ideas by category
  * which old posts need refresh
  * internal-link suggestions    — concrete neighbor links to add per gap post

Reuse, don't duplicate:
  * post loading / frontmatter / cluster inference → `scripts/related_engine.py`
  * semantic neighbors / scores  → `data/related.json`, `data/scores.json`
  * SEO scores                   → `data/seo-qa-scores.json` (seo_qa_checker.py)

Optional libs (textstat, rank-bm25) refine readability/keyword signals when
present; every use is guarded so a missing lib only drops that one signal.

CLI:
    python3 scripts/content_direction.py            # build the report
    python3 scripts/content_direction.py --print     # build + summary to stdout
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import related_engine as RE  # reuse: load_posts, clusters, strip_markdown, parse_post
from link_utils import classify, extract_urls, is_external, is_internal  # safe links

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = REPO_ROOT / "static" / "data" / "content-direction" / "report.json"
RELATED_PATH = REPO_ROOT / "data" / "related.json"
SCORES_PATH = REPO_ROOT / "data" / "scores.json"
SEO_PATH = REPO_ROOT / "data" / "seo-qa-scores.json"
CATEGORIES_PATH = REPO_ROOT / "categories.json"

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("Asia/Ho_Chi_Minh")
except Exception:  # pragma: no cover
    TZ = timezone(timedelta(hours=7))

MIN_INTERNAL_LINKS = 5     # SEO CONTENT SYSTEM RULE §3
THIN_WORDS = 800           # below this = thin content
SEO_WEAK_SCORE = 70        # seo_qa_checker grade < B
REFRESH_AGE_DAYS = 150     # posts older than this are refresh candidates
SITE_HOST = "banhang-chogao.github.io"

# AdSense / helpful-content guardrails (rule-based, no network).
ADSENSE_RISK_TERMS = (
    "cá độ", "ca do", "cờ bạc", "co bac", "casino", "kèo nhà cái",
    "vay nóng", "tín dụng đen", "hack", "crack", "lậu", "18+", "nổ hũ",
)

def now_ict() -> datetime:
    return datetime.now(TZ)


def _load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _is_internal(href: str) -> bool:
    # /zola/* and any root-absolute/relative path is internal (no host needed);
    # a full self-host absolute URL also counts as internal.
    if is_internal(href):
        return True
    return is_external(href) and SITE_HOST in href


def count_links(body: str) -> tuple[int, int]:
    """Return (internal, external) link counts from a markdown/HTML body.

    Uses the shared, code-span-aware extractor so links inside fenced/inline
    code examples are not miscounted, and ``/zola/*`` internal links are never
    dropped by a host check.
    """
    internal = external = 0
    for url in extract_urls(body):
        kind = classify(url)
        if kind == "internal":
            internal += 1
        elif kind == "external":
            # A full self-host absolute URL is really an internal link.
            if SITE_HOST in url:
                internal += 1
            else:
                external += 1
    return internal, external


def _word_count(body: str) -> int:
    return len(RE.strip_markdown(body).split())


def _age_days(date_str: str) -> int | None:
    try:
        d = datetime.fromisoformat(date_str.split("T")[0]).date()
    except (ValueError, AttributeError):
        return None
    return (date.today() - d).days


def build_report() -> dict:
    posts = RE.load_posts()  # PostRecord list (drafts skipped, posting+baochi)
    related = _load_json(RELATED_PATH, {})
    scores = {s["slug"]: s for s in _load_json(SCORES_PATH, [])}
    seo_raw = _load_json(SEO_PATH, {})
    seo_posts = seo_raw.get("posts", {}) if isinstance(seo_raw, dict) else {}
    seo_by_slug = {v.get("slug"): v for v in seo_posts.values() if isinstance(v, dict)}
    valid_categories = (_load_json(CATEGORIES_PATH, {}) or {}).get("categories", [])

    # Per-post body metrics (reuse related_engine.parse_post) -------------------
    bodies: dict[str, str] = {}
    for section in RE.CONTENT_SECTIONS:
        cdir = REPO_ROOT / "content" / section
        if not cdir.is_dir():
            continue
        for path in cdir.glob("*.md"):
            if path.name.startswith("_"):
                continue
            try:
                meta, content = RE.parse_post(path)
            except OSError:
                continue
            if meta.get("draft") is True:
                continue
            bodies[meta.get("slug") or path.stem] = content

    # Inbound link map from semantic neighbors (proxy for "who points here") ----
    inbound: dict[str, int] = defaultdict(int)
    for _src, neighbors in related.items():
        for n in neighbors or []:
            if isinstance(n, dict) and n.get("slug"):
                inbound[n["slug"]] += 1

    cluster_buckets: dict[str, list] = defaultdict(list)
    category_counter: Counter = Counter()
    tag_counter: Counter = Counter()
    keyword_counter: Counter = Counter()

    link_gaps: list[dict] = []
    orphans: list[dict] = []
    seo_weakness: list[dict] = []
    refresh: list[dict] = []
    adsense_flags: list[dict] = []

    for p in posts:
        cluster_buckets[p.cluster].append(p)
        for c in p.categories:
            category_counter[c] += 1
        for t in p.tags:
            tag_counter[t.lower()] += 1
        if p.seo_keyword:
            keyword_counter[p.seo_keyword.lower()] += 1

        body = bodies.get(p.slug, "")
        n_int, n_ext = count_links(body)
        words = _word_count(body) if body else 0

        # internal link gap + suggestions from semantic neighbors not yet linked
        if n_int < MIN_INTERNAL_LINKS:
            suggestions = []
            for n in (related.get(p.slug) or [])[:6]:
                nslug = n.get("slug") if isinstance(n, dict) else None
                if not nslug:
                    continue
                nb = scores.get(nslug, {})
                suggestions.append({
                    "slug": nslug,
                    "title": nb.get("title", nslug),
                    "score": n.get("score", 0),
                })
            link_gaps.append({
                "slug": p.slug, "title": p.title, "section": p.section,
                "internal_links": n_int, "external_links": n_ext,
                "need": MIN_INTERNAL_LINKS - n_int,
                "cluster_label": RE.CLUSTER_LABELS.get(p.cluster, p.cluster),
                "suggestions": suggestions[:5],
            })

        # orphan = nothing semantically points to it
        if inbound.get(p.slug, 0) == 0:
            orphans.append({
                "slug": p.slug, "title": p.title, "section": p.section,
                "internal_links": n_int,
                "cluster_label": RE.CLUSTER_LABELS.get(p.cluster, p.cluster),
                "reason": "Không bài nào liên kết tới (0 inbound) — cần được link từ bài cùng cluster.",
            })

        # SEO weakness
        sd = seo_by_slug.get(p.slug, {})
        sc = sd.get("score")
        wc = sd.get("word_count", words)
        issues = []
        if isinstance(sc, (int, float)) and sc < SEO_WEAK_SCORE:
            issues.append(f"điểm SEO {sc:.0f} < {SEO_WEAK_SCORE}")
        if wc and wc < THIN_WORDS:
            issues.append(f"thin content ({wc} từ < {THIN_WORDS})")
        if n_int < MIN_INTERNAL_LINKS:
            issues.append(f"{n_int} internal link < {MIN_INTERNAL_LINKS}")
        if n_ext == 0:
            issues.append("thiếu external link uy tín")
        if issues:
            seo_weakness.append({
                "slug": p.slug, "title": p.title, "section": p.section,
                "score": sc, "grade": sd.get("grade"), "word_count": wc,
                "issues": issues,
            })

        # refresh candidates — old posts (prioritise weaker/older)
        age = _age_days(p.date)
        if age is not None and age >= REFRESH_AGE_DAYS:
            refresh.append({
                "slug": p.slug, "title": p.title, "date": p.date,
                "age_days": age, "score": sc,
                "cluster_label": RE.CLUSTER_LABELS.get(p.cluster, p.cluster),
                "reason": f"Đăng {age} ngày trước — cập nhật dữ liệu/nguồn mới để giữ helpful-content.",
            })

        # AdSense risk scan over title + keyword + tags
        hay = " ".join([p.title, p.seo_keyword, " ".join(p.tags)]).lower()
        hit = [t for t in ADSENSE_RISK_TERMS if t in hay]
        if hit:
            adsense_flags.append({"slug": p.slug, "title": p.title, "terms": hit})

    # Clusters summary ----------------------------------------------------------
    clusters = []
    for cl, items in sorted(cluster_buckets.items(), key=lambda kv: -len(kv[1])):
        cl_tags = Counter()
        sem = []
        pillar = None
        best = -1.0
        for it in items:
            for t in it.tags:
                cl_tags[t.lower()] += 1
            s = scores.get(it.slug, {})
            tv = s.get("top_score", 0) or 0
            sem.append(s.get("score", 0) or 0)
            if tv > best:
                best, pillar = tv, {"slug": it.slug, "title": it.title}
        avg_sem = round(sum(sem) / len(sem), 3) if sem else 0
        clusters.append({
            "cluster": cl,
            "label": RE.CLUSTER_LABELS.get(cl, cl),
            "count": len(items),
            "avg_semantic": avg_sem,
            "pillar": pillar,
            "top_tags": [t for t, _ in cl_tags.most_common(6)],
            "opportunity": len(items) < 6,  # thin cluster = room to grow
        })

    # Keyword / content opportunities ------------------------------------------
    opportunities = []
    for c in clusters:
        if c["opportunity"]:
            opportunities.append({
                "type": "cluster-thin",
                "cluster": c["cluster"], "label": c["label"], "count": c["count"],
                "idea": f"Cụm '{c['label']}' mới có {c['count']} bài — viết thêm bài "
                        f"supporting + 1 bài pillar để tăng topical authority.",
            })
    # categories declared but with little/no content
    declared = {c.lower() for c in valid_categories} - {"tất cả", "premium", "báo chí"}
    have = {c.lower() for c in category_counter}
    for cat in valid_categories:
        cl = cat.lower()
        if cl in declared and category_counter.get(cat, 0) < 3:
            opportunities.append({
                "type": "category-empty",
                "category": cat, "count": category_counter.get(cat, 0),
                "idea": f"Chuyên mục '{cat}' gần như trống ({category_counter.get(cat, 0)} bài) "
                        f"— bổ sung nội dung để hub category không cụt.",
            })

    # Next article ideas by category (rule-based from existing tags) ------------
    article_ideas = []
    angles = ["hướng dẫn từng bước", "so sánh & lựa chọn", "kinh nghiệm thực tế",
              "câu hỏi thường gặp", "checklist cho người mới"]
    for cat, cnt in category_counter.most_common():
        if cat.lower() in ("tất cả", "premium", "báo chí"):
            continue
        cat_tags = Counter()
        for p in posts:
            if cat in p.categories:
                for t in p.tags:
                    cat_tags[t] += 1
        seeds = [t for t, _ in cat_tags.most_common(3)] or [cat.lower()]
        ideas = [f"{seed.capitalize()}: {angle}"
                 for seed, angle in zip(seeds + seeds, angles)][:3]
        article_ideas.append({"category": cat, "count": cnt, "ideas": ideas})

    # Sort / cap lists for a calm dashboard ------------------------------------
    link_gaps.sort(key=lambda x: x["need"], reverse=True)
    orphans.sort(key=lambda x: x["internal_links"])
    seo_weakness.sort(key=lambda x: (x["score"] is None, x["score"] or 0))
    refresh.sort(key=lambda x: x["age_days"], reverse=True)

    avg_seo = None
    seo_vals = [v.get("score") for v in seo_by_slug.values()
                if isinstance(v.get("score"), (int, float))]
    if seo_vals:
        avg_seo = round(sum(seo_vals) / len(seo_vals), 1)

    ts = now_ict()
    return {
        "generated_at": ts.isoformat(),
        "generated_at_display": ts.strftime("%H:%M %d/%m/%Y"),
        "summary": {
            "total_posts": len(posts),
            "clusters": len(clusters),
            "orphans": len(orphans),
            "link_gaps": len(link_gaps),
            "seo_weak": len(seo_weakness),
            "refresh_candidates": len(refresh),
            "avg_seo_score": avg_seo,
            "adsense_status": "review" if adsense_flags else "safe",
        },
        "clusters": clusters,
        "categories": [
            {"name": c, "count": n}
            for c, n in category_counter.most_common()
        ],
        "topics": [{"tag": t, "count": n} for t, n in tag_counter.most_common(20)],
        "keywords": [{"keyword": k, "count": n} for k, n in keyword_counter.most_common(15)],
        "orphans": orphans[:30],
        "link_gaps": link_gaps[:30],
        "seo_weakness": seo_weakness[:30],
        "refresh": refresh[:20],
        "opportunities": opportunities[:20],
        "article_ideas": article_ideas[:12],
        "adsense": {
            "status": "review" if adsense_flags else "safe",
            "flags": adsense_flags[:20],
            "notes": [
                "Nội dung blog (học tiếng Hàn, ngân hàng số, du lịch, công nghệ) thuộc nhóm "
                "AdSense-friendly, miễn tránh chủ đề cờ bạc/tài chính rủi ro cao.",
                "Giữ E-E-A-T: dẫn nguồn thật, không bịa số liệu/khuyến mãi.",
            ] if not adsense_flags else [
                "Phát hiện bài chứa từ khoá nhạy cảm với chính sách AdSense — rà soát thủ công.",
            ],
        },
        "helpful_content": {
            "actions": [
                "Ưu tiên refresh bài cũ trong danh sách 'cần làm mới' để giữ thông tin chính xác.",
                "Bổ sung internal link cho bài thiếu (≥ 5 link) — tăng crawl depth + giảm orphan.",
                "Mỗi cụm thin cần thêm bài supporting + 1 pillar để củng cố topical authority.",
                "Đảm bảo mọi bài có trải nghiệm/nguồn thật (E-E-A-T), không nội dung AI fluff.",
            ],
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Content Direction intelligence report")
    ap.add_argument("--out", default=str(OUT_PATH))
    ap.add_argument("--print", dest="show", action="store_true",
                    help="print a short summary to stdout")
    args = ap.parse_args(argv)

    try:
        report = build_report()
    except Exception as exc:  # never crash a build; keep any cached report
        print(f"WARN: content_direction failed: {exc}", file=sys.stderr)
        return 0

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    s = report["summary"]
    print(f"✓ content-direction → {out.relative_to(REPO_ROOT)} "
          f"({s['total_posts']} bài · {s['clusters']} cụm · {s['orphans']} orphan · "
          f"{s['link_gaps']} link-gap · {s['seo_weak']} SEO-weak)")
    if args.show:
        print(json.dumps({k: report[k] for k in ("summary", "opportunities")},
                         ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
