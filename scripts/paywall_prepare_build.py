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

PREMIUM_CATEGORY = "premium"
DEFAULT_PREMIUM_PRICE = 100_000


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
    marker = "<!-- more -->"
    if marker in body:
        head, tail = body.split(marker, 1)
        return head.strip(), tail.strip()
    return body.strip(), ""


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
        stored_premium = premium_body if premium_body else body
        post_id = pm.get("premium_post_id") or pm.get("slug") or md.stem
        teaser_words = int(pm.get("premium_teaser_words", 180))

        private_path = PRIVATE / f"{post_id}.md"
        private_path.write_text(stored_premium, encoding="utf-8")

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
        strip_premium()
    else:
        restore_premium()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())