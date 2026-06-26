+++
title = "Git là gì? Version control cho người mới bắt đầu"
description = "Git là gì, version control hoạt động ra sao và vì sao mọi lập trình viên đều cần Git? Series Git & GitHub — Bài 1/15, giải thích từ con số 0."
date = 2026-06-18
aliases = ["/git-la-gi-version-control-cho-nguoi-moi/"]
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["git", "git github series", "github", "lập trình", "version control"]
[extra]
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
seo_keyword = "git là gì"
featured = false
series = "git-github"
series_part = 1
series_total = 15

[[extra.faq]]
q = "Git là gì?"
a = "Git là hệ thống quản lý phiên bản phân tán (distributed version control system) ghi lại mọi thay đổi của mã nguồn theo thời gian, cho phép bạn xem lại lịch sử, quay về phiên bản cũ và làm việc nhóm mà không ghi đè lên nhau."

[[extra.faq]]
q = "Git và GitHub khác nhau thế nào?"
a = "Git là phần mềm chạy trên máy bạn để quản lý phiên bản. GitHub là dịch vụ trực tuyến lưu trữ repository Git trên đám mây, thêm các tính năng cộng tác như Pull Request, Issues và CI/CD. Bạn có thể dùng Git mà không cần GitHub, nhưng không thể dùng GitHub mà không có Git."

[[extra.faq]]
q = "Người mới có cần học Git ngay không?"
a = "Có. Git là kỹ năng nền tảng cho mọi lập trình viên, kể cả người làm việc một mình, vì nó giúp lưu lịch sử an toàn và khôi phục khi lỗi. Học Git sớm tiết kiệm rất nhiều thời gian về sau."
+++

> 📚 **Git & GitHub Series (Bài 1/15)** — Đây là bài mở màn của loạt 15 bài đưa bạn từ con số 0 đến mức nâng cao với Git và [GitHub](https://github.com) — nền tảng quản lý phiên bản phổ biến nhất thế giới.

**Git là gì?** Nói ngắn gọn: Git là một hệ thống **quản lý phiên bản** (version control) ghi lại mọi thay đổi trong mã nguồn của bạn theo thời gian, để bạn có thể xem lại, so sánh và quay về bất kỳ phiên bản nào trong quá khứ. Nếu bạn từng lưu file kiểu `baocao_final.doc`, `baocao_final_v2.doc`, `baocao_final_thật.doc` — thì Git chính là cách làm điều đó một cách chuyên nghiệp, gọn gàng và an toàn. Bài này giải thích Git từ đầu cho người chưa biết gì về lập trình lẫn dòng lệnh.

<!-- more -->

## Git là gì — định nghĩa dễ hiểu

Git được Linus Torvalds (cha đẻ của Linux) tạo ra năm 2005 để quản lý chính mã nguồn nhân Linux. Về bản chất, Git là một **hệ thống quản lý phiên bản phân tán** (Distributed Version Control System — DVCS).

Hãy tưởng tượng Git như một chiếc **máy quay thời gian cho thư mục dự án của bạn**:

- Mỗi khi bạn hoàn thành một phần việc, bạn chụp lại một "ảnh chụp" (snapshot) của toàn bộ dự án — gọi là **commit**.
- Mỗi commit được ghi nhãn thời gian, người tạo và một dòng mô tả.
- Bất cứ lúc nào bạn cũng có thể tua ngược về một commit cũ, so sánh hai commit, hoặc tạo một nhánh thời gian song song để thử nghiệm.

Khác với việc lưu file thủ công, Git lưu **toàn bộ lịch sử** một cách hiệu quả: nó chỉ ghi lại phần thay đổi, nén dữ liệu, và đảm bảo tính toàn vẹn bằng mã băm SHA.

## Vì sao "phân tán" lại quan trọng?

Trước Git, các công cụ như SVN hay CVS dùng mô hình **tập trung** (centralized): chỉ có một kho duy nhất trên server, ai cũng phải kết nối tới đó.

Git thì khác — nó **phân tán**:

- Mỗi người clone repository về máy sẽ có **bản sao đầy đủ** của toàn bộ lịch sử.
- Bạn có thể commit, xem log, tạo nhánh **hoàn toàn offline**, không cần mạng.
- Nếu server trung tâm hỏng, bất kỳ bản sao nào trên máy cộng tác viên cũng đủ để khôi phục.

Đây là lý do Git nhanh, an toàn và phù hợp với cả nhóm phân tán toàn cầu lẫn lập trình viên làm việc một mình.

## Git giải quyết vấn đề gì?

Hãy xem bảng so sánh giữa cách làm thủ công và dùng Git:

| Vấn đề | Không dùng Git | Dùng Git |
|---|---|---|
| Lưu lịch sử thay đổi | Copy folder, đặt tên v1, v2… | Mỗi commit là một mốc lịch sử |
| Quay về bản cũ | Tìm thủ công, dễ nhầm | `git checkout` / `git revert` trong vài giây |
| Làm việc nhóm | Gửi file qua email, ghi đè nhau | Merge tự động, phát hiện xung đột |
| Thử tính năng mới | Sợ làm hỏng bản chính | Tạo nhánh riêng, thử thoải mái |
| Biết ai sửa dòng nào | Không thể | `git blame` chỉ rõ từng dòng |

Với một blog tĩnh như blog này — được [tạo bằng Zola](/zola/posting/tao-blog-voi-zola/) và [tự động deploy bằng GitHub Actions](/zola/posting/tu-dong-deploy-zola-github-actions/) — Git chính là xương sống: mỗi bài viết, mỗi sửa đổi giao diện đều là một commit, mỗi tính năng là một nhánh.

## Ba khái niệm cốt lõi bạn sẽ gặp

Để không bị ngợp, bạn chỉ cần nắm ba khái niệm nền tảng trước:

1. **Repository (repo)** — thư mục dự án được Git theo dõi. Khi bạn chạy `git init`, một thư mục ẩn `.git` được tạo ra để lưu toàn bộ lịch sử.
2. **Commit** — một "ảnh chụp" của dự án tại một thời điểm, kèm thông điệp mô tả. Đây là đơn vị cơ bản của lịch sử Git.
3. **Branch (nhánh)** — một dòng thời gian song song. Nhánh mặc định thường tên `main`. Bạn tạo nhánh mới để phát triển tính năng mà không ảnh hưởng bản chính.

Ba khái niệm này sẽ được đào sâu ở các bài sau trong series.

## Ba trạng thái của file trong Git

Một điểm khiến người mới bối rối là Git có **ba khu vực** mà file di chuyển qua lại:

- **Working Directory** — thư mục làm việc thực tế, nơi bạn sửa file.
- **Staging Area (Index)** — khu vực "chuẩn bị", nơi bạn chọn những thay đổi sẽ đưa vào commit tiếp theo bằng `git add`.
- **Repository** — nơi commit được lưu vĩnh viễn bằng `git commit`.

Luồng cơ bản luôn là: **sửa file → `git add` → `git commit`**. Hiểu mô hình ba khu vực này là chìa khóa để không lúng túng khi mới học. Chúng ta sẽ thực hành kỹ ở [Bài 3 về các lệnh Git cơ bản](/zola/posting/lenh-git-co-ban-init-add-commit-status/).

## Git khác GitHub thế nào?

Đây là nhầm lẫn phổ biến nhất của người mới:

- **Git** là phần mềm dòng lệnh chạy trên máy bạn, miễn phí và mã nguồn mở.
- **GitHub** là một **dịch vụ trực tuyến** lưu trữ các repository Git trên đám mây, do Microsoft sở hữu. Ngoài việc lưu trữ, GitHub bổ sung Pull Request, Issues, review code, Actions (CI/CD), wiki…

Nói cách khác: Git là động cơ, GitHub là một trong nhiều "garage" để gửi xe và cộng tác (bên cạnh GitLab, Bitbucket…). Chúng ta sẽ tìm hiểu GitHub kỹ từ [Bài 7](/zola/posting/github-la-gi-tao-repository-dau-tien/).

## Lộ trình 15 bài của series

Series này được thiết kế đi từ dễ đến khó:

- **Bài 1** (bài này): Git là gì, version control & các khái niệm nền.
- **Bài 2**: [Cài đặt Git và cấu hình lần đầu](/zola/posting/cai-dat-git-cau-hinh-lan-dau/).
- **Bài 3**: [Các lệnh cơ bản: init, add, commit, status, log](/zola/posting/lenh-git-co-ban-init-add-commit-status/).
- **Bài 4–6**: Branch, merge & conflict, remote.
- **Bài 7–9**: GitHub, push/pull/fetch, Pull Request.
- **Bài 10–12**: Nâng cao — rebase, stash/cherry-pick/reflog, reset/revert.
- **Bài 13–15**: Workflow chuyên nghiệp, GitHub Actions CI/CD, bảo mật & best practices.

## Cần chuẩn bị gì trước khi bắt đầu?

Tin tốt: gần như không cần gì ngoài một chiếc máy tính. Ở Bài 2 chúng ta sẽ cài Git. Trước đó, bạn chỉ cần làm quen tâm lý rằng Git chủ yếu dùng qua **dòng lệnh (terminal)** — và điều đó hoàn toàn không đáng sợ. Sau vài lệnh đầu tiên, bạn sẽ thấy nó nhanh và rõ ràng hơn nhiều so với kéo thả file.

## Tóm lại

**Git là gì?** — Là hệ thống quản lý phiên bản phân tán giúp bạn lưu lại lịch sử mã nguồn, quay về bất kỳ thời điểm nào, và cộng tác nhóm an toàn. Nó là kỹ năng nền tảng mà mọi lập trình viên — kể cả người viết blog tĩnh hay làm dự án cá nhân — đều nên nắm vững.

Hẹn gặp lại ở **Bài 2: Cài đặt Git và cấu hình lần đầu**, nơi chúng ta sẽ cài Git trên Windows, macOS và Linux, rồi thiết lập tên và email để commit đầu tiên của bạn được ghi nhận đúng.
