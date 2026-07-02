+++
title = "Snapshot Production V2: Theo Dõi Deploy Status Sau Khi Deploy"
description = "Snapshot Production V2 là gì và vì sao theo dõi deploy status ngay sau khi merge giúp phát hiện sự cố production sớm hơn, thay vì đợi người dùng báo lỗi."
date = 2026-07-02T10:06:00+07:00
updated = 2026-07-02T10:06:00+07:00
draft = false
slug = "snapshot-production-v2-theo-doi-deploy-status-la-gi"
[taxonomies]
categories = ["Tất cả", "Series", "Công nghệ"]
tags = ["deploy status monitoring", "snapshot production", "devops", "ci cd", "deploy guard", "site reliability"]
[extra]
author = "Duy Nguyen"
seo_keyword = "theo dõi deploy status sau khi deploy"
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
image_alt = "Bảng điều khiển Snapshot Production V2 hiển thị trạng thái deploy sau khi merge code"
image_source = "seomoney-generated"
image_license = "owned"
series = "deploy-status-monitoring"
series_part = 1
series_order = 1
series_total = 6
pinned = true
pinned_label = "Bài Đáng Xem"
[[extra.faq]]
q = "Snapshot Production V2 là gì?"
a = "Là một trang nội bộ tại /tools/snapshot-production-v2/, tổng hợp trạng thái deploy mới nhất: SHA main, SHA đã deploy, health backend và số PR đang mở, giúp xác nhận production đã cập nhật đúng commit hay chưa."
[[extra.faq]]
q = "Vì sao PR đã merge mà tính năng chưa thấy trên site?"
a = "Vì merge chỉ đưa code vào nhánh main; production chỉ cập nhật sau khi workflow deploy chạy xong thành công. Giữa hai bước này có độ trễ và có thể fail, nên cần một nơi xác nhận riêng thay vì đoán."
[[extra.faq]]
q = "Snapshot Production V2 lấy dữ liệu từ đâu?"
a = "Từ hai file dữ liệu build-time data/prod-snapshot.json và data/deploy-monitor.json, được workflow deploy-monitor.yml làm mới mỗi 20 phút bằng cách đọc lịch sử chạy của workflow deploy chính và endpoint /health của backend."
[[extra.faq]]
q = "Công cụ này có gọi API ngay trên trình duyệt người xem không?"
a = "Không. Toàn bộ dữ liệu được Zola render sẵn lúc build, trang không gọi GitHub API hay backend API khi người dùng mở trình duyệt, nên không phát sinh rủi ro rò rỉ token phía client."
[[extra.faq]]
q = "Ký hiệu D/B/A/F trên bảng deploy history nghĩa là gì?"
a = "D là deployed thành công, B là đang build, A là đang chờ (awaiting/queued), F là fail hoặc bị hủy. Chi tiết cách đọc từng trạng thái được giải thích riêng ở bài 3 của series này."
[[extra.faq]]
q = "Có cần cài thêm công cụ nào để dùng Snapshot Production V2 không?"
a = "Không. Trang là một phần của blog, chỉ cần mở đường link là xem được; dữ liệu tự làm mới theo lịch, không cần thao tác thủ công trừ khi muốn cập nhật ngay qua phím tắt nội bộ."
[[extra.references_external]]
title = "Google SRE Book — Monitoring Distributed Systems"
url = "https://sre.google/sre-book/monitoring-distributed-systems/"

[[extra.references_external]]
title = "DORA — DevOps Research and Assessment metrics"
url = "https://dora.dev/"

[[extra.references_external]]
title = "GitHub Actions — Giới thiệu về deployments"
url = "https://docs.github.com/en/actions/deployment/about-deployments/deploying-with-github-pages"

+++

> **TL;DR:** Merge PR không đồng nghĩa tính năng đã lên production. Snapshot Production V2 (`/tools/snapshot-production-v2/`) là trang tổng hợp trạng thái deploy build-time, giúp xác nhận nhanh: main đã deploy chưa, backend có tụt hậu không, và có PR nào đang chờ merge. Đây là bài mở đầu series 6 phần giải thích vì sao theo dõi deploy status sau khi deploy lại quan trọng đến vậy.

Mình từng gặp cảnh này nhiều lần: merge một PR xong, refresh trang mấy lần liên tiếp, không thấy gì đổi, rồi tự hỏi có phải mình vừa làm hỏng thứ gì đó không. Hóa ra không phải lỗi code — chỉ là workflow deploy chưa chạy xong, hoặc chạy xong nhưng bị rớt ở một bước không liên quan tới nội dung PR. Vấn đề không nằm ở chất lượng code, mà ở chỗ **không có nơi nào để xác nhận** trạng thái deploy thật sự, ngoài việc đoán và refresh.

<!-- more -->

## "Merged" và "Live" là hai trạng thái khác nhau

Nghe có vẻ hiển nhiên, nhưng đây là nguồn gốc của phần lớn nhầm lẫn khi vận hành một site tĩnh triển khai qua CI/CD. Một pull request đi qua ba trạng thái tách biệt:

- **Merged** — code đã nằm trên nhánh `main`. Đây là bước dễ nhất, chỉ cần CI pass và không còn conflict.
- **Deploying** — workflow build & deploy đang chạy, biến source thành file tĩnh và đẩy lên hosting.
- **Live** — production đã phục vụ đúng phiên bản mới, xác nhận được bằng cách gọi thẳng URL production và kiểm tra commit đã deploy.

Ba trạng thái này thường trôi qua trong vài phút nên người ta hay gộp chung làm một. Nhưng khi có sự cố — rate limit từ Pages API, quota GitHub Actions cạn, hay đơn giản là một batch merge dồn dập — khoảng cách giữa "merged" và "live" có thể kéo dài từ vài phút đến vài giờ mà không ai để ý, cho tới khi có người dùng report "sao tôi không thấy tính năng mới".

Nguyên tắc mình rút ra sau nhiều lần bị hố: **một PR merged chỉ là bằng chứng của ý định deploy, không phải bằng chứng deploy đã xảy ra.** Muốn biết chắc, phải kiểm tra hai thứ độc lập với PR: commit nào đang chạy trên production, và commit đó có khớp với HEAD của `main` hay không.

## Snapshot Production V2 giải quyết đúng khoảng trống đó

[Snapshot Production V2](https://seomoney.org/tools/snapshot-production-v2/) là một trang nội bộ, gom toàn bộ tín hiệu cần thiết để trả lời câu hỏi "production có đang khớp với main không" trong một lần xem, thay vì phải mở tab GitHub Actions, tab Render dashboard, rồi tab production riêng để đối chiếu tay.

Trang hiển thị bốn nhóm thông tin chính:

1. **Thanh trạng thái tổng quan** — kết quả so khớp (drift status) giữa main và bản đã deploy: xanh nếu khớp, đỏ nếu lệch, xám nếu chưa xác định được.
2. **Lưới thông tin 4 thẻ** — SHA mới nhất của `main` (kèm link GitHub), SHA đã deploy thật sự + thời điểm deploy, tình trạng backend (SHA, `/health` OK/fail, có mount đúng service comment hay không), và số lượng PR đang mở chờ merge.
3. **Bảng lịch sử deploy** — từng lần chạy workflow deploy được gắn nhãn trạng thái ngắn gọn D/B/A/F (giải thích chi tiết ở [bài 3 của series](/cong-nghe/doc-bang-deploy-history-d-b-a-f/)), kèm commit, tiêu đề PR, nhánh và số run.
4. **Đề xuất hành động** — gợi ý ngắn khi phát hiện bất thường, ví dụ "main đã merge nhưng Pages chưa deploy", "backend tụt sau main — cần đồng bộ thủ công", hoặc "N PR đang mở, cân nhắc merge đợt tiếp theo".

Điểm quan trọng về mặt kỹ thuật: trang này **không gọi API nào từ trình duyệt người xem**. Toàn bộ dữ liệu được Zola render sẵn ở thời điểm build, đọc từ hai file JSON tĩnh (`data/prod-snapshot.json` và `data/deploy-monitor.json`). Hai file này được một workflow riêng — chạy theo lịch mỗi 20 phút — làm mới bằng cách tổng hợp: SHA `main` từ git, lịch sử chạy của workflow deploy chính, và kết quả gọi `/health` tới backend. Cách làm này giữ trang nhẹ, không rò rỉ token phía client, và vẫn đủ mới để dùng cho việc theo dõi vận hành hằng ngày.

## Vì sao không thể chỉ tin vào "CI xanh là xong"

Một ngộ nhận phổ biến: nếu status check trên PR đã xanh và PR đã merge, coi như xong việc. Thực tế CI xanh chỉ xác nhận code hợp lệ ở thời điểm kiểm tra — nó không đảm bảo:

- Workflow deploy chạy **sau đó** có thành công hay không (đây là hai workflow khác nhau, chạy ở hai thời điểm khác nhau).
- Không có sự cố hạ tầng bên ngoài tầm kiểm soát của PR đó — ví dụ rate limit của Pages API, quota API theo giờ của GitHub App installation, hay một batch nhiều PR merge cùng lúc làm deploy trước đó bị hủy giữa chừng.
- Backend (nếu tách riêng khỏi site tĩnh) có được deploy đồng bộ với frontend hay không — hai hệ thống có thể lệch nhịp nếu quy trình release không gắn chặt với nhau.

Từng trường hợp trong ba gạch đầu dòng trên đều là sự cố **thật** đã xảy ra trong quá trình vận hành blog này, và không có trường hợp nào bị bắt bởi CI — vì CI chỉ kiểm tra code, không kiểm tra hạ tầng deploy. Đây chính là lý do một lớp giám sát riêng, độc lập với pipeline CI, lại cần thiết. [Bài 2 của series](/cong-nghe/merged-khong-co-nghia-da-len-production/) đi sâu vào từng kiểu sự cố này với ví dụ cụ thể.

## Theo dõi deploy status sau khi deploy: 4 tín hiệu không thể bỏ qua

Nếu chỉ có thời gian check nhanh, đây là bốn tín hiệu tối thiểu Snapshot Production V2 gom lại giúp bạn không phải tự đi tìm từng nơi:

| Tín hiệu | Câu hỏi trả lời | Vì sao quan trọng |
|---|---|---|
| SHA main vs SHA đã deploy | Production có đang chạy đúng commit mới nhất không? | Đây là bằng chứng trực tiếp duy nhất — không suy đoán qua "PR đã merge" |
| Trạng thái backend `/health` | Backend có đang sống và đúng version không? | Frontend tĩnh có thể deploy độc lập, dễ lệch nhịp với backend nếu không theo dõi |
| Bảng deploy history (D/B/A/F) | Lần deploy gần nhất thành công hay fail, đang chạy hay đang chờ? | Phát hiện fail ngay thay vì chờ người dùng report |
| Số PR đang mở | Có bao nhiêu thay đổi đang chờ được đưa lên production? | Giúp ước lượng khối lượng công việc còn tồn đọng, tránh dồn batch quá lớn |

Bốn tín hiệu này không phải lý thuyết — chúng ánh xạ trực tiếp vào bốn nhóm chỉ số mà cộng đồng DevOps Research and Assessment (DORA) khuyến nghị theo dõi cho một pipeline release lành mạnh: tần suất deploy, thời gian dẫn tới thay đổi, tỷ lệ thay đổi gây lỗi, và thời gian phục hồi sự cố. Snapshot Production V2 không tính đủ bốn chỉ số DORA một cách chính thức, nhưng cung cấp đúng dữ liệu thô cần thiết để tính hai trong số đó: tỷ lệ deploy fail và thời gian phát hiện sự cố.

## Đi sâu vào từng phần của series

Bài này là điểm khởi đầu (pillar) của series 6 phần về theo dõi deploy status. Nếu bạn mới bắt đầu, đây là lộ trình gợi ý:

- **[Bài 2 — Merged Is Not Live](/cong-nghe/merged-khong-co-nghia-da-len-production/):** giải thích chi tiết vì sao khoảng cách giữa merge và deploy thật lại tồn tại, kèm các dạng sự cố thường gặp.
- **[Bài 3 — Đọc bảng Deploy History D/B/A/F](/cong-nghe/doc-bang-deploy-history-d-b-a-f/):** hướng dẫn đọc nhanh bảng lịch sử deploy để chẩn đoán vấn đề trong vài giây.
- **[Bài 4 — Backend tụt sau main](/cong-nghe/backend-tut-sau-main-phat-hien-production-drift/):** cách phát hiện và xử lý khi backend không đồng bộ với frontend đã deploy.
- **[Bài 5 — Case study Deploy Guard](/cong-nghe/giam-deploy-fail-voi-deploy-guard-va-snapshot-production/):** số liệu thực tế cho thấy việc theo dõi deploy status giúp giảm tỷ lệ deploy fail ra sao.
- **[Bài 6 — Checklist theo dõi deploy sau khi merge](/cong-nghe/checklist-theo-doi-deploy-sau-khi-merge-den-production-200/):** quy trình từng bước, từ lúc merge tới lúc xác nhận production trả về 200 OK.

Mỗi bài đều đứng độc lập được, nhưng đọc theo thứ tự sẽ giúp bạn hình dung trọn vẹn lý do một trang tưởng chừng đơn giản như Snapshot Production V2 lại giải quyết một vấn đề vận hành rất thật.

## Áp dụng cho dự án của bạn, không chỉ blog này

Bạn không cần đúng stack Zola + GitHub Pages để áp dụng nguyên tắc này. Điều cốt lõi là: **bất kỳ pipeline deploy nào cũng nên có một nơi xác nhận trạng thái độc lập với chính pipeline đó.** Với dự án nhỏ, một trang tĩnh đọc dữ liệu build-time như Snapshot Production V2 là đủ. Với hệ thống lớn hơn, nguyên tắc tương tự thể hiện qua dashboard nội bộ, alert Slack khi drift được phát hiện, hoặc đơn giản là một job cron gọi endpoint production và so khớp version.

Điều quan trọng không phải công cụ cụ thể, mà là thói quen: sau khi merge, đừng coi task đã xong cho tới khi có bằng chứng production đã cập nhật đúng. Đó cũng chính là nguyên tắc "Merged is not live" mà cả series này xoay quanh — và là điểm khởi đầu để bạn đọc tiếp [bài 2](/cong-nghe/merged-khong-co-nghia-da-len-production/) hoặc bắt tay ngay vào [checklist thực hành ở bài 6](/cong-nghe/checklist-theo-doi-deploy-sau-khi-merge-den-production-200/) nếu muốn áp dụng luôn hôm nay.
