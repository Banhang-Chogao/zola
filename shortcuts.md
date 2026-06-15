# Phím tắt tương tác với Claude

Source of truth cho các shortcut commands giữa user và Claude. Khi user
gõ shortcut, Claude THỰC THI NGAY, không hỏi lại, không giải thích dài.

## `gg` — Deploy to production

Hành động: Claude check tất cả PR đang mở trên repo. Với mỗi PR chưa
merge, Claude:
1. Verify CI status (nếu CI failing → báo lỗi cụ thể, không merge bừa)
2. Squash merge PR vào `main` (trigger deploy.yml tự động)
3. Confirm deploy thành công qua GitHub Pages

Sau khi merge xong → ngắn gọn báo cáo: `Merged PR #X, #Y. Production deploy đang chạy.`

KHÔNG hỏi lại. KHÔNG giải thích flow. Chỉ thực thi.

## `ad` — Audit blog

Hành động: Claude tự động chạy full audit, bao gồm:
1. **Performance**: Lighthouse score (LCP, CLS, INP, TBT) trên homepage + 1 post
2. **Code quality**: scripts/qa_check.py + check console errors
3. **Security**: dependency vulnerabilities (`npm audit` không áp dụng, check `requirements.txt`/Python deps), exposed secrets, CORS misconfig
4. **SEO**: meta tags, alt tags, sitemap, structured data
5. **Accessibility**: ARIA, keyboard nav, color contrast (lưu ý trên SCSS palette)

Output: punch list ≤200 words: done / warnings / errors, sorted by severity.

## Auto-healing pipeline

Khi BẤT KỲ workflow nào fail (Deploy, Performance Audit, Security Audit,
Build Related, QA Gatekeeper, Self-Healing QA):

→ Workflow `.github/workflows/qa-failed-handler.yml` tự động trigger
→ Chạy `qa-failed.py` phân tích logs
→ Match pattern (ModuleNotFoundError / frontmatter / git race / permission)
→ Apply safe fix nếu match → commit + push main → deploy tự re-trigger
→ KHÔNG match pattern hoặc fix fail → tạo GitHub issue `qa-failed` label
  + log artifact 14 ngày để user investigate

Khi user gõ `gg`, Claude phải xác nhận auto-healing đang active. Nếu
workflow `qa-failed-handler.yml` bị disable → báo cáo ngay.

## Quy tắc thực thi shortcut

- Shortcut PHẢI là single line, no extra context.
- Nếu user gõ shortcut KÈM thêm context (e.g., `gg PR #82 only`) → exec với scope hẹp.
- Shortcut KHÔNG hiệu lực giữa câu nói dài. Phải đứng ĐẦU message.
