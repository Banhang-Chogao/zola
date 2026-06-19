#!/usr/bin/env python3
"""
Strip premium post bodies before Zola build — full content → private_content/.

Usage:
  python3 scripts/paywall_prepare_build.py --strip   # before zola build
  python3 scripts/paywall_prepare_build.py --restore # after build (local dev)

Reads Zola TOML frontmatter (+++): premium, premium_post_id, premium_teaser_words
"""

from __future__ import annotations

import argparse
import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
PRIVATE = ROOT / "private_content"
BACKUP = ROOT / "data" / ".paywall-content-backup.json"
CONFIG = ROOT / "config.toml"

PREMIUM_CATEGORY = "premium"
DEFAULT_PREMIUM_PRICE = 100_000
MORE_MARKER = "<!-- more -->"


def _parse_zola_md(text: str) -> tuple[dict, str, str] | None:
    """Return (metadata, body, frontmatter_block) or None if not Zola TOML."""
    if not text.startswith("+++"):
        return None
    end = text.find("+++", 3)
    if end == -1:
        return None
    fm_block = text[: end + 3]
    body = text[end + 3 :].lstrip("\n")
    meta = tomllib.loads(fm_block[3:-3].strip())
    return meta, body, fm_block


def _write_zola_md(path: Path, fm_block: str, body: str) -> None:
    path.write_text(fm_block + "\n\n" + body, encoding="utf-8")


def _split_more(body: str) -> tuple[str, str]:
    """Tách phần public (trước <!-- more -->) và phần premium (sau)."""
    if MORE_MARKER in body:
        head, tail = body.split(MORE_MARKER, 1)
        return head.strip(), tail.strip()
    return body.strip(), ""


def _premium_lock_enabled() -> bool:
    """enable_premium_lock ưu tiên; fallback premium_hidden (deprecated)."""
    if not CONFIG.exists():
        return False
    extra = tomllib.loads(CONFIG.read_text(encoding="utf-8")).get("extra") or {}
    if "enable_premium_lock" in extra:
        return bool(extra["enable_premium_lock"])
    return bool(extra.get("premium_hidden", False))


def _teaser(body: str, words: int) -> str:
    public, _premium = _split_more(body)
    tokens = re.split(r"(\s+)", public)
    word_count = 0
    out: list[str] = []
    for tok in tokens:
        if tok.strip():
            word_count += 1
        out.append(tok)
        if word_count >= words:
            break
    text = "".join(out).strip()
    if len(public) > len(text):
        text += "\n\n…"
    return text


def _has_premium_category(meta: dict) -> bool:
    tax = meta.get("taxonomies") or {}
    cats = tax.get("categories") or []
    return PREMIUM_CATEGORY in cats


def _is_premium(meta: dict) -> bool:
    extra = meta.get("extra") or {}
    if meta.get("premium") or extra.get("premium"):
        return True
    return _has_premium_category(meta)


def _inject_premium_flags(fm_block: str, meta: dict) -> str:
    """Ensure [extra] premium + price for category-based posts (Zola template reads extra)."""
    if not _has_premium_category(meta):
        return fm_block
    extra = meta.get("extra") or {}
    if extra.get("premium"):
        return fm_block
    block = fm_block
    if "premium = true" not in block:
        block = block.replace("[extra]\n", "[extra]\npremium = true\n", 1)
    price_line = f"price = {DEFAULT_PREMIUM_PRICE}"
    if price_line not in block and "price =" not in block:
        block = block.replace("[extra]\n", f"[extra]\n{price_line}\n", 1)
    return block


def _premium_meta(meta: dict) -> dict:
    extra = meta.get("extra") or {}
    merged = {**extra, **{k: v for k, v in meta.items() if k != "extra"}}
    return merged


def find_premium_posts() -> list[Path]:
    posts: list[Path] = []
    for md in CONTENT.rglob("*.md"):
        if md.name == "_index.md":
            continue
        parsed = _parse_zola_md(md.read_text(encoding="utf-8"))
        if parsed and _is_premium(parsed[0]):
            posts.append(md)
    return posts


def _full_body_for_publish(current_body: str, post_id: str) -> str:
    """Ghép nội dung đầy đủ từ private_content/ khi premium lock tắt."""
    private_path = PRIVATE / f"{post_id}.md"
    if not private_path.exists():
        return current_body
    private_body = private_path.read_text(encoding="utf-8").strip()
    if MORE_MARKER in current_body:
        head, _ = current_body.split(MORE_MARKER, 1)
        return f"{head.strip()}\n\n{MORE_MARKER}\n\n{private_body}"
    return private_body


def publish_premium() -> int:
    """Merge private_content → content/ cho build public (lock tắt)."""
    backup: dict[str, str] = {}
    count = 0

    for md in find_premium_posts():
        parsed = _parse_zola_md(md.read_text(encoding="utf-8"))
        if not parsed:
            continue
        meta, body, fm_block = parsed
        pm = _premium_meta(meta)
        post_id = pm.get("premium_post_id") or pm.get("slug") or md.stem
        backup[str(md.relative_to(ROOT))] = body
        full_body = _full_body_for_publish(body, post_id)
        _write_zola_md(md, fm_block, full_body)
        count += 1

    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    BACKUP.write_text(json.dumps(backup, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"paywall_prepare: published {count} premium posts (full content, lock off)")
    return count


def strip_premium() -> int:
    PRIVATE.mkdir(parents=True, exist_ok=True)
    backup: dict[str, str] = {}
    count = 0

    for md in find_premium_posts():
        parsed = _parse_zola_md(md.read_text(encoding="utf-8"))
        if not parsed:
            continue
        meta, body, fm_block = parsed
        pm = _premium_meta(meta)
        _public, premium_body = _split_more(body)
        post_id = pm.get("premium_post_id") or pm.get("slug") or md.stem
        teaser_words = int(pm.get("premium_teaser_words", 180))

        # Persist the FULL premium body to private_content/ for the backend — but
        # NEVER clobber existing full content with a teaser. Source of truth for a
        # post can be either:
        #   (a) content/ holds teaser + "<!-- more -->" + full body → store the
        #       part after the marker, or
        #   (b) content/ holds only the teaser and private_content/ already has
        #       the full body → keep private_content/ as-is (do not overwrite).
        private_path = PRIVATE / f"{post_id}.md"
        if premium_body:
            private_path.write_text(premium_body, encoding="utf-8")
        elif not private_path.exists():
            # No marker and no stored full body yet → fall back to whole body so
            # the backend has something to serve.
            private_path.write_text(body, encoding="utf-8")
        # else: content/ is teaser-only and private_content/ already holds the
        # full body → preserve it untouched.

        backup[str(md.relative_to(ROOT))] = body
        fm_out = _inject_premium_flags(fm_block, meta)
        _write_zola_md(md, fm_out, _teaser(body, teaser_words))
        count += 1

    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    BACKUP.write_text(json.dumps(backup, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"paywall_prepare: stripped {count} premium posts → private_content/")
    return count


def restore_premium() -> int:
    if not BACKUP.exists():
        print("paywall_prepare: no backup to restore")
        return 0
    backup = json.loads(BACKUP.read_text(encoding="utf-8"))
    for rel, body in backup.items():
        md = ROOT / rel
        if not md.exists():
            continue
        parsed = _parse_zola_md(md.read_text(encoding="utf-8"))
        if not parsed:
            continue
        _, _, fm_block = parsed
        _write_zola_md(md, fm_block, body)
    BACKUP.unlink(missing_ok=True)
    print(f"paywall_prepare: restored {len(backup)} posts")
    return len(backup)


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--strip", action="store_true")
    group.add_argument("--restore", action="store_true")
    args = parser.parse_args()

    if args.strip:
        if _premium_lock_enabled():
            strip_premium()
        else:
            publish_premium()
    else:
        restore_premium()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())