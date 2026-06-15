+++
title = "Ngày thứ hai của blog: 100 PR và stack công nghệ tự nâng cấp"
description = "Tổng kết 100+ pull request và tech stack tự nâng cấp trong ngày 2: AI semantic related posts, QA dashboard footer, mobile UX Threads-feel, typography Manrope, GA stats live, image LCP/CLS chuẩn 2026."
date = 2026-06-15
aliases = ["/cong-nghe-blog-day-2/"]

[taxonomies]
categories = ["Ẩm thực"]
tags = ["ai", "ci/cd", "cms", "fastapi", "github actions", "sentence-transformers", "tech stack", "vanilla js", "zola"]
[extra]
thumbnail = "https://picsum.photos/seed/cong-nghe-day-2/600/400"
featured = false
+++

![Tech stack day 2]

Sau bài [Hành trình công nghệ ngày đầu](/posting/cong-nghe-blog-duy-nguyen/),
blog tiếp tục được nâng cấp với tốc độ hơn **100 pull request chỉ trong
một ngày**. Bài này tổng kết các module mới và công nghệ áp dụng — tất
cả đều đang **thực tế chạy** trên blog, không phải demo. Dữ liệu lấy
trực tiếp từ `changelog.json` build-time qua Zola `load_data`.

<!-- more -->

## AI Semantic Related Posts

Tính năng quan trọng nhất triển khai ngày 2: hệ thống **related posts
dựa trên ngữ nghĩa**, không chỉ category hoặc tag matching thông thường.
Nếu muốn đi sâu vào kỹ thuật, đọc bài
[Sentence Transformers (SBERT): kiến trúc, training và ứng dụng](/posting/sentence-transformers-sbert-deep-dive/)
để hiểu chi tiết bi-encoder + cosine similarity.

Pipeline build-time:

1. Script `scripts/build_related.py` quét `content/posting/*.md` (TOML
   frontmatter qua `tomllib` stdlib Python 3.11)
2. `sentence-transformers` model `paraphrase-multilingual-MiniLM-L12-v2`
   encode title + categories + tags + body thành vector 384 chiều
3. Cosine similarity matrix qua `numpy` dot product (vector đã normalize)
4. Top-5 related per post → `data/related.json`
5. Aggregate score = mean của top scores → `data/scores.json`

Web load JSON tĩnh, **0 cost backend**, phù hợp GitHub Pages. Workflow
`build-related.yml` chạy cron `*/5 * * * *` (mỗi 5 phút trong test
phase) rồi tự throttle xuống `0 * * * *` (mỗi giờ) qua workflow
`auto-throttle.yml` để tiết kiệm GitHub Actions quota.

Model multilingual hiểu Tiếng Việt khá tốt — bài "tối ưu hóa ảnh" sẽ
related với "tăng tốc tải trang" dù không chung từ khóa nào.

## Scoring Card: bảng điểm bài viết

Trang `/scoring/` hiển thị bảng tất cả bài viết với **semantic
similarity score**. Score cao = bài có nhiều bài tương đồng ngữ nghĩa
trong network ("well-connected"). Score thấp = bài unique hoặc
isolated.

UI có 3 tier badge gradient theo điểm:

- **High** (≥70%): xanh lá gradient
- **Mid** (40-70%): cam gradient
- **Low** (<40%): xám gradient

Bảng hỗ trợ client-side sort (score / date / title A-Z) và filter time
range (7d / 30d / 90d / all) qua vanilla JS ~2KB. Server-render rows
qua Tera, JS chỉ reorder DOM → instant UX, 0 network call.

## QA Dashboard footer

Section build-time snapshot ở footer hiển thị **6 metric cards**:

| Card | Labels | Data source |
|---|---|---|
| Performance Audit | AUTO + WEEKLY | Cron CN 02:00 UTC |
| Security Scan | CRON + AUDIT | pip-audit + gitleaks weekly |
| Semantic Scoring | AI + PYTORCH | `data/scores.json` length |
| PR Activity | GITHUB + AUTO | `changelog.json` items length |
| Tag Network | STATIC + BUILD | `get_taxonomy()` tags + categories |
| Production Deploy | LIVE + PAGES | `get_section()` posting pages |

Layout 3 cột desktop, 2 cột tablet (≤1024px), 1 cột mobile (≤480px) —
tuân thủ rule responsive trong `CLAUDE.md`. Mỗi card có border 1.5px,
padding chuẩn, labels màu theo 7-color palette (red/green/blue/yellow/
orange/purple/gray).

## Self-healing & Auto-throttle

Pipeline tự sửa lỗi mở rộng thêm 2 lớp:

**`qa-failed.py`** — script Python phân tích logs failed workflow,
match pattern (`ModuleNotFoundError`, Tera syntax, git race, permission
denied), apply fix nếu confident. Buffer + retry 3 lần × 30s tránh race
với GitHub API log lag. Pattern unknown → tạo issue label `qa-failed`
escalate cho user.

**`auto-throttle.yml`** — one-shot workflow chạy 16/06 00:00 UTC sed
thay cron `build-related.yml` từ `*/5 * * * *` xuống `0 * * * *`.
Idempotent: lần fire kế tiếp năm sau no-op vì pattern không match.

## Security Audit cron

Workflow mới `security-audit.yml` chạy cron `0 3 * * 6` (T7 03:00 UTC)
scan 3 dimension:

- **`pip-audit`** trên `services/visitor-counter/requirements.txt` +
  `scripts/requirements.txt` cho CVE
- **`gitleaks`** toàn repo cho secret leak (GitHub PAT, AWS, Slack
  tokens, ...)
- **Workflow permission misconfig** — mỗi `.github/workflows/*.yml`
  phải có `permissions:` block explicit

Output summary + artifacts retention 30 ngày. Không tự fix → user
review báo cáo qua tab Actions.

## Mobile UX Threads-feel

Loạt PR mobile-only theo style **iOS Threads**:

- **Frosted glass navbar**: `backdrop-filter: blur(14px) saturate(180%)`
  + `rgba(17, 17, 17, 0.88)` background → semi-transparent header với
  content phía dưới mờ khi scroll
- **Tap feedback**: `:active { transform: scale(0.97); opacity: 0.85 }`
  chỉ áp `@media (hover: none) and (pointer: coarse)` — không ảnh
  hưởng desktop hover
- **Smooth scroll** + `scroll-padding-top: calc(60px + env(safe-area-inset-top))`
  cho anchor jump không bị che navbar
- **Tap-highlight-color** subtle đỏ `rgba(214, 61, 61, 0.08)` thay xanh
  mặc định iOS
- **`overscroll-behavior-y: contain`** ngăn rubber-band flash khi scroll
  hết trang

iPhone Dynamic Island + Home Indicator được tính safe-area-inset trong
padding navbar + footer.

## Typography upgrade

Stack font mới ưu tiên đa ngôn ngữ + đẹp diacritics:

- **Manrope** (body + heading): round, friendly, full Vietnamese
- **Inter** (UI menu + button): geometric clean, pair tốt với Manrope
- **Be Vietnam Pro** (post meta): diacritics tiếng Việt cực mềm mại
- System mono (code): SF Mono / Consolas

3 font families gộp vào 1 request Google Fonts với `display=swap`,
non-blocking qua `media=print onload swap` trick → FCP/LCP không bị
delay. Desktop body 17px line-height 1.7, mobile 16px line-height
1.65.

## Tag Cloud grid

Thay flex-wrap pills cũ bằng **grid 5 cột uniform** giống tech-stack
showcase. Mỗi tag = 1 card có border, badge HOA màu (8-color cycle
qua `loop.index0 % 8`), mô tả số bài dưới. Responsive: 5 → 4 → 3 → 2
cột theo viewport.

## GA4 + GA Stats live

Module Google Analytics 4 bao gồm:

- Tracking script `gtag.js` async đặt trước `</body>` → không block
  FCP/LCP
- **GA pill ở footer** click mở dashboard intelligenthome (Property ID
  541698865)
- **GA Stats card** dưới QA Dashboard — fetch Data API v1beta qua
  workflow `ga-stats.yml` cron `0 * * * *` (hourly)
- Service Account auth qua GitHub Secret `GA_SERVICE_ACCOUNT_KEY`
- 3 cell hiển thị users + pageviews hôm nay / 7 ngày / 30 ngày
- DEMO mode (amber) khi chưa setup secret, tự chuyển LIVE (green) sau
  fetch lần đầu

## Image LCP/CLS chuẩn 2026

Audit toàn site tối ưu loading attribute:

- **Above-the-fold** (hero, item đầu list): `loading="eager"
  fetchpriority="high"`
- **Below-the-fold** (sidebar, related): `loading="lazy"`
- Tất cả `<img>` thêm `width` + `height` attribute matching CSS
  `aspect-ratio` → browser reserve space ngay khi parse HTML, chống
  CLS dù CSS chưa kịp load
- Hero post 1600×700 (aspect 16/7), card thumbnail 800×600 (4/3),
  related 800×500 (16/10), avatar 80×80 (1/1)

## Shortcut system

7 phím tắt thiết lập qua `shortcuts.md`:

| Shortcut | Mục đích |
|---|---|
| `gg` | Deploy production (merge open PRs) |
| `ad` | Full audit (perf + security + SEO + a11y) |
| `ff` | Full Fix & Deploy fast-path |
| `healing` | QA-Healing thủ công với baseline qa_check.py |
| `sec` | Security Audit only |
| `pef` | Performance Audit only |
| `ll` | Liệt kê cron 3 workflow QA core |
| `run list` | Table 4 cột (Run ID / Workflow / Cause / Status) |

Mỗi shortcut là single line trigger Claude exec ngay, không hỏi lại,
không giải thích dài.

## Quy tắc CSS/Responsive bất biến

`CLAUDE.md` đã lock-in 5 rule sau khi gặp sự cố scroll desktop:

1. **Phân tách phạm vi**: Mobile (media query) ≠ Desktop (global) là 2
   quy trình độc lập
2. **Không sửa Desktop ngoài phạm vi**: cấm đụng `html`, `body`, `*`,
   `.container`, `.navbar` global khi user yêu cầu mobile
3. **Ổn định scroll**: cấm anti-pattern `html, body { overflow-x:
   hidden }`, cấm `body { overflow: hidden }` không scope mobile, cấm
   `height: 100vh` thừa
4. **Code tách block**: sửa cả 2 → 2 block riêng có comment header `/*
   ===== DESKTOP ===== */` + `/* ===== MOBILE ===== */`
5. **Test plan bắt buộc**: mental check desktop scroll + mobile menu
   trước khi merge

## Triết lý ngày 2: tự động hoá > thủ công

Ngày đầu, mọi cải tiến phải tự gõ git commit + push. Ngày 2, hệ thống
**tự sửa lỗi mechanical** (self-healing 6h cron), **tự rebuild AI
related** (build-related hourly), **tự fetch GA stats** (ga-stats
hourly), **tự audit performance** (perf-audit weekly), **tự audit
security** (security-audit weekly), **tự update changelog** mỗi khi
PR merge.

100 PR trong 1 ngày không phải do gõ tay nhanh — mà do mỗi PR sau khi
merge sẽ trigger 3-5 workflow tự động chạy phía sau. Code mới sửa code
cũ. Test mới validate test cũ. Đó là cách scale.

---

**Repo công khai**: [github.com/Banhang-Chogao/zola](https://github.com/Banhang-Chogao/zola).
Mọi feature mô tả ở trên đều có source trực tiếp, có thể đọc và copy.
