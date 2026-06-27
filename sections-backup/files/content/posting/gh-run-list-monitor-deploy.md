+++
title = "Một câu lệnh nhỏ giúp theo dõi deploy GitHub Pages rõ ràng hơn"
date = 2026-06-27
aliases = ["/gh-run-list-monitor-deploy/"]
slug = "gh-run-list-monitor-deploy"
description = "Làm sao biết deploy lên production lúc nào? Học cách dùng gh run list để giám sát GitHub Pages trực tiếp từ terminal, đỡ vào dashboard rồi đoán mò."

[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["deploy", "devops", "github-actions", "github-pages", "monitoring", "webops", "zola"]
[extra]
seo_keyword = "gh run list github pages deploy monitor"
thumbnail = "https://cdn.jsdelivr.net/gh/banhang-chogao/zola@main/static/img/placeholder/placeholder.svg"
toc = true

[[extra.faq]]
q = "Lệnh gh run list là gì?"
a = "Đó là lệnh từ GitHub CLI (`gh`) dùng để liệt kê danh sách các workflow runs của một repository. Bạn có thể dùng nó để theo dõi tất cả hoặc các runs cụ thể như `deploy.yml` mà không cần mở GitHub web."

[[extra.faq]]
q = "Tại sao status cancelled nhưng không phải lỗi?"
a = "Cancelled xảy ra khi bạn push nhiều lần liên tiếp trong thời gian ngắn. GitHub Actions có cài đặt `cancel-in-progress: true`, nghĩa là run cũ bị huỷ để chạy run mới. Đây là hành vi bình thường khi merge/push lên main."

[[extra.faq]]
q = "Làm sao biết deploy đã lên production hay chưa?"
a = "Kiểm tra run gần nhất: nếu status là `completed` và conclusion là `success`, thì code đã lên GitHub Pages. Nếu `in_progress`, chừa chút. Nếu `failure`, kiểm tra log."

[[extra.faq]]
q = "Deploy success nhưng trình duyệt vẫn thấy cũ, phải làm sao?"
a = "Có thể là cache trình duyệt. Mở DevTools → bật Disable cache (trong tab Network) rồi reload, hoặc dùng hard-refresh (Ctrl+Shift+R trên Windows/Linux, Cmd+Shift+R trên Mac)."

[[extra.faq]]
q = "Có thể dùng gh run list cho các workflow khác không?"
a = "Được chứ. Thay `--workflow=deploy.yml` bằng workflow mà bạn muốn giám sát, ví dụ `--workflow=qa.yml`, `--workflow=build-related.yml`. Hoặc bỏ flag `--workflow` để xem tất cả."

+++

## Vấn đề thường ngày: "Đã lên production chưa?"

Bạn mới merge xong một PR vào `main`. Bạn chờ vài phút rồi tự hỏi: *"Deploy xong chưa nhỉ? Code đã sống trên production à?"* 

Thay vì vào GitHub desktop → chọn repository → kéo xuống Actions → tìm `deploy.yml` → bấm vào run gần nhất → xem status, bạn có thể **chỉ cần chạy một câu lệnh duy nhất ở terminal**:

```bash
gh run list -R Banhang-Chogao/zola --workflow=deploy.yml --limit 10
```

Đó là nó. Một bảng terminal hiện lên với đầy đủ thông tin deploy của 10 run gần nhất. Không cần click, không cần chờ trang web load, không cần cuộn. **Đẹp, gọn, rõ ràng.**

Bài này mình chia sẻ cách dùng lệnh `gh run list` để theo dõi GitHub Pages deploy, vì sau nhiều lần push/merge/cancel liên tiếp, mình nhận ra rằng một bảng terminal rõ ràng **tiết kiệm nhiều thời gian hơn** bất cứ dashboard web nào.

---

## Lệnh gh run list là gì?

`gh run list` là câu lệnh từ **GitHub CLI** (`gh`) — công cụ command-line chính thức của GitHub. Nó liệt kê danh sách các workflow runs trong repository của bạn.

Cú pháp cơ bản:

```bash
gh run list [flags]
```

Ở đây, bạn cần:
- **`-R <OWNER/REPO>`** — chỉ định repository (vd `-R Banhang-Chogao/zola`)
- **`--workflow=<WORKFLOW_FILE>`** — lọc chỉ một workflow cụ thể (vd `deploy.yml`)
- **`--limit <N>`** — hiển thị bao nhiêu run gần nhất (thường 10–20 là đủ)

Nếu bạn chưa cài `gh`, [cài GitHub CLI trước](https://cli.github.com/). Nó chỉ mất 2 phút.

---

## Cách chạy và đọc kết quả

### Chạy lệnh

```bash
gh run list -R Banhang-Chogao/zola --workflow=deploy.yml --limit 10
```

Hoặc nếu bạn đã navigate vào thư mục repo Zola:

```bash
gh run list --workflow=deploy.yml --limit 10
```

### Bảng kết quả trông như thế nào

```
STATUS  TITLE                        WORKFLOW  RUN ID         ACTOR          BRANCH  EVENT             CREATED
✓       Merge pull request #1063     deploy.yml 12345678901   github-actions main    workflow_dispatch 2026-06-27 23:45
●       Merge pull request #1062     deploy.yml 12345678902   github-actions main    push              2026-06-27 23:40
✗       Merge pull request #1061     deploy.yml 12345678903   github-actions main    push              2026-06-27 23:35
```

**Giải thích từng cột:**

- **STATUS** (`✓` / `●` / `✗`) — biểu tượng trạng thái
  - `✓` = completed, success
  - `●` = in_progress (đang chạy)
  - `✗` = completed, failure
  - `⊘` = completed, cancelled (nếu có)

- **TITLE** — tiêu đề PR hoặc commit message
- **WORKFLOW** — tên file workflow (`deploy.yml`)
- **RUN ID** — ID duy nhất của run này (để tra log sau)
- **ACTOR** — ai trigger run (người push, automation, etc.)
- **BRANCH** — branch chạy (thường `main` cho deploy)
- **EVENT** — cách trigger: `push` (code được push) hay `workflow_dispatch` (trigger thủ công)
- **CREATED** — thời gian tạo run (dạng `YYYY-MM-DD HH:MM`)

**Đó là! Một cái nhìn toàn cảnh.** Bạn có thể thấy run nào đang chạy, run nào xong, xong rồi success hay fail.

---

## Hiểu các trạng thái deploy

Khi bạn nhìn cột STATUS, bạn sẽ thấy một trong những trạng thái này:

### ✓ Completed, Success

Deployment thành công. Code đã lên GitHub Pages, viewers sẽ thấy phiên bản mới.

**Kiểm tra production:**
```bash
curl -I https://banhang-chogao.github.io/zola/
```

Nếu status code là `200`, tức là site đang sống.

### ● In Progress

Workflow đang chạy. Chừa vài giây rồi chạy lại lệnh để xem cập nhật.

**Không cần chờ.** Nếu bạn cần xem progress chi tiết:

```bash
gh run view <RUN_ID> --log
```

(Thay `<RUN_ID>` bằng ID từ cột RUN ID.)

### ✗ Completed, Failure

Deployment thất bại. Code **chưa lên** GitHub Pages. Bạn cần debug.

**Xem log lỗi:**

```bash
gh run view <RUN_ID> --log
```

Đọc log để tìm bước nào fail (thường là `zola build` vỡ Tera, hoặc Pages API rate limit). Tra CLAUDE.md mục "Vaccine" để xem pattern lỗi đã biết và cách fix nhanh.

### ⊘ Completed, Cancelled

Run bị **huỷ** — không phải lỗi code. Thường xảy ra khi:
- Bạn push 2–3 lần liên tiếp trong 30 giây
- Run cũ đang chờ hoặc đang chạy, run mới push đến → GitHub Actions huỷ run cũ để chạy run mới
- Đây là hành vi của `cancel-in-progress: true` trong workflow

**Không cần lo.** Run mới nhất chính là cái quan trọng. Nếu run mới nhất là `success`, bạn vẫn OK.

---

## Cancelled ≠ Failed: khi nào thì lo?

Đây là điểm quan trọng mà nhiều người nhầm.

Mình từng merge 3 PR liên tiếp trong 2 phút. Nhìn dashboard, thấy build #387 và #388 đều bị cancelled, tự nhiên hoảng: *"Sao deploy fail hết rồi?"* 

Sự thật: những run bị cancelled **chỉ vì chúng bị supersede bởi run mới hơn.**

Workflow deploy có setting `cancel-in-progress: true` trong `.github/workflows/deploy.yml`:

```yaml
concurrency:
  group: pages
  cancel-in-progress: true
```

Nó có nghĩa: *"Nếu có workflow mới cùng group trigger, huỷ workflow cũ đi."*

**Tại sao?** Để tránh race condition khi push quá nhanh. Nếu push 3 lần mà cả 3 cùng chạy, có thể có 2 run cùng ghi `/public` → conflict. Thay vào đó, GitHub chỉ chạy run mới nhất, huỷ cái cũ.

**Quy tắc vàng:** Nếu có nhiều run bị cancelled liên tiếp, nhưng **run mới nhất là `success`**, bạn vẫn **an toàn**. Site đã lên production. Không cần phải sửa gì.

```bash
# Chạy lệnh và xem run mới nhất (dòng đầu)
gh run list -R Banhang-Chogao/zola --workflow=deploy.yml --limit 10

# Dòng đầu tiên là run mới nhất. Nếu nó status ✓ (success), không lo.
```

---

## Debug deploy bằng log

Nếu status là `✗` (failure), đó là lúc bạn cần xem log.

### Cách 1: Xem log đầy đủ

```bash
gh run view <RUN_ID> --log
```

Thay `<RUN_ID>` bằng số từ cột RUN ID. Ví dụ:

```bash
gh run view 12345678903 --log
```

Log sẽ hiện từng job, từng step, từng dòng output. Tìm dòng có từ "ERROR" hoặc "failed".

### Cách 2: Xem job riêng

Nếu workflow có nhiều job (vd `build`, `deploy`, `report`), bạn có thể xem job cụ thể:

```bash
gh run view <RUN_ID> --json=jobs
```

Hoặc mở web version để click job:

```bash
gh run view <RUN_ID> --web
```

Lệnh cuối cùng sẽ mở GitHub web tại run đó, bạn có thể click và xem UI.

### Cách 3: Tra pattern lỗi đã biết

Nếu error message chứa từ quen (vd "API rate limit exceeded", "HuggingFace 401", "internal links hỏng", "FAQ field sai"), tra CLAUDE.md mục §4 "Vaccine" để xem pattern đã biết.

Ví dụ, nếu bạn thấy lỗi:
```
Error: API rate limit exceeded for installation
```

Đó là **V5 — configure-pages rate limit** (hoặc V5b nếu ở deploy job). Mở CLAUDE.md tra V5, bạn sẽ thấy fix pattern ngay.

---

## Tips giám sát hàng ngày

Dưới đây là vài cách mình dùng để giám sát deploy hiệu quả:

### 1. Alias shortcut

Tạo alias bash để không phải gõ cả dòng:

```bash
# Thêm vào ~/.bashrc hoặc ~/.zshrc
alias zola-deploy='gh run list -R Banhang-Chogao/zola --workflow=deploy.yml --limit 10'
```

Sau đó chỉ cần:

```bash
zola-deploy
```

### 2. Theo dõi realtime

Nếu bạn vừa push và muốn xem workflow chạy realtime:

```bash
gh run list -R Banhang-Chogao/zola --workflow=deploy.yml --limit 1
```

Chỉ xem 1 run (mới nhất). Chạy lại vài lần mỗi 10 giây để xem progress.

### 3. Sau merge PR, kiểm tra ngay

Khi bạn vừa merge PR:
1. Chờ 2–3 giây (GitHub cần thời gian dispatch workflow)
2. Chạy `gh run list --workflow=deploy.yml --limit 5`
3. Xem run mới nhất — nó phải là `●` (in progress). Đợi vài phút.
4. Chạy lại để xem nó chuyển sang `✓` (success) hay `✗` (failure)
5. Nếu `✓`, reload site ở trình duyệt (hard-refresh) để xem thay đổi
6. Nếu `✗`, tra log bằng `gh run view <RUN_ID> --log` và fix

### 4. Không luôn luôn là sự cố

Hãy nhớ: **cancelled ≠ failure.** Nếu bạn push 5 lần trong 1 phút, 4 run sẽ bị cancelled. Đó là bình thường. Chỉ quan tâm tới run mới nhất.

---

## Tại sao lệnh này tốt hơn dashboard web?

Bạn có thể hỏi: *"Tại sao không dùng GitHub Actions tab trên web?"*

Có lý do:

| Yếu tố | Terminal (gh run list) | GitHub Web |
|--------|------------------------|------------|
| **Tốc độ** | Instant | Chờ trang load, chờ API |
| **Hiển thị** | Một bảng gọn | Phải scroll, click, mở tab |
| **Thông tin** | Đủ (status, ID, actor, branch, event, time) | Chi tiết hơn nhưng khó quét nhanh |
| **Offline** | Chạy từ cache nếu trước đó fetch qua | Không |
| **Scripting** | Dễ dàng (lệnh pipe, parse) | Không |

Ví dụ, nếu bạn muốn **xem chỉ run failure**:

```bash
gh run list -R Banhang-Chogao/zola --workflow=deploy.yml --status=failure --limit 10
```

Hoặc **xem run success:**

```bash
gh run list -R Banhang-Chogao/zola --workflow=deploy.yml --status=success --limit 10
```

Bạn không thể làm điều này trên GitHub web mà không cần click vài cái.

---

## Trường hợp thực tế

Một buổi sáng, mình merge 3 PR hàng loạt. Mình chạy:

```bash
gh run list -R Banhang-Chogao/zola --workflow=deploy.yml --limit 10
```

Kết quả:

```
STATUS  TITLE                        WORKFLOW  RUN ID         ACTOR          BRANCH  EVENT             CREATED
✓       Merge pull request #1063     deploy    12345678901   github-actions main    workflow_dispatch 2026-06-27 23:50
⊘       Merge pull request #1062     deploy    12345678902   github-actions main    push              2026-06-27 23:45
⊘       Merge pull request #1061     deploy    12345678903   github-actions main    push              2026-06-27 23:40
✓       Merge pull request #1060     deploy    12345678904   github-actions main    push              2026-06-27 23:30
```

Nhìn thế này, mình biết ngay:
- Run mới nhất (#1063) **success** ✓ → code đã lên production
- Run #1062 và #1061 bị **cancelled** ⊘ → vì run mới hơn push đến
- Run #1060 là **success** ✓ → trước đó cũng OK

**Kết luận:** Site bình thường, sạch, không lỗi. Không cần mở GitHub web, không cần login, chỉ là một dòng lệnh. Tiết kiệm được 30 giây mỗi lần kiểm tra.

---

## Bài học rút ra

Sau nhiều lần debug GitHub Pages deploy trên Zola, mình rút ra vài điểm:

1. **Một lệnh terminal rõ ràng hơn bất kỳ dashboard nào** — không cần click, không cần chờ trang load. Data quá đủ.

2. **Cancelled không phải lỗi** — nó là tính năng. Hiểu rằng GitHub Actions tự huỷ run cũ khi run mới push đến sẽ giúp bạn không lo lắng vô căn cứ.

3. **Log là bạn tốt nhất của bạn** — khi deploy fail, log sẽ nói cho bạn nghe. Không bao giờ nên bỏ qua log.

4. **Kiểm tra production, không chỉ CI** — deploy success ở CI không có nghĩa code đã sống trên site. Hãy kiểm tra thực tế: mở trình duyệt, hard-refresh, xem thay đổi có hiện không.

5. **Tự động hoá tiếp theo** — nếu bạn giám sát deploy nhiều lần mỗi ngày, hãy tạo script hoặc alias. Mỗi giây tiết kiệm được là một ngàn giây tiết kiệm trong năm.

---

## Kết luận

GitHub Pages deploy không cần phải là huyền bí. Một câu lệnh nhỏ `gh run list` có thể giải đáp câu hỏi "đã lên production chưa?" trong vòng 1 giây, thay vì 30 giây click qua giao diện web.

Nếu bạn đang quản lý blog Zola (hoặc bất kỳ static site nào chạy GitHub Pages), hãy thêm lệnh này vào toolbox của bạn. Bạn sẽ thấy nó hữu ích ngay từ lần đầu.

**Chúc bạn deploy thành công!** 🚀
