+++
title = "Tôi thiết kế QA Gatekeeper và Daily Vaccine Autofixer"
description = "Pipeline kiểm soát chất lượng cho AI workflow"
date = 2026-06-19
aliases = ["/qa-gatekeeper-vaccine-autofixer/"]
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["qa gatekeeper", "vaccine autofixer", "ai workflow"]
[extra]
thumbnail = "https://banhang-chogao.github.io/zola/img/placeholder/placeholder.svg"
seo_keyword = "QA Gatekeeper Vaccine Autofixer"
featured = false
+++

**Cập nhật lần cuối:** 19/06/2026

---

Sau [10 vaccine CLAUDE.md](/zola/10-vaccine-claude-md-giam-loi-production/), tôi cần **lớp kiểm tra tự động** — vì AI vẫn thỉnh thoảng bỏ qua vaccine khi context dài. **QA Gatekeeper** chạy post-generation; **Daily Vaccine Autofixer** quét repo mỗi ngày.

**Cluster:** [Hệ thống prompt](/zola/he-thong-prompt-zola-blog/) · [Internal link orphan](/zola/sua-orphan-bai-tieng-han-seo/)

---

## QA Gatekeeper — kiến trúc

```
Article markdown
       │
       ▼
┌──────────────┐
│  Gatekeeper  │
│  (checklist) │
└──────┬───────┘
       │
   Pass? ──No──► Autofixer prompt
       │
      Yes
       │
       ▼
   Publish / Build
```

---

## Checklist Gatekeeper (12 mục)

| # | Kiểm tra | Fail action |
|---|----------|-------------|
| 1 | Frontmatter hợp lệ | Autofix thêm `+++` |
| 2 | Title ≠ empty | Báo lỗi |
| 3 | Internal links ≥ 3 | Gợi ý link từ cluster map |
| 4 | Link về pillar | Thêm link pillar |
| 5 | Không self-link orphan | Thêm inbound từ pillar |
| 6 | Keywords trong H2 | Gợi ý đổi H2 |
| 7 | FAQ ≥ 3 | Generate FAQ block |
| 8 | Bảng tóm tắt (pillar) | Thêm template bảng |
| 9 | Không link 404 | Map slug từ build.py |
| 10 | Giọng "Tôi" ≥ 3 lần | Rewrite intro |
| 11 | JSON-LD valid (nếu có) | Fix syntax |
| 12 | `build.py` pass | Chạy build |

---

## Daily Vaccine Autofixer — cron hằng ngày

Tôi chạy script lúc **6h sáng** (cron):

```bash
# 1. Quét orphan pages
python scripts/find_orphans.py articles/

# 2. Quét link 404
python site/build.py 2>&1 | grep SKIP

# 3. Autofix frontmatter thiếu
python scripts/autofix_frontmatter.py

# 4. Báo cáo Slack/email
python scripts/daily_report.py
```

**Output:** File `daily-vaccine-report.md` — tôi review 5 phút trước khi publish batch mới.

---

## Autofixer prompt (rút gọn)

```
Bài sau FAIL Gatekeeper mục: [3, 4, 9]
Cluster map: [danh sách slug]
Chỉ sửa: thêm internal link, không đổi nội dung chính.
Link bắt buộc thêm: /tieng-han/ngu-phap-nang-cao-sau-topik-4, /seo/sua-orphan-tieng-han
```

---

## Kết hợp với SEO cluster

Gatekeeper tích hợp logic từ [Sửa orphan tiếng Hàn](/zola/sua-orphan-bai-tieng-han-seo/):

1. Build **link graph** từ tất cả `.md`
2. Node **in-degree = 0** → orphan
3. Autofixer thêm link từ pillar hoặc bài cùng cluster

---

## Kết quả sau 30 ngày

| Metric | Tuần 1 | Tuần 4 |
|--------|--------|--------|
| Orphan pages | 7 | 0 |
| Gatekeeper pass rate | 62% | 94% |
| Manual fix time | 2h/tuần | 20 phút/tuần |

---

## Liên kết

- [10 vaccine](/zola/10-vaccine-claude-md-giam-loi-production/)
- [Prompt Zola](/zola/he-thong-prompt-zola-blog/)
- [FAQ Schema ngân hàng](/zola/faq-schema-cluster-ngan-hang-ctr/)
- [Orphan strategy](/zola/sua-orphan-bai-tieng-han-seo/)