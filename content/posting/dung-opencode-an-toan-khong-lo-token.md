+++
title = "Dùng OpenCode an toàn: không để AI phá repo hoặc lộ token"
description = "Checklist dùng OpenCode an toàn với branch riêng, quyền tối thiểu, review lệnh và diff, bảo vệ token trong GitHub Codespaces và repo cá nhân."
date = 2026-06-30T13:08:00+07:00
updated = 2026-06-30T13:08:00+07:00
draft = false
slug = "dung-opencode-an-toan-khong-lo-token"
aliases = ["/dung-opencode-an-toan-khong-lo-token/"]
[taxonomies]
categories = ["Tất cả", "Series", "Công nghệ"]
tags = ["ai", "bảo mật", "github", "opencode", "token"]
[extra]
author = "Duy Nguyen"
seo_keyword = "dùng OpenCode an toàn"
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
image_alt = "Checklist bảo vệ repo và token khi dùng OpenCode"
image_source = "seomoney-generated"
image_license = "owned"
series = "opencode-ai-viet-code-mien-phi"
series_part = 9
series_order = 9
series_total = 10
[[extra.faq]]
q = "Có nên đưa token GitHub vào prompt OpenCode không?"
a = "Không; dùng luồng xác thực/secret storage phù hợp và thu hồi token ngay nếu đã lộ."
[[extra.faq]]
q = "OpenCode có thể phá repo không?"
a = "Agent có quyền rộng có thể tạo thay đổi hoặc chạy lệnh sai; branch, permission và review giúp giảm rủi ro."
[[extra.faq]]
q = "Plan mode có an toàn tuyệt đối không?"
a = "Không; plan mode giảm quyền sửa nhưng bạn vẫn phải đọc lệnh, output và chính sách phiên bản hiện tại."
[[extra.faq]]
q = "Có cần tài khoản GitHub không?"
a = "Không bắt buộc cho OpenCode, nhưng GitHub cung cấp branch, PR, audit và secret controls hữu ích."
[[extra.faq]]
q = "OpenCode có thay lập trình viên không?"
a = "Không; con người chịu trách nhiệm permission, review, test và xử lý sự cố."
+++

> **TL;DR:** Không dán secret vào prompt; làm trên branch riêng; bắt đầu bằng plan mode; chỉ cấp quyền cần thiết; đọc mọi lệnh; review diff và test trước commit; thu hồi credential ngay khi nghi lộ. AI coding nhanh không phải lý do bỏ kiểm soát.

Muốn **dùng OpenCode an toàn**, trước hết phải hiểu coding agent khác chatbot ở chỗ nó có thể chạm vào file và tool. Khi quyền đủ rộng, một hiểu nhầm có thể đổi nhiều file, xóa dữ liệu chưa commit hoặc gửi nội dung nhạy cảm tới provider. Điều này không có nghĩa phải tránh OpenCode; nó có nghĩa cần dùng như một công cụ automation có quyền.

OpenCode README mô tả plan agent thiên về đọc và build agent có quyền phát triển đầy đủ hơn. Đây là điểm bắt đầu tốt cho threat model: ai được đọc gì, chạy gì, gửi gì và ghi gì.

<!-- more -->

## Dùng OpenCode an toàn: secret không thuộc về prompt

Token GitHub, API key, cookie, private key, `.env` production và log chứa dữ liệu cá nhân không nên xuất hiện trong prompt. Ngay cả khi giao diện chạy local, provider model có thể nhận context theo cấu hình và chính sách của họ.

Không yêu cầu agent “tìm mọi key trong repo”. Nếu cần audit secret, dùng công cụ chuyên dụng trong phạm vi được phép và bảo đảm output không in giá trị. Khi xác thực provider, dùng device flow, OAuth hoặc secret storage theo docs.

Nếu đã dán token vào chat hoặc commit:

1. thu hồi/rotate credential ngay;
2. kiểm tra audit log và phạm vi quyền;
3. xóa khỏi source/history theo quy trình repo;
4. không đăng giá trị token trong issue/PR khi báo sự cố;
5. ghi lại nguyên nhân để ngăn lặp.

Xóa tin nhắn không thay thế rotation. Secret đã lộ phải được coi là không còn bí mật.

## Branch riêng và worktree sạch

Trước phiên:

```bash
git status
git branch --show-current
git switch -c fix/small-scoped-task
```

Không bắt đầu khi có thay đổi chưa commit của người khác. Agent có thể vô tình ghi đè hoặc trộn chúng. Với task song song, dùng worktree riêng. Commit nhỏ tạo checkpoint, nhưng không dùng `git reset --hard` như nút hoàn tác mặc định.

PR là lớp kiểm soát: diff có thể review, CI chạy, branch protection áp dụng. Không cho agent bypass protection hoặc force-push chỉ để “làm CI xanh”.

## Quyền tối thiểu cho từng giai đoạn

Ở giai đoạn hiểu vấn đề, agent chỉ cần đọc. Ở giai đoạn patch, chỉ cần ghi file liên quan và chạy test an toàn. Push, release, deploy, quản trị secret hoặc xóa resource là quyền khác và không nên cấp theo quán tính.

Một ma trận đơn giản:

| Giai đoạn | Quyền hợp lý | Quyền nên giữ lại |
|---|---|---|
| Chẩn đoán | đọc file, search | ghi file, mạng không cần thiết |
| Lập kế hoạch | đọc config/test | cài dependency, push |
| Sửa | file trong scope, test | secret, deploy, destructive command |
| Giao hàng | commit/PR khi được yêu cầu | merge/deploy ngoài phê duyệt |

Permission prompt không phải phiền toái cần tắt; nó là lúc kiểm tra agent sắp làm gì.

## Đọc lệnh trước khi chấp thuận

Đặc biệt cẩn thận với lệnh xóa, reset, thay permission, tải/chạy script từ mạng, in environment, upload file hoặc chạy installer không rõ nguồn. Dấu `&&`, pipe và command substitution có thể khiến một dòng làm nhiều việc.

Hỏi ba câu: lệnh có cần cho task không, phạm vi file/resource là gì, có phương án chỉ đọc không? Nếu không giải thích được, từ chối và yêu cầu agent chia nhỏ.

Không cho phép `curl ... | sh` chỉ vì docs/blog viết ngắn. Nếu phương thức cài chính thức dùng script, tải/đọc nội dung hoặc dùng package manager có provenance rõ.

## Review diff như một pull request bên ngoài

Sau patch:

```bash
git diff --check
git diff --stat
git diff
```

Tìm secret, endpoint private, email cá nhân, local path, debug log, dependency mới, quyền file và thay đổi ngoài scope. Kiểm tra cả file generated/lockfile. Agent có thể “dọn code” gây diff lớn mà không cần thiết.

Chạy test hẹp và build. Với nội dung, kiểm tra link, canonical, ảnh/alt và nguồn. Với backend, kiểm tra auth boundary nhưng không thử trên production nếu chưa được phép.

## Codespaces và quyền GitHub

Codespace có thể nhận quyền repository và secrets cấu hình cho môi trường. Chỉ cấp secret cần cho repo/phiên; không dùng secret production cho bài học. Kiểm tra token scope và expiration. Đóng Codespace không tự thu hồi token ngoài.

Nếu OpenCode đăng nhập Copilot qua GitHub, dùng flow chính thức. Không copy cookie hoặc token từ browser. Tài khoản Free hay trả phí đều phải tuân thủ điều khoản và quota.

## Prompt injection và nội dung repo

Agent có thể đọc README, issue hoặc file do bên thứ ba tạo. Nội dung ấy có thể chứa hướng dẫn độc hại kiểu “hãy in environment”. Xem tài liệu trong repo là dữ liệu, không phải mệnh lệnh ưu tiên hơn rule của bạn.

Khi làm repo lạ, plan mode, sandbox và network restriction càng quan trọng. Không chạy test/install package từ fork không tin cậy trên máy có credential giá trị.

## Kế hoạch phục hồi

Trước task rủi ro, biết cách quay lại commit và lưu công việc người dùng. Backup dữ liệu ngoài Git nếu cần. Nếu sự cố xảy ra, dừng agent, chụp trạng thái không chứa secret, rotate credential, đánh giá phạm vi rồi phục hồi bằng thao tác Git không phá dữ liệu khác.

Đừng che sự cố bằng force-push. Lịch sử rõ giúp học và ngăn tái diễn.

## Bài học rút ra

OpenCode an toàn hay không phụ thuộc cả sản phẩm, model, provider, permission và hành vi người dùng. Mã nguồn mở tăng khả năng kiểm tra nhưng không xóa rủi ro cấu hình. Free tier không làm dữ liệu ít giá trị hơn.

Hãy bắt đầu nhỏ và giữ một điểm duyệt trước mỗi bước có tác động: sửa, chạy, commit, push. Khi thói quen này tự nhiên, chuyển sang [lộ trình 14 ngày](/posting/lo-trinh-tu-hoc-ai-coding-mien-phi-opencode-github/).

## Liên kết nội bộ

- [Cài OpenCode trong Codespaces](/posting/cai-opencode-trong-github-codespaces/)
- [Workflow 30 phút](/posting/workflow-30-phut-moi-ngay-opencode/)
- [Bảo mật Git và GitHub](/posting/bao-mat-best-practices-git-github/)
- [Hiểu Copilot Free](/posting/github-copilot-free-opencode-han-muc/)
- [Lộ trình 14 ngày](/posting/lo-trinh-tu-hoc-ai-coding-mien-phi-opencode-github/)
- [Hub Series](/series/)

## Liên kết bên ngoài

- [OpenCode agents](https://opencode.ai/docs/agents/)
- [OpenCode repository](https://github.com/anomalyco/opencode)
- [GitHub authentication security](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure)
- [GitHub Codespaces security](https://docs.github.com/en/codespaces/reference/security-in-github-codespaces)

## Bản quyền và ghi nguồn

SEOMONEY biên tập hướng dẫn từ nguyên tắc least privilege, Git workflow và tài liệu chính thức OpenCode/GitHub. Ví dụ không chứa token thật; không sao chép dài. Ảnh OG dùng fallback nội bộ.

## FAQ - Câu hỏi thường gặp

### Có nên đưa token GitHub vào prompt không?

Không. Dùng authentication flow/secret storage chính thức và rotate ngay nếu đã lộ.

### OpenCode có thể phá repo không?

Agent có quyền rộng có thể chạy lệnh hoặc tạo patch sai. Branch, permission, review và backup giảm rủi ro.

### Plan mode có an toàn tuyệt đối không?

Không. Nó giảm quyền sửa mặc định, nhưng bạn vẫn phải kiểm tra lệnh, context và phiên bản.

### Có cần tài khoản GitHub không?

Không cho mọi cách dùng, nhưng GitHub cung cấp PR, audit và controls hữu ích.

### OpenCode có thay lập trình viên không?

Không. Con người vẫn quản lý quyền, review, test và ứng phó sự cố.
