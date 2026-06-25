#!/usr/bin/env python3
"""Áp dụng BẢN ĐỒ GỘP TAG đã duyệt vào front-matter content/*.md.

⚠️  CHỜ DUYỆT: đọc `data/tag-consolidation-map.json` (do build_tag_map.py sinh, NGƯỜI
    duyệt/sửa tay trước). Mặc định `--dry-run` (KHÔNG ghi). Phải truyền `--apply` mới sửa.

Việc làm (chỉ đụng mảng tags/categories, GIỮ NGUYÊN mọi thứ khác trong front-matter):
  1. map:  tag_cũ → canonical (dedupe, giữ thứ tự xuất hiện).
  2. drop: xoá hẳn tag rác.
  3. needs_review: BỎ QUA mặc định (chỉ áp dụng khi --with-review, sau khi người chốt map).
  4. remove_category: gỡ category rác ("Tất cả").
  5. series_keep: tuyệt đối KHÔNG đụng tag *series* (chức năng series-listing, vaccine V8/V32).

An toàn:
  - Idempotent: chạy lại không đổi gì.
  - Chỉ thay mảng 1 dòng `tags = [...]` / `categories = [...]`; mảng nhiều dòng → SKIP + cảnh báo.
  - KHÔNG re-serialize TOML (giữ comment/format); chỉ regex-replace đúng 2 mảng.
  - KHÔNG đụng body, title, description, date, extra.

Dùng:
    python3 scripts/consolidate_tags.py                 # dry-run: in tóm tắt, không ghi
    python3 scripts/consolidate_tags.py --apply         # áp dụng map + drop + remove_category
    python3 scripts/consolidate_tags.py --apply --with-review   # + áp dụng needs_review
"""
from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
MAP_FILE = ROOT / "data" / "tag-consolidation-map.json"
FM = re.compile(r"^(\+\+\+\s*\n)(.*?)(\n\+\+\+\s*\n?)(.*)$", re.DOTALL)
# mảng 1 dòng: key = [ ... ]  (không chứa newline trong [])
ARRAY_1LINE = {
    "tags": re.compile(r'(?m)^(?P<indent>[ \t]*)tags\s*=\s*\[(?P<body>[^\]\n]*)\]\s*$'),
    "categories": re.compile(r'(?m)^(?P<indent>[ \t]*)categories\s*=\s*\[(?P<body>[^\]\n]*)\]\s*$'),
}


def load_map() -> dict:
    if not MAP_FILE.exists():
        raise SystemExit(f"❌ thiếu {MAP_FILE.relative_to(ROOT)} — chạy build_tag_map.py trước.")
    return json.loads(MAP_FILE.read_text(encoding="utf-8"))


def render_array(key: str, items: list[str], indent: str) -> str:
    inner = ", ".join(f'"{i}"' for i in items)
    return f'{indent}{key} = [{inner}]'


def dedupe(seq: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def process(path: Path, tagmap: dict[str, str], drops: set[str], series_keep: set[str],
            remove_cat: set[str], rewrite_tags: bool) -> tuple[bool, list[str]]:
    """→ (changed, notes). Sửa file in-place chỉ khi rewrite_tags=True."""
    raw = path.read_text(encoding="utf-8")
    m = FM.match(raw)
    if not m:
        return False, []
    head, fmtext, sep, body = m.groups()
    try:
        fm = tomllib.loads(fmtext)
    except tomllib.TOMLDecodeError:
        return False, [f"{path.name}: TOML lỗi — SKIP"]

    tax = fm.get("taxonomies", {}) or {}
    cur_tags = [str(t).strip() for t in (tax.get("tags") or fm.get("tags") or [])]
    cur_cats = [str(c).strip() for c in (tax.get("categories") or fm.get("categories") or [])]
    if not cur_tags and not cur_cats:
        return False, []

    # --- tính tags mới ---
    new_tags: list[str] = []
    for t in cur_tags:
        if "series" in t.lower() or t in series_keep:
            new_tags.append(t)            # series: giữ nguyên
        elif t in drops:
            continue                       # drop: bỏ
        else:
            new_tags.append(tagmap.get(t, t))  # map hoặc giữ (canonical)
    new_tags = dedupe(new_tags)
    # --- tính categories mới ---
    # GUARD cứng: "Tất cả" là hub bắt buộc (check_category_first) → KHÔNG BAO GIỜ xoá,
    # và luôn giữ đứng ĐẦU. remove_cat chỉ áp cho category khác.
    safe_remove = {c for c in remove_cat if c != "Tất cả"}
    new_cats = dedupe([c for c in cur_cats if c not in safe_remove])
    if "Tất cả" in new_cats and new_cats[0] != "Tất cả":
        new_cats = ["Tất cả"] + [c for c in new_cats if c != "Tất cả"]

    notes: list[str] = []
    changed = (new_tags != cur_tags) or (new_cats != cur_cats)
    if not changed:
        return False, []

    new_fmtext = fmtext
    if new_tags != cur_tags:
        pat = ARRAY_1LINE["tags"]
        mt = pat.search(new_fmtext)
        if not mt:
            notes.append(f"{path.name}: tags mảng nhiều dòng — SKIP tags")
        else:
            new_fmtext = pat.sub(lambda mm: render_array("tags", new_tags, mm.group("indent")), new_fmtext, count=1)
    if new_cats != cur_cats:
        pat = ARRAY_1LINE["categories"]
        mc = pat.search(new_fmtext)
        if not mc:
            notes.append(f"{path.name}: categories mảng nhiều dòng — SKIP categories")
        else:
            new_fmtext = pat.sub(lambda mm: render_array("categories", new_cats, mm.group("indent")), new_fmtext, count=1)

    if rewrite_tags and new_fmtext != fmtext:
        path.write_text(head + new_fmtext + sep + body, encoding="utf-8")
    return (new_fmtext != fmtext), notes


def main() -> int:
    apply = "--apply" in sys.argv
    with_review = "--with-review" in sys.argv
    data = load_map()

    tagmap = dict(data.get("map", {}))
    if with_review:
        for k, v in data.get("needs_review", {}).items():
            tagmap[k] = re.sub(r"\s*\(.*\)$", "", v).strip()  # bỏ ghi chú "(…)"
    drops = set(data.get("drop", []))
    series_keep = set(data.get("series_keep", []))
    remove_cat = set(data.get("remove_category", []))

    changed_files = 0
    all_notes: list[str] = []
    for p in sorted(CONTENT.glob("**/*.md")):
        if p.name == "_index.md":
            continue
        changed, notes = process(p, tagmap, drops, series_keep, remove_cat, rewrite_tags=apply)
        if changed:
            changed_files += 1
        all_notes.extend(notes)

    mode = "ÁP DỤNG" if apply else "DRY-RUN (không ghi)"
    print(f"[{mode}] files sẽ đổi: {changed_files} | map={len(tagmap)} drop={len(drops)} "
          f"remove_cat={sorted(remove_cat)} with_review={with_review}")
    for n in all_notes[:30]:
        print("  ⚠ ", n)
    if all_notes and len(all_notes) > 30:
        print(f"  … (+{len(all_notes) - 30} cảnh báo nữa)")
    if not apply:
        print("→ Duyệt xong map thì chạy: python3 scripts/consolidate_tags.py --apply")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
