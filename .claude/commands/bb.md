---
description: Dán nội dung báo (VnExpress/Dân Trí/Tuổi Trẻ…) → viết lại thành bài blog gốc SEOMONEY, human, 1000+ từ; chờ duyệt trước khi đăng
---

Khi user gõ `bb` (plain text, không argument ngay), thực thi **NGAY** theo section
`### \`bb\`` trong `shortcuts.md` — đọc file đó trước khi làm. `bb` là **source-agnostic**:
nhận nội dung dán từ **nhiều báo** (VnExpress, Dân Trí, Tuổi Trẻ, Thanh Niên, VietnamNet…),
KHÔNG khoá cứng một nguồn. Đây là phím tắt **paste-first** — KHÔNG tự crawl web.

## Parse

- Cú pháp: `bb` (user sẽ DÁN nội dung/nguồn bài báo sau khi nhận prompt).
- Response: "📰 Anh dán nội dung bài báo (hoặc tiêu đề + đoạn chính, kèm URL nếu có) vào đây. Em sẽ viết lại thành một bài blog gốc cho SEOMONEY theo giọng của anh — human, có quan điểm, 1000+ từ, chuẩn SEO — và chờ anh duyệt trước khi đăng."
- Nội dung dán **quá ngắn / không rõ** → HỎI thêm trước khi viết, KHÔNG tự bịa.

## Thực thi (tóm tắt)

1. Chờ user dán nội dung / nguồn → phân tích chủ đề + góc nhìn chính + nguồn (URL công khai nếu có).
2. Research keyword từ nội dung (tự sinh, không hardcode).
3. Chọn category **best-fit** từ `categories.json` theo nội dung (thường Công nghệ, Tài chính,
   SEO, Đời sống…). `"Tất cả"` luôn đứng đầu mảng; thêm `"Báo chí"` vì bài thuộc nhánh tin.
4. Viết bài **hoàn toàn mới** (KHÔNG copy đoạn dài từ nguồn), cấu trúc:
   - **Mở bài** — vì sao chủ đề đáng chú ý
   - **Bối cảnh / context**
   - **Phân tích chính** (≥2 H2)
   - **Điều người đọc rút ra được** (practical takeaway)
   - **Nhận định/quan điểm cá nhân cuối bài** (I-statement, có chính kiến)
   - **Kết luận** rõ ràng
5. Chuẩn: ≥1000 từ (khi đủ chất liệu), title ≤70 ký tự, description 50–160 ký tự, ≥3 tag,
   ≥1 ảnh có `alt`, internal link tới bài liên quan **nếu có** (không bịa URL).
6. Front matter Zola: `title`, `date`, `description`, `slug` (kebab-case không dấu),
   `categories`, `tags`, `thumbnail` (nếu pattern hỗ trợ), `seo_keyword`.
7. An toàn (BẮT BUỘC):
   - **Bản quyền**: tóm tắt/phân tích/viết lại — KHÔNG copy nguyên văn đoạn dài; KHÔNG để lộ
     nguyên bài gốc thành output cuối.
   - **Sự thật**: chỉ giữ fact có trong nội dung dán; điểm cần kiểm chứng → ghi
     "theo nội dung được trích/dán" hoặc bỏ. KHÔNG bịa số liệu/sự kiện.
   - **AdSense-safe**: không clickbait, không phỉ báng, không overclaim tài chính/y tế/pháp lý,
     không xúi click quảng cáo.
   - **Riêng tư**: KHÔNG đưa email/tên máy/đường dẫn local/token/log thô.
8. File: `content/baochi/<slug>.md`. Gate: `build_references.py` → `seo_qa_checker.py`
   → `qa_check.py` → `check_internal_links.py`.
9. Commit (1 file) lên branch dev: `feat: add bb article — <slug> (inspired by <source>)`.

## Approval gate (KHÔNG tự đăng)

- **KHÔNG auto-merge / auto-deploy.** Sau khi viết + commit lên branch dev, in summary và
  **CHỜ user duyệt** ("đăng"/"merge") rồi mới merge `main` → deploy. Đây là yêu cầu an toàn
  của `bb` (no auto-publish) — khác các shortcut auto-merge khác.

## Output

Summary only (≤150 từ): nguồn · chủ đề · category · file · words · SEO QA · QA · branch.
Kết bằng 1 dòng nhắc: "Duyệt đăng? (gõ để merge/deploy)".

KHÔNG thêm CSS/JS. Tuân S-DNA + Branding + Font Guideline.
KHÔNG nói "bài lấy từ <báo>" trừ khi user yêu cầu + có URL công khai cần dẫn.
