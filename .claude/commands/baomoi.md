---
description: Từ chủ đề user → bài hoặc series Markdown production-ready, category AI-driven, SEO Google
---

Khi user gõ `/baomoi <topic>` hoặc `baomoi <topic>` (plain text), thực thi **NGAY**
theo section `### baomoi <topic>` trong `shortcuts.md` — đọc file đó trước khi làm.

## Parse

- Cú pháp: `baomoi <chủ đề>` — thiếu topic → hỏi lại, không tự bịa.
- Ví dụ: `baomoi ChatGPT Agent mới của OpenAI`, `baomoi BHXH 1 lần 2026`.

## Thực thi (tóm tắt)

1. Research topic (WebSearch nếu cần facts 2026).
2. AI quyết định **single vs series** (2–5 bài), section `baochi` vs `posting`.
3. **Category AI-driven** từ `categories.json` — KHÔNG hardcode; `"Tất cả"` đầu mảng;
   `"Báo chí"` chỉ khi tin trong `content/baochi/`; tạo category mới chỉ khi cần.
4. Viết Markdown production-ready: SEO on-page, E-E-A-T, ≥5 internal links, FAQ khi
   phù hợp, giọng Việt tự nhiên, không picsum — placeholder ảnh hệ thống.
5. Grep tránh duplicate slug/title; cross-link nếu series.
6. Gate: `build_references.py` → `seo_qa_checker.py` → `qa_check.py` →
   `check_internal_links.py`.
7. Commit chỉ file liên quan → push → auto-merge (không mở PR thủ công).

## Output

Summary only (≤150 từ): topic · single/series · files · category · SEO QA · QA · push branch.

KHÔNG hỏi xác nhận. KHÔNG thêm CSS/JS. Tuân S-DNA + Branding + Font Guideline.