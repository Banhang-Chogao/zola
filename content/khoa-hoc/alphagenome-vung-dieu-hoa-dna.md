+++

title = "Đột biến gen không chỉ nằm trong vùng mã hoá: vì sao AlphaGenome quan trọng?"
description = "AlphaGenome — mô hình AI của Google DeepMind dự đoán ảnh hưởng của biến thể DNA lên điều hoà gen, mở rộng phân tích ra ngoài vùng mã hoá protein, vào 98% bộ gen từng bị gọi là 'DNA rác'."
date = 2026-07-01

[taxonomies]
categories = ["Tất cả", "Khoa học", "Series"]
tags = ["khoa học", "google deepmind series", "alphagenome", "điều hoà gen", "non-coding DNA", "DNA rác", "biểu sinh học", "genomics"]

[extra]
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
seo_keyword = "AlphaGenome điều hoà DNA"
series = "google-deepmind"
series_part = 6
series_total = 10
[[extra.faq]]
q = "AlphaGenome là gì?"
a = "AlphaGenome là mô hình AI của Google DeepMind dự đoán ảnh hưởng của biến thể DNA lên quá trình điều hoà gen — bao gồm biểu hiện gen, splicing, khả năng tiếp cận DNA và liên kết yếu tố phiên mã."
[[extra.faq]]
q = "AlphaGenome khác AlphaMissense thế nào?"
a = "AlphaMissense phân loại biến thể trong vùng mã hoá (chỉ 2% bộ gen). AlphaGenome phân tích các biến thể trong vùng không mã hoá (98% còn lại) — nơi điều khiển khi nào, ở đâu và bao nhiêu protein được tạo ra."
[[extra.faq]]
q = "AlphaGenome có đọc được toàn bộ bộ gen không?"
a = "AlphaGenome có thể tiếp nhận đầu vào lên tới 1 triệu nucleotide DNA để dự đoán, nhưng không phải là mô hình giải mã toàn bộ bộ gen. Nó dự đoán các đặc tính điều hoà hơn là hiểu mọi chức năng DNA."
[[extra.faq]]
q = "Dữ liệu huấn luyện AlphaGenome từ đâu?"
a = "AlphaGenome được huấn luyện trên dữ liệu từ các dự án hợp tác nghiên cứu lớn: ENCODE, GTEx, 4D Nucleome và FANTOM5 — tất cả đều là các consortium công khai."
[[extra.references_external]]
title = "Google DeepMind — AlphaGenome: AI for better understanding the genome"
url = "https://deepmind.google/blog/alphagenome-ai-for-better-understanding-the-genome/"
[[extra.references_external]]
title = "Google DeepMind — Science page"
url = "https://deepmind.google/science/"
+++

Bài 6 trong series **Google DeepMind & nghiên cứu y sinh**.

Ở [bài 5](/khoa-hoc/alphamissense-dot-bien-gen-nguoi/), mình đã viết về AlphaMissense — công cụ phân loại biến thể missense trong các gen mã hoá protein. Nhưng câu chuyện đột biến gen không dừng ở đó. Thực tế, phần lớn bộ gen của con người — tới 98% — không mã hoá protein gì cả. Vậy 98% đó có chức năng gì? Và vì sao AlphaGenome của DeepMind lại tập trung vào nó?

<!-- more -->

## Câu chuyện về 2% và 98%

Nếu bộ gen người là một cuốn sách dài 3,2 tỷ chữ cái, thì chỉ khoảng 2% — khoảng 64 triệu chữ — là **vùng mã hoá** (coding region), nơi chứa các gen sản xuất protein. Đây là phần đã được nghiên cứu rất nhiều. AlphaFold dự đoán cấu trúc của protein từ chính các gen này. AlphaMissense phân loại đột biến làm thay đổi amino acid trong các protein đó.

98% còn lại từng bị gọi là **"DNA rác" (junk DNA)** — một cái tên ra đời từ thời các nhà khoa học chưa hiểu nó làm gì. Giờ ta đã biết: phần lớn vùng không mã hoá này đóng vai trò **điều hoà (regulatory)**: nó quyết định khi nào, ở đâu, với số lượng bao nhiêu một gen sẽ được "bật" lên.

[Theo blog của DeepMind về AlphaGenome](https://deepmind.google/blog/alphagenome-ai-for-better-understanding-the-genome/), các biến thể trong vùng điều hoà này có liên quan đến nhiều bệnh phức tạp, nhưng việc dự đoán chúng gây ảnh hưởng thế nào vẫn còn rất khó khăn.

> **Hiểu đơn giản:**
> 
> Hãy tưởng tượng bộ gen là một nhà máy lớn:
> - Vùng **mã hoá** (coding) là các dây chuyền sản xuất — nơi protein thực sự được tạo ra.
> - Vùng **không mã hoá** (non-coding) là đội ngũ quản lý, bảng điều khiển, lịch trình, cảm biến — quyết định dây chuyền nào chạy, khi nào chạy và chạy với công suất bao nhiêu.
> 
> AlphaMissense giỏi phát hiện lỗi trên dây chuyền sản xuất. AlphaGenome giỏi phát hiện lỗi trong bảng điều khiển.

## Các cơ chế điều hoà gen

Vùng không mã hoá ảnh hưởng đến biểu hiện gen qua nhiều cơ chế. AlphaGenome dự đoán ảnh hưởng của biến thể đến vài quá trình then chốt:

**Biểu hiện gen (gene expression):** Một gen có thể được phiên mã nhiều hay ít tùy vào tín hiệu từ vùng điều hoà phía trước nó (promoter, enhancer). Biến thể ở vùng này có thể khiến gen hoạt động quá mức (gây ung thư) hoặc không hoạt động đủ (gây thiếu hụt protein).

**Splicing — cắt nối RNA:** DNA được phiên mã ra tiền-mRNA, sau đó các đoạn intron (không mã hoá) bị cắt bỏ và exon (mã hoá) được nối lại. Quá trình này gọi là splicing. Biến thể ở vùng splice-site có thể làm sai lệch cách cắt nối, tạo ra protein dị dạng. [Tham khảo thêm trên trang Science của DeepMind](https://deepmind.google/science/).

**Khả năng tiếp cận DNA (chromatin accessibility):** DNA trong tế bào không phải là sợi trần — nó được quấn quanh protein histone và nén chặt trong nhân tế bào. Một số vùng DNA được "mở" để sẵn sàng cho phiên mã, số khác bị "đóng". Biến thể có thể ảnh hưởng đến cấu trúc này.

**Liên kết yếu tố phiên mã:** Các protein gọi là yếu tố phiên mã (transcription factor) bám vào DNA để kích hoạt hoặc ức chế gen. Một biến thể nhỏ ở vị trí bám có thể làm mất hoặc tăng ái lực liên kết, thay đổi toàn bộ chương trình biểu hiện gen.

## AlphaGenome khác gì AlphaMissense?

Đây là câu hỏi mình thấy nhiều người thắc mắc. Cả hai đều là mô hình AI phân tích tác động của biến thể DNA, nhưng phạm vi khác nhau:

| Tiêu chí | AlphaMissense | AlphaGenome |
|-----------|---------------|-------------|
| Vùng phân tích | Vùng mã hoá protein (exon) | Vùng không mã hoá + mã hoá |
| Đầu ra | Gây bệnh/lành tính | Nhiều đầu ra riêng (biểu hiện gen, splicing, accessibility...) |
| Cơ sở | Cấu trúc protein (AlphaFold) + tiến hoá | Dữ liệu thực nghiệm (ENCODE, GTEx...) |
| Kích thước đầu vào | Một biến thể đơn lẻ | Lên tới 1 triệu nucleotide |
| Ứng dụng chính | Bệnh di truyền hiếm (monogenic) | Bệnh phức tạp (đa gen, ung thư) |

[Theo phân tích trên blog DeepMind](https://deepmind.google/blog/alphagenome-ai-for-better-understanding-the-genome/), AlphaGenome có thể tiếp nhận một đoạn DNA lên tới **1 triệu chữ cái** và dự đoán các tính chất điều hoà ở từng vị trí trong đó. Đây là bước tiến lớn so với các mô hình trước đây vốn chỉ nhìn được vài nghìn base.

## AlphaGenome hoạt động thế nào? (phiên bản người không học AI)

Không đi sâu vào kiến trúc mạng neuron (mình cũng không phải chuyên gia AI), nhưng mình có thể giải thích ý tưởng chính:

AlphaGenome thuộc loại mô hình **self-supervised learning** tương tự các mô hình ngôn ngữ lớn. Nó học cách "hiểu" ngữ pháp của bộ gen bằng cách tự dự đoán các đoạn DNA bị che đi, giống như cách GPT học ngôn ngữ bằng cách đoán từ tiếp theo.

Sau khi học xong "ngữ pháp", mô hình được fine-tune với dữ liệu thực nghiệm từ các dự án consortium:

- **ENCODE** (Encyclopedia of DNA Elements) — bản đồ các vùng chức năng trong bộ gen người.
- **GTEx** (Genotype-Tissue Expression) — dữ liệu về mối liên hệ giữa biến thể gen và mức biểu hiện gen ở nhiều mô khác nhau.
- **4D Nucleome** — dữ liệu về cấu trúc không gian 3D và 4D của DNA trong nhân tế bào.
- **FANTOM5** — bản đồ promoter và enhancer hoạt động ở nhiều loại tế bào.

[DeepMind ghi nhận](https://deepmind.google/blog/alphagenome-ai-for-better-understanding-the-genome/) sự hợp tác của các consortium này là yếu tố quan trọng để AlphaGenome có dữ liệu chất lượng cao.

## Tại sao AlphaGenome quan trọng?

Có một thực tế: hầu hết các **genome-wide association studies (GWAS)** — nghiên cứu tìm mối liên hệ giữa biến thể gen và bệnh tật — phát hiện ra rằng biến thể liên quan đến bệnh thường nằm ở vùng không mã hoá, không phải trong gen.

Ví dụ: một nghiên cứu GWAS về nguy cơ mắc tiểu đường type 2 có thể tìm ra một biến thể trên nhiễm sắc thể số X, nhưng biến thể đó lại nằm giữa hai gen, không nằm trong gen nào cả. Trước đây, ta không biết biến thể đó ảnh hưởng tới gen nào, bằng cách nào.

AlphaGenome giúp trả lời: biến thể đó có nằm trong vùng enhancer không? Enhancer đó điều khiển gen nào? Liệu nó có làm thay đổi mức biểu hiện gen ở mô tuỵ không?

[Theo công bố của DeepMind](https://deepmind.google/science/), mô hình có thể dự đoán ảnh hưởng của biến thể lên biểu hiện gen ở nhiều loại mô khác nhau — điều cực kỳ quan trọng vì cùng một biến thể có thể ảnh hưởng đến gan khác với não.

## Ứng dụng tiềm năng

**Ung thư:** Nhiều biến thể gây ung thư nằm ở vùng điều hoà — ví dụ, đột biến ở vùng promoter của gen *TERT* (một gen liên quan đến khả năng tự tái tạo của tế bào) là một trong những đột biến phổ biến nhất trong ung thư. AlphaGenome có thể giúp phân tích tác động của những biến thể này.

**Bệnh đa gen phức tạp:** Tiểu đường, tăng huyết áp, tự kỷ, tâm thần phân liệt — những bệnh này chịu ảnh hưởng của hàng trăm, thậm chí hàng nghìn biến thể nhỏ, mỗi biến thể đóng góp một phần rủi ro nhỏ. Hiểu được biến thể nào trong vùng điều hoà ảnh hưởng đến gen nào giúp ghép mảnh ghép lại với nhau.

**Y học cá thể hoá:** Mỗi người có hàng triệu biến thể riêng. Phần lớn vô hại, nhưng một số ảnh hưởng đến nguy cơ bệnh hoặc đáp ứng thuốc. AlphaGenome có thể giúp sàng lọc.

> **Đừng hiểu lầm:**
> 
> AlphaGenome **không phải** công cụ giải mã toàn bộ bộ gen. Nó không đọc DNA và nói cho bạn biết bạn mắc bệnh gì. Nó dự đoán các **đặc tính phân tử** (molecular phenotypes) — mức biểu hiện gen, cường độ splicing, v.v.
> 
> Nó cũng không thay thế được thí nghiệm thực tế. Dự đoán về điều hoà gen vẫn cần được kiểm chứng bằng các kỹ thuật như ChIP-seq, ATAC-seq hoặc CRISPR-based reporter assays.
> 
> Cuối cùng, AlphaGenome hiện vẫn là mô hình nghiên cứu — không phải công cụ lâm sàng đã được phê duyệt.

## Tôi tự ghi chú lại như sau

1. **AlphaMissense + AlphaGenome là hai mặt của cùng một đồng xu.** Một cái nhìn vào vùng mã hoá (2%), một cái nhìn vào vùng điều hoà (98%). Để hiểu đầy đủ ảnh hưởng của một biến thể gen, ta cần cả hai.

2. **Khái niệm "DNA rác" đã chết.** Càng nghiên cứu, ta càng thấy vùng không mã hoá có tổ chức tinh vi đến mức nào. Gọi nó là "rác" là thiếu công bằng.

3. **Dữ liệu consortium là chìa khoá.** AlphaGenome không thể tồn tại nếu không có ENCODE, GTEx, 4D Nucleome và FANTOM5. Những dự án lớn, công khai, hợp tác quốc tế này mới thực sự là nền tảng cho tiến bộ.

4. **Khoảng cách còn rất xa.** Từ dự đoạn in silico đến hiểu được cơ chế bệnh sinh rồi đến phát triển thuốc — đó là một hành trình rất dài. AlphaGenome mới giúp ta nhìn rõ hơn ở bước đầu tiên.

---

## Liên kết nội bộ

- Bài trước: [AlphaMissense: AI đọc 71 triệu biến thể missense](/khoa-hoc/alphamissense-dot-bien-gen-nguoi/) — phần 5: phân loại biến thể trong vùng mã hoá
- Bài kế tiếp: [AlphaGenome hoạt động ra sao](/khoa-hoc/alphagenome-doc-mot-trieu-chu-dna/) — phần 7: kỹ thuật đằng sau mô hình 1 triệu nucleotide

## Liên kết bên ngoài

- [Google DeepMind Blog — AlphaGenome: AI for better understanding the genome](https://deepmind.google/blog/alphagenome-ai-for-better-understanding-the-genome/)
- [Google DeepMind — Science Page](https://deepmind.google/science/)
- [ENCODE Project](https://www.encodeproject.org/)
- [GTEx Portal](https://gtexportal.org/)
- [4D Nucleome Project](https://www.4dnucleome.org/)
- [FANTOM5](https://fantom.gsc.riken.jp/5/)

## Bản quyền & nguồn tham khảo

Bài viết được biên soạn dựa trên thông tin từ Google DeepMind (blog và trang Science), các consortium ENCODE, GTEx, 4D Nucleome và FANTOM5. Nội dung được diễn giải lại nhằm mục đích phổ biến kiến thức khoa học. Các liên kết đến cơ sở dữ liệu công khai được dẫn để người đọc tự kiểm chứng.

## Gợi ý đọc tiếp

- Bài 2 trong series: [AlphaFold là gì: vì sao dự đoán cấu trúc protein từng là bài toán 50 năm?](/khoa-hoc/alphafold-la-gi-cau-truc-protein/)
- Bài 5: [AlphaMissense: AI đọc 71 triệu biến thể missense](/khoa-hoc/alphamissense-dot-bien-gen-nguoi/)
- [Bảng mã codon DNA và RNA](/khoa-hoc/bang-ma-codon-dna-rna/) — kiến thức nền về mã di truyền

## Tuyên bố miễn trừ trách nhiệm y tế / khoa học

Bài viết này chỉ mang tính chất giáo dục và phổ biến kiến thức khoa học. Nó **không** phải lời khuyên y tế, chẩn đoán hay hướng dẫn điều trị. AlphaGenome là mô hình nghiên cứu, không phải công cụ chẩn đoán lâm sàng đã được cơ quan quản lý phê duyệt. Mọi quyết định liên quan đến sức khỏe cần được thực hiện bởi bác sĩ có chuyên môn. Dự đoán của AlphaGenome về điều hoà gen là kết quả tính toán, cần được kiểm chứng thực nghiệm trước khi sử dụng trong nghiên cứu hoặc ứng dụng lâm sàng.

