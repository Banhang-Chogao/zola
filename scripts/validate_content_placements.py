#!/usr/bin/env python3
"""
Validate content placement registry + blocks + template hooks.

Usage:
  python3 scripts/validate_content_placements.py

Exit codes:
  0 — OK
  2 — validation failed (blocks CI)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "content-placements.json"
TEMPLATE_GLOB = [
    ROOT / "templates" / "base.html",
    ROOT / "templates" / "index.html",
    ROOT / "templates" / "page.html",
    ROOT / "templates" / "admin-momo-url.html",
    ROOT / "templates" / "posting-left-sidebar.html",
]

BLOCK_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
HOOK_RE = re.compile(r'placement::render\s*\(\s*id\s*=\s*"([^"]+)"')
MOMO_TYPES = {"momo_cta", "donate_box", "premium_cta"}


def load_data() -> dict:
    if not DATA_FILE.exists():
        print(f"❌ Missing {DATA_FILE.relative_to(ROOT)}")
        sys.exit(2)
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"❌ Invalid JSON in {DATA_FILE}: {exc}")
        sys.exit(2)


def hooked_ids() -> set[str]:
    hooked: set[str] = set()
    for path in TEMPLATE_GLOB:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for match in HOOK_RE.finditer(text):
            hooked.add(match.group(1))
    return hooked


def main() -> int:
    data = load_data()
    placements = data.get("placements") or []
    blocks = data.get("blocks") or []

    placement_ids = {p.get("id") for p in placements if p.get("id")}
    if not placement_ids:
        print("❌ placements[] is empty")
        return 2

    errors: list[str] = []
    warnings: list[str] = []

    # Unique placement IDs
    seen_p: set[str] = set()
    for p in placements:
        pid = (p.get("id") or "").strip()
        if not pid:
            errors.append("placement missing id")
            continue
        if pid in seen_p:
            errors.append(f"duplicate placement id: {pid}")
        seen_p.add(pid)

    # Template hooks vs registry.hooked flag
    hooks = hooked_ids()
    for p in placements:
        pid = p.get("id")
        if not pid:
            continue
        marked = bool(p.get("hooked"))
        in_template = pid in hooks
        if marked and not in_template:
            errors.append(f"placement {pid} marked hooked=true but no template hook found")
        if in_template and not marked:
            warnings.append(f"placement {pid} has template hook but hooked=false in JSON")

    # Blocks
    seen_b: set[str] = set()
    for block in blocks:
        bid = (block.get("id") or "").strip()
        if not bid:
            errors.append("block missing id")
            continue
        if not BLOCK_ID_RE.match(bid):
            errors.append(f"invalid block id: {bid}")
        if bid in seen_b:
            errors.append(f"duplicate block id: {bid}")
        seen_b.add(bid)

        placement_id = (block.get("placement_id") or "").strip()
        if placement_id not in placement_ids:
            errors.append(f"block {bid} references unknown placement_id: {placement_id}")

        btype = (block.get("type") or "").strip()
        url = (block.get("url") or "").strip()
        if url and not url.startswith("https://"):
            errors.append(f"block {bid} url must be https")
        if btype in MOMO_TYPES and url and not url.startswith("https://me.momo.vn/"):
            errors.append(f"block {bid} ({btype}) requires https://me.momo.vn/ URL")

        if btype == "html_safe" and block.get("body"):
            body = block["body"]
            if re.search(r"<\s*script\b", body, re.I):
                errors.append(f"block {bid} html_safe body must not contain <script>")

    for w in warnings:
        print(f"⚠️  {w}")

    if errors:
        for err in errors:
            print(f"❌ {err}")
        print(f"\nFailed: {len(errors)} error(s)")
        return 2

    print(
        f"✅ Content placements OK — {len(placements)} placements, "
        f"{len(blocks)} blocks, {len(hooks)} template hooks"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())