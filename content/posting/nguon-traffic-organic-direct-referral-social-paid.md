+++
title = "Nguồn traffic GA4: Organic, Direct, Referral, Social, Paid"
description = "Nguồn traffic trong Google Analytics GA4 gồm Organic, Direct, Referral, Social, Paid. Cách GA4 phân kênh, phân biệt User vs Traffic acquisition và đọc cho SEO."
date = 2026-06-18
aliases = ["/nguon-traffic-organic-direct-referral-social-paid/"]

[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["ga4", "google analytics", "google analytics series", "nguồn traffic", "seo"]
[extra]
thumbnail = "https://banhang-chogao.github.io/zola/img/placeholder/placeholder.svg"
seo_keyword = "nguồn traffic"
featured = false
series = "google-analytics"
series_part = 4
series_total = 5

[[extra.faq]]
q = "GA4 phân loại nguồn traffic dựa trên cái gì?"
a = "GA4 dùng Default channel grouping để gom traffic vào các kênh như Organic Search, Direct, Referral, Organic Social, Paid Search. Việc gom dựa trên cặp source/medium và các tham số UTM mà bạn gắn vào link chiến dịch. Nếu link không có thông tin nguồn, GA4 thường xếp vào Direct."

[[extra.faq]]
q = "Direct traffic có phải là khách trung thành không?"
a = "Không hẳn. Direct là kênh chứa những phiên mà GA4 không xác định được nguồn: gõ thẳng URL, mở bookmark, click link trong một số ứng dụng, hoặc traffic không gắn thẻ UTM. Vì vậy Direct giống một thùng chứa hơn là dấu hiệu chắc chắn của khách trung thành."

[[extra.faq]]
q = "User acquisition và Traffic acquisition khác nhau thế nào?"
a = "User acquisition cho biết nguồn mà người dùng đến với site lần đầu tiên, gắn với cả vòng đời của user đó. Traffic acquisition cho biết nguồn của từng phiên truy cập, kể cả khi cùng một người quay lại bằng kênh khác. Một cái nói về người, một cái nói về phiên."
+++

> 📚 **Series "10 ngày để hiểu Google Analytics" — Bài 4/5.** Ở [Bài 3](/zola/posting/engagement-rate-bounce-rate-google-analytics/) ta đã đọc *chất lượng* của traffic. Hôm nay ta trả lời câu hỏi đứng sau mọi quyết định nội dung: khách của bạn đến từ *đâu*?

Có một báo cáo mà mình mở gần như mỗi ngày: **nguồn traffic**. Lý do đơn giản — biết người đọc đến từ đâu thì mới biết nên đầu tư công sức vào kênh nào. Nhưng cũng chính báo cáo này khiến mình hiểu nhầm khá lâu, đặc biệt là cái nhãn "Direct". Bài này sẽ bóc tách năm nhóm nguồn traffic chính trong GA4 và chỉ ra mấy cái bẫy mình từng sa vào.

## GA4 phân loại nguồn traffic dựa trên cái gì

Trước khi gọi tên từng kênh, cần hiểu *cơ chế* GA4 dùng để xếp một phiên vào kênh nào. Nó dựa trên ba thứ:

- **Source (nguồn):** nơi cụ thể phiên đến từ, ví dụ `google`, `facebook.com`, `bing`.
- **Medium (phương tiện):** loại liên kết, ví dụ `organic` (tìm kiếm không trả phí), `referral` (link từ web khác), `cpc` (quảng cáo trả theo click).
- **Tham số UTM:** khi bạn gắn `utm_source`, `utm_medium`, `utm_campaign` vào link chiến dịch, GA4 đọc đúng các giá trị đó để phân kênh.

GA4 lấy cặp **source/medium** rồi đối chiếu với một bộ quy tắc gọi là **Default channel grouping** để gom thành kênh dễ đọc (Organic Search, Direct, Referral…). Bạn không phải tự phân loại — GA4 làm sẵn. Việc của bạn là *gắn UTM cho đúng* để GA4 có dữ liệu mà phân.

Một điều mình mất khá lâu mới hiểu: GA4 phân kênh theo *quy tắc cố định*, nó không "đoán" được ý định của bạn. Nếu bạn gửi một chiến dịch email mà gắn medium là `newsletter` thay vì `email`, GA4 sẽ không nhận ra đó là kênh Email theo quy tắc mặc định, mà có thể xếp nó vào nhóm khác hoặc Unassigned. Vì thế, dùng đúng *từ khoá medium chuẩn* mà Google quy ước (`organic`, `cpc`, `email`, `referral`, `affiliate`…) quan trọng hơn người ta tưởng. Sai một chữ là cả chiến dịch bị quy nhầm chỗ.

![Infographic: cách GA4 dùng source, medium và UTM để gom traffic vào các kênh](/zola/img/placeholder/placeholder-wide.svg)

## Nguồn traffic trong GA4 gồm những gì

Đây là các kênh bạn sẽ gặp nhiều nhất, kèm ý nghĩa thực tế cho một blog:

- **Direct (Trực tiếp):** phiên mà GA4 *không có thông tin nguồn* — người gõ thẳng URL, mở bookmark, click link trong một số app, hoặc traffic không gắn thẻ. Đây thực chất là *thùng chứa những gì GA không xác định được*, không nên hiểu là "toàn fan trung thành".
- **Organic Search (Tìm kiếm tự nhiên):** người đến từ kết quả tìm kiếm *không trả phí* (Google, Bing…). **Đây là chỉ số quan trọng nhất với SEO.**
- **Paid Search (Tìm kiếm trả phí):** đến từ quảng cáo trên trang kết quả tìm kiếm (Google Ads).
- **Organic Social (Mạng xã hội tự nhiên):** đến từ bài đăng không trả phí trên Facebook, X, LinkedIn…
- **Paid Social (Mạng xã hội trả phí):** đến từ quảng cáo chạy trên mạng xã hội.
- **Referral (Giới thiệu):** đến từ *link trên một website khác* trỏ về bạn — báo, blog bạn bè, diễn đàn.
- **Email:** đến từ link trong newsletter/email bạn gửi (cần gắn UTM medium `email`).
- **Display / Video / Affiliates:** quảng cáo banner, video, hoặc link tiếp thị liên kết.

Với một blog mới, ba kênh mình theo sát nhất là **Organic Search** (sức khoẻ SEO), **Organic Social** (sức lan toả), và **Referral** (ai đang dẫn link về mình).

Có một mẹo nhỏ giúp phân biệt nhanh: nhìn vào *medium*. Medium `organic` là tìm kiếm tự nhiên, `cpc` hoặc `ppc` là quảng cáo trả phí theo click, `referral` là link từ web khác, `email` là từ newsletter, còn `(none)` đi kèm source `(direct)` chính là kênh Direct. Khi mở báo cáo ở chế độ xem *Session source / medium*, bạn sẽ thấy đúng các cặp này — đó là dữ liệu thô mà GA4 dựa vào để gom kênh. Khi nghi ngờ một kênh bị phân sai, mình luôn quay về xem cặp source/medium gốc thay vì tin ngay cái nhãn kênh đã gom.

## User acquisition vs Traffic acquisition

Trong GA4, mục Acquisition có *hai* báo cáo nghe na ná nhau nhưng trả lời hai câu hỏi khác hẳn. Phân biệt được hai cái này là bạn đã hơn rất nhiều người dùng GA4.

- **User acquisition:** nguồn mà người dùng đến với site **lần đầu tiên**. Nguồn này gắn với *cả vòng đời* của user đó. Nếu lần đầu họ tới từ Organic Search, thì mọi lượt sau vẫn ghi nhận user này "thuộc về" Organic Search trong báo cáo User acquisition.
- **Traffic acquisition:** nguồn của **từng phiên** truy cập. Cùng một người, lần đầu vào từ Google (organic), lần sau vào từ link Facebook bạn share — thì hai phiên này được tính cho hai kênh khác nhau.

Khi nào dùng cái nào? Mình dùng **User acquisition** khi muốn biết *kênh nào kéo người lạ về blog* (đo độ phủ, đo hiệu quả thu hút khách mới). Còn **Traffic acquisition** khi muốn biết *kênh nào đang tạo ra lượt truy cập gần đây* (đo nhịp traffic hằng ngày, đánh giá một chiến dịch vừa chạy).

![Infographic: phân biệt User acquisition theo người và Traffic acquisition theo phiên](/zola/img/placeholder/placeholder-wide.svg)

## Đọc nguồn traffic để đánh giá SEO

Vì series này hướng nhiều tới blogger và người làm SEO, mình tập trung phần này.

Chỉ số cốt lõi là **tỉ trọng và xu hướng của Organic Search**. Mình không nhìn con số tuyệt đối một ngày, mà nhìn *đường xu hướng* qua nhiều tuần: organic đang tăng đều, đi ngang, hay tụt? Một blog khoẻ về SEO sẽ thấy organic chiếm phần ngày càng lớn trong tổng traffic.

Tiếp theo, mình kết hợp với **landing page** — trong báo cáo Traffic acquisition hoặc Engagement, xem *trang nào* đang nhận organic. Nó cho biết bài nào đang lên hạng và kéo khách. Từ đó quyết định nên viết thêm bài cùng cụm chủ đề.

Cuối cùng, GA4 không phải tất cả. Để hiểu *người ta gõ từ khoá gì* trước khi vào bài, bạn cần ghép thêm **Google Search Console** — công cụ cho biết truy vấn, vị trí trung bình, tỉ lệ click. GA4 nói *sau khi vào site họ làm gì*, Search Console nói *họ tìm gì để vào*. Hai cái bổ trợ nhau.

Nếu bạn chưa nắm chắc cách Google xếp hạng, nên đọc song song [SEO là gì](/zola/posting/seo-la-gi-huong-dan-co-ban-google-search/) và [Google Search hoạt động thế nào](/zola/posting/google-search-hoat-dong-the-nao/) — hiểu vế tìm kiếm thì đọc Organic Search trong GA4 mới có chiều sâu.

## Bốn hiểu lầm phổ biến về nguồn traffic

Đây là phần mình ước có ai nói sớm cho mình:

1. **Tưởng Direct = khách trung thành.** Sai. Direct gồm cả traffic *untagged* và cái người ta hay gọi là "dark social" — link share qua tin nhắn, ứng dụng chat, app không truyền thông tin nguồn. Direct phình to thường là dấu hiệu bạn *quên gắn UTM*, chứ chưa chắc là fan đông.
2. **Không gắn UTM cho chiến dịch.** Gửi newsletter, chạy bài mạng xã hội mà không gắn `utm_source`/`utm_medium` thì GA4 không biết quy về đâu, dễ rơi vào Direct hoặc bị phân sai. Gắn UTM nhất quán là việc nhỏ nhưng cứu cả báo cáo.
3. **Self-referral.** Khi một phần website của bạn (ví dụ cổng thanh toán, subdomain) trỏ về site chính mà chưa cấu hình loại trừ, GA4 tính nó là *referral* từ chính bạn — làm nhiễu số liệu. Cần khai báo các domain nội bộ vào danh sách loại trừ.
4. **Nhầm Organic Social với Organic Search.** Hai cái đều có chữ "Organic" nhưng khác hẳn: một bên là *mạng xã hội* không trả phí, một bên là *tìm kiếm* không trả phí. Đánh giá SEO mà nhìn nhầm sang Organic Social thì kết luận sai hoàn toàn.

Mình từng dính cả bốn. Sau khi gắn UTM bài bản và loại trừ self-referral, báo cáo nguồn traffic của mình mới thật sự đáng tin.

## Một ví dụ đọc báo cáo nguồn traffic

Để thấy cách ghép mọi thứ lại, giả sử trong một tháng blog của mình có phân bổ traffic như bảng dưới (đây chỉ là *ví dụ* minh hoạ, không phải số liệu thật):

| Kênh | Sessions (ví dụ) | Tỉ trọng | Mình đọc ra điều gì |
|------|------------------|----------|---------------------|
| Organic Search | 1.200 | 48% | SEO đang là trụ chính, sức khoẻ tốt |
| Direct | 700 | 28% | Hơi cao — nghi ngờ untagged/dark social |
| Organic Social | 350 | 14% | Vài bài lan toả trên mạng xã hội |
| Referral | 180 | 7% | Có web khác bắt đầu dẫn link về |
| Email | 70 | 3% | Newsletter còn nhỏ, cần nuôi thêm |

Đọc bảng này mình rút ra mấy việc cụ thể. Thứ nhất, **Organic chiếm gần một nửa** là tín hiệu mừng cho SEO, nên tiếp tục đầu tư nội dung cụm chủ đề đang lên. Thứ hai, **Direct cao tới 28%** khiến mình giật mình — nhiều khả năng do mình share link qua tin nhắn mà *không gắn UTM*, nên cần sửa thói quen này để biết thực chất traffic đó từ đâu. Thứ ba, **Referral đang nhú lên** — mình sẽ vào xem cụ thể *website nào* đang dẫn link, để cảm ơn hoặc tìm thêm cơ hội hợp tác.

Điểm mấu chốt: con số tuyệt đối ít quan trọng bằng *tỉ trọng* và *xu hướng theo thời gian*. Một kênh tăng đều qua nhiều tháng đáng giá hơn một con số to nhưng nhất thời.

## Bảng tổng hợp các kênh

| Kênh | Nguồn điển hình | Bạn học được gì |
|------|-----------------|-----------------|
| Organic Search | google, bing (medium `organic`) | Sức khoẻ SEO, bài nào lên hạng |
| Direct | gõ URL, bookmark, untagged | Độ nhận diện thương hiệu (đọc thận trọng) |
| Referral | link từ web/báo/blog khác | Ai đang dẫn link về bạn |
| Organic Social | facebook, x, linkedin (không trả phí) | Nội dung lan toả tự nhiên tới đâu |
| Paid Search / Paid Social | Google Ads, quảng cáo MXH | Hiệu quả tiền quảng cáo |
| Email | newsletter gắn UTM `email` | Danh sách email hoạt động ra sao |

## Bảng tóm tắt

| Khái niệm | Một câu để nhớ |
|-----------|----------------|
| Default channel grouping | Quy tắc GA4 gom traffic theo source/medium |
| Organic Search | Tìm kiếm không trả phí — chỉ số SEO quan trọng nhất |
| Direct | Phiên không rõ nguồn — *không* mặc nhiên là fan trung thành |
| User acquisition | Nguồn của user **lần đầu** |
| Traffic acquisition | Nguồn của **từng phiên** |
| UTM | Tham số bạn gắn để GA4 quy nguồn cho đúng |

## Bước tiếp theo

Giờ bạn đọc được *bao nhiêu người, chất lượng ra sao, đến từ đâu*. Mảnh ghép cuối là biến tất cả thành một *thói quen*: mở GA4 mỗi ngày 15 phút và biết chính xác cần nhìn gì. Đó là bài khép lại series.

👉 **Đọc tiếp:** [Bài 5 — Đọc báo cáo Google Analytics 15 phút mỗi ngày](/zola/posting/doc-bao-cao-google-analytics-15-phut-moi-ngay/). Muốn ôn lại nền tảng thì quay về [Bài 1](/zola/posting/google-analytics-la-gi-lo-trinh-10-ngay/), hoặc xem cả series trong chuyên mục [Công nghệ](/zola/categories/cong-nghe/).

*Nguồn tham khảo: [Google Analytics Help — Default channel group](https://support.google.com/analytics/answer/9756891) và tài liệu chính thức về [User acquisition và Traffic acquisition](https://support.google.com/analytics/answer/12922327).*
