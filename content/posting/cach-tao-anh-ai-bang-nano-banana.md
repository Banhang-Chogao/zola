+++
title = "Cách tạo ảnh AI bằng Nano Banana: hướng dẫn cho người mới"
date = 2026-07-02T14:00:00+07:00
aliases = ["/cach-tao-anh-ai-bang-nano-banana/"]
description = "Cách tạo ảnh AI bằng Nano Banana từng bước: chọn phiên bản, viết prompt hiệu quả, dùng ảnh tham chiếu và tránh lỗi thường gặp khi tạo ảnh."
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["nano banana", "tạo ảnh ai", "hướng dẫn ai", "gemini", "google ai studio", "prompt", "google deepmind"]
[extra]
seo_keyword = "cách tạo ảnh AI bằng Nano Banana"
thumbnail = "/img/og-fallbacks/og-fallback-5.svg"
toc = true

[[extra.faq]]
q = "Cách tạo ảnh AI bằng Nano Banana nhanh nhất là gì?"
a = "Nhanh nhất là mở Gemini app, chọn 'Create images' trong menu tools, gõ mô tả ảnh bằng ngôn ngữ tự nhiên (kể cả tiếng Việt) và nhận kết quả trong vài giây. Không cần cài đặt hay đăng ký API."

[[extra.faq]]
q = "Tạo ảnh bằng Nano Banana có mất phí không?"
a = "Dùng qua Gemini app hoặc Google Flow là miễn phí cho người dùng cá nhân. Nếu tích hợp qua Gemini API để tạo ảnh hàng loạt, chi phí tính theo số ảnh, ví dụ Nano Banana 2 Lite khoảng $0.034 cho mỗi 1.000 ảnh."

[[extra.faq]]
q = "Làm sao để prompt tạo ảnh đẹp và đúng ý hơn?"
a = "Mô tả càng cụ thể càng tốt: chủ thể, bối cảnh, ánh sáng, góc chụp, phong cách nghệ thuật, và tỷ lệ khung hình mong muốn. Tránh prompt quá ngắn hoặc quá mơ hồ — Nano Banana phản hồi tốt với prompt có cấu trúc rõ ràng."

[[extra.faq]]
q = "Có thể chỉnh sửa ảnh đã tạo trước đó không?"
a = "Có. Đây là điểm mạnh riêng của Nano Banana — bạn có thể tiếp tục hội thoại và yêu cầu chỉnh sửa ảnh vừa tạo (đổi màu, thêm chi tiết, đổi bối cảnh) mà không cần viết lại toàn bộ prompt từ đầu."

[[extra.faq]]
q = "Ảnh do Nano Banana tạo ra có thể dùng cho mục đích thương mại không?"
a = "Về mặt kỹ thuật có thể, nhưng nên đọc kỹ điều khoản sử dụng chính thức của Google trước khi dùng cho mục đích thương mại, đặc biệt liên quan tới bản quyền hình ảnh người thật hoặc thương hiệu trong ảnh được tạo."

[[extra.references_external]]
title = "Google DeepMind — Nano Banana 2"
url = "https://deepmind.google/models/gemini-image/flash/"

[[extra.references_external]]
title = "Google AI for Developers — Image Generation"
url = "https://ai.google.dev/gemini-api/docs/image-generation"

[[extra.references_external]]
title = "Google AI Studio"
url = "https://aistudio.google.com/"

+++

Sau khi viết [bài tổng quan gia đình Nano Banana](/posting/deepmind-nano-banana/), câu hỏi mình nhận nhiều nhất không phải là "Nano Banana có gì" mà là "vậy **cách tạo ảnh AI bằng Nano Banana** cụ thể ra sao, viết prompt sao cho ra đúng ý?" Đây là bài hướng dẫn thực hành, đi từ bước đầu tiên tới việc viết prompt hiệu quả và tránh những lỗi phổ biến.

<!-- more -->

## Cách tạo ảnh AI bằng Nano Banana: 3 nơi bạn có thể bắt đầu

Có ba cách chính để bắt đầu, tuỳ vào việc bạn cần gì:

1. **Gemini app** — nhanh nhất, miễn phí, phù hợp nếu bạn chỉ cần tạo vài ảnh cho cá nhân.
2. **Google AI Studio** — phù hợp nếu muốn thử nhiều model (Nano Banana 2 Lite, Nano Banana 2, Nano Banana Pro) và xem kết quả song song.
3. **Gemini API** — cần thiết nếu bạn muốn tự động hoá tạo ảnh hàng loạt cho một ứng dụng hoặc quy trình.

Với người mới, mình khuyên bắt đầu ở Gemini app hoặc Google AI Studio trước khi nghĩ tới việc gọi API.

## Bước 1: Chọn đúng phiên bản Nano Banana

Trước khi viết prompt, nên biết bạn đang dùng phiên bản nào, vì mỗi bản có điểm mạnh khác nhau:

| Nhu cầu | Phiên bản nên dùng |
|---|---|
| Tạo nhanh, số lượng lớn, ngân sách thấp | Nano Banana 2 Lite |
| Cân bằng chất lượng và tốc độ, cần ảnh tham chiếu | Nano Banana 2 |
| Chất lượng studio, kiểm soát thương hiệu chính xác | Nano Banana Pro |

Nếu chỉ mới thử nghiệm, Nano Banana 2 là lựa chọn mặc định hợp lý nhất — đây cũng là khuyến nghị chính thức của [Google DeepMind](https://deepmind.google/models/gemini-image/flash/) cho hầu hết dự án mới.

## Bước 2: Viết prompt hiệu quả

Đây là phần quan trọng nhất và cũng là nơi người mới hay gặp khó khăn nhất. Một prompt tốt thường có đủ 5 thành phần:

1. **Chủ thể chính** — cái gì/ai là trung tâm bức ảnh
2. **Bối cảnh** — không gian, thời gian, môi trường xung quanh
3. **Phong cách** — ảnh thật, minh hoạ, 3D render, tranh sơn dầu...
4. **Ánh sáng và góc chụp** — ánh sáng buổi sáng, ngược sáng, góc từ trên xuống...
5. **Tỷ lệ khung hình** — vuông, ngang, dọc, banner...

Ví dụ một prompt yếu và một prompt tốt cho cùng ý tưởng:

- ❌ Yếu: "một quán cà phê đẹp"
- ✅ Tốt: "quán cà phê nhỏ phong cách Bắc Âu, ánh sáng tự nhiên buổi sáng chiếu qua cửa sổ lớn, ghế gỗ mộc, tách cà phê latte art trên bàn gỗ, phong cách ảnh chụp thực tế, tỷ lệ 16:9"

Prompt tốt không cần dài dòng hoa mỹ — chỉ cần đủ chi tiết để Nano Banana hiểu chính xác bạn muốn gì, thay vì để nó tự đoán.

## Bước 3: Dùng ảnh tham chiếu để tăng độ chính xác

Với Nano Banana 2 trở lên, bạn có thể đính kèm tới 14 ảnh tham chiếu trong một lần tạo. Đây là cách hiệu quả để:

- Giữ đúng khuôn mặt hoặc nhận dạng nhân vật xuyên suốt nhiều ảnh
- Tái tạo chính xác một địa danh hoặc sản phẩm có thật (nhờ tính năng image grounding tìm kiếm ảnh thật trên web)
- Trộn phong cách từ nhiều ảnh mẫu vào một kết quả

Ví dụ thực tế: nếu bạn cần ảnh sản phẩm cho một chiến dịch quảng cáo, hãy đính kèm ảnh sản phẩm thật cùng 1-2 ảnh phong cách chụp bạn muốn tham khảo, thay vì chỉ mô tả bằng chữ.

## Bước 4: Tinh chỉnh bằng hội thoại thay vì viết lại prompt

Điểm khác biệt lớn nhất của Nano Banana so với các công cụ tạo ảnh AI thế hệ cũ là khả năng **chỉnh sửa hội thoại**. Sau khi có kết quả đầu tiên, bạn không cần viết lại toàn bộ prompt — chỉ cần nói tiếp:

- "Đổi ánh sáng thành hoàng hôn"
- "Thêm một chiếc xe đạp bên cạnh"
- "Làm cho không gian rộng hơn một chút"

Nano Banana sẽ giữ nguyên bối cảnh đã tạo và chỉ điều chỉnh phần bạn yêu cầu. Đây là cách làm việc hiệu quả hơn nhiều so với việc thử-sai bằng cách viết lại toàn bộ mô tả mỗi lần.

## Ví dụ dùng qua Gemini API

Nếu bạn muốn tự động hoá việc tạo ảnh trong một ứng dụng, đây là ví dụ gọi API cơ bản:

```python
from google import genai

client = genai.Client(api_key="YOUR_API_KEY")
response = client.models.generate_content(
    model="gemini-3.1-flash-image",
    contents=["Quán cà phê nhỏ phong cách Bắc Âu, ánh sáng buổi sáng, phong cách ảnh thực tế, tỷ lệ 16:9"]
)
print(response.text)
```

## 5 lỗi thường gặp khi mới bắt đầu

1. **Prompt quá ngắn hoặc mơ hồ** — "ảnh đẹp về công nghệ" sẽ cho kết quả ngẫu nhiên, không đúng ý.
2. **Không chỉ định tỷ lệ khung hình** — dẫn tới ảnh không phù hợp khi dùng cho banner web hoặc mạng xã hội.
3. **Bỏ qua bước chỉnh sửa hội thoại** — nhiều người tạo lại từ đầu thay vì tận dụng khả năng sửa liên tục, tốn thời gian hơn nhiều.
4. **Dùng sai phiên bản cho nhu cầu** — ví dụ dùng Lite khi cần độ phân giải 4K, kết quả sẽ không đạt kỳ vọng.
5. **Quên kiểm tra watermark SynthID** — nếu bạn dùng ảnh cho mục đích cần minh bạch nguồn gốc (báo chí, quảng cáo), nên biết ảnh đã được gắn watermark vô hình theo mặc định.

## Mẹo nâng cao: tạo bộ ảnh nhất quán cho một dự án

Nếu bạn cần một bộ nhiều ảnh có phong cách đồng nhất (ví dụ minh hoạ cho một bài viết hoặc bộ nhận diện thương hiệu nhỏ), cách làm hiệu quả là:

1. Tạo ảnh đầu tiên thật kỹ, ưng ý về phong cách và ánh sáng
2. Dùng chính ảnh đó làm ảnh tham chiếu cho các lần tạo tiếp theo
3. Giữ nguyên phần mô tả phong cách trong prompt, chỉ đổi phần chủ thể/bối cảnh

Cách này tận dụng tốt tính năng subject consistency của Nano Banana 2, giúp bộ ảnh trông như được thực hiện bởi cùng một "nhiếp ảnh gia" thay vì rời rạc từng tấm.

## So sánh nhanh: prompt yếu vs prompt tốt qua nhiều thể loại

Để việc luyện viết prompt dễ hình dung hơn, dưới đây là vài ví dụ khác theo từng thể loại ảnh phổ biến:

**Ảnh chân dung sản phẩm:**
- ❌ Yếu: "ảnh chai nước hoa"
- ✅ Tốt: "chai nước hoa thuỷ tinh trong suốt đặt trên nền đá cẩm thạch trắng, ánh sáng studio dịu từ bên trái, phông nền mờ nhẹ, phong cách chụp sản phẩm cao cấp, tỷ lệ vuông"

**Ảnh minh hoạ bài viết:**
- ❌ Yếu: "ảnh về công nghệ AI"
- ✅ Tốt: "minh hoạ trừu tượng về mạng neural, tông màu xanh dương và tím, phong cách flat design tối giản, phù hợp làm ảnh bìa bài blog, tỷ lệ 16:9"

**Ảnh nhân vật nhất quán qua nhiều cảnh:**
- ❌ Yếu: "một cô gái đi du lịch"
- ✅ Tốt: "cùng một cô gái tóc ngắn màu nâu, áo khoác denim (dùng ảnh tham chiếu đính kèm), đang đứng trước tháp Eiffel buổi hoàng hôn, phong cách ảnh chụp du lịch tự nhiên"

Quy tắc chung: prompt tốt luôn trả lời được câu hỏi "nếu đưa mô tả này cho một nhiếp ảnh gia thật, họ có đủ thông tin để chụp đúng ý bạn không?"

## Ứng dụng thực tế: vài trường hợp mình đã dùng

Ngoài việc luyện viết prompt, đây là vài tình huống thực tế mình thấy Nano Banana hữu ích nhất trong công việc hằng ngày:

- **Ảnh minh hoạ cho bài blog** — thay vì tìm ảnh stock chung chung không khớp nội dung, tạo ảnh minh hoạ đúng chủ đề bài viết trong vài giây.
- **Thử nghiệm concept thiết kế nhanh** — trước khi thuê designer làm bản chính thức, dùng Nano Banana để hình dung concept, sau đó gửi làm tài liệu tham khảo.
- **Tạo ảnh mạng xã hội theo bộ nhận diện** — dùng ảnh tham chiếu để giữ tông màu và phong cách nhất quán giữa các bài đăng.
- **Prototyping sản phẩm** — hình dung nhanh một ý tưởng sản phẩm trước khi đầu tư vào ảnh chụp thật.

Điểm chung của các trường hợp này là: Nano Banana không thay thế hoàn toàn nhiếp ảnh hay thiết kế chuyên nghiệp, nhưng rút ngắn đáng kể thời gian ở giai đoạn ý tưởng và thử nghiệm ban đầu.

## Kết luận

Tạo ảnh AI bằng Nano Banana không khó, nhưng để ra kết quả ưng ý ngay từ đầu cần một chút kỹ thuật viết prompt và biết tận dụng khả năng chỉnh sửa hội thoại. Bắt đầu từ Gemini app để làm quen, sau đó chuyển qua Google AI Studio khi cần thử nghiệm nhiều hơn, và chỉ dùng API khi thực sự cần tự động hoá quy trình.

## Đọc thêm

Bài này là một phần trong loạt bài mình theo dõi về [công nghệ AI](/categories/cong-nghe/) của Google DeepMind. Xem thêm [tổng quan gia đình mô hình Nano Banana](/posting/deepmind-nano-banana/), [so sánh Nano Banana với Midjourney và DALL-E](/posting/nano-banana-so-sanh-midjourney-dalle/), hoặc [Nano Banana 2 Lite kết hợp Gemini Omni Flash tạo video](/posting/nano-banana-2-lite-gemini-omni-flash/). Nếu đây là lần đầu bạn ghé blog, [tìm hiểu thêm về mình](/posting/chao-mung-den-voi-duy-nguyen/).
