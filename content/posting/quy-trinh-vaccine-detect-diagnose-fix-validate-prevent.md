+++
title = "Quy Trình Vaccine Website: 5 Bước Từ Bug Đến Prevention"
description = "5 bước tạo vaccine cho CI/CD blog: từ phát hiện pattern CI log đến fix tối thiểu, validate pipeline, và viết quy tắc phòng ngừa vào CLAUDE.md."
date = 2026-06-20
aliases = ["/vaccine-quy-trinh/"]
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["bug fix", "ci/cd", "qa check", "vaccine số", "zola blog"]
[extra]
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
seo_keyword = "quy trình vaccine website"
featured = false
series = "vaccine-so"
series_part = 3
series_total = 5

[[extra.faq]]
q = "Quy trình vaccine website gồm mấy bước?"
a = "5 bước: Detect (nhận diện pattern từ CI log), Diagnose (tìm root cause, không chỉ symptom), Fix (sửa delta tối thiểu), Validate (chạy qa_check.py + zola build), Prevent (viết vaccine vào CLAUDE.md). Bỏ qua bước nào cũng làm vaccine kém hiệu quả."

[[extra.faq]]
q = "Tại sao phải có bước Diagnose riêng, không fix thẳng từ dấu hiệu?"
a = "Vì triệu chứng và nguyên nhân thường khác nhau. V5 (GitHub Pages rate limit) trông như lỗi build nhưng thực ra là lỗi API quota — fix sai (sửa build) không giải quyết được gì. Diagnose đúng root cause mới fix được."

[[extra.faq]]
q = "Validate pipeline gồm những gì?"
a = "Tối thiểu: python3 qa_check.py → python3 scripts/paywall_prepare_build.py --strip → zola build → python3 scripts/check_internal_links.py. Tùy context còn thêm qa-404-checker.py và seo_qa_checker.py. Phải pass toàn bộ mới coi là xanh."

[[extra.faq]]
q = "Fix safe là gì, khác fix risky thế nào?"
a = "Fix safe là fix idempotent, không động vào content người dùng, confidence ≥90% — ví dụ sửa model ID trong script, fix internal link 404 rõ ràng, rebuild references.json. Fix risky là sửa template, thay đổi logic workflow, động vào data curate tay — phải đi qua PR và review thủ công."

[[extra.faq]]
q = "Bao lâu thì viết được một vaccine hoàn chỉnh?"
a = "Sau khi đã fix và validate xong, viết vaccine vào CLAUDE.md thường mất 15–30 phút. Phần tốn thời gian nhất là Diagnose — tìm root cause đúng. Nếu đã biết root cause, cả pipeline từ Detect đến Prevent có thể xong trong 1 giờ."
+++

**Quy trình vaccine website** của tôi gồm 5 bước cố định: Detect → Diagnose → Fix → Validate → Prevent. Mỗi lần CI đỏ mà không khớp vaccine nào trong thư viện, tôi chạy đủ 5 bước này và kết thúc bằng một vaccine mới — để lần sau không phải làm lại từ đầu.

Bài [trước trong series](/posting/tu-dns-404-den-conflict-pr-nhung-bug-khien-toi-tao-vaccine/) kể chi tiết 6 bug cụ thể. Bài này giải thích pipeline tôi dùng để biến bug thành vaccine — có thể áp cho bất kỳ loại lỗi CI nào.

## Bước 1 — Detect: Nhận Diện Pattern Từ CI Log

Không phải mọi lần CI đỏ đều cần vaccine. Bước đầu tiên là **phân biệt incident đơn lẻ với pattern**.

Quy tắc tôi dùng: **xuất hiện 3 lần với cùng dấu hiệu → đủ điều kiện thành vaccine**.

- Lần 1: fix thủ công, ghi chú nhanh
- Lần 2: cảnh báo, bắt đầu thu thập log
- Lần 3: đủ bằng chứng pattern, mở pipeline vaccine

**Cách nhận diện pattern từ CI log:** tìm dòng error cụ thể và lặp lại. Ví dụ:
- `API rate limit exceeded for installation` → V5 pattern
- `Repository Not Found` + HuggingFace URL → V1 pattern
- `Filter 'replace' failed: expected arg called 'from'` → V8 pattern

Mỗi vaccine trong thư viện có "Dấu hiệu" là đoạn log cụ thể để match — không phải mô tả chung chung.

## Bước 2 — Diagnose: Root Cause, Không Phải Symptom

Đây là bước hay bị bỏ qua nhất, và cũng là bước quan trọng nhất.

**Ví dụ sai:** V5 (GitHub Pages rate limit) — lần đầu tôi tưởng lỗi `configure-pages` là do file `deploy.yml` có vấn đề, nên sửa các tham số trong file đó. Fix không hiệu quả vì root cause là quá nhiều deploy song song, không phải config deploy.

**Cách Diagnose đúng:**
1. Đọc full log, không chỉ dòng đỏ — dòng đỏ là symptom, nguyên nhân thường ở trên
2. Hỏi: "Điều gì thay đổi trước khi lỗi xảy ra?" — V5 xuất hiện sau đợt merge nhiều PR
3. Phân biệt "lỗi code" vs "lỗi môi trường" vs "lỗi config" — ba loại có fixer khác nhau
4. Kiểm tra lịch sử: lỗi này có xảy ra trước không? Bao giờ? Điều kiện nào?

**Checklist diagnose nhanh:**

| Câu hỏi | Nếu có → Xem xét |
|---------|-----------------|
| `zola build` vẫn pass? | Lỗi ở CI/deploy, không phải code |
| Xảy ra sau merge dày đặc? | Rate limit, concurrency |
| Chỉ fail một file cụ thể? | Config/path/naming |
| Log báo 401/403? | Auth, API key, permission |
| Nhiều run cancelled liên tiếp? | Concurrency cancel — không phải fail |

## Bước 3 — Fix: Delta Tối Thiểu

Nguyên tắc: **chỉ sửa đúng phần cần sửa, không làm gì thêm**.

Tôi từng có thói quen "tiện tay refactor" khi fix — và tạo thêm bug mới. Bây giờ tôi giữ rule cứng: một fix = một commit = một diff tối thiểu.

**Phân loại fix:**

| Loại | Điều kiện | Cách xử lý |
|------|-----------|-----------|
| **Safe** | Idempotent, không động content | Auto-fix + push qua PR flow |
| **Risky** | Template/logic/data curate | PR + review thủ công |
| **Destructive** | Xóa file, reset history | Hỏi người dùng trước |

Safe fix: sửa model ID trong script, fix link 404 rõ ràng, rebuild references. Đây là những thứ `vaccine_autofixer.py` có thể tự làm.

Risky fix: sửa `templates/base.html`, thay đổi series manifest, sửa workflow CI. Phải đi qua PR — dù CI xanh cũng cần mắt người nhìn qua một lần.

## Bước 4 — Validate: Pipeline Kiểm Tra Toàn Diện

Fix xong, trước khi commit, tôi chạy đủ pipeline:

```bash
python3 qa_check.py                              # bước 1: QA check toàn repo
python3 scripts/paywall_prepare_build.py --strip # bước 2: strip premium content
zola build                                        # bước 3: build site
python3 scripts/paywall_prepare_build.py --restore
python3 scripts/check_internal_links.py          # bước 5: internal link check
python3 qa-404-checker.py                        # bước 6: 404 check
```

Một điểm quan trọng: tôi không bỏ qua bước nào dù "trông có vẻ không liên quan". V14 là bài học đắt giá — `zola build` pass hoàn toàn nhưng `qa-404-checker.py` báo 40 internal broken links. Build pass ≠ production safe.

Thêm một lưu ý từ [Zola documentation](https://www.getzola.org/documentation/content/linking/): Zola không validate dangling markdown links tại build time — đây là lý do phải có gate riêng.

## Bước 5 — Prevent: Viết Vaccine Vào CLAUDE.md

Bước cuối là biến fix thành vaccine để hệ thống học.

**Cấu trúc vaccine trong CLAUDE.md:**

```markdown
#### V18 — Tên Vaccine: mô tả ngắn vấn đề

- **Dấu hiệu:** đoạn log cụ thể, error code, hành vi observable
- **Nguyên nhân:** root cause thật (không phải symptom)
- **FIXER:** lệnh/file/action cụ thể — chạy được ngay
- **Prevention:** rule ngăn tái phát trong code/config
```

Vaccine phải đủ cụ thể để **AI đọc log → match vaccine → chạy fixer mà không cần hỏi lại**. Nếu vaccine quá mơ hồ, nó không match được khi cần.

**Sau khi viết vaccine:** cập nhật số thứ tự, ghi date, test match với log cũ. Sau đó `vaccine_autofixer.py` tự biết có vaccine mới khi chạy lần sau.

## Quy Trình Vaccine Website: Anti-Loop Mechanism

Một rủi ro của hệ thống tự fix: vòng lặp vô tận. Fix A tạo ra lỗi B → fix B tạo ra lỗi A → lặp mãi.

Tôi xây anti-loop bằng hai cơ chế:
1. **Counter per issue-id:** mỗi vaccine fix tăng counter; đến `LOOP_THRESHOLD` (mặc định 3) thì dừng và escalate
2. **Concurrency lock:** `data/vaccine-autofixer-state.json` — chỉ 1 instance chạy tại 1 thời điểm; nếu lock còn active sau 30 phút thì coi là stale và reset

Nếu cùng issue-id đã fix ≥3 lần mà vẫn fail → dừng auto-fix, tạo issue, chờ người review. Đây là ranh giới giữa tự động và an toàn.

## Tóm Tắt Pipeline

```
CI đỏ
  │
  ▼
Match vaccine? ──Yes──► Chạy fixer → push → done
  │
  No
  │
  ▼
Detect pattern (3 lần?)
  │
  ▼
Diagnose root cause
  │
  ▼
Fix delta tối thiểu
  │
  ▼
Validate: qa_check → zola build → link check
  │
  ▼
Prevent: viết vaccine V(N+1) vào CLAUDE.md
  │
  ▼
Done — thư viện vaccine +1
```

---

Bài tiếp theo: [Bài Học Xây Hệ Thống Tự Chữa Lỗi](/posting/bai-hoc-xay-he-thong-tu-chua-loi-cho-blog/) — những điều tôi tưởng sẽ hoạt động tốt nhưng thực ra không, và những gì bất ngờ hoạt động rất tốt.

Xem báo cáo vaccine chạy thực tế tại trang [Insights](/insights/) và bài giới thiệu series tại [Vaccine Số Là Gì?](/posting/vaccine-so-la-gi-bien-bug-thanh-he-mien-dich-website/).
