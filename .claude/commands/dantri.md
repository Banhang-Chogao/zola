---
description: Paste nội dung nguồn → viết lại thành bài blog mới, human-tone, 1000+ từ, chuẩn SEO, có review
---

Khi user gõ `dantri` (plain text, không argument ngay), thực thi **NGAY** theo section
`### dantri` trong `shortcuts.md` — đọc file đó trước khi làm.

> **Alias hẹp của `bb`**: `dantri` dùng chung engine viết lại paste→bài gốc của `bb`
> (xem `.claude/commands/bb.md` + section `### \`bb\`` trong `shortcuts.md`). Khác biệt:
> `dantri` không ép `content/baochi/`/`"Báo chí"` (đặt section theo nội dung). **Cùng
> approval gate** với `bb`: chờ user duyệt, KHÔNG tự đăng.

## Parse

- Cú pháp: `dantri` (user sẽ dán nội dung/link sau khi nhận prompt)
- Response: "Anh dán nội dung bài gốc hoặc link + phần nội dung chính vào đây. Em sẽ viết lại thành một bài blog mới theo góc nhìn của anh, văn phong human, chuẩn SEO, hơn 1000 từ, có nhận định/review cuối bài, và không copy nguyên văn nguồn."

## Thực thi (tóm tắt)

1. Chờ user dán nội dung / link + excerpt.
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
11. Commit (1 file) lên branch dev: `feat: add dantri article — <slug> (inspired by <source>)`.
12. **DỪNG & chờ user duyệt** (cùng approval gate với `bb`) — KHÔNG auto-merge/deploy;
    chỉ merge `main` → deploy sau khi user duyệt rõ ràng.

## Output

Summary only (≤150 từ): nguồn · chủ đề · file · words · SEO QA · QA · push branch.

KHÔNG hỏi xác nhận. KHÔNG thêm CSS/JS. Tuân S-DNA + Branding + Font Guideline.
KHÔNG nói "bài này lấy từ Dân trí" trừ khi user yêu cầu + có URL công khai cần dẫn.
