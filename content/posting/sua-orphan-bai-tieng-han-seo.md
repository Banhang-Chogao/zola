+++
title = "Tôi tìm và sửa các bài tiếng Hàn bị orphan"
description = "Chiến lược internal linking cho topic cluster"
date = 2026-06-19
aliases = ["/sua-orphan-bai-tieng-han-seo/"]
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["internal linking", "orphan pages", "seo", "topic cluster"]
[extra]
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
seo_keyword = "sửa orphan tiếng hàn"
featured = false
+++

**Cập nhật lần cuối:** 19/06/2026

---

**Orphan page** là trang không có internal link inbound từ bài khác — Google khó đánh giá authority, PageRank nội bộ = 0. Tôi từng có **7 bài tiếng Hàn orphan** trước khi áp dụng chiến lược này.

**SEO Cluster:** [FAQ Schema ngân hàng](/faq-schema-cluster-ngan-hang-ctr/) · [Korean pillar](/ngu-phap-nang-cao-sau-topik-4/)

---

## Orphan page là gì?

```
Pillar (inbound: 5)
    ↑
    ├── Bài A (inbound: 2) ✅
    ├── Bài B (inbound: 0) ❌ ORPHAN
    └── Bài C (inbound: 1) ⚠️ yếu
```

**Bài B** không ai link tới → orphan → tôi sửa bằng cách thêm link từ Pillar và Bài A.

---

## Cách tôi tìm orphan pages

### Bước 1: Build link graph

```python
import re
from pathlib import Path

def extract_links(md_text: str) -> list[str]:
    return re.findall(r'\]\((/[^)]+|\.[^)]+\.md)\)', md_text)

pages = {}
for md in Path("articles").rglob("*.md"):
    slug = ...  # map từ build.py
    pages[slug] = {"out": extract_links(md.read_text()), "in": []}

for slug, data in pages.items():
    for link in data["out"]:
        target = resolve(link)
        if target in pages:
            pages[target]["in"].append(slug)

orphans = [s for s, d in pages.items() if len(d["in"]) == 0 and s != "/"]
```

### Bước 2: Chạy qua QA Gatekeeper

[QA Gatekeeper](/qa-gatekeeper-vaccine-autofixer/) chạy script này mỗi ngày — báo cáo orphan trong `daily-vaccine-report.md`.

---

## Topic cluster tiếng Hàn — cấu trúc tôi dùng

| Vai trò | Bài | Inbound mục tiêu |
|---------|-----|------------------|
| **Pillar** | [Ngữ pháp sau TOPIK 4](/ngu-phap-nang-cao-sau-topik-4/) | ≥ 4 |
| Supporting | [-더라도 / -는다 해도](/derado-va-neunda-haedo-tieng-han/) | ≥ 2 |
| Supporting | [-곤 하다, -기 마련이다](/gon-hada-ki-mareonida-tieng-han/) | ≥ 2 |
| Supporting | [Giả định nâng cao](/ngu-phap-gia-dinh-nang-cao-topik/) | ≥ 2 |
| Supporting | [50 mẫu câu](/50-mau-cau-topik-nang-cao/) | ≥ 3 |

**Korean Converter** (tool site) link về pillar — tôi thêm footer "Học thêm ngữ pháp".

---

## Anchor text strategy — tôi không dùng "click here"

| ❌ Tránh | ✅ Dùng |
|----------|---------|
| Xem thêm | phân biệt -더라도 và -는다 해도 |
| Tại đây | 50 mẫu câu TOPIK nâng cao |
| Link | ngữ pháp tiếng Hàn sau TOPIK 4 |

**Quy tắc:** Anchor text chứa **keyword hoặc biến thể semantic** — không spam exact match.

---

## Internal linking strategy — 4 quy tắc

### 1. Hub & Spoke

Pillar link **tất cả** supporting bài. Mỗi supporting **link ngược** pillar + **1 bài sibling**.

### 2. Cross-cluster có chủ đích

Bài tiếng Hàn link [SEO orphan](/faq-schema-cluster-ngan-hang-ctr/) khi nói về cấu trúc site — không link ngẫu nhiên sang ngân hàng.

### 3. Bảng Vàng SEO

Trang **Bảng Vàng SEO** (trang hub toàn site) link 4 pillar:
- Finance: [/bhxh/vssid-khong-hien-bhtn](/vssid-khong-hien-qua-trinh-dong-bhtn/)
- Korean: [/tieng-han/ngu-phap-nang-cao-sau-topik-4](/ngu-phap-nang-cao-sau-topik-4/)
- AI: [/ai/he-thong-prompt-zola](/he-thong-prompt-zola-blog/)
- SEO: [FAQ Schema](/faq-schema-cluster-ngan-hang-ctr/)

### 4. FAQ là điểm link

Mỗi câu FAQ cuối bài có link "Chi tiết: [bài X]" — tăng inbound tự nhiên.

---

## Ví dụ sửa orphan — bài [-곤 하다](/gon-hada-ki-mareonida-tieng-han/)

**Trước:** 0 inbound link

**Sau tôi thêm link từ:**

1. [Pillar TOPIK 4](/ngu-phap-nang-cao-sau-topik-4/) — anchor: "cấu trúc -곤 하다, -기 마련이다"
2. [50 mẫu câu](/50-mau-cau-topik-nang-cao/) — anchor: "nhóm 4: -기 마련이다"
3. [Giả định nâng cao](/ngu-phap-gia-dinh-nang-cao-topik/) — anchor: "so sánh với -기 십상이다"

**Kết quả:** 3 inbound → không còn orphan.

---

## Kết quả SEO sau 6 tuần

| Metric | Trước | Sau |
|--------|-------|-----|
| Orphan pages (Korean) | 7 | 0 |
| Avg position "ngữ pháp tiếng Hàn TOPIK" | 18 | 9 |
| Internal links/bài | 1.2 | 4.5 |

---

## Liên kết cluster

- [FAQ Schema ngân hàng](/faq-schema-cluster-ngan-hang-ctr/)
- [QA Gatekeeper](/qa-gatekeeper-vaccine-autofixer/)
- [Pillar ngữ pháp Hàn](/ngu-phap-nang-cao-sau-topik-4/)
- [Prompt Zola](/he-thong-prompt-zola-blog/)
