+++
title = "Giảm Deploy Fail Từ Hàng Chục Xuống Gần 0: Case Study Deploy Guard"
description = "Case study nội bộ: 4 fix nhỏ giúp giảm deploy fail rõ rệt, và vì sao Deploy Guard chỉ chứng minh được hiệu quả nhờ có Snapshot Production V2 theo dõi."
date = 2026-07-02T10:02:00+07:00
updated = 2026-07-02T10:02:00+07:00
draft = false
slug = "giam-deploy-fail-voi-deploy-guard-va-snapshot-production"
[taxonomies]
categories = ["Tất cả", "Series", "Công nghệ"]
tags = ["deploy status monitoring", "deploy guard", "case study", "ci cd reliability", "devops"]
[extra]
author = "Duy Nguyen"
seo_keyword = "giảm deploy fail deploy guard"
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
image_alt = "Biểu đồ minh họa số lần deploy fail giảm dần sau khi thêm Deploy Guard giám sát"
image_source = "seomoney-generated"
image_license = "owned"
series = "deploy-status-monitoring"
series_part = 5
series_order = 5
series_total = 6
pinned = true
pinned_label = "Bài Đáng Xem"
[[extra.faq]]
q = "Deploy Guard là gì?"
a = "Là một workflow nội bộ chạy theo lịch mỗi giờ (và thêm khi có sự kiện workflow_run) để kiểm tra commit mới nhất trên main đã thực sự lên production hay chưa. Nếu phát hiện lệch, nó tự động dispatch lại workflow deploy thay vì chờ ai đó phát hiện thủ công."
[[extra.faq]]
q = "Vì sao cancel-in-progress: true lại làm mất deploy?"
a = "Vì trong lúc merge nhiều PR liên tiếp, một deploy run đang chờ chạy có thể bị hủy bởi run mới hơn trước khi nó kịp thực thi. Nếu run bị hủy đó là run duy nhất mang commit thật sự cần lên production, kết quả là commit đó không bao giờ được deploy dù PR đã merge."
[[extra.faq]]
q = "Con số giảm 60-100 lần fail mỗi năm lấy từ đâu?"
a = "Đây là ước tính nội bộ dựa trên tần suất sự cố tương tự từng ghi nhận trước khi có các fix, không phải số liệu audit từ bên ngoài. Mình nêu rõ để không gây hiểu nhầm đây là benchmark ngành."
[[extra.faq]]
q = "Vì sao cancelled deploy từng bị hiểu nhầm là fail?"
a = "Vì dashboard nội bộ trước đây gán mọi trạng thái không phải success thành success: false, nên một deploy bị hủy do có run mới hơn thay thế (chuyện bình thường) hiện lên y hệt màu đỏ như một deploy fail thật. Sau khi thêm field status_normalized, cancelled được tách riêng thành màu trung tính."
[[extra.faq]]
q = "Nếu không có Snapshot Production V2 thì 4 fix này có còn giá trị không?"
a = "Vẫn có, nhưng sẽ không ai chứng minh được chúng thực sự hoạt động. Cả 4 fix đều là cải thiện âm thầm phía sau workflow; phải có một nơi hiển thị trạng thái deploy theo thời gian thì mới so sánh trước/sau và biết chắc số lần fail có giảm hay không."
[[extra.faq]]
q = "Team khác không dùng GitHub Pages/GitHub Actions có áp dụng được bài học này không?"
a = "Được, vì bản chất bài học không nằm ở công cụ cụ thể mà ở nguyên tắc: đừng để queue âm thầm rớt việc, có cơ chế tự phát hiện lệch giữa main và production, xử lý rate limit bằng retry thay vì fail ngay, và phân biệt rõ cancelled với failed trên mọi dashboard giám sát."
[[extra.references_external]]
title = "DORA — Four Keys metrics guide"
url = "https://dora.dev/guides/dora-metrics-four-keys/"
+++

> **TL;DR:** Đây là case study thật từ chính blog này: một PR đã merge (#1125) từng biến mất khỏi production vì `cancel-in-progress: true` âm thầm hủy đúng deploy run cần chạy. Team mình vá bằng 4 fix — queue thay vì hủy, Deploy Guard tự phát hiện lệch, retry khi API rate limit, và tách rõ cancelled với failed trên dashboard. Ước tính nội bộ: giảm 60-100 lần fail/năm, MTTR giảm 50-95%. Nhưng điểm mấu chốt là: không có [Snapshot Production V2](/tools/snapshot-production-v2/) để nhìn thấy kết quả, 4 fix này mãi mãi chỉ là "chắc là tốt hơn" chứ không ai chứng minh được.

Mình từng viết ở [bài 2 của series này](/cong-nghe/merged-khong-co-nghia-da-len-production/) về khoảng cách giữa "merged" và "live". Bài đó nói về hiện tượng. Bài này là chuyện đã thực sự xảy ra trên blog này, và cách team mình xử lý nó — kèm số liệu ước tính, không phải lý thuyết suông.

<!-- more -->

## Sự cố bắt đầu mọi thứ

PR #1125 merge xong xuôi. Check xanh, không ai nghi ngờ gì. Nhưng khi kiểm tra lại, tính năng trong PR đó không hề xuất hiện trên production. Không phải build lỗi, không phải code sai — commit đó **chưa bao giờ được deploy**.

Nguyên nhân nằm ở một dòng cấu hình nhỏ trong workflow deploy: `cancel-in-progress: true` trên concurrency group. Nghe thì hợp lý — merge dồn dập thì hủy run cũ, chạy run mới nhất cho nhanh, đỡ tốn tài nguyên CI. Nhưng thực tế lại khác:

- Nhiều PR merge liên tiếp trong thời gian ngắn (batch merge).
- Mỗi lần merge kích hoạt một deploy run mới.
- Run đang **chờ** (pending, chưa kịp chạy) bị run mới hơn hủy ngay lập tức.
- Nếu run bị hủy đó lại là run duy nhất mang đúng commit cần lên production, thì commit đó **rớt khỏi hàng đợi vĩnh viễn** — không ai deploy lại nó nữa trừ khi có commit mới đè lên.

Vấn đề không phải build vỡ hay lỗi code. Vấn đề là cơ chế "hủy run cũ để chạy run mới" tưởng như tối ưu tài nguyên, lại âm thầm bỏ sót đúng cái cần làm. Và vì không có nơi nào xác nhận "commit X đã deploy hay chưa", team phải **kiểm tra thủ công từng trường hợp** mỗi khi nghi ngờ có gì đó không đúng. Cách này rõ ràng không scale khi tần suất merge tăng lên.

## Bốn fix, và fix nào giải quyết vấn đề gì

Sau khi xác định gốc rễ, team mình xử lý theo bốn hướng riêng biệt. Mỗi fix nhắm vào một lớp lỗi khác nhau — không có fix nào là "giải pháp toàn diện" một mình.

| Fix | Vấn đề giải quyết | Cách hoạt động |
|---|---|---|
| **Queue thay vì hủy** | Deploy run bị hủy giữa chừng khi merge dồn dập, làm rớt commit | Đổi `cancel-in-progress: true` → `false`. Deploy run mới không hủy run cũ nữa, mà xếp hàng chờ tới lượt. Đảm bảo commit mới nhất trên main sớm muộn cũng được deploy, đổi lại là queue có thể chờ lâu hơn khi traffic merge cao. |
| **Deploy Guard** | Không ai chủ động phát hiện khi main và production lệch nhau | Workflow riêng, chạy theo lịch mỗi giờ + phản ứng thêm khi có sự kiện `workflow_run`. Nó so sánh HEAD của main với commit đã thực sự deploy; lệch thì tự dispatch lại workflow deploy — biến việc "phải có người để ý" thành vòng lặp tự chữa lành. |
| **Retry khi rate limit** | Bước `configure-pages` fail với lỗi "API rate limit exceeded for installation" trong lúc merge dồn dập | GitHub App installation có quota API theo giờ; nhiều PR/push tự động cùng lúc dễ chạm ngưỡng. Fix bằng 3 lần thử với exponential backoff (10s → 20s → 40s) thay vì fail ngay lập tức. |
| **Chuẩn hóa trạng thái dashboard** | Deploy bị `cancelled` (bình thường, chỉ là bị run mới thay thế) hiển thị y hệt màu đỏ như deploy fail thật | Thêm field `status_normalized` (success/failed/cancelled/skipped/in_progress). Cancelled hiện màu trung tính/cảnh báo, chỉ trạng thái `failed` thật mới bị đánh dấu lỗi. |

Có một điểm đáng nói riêng về fix retry rate limit: lúc đầu team chỉ vá ở bước `configure-pages` vì đó là chỗ log lỗi hiện ra đầu tiên. Nhưng sau đó, đúng nguyên nhân gốc (rate limit của cùng một installation) lại xuất hiện ở một bước khác — `deploy-pages` — vì bước này gọi API tạo deployment riêng, không dùng chung cơ chế retry với bước kia. Phải thêm một chuỗi retry tương tự (lần này 0 → 60s → 120s) cho đúng bước đó mới xử lý dứt điểm.

Bài học ở đây khá đơn giản nhưng dễ bị bỏ qua: **sửa xong điểm lỗi hiện ra trước mắt không có nghĩa đã sửa hết mọi chỗ cùng nguyên nhân gốc có thể lộ ra**. Rate limit của một API dùng chung có thể chạm ở nhiều bước khác nhau trong cùng một pipeline, và mỗi bước cần được xử lý riêng.

## Ước tính tác động — và vì sao mình nói "ước tính"

Đây là số nội bộ, dựa trên tần suất sự cố tương tự từng quan sát được trước và sau khi áp các fix trên. Không phải audit từ bên thứ ba, không phải benchmark ngành — mình nói rõ để tránh ai đó trích dẫn nhầm thành số liệu chính thức:

- Ước tính giảm khoảng **60–100 lần deploy fail mỗi năm**.
- MTTR (thời gian trung bình để phát hiện và khắc phục sự cố) giảm khoảng **50–95%** — chủ yếu nhờ Deploy Guard tự phát hiện thay vì chờ người báo.
- Tỷ lệ tin cậy CI (CI reliability) cải thiện từ khoảng **46.7% lên hơn 65%**.

Cách đọc các con số này đúng đắn nhất là nhìn qua lăng kính DORA. Theo [hướng dẫn Four Keys của DORA](https://dora.dev/guides/dora-metrics-four-keys/), hai trong bốn chỉ số cốt lõi để đánh giá hiệu suất delivery chính là **change failure rate** (tỷ lệ thay đổi gây lỗi) và **time to restore service** (thời gian khôi phục dịch vụ). Cả hai chỉ số đó đều được cải thiện trực tiếp bởi bốn fix ở trên — không phải vì code chạy nhanh hơn, mà vì pipeline ít rớt việc hơn và tự phát hiện lệch nhanh hơn.

Điều quan trọng cần nhấn mạnh: những con số này **chỉ có ý nghĩa nếu có cách đo trước/sau**. Nếu team mình chỉ nói "chắc là ổn hơn rồi" mà không có dữ liệu lịch sử deploy để so sánh, thì tất cả chỉ là cảm giác, không phải bằng chứng.

## Monitoring là thứ biến "chắc là tốt hơn" thành "đã chứng minh"

Đây là phần mình nghĩ hay bị bỏ qua nhất khi làm reliability engineering: fix xong một sự cố dễ, nhưng **chứng minh fix đó có tác dụng thật lại khó hơn nhiều**, đặc biệt khi fix nằm sâu trong workflow, không có UI trực tiếp để nhìn thấy kết quả.

[Snapshot Production V2](/tools/snapshot-production-v2/) — công cụ mình giới thiệu ở phần đầu series — chính là lớp hiển thị giúp bốn fix trên trở nên có thể kiểm chứng:

- Nhờ có nó, team mới **nhận ra** số lượng cảnh báo giả giảm hẳn sau khi fix chuẩn hóa trạng thái dashboard — trước đó, mỗi lần có deploy `cancelled` là một lần ai đó hoảng hốt tưởng production sập.
- Nhờ có nó, team mới **xác nhận** được deploy vẫn tới đích production ngay cả trong những đợt merge dồn dập, sau khi đổi sang cơ chế queue.
- Nhờ có nó, team mới **thấy** retry rate-limit thực sự chạy thành công thay vì cả pipeline chết lặng không rõ lý do.

Nói cách khác: cả bốn fix đều là cải thiện nằm bên trong workflow, người dùng cuối không nhìn thấy, và bản thân team cũng sẽ không nhìn thấy nếu không có một bề mặt giám sát riêng để theo dõi theo thời gian. Không có công cụ theo dõi, mọi cải thiện âm thầm này chỉ là "hy vọng nó tốt hơn" — không ai kiểm chứng được.

Đây cũng là lý do trang [changelog](/changelog/) của blog này công khai lịch sử PR đã merge kèm trạng thái deploy và xác minh production — không chỉ để nội bộ theo dõi, mà để bất kỳ ai cũng có thể tự kiểm tra một tính năng đã thật sự lên production hay chưa, thay vì chỉ tin vào "PR đã merge".

## Bài học cho team khác — kể cả không dùng đúng stack này

Bốn fix trên gắn với GitHub Actions và GitHub Pages cụ thể, nhưng nguyên tắc phía sau thì dùng được ở bất kỳ pipeline CI/CD nào:

1. **Đừng để cơ chế "tối ưu" âm thầm bỏ sót việc cần làm.** `cancel-in-progress` nghe hợp lý nhưng có thể hủy đúng thứ cần chạy — kiểm tra kỹ mọi cấu hình concurrency trước khi tin nó an toàn.
2. **Có cơ chế tự phát hiện lệch, đừng chờ người báo.** Một job chạy định kỳ so sánh trạng thái mong muốn với trạng thái thực tế, rồi tự sửa nếu lệch — rẻ hơn nhiều so với việc con người phải nhớ kiểm tra thủ công.
3. **Rate limit là lỗi tạm thời, không phải lỗi vĩnh viễn.** Retry với backoff gần như luôn tốt hơn fail ngay, và nhớ kiểm tra xem cùng một nguyên nhân gốc có xuất hiện ở nhiều điểm khác trong pipeline không.
4. **Phân biệt rõ "bị hủy" và "thất bại" trên mọi dashboard.** Gộp hai trạng thái này làm một là cách nhanh nhất để tạo ra báo động giả liên tục, khiến người vận hành dần bỏ qua cảnh báo thật.
5. **Không có giám sát thì không có bằng chứng.** Fix bao nhiêu cũng được, nhưng nếu không đo được trước/sau, sẽ không ai biết chắc nó có tác dụng.

Muốn tìm hiểu sâu hơn về cách đọc trạng thái deploy history hay cách công cụ này ghép dữ liệu, có thể xem thêm ở [các bài Công nghệ khác](/categories/cong-nghe/) trên blog, hoặc quay lại [bài mở đầu series](/cong-nghe/snapshot-production-v2-theo-doi-deploy-status-la-gi/) để nắm tổng quan trước khi đọc case study này.

Case study này là ví dụ cụ thể, nhưng để áp dụng đều đặn thì cần biến nó thành thói quen lặp lại được — không thể mỗi lần deploy lại nhớ lại từng bài học một cách rời rạc. Đó là lý do [bài cuối cùng của series](/cong-nghe/checklist-theo-doi-deploy-sau-khi-merge-den-production-200/) sẽ gói toàn bộ những gì đã nói ở 5 bài trước thành một checklist theo dõi deploy ngắn gọn, dùng được ngay sau mỗi lần merge.
