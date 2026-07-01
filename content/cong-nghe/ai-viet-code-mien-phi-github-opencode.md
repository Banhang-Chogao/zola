+++
title = "AI viết code miễn phí với GitHub và OpenCode từ số 0 - Duy Nguyen"
description = "Duy Nguyen hướng dẫn bắt đầu AI viết code miễn phí với OpenCode, Copilot Free và GitHub — nội dung SEO cho lập trình viên tự học và affiliate công cụ developer."
date = 2026-06-30T13:00:00+07:00
updated = 2026-06-30T13:00:00+07:00
draft = false
slug = "ai-viet-code-mien-phi-github-opencode"
aliases = ["/ai-viet-code-mien-phi-github-opencode/",
  "/posting/ai-viet-code-mien-phi-github-opencode/"
]

[taxonomies]
categories = ["Tất cả", "Series", "Công nghệ"]
tags = ["ai", "ai coding", "github", "github copilot", "opencode"]
[extra]
author = "Duy Nguyen"
seo_keyword = "AI viết code miễn phí GitHub"
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
image_alt = "Quy trình dùng OpenCode và GitHub để viết code bằng AI miễn phí"
image_source = "seomoney-generated"
image_license = "owned"
series = "opencode-ai-viet-code-mien-phi"
series_part = 1
series_order = 1
series_total = 10

[[extra.faq]]
q = "OpenCode có miễn phí không?"
a = "Phần lõi OpenCode là mã nguồn mở và có thể cài miễn phí; model hoặc dịch vụ AI kết nối vào có thể miễn phí, giới hạn hoặc trả phí."

[[extra.faq]]
q = "Có cần tài khoản GitHub không?"
a = "Không bắt buộc cho mọi provider, nhưng tài khoản GitHub giúp dùng repo, Codespaces và đăng nhập Copilot thuận tiện hơn."

[[extra.faq]]
q = "GitHub Copilot Free có đủ để học không?"
a = "Đủ để học và xử lý task nhỏ nếu dùng có kế hoạch, nhưng đây là hạn mức theo tháng chứ không phải miễn phí vô hạn."

[[extra.faq]]
q = "OpenCode có thay được lập trình viên không?"
a = "Không. OpenCode hỗ trợ đọc, đề xuất và sửa code; người dùng vẫn phải đặt yêu cầu, review diff và kiểm tra kết quả."

[[extra.faq]]
q = "Dùng OpenCode có an toàn không?"
a = "Có thể dùng an toàn hơn khi làm trên branch riêng, không đưa secret vào prompt, giới hạn quyền và luôn review lệnh cùng diff."
[[extra.references_external]]
title = "OpenCode — trang chính thức"
url = "https://opencode.ai/"

[[extra.references_external]]
title = "Tài liệu bắt đầu với OpenCode"
url = "https://opencode.ai/docs/"

[[extra.references_external]]
title = "Repository OpenCode trên GitHub"
url = "https://github.com/anomalyco/opencode"

[[extra.references_external]]
title = "Các gói GitHub Copilot"
url = "https://github.com/features/copilot/plans"

+++

> **TL;DR:** Bạn có thể bắt đầu **AI viết code miễn phí GitHub** với bốn thứ: OpenCode, tài khoản GitHub, Copilot Free hoặc một model miễn phí được hỗ trợ, và repo cá nhân. “Miễn phí” ở đây là đủ để học và sửa task nhỏ, không phải sử dụng vô hạn.

Tôi thích cách bắt đầu này vì nó không đòi hỏi mua ngay một IDE mới hay đăng ký nhiều dịch vụ. Bạn mở repo quen thuộc, giao một việc nhỏ cho AI, xem nó đề xuất gì rồi tự kiểm tra. Sau vài vòng như vậy, bạn hiểu cả công cụ lẫn code tốt hơn nhiều so với việc yêu cầu AI “làm toàn bộ ứng dụng”.

OpenCode là một AI coding agent mã nguồn mở. Theo trang chính thức, công cụ có giao diện terminal, extension IDE và ứng dụng desktop. OpenCode không tự biến thành model AI; nó là lớp agent kết nối model/provider, đọc ngữ cảnh dự án, lập kế hoạch và hỗ trợ thao tác trên code. GitHub cung cấp nơi lưu repo, branch, commit và pull request. Hai phần ghép lại thành một phòng thực hành khá hoàn chỉnh.

<!-- more -->

## Bộ công cụ AI viết code miễn phí GitHub tối thiểu

Bạn chưa cần server riêng hay máy tính mạnh. Bộ tối thiểu gồm:

1. **OpenCode** để trò chuyện với agent trong project.
2. **Tài khoản GitHub** để lưu code và quản lý thay đổi.
3. **Một nguồn model có hạn mức miễn phí**, chẳng hạn Copilot Free hoặc free model OpenCode đang hỗ trợ tại thời điểm dùng.
4. **Một repo cá nhân** đủ nhỏ để bạn hiểu cấu trúc và biết kết quả mong đợi.

Repo đầu tiên nên đơn giản: blog tĩnh, trang HTML/CSS, script Python nhỏ hoặc dự án học tập có test. Đừng chọn production của công ty làm nơi thử nghiệm đầu tiên. Agent có khả năng sửa nhiều file nhanh, nhưng tốc độ ấy chỉ có ích khi bạn kiểm soát phạm vi.

Nếu không muốn cài local, bạn có thể dùng GitHub Codespaces. Bài [cài OpenCode trong GitHub Codespaces](/posting/cai-opencode-trong-github-codespaces/) sẽ đi từng bước. Nếu đã có terminal trên máy, hãy theo tài liệu cài đặt chính thức thay vì copy một lệnh không rõ nguồn.

## “Miễn phí để bắt đầu” khác “miễn phí vô hạn”

Đây là chỗ dễ gây hiểu nhầm nhất. OpenCode có phần lõi mã nguồn mở, nhưng agent vẫn cần model xử lý prompt. Model đó có thể đi kèm free tier, quota, credit hoặc giá theo usage. Chính sách có thể thay đổi, vì vậy luôn kiểm tra trang của provider trước khi bắt đầu một task dài.

GitHub hiện công bố Copilot Free gồm **2.000 code completions và 50 chat requests mỗi tháng**. Đó là quota tháng, không phải quota ngày. Nếu chia đều, người mới vẫn có thể học và sửa code hằng ngày, nhưng không nên biến phép chia thành cam kết “mỗi ngày được cấp lại”. Chi tiết được phân tích ở bài [GitHub Copilot Free với OpenCode](/posting/github-copilot-free-opencode-han-muc/).

OpenCode cũng quảng bá free models và khả năng kết nối nhiều provider. “Free model” không đồng nghĩa luôn sẵn sàng hoặc không giới hạn. Provider có thể thay model, tốc độ, cửa sổ ngữ cảnh và chính sách. Cách an toàn là xem free tier như môi trường học, còn task quan trọng phải có kế hoạch chi phí và phương án dừng.

## Bài thực hành đầu tiên: sửa một lỗi nhỏ

Giả sử repo có một nút “Đăng ký” bị lệch trên màn hình nhỏ. Đừng prompt: “Kiểm tra và làm website đẹp hơn”. Hãy mô tả cụ thể:

```text
Đọc CSS của nút đăng ký. Chỉ tìm nguyên nhân nút tràn ngang ở viewport 375px.
Chưa sửa file. Hãy đưa kế hoạch ngắn, nêu file dự kiến thay đổi và cách kiểm tra.
```

Sau khi đọc kế hoạch, bạn mới cho phép sửa đúng file. Tiếp đó yêu cầu agent chạy test hoặc build hiện có. Quy trình nên là:

- tạo branch mới, ví dụ `fix/mobile-signup-button`;
- kiểm tra `git status` trước khi giao việc;
- dùng plan/read-only trước khi cho sửa;
- giới hạn một lỗi, một nhóm file;
- xem `git diff` bằng mắt;
- chạy test/build;
- commit nhỏ với thông điệp mô tả đúng thay đổi;
- mở PR để có thêm một lớp review.

AI có thể viết cú pháp đúng nhưng hiểu sai mục tiêu. Một build xanh cũng chưa chứng minh giao diện đúng. Bạn vẫn cần mở preview, thử bàn phím, kiểm tra mobile và đọc diff. Đó là kỹ năng cốt lõi của việc **tự viết code bằng AI miễn phí**: dùng agent để tăng tốc suy nghĩ, không giao luôn trách nhiệm.

## Cách dùng quota hiệu quả hơn

Một request tốt thường tiết kiệm hơn năm request mơ hồ. Trước khi hỏi, hãy viết ba dòng: lỗi là gì, phạm vi nào được sửa, điều kiện nào chứng minh đã xong. Nếu agent thiếu dữ liệu, cung cấp tên file hoặc output lỗi đã loại secret; đừng ném toàn bộ log dài.

Tôi thường tách task thành bốn nhịp:

1. **Hiểu:** yêu cầu đọc code và giải thích nguyên nhân.
2. **Lập kế hoạch:** liệt kê thay đổi nhỏ nhất và rủi ro.
3. **Thực hiện:** sửa đúng phạm vi đã duyệt.
4. **Xác minh:** chạy test, đọc diff, ghi điều chưa chắc.

Nhịp này vừa tiết kiệm quota vừa giúp người mới học được lý do đằng sau patch. Một workflow 30 phút cụ thể nằm ở [bài 5 của series](/posting/workflow-30-phut-moi-ngay-opencode/).

## Khi nào nên dừng agent

Hãy dừng khi agent muốn xóa nhiều file, cài dependency không cần thiết, sửa workflow deploy, yêu cầu secret hoặc mở rộng task mà chưa giải thích. Đừng chấp thuận lệnh nguy hiểm chỉ vì nó được trình bày tự tin. Với repo cá nhân, branch và lịch sử Git giúp quay lại, nhưng chúng không cứu được token đã lộ hay dữ liệu đã gửi ra ngoài.

Bạn cũng nên dừng khi không còn hiểu diff. Mục tiêu của series không phải tạo cảm giác “AI làm được mọi thứ”, mà là giúp bạn hình thành vòng lặp có kiểm soát. Bài [dùng OpenCode an toàn](/posting/dung-opencode-an-toan-khong-lo-token/) có checklist quyền, secret và lệnh shell chi tiết hơn.

## Bài học rút ra

Rào cản thử AI coding đã thấp hơn trước: công cụ mở, tài khoản GitHub phổ biến và free tier đủ cho bài tập nhỏ. Tuy nhiên, giá trị thật không nằm ở số dòng code agent tạo ra. Nó nằm ở khả năng biến một vấn đề mơ hồ thành task nhỏ, kiểm chứng được và có lịch sử thay đổi rõ ràng.

Sau bài này, bước hợp lý là hiểu [OpenCode là gì và khác một chatbot code ra sao](/posting/opencode-la-gi-ai-coding-agent/). Khi hiểu vai trò của agent, bạn sẽ chọn provider, quota và workflow đúng hơn thay vì chạy theo chữ “free”.
