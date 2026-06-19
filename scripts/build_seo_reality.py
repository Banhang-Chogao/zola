#!/usr/bin/env python3
"""Build SEO Reality Check sidebar data (data/seo-reality.json).

Honest companion to the Google Rank widget. It separates:

  * Technical SEO readiness   — INTERNAL heuristic (reuses google-rank.json)
  * Google Search Console     — REAL data only if data/gsc-metrics.json exists,
                                otherwise rendered as "not connected"
  * Indexing status           — GSC API (real) or "unknown"
  * Authority metrics         — site age ESTIMATED; backlinks NOT MEASURED
  * Organic growth stage      — ESTIMATED from site age

Rule: never fake Google data. Missing APIs are labelled, not invented.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
STATIC_DATA = ROOT / "static" / "data"
CONTENT_DIRS = (ROOT / "content" / "posting", ROOT / "content" / "baochi")

_DATE_RE = re.compile(r"^\s*date\s*=\s*\"?(\d{4}-\d{2}-\d{2})", re.MULTILINE)


def _load_json(path: Path):
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _earliest_post_date() -> datetime | None:
    """Earliest published-post date — honest proxy for site age."""
    earliest: datetime | None = None
    for folder in CONTENT_DIRS:
        if not folder.is_dir():
            continue
        for md in folder.glob("*.md"):
            if md.name.startswith("_"):
                continue
            try:
                text = md.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            m = _DATE_RE.search(text)
            if not m:
                continue
            try:
                d = datetime.strptime(m.group(1), "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            if earliest is None or d < earliest:
                earliest = d
    return earliest


def _age_label(days: int) -> str:
    if days <= 0:
        return "Hôm nay"
    if days < 60:
        return f"{days} ngày"
    if days < 365:
        return f"{days // 30} tháng"
    years = days // 365
    rem_months = (days % 365) // 30
    return f"{years} năm" + (f" {rem_months} tháng" if rem_months else "")


def _authority_level(days: int) -> dict[str, str]:
    """Estimate authority maturity from site age only (no backlink data)."""
    if days < 90:
        return {"level": "New Site", "slug": "new-site"}
    if days < 180:
        return {"level": "Growing", "slug": "growing"}
    if days < 365:
        return {"level": "Established", "slug": "established"}
    return {"level": "Strong Authority", "slug": "strong-authority"}


def _growth_stage(days: int) -> dict[str, str]:
    """Estimate organic-growth stage from site age (time-based heuristic)."""
    if days <= 30:
        return {
            "stage": "Indexing Phase",
            "slug": "indexing",
            "stage_vi": "Giai đoạn lập chỉ mục",
        }
    if days <= 90:
        return {
            "stage": "Discovery Phase",
            "slug": "discovery",
            "stage_vi": "Giai đoạn khám phá",
        }
    if days <= 180:
        return {
            "stage": "Growth Phase",
            "slug": "growth",
            "stage_vi": "Giai đoạn tăng trưởng",
        }
    return {
        "stage": "Authority Phase",
        "slug": "authority",
        "stage_vi": "Giai đoạn xây thẩm quyền",
    }


def _technical_seo() -> dict:
    gr = _load_json(DATA / "google-rank.json") or {}
    seo = _load_json(DATA / "seo-scores.json") or {}
    score = gr.get("score")
    if score is None:
        score = int(round(float(seo.get("site_score") or 0)))
    return {
        "score": score,
        "max_score": gr.get("max_score", 100),
        "grade": seo.get("grade"),
        "level": gr.get("level"),
        "source": "internal",
    }


def _gsc_connected(gsc: dict | None) -> bool:
    return isinstance(gsc, dict) and bool(gsc.get("connected"))


def _gsc_section(gsc: dict | None) -> dict:
    """Real Google Search Console data if present, else honest 'not connected'."""
    if not _gsc_connected(gsc):
        return {
            "connected": False,
            "property": None,
            "updated_at": None,
            "status": "not_connected",
            "indexed_pages": None,
            "impressions": None,
            "clicks": None,
            "ctr": None,
            "avg_position": None,
            "coverage_issues": None,
            "sitemap_status": None,
            "last_crawl": None,
            "period_days": 28,
        }
    return {
        "connected": True,
        "property": gsc.get("property"),
        "updated_at": gsc.get("updated_at"),
        "status": gsc.get("status", "ok"),
        "indexed_pages": gsc.get("indexed_pages"),
        "impressions": gsc.get("impressions"),
        "clicks": gsc.get("clicks"),
        "ctr": gsc.get("ctr"),
        "avg_position": gsc.get("avg_position"),
        "coverage_issues": gsc.get("coverage_issues"),
        "sitemap_status": gsc.get("sitemap_status"),
        "last_crawl": gsc.get("last_crawl"),
        "period_days": gsc.get("period_days", 28),
    }


def _indexing_section(gsc: dict | None, sitemap_pages: int) -> dict:
    if _gsc_connected(gsc):
        submitted = gsc.get("submitted_pages")
        indexed = gsc.get("indexed_pages")
        non_indexed = gsc.get("non_indexed_pages")
        if non_indexed is None and submitted and indexed is not None:
            non_indexed = max(0, int(submitted) - int(indexed))
        return {
            "connected": True,
            "pages_indexed": indexed,
            "pages_non_indexed": non_indexed,
            "pages_waiting": gsc.get("pages_waiting", non_indexed),
            "submitted_pages": submitted,
            "avg_delay_days": gsc.get("avg_index_delay_days"),
            "last_crawl": gsc.get("last_crawl"),
            "sitemap_status": gsc.get("sitemap_status"),
            "index_health": gsc.get("index_health"),
            "sitemap_pages": sitemap_pages,
        }
    return {
        "connected": False,
        "pages_indexed": None,
        "pages_non_indexed": None,
        "pages_waiting": None,
        "submitted_pages": None,
        "avg_delay_days": None,
        "last_crawl": None,
        "sitemap_status": None,
        "index_health": None,
        "sitemap_pages": sitemap_pages,
    }


def _gsc_extras(gsc: dict | None) -> dict:
    if not _gsc_connected(gsc):
        return {
            "top_pages": [],
            "top_queries": [],
            "trend": {"daily": [], "weekly": [], "monthly": []},
            "executive_summary": [],
        }
    return {
        "top_pages": gsc.get("top_pages") or [],
        "top_queries": gsc.get("top_queries") or [],
        "trend": gsc.get("trend") or {"daily": [], "weekly": [], "monthly": []},
        "executive_summary": gsc.get("executive_summary") or [],
    }


def compute_reality() -> dict:
    seo = _load_json(DATA / "seo-scores.json") or {}
    gsc = _load_json(DATA / "gsc-metrics.json")  # future: real GSC API output

    earliest = _earliest_post_date()
    now = datetime.now(timezone.utc)
    age_days = (now - earliest).days if earliest else 0
    age_days = max(0, age_days)

    sitemap_pages = int(seo.get("pages_scanned") or 0)
    authority = _authority_level(age_days)
    growth = _growth_stage(age_days)
    gsc_connected = _gsc_connected(gsc)
    extras = _gsc_extras(gsc)

    return {
        "updated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "site_age_days": age_days,
        "site_age_label": _age_label(age_days),
        "site_launch_date": earliest.strftime("%Y-%m-%d") if earliest else None,
        "technical_seo": _technical_seo(),
        "gsc": _gsc_section(gsc),
        "indexing": _indexing_section(gsc, sitemap_pages),
        "top_pages": extras["top_pages"],
        "top_queries": extras["top_queries"],
        "trend": extras["trend"],
        "executive_summary": extras["executive_summary"],
        "authority": {
            "site_age_days": age_days,
            "site_age_label": _age_label(age_days),
            "referring_domains": None,
            "backlinks": None,
            "authority_level": authority["level"],
            "authority_level_slug": authority["slug"],
            "authority_source": "estimated",
            "backlinks_source": "not_measured",
        },
        "growth": {
            "stage": growth["stage"],
            "stage_slug": growth["slug"],
            "stage_vi": growth["stage_vi"],
            # No real traffic/GSC data → growth is time-based only → low confidence.
            "confidence": "high" if gsc_connected else "low",
            "source": "estimated",
            "note": (
                "Điểm kỹ thuật có thể cao trong khi traffic còn thấp — điều này "
                "hoàn toàn bình thường với một blog mới đang được Google lập chỉ mục."
            ),
        },
        "tooltip": (
            "Technical SEO Score phản ánh mức độ sẵn sàng kỹ thuật của site, "
            "KHÔNG phải thứ hạng Google. Hiệu quả tìm kiếm thực tế phụ thuộc vào "
            "chất lượng nội dung, backlink, thẩm quyền tên miền, độ cạnh tranh "
            "từ khoá, search intent, trạng thái lập chỉ mục và thời gian."
        ),
    }


def write_outputs(payload: dict) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    STATIC_DATA.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    (DATA / "seo-reality.json").write_text(text, encoding="utf-8")
    (STATIC_DATA / "seo-reality.json").write_text(text, encoding="utf-8")


def main() -> int:
    payload = compute_reality()
    write_outputs(payload)
    tech = payload["technical_seo"]
    print(
        f"seo-reality: tech={tech['score']}/{tech['max_score']} (internal) · "
        f"age={payload['site_age_label']} · "
        f"gsc={'connected' if payload['gsc']['connected'] else 'not-connected'} · "
        f"stage={payload['growth']['stage']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
