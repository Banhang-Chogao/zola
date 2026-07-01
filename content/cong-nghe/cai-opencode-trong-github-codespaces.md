+++
title = "Cài OpenCode trong GitHub Codespaces để viết code bằng AI"
description = "Hướng dẫn cài OpenCode trong GitHub Codespaces, kết nối model hợp lệ, khởi tạo rule và sửa code bằng AI trên branch riêng an toàn."
date = 2026-06-30T13:02:00+07:00
updated = 2026-06-30T13:02:00+07:00
draft = false
slug = "cai-opencode-trong-github-codespaces"
aliases = ["/cai-opencode-trong-github-codespaces/",
  "/posting/cai-opencode-trong-github-codespaces/"
]

[taxonomies]
categories = ["Tất cả", "Series", "Công nghệ"]
tags = ["ai", "codespaces", "github", "hướng dẫn", "opencode"]
[extra]
author = "Duy Nguyen"
seo_keyword = "OpenCode trong GitHub Codespaces"
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
image_alt = "Các bước cài OpenCode trong một GitHub Codespace"
image_source = "seomoney-generated"
image_license = "owned"
series = "opencode-ai-viet-code-mien-phi"
series_part = 3
series_order = 3
series_total = 10

[[extra.faq]]
q = "OpenCode có cài được trong GitHub Codespaces không?"
a = "Có, Codespaces cung cấp terminal Linux trong repo nên có thể dùng phương thức cài chính thức phù hợp với môi trường."
[[extra.faq]]
q = "Có cần tài khoản GitHub không?"
a = "Có, bạn cần tài khoản GitHub và quyền mở Codespace cho repo muốn sử dụng."
[[extra.faq]]
q = "Có nên dán token vào chat OpenCode không?"
a = "Không. Hãy dùng cơ chế xác thực của provider hoặc secret storage phù hợp và không đưa token vào prompt, file hay log."
[[extra.faq]]
q = "GitHub Copilot Free có đủ để học không?"
a = "Có thể đủ cho các task nhỏ nếu bạn lập kế hoạch và tiết kiệm request trong hạn mức tháng."
[[extra.faq]]
q = "Làm sao tránh OpenCode sửa nhầm branch chính?"
a = "Tạo branch riêng trước phiên làm việc, kiểm tra git status và chỉ commit sau khi review diff cùng test."
[[extra.references_external]]
title = "Repository OpenCode"
url = "https://github.com/anomalyco/opencode"

[[extra.references_external]]
title = "Tài liệu GitHub Codespaces"
url = "https://docs.github.com/en/codespaces"

[[extra.references_external]]
title = "Các gói GitHub Copilot"
url = "https://github.com/features/copilot/plans"

+++

> **TL;DR:** Mở Codespace từ repo cá nhân, tạo branch mới, cài OpenCode bằng phương thức chính thức, xác thực provider mà không dán token vào chat, bắt đầu bằng plan mode rồi review diff và build trước khi commit.

GitHub Codespaces phù hợp với người không muốn cài môi trường phát triển trên máy cá nhân. Chạy **OpenCode trong GitHub Codespaces** nghĩa là dùng agent ngay trong môi trường cloud gắn với repo: có terminal, editor, Git và runtime theo cấu hình dự án. Vì OpenCode có giao diện terminal, hai công cụ ghép với nhau khá tự nhiên.

Điều cần nhớ là Codespace không phải hộp thử vô hại. Nó vẫn có quyền với repo và có thể chứa secret được cấp cho môi trường. Cài một **AI coding agent miễn phí** không có nghĩa bạn nên cho agent chạy mọi lệnh. Hướng dẫn này ưu tiên quy trình quan sát được thay vì “auto-approve cho nhanh”.

<!-- more -->

## Chuẩn bị OpenCode trong GitHub Codespaces

Chọn repo cá nhân nhỏ mà bạn có quyền tạo branch. Repo nên có README mô tả cách chạy và ít nhất một lệnh kiểm tra như test, lint hoặc build. Nếu chưa có, một trang HTML/CSS đơn giản cũng được; mục tiêu đầu tiên là học vòng lặp, không phải dựng sản phẩm lớn.

Trên GitHub, mở repo, chọn **Code → Codespaces → Create codespace**. Tên nút có thể thay đổi theo giao diện. Khi editor mở, chạy các lệnh chỉ đọc:

```bash
pwd
git status
git branch --show-current
```

Đọc output và chắc chắn bạn đang ở đúng repo. Sau đó tạo branch:

```bash
git switch -c learn/opencode-first-task
```

Branch riêng là hàng rào đầu tiên. Nó không ngăn lộ secret, nhưng giúp tách patch và quay lại dễ hơn. Không giao agent làm việc khi `git status` đang có thay đổi bạn chưa hiểu.

## Cài OpenCode từ nguồn chính thức

README chính thức liệt kê nhiều cách cài, gồm install script, npm, Homebrew và package manager khác. Codespaces thường có Node.js, nên npm là lựa chọn dễ kiểm tra:

```bash
npm install -g opencode-ai@latest
opencode --version
```

Phiên bản và package có thể đổi. Trước khi chạy, đối chiếu với [tài liệu cài đặt OpenCode](https://opencode.ai/docs/) và repository chính thức. Không copy script từ blog lạ, gist không rõ chủ sở hữu hoặc comment mạng xã hội. Nếu dùng install script, hãy đọc nguồn và hiểu nó ghi binary vào đâu.

Một dự án có devcontainer quản lý chặt có thể không cho cài global. Khi đó, chọn phương thức được repo chấp nhận thay vì dùng `sudo` tùy tiện. Không thêm OpenCode vào dependency production chỉ để tiện một phiên phát triển nếu team chưa đồng ý.

## Kết nối GitHub Copilot hoặc provider

Website OpenCode cho biết người dùng có thể đăng nhập GitHub để sử dụng tài khoản Copilot và có thể kết nối nhiều provider. Hãy làm theo luồng xác thực mà OpenCode hiển thị và tài liệu provider hiện hành. Không chép access token vào prompt kiểu:

```text
Token của tôi là [ĐÃ ẨN], hãy cấu hình giúp.
```

Đó là anti-pattern. Prompt có thể được gửi tới model, xuất hiện trong history hoặc log. Nếu provider yêu cầu API key, dùng biến môi trường/secret mechanism được tài liệu hướng dẫn, đặt quyền tối thiểu và không commit file chứa key. GitHub Codespaces có cơ chế secrets riêng; agent không cần đọc giá trị để bạn xác thực dịch vụ.

Với Copilot Free, quota hiện được GitHub trình bày theo tháng. Bài [hiểu đúng hạn mức Copilot Free](/posting/github-copilot-free-opencode-han-muc/) giải thích cách không lãng phí request.

## Khởi tạo rule cho repo

OpenCode có cơ chế cấu hình/rule theo tài liệu từng phiên bản. Đừng để agent tự bịa quy ước. Trước khi init, hãy đọc README, CONTRIBUTING, package scripts và workflow kiểm tra. Rule ngắn nên nói rõ:

- ngôn ngữ và formatter đang dùng;
- lệnh test/build hợp lệ;
- file hoặc thư mục không được sửa;
- cấm đọc/in secret;
- không cài dependency nếu chưa được chấp thuận;
- luôn báo danh sách file dự kiến thay đổi;
- không commit hoặc push khi chưa có yêu cầu.

Nếu repo đã có `AGENTS.md`, `CLAUDE.md` hay tài liệu tương đương, ưu tiên dùng convention sẵn có. Không tạo nhiều file rule trùng nhau. Rule không thay thế sandbox hay permission; nó chỉ là chỉ dẫn cho agent.

## Chạy task đầu tiên bằng plan mode

README OpenCode mô tả plan agent ở chế độ thiên về đọc, không sửa file mặc định và hỏi trước khi chạy bash. Hãy bắt đầu tại đây:

```text
Đọc README và file liên quan đến trang About. Không sửa code.
Tìm một lỗi accessibility nhỏ, giải thích bằng tiếng Việt,
đưa patch tối thiểu và lệnh kiểm tra.
```

Bạn nên kiểm tra từng đường dẫn agent nhắc tới. Nếu kế hoạch hợp lý, chuyển sang build mode hoặc cho phép sửa đúng file. Sau patch:

```bash
git diff --check
git diff
```

Chạy lệnh test/build của repo, không phải lệnh agent tự nghĩ ra. Với Zola có thể là `zola build`; với Node có thể là script trong `package.json`. Nếu build cần secret production, dừng lại và chọn kiểm tra local an toàn hơn.

## Tạo commit và pull request có thể review

Một commit tốt chứa một mục đích. Đọc `git diff --stat`, sau đó đọc diff đầy đủ. Tìm các dấu hiệu: file lạ bị sửa, dependency lock thay đổi, đoạn debug còn sót, URL cũ, secret hoặc dữ liệu cá nhân.

Khi mọi thứ đúng:

```bash
git add path/to/file
git commit -m "fix: improve about page accessibility"
git push -u origin learn/opencode-first-task
```

Mở PR, ghi nguyên nhân, thay đổi, cách test và giới hạn còn lại. Đừng ghi “AI generated” như một cách miễn trách nhiệm. Người mở PR vẫn là người chịu trách nhiệm nội dung.

## Các lỗi người mới thường gặp

**Cài nhầm package:** luôn kiểm tra tên package và link từ repository chính thức. **Chạy ở sai thư mục:** xem `pwd` và `git status`. **Làm trên main:** tạo branch trước. **Dán token vào chat:** thu hồi token nếu đã lộ và chuyển sang secret mechanism. **Prompt quá rộng:** giảm xuống một bug. **Tin build xanh tuyệt đối:** kiểm tra hành vi thật.

Codespaces cũng có chi phí/hạn mức riêng theo tài khoản GitHub. Đóng Codespace khi không dùng và xem chính sách hiện tại; bài này không khẳng định một quota cố định vì GitHub có thể thay đổi.

## Kinh nghiệm thực tế

Điểm mạnh của Codespaces là tính lặp lại. Nếu agent làm môi trường rối, bạn có thể xem diff hoặc tạo lại Codespace từ repo sạch. Nhưng đừng dựa vào khả năng tạo lại để bỏ qua bảo mật. Secret bị gửi ra ngoài không thể “reset” bằng cách xóa máy ảo.

Task tốt nhất cho buổi đầu là sửa tài liệu, test nhỏ hoặc lỗi CSS cô lập. Sau khi quen vòng lặp plan → patch → test → diff → PR, bạn mới tăng phạm vi. Bài [workflow 30 phút mỗi ngày](/posting/workflow-30-phut-moi-ngay-opencode/) biến quy trình này thành thói quen.
