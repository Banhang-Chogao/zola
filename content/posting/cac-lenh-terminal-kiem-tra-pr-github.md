+++
title = "Câu lệnh kiểm tra PR GitHub từ terminal: hướng dẫn"
date = 2026-06-22
aliases = ["/cac-lenh-terminal-kiem-tra-pr-github/"]
description = "Các lệnh terminal kiểm tra PR, CI/CD, deploy trên GitHub từ terminal mà không cần UI."
slug = "cac-lenh-terminal-kiem-tra-pr-github"

[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["ci cd", "debug", "gh", "git", "github", "github cli", "pr", "terminal"]
[extra]
thumbnail = "https://picsum.photos/seed/terminal-github-pr/600/400"
seo_keyword = "câu lệnh kiểm tra PR GitHub"
featured = false
+++

Khi bạn làm việc trên một dự án có CI/CD tự động, việc dùng **các câu lệnh kiểm tra PR GitHub** trực tiếp từ terminal sẽ giúp bạn nhanh hơn và không phụ thuộc vào UI web. Thay vì click qua các tab, bạn có thể dùng GitHub CLI để check PR status, xem CI log, quản lý workflow — chỉ cần mở terminal.

Bài này liệt kê **toàn bộ câu lệnh terminal kiểm tra PR GitHub** mà bạn cần để check status, xem CI/deploy log, quản lý workflow từ local — giúp bạn tự chẩn đoán khi build fail hay deploy chậm mà không cần chờ UI load.

<!-- more -->

## Tại sao nên dùng các câu lệnh kiểm tra PR GitHub?

**Tính độc lập:** bạn có thể kiểm tra bất kỳ lúc nào từ máy riêng, không cần mở browser.

**Tốc độ:** đánh một lệnh nhanh hơn click qua 5 tab UI.

**Debug hiệu quả:** xem CI log trực tiếp, không lỡ thông tin khi UI load chậm.

**Tự động hoá:** kết hợp script để monitor deployment hoặc trigger workflow mà không cần tay.

## Cài đặt & đăng nhập GitHub CLI

Trước hết, bạn cần cài GitHub CLI (`gh`):

```bash
# Trên Mac (dùng Homebrew)
brew install gh

# Trên Linux (Ubuntu/Debian)
sudo apt install gh

# Trên Windows (dùng Chocolatey)
choco install gh
```

**Kiểm tra cài đặt:**

```bash
gh --version
```

**Đăng nhập vào GitHub:**

```bash
gh auth login
```

Làm theo hướng dẫn trên màn hình — chọn GitHub.com, HTTPS, authorize browser.

**Kiểm tra trạng thái đăng nhập:**

```bash
gh auth status
```

Nếu thành công, bạn sẽ thấy tên tài khoản GitHub của mình.

---

## Kiểm tra trạng thái PR

### 1. Xem danh sách PR đang mở (`gh pr status`)

```bash
gh pr status
```

**Kết quả:** liệt kê PR của bạn (draft, review, CI checking…).

**Khi dùng:** sau khi push branch mới để xác nhận PR đã được tạo.

### 2. Xem chi tiết 1 PR cụ thể (`gh pr view`)

```bash
gh pr view 123
```

**Kết quả:** hiển thị số PR, tiêu đề, mô tả, người review, trạng thái merge.

**Khi dùng:** kiểm tra PR có sẵn hay chưa, xem review comment.

### 3. Xem kết quả checks của PR (`gh pr checks`)

```bash
gh pr checks 123
```

**Kết quả:** liệt kê tất cả check (CI/QA/build…) và trạng thái (✓ pass, ✗ fail, ⊘ pending).

**Khi dùng:** xác minh rằng QA, build và tất cả required check đều xanh trước khi merge.

### 4. Theo dõi check realtime (`gh pr checks --watch`)

```bash
gh pr checks 123 --watch
```

**Kết quả:** hiển thị check và tự cập nhật khi trạng thái thay đổi — không cần refresh.

**Khi dùng:** đợi CI chạy xong mà không cần vào GitHub.com.

### 5. So sánh code giữa PR và main (`gh pr diff`)

```bash
gh pr diff 123
```

**Kết quả:** diff đầy đủ các file thay đổi trong PR.

**Khi dùng:** xem lại diff local trước khi merge hoặc review code thay đổi.

---

## Kiểm tra CI/Workflow & Deploy

### 1. Liệt kê các workflow run gần nhất (`gh run list`)

```bash
gh run list
```

**Kết quả:** danh sách 10 run gần nhất (ID, tên workflow, status, branch, ngày).

**Khi dùng:** xem lịch sử deploy hay workflow chạy.

**Ví dụ:** `gh run list --limit 20` — xem 20 run cuối cùng.

### 2. Xem chi tiết 1 run (`gh run view`)

```bash
gh run view 12345
```

**Kết quả:** ID run, workflow name, status, jobs, ngày start/finish.

**Khi dùng:** kiểm tra run cụ thể để xem job nào fail.

### 3. Xem log chi tiết của 1 run (`gh run view --log`)

```bash
gh run view 12345 --log
```

**Kết quả:** in toàn bộ log text của tất cả job trong run đó.

**Khi dùng:** debug khi workflow fail — xem error message, stack trace.

**Ví dụ:** `gh run view 12345 --log | grep -i "error"` — tìm error trong log.

### 4. Theo dõi run realtime (`gh run watch`)

```bash
gh run watch 12345
```

**Kết quả:** hiển thị trạng thái job và cập nhật live khi job chạy.

**Khi dùng:** đợi deploy xong mà không cần mở browser.

### 5. Liệt kê workflow (`gh workflow list`)

```bash
gh workflow list
```

**Kết quả:** danh sách workflow trong repo (build, deploy, qa-check…) và trạng thái.

**Khi dùng:** xem tất cả workflow để quyết định trigger cái nào.

### 6. Xem workflow cụ thể (`gh workflow view`)

```bash
gh workflow view deploy.yml
```

**Kết quả:** chi tiết workflow: trigger, step, status.

**Khi dùng:** hiểu workflow hoạt động thế nào trước khi trigger.

---

## Kiểm tra Git local

### `git status`

```bash
git status
```

**Kết quả:** branch hiện tại, file thay đổi, staged changes.

**Khi dùng:** trước khi commit — xác nhận thay đổi đúng.

### `git branch -a`

```bash
git branch -a
```

**Kết quả:** danh sách branch local và remote.

**Khi dùng:** check branch nào đã merge hay tìm branch cũ.

### `git log --oneline -20`

```bash
git log --oneline -20
```

**Kết quả:** 20 commit gần nhất, mỗi dòng một commit (SHA, message).

**Khi dùng:** xem commit history và tìm commit cụ thể.

### `git remote -v`

```bash
git remote -v
```

**Kết quả:** danh sách remote (origin URL, upstream…).

**Khi dùng:** xác minh remote đúng trước khi push.

### `git fetch origin`

```bash
git fetch origin
```

**Kết quả:** tải thông tin branch mới từ remote (không thay file local).

**Khi dùng:** cập nhật cache remote trước khi check branch.

---

## Bảng lệnh nhanh — dùng khi nào + ví dụ

| Lệnh | Khi dùng | Ví dụ |
|------|----------|-------|
| `gh pr status` | Xem PR của bạn đang ở trạng thái gì | Sau khi push branch mới |
| `gh pr view 123` | Xem chi tiết PR #123 | Trước merge — check reviewer |
| `gh pr checks 123` | Xem check/CI pass hay fail | Đợi CI xong |
| `gh pr checks 123 --watch` | Đợi CI mà không refresh | Đợi deploy lần đầu |
| `gh pr diff 123` | So sánh code PR vs main | Review before merge |
| `gh run list` | Xem workflow run gần nhất | Tìm run fail |
| `gh run view 12345` | Chi tiết run cụ thể | Xem job nào fail |
| `gh run view 12345 --log` | Log text đầy đủ | Debug error message |
| `gh run watch 12345` | Theo dõi run live | Đợi deploy xong realtime |
| `gh workflow list` | Danh sách workflow | Quyết định trigger nào |
| `git status` | File thay đổi hiện tại | Trước commit |
| `git log --oneline -20` | 20 commit gần nhất | Tìm commit để revert |
| `git fetch origin` | Cập nhật cache remote | Trước kiểm tra branch cũ |

---

## Quy trình debug nhanh 5 phút

Khi PR fail hoặc deploy chậm, đây là các bước kiểm tra nhanh:

**Bước 1:** Kiểm tra PR check xanh hay đỏ
```bash
gh pr checks 123
```

**Bước 2:** Nếu đỏ, xem log của run fail
```bash
gh run list | grep -i "deploy\|build\|fail"
# Lấy RUN_ID từ kết quả
gh run view <RUN_ID> --log | grep -i "error"
```

**Bước 3:** Nếu không tìm thấy, xem log đầy đủ
```bash
gh run view <RUN_ID> --log | less
# Bấm '/' để search keyword, 'q' để thoát
```

**Bước 4:** Nếu là build fail (Zola, SCSS, JS…), fix local + commit + push
```bash
git add .
git commit -m "fix: build error on [component]"
git push origin <branch-name>
# Quay lại bước 1
```

**Bước 5:** Nếu là merge conflict, resolve + push lại
```bash
git fetch origin main
git merge origin/main
# Sửa conflict trong editor
git add .
git commit -m "resolve: merge conflict with main"
git push origin <branch-name>
```

---

## FAQ

**Q: Làm sao để trigger workflow từ terminal?**

A: Dùng `gh workflow run`:
```bash
gh workflow run deploy.yml --ref main
```

**Q: Có thể xem log của job cụ thể (không phải toàn run)?**

A: Chưa có lệnh riêng, nhưng bạn có thể filter log:
```bash
gh run view 12345 --log | grep "job-name-here"
```

**Q: Làm sao để tự động check PR cứ 30 giây?**

A: Viết script bash loop (hoặc dùng `watch`):
```bash
watch -n 30 "gh pr checks 123"
```

**Q: Terminal không hiển thị màu, khó đọc?**

A: Thêm flag `--web` để mở browser thay vì terminal:
```bash
gh pr view 123 --web
```

---

## Kết luận

Biết các lệnh terminal để kiểm tra PR, CI, deploy sẽ giúp bạn:

✅ **Độc lập:** không cần UI, không cần click chuột.

✅ **Nhanh:** lệnh text nhanh hơn mở browser.

✅ **Chuyên nghiệp:** developer thật biết dùng terminal.

✅ **Tự động:** có thể kết hợp script để monitor.

Nếu bạn muốn tìm hiểu sâu hơn về quy trình git từ đầu, đừng bỏ qua bài [lệnh Git đưa blog lên production](/cac-lenh-git-dua-blog-len-production/) — nó giải thích từng bước push, commit, tạo PR.

Hôm nay, hãy mở terminal và thử `gh pr status` — bạn sẽ thấy nó dễ dùng hơn bạn tưởng. 

**Tham khảo thêm:** [GitHub CLI Documentation](https://cli.github.com/manual/) (tiếng Anh) có đầy đủ lệnh và ví dụ từ chính GitHub. 🚀
