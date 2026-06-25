+++
title = "Bài Học Xây Hệ Thống Tự Chữa Lỗi Cho Blog"
description = "7 bài học thật sau khi xây 17+ vaccine cho blog Zola: khi nào automation phản tác dụng, tại sao CI green không đủ, và semantic merge quan trọng hơn text merge."
date = 2026-06-20
aliases = ["/vaccine-bai-hoc/"]
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["ai system", "automation", "bài học", "vaccine số", "zola blog"]
[extra]
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
seo_keyword = "hệ thống tự chữa lỗi blog"
featured = false
series = "vaccine-so"
series_part = 4
series_total = 5

[[extra.faq]]
q = "Hệ thống tự chữa lỗi blog có thể xử lý 100% lỗi tự động không?"
a = "Không, và không nên cố gắng. Hệ thống tự fix hiệu quả nhất là 70–80% lỗi lặp lại có pattern rõ. 20–30% còn lại là lỗi mới chưa từng gặp, lỗi cần judgment call, hoặc lỗi ảnh hưởng data người dùng — những cái này cần người review."

[[extra.faq]]
q = "CI green có phải điều kiện đủ để deploy production không?"
a = "Không. CI green (zola build pass) không đảm bảo link nội bộ không 404, không đảm bảo backend đồng bộ với frontend, không đảm bảo content không có vấn đề SEO. Gate cứng của tôi là: zola build + qa_check + qa-404-checker + internal link check — tất cả phải pass."

[[extra.faq]]
q = "Semantic merge khác text merge thế nào?"
a = "Text merge nhìn vào dòng code và giải quyết conflict theo --ours hoặc --theirs. Semantic merge nhìn vào intent: đoạn code này làm gì? Nếu cả hai PR đều thêm một module vào footer, semantic merge giữ cả hai — text merge có thể chọn một trong hai và bỏ mất feature."

[[extra.faq]]
q = "Workflow remediation tự đỏ là vấn đề gì?"
a = "Là khi workflow được tạo ra để theo dõi/sửa lỗi của workflow khác lại tự fail. Điều này tạo ra noise — người nhìn CI không biết đỏ vì lỗi thật hay đỏ vì observer fail. Rule: mọi observer/remediation workflow phải có continue-on-error hoặc nuốt exit code, chỉ để gate thật mới được đỏ."

[[extra.faq]]
q = "Vaccine 'chết' là gì?"
a = "Vaccine không còn trigger được vì lỗi nó phòng đã được fix ở tầng hạ tầng. Ví dụ: V2 (Slack action v1→v3) đã pin version cụ thể, nếu sau này không còn dùng Slack action thì V2 không bao giờ match nữa. Vaccine chết không gây hại, nhưng cần cleanup định kỳ để thư viện gọn."
+++

Sau khi xây **hệ thống tự chữa lỗi blog** với 17+ vaccine và hai tháng vận hành thực tế, tôi học được nhiều thứ hơn tôi nghĩ — phần lớn từ những chỗ hệ thống không hoạt động như kỳ vọng.

Đây là 7 bài học quan trọng nhất. Không phải lý thuyết — là những chỗ tôi đã làm sai và tốn thời gian để nhận ra.

Bạn có thể đọc bài mở đầu series [Vaccine Số Là Gì?](/posting/vaccine-so-la-gi-bien-bug-thanh-he-mien-dich-website/) và bài về [quy trình 5 bước](/posting/quy-trinh-vaccine-detect-diagnose-fix-validate-prevent/) trước để có context. Bài này liên quan trực tiếp đến các nguyên tắc trong [GitHub Actions best practices](https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/using-concurrency) mà tôi học được qua thực tế.

## Bài Học 1: Observer Không Được Tự Đỏ (V7)

Tôi có `build-failure-handler.yml` — workflow chạy khi CI fail, chẩn đoán lỗi, cố fix và báo cáo. Ý tưởng tốt. Thực tế: workflow này tự fail vì `get_run_status` parse `gh run view --json` gặp non-JSON output khi GitHub rate-limit → `status=unknown` → bail ngay → exit code 1.

Kết quả: CI fail → handler chạy → handler cũng fail → hai đỏ thay vì một. Người nhìn dashboard không biết lỗi thật là gì.

**Bài học:** Mọi workflow observer/remediation phải có `continue-on-error: true` hoặc nuốt exit code. Chỉ có CI gate thật (qa-check, zola build) mới được đỏ. Observer đỏ = noise, không phải tín hiệu.

## Bài Học 2: CI Green Không Đủ — Hệ Thống Tự Chữa Lỗi Blog Cần Nhiều Gate Hơn

V14 là bài học đắt nhất. Batch 19 bài được tạo tự động, `zola build` pass hoàn toàn. Deploy lên production. Sau đó `qa-404-checker.py` chạy scheduled báo **40 internal broken links**.

Zola không validate dangling markdown links tại build time — nó chỉ check Zola's own `@/` refs. Link dạng markdown thông thường — ví dụ `[tên bài](đường-dẫn)` — hoàn toàn bypass build check.

**Gate cứng của tôi hiện tại:**
1. `qa_check.py` — conflict markers, secret leak, SCSS, SEO cơ bản
2. `zola build` — template syntax, Tera, section config
3. `qa-404-checker.py` — internal 404, broken links
4. `check_internal_links.py` — cross-reference consistency

Build green chỉ là một trong bốn gate. Mỗi gate bắt một loại vấn đề khác nhau.

## Bài Học 3: Merge Race Không Phải Code Bug

Hai lần PR của tôi bị báo `mergeable_state: dirty` sau khi QA đã xanh. Lần đầu tôi nghĩ code có vấn đề — mất 1 giờ debug mới hiểu ra đây là **merge race**: branch tôi tách ra từ `main` cũ, trong lúc chờ review thì PR khác merge trước, làm base của tôi stale.

**Bài học:** `dirty` PR = merge race, không phải code bug. Fixer: fetch latest main → rebase → regenerate data files → push. Không cần debug code. Việc này xảy ra thường xuyên khi nhiều người (hoặc nhiều bot) push cùng lúc — đây là normal operation, không phải incident.

## Bài Học 4: Semantic Merge Quan Trọng Hơn Text Merge

V12 (semantic conflict trong `templates/base.html` và `sass/_footer.scss`) dạy tôi một điều: **khi nhiều PR cùng sửa shared infrastructure file, text merge thường cho kết quả sai**.

Ví dụ thực: PR #467 thêm `.seo_reality` vào sidebar, PR #468 chuyển `.footer-categories` vào footer, PR #469 thêm `.footer-tags` vào footer, PR #470 thêm S-DNA menu. Tất cả merge vào `base.html` cùng tuần.

Nếu dùng `git checkout --theirs` hoặc `--ours` → mất feature của PR kia. Semantic merge đúng là: giữ cả bốn feature, dedup các import trùng, đảm bảo mỗi selector định nghĩa đúng một lần.

**Rule cứng:** Với `base.html` và `_footer.scss` — không bao giờ merge bằng text. Phân loại từng hunk: additive (giữ cả hai), overlapping (merge theo intent), replacement (chọn phiên bản mới hơn).

## Bài Học 5: Cancelled ≠ Failed (Dashboard Lesson)

Một lần nhìn Build Dashboard thấy 5–6 card đỏ liên tiếp, tôi tưởng production đang có vấn đề nghiêm trọng. Sau 20 phút điều tra: tất cả là `conclusion: cancelled`, không phải `conclusion: failure`.

Trong GitHub Actions, `cancelled` xảy ra khi concurrency group cancel run cũ để chạy run mới — đây là hành vi bình thường và mong muốn. Chỉ `failure` mới là vấn đề thật.

**Bài học:** Dashboard phải phân biệt `status_normalized` riêng: `success | failed | cancelled | skipped | in_progress`. UI dùng màu khác nhau cho từng loại. Kiểm tra run **mới nhất** trước khi báo production degraded.

## Bài Học 6: Vaccine Chết Là Bình Thường

Sau vài tháng, tôi nhận ra một số vaccine không bao giờ trigger nữa. V2 (Slack action v1→v3) — chúng tôi đã pin version, không auto-upgrade nữa. V3 (GitHub Actions không tạo được PR) — bật setting đúng rồi, không còn fail.

Vaccine "chết" không gây hại nhưng tốn bộ nhớ context của AI và làm thư viện dài hơn cần thiết. Tôi lên kế hoạch review định kỳ và archive các vaccine không còn relevant — nhưng không xóa hẳn, vì lịch sử vẫn có giá trị tham chiếu.

**Bài học:** Thư viện vaccine cần maintenance như code. Định kỳ mark "archived" cho vaccine không còn active — giữ thư viện gọn và dễ scan.

## Bài Học 7: Automation Sai Chỗ Gây Ra Nhiều Lỗi Hơn Là Fix

Lần đầu tôi build `vaccine_hotfix.py` — tự động detect CI đỏ, tạo PR fix, push và auto-merge. Kết quả: 3 ngày đầu có 7 PR `vaccine-hotfix/*` được tạo, trong đó 2 PR fix sai (tạo thêm vấn đề mới), 1 PR conflict với PR đang có của người dùng.

**Vấn đề:** Tôi cho phép auto-fix quá nhiều loại lỗi, trong đó có những lỗi cần judgment call.

**Bài học:** Automation chỉ nên xử lý những gì **deterministic và idempotent**. Nếu có thể hỏi "fix này có thể sai không?" mà câu trả lời là "có thể" → không auto-fix. Boundary rõ ràng hơn, ít drama hơn.

Xem [10 Vaccine CLAUDE.md](/10-vaccine-claude-md-giam-loi-production/) để thấy ví dụ cụ thể về ranh giới safe/risky fix, và bài [QA Gatekeeper](/qa-gatekeeper-vaccine-autofixer/) về cách pipeline kiểm tra hoạt động.

---

## Tóm Tắt 7 Bài Học

| # | Bài học | Rule cứng |
|---|---------|-----------|
| 1 | Observer không được tự đỏ | `continue-on-error` cho mọi remediation workflow |
| 2 | CI green không đủ | 4 gate: build + qa + 404 + link check |
| 3 | Dirty PR = merge race | Fetch + rebase + regenerate, không debug code |
| 4 | Semantic merge > text merge | Phân loại từng hunk, không `--ours`/`--theirs` |
| 5 | Cancelled ≠ failed | `status_normalized` riêng, check run mới nhất |
| 6 | Vaccine chết cần cleanup | Review định kỳ, archive không xóa hẳn |
| 7 | Automation sai chỗ sinh lỗi | Auto chỉ cho deterministic + idempotent |

Bài tiếp theo: [CMS, SEO Engine Và Hệ Vaccine Tự Tiến Hoá](/posting/direction-cms-seo-engine-he-vaccine-tu-tien-hoa/) — hướng phát triển của hệ thống vaccine trong năm tới, bao gồm tự sinh vaccine từ CI log và tích hợp với SEO engine.

Theo dõi tiến độ thực tế tại trang [Insights](/insights/).
