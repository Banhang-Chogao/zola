+++
title = "Kiểm tra tình trạng PR sau merge: merged ≠ live"
date = 2026-06-28
aliases = ["/kiem-tra-trang-thai-pr-sau-khi-merge/"]
slug = "kiem-tra-trang-thai-pr-sau-khi-merge"
description = "PR merge xong chưa chắc code đã lên production. Học kiểm tra thực tế bằng CLI: gh run list deploy.yml, gh run view --log, curl production. Biết chính xác deploy thành công chưa."
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["ci-cd", "deploy", "devops", "github", "github-actions", "github-pages", "merge"]
[extra]
seo_keyword = "kiểm tra PR sau merge"
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
toc = true

[[extra.faq]]
q = "Merge PR xong có chắc chắn code lên production không?"
a = "Không. Merge chỉ đưa code vào nhánh main. Sau đó còn GitHub Actions build, GitHub Pages deploy, CDN cache. Mỗi bước đều có thể fail. Bạn cần kiểm tra thực tế bằng gh run list và curl chứ không chỉ nhìn vào nút Merge xanh."

[[extra.faq]]
q = "Lệnh nào quan trọng nhất để kiểm tra deploy sau merge?"
a = "gh run list --workflow deploy.yml --branch main --limit 5 2>&1. Nó cho bạn thấy 5 deploy run gần nhất trên nhánh main, kèm trạng thái (success/failure/in_progress/cancelled). Đọc từ trên xuống: dòng đầu là run mới nhất, nếu là success là code đã lên."

[[extra.faq]]
q = "Build PASS nhưng site không thay đổi, nguyên nhân do đâu?"
a = "Ba khả năng: (1) workflow còn đang chạy ở step deploy, (2) CDN cache chưa refresh (hard-reload trình duyệt), (3) deploy thực sự fail nhưng build job PASS — bạn cần xem cả build và deploy job trong workflow."

[[extra.faq]]
q = "Làm sao để xem workflow deploy đang chạy đến bước nào?"
a = "Dùng gh run view RUN_ID --log để xem log realtime. Nếu không nhớ RUN_ID, chạy gh run list --workflow deploy.yml --limit 1 lấy run mới nhất, copy ID từ cột thứ ba."

[[extra.faq]]
q = "Curl kiểm tra production khác gì so với xem GitHub Actions status?"
a = "GitHub Actions báo deploy success có nghĩa workflow chạy xong không lỗi. Curl kiểm tra URL thật cho bạn biết server trả về HTTP gì: 200 là OK, 404 là route chưa có, 5xx là lỗi server. Luôn dùng cả hai."

[[extra.faq]]
q = "Nếu thấy cancelled status sau merge thì có sao không?"
a = "Cancelled thường không đáng lo. Nó xảy ra khi bạn push/merge liên tiếp — run cũ bị huỷ để chạy run mới hơn. Chỉ cần run mới nhất là success là OK. Nếu run mới nhất cũng cancelled thì mới đáng xem xét."

[[extra.faq]]
q = "Có cách nào kiểm tra nhanh một route mới đã live chưa?"
a = "Dùng curl -I https://domain.com/duong-dan-moi/ và xem HTTP status. 200 là live. 404 là chưa có (có thể do route sai, slug sai, hoặc deploy chưa xong). Kết hợp với việc kiểm tra file public/duong-dan-moi/index.html trong local build."

[[extra.faq]]
q = "Tôi dùng AI Coding (Claude, Codex) để tạo PR, làm sao biết nó đã deploy thành công?"
a = "Sau khi AI tạo PR và auto-merge, chạy gh run list --workflow deploy.yml --branch main --limit 5. Nếu dòng đầu là success, kiểm tra production bằng curl. Nếu fail, đọc log bằng gh run view. Đừng tin PR merge là xong."
+++

## Chuyện buổi sáng: PR xanh, Merge xanh, nhưng website vẫn cũ

Tôi merge một PR vào lúc 9:05 sáng. GitHub báo **"Merged successfully"**. Nút xanh lè. Tôi mở website — vẫn là nội dung cũ. Hard-refresh. Vẫn cũ. Đợi 5 phút. Vẫn cũ.

Bắt đầu hoảng.

Tôi là người dùng AI Coding — Claude viết code, tạo PR, tự merge. Tôi chỉ ngồi nhìn. Vậy mà cái PR đầu tiên trong ngày, dù đã qua auto-merge thành công, vẫn chưa lên website.

Hoá ra: workflow deploy bị **rate limit GitHub API** (V5 trong vaccine library của blog này). Build job PASS nhưng deploy job FAIL vì GitHub Pages API trả 403. Code nằm ở nhánh main, nhưng **chưa bao giờ lên GitHub Pages**.

Tôi mất 15 phút để nhận ra: không có lỗi code, không có conflict, không có draft — chỉ là GitHub Actions hết quota API tạm thời. Và nếu tôi biết kiểm tra từ đầu bằng `gh run list`, tôi đã tiết kiệm được 15 phút đó.

Câu chuyện này không hiếm. Với các bạn dùng AI để code (Claude Code, OpenCode, Codex, Copilot), PR được tạo và merge tự động liên tục — mỗi lần là một cơ hội để lỗi deploy lọt qua. Không phải lỗi code, mà là lỗi quy trình.

Từ lần đó tôi rút ra một nguyên tắc:

> **Merged ≠ Live.** Nhìn thấy chữ "Merged" màu xanh trên GitHub là chưa đủ. Bạn PHẢI kiểm tra thực tế.

Bài này tôi viết lại toàn bộ quy trình kiểm tra sau merge mà tôi dùng mỗi ngày — dành cho lập trình viên GitHub, DevOps, và đặc biệt là những ai dùng AI Coding (Claude, Codex, OpenCode) để tự động tạo và merge PR.

---

## Quy trình từ Merge đến Production

Trước khi đi vào lệnh cụ thể, bạn cần hiểu luồng này:

```text
Merge PR vào main
    ↓
GitHub Actions dispatch deploy workflow
    ↓
Build job: zola build (hoặc build tool khác)
    ↓
Deploy job: configure-pages → deploy-pages (GitHub Pages Action)
    ↓
GitHub Pages serve static files
    ↓
CDN cache (Cloudflare hoặc GitHub CDN)
    ↓
Trình duyệt người dùng
```

Mỗi mũi tên là một cơ hội để **fail**. PR merge chỉ vượt qua bước 1. Còn 5 bước nữa mới tới tay người dùng. Nếu bạn dừng lại ở merge — bạn đang đánh cược.

Trong thực tế, mỗi bước có thể thất bại vì những lý do rất khác nhau:

- **Merge** — nhìn chung an toàn (Git tự gộp hoặc báo conflict ngay)
- **Build** — lỗi template, thiếu dependency, syntax sai. Zola build thường fail vì Tera syntax (xem bài [GitHub Actions CI/CD cho người mới](/posting/github-actions-ci-cd-cho-nguoi-moi/))
- **Deploy job** — lỗi quota API, permission, Pages conflict. Đây là bước hay fail nhất mà không ai ngờ tới
- **CDN** — cache cũ làm người dùng thấy nội dung không đổi dù deploy thành công

Bài viết [Pull Request và quy trình cộng tác trên GitHub](/posting/pull-request-quy-trinh-cong-tac-github/) giải thích phần merge. Bài này tập trung vào **những gì xảy ra sau khi merge**.

---

## Các lệnh tôi dùng hằng ngày

Đây là danh sách các lệnh tôi chạy *gần như mỗi lần merge PR*. Tôi xếp theo tần suất sử dụng, từ cao xuống thấp.

### 1. `gh run list --workflow deploy.yml --branch main --limit 5 2>&1`

**Đây là lệnh tôi dùng nhiều nhất.** Không phải ngày — mà mỗi lần merge PR là chạy.

```bash
gh run list --workflow deploy.yml --branch main --limit 5 2>&1
```

Tại sao lệnh này hữu ích:

- **`--workflow deploy.yml`** — lọc chỉ workflow deploy (bỏ qua các workflow phụ như QA, audit, build-related)
- **`--branch main`** — chỉ xem run trên nhánh main (deploy production), bỏ qua run từ nhánh feature
- **`--limit 5`** — 5 run gần nhất là đủ để thấy pattern: mới nhất success? hay fail liên tiếp?
- **`2>&1`** — gộp stderr vào stdout để tránh lỗi pipe

Kết quả trông như thế này:

```
STATUS  TITLE                         WORKFLOW   RUN ID           ACTOR          BRANCH  EVENT             CREATED
✓       Merge pull request #1090      deploy.yml 12345678901     github-actions main    workflow_dispatch 2026-06-28 09:05
⊘       Merge pull request #1089      deploy.yml 12345678902     github-actions main    push              2026-06-28 08:55
✓       Merge pull request #1088      deploy.yml 12345678903     github-actions main    push              2026-06-28 08:30
✗       Merge pull request #1087      deploy.yml 12345678904     github-actions main    workflow_dispatch 2026-06-28 08:00
✓       Merge pull request #1086      deploy.yml 12345678905     github-actions main    push              2026-06-28 07:00
```

**Cách đọc nhanh:**

- **STATUS** — `✓` success, `●` in_progress, `✗` failure, `⊘` cancelled
- **Dòng đầu tiên** = run mới nhất. Đây là cái bạn quan tâm nhất
- Nếu dòng đầu là `✓` → code đã lên production
- Nếu là `●` → chờ thêm (bài viết [Một câu lệnh nhỏ giúp theo dõi deploy GitHub Pages](/posting/gh-run-list-monitor-deploy/) giải thích chi tiết về cancelled status)

### 2. `curl -I https://seomoney.org/`

Kiểm tra production thực tế. `-I` = chỉ lấy HEAD request (nhanh, không tải cả trang):

```bash
curl -I https://seomoney.org/
```

Kết quả:

```
HTTP/2 200
server: GitHub.com
content-type: text/html; charset=utf-8
last-modified: Sun, 28 Jun 2026 09:06:00 GMT
```

HTTP `200` là site sống. Kiểm tra `last-modified` — nếu khớp với thời gian deploy gần nhất, code đã lên.

### 3. `curl -I https://seomoney.org/<slug>/`

Kiểm tra route mới cụ thể. Ví dụ sau khi merge PR thêm trang `/tools/something/`:

```bash
curl -I https://seomoney.org/tools/something/
```

HTTP `200` = route đã live. `404` = chưa (xem bài [Zola deploy và GitHub Pages](/posting/tu-dong-deploy-zola-github-actions/) để hiểu cấu trúc route).

### 4. `gh run watch`

Xem workflow đang chạy realtime. Sau khi chạy `gh run list`, copy RUN_ID rồi:

```bash
gh run watch 12345678901
```

Nó sẽ show log realtime từng job, từng step. Ctrl+C để thoát.

### 5. `gh run view --log`

Xem log đầy đủ của run (kể cả khi đã kết thúc):

```bash
gh run view 12345678901 --log
```

Hữu ích khi run FAIL và bạn cần tìm dòng lỗi. Tìm `##[error]` hoặc `failed` trong output.

### 6. `gh pr view`

Xem chi tiết PR vừa merge:

```bash
gh pr view 1090
```

Cho bạn biết commits, files changed, reviewers — xác nhận đúng PR đã merge.

### 7. `gh pr checks`

Xem trạng thái CI checks của PR trước khi merge:

```bash
gh pr checks 1090
```

Dùng để kiểm tra QA check còn đang chạy hay đã pass hết. Nếu checks chưa xong mà PR đã merge — có thể có vấn đề.

### 8. `gh pr checks --watch`

Giống `gh pr checks` nhưng realtime:

```bash
gh pr checks 1090 --watch
```

### 9. `gh run list --branch main`

Xem tất cả workflow runs (không chỉ deploy) trên nhánh main:

```bash
gh run list --branch main --limit 10
```

Hữu ích khi bạn muốn biết có workflow nào đang chạy ngoài deploy không (QA, audit, build-related, v.v.). Một số workflow chạy song song cùng lúc, đặc biệt khi bạn dùng AI Coding để tự động hoá nhiều thao tác cùng lúc.

Khi xem kết quả, chú ý cột EVENT để biết workflow được trigger như thế nào:

- **push** — code được push lên branch. Đây là event phổ biến nhất cho deploy
- **workflow_dispatch** — trigger thủ công (bằng tay hoặc qua API như `gh workflow run`)
- **pull_request** — workflow chạy khi có PR mở hoặc cập nhật (thường là QA check)
- **schedule** — workflow chạy theo cron, ví dụ audit chạy mỗi 6 tiếng
- **workflow_run** — workflow được trigger bởi workflow khác hoàn thành

---

## Kinh nghiệm debug: build PASS nhưng site chưa live

Đây là kịch bản khó chịu nhất. Bạn thấy:

```
gh run list --workflow deploy.yml --branch main --limit 5
```

Kết quả:

```
STATUS  TITLE    WORKFLOW   RUN ID       BRANCH  EVENT  CREATED
✓       ...      deploy.yml 12345678901  main    push   2026-06-28 09:05
```

Status là `✓` (success). Nhưng mở trình duyệt — vẫn cũ.

**Nguyên nhân thường gặp:**

| Nguyên nhân | Cách kiểm tra | Cách xử lý |
|---|---|---|
| **CDN cache** | Hard-reload: Cmd+Shift+R (Mac) / Ctrl+Shift+R (Windows) | Xong. Đợi thêm vài phút nếu có CDN như Cloudflare. |
| **Deploy chưa kịp propagate** | Chờ 2-3 phút rồi thử lại | Bình thường với GitHub Pages. |
| **Build job PASS nhưng deploy job FAIL** | `gh run view RUN_ID --log` — xem job deploy có lỗi không | Tra V5 trong vaccine library. |
| **Route chưa tồn tại** | `ls public/<duong-dan>/index.html` (build local) | Kiểm tra slug, path, draft status. |
| **Base URL sai** | Kiểm tra `config.toml` có đúng `base_url` không | Sai base_url làm link nội bộ hỏng. |

**Quy tắc số một:** Luôn kiểm tra production bằng `curl -I` sau khi deploy. CI success không đồng nghĩa với production live.

---

## Workflow còn chạy: đừng vội

Sau merge, workflow deploy không dispatch ngay lập tức. Có độ trễ 2-10 giây. Nếu bạn chạy `gh run list` ngay sau khi merge và thấy **không có run mới** — đừng lo. Chờ 10 giây rồi chạy lại.

Khi workflow đang chạy, bạn thấy:

```
STATUS  TITLE    WORKFLOW   RUN ID       BRANCH  EVENT  CREATED
●       ...      deploy.yml 12345678901  main    push   2026-06-28 09:05
```

Dấu `●` (in_progress). Dùng `gh run watch RUN_ID` để theo dõi realtime.

---

## Deploy FAIL: workflow fail checklist

Khi workflow deploy FAIL (`✗`), đừng hoảng. Làm tuần tự:

1. **Xác định job nào fail**: `gh run view RUN_ID --log | grep "failed"`
2. **Phân loại lỗi**:
   - Build job fail → lỗi code (Tera syntax, SCSS lỗi, internal link hỏng)
   - Deploy job fail → lỗi hạ tầng (rate limit, permission, Pages API)
3. **Tra vaccine library**: Blog này có thư viện lỗi đã biết (V1-V25 trong `CLAUDE.md`). Ví dụ:
   - **V5**: GitHub Pages API rate limit → exponential backoff retry
   - **V19**: FAQ field sai → `question=`/`answer=` thay vì `q=`/`a=`
   - **V23**: YAML workflow invalid → sai cú pháp github-script
4. **Fix trên cùng branch → re-push → CI tự chạy lại**

Bài viết [QA Gatekeeper tự fix lỗi blog](/posting/qa-gatekeeper-tu-fix-loi-blog/) giải thích cách hệ thống tự phát hiện và sửa lỗi.

---

## CDN chưa refresh

GitHub Pages có CDN cache mặc định khoảng 5-10 phút (Cache-Control: max-age=600). Nếu bạn hard-reload mà vẫn thấy nội dung cũ, có thể CDN chưa kịp refresh.

Cách xử lý:

- **Hard-reload trình duyệt**: Cmd+Shift+R (Mac), Ctrl+Shift+R (Windows/Linux)
- **Mở tab ẩn danh**: Nếu thấy nội dung mới, là cache trình duyệt, không phải CDN
- **Dùng curl kiểm tra last-modified**: `curl -I https://domain.com/` — nếu status 200 và `last-modified` sát với thời gian deploy, CDN đã serve phiên bản mới
- **Dùng curl kiểm tra header cụ thể**: `curl -sI https://domain.com/ | grep -i "last-modified\|x-cache\|age"` — xem cache header trực tiếp, biết được CDN đang serve bản cũ hay mới

Nếu site của bạn dùng Cloudflare trước GitHub Pages, bạn cũng có thể purge cache Cloudflare qua Cloudflare Dashboard.

## PR merge nhưng deploy chạy từ commit sai

Một lỗi hiếm nhưng rất khó chịu: PR đã merge, workflow deploy chạy success, nhưng nội dung trên production vẫn là bản cũ.

Nguyên nhân: workflow deploy được trigger bởi push vào main, nhưng lúc đó commit của PR chưa kịp update (race condition giữa merge và trigger). Kết quả: workflow chạy trên commit cũ, deploy ra bản cũ.

Cách kiểm tra:

```bash
# Xem run mới nhất
gh run list --workflow deploy.yml --branch main --limit 1

# Lấy commit SHA của run đó
gh run view RUN_ID --json headSha --jq .headSha

# So sánh với commit mới nhất trên main
git log origin/main -1 --format=%H
```

Nếu hai SHA khác nhau, bạn đã gặp race condition. Cách xử lý: re-run workflow deploy thủ công bằng `gh workflow run deploy.yml --ref main`.

---

## Checklist sau mỗi lần merge PR — dán ở terminal

Tôi dùng checklist này mỗi lần merge PR. Bạn copy và dùng luôn:

```bash
# Sau khi merge PR:

# Bước 1: Kiểm tra deploy workflow
gh run list --workflow deploy.yml --branch main --limit 5 2>&1

# Bước 2: Nếu success, kiểm tra production
curl -I https://domain.com/

# Bước 3: Nếu success, kiểm tra route mới (nếu có)
curl -I https://domain.com/duong-dan-moi/

# Bước 4: Nếu in_progress, watch realtime
gh run watch RUN_ID

# Bước 5: Nếu failure, đọc log
gh run view RUN_ID --log

# Bước 6: Xác nhận trên trình duyệt (hard-reload)
```

---

## Best practices

### Tạo alias cho lệnh hay dùng

Thêm vào `~/.zshrc` hoặc `~/.bashrc`:

```bash
alias deploy-status='gh run list --workflow deploy.yml --branch main --limit 5 2>&1'
alias gh-log='gh run view $(gh run list --workflow deploy.yml --limit 1 --json databaseId --jq ".[0].databaseId") --log'
```

Sau đó chỉ cần gõ `deploy-status` — nhanh hơn vào GitHub web.

### Dùng workflow_dispatch thay vì push để deploy

Nếu workflow cho phép, trigger thủ công:

```bash
gh workflow run deploy.yml --ref main
```

Rõ ràng hơn là merge rồi đợi.

### Kiểm tra 2 bước: CI + production

Không bao giờ chỉ dựa vào CI xanh. Luôn kiểm tra production thực tế sau deploy.

---

## Các lỗi thường gặp

| Lỗi | Dấu hiệu | Cách fix |
|---|---|---|
| **Deploy workflow không chạy** | Merge xong không thấy run mới sau 30s | Kiểm tra workflow có trigger trên push main không. Xem workflow có bị disable không. |
| **Build fail vì Tera syntax** | Log báo lỗi template Zola | Tra V8, V19 (FAQ field sai, Tera ternary). Fix template, push lại. |
| **Deploy fail vì rate limit** | Log "API rate limit exceeded for installation" | V5 — tự động retry. Nếu vẫn fail, chờ 1 tiếng rồi re-run. |
| **Site live nhưng route 404** | `curl` route mới trả 404 | Kiểm tra slug, path trong frontmatter. Có thể thiếu `path` khi section có `render = false`. |
| **Incident trong workflow YAML** | GitHub báo "Invalid workflow file" | V23 — validate YAML syntax, sửa github-script block scalar. |
| **Data JSON conflict** | PR merge xong mà file `data/*.json` conflict | V18 — auto-resolve theo chiến lược: data lấy main, content giữ PR. |
| **PR merge nhưng deploy không gồm commit** | Deploy success nhưng nội dung không đổi | Kiểm tra commit SHA của deploy run. Có thể deploy chạy từ commit cũ trước khi merge. |

---

## Kết luận

Một PR được merge không có nghĩa là code đã lên production. Quy trình từ merge đến deploy là một chuỗi nhiều bước — mỗi bước đều có thể fail. Nếu bạn dùng AI Coding (Claude, Codex, OpenCode) để tự động tạo và merge PR, việc kiểm tra sau merge càng quan trọng hơn: AI có thể tạo PR và merge, nhưng nó không thể tự biết deploy có thành công không — trừ khi bạn dạy nó kiểm tra.

Hãy nhớ:

1. **Merged ≠ Live.** Luôn kiểm tra thực tế.
2. **`gh run list --workflow deploy.yml --branch main --limit 5`** là lệnh đầu tiên sau mỗi merge.
3. **`curl -I`** là lời khẳng định cuối cùng — nếu HTTP 200, code đã lên.
4. **Cancelled = bình thường.** Chỉ lo khi run mới nhất không phải success.
5. **Tra vaccine library** khi gặp lỗi lạ — khả năng cao đã có pattern fix sẵn.

Bài viết liên quan: [Git merge và xử lý conflict](/posting/git-merge-va-xu-ly-conflict/), [GitHub Actions CI/CD cho người mới](/posting/github-actions-ci-cd-cho-nguoi-moi/), [Deploy blog Zola lên GitHub Pages](/posting/tu-dong-deploy-zola-github-actions/), [Theo dõi deploy bằng gh run list](/posting/gh-run-list-monitor-deploy/).

**Chúc bạn deploy thành công!**
