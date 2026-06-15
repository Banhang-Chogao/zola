"""
Build semantic related posts index using sentence-transformers.

Quét content/posting/*.md → generate multilingual embeddings → cosine
similarity → top-N related per post → output data/related.json.

Run locally:
    pip install -r scripts/requirements.txt
    python scripts/build_related.py

Run in CI:
    Triggered by .github/workflows/build-related.yml
    (weekly + on content push)
"""
import json
import re
import sys
from pathlib import Path

import frontmatter
import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content" / "posting"
OUTPUT_FILE = ROOT / "data" / "related.json"
SCORES_FILE = ROOT / "data" / "scores.json"

# Multilingual model: ~120MB, hỗ trợ Tiếng Việt tốt, đủ nhanh cho blog
# vài chục bài. Có thể đổi thành paraphrase-multilingual-mpnet-base-v2
# (~500MB) cho accuracy cao hơn nhưng build chậm gấp 3.
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
TOP_N = 5
MIN_SCORE = 0.15  # filter junk pairs


def strip_markdown(text: str) -> str:
    text = re.sub(r"```[\s\S]*?```", " ", text)
    text = re.sub(r"`[^`]+`", " ", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[*_#>~|]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def load_posts():
    posts = []
    if not CONTENT_DIR.exists():
        print(f"WARN: {CONTENT_DIR} does not exist.")
        return posts
    for path in sorted(CONTENT_DIR.glob("*.md")):
        if path.name.startswith("_"):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                post = frontmatter.load(f)
        except Exception as e:
            print(f"WARN: skip {path.name}: {e}", file=sys.stderr)
            continue
        slug = post.metadata.get("slug") or path.stem
        title = post.metadata.get("title", "")
        date = post.metadata.get("date", "")
        # date có thể là datetime object hoặc string → normalize
        date_str = date.isoformat() if hasattr(date, "isoformat") else str(date)
        tags = post.metadata.get("taxonomies", {}).get("tags", [])
        cats = post.metadata.get("taxonomies", {}).get("categories", [])
        body = strip_markdown(post.content)
        # Concat title + cats + tags + body (cap 2000 chars để fit model
        # context 512 tokens, model tự truncate phần dư)
        text_parts = [title, " ".join(cats), " ".join(tags), body[:2000]]
        text = ". ".join(p for p in text_parts if p)
        posts.append({
            "slug": slug,
            "text": text,
            "title": title,
            "date": date_str,
        })
    return posts


def main():
    posts = load_posts()
    print(f"Loaded {len(posts)} posts.")
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    if len(posts) < 2:
        OUTPUT_FILE.write_text("{}", encoding="utf-8")
        print("Need >=2 posts. Wrote empty index.")
        return

    print(f"Loading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    print("Encoding...")
    embeddings = model.encode(
        [p["text"] for p in posts],
        show_progress_bar=True,
        normalize_embeddings=True,
        batch_size=16,
    )

    # Normalized vectors → cosine = dot product
    sim = np.dot(embeddings, embeddings.T)

    result = {}
    for i, post in enumerate(posts):
        scores = sim[i].copy()
        scores[i] = -1.0  # exclude self
        top_idx = np.argsort(scores)[::-1][:TOP_N]
        related = [
            {"slug": posts[j]["slug"], "score": round(float(scores[j]), 4)}
            for j in top_idx
            if scores[j] >= MIN_SCORE
        ]
        result[post["slug"]] = related

    OUTPUT_FILE.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT_FILE.relative_to(ROOT)} ({len(result)} entries)")

    # ===== SCORING CARD: per-post aggregate scores =====
    # score = mean of top-N related scores → đo "connectedness" của bài
    # trong network. High score = bài có nhiều bài tương đồng nội dung.
    scores_list = []
    for post in posts:
        related = result.get(post["slug"], [])
        if related:
            avg = sum(r["score"] for r in related) / len(related)
            top = max(r["score"] for r in related)
        else:
            avg = 0.0
            top = 0.0
        scores_list.append({
            "slug": post["slug"],
            "title": post["title"],
            "date": post["date"],
            "score": round(avg, 4),
            "top_score": round(top, 4),
            "neighbors": len(related),
        })
    # Sort score desc cho default render
    scores_list.sort(key=lambda x: x["score"], reverse=True)
    SCORES_FILE.write_text(
        json.dumps(scores_list, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {SCORES_FILE.relative_to(ROOT)} ({len(scores_list)} entries)")


if __name__ == "__main__":
    main()
