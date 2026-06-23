+++
title = "Nâng cấp LC8 Patch 4: khi Terminal không chỉ chạy lệnh, mà còn bi..."
description = "Hôm nay tôi tiếp tục nâng cấp workflow LC8 lên Patch 4. Đây là một nâng cấp nhỏ về giao diện Terminal, nhưng lại làm trải nghiệm dùng thật dễ chịu hơn rất nh..."
date = 2026-06-23
[taxonomies]
categories = ["Công nghệ"]
tags = ["LC8", "Terminal", "Git", "Zola", "WebOps"]
+++

# Nâng cấp LC8 Patch 4: khi Terminal không chỉ chạy lệnh, mà còn bi...

Hôm nay tôi tiếp tục nâng cấp workflow LC8 lên Patch 4. Đây là một nâng cấp nhỏ về giao diện Terminal, nhưng lại làm trải nghiệm dùng thật dễ chịu hơn rất nhiều: hệ thống có progress bar để người dùng biết nó đang chạy tới đâu.

<!-- more -->

Hôm nay tôi tiếp tục nâng cấp workflow LC8 lên Patch 4. Đây là một nâng cấp nhỏ về giao diện Terminal, nhưng lại làm trải nghiệm dùng thật dễ chịu hơn rất nhiều: hệ thống có progress bar để người dùng biết nó đang chạy tới đâu.

Trước đây, LC8 đã làm được khá nhiều việc. Tôi chỉ cần gõ `lc8`, dán text hoặc ý tưởng cần viết bài, kết thúc bằng `LC8END`, rồi hệ thống tự tạo bài Markdown, chạy kiểm tra, commit, push và mở pull request trên GitHub.

Sau vài lần thử, tôi nhận ra một vấn đề rất thực tế: khi một script chạy nhiều bước liên tiếp, người dùng rất dễ có cảm giác “nó đang đứng hay đang chạy?”. Đặc biệt khi Terminal chỉ hiện vài dòng như “Checking site...” hoặc “Done in 170ms”, người mới có thể không hiểu đó là đã xong toàn bộ hay chỉ xong một bước nhỏ.

Vì vậy Patch 4 ra đời với mục tiêu rất rõ: làm cho LC8 biết báo tiến độ trực quan hơn.

Trước Patch 4, flow LC8 đã có những phần quan trọng:

* Nhận text nhiều dòng bằng Terminal. * Dùng `LC8END` làm dấu hiệu kết thúc input. * Gọi Claude CLI hoặc Codex CLI nếu có. * Nếu AI CLI hết quota, chuyển sang fallback menu. * Cho phép dùng lại text vừa dán và tự bọc thành Markdown. * Tạo file bài viết trong thư mục `content/posting`. * Tạo branch riêng dạng `post/lc8-<timestamp>`. * Chạy `zola check`. * Chạy `python3 qa_check.py`. * Commit đúng file bài viết. * Push branch. * Tạo pull request bằng GitHub CLI. * Hỏi người dùng muốn theo dõi PR checks, GitHub Actions run hay deploy.

Nhưng điểm thiếu là: người dùng không thấy rõ tiến trình từng stage.

Patch 4 thêm một hàm Bash nhỏ tên là `lc8_step`. Hàm này quản lý tổng số bước của workflow và in ra một thanh tiến độ dạng text ngay trong Terminal.

Ví dụ:

LC8 Progress [██████░░░░░░░░░░░░░░░░] 25% 2/8 · AI/Fallback: tạo nội dung bài viết

Thanh này không phải progress theo thời gian thật tuyệt đối, vì mỗi bước có thể nhanh hoặc chậm tùy mạng, GitHub, AI CLI, Zola hoặc QA. Nhưng nó cho người dùng biết hệ thống đang ở đoạn nào trong workflow.

Patch 4 chia LC8 thành các mốc chính:

1. Input: đã nhận source text. 2. AI/Fallback: tạo nội dung bài viết. 3. Markdown: chuẩn hóa nội dung bài. 4. Git: tạo branch và cập nhật main. 5. QA: chạy Zola và repo checks. 6. GitHub: commit và push branch. 7. GitHub: tạo pull request. 8. Done: PR đã tạo, chuyển sang theo dõi.

Nhìn như vậy, người dùng không còn phải đoán. Nếu hệ thống đang ở bước QA thì biết là nó đang kiểm tra. Nếu đang ở bước GitHub thì biết là nó đang commit, push hoặc tạo PR. Nếu đã tới bước Done thì phần tạo bài đã xong, chỉ còn chọn theo dõi hay thoát.

Tech đứng sau Patch 4 thật ra khá đơn giản nhưng hiệu quả.

LC8 là một Bash script nằm trong:

~/.local/bin/lc8

Để Terminal gọi được lệnh `lc8`, thư mục `~/.local/bin` được thêm vào PATH.

Trong Patch 4, script được thêm biến:

LC8_PROGRESS_TOTAL=8 LC8_PROGRESS_STEP=0

Mỗi lần workflow đi qua một stage, hàm `lc8_step` được gọi. Hàm này tăng biến `LC8_PROGRESS_STEP`, tính phần trăm hoàn thành, rồi dựng progress bar bằng ký tự `█` và `░`.

Ví dụ nếu tổng có 8 bước và đang ở bước 4, phần trăm là 50%. Script sẽ in một thanh gần như lấp một nửa.

Điểm hay là cách này không cần thư viện ngoài. Không cần Node package. Không cần Python package. Không cần cài thêm tool như `watch`, `pv` hay dashboard phức tạp. Chỉ cần Bash là đủ.

Tôi thích cách này vì nó giữ đúng tinh thần LC8: nhẹ, local-first, dễ hiểu, chạy được ngay trong Terminal trên Mac.

Patch 4 cũng làm rõ hơn ranh giới giữa “phần người dùng” và “phần hệ thống”.

Phần của tôi chỉ là:

* Chạy `lc8`. * Dán text. * Gõ `LC8END`. * Nếu AI CLI hết quota thì chọn option 1 để dùng lại text vừa dán. * Sau đó chờ hệ thống chạy.

Từ đó trở đi, LC8 tự làm phần còn lại.

Nếu mọi thứ ổn, Terminal sẽ hiện các mốc như:

* Article content ready. * Preparing branch. * Running checks. * Zola build PASS. * Repo QA PASS. * Commit + push. * Creating PR. * LC8 done.

Nếu có lỗi, hệ thống phải dừng rõ ràng và báo fail. Đây là điểm quan trọng, vì automation không nên âm thầm bỏ qua lỗi. Nó phải hoặc pass rõ, hoặc fail rõ.

Một bài học nhỏ trong quá trình nâng cấp là chữ “Done” không phải lúc nào cũng có nghĩa là toàn bộ việc đã xong. Ví dụ `zola check` có thể in “Done in 170ms”, nhưng đó chỉ là Zola chạy xong bước của nó. Còn workflow LC8 vẫn có thể phải chạy QA, commit, push và tạo PR.

Vì vậy, Patch 4 nên được hiểu là nâng cấp UX cho Terminal automation. Nó không chỉ chạy lệnh, mà còn giúp người dùng hiểu trạng thái của lệnh.

Bên dưới Patch 4 còn có nhiều thành phần phối hợp:

Bash điều phối toàn bộ workflow. Git bảo vệ branch và commit. Zola kiểm tra static site. Python xử lý text thường thành Markdown và tạo slug. GitHub CLI tạo PR và theo dõi checks. Fallback menu giúp workflow vẫn chạy khi Claude hoặc Codex hết quota. Progress bar giúp người dùng nhìn được hệ thống đang làm tới đâu.

Điểm đáng giá nhất là LC8 ngày càng giống một trợ lý WebOps local. Nó không thay thế con người, mà giảm việc phải nhớ lệnh.

Thay vì nhớ:

git switch main git pull --rebase origin main git switch -c post/... zola check --skip-external-links python3 qa_check.py git add ... git commit ... git push ... gh pr create gh pr checks --watch

Tôi chỉ cần nhớ:

lc8

Sau đó hệ thống hỏi gì thì chọn.

Patch 4 cũng cho thấy một nguyên tắc quan trọng khi xây automation: không chỉ tối ưu máy chạy, mà phải tối ưu cảm giác của người dùng khi chờ máy chạy.

Một automation tốt nên có:

* Guard để không chạy trên repo bẩn. * Fallback khi AI CLI hết quota. * Check rõ pass/fail. * Không add file bừa bãi. * Tạo branch riêng cho từng việc. * Tạo PR sạch. * Có menu theo dõi sau khi tạo PR. * Có progress bar để người dùng không hoang mang.

Kết luận: LC8 Patch 4 không phải là một thay đổi lớn về tính năng cốt lõi, nhưng là một nâng cấp rất quan trọng về trải nghiệm. Nó biến Terminal từ một màn hình đen chạy lệnh thành một workflow có trạng thái, có tiến độ và có phản hồi rõ ràng.

Với tôi, đây là bước làm cho việc viết blog bằng Terminal trở nên thân thiện hơn: người dùng chỉ cần dán ý tưởng, còn hệ thống sẽ lo phần kỹ thuật phía sau.

## Checklist

- Kiểm tra branch trước khi viết.
- Tạo file Markdown đúng thư mục.
- Chạy `zola check`.
- Chạy `python3 qa_check.py`.
- Commit đúng file.
- Push branch và tạo PR.
