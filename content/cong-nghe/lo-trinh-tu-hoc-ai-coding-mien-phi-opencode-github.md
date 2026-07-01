+++
title = "Lộ trình 14 ngày tự học AI coding miễn phí với OpenCode"
description = "Lộ trình 14 ngày học AI coding miễn phí bằng OpenCode và GitHub, từ cài đặt, prompt, sửa bug, test, PR đến bảo mật và đánh giá chi phí."
date = 2026-06-30T13:09:00+07:00
updated = 2026-06-30T13:09:00+07:00
draft = false
slug = "lo-trinh-tu-hoc-ai-coding-mien-phi-opencode-github"
aliases = ["/lo-trinh-tu-hoc-ai-coding-mien-phi-opencode-github/",
  "/posting/lo-trinh-tu-hoc-ai-coding-mien-phi-opencode-github/"
]
[taxonomies]
categories = ["Tất cả", "Series", "Công nghệ"]
tags = ["ai", "ai coding", "github", "lộ trình học", "opencode"]
[extra]
author = "Duy Nguyen"
seo_keyword = "AI coding miễn phí với OpenCode"
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
image_alt = "Lộ trình 14 ngày học AI coding với OpenCode và GitHub"
image_source = "seomoney-generated"
image_license = "owned"
series = "opencode-ai-viet-code-mien-phi"
series_part = 10
series_order = 10
series_total = 10
[[extra.faq]]
q = "OpenCode có miễn phí không?"
a = "Lõi là open-source; lộ trình dùng free tier hợp lệ nhưng model/provider có thể có quota hoặc phí."
[[extra.faq]]
q = "Có cần biết code trước không?"
a = "Không cần chuyên sâu, nhưng phải học Git, đọc diff và kiểm tra kết quả thay vì giao hết cho AI."
[[extra.faq]]
q = "Copilot Free có đủ cho 14 ngày không?"
a = "Có thể đủ nếu mỗi ngày làm task nhỏ; hạn mức là theo tháng và phụ thuộc cách tính hiện hành."
[[extra.faq]]
q = "OpenCode có thay lập trình viên không?"
a = "Không; lộ trình tập trung dùng agent để học và tăng tốc dưới sự kiểm soát con người."
[[extra.faq]]
q = "Sau 14 ngày nên trả phí không?"
a = "Chỉ cân nhắc khi nhật ký usage cho thấy quota/reliability thực sự cản trở workload."
[[extra.references_external]]
title = "OpenCode"
url = "https://opencode.ai/"

[[extra.references_external]]
title = "Tài liệu OpenCode"
url = "https://opencode.ai/docs/"

[[extra.references_external]]
title = "Repository OpenCode"
url = "https://github.com/anomalyco/opencode"

[[extra.references_external]]
title = "GitHub Copilot plans"
url = "https://github.com/features/copilot/plans"

[[extra.references_external]]
title = "GitHub Codespaces"
url = "https://docs.github.com/en/codespaces"

+++

> **TL;DR:** Trong 14 ngày, bạn đi từ repo sạch và plan mode tới một PR nhỏ có test, rồi học bảo mật, so sánh tool và đánh giá business model. Mỗi ngày 20–30 phút; mục tiêu là hiểu diff và quy trình, không phải tạo thật nhiều code.

Lộ trình này dành cho blogger, indie hacker và người không chuyên code muốn học **AI coding miễn phí với OpenCode** mà không lao ngay vào dự án lớn. Bạn cần tài khoản GitHub, repo cá nhân và một free tier hợp lệ như Copilot Free hoặc model được OpenCode hỗ trợ tại thời điểm dùng.

Đừng hiểu “14 ngày” như cam kết thành lập trình viên. Sau hai tuần, kết quả hợp lý là bạn biết giao task nhỏ, giữ repo sạch, review patch, chạy test và nhận ra lúc nào agent không đáng tin.

<!-- more -->

## AI coding miễn phí với OpenCode: chuẩn bị trước ngày 1

Chọn repo không chứa dữ liệu nhạy cảm. Viết mục tiêu: sửa một bug nhỏ hoặc cải thiện một tính năng đơn giản. Xác định lệnh build/test. Đọc [bài mở đầu series](/posting/ai-viet-code-mien-phi-github-opencode/) và [hướng dẫn an toàn](/posting/dung-opencode-an-toan-khong-lo-token/).

Tạo nhật ký với bốn cột: task, prompt, kết quả, điều học được. Không ghi token, email riêng hay log nhạy cảm.

## Ngày 1: hiểu OpenCode

Đọc [OpenCode là gì](/posting/opencode-la-gi-ai-coding-agent/) và docs chính thức. Phân biệt OpenCode (agent), GitHub (repo/workflow) và provider/model (inference). Cài từ nguồn chính thức, kiểm tra version; chưa giao quyền sửa.

**Đầu ra:** bạn giải thích được ba lớp bằng lời của mình.

## Ngày 2: repo, branch và status

Mở repo, chạy `git status`, `git branch --show-current`, tạo branch `learn/opencode-14-days`. Đọc README và scripts. Không dùng agent nếu worktree có thay đổi không rõ.

**Đầu ra:** branch riêng sạch và danh sách lệnh test/build.

## Ngày 3: Codespaces hoặc môi trường local

Nếu không muốn cài local, làm theo [hướng dẫn Codespaces](/posting/cai-opencode-trong-github-codespaces/). Kiểm tra secret scope, không dán token vào chat. Nếu dùng local, bảo đảm project chạy trước khi thêm agent.

**Đầu ra:** môi trường build được baseline hiện tại.

## Ngày 4: prompt chỉ đọc

Yêu cầu plan mode giải thích một module nhỏ:

```text
Đọc file X và test liên quan. Không sửa code.
Giải thích luồng dữ liệu, hai edge case và lệnh test.
```

Đối chiếu từng claim với code. Ghi một điểm agent đúng và một điểm thiếu.

## Ngày 5: tái hiện bug

Chọn issue nhỏ. Tự viết bước reproduction trước khi hỏi AI. Nhờ agent đề xuất test nhưng chưa sửa implementation. Test phải fail vì bug, không phải vì setup.

**Đầu ra:** reproduction hoặc unit test thể hiện vấn đề.

## Ngày 6: patch tối thiểu

Cho agent sửa đúng phạm vi đã duyệt. Không thêm dependency. Đọc `git diff --stat` và `git diff`. Nếu không giải thích được một dòng, hỏi hoặc bỏ patch.

**Đầu ra:** patch nhỏ làm test mục tiêu pass.

## Ngày 7: build và review như người lạ

Chạy test hẹp, formatter và build. Kiểm tra regression, accessibility hoặc mobile nếu liên quan. Tìm debug log, domain cũ, secret và file ngoài scope.

Đọc lại [workflow 30 phút](/posting/workflow-30-phut-moi-ngay-opencode/) và so với phiên của bạn.

## Ngày 8: commit có chủ đích

Stage từng file, commit một mục đích. Viết message mô tả hành vi, không phải “AI update”. Không push nếu build fail.

**Đầu ra:** một commit sạch có thể revert độc lập.

## Ngày 9: mở pull request

Push branch và mở PR. Mô tả vấn đề, thay đổi, lệnh test, ảnh/preview nếu cần và giới hạn. Đọc diff trên GitHub lần nữa; giao diện PR đôi khi làm file ngoài scope dễ thấy hơn.

**Đầu ra:** PR reviewable, chưa cần merge vội.

## Ngày 10: tối ưu quota

Đọc [hạn mức Copilot Free](/posting/github-copilot-free-opencode-han-muc/). Xem usage thực tế, đếm request lặp và viết lại một prompt mơ hồ thành prompt có phạm vi. Nhớ: quota được công bố theo tháng, không reset mỗi ngày.

**Đầu ra:** template prompt bốn phần: triệu chứng, scope, ràng buộc, test.

## Ngày 11: luyện xử lý câu trả lời sai

Đưa cho agent một lỗi có bằng chứng rõ. Khi câu trả lời sai, không nói “làm lại”; nêu test/output mâu thuẫn và yêu cầu cập nhật giả thuyết. Sau hai vòng không tiến triển, dừng và đọc docs.

**Đầu ra:** bạn biết phản biện bằng bằng chứng, không bằng cảm giác.

## Ngày 12: bảo mật và permission

Audit phiên: agent đã đọc file nào, chạy lệnh nào, có network không, có secret trong context không. Đọc [checklist OpenCode an toàn](/posting/dung-opencode-an-toan-khong-lo-token/). Thu hẹp quyền mặc định.

**Đầu ra:** rule ngắn về secret, lệnh nguy hiểm, file cấm và quyền push/deploy.

## Ngày 13: chọn công cụ theo workflow

Đọc [so sánh OpenCode, Cursor, Claude Code và Copilot](/posting/opencode-so-voi-cursor-claude-code-copilot/). Dùng cùng task chỉ đọc để đánh giá giao diện, số vòng hỏi và độ rõ. Không cần đăng ký mọi gói trả phí.

**Đầu ra:** quyết định có lý do: tiếp tục OpenCode, kết hợp Copilot, hay dùng tool khác.

## Ngày 14: tổng kết sản phẩm và chi phí

Đọc [lịch sử OpenCode](/posting/lich-su-opencode-ai-coding-open-source/) và [mô hình kinh doanh](/posting/opencode-mien-phi-kiem-tien-nhu-the-nao/). Tổng hợp nhật ký: task hoàn thành, thời gian tiết kiệm, quota, lỗi agent và rủi ro.

Chỉ cân nhắc trả phí nếu một giới hạn lặp lại đang cản workload thật. Free core là điểm vào; paid service bán reliability/usage, không phải phép màu thay kỹ năng.

## Checklist tốt nghiệp

- [ ] Tôi biết OpenCode khác model/provider.
- [ ] Tôi luôn tạo branch và kiểm tra status.
- [ ] Tôi dùng plan/read-only trước task chưa rõ.
- [ ] Tôi không đưa secret vào prompt/log.
- [ ] Tôi đọc lệnh trước khi duyệt.
- [ ] Tôi review diff và chạy test/build.
- [ ] Tôi không hiểu quota tháng thành quota ngày.
- [ ] Tôi có thể dừng khi không hiểu patch.
- [ ] PR của tôi mô tả bằng chứng và giới hạn.
- [ ] Tôi không tin AI thay lập trình viên.

## Kinh nghiệm thực tế

Ngày tạo nhiều code nhất không nhất thiết là ngày học tốt nhất. Một buổi chỉ tìm được root cause nhưng chưa patch vẫn có giá trị. Nhật ký giúp bạn thấy năng lực tăng ở chất lượng câu hỏi và review, không ở mức phụ thuộc agent.

Sau lộ trình, lặp lại với repo khác nhưng giữ task nhỏ. Nếu chuyển sang production/team, bổ sung policy dữ liệu, approval và security review; không bê nguyên cấu hình học tập.
