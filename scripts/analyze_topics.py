#!/usr/bin/env python3
"""
Topic gap analysis cho blog Zola — cluster bài cũ theo embedding, phát
hiện cluster đang yếu để định hướng bài tiếp theo.

Workflow:
  1. Embed toàn bộ content/posting/*.md qua sentence-transformers
  2. K-means cluster (auto-pick k bằng silhouette score, k in 2..6)
  3. Mỗi cluster:
     - List bài thành viên + category gốc
     - Extract top keywords (TF-IDF)
     - Tính density (bao nhiêu bài / tổng)
  4. Output:
     - data/topic_map.json (machine-readable)
     - Bảng + Mermaid diagram stdout (paste vào /insights)

Run:
  python scripts/analyze_topics.py
  python scripts/analyze_topics.py --k 4              # ép k cụ thể
  python scripts/analyze_topics.py --output - --no-json   # in console only
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.feature_extraction.text import TfidfVectorizer

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content" / "posting"
OUTPUT_FILE = ROOT / "data" / "topic_map.json"
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

# Stopwords tiếng Việt + Anh tối thiểu — TF-IDF đã loại frequency thấp
# nhưng cần cản các từ chức năng cao tần
STOPWORDS = {
    "mình", "của", "cho", "với", "thì", "là", "có", "và", "nhưng", "khi",
    "này", "đó", "kia", "ấy", "vậy", "nhé", "nhỉ", "đã", "sẽ", "đang",
    "không", "rất", "quá", "lắm", "chỉ", "vừa", "mới", "thôi", "luôn",
    "the", "and", "for", "with", "that", "this", "from", "but", "you",
    "are", "was", "were", "have", "has", "can", "will", "all", "one",
    "two", "khi", "nên", "ai", "gì", "nào", "sao",
}


def parse_post_minimal(path: Path) -> tuple[str, str, list[str]]:
    """Trả (title, body_clean, tags). Đơn giản hoá vs content_gen để chạy độc lập."""
    import tomllib
    text = path.read_text(encoding="utf-8")
    title, tags, body = path.stem, [], text
    if text.startswith("+++"):
        m = re.match(r"^\+\+\+\s*\n(.*?)\n\+\+\+\s*\n?(.*)$", text, re.DOTALL)
        if m:
            try:
                meta = tomllib.loads(m.group(1))
                title = meta.get("title", title)
                tags = (meta.get("taxonomies") or {}).get("tags") or []
            except tomllib.TOMLDecodeError:
                pass
            body = m.group(2)
    # strip markdown
    body = re.sub(r"```[\s\S]*?```", " ", body)
    body = re.sub(r"`[^`]+`", " ", body)
    body = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", body)
    body = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", body)
    body = re.sub(r"<[^>]+>", " ", body)
    body = re.sub(r"[*_#>~|]+", " ", body)
    body = re.sub(r"\s+", " ", body).strip()
    return title, body, tags


def load_posts() -> list[dict]:
    posts = []
    for path in sorted(CONTENT_DIR.glob("*.md")):
        if path.name.startswith("_"):
            continue
        title, body, tags = parse_post_minimal(path)
        if not body or len(body) < 100:
            continue
        posts.append({
            "slug": path.stem,
            "title": title,
            "body": body[:3000],
            "tags": tags,
        })
    return posts


def pick_k(embeddings: np.ndarray, k_range: range) -> int:
    """Pick k cho k-means qua silhouette score."""
    best_k, best_score = k_range.start, -1.0
    for k in k_range:
        if k >= len(embeddings):
            break
        km = KMeans(n_clusters=k, random_state=42, n_init=10).fit(embeddings)
        score = silhouette_score(embeddings, km.labels_)
        if score > best_score:
            best_score, best_k = score, k
    return best_k


def extract_keywords(texts: list[str], top_n: int = 5) -> list[str]:
    """TF-IDF top-N keyword cho 1 cluster (gộp các text trong cluster)."""
    if not texts:
        return []
    blob = " ".join(texts).lower()
    vec = TfidfVectorizer(
        max_features=200,
        ngram_range=(1, 2),
        token_pattern=r"(?u)\b[a-zA-Zà-ỹÀ-Ỹ]{3,}\b",
    )
    try:
        tfidf = vec.fit_transform([blob])
    except ValueError:
        return []
    scores = tfidf.toarray()[0]
    terms = vec.get_feature_names_out()
    ranked = sorted(zip(scores, terms), reverse=True)
    out = []
    for s, t in ranked:
        if s <= 0:
            break
        if t in STOPWORDS or any(w in STOPWORDS for w in t.split()):
            continue
        out.append(t)
        if len(out) >= top_n:
            break
    return out


def render_mermaid(clusters: list[dict]) -> str:
    """Mermaid mindmap node graph (paste vào markdown trong /insights)."""
    lines = ["```mermaid", "mindmap", "  root((Blog Duy Nguyen))"]
    for c in clusters:
        topic = c["topic"]
        density_pct = round(c["density"] * 100)
        lines.append(f"    {topic} [{density_pct}%]")
        for slug in c["posts"][:3]:  # show top 3 per cluster
            lines.append(f"      {slug}")
        if len(c["posts"]) > 3:
            lines.append(f"      ...{len(c['posts']) - 3} bài khác")
    lines.append("```")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--k", type=int, help="Ép số cluster (default: silhouette auto)")
    ap.add_argument("--top-keywords", type=int, default=5,
                    help="Số keyword extract mỗi cluster")
    ap.add_argument("--output", type=Path, default=OUTPUT_FILE,
                    help="Path JSON output. '-' = stdout")
    ap.add_argument("--no-json", action="store_true",
                    help="Không ghi JSON, chỉ in bảng + Mermaid")
    args = ap.parse_args()

    posts = load_posts()
    print(f"Loaded {len(posts)} posts", file=sys.stderr)
    if len(posts) < 3:
        print("Cần >=3 bài để cluster. Abort.", file=sys.stderr)
        sys.exit(1)

    print(f"Loading model {MODEL_NAME}...", file=sys.stderr)
    model = SentenceTransformer(MODEL_NAME)
    texts = [f"{p['title']}. {p['body']}" for p in posts]
    print("Encoding...", file=sys.stderr)
    embeddings = model.encode(texts, normalize_embeddings=True,
                              show_progress_bar=False)

    if args.k:
        k = args.k
    else:
        # Range hợp lý cho blog cá nhân: 2-6 cluster
        k_max = min(6, len(posts) - 1)
        k = pick_k(embeddings, range(2, k_max + 1))
    print(f"Cluster k={k}", file=sys.stderr)

    km = KMeans(n_clusters=k, random_state=42, n_init=10).fit(embeddings)
    labels = km.labels_

    clusters = []
    for ci in range(k):
        members = [posts[i] for i, lab in enumerate(labels) if lab == ci]
        if not members:
            continue
        keywords = extract_keywords([m["body"] for m in members],
                                    top_n=args.top_keywords)
        # tag dominance: tag xuất hiện nhiều nhất trong cluster
        tag_counter = Counter()
        for m in members:
            tag_counter.update(m["tags"])
        dominant_tags = [t for t, _ in tag_counter.most_common(5)]

        clusters.append({
            "id": ci,
            "topic": keywords[0] if keywords else f"cluster-{ci}",
            "keywords": keywords,
            "dominant_tags": dominant_tags,
            "density": len(members) / len(posts),
            "post_count": len(members),
            "posts": [m["slug"] for m in members],
        })

    clusters.sort(key=lambda c: -c["density"])

    # ===== Output =====
    print("\n" + "=" * 70)
    print(f"TOPIC MAP — {len(posts)} bài, {k} cluster")
    print("=" * 70)
    for c in clusters:
        print(f"\n[{c['post_count']:>2} bài | {c['density']:>4.0%}] {c['topic'].upper()}")
        print(f"  keywords: {', '.join(c['keywords'])}")
        if c["dominant_tags"]:
            print(f"  tags    : {', '.join(c['dominant_tags'])}")
        for slug in c["posts"]:
            print(f"    - {slug}")

    print("\n" + "=" * 70)
    print("MERMAID (paste vào content/insights/_index.md hoặc bài /insights):")
    print("=" * 70)
    print(render_mermaid(clusters))

    # Gap analysis: cluster nào yếu nhất → đề xuất viết thêm
    weakest = min(clusters, key=lambda c: c["density"])
    print("\n" + "=" * 70)
    print(f"GỢI Ý: cluster yếu nhất là '{weakest['topic'].upper()}' "
          f"({weakest['post_count']} bài, {weakest['density']:.0%}).")
    print(f"Cân nhắc viết thêm bài về: {', '.join(weakest['keywords'])}.")
    print("=" * 70)

    if not args.no_json:
        out_path = args.output
        payload = {
            "k": k,
            "total_posts": len(posts),
            "clusters": clusters,
            "weakest_cluster": weakest["id"],
        }
        if str(out_path) == "-":
            json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        else:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"\n✓ Wrote {out_path.relative_to(ROOT)}", file=sys.stderr)


if __name__ == "__main__":
    main()
