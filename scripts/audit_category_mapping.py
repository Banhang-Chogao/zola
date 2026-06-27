#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit_category_mapping.py — Phân loại bài `bb`/`baochi` vào CHUYÊN MỤC NỘI DUNG thật.

Chốt logic (CLAUDE.md §"Quy tắc Category", hiệu lực 27/06/2026):

    source/type   = baochi  (nguồn bài từ phím tắt `bb`)  -> [extra] source / content_origin
    real category = ngan-hang / tai-chinh / cong-nghe ...  -> [taxonomies] categories

"Báo chí" **không phải** chuyên mục nội dung — nó chỉ là nguồn/loại bài. Vì vậy
"Báo chí" KHÔNG được dùng làm chuyên mục khám phá chính. Script này:

  1. Quét content/**/*.md (mặc định baochi + posting + mọi section có bài).
  2. Tìm bài có "Báo chí" (source giả dạng category) trong `[taxonomies] categories`.
  3. Bỏ "Báo chí" khỏi categories, GIỮ chuyên mục nội dung sẵn có; nếu bài chưa có
     chuyên mục thật → SUY RA bằng bộ phân loại theo title/body/keywords.
  4. Chuyển dấu nguồn vào `[extra]`: source = "bb", content_origin = "baochi"
     (chỉ cho bài nằm trong section `baochi/`).
  5. Mặc định **dry-run** (chỉ in bảng); `--apply` mới ghi file.

Quy tắc an toàn:
  - KHÔNG bao giờ tự gán "premium" (chỉ giữ nếu đã có sẵn — do biên tập chọn tay).
  - Confidence < 0.65 và bài chưa có chuyên mục thật → fallback "Đời sống" (an toàn).
  - KHÔNG tự tạo chuyên mục MỚI — chỉ map vào tập canonical đã có (+ fallback).
  - Bảo toàn chuyên mục đã set tay (existing real category luôn được giữ).

stdlib only. Test: scripts/test_audit_category_mapping.py
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import sys
import unicodedata
from dataclasses import dataclass, field

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Sections quét mặc định (mọi nơi có thể chứa bài bb/baochi).
DEFAULT_SECTIONS = ["baochi", "posting", "du-lich", "dien-anh"]

# Giá trị trong `categories` thật ra là NGUỒN/LOẠI bài, không phải chuyên mục nội
# dung → cần gỡ khỏi [taxonomies] và chuyển sang [extra]. So khớp không dấu.
SOURCE_TYPE_TERMS = {"bao chi"}  # "Báo chí"

ALWAYS_KEEP = {"tat ca"}        # "Tất cả" — luôn ở đầu mảng
PREMIUM_TERM = "premium"        # giữ nguyên nếu có, KHÔNG bao giờ tự thêm

FALLBACK_CATEGORY = "Đời sống"  # khi confidence < threshold và bài chưa có cat thật
CONFIDENCE_THRESHOLD = 0.65

# ---------------------------------------------------------------------------
# Bộ chuyên mục canonical (display name khớp taxonomy đang dùng trong repo) +
# từ khoá nhận diện. weight: dấu hiệu mạnh = 3, trung bình = 2, yếu = 1.
# Khớp trên văn bản đã bỏ dấu, lowercase.
# ---------------------------------------------------------------------------
CATEGORY_KEYWORDS: dict[str, list[tuple[str, int]]] = {
    "Ngân hàng": [
        ("ngan hang", 3), ("ngan hang so", 3), ("banking", 3), ("digital bank", 3),
        ("the tin dung", 3), ("the ghi no", 2), ("tai khoan", 2), ("lai suat", 3),
        ("gui tiet kiem", 2), ("ekyc", 3), ("app banking", 3), ("smartbanking", 3),
        ("internet banking", 2), ("mobile banking", 2), ("chuyen khoan", 2),
        ("vietcombank", 3), ("techcombank", 3), ("bidv", 3), ("vpbank", 3),
        ("vietinbank", 3), ("agribank", 3), ("sacombank", 3), ("liobank", 3),
        ("msb", 3), ("mb bank", 3), ("napas", 2), ("atm", 2), ("private banking", 3),
        ("hoan tien", 2), ("cashback", 2), ("mo the", 3), ("mo tai khoan", 2),
        ("the ngan hang", 3), ("vay", 1), ("tin dung", 2),
    ],
    "Tài chính": [
        ("tai chinh ca nhan", 3), ("tai chinh", 2), ("thue", 3), ("hoan thue", 3),
        ("gtgt", 3), ("thue gtgt", 3), ("tien luong", 2), ("dau tu", 2),
        ("chi tieu", 2), ("quan ly chi tieu", 3), ("ngan sach", 2), ("tiet kiem", 2),
        ("gia vang", 3), ("vang", 2), ("chung khoan", 3), ("lam phat", 3),
        ("co phieu", 2), ("quy dau tu", 2),
    ],
    "Công nghệ": [
        ("cong nghe", 3), ("phan mem", 2), ("ung dung", 1), ("app", 1),
        ("iphone", 3), ("macos", 3), ("mac", 2), ("android", 3), ("smartphone", 2),
        ("laptop", 2), ("chip", 2), ("github", 3), ("zola", 3), ("claude", 2),
        ("openai", 3), ("ai", 1), ("website", 2), ("web", 1), ("lap trinh", 3),
        ("code", 2), ("bao mat", 2), ("vneid", 3), ("cccd", 3), ("ma qr", 2),
        ("qr", 1), ("lua dao", 2), ("deepfake", 3), ("ten mien", 3), ("domain", 2),
    ],
    "SEO": [
        ("seo", 3), ("tu khoa", 2), ("google search", 3), ("search console", 3),
        ("backlink", 3), ("ranking", 2), ("lighthouse", 3), ("organic", 2),
        ("traffic", 1), ("noi dung", 1), ("content", 1), ("giu chan nguoi doc", 2),
    ],
    "Du lịch": [
        ("du lich", 3), ("visa", 3), ("khach san", 3), ("san bay", 3),
        ("hanh ly", 2), ("itinerary", 2), ("chuyen di", 2), ("diem den", 2),
        ("tour", 2), ("ve may bay", 3), ("check-in", 1), ("homestay", 3),
        ("resort", 2), ("incheon", 3), ("airport", 2), ("fansipan", 2),
        ("starbucks", 1), ("xu dong", 1), ("vai co thu", 1),
    ],
    "Học tiếng Hàn": [
        ("tieng han", 3), ("topik", 3), ("tu vung", 2), ("ngu phap", 2),
        ("hangul", 3), ("han quoc hoc", 2),
    ],
    "Khoa học": [
        ("khoa hoc", 3), ("uranium", 3), ("hat nhan", 3), ("vat ly", 3),
        ("hoa hoc", 2), ("sinh hoc", 2), ("nghien cuu", 1), ("nang luong nguyen tu", 3),
        ("phong xa", 2),
    ],
    "Bảo hiểm": [
        ("bao hiem", 3), ("bhyt", 3), ("bhxh", 3), ("bao hiem y te", 3),
        ("bao hiem xa hoi", 3), ("muc dong", 2), ("ho gia dinh", 1),
    ],
    "Thế giới": [
        ("the gioi", 3), ("quoc te", 2), ("iran", 2), ("trung dong", 3),
        ("hoa binh", 2), ("chien tranh", 2), ("xung dot", 2), ("ngoai giao", 2),
        ("global", 1),
    ],
    "Thể thao": [
        ("world cup", 3), ("bong da", 3), ("ronaldo", 3), ("messi", 3),
        ("the thao", 3), ("tran dau", 2), ("vo dich", 2), ("cau thu", 2),
        ("hat-trick", 2), ("hat trick", 2),
    ],
    "Điện ảnh": [
        ("dien anh", 3), ("phim", 2), ("dao dien", 2), ("dien vien", 2),
        ("bom tan", 2), ("rap phim", 2),
    ],
    "Ẩm thực": [
        ("am thuc", 3), ("mon an", 2), ("cong thuc", 1), ("nau an", 2),
        ("nha hang", 1), ("dac san", 2), ("trai cay", 1),
    ],
    "Đời sống": [
        ("doi song", 3), ("suc khoe", 2), ("gia dinh", 2), ("loi song", 2),
        ("meo vat", 2), ("mua he", 1), ("bu nuoc", 1), ("an toan", 1),
    ],
}

# Bản đồ alias → chuyên mục canonical (cho chuỗi category thô từ `bb`).
ALIAS_MAP = {
    "bank": "Ngân hàng", "banking": "Ngân hàng", "ngan hang": "Ngân hàng",
    "ngan-hang": "Ngân hàng",
    "finance": "Tài chính", "personal finance": "Tài chính",
    "tai chinh": "Tài chính", "tai chinh ca nhan": "Tài chính", "tai-chinh": "Tài chính",
    "tech": "Công nghệ", "technology": "Công nghệ", "cong nghe": "Công nghệ",
    "ai webops": "Công nghệ", "cong-nghe": "Công nghệ",
    "life": "Đời sống", "doi song": "Đời sống", "xa hoi": "Đời sống", "doi-song": "Đời sống",
    "travel": "Du lịch", "du lich": "Du lịch", "solo trip": "Du lịch", "du-lich": "Du lịch",
    "seo": "SEO", "khoa hoc": "Khoa học", "science": "Khoa học",
    "bao hiem": "Bảo hiểm", "insurance": "Bảo hiểm",
    "the gioi": "Thế giới", "world": "Thế giới",
    "the thao": "Thể thao", "sport": "Thể thao", "sports": "Thể thao",
    "am thuc": "Ẩm thực", "food": "Ẩm thực",
    "dien anh": "Điện ảnh", "movie": "Điện ảnh", "film": "Điện ảnh",
    "tieng han": "Học tiếng Hàn", "korean": "Học tiếng Hàn",
}


def strip_accents(text: str) -> str:
    """Bỏ dấu tiếng Việt + chuẩn hoá đ/Đ → d, lowercase."""
    text = text.replace("đ", "d").replace("Đ", "D")
    nfkd = unicodedata.normalize("NFD", text)
    out = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    return out.lower()


@dataclass
class ClassResult:
    category: str
    confidence: float
    reason: str
    scores: dict[str, int] = field(default_factory=dict)


def classify(title: str, body: str) -> ClassResult:
    """Chấm điểm keyword theo từng chuyên mục, trả về chuyên mục mạnh nhất.

    title hit ×3, body hit ×1 (mỗi keyword body cap 3 lần để 1 từ lặp không lấn át).
    confidence = hàm của độ tách biệt (margin) giữa top và runner-up + độ mạnh tuyệt đối.
    """
    norm_title = strip_accents(title)
    norm_body = strip_accents(body)
    scores: dict[str, int] = {}
    hits: dict[str, list[str]] = {}
    for cat, kws in CATEGORY_KEYWORDS.items():
        total = 0
        cat_hits: list[str] = []
        for kw, weight in kws:
            in_title = kw in norm_title
            body_count = min(norm_body.count(kw), 3)
            if in_title:
                total += weight * 3
                cat_hits.append(kw)
            if body_count:
                total += weight * body_count
                if not in_title:
                    cat_hits.append(kw)
        if total:
            scores[cat] = total
            hits[cat] = cat_hits

    if not scores:
        return ClassResult(FALLBACK_CATEGORY, 0.0,
                           "Không phát hiện từ khoá chuyên mục — dùng fallback an toàn.",
                           {})

    ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    top_cat, top_score = ordered[0]
    second_score = ordered[1][1] if len(ordered) > 1 else 0

    if top_score <= 1:
        confidence = 0.5
    else:
        margin = (top_score - second_score) / top_score
        confidence = round(min(0.99, 0.55 + 0.4 * margin), 2)

    top_signals = ", ".join(hits[top_cat][:5])
    reason = (f"Nội dung tập trung vào {top_cat.lower()} "
              f"(tín hiệu: {top_signals}).")
    return ClassResult(top_cat, confidence, reason, scores)


# ---------------------------------------------------------------------------
# Đọc / sửa frontmatter (line-oriented, an toàn — không reserialize toàn TOML).
# ---------------------------------------------------------------------------
FM_DELIM = "+++"
CAT_LINE_RE = re.compile(r'^(\s*)categories\s*=\s*\[(.*)\]\s*$')
EXTRA_HEADER_RE = re.compile(r'^\s*\[extra\]\s*$')
SOURCE_KEY_RE = re.compile(r'^\s*source\s*=')
ORIGIN_KEY_RE = re.compile(r'^\s*content_origin\s*=')


def split_frontmatter(lines: list[str]) -> tuple[int, int]:
    """Trả về (idx_open, idx_close) của 2 dòng +++ bao frontmatter, hoặc (-1,-1)."""
    opens = [i for i, ln in enumerate(lines) if ln.strip() == FM_DELIM]
    if len(opens) < 2:
        return -1, -1
    return opens[0], opens[1]


def parse_category_array(raw: str) -> list[str]:
    return [m.group(1) for m in re.finditer(r'"([^"]*)"', raw)]


def build_category_array(cats: list[str]) -> str:
    return "[" + ", ".join(f'"{c}"' for c in cats) + "]"


def read_body_after_fm(lines: list[str], close_idx: int) -> str:
    return "".join(lines[close_idx + 1:])


@dataclass
class FileRecord:
    path: str
    old_cats: list[str]
    new_cats: list[str]
    confidence: float
    reason: str
    changed: bool
    added_source_meta: bool = False


def process_file(path: str, apply: bool) -> FileRecord | None:
    with open(path, "r", encoding="utf-8") as fh:
        lines = fh.readlines()

    open_idx, close_idx = split_frontmatter(lines)
    if open_idx < 0:
        return None

    fm = lines[open_idx:close_idx + 1]
    cat_line_idx = None
    for i in range(open_idx, close_idx + 1):
        if CAT_LINE_RE.match(lines[i]):
            cat_line_idx = i
            break
    if cat_line_idx is None:
        return None

    m = CAT_LINE_RE.match(lines[cat_line_idx])
    indent, raw = m.group(1), m.group(2)
    old_cats = parse_category_array(raw)

    # Có "Báo chí" (source giả dạng category) không?
    has_source_type = any(strip_accents(c) in SOURCE_TYPE_TERMS for c in old_cats)
    if not has_source_type:
        return None  # không phải bài cần xử lý

    has_premium = any(strip_accents(c) == PREMIUM_TERM for c in old_cats)
    # Chuyên mục NỘI DUNG thật đang có (bỏ Tất cả / Báo chí / premium), giữ thứ tự.
    existing_real: list[str] = []
    for c in old_cats:
        s = strip_accents(c)
        if s in ALWAYS_KEEP or s in SOURCE_TYPE_TERMS or s == PREMIUM_TERM:
            continue
        if c not in existing_real:
            existing_real.append(c)

    # Suy luận (để báo cáo + dùng khi thiếu cat thật).
    title = ""
    for ln in fm:
        tm = re.match(r'^\s*title\s*=\s*"(.*)"\s*$', ln)
        if tm:
            title = tm.group(1)
            break
    body = read_body_after_fm(lines, close_idx)
    suggestion = classify(title, body)

    if existing_real:
        new_real = existing_real
        confidence = 1.0
        reason = ("Giữ chuyên mục nội dung sẵn có; gỡ 'Báo chí' (nguồn) khỏi taxonomy. "
                  f"Gợi ý phân loại: {suggestion.category} ({suggestion.confidence}).")
    else:
        if suggestion.confidence >= CONFIDENCE_THRESHOLD:
            new_real = [suggestion.category]
            confidence = suggestion.confidence
            reason = suggestion.reason
        else:
            new_real = [FALLBACK_CATEGORY]
            confidence = suggestion.confidence
            reason = (f"Confidence {suggestion.confidence} < {CONFIDENCE_THRESHOLD} "
                      f"→ fallback an toàn '{FALLBACK_CATEGORY}'.")

    new_cats = ["Tất cả"] + new_real + (["premium"] if has_premium else [])

    # Bài bb/baochi → đảm bảo dấu nguồn ở [extra].
    in_baochi_section = (os.sep + "baochi" + os.sep) in path
    needs_source_meta = in_baochi_section

    changed = new_cats != old_cats
    added_meta = False

    if apply:
        new_lines = list(lines)
        new_lines[cat_line_idx] = f"{indent}categories = {build_category_array(new_cats)}\n"

        if needs_source_meta:
            new_lines, added_meta = ensure_source_meta(new_lines)

        if changed or added_meta:
            with open(path, "w", encoding="utf-8") as fh:
                fh.writelines(new_lines)
    else:
        # dry-run: vẫn tính xem có cần thêm meta để báo cáo.
        if needs_source_meta:
            _, added_meta = ensure_source_meta(list(lines))

    return FileRecord(
        path=os.path.relpath(path, ROOT),
        old_cats=old_cats,
        new_cats=new_cats,
        confidence=confidence,
        reason=reason,
        changed=changed or added_meta,
        added_source_meta=added_meta,
    )


def ensure_source_meta(lines: list[str]) -> tuple[list[str], bool]:
    """Chèn source="bb" + content_origin="baochi" dưới [extra]. Trả (lines, added)."""
    open_idx, close_idx = split_frontmatter(lines)
    if open_idx < 0:
        return lines, False

    has_source = any(SOURCE_KEY_RE.match(lines[i]) for i in range(open_idx, close_idx + 1))
    has_origin = any(ORIGIN_KEY_RE.match(lines[i]) for i in range(open_idx, close_idx + 1))
    if has_source and has_origin:
        return lines, False

    extra_idx = None
    for i in range(open_idx, close_idx + 1):
        if EXTRA_HEADER_RE.match(lines[i]):
            extra_idx = i
            break

    inserts = []
    if not has_source:
        inserts.append('source = "bb"\n')
    if not has_origin:
        inserts.append('content_origin = "baochi"\n')
    if not inserts:
        return lines, False

    if extra_idx is not None:
        new_lines = lines[:extra_idx + 1] + inserts + lines[extra_idx + 1:]
    else:
        # Không có [extra] → tạo mới ngay trước dòng +++ đóng.
        new_lines = lines[:close_idx] + ["[extra]\n"] + inserts + lines[close_idx:]
    return new_lines, True


def discover_files(sections: list[str]) -> list[str]:
    files: list[str] = []
    for sec in sections:
        pattern = os.path.join(ROOT, "content", sec, "**", "*.md")
        for p in glob.glob(pattern, recursive=True):
            base = os.path.basename(p)
            if base == "_index.md" or "feed-anchor" in base:
                continue
            files.append(p)
    return sorted(set(files))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true",
                    help="Ghi thay đổi vào file (mặc định dry-run).")
    ap.add_argument("--sections", nargs="*", default=DEFAULT_SECTIONS,
                    help=f"Sections quét (mặc định: {', '.join(DEFAULT_SECTIONS)}).")
    ap.add_argument("--path", help="Chỉ xử lý 1 file cụ thể.")
    args = ap.parse_args()

    if args.path:
        targets = [os.path.join(ROOT, args.path)] if not os.path.isabs(args.path) else [args.path]
    else:
        targets = discover_files(args.sections)

    records: list[FileRecord] = []
    for path in targets:
        rec = process_file(path, apply=args.apply)
        if rec:
            records.append(rec)

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"=== audit_category_mapping ({mode}) — {len(records)} bài có 'Báo chí' (nguồn) ===\n")
    if not records:
        print("Không tìm thấy bài nào dùng 'Báo chí' làm category. Sạch ✅")
        return 0

    # Bảng kết quả.
    print(f"{'file':<58} | {'old → new category':<46} | conf | reason")
    print("-" * 140)
    for r in records:
        old_disp = ",".join(c for c in r.old_cats if strip_accents(c) not in ALWAYS_KEEP) or "—"
        new_disp = ",".join(c for c in r.new_cats if strip_accents(c) not in ALWAYS_KEEP) or "—"
        change = f"{old_disp} → {new_disp}"
        fname = r.path.replace("content/", "")
        meta = " +[extra]source/origin" if r.added_source_meta else ""
        print(f"{fname:<58} | {change:<46} | {r.confidence:.2f} | {r.reason}{meta}")

    changed = sum(1 for r in records if r.changed)
    print(f"\nTổng: {len(records)} bài | {changed} cần thay đổi"
          f"{' (đã ghi)' if args.apply else ' (dry-run — dùng --apply để ghi)'}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
