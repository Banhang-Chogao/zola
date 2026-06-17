#!/usr/bin/env python3
"""
Related Posts QA Checker — quét, chấm điểm và fix related posts theo topic cluster.

Chạy hằng ngày 22:00 giờ Việt Nam (15:00 UTC) qua .github/workflows/related-qa.yml.

Usage:
    python3 scripts/related_qa_checker.py --dry-run   # report only
    python3 scripts/related_qa_checker.py --fix      # ghi related.json + scores.json + report
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
REPORT_JSON = ROOT / "data" / "related-qa-report.json"
REPORT_MD = ROOT / "reports" / "related-qa-latest.md"

sys.path.insert(0, str(ROOT / "scripts"))

from related_engine import (  # noqa: E402
    CLUSTER_LABELS,
    RELATED_FILE,
    SCORES_FILE,
    build_indexes,
    load_posts,
    tier_from_score,
    write_outputs,
)


def load_json(path: Path) -> Any:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def summarize_tiers(scores: list[dict[str, Any]]) -> dict[str, int]:
    out = {"high": 0, "mid": 0, "low": 0}
    for s in scores:
        tier = s.get("tier") or tier_from_score(float(s.get("score", 0)))
        out[tier] = out.get(tier, 0) + 1
    return out


def score_map(scores: list[dict[str, Any]] | None) -> dict[str, dict[str, Any]]:
    if not scores:
        return {}
    return {s["slug"]: s for s in scores if s.get("slug")}


def related_map_by_slug(data: dict | None) -> dict[str, list[dict[str, Any]]]:
    return data if isinstance(data, dict) else {}


def cannot_reach_green_reason(post_meta: dict, related: list[dict], pool_size: int) -> str:
    cluster = post_meta.get("cluster", "misc")
    label = CLUSTER_LABELS.get(cluster, cluster)
    if pool_size <= 1:
        return f"Chỉ có {pool_size} bài trong cluster '{label}' — không đủ neighbor cùng chủ đề."
    if not related:
        return "Không tìm được cặp semantic đủ mạnh trong cluster."
    top = max(r["score"] for r in related)
    if top < 0.55:
        return f"Top semantic score thấp ({top:.2f}) — nội dung quá khác biệt trong cluster."
    if post_meta.get("score", 0) < 0.7:
        return f"Trung bình top-{len(related)} = {post_meta.get('score', 0):.2f} < 0.70 — cần thêm bài cùng intent hoặc làm sâu nội dung cluster."
    return ""


def build_report(
    before_scores: list[dict[str, Any]] | None,
    after_scores: list[dict[str, Any]],
    before_related: dict[str, list[dict[str, Any]]],
    after_related: dict[str, list[dict[str, Any]]],
    posts_meta: list[dict[str, Any]],
    *,
    fixed: bool,
) -> dict[str, Any]:
    before_by_slug = score_map(before_scores)
    after_by_slug = score_map(after_scores)
    cluster_counts: dict[str, int] = {}
    for p in posts_meta:
        cluster_counts[p["cluster"]] = cluster_counts.get(p["cluster"], 0) + 1

    entries = []
    fixed_slugs = []
    still_orange = []
    still_red = []

    for meta in posts_meta:
        slug = meta["slug"]
        b = before_by_slug.get(slug, {})
        a = after_by_slug.get(slug, meta)
        tier_b = b.get("tier") or tier_from_score(float(b.get("score", 0)))
        tier_a = a.get("tier") or tier_from_score(float(a.get("score", 0)))
        score_b = float(b.get("score", 0))
        score_a = float(a.get("score", 0))
        rel_b = before_related.get(slug, [])
        rel_a = after_related.get(slug, [])
        pool = cluster_counts.get(meta["cluster"], 0)

        changed = rel_b != rel_a or abs(score_b - score_a) > 0.0001
        action = "fixed" if changed and fixed else ("analyzed" if changed else "unchanged")

        reason = ""
        if tier_a != "high":
            reason = cannot_reach_green_reason(a, rel_a, pool)

        entry = {
            "slug": slug,
            "section": meta["section"],
            "title": meta["title"],
            "cluster": meta["cluster"],
            "cluster_label": CLUSTER_LABELS.get(meta["cluster"], meta["cluster"]),
            "tier_before": tier_b,
            "tier_after": tier_a,
            "score_before": round(score_b, 4),
            "score_after": round(score_a, 4),
            "delta": round(score_a - score_b, 4),
            "related_before": rel_b,
            "related_after": rel_a,
            "action": action,
            "cannot_green_reason": reason or None,
        }
        entries.append(entry)

        if changed and fixed:
            fixed_slugs.append(slug)
        if tier_a == "mid":
            still_orange.append(slug)
        if tier_a == "low":
            still_red.append(slug)

    entries.sort(key=lambda e: (e["tier_after"] != "high", -e["score_after"]))

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "timezone_note": "Scheduled 22:00 Asia/Ho_Chi_Minh (15:00 UTC)",
        "fixed_applied": fixed,
        "summary": {
            "total_posts": len(posts_meta),
            "before": summarize_tiers(list(before_by_slug.values())) if before_by_slug else None,
            "after": summarize_tiers(after_scores),
            "fixed_count": len(fixed_slugs),
            "still_orange": len(still_orange),
            "still_red": len(still_red),
            "green_count": summarize_tiers(after_scores).get("high", 0),
        },
        "fixed_slugs": fixed_slugs,
        "still_orange_slugs": still_orange,
        "still_red_slugs": still_red,
        "posts": entries,
    }


def write_markdown_report(report: dict[str, Any]) -> None:
    s = report["summary"]
    lines = [
        "# Related Posts QA Report",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "## Summary",
        "",
        f"- Total posts: **{s['total_posts']}**",
        f"- Green (≥70): **{s['green_count']}**",
        f"- Orange (40–69): **{s['still_orange']}**",
        f"- Red (<40): **{s['still_red']}**",
        f"- Fixed this run: **{s['fixed_count']}**",
        "",
    ]
    if s.get("before"):
        b = s["before"]
        lines.append(
            f"- Before: green {b.get('high', 0)}, orange {b.get('mid', 0)}, red {b.get('low', 0)}"
        )
    a = s["after"]
    lines.append(
        f"- After: green {a.get('high', 0)}, orange {a.get('mid', 0)}, red {a.get('low', 0)}"
    )
    lines.extend(["", "## Fixed posts", ""])
    if report["fixed_slugs"]:
        for slug in report["fixed_slugs"]:
            p = next(x for x in report["posts"] if x["slug"] == slug)
            lines.append(
                f"- `{slug}`: {p['score_before']:.2f} → **{p['score_after']:.2f}** "
                f"({p['tier_before']} → {p['tier_after']})"
            )
    else:
        lines.append("- (none)")

    lines.extend(["", "## Still orange/red", ""])
    for p in report["posts"]:
        if p["tier_after"] in ("mid", "low"):
            reason = p.get("cannot_green_reason") or "—"
            lines.append(
                f"- `{p['slug']}` [{p['tier_after']}] score={p['score_after']:.2f} — {reason}"
            )

    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {REPORT_MD.relative_to(ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Related Posts QA Checker")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Ghi data/related.json + data/scores.json sau khi phân tích",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Chỉ phân tích + report, không ghi related/scores",
    )
    args = parser.parse_args()
    do_fix = args.fix and not args.dry_run

    before_scores = load_json(SCORES_FILE)
    before_related = related_map_by_slug(load_json(RELATED_FILE))

    posts = load_posts()
    print(f"QA scan: {len(posts)} posts")
    if len(posts) < 2:
        print("Need >= 2 posts for related QA.")
        return 1

    related_map, scores_list = build_indexes(posts, use_embeddings=True)

    posts_meta = [
        {
            "slug": p.slug,
            "section": p.section,
            "title": p.title,
            "cluster": p.cluster,
        }
        for p in posts
    ]

    report = build_report(
        before_scores if isinstance(before_scores, list) else None,
        scores_list,
        before_related,
        related_map,
        posts_meta,
        fixed=do_fix,
    )

    if do_fix:
        write_outputs(related_map, scores_list)

    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {REPORT_JSON.relative_to(ROOT)}")
    write_markdown_report(report)

    s = report["summary"]
    print(
        f"\nRelated QA: green={s['green_count']} orange={s['still_orange']} "
        f"red={s['still_red']} fixed={s['fixed_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())