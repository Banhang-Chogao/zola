+++
title = "Đọc Bảng Deploy History D/B/A/F: Chẩn Đoán Deploy Status Nhanh"
description = "Cách đọc bảng deploy history với ký hiệu D/B/A/F trên Snapshot Production V2, phân biệt fail thật với run bị hủy do concurrency."
date = 2026-07-02T10:04:00+07:00
updated = 2026-07-02T10:04:00+07:00
draft = false
slug = "doc-bang-deploy-history-d-b-a-f"
[taxonomies]
categories = ["Tất cả", "Series", "Công nghệ"]
tags = ["deploy status monitoring", "deploy history", "github actions", "ci cd", "troubleshooting"]
[extra]
author = "Duy Nguyen"
seo_keyword = "đọc bảng deploy history D B A F"
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
image_alt = "Bảng deploy history với các badge trạng thái D B A F xếp theo từng dòng commit"
image_source = "seomoney-generated"
image_license = "owned"
series = "deploy-status-monitoring"
series_part = 3
series_order = 3
series_total = 6
pinned = true
pinned_label = "Bài Đáng Xem"
[[extra.faq]]
q = "Ký hiệu D/B/A/F trên bảng deploy history nghĩa là gì?"
a = "D là Deployed (đã deploy thành công, production đang phục vụ đúng commit này), B là Building (đang chạy, chưa xong), A là Awaiting (đang xếp hàng chờ runner hoặc chờ deploy khác chạy trước), F là Failed (thất bại thật sự hoặc bị hủy)."
[[extra.faq]]
q = "Thấy dòng F trên bảng deploy history có phải luôn là lỗi cần sửa ngay không?"
a = "Không hẳn. F gồm cả run bị hủy vì một deploy mới hơn đã vào cùng concurrency group — trường hợp này bình thường khi merge dồn dập. Chỉ cần lo khi F rơi đúng vào commit mới nhất và không có run D nào mới hơn thay thế nó."
[[extra.faq]]
q = "Làm sao phân biệt run bị hủy (cancelled) với run fail thật?"
a = "Kiểm tra xem có run nào cho commit mới hơn đã kết thúc với trạng thái D hay chưa. Nếu có, run F trước đó gần như chắc chắn chỉ là bị thay thế do concurrency, không phải lỗi build hay QA thật."
[[extra.faq]]
q = "Bảng deploy history hiển thị khác nhau trên desktop và mobile không?"
a = "Dữ liệu giống nhau, chỉ khác cách trình bày. Desktop hiển thị dạng bảng nhiều cột, mobile chuyển thành thẻ xếp chồng để dễ đọc trên màn hình hẹp. Trang không dùng JS phía client, toàn bộ do Zola render sẵn."
[[extra.faq]]
q = "Mục Đề xuất trên trang Snapshot Production V2 có đáng tin tuyệt đối không?"
a = "Đây là gợi ý tự động dựa trên vài quy tắc đơn giản, hữu ích để có hướng nhìn nhanh nhưng không thay thế việc tự đọc bảng deploy history và các thẻ thông tin. Khi nghi ngờ, luôn quay lại đọc dữ liệu gốc."
[[extra.faq]]
q = "Nếu một dòng A đứng yên quá lâu thì nên làm gì?"
a = "Đó là dấu hiệu có thể runner đang bị nghẽn hoặc hàng đợi deploy dồn ứ. Nên kiểm tra trực tiếp tab Actions trên GitHub thay vì đoán, vì bảng deploy history chỉ phản ánh trạng thái tại thời điểm build trang, không real-time tuyệt đối."
[[extra.references_external]]
title = "GitHub Actions — Monitoring và troubleshooting workflows"
url = "https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows/about-monitoring-and-troubleshooting"
+++

> **TL;DR:** Bảng deploy history trên [Snapshot Production V2](/tools/snapshot-production-v2/) gắn mỗi lần chạy workflow deploy với một badge D/B/A/F. D là đã lên production thật sự, B là đang chạy, A là đang chờ, F là fail hoặc bị hủy — và hai thứ trong F không giống nhau về mức độ nghiêm trọng. Đọc đúng bảng này giúp mình tránh hoảng loạn không cần thiết khi thấy màu đỏ trên màn hình.

Lần đầu nhìn bảng deploy history, mình từng phản xạ kiểu: thấy chữ F là tim đập nhanh hơn một nhịp. Sau vài tuần theo dõi thật, mình nhận ra phần lớn F không phải chuyện gì to tát — chỉ là một run bị thay thế bởi run mới hơn trong lúc merge dồn dập. Bài này mình viết lại cách đọc bảng cho đúng, để không phải cuống lên mỗi lần thấy màu đỏ.

<!-- more -->

## Bảng deploy history đang hiển thị cái gì

Mỗi dòng trong bảng ứng với một lần workflow deploy chạy — không phải một lần merge, mà một lần **chạy thật** của workflow. Thông tin đi kèm gồm:

- **Commit SHA** — rút gọn, có link thẳng tới commit trên GitHub để xem đúng đã đổi gì.
- **Tiêu đề PR** — giúp nhận ra ngay đây là thay đổi nào mà không cần bấm vào commit.
- **Nhánh** — thường là `main`, vì đó là nhánh production build ra.
- **Số thứ tự run** — để đối chiếu với tab Actions khi cần đào sâu.
- **Badge trạng thái** — một trong bốn ký hiệu D/B/A/F, gói gọn kết quả của run đó.

Trên desktop, dữ liệu này hiện dạng bảng nhiều cột, dễ quét nhanh theo hàng. Trên mobile, cùng dữ liệu đó được xếp lại thành từng thẻ chồng lên nhau — không cột ngang chật chội, đọc dọc thoải mái hơn trên màn hình nhỏ. Điểm quan trọng: đây không phải hai nguồn dữ liệu khác nhau, chỉ là hai cách trình bày cùng một tập dữ liệu, vì trang được [Snapshot Production V2](/tools/snapshot-production-v2/) render sẵn lúc build bằng Zola, không có JavaScript client nào can thiệp để đổi nội dung theo thiết bị.

Bài đầu series đã nói kỹ vì sao cần một trang như vậy — merge xong không có nghĩa production đã cập nhật, và [khoảng cách giữa merged với live](/cong-nghe/merged-khong-co-nghia-da-len-production/) chính là lý do bảng deploy history tồn tại. Nếu chưa đọc bài đó, nên đọc trước vì nó giải thích gốc rễ của vấn đề mà bảng này đang cố gắng trả lời.

## Đọc bảng deploy history: bốn trạng thái D/B/A/F nghĩa là gì

Đây là phần cốt lõi. Mỗi badge phản ánh một giai đoạn khác nhau trong vòng đời của một lần chạy workflow deploy, và ý nghĩa thực tế của chúng khác khá xa so với cảm giác đầu tiên khi nhìn màu sắc.

**D — Deployed.** Run đã hoàn tất thành công, và quan trọng hơn: production đang thật sự phục vụ đúng commit này. Đây là trạng thái duy nhất chứng minh được "live" theo đúng nghĩa — không phải "chắc là xong rồi", mà là đã xác nhận.

**B — Building.** Run đang chạy (`in_progress`), chưa kết thúc. Thấy B thì đừng vội báo "xong rồi" — nó đang ở giữa quá trình build và deploy, có thể mất vài phút tùy độ nặng của bước build.

**A — Awaiting.** Run đang xếp hàng, chờ runner rảnh hoặc chờ tới lượt sau các deploy khác đang chạy trước. Trạng thái này hay xuất hiện khi cấu hình concurrency là `cancel-in-progress: false` — tức là deploy mới không hủy deploy cũ đang chờ, mà xếp hàng nối đuôi. Trong những đợt merge dồn dập, A có thể tồn tại một lúc trước khi tới lượt chạy.

**F — Failed.** Đây là badge dễ gây hiểu lầm nhất, vì nó gộp chung hai tình huống khác hẳn nhau về mức độ nghiêm trọng:

- Run **thật sự thất bại** — lỗi build, một QA gate không pass, hoặc rate limit của Pages API cạn ngay cả sau khi đã retry.
- Run **bị hủy (cancelled)** — vì một deploy mới hơn đã tham gia cùng concurrency group và thay thế nó. Đây là hành vi bình thường trong lúc merge nhiều PR liên tiếp, không phải lỗi code hay lỗi cấu hình.

Bảng dưới đây tóm gọn lại bốn trạng thái, để lúc cần tra nhanh không phải đọc lại cả đoạn:

| Badge | Ý nghĩa | Hành động nên làm |
|-------|---------|---------------------|
| **D** | Đã deploy thành công, production đang phục vụ đúng commit | Không cần làm gì, đây là trạng thái mong muốn |
| **B** | Đang build/deploy, chưa xong | Chờ, kiểm tra lại sau vài phút |
| **A** | Đang chờ runner hoặc chờ tới lượt trong hàng đợi | Bình thường nếu ngắn; kiểm tra Actions nếu kéo dài bất thường |
| **F** | Fail thật hoặc bị hủy do concurrency | Xem có run D mới hơn không — nếu có, F cũ chỉ là bị thay thế; nếu không, cần chẩn đoán lỗi thật |

Cách phân biệt hai loại F không khó: nhìn xem có run nào cho commit **mới hơn** đã kết thúc với D hay chưa. Nếu có — run F trước đó gần như chắc chắn chỉ là bị deploy mới hơn "vượt mặt" trong concurrency group, không phải lỗi thật. Nếu không có run D nào mới hơn thay thế, và F rơi đúng vào commit mới nhất, thì đó mới là tín hiệu cần ngồi xuống chẩn đoán nghiêm túc. Tài liệu chính thức của GitHub về [monitoring và troubleshooting workflows](https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows/about-monitoring-and-troubleshooting) cũng nói rõ: `cancelled` và `failure` là hai `conclusion` khác nhau, không nên gộp chung khi phân tích.

## Quy trình đọc nhanh, không cần đoán

Sau một thời gian nhìn bảng này mỗi ngày, mình rút ra một luồng đơn giản, gần như không cần suy nghĩ:

- Dòng ứng với commit mới nhất hiện **D** → xong, không có gì phải làm.
- Dòng hiện **B** → đang chạy, quay lại kiểm tra sau vài phút, không cần refresh liên tục.
- Dòng hiện **A** và đứng yên khá lâu → có thể runner đang nghẽn hoặc hàng đợi bị dồn ứ, nên mở thẳng tab Actions trên GitHub để xem thực tế thay vì đoán qua bảng.
- Dòng ứng với commit **mới nhất** hiện **F**, và không có run D nào mới hơn thay thế → đây mới là fail thật, cần chẩn đoán nguyên nhân gốc trước khi làm gì tiếp — tuyệt đối không nên bấm retry mù mà không biết vì sao nó fail.

Luồng này giúp mình tránh được thói quen xấu nhất khi vận hành: retry lặp lại một cách vô thức chỉ vì thấy màu đỏ, trong khi vấn đề thật có thể nằm ở chỗ khác — ví dụ backend đang tụt sau main chứ không liên quan gì tới workflow deploy của site tĩnh. Trường hợp đó mình sẽ nói kỹ hơn ở phần sau của series.

## Mục "Đề xuất" — gợi ý, không phải phán quyết cuối cùng

Ngoài bảng deploy history, trang còn có một khối nhỏ liệt kê vài dòng gợi ý ngắn, kiểu như "main đã merge nhưng Pages chưa deploy", "backend tụt sau main — cần đồng bộ thủ công", hoặc "N PR đang mở chờ merge". Những dòng này được sinh tự động từ vài quy tắc đơn giản so sánh dữ liệu giữa các nguồn — không phải AI phân tích sâu, cũng không phải cảnh báo được đội ngũ vận hành xác nhận thủ công.

Nói cách khác, mục Đề xuất là lớp tóm tắt nhanh để có hướng nhìn ngay khi vừa mở trang, chứ không thay thế được việc tự đọc bảng deploy history và các thẻ thông tin gốc. Khi có gì đó không khớp giữa gợi ý và dữ liệu bảng, luôn tin bảng dữ liệu hơn — vì gợi ý chỉ là lớp diễn giải, còn bảng mới là dữ liệu thật lấy trực tiếp từ lịch sử run của workflow.

## Một tình huống thực tế: ba lần merge liên tiếp

Có một buổi chiều mình merge liền ba PR nhỏ trong vòng chưa đầy năm phút — sửa một đoạn CSS, cập nhật một bài viết, và một fix nhỏ ở script. Mở bảng deploy history lên, thấy ngay hai dòng đầu hiện **F**, dòng thứ ba hiện **D**. Phản xạ đầu tiên: "chết rồi, hai lần deploy fail liên tiếp".

Nhưng nhìn kỹ lại thì cả hai dòng F đều ứng với hai commit **cũ hơn** dòng D. Và dòng D chính là commit **mới nhất** trong ba lần merge đó. Ghép lại thì câu chuyện rất đơn giản: PR đầu tiên trigger một deploy, đang chạy dở thì PR thứ hai merge vào, deploy đầu bị hủy để nhường chỗ; deploy thứ hai cũng bị hủy tương tự khi PR thứ ba merge vào; chỉ có deploy cuối cùng — ứng với commit mới nhất — chạy trọn vẹn và ra D.

Kết luận đúng ở đây là: **mọi thứ ổn, chỉ có lần chạy cuối cùng là quan trọng.** Hai chữ F kia không cần sửa gì cả, vì chúng chưa từng đại diện cho trạng thái cuối cùng của production — chúng chỉ là những bước trung gian bị vượt mặt trong lúc dồn merge. Nếu hôm đó mình vội vàng mở PR "hotfix deploy" chỉ vì thấy hai dòng đỏ, coi như tốn công vô ích cho một việc chẳng có gì để sửa.

Đây cũng là lý do bài 1 của series nhấn mạnh nguyên tắc "merged không có nghĩa đã lên production" — nhìn bảng deploy history đúng cách là bước thực hành trực tiếp của nguyên tắc đó, chứ không phải lý thuyết suông.

Nếu muốn đọc lại toàn bộ bức tranh, quay về bài tổng quan [Snapshot Production V2: theo dõi deploy status là gì](/cong-nghe/snapshot-production-v2-theo-doi-deploy-status-la-gi/) để nắm bốn nhóm thông tin chính trên trang, hoặc ghé [các bài Công nghệ khác](/categories/cong-nghe/) nếu quan tâm thêm về vận hành site tĩnh trên GitHub Pages.

Badge D/B/A/F chỉ nói về **workflow deploy của site tĩnh** — nó không biết gì về việc backend (dịch vụ riêng chạy trên Render, phục vụ các tính năng như bình luận hay xác thực) có đang đồng bộ với main hay không. Đó là một lớp trạng thái hoàn toàn khác, và cũng là kiểu sự cố dễ bị bỏ sót nhất vì bảng deploy history vẫn có thể hiện toàn D trong khi backend đã tụt lại phía sau âm thầm. Phần tiếp theo của series sẽ nói kỹ về [cách phát hiện backend tụt sau main](/cong-nghe/backend-tut-sau-main-phat-hien-production-drift/) — đây là dạng lỗi đáng chú ý tiếp theo, vì nó không hiện rõ ràng trên bảng deploy history như F hay A.
