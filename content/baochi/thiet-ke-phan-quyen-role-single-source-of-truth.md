+++
title = "Phân quyền role: vì sao nên gom về một nguồn sự thật"
description = "Kinh nghiệm gom hệ thống phân quyền role (super, admin, vip, user) về một nguồn sự thật duy nhất: ưu tiên role, ma trận quyền và bài học cookie cross-site."
date = 2026-06-20
[taxonomies]
categories = ["Tất cả", "Công nghệ", "Báo chí"]
tags = ["phân quyền", "rbac", "role", "bảo mật", "oauth", "kiến trúc phần mềm"]
[extra]
thumbnail = "https://seomoney.org/img/og-default.webp"
seo_keyword = "phân quyền role"
featured = false

[[extra.faq]]
q = "Phân quyền role là gì và vì sao cần một nguồn sự thật?"
a = "Phân quyền role (role-based access control) là cách gán cho mỗi người dùng một vai trò như user, vip, admin hay super, rồi quyết định họ được làm gì dựa trên vai trò đó. Một nguồn sự thật nghĩa là chỉ có duy nhất một module định nghĩa role và quyền; mọi nơi khác đều đọc từ đó thay vì tự suy luận, nhờ vậy tránh được tình trạng mỗi chỗ hiểu quyền một kiểu."
[[extra.faq]]
q = "Vì sao không nên để frontend tự đoán quyền của người dùng?"
a = "Frontend chỉ nên hiển thị, không nên quyết định ai được phép làm gì. Nếu để JavaScript tự đoán role theo email hay username, kẻ tấn công có thể chỉnh sửa biến trong trình duyệt để giả mạo quyền. An toàn hơn là backend trả về danh sách quyền cụ thể qua API, frontend chỉ bật/tắt nút theo đó còn việc chặn thật vẫn nằm ở server."
[[extra.faq]]
q = "Ưu tiên role super, admin, vip, user nên hoạt động ra sao?"
a = "Nên có thứ tự rõ ràng: super cao nhất, rồi admin, vip và cuối cùng là user. Quyền thấp luôn là tập con của quyền cao, và một role chỉ được nâng lên cấp cao nhất khi nằm trong danh sách được khai báo tường minh — không nên để admin tự động trở thành super chỉ vì trùng một danh sách phụ nào đó."
[[extra.faq]]
q = "Cookie SameSite=None dùng để làm gì trong đăng nhập cross-site?"
a = "Khi trang tĩnh nằm ở một tên miền còn API xác thực nằm ở tên miền khác, trình duyệt như Safari hoặc Edge sẽ chặn cookie phiên nếu không khai báo SameSite=None kèm Secure và HttpOnly. Đặt đúng ba thuộc tính này giúp phiên đăng nhập đi kèm request cross-site mà vẫn an toàn, tránh lỗi đăng nhập xong nút quản trị vẫn biến mất."
+++

Tuần rồi mình dành gần một buổi để dọn lại một thứ tưởng nhỏ mà hóa ra rất dễ gây đau đầu: hệ thống **phân quyền role** của một ứng dụng có nhiều cấp người dùng. Ban đầu chỉ định sửa một cái nút quản trị lúc ẩn lúc hiện, nhưng càng đào càng thấy gốc rễ nằm ở chỗ logic quyền bị rải khắp nơi, mỗi file hiểu một kiểu. Bài này mình ghi lại cách mình gom tất cả về một mối, và vài bài học rút ra mà mình nghĩ ai làm sản phẩm có đăng nhập đều sẽ gặp.

<!-- more -->

![Sơ đồ phân quyền role với một nguồn sự thật duy nhất](https://assets.seomoney.org/img/placeholder/placeholder-wide.svg)

Mình viết theo kiểu chia sẻ kinh nghiệm thực tế chứ không phải tài liệu hàn lâm, nên sẽ ưu tiên những thứ "đụng vào là thấy đau" hơn là định nghĩa sách vở.

## Phân quyền role bị rải rác thì hỏng ở đâu?

Vấn đề kinh điển: ở giai đoạn đầu, mỗi khi cần kiểm tra "người này có phải admin không", lập trình viên lại viết một đoạn nho nhỏ ngay tại chỗ. Một thời gian sau, cùng một câu hỏi "ai là super admin" được trả lời ở ba, bốn file khác nhau — và tệ hơn, mỗi nơi trả lời hơi lệch nhau.

Trong trường hợp mình gặp, danh sách email và username admin được khai báo lặp lại ở ba file riêng biệt, thậm chí còn có một email mặc định viết cứng (hardcode) trong code. Logic dựng "thông tin định danh" trả về cho client thì có hai bản, và hai bản này tính cờ `is_super` theo hai cách không giống nhau. Hậu quả là cùng một tài khoản, hỏi chỗ này thì ra admin, hỏi chỗ kia lại thành super.

Đáng sợ nhất là một nhánh logic: hệ thống lấy danh sách username admin rồi vô tình OR (gộp) với điều kiện super, khiến **admin âm thầm được nâng thành super** dù không ai cố ý cho phép điều đó. Đây chính là loại lỗi phân quyền mà các tài liệu bảo mật như [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html) cảnh báo: quyền leo thang ngoài ý muốn vì logic kiểm tra không nhất quán.

Bài học đầu tiên rất đơn giản nhưng dễ quên: **logic quyền mà lặp lại ở nhiều chỗ thì sớm muộn cũng lệch nhau**, và khi nó lệch trong chuyện phân quyền thì đó không còn là bug giao diện, mà là lỗ hổng bảo mật.

## Gom về một nguồn sự thật như thế nào?

Cách mình làm là tạo ra **một module duy nhất** — gọi nó là `roles` cho dễ hình dung — đóng vai trò nguồn sự thật cho toàn bộ chuyện vai trò và quyền. Nguyên tắc mình tự đặt ra:

- Mọi danh sách quyết định role (ai là admin, ai là super) chỉ được khai báo **một lần**, lấy từ biến môi trường, không viết cứng giá trị trong code.
- Mọi nơi cần biết role của người dùng đều **gọi vào module này**, không tự suy luận lại.
- Hàm dựng thông tin định danh trả cho client cũng nằm ở đây, để cả phần đăng nhập lẫn phần kiểm tra phiên đều dùng chung một logic.

Sau khi gom, kết quả khá gọn. Hàm kiểm tra `is_admin` trước nằm lẫn trong module xác thực thì được dời về `roles`. Hai bản dựng payload `/me` trước đây tính khác nhau thì cùng ủy quyền cho một hàm `build_identity` duy nhất. Và quan trọng nhất: **super giờ chỉ được xác định bằng đúng một danh sách super tường minh**, không còn chuyện admin vô tình leo thang.

Một điểm mình thấy đáng giá là việc xóa email mặc định hardcode. Khi một giá trị nhạy cảm nằm cứng trong source của một repo công khai, nó vừa là rủi ro lộ thông tin vừa là nguồn gây nhầm lẫn về sau. Đẩy hết ra biến môi trường giúp code sạch hơn và an toàn hơn — đây cũng là nguyên tắc mình luôn nhắc trong các bài về [bảo mật ngân hàng số như MSB Digital Bank](/baochi/msb-digital-bank-cong-nghe-bao-mat/): đừng để bí mật nằm trong nơi ai cũng đọc được.

## Ưu tiên role và ma trận quyền

Sau khi có một nguồn sự thật, mình định nghĩa rõ thứ tự ưu tiên:

> super > admin > vip > user

Thứ tự này không chỉ để cho đẹp. Nó có nghĩa là quyền của cấp thấp luôn là tập con của cấp cao: super làm được mọi thứ admin làm được, admin làm được mọi thứ vip làm được, cứ thế. Nhờ vậy mình tránh được tình huống dở khóc dở cười là một super admin lại không xem được nội dung mà một vip bình thường xem được.

Phần thứ hai là **ma trận nội dung** (public, premium, admin-only) được kiểm tra hoàn toàn ở phía backend. Cụ thể, mỗi loại nội dung gắn với một điều kiện quyền: nội dung premium cần `can_read_premium`, khu quản trị cần `can_admin`, còn các thao tác cấp cao nhất cần `can_superadmin`. Backend là nơi quyết định cho qua hay chặn, frontend không bao giờ là chốt chặn cuối cùng.

Cách tư duy "quyền là một danh sách permission cụ thể" thay vì "role là một cái nhãn" giúp mở rộng về sau dễ hơn nhiều. Khi cần thêm một quyền mới, mình chỉ việc thêm một permission và gắn nó vào các role phù hợp, chứ không phải đi sửa hàng loạt câu lệnh `if role == "admin"` nằm rải rác.

## Bài học về đăng nhập cross-site và frontend

Phần khiến mình mất thời gian nhất hóa ra lại là chuyện rất "đời": cái nút quản trị lúc hiện lúc mất, đặc biệt trên Safari và Edge.

Nguyên nhân gốc là phiên đăng nhập chỉ được lưu ở `sessionStorage` rồi gửi kèm qua header, trong khi trang tĩnh và API xác thực lại nằm ở hai tên miền khác nhau. Các trình duyệt siết chặt cookie cross-site sẽ không gửi phiên đi cùng request, dẫn đến tình trạng đăng nhập thành công nhưng quay lại trang thì hệ thống lại tưởng bạn là khách.

Cách xử lý là phát hành thêm một **cookie phiên cross-site** với đủ ba thuộc tính: `Secure`, `HttpOnly` và `SameSite=None`. Ba thứ này đi cùng nhau mới có tác dụng — thiếu `Secure` thì trình duyệt từ chối `SameSite=None`, còn `HttpOnly` giúp JavaScript phía client không đọc trộm được cookie. Cùng với đó, các lời gọi API được đặt `credentials: include` để cookie thực sự được gửi kèm.

Bài học lớn thứ hai nằm ở chỗ này: **đừng để frontend tự đoán quyền**. Trước đây, JavaScript có một danh sách username và email "super" viết cứng để tự quyết định hiển thị nút. Cách này vừa dễ sai vừa không an toàn — ai mở DevTools chỉnh biến là "tự phong" được. Sau khi dọn, toàn bộ frontend chỉ đọc danh sách permission do backend trả về qua một lời gọi `/me` được cache lại, rồi bật tắt giao diện theo đó. Việc kiểm tra thật vẫn nằm ở server, frontend chỉ phản ánh trạng thái.

Nếu bạn quan tâm tới khía cạnh xác thực danh tính nói chung, mình từng viết về [hướng dẫn xác thực CCCD trên app ngân hàng](/baochi/huong-dan-xac-thuc-cccd-msb-digital-bank/) và [cách các ngân hàng số bảo mật tài khoản](/baochi/liobank-bao-mat-an-toan-the-nao/) — cùng một tinh thần: lớp xác thực phải nằm ở nơi người dùng không can thiệp được.

## Vài lưu ý khi triển khai và kiểm thử

Một thay đổi về phân quyền luôn tiềm ẩn rủi ro làm sập quyền của ai đó, nên mình ép bản thân kiểm thử kỹ trước khi đẩy đi:

- Viết test cho từng cấp role: user thường bị chặn nội dung premium, vip xem được premium, admin vào được khu quản trị, super làm được thao tác cấp cao nhất.
- Kiểm tra cả luồng đăng nhập OAuth không bị vỡ sau khi đổi cách lưu phiên.
- Đảm bảo cookie cross-site và ma trận nội dung vẫn hoạt động đúng trên trình duyệt khó tính.

Một điểm thực tế cần nhớ với hệ thống tách rời frontend tĩnh và backend: khi bạn deploy lại trang tĩnh, **backend chưa chắc đã cập nhật theo**. Nếu API trả về cấu trúc `/me` mới mà bản backend đang chạy vẫn là bản cũ, frontend có thể hiểu sai. Vì vậy mình luôn để một lớp **fallback**: nếu API chưa trả permission theo định dạng mới thì frontend tạm dùng logic cũ để quyền không bị gãy, đồng thời có một bước kiểm tra phiên bản backend đã đồng bộ chưa trước khi coi như "xong".

## Kết lại

Nếu rút gọn cả buổi dọn dẹp thành vài câu, mình sẽ nói thế này. Phân quyền là thứ phải có **một nguồn sự thật duy nhất** — đừng để mỗi file tự định nghĩa lại. Ưu tiên role phải rõ ràng và quyền thấp là tập con của quyền cao. Backend mới là nơi chặn thật, frontend chỉ hiển thị. Và những chuyện tưởng nhỏ như cookie `SameSite=None` lại đủ sức làm hỏng cả trải nghiệm đăng nhập trên một số trình duyệt.

Đây không phải kiến thức cao siêu, nhưng là loại lỗi rất hay gặp khi sản phẩm lớn dần mà không ai dừng lại dọn nợ kỹ thuật. Hy vọng vài ghi chú này tiết kiệm được cho bạn một buổi chiều như mình đã mất.

Bạn đang xây hệ thống có nhiều cấp người dùng? Hãy thử rà lại xem logic role của mình đang nằm ở bao nhiêu chỗ — nếu nhiều hơn một, có lẽ đã đến lúc gom về một mối. Đọc thêm các bài cùng chủ đề trong chuyên mục [Công nghệ](/topic/cong-nghe/) hoặc xem toàn bộ tin tại [trang Báo chí](/categories/bao-chi/) của blog nhé.
