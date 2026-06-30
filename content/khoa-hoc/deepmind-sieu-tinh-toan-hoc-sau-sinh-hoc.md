+++
title = "Siêu tính toán, dữ liệu sinh học và học sâu: phía sau các mô hình AI sinh học của DeepMind"
description = "Học sâu, dữ liệu Protein Data Bank, genomics ENCODE/GTEx và sức mạnh TPU — phía sau AlphaFold và các mô hình AI sinh học của DeepMind là gì?"
date = 2026-07-01

[taxonomies]
categories = ["Tất cả", "Khoa học", "Series"]
tags = ["khoa học", "google deepmind series", "học sâu", "alphafold", "protein", "tpu", "bioinformatics"]

[extra]
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
seo_keyword = "học sâu trong sinh học phân tử"
series = "google-deepmind"
series_part = 9
series_total = 10
toc = true

[[extra.faq]]
q = "Học sâu (deep learning) hoạt động thế nào trong dự đoán cấu trúc protein?"
a = "Học sâu trong AlphaFold dùng mạng neural nhiều lớp để học cách sắp xếp không gian của chuỗi amino acid từ hàng trăm nghìn cấu trúc đã biết — không cần định luật vật lý viết tay, mô hình tự 'học' từ dữ liệu."

[[extra.faq]]
q = "Dự đoán của AlphaFold có thay thế được thí nghiệm thật không?"
a = "Không. Dự đoán AI là công cụ hỗ trợ mạnh, nhưng thí nghiệm thực tế (X-ray, cryo-EM, NMR) vẫn là tiêu chuẩn vàng. AlphaFold chỉ đưa ra giả thuyết có độ tin cậy kèm theo — kết quả phải được kiểm chứng."

[[extra.faq]]
q = "Protein Data Bank (PDB) là gì và vì sao nó quan trọng với AI?"
a = "PDB là kho lưu trữ quốc tế chứa hơn 200.000 cấu trúc protein được xác định bằng thực nghiệm — đây là 'dữ liệu gốc' mà AlphaFold được huấn luyện trên đó."

[[extra.faq]]
q = "TPU là gì và tại sao AlphaFold cần nó?"
a = "TPU (Tensor Processing Unit) là chip chuyên dụng của Google cho machine learning. AlphaFold cần TPU vì mô hình có hàng trăm triệu tham số — huấn luyện trên CPU hay GPU thông thường mất quá lâu."
+++

> 🔬 **Series Khoa học — Google DeepMind & AI y sinh (Bài 9/10)** — [Bài 8](/khoa-hoc/alphaproteo-thiet-ke-protein-moi/) kể chuyện AI thiết kế protein mới. Bài này lùi lại một bước: nhìn vào **hạ tầng** đằng sau — dữ liệu, sức mạnh tính toán, và học sâu (deep learning) đã làm việc với dữ liệu sinh học như thế nào.

Tôi đã viết 8 bài về các mô hình AI của Google DeepMind: AlphaFold dự đoán cấu trúc protein, AlphaMissense phân loại đột biến, AlphaGenome dự đoán vùng điều hoà, AlphaProteo thiết kế protein mới. Nhưng tôi chưa dừng lại để hỏi: **thứ đổ vào các mô hình này là gì, và thứ bên trong chúng hoạt động ra sao?**

Bài này không đi vào công thức hay code. Tôi muốn kể câu chuyện về *dữ liệu* và *tính toán* — hai thứ âm thầm làm nên cuộc cách mạng.

<!-- more -->

## Dữ liệu sinh học: kho báu mất 50 năm để xây

Muốn AI học được ngôn ngữ sinh học, bạn phải cho nó *đọc* ngôn ngữ sinh học. Dữ liệu là nền tảng tuyệt đối.

### Protein Data Bank — "sách giáo khoa" cho AI về protein

**Protein Data Bank (PDB)** ([rcsb.org](https://www.rcsb.org/)) là kho lưu trữ quốc tế chứa cấu trúc protein được xác định bằng thực nghiệm (X-ray tinh thể học, cryo-EM, NMR). Theo [thống kê của wwPDB](https://www.wwpdb.org/stats/), PDB hiện có hơn 200.000 cấu trúc — con số tích luỹ từ năm 1971 tới nay.

Mỗi cấu trúc trong PDB là kết tinh của *tháng hoặc năm* thí nghiệm: các nhà khoa học tinh thể hoá protein, chiếu tia X, ghi nhận nhiễu xạ, tính toán mật độ electron, dựng mô hình nguyên tử — tất cả cho ra một file `.pdb` mô tả toạ độ từng nguyên tử.

Đây là dữ liệu mà AlphaFold được huấn luyện trên đó. Như [DeepMind giải thích](https://deepmind.google/science/alphafold/), mô hình học cách dự đoán khoảng cách giữa các cặp amino acid từ các cấu trúc đã biết, sau đó suy ra cấu trúc cho protein chưa từng được giải.

### AlphaFold tạo ra "PDB thứ hai"

Từ chỗ chỉ có 200.000 cấu trúc thực nghiệm, AlphaFold đã dự đoán thêm **hơn 200 triệu cấu trúc** — phủ gần như toàn bộ protein đã biết trong tự nhiên, theo [công bố của EMBL-EBI](https://alphafold.ebi.ac.uk/). Con số này được tích hợp vào cơ sở dữ liệu **AlphaFold DB** ([alphafold.ebi.ac.uk](https://alphafold.ebi.ac.uk/)).

Hơn **3 triệu nhà nghiên cứu** trên thế giới đã truy cập AlphaFold DB kể từ khi ra mắt, theo số liệu DeepMind công bố trên [trang Science của họ](https://deepmind.google/science/).

### Dữ liệu genomics: ENCODE, GTEx và hàng nghìn bộ gen người

Với AlphaGenome, dữ liệu đầu vào còn đồ sộ hơn:

- **ENCODE** ([encodeproject.org](https://www.encodeproject.org/)) — dự án 15 năm+ nhằm lập bản đồ toàn bộ vùng chức năng trong bộ gen người. Hàng nghìn thí nghiệm xác định đâu là vùng điều hoà, đâu là vùng phiên mã, đâu là vùng gắn protein.
- **GTEx** ([gtexportal.org](https://www.gtexportal.org/home/)) — đo mức biểu hiện gen ở hàng chục mô khác nhau từ hàng trăm người hiến tặng.
- **GWAS Catalog** ([ebi.ac.uk/gwas](https://www.ebi.ac.uk/gwas/)) — hàng chục nghìn biến thể gen liên quan tới bệnh.

Như [blog AlphaGenome của DeepMind](https://deepmind.google/blog/alphagenome-ai-for-better-understanding-the-genome/) chỉ rõ, mô hình của họ được huấn luyện trên toàn bộ dữ liệu này — hơn một triệu "chữ" DNA (nucleotide) trong một lần đọc, kết hợp với thông tin điều hoà từ ENCODE và dữ liệu biểu hiện gen từ GTEx.

## Học sâu (deep learning) với dữ liệu sinh học — giải thích đơn giản

Tôi biết nhiều bạn (kể cả tôi trước đây) nghe "deep learning" là thấy ngại. Tôi sẽ giải thích theo cách tôi đã *tự* hiểu.

<div class="box box--tip">
<strong>🧠 Hiểu đơn giản: học sâu hoạt động thế nào trong sinh học phân tử</strong>

<p>Hãy tưởng tượng bạn chưa bao giờ nhìn thấy con mèo. Tôi cho bạn xem 200.000 bức ảnh, mỗi bức có một con mèo, và nói "đây là mèo". Dần dần bạn bắt đầu thấy pattern: mèo có tai nhọn, ria mép, đuôi dài. Sau đó tôi cho bạn xem ảnh chụp một con vật bạn chưa thấy, bạn có thể nói "có thể nó là mèo" với độ chắc chắn nào đó.</p>

<p>AlphaFold làm y hệt vậy với protein. Nó "xem" 200.000 cấu trúc protein từ PDB — học pattern: nếu amino acid A ở vị trí 10, amino acid B ở vị trí 50, khoảng cách giữa chúng thường là X angstron. Sau đó nó nhìn vào dãy amino acid của protein mới và dự đoán: các nguyên tử này sẽ sắp xếp ra sao trong không gian?</p>

<p>Không ai viết luật vật lý tay cho AlphaFold. Nó tự học luật từ dữ liệu. Đó là bản chất của học sâu — <strong>máy học pattern từ ví dụ</strong>, không từ công thức.</p>
</div>

Mô hình học sâu trong AlphaFold có hàng trăm triệu "tham số" (parameters) — có thể hiểu nôm na là các núm xoay bên trong mô hình. Trong quá trình huấn luyện, mỗi núm xoay được tinh chỉnh hàng tỷ lần cho tới khi dự đoán khớp với cấu trúc thật nhất có thể.

## Dự đoán ≠ thí nghiệm thật

Đây là điểm tôi thấy nhiều người hiểu nhầm nhất, và tôi muốn dành hẳn một box cho nó.

<div class="box box--warning">
<strong>⚠️ Đừng hiểu lầm: dự đoán AI không phải bằng chứng thực nghiệm</strong>

<p>AlphaFold dự đoán cấu trúc protein với độ chính xác cao — nhưng <strong>dự đoán không phải kết quả thí nghiệm</strong>. Một cấu trúc từ X-ray tinh thể học có sai số ở mức sub-angstrom. Một cấu trúc AlphaFold có sai số lớn hơn, đặc biệt ở vùng linh hoạt hoặc vùng không có template trong PDB.</p>

<p>Trong nghiên cứu sinh học, <strong>tiêu chuẩn vàng</strong> vẫn là thực nghiệm: X-ray tinh thể học, cryo-EM, NMR, các assay chức năng. AlphaFold đưa ra <em>giả thuyết có độ tin cậy</em> — giả thuyết này sau đó phải được kiểm chứng.</p>

<p>Nếu bạn đọc báo nói "AI khám phá cấu trúc protein mới", hãy nhớ: AI <em>dự đoán</em>, con người <em>kiểm chứng</em>. Cả hai đều cần.</p>
</div>

### Độ tin cậy (confidence) — thứ AI có mà dự đoán không có

Một điểm tôi đánh giá cao ở các mô hình DeepMind: chúng **đi kèm độ tin cậy**.

- AlphaFold dùng **pLDDT** (predicted Local Distance Difference Test) — điểm từ 0 đến 100 cho mỗi vùng protein. Vùng nào pLDDT > 90 là rất chắc chắn; vùng < 50 là dự đoán yếu, có thể sai nhiều.
- AlphaMissense có **score pathogenicity** cho mỗi biến thể missense — từ 0 (lành tính) đến 1 (gây bệnh). Mô hình cũng báo vùng "không chắc chắn".
- AlphaProteo có **binding score** dự đoán khả năng protein thiết kế gắn được vào mục tiêu.

Tôi thấy đây là thái độ khoa học đúng đắn: không khẳng định chắc chắn, mà nói "tôi tin X%, đây là vùng tôi không chắc".

## Sức mạnh tính toán: vì sao cần TPU?

Huấn luyện AlphaFold không phải chuyện chạy trên laptop. Tôi tìm hiểu qua [các bài mô tả kỹ thuật của DeepMind](https://deepmind.google/science/):

### TPU — Tensor Processing Unit

**TPU** (Tensor Processing Unit) là chip chuyên dụng do Google thiết kế riêng cho machine learning. Khác với CPU (vài lõi mạnh, đa năng) hay GPU (hàng nghìn lõi nhỏ cho đồ hoạ), TPU là **ma trận tính toán khổng lồ** — tối ưu cho phép nhân ma trận, thao tác cốt lõi của mạng neural.

AlphaFold chạy trên **TPU v3** (và sau này TPU v4) — mỗi chip có thể thực hiện hàng chục nghìn tỷ phép tính mỗi giây. Toàn bộ quá trình huấn luyện mô hình AlphaFold 2 tốn **khoảng vài tuần trên 128 TPU** — nếu chạy trên CPU, con số có thể là *năm*.

### Vì sao AlphaFold cần siêu tính toán?

Mô hình học sâu của AlphaFold 2 có khoảng **93 triệu tham số**. Trong quá trình huấn luyện, mỗi tham số được cập nhật hàng triệu lần. Mỗi lần cập nhật đòi hỏi tính toán gradient (đạo hàm) qua toàn bộ mạng — đây là khối lượng tính toán khủng khiếp.

Không chỉ huấn luyện, suy luận (inference) cũng cần tính toán đáng kể. Dự đoán một cấu trúc protein cỡ trung bình (khoảng 400 amino acid) tốn vài phút đến vài giờ trên GPU, tuỳ độ phức tạp.

Để so sánh:

| Phương pháp | Thời gian | Chi phí ước tính |
|-------------|-----------|-----------------|
| X-ray tinh thể học (thực nghiệm) | Tháng – năm | $50.000 – $200.000+ / protein |
| Cryo-EM | Tháng | $20.000 – $100.000 / protein |
| AlphaFold dự đoán | Phút – giờ | Gần như miễn phí (điện + cloud compute) |

Con số chi phí thực nghiệm tôi tổng hợp từ [các báo cáo của HIgh-Throughput Crystallization](https://en.wikipedia.org/wiki/X-ray_crystallography) và [bài viết của Nature về structural biology economics](https://www.nature.com/articles/d41586-021-03509-1).

Tất nhiên, so sánh này hơi "gian" vì AlphaFold dựa trên dữ liệu thực nghiệm để huấn luyện. Nhưng nó cho thấy tiềm năng: thay vì tốn $100K cho mỗi protein, nhà nghiên cứu có thể dùng AI để khoanh vùng chỉ vài protein thực sự cần thí nghiệm tốn kém.

## Giới hạn mà tôi thấy cần ghi nhớ

Sau khi đọc và viết cả series này, tôi tổng kết giới hạn của các mô hình như sau:

1. **Chất lượng dự đoán phụ thuộc dữ liệu gốc** — nếu PDB thiếu protein họ hàng gần, AlphaFold dự đoán kém chính xác.
2. **Protein linh hoạt (disordered regions)** — AlphaFold dự đoán tệ nhất ở các vùng protein không có cấu trúc cố định.
3. **Tương tác phức tạp** — dù AlphaFold 3 đã tốt hơn, dự đoán tương tác protein-thuốc vẫn còn khoảng cách xa so với thực nghiệm.
4. **Không thay thế được chức năng sinh học** — cấu trúc là một phần; protein hoạt động ra sao trong tế bào còn phụ thuộc hàng trăm yếu tố khác.

## Tôi tự ghi chú lại như sau

Sau bài này, tôi tự ghi nhớ mấy điều:

- **Dữ liệu mới là "dầu" thật sự.** AI chỉ mạnh khi có dữ liệu chất lượng. PDB mất 50 năm để xây — AlphaFold thành công là nhờ đứng trên vai những nhà tinh thể học suốt nửa thế kỷ.
- **Đừng nhìn con số phổng phao (200 triệu cấu trúc) mà quên độ tin cậy đi kèm.** Một cấu trúc pLDDT thấp cũng vô dụng như không có.
- **Tính toán là "xương sống"** — không có TPU, không có quy mô Google Cloud, AlphaFold không thể ra đời. Khoa học hiện đại phụ thuộc hạ tầng công nghệ nhiều hơn tôi tưởng.
- **Dự đoán AI là giả thuyết, không phải kết luận.** Câu này tôi muốn nhắc lại mỗi khi đọc tin AI khám phá điều gì đó.

---

### Liên kết nội bộ

- [Bài 8 — AlphaProteo: khi AI bắt đầu thiết kế protein mới](/khoa-hoc/alphaproteo-thiet-ke-protein-moi/)
- [Bài 10 (tổng kết) — AI có thể thay đổi ngành y tế đến đâu](/khoa-hoc/ai-y-te-tu-alphafold-den-alphaproteo/)

### Liên kết bên ngoài

- [Google DeepMind — AlphaFold](https://deepmind.google/science/alphafold/)
- [Google DeepMind — Science overview](https://deepmind.google/science/)
- [AlphaGenome — AI for better understanding the genome](https://deepmind.google/blog/alphagenome-ai-for-better-understanding-the-genome/)
- [AlphaFold DB — EMBL-EBI](https://alphafold.ebi.ac.uk/)
- [Protein Data Bank (PDB)](https://www.rcsb.org/)
- [ENCODE Project](https://www.encodeproject.org/)
- [GTEx Portal](https://www.gtexportal.org/home/)

### Bản quyền & nguồn tham khảo

Bài viết tổng hợp từ tài liệu công khai của Google DeepMind (deepmind.google/science/), Protein Data Bank (rcsb.org), EMBL-EBI (alphafold.ebi.ac.uk), ENCODE Consortium, GTEx Consortium, Nature, Wikipedia. Nội dung nhằm mục đích giáo dục và phổ biến khoa học. Google DeepMind là thương hiệu của Google LLC.

### Gợi ý đọc tiếp

- Đọc lại toàn bộ Series [Google DeepMind & AI y sinh](/khoa-hoc/google-deepmind-ai-ngon-ngu-su-song/) từ đầu
- Cuốn *The Protein Folding Problem and Its Solutions* (2011) — bối cảnh khoa học trước AlphaFold
- Theo dõi [DeepMind Science Blog](https://deepmind.google/science/) để cập nhật mô hình mới

### Tuyên bố miễn trách nhiệm y tế / khoa học

Bài viết này không phải tư vấn y tế, không hướng dẫn chẩn đoán hay điều trị bệnh. Các dự đoán của AI (AlphaFold, AlphaMissense, AlphaGenome, AlphaProteo) là công cụ nghiên cứu, chưa được phê duyệt lâm sàng. Mọi quyết định y khoa phải dựa trên tư vấn của bác sĩ chuyên môn và các xét nghiệm/kết quả thực nghiệm đã được kiểm chứng.
