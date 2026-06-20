+++
title = "Tôi xây dựng hệ thống prompt cho blog Zola như thế nào"
description = "Kiến trúc prompt thực chiến cho static site"
date = 2026-06-19
aliases = ["/he-thong-prompt-zola-blog/"]
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["blog automation", "prompt engineering", "zola"]
[extra]
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
seo_keyword = "hệ thống prompt Zola"
featured = true
+++

**Cập nhật lần cuối:** 19/06/2026

---

Blog tĩnh **Zola** của tôi cần hàng chục bài SEO mỗi tháng — viết tay không kịp, nhưng AI thuần hay lỗi frontmatter, sai internal link, thiếu E-E-A-T. Tôi xây **hệ thống prompt** phân tầng để AI viết đúng format Zola ngay từ đầu.

**AI Cluster:**
- [10 vaccine CLAUDE.md](/10-vaccine-claude-md-giam-loi-production/)
- [QA Gatekeeper & Vaccine Autofixer](/qa-gatekeeper-vaccine-autofixer/)
- [FAQ Schema ngân hàng](/faq-schema-cluster-ngan-hang-ctr/) — output của pipeline

---

## Kiến trúc 4 tầng prompt

```
┌─────────────────────────────────────┐
│  Tầng 1: CLAUDE.md (vaccine cố định) │
├─────────────────────────────────────┤
│  Tầng 2: Cluster context (pillar)   │
├─────────────────────────────────────┤
│  Tầng 3: Article brief (keywords)   │
├─────────────────────────────────────┤
│  Tầng 4: QA Gatekeeper (post-check)  │
└─────────────────────────────────────┘
```

---

## Tầng 1: CLAUDE.md — quy tắc không đổi

Tôi đặt **10 vaccine** trong CLAUDE.md — chi tiết ở [Bài 2](/10-vaccine-claude-md-giam-loi-production/). Ví dụ:

- Luôn dùng frontmatter Zola (`+++` hoặc `---`)
- Internal link dạng relative `.md`
- Giọng văn first-person (Tôi…)
- Không bịa số liệu — ghi nguồn hoặc "theo kinh nghiệm"

---

## Tầng 2: Cluster context

Mỗi cluster có **file context** riêng:

| Cluster | File context | Số bài (authority) |
|---------|--------------|-------------------|
| Finance | `finance-cluster.md` | 9 bài |
| Korean | `korean-cluster.md` | 5 bài |
| AI | `ai-cluster.md` | 3 bài |
| SEO | `seo-cluster.md` | 2 bài |

**Nguyên tắc topical authority:** Korean cluster 5 bài vì đây là chủ đề authority cao; SEO cluster 1–2 bài vì hỗ trợ.

---

## Tầng 3: Article brief template

```markdown
## Brief
- Title: [tiêu đề]
- Slug: [slug-zola]
- Cluster: [finance/korean/ai/seo]
- Pillar: [yes/no]
- Keywords: [kw1, kw2, kw3]
- Internal links (bắt buộc): [url1, url2]
- Word count: 1500–2500
- Format: H2/H3, bảng, FAQ cuối bài
```

Tôi paste brief + cluster context vào prompt — AI viết 1 shot.

---

## Tầng 4: QA Gatekeeper

Sau khi AI viết xong, [QA Gatekeeper](/qa-gatekeeper-vaccine-autofixer/) chạy checklist:

- [ ] Frontmatter đủ field?
- [ ] Internal link ≥ 3?
- [ ] Keyword trong H2 đầu?
- [ ] Không orphan (link về pillar)?
- [ ] FAQ schema-ready?

---

## Ví dụ prompt thực tế (rút gọn)

```
Bạn viết bài Zola cho Finance cluster.
Đọc CLAUDE.md vaccine.
Pillar: /bhxh/vssid-khong-hien-bhtn
Keywords: bảo hiểm thất nghiệp, tra cứu VssID
Link bắt buộc: /huu-tri/tinh-luong-huu-2026, /vietinbank/10-meo-ipay-nang-cao
Giọng: first-person, E-E-A-T
Output: markdown + frontmatter Zola
```

---

## Kết quả tôi đo được

| Metric | Trước hệ thống | Sau hệ thống |
|--------|----------------|--------------|
| Lỗi frontmatter | ~40% bài | < 5% |
| Orphan pages | ~30% | 0% (sau Gatekeeper) |
| Thời gian sửa/post | 45 phút | 10 phút |

---

## Liên kết cluster

- [10 vaccine CLAUDE.md](/10-vaccine-claude-md-giam-loi-production/)
- [QA Gatekeeper](/qa-gatekeeper-vaccine-autofixer/)
- [Sửa orphan tiếng Hàn](/sua-orphan-bai-tieng-han-seo/)
- [Finance cluster](/vssid-khong-hien-qua-trinh-dong-bhtn/)
