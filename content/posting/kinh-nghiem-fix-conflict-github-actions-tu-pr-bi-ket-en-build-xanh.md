+++
title = "Kinh nghiệm fix conflict GitHub Actions: từ PR bị kẹt đến build xanh"
date = 2026-06-24
aliases = ["/kinh-nghiem-fix-conflict-github-actions-tu-pr-bi-ket-en-build-xanh/"]

[taxonomies]
categories = ["Công nghệ"]
tags = ["git", "lc8", "terminal", "webops", "zola"]
[extra]
+++

# Kinh nghiệm fix conflict GitHub Actions: từ PR bị kẹt đến build xanh

Có một kiểu lỗi rất quen với người làm blog kỹ thuật: PR đã code xong, tưởng chỉ chờ merge, nhưng GitHub lại báo conflict. Không phải conflict đơn giản trong một bài viết Markdown, mà là conflict nằm trong file report, script QA, template, SCSS, workflow và cả những phần generated data mà bình thường mình ít để ý.

<!-- more -->

Có một kiểu lỗi rất quen với người làm blog kỹ thuật: PR đã code xong, tưởng chỉ chờ merge, nhưng GitHub lại báo conflict. Không phải conflict đơn giản trong một bài viết Markdown, mà là conflict nằm trong file report, script QA, template, SCSS, workflow và cả những phần generated data mà bình thường mình ít để ý.

Lúc đó vấn đề không còn là “sửa dòng nào” nữa. Vấn đề thật sự là: mình đang sửa đúng lỗi, hay đang làm rối thêm một nhánh vốn đã rối?

Tôi gặp đúng tình huống này khi xử lý một PR có nhiệm vụ gỡ bỏ ShortenSEA và các gate paywall cũ. Đây là tính năng đã được retire, nghĩa là không còn dùng trong sản phẩm nữa. Nhưng vì blog đã phát triển lâu, dấu vết của nó vẫn nằm rải rác trong template, script QA, file test và workflow cũ. Kết quả là PR bị kẹt: GitHub báo conflict, QA Gatekeeper fail, còn build thì cứ lần lượt lòi ra lỗi cũ.

Điểm đầu tiên tôi nhận ra là: conflict không chỉ là chuyện chọn “ours” hay “theirs”. Mỗi file conflict có bản chất khác nhau.

Ví dụ, data/qa-404-report.json là file generated report. Đây là loại file thường được tạo lại bởi workflow hoặc script kiểm tra link. Với loại file này, nếu không có lý do đặc biệt, cách an toàn nhất là lấy bản từ main, vì main đang đại diện cho trạng thái production gần nhất.

Nhưng scripts/qa_vaccines.py lại là source code thật. File này chứa logic QA vaccine. Nếu chọn bừa một phía, có thể làm mất logic mới hoặc làm CI fail. Còn scripts/test_qa_vaccines.py là test compatibility. Dù tính năng cũ đã bỏ, workflow cũ vẫn có thể gọi test này. Nếu xóa hẳn, CI sẽ fail vì không import được module.

Bài học đầu tiên: phải phân loại file trước khi resolve conflict. File generated thì thường lấy main. File source code thì phải đọc kỹ. File test compatibility thì có thể cần giữ stub để workflow cũ không gãy.

Một sai lầm rất dễ mắc là fix conflict trên một working tree bẩn. Trong lúc làm việc, tôi vừa xử lý Cloudflare R2, vừa chạy build local, vừa có report generated. Nếu không để ý, PR gỡ ShortenSEA có thể bị lẫn cả thay đổi CDN, file r2-migrate-report, file cdn-rewrite-report, public_test và nhiều file content không liên quan.

Đó là điều rất nguy hiểm. Một PR vốn chỉ nên nói một câu chuyện sẽ biến thành một PR khổng lồ, khó review, khó rollback và khó biết lỗi đến từ đâu.

Vì vậy trước khi fix conflict, tôi luôn chạy git status -sb. Nếu thấy public, public_test hoặc file generated không liên quan, tôi dọn trước. Nếu nhánh đã quá rối, tôi quay về đúng remote branch rồi merge main lại từ đầu. Cách làm này hơi mất thêm vài phút, nhưng giúp tránh việc commit nhầm rác local.

Trong case này, một nguyên tắc rất quan trọng là không được hồi sinh tính năng đã retire. Paywall, MoMo và ShortenSEA đã được gỡ khỏi sản phẩm. Vì vậy khi resolve conflict, nếu main còn đoạn import macro paywall hoặc gọi momo_support, tôi không được lấy lại chỉ để build xanh. Build xanh mà kéo lại logic đã bỏ thì vẫn là sai.

Retire nghĩa là gỡ import cũ, gỡ call cũ, gỡ gate cũ. Không tạo lại macro paywall. Không tạo lại momo_support. Không thêm lại payment gate.

Tuy nhiên, có một chi tiết kỹ thuật: QA runner cũ vẫn mong một function trả về object có thuộc tính status. Nếu function cũ bị gỡ hoặc trả về dict, QA có thể báo lỗi kiểu “dict object has no attribute status”. Cách xử lý hợp lý là giữ một compatibility shim rất nhỏ, trả về trạng thái pass và thông báo rằng gate này đã retire. Như vậy workflow không bị gãy, nhưng product logic cũ cũng không bị hồi sinh.

Một lỗi khác cũng khá thường gặp là xóa file test cũ nhưng workflow vẫn gọi. Nếu workflow còn chạy test scripts.test_qa_vaccines, thì file scripts/test_qa_vaccines.py vẫn cần tồn tại. Trong trường hợp này, tôi giữ một test stub đơn giản để CI import được. Nó không phải là test giả để qua mặt hệ thống, mà là lớp chuyển tiếp cho một tính năng đã nghỉ hưu.

Sau khi resolve conflict, QA Gatekeeper vẫn fail. Nếu chỉ nhìn summary, rất dễ hoảng vì nó báo NOT PRODUCTION-SAFE. Nhưng summary không nói đủ. Phải tìm đúng dòng fail thật.

Tôi chạy lại qa_check.py và lọc các dòng có FAIL, FAILED, error hoặc NOT PRODUCTION. Lúc đó mới thấy lỗi thật không còn nằm ở paywall nữa, mà nằm ở KOREAN-BANNER. Vaccine này báo rằng giao diện Korean banner thiếu overflow hidden, thiếu pointer-events none cho hangeul-pattern và thiếu breakpoint mobile.

Đây là một bài học khác: đang fix conflict không có nghĩa là mọi lỗi hiện ra đều thuộc conflict ban đầu. QA có thể phát hiện một vấn đề UI độc lập. Lúc đó phải sửa tối thiểu đúng rule, không mở rộng scope lung tung.

Tôi thêm delta SCSS nhỏ cho home tabs: overflow hidden để chữ Hangul không tràn ra ngoài, pointer-events none để pattern trang trí không chặn click, và breakpoint mobile để layout không vỡ trên màn hình nhỏ. Đây là kiểu fix nên làm: nhỏ, đúng lỗi, đúng vaccine, không redesign.

Sau khi QA pass, vẫn chưa được vội commit. Tôi kiểm tra lại git status. Nếu thấy public_test hoặc data report không liên quan, phải dọn. Nếu thấy file R2 hoặc CDN trong PR paywall, phải bỏ ra. PR này chỉ nên chứa các thay đổi liên quan đến conflict và retired paywall gate.

Điều tôi rút ra rõ nhất là: build pass chỉ là điều kiện cần. PR sạch scope mới là điều kiện đủ.

Một PR tốt phải có một câu chuyện rõ ràng. PR gỡ ShortenSEA thì chỉ gỡ ShortenSEA và các gate paywall liên quan. PR Cloudflare R2 thì chỉ lo upload media, custom domain assets.seomoney.org và rewrite asset URL. PR chỉnh layout bài viết thì chỉ chỉnh SCSS layout. Nếu trộn cả ba vào một PR, mọi thứ sẽ khó review, khó debug và khó merge hơn rất nhiều.

Quy trình tôi sẽ dùng lại cho các lần sau là:

Trước hết kiểm tra git status để biết working tree có sạch không. Sau đó dọn public, public_test và các file generated không liên quan. Tiếp theo fetch main, merge main vào branch, rồi phân loại từng file conflict.

File generated report thì thường lấy bản main. File source code thì đọc conflict marker và giữ đúng intent của branch. File test compatibility thì giữ stub nếu workflow cũ còn gọi. Với tính năng đã retire, tuyệt đối không hồi sinh logic cũ chỉ để build xanh.

Sau khi resolve, kiểm tra lại conflict marker. Chạy unit test liên quan. Chạy qa_check.py. Chạy zola check. Chạy zola build. Sau build thì xóa public_test. Cuối cùng kiểm tra git status lần nữa, chỉ stage đúng file thuộc scope, rồi mới commit và push.

Tôi thích cách nhìn này: conflict không phải là tai nạn. Conflict là tín hiệu cho thấy hai luồng thay đổi đang chạm vào nhau. Nếu xử lý có kỷ luật, nó giúp mình dọn lại hệ thống. Nếu xử lý vội, nó biến repository thành một mớ rối.

Lần này, lỗi không chỉ dạy tôi cách resolve vài file. Nó nhắc tôi rằng WebOps cho một blog lớn không chỉ là viết bài và push code. Nó là việc giữ đường ray sạch: QA rõ ràng, PR đúng scope, build output không lọt vào repo, tính năng đã bỏ không bị kéo lại, và mỗi thay đổi đều có thể giải thích được sau này.

Đó là phần quan trọng nhất khi một blog tĩnh bắt đầu lớn dần thành một hệ sinh thái kỹ thuật.

## Checklist

- Kiểm tra branch trước khi viết.
- Tạo file Markdown đúng thư mục.
- Chạy `zola check`.
- Chạy `python3 qa_check.py`.
- Commit đúng file.
- Push branch và tạo PR..[GitHub CLI: lệnh nhỏ giúp tôi biết workflow còn chạy bao lâu mà k...](https://seomoney.org/posting/github-cli-lenh-nho-giup-toi-biet-workflow-con-chay-bao-lau-ma-k/)
