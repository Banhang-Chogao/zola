+++
title = "Merged Is Not Live: Vì Sao PR Merge Xong Chưa Chắc Đã Lên Production"
description = "PR đã merged không có nghĩa đã lên production — tìm hiểu 3 trạng thái deploy và cách Snapshot Production V2 kiểm chứng thật."
date = 2026-07-02T10:05:00+07:00
updated = 2026-07-02T10:05:00+07:00
draft = false
slug = "merged-khong-co-nghia-da-len-production"
[taxonomies]
categories = ["Tất cả", "Series", "Công nghệ"]
tags = ["deploy status monitoring", "merged is not live", "ci cd", "github actions", "production"]
[extra]
author = "Duy Nguyen"
seo_keyword = "merged is not live production"
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
image_alt = "Sơ đồ minh họa khoảng cách giữa một PR đã merged và một bản deploy thực sự live trên production"
image_source = "seomoney-generated"
image_license = "owned"
series = "deploy-status-monitoring"
series_part = 2
series_order = 2
series_total = 6
pinned = true
pinned_label = "Bài Đáng Xem"
[[extra.faq]]
q = "PR merged rồi thì bao lâu sau mới lên production?"
a = "Không có con số cố định. Thường chỉ mất vài phút nếu workflow deploy chạy trơn tru, nhưng nếu gặp rate limit từ API hoặc bị một merge khác chen ngang, thời gian có thể kéo dài hoặc thậm chí không tự chạy lại nếu không có cơ chế giám sát. Cách chắc chắn nhất là kiểm tra SHA đã deploy thay vì đoán theo thời gian."

[[extra.faq]]
q = "Làm sao biết chắc một commit đã thực sự lên production chứ không chỉ merged vào main?"
a = "So sánh SHA của commit mới nhất trên nhánh main với SHA mà GitHub Pages (hoặc hạ tầng deploy đang dùng) báo cáo là đã deploy. Nếu hai SHA khớp nhau, đó là bằng chứng thật. PR hiện trạng thái 'Merged' chỉ nói lên việc code đã vào main, không nói gì về việc đã build và deploy xong chưa."

[[extra.faq]]
q = "Tại sao CI xanh (pass) mà production vẫn chưa cập nhật?"
a = "CI kiểm tra code tại thời điểm merge — build thử, chạy test, lint. Việc deploy thật sự diễn ra sau đó, trên một workflow khác, chạy trên hạ tầng khác (ví dụ GitHub Pages API). Workflow deploy có thể fail vì lý do hoàn toàn không liên quan tới nội dung PR, như rate limit hoặc bị một deploy khác huỷ ngang."

[[extra.faq]]
q = "cancel-in-progress trong GitHub Actions gây ra vấn đề gì với deploy?"
a = "Khi concurrency group của workflow deploy đặt cancel-in-progress: true, một merge mới sẽ huỷ luôn deploy đang chờ chạy của merge trước đó. Nếu nhiều PR merge dồn dập, deploy cuối cùng có thể không bao giờ chạy tới nơi, để lại main ở trạng thái chưa được deploy mà không ai biết."

[[extra.faq]]
q = "Snapshot Production V2 có gọi API lúc người dùng mở trang không?"
a = "Không. Trang được render sẵn lúc build bằng Zola, đọc dữ liệu từ hai file JSON đã được một workflow theo lịch làm mới mỗi 20 phút. Nhờ vậy trang tải nhanh, không phụ thuộc API còn sống lúc người xem truy cập, và vẫn phản ánh đúng trạng thái deploy gần nhất."
[[extra.references_external]]
title = "GitHub REST API — Deployment statuses"
url = "https://docs.github.com/en/rest/deployments/statuses"
+++

> **TL;DR:** PR hiện chữ "Merged" màu tím trên GitHub không có nghĩa là code đó đã chạy trên production. Giữa merged và live còn một bước deploy, và bước đó có thể fail vì rate limit, bị huỷ ngang bởi merge khác, hoặc đơn giản là chưa chạy tới. Cách duy nhất để biết chắc là so SHA đã deploy với SHA mới nhất trên main — đúng như cách [Snapshot Production V2](/tools/snapshot-production-v2/) đang làm.

Mình từng report với sếp (thật ra là tự report với chính mình, vì đây là blog cá nhân) rằng một route mới "đã live" chỉ vì thấy PR merge thành công. Hai tiếng sau mở URL thật ra vẫn 404. Từ đó mình mới hiểu merged và live là hai chuyện hoàn toàn khác nhau, và viết loạt bài này một phần cũng để tự nhắc bản thân đừng lặp lại sai lầm đó.

<!-- more -->

## Ba trạng thái: merged, đang deploy, và live

Nhìn tưởng đơn giản nhưng thực ra có ba trạng thái tách biệt, và vấn đề nằm ở chỗ hầu hết chúng ta chỉ theo dõi trạng thái đầu tiên.

- **Merged** — PR đã được gộp vào nhánh `main`. Đây là sự kiện xảy ra trên GitHub, không liên quan gì tới hạ tầng chạy site thật.
- **Đang deploy** — một workflow (ví dụ `deploy.yml`) được kích hoạt sau khi push vào `main`, build lại toàn bộ site, rồi gọi API của nền tảng hosting (GitHub Pages, Render, Vercel...) để đẩy bản build mới lên.
- **Live** — request thật tới URL production trả về đúng nội dung mới. Đây mới là trạng thái người dùng cuối quan tâm.

Vấn đề là bước giữa — đang deploy — hoàn toàn có thể fail mà không ai để ý, vì giao diện PR trên GitHub chỉ hiện "Merged", nó không tự động cập nhật lại thành "chưa deploy được" khi workflow sau đó gặp sự cố. Người xem PR nhìn vào chữ tím đó và mặc định mọi thứ đã xong.

Đây chính là lý do rule nội bộ của repo này có một dòng khá thẳng: **"Merged is not live."** Với mọi route hoặc page public mới, task chỉ được coi là hoàn thành khi cả file build tồn tại lẫn URL production trả về HTTP 200 — không phải khi PR chuyển màu tím.

## Những lần khoảng cách này từng xảy ra thật

Đây không phải chuyện giả định để minh hoạ cho vui. Repo blog này (chạy trên GitHub Pages, build bằng Zola) từng dính đúng kiểu lỗi "merged nhưng chưa live" vài lần, và mỗi lần đều để lại một bài học cụ thể.

**Rate limit ở bước cấu hình Pages.** Khi nhiều PR merge dồn trong thời gian ngắn — mấy bot refresh dữ liệu, cộng vài PR nội dung merge cùng lúc — quota API theo giờ của GitHub App installation bị cạn. Bước `configure-pages` trong workflow deploy báo lỗi "API rate limit exceeded for installation". Điều đáng nói là `zola build` vẫn pass bình thường, lỗi nằm hoàn toàn ở khâu gọi Pages API, không phải ở code. Cách sửa là thay action gọi Pages bằng một request tự viết có cơ chế lùi theo cấp số nhân: thử lại 3 lần với khoảng chờ 10 giây, rồi 20 giây, rồi 40 giây.

**Rate limit lặp lại ở chính bước deploy.** Sau khi vá xong bước `configure-pages`, tưởng đã xong, nhưng hoá ra bước deploy thật sự (`actions/deploy-pages`) — cái gọi API tạo deployment — cũng dính đúng loại lỗi rate limit, và bước này lại không có retry nội bộ nào cả. Build job pass, `configure-pages` cũng pass, nhưng job deploy vẫn đỏ. Bài học ở đây khá quan trọng: rate limit của một installation ảnh hưởng tới **mọi** lời gọi API Pages trong cùng một lần chạy, không chỉ một bước duy nhất. Giải pháp là thêm một chuỗi 3 lần thử với thời gian chờ 0, 60, rồi 120 giây riêng cho bước deploy.

**Batch merge huỷ ngang deploy đang chờ.** Đây là kiểu lỗi âm thầm nhất. Workflow deploy dùng concurrency group để tránh chạy chồng lên nhau, nhưng cấu hình ban đầu đặt `cancel-in-progress: true` — nghĩa là mỗi lần có merge mới, deploy đang chờ chạy của lần merge trước bị huỷ ngay lập tức để nhường chỗ cho lần mới. Nghe hợp lý cho tới khi nhiều PR merge liên tiếp trong vài phút: deploy của merge đầu bị huỷ bởi merge thứ hai, deploy của merge thứ hai lại bị huỷ bởi merge thứ ba... Kết quả là có một PR đã merge thành công nhưng commit của nó chưa bao giờ thực sự lên GitHub Pages, và không có cảnh báo nào báo cho biết điều đó. Người vận hành phải tự soát tay từng trường hợp để phát hiện ra.

Cách sửa cho vấn đề thứ ba gồm hai phần: đổi `cancel-in-progress` thành `false` để deploy xếp hàng thay vì bị huỷ, và thêm một workflow "Deploy Guard" chạy mỗi giờ, tự kiểm tra xem SHA mới nhất trên `main` có thật sự khớp với SHA đang chạy trên production không — nếu lệch, tự động kích hoạt lại deploy mà không cần ai can thiệp thủ công.

Bảng dưới tóm tắt lại ba sự cố cho dễ nhớ:

| Sự cố | Bước bị ảnh hưởng | Cách vá |
|---|---|---|
| Rate limit khi cấu hình Pages | `configure-pages` | Retry lùi cấp số nhân: 10s → 20s → 40s |
| Rate limit khi deploy thật | `actions/deploy-pages` | Retry riêng: 0 → 60s → 120s |
| Batch merge huỷ ngang deploy | Toàn bộ workflow deploy | `cancel-in-progress: false` + Deploy Guard chạy hàng giờ |

## Vì sao CI xanh không đồng nghĩa đã lên production

Mình nghĩ gốc rễ của sự nhầm lẫn này nằm ở chỗ CI và deploy trông giống nhau trên giao diện GitHub — đều là mấy dấu tick xanh — nhưng bản chất khác hẳn nhau.

CI (kiểm tra QA, build thử, lint) chạy **tại thời điểm PR**, trên chính commit của PR đó, để trả lời câu hỏi "code này có an toàn để merge không". Nó không biết gì về hạ tầng hosting, không biết quota API còn bao nhiêu, không biết có PR nào khác đang merge cùng lúc.

Deploy thì chạy **sau khi đã merge**, trên nhánh `main`, gọi tới hạ tầng bên ngoài (GitHub Pages API, CDN, DNS...) — những thứ hoàn toàn nằm ngoài phạm vi mà CI kiểm tra được. Một PR có thể vượt qua toàn bộ CI với nội dung code hoàn hảo, nhưng vẫn kẹt lại ở bước deploy vì lý do chẳng liên quan gì tới nội dung PR cả.

Nói cách khác: CI xanh chứng minh code không vỡ. Deploy thành công mới chứng minh code đang chạy thật. Hai chứng minh này độc lập với nhau, và chỉ tin vào cái đầu là chưa đủ.

## Snapshot Production V2 thu hẹp khoảng cách này thế nào

Đây là lý do mình xây [Snapshot Production V2](/tools/snapshot-production-v2/) — một trang được giới thiệu kỹ ở [bài mở đầu series](/cong-nghe/snapshot-production-v2-theo-doi-deploy-status-la-gi/). Ý tưởng cốt lõi rất đơn giản: đừng tin vào trạng thái PR, hãy nhìn thẳng vào bằng chứng deploy thật.

Trang này được render sẵn lúc build (Zola, không gọi API phía client), đọc dữ liệu từ hai file: `data/prod-snapshot.json` và `data/deploy-monitor.json`. Một workflow theo lịch làm mới hai file này mỗi 20 phút. Nhờ cách làm này, trang tải cực nhanh và không phụ thuộc việc API còn sống lúc người xem mở trang lên.

Những gì trang hiển thị:

- **SHA của main HEAD** so với **SHA đã thực sự deploy** — đây là bằng chứng duy nhất đáng tin, không phải chữ "Merged" trên PR.
- **Tình trạng backend** (còn sống hay không).
- **Lịch sử deploy** với các badge trạng thái D/B/A/F — phần này được giải thích chi tiết ở [bài đọc bảng deploy history](/cong-nghe/doc-bang-deploy-history-d-b-a-f/) trong series.
- **Số PR đang mở** — để biết còn bao nhiêu thay đổi chưa vào main.

Cách tiếp cận này khớp với cơ chế mà GitHub cung cấp qua [Deployment statuses API](https://docs.github.com/en/rest/deployments/statuses) — mỗi deployment có một chuỗi trạng thái (queued, in_progress, success, failure...) độc lập với trạng thái merge của PR. Việc kiểm tra SHA đã deploy chính là cách thực hành đúng tinh thần của API đó, chỉ khác là mình gói nó lại thành một trang dễ nhìn thay vì phải tự gọi API mỗi lần muốn kiểm tra.

## Quy tắc xác nhận trước khi báo "đã live"

Từ mấy lần bị hố, giờ mình áp dụng một checklist ngắn cho mọi route hoặc page public mới trước khi dám nói "xong":

1. Kiểm tra workflow deploy gần nhất đã chạy xong chưa, và chạy thành công.
2. Xác nhận commit vừa deploy có bao gồm đúng thay đổi mình cần (không phải một commit cũ hơn).
3. Chạy build local để chắc chắn file output tồn tại đúng vị trí mong đợi.
4. Gửi request trực tiếp tới URL production và chỉ tin khi nhận được HTTP 200.

Chỉ khi cả bốn bước trên đều pass thì mới được phép nói route đó đã live. Bỏ qua bước 4 — tức chỉ dựa vào "PR đã merge" — chính là nguyên nhân của gần như mọi lần báo cáo sai mà mình từng gặp.

Nếu muốn xem một tình huống thực tế áp dụng đúng cách kiểm tra này, cùng với con số cụ thể trước và sau khi vá các lỗi rate limit và batch merge, phần tiếp theo của series — [bài case study về giảm deploy fail](/cong-nghe/giam-deploy-fail-voi-deploy-guard-va-snapshot-production/) — sẽ đi sâu vào đó. Ngoài ra, trang [changelog](/changelog/) của blog cũng là một nguồn tham khảo hay: nó liệt kê các PR vừa merge gần đây kèm trạng thái deploy và kết quả xác minh trực tiếp trên production, tức là một dạng "Production Dashboard" thu nhỏ áp dụng đúng nguyên tắc merged-is-not-live này.

Bài kế tiếp trong loạt, phần 6, sẽ gói gọn toàn bộ quy trình thành một checklist thực hành ngắn gọn tại [checklist theo dõi deploy sau khi merge đến production](/cong-nghe/checklist-theo-doi-deploy-sau-khi-merge-den-production-200/) — hữu ích nếu bạn muốn có sẵn một danh sách để dán vào quy trình release của chính mình. Nếu quan tâm thêm về hạ tầng và công cụ vận hành blog, có thể ghé qua [các bài Công nghệ khác](/categories/cong-nghe/) trên blog này.
