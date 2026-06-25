"""
Shared engine: topic-aware semantic related posts for posting + baochi.

Used by build_related.py (CI hourly) and related_qa_checker.py (daily QA).
"""
from __future__ import annotations

import json
import re
import sys
import tomllib
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# numpy is only needed by build_indexes/pick_related (the embedding pass). Import
# it lazily so the lightweight parsing helpers (load_posts, parse_post,
# strip_markdown, cluster maps) can be reused without numpy installed — e.g. by
# scripts/content_direction.py running in a minimal/offline env.
ROOT = Path(__file__).resolve().parent.parent
CONTENT_SECTIONS = ("posting", "baochi")


def zola_url_slug(stem: str) -> str:
    """Zola's URL slug for a filename stem.

    Strips a leading ``YYYY-MM-DD-`` date prefix (Zola treats it as the page
    date, not part of the slug) and slugifies Unicode → ASCII (đ→d, diacritics
    stripped). Without this, filenames like ``2026-06-25-foo.md`` or
    ``tai-sao-diều.md`` were stored with their raw stem and rendered as phantom
    links (``/posting/2026-06-25-foo/``, ``/posting/…diều…/``) on the scoring
    page. Mirrors Zola's own slug derivation so stored slugs match built URLs.
    """
    m = re.match(r"^\d{4}-\d{2}-\d{2}-(.+)$", stem)
    if m:
        stem = m.group(1)
    stem = stem.replace("đ", "d").replace("Đ", "D")
    stem = unicodedata.normalize("NFKD", stem)
    stem = "".join(c for c in stem if not unicodedata.combining(c))
    return re.sub(r"[^a-zA-Z0-9]+", "-", stem).strip("-").lower()
RELATED_FILE = ROOT / "data" / "related.json"
SCORES_FILE = ROOT / "data" / "scores.json"

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
TOP_N = 5
MIN_SEMANTIC = 0.12
MIN_CROSS_CLUSTER = 0.42
CROSS_CLUSTER_FACTOR = 0.35
TAG_BOOST = 0.08
SAME_SECTION_BOOST = 0.03

SKIP_CATEGORIES = {"Tất cả", "Báo chí"}

# Topic cluster — ưu tiên related cùng intent/chủ đề
CLUSTER_BY_CATEGORY = {
    "du lịch": "du-lich",
    "ẩm thực": "am-thuc",
    "công nghệ": "cong-nghe",
    "ngân hàng": "tai-chinh",
    "bảo hiểm": "tai-chinh",
    "thế giới": "the-gioi",
    "khoa học": "khoa-hoc",
}

CLUSTER_LABELS = {
    "du-lich": "Du lịch",
    "am-thuc": "Ẩm thực",
    "cong-nghe": "Công nghệ",
    "tai-chinh": "Tài chính & Ngân hàng",
    "the-gioi": "Thế giới",
    "khoa-hoc": "Khoa học",
    "khuyen-mai": "Khuyến mãi & Affiliate",
    "misc": "Khác",
}

AFFILIATE_HINTS = ("affiliate", "shopee", "khuyến mãi", "khuyen mai", "hoàn tiền thẻ")


@dataclass
class PostRecord:
    slug: str
    section: str
    title: str
    date: str
    description: str
    categories: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    seo_keyword: str = ""
    cluster: str = "misc"
    text: str = ""


def strip_markdown(text: str) -> str:
    text = re.sub(r"```[\s\S]*?```", " ", text)
    text = re.sub(r"`[^`]+`", " ", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[*_#>~|]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_post(path: Path) -> tuple[dict[str, Any], str]:
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


def _norm(s: str) -> str:
    return s.lower().strip()


def infer_cluster(categories: list[str], tags: list[str], title: str, description: str) -> str:
    for cat in reversed(categories):
        key = _norm(cat)
        if key in CLUSTER_BY_CATEGORY:
            return CLUSTER_BY_CATEGORY[key]

    hay = _norm(" ".join([title, description, " ".join(tags)]))
    if any(h in hay for h in AFFILIATE_HINTS):
        return "khuyen-mai"
    if any(k in hay for k in ("du lịch", "hàn quốc", "busan", "seoul", "jeju", "visa")):
        return "du-lich"
    if any(k in hay for k in ("ăn", "ẩm thực", "quán", "sài gòn", "món")):
        return "am-thuc"
    if any(k in hay for k in ("ngân hàng", "thẻ", "msb", "liobank", "bidv", "lpbank")):
        return "tai-chinh"
    if any(k in hay for k in ("zola", "github", "deploy", "blog", "claude", "sbert", "semantic")):
        return "cong-nghe"
    if any(k in hay for k in ("iran", "world cup", "f-18", "uranium", "trung đông")):
        return "the-gioi"
    return "misc"


def tag_jaccard(a: list[str], b: list[str]) -> float:
    sa = {_norm(t) for t in a if t}
    sb = {_norm(t) for t in b if t}
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def load_posts() -> list[PostRecord]:
    posts: list[PostRecord] = []
    for section in CONTENT_SECTIONS:
        content_dir = ROOT / "content" / section
        if not content_dir.is_dir():
            continue
        for path in sorted(content_dir.glob("*.md")):
            if path.name.startswith("_"):
                continue
            try:
                meta, content = parse_post(path)
            except OSError as exc:
                print(f"WARN: skip {path}: {exc}", file=sys.stderr)
                continue

            if meta.get("draft") is True:
                continue

            tax = meta.get("taxonomies") or {}
            cats = [c for c in tax.get("categories", []) if c not in SKIP_CATEGORIES]
            tags = list(tax.get("tags", []) or [])
            extra = meta.get("extra") or {}
            title = str(meta.get("title") or "")
            description = str(meta.get("description") or "")
            seo_keyword = str(extra.get("seo_keyword") or "")
            date = meta.get("date", "")
            date_str = date.isoformat() if hasattr(date, "isoformat") else str(date)
            body = strip_markdown(content)

            text_parts = [title, seo_keyword, description, " ".join(cats), " ".join(tags), body[:2000]]
            text = ". ".join(p for p in text_parts if p)

            cluster = infer_cluster(list(tax.get("categories", []) or []), tags, title, description)

            posts.append(
                PostRecord(
                    slug=meta.get("slug") or zola_url_slug(path.stem),
                    section=section,
                    title=title,
                    date=date_str,
                    description=description,
                    categories=cats,
                    tags=tags,
                    seo_keyword=seo_keyword,
                    cluster=cluster,
                    text=text,
                )
            )
    return posts


def load_model(name: str):
    import time
    from huggingface_hub import snapshot_download
    from sentence_transformers import SentenceTransformer

    try:
        local_dir = snapshot_download(name, local_files_only=True)
        print(f"Model load từ cache cục bộ: {local_dir}")
        return SentenceTransformer(local_dir)
    except Exception as exc:
        print(f"Chưa có cache cục bộ ({exc}); tải online + retry...", file=sys.stderr)

    last_err = None
    for attempt in range(1, 5):
        try:
            local_dir = snapshot_download(name)
            return SentenceTransformer(local_dir)
        except Exception as exc:
            last_err = exc
            wait = 2 ** attempt
            print(f"Tải model lần {attempt} lỗi: {exc}; chờ {wait}s...", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"Không nạp được model sau 4 lần thử: {last_err}")


def tier_from_score(score: float) -> str:
    pct = score * 100
    if pct >= 70:
        return "high"
    if pct >= 40:
        return "mid"
    return "low"


def score_entry(post: PostRecord, related: list[dict[str, Any]]) -> dict[str, Any]:
    if related:
        avg = sum(r["score"] for r in related) / len(related)
        top = max(r["score"] for r in related)
    else:
        avg = 0.0
        top = 0.0
    return {
        "slug": post.slug,
        "section": post.section,
        "title": post.title,
        "date": post.date,
        "cluster": post.cluster,
        "cluster_label": CLUSTER_LABELS.get(post.cluster, post.cluster),
        "score": round(avg, 4),
        "top_score": round(top, 4),
        "neighbors": len(related),
        "tier": tier_from_score(avg),
    }


def pick_related(
    idx: int,
    posts: list[PostRecord],
    sim: np.ndarray,
) -> list[dict[str, Any]]:
    source = posts[idx]
    same_cluster: list[tuple[int, float]] = []
    cross_cluster: list[tuple[int, float]] = []

    for j, target in enumerate(posts):
        if j == idx:
            continue
        cosine = float(sim[idx, j])
        tag_boost = TAG_BOOST * tag_jaccard(source.tags, target.tags)
        section_boost = SAME_SECTION_BOOST if source.section == target.section else 0.0
        adjusted = cosine + tag_boost + section_boost

        if target.cluster == source.cluster:
            if adjusted >= MIN_SEMANTIC:
                same_cluster.append((j, adjusted))
        elif cosine >= MIN_CROSS_CLUSTER:
            cross_cluster.append((j, adjusted * CROSS_CLUSTER_FACTOR))

    same_cluster.sort(key=lambda x: x[1], reverse=True)
    cross_cluster.sort(key=lambda x: x[1], reverse=True)

    chosen: list[tuple[int, float]] = []
    for pair in same_cluster:
        if len(chosen) >= TOP_N:
            break
        chosen.append(pair)

    if len(chosen) < TOP_N:
        for pair in cross_cluster:
            if len(chosen) >= TOP_N:
                break
            if pair[0] not in {c[0] for c in chosen}:
                chosen.append(pair)

    return [
        {
            "slug": posts[j].slug,
            "score": round(score, 4),
            "section": posts[j].section,
            "cluster": posts[j].cluster,
        }
        for j, score in chosen
    ]


def build_indexes(
    posts: list[PostRecord],
    *,
    use_embeddings: bool = True,
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    if len(posts) < 2:
        return {}, []

    import numpy as np

    if use_embeddings:
        model = load_model(MODEL_NAME)
        print("Encoding posts (topic-aware related)...")
        embeddings = model.encode(
            [p.text for p in posts],
            show_progress_bar=True,
            normalize_embeddings=True,
            batch_size=16,
        )
        sim = np.dot(embeddings, embeddings.T)
    else:
        sim = np.zeros((len(posts), len(posts)))

    related_map: dict[str, list[dict[str, Any]]] = {}
    scores_list: list[dict[str, Any]] = []

    slug_to_idx = {p.slug: i for i, p in enumerate(posts)}

    for i, post in enumerate(posts):
        related = pick_related(i, posts, sim)
        related_map[post.slug] = [
            {"slug": r["slug"], "score": r["score"]} for r in related
        ]
        entry = score_entry(post, related_map[post.slug])
        scores_list.append(entry)

    scores_list.sort(key=lambda x: x["score"], reverse=True)
    return related_map, scores_list


def write_outputs(
    related_map: dict[str, list[dict[str, Any]]],
    scores_list: list[dict[str, Any]],
) -> None:
    RELATED_FILE.parent.mkdir(parents=True, exist_ok=True)
    RELATED_FILE.write_text(
        json.dumps(related_map, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    SCORES_FILE.write_text(
        json.dumps(scores_list, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {RELATED_FILE.relative_to(ROOT)} ({len(related_map)} entries)")
    print(f"Wrote {SCORES_FILE.relative_to(ROOT)} ({len(scores_list)} entries)")


def rebuild_related(*, write: bool = True, use_embeddings: bool = True) -> tuple[dict, list]:
    posts = load_posts()
    print(f"Loaded {len(posts)} posts from {', '.join(CONTENT_SECTIONS)}.")
    if len(posts) < 2:
        empty: dict = {}
        if write:
            write_outputs(empty, [])
        return empty, []

    related_map, scores_list = build_indexes(posts, use_embeddings=use_embeddings)
    if write:
        write_outputs(related_map, scores_list)
    return related_map, scores_list