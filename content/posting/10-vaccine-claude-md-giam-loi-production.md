+++
title = "10 vaccine trong CLAUDE.md đã giúp tôi giảm lỗi production"
description = "Quy tắc phòng lỗi AI coding hiệu quả"
date = 2026-06-19
aliases = ["/10-vaccine-claude-md-giam-loi-production/"]
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["claude.md", "vaccine", "ai coding"]
[extra]
thumbnail = "https://banhang-chogao.github.io/zola/img/placeholder/placeholder.svg"
seo_keyword = "10 vaccine CLAUDE.md"
featured = false
+++

**Cập nhật lần cuối:** 19/06/2026

---

**Vaccine** là quy tắc cố định trong `CLAUDE.md` — AI đọc trước mỗi session, giảm lỗi lặp lại. Tôi ghi **10 vaccine** đã giảm lỗi production từ ~40% xuống <5%.

**Cluster:** [Hệ thống prompt Zola](/bai-1-he-thong-prompt-zola-pillar/) · [QA Gatekeeper](/bai-3-qa-gatekeeper-vaccine-autofixer/)

---

## 10 vaccine tôi dùng

### Vaccine 1: Frontmatter Zola bắt buộc

```toml
+++
title = "..."
description = "..."
date = 2026-06-19
[taxonomies]
tags = ["..."]
+++
```

**Lỗi trước:** AI quên `+++` hoặc sai field → build fail.

---

### Vaccine 2: Slug = lowercase, dấu gạch ngang

**Quy tắc:** `bhxh/vssid-khong-hien-bhtn` — không underscore, không tiếng Việt có dấu.

---

### Vaccine 3: Internal link ≥ 3 mỗi bài

Mỗi bài phải link **pillar** + **2 bài cùng cluster** + **1 bài cross-cluster**.

---

### Vaccine 4: Giọng first-person (Tôi…)

E-E-A-T yêu cầu **Experience**. Cấm giọng encyclopedia "Bảo hiểm thất nghiệp là…" mở đầu.

---

### Vaccine 5: Không bịa số liệu

Nếu không có nguồn → ghi **"theo kinh nghiệm tôi"** hoặc **"tham khảo VssID"**.

---

### Vaccine 6: Bảng tóm tắt đầu bài

Mỗi pillar có **bảng tóm tắt** trong 200 từ đầu — featured snippet.

---

### Vaccine 7: FAQ cuối bài (schema-ready)

≥ 3 câu H3 dạng câu hỏi + câu trả lời ngắn đầu tiên.

---

### Vaccine 8: Code block có ngôn ngữ

````markdown
```json
{ ... }
```
````

Không để plain ``` cho JSON-LD.

---

### Vaccine 9: Không xóa code unrelated

Khi sửa file, **chỉ diff phần liên quan** — không refactor lan.

---

### Vaccine 10: Chạy build trước khi commit

```bash
python site/build.py
```

Nếu fail → không merge.

---

## Kết quả đo lường

| Lỗi | Trước vaccine | Sau vaccine |
|-----|---------------|-------------|
| Frontmatter sai | 12/30 bài | 1/30 |
| Orphan page | 9/30 | 0/30 |
| Link 404 | 5/30 | 0/30 |
| Giọng văn sai | 8/30 | 2/30 |

---

## Liên kết

- [Prompt system Zola](/bai-1-he-thong-prompt-zola-pillar/)
- [QA Gatekeeper](/bai-3-qa-gatekeeper-vaccine-autofixer/)
- [FAQ Schema](/faq-schema-cluster-ngan-hang-ctr/)