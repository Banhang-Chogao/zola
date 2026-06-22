+++
title = "Git stash, cherry-pick và reflog (nâng cao)"
description = "Git stash cất tạm thay đổi, cherry-pick chọn commit lẻ, reflog cứu commit tưởng đã mất. Series Git & GitHub — Bài 11/15 nâng cao."
date = 2026-06-18
aliases = ["/git-stash-cherry-pick-reflog-nang-cao/"]
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["git", "git github series", "git stash", "github", "lập trình"]
[extra]
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
seo_keyword = "git stash"
featured = false
series = "git-github"
series_part = 11
series_total = 15

[[extra.faq]]
q = "Git stash dùng để làm gì?"
a = "Git stash cất tạm các thay đổi chưa commit vào một ngăn riêng, trả working directory về sạch sẽ để bạn chuyển nhánh hay pull. Khi cần, bạn lấy lại bằng git stash pop. Rất hữu ích khi đang làm dở mà phải chuyển việc gấp."

[[extra.faq]]
q = "git cherry-pick là gì?"
a = "git cherry-pick sao chép một (hoặc vài) commit cụ thể từ nhánh này sang nhánh hiện tại, mà không gộp toàn bộ nhánh. Dùng khi bạn chỉ cần một bản vá lỗi cụ thể từ nhánh khác."

[[extra.faq]]
q = "git reflog có thể khôi phục commit đã mất không?"
a = "Có. git reflog ghi lại mọi nơi HEAD từng trỏ tới, kể cả sau reset cứng hay rebase. Nhờ đó bạn tìm lại mã băm của commit tưởng đã mất và khôi phục bằng git checkout hoặc git reset tới mã đó."
+++

> 📚 **Git & GitHub Series (Bài 11/15)** — Tiếp nối phần nâng cao sau [git rebase ở Bài 10](/git-rebase-lam-sach-lich-su-commit/), bài này giới thiệu ba "phao cứu sinh": **git stash**, cherry-pick và reflog.

**Git stash**, `cherry-pick` và `reflog` là ba công cụ không dùng mỗi ngày nhưng cứu bạn trong những tình huống ngặt nghèo: đang làm dở phải chuyển việc gấp, cần một commit lẻ từ nhánh khác, hay lỡ tay xóa mất commit quan trọng. Nắm chúng giúp bạn tự tin xử lý mọi sự cố mà không hoảng loạn.

<!-- more -->

## Git stash — cất tạm việc đang làm dở

Tình huống quen thuộc: bạn đang sửa dở một tính năng thì sếp nhờ fix gấp lỗi ở nhánh khác. Commit thì chưa xong, bỏ thì tiếc. Giải pháp là `git stash`:

```bash
git stash
```

Lệnh này cất mọi thay đổi chưa commit vào một ngăn tạm và trả working directory về sạch. Giờ bạn tự do chuyển nhánh. Khi quay lại:

```bash
git stash pop
```

Theo [tài liệu git stash](https://git-scm.com/docs/git-stash), bạn có thể cất nhiều "ngăn" cùng lúc.

### Các lệnh stash hữu ích

| Lệnh | Tác dụng |
|---|---|
| `git stash list` | Xem danh sách các stash đã cất |
| `git stash pop` | Lấy lại stash mới nhất và xóa nó khỏi danh sách |
| `git stash apply` | Lấy lại nhưng giữ stash trong danh sách |
| `git stash -u` | Cất cả file chưa được track |
| `git stash drop` | Xóa một stash |

## Git cherry-pick — chọn commit lẻ

Đôi khi bạn chỉ cần **một commit cụ thể** từ nhánh khác, không phải cả nhánh. Ví dụ một bản vá lỗi nằm trên nhánh `develop` mà bạn muốn đưa gấp vào `main`:

```bash
git switch main
git cherry-pick a1b2c3d
```

`a1b2c3d` là mã băm của commit (lấy từ `git log`). Git tạo một commit mới trên nhánh hiện tại với cùng nội dung thay đổi. Nếu gặp conflict, xử lý rồi `git cherry-pick --continue`.

Cherry-pick rất tiện cho hotfix, nhưng đừng lạm dụng — nếu sao chép quá nhiều commit, hãy cân nhắc merge hoặc rebase thay thế.

## Git reflog — cỗ máy thời gian cứu hộ

Đây là công cụ nhiều người không biết, nhưng đã cứu vô số lập trình viên. `git reflog` ghi lại **mọi vị trí HEAD từng đi qua** — kể cả sau `reset --hard`, rebase hỏng, hay xóa nhầm nhánh:

```bash
git reflog
```

Bạn sẽ thấy danh sách như:

```text
a1b2c3d HEAD@{0}: reset: moving to HEAD~3
e4f5g6h HEAD@{1}: commit: Thêm tính năng quan trọng
```

Thấy commit `e4f5g6h` tưởng đã mất? Khôi phục ngay:

```bash
git checkout e4f5g6h
git switch -c cuu-ho
```

Hoặc đưa nhánh về lại điểm đó bằng `git reset --hard e4f5g6h`. Reflog là lý do bạn gần như **không bao giờ thật sự mất commit** trong Git, miễn là chúng đã từng được commit.

## Một số tình huống thực tế

Để thấy ba công cụ này hữu ích thế nào, hãy xét vài kịch bản hay gặp khi làm việc thật:

- **Pull bị chặn vì có thay đổi chưa commit**: thay vì commit vội một mớ dở dang, hãy `git stash`, chạy `git pull`, rồi `git stash pop`. Working directory của bạn được giữ nguyên ý định ban đầu.
- **Sửa lỗi khẩn trên production**: bản vá đã được commit trên nhánh phát triển, nhưng bản chính cần ngay. Một lệnh `git cherry-pick` đưa đúng bản vá đó sang nhánh phát hành mà không kéo theo tính năng chưa hoàn thiện.
- **Lỡ tay `git reset --hard` mất hết commit hôm nay**: đừng hoảng. Mở `git reflog`, tìm mã băm trước khi reset, và đưa nhánh về đúng điểm đó. Mọi thứ trở lại như chưa có gì xảy ra.

Những tình huống này cho thấy Git được thiết kế để **tha thứ cho sai lầm** — gần như mọi thao tác đều có đường lùi, miễn là bạn đã commit.

## Khi nào dùng công cụ nào?

- **Đang làm dở, cần chuyển nhánh gấp** → `git stash`.
- **Cần đúng một commit từ nhánh khác** → `git cherry-pick`.
- **Lỡ reset/rebase, mất commit** → `git reflog` rồi khôi phục.

Ba công cụ này bổ trợ cho kỹ năng [reset và revert ở Bài 12](/git-reset-revert-khoi-phuc-su-co/), tạo thành bộ đồ nghề xử lý sự cố hoàn chỉnh.

## Tóm lại

**Git stash** cất tạm việc dang dở, `cherry-pick` nhặt đúng commit cần, còn `reflog` là tấm lưới an toàn cứu commit tưởng đã mất. Đây là những công cụ nâng cao giúp bạn bình tĩnh trước mọi tình huống — dấu hiệu của một người dùng Git trưởng thành.

Ở **Bài 12**, chúng ta học cách quay ngược thời gian có chủ đích với [git reset, revert và khôi phục sự cố](/git-reset-revert-khoi-phuc-su-co/).
