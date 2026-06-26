# Chiến lược SEO & Bộ từ khoá — Blog "Duy Nguyen"

> Tài liệu nội bộ (không publish — nằm ngoài `content/`). Tổng hợp từ nghiên cứu SERP tiếng Việt thật (tháng 6/2026) cho 4 mảng: Công nghệ, Du lịch Hàn Quốc, Ẩm thực, Ngân hàng.
> Cập nhật: 16/06/2026.

---

## 0. TL;DR — đọc cái này trước

**Vấn đề bạn nêu đúng:** không ai search "Duy Nguyen". Brand search ≈ 0, lại là blog mới, độ uy tín tên miền (DA) thấp, host GitHub Pages. → **Không thể** dựa vào tên blog, cũng **không thể** đú các từ khoá "đầu" (head term) như *du lịch hàn quốc*, *tối nay ăn gì*, *ngân hàng số*… vì SERP đã bị Klook / Traveloka / Foody / web ngân hàng (DA cực cao) khoá chặt.

**Lời giải (cốt lõi của cả tài liệu):**
1. **Không đi tìm traffic qua tên blog — đi tìm qua NHU CẦU người đọc gõ vào Google.** Brand search sẽ tự lớn *sau khi* bạn xếp hạng cho nội dung hữu ích, không phải ngược lại.
2. **Niche down + long-tail.** Thắng ở từ khoá dài, cụ thể, ít cạnh tranh (vd *"lịch trình Busan tự túc 3 ngày 2 đêm"*, *"trời mưa Sài Gòn ăn gì"*, *"tạo blog với Zola"*) thay vì từ ngắn.
3. **Vũ khí độc quyền = E-E-A-T "Experience".** Giọng "thổ địa / ngôi thứ nhất / tôi đã đi, đã ăn, đã code" mà Klook/Foody/ngân hàng KHÔNG thể sao chép.
4. **Gom thành cụm chủ đề (topic cluster) + internal link** để dồn "topical authority" cho từng mảng.

**Thứ tự ưu tiên đầu tư (quan trọng):**

| Hạng | Mảng | Vì sao | Độ khả thi |
|---|---|---|---|
| 🥇 | **Công nghệ (Zola / tự động hoá blog / AI có code)** | "tạo blog với zola" gần như **không có đối thủ tiếng Việt** (blog đã top 1). Tech tiếng Việt dễ hơn tiếng Anh. | **Cao nhất** |
| 🥈 | **Du lịch Hàn Quốc** | Lịch trình Busan/Jeju tự túc — SERP đã lọt blog cá nhân. Nhu cầu lớn, mùa vụ rõ. | Cao |
| 🥉 | **Ẩm thực (Sài Gòn + Hàn)** | Long-tail ngữ cảnh (mưa/đêm/quận/dịp) bị aggregator bỏ trống chiều sâu. | Trung bình |
| 4 | **Ngân hàng / tài chính** | YMYL khắc nghiệt — **chỉ làm nhẹ** (tin ngách + giải thích công nghệ), không thành trụ cột. | Thấp (làm chọn lọc) |

---

## 1. Định hướng chiến lược

### 1.1 Tại sao "Duy Nguyen" không kéo được organic search
- Tên cá nhân, không gắn với nhu cầu tìm kiếm nào → 0 brand volume.
- Blog mới + GitHub Pages subpath (`/zola/`) + ít backlink → DA thấp.
- Mọi vertical đều bị domain DA cao thống trị ở từ khoá ngắn.

### 1.2 Bốn nguyên tắc nền tảng
1. **Topical authority, không phải brand.** Chọn vài ngách hẹp, viết sâu & nhiều → Google coi blog là "chuyên gia" mảng đó → xếp hạng cả từ khoá mới. Đây là con đường duy nhất cho blog không brand.
2. **Search intent first.** Mỗi bài nhắm đúng 1 ý định: *thông tin* (là gì / vì sao), *điều hướng*, *thương mại điều tra* (so sánh / review), *giao dịch*. Đừng trộn.
3. **E-E-A-T qua trải nghiệm thật.** Ảnh tự chụp, số liệu thật, "tôi đã…", ngày cập nhật rõ ràng. Với YMYL (ngân hàng) thì bắt buộc + disclaimer.
4. **Pillar → Cluster → Internal link.** 1 bài "trụ" (pillar) bao quát + nhiều bài con long-tail trỏ về nhau.

### 1.3 Đáp án trực diện cho lo lắng của bạn
> "Tên blog không ai search" → **đúng, và không sao cả.** Mục tiêu không phải để người ta search "Duy Nguyen", mà để khi ai đó gõ *"đi Hàn mùa nào rẻ nhất"* hay *"tạo blog với Zola"*, **bài của bạn nằm top**. Làm tốt 6–12 tháng, lượng truy cập đến từ hàng trăm từ khoá long-tail — không phụ thuộc tên blog chút nào.

---

## 2. Bộ từ khoá theo mảng

> Quy ước: **Cạnh tranh** = ước lượng định tính từ SERP thật (không phải số volume). Ưu tiên cụm **Thấp/TB** cho blog mới.

### 2.1 🥇 CÔNG NGHỆ — mỏ vàng, đầu tư mạnh nhất

**Phát hiện then chốt:** blog **đã rank #1 "tạo blog với zola"** (SERP còn lại toàn tiếng Anh/Medium). Mảng Zola/SSG tiếng Việt gần như trống. Viblo/200Lab mạnh nhưng chỉ ở Laravel/Node/React — **không ai làm Rust/Zola/blog tĩnh thuần**.

**Primary keywords:**

| Từ khoá | Intent | Cạnh tranh | Ghi chú |
|---|---|---|---|
| tạo blog với zola | How-to | **Thấp** ⭐ | Đã top 1, đào sâu ngay |
| github actions tự động deploy | How-to | TB | Né góc static site/GitHub Pages còn trống |
| deploy github pages miễn phí | How-to | TB | Bài text chi tiết còn thiếu (đa số là video) |
| static site generator là gì | Thông tin | TB | Nội dung top đang nông |
| sentence transformers là gì | Thông tin | TB-cao | Thắng bằng deep-dive + code |
| semantic search bằng python | Thông tin | **Thấp-TB** ⭐ | Content gap lớn (SERP bị khối SEO-marketing chiếm sai intent) |
| embeddings cho văn bản tiếng việt | Thông tin | TB | Ngách multilingual còn trống |

**Long-tail clusters:**
- **Zola/SSG:** zola tiếng việt hướng dẫn · cài đặt zola windows/mac/linux · zola vs hugo · tùy biến theme zola · thêm tiếng việt vào zola (i18n) · config.toml zola · tera template cơ bản.
- **GitHub Actions/CI-CD:** github actions tự động deploy github pages · viết file deploy.yml · ci/cd cho blog cá nhân · github actions cron job · tự động build & deploy zola · workflow cho người mới.
- **AI/Embeddings:** sentence transformers tiếng việt · cách tạo embeddings tiếng việt · so sánh độ tương đồng văn bản python · SBERT multilingual · bi-encoder vs cross-encoder · semantic search cho blog.
- **SEO cho blog tĩnh:** seo cho blog tĩnh github pages · tối ưu lighthouse 100 · thêm sitemap cho zola · structured data schema cho blog · custom domain github pages.
- **Build in public ($0):** tự xây blog cá nhân miễn phí · blog không cần wordpress · host blog $0 · mini cms vanilla js · self-healing CI.

**Content gap (đánh ngay):** `semantic search bằng Python` (né khối SEO) · `tự động deploy Zola lên GitHub Pages` · `embeddings tiếng Việt` · `SSG self-healing / CI auto-fix` (độc nhất, bạn đã làm thật).

**5 bài nên viết:**
1. *"Hướng dẫn tạo blog với Zola từ A–Z (2026): cài đặt, theme, deploy GitHub Pages miễn phí"* — cơ hội top 1 cao nhất.
2. *"Tự động deploy blog Zola lên GitHub Pages bằng GitHub Actions (giải thích deploy.yml từng dòng)"*.
3. *"Semantic search tiếng Việt bằng Python với Sentence Transformers"* — đánh thẳng content gap.
4. *"Embeddings cho văn bản tiếng Việt: chọn model multilingual nào + code minh hoạ"*.
5. *"Zola vs Hugo: nên chọn cái nào cho blog cá nhân?"* — định dạng so sánh → dễ featured snippet.

**Map bài hiện có:**
| Bài | KW mục tiêu | Sửa |
|---|---|---|
| `cong-nghe-blog-duy-nguyen` | tự xây blog cá nhân miễn phí · static site generator | ⚠️ **Đang sai category "Ẩm thực" → đổi "Công nghệ"**. Title: *"Dưới nắp ca-pô: tự xây blog cá nhân $0/tháng với Zola + GitHub Pages"* |
| `qa-gatekeeper-tu-fix-loi-blog` | ci/cd cho blog cá nhân · github actions tự động | Title thêm "CI/CD" + "GitHub Actions" |
| `sentence-transformers-sbert-deep-dive` | sentence transformers là gì · semantic search | ⚠️ **Đang sai category "Ẩm thực" → đổi "Công nghệ"**. Title thêm vế "là gì"; thêm FAQ |

---

### 2.2 🥈 DU LỊCH HÀN QUỐC

**Tín hiệu xanh:** SERP "du lịch busan tự túc 3 ngày 2 đêm" **đã lọt blog cá nhân** (lamgibaygio.wordpress, discoverupandgo) → query lịch trình chi tiết + nhật ký cá nhân vẫn để blog nhỏ lên. Càng cụ thể theo tháng/thành phố, SERP càng loãng.

**Primary keywords (trần nên nhắm — KHÔNG đú head term):**

| Từ khoá | Intent | Cạnh tranh | Ghi chú |
|---|---|---|---|
| du lịch busan tự túc (3N2Đ) | Thông tin | **TB** ⭐ | Cửa sáng nhất — blog cá nhân đã top |
| du lịch hàn quốc tháng 6 (theo tháng cụ thể) | Thông tin (mùa) | **TB** ⭐ | Query theo-tháng loãng, dễ chen |
| đi hàn tháng mấy / mùa nào đẹp nhất | Thông tin | TB-cao | Nội dung top sơ sài → thắng nếu so sánh sâu + ngân sách |
| lịch trình seoul 5 ngày 4 đêm tự túc | Thông tin | Cao | Cửa hẹp: bản đồ hoá + giá thật |
| mùa lá đỏ hàn quốc tháng mấy/ở đâu | Thông tin (mùa) | TB-cao | Đánh biến thể địa điểm cụ thể |

> **Né hẳn:** *du lịch hàn quốc*, *kinh nghiệm du lịch hàn quốc tự túc*, *chi phí du lịch hàn quốc* (head term — chỉ dùng làm chủ đề pillar, nhắm gián tiếp).

**Long-tail clusters:**
- **Theo mùa/tháng (xương sống):** du lịch hàn tháng 6 thời tiết có mưa không · đi hàn mùa nào hợp ngân sách / rẻ nhất · mùa mưa jangma kéo dài đến tháng mấy · hàn quốc mùa đông trượt tuyết cho người mới · so sánh xuân vs thu.
- **Theo thành phố / lịch trình (cửa sáng nhất):** lịch trình busan 3N2Đ tự túc · seoul 5N4Đ tiết kiệm · jeju tự túc đi lại bằng gì · nami + everland 1 ngày có kịp không · one-day trip từ seoul.
- **Chi phí/ngân sách:** đi hàn 5N4Đ hết bao nhiêu tiền tự túc · chi phí ăn uống 1 ngày ở seoul · du lịch hàn tiết kiệm dưới 15 triệu · thẻ T-money mua ở đâu nạp bao nhiêu · mẹo tiết kiệm khi đi hàn.
- **Visa & thủ tục (cẩn trọng):** xin visa hàn tự túc cần giấy tờ gì · mẫu chứng minh tài chính · visa bị từ chối phải làm sao · visa cho freelancer/lao động tự do · K-ETA là gì có cần không. ⚠️ Chỉ làm 1–2 bài *kinh nghiệm thật + checklist*, không đú "dịch vụ visa".
- **Ăn uống/mua sắm (bổ trợ):** mua gì ở myeongdong giá rẻ · mỹ phẩm olive young nên mua gì · món đường phố hàn · naengmyeon/bingsu (món hè) · hoàn thuế tax refund cho khách.

**Content gap:** thiếu trải nghiệm ngôi thứ nhất thật · thiếu **bóc tách chi phí thật (có ảnh hoá đơn)** · thiếu bài "ra quyết định" (A vs B) · thiếu "đi tháng X tránh mùa mưa jangma".

**5 bài nên viết:**
1. *"Đi Hàn hết bao nhiêu tiền? Bóc trần hoá đơn chuyến Seoul–Busan 6 ngày (kèm ảnh receipt)"*.
2. *"Lịch trình Busan tự túc 3 ngày 2 đêm: bản đồ Google Maps + giá vé từng điểm (2026)"* — cửa sáng nhất.
3. *"Đi Hàn mùa nào RẺ nhất? Xếp hạng 12 tháng theo giá vé + đám đông + thời tiết"*.
4. *"Jeju tự túc: thuê xe tự lái hay đi bus? So sánh chi phí, tiện, rủi ro"*.
5. *"Xin visa Hàn cho freelancer: mình chứng minh tài chính thế nào để được duyệt"* + checklist tải về.

**Map bài hiện có:**
| Bài | KW mục tiêu | Sửa |
|---|---|---|
| `mua-nao-di-han-la-dep-nhat` | đi hàn mùa nào đẹp nhất · mùa nào hợp ngân sách | Title: thêm "(2026)" + "hợp ngân sách". **Là pillar cụm "theo mùa"** → thêm bảng so sánh + FAQ |
| `summer-korea-4-diem-dung-mua-he` | du lịch hàn quốc mùa hè đi đâu | ⚠️ **Title mở đầu tiếng Anh "Summer Korea" → đổi**: *"Du lịch Hàn Quốc mùa hè đi đâu? 4 điểm Seoul – Busan – Seoraksan – Jeju"* |
| `thang-6-di-han-an-gi-lam-gi` | du lịch hàn quốc tháng 6 | **Model chuẩn, nhân rộng ra tháng 7/9/10/12.** Title thêm "du lịch hàn quốc" + "thời tiết/mùa mưa" |
| `tet-doan-ngo-han-viet-trung` | tết đoan ngọ ở hàn quốc · 3 nước | Bài **văn hoá** (không phải du lịch). Title thêm "(mùng 5/5 âm lịch)" |

---

### 2.3 🥉 ẨM THỰC (Sài Gòn + Hàn)

**Bối cảnh:** SERP bị aggregator (vinwonders, mia.vn, foody, zalopay…) + hãng bay chiếm head term. **Cửa thắng = micro-long-tail có ngữ cảnh** (giờ giấc/thời tiết/tâm trạng/dịp/món cụ thể) + góc thổ địa.

**Primary keywords:**

| Từ khoá | Intent | Cạnh tranh | Ghi chú |
|---|---|---|---|
| tối nay ăn gì sài gòn | Decision | Cao | Đánh qua biến thể dài |
| quán ăn đêm / ăn khuya sài gòn | Local | TB-cao | "Dân bản địa mách" thắng được |
| trời mưa sài gòn ăn gì | Seasonal | **TB-thấp** ⭐ | Cơ hội tốt, hợp mùa mưa T6–T11 |
| quán ốc quận 4 ngon rẻ | Local | TB | SERP có domain nhỏ → chen được |
| ăn vặt sài gòn quận 3 | Local | TB | Foody còn top → SERP cũ, dễ chen |
| đi hàn quốc ăn gì / ăn gì ở seoul tự túc | Thông tin | Cao | Thắng ở góc "tự túc + quy đổi won→VND" |
| cách làm tteokbokki tại nhà | How-to | TB | Recipe + ảnh tự chụp |

**Long-tail clusters:**
- **Theo bữa/lúc (decision, traffic đều mỗi tối):** tối nay ăn gì gần đây · ăn gì khi lười nấu · ăn gì cuối tuần SG · ăn gì sau giờ làm quận 1 · trưa nay ăn gì văn phòng.
- **Theo quận/khu vực:** phố ốc Vĩnh Khánh quận 4 · ăn vặt/chè quận 3 · ăn đêm quận 5 chợ lớn · hủ tiếu người Hoa Q5 · cơm tấm Phú Nhuận.
- **Theo dịp/tâm trạng/thời tiết (CỬA THẮNG CHÍNH):** trời mưa ăn gì cho ấm · quán hẹn hò cho cặp đôi · quán nhóm đông người · ăn gì giải ngấy · ăn gì khi buồn.
- **Món/đặc sản cụ thể (dễ featured snippet):** hủ tiếu Nam Vang ngon · phá lấu Q1 · bún mắm ở đâu · súp cua · bột chiên trứng · bò né.
- **Ẩm thực Hàn:** ăn gì ở seoul tự túc · món vặt đường phố hàn · naengmyeon/bingsu · chợ Gwangjang/Jagalchi · cách làm tteokbokki/kimbap.

**Content gap:** aggregator viết generic, không có "cái tôi", thiếu **giá chính xác 2026 + giờ mở + mẹo đậu xe + combo cho N người**, thiếu góc ngữ cảnh (mưa/đêm/tâm trạng), thiếu **single-dish deep-dive**.

**5 bài nên viết:**
1. *"Trời mưa Sài Gòn ăn gì cho ấm bụng? 8 món thổ địa + quán mở giờ mưa"*.
2. *"Phố ốc Vĩnh Khánh quận 4: ăn quán nào, gọi món gì, hết bao nhiêu (2026)"*.
3. *"Ăn khuya Sài Gòn: 10 quán dân cú đêm ruột, mở sau 11h đêm"*.
4. *"Cách làm tteokbokki chuẩn vị Hàn tại nhà trong 20 phút (ảnh từng bước)"*.
5. *"Ăn vặt Sài Gòn dưới 50k: tổng hợp theo từng quận"*.

**Map bài hiện có:**
| Bài | KW mục tiêu | Sửa |
|---|---|---|
| `toi-nay-sai-gon-an-gi` | tối nay ăn gì sài gòn (+ ăn khuya) | Title: *"…12 quán thổ địa ăn tối & ăn khuya (2026)"*. Thêm FAQ; tách 1–2 món hot thành bài deep-dive |
| `thang-6-di-han-an-gi-lam-gi` (phần ẩm thực) | đi hàn ăn gì mùa hè | Cân nhắc tách riêng bài ẩm thực Hàn; mỗi món thêm 1 câu định nghĩa (bắt snippet) |

---

### 2.4 ⚠️ NGÂN HÀNG & TÀI CHÍNH — làm nhẹ, có chọn lọc

**Đánh giá thẳng:** vertical YMYL khắc nghiệt nhất. SERP bị web ngân hàng chính chủ + cafef/vnexpress/dantri + trang luật khoá. Blog cá nhân **không có cửa** ở từ khoá giao dịch (lãi suất/vay/đầu tư/mở thẻ). **Cửa duy nhất: tin ngách + giải thích "khách cần làm gì" + công nghệ hậu trường + trải nghiệm app thật.**

**Primary (chỉ #1, #6, #7 là nơi blog thực sự có cửa):**

| Từ khoá | Intent | Cạnh tranh | Ghi chú |
|---|---|---|---|
| MSB Digital Bank thay mBank | Tin tức+how-to | **TB** ⭐ | Sự kiện mới, còn "tươi" → vào sớm có cửa |
| xác thực sinh trắc học (khi đổi app) | How-to | TB (đuôi dài) | Nhu cầu lớn, lặp theo quy định |
| Backbase / eKYC là gì | Thông tin kỹ thuật | **Thấp-TB** ⭐ | Ít YMYL, hợp chất blog công nghệ → cửa bền nhất |
| private banking là gì | Thông tin | Cao | Chỉ làm dạng kể chuyện + giải thích |
| app ngân hàng số nào tốt (Cake/TNEX/Timo) | So sánh | Cao | Chỉ thắng bằng **trải nghiệm thật** (E-E-A-T) |

**Cụm nên làm:** (A) tin đổi tên app/quy định mới · (E) công nghệ hậu trường (Backbase/eKYC/ISO 30107 "dịch sang tiếng người") · (C) how-to thao tác đuôi dài · (D) so sánh trải nghiệm thật.
**Cụm BỎ:** lãi suất · vay online · nên đầu tư gì · gửi tiết kiệm lãi cao · mở thẻ tín dụng nào.

**5 bài khả thi (góc tin/how-to):**
1. *"TNEX được vinh danh 'Ngân hàng số tốt nhất 2026' — danh hiệu này thực sự nói lên điều gì?"*
2. *"Nhiều app ngân hàng tự thoát trên điện thoại cũ: máy bạn có trong danh sách?"* (Thông tư 77/50).
3. *"Tài khoản phải trùng tên CCCD: ai bị ảnh hưởng, cần làm gì?"*
4. *"Backbase — công nghệ đứng sau loạt app ngân hàng số Việt (giải thích cho người không rành kỹ thuật)"*.
5. *"Cake, TNEX hay Timo: tôi dùng thử cả ba — khác biệt thật về phí, thẻ, trải nghiệm (2026)"*.

**Map bài hiện có:**
| Bài | KW mục tiêu | Sửa |
|---|---|---|
| `bidv-flagship-private-banking-tphcm` | private banking là gì · BIDV private banking | ⚠️ Đang category "Posting" → nên "Ngân hàng". Title gộp "là gì": *"Private Banking là gì? Nhìn từ chi nhánh BIDV vừa mở cho giới siêu giàu ở Sài Gòn"* |
| `msb-digital-bank-ra-mat-thay-mbank` | MSB Digital Bank thay mBank | **Đã tốt.** Thêm mốc "từ 1/6/2026" vào title; thêm FAQ schema |

**Khuyến nghị:** coi ngân hàng là **nhánh phụ của "tin tức + giải thích công nghệ"**, ~1–2 bài/tháng, luôn có disclaimer "không phải tư vấn tài chính". KHÔNG biến thành blog tài chính.

---

## 3. Cấu trúc nội dung — Topic Cluster

Mỗi mảng = **1 trang pillar** (bao quát, nhắm head term gián tiếp) + **nhiều bài con long-tail** trỏ về pillar và trỏ lẫn nhau.

```
PILLAR: "Cẩm nang du lịch Hàn Quốc tự túc cho người Việt"
 ├── Lịch trình Busan 3N2Đ          (cluster: thành phố)
 ├── Lịch trình Seoul 5N4Đ          (cluster: thành phố)
 ├── Đi Hàn mùa nào rẻ nhất         (cluster: mùa/ngân sách)
 ├── Bóc hoá đơn chuyến đi          (cluster: chi phí)
 └── Xin visa Hàn tự túc            (cluster: thủ tục)

PILLAR: "Tự xây blog cá nhân $0 với Zola"
 ├── Tạo blog Zola A–Z
 ├── Tự động deploy bằng GitHub Actions
 ├── SEO cho blog tĩnh
 └── Self-healing CI (QA Gatekeeper)
```

**Internal linking:** mỗi bài con link lên pillar (anchor = từ khoá pillar) + link ngang 2–3 bài cùng cụm. Pillar link xuống tất cả bài con. (Trang chủ + `/posting/` đã liệt kê mọi bài — đã fix ở task trước.)

---

## 4. Checklist SEO on-page (áp cho MỌI bài)

- [ ] **Title** ≤ 60 ký tự, **từ khoá chính đứng đầu**, có yếu tố hút click (số, năm, "2026", lợi ích). KHÔNG mở đầu bằng tiếng Anh.
- [ ] **Meta description** ≤ 155 ký tự, chứa từ khoá chính + 1 từ phụ + lời hứa giá trị.
- [ ] **1 H1 duy nhất** = title; **H2/H3 dạng câu hỏi** (bắt People Also Ask).
- [ ] **Đoạn mở 40–55 từ trả lời thẳng câu hỏi chính** (chiếm featured snippet).
- [ ] **Block FAQ cuối bài** (3–5 câu PAA) + **`FAQPage` schema**.
- [ ] **Bảng so sánh / list đánh số** cho nội dung so sánh & how-to (table/numbered snippet).
- [ ] **Ảnh thật tự chụp** (KHÔNG picsum), tên file slug-hoá + **alt tiếng Việt có từ khoá**.
- [ ] **Internal link**: ≥1 lên pillar + 2–3 ngang cụm.
- [ ] **Ngày hiển thị** `dd/mm/yyyy`, GMT+7 (theo CLAUDE.md); cập nhật ngày với bài mùa vụ.
- [ ] **Slug** ngắn, tiếng Việt không dấu, chứa từ khoá.

---

## 5. SEO kỹ thuật — trạng thái

**Đã có (task trước):** sitemap.xml + RSS/Atom · canonical · OpenGraph + Twitter Card · JSON-LD Article + publisher logo · robots rich-preview · Google Search Console verified + sitemap submitted · IndexNow tự động (Bing/Yandex/Seznam/Naver/DuckDuckGo) · trang chủ + `/posting/` liệt kê đủ bài · nút "Trang chủ" · 404.html.

**Nên bổ sung:**
- [ ] **`FAQPage` schema** cho bài có FAQ (rich result + PAA).
- [ ] **`BreadcrumbList` schema** + breadcrumb hiển thị.
- [ ] **Thay toàn bộ ảnh `picsum.photos`** bằng ảnh thật (15 bài) — ưu tiên cao (image pack + E-E-A-T).
- [ ] **Pillar pages** cho 2 mảng top (Du lịch Hàn, Zola).
- [ ] Cân nhắc **custom domain** (tăng uy tín hơn `github.io/zola` subpath) — dài hạn.
- [ ] **`HowTo` schema** cho bài hướng dẫn (recipe, deploy.yml…).

---

## 6. Quick wins — làm ngay (đã verify)

| # | Việc | Loại | Mức độ |
|---|---|---|---|
| 1 | `cong-nghe-blog-duy-nguyen` & `sentence-transformers-sbert-deep-dive`: category **"Ẩm thực" → "Công nghệ"** | 🐞 Bug | **Cao** |
| 2 | `summer-korea-…`: bỏ "Summer Korea" tiếng Anh ở đầu title → cụm tiếng Việt | Title | Cao |
| 3 | Thống nhất taxonomy: gộp `["Posting"]` chung chung + đổi `"Banking"` → `"Ngân hàng"`; gán category đúng cho các bài thời sự | Taxonomy | TB |
| 4 | Thêm năm "2026" + từ khoá phụ vào title các bài evergreen | Title/meta | TB |
| 5 | Thay ảnh `picsum.photos` (15 bài) bằng ảnh thật | Ảnh/E-E-A-T | Cao (cần asset) |
| 6 | Thêm block FAQ + `FAQPage` schema vào các bài chủ lực | On-page | Cao |

---

## 7. Lộ trình 90 ngày

**Tháng 1 — nền móng + quick wins**
- Sửa toàn bộ quick win #1–4 (#6 cho 3 bài top).
- Viết pillar **"Tự xây blog Zola $0"** + bài **"Tạo blog Zola A–Z"** (cơ hội top 1).
- Viết **"Lịch trình Busan tự túc 3N2Đ"** (cửa du lịch sáng nhất).
- Bắt đầu thay ảnh thật cho 3 bài chủ lực.

**Tháng 2 — mở rộng cụm mạnh**
- Tech: *deploy.yml GitHub Actions* + *semantic search Python*.
- Du lịch: *đi Hàn mùa nào rẻ nhất* + *bóc hoá đơn chi phí*.
- Ẩm thực: *trời mưa Sài Gòn ăn gì* (đúng mùa mưa) + *ăn khuya Sài Gòn*.
- Pillar **"Cẩm nang du lịch Hàn tự túc"** + internal link toàn cụm.

**Tháng 3 — phủ rộng + đo lường**
- Tech: *Zola vs Hugo* + *embeddings tiếng Việt*.
- Du lịch: nhân rộng *du lịch Hàn tháng 9/10* + *Jeju tự túc*.
- Ẩm thực: *phố ốc Vĩnh Khánh Q4* + *tteokbokki tại nhà*.
- Ngân hàng (nhẹ): *Backbase là gì* + 1 bài tin sự kiện.
- Rà GSC: bài nào lên trang 2 → bồi nội dung/internal link đẩy lên trang 1.

---

## 8. Đo lường

- **Google Search Console** (đã có): theo dõi *impressions / clicks / vị trí trung bình* theo query; lọc bài ở vị trí 8–20 để tối ưu đẩy lên top.
- **Kiểm tra index:** `site:banhang-chogao.github.io/zola` trên Google + Bing.
- **Mục tiêu định hướng (blog mới, ~6 tháng):** mỗi mảng top có ≥1 bài vào top 10 cho 1 cụm long-tail; tổng số query có impression tăng đều; **traffic KHÔNG đến từ tên blog** mà từ từ khoá nội dung.
- **Chỉ báo thành công thật:** khi cụm "tạo blog với zola", "lịch trình busan tự túc", "trời mưa sài gòn ăn gì" mang khách về đều — chứng tỏ chiến lược topical authority hiệu quả, không cần brand.

---

### Phụ lục — nguồn SERP tham khảo (quan sát 6/2026)
Klook, Traveloka, BestPrice, Mia.vn, Vietnambooking, gody.vn, lamgibaygio.wordpress (blog cá nhân lên top Busan) · Foody, vinwonders, zalopay, bachhoaxanh, eva, vnpay, kkday, vincom (ẩm thực) · getzola.org, Viblo, 200Lab, TopDev, hoccodeai, aivietnam, vietnix (công nghệ) · techcombank/vpbank/cake/timo/msb, cafef, vnexpress, dantri, thuvienphapluat (ngân hàng).
