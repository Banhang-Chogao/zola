+++
title = "Gemini 3.5 có gì mới? Google DeepMind vừa ra mắt mô hình frontier với khả năng hành động"
date = 2026-07-01T17:00:00+07:00
aliases = ["/gemini-3-5-co-gi-moi/"]
description = "Gemini 3.5 Flash vừa ra mắt với khả năng agentic coding, multimodal, long horizon tasks. So sánh benchmark với Claude, GPT-5.5 và góc nhìn chi tiết."
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["agentic ai", "ai benchmarks", "gemini 3.5 flash", "gemini flash", "gemini-3-5", "google deepmind", "multimodal"]
[extra]
seo_keyword = "Gemini 3.5 có gì mới"
thumbnail = "/img/og-fallbacks/og-fallback-15.svg"
toc = true

[[extra.faq]]
q = "Gemini 3.5 khác gì so với Gemini 3.1 Pro?"
a = "Gemini 3.5 Flash tập trung vào agentic workflows — khả năng tự động hoá tác vụ, coding, điều khiển công cụ. Gemini 3.1 Pro mạnh về complex tasks và creative concepts. 3.5 Flash nhanh hơn, rẻ hơn, nhưng 3.1 Pro vẫn là lựa chọn tốt cho các tác vụ cần chất lượng suy luận sâu. Bản 3.5 Pro (sắp ra mắt) hứa hẹn kết hợp cả hai."

[[extra.faq]]
q = "Gemini 3.5 Flash có sẵn chưa?"
a = "Có. Gemini 3.5 Flash đã có sẵn trên Gemini app, Google AI Studio, Gemini API và Gemini Enterprise Agent Platform."

[[extra.faq]]
q = "Gemini 3.5 Pro bao giờ ra mắt?"
a = "Google DeepMind công bố '3.5 Pro coming soon' trên trang sản phẩm chính thức. Chưa có ngày cụ thể."

[[extra.faq]]
q = "Gemini 3.5 Flash có miễn phí không?"
a = "Có sẵn qua Gemini app (miễn phí). Google AI Studio và Gemini API có free tier và tính phí theo usage."

[[extra.faq]]
q = "Gemini 3.5 có hỗ trợ tiếng Việt không?"
a = "Có. Gemini hỗ trợ đa ngôn ngữ, bao gồm tiếng Việt, ở cả đầu vào và đầu ra. Các benchmark MMMU-Pro và CharXiv đã kiểm tra khả năng đa ngôn ngữ."
[[extra.references_external]]
title = "Google DeepMind — Gemini 3.5"
url = "https://deepmind.google/models/gemini/gemini-3-5/"

[[extra.references_external]]
title = "Google AI for Developers — Gemini API"
url = "https://ai.google.dev/gemini-api/docs"

[[extra.references_external]]
title = "Google AI Studio"
url = "https://aistudio.google.com/"

[[extra.references_external]]
title = "Google DeepMind — Gemini 3.5 Evals Methodology"
url = "https://deepmind.google/models/evals-methodology/gemini-3-5-flash"

+++

Google DeepMind vừa chính thức trình làng **Gemini 3.5** — dòng mô hình mới nhất đánh dấu bước chuyển từ "AI trả lời câu hỏi" sang "AI hành động". Đây không phải là một bản nâng cấp thông thường về benchmark. Cách họ định vị Gemini 3.5 nói lên nhiều điều: "Frontier intelligence with action."

Mình đã dành thời gian đọc tài liệu, soi từng con số benchmark và xem các demo use case để hiểu xem Gemini 3.5 thực sự có gì mới, và quan trọng hơn — nó khác gì so với Gemini 3.1 Pro hay thậm chí GPT-5.5 hay Claude Opus 4.7.

<!-- more -->

## Gemini 3.5: Không chỉ nhanh hơn, mà là một cách tiếp cận khác

Ngay khi mở trang sản phẩm của Google DeepMind, điều đầu tiên mình để ý là họ không còn so sánh Gemini 3.5 với các mô hình khác về benchmark "chat" truyền thống nữa. Tất cả benchmark đều xoay quanh **agentic workflows** — khả năng tự động hoá tác vụ, lập trình, điều khiển trình duyệt và phối hợp công cụ.

Cụ thể, Gemini 3.5 có bốn năng lực chính:

1. **Agentic coding** — tự động hoá tác vụ lập trình phức tạp
2. **Advanced multimodal understanding** — xử lý text, ảnh, video, audio
3. **Long horizon tasks** — thực thi workflow kéo dài, nhiều bước
4. **Multi-step problem-solving** — giải quyết vấn đề thực tế qua nhiều công cụ

Hiện tại Gemini 3.5 Flash đã có sẵn trên Gemini app và Google AI Studio. Phiên bản **3.5 Pro** sẽ ra mắt sau.

## Agentic Coding: Code nhanh hơn, thông minh hơn

Điểm mạnh nhất của Gemini 3.5 Flash là ở mảng coding. Nhìn vào bảng benchmark:

| Benchmark | Gemini 3.5 Flash | Gemini 3 Flash | GPT-5.5 | Claude Opus 4.7 |
|---|---|---|---|---|
| Terminal-bench 2.1 | **76.2%** | 58.0% | 78.2% | 66.1% |
| SWE-Bench Pro | **55.1%** | 49.6% | 58.6% | 64.3% |
| MCP Atlas | **83.6%** | 62.0% | 75.3% | 79.1% |
| OSWorld-Verified | **78.4%** | 65.1% | 78.7% | 78.0% |

Con số mình thấy ấn tượng nhất là **MCP Atlas 83.6%** — vượt qua cả Claude Opus 4.7 và GPT-5.5. MCP Atlas đo lường khả năng thực hiện multi-step workflow sử dụng Model Context Protocol. Đây là bài toán thực tế: AI không chỉ viết code, mà còn phải gọi công cụ, đọc tài liệu, thực thi lệnh và điều chỉnh hành vi dựa trên kết quả.

OSWorld-Verified (78.4%) cũng là một tín hiệu đáng chú ý — nó đo khả năng AI điều khiển máy tính như một người dùng thực: mở ứng dụng, click, gõ phím, đọc màn hình. Con số này ngang ngửa Claude Opus 4.7 (78.0%) và GPT-5.5 (78.7%).

Shopify là một trong những đơn vị tiên phong dùng Gemini 3.5 Flash. Họ chạy các subagent song song để phân tích dữ liệu phức tạp cho dự báo tăng trưởng merchant trên quy mô toàn cầu. Câu chuyện của họ cho thấy AI agent không chỉ là chạy một lệnh đơn lẻ — nó là một hệ thống phối hợp nhiều tác vụ.

## Multimodal: Hiểu sâu hơn từ nhiều nguồn

Gemini vốn đã mạnh về multimodal ngay từ đầu, và 3.5 Flash tiếp tục cải thiện:

| Benchmark | Gemini 3.5 Flash | Gemini 3 Flash | GPT-5.5 | Claude Opus 4.7 |
|---|---|---|---|---|
| MMMU-Pro | **83.6%** | 81.2% | 81.2% | 75.2% |
| CharXiv Reasoning | **84.2%** | 80.3% | 84.1% | 82.1% |
| Blueprint-Bench 2 | **33.6%** | 0.0% | 36.2% | 24.5% |

MMMU-Pro 83.6% dẫn đầu — cho thấy khả năng hiểu và suy luận đa phương thức vượt trội. CharXiv Reasoning 84.2% suýt soát GPT-5.5 (84.1%). Đặc biệt Blueprint-Bench 2 (agentic spatial reasoning) đạt 33.6%, trong khi Gemini 3 Flash cũ là 0% — một bước nhảy vọt.

## Long Context: Giữ bối cảnh tốt hơn ở 128K

MRCR v2 (8-needle) ở 128K đạt 77.3% — thấp hơn GPT-5.5 (94.8%) và Claude Opus 4.7 (84.9%). Ở 1M tokens, chỉ đạt 26.6%. Đây có vẻ là điểm yếu của 3.5 Flash so với đối thủ. Gemini 3.1 Pro vẫn làm tốt hơn ở hạng mục này (84.9% ở 128K). Nếu bạn cần xử lý context cực dài, 3.1 Pro hoặc Claude Opus có vẻ là lựa chọn an toàn hơn.

## Reasoning: Có tiến bộ nhưng chưa dẫn đầu

| Benchmark | Gemini 3.5 Flash | Gemini 3 Flash | GPT-5.5 | Claude Opus 4.7 |
|---|---|---|---|---|
| Humanity's Last Exam | **40.2%** | 33.7% | 41.4% | 46.9% |
| ARC-AGI-2 | **72.1%** | 33.6% | 84.6% | 75.8% |

Gemini 3.5 Flash tăng đáng kể so với Gemini 3 Flash (40.2% vs 33.7% trên HLE), nhưng vẫn thua Claude Opus 4.7 và GPT-5.5. Điều này dễ hiểu vì Flash là dòng tối ưu tốc độ, không phải reasoning thuần tuý. Bản Pro sắp tới hứa hẹn sẽ cạnh tranh hơn ở mảng này.

## Phản ứng từ đối tác và khách hàng

Phần thú vị nhất khi đọc trang sản phẩm là testimonial từ các đối tác:

- **Box** — ghi nhận Gemini 3.5 Flash beat Gemini 3 Flash 19.6% trên enterprise work evaluation. Đặc biệt, trong lĩnh vực Life Sciences, độ chính xác tăng 96.4% khi trích xuất dữ liệu khoa học.
- **Cline** (công cụ coding agent) — cho biết Gemini 3.5 giải quyết được các vấn đề mà các mô hình khác bó tay, nhờ khả năng hiểu context dài và sâu.
- **Cursor** — thấy cải thiện rõ rệt về frontend quality. Sualeh Asif, Co-founder Cursor, nói model này "hoạt động tốt cho những tác vụ tham vọng nhất."
- **GitHub Copilot** — 35% higher accuracy trong software engineering challenges so với Gemini 2.5 Pro.
- **JetBrains Junie** — coding quality gần ngang Gemini Pro, nhưng với tốc độ và chi phí của dòng Flash.
- **Figma** — Gemini 3.5 trong Figma Make giúp dịch thiết kế thành code chính xác hơn.

## Gemini 3.5 ảnh hưởng tới hệ sinh thái Google

Gemini 3.5 Flash có sẵn trên toàn bộ nền tảng của Google: Gemini app, Google AI Studio, Gemini API, Gemini Enterprise Agent Platform. Điều này có nghĩa là nếu bạn đang xây dựng ứng dụng trên hệ sinh thái Google, bạn có thể dùng ngay mà không cần migration phức tạp.

Google cũng giới thiệu **Google Antigravity** — nền tảng phát triển AI-first cho phép bất kỳ ai cũng có thể xây dựng ứng dụng. Đây là động thái cho thấy Google không chỉ bán model, họ muốn bán cả nền tảng.

## Suy nghĩ của mình

Đọc về Gemini 3.5, mình thấy vài điều đáng chú ý:

**Thứ nhất**, cuộc đua AI đã chuyển từ "ai nói chuyện hay hơn" sang "ai làm việc tốt hơn." Các benchmark agentic (MCP Atlas, OSWorld, Terminal-bench) mới là thước đo thực sự. Và Gemini 3.5 Flash đang cạnh tranh rất tốt ở mảng này, thậm chí dẫn đầu ở MCP Atlas.

**Thứ hai**, chiến lược của Google với dòng Flash rất thông minh. Họ đưa khả năng gần ngang Pro vào một mô hình nhanh, rẻ, phù hợp với agentic workflow. Điều này hạ rào cản cho các startup và nhà phát triển cá nhân muốn xây dựng AI agent.

**Thứ ba**, 3.5 Pro sắp tới mới là mảnh ghép đáng chờ đợi. Nếu Flash đã làm tốt ở agentic tasks, Pro hứa hẹn sẽ cạnh tranh sòng phẳng với Claude Opus 4.7 và GPT-5.5 ở mọi mặt trận.

Về điểm yếu, long context (đặc biệt ở 1M tokens) vẫn là khoảng cách lớn với GPT-5.5 và Claude Opus. Và trên các benchmark reasoning thuần tuý, 3.5 Flash vẫn chưa phải số một — nhưng đó là nhiệm vụ của bản Pro.

Nếu bạn muốn dùng thử, Gemini 3.5 Flash đã có trên Google AI Studio. Hãy dùng thử với các tác vụ coding hoặc agentic để tự cảm nhận sự khác biệt.
