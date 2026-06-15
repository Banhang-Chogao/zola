#!/usr/bin/env python3
"""
Internal linking suggester cho blog Zola.

Workflow:
  1. Embed mỗi bài (title + body) → doc embedding
  2. Cho mỗi bài, split body thành paragraph
  3. Embed mỗi paragraph → query embedding
  4. Cosine sim với mọi bài KHÁC, lấy top-N candidates qua threshold
  5. Filter: paragraph đã có link tới target (regex /posting/<slug>/)
     hoặc đã chứa title target → skip
  6. Output data/link_suggestions.json + human-readable markdown stdout

Lý do: bài cũ thường chỉ có 1-2 cross-link ở cuối. Script này tìm chỗ
chèn link giữa bài (topical authority boost cho SEO). Ông review tay
rồi insert thủ công.

Run:
  python scripts/build_internal_links.py
  python scripts/build_internal_links.py --min-score 0.55 --top-k 2
  python scripts/build_internal_links.py --output - --no-json  # stdout only
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content" / "posting"
OUTPUT_FILE = ROOT / "data" / "link_suggestions.json"
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

DEFAULT_TOP_K = 2          # max candidate / paragraph
DEFAULT_MIN_SCORE = 0.5    # cosine threshold
MIN_PARA_LEN = 80          # bỏ qua paragraph ngắn (heading, divider...)
PARA_EXCERPT_LEN = 140     # độ dài excerpt in ra report


def strip_md(text: str) -> str:
    text = re.sub(r"```[\s\S]*?```", " ", text)
    text = re.sub(r"`[^`]+`", " ", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[*_#>~|]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_post(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("+++"):
        return {}, text
    m = re.match(r"^\+\+\+\s*\n(.*?)\n\+\+\+\s*\n?(.*)$", text, re.DOTALL)
    if not m:
        return {}, text
    try:
        return tomllib.loads(m.group(1)), m.group(2)
    except tomllib.TOMLDecodeError:
        return {}, m.group(2)


def split_paragraphs(body: str) -> list[str]:
    """Split body theo `\\n\\n`, bỏ heading / code block / shortcode."""
    # Loại code block trước khi split (giữ ranh giới paragraph)
    body = re.sub(r"```[\s\S]*?```", "", body)
    raw = [p.strip() for p in re.split(r"\n\s*\n", body)]
    out = []
    for p in raw:
        if not p:
            continue
        # Bỏ heading thuần
        if re.match(r"^#{1,6}\s", p):
            continue
        # Bỏ HTML shortcode / comment
        if p.startswith("<!--") or p.startswith("<"):
            continue
        # Bỏ divider / blockquote-only
        if re.match(r"^[-=*_]{3,}$", p):
            continue
        clean = strip_md(p)
        if len(clean) >= MIN_PARA_LEN:
            out.append((p, clean))  # keep raw + clean
    return out


def already_linked(paragraph_raw: str, target_slug: str, target_title: str) -> bool:
    """Skip nếu paragraph đã có link tới target hoặc đã nêu title."""
    if f"/posting/{target_slug}/" in paragraph_raw:
        return True
    if f"/{target_slug}/" in paragraph_raw:
        return True
    # Title match: nếu phần lớn title đã xuất hiện trong paragraph
    title_words = [w for w in target_title.split() if len(w) > 4]
    if title_words:
        matches = sum(1 for w in title_words if w.lower() in paragraph_raw.lower())
        if matches / len(title_words) > 0.7:
            return True
    return False


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--top-k", type=int, default=DEFAULT_TOP_K,
                    help=f"Max candidate / paragraph (default {DEFAULT_TOP_K})")
    ap.add_argument("--min-score", type=float, default=DEFAULT_MIN_SCORE,
                    help=f"Cosine threshold (default {DEFAULT_MIN_SCORE})")
    ap.add_argument("--output", type=Path, default=OUTPUT_FILE,
                    help="JSON output path. '-' = stdout")
    ap.add_argument("--no-json", action="store_true",
                    help="Không ghi JSON, chỉ in markdown report")
    args = ap.parse_args()

    posts = []
    for path in sorted(CONTENT_DIR.glob("*.md")):
        if path.name.startswith("_"):
            continue
        meta, body = parse_post(path)
        if not meta:
            continue
        posts.append({
            "slug": path.stem,
            "title": meta.get("title", path.stem),
            "body": body,
            "doc_text": f"{meta.get('title','')}. {strip_md(body)[:2000]}",
        })

    print(f"Loaded {len(posts)} posts", file=sys.stderr)
    if len(posts) < 2:
        print("Cần >=2 bài. Abort.", file=sys.stderr)
        sys.exit(1)

    print(f"Load model {MODEL_NAME}...", file=sys.stderr)
    model = SentenceTransformer(MODEL_NAME)
    doc_emb = model.encode(
        [p["doc_text"] for p in posts],
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    suggestions: list[dict] = []
    seen_pairs: set[tuple[str, str, int]] = set()

    for i, p in enumerate(posts):
        paragraphs = split_paragraphs(p["body"])
        if not paragraphs:
            continue
        para_texts = [clean for _, clean in paragraphs]
        para_emb = model.encode(para_texts, normalize_embeddings=True,
                                show_progress_bar=False)
        # similarities: shape (n_paragraphs, n_docs)
        sims = para_emb @ doc_emb.T
        # Mask chính bài (self)
        sims[:, i] = -1.0

        for pi, (raw, clean) in enumerate(paragraphs):
            row = sims[pi]
            # Top-K candidates qua threshold
            top_idx = np.argsort(-row)[: args.top_k * 3]  # over-fetch để filter
            kept = 0
            for j in top_idx:
                if kept >= args.top_k:
                    break
                score = float(row[j])
                if score < args.min_score:
                    break
                target = posts[j]
                if already_linked(raw, target["slug"], target["title"]):
                    continue
                key = (p["slug"], target["slug"], pi)
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)
                suggestions.append({
                    "source_slug": p["slug"],
                    "source_title": p["title"],
                    "paragraph_index": pi,
                    "paragraph_excerpt": clean[:PARA_EXCERPT_LEN]
                                         + ("…" if len(clean) > PARA_EXCERPT_LEN else ""),
                    "target_slug": target["slug"],
                    "target_title": target["title"],
                    "score": round(score, 3),
                    "markdown_hint": f"[{target['title']}](/posting/{target['slug']}/)",
                })
                kept += 1

    suggestions.sort(key=lambda s: (-s["score"], s["source_slug"]))

    # ===== Human report =====
    print("\n" + "=" * 70)
    print(f"INTERNAL LINK SUGGESTIONS — {len(suggestions)} chỗ "
          f"(threshold={args.min_score}, top-k={args.top_k}/para)")
    print("=" * 70)
    by_src: dict[str, list[dict]] = {}
    for s in suggestions:
        by_src.setdefault(s["source_slug"], []).append(s)
    for src, items in by_src.items():
        print(f"\n## {src} ({len(items)} suggestion)")
        for s in items:
            print(f"  para #{s['paragraph_index']:>2}  →  "
                  f"{s['target_slug']:<40}  score={s['score']}")
            print(f"    excerpt: {s['paragraph_excerpt']}")
            print(f"    insert : {s['markdown_hint']}")

    if not args.no_json:
        out_path = args.output
        payload = {
            "threshold": args.min_score,
            "top_k": args.top_k,
            "total": len(suggestions),
            "suggestions": suggestions,
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
