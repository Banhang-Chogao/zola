+++
title = "Bug Website Và Vaccine Số: Từ DNS, 404 Đến Conflict PR"
description = "6 bug thật trên blog Zola — HuggingFace 401, GitHub Pages rate limit, stash conflict, Tera syntax sai — và cách mỗi bug sinh ra một vaccine."
date = 2026-06-20
aliases = ["/vaccine-bug-lich-su/"]
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["bug fix", "ci/cd", "github pages", "vaccine số", "zola blog"]
[extra]
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
seo_keyword = "bug website vaccine số"
featured = false
series = "vaccine-so"
series_part = 2
series_total = 5

[[extra.faq]]
q = "Bug nào thường xuyên nhất trên blog Zola tự động?"
a = "Theo kinh nghiệm của tôi: conflict trên data/*.json tự sinh (hầu như mỗi tuần trong giai đoạn phát triển nhanh), rate limit GitHub Pages khi merge nhiều PR cùng lúc, và link 404 từ bài được tạo tự động với URL bịa. Ba loại này chiếm khoảng 70% lần CI đỏ không phải lỗi code."

[[extra.faq]]
q = "Làm sao biết một bug đã đủ điều kiện thành vaccine?"
a = "Tôi dùng quy tắc 3 lần: cùng dấu hiệu trong CI log xuất hiện lần thứ ba thì viết vaccine. Lần đầu fix thủ công, lần hai ghi chú nhanh, lần ba đủ bằng chứng về pattern."

[[extra.faq]]
q = "HuggingFace 401 là lỗi gì?"
a = "Lỗi xác thực 401 từ HuggingFace Hub khi tải model. Nguyên nhân tôi gặp: dùng tên model 'trần' (không có org prefix) như 'paraphrase-multilingual-MiniLM-L12-v2' thay vì 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'. HuggingFace tìm repo ở top-level, không tồn tại, trả 401."

[[extra.faq]]
q = "GitHub Pages API rate limit xảy ra khi nào?"
a = "Khi nhiều PR merge vào main trong khoảng thời gian ngắn — mỗi merge kích hoạt một deploy, mỗi deploy gọi API GitHub Pages. Cộng với data refresh bot chạy định kỳ, tổng số API call vượt quota theo giờ của GitHub App installation."
+++

**Bug website vaccine số** — đây là chuỗi 6 bug thật tôi gặp khi vận hành blog, và mỗi bug là lý do sinh ra một vaccine cụ thể. Không phải lý thuyết. Là nhật ký debug.

Bài trước ([Vaccine Số Là Gì?](/posting/vaccine-so-la-gi-bien-bug-thanh-he-mien-dich-website/)) giải thích khái niệm chung. Bài này đi vào từng case cụ thể — vì vaccine không được sinh ra từ tưởng tượng, mà từ đau thật.

## Bug #1 — HuggingFace 401: Khi Tên Model Thiếu Org Prefix (V1)

**Bối cảnh:** Blog có workflow `build-related.yml` dùng SBERT để tính bài viết liên quan theo semantic similarity. Script gọi `snapshot_download()` từ `huggingface_hub` để tải model về.

**Dấu hiệu CI:** Log báo `401 Client Error: Repository Not Found for url: https://huggingface.co/api/models/paraphrase-multilingual-MiniLM-L12-v2`. Workflow đỏ mỗi 5 phút vì cron.

**Debug 30 phút:** Ban đầu tưởng mạng, tưởng quota, tưởng đủ thứ. Sau cùng phát hiện: class `SentenceTransformer` tự thêm prefix `sentence-transformers/` khi cần, nhưng `snapshot_download()` thì không — nó tìm repo top-level, không tồn tại, trả 401.

**Vaccine V1:** Mọi chỗ gọi `snapshot_download()` hoặc HuggingFace API PHẢI dùng `org/model` đầy đủ. Rule: không bao giờ dùng tên model trần với HF Hub API.

---

## Bug #2 — Slack Notification Vỡ Sau Bump Action (V2)

Workflow `slack-notify.yml` chạy ngon một năm. Dependabot bump `slackapi/slack-github-action` từ v1 lên v3 — mọi thứ vỡ ngay với `Missing input! The webhook type must be 'incoming-webhook'`.

Root cause: v3 đổi API hoàn toàn — không còn env `SLACK_WEBHOOK_TYPE`, thay bằng `with: webhook-type: incoming-webhook` và `payload:` inline JSON. Cú pháp cũ không chạy được trên v3.

**Vaccine V2:** Pin action version cụ thể (`@v3.x`). Mỗi lần bump version thì đọc changelog breaking changes trước, không để auto-merge upgrade major.

---

## Bug #3 — GitHub Pages Rate Limit: Cái Giá Của Merge Storm (V5)

Đây là bug khiến tôi mất nhiều thời gian nhất vì dấu hiệu trông như lỗi code nhưng thực ra không phải.

**Bối cảnh:** Một ngày merge nhiều PR liên tiếp, mỗi PR kích hoạt `deploy.yml`. Khoảng 10–15 deploy run trong 1 giờ.

**Dấu hiệu:** Step `actions/configure-pages` đỏ với `API rate limit exceeded for installation`. `zola build` vẫn pass — lỗi chỉ ở bước Pages, không phải build.

**Debug:** Nhìn vào lịch sử: tất cả fail đều ở `configure-pages`, không phải Zola. Nhìn vào thời điểm: tất cả xuất hiện sau đợt merge dày đặc. Nguyên nhân: mỗi deploy gọi GitHub Pages API; nhiều deploy song song làm cạn quota theo giờ của GitHub App.

**Vaccine V5:** Thêm `concurrency` vào `deploy.yml` — chỉ 1 deploy chạy tại 1 thời điểm, deploy mới xếp hàng (`cancel-in-progress: false`). Data refresh bot bỏ `DISPATCH_DEPLOY` mặc định, chỉ dispatch khi thật sự cần.

---

## Bug #4 — git stash pop Conflict: Khi Bot Tự Phá Mình (V6)

Workflow data refresh (fetch merge report, build dashboard) có pattern:
1. Sinh `data/*.json` mới
2. `git stash`
3. `git pull --rebase`
4. `git stash pop`
5. Commit + push

**Vấn đề:** Nếu `main` đã sinh cùng file `data/*.json` trong lúc bot chạy, `stash pop` gặp conflict. `set -euo pipefail` → script chết ở đây → workflow đỏ.

**Root cause:** Data file do CI tự sinh (timestamp + entries) → không bao giờ nên để conflict này làm sập workflow, vì file của bot luôn là bản mới nhất cần publish.

**Vaccine V6:** Bọc `git stash pop` trong if: nếu fail, lấy bản bot vừa sinh (`git checkout --theirs / stash@{0}`), `git add`, `git stash drop`. Bot data mới nhất = bản publish. Conflict không còn kéo sập workflow.

---

## Bug #5 — Tera Syntax: Python kwargs Trong Template Zola (V8)

**Bối cảnh:** Thêm series mới vào blog. PR không conflict, `zola build` đột nhiên fail với `Filter 'replace' failed: Filter replace expected an arg called 'from'`.

**Debug:** Template dùng `replace(old="-", new=" ")` — cú pháp Python. Tera (template engine của Zola) dùng `replace(from="-", to=" ")` — khác hoàn toàn.

**Tại sao chưa thấy trước?** Branch fallback (orphan series) vốn không active — chỉ kích hoạt khi có series chưa đăng ký trong manifest. Series mới thêm nhưng quên đăng ký → rơi vào orphan fallback → chạm vào Tera syntax sai → vỡ build.

**Vaccine V8:** Hai rule không tách rời nhau:
1. Series mới PHẢI đăng ký trong `series-listing.html`, `page.html`, `series-nav.html`
2. KHÔNG bao giờ dùng `old=`/`new=` trong Tera — luôn dùng `from=`/`to=`

---

## Bug #6 — Fabricated 404 Links: Khi AI Bịa URL (V14)

Đây là bug tốn kém nhất về thời gian fix, vì nó không lộ ra ngay.

**Bối cảnh:** Batch 19 bài "topic authority cluster" được tạo tự động. `zola build` pass. Nhưng `qa-404-checker.py` báo **40 internal broken links**.

**Root cause:** Các bài này cross-link lẫn nhau theo scheme bịa: `/zola/bai-{part}-{slugify(title)}/` — tức là lấy số thứ tự bài trong cluster + slugify tiêu đề. Không có trang nào được build ở path này. Real URL phải là `/posting/{real-slug}/`.

**Lesson tàn khốc:** `zola build` không check dangling markdown links — Zola build thành công nhưng link vẫn 404 ở production. Chỉ có `qa-404-checker.py` mới bắt được. CI green ≠ link-safe.

**Vaccine V14:** Mọi cross-link giữa bài PHẢI dùng URL thật (`/posting/<slug>/`) hoặc alias đã khai báo. Không bao giờ dùng scheme bịa `/bai-N-<title>/`. `qa-404-checker.py` là gate cứng — vào CI, chặn auto-merge nếu có link 404.

---

## Bug Website Vaccine Số: Ba Pattern Tôi Nhận Ra

Nhìn lại 6 bug trên, tôi thấy ba pattern lặp đi lặp lại trong mọi bug website dẫn đến vaccine số:

**1. Assumption sai về hành vi của tool/API** — V1 (HF Hub không auto-prefix theo [tài liệu `snapshot_download`](https://huggingface.co/docs/huggingface_hub/en/package_reference/file_download)), V8 (Tera dùng `from=` không phải `old=`). Fix: luôn đọc docs thay vì assume.

**2. Cascade failure từ shared resource** — V2 (version bump), V5 (rate limit). GitHub Actions có cơ chế [concurrency control](https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/using-concurrency) để queue deploy — đây là fix đúng cho V5. Fix chung: isolate + queue, không burst.

**3. Phantom success** — V6 (stash pop silently conflict), V14 (build pass nhưng link 404). Fix: thêm explicit gate cho mọi assumption quan trọng.

Ba pattern này xuất hiện ở mọi hệ thống phần mềm đủ phức tạp. Vaccine không trị được nguyên nhân sâu xa — nhưng giúp nhận ra nhanh khi pattern xuất hiện lại.

---

## Tiếp Theo Trong Series

- **Bài 3:** [Quy Trình 5 Bước Từ Bug Đến Vaccine](/posting/quy-trinh-vaccine-detect-diagnose-fix-validate-prevent/) — pipeline Detect → Diagnose → Fix → Validate → Prevent
- **Bài 4:** [Bài Học Xây Hệ Thống Tự Chữa Lỗi](/posting/bai-hoc-xay-he-thong-tu-chua-loi-cho-blog/) — những gì không hoạt động như tôi nghĩ
- **Bài 5:** [Hướng Phát Triển Tiếp Theo](/posting/direction-cms-seo-engine-he-vaccine-tu-tien-hoa/) — vaccine tự sinh, SEO engine, CMS

Xem thêm bài [10 Vaccine CLAUDE.md](/posting/10-vaccine-claude-md-giam-loi-production/) và trang [Insights](/insights/) để thấy vaccine đang vận hành thực tế.
