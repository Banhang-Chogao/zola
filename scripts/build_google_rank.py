#!/usr/bin/env python3
"""Build Google Rank sidebar metrics from local SEO data (no paid APIs)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
STATIC_DATA = ROOT / "static" / "data"
CONTENT_DIRS = (ROOT / "content" / "posting", ROOT / "content" / "baochi")

LEVELS: list[tuple[int, str, str]] = [
    (91, "Top Tier", "🏆"),
    (81, "Premium", "💎"),
    (71, "Elite", "⭐"),
    (61, "High Authority", "🔷"),
    (51, "Authority", "📣"),
    (41, "Strong", "💪"),
    (31, "Established", "🏗"),
    (21, "Growing", "📈"),
    (11, "Beginner", "🌿"),
    (0, "New Site", "🌱"),
]

WEIGHTS = {
    "seo_audit": 0.25,
    "compliance": 0.20,
    "lighthouse_seo": 0.15,
    "content_volume": 0.10,
    "category_diversity": 0.05,
    "topical_authority": 0.10,
    "schema_coverage": 0.10,
    "internal_links": 0.05,
}


def _load_json(path: Path) -> dict | list | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _level(score: int) -> dict[str, str]:
    for threshold, name, emoji in LEVELS:
        if score >= threshold:
            return {"name": name, "emoji": emoji, "slug": name.lower().replace(" ", "-")}
    return {"name": "New Site", "emoji": "🌱", "slug": "new-site"}


def _parse_ratio(detail: str) -> float | None:
    m = re.search(r"(\d+)\s*/\s*(\d+)", detail or "")
    if not m:
        return None
    total = int(m.group(2))
    if total <= 0:
        return None
    return int(m.group(1)) / total * 100.0


def _count_articles() -> int:
    n = 0
    for folder in CONTENT_DIRS:
        if not folder.is_dir():
            continue
        for md in folder.glob("*.md"):
            if md.name.startswith("_"):
                continue
            n += 1
    return n


def _count_categories() -> int:
    cats: set[str] = set()
    for folder in CONTENT_DIRS:
        if not folder.is_dir():
            continue
        for md in folder.glob("*.md"):
            if md.name.startswith("_"):
                continue
            text = md.read_text(encoding="utf-8", errors="ignore")
            if not text.startswith("+++"):
                continue
            end = text.find("+++", 3)
            if end < 0:
                continue
            fm = text[3:end]
            for line in fm.splitlines():
                if line.strip().startswith("categories"):
                    # categories = ["a", "b"] or single value
                    vals = re.findall(r'"([^"]+)"', line)
                    cats.update(vals)
    return len(cats)


def _internal_link_total(refs: dict | None) -> int:
    if not isinstance(refs, dict):
        return 0
    return sum(int(v.get("internal_count", 0) or 0) for v in refs.values() if isinstance(v, dict))


def _topical_score(scores: list | None) -> float:
    if not scores:
        return 50.0
    clusters = {row.get("cluster") for row in scores if isinstance(row, dict) and row.get("cluster")}
    # 8+ clusters ≈ full topical spread for this blog size
    return _clamp(len(clusters) / 8.0 * 100.0)


def _schema_pct(compliance: dict | None) -> float:
    if not compliance:
        return 0.0
    for cat in compliance.get("categories") or []:
        if cat.get("id") != "structure":
            continue
        for item in cat.get("items") or []:
            if "structured data" in (item.get("label") or "").lower():
                ratio = _parse_ratio(item.get("detail", ""))
                if ratio is not None:
                    return ratio
        return float(cat.get("score") or 0)
    return 0.0


def compute_rank() -> dict:
    seo = _load_json(DATA / "seo-scores.json") or {}
    compliance = _load_json(DATA / "compliance-score.json") or {}
    pagespeed = _load_json(DATA / "pagespeed.json") or {}
    refs = _load_json(DATA / "references.json") or {}
    related_scores = _load_json(DATA / "scores.json") or []

    seo_audit = float(seo.get("site_score") or 0)
    compliance_score = float(compliance.get("score") or 0)
    lh = pagespeed.get("mobile") or pagespeed.get("desktop") or {}
    lighthouse_seo = float(lh.get("seo") or 0)

    articles = _count_articles()
    pages_indexed = int(seo.get("pages_scanned") or 0)
    categories = _count_categories()
    internal_links = _internal_link_total(refs)
    schema_pct = _schema_pct(compliance)
    topical = _topical_score(related_scores if isinstance(related_scores, list) else None)

    components = {
        "seo_audit": _clamp(seo_audit),
        "compliance": _clamp(compliance_score),
        "lighthouse_seo": _clamp(lighthouse_seo),
        "content_volume": _clamp(min(100.0, articles * 1.5 + pages_indexed * 0.05)),
        "category_diversity": _clamp(min(100.0, categories * 9.0)),
        "topical_authority": topical,
        "schema_coverage": _clamp(schema_pct),
        "internal_links": _clamp(min(100.0, internal_links / 4.0)),
    }

    raw = sum(components[k] * WEIGHTS[k] for k in WEIGHTS)
    score = int(round(_clamp(raw)))

    level = _level(score)
    bar_filled = max(0, min(10, round(score / 10)))

    return {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "score": score,
        "max_score": 100,
        "level": level["name"],
        "level_emoji": level["emoji"],
        "level_slug": level["slug"],
        "bar_filled": bar_filled,
        "bar_total": 10,
        "components": {k: round(v, 1) for k, v in components.items()},
        "details": {
            "pages_indexed": pages_indexed,
            "articles": articles,
            "categories": categories,
            "internal_links": internal_links,
            "schema_coverage_pct": round(schema_pct, 1),
            "seo_audit": round(seo_audit, 1),
        },
        "tooltip": (
            "Modern SEO Authority Score inspired by Google's current ranking factors. "
            "Google no longer publishes Toolbar PageRank."
        ),
    }


def write_outputs(payload: dict) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    STATIC_DATA.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    (DATA / "google-rank.json").write_text(text, encoding="utf-8")
    (STATIC_DATA / "google-rank.json").write_text(text, encoding="utf-8")


def main() -> int:
    payload = compute_rank()
    write_outputs(payload)
    print(
        f"google-rank: {payload['score']}/100 — {payload['level_emoji']} {payload['level']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())