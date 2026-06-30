+++
title = "Workflow 30 phút mỗi ngày: sửa bug và tạo PR với OpenCode"
description = "Quy trình 30 phút dùng OpenCode sửa bug nhỏ, chạy test, review diff và tạo pull request trên GitHub, phù hợp hạn mức AI miễn phí."
date = 2026-06-30T13:04:00+07:00
updated = 2026-06-30T13:04:00+07:00
draft = false
slug = "workflow-30-phut-moi-ngay-opencode"
aliases = ["/workflow-30-phut-moi-ngay-opencode/",
  "/posting/workflow-30-phut-moi-ngay-opencode/"
]
[taxonomies]
categories = ["Tất cả", "Series", "Công nghệ"]
tags = ["ai", "github", "opencode", "pull request", "workflow"]
[extra]
author = "Duy Nguyen"
seo_keyword = "workflow OpenCode 30 phút mỗi ngày"
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
image_alt = "Workflow 30 phút dùng OpenCode sửa bug và tạo pull request"
image_source = "seomoney-generated"
image_license = "owned"
series = "opencode-ai-viet-code-mien-phi"
series_part = 5
series_order = 5
series_total = 10
[[extra.faq]]
q = "30 phút có đủ để sửa bug bằng OpenCode không?"
a = "Đủ với bug nhỏ, phạm vi rõ và repo có lệnh kiểm tra; task lớn nên chia thành nhiều phiên."
[[extra.faq]]
q = "Có cần tài khoản GitHub không?"
a = "Nên có để dùng branch, commit, pull request và CI làm lớp kiểm tra."
[[extra.faq]]
q = "Copilot Free có đủ cho workflow hằng ngày không?"
a = "Có thể đủ nếu không dùng mỗi ngày như quota cố định và ưu tiên task nhỏ, prompt rõ."
[[extra.faq]]
q = "Có nên để OpenCode tự commit và push không?"
a = "Người mới nên tự review diff rồi chủ động commit/push để giữ điểm kiểm soát."
[[extra.faq]]
q = "OpenCode có thay lập trình viên không?"
a = "Không; agent hỗ trợ một vòng làm việc, còn người dùng quyết định đúng sai và chịu trách nhiệm PR."
+++

> **TL;DR:** Chia 30 phút thành năm chặng: chọn issue, plan, sửa nhỏ, test/review, commit/PR. Mỗi phiên chỉ theo đuổi một kết quả kiểm chứng được; hết giờ mà chưa hiểu diff thì dừng, không ép agent làm tiếp.

Hạn mức miễn phí có thể trở thành lợi thế học tập nếu buộc bạn chọn task nhỏ. Thay vì mở OpenCode rồi hỏi ngẫu hứng, tôi dùng một khung 30 phút. Nó đủ ngắn để duy trì hằng ngày, nhưng có đầy đủ branch, plan, test và review.

Workflow này không hứa mỗi bug đều xong sau nửa giờ. Mục tiêu là tạo một đơn vị tiến bộ an toàn: hoặc có PR nhỏ, hoặc có chẩn đoán tốt để tiếp tục ngày mai. Với **AI viết code miễn phí GitHub**, kỷ luật phạm vi quan trọng hơn số request.

<!-- more -->

## Phút 0–5: chọn một issue có điểm dừng

Task phù hợp có thể mô tả bằng một câu và kiểm tra bằng một lệnh/hành vi. Ví dụ: sửa link 404 trong docs, thêm test cho edge case rỗng, chỉnh CSS overflow ở 375px, hoặc giải thích một warning build.

Task không phù hợp: “refactor toàn bộ”, “làm site nhanh hơn”, “nâng cấp mọi dependency”. Chúng thiếu điểm dừng và dễ kéo agent ra ngoài phạm vi.

Trước khi mở OpenCode:

```bash
git status
git switch -c fix/short-description
```

Nếu worktree có thay đổi khác, đừng trộn. Ghi tiêu chí hoàn thành vào note: “test X pass, không đổi API, tối đa hai file”.

## Phút 5–10: yêu cầu plan chỉ đọc

Prompt nên có bốn phần: triệu chứng, phạm vi, điều cấm và cách xác minh.

```text
Test normalize_slug_empty đang fail. Chỉ đọc implementation và test liên quan.
Không sửa code, không cài dependency. Nêu root cause, patch nhỏ nhất,
rủi ro regression và lệnh test chính xác.
```

Đối chiếu đường dẫn, function và giả định agent đưa ra. Nếu nó nói về file không tồn tại, yêu cầu kiểm tra lại thay vì tiếp tục. Plan mode giảm rủi ro nhưng không bảo đảm kết luận đúng.

## Phút 10–20: sửa phạm vi nhỏ

Khi plan hợp lý, cho phép sửa đúng file. Nhắc lại giới hạn, vì một agent có thể tìm thấy “cơ hội cải thiện” không liên quan. Patch tốt thường nhỏ hơn bạn nghĩ.

Trong lúc agent chạy, không phê duyệt lệnh chỉ dựa vào tên. Đọc đầy đủ. Lệnh xóa, reset, cài global, thay quyền hoặc gửi dữ liệu ra mạng cần lý do rõ và thường không cần cho bug nhỏ.

Nếu agent sửa thêm dependency, workflow hoặc config ngoài plan, dừng và hỏi tại sao. Không để sunk cost khiến bạn giữ patch khó hiểu.

## Phút 20–25: test và review diff

Chạy test hẹp trước, build rộng sau nếu thời gian cho phép:

```bash
git diff --check
git diff --stat
git diff
```

Sau đó chạy lệnh repo quy định. Test pass chưa đủ; kiểm tra test có thực sự bao phủ bug không. Với UI, mở preview. Với link, truy cập route local. Với dữ liệu, thử edge case.

Đọc diff như code do người lạ gửi: có secret, debug log, hardcode domain cũ, comment sai hay thay đổi formatting hàng loạt không? Agent không được miễn review chỉ vì prompt do bạn viết.

## Phút 25–30: commit, PR và ghi bài học

Chỉ stage file thuộc task:

```bash
git add path/to/changed-file path/to/test
git commit -m "fix: handle empty slug input"
```

PR nên ghi: vấn đề, patch, lệnh test và điều chưa kiểm tra. Nếu chưa xong, đừng tạo commit giả vờ hoàn thành. Ghi note về root cause và bước tiếp theo rồi dừng phiên.

Nhật ký một dòng rất hữu ích: “Prompt ban đầu thiếu test name nên agent đọc quá rộng” hoặc “Plan mode tìm đúng root cause trong một lượt”. Sau 14 ngày, bạn sẽ thấy mẫu prompt nào tiết kiệm quota.

## Một tuần mẫu

- **Thứ hai:** đọc issue và viết reproduction.
- **Thứ ba:** thêm unit test tái hiện lỗi.
- **Thứ tư:** sửa implementation tối thiểu.
- **Thứ năm:** review accessibility/performance của patch.
- **Thứ sáu:** dọn docs và mở PR.
- **Cuối tuần:** đọc lại PR, ghi điều học được; không bắt buộc tạo code.

Một bug có thể kéo dài nhiều phiên mà vẫn hiệu quả. Mỗi ngày có artifact nhỏ và kiểm chứng được. Đây là cách tránh đốt 50 chat requests trong một buổi rồi không biết agent đã làm gì.

## Khi agent trả lời sai

Đừng prompt “sai rồi, làm lại” mà không chỉ ra bằng chứng. Nêu test fail, dòng code hoặc hành vi trái yêu cầu. Yêu cầu agent cập nhật giả thuyết trước khi sửa tiếp. Nếu hai vòng vẫn không tiến triển, tự đọc code hoặc dừng để tìm tài liệu.

Không phải mọi vấn đề đều phù hợp với model miễn phí. Context lớn, kiến trúc phức tạp hay lỗi production có thể cần chuyên môn con người và công cụ khác. Biết dừng là một kỹ năng kỹ thuật.

Một mẹo hữu ích là giữ lại reproduction tối thiểu trước khi cho agent sửa. Khi câu trả lời mới xuất hiện, chạy lại đúng reproduction cũ thay vì đổi tiêu chí theo patch. Nếu bug biến mất nhưng một hành vi khác hỏng, bạn đã có regression chứ chưa hoàn thành task. Với lỗi giao diện, ghi viewport và thao tác; với API, ghi input cùng status mong đợi; với build, giữ nguyên câu lệnh và môi trường. Bằng chứng ổn định giúp cuộc trao đổi ngắn hơn và tránh việc agent liên tục “chữa” triệu chứng mới do chính patch trước tạo ra.

## Bài học rút ra

Workflow 30 phút tạo ba hàng rào: thời gian, phạm vi và bằng chứng. OpenCode tăng tốc thao tác giữa các hàng rào; GitHub lưu lịch sử và PR; test cung cấp tín hiệu. Không thành phần nào tự bảo đảm code đúng.

Nếu duy trì mỗi ngày, hãy dành riêng vài phút cuối để dọn branch và ghi trạng thái. Một repo sạch cùng note rõ giúp phiên hôm sau bắt đầu từ bằng chứng, không phải yêu cầu agent đoán lại toàn bộ bối cảnh.

Khi đã làm quen, hãy so sánh [OpenCode với Cursor, Claude Code và Copilot](/posting/opencode-so-voi-cursor-claude-code-copilot/) để chọn giao diện phù hợp. Quy trình plan–diff–test vẫn có giá trị dù bạn đổi tool.

## Liên kết nội bộ

- [Bắt đầu AI viết code miễn phí](/posting/ai-viet-code-mien-phi-github-opencode/)
- [Hiểu hạn mức Copilot Free](/posting/github-copilot-free-opencode-han-muc/)
- [Dùng OpenCode an toàn](/posting/dung-opencode-an-toan-khong-lo-token/)
- [Git và GitHub cho người mới](/posting/github-la-gi-tao-repository-dau-tien/)
- [Lộ trình 14 ngày](/posting/lo-trinh-tu-hoc-ai-coding-mien-phi-opencode-github/)
- [Hub Series](/series/)

## Liên kết bên ngoài

- [Tài liệu agent OpenCode](https://opencode.ai/docs/agents/)
- [Repository OpenCode](https://github.com/anomalyco/opencode)
- [GitHub Docs về pull request](https://docs.github.com/en/pull-requests)
- [GitHub Copilot plans](https://github.com/features/copilot/plans)

## Bản quyền và ghi nguồn

Bài do SEOMONEY biên tập từ kinh nghiệm workflow Git/PR và tài liệu chính thức OpenCode, GitHub. Ví dụ là minh họa độc lập, không sao chép tài liệu nguồn. Ảnh OG dùng fallback nội bộ.

## FAQ - Câu hỏi thường gặp

### 30 phút có đủ để sửa bug không?

Đủ cho bug nhỏ có reproduction và test. Task lớn nên chia thành nhiều phiên có artifact riêng.

### Có cần tài khoản GitHub không?

Không bắt buộc cho OpenCode, nhưng cần nếu muốn dùng branch remote, PR, Codespaces và Copilot.

### Copilot Free có đủ để học hằng ngày không?

Có thể đủ nếu dùng task nhỏ và không hiểu quota tháng như khoản cấp lại mỗi ngày.

### Có nên để OpenCode tự push không?

Người mới nên tự review, stage và push để giữ điểm kiểm soát rõ ràng.

### OpenCode có thay lập trình viên không?

Không. Agent giúp thao tác; người dùng vẫn quyết định thiết kế, chất lượng và việc merge.
