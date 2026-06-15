#!/usr/bin/env python3
"""
Style consistency QA gate — kiểm tra bản nháp có khớp văn phong category.

Workflow:
  1. Embed mọi bài cũ trong content/posting/, gom theo category display
     name (Du lịch / Công nghệ / Ẩm thực / Posting / ...)
  2. Tính centroid embedding mỗi category = mean(embeddings)
  3. Với mỗi file input:
     - Detect category từ frontmatter taxonomies.categories[0]
     - Embed body
     - Cosine vs centroid của chính category đó = style_score
     - Cosine vs MỌI centroid → tìm category gần nhất thực tế
  4. Cảnh báo nếu:
     - style_score < threshold (default 0.55)
     - HOẶC category gần nhất khác category khai báo (mis-categorize)

Use case:
  - Chạy thủ công sau khi viết draft, trước khi commit
  - Tích hợp pre-commit hook local (xem ví dụ cuối docstring)
  - Bắt sớm bản nháp AI-sinh quá đồng nhất hoặc bản tay đi lạc tone

Run:
  python scripts/qa_style.py content/posting/new-post.md
  python scripts/qa_style.py drafts/*.md --threshold 0.5
  python scripts/qa_style.py drafts/x.md --strict   # exit 1 nếu drift

Tích hợp pre-commit local (không push vào repo's .pre-commit-config.yaml
vì nặng dep): tạo `.git/hooks/pre-commit` hoặc thêm vào local config:

    - repo: local
      hooks:
        - id: qa-style
          name: QA style consistency
          entry: python scripts/qa_style.py
          language: system
          files: ^content/posting/.*\\.md$
          pass_filenames: true
"""
from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content" / "posting"
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

DEFAULT_THRESHOLD = 0.55  # cosine < threshold → warn drift
MIN_CATEGORY_SIZE = 2     # category cần >=2 bài mới tính centroid tin cậy


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


def get_category(meta: dict) -> str:
    cats = (meta.get("taxonomies") or {}).get("categories") or []
    return cats[0] if cats else ""


def compute_centroids(
    model: SentenceTransformer,
) -> tuple[dict[str, np.ndarray], dict[str, list[str]]]:
    """Embed mọi bài cũ, gom theo category, tính centroid."""
    by_cat: dict[str, list[tuple[str, str]]] = {}
    for path in sorted(CONTENT_DIR.glob("*.md")):
        if path.name.startswith("_"):
            continue
        meta, body = parse_post(path)
        if not meta:
            continue
        cat = get_category(meta)
        if not cat:
            continue
        clean = strip_md(body)[:2000]
        if len(clean) < 100:
            continue
        by_cat.setdefault(cat, []).append((path.stem, clean))

    centroids: dict[str, np.ndarray] = {}
    members: dict[str, list[str]] = {}
    for cat, items in by_cat.items():
        if len(items) < MIN_CATEGORY_SIZE:
            print(f"  WARN: category '{cat}' chỉ {len(items)} bài, skip centroid",
                  file=sys.stderr)
            continue
        emb = model.encode([t for _, t in items], normalize_embeddings=True,
                           show_progress_bar=False)
        # Mean rồi re-normalize để giữ cosine sim valid
        centroid = emb.mean(axis=0)
        norm = np.linalg.norm(centroid)
        if norm > 0:
            centroid = centroid / norm
        centroids[cat] = centroid
        members[cat] = [slug for slug, _ in items]
    return centroids, members


def analyze_file(
    path: Path,
    model: SentenceTransformer,
    centroids: dict[str, np.ndarray],
    threshold: float,
) -> dict:
    meta, body = parse_post(path)
    declared_cat = get_category(meta)
    clean = strip_md(body)[:2000]
    if len(clean) < 100:
        return {"path": path, "error": "body quá ngắn (<100 chars)"}

    emb = model.encode([clean], normalize_embeddings=True,
                       show_progress_bar=False)[0]
    scores = {cat: float(emb @ c) for cat, c in centroids.items()}
    nearest_cat = max(scores, key=scores.get) if scores else None

    declared_score = scores.get(declared_cat)
    return {
        "path": path,
        "declared_category": declared_cat or "(không có)",
        "declared_score": declared_score,
        "nearest_category": nearest_cat,
        "nearest_score": scores.get(nearest_cat) if nearest_cat else None,
        "all_scores": scores,
        "passed": (
            declared_score is not None
            and declared_score >= threshold
            and (nearest_cat == declared_cat or scores[nearest_cat] - declared_score < 0.05)
        ),
    }


def print_report(result: dict, threshold: float) -> None:
    path = result["path"]
    if "error" in result:
        print(f"[{path}] ERROR: {result['error']}")
        return

    declared = result["declared_category"]
    d_score = result["declared_score"]
    nearest = result["nearest_category"]
    n_score = result["nearest_score"]

    status = "✓ OK" if result["passed"] else "✗ DRIFT"
    print(f"\n[{path}] category={declared}  {status}")

    if d_score is None:
        print(f"  WARN: không có centroid cho category '{declared}' "
              "(category mới hoặc < 2 bài trong pool)")
    else:
        bar = _bar(d_score, threshold)
        print(f"  Style score: {d_score:.3f} (threshold {threshold})  {bar}")

    if nearest and nearest != declared:
        delta = (n_score or 0) - (d_score or 0)
        marker = "← gợi ý re-categorize" if delta > 0.05 else ""
        print(f"  Nearest centroid: {nearest} ({n_score:.3f})  {marker}")

    if len(result["all_scores"]) > 1:
        print("  All scores:")
        for cat, sc in sorted(result["all_scores"].items(), key=lambda x: -x[1]):
            print(f"    - {cat:<20} {sc:.3f}")


def _bar(score: float, threshold: float, width: int = 20) -> str:
    filled = int(min(max(score, 0), 1) * width)
    bar = "█" * filled + "░" * (width - filled)
    mark = "✓" if score >= threshold else "✗"
    return f"[{bar}] {mark}"


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("files", nargs="+", type=Path,
                    help="File .md cần check (1 hoặc nhiều)")
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                    help=f"Cosine threshold (default {DEFAULT_THRESHOLD})")
    ap.add_argument("--strict", action="store_true",
                    help="Exit 1 nếu có file drift (default: warn-only, exit 0)")
    args = ap.parse_args()

    # Validate inputs
    for f in args.files:
        if not f.exists():
            print(f"ERROR: file not found: {f}", file=sys.stderr)
            sys.exit(2)

    print(f"Load model {MODEL_NAME} + compute centroids...", file=sys.stderr)
    model = SentenceTransformer(MODEL_NAME)
    centroids, members = compute_centroids(model)
    if not centroids:
        print("ERROR: không tính được centroid nào. Pool quá nhỏ?",
              file=sys.stderr)
        sys.exit(2)

    print(f"Centroids: {len(centroids)} category", file=sys.stderr)
    for cat, ms in members.items():
        print(f"  - {cat}: {len(ms)} bài", file=sys.stderr)

    fail_count = 0
    for f in args.files:
        result = analyze_file(f, model, centroids, args.threshold)
        print_report(result, args.threshold)
        if "error" not in result and not result["passed"]:
            fail_count += 1

    print(f"\n{'=' * 50}")
    if fail_count == 0:
        print(f"✓ {len(args.files)} file đều OK.")
        sys.exit(0)
    print(f"✗ {fail_count}/{len(args.files)} file drift văn phong.")
    if args.strict:
        sys.exit(1)
    print("(warn-only, exit 0 — dùng --strict để fail commit)")
    sys.exit(0)


if __name__ == "__main__":
    main()
