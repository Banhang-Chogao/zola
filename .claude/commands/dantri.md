---
description: Crawl bài từ dantri.com.vn (link) → viết lại thành bài blog mới, human-tone, 1000+ từ, chuẩn SEO, có review
---

Khi user gõ `dantri` (plain text, không argument ngay), thực thi **NGAY** theo section
`### dantri` trong `shortcuts.md` — đọc file đó trước khi làm.

> **Riêng biệt với `bb`** (KHÔNG dùng chung logic). `dantri` chuyên **crawl tin từ
> dantri.com.vn** (user đưa link dantri.com.vn → Claude tự fetch/đọc bài → viết lại).
> `bb` thì ngược lại — viết từ **văn bản user copy/dán** (đa nguồn). Phạm vi `dantri`:
> **chỉ dantri.com.vn**.

## Parse

- Cú pháp: `dantri` (user sẽ đưa **link dantri.com.vn** sau khi nhận prompt).
- Response: "Anh dán **link bài trên dantri.com.vn** (hoặc nội dung chính nếu fetch bị chặn) vào đây. Em sẽ crawl bài đó, viết lại thành một bài blog mới theo góc nhìn của anh, văn phong human, chuẩn SEO, hơn 1000 từ, có nhận định/review cuối bài, và không copy nguyên văn nguồn."

## Thực thi (tóm tắt)

1. Chờ user đưa link dantri.com.vn → **fetch/crawl** bài (WebFetch). Network chặn → dùng nội dung user dán.
2. Phân tích nguồn → topic + góc nhìn chính.
3. Research keyword từ nội dung (tự sinh, không hardcode).
4. Viết bài **hoàn toàn mới**:
   - Mở bài: Vì sao chủ đề đáng chú ý?
   - Tóm tắt nội dung bằng lời mới (paraphrase, không copy)
   - Góc nhìn cá nhân (I-statement, có chính kiến)
   - Phân tích/bàn luận những điểm nổi bật
   - Tác động / bài học cho người đọc
   - Nhận định/review cuối bài (rõ ràng)
   - Kết luận (cụ thể)
5. Chuẩn: ≥1000 từ, ≥2 H2/H3, ≥3 tag, title ≤70 ký tự, meta description 140–160 ký tự.
6. ≥2 internal link (semantic) + ≥1 external link uy tín (nếu có trích dẫn).
7. Quality bar: viết lại hoàn toàn, không spin, không lặp câu nguồn, không bịa sự thật.
8. KHÔNG đưa private data: email, tên máy, path local, token, log terminal.
9. Category: chọn từ `categories.json` theo nội dung; `"Tất cả"` đầu mảng.
10. Gate: `build_references.py` → `seo_qa_checker.py` → `qa_check.py` → `check_internal_links.py`.
11. Commit (1 file): `feat: add dantri article — <slug> (inspired by <source>)`.
12. Push → auto-merge (không mở PR thủ công).

## Output

Summary only (≤150 từ): nguồn · chủ đề · file · words · SEO QA · QA · push branch.

KHÔNG hỏi xác nhận. KHÔNG thêm CSS/JS. Tuân S-DNA + Branding + Font Guideline.
KHÔNG nói "bài này lấy từ Dân trí" trừ khi user yêu cầu + có URL công khai cần dẫn.
