#!/usr/bin/env python3
"""Sinh BẢN ĐỒ GỘP TAG (review artifact) → data/tag-consolidation-map.json.

Bối cảnh: seomoney.org có 631 tag (471 dùng 1 lần) làm loãng crawl budget của
domain mới. Mục tiêu: gộp 568 tag <5 bài về ~51 tag canonical (pillar). Script
NÀY chỉ *đề xuất* map để người duyệt — KHÔNG sửa content. Việc áp dụng do
`consolidate_tags.py` làm SAU KHI map được duyệt.

Output JSON gồm:
  - canonical_tags : 51 tag ≥5 bài (giữ nguyên, đích gộp)
  - series_keep    : tag *series* (chức năng, KHÔNG đụng)
  - remove_category: category rác cần gỡ ("Tất cả")
  - map            : {tag_cũ: canonical}  — đề xuất CHẮC CHẮN
  - needs_review   : {tag_cũ: gợi_ý}      — người duyệt quyết
  - drop           : [tag]                 — đề xuất XOÁ hẳn (rác/hyper-specific)

Dùng:
    python3 scripts/build_tag_map.py            # ghi data/tag-consolidation-map.json
    python3 scripts/build_tag_map.py --print    # in tóm tắt, không ghi
"""
from __future__ import annotations

import json
import re
import sys
import tomllib
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
OUT = ROOT / "data" / "tag-consolidation-map.json"
FM = re.compile(r"^\+\+\+\s*\n(.*?)\n\+\+\+\s*\n?(.*)$", re.DOTALL)
KOREAN = re.compile(r"[가-힣]")  # Hangul syllables → gộp về ngữ pháp tiếng hàn

KEEP_MIN = 5  # tag dùng ≥5 bài = canonical hub, giữ nguyên


def tag_counts() -> Counter:
    c: Counter = Counter()
    for p in CONTENT.glob("**/*.md"):
        if p.name == "_index.md":
            continue
        m = FM.match(p.read_text(encoding="utf-8", errors="ignore"))
        if not m:
            continue
        try:
            fm = tomllib.loads(m.group(1))
        except tomllib.TOMLDecodeError:
            continue
        for t in (fm.get("taxonomies", {}) or {}).get("tags", []) or []:
            c[str(t).strip()] += 1
    return c


# Rule gộp — THỨ TỰ QUAN TRỌNG: specific → general (first match wins).
# Mỗi rule: (canonical, [substring lowercased]). Đặt ngân hàng TRƯỚC tiếng hàn để
# "so sánh ngân hàng số" không bị nuốt bởi chuỗi "hàn".
RULES: list[tuple[str, list[str]]] = [
    # --- Định danh điện tử (đặt trước ngân hàng) ---
    ("định danh điện tử", ["vneid", "căn cước", "cccd", "định danh", "xác thực cccd",
                            "chữ ký số", "chữ ký điện tử", "ký số", "mysign", "viettel-ca", "giá trị pháp lý"]),
    # --- Ngân hàng số (brand-specific giữ brand nếu brand là canonical) ---
    ("vietinbank", ["vietinbank", "v-plus", "v-advance", "v-family", "v-wealth", "ipay"]),
    ("liobank", ["liobank"]),
    ("msb", ["msb", "mysign"]),
    ("ngân hàng số", ["ngân hàng", "bank", "thẻ tín dụng", "thẻ ngân hàng", "thẻ digital",
                       "chuyển khoản", "phí chuyển khoản", "hoàn tiền", "cashback", "ekyc",
                       "open banking", "digital banking", "core banking", "interchange", "napas",
                       "vpbank", "bidv", "timo", "tnex", "cake", "lpbank", "ocb", "techcombank",
                       "big 4", "mở thẻ", "mở tài khoản", "ví điện tử", "apple pay", "internet banking",
                       "miễn phí chuyển khoản", "fintech", "tín dụng", "rủi ro ngân hàng", "app ngân hàng"]),
    # --- Học tiếng Hàn ---
    ("topik", ["topik"]),
    ("ngữ pháp tiếng hàn", ["ngữ pháp", "trợ từ", "động từ", "phụ âm", "nguyên âm", "patchim",
                            "kính ngữ", "câu điều kiện", "câu mệnh lệnh", "đại từ", "định ngữ",
                            "liên từ", "trích dẫn", "phủ định", "chia động từ", "ghép âm", "nối âm",
                            "đồng hóa", "số đếm", "quy tắc phát âm", "받침", "높임말", "간접화법",
                            "더라도", "기 마련이다", "는다 해도", "곤 하다"]),
    ("học tiếng hàn", ["tiếng hàn", "hangul", "chào hỏi", "giao tiếp", "hội thoại", "mẫu câu",
                       "mua sắm tiếng", "mong muốn tiếng", "ôn tập hangul", "ôn thi topik", "thi topik"]),
    ("du lịch hàn quốc", ["seoul", "busan", "jeju", "hàn river", "seoraksan", "visa hàn", "xin visa", "anh đào"]),
    # --- DevOps / Git ---
    ("git", ["git ", "lệnh git", "git mac", "git branch", "git fetch", "git merge", "git pull",
             "git push", "git rebase", "git remote", "git reset", "git stash", "git workflow", "cài đặt git"]),
    ("github", ["github"]),
    ("github actions", ["github actions", "actions"]),
    ("ci/cd", ["ci/cd", "ci cd", "cicd", "pipeline", "merge conflict", "pull request",
               "regression test", "non-fast-forward", "qa gatekeeper", "qa check", "qa workflow"]),
    ("devops", ["devops", "webops", "self-healing", "automation", "tự động hoá", "deploy",
                "vaccine", "auto fixer", "autofixer", "bug fix", "debug"]),
    # --- Lập trình ---
    ("zola", ["zola", "ssg", "static site", "static blog", "blog tĩnh", "hugo", "rendering"]),
    ("terminal", ["terminal", "homebrew", "cli", "mac", "macos", "thinkpad", "lenovo", "laptop",
                  "84key", "keyboard", "bàn phím", "trackpoint"]),
    ("lập trình", ["python", "rust", "vanilla js", "javascript", "json-ld", "yaml", "markdown",
                   "frontend", "tech stack", "kiến trúc phần mềm", "vs-code", "sublime", "brackets",
                   "code-editor", "dev tools", "virtualenv", "bộ gõ", "font tiếng việt", "oauth",
                   "rbac", "phân quyền", "sessions", "cloudflare", "tên miền", "version control"]),
    # --- SEO / AdSense / Analytics ---
    ("seo", ["seo", "sitemap", "index", "crawl", "robots", "search console", "backlink",
             "internal linking", "topic cluster", "orphan", "og image", "ảnh og", "social preview",
             "open graph", "site readiness", "noindex", "content-strategy", "tối ưu hình ảnh"]),
    ("adsense", ["adsense", "publisher", "nội dung bị cấm", "nội dung hạn chế", "quy định cấm"]),
    ("monetization", ["monetiz", "kiếm tiền", "affiliate", "shopee", "creator economy",
                      "donate", "gây quỹ", "ủng hộ", "đóng góp", "mô hình kinh doanh", "bán hàng online"]),
    ("google analytics", ["analytics", "ga4", "bounce", "engagement", "nguồn traffic", "traffic", "phân tích dữ liệu"]),
    # --- Khoa học ---
    ("uranium", ["uranium", "làm giàu"]),
    ("hạt nhân", ["hạt nhân", "điện hạt nhân", "iaea", "năng lượng", "nuclear"]),
    ("khoa học q&a", ["khoa học", "vật lý", "hóa học", "hóa sinh", "sinh học", "vũ trụ", "không gian",
                      "quang học", "quang hợp", "chu trình nước", "thực vật", "động vật", "vi khuẩn",
                      "thời tiết", "trời mưa", "tuyết", "màu sắc", "mùi", "cảm giác", "tự do ý chí"]),
    # --- Sức khỏe ---
    ("sức khỏe", ["sức khỏe", "health", "dinh dưỡng", "tim", "não", "hô hấp", "giấc ngủ", "ngủ",
                  "vitamin", "detox", "sinh lý", "cơ thể", "tiêu hoá", "mắt", "tóc", "stress",
                  "đau đầu", "hành vi", "tâm lý"]),
    # --- Giáo dục ---
    ("giáo dục", ["thpt", "đáp án", "dap an", "tuyển sinh", "điểm chuẩn", "điểm thi", "học sinh", "sinh viên"]),
    # --- Du lịch / Ẩm thực ---
    ("du lịch", ["du lịch", "travel", "sa pa", "fansipan", "biển", "núi", "hiking", "phượt",
                 "festival", "lễ hội", "tết", "đoan ngọ", "vu-lan", "ngày lễ", "phong tục", "văn hóa"]),
    ("ẩm thực", ["ẩm thực", "f&b", "gourmand", "michelin", "món", "cà phê", "starbucks", "quán",
                 "phở", "street food", "ăn ", "ẩm thực", "vải thiều"]),
    # --- AI ---
    ("ai", ["ai", "machine learning", "deep learning", "bert", "sbert", "embeddings", "nlp",
            "máy học", "trí tuệ nhân tạo", "apple intelligence", "pytorch", "sentence-transformers",
            "prompt", "claude", "gpt", "llm"]),
    # --- Công nghệ chung ---
    ("công nghệ", ["apple", "wwdc", "macos 27", "phần cứng", "công nghệ", "an ninh mạng",
                   "bảo mật", "an toàn", "chống spam", "watermark", "bảo vệ ảnh"]),
]

# needs_review: chủ đề KHÔNG có canonical mạnh → người duyệt quyết (giữ/tạo pillar mới/xoá)
REVIEW_HINTS: list[tuple[str, list[str]]] = [
    ("sức khỏe (bảo hiểm?)", ["bhxh", "bhyt", "bhtn", "bảo hiểm", "lương hưu", "trợ cấp",
                              "an sinh", "vssid", "hồ sơ hưởng", "chốt sổ", "rút bhxh", "lao động"]),
    ("tài chính (pillar mới?)", ["tài chính", "đầu tư", "vàng", "fed", "lãi suất", "kinh tế",
                                 "thuế", "gtgt", "chứng khoán", "ngân sách", "chi phí", "tiết kiệm",
                                 "quản lý chi tiêu", "làm giàu", "hoàn thuế"]),
    ("thế giới (pillar mới?)", ["argentina", "anguilla", "bo-dao-nha", "chdc-congo", "iran", "mỹ",
                                "trung quốc", "nhật bản", "việt nam", "world cup", "bóng đá", "messi",
                                "ronaldo", "địa-chính-trị", "quốc tế", "công-nghệ-quân-sự", "oecd"]),
    ("năng suất (pillar mới?)", ["productivity", "trello", "calendar", "quản lý công việc",
                                 "decision making", "personal systems", "life systems", "life design",
                                 "self management", "money systems", "personal framework", "kinh nghiệm",
                                 "bài học", "thói quen", "freelancer", "digital nomad", "gen z"]),
]


def classify(tag: str) -> tuple[str, str | None]:
    """→ (bucket, canonical|hint). bucket ∈ {map, review, drop}."""
    low = tag.lower()
    for canon, kws in RULES:
        for kw in kws:
            if kw in low:
                return "map", canon
    if KOREAN.search(tag):
        return "map", "ngữ pháp tiếng hàn"
    for hint, kws in REVIEW_HINTS:
        for kw in kws:
            if kw in low:
                return "review", hint
    return "drop", None


def main() -> int:
    counts = tag_counts()
    canonical = sorted([t for t, c in counts.items() if c >= KEEP_MIN and "series" not in t.lower()],
                       key=lambda t: -counts[t])
    series = sorted([t for t in counts if "series" in t.lower()], key=lambda t: -counts[t])
    canon_set = set(canonical)

    mapping: dict[str, str] = {}
    review: dict[str, str] = {}
    drop: list[str] = []
    for tag, c in counts.items():
        if c >= KEEP_MIN or "series" in tag.lower():
            continue
        bucket, target = classify(tag)
        # nếu target không nằm trong canonical_set → hạ xuống review (an toàn)
        if bucket == "map" and target not in canon_set:
            review[tag] = f"{target} (chưa canonical — duyệt)"
        elif bucket == "map":
            mapping[tag] = target
        elif bucket == "review":
            review[tag] = target
        else:
            drop.append(tag)

    out = {
        "_meta": {
            "generated_by": "scripts/build_tag_map.py",
            "purpose": "Review-only: gộp 568 tag <5 bài → ~51 canonical. Áp dụng bằng consolidate_tags.py SAU khi duyệt.",
            "keep_min": KEEP_MIN,
            "total_tags": len(counts),
            "canonical_count": len(canonical),
            "map_count": len(mapping),
            "review_count": len(review),
            "drop_count": len(drop),
            "note": "Sửa tay file này trước khi chạy consolidate_tags.py. Chuyển dòng từ needs_review/drop sang map khi đã quyết.",
        },
        "canonical_tags": canonical,
        "series_keep": series,
        # KHÔNG xoá "Tất cả": là hub /categories/tat-ca/ CÓ CHỦ ĐÍCH (check_category_first
        # bắt buộc "Tất cả" đứng đầu mọi bài). Để rỗng → consolidate_tags.py KHÔNG đụng categories.
        "remove_category": [],
        "map": dict(sorted(mapping.items())),
        "needs_review": dict(sorted(review.items())),
        "drop": sorted(drop),
    }

    summary = (f"tags={len(counts)} | canonical={len(canonical)} | map={len(mapping)} "
               f"| needs_review={len(review)} | drop={len(drop)} | series_keep={len(series)}")
    if "--print" in sys.argv:
        print(summary)
        print("\ncanonical:", ", ".join(canonical))
        print("\nsample map:", dict(list(out["map"].items())[:15]))
        print("\nsample review:", dict(list(out["needs_review"].items())[:10]))
        print("\nsample drop:", out["drop"][:20])
        return 0

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✅ {OUT.relative_to(ROOT)}\n   {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
