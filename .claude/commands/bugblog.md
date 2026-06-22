---
description: Sau bugfix dài/nhiều debug → soạn nháp blog case-study công nghệ SEO-safe từ bài học kỹ thuật (không tự đăng)
---

Khi user gõ `/bugblog` hoặc `bugblog` (plain text), thực thi **NGAY** theo section
`### \`bugblog\`` trong `shortcuts.md` — đọc file đó trước khi làm. Doctrine nền:
`CLAUDE.md` §"Post-Bugfix → Blog Draft Policy".

## Parse

- Cú pháp: `bugblog` (không cần argument).
- Nếu vừa fix xong trong session → tự rút thông tin từ session, chỉ hỏi phần thiếu.
- Nếu chưa có context → response gom 6 trường: issue summary · root cause · fix ·
  QA result · vaccine/prevention · public-safe details.

## Trigger (chỉ khi đủ)

- Chỉ sau **bugfix/debug task** đã substantially complete HOẶC có bài học rõ.
- "Done" cần bằng chứng (QA/build/commit/PR/deploy). Thiếu → chỉ ra **draft notes**,
  KHÔNG bài publish-ready, KHÔNG bịa "production success".
- KHÔNG chạy cho thay đổi nhỏ/cosmetic hoặc khi còn đang debug dở.

## Thực thi (tóm tắt)

1. Thu thập 6 trường ở trên (tự rút từ session, hỏi phần thiếu).
2. **Chọn mode**: chất liệu mỏng / chưa xong → **draft notes** (bullet, không frontmatter,
   không vào `content/posting/`); xong + đủ liệu → **full article**.
3. Full article: Zola Markdown ≥1000 từ tiếng Việt, ngôi thứ nhất, human, SEO-friendly,
   gồm Problem · Symptoms · Root cause · Debugging steps · Fix · Vaccine/Prevention ·
   Checklist · Lessons learned. Category mặc định **Công nghệ**.
4. **Safety guards**: bỏ private/local (path, secret, token, URL nội bộ, log thô, account);
   AdSense-safe (no clickbait/misleading/overclaim/xúi click ads); no fabrication.
5. **No auto-publish**: trình nháp cho user; chỉ lưu `content/posting/<slug>.md` **sau khi
   user duyệt rõ ràng**, rồi mới qua gate `seo_qa_checker.py` → `qa_check.py` →
   `check_internal_links.py` → commit 1 file. KHÔNG đụng UI/UX.

## Output

Summary only: mode · chủ đề · material/evidence · file · words · safety checks · next.

KHÔNG tự đăng. KHÔNG thêm CSS/JS. Tuân S-DNA + Branding + Font Guideline.
