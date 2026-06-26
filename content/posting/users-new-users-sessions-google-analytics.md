+++
title = "Users, New Users và Sessions trong Google Analytics"
description = "Users, New Users và Sessions trong Google Analytics khác nhau thế nào? Mình giải thích bằng ví dụ thực tế và mách bạn khi nào nên nhìn chỉ số nào trên GA4."
date = 2026-06-18
aliases = ["/users-new-users-sessions-google-analytics/"]

[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["ga4", "google analytics", "google analytics series", "sessions", "users"]
[extra]
thumbnail = "https://banhang-chogao.github.io/zola/img/placeholder/placeholder.svg"
seo_keyword = "users new users và sessions"
featured = false
series = "google-analytics"
series_part = 2
series_total = 5

[[extra.faq]]
q = "Users và Sessions khác nhau thế nào?"
a = "Users là số người dùng (thiết bị) duy nhất, còn Sessions là số phiên truy cập. Một user có thể tạo nhiều session khi quay lại nhiều lần, nên Sessions thường lớn hơn hoặc bằng Users."

[[extra.faq]]
q = "New Users được tính khi nào trong GA4?"
a = "New Users là số người dùng tương tác với site lần đầu tiên, được GA4 ghi nhận qua sự kiện first_visit (web) hoặc first_open (app). Con số này phụ thuộc vào khoảng thời gian bạn chọn trong báo cáo."

[[extra.faq]]
q = "Vì sao Active Users của tôi nhỏ hơn Total Users?"
a = "Trong GA4, Total Users là tổng người dùng duy nhất, còn Active Users chỉ tính người có phiên tương tác (engaged session). Báo cáo chuẩn của GA4 lấy Active Users làm chỉ số 'Users' chính, nên nó có thể nhỏ hơn Total Users."
+++

> 📚 **Series "10 ngày để hiểu Google Analytics" — Bài 2/5.** Ở [Bài 1](/zola/posting/google-analytics-la-gi-lo-trinh-10-ngay/) mình đã dựng bản đồ tổng thể. Hôm nay ta soi kỹ ba con số mà mình tin là gây nhầm lẫn nhiều nhất cho người mới.

Hồi đầu mình cứ tưởng "100 users" nghĩa là 100 lượt vào web. Sai. Rồi mình lại tưởng "New Users" là người chưa từng biết blog mình. Cũng không hẳn. Ba chỉ số **Users, New Users và Sessions** nghe đơn giản nhưng định nghĩa của chúng trong GA4 có vài cái bẫy. Hiểu sai từ đây thì mọi kết luận phía sau đều lệch.

## Phân biệt Users, New Users và Sessions

Hãy bắt đầu bằng định nghĩa gọn nhất:

- **Users (người dùng):** số người dùng *duy nhất* truy cập site, nhận diện qua client ID lưu trong cookie. Cùng một người mở blog 5 lần trong tuần vẫn là **1 user**.
- **New Users (người dùng mới):** số user *tương tác với site lần đầu* trong khoảng thời gian bạn chọn. GA4 đánh dấu bằng sự kiện `first_visit`.
- **Sessions (phiên):** số *lượt truy cập*. Một user quay lại 3 lần (cách nhau hơn 30 phút không hoạt động) tạo ra **3 sessions**.

Mối quan hệ điển hình: **Sessions ≥ Users ≥ New Users**. Nếu thấy ngược lại, gần như chắc chắn bạn đang đọc nhầm khoảng thời gian hoặc nhầm cột.

![Infographic: sơ đồ 1 user tạo nhiều session và mối quan hệ Users vs Sessions](/zola/img/placeholder/placeholder-wide.svg)

## Một cái bẫy của GA4: Total Users vs Active Users

Đây là chỗ khác biệt lớn so với Universal Analytics. GA4 có hai khái niệm người dùng:

- **Total Users:** tổng số người dùng duy nhất.
- **Active Users:** người dùng có *phiên tương tác* (engaged session) — tức ở lại đủ lâu, xem nhiều trang, hoặc kích hoạt sự kiện chuyển đổi.

Điểm cần nhớ: trong hầu hết báo cáo chuẩn, GA4 hiển thị **Active Users** dưới nhãn "Users". Đó là lý do đôi khi con số "Users" trông nhỏ hơn bạn tưởng — nó đã lọc ra những lượt ghé rồi thoát ngay. Universal Analytics trước đây lấy Total Users làm mặc định, nên người quen UA hay giật mình khi chuyển sang GA4.

## Ví dụ thực tế cho dễ hình dung

Giả sử trong một tuần, blog của mình có dữ liệu như sau:

| Chỉ số | Giá trị (ví dụ) | Ý nghĩa |
|--------|-----------------|---------|
| Total Users | 120 | 120 người duy nhất từng ghé |
| Active Users | 100 | 100 người thực sự *tương tác* |
| New Users | 70 | 70 người lần đầu vào blog |
| Sessions | 150 | 150 lượt truy cập |

Đọc bảng này mình hiểu được: có **70/100 người là khách mới** (kênh thu hút đang chạy tốt), và **150 sessions / 100 users = 1,5 phiên/người** — tức nhiều người quay lại hơn một lần. Nếu tỉ lệ phiên trên người dùng cao và lượng khách quay lại lớn, đó là tín hiệu nội dung giữ chân tốt.

Lưu ý quan trọng về **New Users**: con số này gắn với *khoảng thời gian báo cáo*. Một người lần đầu vào blog tháng trước, tháng này quay lại, thì trong báo cáo *tháng này* họ là **returning user**, không phải new user. Vậy nên đừng cộng dồn New Users của 12 tháng rồi bảo "blog có ngần đó người biết tới" — sẽ đếm trùng.

## Khi nào nên nhìn chỉ số nào

Mỗi con số trả lời một câu hỏi khác nhau. Mình hay tự hỏi *mình đang muốn biết điều gì* trước khi chọn cột:

| Bạn muốn biết… | Nhìn chỉ số | Vì sao |
|-----------------|-------------|--------|
| Nội dung mới có kéo người lạ về không? | **New Users** | Phản ánh khả năng tiếp cận, độ phủ |
| Site có giữ chân, có khách trung thành không? | **Returning Users / Active Users** | Phản ánh chất lượng & độ dính |
| Quy mô traffic tổng | **Sessions** | Đếm số lượt truy cập thực tế |
| Trung bình mỗi người ghé bao nhiêu lần | **Sessions / Users** | Đo mức độ quay lại |

Với một blog đang muốn lớn, mình ưu tiên theo dõi **New Users** (để biết tuyến nội dung nào kéo khách mới) song song với **tỉ lệ quay lại**. Chỉ nhìn Sessions dễ ru ngủ: số to nhưng nếu toàn người vào rồi thoát thì chẳng có giá trị.

![Infographic: bảng quyết định nên xem chỉ số nào theo mục tiêu](/zola/img/placeholder/placeholder-wide.svg)

## Cách xem ba chỉ số này trong GA4

Lý thuyết là vậy, còn trên giao diện thì tìm ở đâu? Mình hay đi theo đường này:

- **Tổng quan nhanh:** *Reports → Reports snapshot* hoặc *Reports → Acquisition → User acquisition*. Ở đây có ngay New Users và tổng người dùng.
- **So sánh Users và Sessions:** mở *Acquisition → Traffic acquisition*. Báo cáo này liệt kê Sessions theo kênh; bạn thêm cột hoặc đổi chỉ số để thấy cả Users.
- **Tùy biến sâu:** dùng *Explore* (Khám phá) để tự kéo các chỉ số Total Users, Active Users, New Users, Sessions vào cùng một bảng và chọn khoảng thời gian. Đây là cách mình kiểm chứng quan hệ "Sessions ≥ Users ≥ New Users" trên chính dữ liệu của mình.

Mẹo nhỏ: luôn để ý **bộ chọn khoảng thời gian** ở góc trên. Đổi từ "7 ngày" sang "28 ngày" là cả ba con số nhảy hết — và New Users nhảy mạnh nhất, vì khung thời gian càng rộng thì càng nhiều người được tính là "mới trong khoảng đó".

## Lỗi thường gặp khi đọc Users và Sessions

Vài cái bẫy mình từng mắc, kể ra để bạn né:

1. **Cộng dồn New Users qua nhiều tháng.** Như đã nói, một người có thể là "mới" ở tháng này và "cũ" ở tháng sau. Cộng dồn sẽ đếm trùng và thổi phồng độ phủ.
2. **So Users của GA4 với Search Console.** Search Console đếm *click* từ kết quả tìm kiếm Google, GA4 đếm *user/phiên* có tag chạy. Hai con số gần như không bao giờ khớp tuyệt đối — đừng coi đó là lỗi.
3. **Quên rằng chặn cookie làm hụt số.** Người dùng từ chối cookie hoặc dùng trình duyệt chặn tracking có thể không được đếm đầy đủ. GA4 vẫn ước lượng, nhưng con số tuyệt đối không nên xem là chân lý — *xu hướng* mới là thứ đáng tin.
4. **Nhìn Sessions mà quên chất lượng.** Số phiên to chưa chắc tốt. Phải ghép với nhóm chỉ số engagement ở bài sau mới biết phiên đó "có giá trị" hay chỉ vào rồi thoát.

## Bảng tóm tắt

| Khái niệm | Một câu để nhớ |
|-----------|----------------|
| Users | Người dùng duy nhất (1 người ghé 5 lần = 1 user) |
| Total Users | Tổng người dùng duy nhất |
| Active Users | Người có phiên *tương tác* — nhãn "Users" mặc định của GA4 |
| New Users | Người vào lần đầu trong *khoảng thời gian báo cáo* |
| Sessions | Số lượt truy cập (hết hạn sau 30 phút không hoạt động) |

## Bước tiếp theo

Bài này cho bạn cách đếm *bao nhiêu người* và *bao nhiêu lượt*. Nhưng số lượng chưa nói lên chất lượng: 1.000 sessions mà ai cũng thoát sau 2 giây thì không bằng 200 sessions đọc hết bài. Đó chính là việc của nhóm chỉ số *engagement* — chủ đề bài kế tiếp.

Nếu bạn quan tâm tới việc kéo **New Users** từ Google, hãy đọc thêm [SEO là gì](/zola/posting/seo-la-gi-huong-dan-co-ban-google-search/) để hiểu nguồn organic — bài 4 của series sẽ nối hai mạch này lại.

👉 **Đọc tiếp:** [Bài 3 — Engagement Rate, Average Engagement Time và Bounce Rate nói gì về nội dung của bạn?](/zola/posting/engagement-rate-bounce-rate-google-analytics/). Quay lại [Bài 1](/zola/posting/google-analytics-la-gi-lo-trinh-10-ngay/) hoặc xem cả series trong chuyên mục [Công nghệ](/zola/categories/cong-nghe/).

*Nguồn tham khảo: [Google Analytics Help — User metrics](https://support.google.com/analytics/answer/12253918) và tài liệu chính thức về [Active users trong GA4](https://support.google.com/analytics/answer/12253918).*
