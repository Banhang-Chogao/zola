+++

title = "AlphaGenome hoạt động ra sao: đọc một triệu chữ DNA để dự đoán điều gì xảy ra?"
description = "Cách AlphaGenome của Google DeepMind đọc trình tự DNA dài một triệu base pair, dự đoán hàng nghìn tính chất phân tử, và ứng dụng trong nghiên cứu bệnh di truyền."
date = 2026-07-01

[taxonomies]
categories = ["Tất cả", "Khoa học", "Series"]
tags = ["khoa học", "google deepmind series", "alphagenome", "ai", "dna", "genomics", "regulatory genomics"]

[extra]
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
seo_keyword = "AlphaGenome cách hoạt động"
series = "google-deepmind"
series_part = 7
series_total = 10
+++

Đây là bài thứ 7 trong series tìm hiểu Google DeepMind và AI cho nghiên cứu y sinh. Ở [bài trước](/khoa-hoc/alphagenome-vung-dieu-hoa-dna/), tôi đã viết về lý do vùng DNA không mã hoá mới thực sự là thách thức — vì 98% bộ gen không phải gene, nhưng chứa hơn 90% biến thể liên quan bệnh. Bài này đi sâu vào **cách AlphaGenome hoạt động**: nó đọc cái gì, suy luận ra sao, và có thể làm gì với một đoạn DNA dài tới một triệu chữ cái.

Nguồn chính cho bài này: [blog chính thức của Google DeepMind về AlphaGenome](https://deepmind.google/blog/alphagenome-ai-for-better-understanding-the-genome/) và [Nature bài báo gốc (tháng 1/2026)](https://www.nature.com/articles/s41586-025-10014-0).

<!-- more -->

## Tại sao một triệu base pair?

DNA người có ~3 tỷ base pair. Nhưng một mô hình AI không cần — và không thể — đọc hết 3 tỷ trong một lần. Câu hỏi là: **bao nhiêu là đủ** để dự đoán được điều hoà gene?

Các nhà khoa học biết rằng một gene có thể được điều hoà bởi những vùng nằm cách nó rất xa — có khi tới vài trăm nghìn base pair. Những vùng này gọi là *enhancer* xa. Nếu mô hình chỉ đọc 1.000–10.000 base pair như các mô hình trước đây, nó sẽ bỏ sót các enhancer ở xa.

> **Hiểu đơn giản:** Hãy tưởng tượng bạn muốn hiểu một câu chuyện. Đọc một trang thì dễ, nhưng nếu plot twist nằm ở trang 50, bạn sẽ không bao giờ đoán được nếu chỉ đọc trang 2. AlphaGenome đọc 1.000.000 chữ cái — tương đương khoảng 1% genome — là đủ dài để bao phủ hầu hết vùng điều hoà quan trọng, nhưng vẫn đủ ngắn để tính toán hiệu quả.

Theo [blog DeepMind](https://deepmind.google/blog/alphagenome-ai-for-better-understanding-the-genome/), "Our model analyzes up to 1 million DNA letters and makes predictions at the resolution of individual letters."

Độ phân giải **từng base pair** là chìa khoá: các mô hình cũ thường phải hy sinh độ phân giải (chỉ đọc ở mức window 100–1.000 bp) để kéo dài đầu vào. AlphaGenome làm được cả hai: dài mà vẫn chi tiết.

## AlphaGenome nhận đầu vào, trả ra cái gì?

### Đầu vào: Trình tự DNA dài 1.000.000 ký tự

Cụ thể hơn, mô hình nhận một chuỗi DNA (chuỗi A, T, G, C) và một vị trí tham chiếu trên chuỗi đó — điểm "quan tâm" — như một gene hay một SNP (single nucleotide polymorphism).

### Đầu ra: Hàng nghìn "tính chất phân tử"

AlphaGenome dự đoán hàng loạt đặc tính sinh học từ chuỗi DNA đầu vào. Các dự đoán này bao gồm ([nguồn](https://deepmind.google/blog/alphagenome-ai-for-better-understanding-the-genome/)):

- **Vị trí gene start và end** trong các loại tế bào và mô khác nhau
- **Vị trí splice junction** (chỗ RNA bị cắt nối) — tính năng hoàn toàn mới, chưa mô hình nào trước đây dự đoán trực tiếp được
- **Lượng RNA được sản xuất** (gene expression level)
- **Vùng DNA mở/đóng** (chromatin accessibility)
- **Vùng DNA gần nhau trong không gian 3D** (interaction)
- **Vị trí protein bám vào DNA** (protein binding)

Tất cả các dự đoán này được thực hiện cho nhiều loại tế bào và mô khác nhau, dựa trên dữ liệu huấn luyện từ các consortium nghiên cứu lớn.

## Kiến trúc mô hình: convolution + transformer + classification

AlphaGenome kết hợp ba kiểu kiến trúc neural network quen thuộc nhưng phối hợp theo cách mới.

### 1. Convolutional layers — dò tín hiệu địa phương

Tầng đầu tiên dùng **convolutional neural network** (CNN) để quét chuỗi DNA và phát hiện các mẫu ngắn. Các mẫu này có thể là motif bám của protein điều hoà, tín hiệu splice, hoặc các sequence pattern đặc trưng.

Hãy nghĩ như một máy dò quét slide kính hiển vi: nó tìm kiếm các đặc điểm cục bộ trước, trước khi ghép lại để hiểu bức tranh lớn.

### 2. Transformer layers — kết nối toàn bộ chuỗi

Sau khi CNN phát hiện các tín hiệu ở từng vị trí, **transformer** (cùng họ với kiến trúc trong GPT, BERT, Gemini) cho phép mô hình truyền thông tin giữa mọi vị trí trong chuỗi một triệu base pair.

Đây là cải tiến kỹ thuật quan trọng. Transformer giúp mô hình trả lời câu hỏi: "tín hiệu ở vị trí 500.000 có liên quan gì đến vị trí 10.000 không?" — điều mà CNN thuần tuý không làm được.

### 3. Final layers — chuyển mẫu thành dự đoán

Tầng cuối biến các đặc trưng đã phát hiện thành dự đoán cho từng "modality": vị trí exon, mức độ biểu hiện, tương tác chromatin, v.v.

### Phân phối tính toán

Theo [blog](https://deepmind.google/blog/alphagenome-ai-for-better-understanding-the-genome/), "during training, this computation is distributed across multiple interconnected Tensor Processing Units (TPUs) for a single sequence." Một chuỗi duy nhất được trải trên nhiều TPU — cho thấy khối lượng tính toán khổng lồ.

Điều thú vị: toàn bộ quá trình huấn luyện **một mô hình AlphaGenome (phiên bản gốc, chưa distillation)** chỉ mất 4 giờ và tốn một nửa compute budget so với Enformer (mô hình tiền nhiệm năm 2021). Tức hiệu quả tính toán đã tăng gấp đôi so với 4 năm trước.

## Dữ liệu huấn luyện: consortium nghiên cứu lớn

AlphaGenome được huấn luyện trên dữ liệu thực nghiệm từ các consortium quốc tế ([nguồn](https://deepmind.google/blog/alphagenome-ai-for-better-understanding-the-genome/)):

| Consortium | Loại dữ liệu |
|-----------|-------------|
| [ENCODE](http://encodeproject.org/) | Vùng DNA điều hoà, protein binding, chromatin accessibility — hàng trăm loại tế bào |
| [GTEx](https://www.gtexportal.org/) | Mức biểu hiện gene trên nhiều mô người (genotype-tissue expression) |
| [4D Nucleome](https://4dnucleome.org/) | Cấu trúc không gian 3D của genome — vùng DNA nào gần nhau trong nhân tế bào |
| [FANTOM5](https://fantom.gsc.riken.jp/5/) | Promoter và enhancer hoạt động ở đâu trong cơ thể |

Đây là những bộ dữ liệu công khai, được thu thập qua nhiều năm bằng thực nghiệm ướt (wet lab). AlphaGenome không phải "bịa" ra kiến thức — nó học từ dữ liệu thực tế do hàng trăm phòng thí nghiệm trên thế giới tạo ra.

## Tính năng đặc biệt: dự đoán splice junction

Một trong những cải tiến thú vị nhất của AlphaGenome là khả năng **dự đoán vị trí và mức độ cắt nối RNA (RNA splicing) trực tiếp từ trình tự DNA** ([nguồn](https://deepmind.google/blog/alphagenome-ai-for-better-understanding-the-genome/)).

Splicing là quá trình RNA cắt bỏ các đoạn intron và nối các exon lại với nhau. Quá trình này cực kỳ phức tạp và dễ sai. Lỗi splicing là nguyên nhân gây ra nhiều bệnh hiếm gặp, bao gồm:

- **Spinal muscular atrophy (teo cơ cột sống):** do lỗi splicing gene SMN1/SMN2
- **Một số dạng cystic fibrosis (xơ nang):** do đột biến vùng điều hoà splicing

Đây là lần đầu tiên một mô hình AI có thể explicit mô hình hoá vị trí và mức độ splice junction trực tiếp từ DNA sequence. Các mô hình trước đây chỉ dự đoán gián tiếp (vd qua mức biểu hiện gene hoặc thông qua các tín hiệu gián tiếp).

## State-of-the-art: điểm benchmark

Theo [blog DeepMind](https://deepmind.google/blog/alphagenome-ai-for-better-understanding-the-genome/):

- **22/24** đánh giá trên trình tự đơn (single sequence): AlphaGenome vượt mọi mô hình bên ngoài
- **24/26** đánh giá tác động biến thể (variant effect): AlphaGenome đạt hoặc vượt mô hình chuyên biệt tốt nhất

Điểm đáng chú ý: AlphaGenome **vượt cả các mô hình được thiết kế riêng cho từng tác vụ** — mặc dù nó là mô hình đa năng (generalist) duy nhất dự đoán tất cả các modality trong cùng một kiến trúc.

## Ứng dụng cụ thể: từ nghiên cứu cơ bản đến ung thư

Blog DeepMind đưa ra một ví dụ cụ thể ([nguồn](https://deepmind.google/blog/alphagenome-ai-for-better-understanding-the-genome/)):

Trong một nghiên cứu về **bệnh bạch cầu lympho cấp tế bào T (T-ALL)**, các nhà nghiên cứu quan sát thấy đột biến tại một vị trí cụ thể trong genome. AlphaGenome dự đoán rằng các đột biến này sẽ **kích hoạt gene TAL1** gần đó bằng cách tạo ra một motif bám MYB mới. Phát hiện này tái hiện chính xác cơ chế bệnh đã biết — chứng minh khả năng liên kết biến thể không mã hoá với bệnh của mô hình.

> "AlphaGenome will be a powerful tool for the field. Determining the relevance of different non-coding variants can be extremely challenging, particularly to do at scale."
> — **Prof. Marc Mansour**, University College London ([nguồn](https://deepmind.google/blog/alphagenome-ai-for-better-understanding-the-genome/))

## Tôi tự ghi chú lại như sau

Một vài điểm tôi thấy tâm đắc sau khi đọc tài liệu:

1. **Đây là bước tiến từ Enformer, không phải thay thế.** AlphaGenome là "đứa con" của Enformer (2021) với nhiều cải tiến về kiến trúc (transformer + CNN thay vì CNN thuần). Nhưng cốt lõi vẫn là ý tưởng: đầu vào dài, đầu ra đa modality.

2. **Tính đơn giản đáng ngạc nhiên của training.** Chỉ 4 giờ với bằng nửa compute của Enformer là một cải tiến lớn. Cho thấy kiến trúc mới không chỉ mạnh hơn mà còn hiệu quả hơn.

3. **Splice junction prediction là game changer.** Với các bệnh do lỗi splicing — ước tính chiếm 15–50% các bệnh di truyền — đây là công cụ đầu tiên có thể dự đoán trực tiếp từ sequence. Trước đây phải dùng các mô hình chuyên biệt nhỏ.

4. **Vẫn còn khoảng cách với thực tế.** Mô hình dự đoán tốt nhưng "chưa được thiết kế hoặc xác nhận cho việc dự đoán genome cá nhân" — trích từ DeepMind — và vẫn gặp khó với các enhancer rất xa (>100.000 bp).

## Hạn chế cần lưu ý

Blog DeepMind thẳng thắn chỉ ra các hạn chế ([nguồn](https://deepmind.google/blog/alphagenome-ai-for-better-understanding-the-genome/)):

1. **Vùng điều hoà quá xa:** mô hình vẫn gặp khó khăn khi enhancer nằm cách gene >100.000 base pair. Đây là giới hạn của tầm nhìn một triệu base pair.

2. **Tính đặc hiệu mô/tế bào:** dù đã dự đoán được cho nhiều loại tế bào, việc tăng khả năng "hiểu" sự khác biệt tinh vi giữa các mô là ưu tiên tương lai.

3. **Không phải công cụ dự đoán genome cá nhân:** AlphaGenome chưa được thiết kế hay xác nhận cho mục đích tiên lượng cho từng người — một thách thức chung cho mọi mô hình AI trong genomics.

4. **Từ dự đoán phân tử đến hiểu bệnh:** dự đoán một đột biến làm thay đổi mức biểu hiện gene là một chuyện; hiểu được nó gây ra bệnh gì lại là chuyện khác, vì bệnh thường liên quan đến nhiều yếu tố môi trường và phát triển ngoài tầm dự đoán của mô hình.

> **Đừng hiểu lầm:** AlphaGenome là công cụ **nghiên cứu** (research tool), không phải công cụ chẩn đoán lâm sàng. Các dự đoán của mô hình **chỉ dành cho mục đích nghiên cứu** và chưa được xác nhận cho mục đích lâm sàng trực tiếp. Không dùng kết quả AlphaGenome để đưa ra quyết định y tế cho cá nhân. Nguồn: [DeepMind](https://deepmind.google/blog/alphagenome-ai-for-better-understanding-the-genome/).

## Kết luận: tại sao mô hình "đa năng" lại quan trọng?

Sức mạnh của AlphaGenome không chỉ nằm ở điểm benchmark. DeepMind nhấn mạnh ([nguồn](https://deepmind.google/blog/alphagenome-ai-for-better-understanding-the-genome/)): "AlphaGenome's generality allows scientists to simultaneously explore a variant's impact on a number of modalities with a single API call."

Điều này có nghĩa là: thay vì dùng model A để đo mức biểu hiện, model B để đo chromatin, model C để đo splicing, và model D để đo protein binding — giờ chỉ cần **một mô hình, một API call**. Giả thuyết được kiểm tra nhanh hơn, khám phá rộng hơn.

Với việc đã được [Nature xuất bản tháng 1/2026](https://www.nature.com/articles/s41586-025-10014-0) và mã nguồn mở trên [GitHub](https://github.com/google-deepmind/alphagenome_research), AlphaGenome đang trở thành nền tảng cho cộng đồng xây dựng tiếp.

Bài sau tôi sẽ chuyển từ đọc DNA sang **thiết kế protein mới** — khi AI không chỉ dự đoán mà còn sáng tạo ra protein để bám vào mục tiêu sinh học. Mời bạn đọc tiếp [AlphaProteo: khi AI bắt đầu thiết kế protein mới](/khoa-hoc/alphaproteo-thiet-ke-protein-moi/).

---

### Liên kết nội bộ

- [Bài 6: Đột biến gen không chỉ nằm trong vùng mã hoá — vì sao AlphaGenome quan trọng?](/khoa-hoc/alphagenome-vung-dieu-hoa-dna/)
- [Bài 8: AlphaProteo — khi AI bắt đầu thiết kế protein mới](/khoa-hoc/alphaproteo-thiet-ke-protein-moi/)

### Liên kết bên ngoài

- [Google DeepMind: AlphaGenome — AI for better understanding the genome](https://deepmind.google/blog/alphagenome-ai-for-better-understanding-the-genome/)
- [Nature paper: AlphaGenome (January 2026)](https://www.nature.com/articles/s41586-025-10014-0)
- [AlphaGenome on GitHub](https://github.com/google-deepmind/alphagenome_research)
- [ENCODE Project](https://www.encodeproject.org/)
- [GTEx Portal](https://www.gtexportal.org/)
- [4D Nucleome](https://www.4dnucleome.org/)
- [FANTOM5](https://fantom.gsc.riken.jp/5/)
- [Google DeepMind Science — trang tổng hợp](https://deepmind.google/science/)

### Bản quyền & nguồn tham khảo

Bài viết này là ghi chép học tập cá nhân, tổng hợp từ nguồn mở do Google DeepMind công bố. Nội dung tham khảo từ [blog](https://deepmind.google/blog/alphagenome-ai-for-better-understanding-the-genome/) và [Nature bài báo](https://www.nature.com/articles/s41586-025-10014-0) của Žiga Avsec, Natasha Latysheva và cộng sự (2025–2026). Các hình ảnh, kiến trúc mô hình, điểm benchmark thuộc bản quyền Google DeepMind. Bài viết không có mục đích thương mại; ghi rõ nguồn khi chia sẻ.

### Gợi ý đọc tiếp

- [AlphaMissense: AI đọc 71 triệu biến thể missense](/khoa-hoc/alphamissense-dot-bien-gen-nguoi/) (bài 5 trong series)
- [Siêu tính toán, dữ liệu sinh học và học sâu](/khoa-hoc/deepmind-sieu-tinh-toan-hoc-sau-sinh-hoc/) (bài 9)

### Tuyên bố miễn trừ trách nhiệm y tế / khoa học

**Đây không phải lời khuyên y tế.** Các thông tin trong bài chỉ dành cho mục đích giáo dục và tham khảo khoa học. AlphaGenome là công cụ nghiên cứu (research tool) — dự đoán của nó chưa được xác nhận cho chẩn đoán lâm sàng hay tiên lượng cá nhân. Không tự ý diễn giải kết quả mô hình AI thành quyết định y tế. Tham khảo ý kiến bác sĩ hoặc chuyên gia di truyền cho các vấn đề sức khoẻ cụ thể.
