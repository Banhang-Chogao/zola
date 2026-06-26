+++
title = "Khắc Phục 7 PR CI/CD Thất Bại Trên Blog Zola"
description = "Cách tôi chẩn đoán và sửa 7 Pull Request đỏ CI/CD trên blog Zola: build treo, lỗi cú pháp Tera, merge conflict và thứ tự merge an toàn. Có bản tiếng Anh."
date = 2026-06-26
aliases = ["/sua-7-pr-ci-cd-that-bai-zola/"]
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["ci cd", "github actions", "zola", "tera", "merge conflict", "devops", "pull request"]
[extra]
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
seo_keyword = "khắc phục 7 PR CI/CD thất bại"
featured = false
toc = true
+++

> 🇻🇳 **Tiếng Việt** ở phần đầu — 🇬🇧 **English version** scroll xuống cuối bài (*scroll down for the English version*).

Có những ngày bảng Pull Request đỏ rực. Không phải một PR, mà **bảy** PR cùng đỏ CI/CD một lúc. Bài này ghi lại cách **khắc phục 7 PR CI/CD thất bại** trên blog [Zola](https://www.getzola.org/documentation/getting-started/overview/): bình tĩnh phân loại từng lỗi, sửa đúng gốc rễ, rồi merge theo một thứ tự an toàn để không tạo thêm conflict. Nếu bạn vận hành một site tĩnh lớn trên GitHub Actions, hy vọng quy trình này giúp bạn tiết kiệm vài giờ hoảng loạn.

> 📌 Đọc thêm: [Cải thiện hệ thống QA & CI/CD cho blog Zola](/cai-thien-qa-ci-cd-zola/) · [10 vaccine trong CLAUDE.md giảm lỗi production](/10-vaccine-claude-md-giam-loi-production/)

## Bối cảnh: Khắc phục 7 PR CI/CD thất bại cùng lúc

Nguyên tắc đầu tiên khi thấy nhiều PR đỏ: **đừng sửa tràn lan**. Mỗi PR đỏ vì một lý do khác nhau. Việc của tôi là đọc log, gán mỗi PR vào một nhóm nguyên nhân, rồi xử lý từng nhóm theo mức ưu tiên. Bảy PR rơi vào bốn nhóm:

| Nhóm lỗi | PR liên quan | Bản chất |
|----------|-------------|----------|
| Build treo / runner kẹt | #934 | Hạ tầng CI, không phải lỗi code |
| Lỗi cú pháp template (Tera) | #935 | Vỡ `zola build` thật sự |
| Merge conflict với `main` | #936, #938 | Base nhánh đã cũ |
| CI không kích hoạt / đã xong | #939, #942, #943 | Trigger hoặc trạng thái |

Phân loại xong, mọi thứ bớt đáng sợ. Giờ đi vào từng ca.

## #934 — Build treo: hủy và chạy lại

Triệu chứng của #934 là job `build-smoke` chạy mãi không kết thúc. Log dừng cập nhật, runner không nhả, và sau cùng GitHub đánh dấu timeout. Đây **không phải lỗi code** — đây là một runner bị kẹt, một hiện tượng hạ tầng.

Với lớp lỗi này, chẩn đoán lại code là vô ích. Cách xử lý đúng:

1. Vào tab **Actions** trên GitHub UI.
2. Mở run đang treo, bấm **Cancel workflow** để hủy job kẹt.
3. Bấm **Re-run jobs** để chạy lại từ đầu trên một runner mới.

Sau khi chạy lại, `build-smoke` xanh ngay. Bài học: phân biệt **lỗi hạ tầng** với **lỗi logic**. Một runner treo không cần một commit sửa code — nó cần được hủy và chạy lại.

## #935 — Lỗi cú pháp Tera: gốc rễ làm vỡ build

Đây là PR nguy hiểm nhất vì nó làm **vỡ `zola build` thật sự**. Log báo lỗi render template, trỏ vào hai file: `faq.html` và `related-posts.html`.

Có hai vấn đề cú pháp Tera (ngôn ngữ template của Zola):

**Thứ nhất — toán tử `contains` dùng sai ngữ cảnh.** Tera không hỗ trợ `contains` như một toán tử trung tố tùy tiện trên mọi kiểu dữ liệu. Khi template cố dùng `contains` để kiểm tra chuỗi/mảng theo kiểu không được hỗ trợ, bộ render ném lỗi. Cách sửa là gỡ bỏ toán tử `contains` và thay bằng logic hợp lệ (ví dụ dùng filter hoặc kiểm tra điều kiện theo đúng API của Tera).

**Thứ hai — nối chuỗi bằng `concat` thay vì toán tử `~`.** Trong Tera, cách nối chuỗi chuẩn là toán tử dấu ngã `~`, không phải hàm kiểu `concat`. Ví dụ minh họa:

```jinja2
{# ❌ Sai — gây lỗi render #}
{% set url = concat(base, slug) %}

{# ✅ Đúng — dùng toán tử ~ để nối chuỗi #}
{% set url = base ~ slug %}
```

Sau khi gỡ `contains` và đổi `concat` thành `~` trong cả `faq.html` lẫn `related-posts.html`, build xanh. Đây chính là loại lỗi mà một "vaccine" cú pháp Tera tĩnh nên bắt được trước cả khi chạy build — dò template tìm pattern sai và chặn ngay ở cổng QA.

## #936 và #938 — Merge conflict: rebase về main mới nhất

Hai PR này đỏ vì base nhánh đã **cũ hơn `main`**. Trong thời gian PR mở, `main` đã nhận thêm commit, và những thay đổi đó đụng vào cùng vùng file.

- **#936**: conflict nằm ở `base.html` — file hạ tầng dùng chung, rất dễ va chạm khi nhiều PR cùng sửa layout. Cách xử lý: rebase nhánh về `main` hiện tại, mở `base.html`, đọc kỹ **cả hai phía**, giữ ý định của PR đồng thời bảo toàn các bản vá an toàn đã có trên `main`. Với file template/UI dùng chung, tuyệt đối không chọn bừa một bên.
- **#938**: sau khi rebase về `main`, nhóm kiểm tra tĩnh (`static-checks`) xanh trở lại — vì bản cập nhật cổng vaccine mới nhất đã nằm trên `main`. Nhánh cũ chạy với detector cũ nên báo sai; rebase đồng bộ detector là đủ.

Quy tắc rút ra: rất nhiều PR "đỏ" không phải vì code sai, mà vì **nhánh tụt hậu so với `main`**. Rebase trước, phán xét sau.

## #939 — CI không kích hoạt: commit rỗng để re-trigger

#939 ở trạng thái khó chịu: không có check nào chạy, PR treo lơ lửng chờ CI mà CI không bao giờ tới. Nguyên nhân thường gặp là pipeline dùng trigger qua `push`/`workflow_run` và sự kiện kích hoạt bị lỡ.

Cách re-trigger sạch sẽ nhất mà không đụng nội dung là đẩy một **commit rỗng**:

```bash
git commit --allow-empty -m "trigger CI"
git push
```

Commit rỗng không thay đổi một dòng code nào nhưng tạo ra sự kiện `push` mới, đánh thức pipeline. CI chạy, các check xanh, PR sẵn sàng.

## #942 và #943 — Đã xong và sẵn sàng

- **#942**: đã được merge từ trước. Tôi ghi lại như một mốc tham chiếu, không thao tác thêm. Việc nhận ra "PR này đã xong" cũng quan trọng như sửa lỗi — tránh thao tác thừa lên thứ đã đóng.
- **#943**: tất cả check đã xanh, không conflict. PR này merge thẳng được.

## Thứ tự merge an toàn

Sửa được lỗi mới là một nửa. Nửa còn lại là **merge đúng thứ tự** để không tạo ra vòng conflict mới. Khi nhiều PR cùng đụng các file dùng chung, mỗi lần merge làm `main` dịch chuyển — và các PR còn lại lập tức tụt base.

Thứ tự tôi áp dụng:

1. **#943 trước** — đã xanh hoàn toàn, merge để chốt một baseline sạch.
2. **#936 tiếp theo** — PR đụng `base.html`; merge sớm để các nhánh khác rebase lên layout mới nhất.
3. **Rebase #934, #935, #938, #939** lên `main` vừa cập nhật, rồi **merge tuần tự** từng cái một, mỗi lần chờ CI xanh trước khi sang PR kế.

Lệnh merge tôi dùng cho từng PR (squash để giữ lịch sử `main` sạch, xóa nhánh sau khi merge):

```bash
gh pr merge <PR> -s --delete-branch
```

Cờ `-s` (squash) gộp toàn bộ commit của PR thành một commit duy nhất trên `main`; `--delete-branch` dọn nhánh đã merge. Merge **tuần tự** — một pipeline tại một thời điểm — tránh việc nhiều deploy chạy song song gây nghẽn API.

## Checklist rút gọn cho lần sau

- [ ] **Phân loại trước, sửa sau.** Gán mỗi PR đỏ vào một nhóm nguyên nhân.
- [ ] **Lỗi hạ tầng ≠ lỗi code.** Build treo → hủy và chạy lại, đừng commit.
- [ ] **Tera: nối chuỗi bằng `~`, không phải `concat`.** Tránh `contains` ngoài ngữ cảnh hỗ trợ.
- [ ] **Nhánh tụt hậu → rebase về `main`** trước khi nghi ngờ code.
- [ ] **CI không chạy → commit rỗng** `git commit --allow-empty`.
- [ ] **Merge theo thứ tự**: baseline sạch trước, file dùng chung sớm, phần còn lại rebase rồi merge tuần tự.
- [ ] **Squash + xóa nhánh**: `gh pr merge <PR> -s --delete-branch`.

## Bài học lớn nhất

Bảy PR đỏ trông như khủng hoảng, nhưng phần lớn không phải "code sai". Chúng là tổ hợp của một runner kẹt, hai dòng cú pháp template, vài nhánh tụt base và một sự kiện CI bị lỡ. Khi tách bạch từng lớp — hạ tầng, cú pháp, đồng bộ base, trigger — mỗi lỗi trở nên nhỏ và có cách sửa đã biết. Bình tĩnh phân loại quan trọng hơn gõ phím thật nhanh.

---

## 🇬🇧 English Version — Fixing 7 Failed CI/CD Pull Requests on a Zola Blog

Some days the Pull Request board lights up red. Not one PR — **seven** of them, all failing CI/CD at once. This is a hands-on log of how I calmly triaged each failure, fixed the real root cause, and then merged everything in a safe order so I wouldn't create fresh conflicts. If you run a large static site on GitHub Actions, I hope this saves you a few hours of panic.

## Context: When several PRs fail together

The first rule when many PRs are red: **don't fix blindly**. Each PR fails for a different reason. My job is to read the logs, bucket every PR into a root-cause group, then handle each group by priority. The seven PRs fell into four buckets:

| Failure group | PRs | Nature |
|---------------|-----|--------|
| Hung build / stuck runner | #934 | CI infrastructure, not a code bug |
| Template (Tera) syntax error | #935 | Genuinely breaks `zola build` |
| Merge conflict with `main` | #936, #938 | Stale branch base |
| CI not triggered / already done | #939, #942, #943 | Trigger or state |

Once classified, the situation felt far less scary. Let's walk each case.

## #934 — Hung build: cancel and re-run

The symptom for #934 was a `build-smoke` job that ran forever. The log stopped updating, the runner never released, and GitHub eventually marked it as a timeout. This is **not a code bug** — it's a stuck runner, an infrastructure event.

For this class of failure, re-diagnosing the code is pointless. The correct fix:

1. Open the **Actions** tab in the GitHub UI.
2. Open the hung run and click **Cancel workflow** to kill the stuck job.
3. Click **Re-run jobs** to start fresh on a new runner.

After the re-run, `build-smoke` went green immediately. Lesson: distinguish an **infrastructure failure** from a **logic failure**. A hung runner doesn't need a code commit — it needs to be cancelled and re-run.

## #935 — Tera syntax error: the root cause that broke the build

This was the most dangerous PR because it **actually broke `zola build`**. The log reported a template render error pointing at two files: `faq.html` and `related-posts.html`.

There were two Tera (Zola's template language) syntax problems:

**First — the `contains` operator used out of context.** Tera does not support `contains` as an arbitrary infix operator on every data type. When the template tried to use `contains` for string/array checks in an unsupported way, the renderer threw. The fix is to remove the `contains` operator and replace it with valid logic (for example, a proper filter or a condition that matches Tera's actual API).

**Second — string concatenation via `concat` instead of the `~` operator.** In Tera, the canonical way to join strings is the tilde `~` operator, not a `concat`-style function. A quick illustration:

```jinja2
{# ❌ Wrong — causes a render error #}
{% set url = concat(base, slug) %}

{# ✅ Right — use the ~ operator to concatenate #}
{% set url = base ~ slug %}
```

After removing `contains` and switching `concat` to `~` in both `faq.html` and `related-posts.html`, the build went green. This is exactly the kind of error a static Tera-syntax "vaccine" should catch before the build even runs — scan templates for the bad pattern and block it right at the QA gate.

## #936 and #938 — Merge conflicts: rebase onto the latest main

Both PRs were red because their branch base was **older than `main`**. While the PRs sat open, `main` received new commits, and those changes touched the same file regions.

- **#936**: the conflict was in `base.html` — a shared infrastructure file that collides easily when several PRs edit the layout. The fix: rebase the branch onto current `main`, open `base.html`, read **both sides** carefully, preserve the PR's intent while keeping the safety fixes already on `main`. For shared template/UI files, never blindly pick one side.
- **#938**: after rebasing onto `main`, the `static-checks` group went green again — because the latest vaccine-gate update was already on `main`. The stale branch ran against an old detector and reported a false failure; syncing the detector via rebase was enough.

The takeaway: many "red" PRs aren't red because the code is wrong — they're red because the **branch lags behind `main`**. Rebase first, judge second.

## #939 — CI not triggered: empty commit to re-trigger

#939 sat in an annoying state: no checks ran, and the PR hung waiting for a CI that never arrived. A common cause is a pipeline that triggers via `push`/`workflow_run` where the triggering event was missed.

The cleanest way to re-trigger without touching content is to push an **empty commit**:

```bash
git commit --allow-empty -m "trigger CI"
git push
```

An empty commit changes not a single line of code but creates a new `push` event that wakes the pipeline. CI runs, checks pass, the PR is ready.

## #942 and #943 — Done and ready

- **#942**: already merged earlier. I noted it as a reference point and took no further action. Recognizing that "this PR is already done" matters as much as fixing a bug — it avoids redundant operations on something already closed.
- **#943**: all checks green, no conflicts. This PR could be merged directly.

## A safe merge order

Fixing the failures is only half the job. The other half is **merging in the right order** so you don't spawn a new round of conflicts. When several PRs touch shared files, each merge shifts `main` — and the remaining PRs instantly fall behind their base.

The order I applied:

1. **#943 first** — fully green; merge it to lock in a clean baseline.
2. **#936 next** — it touches `base.html`; merge it early so the other branches can rebase onto the newest layout.
3. **Rebase #934, #935, #938, #939** onto the freshly updated `main`, then **merge sequentially** one at a time, waiting for green CI before moving to the next PR.

The merge command I used for each PR (squash to keep `main` history clean, delete the branch after merge):

```bash
gh pr merge <PR> -s --delete-branch
```

The `-s` (squash) flag collapses all of a PR's commits into a single commit on `main`; `--delete-branch` cleans up the merged branch. Merging **sequentially** — one pipeline at a time — avoids multiple deploys running in parallel and hammering the API.

## A short checklist for next time

- [ ] **Classify first, fix second.** Bucket every red PR into a root-cause group.
- [ ] **Infrastructure failure ≠ code failure.** Hung build → cancel and re-run, don't commit.
- [ ] **Tera: concatenate with `~`, not `concat`.** Avoid `contains` outside its supported context.
- [ ] **Stale branch → rebase onto `main`** before suspecting the code.
- [ ] **CI didn't run → empty commit** `git commit --allow-empty`.
- [ ] **Merge in order**: clean baseline first, shared files early, the rest rebased then merged sequentially.
- [ ] **Squash + delete branch**: `gh pr merge <PR> -s --delete-branch`.

## The biggest lesson

Seven red PRs look like a crisis, but most of them weren't "bad code." They were a mix of one stuck runner, two lines of template syntax, a few stale-base branches, and one missed CI event. Once you separate the layers — infrastructure, syntax, base sync, trigger — each failure becomes small and has a known fix. Calm classification beats fast typing.
