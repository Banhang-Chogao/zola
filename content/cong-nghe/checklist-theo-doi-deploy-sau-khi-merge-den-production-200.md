+++
title = "Checklist Theo Dõi Deploy Sau Khi Merge: Đến Khi Production Trả 200 OK"
description = "Checklist từng bước theo dõi deploy sau khi merge PR, tới khi production trả về 200 OK — áp dụng được cho mọi stack, không chỉ Zola."
date = 2026-07-02T10:01:00+07:00
updated = 2026-07-02T10:01:00+07:00
draft = false
slug = "checklist-theo-doi-deploy-sau-khi-merge-den-production-200"
[taxonomies]
categories = ["Tất cả", "Series", "Công nghệ"]
tags = ["deploy status monitoring", "checklist", "post-deploy verification", "ci cd", "devops"]
[extra]
author = "Duy Nguyen"
seo_keyword = "checklist theo dõi deploy sau khi merge"
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
image_alt = "Checklist từng bước xác nhận deploy sau khi merge cho tới khi production trả về HTTP 200"
image_source = "seomoney-generated"
image_license = "owned"
series = "deploy-status-monitoring"
series_part = 6
series_order = 6
series_total = 6
pinned = true
pinned_label = "Bài Đáng Xem"
[[extra.faq]]
q = "Vì sao cần cả một checklist, không phải chỉ nhìn CI xanh là đủ?"
a = "Vì CI xanh chỉ xác nhận code hợp lệ tại thời điểm kiểm tra, còn deploy là một quy trình riêng chạy sau đó, có thể fail vì lý do không liên quan tới code (rate limit, quota, batch merge chồng nhau). Checklist gom lại đúng những điểm có thể lệch để không bỏ sót bước nào."
[[extra.faq]]
q = "Nếu không dùng Snapshot Production V2 thì kiểm tra deploy bằng cách nào?"
a = "Về bản chất chỉ cần ba việc: gọi thẳng URL production bằng curl -I để xem status code, xem lịch sử run của workflow CI/CD ứng với đúng commit SHA, và đối chiếu commit đó với HEAD của nhánh chính. Có thể làm thủ công hoặc dựng một trang trạng thái đơn giản đọc từ một file JSON cập nhật theo lịch."
[[extra.faq]]
q = "Route mới đã có trong content nhưng vẫn 404 trên production thì kiểm tra gì trước?"
a = "Kiểm tra theo thứ tự: file output cho route đó đã sinh ra trong thư mục build chưa, commit đó đã thực sự nằm trong lần deploy gần nhất chưa, và menu/nav có trỏ đúng đường dẫn không. Phần lớn trường hợp 404 sau merge là do thiếu một trong ba điều này, không phải lỗi code."
[[extra.faq]]
q = "Khi thấy deploy bị stale, có nên bấm retry ngay không?"
a = "Không nên retry mù. Nên đọc lại trạng thái D/B/A/F trước — nếu là A (đang chờ) do rate limit thì retry sẽ tự khỏi sau khi quota hồi, nếu là F (fail thật) do lỗi build thì retry chỉ lặp lại lỗi. Chẩn đoán trước khi hành động tiết kiệm thời gian hơn nhiều so với bấm lại nhiều lần."
[[extra.faq]]
q = "Ai nên dùng checklist này — chỉ con người hay cả AI agent cũng áp dụng được?"
a = "Cả hai. Với con người, đây là thói quen tránh báo 'xong việc' quá sớm. Với AI agent tự động hóa deploy, checklist này có thể biến thành điều kiện dừng bắt buộc trước khi agent được phép báo cáo một tính năng đã live."
[[extra.references_external]]
title = "Google SRE Book — Release Engineering"
url = "https://sre.google/sre-book/release-engineering/"
+++

> **TL;DR:** Merge xong không có nghĩa là xong việc. Bài này gom lại thành một checklist thực hành: từ lúc PR merge, qua lúc deploy chạy, tới lúc gọi thẳng URL production và thấy đúng nội dung mới — kèm mẫu báo cáo để tự xác nhận (hoặc bắt AI agent xác nhận) trước khi nói "đã live". Đây là bài khép lại series 6 phần về theo dõi deploy status.

Năm bài trước trong series này mỗi bài xoáy vào một kiểu sự cố riêng: [khoảng cách giữa merge và deploy thật](/cong-nghe/merged-khong-co-nghia-da-len-production/), [cách đọc bảng lịch sử deploy](/cong-nghe/doc-bang-deploy-history-d-b-a-f/), [backend tụt lại phía sau frontend](/cong-nghe/backend-tut-sau-main-phat-hien-production-drift/), và [số liệu thực tế sau khi thêm lớp giám sát](/cong-nghe/giam-deploy-fail-voi-deploy-guard-va-snapshot-production/). Bài này không lặp lại từng chi tiết đó — nó gộp tất cả thành một quy trình duy nhất, đủ ngắn để chạy mỗi lần merge mà không thấy phiền.

<!-- more -->

## Vì sao cần checklist, không phải chỉ "tin tưởng công cụ"

Có công cụ tốt như [Snapshot Production V2](https://seomoney.org/tools/snapshot-production-v2/) vẫn chưa đủ nếu không có thói quen dùng nó đúng lúc. Mình từng bỏ qua bước cuối — gọi thẳng URL production — vì nghĩ "dashboard xanh rồi, chắc ổn", rồi phát hiện ra route mới vẫn 404 vì file build chưa sinh đúng chỗ. Dashboard không sai, mình chỉ dừng lại sớm hơn cần thiết.

Ba trạng thái merged, deploying, live không tự động nối tiếp nhau trong đầu người xem — phải chủ động kiểm tra từng nấc. Checklist bên dưới chính là cách ép bản thân (hoặc ép một AI agent đang làm thay) không bỏ bước nào, dù đang vội tới đâu.

## Checklist theo dõi deploy sau khi merge

Đây là phần cốt lõi của bài — một chuỗi bước theo đúng thứ tự thời gian, từ lúc PR còn mở tới lúc xác nhận production.

| # | Bước | Xác nhận bằng gì | Đạt khi |
|---|------|-------------------|---------|
| 1 | PR đã thực sự merge vào nhánh chính | Trạng thái PR trên GitHub (`merged`, không chỉ `approved`) | PR hiện badge "Merged", không còn ở trạng thái chờ merge |
| 2 | Workflow deploy cho commit đó đã bắt đầu chạy | Tab Actions / bảng deploy history | Có một run mới xuất hiện, không kẹt ở trạng thái A (chờ) quá lâu |
| 3 | Workflow deploy kết thúc thành công **cho đúng SHA** | Conclusion của run, đối chiếu SHA | Trạng thái D (deployed) gắn với đúng commit vừa merge, không phải run cũ |
| 4 | File output cho route mới đã sinh ra (nếu có route/page mới) | Kiểm tra thư mục build sau khi build xong | File output tương ứng route đó tồn tại trong thư mục build (ví dụ `public/<route>/index.html` với site tĩnh Zola) |
| 5 | Gọi thẳng URL production, không qua cache | `curl -I` hoặc mở tab ẩn danh | HTTP 200 OK, nội dung đúng phiên bản mới, không phải trang cache cũ hay 404 |
| 6 | Backend (nếu tách riêng) đồng bộ với frontend mới | Version/health của backend | Version backend khớp với điều frontend mới cần — xem thêm [bài 4](/cong-nghe/backend-tut-sau-main-phat-hien-production-drift/) nếu nghi ngờ lệch |
| 7 | Chỉ lúc này mới báo "đã live" | Toàn bộ 6 bước trên đã pass | Có bằng chứng cụ thể cho từng bước, không phải suy đoán |

Một bước "bonus" đáng nhắc riêng: nếu bước 2 hoặc 3 cho kết quả bất thường (kẹt ở A quá lâu, hoặc F), đừng bấm retry ngay lập tức. Đọc lại ký hiệu D/B/A/F theo [bài 3](/cong-nghe/doc-bang-deploy-history-d-b-a-f/) để biết đây là rate limit tạm thời, bị hủy vì một run mới hơn thay thế, hay lỗi build thật sự — mỗi nguyên nhân cần một cách xử lý khác nhau, retry mù chỉ tổ mất thời gian và có thể che mất lỗi thật.

Bảy bước này không cần công cụ đặc thù để làm — [Snapshot Production V2](https://seomoney.org/tools/snapshot-production-v2/) chỉ gom nhiều bước trong số đó vào một màn hình cho nhanh, nhưng bản chất từng bước vẫn làm tay được với bất kỳ stack nào.

## Mẫu báo cáo bắt buộc — bằng chứng, không phải cảm giác "chắc xong rồi"

Cách hiệu quả nhất để không bỏ bước là buộc bản thân điền vào một mẫu cố định trước khi coi task đã xong. Mẫu này áp dụng được cho cả người lẫn AI agent đang tự động hóa phần deploy:

```text
Route/feature: ...
Deployed commit: ...
Build output exists: Yes/No
Production URL status: ...
Live verified: Yes/No
```

Lý do mẫu này hữu ích không nằm ở format, mà ở chỗ nó **ép phải có dữ liệu thật** cho từng dòng. Không thể điền "Live verified: Yes" nếu chưa thật sự gọi URL production và nhìn thấy status code. Sai lầm phổ biến nhất — kể cả với AI agent — là báo "xong rồi" ngay sau khi thấy PR merged, trong khi deploy còn đang chạy hoặc chưa chạy. Một dòng report trống hoặc "chưa kiểm tra" trong mẫu này là tín hiệu rõ ràng: còn việc chưa làm, đừng báo cáo vội.

## Áp dụng checklist này khi không có Snapshot Production V2

Không có trang tổng hợp riêng cũng không sao — ba việc dưới đây làm tay là đủ để phủ gần hết bảy bước ở trên.

**Kiểm tra status code trực tiếp:**

```bash
curl -I https://your-production-url/route/
```

Nhìn dòng đầu tiên trả về — `HTTP/2 200` là ổn, `404` nghĩa là route chưa lên hoặc sai đường dẫn, `301/302` cần theo redirect xem đích cuối có đúng không.

**Đối chiếu commit SHA với lịch sử CI/CD:**

Vào phần lịch sử run của nền tảng CI/CD đang dùng (GitHub Actions, GitLab CI, CircleCI...), tìm run ứng với đúng commit SHA vừa merge, xem conclusion là success hay failure. Đừng chỉ nhìn run mới nhất — nếu có nhiều commit merge liên tiếp, run mới nhất chưa chắc đúng commit bạn quan tâm.

**Dựng một trang trạng thái nội bộ đơn giản:**

Nếu muốn tái sử dụng cho nhiều lần sau, một job chạy theo lịch (cron) ghi lại SHA đã deploy + kết quả gọi `/health` vào một file JSON tĩnh, rồi một trang nhỏ đọc file đó để hiển thị, là đủ để có bản rút gọn của Snapshot Production V2 mà không cần hạ tầng phức tạp. Cuốn Site Reliability Engineering của Google có một chương riêng nói về release engineering theo hướng này — đáng đọc nếu muốn hiểu sâu hơn phần lý thuyết đằng sau thói quen thực hành ở trên.

## Khép lại series: 6 bài, 1 thói quen

Nếu bạn mới đọc tới bài này mà chưa qua các bài trước, đây là bản đồ nhanh:

- **[Bài 1 — Snapshot Production V2 là gì](/cong-nghe/snapshot-production-v2-theo-doi-deploy-status-la-gi/):** giới thiệu công cụ và lý do ba trạng thái merged/deploying/live cần tách bạch.
- **[Bài 2 — Merged Is Not Live](/cong-nghe/merged-khong-co-nghia-da-len-production/):** các dạng sự cố khiến merge xong mà chưa lên production.
- **[Bài 3 — Đọc bảng Deploy History D/B/A/F](/cong-nghe/doc-bang-deploy-history-d-b-a-f/):** cách đọc nhanh trạng thái deploy để chẩn đoán đúng nguyên nhân.
- **[Bài 4 — Backend tụt sau main](/cong-nghe/backend-tut-sau-main-phat-hien-production-drift/):** phát hiện production drift khi backend và frontend lệch nhịp.
- **[Bài 5 — Case study Deploy Guard](/cong-nghe/giam-deploy-fail-voi-deploy-guard-va-snapshot-production/):** số liệu thực tế sau khi thêm lớp giám sát này vào quy trình.

Theo dõi deploy status không phải một lần sửa xong là xong mãi — nó là thói quen lặp lại mỗi lần merge, giống như đánh răng chứ không phải một dự án có ngày kết thúc. Nếu chỉ mang đi một thứ từ cả series này, hãy mang checklist bảy bước ở trên: dán nó vào quy trình review hoặc template PR của bạn ngay hôm nay, và đừng gõ chữ "done" cho tới khi cả bảy dòng đều có bằng chứng thật, không phải phỏng đoán. Muốn xem cách blog này áp dụng đúng nguyên tắc đó mỗi ngày, quay lại [trang giới thiệu Snapshot Production V2](/cong-nghe/snapshot-production-v2-theo-doi-deploy-status-la-gi/) hoặc ghé qua [các bài Công nghệ khác](/categories/cong-nghe/) để đọc thêm về vận hành CI/CD.
