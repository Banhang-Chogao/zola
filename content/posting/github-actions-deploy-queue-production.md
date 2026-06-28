+++
title = "GitHub Actions Deploy Queue: cách đọc và trigger đúng cách"
description = "GitHub Actions deploy queue là gì? Hướng dẫn đọc pending/in_progress/completed, kiểm tra commit đang deploy, dispatch đúng cách và theo dõi production realtime."
date = 2026-06-28
aliases = ["/github-actions-deploy-queue-production/"]

[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["ci-cd", "deploy", "devops", "github-actions", "github-pages", "kinh-nghiem", "workflow"]
[extra]
seo_keyword = "GitHub Actions deploy queue"
thumbnail = "img/placeholder/placeholder.svg"
toc = true

[[extra.faq]]
q = "Vì sao deploy workflow mới ở trạng thái pending?"
a = "Vì GitHub Actions queue chỉ chạy một workflow run trên mỗi concurrency group tại một thời điểm. Nếu đã có run đang in_progress, run mới xếp hàng chờ. Đây là cơ chế bình thường, không phải lỗi."

[[extra.faq]]
q = "Làm sao phân biệt pending khác queued?"
a = "Pending là đã dispatch nhưng chưa được runner nhận — đang trong queue nội bộ của GitHub. Queued (nếu thấy) là workflow đã có runner nhưng chờ tài nguyên. Thực tế GitHub Actions hay dùng pending và in_progress; queued ít xuất hiện."

[[extra.faq]]
q = "Dispatch deploy workflow có nghĩa production cập nhật ngay không?"
a = "Không. Dispatch chỉ thêm run vào queue. Nếu đang có run khác chạy, run mới pending. Production chỉ cập nhật khi nó completed success. Merge cũng vậy — merged ≠ live."

[[extra.faq]]
q = "Làm sao biết commit nào đang được deploy?"
a = "Dùng gh run list --workflow deploy.yml --branch main --limit 3. Cột headSha cho biết commit đang chạy. So với git log origin/main để biết commit cuối cùng có được deploy chưa."

[[extra.faq]]
q = "Rate limit GitHub API ảnh hưởng tới deploy thế nào?"
a = "GitHub App installation có rate limit theo giờ. Khi vượt, mọi call API (kể cả gh workflow run deploy) đều trả 403. Điều này làm Deploy Guard thất bại và cần dispatch thủ công hoặc chờ reset."

[[extra.faq]]
q = "Cần kiểm tra gì sau mỗi lần merge PR?"
a = "Ba bước: (1) gh run list kiểm tra deploy run mới nhất có success không; (2) so headSha của run với git log origin/main -1; (3) curl -I https://domain.com/trang-moi/ xác nhận HTTP 200. Chỉ kết luận live khi cả ba pass."

[[extra.faq]]
q = "Deploy guard là gì và nó hoạt động ra sao?"
a = "Deploy Guard là workflow chạy theo lịch (thường mỗi giờ) hoặc kích hoạt khi deploy.yml kết thúc. Nó so sánh commit đang live trên GitHub Pages với latest main HEAD. Nếu lệch, nó dispatch deploy.yml để catch up."

[[extra.faq]]
q = "cancel-in-progress: true hay false tốt hơn cho deploy?"
a = "False (queue) tốt hơn cho production. cancel-in-progress: true huỷ run cũ — batch merge có thể khiến run bị huỷ giữa chừng và latest main không bao giờ được deploy. Queue đảm bảo mọi commit cuối cùng đều lên sóng."
+++

## Deploy không lên? Chuyện thường ngày ở GitHub Actions

Bạn merge một Pull Request, thấy nút Merge xanh, workflow deploy.yml chạy thành công — nhưng lên production vẫn là nội dung cũ. Hoặc bạn dispatch deploy workflow bằng `gh workflow run deploy.yml`, nó báo thành công, nhưng `curl` URL vẫn trả nội dung không đổi.

Tôi vừa trải qua cảnh đó với PR #1177: merge lúc 08:46, nhưng deploy queue dồn ứ, Deploy Guard rate-limit, phải dispatch thủ công tới run thứ 3 mới lên được.

Bài này ghi lại **kinh nghiệm thực tế** khi vận hành GitHub Actions CI/CD cho blog Zola trên GitHub Pages — cách đọc queue, trigger deploy đúng cách, và biết chính xác khi nào production cập nhật.

## GitHub Actions Deploy Queue hoạt động thế nào?

GitHub Actions dùng cơ chế **concurrency group** để kiểm soát số workflow chạy đồng thời. Với deploy production, hầu hết dự án đặt:

```yaml
concurrency:
  group: pages
  cancel-in-progress: false
```

`cancel-in-progress: false` có nghĩa: nếu một deploy run đang chạy, run mới **không bị huỷ** — nó xếp hàng chờ. Đây là thiết lập đúng cho production, vì nó đảm bảo **mọi commit cuối cùng đều lên sóng**, dù batch merge gây bão deploy.

### Dòng chảy thực tế

```
Push/merge → trigger deploy.yml
  → concurrency group kiểm tra: có run khác đang chạy?
    → KHÔNG → chạy ngay (in_progress)
    → CÓ → xếp queue (pending)
      → run hiện tại kết thúc → run tiếp theo nhận được runner → in_progress
```

Trong phiên deploy gần nhất, queue của tôi như thế này:

| Run # | Status | Commit | Title |
|-------|--------|--------|-------|
| #1405 | success | `1caef59` | Build and deploy (latest deploy thành công) |
| #1407 | in_progress | `1c3b304` | Deploy queue fix |
| #1409 | pending | `dea1498` | PR #1185 |
| #1410 | pending | `0c22c76` | **Latest main (gồm PR #1177)** |

Run #1410 dispatch lúc 09:44 nhưng phải chờ #1407 và #1409 xong mới tới lượt.

## Bảng trạng thái workflow cần biết

| Status | Ý nghĩa | Hành động cần làm |
|--------|---------|-------------------|
| **queued** | Workflow đã dispatch, chờ runner | Không cần gì — đợi hoặc kiểm tra runner availability |
| **pending** | Workflow đã có runner nhưng chờ concurrency group | Kiểm tra run nào đang in_progress |
| **in_progress** | Workflow đang chạy | `gh run view RUN_ID --log` để theo dõi từng step |
| **completed** | Workflow đã kết thúc | Kiểm tra `conclusion`: success, failure, cancelled |
| **success** | Hoàn thành không lỗi | Xác nhận production bằng curl |
| **failure** | Có step exit code ≠0 | Đọc log, tra vaccine library, fix trên branch |
| **cancelled** | Bị huỷ (concurrency hoặc thủ công) | cancelled bởi concurrency group là bình thường; xác nhận run mới hơn success |

## Dispatch deploy không có nghĩa production cập nhật ngay

Đây là nhầm lẫn phổ biến nhất. `gh workflow run deploy.yml --ref main` báo `HTTP 201` (Created) — nhưng nó chỉ **tạo một workflow run mới**, không hề chạy ngay.

Ví dụ thực tế:

```bash
gh workflow run deploy.yml --ref main
# → https://github.com/.../actions/runs/28318272025  (tạo thành công)
```

Run #1410 được tạo, nhưng trạng thái là **pending**. Nếu queue trống, nó chuyển ngay sang in_progress. Nếu đã có run trước, nó chờ.

Giải pháp: không dispatch nếu chưa kiểm tra queue trống.

```bash
# Kiểm tra queue trước khi dispatch
gh run list --workflow deploy.yml --limit 3
# Nếu thấy pending/in_progress → dispatch sẽ xếp sau
# dispatch hay không tuỳ bạn — nhưng biết trước để không ngạc nhiên
```

## Cách kiểm tra commit nào đang được deploy

### Lệnh quan trọng nhất: `gh run list`

```bash
gh run list --workflow deploy.yml --branch main --limit 5 --json number,status,conclusion,headSha,displayTitle
```

Kết quả dạng:

```json
[
  {"number":1410,"status":"pending","conclusion":"","headSha":"0c22c76ba12365d63f87ae38cc19419b1346163e","displayTitle":"Build and deploy..."},
  {"number":1409,"status":"pending","conclusion":"","headSha":"dea149801bbf51b45941f24be304bcd9a656f50a","displayTitle":"fix(baochi/nha-tranh):..."},
  {"number":1407,"status":"in_progress","conclusion":"","headSha":"1c3b3047ee9250d204c14c8c5ea17eee00dcdb75","displayTitle":"Build and deploy..."}
]
```

So `headSha` với `git log origin/main -1`:

```bash
git log origin/main --oneline -1
# 0c22c76b latest main commit

git merge-base --is-ancestor 0c22c76b <deployed_sha> && echo "Deployed" || echo "Not deployed"
```

Nếu commit của PR bạn không nằm trong deployed SHA → nó chưa lên production. Đơn giản vậy.

### Theo dõi run realtime

```bash
gh run watch 1410
```

Lệnh này refresh trạng thái mỗi vài giây và hiển thị log realtime. Ấn `Ctrl+C` để thoát — workflow vẫn chạy nền.

## Ý nghĩa của `last-modified`

Khi bạn `curl -I https://domain.com/`, HTTP header `last-modified` cho biết **file HTML cuối cùng được GitHub Pages serve** được sinh lúc nào.

```bash
curl -sI https://seomoney.org/ | grep -i last-modified
# last-modified: Sun, 28 Jun 2026 09:33:18 GMT
```

Con số này tương ứng với thời điểm `actions/deploy-pages` hoàn tất. Nếu PR của bạn merge lúc 08:46 mà `last-modified` là 09:33 — có thể nó đã được deploy (nếu deploy run chạy lúc 09:33). Còn nếu `last-modified` cũ hơn commit của bạn → chưa live.

**Giới hạn:** `last-modified` chỉ chính xác tới phút. GitHub Pages không expose commit SHA qua HTTP header, nên bạn phải kết hợp với `gh run list` để xác nhận.

## Cách đọc log Deploy Guard

Deploy Guard là workflow tự động kiểm tra: **commit đang live có khớp với latest main HEAD không?** Nếu không, nó dispatch deploy.

Log thực tế từ Deploy Guard run #47:

```
✓ GitHub Pages status: deployed
  Deployed SHA: 1caef59
✓ Latest deploy run: #1405 (SHA: 1caef59)
⏳ Deploy already active: #1407 (in_progress), #1409 (queued) — skipping dispatch
```

Các trạng thái guard:

| Guard Status | Ý nghĩa |
|-------------|---------|
| **live** | Main HEAD đã deploy — không cần làm gì |
| **stale_deploy** | Deployed SHA cũ hơn main — guard dispatch deploy |
| **no_deploy** | Không tìm thấy Pages deployment — guard dispatch deploy |
| **deploy_pending** | Đã có deploy đang chạy — guard không dispatch (tránh queue dài) |
| **unknown** | Thiếu token hoặc API lỗi |

Khi guard gặp **rate limit** (403 API rate limit exceeded), dispatch thất bại:

```
HTTP 403: API rate limit exceeded for installation
##[error]Process completed with exit code 1.
```

Đây là lúc cần dispatch thủ công, hoặc chờ rate limit reset (thường 1 giờ với GitHub App installation).

## Kinh nghiệm thực chiến

### 1. Queue hơn huỷ

Từng dùng `cancel-in-progress: true` vì nghĩ "chỉ cần run mới nhất". Sai. Batch merge tạo bão deploy — run cũ bị huỷ, run mới bị huỷ tiếp, không run nào lên được production. Chuyển sang `false` (queue) giải quyết triệt để. Xem thêm bài [kiểm tra trạng thái PR sau khi merge](/posting/kiem-tra-trang-thai-pr-sau-khi-merge/) nơi tôi phân tích chi tiết case này.

### 2. Deploy guard cần retry

Rate limit ập tới bất kỳ lúc nào, nhất là khi có nhiều bot push (compliance audit, merge report, security scan). Deploy guard dùng `gh workflow run deploy.yml` một lần duy nhất — nếu 403, nó im lặng thất bại. Giải pháp: thêm exponential backoff retry (3 lần, 10s → 20s → 40s) tương tự cách V5 vaccine xử lý `configure-pages` rate limit.

### 3. Dispatch thủ công: kiểm tra queue trước

Thói quen: dispatch xong mới kiểm tra. Đúng ra phải:

```bash
gh run list --workflow deploy.yml --limit 3
# Nếu không có pending/in_progress → dispatch
gh workflow run deploy.yml --ref main
# Nếu có → cân nhắc dispatch hay chờ
# (nếu dispatch, nó sẽ xếp cuối queue)
```

### 4. Merge xong chưa phải live

PR merged ≠ code lên production. Tôi có checklist 3 bước sau mỗi merge:

1. `gh run list --workflow deploy.yml --branch main --limit 3` — run mới nhất **success**?
2. `curl -I https://domain.com/trang-moi/` — **HTTP 200**?
3. Deployed commit có chứa PR của tôi không? (`git merge-base --is-ancestor`)

Chỉ khi cả ba pass mới thông báo "done". Nguyên tắc này được ghi rõ trong V21 vaccine của blog — **merged is not live**.

### 5. Queue dài = dấu hiệu cần kiểm tra

Nếu deploy queue luôn có 3+ run pending, đó là tín hiệu:
- Có workflow khác push main liên tục (bot maintenance)
- Thiếu `concurrency` group hoặc `cancel-in-progress` sai
- Deploy guard dispatch không kiểm tra queue trước

Giải pháp: Deploy Guard thông minh có logic `has_active_deploy → wait` thay vì dispatch chồng queue.

### 6. Rate limit là có thật

GitHub App installation có rate limit riêng, không phải user token. Các action phổ biến dễ chạm ngưỡng:

| Action | Rate limit window |
|--------|------------------|
| `gh workflow run` | 5000 req/hour (installation) |
| Pages API (`configure-pages`, `deploy-pages`) | 5000 req/hour |
| `gh api /repos/*/pages` | 5000 req/hour |

Rate limit ảnh hưởng cả deploy guard lẫn deploy job — cần retry ở cả hai.

## Best practices để giảm deploy queue và tránh rate limit

### Thiết lập concurrency đúng

```yaml
concurrency:
  group: pages
  cancel-in-progress: false
```

Không `cancel-in-progress: true` cho production deploy.

### Deploy Guard kiểm tra queue trước khi dispatch

```python
# Pseudo-code: kiểm tra queue trước dispatch
active_runs = api_get(f"/repos/{REPO}/actions/workflows/deploy.yml/runs?status=in_progress&per_page=1")
queued_runs = api_get(f"/repos/{REPO}/actions/workflows/deploy.yml/runs?status=queued&per_page=1")
if active_runs or queued_runs:
    print(f"⏳ Deploy already active — skipping dispatch")
    # Deploy guard status = deploy_pending
else:
    gh workflow run deploy.yml --ref main
```

### Hạn chế bot push chồng lên main

Bot maintenance (compliance audit, merge report, build dashboard) không cần trigger deploy riêng. Gom vào một lần push định kỳ, hoặc dùng `push_via_pr.sh` (tạo PR thay vì push thẳng).

### Dispatch thủ công có chủ đích

```bash
# Kiểm tra queue
gh run list --workflow deploy.yml --limit 3

# Nếu sạch, dispatch
gh workflow run deploy.yml --ref main

# Theo dõi
gh run watch $(gh run list --workflow deploy.yml --limit 1 --json databaseId -q '.[0].databaseId')
```

## Checklist sau mỗi lần merge production

```text
□ gh run list --workflow deploy.yml --branch main --limit 3
  → Run mới nhất conclusion = success?
□ gh run view RUN_ID --json headSha
  → headSha có là ancestor của origin/main?
    git merge-base --is-ancestor <headSha> origin/main
□ curl -I https://domain.com/
  → HTTP 200?
□ Nếu thêm route mới:
  → curl -I https://domain.com/duong-dan-moi/
  → HTTP 200, không 404
□ Deploy guard run gần nhất
  → status = live (không stale_deploy)
□ last-modified header
  → sau thời điểm merge
```

Nếu bất kỳ bước nào đỏ → chưa live. Chờ queue, hoặc kiểm tra deploy log.

## Tổng kết

GitHub Actions deploy queue là cơ chế bình thường — không phải lỗi. `pending` không có nghĩa workflow hỏng, `dispatch` không đồng nghĩa deploy ngay, và `merged` chắc chắn không phải `live`.

Ba lệnh bạn cần nhớ:

```bash
gh run list --workflow deploy.yml --branch main --limit 3
curl -I https://domain.com/
git merge-base --is-ancestor <commit> origin/main
```

Và một nguyên tắc: **kiểm tra queue trước dispatch, kiểm tra production sau deploy, kiểm tra commit trước khi báo live.**

Tham khảo thêm cách vận hành CI/CD cho Zola trong bài [tự động deploy Zola với GitHub Actions](/posting/tu-dong-deploy-zola-github-actions/) và kinh nghiệm xử lý [merge conflict tự động trong CI/CD](/posting/giai-quyet-merge-conflict-tu-dong-ci-cd/).

---

### Tham khảo & Nguồn dữ liệu

- [GitHub Actions — Workflow syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [GitHub Actions — Concurrency](https://docs.github.com/en/actions/using-jobs/using-concurrency)
- [GitHub Pages — Deployment history](https://docs.github.com/en/pages)
- [GitHub CLI — gh run](https://cli.github.com/manual/gh_run_list)
- Deploy log thực tế từ blog seomoney.org (run #1405–#1410, Deploy Guard #45–#47)

### Liên kết nội bộ liên quan

- [Kiểm tra trạng thái PR sau khi merge](/posting/kiem-tra-trang-thai-pr-sau-khi-merge/)
- [Tự động deploy Zola với GitHub Actions](/posting/tu-dong-deploy-zola-github-actions/)
- [Giải quyết merge conflict tự động trong CI/CD](/posting/giai-quyet-merge-conflict-tu-dong-ci-cd/)
- [GitHub Actions CI/CD cho người mới](/posting/github-actions-ci-cd-cho-nguoi-moi/)
- [Xử lý lỗi pipeline GitHub Actions](/posting/github-actions-ci-cd-build-failure-vipzone-token/)
- [Invalid workflow file YAML case study](/posting/loi-yaml-github-actions-workflow-invalid-case-study/)

### Bản quyền & Ghi nguồn

Bài viết dựa trên kinh nghiệm vận hành thực tế blog seomoney.org. Minh hoạ terminal và log đã được sanitize để bảo vệ token và thông tin nhạy cảm. Toàn bộ nội dung thuộc sở hữu của tác giả.
+++
