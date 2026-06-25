+++
title = "Git commands đưa blog lên production: giải thích từng lệnh"
date = 2026-06-22
aliases = ["/cac-lenh-git-dua-blog-len-production/"]
description = "Giải thích các câu lệnh Git đã dùng để viết bài blog từ local terminal, chạy QA, tạo PR và đưa nội dung lên production."
slug = "cac-lenh-git-dua-blog-len-production"

[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["ci cd", "git", "github", "production", "qa gatekeeper", "static blog", "terminal"]
[extra]
thumbnail = "https://picsum.photos/seed/git-terminal-production/600/400"
seo_keyword = "lệnh Git đưa blog lên production"
featured = false
+++

Bài này liệt kê và giải thích toàn bộ các **lệnh Git đưa blog lên production** mà tôi đã dùng để viết, kiểm tra và xuất bản một bài viết trên blog tĩnh Zola — đúng theo thứ tự thực tế trong terminal. Nếu bạn chưa đọc bối cảnh, hãy xem trước [case study fix QA Gatekeeper GitHub Actions](/fix-qa-gatekeeper-github-actions-merge-conflict-zola/) để hiểu vì sao quy trình này lại quan trọng.

Mục tiêu của bài là beginner-friendly: với mỗi lệnh, tôi sẽ nói rõ **nó làm gì**, **vì sao tôi dùng**, và **nó tránh được sai lầm nào**. Đây không phải lý thuyết Git hàn lâm, mà là đúng những lệnh một người viết blog cần để đưa nội dung từ máy mình lên production an toàn.

<!-- more -->

## Bước 1 — Đồng bộ với main trước khi làm gì cả

### `git fetch origin`

```bash
git fetch origin
```

* **Làm gì:** tải về thông tin mới nhất từ remote (`origin`) nhưng **không** thay đổi file đang làm việc của bạn.
* **Vì sao dùng:** để biết `main` trên GitHub đã đi tới đâu trước khi bắt đầu.
* **Tránh sai lầm:** tránh làm việc trên một bản `main` cũ rồi sau đó dính merge conflict không đáng có.

### `git checkout main`

```bash
git checkout main
```

* **Làm gì:** chuyển sang nhánh `main` trong máy bạn.
* **Vì sao dùng:** mọi nhánh mới nên xuất phát từ `main`, để bài viết của bạn dựa trên trạng thái production gần nhất.
* **Tránh sai lầm:** tránh tạo nhánh từ một nhánh cũ dở dang, kéo theo thay đổi không liên quan.

### `git pull origin main`

```bash
git pull origin main
```

* **Làm gì:** cập nhật nhánh `main` cục bộ bằng những commit mới nhất từ remote.
* **Vì sao dùng:** `fetch` chỉ tải về, `pull` mới thực sự hợp nhất vào nhánh hiện tại.
* **Tránh sai lầm:** tránh "stale base" — tức nhánh mới tạo đã lạc hậu ngay từ đầu.

## Bước 2 — Tạo nhánh làm việc riêng

### `git checkout -b feat/ten-nhanh`

```bash
git checkout -b feat/blog-terminal-production-cluster
```

* **Làm gì:** tạo một nhánh mới và chuyển sang nó ngay.
* **Vì sao dùng:** mỗi thay đổi nên nằm trên một nhánh riêng, không đụng trực tiếp `main`.
* **Tránh sai lầm:** tránh commit thẳng vào `main`, điều mà branch protection thường chặn và cũng rất rủi ro.

> Mẹo đặt tên: dùng tiền tố như `feat/`, `fix/`, `hotfix/` để người khác (và CI) hiểu ngay nhánh này làm gì.

## Bước 3 — Tìm và sắp xếp file nội dung

### `find ...`

```bash
find content/posting -maxdepth 1 -name "*.md" -print
```

* **Làm gì:** liệt kê file theo điều kiện (tên, loại, thư mục).
* **Vì sao dùng:** để chắc chắn file bài viết nằm đúng thư mục và chưa trùng tên.
* **Tránh sai lầm:** tránh tạo file ở sai chỗ khiến Zola build ra URL không như mong muốn.

### `grep ...`

```bash
grep -RIn "slug =" content/posting/
```

* **Làm gì:** tìm chuỗi văn bản bên trong file.
* **Vì sao dùng:** kiểm tra xem `slug` mới có bị trùng với bài cũ không, hoặc tìm conflict marker còn sót.
* **Tránh sai lầm:** tránh trùng slug (gây lỗi URL) và tránh để sót dấu `<<<<<<<` sau khi resolve conflict.

### `mv ...`

```bash
mv content/posting/ban-nhap.md content/posting/ten-bai-chinh-thuc.md
```

* **Làm gì:** đổi tên hoặc di chuyển file.
* **Vì sao dùng:** khi muốn đổi slug bằng cách đổi tên file, hoặc dời file vào đúng section.
* **Tránh sai lầm:** tránh tạo file mới rồi copy thủ công, dễ để lại bản nháp thừa trong repo.

## Bước 4 — Kiểm tra chất lượng ngay trên máy

### `python3 qa_check.py`

```bash
python3 qa_check.py
```

* **Làm gì:** chạy bộ kiểm tra QA của repo — conflict marker, secret, SEO frontmatter, SCSS và các rule production-safe.
* **Vì sao dùng:** để bắt lỗi **trước** khi đẩy lên GitHub, thay vì chờ CI báo đỏ rồi mới sửa.
* **Tránh sai lầm:** tránh push một bài thiếu `title`, sai `date`, hoặc còn sót lỗi mà QA Gatekeeper chắc chắn sẽ chặn.

## Bước 5 — Build sạch và kiểm 404 trước khi push

Đây là phần nhiều người bỏ qua, nhưng với blog tĩnh thì cực kỳ quan trọng.

### `rm -rf public`

```bash
rm -rf public
```

* **Làm gì:** xóa thư mục build cũ.
* **Vì sao dùng:** để lần build sau hoàn toàn sạch, không lẫn file rác từ lần trước.
* **Tránh sai lầm:** tránh "stale public" — khi checker đọc nhầm bản build cũ và báo 404 giả hàng loạt.

### `zola build`

```bash
zola build
```

* **Làm gì:** dựng toàn bộ site tĩnh vào thư mục `public/`.
* **Vì sao dùng:** để có bản HTML thật mà trình kiểm tra link sẽ quét.
* **Tránh sai lầm:** tránh push khi build đang lỗi (sai cú pháp Tera, frontmatter hỏng…).

### `python3 qa-404-checker.py`

```bash
python3 qa-404-checker.py
echo "qa_404_exit=$?"
```

* **Làm gì:** quét mọi trang trong `public/` và báo internal link/ảnh bị hỏng.
* **Vì sao dùng:** để chắc chắn bài mới không tạo broken link, đặc biệt là đường dẫn ảnh.
* **Tránh sai lầm:** tránh xuất bản link chết — thứ làm hỏng trải nghiệm đọc và ảnh hưởng index trên Google. Nếu checker fail vì broken link thật trong bài mới, **đừng push** cho tới khi sửa xong.

## Bước 6 — Soi kỹ thay đổi trước khi commit

### `git status -sb`

```bash
git status -sb
```

* **Làm gì:** hiển thị ngắn gọn nhánh hiện tại và các file đã đổi/đang chờ.
* **Vì sao dùng:** để biết chính xác mình sắp commit những gì.
* **Tránh sai lầm:** tránh vô tình commit file rác như `public/`, file tạm, hay report tự sinh.

### `git diff --stat`

```bash
git diff --stat
```

* **Làm gì:** tóm tắt số dòng thêm/bớt ở mỗi file chưa staged.
* **Vì sao dùng:** để xác nhận thay đổi đúng phạm vi bài viết, không lan sang file khác.
* **Tránh sai lầm:** tránh "PR phình to" do lỡ sửa file không liên quan.

## Bước 7 — Staging có chủ đích (đừng `git add .` bừa)

### `git add <đường-dẫn-cụ-thể>`

```bash
git add content/posting/ten-bai.md
git add static/img/posting/ten-bai/cover.webp
```

* **Làm gì:** đưa đúng những file bạn muốn vào vùng staging.
* **Vì sao dùng:** để commit chỉ gồm bài viết và ảnh của nó.
* **Tránh sai lầm:** đây là chỗ quan trọng nhất của bài.

> ⚠️ **Cảnh báo:** đừng dùng `git add .` một cách máy móc khi bạn chỉ định commit một bài viết và vài ảnh. `git add .` gom **tất cả** thay đổi trong thư mục, kể cả file build `public/`, report do công cụ tự sinh (ví dụ `data/*.json`), hay file cấu hình cá nhân. Hãy liệt kê đường dẫn cụ thể. Một commit sạch giúp PR dễ review và giảm hẳn nguy cơ conflict.

### `git diff --cached --stat`

```bash
git diff --cached --stat
```

* **Làm gì:** xem tóm tắt những gì **đã** được staged (chuẩn bị commit).
* **Vì sao dùng:** kiểm tra lần cuối trước khi commit — đúng file, đúng số lượng.
* **Tránh sai lầm:** tránh commit nhầm file lọt vào staging mà bạn không để ý.

## Bước 8 — Ghi lại lịch sử với một commit rõ ràng

### `git commit -m "..."`

```bash
git commit -m "feat(blog): publish terminal production content cluster"
```

* **Làm gì:** tạo một commit từ các file đã staged, kèm thông điệp mô tả.
* **Vì sao dùng:** commit message rõ ràng giúp bạn và người khác hiểu thay đổi sau này.
* **Tránh sai lầm:** tránh message kiểu "update" hay "fix" vô nghĩa. Một tiền tố như `feat(blog):` cho biết ngay đây là nội dung mới.

## Bước 9 — Đẩy nhánh lên GitHub

### `git push -u origin <branch>`

```bash
git push -u origin feat/blog-terminal-production-cluster
```

* **Làm gì:** đẩy nhánh cục bộ lên remote và thiết lập theo dõi (`-u`).
* **Vì sao dùng:** nhờ `-u`, các lần sau bạn chỉ cần `git push` là đủ.
* **Tránh sai lầm:** tránh push nhầm vào nhánh khác; luôn nêu rõ tên nhánh ở lần đầu.

## Bước 10 — Mở Pull Request và theo dõi CI

### `gh pr create ...`

```bash
gh pr create --base main --head feat/blog-terminal-production-cluster \
  --title "feat(blog): publish terminal production content cluster" \
  --body "Thêm cụm 3 bài về quy trình đưa blog lên production."
```

* **Làm gì:** tạo Pull Request từ dòng lệnh bằng [GitHub CLI](https://cli.github.com/manual/).
* **Vì sao dùng:** nhanh hơn mở trình duyệt; phù hợp khi đang làm việc trong terminal.
* **Tránh sai lầm:** tránh quên chọn đúng `--base`; PR phải nhắm vào `main` để đi qua pipeline chuẩn.

### `gh pr checks --watch`

```bash
gh pr checks --watch
```

* **Làm gì:** theo dõi trạng thái các check CI của PR theo thời gian thực.
* **Vì sao dùng:** để biết QA Gatekeeper xanh hay đỏ mà không cần F5 trình duyệt.
* **Tránh sai lầm:** tránh tưởng "push xong là xong" — production chỉ an toàn khi mọi check đã xanh.

## Vì sao trật tự các lệnh Git đưa blog lên production lại quan trọng

Thứ tự ở trên không ngẫu nhiên. Đồng bộ `main` trước để tránh stale base. Tạo nhánh riêng để giữ `main` sạch. Build và kiểm 404 trước khi push để không đẩy link chết. Staging có chủ đích để commit gọn. Cuối cùng mới mở PR và để CI làm trọng tài.

Nếu phải tóm trong một câu: **mỗi lệnh là một lớp kiểm tra**, và bỏ qua một lớp thường đồng nghĩa với việc bạn sẽ gặp lại lỗi đó ở lớp sau — chỉ là muộn hơn và khó sửa hơn. Theo [tài liệu chính thức của Git](https://git-scm.com/doc), phần lớn rắc rối của người mới đến từ việc không nắm rõ trạng thái của repo trước mỗi thao tác; các lệnh `status`, `diff` và `fetch` chính là để xóa bỏ sự mơ hồ đó.

## Kết luận

Toàn bộ quy trình này không yêu cầu công cụ đắt tiền hay kiến thức Git nâng cao. Nó chỉ cần kỷ luật: đồng bộ, tạo nhánh, kiểm tra local, build sạch, soi diff, staging có chủ đích, commit rõ ràng, push, mở PR, theo dõi check.

Nếu bạn muốn xem các lệnh này được đặt trong một quy trình hoàn chỉnh — kể cả khi không có trợ lý AI hỗ trợ — hãy đọc tiếp [viết blog bằng local terminal khi AI hết credit](/viet-blog-bang-local-terminal-khi-ai-het-credit/). Và để hiểu vì sao việc chạy QA trước khi push lại quý đến vậy, [case study fix QA Gatekeeper GitHub Actions](/fix-qa-gatekeeper-github-actions-merge-conflict-zola/) sẽ cho bạn một ví dụ rất thật.
