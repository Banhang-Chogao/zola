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
import tomllib
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


def parse_post(path: Path) -> tuple[dict, str]:
    """Zola dùng TOML frontmatter (+++) còn python-frontmatter default YAML.
    Detect format theo prefix → TOML qua tomllib stdlib, YAML qua frontmatter."""
    text = path.read_text(encoding="utf-8")
    if text.startswith("+++"):
        m = re.match(r"^\+\+\+\s*\n(.*?)\n\+\+\+\s*\n?(.*)$", text, re.DOTALL)
        if not m:
            return {}, text
        try:
            return tomllib.loads(m.group(1)), m.group(2)
        except tomllib.TOMLDecodeError as e:
            print(f"WARN: TOML parse fail {path.name}: {e}", file=sys.stderr)
            return {}, m.group(2)
    if text.startswith("---"):
        post = frontmatter.loads(text)
        return post.metadata, post.content
    return {}, text


def load_posts():
    posts = []
    if not CONTENT_DIR.exists():
        print(f"WARN: {CONTENT_DIR} does not exist.")
        return posts
    for path in sorted(CONTENT_DIR.glob("*.md")):
        if path.name.startswith("_"):
            continue
        try:
            meta, content = parse_post(path)
        except Exception as e:
            print(f"WARN: skip {path.name}: {e}", file=sys.stderr)
            continue
        slug = meta.get("slug") or path.stem
        title = meta.get("title", "") or ""
        date = meta.get("date", "")
        # date có thể là datetime object hoặc string → normalize
        date_str = date.isoformat() if hasattr(date, "isoformat") else str(date)
        tags = meta.get("taxonomies", {}).get("tags", [])
        cats = meta.get("taxonomies", {}).get("categories", [])
        body = strip_markdown(content)
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


def load_model(name: str):
    """Nạp SBERT model resilient với lỗi HF Hub 429 (Too Many Requests).

    transformers bản mới gọi model_info() ONLINE (qua _patch_mistral_regex /
    is_base_mistral) mỗi khi nhận repo-id → schedule chạy dày dễ dính 429, fail
    cả build. Workaround độc lập version: resolve snapshot model từ CACHE CỤC BỘ
    (đã được actions/cache khôi phục) rồi nạp bằng ĐƯỜNG DẪN local → transformers
    coi là local, BỎ QUA hẳn call online. Cold cache → tải online + retry backoff.
    """
    import time
    from huggingface_hub import snapshot_download

    # 1. Ưu tiên cache cục bộ — 0 network call, tránh 429 hoàn toàn.
    try:
        local_dir = snapshot_download(name, local_files_only=True)
        print(f"Model load từ cache cục bộ: {local_dir}")
        return SentenceTransformer(local_dir)
    except Exception as e:
        print(f"Chưa có cache cục bộ ({e}); chuyển sang tải online + retry...",
              file=sys.stderr)

    # 2. Cold cache: tải online, retry exponential backoff khi gặp 429/lỗi mạng.
    last_err = None
    for attempt in range(1, 5):
        try:
            local_dir = snapshot_download(name)
            return SentenceTransformer(local_dir)
        except Exception as e:
            last_err = e
            wait = 2 ** attempt
            print(f"Tải model lần {attempt} lỗi: {e}; chờ {wait}s rồi thử lại...",
                  file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"Không nạp được model sau 4 lần thử: {last_err}")


def main():
    posts = load_posts()
    print(f"Loaded {len(posts)} posts.")
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    if len(posts) < 2:
        OUTPUT_FILE.write_text("{}", encoding="utf-8")
        print("Need >=2 posts. Wrote empty index.")
        return

    print(f"Loading model: {MODEL_NAME}")
    model = load_model(MODEL_NAME)

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
