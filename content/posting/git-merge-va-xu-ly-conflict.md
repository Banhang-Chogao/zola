+++
title = "Git merge và cách xử lý conflict khi gộp nhánh"
description = "Git merge là gì, fast-forward vs merge commit, và cách xử lý conflict từng bước khi gộp nhánh. Series Git & GitHub — Bài 5/15."
date = 2026-06-18
aliases = ["/git-merge-va-xu-ly-conflict/"]
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["git", "git github series", "git merge", "github", "lập trình"]
[extra]
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
seo_keyword = "git merge"
featured = false
series = "git-github"
series_part = 5
series_total = 15

[[extra.faq]]
q = "Git merge là gì?"
a = "Git merge là thao tác gộp lịch sử của một nhánh vào nhánh hiện tại. Nếu hai nhánh không sửa cùng chỗ, Git tự gộp; nếu trùng chỗ và mâu thuẫn, Git báo conflict để bạn giải quyết thủ công."

[[extra.faq]]
q = "Conflict trong Git xảy ra khi nào?"
a = "Conflict xảy ra khi hai nhánh cùng sửa một dòng (hoặc một bên sửa, một bên xóa) cùng một file, khiến Git không tự quyết được nên giữ bản nào. Bạn phải mở file, chọn nội dung đúng, rồi add và commit."

[[extra.faq]]
q = "Fast-forward merge khác merge commit thế nào?"
a = "Fast-forward xảy ra khi nhánh đích không có commit mới nào — Git chỉ dời con trỏ tới trước, không tạo commit gộp. Merge commit được tạo khi cả hai nhánh đều có commit mới, ghi lại điểm hợp nhất."
+++

> 📚 **Git & GitHub Series (Bài 5/15)** — Đã biết tạo nhánh ở [Bài 4 về git branch](/zola/posting/git-branch-lam-viec-voi-nhanh/), giờ ta học cách gộp chúng lại bằng **git merge** và xử lý xung đột.

**Git merge** là thao tác đưa công sức từ một nhánh trở lại nhánh chính. Phần lớn thời gian Git gộp tự động trơn tru, nhưng đôi khi bạn sẽ gặp **conflict** — và đây chính là lúc nhiều người mới hoảng sợ. Tin tốt: conflict hoàn toàn bình thường và có quy trình rõ ràng để giải quyết. Bài này hướng dẫn cả hai trường hợp, từng bước.

<!-- more -->

## Cơ chế của git merge

Khi bạn đứng ở nhánh `main` và chạy `git merge tinh-nang`, Git sẽ đưa các commit của `tinh-nang` vào `main`. Theo [tài liệu Git chính thức](https://git-scm.com/docs/git-merge), có hai kịch bản chính:

- **Fast-forward**: `main` chưa có commit mới nào kể từ khi tách nhánh → Git chỉ cần dời con trỏ `main` tới trước. Không tạo commit gộp.
- **Three-way merge**: cả hai nhánh đều có commit mới → Git tạo một **merge commit** mới hợp nhất hai dòng lịch sử.

## Thực hành merge cơ bản

```bash
git switch main
git merge tinh-nang
```

Nếu thành công, Git in ra số file thay đổi. Trong trường hợp fast-forward, bạn có thể ép tạo merge commit để giữ dấu vết nhánh:

```bash
git merge --no-ff tinh-nang
```

Nhiều nhóm thích `--no-ff` vì lịch sử thể hiện rõ "tính năng này được gộp ở đây".

## Khi nào xảy ra conflict?

Conflict xảy ra khi hai nhánh **cùng sửa một vùng** của cùng một file theo cách mâu thuẫn. Git không thể đoán bạn muốn giữ bản nào, nên dừng lại và nhờ bạn quyết định. Đây không phải lỗi — chỉ là Git đang thận trọng.

Khi merge gặp conflict, Git báo:

```
Auto-merging trang-chu.html
CONFLICT (content): Merge conflict in trang-chu.html
Automatic merge failed; fix conflicts and then commit the result.
```

## Đọc dấu hiệu conflict trong file

Mở file bị conflict, bạn sẽ thấy các "dấu phân cách" do Git chèn vào:

```text
  <<<<<<< HEAD
  Tiêu đề từ nhánh main
  =======
  Tiêu đề từ nhánh tính năng
  >>>>>>> tinh-nang
```

*(Trong file thật các dấu này nằm sát lề trái; ở đây thụt vào cho dễ đọc.)* Ý nghĩa:

- Phần giữa dấu mở `<<<<<<< HEAD` và dấu ngăn `=======` là nội dung **nhánh hiện tại** (main).
- Phần giữa dấu ngăn và dấu đóng `>>>>>>> tinh-nang` là nội dung **nhánh đang gộp vào**.

## Quy trình xử lý conflict từng bước

1. Chạy `git status` để xem file nào đang conflict.
2. Mở từng file, tìm các khối `<<<<<<<` / `=======` / `>>>>>>>`.
3. **Quyết định nội dung cuối cùng**: giữ một bên, giữ cả hai, hay viết lại hoàn toàn.
4. **Xóa hết** các dòng dấu phân cách `<<<<<<<`, `=======`, `>>>>>>>`.
5. `git add <file>` để đánh dấu đã giải quyết.
6. `git commit` để hoàn tất merge (Git tự soạn sẵn thông điệp).

Trên blog này, hệ thống tự động còn có cả [bot tự sửa conflict](/zola/posting/qa-gatekeeper-tu-fix-loi-blog/) cho các trường hợp đơn giản, nhưng hiểu quy trình thủ công vẫn là kỹ năng nền tảng.

## Công cụ hỗ trợ và hủy merge

- `git merge --abort` — hủy toàn bộ merge, quay về trạng thái trước khi gộp. Rất hữu ích khi bạn lỡ tay và muốn làm lại.
- `git mergetool` — mở công cụ trực quan (VS Code, Meld…) để giải quyết conflict dễ hơn.
- VS Code hiển thị nút "Accept Current / Accept Incoming / Accept Both" ngay trên vùng conflict — thân thiện cho người mới.

## Mẹo giảm conflict

| Thói quen | Lợi ích |
|---|---|
| Merge `main` vào nhánh tính năng thường xuyên | Conflict nhỏ, dễ xử lý hơn để dồn cuối |
| Nhánh sống ngắn, gộp sớm | Ít cơ hội đụng độ |
| Chia commit nhỏ, rõ ràng | Dễ thấy bên nào sửa gì |
| Thống nhất format code trong nhóm | Tránh conflict do định dạng |

## Tóm lại

**Git merge** gộp công sức giữa các nhánh; phần lớn tự động, và khi gặp **conflict** bạn chỉ cần bình tĩnh: mở file, chọn nội dung đúng, xóa dấu phân cách, rồi `add` và `commit`. Conflict là phần bình thường của làm việc nhóm, không phải dấu hiệu bạn làm sai.

Ở **Bài 6**, chúng ta đưa Git ra khỏi máy cá nhân: [làm việc với repository từ xa qua git remote](/zola/posting/git-remote-lam-viec-voi-repository-tu-xa/) — bước đệm trước khi lên GitHub ở Bài 7.
