+++
title = "Sentence Transformers (SBERT) là gì? Kiến trúc"
description = "Phân tích kiến trúc bi-encoder, 4 cách training (softmax, contrastive, triplet, MNR), multilingual distillation và case study semantic search trên Zola."
date = 2026-06-15
aliases = ["/sentence-transformers-sbert-deep-dive/"]

[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["ai", "bert", "deep learning", "embeddings", "machine learning", "nlp", "python", "pytorch", "sbert", "sentence-transformers"]
[extra]
seo_keyword = "Sentence Transformers"
thumbnail = "https://banhang-chogao.github.io/zola/img/covers/sentence-transformers-sbert-deep-dive.svg"
featured = false
[[extra.faq]]
q = "Sentence Transformers (SBERT) là gì?"
a = "SBERT (Sentence-BERT) là biến thể của BERT dùng kiến trúc bi-encoder để mã hoá cả câu thành một vector embedding cố định. Nhờ đó có thể so sánh độ tương đồng ngữ nghĩa giữa các câu bằng cosine similarity rất nhanh, thay vì đưa từng cặp câu qua BERT."

[[extra.faq]]
q = "SBERT khác BERT gốc thế nào?"
a = "BERT gốc phải ghép 2 câu vào cùng một lần chạy để so sánh (cross-encoder) nên rất chậm khi có nhiều câu. SBERT mã hoá mỗi câu độc lập thành vector một lần rồi so sánh vector, nhanh hơn hàng nghìn lần cho bài toán tìm kiếm ngữ nghĩa."

[[extra.faq]]
q = "Model SBERT nào dùng tốt cho tiếng Việt?"
a = "Các model đa ngôn ngữ như paraphrase-multilingual-MiniLM-L12-v2 hay distiluse-base-multilingual-cased hỗ trợ tiếng Việt khá tốt và nhẹ. Cần chất lượng cao hơn thì fine-tune trên dữ liệu tiếng Việt riêng."

[[extra.faq]]
q = "Bi-encoder và cross-encoder khác gì nhau?"
a = "Bi-encoder mã hoá mỗi câu thành vector riêng nên nhanh, hợp tìm kiếm quy mô lớn. Cross-encoder đưa cả cặp câu vào model cùng lúc nên chính xác hơn nhưng chậm. Thực tế thường dùng bi-encoder lọc nhanh rồi cross-encoder xếp hạng lại top kết quả."

+++

![Sentence Transformers SBERT]

**Sentence Transformers** (SBERT) là một framework Python kết hợp với
một lớp model deep learning chuyên biệt để chuyển đổi text, hình ảnh
và âm thanh thành các **vector số học dense** (embeddings). Khác với
mô hình BERT gốc vốn tạo ra word-level embeddings cần pooling phức
tạp, SBERT sinh ra **sentence-level embeddings** sẵn sàng dùng cho
cosine similarity. Bài viết này phân tích chi tiết kiến trúc, phương
pháp training, các model phổ biến, và case study triển khai thực tế
trên blog tĩnh chạy GitHub Pages.

<!-- more -->

## 1. Bối cảnh: vấn đề của BERT gốc với sentence similarity

BERT (Bidirectional Encoder Representations from Transformers) do
Google công bố năm 2018 đã thay đổi NLP. Tuy nhiên, để tính similarity
giữa 2 câu, BERT gốc yêu cầu cách tiếp cận **cross-encoder**: feed cả
2 câu cùng lúc vào model, output classification score.

Với tập dữ liệu N câu, để tìm cặp similarity cao nhất cần `N × (N-1) /
2` lần inference. Với N=10,000, đó là **49,995,000 lần forward pass**
— hoàn toàn không khả thi production.

SBERT (Reimers & Gurevych, EMNLP 2019, paper *"Sentence-BERT: Sentence
Embeddings using Siamese BERT-Networks"*) giải quyết bằng kiến trúc
**bi-encoder**: encode mỗi câu thành vector cố định **một lần duy
nhất**, sau đó tính cosine similarity trên vector. Độ phức tạp giảm từ
O(N²) inference xuống O(N) inference + O(N²) dot product (rất nhanh
trên numpy).

## 2. Kiến trúc bi-encoder của Sentence Transformers

```
Sentence A ──► [BERT] ──► [Pooling] ──► Vector A (768-dim)
                                              │
                                              ▼
                                       Cosine similarity ──► Score
                                              ▲
                                              │
Sentence B ──► [BERT] ──► [Pooling] ──► Vector B (768-dim)
```

### Pooling strategies

Sau khi BERT output token embeddings (`[CLS], token_1, token_2, ...,
[SEP]`), cần pooling thành 1 vector duy nhất:

| Strategy | Mô tả | Khi dùng |
|---|---|---|
| `[CLS]` token | Lấy embedding của token đặc biệt đầu chuỗi | BERT gốc |
| **Mean pooling** | Trung bình tất cả token (loại padding) | SBERT default — tốt nhất |
| Max pooling | Max từng chiều qua tất cả token | Một số task đặc thù |

Mean pooling thắng [CLS] trong hầu hết benchmark vì tận dụng được mọi
token context, không chỉ vị trí 0.

### Output dimension

- BERT-base: **768 chiều**
- BERT-large: **1024 chiều**
- DistilBERT: **768 chiều** (nhỏ hơn, nhanh hơn ~60%)
- MiniLM: **384 chiều** (gọn nhất, vẫn giữ 95% accuracy)

Chiều thấp = lưu trữ nhỏ, dot product nhanh. Trade-off với accuracy.

## 3. Phương pháp training

SBERT training dùng **siamese network** hoặc **triplet network** với 3
loss function chính.

### 3.1. Softmax loss (NLI training)

Dữ liệu: SNLI + MultiNLI (~1M cặp câu) với label `entailment`,
`contradiction`, `neutral`.

Pipeline:

1. Encode câu u và câu v qua BERT shared weights
2. Concat `[u, v, |u-v|]` → linear → softmax 3 class
3. Cross-entropy loss

Trick `|u-v|` là vector element-wise absolute difference — capture
semantic distance. Đây là kỹ thuật quan trọng giúp embedding vector
hữu ích downstream.

### 3.2. Contrastive loss (MSE training)

Dữ liệu: STS Benchmark (8,628 cặp với continuous score 0-5).

Mục tiêu: cosine similarity giữa u và v ≈ ground truth score.

Loss = MSE(cosine(u, v), gold_score)

Đơn giản hơn softmax, hiệu quả với task regression similarity.

### 3.3. Triplet loss

Dữ liệu: triplets `(anchor, positive, negative)` — positive cùng nghĩa
với anchor, negative khác nghĩa.

Loss = `max(||u_anchor - u_positive|| - ||u_anchor - u_negative|| +
margin, 0)`

Mục tiêu: kéo positive gần anchor, đẩy negative xa anchor ít nhất
`margin` đơn vị. Margin thường = 1.0.

### 3.4. Multiple Negatives Ranking (MNR) loss

State-of-the-art hiện tại (paper Henderson et al., 2017). Cho batch
size B với B cặp positive `(query_i, doc_i)`:

- Mỗi `query_i` coi `doc_i` là positive
- Coi `doc_j` (j ≠ i) trong cùng batch là **negative ngầm định**
- Cross-entropy trên B-way classification

Ưu điểm: không cần curate hard negatives thủ công. Batch size lớn →
nhiều negative free → contrastive signal mạnh.

## 4. Multilingual models

Một trong những đột phá lớn nhất: **multilingual SBERT** hỗ trợ 50+
ngôn ngữ trong cùng vector space. Bài tiếng Anh và bài tiếng Việt
cùng nghĩa sẽ có cosine similarity cao.

Phương pháp: **multilingual knowledge distillation** (Reimers &
Gurevych, 2020). Train multilingual student model bằng cách mô phỏng
embedding của English teacher model trên parallel corpora:

1. Teacher: `sentence-transformers/all-mpnet-base-v2` (English)
2. Student: `xlm-roberta-base` (multilingual base)
3. Loss = MSE(student(en), teacher(en)) + MSE(student(non-en),
   teacher(en))

Kết quả: student học mapping tất cả ngôn ngữ về cùng vector space với
English.

### Models multilingual phổ biến

| Model | Size | Dim | Languages | Use case |
|---|---|---|---|---|
| `paraphrase-multilingual-MiniLM-L12-v2` | 120MB | 384 | 50+ | Production nhẹ, default |
| `paraphrase-multilingual-mpnet-base-v2` | 500MB | 768 | 50+ | Accuracy cao hơn |
| `LaBSE` (Google) | 1.8GB | 768 | 109 | Cross-lingual retrieval |
| `distiluse-base-multilingual-cased-v2` | 480MB | 512 | 50+ | Balance speed/accuracy |

## 5. So sánh chi tiết: bi-encoder vs cross-encoder

| Aspect | Bi-encoder (SBERT) | Cross-encoder (BERT) |
|---|---|---|
| Speed (10k pairs) | 0.5 giây | ~1 giờ |
| Accuracy | ~84% Spearman STS | ~88% Spearman STS |
| Vector cached | Có | Không |
| Use case | Semantic search, clustering | Re-ranking, pair classification |

**Best practice**: 2-stage retrieval. Dùng bi-encoder retrieve top-100
candidates nhanh, rồi cross-encoder re-rank top-100 → top-10 cuối
cùng. Kết hợp tốt nhất 2 thế giới.

## 6. Code minimal

```python
from sentence_transformers import SentenceTransformer
import numpy as np

# Load model multilingual
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# Encode 3 câu
sentences = [
    "Tối ưu hóa hình ảnh cho website",
    "Tăng tốc độ tải trang web",
    "Công thức nấu phở bò",
]
embeddings = model.encode(
    sentences,
    normalize_embeddings=True,   # quan trọng để cosine = dot product
    show_progress_bar=False,
)
print(embeddings.shape)  # (3, 384)

# Similarity matrix
sim = np.dot(embeddings, embeddings.T)
print(sim)
# [[1.00, 0.74, 0.12],
#  [0.74, 1.00, 0.15],
#  [0.12, 0.15, 1.00]]
```

Câu 1 và câu 2 có similarity 0.74 dù KHÔNG chia sẻ từ khóa nào ("ảnh"
vs "tải trang") — model hiểu ngữ nghĩa cùng chủ đề performance. Câu 3
isolate ~ 0.1.

## 7. Use cases sản xuất

### 7.1. Semantic Search

Index toàn bộ document corpus thành vectors, lưu trong vector database
(FAISS, Milvus, Pinecone, pgvector). Khi user query:

1. Encode query → vector
2. Approximate Nearest Neighbor (ANN) search trên index
3. Return top-K most similar documents

ANN dùng HNSW (Hierarchical Navigable Small World) hoặc IVF (Inverted
File Index) để search sub-millisecond trên hàng trăm triệu vectors.

### 7.2. Semantic Clustering

K-means hoặc HDBSCAN trên vectors → tự động group documents theo chủ
đề mà KHÔNG cần label trước. Hữu ích cho:

- Topic discovery trong customer feedback
- Duplicate detection
- News article clustering

### 7.3. Related Posts trên blog tĩnh

Đây chính là use case blog này áp dụng:

```python
# Build-time pipeline
posts = load_all_posts()
embeddings = model.encode([p.title + " " + p.body for p in posts],
                          normalize_embeddings=True)
sim_matrix = np.dot(embeddings, embeddings.T)

# Top-5 related per post
for i, post in enumerate(posts):
    scores = sim_matrix[i].copy()
    scores[i] = -1   # exclude self
    top_5 = np.argsort(scores)[::-1][:5]
    post.related = [(posts[j].slug, scores[j]) for j in top_5]

# Output JSON tĩnh
json.dump(related_data, open("data/related.json", "w"))
```

Chạy build-time qua GitHub Actions cron, output JSON → Tera template
render → 0 cost runtime. Workflow `build-related.yml` trên repo này
chính là implementation của pattern này.

### 7.4. Zero-shot Classification

Cho labels là text description, encode cả document và label, label nào
similarity cao nhất → predicted class. KHÔNG cần training data có
label sẵn.

```python
labels = ["công nghệ", "ẩm thực", "du lịch"]
doc = "Phở bò Hà Nội ngon nhất quận Ba Đình"
label_emb = model.encode(labels, normalize_embeddings=True)
doc_emb = model.encode([doc], normalize_embeddings=True)
scores = np.dot(doc_emb, label_emb.T)[0]
print(labels[np.argmax(scores)])  # 'ẩm thực'
```

## 8. Performance benchmarks

Tốc độ encode trên 1 GPU NVIDIA T4 (free tier Colab):

| Model | Sentences/sec | Throughput |
|---|---|---|
| MiniLM-L6-v2 | 14,000 | Real-time API OK |
| MiniLM-L12-v2 | 7,500 | Real-time API OK |
| MPNet-base-v2 | 2,800 | Batch process OK |
| LaBSE | 1,200 | Batch only |

Trên CPU (no GPU), throughput giảm ~10-20x. Vẫn đủ dùng cho blog
~100-1000 documents build-time.

## 9. Best practices

1. **Always normalize embeddings** với `normalize_embeddings=True` →
   cosine = dot product = nhanh hơn nhiều
2. **Cache embeddings** vào disk/database — không re-encode trừ khi
   text thay đổi (check hash)
3. **Choose model theo trade-off**: MiniLM cho production scale lớn,
   MPNet cho accuracy critical
4. **Multilingual cho VN content** — luôn dùng `paraphrase-multilingual-*`
   thay vì English-only model
5. **Quantization INT8** giảm size 4x với <2% accuracy loss qua thư
   viện `optimum`
6. **ONNX export** cho production inference nhanh hơn 3-5x vs PyTorch
   native

## 10. Hạn chế và bài học

- **Context length 512 tokens** (~400 từ tiếng Anh, ~250 từ tiếng
  Việt) — bài dài hơn phải truncate hoặc chia chunks
- **Domain shift**: model train trên Wikipedia/news, không tự hiểu
  từ vựng đặc thù (y khoa, luật). Cần **fine-tune** với data domain
- **Semantic ≠ factual**: similarity cao không có nghĩa đúng sự thật.
  Đừng dùng để verify facts
- **Vector drift**: cập nhật model version → vectors cũ KHÔNG còn
  tương thích → phải re-encode tất cả

## Kết luận

SBERT đã trở thành công cụ chuẩn cho mọi task semantic understanding.
Triết lý đơn giản — bi-encoder + contrastive loss — nhưng thay đổi
hoàn toàn cách industry tiếp cận semantic search và clustering.

Trên blog này, sentence-transformers chạy build-time qua GitHub
Actions, output JSON tĩnh, web load 0 cost runtime. Đó là minh chứng:
AI deep learning hoàn toàn có thể áp dụng cho **static site personal
blog** mà không cần backend server, không cần GPU runtime, không cần
trả phí inference per request.

Để xem implementation cụ thể của pipeline này, đọc thêm bài
[Hành trình công nghệ ngày đầu](/zola/posting/cong-nghe-blog-duy-nguyen/)
hoặc [Syntax highlighting trong Zola: từ cơ bản đến custom theme](/zola/posting/tao-blog-voi-zola/)
nếu bạn quan tâm Zola SSG nói chung.

Repo gốc: [github.com/UKPLab/sentence-transformers](https://github.com/UKPLab/sentence-transformers).
Documentation: [sbert.net](https://www.sbert.net). Paper gốc:
*"Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks"*
(Reimers & Gurevych, EMNLP 2019).
