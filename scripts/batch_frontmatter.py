#!/usr/bin/env python3
"""
Batch frontmatter enhancer cho bài cũ trong content/posting/.

Use case: blog ông đã có 12 bài, một vài bài thiếu `description` hoặc
tags nghèo (vd syntax-highlight.md). Script này quét toàn pool, detect
bài "weak metadata", gọi LiteLLM mode=frontmatter để regenerate
description + tags, GIỮ NGUYÊN body.

ROI cao nhất, rủi ro thấp nhất → chạy đầu tiên trong roadmap AI pipeline.

Run:
  # Dry-run (default): in diff ra terminal, không sửa file
  python scripts/batch_frontmatter.py

  # Apply: sửa thật, có prompt confirm trước mỗi file
  python scripts/batch_frontmatter.py --apply

  # Force-regen toàn bộ không quan tâm "weak" detection
  python scripts/batch_frontmatter.py --all --apply

Criteria detect "weak":
  - Thiếu key `description` HOẶC description rỗng / < 50 ký tự
  - HOẶC tags count < 4
"""
from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

# Reuse logic content_gen.py để không duplicate code
sys.path.insert(0, str(Path(__file__).resolve().parent))
from content_gen import (  # noqa: E402
    CATEGORIES,
    CONTENT_DIR,
    DEFAULT_LLM,
    StyleRetriever,
    build_chain,
    build_frontmatter,
    format_examples,
    parse_post,
    parse_llm_output,
    MODE_INSTRUCTIONS,
)

MIN_DESC_LEN = 50
MIN_TAGS = 4


def is_weak(meta: dict) -> tuple[bool, str]:
    """Trả (True, lý do) nếu metadata 'weak' cần regen."""
    desc = (meta.get("description") or "").strip()
    tags = (meta.get("taxonomies") or {}).get("tags") or []
    if not desc:
        return True, "thiếu description"
    if len(desc) < MIN_DESC_LEN:
        return True, f"description quá ngắn ({len(desc)} chars)"
    if len(tags) < MIN_TAGS:
        return True, f"chỉ có {len(tags)} tags (<{MIN_TAGS})"
    return False, ""


def detect_category_slug(meta: dict) -> str:
    """Map từ display name trong taxonomies về category slug của prompt library."""
    cats = (meta.get("taxonomies") or {}).get("categories") or []
    cat_display = cats[0] if cats else ""
    rev = {v["display"]: k for k, v in CATEGORIES.items()}
    return rev.get(cat_display, "posting")


def regenerate_frontmatter(
    path: Path,
    meta: dict,
    body: str,
    retriever: StyleRetriever,
    model: str,
    top_k: int,
) -> dict:
    """Gọi LLM mode=frontmatter → trả dict {title, description, tags}."""
    category = detect_category_slug(meta)
    examples = retriever.retrieve(body[:2000], top_k=top_k, category=category)
    chain = build_chain(model, category, "frontmatter")
    # IDEA chứa cả title cũ + body để LLM giữ ngữ cảnh title gốc
    idea = f"TITLE_HIENTAI: {meta.get('title', '')}\n\nBODY:\n{body}"
    result = chain.invoke({
        "examples": format_examples(examples),
        "mode_instruction": MODE_INSTRUCTIONS["frontmatter"],
        "idea": idea,
    })
    return parse_llm_output(result)


def render_full_post(
    meta: dict,
    body: str,
    new_meta: dict,
) -> str:
    """Render lại file với frontmatter mới, body không đổi.

    Giữ title cũ nếu LLM trả title rỗng (mode=frontmatter chủ yếu sinh
    description + tags). Date / aliases / extra giữ nguyên từ meta cũ
    bằng cách build TOML thủ công thay vì dùng build_frontmatter().
    """
    title = new_meta.get("title") or meta.get("title", "")
    description = new_meta.get("description") or meta.get("description", "")
    tags = new_meta.get("tags") or (meta.get("taxonomies") or {}).get("tags", [])
    cats = (meta.get("taxonomies") or {}).get("categories") or ["Posting"]
    date = meta.get("date")
    date_str = date.isoformat() if hasattr(date, "isoformat") else str(date)
    aliases = meta.get("aliases") or []
    extra = meta.get("extra") or {}

    def _esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"')

    lines = [
        "+++",
        f'title = "{_esc(title)}"',
        f'description = "{_esc(description)}"',
        f"date = {date_str}",
    ]
    if aliases:
        lines.append("aliases = [" + ", ".join(f'"{a}"' for a in aliases) + "]")
    lines.append("")
    lines.append("[taxonomies]")
    lines.append("categories = [" + ", ".join(f'"{c}"' for c in cats) + "]")
    lines.append("tags = [" + ", ".join(f'"{t}"' for t in tags) + "]")
    if extra:
        lines.append("")
        lines.append("[extra]")
        for k, v in extra.items():
            if isinstance(v, bool):
                lines.append(f"{k} = {str(v).lower()}")
            elif isinstance(v, (int, float)):
                lines.append(f"{k} = {v}")
            else:
                lines.append(f'{k} = "{_esc(str(v))}"')
    lines.append("+++")
    lines.append("")
    return "\n".join(lines) + body.lstrip("\n")


def show_diff(path: Path, old: str, new: str) -> None:
    diff = difflib.unified_diff(
        old.splitlines(keepends=True),
        new.splitlines(keepends=True),
        fromfile=f"{path.name} (cũ)",
        tofile=f"{path.name} (mới)",
        n=2,
    )
    sys.stdout.writelines(diff)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true",
                    help="Ghi đè file thật. Default = dry-run in diff.")
    ap.add_argument("--all", action="store_true",
                    help="Regen mọi bài, bỏ qua filter 'weak'")
    ap.add_argument("--yes", action="store_true",
                    help="Không hỏi confirm từng file (chạy CI)")
    ap.add_argument("--model", default=DEFAULT_LLM)
    ap.add_argument("--top-k", type=int, default=3)
    args = ap.parse_args()

    print(f"Scan {CONTENT_DIR} ...")
    candidates = []
    for path in sorted(CONTENT_DIR.glob("*.md")):
        if path.name.startswith("_"):
            continue
        meta, body = parse_post(path)
        if not meta:
            continue
        weak, reason = is_weak(meta)
        if args.all or weak:
            candidates.append((path, meta, body, reason if weak else "force --all"))

    if not candidates:
        print("✓ Không có bài nào cần regen frontmatter.")
        return

    print(f"Cần regen: {len(candidates)} bài")
    for p, _, _, r in candidates:
        print(f"  - {p.name}  ({r})")

    print("\nLoading style retriever (sentence-transformers)...")
    retriever = StyleRetriever(CONTENT_DIR)

    for path, meta, body, reason in candidates:
        print(f"\n{'='*70}\n[{path.name}] {reason}")
        old_text = path.read_text(encoding="utf-8")
        try:
            new_meta = regenerate_frontmatter(
                path, meta, body, retriever, args.model, args.top_k,
            )
        except Exception as e:
            print(f"  ERROR: {e}", file=sys.stderr)
            continue
        if not new_meta.get("description") or not new_meta.get("tags"):
            print("  WARN: LLM không sinh đủ description/tags, skip")
            continue
        new_text = render_full_post(meta, body, new_meta)
        show_diff(path, old_text, new_text)

        if not args.apply:
            continue
        if not args.yes:
            ans = input(f"\nGhi đè {path.name}? [y/N] ")
            if ans.strip().lower() != "y":
                print("  skip.")
                continue
        path.write_text(new_text, encoding="utf-8")
        print(f"  ✓ written {path.relative_to(path.parents[1])}")


if __name__ == "__main__":
    main()
