+++
title = "AlphaGenome — Phần 2: Đọc một triệu chữ DNA cùng AI"
description = "AlphaGenome của DeepMind đạt khả năng đọc ngữ cảnh lên đến một triệu nucleotide — cho phép AI nắm bắt toàn bộ cấu trúc và điều hoà của bộ gen người ở quy mô chưa từng có."
date = 2026-07-01T20:00:00+07:00

[taxonomies]
categories = ["Tất cả", "Khoa học"]
tags = ["alphagenome", "deepmind", "dna", "ngữ cảnh dài", "long-context", "bộ gen người", "ai sinh học", "google deepmind series"]

[extra]
thumbnail = "https://seomoney.org/img/covers/tao-blog-voi-zola.svg"
seo_keyword = "AlphaGenome ngữ cảnh dài"
featured = false
series = "google-deepmind"
series_part = 6
series_total = 7
toc = true

[[extra.faq]]
q = "AlphaGenome có thể đọc toàn bộ bộ gen người cùng lúc không?"
a = "Dùng kiến trúc ngữ cảnh dài (long-context), AlphaGenome có thể xử lý đồng thời một triệu nucleotide — đủ để nắm bắt một vùng lớn của bộ gen, bao gồm cấu trúc không gian và tương tác điều hoà."

[[extra.faq]]
q = "Có gì khác biệt giữa AlphaGenome Phần 1 và Phần 2?"
a = "Phần 1 tập trung vào vùng điều hoà (công tắc gen). Phần 2 mở rộng ra cấu trúc không gian của DNA và khả năng đọc ngữ cảnh lên đến một triệu chữ DNA — gần như toàn bộ một nhiễm sắc thể."

[[extra.faq]]
q = "Một triệu nucleotide đủ để làm gì?"
a = "Đủ để bao phủ vùng gen lớn với đầy đủ enhancer, promoter, gen và vùng liên gen — cho phép mô hình hiểu mối quan hệ không gian giữa các thành phần cách xa nhau hàng trăm nghìn nucleotide."
+++

> 🔬 **Series Khoa học — Google DeepMind & AI Sinh học (Bài 6/7)** — Bài trước: [AlphaGenome Phần 1 — vùng điều hoà DNA](/khoa-hoc/alphagenome-vung-dieu-hoa-dna/). Bài này đi sâu vào khả năng **ngữ cảnh dài** của AlphaGenome.

DNA của bạn dài khoảng 2 mét (tính tổng chiều dài các sợi), nhưng được nén gọn trong mỗi nhân tế bào. Cách DNA cuộn gấp trong không gian 3D quyết định vùng điều hoà nào tiếp xúc với gen nào — một lớp thông tin hoàn toàn mới ngoài trình tự tuyến tính.

AlphaGenome Phần 2 là bước đột phá: mô hình có thể xử lý **ngữ cảnh lên đến một triệu nucleotide** — gần như đọc cả một đoạn lớn của nhiễm sắc thể trong một lần, nắm bắt đồng thời trình tự DNA, vùng điều hoà, và cấu trúc không gian.

<!-- more -->

## Tại sao ngữ cảnh dài quan trọng?

Các mô hình dự đoán DNA trước đây hoạt động với các cửa sổ nhỏ — vài trăm đến vài nghìn nucleotide. Lý do: chi phí tính toán của cơ chế attention trong transformer tăng theo bình phương độ dài đầu vào.

Vấn đề: tương tác điều hoà trong bộ gen không tuân theo giới hạn cục bộ. Một enhancer có thể nằm cách gen nó điều khiển **1 triệu nucleotide** — và vẫn hoạt động bình thường nhờ DNA cuộn gấp đưa chúng lại gần nhau.

Giới hạn:
| Cửa sổ xử lý | Có thể thấy | Không thể thấy |
|---|---|---|
| 1.000 bp | Một gen nhỏ, promoter gần | Enhancer xa, cấu trúc không gian |
| 10.000 bp | Gen + một vài enhancer lân cận | Tổ chức TAD (Topologically Associating Domain) |
| 100.000 bp | Một vùng gen lớn | Liên kết chéo giữa các TAD |
| **1.000.000 bp** | Gần như toàn bộ tổ chức không gian của vùng | — |

AlphaGenome đạt đến **1 triệu bp** — cho phép mô hình nắm bắt hầu hết cấu trúc không gian quan trọng trong bộ gen.

## Kiến trúc: từ transformer sang mamba

Để đạt ngữ cảnh 1 triệu bp, AlphaGenome không dùng transformer thuần tuý. Thay vào đó, mô hình kết hợp:

1. **Mamba (state space model)** — kiến trúc attention tuyến tính, chi phí tính toán tỷ lệ O(n) thay vì O(n²), cho phép xử lý trình tự cực dài
2. **DNA token embedding** — mã hoá nucleotide (A, T, G, C) thành vector nhúng có vị trí (positional encoding)
3. **Multi-resolution** — mô hình học ở nhiều cấp độ: nucleotide đơn, motif (bộ 3-6 bp), vùng gen

Kết quả: AlphaGenome xử lý trình tự dài gấp **100–1000 lần** các mô hình transformer trước đây với cùng tài nguyên tính toán.

## Cấu trúc không gian của DNA

DNA trong nhân tế bào không phải sợi thẳng — nó được gấp cuộn có tổ chức. Một trong những cấu trúc quan trọng nhất là **TAD** (Topologically Associating Domain):

- Các vùng TAD là "vùng lân cận" trong không gian 3D
- Bên trong một TAD, các vùng điều hoà tương tác mạnh với nhau
- Giữa các TAD, tương tác bị hạn chế (nhờ insulator)
- Mỗi TAD dài khoảng 100.000–1.000.000 bp

AlphaGenome với ngữ cảnh 1 triệu bp có thể bao phủ **một hoặc nhiều TAD** — đủ để hiểu enhancer nào ảnh hưởng gen nào trong cùng một vùng không gian.

## Phát hiện mới từ AlphaGenome

Khi áp dụng AlphaGenome lên bộ gen người, các nhà nghiên cứu phát hiện nhiều điều mới:

1. **Enhancer ẩn** — hàng trăm enhancer mới trong vùng từng coi là "DNA rác", nhiều enhancer có vai trò quan trọng trong phát triển phôi thai
2. **Liên kết bệnh mới** — các biến thể trong enhancer mới phát hiện liên quan đến bệnh tiểu đường type 2 và bệnh tim mạch
3. **Tổ chức gen theo không gian** — các gen cùng chức năng thường nằm trong cùng TAD, và AlphaGenome dự đoán chính xác TAD chỉ từ trình tự DNA
4. **Đột biến cấu trúc** — phát hiện đột biến làm thay đổi cấu trúc TAD (gây ung thư và bệnh phát triển)

Một phát hiện đặc biệt: AlphaGenome xác định được các **vùng liên kết giữa các TAD** — ranh giới giữa các vùng tổ chức không gian. Đột biến ở ranh giới này có thể khiến enhancer của TAD này tác động nhầm sang gen của TAD khác — một cơ chế gây ung thư mới được hiểu rõ nhờ AI.

## So sánh: từ protein đến toàn bộ gen

Nhìn lại toàn bộ gia đình Alpha:

| Mô hình | Đầu vào | Quy mô | Năm |
|---|---|---|---|
| AlphaFold | ~1.000 aa | Một protein | 2020 |
| AlphaFold 3 | Phức hợp ~10.000 nguyên tử | Một hệ tương tác | 2024 |
| AlphaMissense | Đột biến một vị trí | Một axit amin | 2023 |
| AlphaProteo | Mục tiêu phân tử | Protein mới | 2024 |
| AlphaGenome P1 | Vùng điều hoà ~1.000.000 bp | Một TAD | 2025 |
| **AlphaGenome P2** | **~1.000.000 bp** | **Nhiều TAD** | **2025–2026** |

Đây là lộ trình rõ ràng: từ phân tử nhỏ → một protein → phức hợp protein → đột biến đơn → thiết kế protein → bộ gen.

{{ qa_pair(q = "AlphaGenome có thể thay thế giải trình tự gen không?", a = "Không. Giải trình tự là thí nghiệm đọc trình tự DNA thật. AlphaGenome là AI phân tích kết quả giải trình tự — giúp hiểu ý nghĩa của những gì đã đọc được, nhưng không thay thế bước đọc.") }}

{{ qa_pair(q = "Một triệu nucleotide đã là toàn bộ bộ gen chưa?", a = "Chưa. Bộ gen người có 3,2 tỷ nucleotide. Nhưng 1 triệu đủ để bao phủ toàn bộ một vùng di truyền quan trọng — tương đương một TAD hoặc cụm gen. Mô hình có thể xử lý các vùng chồng lấn để phủ toàn bộ gen.") }}

## Tóm lại

**AlphaGenome Phần 2** đưa khả năng đọc bộ gen của DeepMind lên một tầm cao mới. Với ngữ cảnh 1 triệu nucleotide, mô hình không chỉ đọc trình tự DNA mà còn hiểu được **cách bộ gen được tổ chức trong không gian** — điều mà trước đây chỉ có thí nghiệm Hi-C và các phương pháp đắt đỏ mới làm được.

Đây là bài cuối cùng của series về từng mô hình Alpha. Bài tổng kết: [Google DeepMind: AI & ngôn ngữ sự sống](/khoa-hoc/google-deepmind-ai-ngon-ngu-su-song/) — nhìn lại toàn bộ hành trình và bức tranh lớn.
+++
