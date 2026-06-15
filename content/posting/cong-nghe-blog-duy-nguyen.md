+++
title = "Hành trình công nghệ: Dưới nắp ca-pô của blog cá nhân Duy Nguyen"
description = "Stack 3 lớp tối giản: Zola + GitHub Pages + GitHub Actions. Mini CMS vanilla JS, QA Gatekeeper auto-fix, defense in depth, $0/tháng. Lighthouse 99/100."
date = 2026-06-15
aliases = ["/cong-nghe-blog-duy-nguyen/"]

[taxonomies]
categories = ["Ẩm thực"]
tags = ["cms", "github actions", "tech stack", "vanilla js", "zola"]
[extra]
thumbnail = "https://picsum.photos/seed/cong-nghe-blog-duy-nguyen/600/400"
featured = true
featured_at = "2026-06-15T09:43:31.498Z"
+++

![Hành trình công nghệ]

Blog này không phải một template "fork-and-deploy". Mỗi tính năng đều
được viết tay từ đầu — không framework JavaScript, không runtime
dependency, không backend server. Toàn bộ trải nghiệm tương tác chạy
**client-side thuần** trên trình duyệt visitor. Bài viết này tổng kết
stack công nghệ và những quyết định kỹ thuật đằng sau hậu trường.

<!-- more -->

## Tổng quan kiến trúc

Stack ba lớp đơn giản nhưng nguyên tắc:

- **Zola** (Rust static site generator) build markdown thành HTML
- **GitHub Pages** host miễn phí, CDN toàn cầu
- **GitHub Actions** CI/CD: chạy build, QA gate, self-healing, auto-deploy

Toàn bộ chi phí vận hành: `$0/tháng`. Build time: dưới 1 giây cho ~70
trang. Lighthouse Performance: 99/100.

Triết lý xuyên suốt là **zero runtime dependency**. Không có
`node_modules`, không bundler, không transpiler. Mỗi file JavaScript
là một IIFE chạy thẳng, không qua build step.

## Mini CMS: viết bài trực tiếp từ trình duyệt

Trang `/editor/` cho phép tôi viết bài Markdown live-preview rồi push
thẳng file `.md` vào repo qua GitHub REST API. Toàn bộ là vanilla JS
tự viết, không Netlify CMS, không backend.

**Cơ chế xác thực hai tầng:**

1. **OTP gate** (SHA-256 hash trong source) — chống casual visitor vô
   tình click vào `/editor/`. Modal cố định giữa màn hình, blur
   backdrop, input chặn password manager autofill.

2. **GitHub PAT** — tầng bảo vệ thật. Token chỉ giữ trong sessionStorage,
   prompt một lần mỗi tab session, đóng tab là clear. Không bao giờ
   chạm vào localStorage hay cookies.

Editor có toolbar markdown 10 nút SVG inline (B/I/H/Link/Image/Quote/
Code/List), keyboard shortcuts (`Ctrl+S/B/I/K/E`), live split-preview
debounce 500ms, autosave draft mỗi 1 giây, và slash command menu (gõ
`/` mở menu suggest — tương tự Notion). Caret position được tính bằng
mirror div technique, hoàn toàn vanilla JS.

## QA Gatekeeper: tự dọn rác

`qa_check.py` (Python stdlib only) chạy trước mỗi commit qua
`pre-commit` hook và trên CI để chặn:

- Conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`)
- Hardcoded secrets (GitHub PAT, OpenAI key, AWS, Slack token, ...)
- Bài viết thiếu title/date/body hoặc body quá ngắn (sẽ làm Zola
  crash khi extract summary)

Self-healing cấp 2: GitHub Action chạy cron mỗi 6 tiếng với flag
`--fix`. Tự normalize tags (lowercase + dedupe + sort), format date,
trim whitespace, đảm bảo trailing newline. Sau khi fix, bot tự mở PR
`fix/auto-qa` (rolling branch, single PR) cho tôi review. Không bao
giờ auto-merge.

## Real-time deploy status

Header banner trên mọi trang hiển thị trạng thái deploy GitHub Pages
real-time. Logic:

```js
// 1. GET /repos/.../deployments?environment=github-pages
// 2. GET <statuses_url> của deployment mới nhất
// 3. Hiển thị: QUEUED / PROCESSING / DONE / FAILED + timestamp
```

Cache `sessionStorage` 60 giây để không tốn quota GitHub API 60/h
unauth. Hai container `[data-deploy-status]` (deploy row trong GitHub
box + github-pages card) share cùng một fetch qua `querySelectorAll`.

## Auto-changelog: bot tự cập nhật trang Changelog

Mỗi khi PR merge vào main, GitHub Action `changelog-update.yml`
trigger và chạy Python script:

1. Parse PR data từ env (`PR_TITLE`, `PR_BODY`, `PR_ADDITIONS`, ...)
2. Infer tag (label → prefix → keyword → default 'chore')
3. Extract highlights từ bullet points trong PR body, max 5 items
4. Mask secret-like patterns trước khi ghi (GitHub PAT, AWS key, OTP,
   ...)
5. Prepend entry mới vào đầu mảng `items` trong `changelog.json`
6. Bot commit + push lên main (retry pull-rebase nếu conflict với
   deploy bot)

Trang `/changelog` render dữ liệu này qua Zola `load_data` tại build
time. Mỗi entry có Meta Verified badge (gradient xanh + checkmark) và
stats line `−X dòng xóa · +Y dòng thêm · Net Z dòng`.

## Bảo mật: defense in depth

Vì blog static thuần và CMS chạy client-side, mỗi layer phải tự bảo
vệ:

- **Content Security Policy** meta tag (GitHub Pages không cho custom
  HTTP headers): `default-src 'self'`, allowlist CDN cho marked +
  GA4 + web-vitals, `frame-ancestors 'none'` chống clickjacking
- **Subresource Integrity** placeholder cho CDN script (đã từng bật
  rồi gỡ vì version drift)
- **XSS sanitize**: trước khi `innerHTML = marked.parse(body)`, strip
  `<script>`, `<iframe>`, `on*=` attrs, `javascript:`/`data:` URLs
- **RSS DOM-based render**: thay `innerHTML` concat bằng
  `createElement` + `textContent` cho mọi giá trị từ external feed
- **security.txt** RFC 9116 báo cáo vulnerability qua GitHub Security
  Advisory channel

## Tools nhỏ tự xây

Ngoài CMS và changelog, blog có vài tool đứng riêng:

- **`/converter/`** — chuyển số sang chữ Hán Hàn (Sino-Korean). Hỗ
  trợ tới 16 chữ số (hàng `경`, 10¹⁶) qua BigInt. Hai style song
  song: Formal `정식` và Natural `자연`. Mobile responsive, dark mode
  auto.
- **`/stats/`** — Speed Insights dashboard, đo Core Web Vitals (LCP /
  FCP / INP / CLS / TTFB) qua thư viện `web-vitals` của Google, lưu
  500 sample gần nhất vào `localStorage`.

## Triết lý cuối: tại sao không Next.js?

Câu trả lời ngắn gọn: tôi không cần.

- **Blog cá nhân** = nội dung chủ yếu là markdown, không cần SSR
  real-time
- **Static + CDN** = TTFB cực thấp, không cold start
- **Vanilla JS** = không vendor lock-in, hiểu rõ từng dòng mình viết,
  debug bằng DevTools không qua source map
- **GitHub Pages** = miễn phí, có sẵn HTTPS, không cần Vercel /
  Netlify dashboard
- **Build under 1s** = dev loop nhanh hơn bất kỳ framework JS nào

Đánh đổi: không có hydration, không có dynamic routes, không có ISR.
Nhưng blog cá nhân thì không cần những thứ đó. Mỗi feature visitor
thấy đều có thể đọc source 1 lần và hiểu — không có magic.

Nếu bạn cũng đang chọn stack cho blog cá nhân, lời khuyên duy nhất là
**bắt đầu nhỏ nhất có thể**. Một file HTML + một file CSS đã đủ để
viết. Thêm khi cần, không thêm khi không.

---

Đọc thêm chi tiết về [QA Gatekeeper: bí quyết blog tự fix lỗi 24/7](/posting/qa-gatekeeper-tu-fix-loi-blog/)
hoặc [Sentence Transformers SBERT cho semantic related posts](/posting/sentence-transformers-sbert-deep-dive/).

**Repo công khai**: [github.com/Banhang-Chogao/zola](https://github.com/Banhang-Chogao/zola).
Mọi feature mô tả ở trên đều có thể đọc source trực tiếp.
