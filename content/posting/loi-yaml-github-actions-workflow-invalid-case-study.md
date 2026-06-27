+++
title = "2 lỗi YAML ẩn khiến GitHub Actions workflow invalid"
description = "Case study workflow check-branch-ancestry: block scalar bị phá bởi template literal, plain scalar chứa dấu hai chấm — và gate validate_workflows chặn tái phát."
date = 2026-06-27
slug = "loi-yaml-github-actions-workflow-invalid-case-study"

[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["github-actions", "yaml", "ci-cd", "devops", "qa", "automation", "workflow"]

[extra]
seo_keyword = "lỗi YAML GitHub Actions workflow invalid"
thumbnail = "img/placeholder/placeholder.svg"
toc = true

[[extra.faq]]
q = "Workflow GitHub Actions hiện dấu ✗ trên tab Actions nghĩa là gì?"
a = "Dấu ✗ thường có nghĩa GitHub không parse được file workflow YAML — workflow chưa từng chạy job nào. Khác với job đỏ sau khi chạy: lỗi parse xảy ra trước cả bước checkout. Cần mở file .github/workflows/*.yml và sửa cú pháp YAML."

[[extra.faq]]
q = "Vì sao template literal JavaScript trong script: | làm vỡ YAML?"
a = "Block scalar script: | kết thúc khi gặp dòng không thụt lề so với block. Nếu chuỗi template literal xuống dòng và có markdown (**, ```) bắt đầu ở cột 1, parser YAML coi đó là key mới → lỗi could not find expected ':'. Cách an toàn: dùng array.join('\\n') hoặc giữ mọi dòng nội dung thụt lề đều trong block."

[[extra.faq]]
q = "Lỗi mapping values are not allowed here trong workflow là gì?"
a = "YAML đang parse giá trị plain scalar (một dòng) nhưng gặp dấu hai chấm : ở giữa chuỗi, tưởng đó là cặp key: value. Hay gặp với run: echo \"text: ${{ ... }}\". Sửa bằng block scalar run: | hoặc quote/escape đúng, hoặc truyền biến qua env thay vì nội suy trực tiếp trong scalar."

[[extra.faq]]
q = "Tại sao qa_check.py không bắt được workflow YAML hỏng?"
a = "qa_check.py tập trung frontmatter, template Tera, SCSS, content — không parse toàn bộ .github/workflows/*.yml. Workflow invalid vẫn có thể merge nếu không có gate YAML riêng. Cần script validate_workflows.py (hoặc action chuyên dụng) wired vào qa.yml trước zola build."

[[extra.faq]]
q = "Nên truyền ${{ github.head_ref }} vào github-script như thế nào?"
a = "Không nội suy expression trực tiếp vào chuỗi shell/script khi có thể tránh injection. Pattern an toàn: khai báo env: HEAD_REF: ${{ github.head_ref }} rồi đọc process.env.HEAD_REF trong JavaScript. Context đúng cho PR: github.event.pull_request.head.sha, không phải github.pull_request."

[[extra.faq]]
q = "Làm sao kiểm tra workflow YAML trước khi push?"
a = "Chạy python3 scripts/validate_workflows.py (exit 2 nếu lỗi), hoặc dùng actionlint/yamllint local. Sau sửa, mở PR thử — tab Checks phải hiện tên workflow (vd Check branch ancestry) chứ không còn icon ✗ cạnh tên file."
+++

Một workflow GitHub Actions có thể **chết im** — không chạy job, không log hữu ích, chỉ hiện dấu ✗ cạnh tên file trên tab Actions. Mình vừa gặp đúng kiểu đó với `.github/workflows/check-branch-ancestry.yml`: file đã merge vào `main`, nhưng GitHub coi YAML **invalid** nên gate kiểm tra stale branch không bao giờ kích hoạt.

Đáng nói, đây không phải lỗi logic Git hay merge-base. Chỉ là **hai lỗi cú pháp YAML** xếp chồng — một cái ở giữa khối `github-script`, một cái ở dòng cuối file. QA content vẫn xanh vì `qa_check.py` không đọc workflow. Bài này ghi lại case study đó: triệu chứng, nguyên nhân gốc, cách sửa, và lớp phòng ngừa để lỗi tương tự không lọt auto-merge nữa.

## Bối cảnh: workflow ancestry và vì sao file này quan trọng

Trước đó blog đã gặp [git stale branch mất common ancestor với main](/posting/git-stale-branch-root-cause-analysis-va-giai-phap/). Nhánh tạo từ commit cũ, `main` bị force-push, `git merge-base` fail — CI đỏ sau vài phút build vô ích. Giải pháp là workflow **Check branch ancestry**: chạy sớm trên mỗi pull request, gọi `git merge-base HEAD origin/main`, fail nhanh và comment hướng dẫn rebase.

Workflow nghe đơn giản. Nhưng vì nó nằm trong `.github/workflows/`, **một dấu hai chấm sai chỗ** cũng đủ vô hiệu hóa toàn bộ lớp phòng ngừa. Đó là điểm mình muốn nhấn: automation chỉ mạnh khi file khai báo automation còn parse được.

## Triệu chứng workflow invalid trên GitHub UI

Khi YAML hỏng, tab Actions không hiện run kiểu bình thường. Thay vào đó:

| Dấu hiệu | Ý nghĩa |
|----------|---------|
| `.github/workflows/check-branch-ancestry.yml` + **✗** | File workflow invalid, GitHub Actions bỏ qua |
| Không có job "Verify branch has common ancestor with main" | Parser dừng trước khi định nghĩa job |
| PR vẫn merge được nhánh khác | Gate ancestry **không chạy** — lỗ hổng im lặng |
| `qa-check` xanh | QA hiện tại không validate workflow YAML |

Mình nhận ra chậm vì mắt vẫn nhìn log build Zola và [QA Gatekeeper](/posting/qa-gatekeeper-tu-fix-loi-blog/) — trong khi workflow đã chết từ bước parse. Cảm giác giống cài báo cháy nhưng quên nối pin: hệ thống tưởng đã bảo vệ, thực tế không.

## Các bước debug lỗi YAML GitHub Actions workflow invalid

Khi nghi workflow không chạy, mình không mở ngay file JS dài. Thứ tự gọn:

1. **Tab Actions → danh sách workflow** — tìm tên `Check branch ancestry`. Nếu chỉ thấy đường dẫn file kèm ✗, YAML chưa hợp lệ.
2. **Click vào file lỗi** — GitHub thường chỉ dòng gần chỗ parse fail (`could not find expected ':'` hoặc `mapping values are not allowed`).
3. **Đối chiếu indent** — với mỗi `script: |` hoặc `run: |`, kéo mắt xuống từng dòng: có dòng nào về cột 0 không?
4. **Sửa từng bug, validate lại** — sau bug 1 có thể mới thấy bug 2 ở cuối file; đừng dừng sớm.
5. **Push PR thử** — pass khi Checks hiện **tên workflow**, job chạy, không còn invalid marker.

Công cụ hỗ trợ: `python3 scripts/validate_workflows.py` (khi đã có trên nhánh), hoặc [actionlint](https://github.com/rhysd/actionlint) local. Tài liệu [workflow syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions) có mục về expressions — đối chiếu khi nghi `${{ }}` sai context.

## Nguyên nhân gốc: hai bug YAML độc lập

Sau khi mở file và đối chiếu thông báo lỗi GitHub, mình tách được **hai bug** — sửa một cái vẫn còn cái kia.

### Bug 1 — Block scalar `script: |` bị template literal phá (khoảng dòng 57)

Step comment PR dùng `actions/github-script@v7` với `script: |` — block scalar nhiều dòng trong YAML. Bên trong, message PR được dựng bằng **template literal** JavaScript (backtick) chứa markdown: tiêu đề in đậm, khối code bash, dòng giải thích.

Vấn đề: trong template literal nhiều dòng, các dòng markdown (`**How to fix**`, `` ```bash ``) nằm **ở cột 1** (không thụt lề so với block `script: |`). Parser YAML hiểu block scalar **kết thúc sớm** tại dòng không indent — phần còn lại trông như key mới nhưng thiếu `:` hợp lệ.

Thông báo điển hình:

```text
could not find expected ':'
```

Đây là lỗi kinh điển khi trộn **YAML block scalar** với **chuỗi nhiều dòng không kiểm soát indent**. Người quen viết JS trong workflow hay mắc: backtick cho phép xuống dòng "tự nhiên", nhưng YAML không biết đó là nội dung chuỗi — YAML chỉ nhìn cột đầu dòng.

**Pattern nguy hiểm (minh họa — không chạy được):**

```yaml
script: |
  const msg = `Tiêu đề

**Bold ở cột 1**   # ← YAML nghĩ block scalar đã hết
`;
```

### Bug 2 — Plain scalar `run: echo` chứa dấu `:` (dòng cuối file)

Step pass cuối file ban đầu kiểu:

```yaml
run: echo "✓ Branch has healthy ancestry: ${{ steps.check.outputs.merge_base }}"
```

Chuỗi sau `run:` là **plain scalar một dòng**. Trong YAML, dấu `:` giữa chữ `ancestry` và phần expression bị parser coi là **bắt đầu mapping** → `mapping values are not allowed here`.

Bug này **ẩn** vì chỉ lộ sau khi sửa bug 1 — hoặc khi validator quét tới cuối file. Mình từng focus vào khối `github-script` dài, bỏ qua dòng echo ngắn phía dưới.

## Bảng fix đã merge

| Vấn đề | Cách sửa |
|--------|----------|
| Template literal phá block scalar | Dựng message bằng `array.join('\n')` — mọi dòng JS thụt lề đều; markdown nằm trong phần tử string, không lọt cột 1 YAML |
| Nội suy `${{ }}` trực tiếp trong script | Truyền qua `env:` → `process.env.*` (giảm rủi ro injection, parser shell rõ ràng hơn) |
| Plain scalar chứa `:` | Bọc lệnh trong block scalar `run: \|` hoặc tách message |
| Context GitHub sai | `github.pull_request` → `github.event.pull_request` (đúng payload PR event) |

**Hướng sửa message an toàn (rút gọn):**

```javascript
const msg = [
  '❌ **Branch has no common ancestor with `main`**',
  '',
  'This branch is "stale" — ...',
  '',
  '**How to fix (rebase):**',
  '```bash',
  'git fetch origin main',
  'git rebase origin/main',
  'git push --force-with-lease -u origin ' + process.env.HEAD_REF,
  '```',
].join('\n');
```

Kèm `env:`:

```yaml
env:
  HEAD_REF: ${{ github.head_ref }}
  PR_HEAD_SHA: ${{ github.event.pull_request.head.sha }}
```

Step echo cuối chuyển sang block:

```yaml
run: |
  echo "✓ Branch has healthy ancestry: ${{ steps.check.outputs.merge_base }}"
```

## Vì sao lỗi lọt qua QA trước đây

Pipeline blog chạy [GitHub Actions CI/CD](/posting/github-actions-ci-cd-cho-nguoi-moi/) + `qa_check.py` + `zola build` + internal link gate. Tất cả giả định **workflow files hợp lệ**.

`qa_check.py` giỏi bắt frontmatter TOML, Tera, SCSS, conflict marker — nhưng **không parse YAML workflow**. PR #1078 (workflow fix) và PR #1077 (content placement) có thể cùng lúc xanh QA trong khi `check-branch-ancestry.yml` vẫn invalid trên GitHub.

Bài học khớp case [giải quyết merge conflict tự động](/posting/giai-quyet-merge-conflict-tu-dong-ci-cd/): **CI xanh trên một tập check không đồng nghĩa mọi lớp bảo vệ đang hoạt động**. Phải có check riêng cho từng loại artifact.

## Chống tái phát: `validate_workflows.py` + qa.yml

Sau fix, mình thêm gate thật:

1. **`scripts/validate_workflows.py`** — quét mọi `.github/workflows/*.yml`: parse YAML, lint pattern đã biết (block scalar + `script: |`, plain scalar `run:` có `:`, v.v.). Bắt được cả bản cũ hỏng; **exit 2** khi fail.
2. **Wired vào `qa.yml`** — chạy trước bước tốn thời gian. Workflow YAML invalid → **chặn auto-merge** (trước đây lọt vì thiếu bước này).
3. **Vaccine V23** trong `CLAUDE.md` — ghi dấu hiệu + FIXER để lần sau khớp pattern là sửa ngay, không chẩn đoán lại.

Lệnh local nhanh:

```bash
python3 scripts/validate_workflows.py   # exit 0 = pass, 2 = có workflow hỏng
```

## Bằng chứng sau fix

Sau commit fix merge:

- Tab Checks hiện workflow **"Check branch ancestry"** (tên `name:` trong file), không còn icon ✗ cạnh đường dẫn file.
- Job **"Verify branch has common ancestor with main"** chạy trên PR — fetch `origin/main`, `git merge-base`, comment khi stale.
- Gate ancestry lại nằm đúng vị trí trong chuỗi phòng ngừa stale branch (bổ sung cho tài liệu [ROOT-CAUSE stale branch](/posting/git-stale-branch-root-cause-analysis-va-giai-phap/)).

Deploy production theo [tự động deploy Zola](/posting/tu-dong-deploy-zola-github-actions/) qua `deploy.yml` — cần xác nhận run deploy gần nhất success và commit đã lên GitHub Pages. Nguyên tắc **merged ≠ live**: workflow fix chỉ coi là hoàn tất khi Actions parse file **và** site production nhận build mới.

Trong phiên này, hai PR liên quan là **#1077** (content placement — macro placement, `data/content-placements.json`, admin hook) và **#1078** (workflow fix + validator). Content placement là feature riêng; còn workflow fix quyết định gate ancestry có thực sự chạy hay không. Mình tách PR theo rule “mỗi thay đổi logic một PR” để auto-merge không kéo theo thay đổi không liên quan.

Sau merge, mình kiểm tra deploy run `deploy.yml` (không nhầm với cancelled do concurrency — xem Insights dashboard nếu cần). Nếu deploy fail, xử lý theo Vaccine library (V5 Pages API rate limit, v.v.) — ngoài phạm vi bài này nhưng nằm trong cùng văn hóa “bug found → fix → learn → gate”.

## Checklist cho lần sau

Khi sửa workflow có `github-script` hoặc heredoc dài:

- [ ] Mọi dòng trong `script: |` thụt lề **sâu hơn** block scalar — không để markdown ở cột 1
- [ ] Ưu tiên `array.join('\n')` thay template literal nhiều dòng trong YAML
- [ ] `${{ }}` quan trọng → `env:` + `process.env`
- [ ] `run: echo "..."` có dấu `:` → đổi sang `run: |`
- [ ] Context PR: `github.event.pull_request`, không rút gọn sai
- [ ] Chạy `validate_workflows.py` trước push
- [ ] Mở PR thử: tên workflow xuất hiện trên Checks, không còn ✗ invalid

## Kết luận

Hai lỗi YAML nhỏ đủ làm mất cả lớp gate ancestry — trong khi phần còn lại của CI vẫn xanh. Block scalar bị template literal phá và plain scalar chứa `:` là hai mẫu lỗi dễ tái diễn nếu chỉ dựa mắt review.

Fix không cần redesign workflow: đổi cách dựng chuỗi, bọc scalar, sửa context, thêm validator. Quan trọng hơn là **gate thật trong qa.yml** — vì workflow invalid im lặng nguy hiểm hơn job đỏ có log.

**Bước tiếp theo:** đọc thêm [chuyên mục Công nghệ](/categories/cong-nghe/) hoặc [tất cả bài viết](/categories/tat-ca/) nếu bạn đang vận hành blog/static site với GitHub Actions. Khi gặp workflow ✗ invalid, chạy validator trước — đừng đợi build Zola báo lỗi không liên quan.

## Tham khảo

- [GitHub Actions — Workflow syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [YAML specification — Block scalars](https://yaml.org/spec/1.2.2/#8132-block-scalars)
- [actions/github-script](https://github.com/actions/github-script)