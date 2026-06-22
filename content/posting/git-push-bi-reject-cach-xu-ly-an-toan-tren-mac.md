+++
title = "Git push bị reject? Cách xử lý an toàn trên Mac"
description = "Xử lý git push reject: non-fast-forward, git rebase, và tránh QA false positive từ .venv."
date = 2026-06-21
aliases = ["/git-push-bi-reject-cach-xu-ly-an-toan-tren-mac/"]
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["git fetch", "git mac", "git pull rebase", "git push reject", "github cli", "non-fast-forward", "qa workflow", "virtualenv"]
[extra]
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
seo_keyword = "git push bị reject"
featured = false

[[extra.faq]]
q = "Non-fast-forward là gì và tại sao nó khiến git push bị reject?"
a = "Non-fast-forward xảy ra khi branch local của bạn đã lạc hậu so với remote (ai đó đã push commit mới từ máy khác hoặc branch khác). Git không cho phép push vì sẽ làm mất những commit mới đó trên server. Cách an toàn: chạy `git fetch origin` để lấy thay đổi mới nhất, rồi `git rebase origin/main` để đặt commit của bạn lên trên."

[[extra.faq]]
q = "Git pull rebase khác gì so với git merge, và tại sao nó an toàn?"
a = "`git merge` tạo ra một commit merge thêm, có thể làm lộn xộn lịch sử; `git rebase` sắp xếp lại commit của bạn lên trên những commit mới từ remote, giữ lịch sử tuyến tính và sạch. Rebase an toàn miễn là bạn chưa push commit đó (quy tắc: không rebase commit công khai)."

[[extra.faq]]
q = "Tại sao git push --force nguy hiểm và khi nào mới dùng?"
a = "`git push --force` bỏ qua tất cả kiểm tra và ghi đè những gì trên server, có thể làm mất commit của người khác. Chỉ dùng trong trường hợp rất hiếm gặp (vd: fix commit công khai bằng `git commit --amend` rồi force-push đến nhánh riêng của bạn), và phải báo trước team. KHÔNG bao giờ force-push `main` hoặc branch dùng chung."

[[extra.faq]]
q = "QA false positive do .venv là gì? Làm sao để tránh?"
a = "Khi bạn commit thư mục `.venv` (Python virtualenv) vào repo, máy khác clone repo này sẽ có `.venv` lạ hoặc khác phiên bản, làm cho local QA tests chạy không đúng (vd: một test pass, máy khác fail). Giải pháp: thêm `.venv/` vào `.gitignore`, tạo `.venv` ở ngoài repo hoặc dùng `/tmp/project-qa-venv` cho mục đích QA."

[[extra.faq]]
q = "Làm sao để chắc chắn push của tôi không bị reject lần tới?"
a = "Trước mỗi push, chạy `git fetch origin` để lấy thay đổi mới nhất, kiểm tra `git log origin/main..HEAD` để xem commit của bạn, rồi `git rebase origin/main` nếu có diverge. Ghi nhớ: fetch trước, rebase nếu cần, push sau. Trên Mac, có thể tạo Git hook để tự động làm điều này."
+++

> 🔧 **Bài học từ thực tế**: Lỗi "git push bị reject" thường xảy ra khi làm việc theo team — ai đó push commit, bạn không fetch kip, rồi bạn push code mà không biết có commit mới từ remote. Bài này hướng dẫn cách xử lý an toàn và cách tránh QA false positive ngoài ý muốn. Xem thêm [hướng dẫn sync cơ bản push/pull/fetch](/push-pull-fetch-dong-bo-voi-github/) hoặc [cách xử lý conflict](/git-merge-va-xu-ly-conflict/).

Mỗi lập trình viên làm việc với team từng gặp tình huống này: bạn code xong, chạy `git push origin main`, nhưng Git từ chối với dòng lỗi kiểu **"rejected ... \[non-fast-forward\]"**. Điều gì xảy ra? Làm thế nào để sửa mà không mất code, mà không phải xoá branch và clone lại từ đầu? Bài viết này sẽ giải thích rõ ràng, cung cấp từng bước an toàn và cách tránh lỗi phổ biến mà nhiều người mắc phải.

<!-- more -->

## Tại sao git push bị reject: Non-fast-forward là gì?

Git từ chối push khi phát hiện **non-fast-forward** — điều này có nghĩa là remote branch (trên server, vd GitHub) đã có commit mà local repository của bạn chưa có. Định nghĩa chính thức có thể tìm tại [tài liệu Git chính thức](https://git-scm.com/docs/git-push).

**Kịch bản thực tế:**
1. Lúc 9:00 sáng, bạn và đồng nghiệp A clone repo từ server. Cả hai ở commit `A123`.
2. Lúc 10:00, A code xong 2 commit mới (`B456`, `C789`) và push lên main.
3. Lúc 11:00, bạn code xong 1 commit của mình (`D012`) và chạy `git push origin main`.
4. **Git từ chối**: vì server có `B456 → C789`, nhưng bạn chỉ có `A123 → D012`. Hai nhánh đã **phân nhánh** (diverge), Git không biết nên giữ lại cái nào.

Cách fix: bạn phải kéo những commit mới của A xuống, đặt commit của bạn lên trên, rồi mới được push.

## Git fetch vs Git pull vs Git rebase: Hiểu đúng từng lệnh

Trước khi fix, bạn cần hiểu rõ ba lệnh thường nhầm lẫn:

### Git fetch — "Lấy, nhưng chưa merge"

```bash
git fetch origin
```

Lệnh này **download** tất cả commit mới từ remote (GitHub/server) vào máy của bạn, nhưng **không thay đổi file hiện tại**. Điều này an toàn hoàn toàn — chỉ download, không merge hay xoá.

Sau `git fetch`, bạn có thể xem `git log origin/main..HEAD` để kiểm tra bạn có bao nhiêu commit ahead (phía trước) so với remote.

### Git pull — "Fetch + merge (thường)"

```bash
git pull origin main
```

Mặc định, `git pull` = `git fetch` + `git merge`. Nghĩa là nó vừa download vừa merge, rồi tạo ra một **commit merge** nếu có xung đột (conflict). Commit merge này làm lịch sử Git trông "loạn".

### Git rebase — "Sắp xếp lại commit: sạch nhưng cần cẩn"

```bash
git fetch origin
git rebase origin/main
```

Thay vì merge, `rebase` **sắp xếp lại** commit của bạn lên trên những commit mới từ remote. Kết quả là một đường thẳng sạch sẽ thay vì nhiều nhánh rối.

> ⚠️ **Quy tắc vàng của rebase**: Chỉ rebase commit mà **bạn chưa push** hoặc commit trên **nhánh riêng của bạn**. KHÔNG rebase commit công khai (người khác đã pull) vì sẽ khiến lịch sử bị thay đổi và gây khó chịu cho team.

## Quy trình an toàn khi git push bị reject

Khi bạn gặp lỗi "rejected", hãy làm theo từng bước:

### Bước 1: Fetch thay đổi mới nhất từ remote

```bash
git fetch origin
```

Không có hại, an toàn hoàn toàn. Lệnh này chỉ download, không merge hay xoá.

### Bước 2: Kiểm tra tình trạng branch

```bash
git log origin/main..HEAD
```

Lệnh này hiển thị commit của bạn (HEAD) mà remote chưa có (origin/main). Nếu thấy commit của bạn ở đây, điều đó có nghĩa là bạn ahead.

Ngược lại, kiểm tra remote ahead:

```bash
git log HEAD..origin/main
```

Nếu thấy commit ở đây, điều đó có nghĩa là remote ahead — cần rebase.

### Bước 3: Rebase an toàn (phương pháp được khuyến nghị)

```bash
git rebase origin/main
```

Lệnh này sắp xếp lại commit của bạn lên trên những commit mới từ remote. Nếu có xung đột (conflict), Git sẽ dừng và báo cho bạn giải quyết.

Nếu gặp conflict, hãy sửa file, rồi:

```bash
git add <file-name>
git rebase --continue
```

Nếu muốn hủy rebase (quay lại trạng thái trước):

```bash
git rebase --abort
```

### Bước 4: Push lại

```bash
git push origin main
```

Lần này sẽ thành công vì bạn đã có tất cả commit từ remote.

## Tại sao không dùng git push --force?

`--force` (hay `-f`) là lệnh rất nguy hiểm:

```bash
git push --force origin main  # ⚠️ NGUY HIỂM! Đừng làm!
```

Lệnh này bỏ qua tất cả kiểm tra, ghi đè bất kỳ thứ gì trên server. Nếu đồng nghiệp vừa push commit lên server, `--force` của bạn sẽ **xoá commit đó đi**. Họ sẽ rất tức giận.

**Khi nào thì dùng `--force`?**
- Rất hiếm, và phải báo trước team.
- Ví dụ: bạn làm việc trên nhánh riêng `feature/bao-mat-password`, commit được push lên, nhưng bạn phát hiện lỗi bảo mật, dùng `git commit --amend` để sửa, rồi `git push --force` để cập nhật nhánh đó (chỉ nếu không ai khác đang pull nhánh này).
- **KHÔNG bao giờ** `git push --force` vào `main` hoặc nhánh dùng chung.

Thay `--force`, dùng `git push --force-with-lease` nếu thật sự cần — nó an toàn hơn một chút vì sẽ từ chối nếu có commit mới từ người khác.

## QA false positive do .venv trong repo: Bài học thực tế

Có một vấn đề phổ biến khác khiến developer mắc lỗi: commit thư mục `.venv` (hoặc `node_modules`, `vendor/`) vào repo.

**Kịch bản:**
1. Bạn tạo virtualenv: `python3 -m venv .venv` để cài dependencies.
2. Vô tình commit `.venv/` vào repo (quên thêm vào `.gitignore`).
3. Đồng nghiệp B clone repo, anh ta có `.venv` lạ hoặc khác phiên bản dependencies.
4. Chạy `python3 qa_check.py`, test fails trên máy B nhưng pass trên máy bạn.
5. Cả hai bối rối: "Why fail here but pass on yours?" — **False positive do environment mismatch**.

**Cách fix:**
1. Thêm vào `.gitignore`:

```
.venv/
venv/
node_modules/
```

2. Tạo virtualenv ở ngoài repo hoặc tại `/tmp`:

```bash
python3 -m venv /tmp/project-qa-venv
source /tmp/project-qa-venv/bin/activate
pip install -r requirements.txt
python3 qa_check.py
```

3. Hoặc tạo script tự động:

```bash
#!/bin/bash
QA_VENV="/tmp/project-qa-venv"
python3 -m venv "$QA_VENV"
source "$QA_VENV/bin/activate"
pip install -r requirements.txt
python3 qa_check.py
```

Lợi ích:
- Không phải commit virtual env.
- Mỗi máy tự cài dependencies sạch sẽ.
- QA tests chạy đúng, không false positive.

## Pre-push checklist cho macOS

Trước mỗi `git push`, hãy chạy checklist này để tránh lỗi:

1. **Fetch mới nhất:**
   ```bash
   git fetch origin
   ```

2. **Kiểm tra branch nào được push:**
   ```bash
   git branch -vv
   ```
   Nên thấy `[origin/main]` hoặc nhánh tracking của bạn.

3. **Xem lại log commit của bạn:**
   ```bash
   git log origin/main..HEAD --oneline
   ```

4. **Rebase nếu cần:**
   ```bash
   git rebase origin/main
   ```

5. **Chạy local QA (nếu có):**
   ```bash
   python3 qa_check.py
   ```
   (Chắc chắn `.venv` không trong repo, hoặc dùng `/tmp/project-qa-venv`).

6. **Push:**
   ```bash
   git push origin main
   ```

## Sử dụng GitHub CLI (gh) để kiểm tra trước push

Nếu bạn dùng GitHub CLI (`gh`), có thể kiểm tra trạng thái PR/branch:

```bash
gh pr list --draft=false --state=open
```

Hoặc kiểm tra workflows:

```bash
gh run list
```

Điều này giúp bạn biết có QA failure hay CI đỏ trước khi push thêm.

## Tóm lại: Cách an toàn và quy tắc vàng

**Git push bị reject** không phải lỗi nghiêm trọng — chỉ là Git bảo vệ bạn khỏi việc mất commit. Quy trình an toàn:

1. `git fetch origin` — lấy thay đổi mới nhất (an toàn).
2. `git log HEAD..origin/main` — kiểm tra xem remote có commit nào mới.
3. `git rebase origin/main` — sắp xếp lại commit của bạn (sạch hơn merge).
4. `git push origin main` — push lên.

**Tránh:**
- `git push --force` vào `main` hoặc nhánh dùng chung.
- Commit `.venv/`, `node_modules/`, hoặc file tạm vào repo.
- Để `.venv` trong repo mà không sửa `.gitignore` (gây QA false positive).

Khi team làm việc cùng nhau, những qui tắc đơn giản này giúp mọi người không bị mất code, lịch sử Git sạch sẽ, và QA tests chạy đúng trên tất cả máy.

Hẹn gặp lại ở bài tiếp theo về cách quản lý nhánh (branch) hiệu quả! 🚀
