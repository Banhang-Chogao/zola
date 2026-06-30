+++
title = "Nano Banana 2 Lite và Gemini Omni Flash: Google DeepMind mở cửa tạo ảnh siêu nhanh và video AI"
date = 2026-07-01T16:00:00+07:00
description = "Google DeepMind vừa ra mắt Nano Banana 2 Lite (tạo ảnh 4 giây, $0.034/1K ảnh) và Gemini Omni Flash (tạo video hội thoại). Mình tìm hiểu và tổng hợp những thứ đáng chú ý nhất."
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["google deepmind", "nano banana", "gemini omni flash", "ai image generation", "ai video", "nano banana 2 lite", "gemini api", "google ai studio"]
[extra]
seo_keyword = "Nano Banana 2 Lite Gemini Omni Flash"
thumbnail = "/img/og-fallbacks/og-fallback-7.svg"
toc = true
+++

Tuần này Google DeepMind vừa có hai bản phát hành khiến mình khá hào hứng: **Nano Banana 2 Lite** — mô hình tạo ảnh nhanh nhất và rẻ nhất của họ từ trước tới nay, và **Gemini Omni Flash** — đưa khả năng tạo video hội thoại ra tay các nhà phát triển.

Mình đã dành thời gian đọc tài liệu, so sánh số liệu và suy nghĩ về bức tranh tổng thể. Bài này mình sẽ chia sẻ lại những gì tìm hiểu được — không phải bản dịch thông cáo báo chí, mà là góc nhìn của một người đang theo dõi mảng AI tạo sinh.

<!-- more -->

## Nano Banana 2 Lite: Tạo ảnh 4 giây, giá không thể rẻ hơn

Khi Nano Banana 2 ra mắt hồi tháng 2 năm nay, mình đã khá ấn tượng với chất lượng ảnh so với tốc độ. Nhưng Google DeepMind vẫn thấy chưa đủ — họ muốn thứ gì đó còn nhanh hơn, rẻ hơn cho những tác vụ mà tốc độ là ưu tiên số một.

**Nano Banana 2 Lite** (tên API `gemini-3.1-flash-lite-image`) là câu trả lời. Mỗi ảnh chỉ mất **4 giây** để sinh, và giá chỉ **$0.034 cho 1.000 ảnh** — tức chưa tới 35 đô la cho 1 triệu ảnh. Con số này khiến nó trở thành mô hình tạo ảnh rẻ nhất của Google từ trước đến nay.

Điểm mình thấy thú vị là Google không hạ thấp chất lượng để đạt tốc độ. Họ tuyên bố Nano Banana 2 Lite vẫn giữ được:

- **Prompt adherence** ổn định — làm theo đúng yêu cầu
- **Character consistency** — giữ nhận dạng nhân vật xuyên suốt
- **In-image text rendering** — chữ trong ảnh đọc được

Tất nhiên, Lite không hỗ trợ độ phân giải cao như các anh lớn trong nhà (chỉ 1K, không có 2K hay 4K), và cũng không có Thinking mode như Nano Banana 2. Nhưng nếu bạn cần tạo ảnh hàng loạt, prototyping nhanh, hoặc chạy pipeline với ngân sách eo hẹp, thì đây là lựa chọn số một.

Google cũng khuyến nghị thẳng thừng: nếu bạn đang dùng Nano Banana 1 cũ (`gemini-2.5-flash-image`), hãy chuyển sang Lite ngay — chất lượng tốt hơn, nhanh hơn và rẻ hơn.

### Đặt trong bối cảnh gia đình Nano Banana

Đọc tài liệu của Google mới thấy họ phân hoá dòng sản phẩm khá rõ ràng:

- **Nano Banana 2 Lite** — tối ưu tốc độ, giá rẻ, khối lượng lớn
- **Nano Banana 2** — con ngựa chiến đa năng, cân bằng chất lượng-giá
- **Nano Banana Pro** — studio-quality, cho tác vụ phức tạp cần độ chính xác cao

Cả ba đều có chỗ đứng riêng. Lite không phải là bản rẻ tiền, nó là bản **chuyên dụng cho một loại workload cụ thể**: nơi tốc độ và chi phí là ràng buộc khó nhất.

## Gemini Omni Flash: Tạo video bằng hội thoại

Đây là phần làm mình phấn khích nhất.

**Gemini Omni Flash** (`gemini-omni-flash-preview`) là mô hình tạo video của Google DeepMind, và giờ nó đã có trong tay các nhà phát triển qua Gemini API và Google AI Studio.

Điểm đặc biệt của Omni Flash không chỉ là tạo video — mà là **chỉnh sửa video bằng ngôn ngữ tự nhiên** (conversational editing). Bạn có thể nói "thêm chữ chào mừng ở đầu video" hay "đổi màu nền thành xanh dương" và nó làm theo. Nghe giống như chỉnh ảnh với Nano Banana, nhưng lần này là video.

Một số thông số mình tổng hợp được:

| Thông số | Giá trị |
|----------|---------|
| Giá | $0.10/giây video output |
| Độ dài tối đa | 10 giây (hiện tại) |
| Input | Text, ảnh, video (tối đa 3 giây) |
| Multimodal referencing | Phối hợp text + ảnh + video |
| Text & action sync | Nối chữ/chuyển động vào video |

Cái hay là Omni Flash có thể nhận nhiều loại đầu vào cùng lúc — bạn upload ảnh, viết prompt hướng dẫn, và nó sinh video kết hợp cả hai. Ngoài ra, nó dùng chung kiến thức nền của Gemini (lịch sử, sinh học, logic tường thuật) để tạo video có ý nghĩa, thay vì chỉ ghép khung hình ngẫu nhiên.

### Hạn chế cần biết

Là bản preview nên Omni Flash còn một số giới hạn:

- Video chỉ dài tối đa **10 giây** (bản dài hơn đang phát triển)
- Chưa hỗ trợ upload audio reference
- Scene extension chưa có
- Video input 3 giây chấp nhận trong API schema nhưng chưa xử lý đúng
- Character consistency khi chuyển cảnh còn hạn chế

Dù vậy, với bản preview đầu tiên, những gì Omni Flash làm được đã khá ấn tượng.

## Kết hợp cả hai: Hình dung một luồng làm việc mới

Phần làm mình thấy tâm đắc nhất là cách hai mô hình này bổ trợ cho nhau.

Google DeepMind giới thiệu ba demo app để minh hoạ:

1. **Anywhere** — chụp ảnh selfie, Nano Banana 2 Lite đưa bạn tới hàng chục địa danh nổi tiếng, rồi Omni Flash biến ảnh đó thành video ngắn về địa điểm.
2. **Space Lift** — upload ảnh căn phòng, Lite tạo ra các concept thiết kế nội thất, Omni Flash dựng video walkthrough cho từng concept.
3. **Omni Product Studio** — ảnh sản phẩm từ Lite, Omni Flash chuyển thành video quảng cáo e-commerce.

Công nghệ đằng sau là **Interactions API** — cho phép giữ session history và context xuyên suốt quá trình chỉnh sửa. Người dùng có thể stack tới 3 lần chỉnh sửa liên tiếp mà không mất ngữ cảnh.

Với mình, đây là hướng đi đúng. AI tạo sinh không nên là những công cụ rời rạc — bạn tạo ảnh ở chỗ này, tạo video ở chỗ kia, rồi ghép tay. Luồng làm việc lý tưởng là: ý tưởng → hình ảnh → video chuyển động, tất cả trong một hệ sinh thái duy nhất. Google DeepMind đang xây dựng thứ đó.

## SynthID và vấn đề an toàn

Như mọi mô hình của Google DeepMind, cả Nano Banana 2 Lite và Omni Flash đều được gắn **SynthID watermark** — dấu vân tay kỹ thuật số vô hình để nhận biết nội dung do AI tạo ra. Điều này quan trọng khi video AI ngày càng khó phân biệt với video thật, đặc biệt trong bối cảnh tin giả và deepfake đang là vấn đề nhức nhối.

## Suy nghĩ của mình

Đọc thông báo này, mình thấy vài điểm đáng suy ngẫm:

**Thứ nhất**, Google đang đẩy mạnh phân khúc giá rẻ. Nano Banana 2 Lite với giá $0.034/1K ảnh là một cú hích lớn cho các startup và nhà phát triển cá nhân. AI tạo ảnh giờ đã rẻ tới mức ai cũng có thể dùng thử mà không lo về budget.

**Thứ hai**, video đang trở thành mặt trận mới. Omni Flash với conversational editing là một cách tiếp cận khác so với các đối thủ như Runway hay Pika — thay vì tập trung vào chất lượng khung hình đơn lẻ, Google nhấn mạnh vào khả năng chỉnh sửa tương tác. Đây là thế mạnh của một công ty có nền tảng về AI hội thoại.

**Thứ ba**, việc kết hợp ảnh + video trong cùng một ecosystem cho thấy tầm nhìn dài hạn: AI tạo sinh không chỉ là tạo ra nội dung, mà là **quản lý cả một quy trình sáng tạo** từ ý tưởng đến sản phẩm cuối.

Nếu bạn muốn dùng thử, Google AI Studio là điểm khởi đầu nhanh nhất. Cả hai model đều có sẵn trong playground để bạn tự trải nghiệm.

## Liên kết nội bộ

- [Google DeepMind Nano Banana: Gia đình mô hình tạo ảnh AI mới nhất 2026](/posting/deepmind-nano-banana/)
- [Google Search hoạt động thế nào?](/cong-nghe/google-search-hoat-dong-the-nao/)
- [OpenCode so với Cursor, Claude Code, Copilot](/cong-nghe/opencode-so-voi-cursor-claude-code-copilot/)
- [GitHub Actions CI/CD cho người mới bắt đầu](/cong-nghe/github-actions-ci-cd-cho-nguoi-moi/)

## Liên kết bên ngoài

- [Google Blog — Start building with Nano Banana 2 Lite and Gemini Omni Flash](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-omni-flash-nano-banana-2-lite/)
- [Google DeepMind — Gemini Omni Flash](https://deepmind.google/models/gemini-omni/)
- [Google DeepMind — Nano Banana 2 Lite](https://deepmind.google/models/gemini-image/flash-lite/)
- [Google AI Studio — Nano Banana](https://aistudio.google.com/models/nano-banana)

## Bản quyền và ghi nguồn

Bài viết được Duy Nguyen biên tập và tổng hợp từ bài đăng chính thức của Google DeepMind ngày 30/06/2026, cùng tài liệu kỹ thuật từ Google AI for Developers. Thông tin giá cả và tính năng có thể thay đổi theo thời gian; vui lòng kiểm tra tài liệu chính thức của Google để cập nhật mới nhất. Ảnh đại diện là fallback OG của Duy Nguyen.

## FAQ - Câu hỏi thường gặp

**Nano Banana 2 Lite khác gì Nano Banana 2?**

Lite nhanh hơn (4 giây so với khoảng 6-10 giây), rẻ hơn đáng kể ($0.034/1K so với ~$0.05-0.15/1K của NB2), nhưng chỉ hỗ trợ độ phân giải 1K và không có Thinking mode. NB2 là lựa chọn đa năng, Lite là chuyên dụng cho tốc độ và chi phí thấp.

**Gemini Omni Flash có thể tạo video bao lâu?**

Hiện tại tối đa 10 giây cho mỗi lần tạo. Google đang phát triển bản hỗ trợ video dài hơn.

**Tôi có thể dùng Nano Banana 2 Lite ở đâu?**

Có sẵn trên Google AI Studio, Gemini API, và các sản phẩm tiêu dùng của Google như AI Mode trong Search, Gemini App, Google Photos, Google Flow.

**Omni Flash có giá bao nhiêu?**

$0.10 cho mỗi giây video. Ví dụ, một video 10 giây sẽ tốn $1. Đây là mức giá tương đương với Veo 3.1 Fast.

**Có thể dùng cả hai model cùng lúc không?**

Có. Đây chính là điểm mạnh của hệ sinh thái Google DeepMind. Bạn có thể dùng Nano Banana 2 Lite để tạo ảnh, sau đó dùng ảnh đó làm reference cho Omni Flash để tạo video — tất cả qua Interactions API với context được giữ xuyên suốt.
+++
