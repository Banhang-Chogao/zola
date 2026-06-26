+++
title = "Google Publisher Policies — nội dung bị cấm hiển thị quảng cáo"
description = "Google Publisher Policies: nội dung bị cấm đặt quảng cáo AdSense. Series AdSense Bài 4/15 — bám tài liệu Google chính thức."
date = 2026-06-18
aliases = ["/google-publisher-policies-noi-dung-bi-cam/"]
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["adsense", "adsense foundation series", "google adsense", "monetization", "nội dung bị cấm", "publisher policies"]
[extra]
thumbnail = "https://banhang-chogao.github.io/zola/img/covers/tao-blog-voi-zola.svg"
seo_keyword = "google publisher policies nội dung bị cấm"
featured = false
series = "adsense-foundation"
series_part = 4
series_total = 15
references_copyright = "Nội dung dựa trên tài liệu chính thức Google AdSense Help (Google Publisher Policies, AdSense Program policies). Google có thể cập nhật danh sách nội dung bị cấm bất cứ lúc nào — publisher có trách nhiệm theo dõi và tuân thủ phiên bản mới nhất theo Terms and Conditions."

[[extra.faq]]
q = "Google Publisher Policies là gì?"
a = "Là bộ quy tắc Google áp dụng cho mọi publisher đặt quảng cáo Google (AdSense, Ad Manager…). Policies quy định nội dung và hành vi bị cấm hoàn toàn — vi phạm có thể dẫn đến ads disabled, từ chối duyệt, hoặc đóng tài khoản. Khác với Restrictions (giới hạn quảng cáo một phần), Policies là lớp 'không được phép'."

[[extra.faq]]
q = "Scraped content có vi phạm Publisher Policies không?"
a = "Có. Google cấm đặt ads trên site scraped hoặc copyrighted content không có quyền sử dụng. Site chỉ tổng hợp RSS, paraphrase tool, hoặc copy nguyên bài site khác — dù có traffic — vẫn vi phạm và có thể bị disable ads hoặc đóng account."

[[extra.faq]]
q = "Nội dung adult hoặc bạo lực có chạy AdSense được không?"
a = "Không. Sexually explicit content, shocking content (bạo lực graphic, gore), dangerous or derogatory content đều nằm trong Policies bị cấm. Một số chủ đề nhạy cảm khác thuộc Restrictions (giới hạn quảng cáo) — series sẽ phân tích ở Bài 5; bài này tập trung nội dung bị cấm hoàn toàn."
+++

> 📚 **Google AdSense Foundation Series (Bài 4/15)** — Sau [Bài 1: Google AdSense là gì & khung Program policies](/zola/posting/google-adsense-la-gi-chinh-sach-chuong-trinh/), [Bài 2: Điều kiện đủ tư cách AdSense](/zola/posting/dieu-kien-du-tu-cach-adsense/) và [Bài 3: Website sẵn sàng cho AdSense](/zola/posting/website-san-sang-cho-adsense/), bài này đi vào lớp chính sách publisher hay bỏ qua cho đến khi bị cảnh báo: **Google Publisher Policies — nội dung bị cấm hiển thị quảng cáo**. Tôi bám [Google Publisher Policies](https://support.google.com/adsense/answer/9335564?hl=en) — không phải tóm tắt forum, mà là khung Google dùng để disable ads hoặc đóng tài khoản.

[Bài 3](/zola/posting/website-san-sang-cho-adsense/) đã nhắc scraped content và policies khi nói site readiness. Bài 4 **mở rộng toàn bộ** danh mục nội dung bị cấm — giúp bạn audit site **trước** apply và **sau** khi đã monetize, tránh mất doanh thu đột ngột vì một bài vi phạm.

<!-- more -->

## Google Publisher Policies — nội dung bị cấm vs Program policies {#policies-vs-program}

Trong [AdSense Program policies](https://support.google.com/adsense/answer/48182?hl=en), Google tách hai lớp:

| Lớp | Ý nghĩa | Ví dụ |
|---|---|---|
| **Google Publisher Policies** | Nội dung/hành vi **bị cấm** đặt quảng cáo Google | Illegal content, scraped, CSAM, malware |
| **Google Publisher Restrictions** | Nội dung **được phép** nhưng quảng cáo **bị giới hạn** | Một số chủ đề tài chính, thuốc, tin tức nhạy cảm |

**Bài 4** (bài này) = Policies = **cấm tuyệt đối**. **Bài 5** series sẽ cover Restrictions — giới hạn fill rate, không phải disable toàn site.

[Bài 1](/zola/posting/google-adsense-la-gi-chinh-sach-chuong-trinh/) đã vẽ bức tranh tổng thể. [Bài 2](/zola/posting/dieu-kien-du-tu-cach-adsense/) yêu cầu tuân thủ policies **trước khi đăng ký**. [Bài 3](/zola/posting/website-san-sang-cho-adsense/) gắn scraped content với site readiness. Bài 4 là **bản đồ chi tiết** để không vi phạm vô tình.

Google ghi rõ trong [9335564](https://support.google.com/adsense/answer/9335564?hl=en): publishers **không được** đặt Google ads trên content vi phạm Policies. Vi phạm nghiêm trọng hoặc lặp lại → **account disabled** — khó khôi phục.

## Hậu quả vi phạm Publisher Policies {#hau-qua-vi-pham}

Theo [AdSense Program policies](https://support.google.com/adsense/answer/48182?hl=en) và [Policy center](https://support.google.com/adsense/answer/7003627?hl=en):

1. **Ads disabled** trên trang hoặc toàn site — doanh thu dừng ngay.
2. **Account không được duyệt** — apply lần đầu fail vì reviewer thấy nội dung cấm.
3. **Account disabled** — vi phạm nặng, invalid traffic kèm policy, hoặc tái phạm.
4. **Thanh toán giữ lại** — Google có thể withhold payment khi có vi phạm nghiêm trọng (xem Terms).

Khác với SEO penalty (có thể recover từ từ), AdSense policy strike thường **rõ ràng và nhanh** — một trang adult nhúng nhầm, một tool download crack, hoặc forum UGC không moderate đủ đều có thể kích hoạt cảnh báo.

Publisher nên coi Policies như **điều kiện sống còn** của monetization — không phải "guideline mềm".

## Nội dung bất hợp pháp và lạm dụng sở hữu trí tuệ {#illegal-va-ip}

### Illegal content

Google cấm content **promotes, facilitates, or enables** hoạt động bất hợp pháp — theo luật nơi publisher hoặc nơi quảng cáo hiển thị. Ví dụ khái niệm:

- Hướng dẫn hack, crack phần mềm trả phí.
- Bán thuốc/vật chất bất hợp pháp.
- Dịch vụ vi phạm luật địa phương (cờ bạc không phép, v.v.).

Blog giáo dục công nghệ hợp pháp (SEO, Zola, AdSense) thường không chạm nhóm này — nhưng **comment/UGC** hoặc guest post có thể đưa link bất hợp pháp vào site. Bạn **chịu trách nhiệm** toàn bộ nội dung trên domain.

### Intellectual property abuse

Cấm content vi phạm bản quyền, nhãn hiệu, hoặc quyền sở hữu trí tuệ khác — không có quyền sử dụng hợp pháp. Liên quan trực tiếp [Bài 3](/zola/posting/website-san-sang-cho-adsense/):

- Copy nguyên bài báo, ebook, ảnh stock không license.
- Reupload video YouTube người khác làm "nội dung chính" trang.
- Theme/plugin nulled, keygen, ROM game thương mại.

Google tham chiếu [DMCA](https://www.google.com/adsense/support/bin/request.py?contact_type=dmca) và báo cáo vi phạm IP. Publisher nhận cảnh báo Policy center trước khi disable trong nhiều trường hợp — nhưng **không nên** chờ DMCA mới sửa.

## Nội dung nguy hiểm, kỳ thị và hate speech {#nguy-hiem-va-hate}

### Dangerous or derogatory content

Theo [Publisher Policies](https://support.google.com/adsense/answer/9335564?hl=en), cấm content **harasses, intimidates, or bullies** cá nhân/nhóm; **incites hatred**; hoặc **discriminates** dựa trên đặc điểm được bảo vệ (tuổi, chủng tộc, tôn giáo, giới tính, khuyết tật, orientation, v.v.).

Blog tin tức hoặc opinion piece **có thể** thảo luận chủ đề nhạy cảm nếu **journalistic, educational** và không kích động thù hận. Ranh giới mỏng — Google đánh giá **ngữ cảnh và mục đích**. Series AdSense của tôi giữ giọng giáo dục, trung lập — đúng hướng.

### Hate speech

Nội dung cổ vũ bạo lực hoặc phân biệt đối xử nghiêm trọng — **cấm tuyệt đối**. Không có "fill rate thấp" như Restrictions — ads không được phép.

Publisher forum/community: một thread hate có thể kéo cả site vào policy violation — xem [user-generated content](https://support.google.com/adsense/answer/1355699?hl=en) ở Bài 3.

## Nội dung gây sốc, sự kiện nhạy cảm, quấy rối {#soc-va-quay-roi}

### Shocking content

Cấm content **gratuitous gore**, **acts of violence**, hoặc **disturbing** không có ngữ cảnh báo chí/education hợp lý. Ảnh tai nạn graphic, nội dung tra tấn — không monetize bằng AdSense.

### Sensitive events

Google có policy về **sensitive events** — thảm họa, xung đột, bệnh dịch đang diễn ra — hạn chế exploitation (giả mạo từ thiện, price gouging, misinformation). Một phần overlap Restrictions; vi phạm nặng (lừa đảo trong khủng hoảng) thuộc Policies.

### Bullying and harassment

Cá nhân hóa tấn công, doxxing, khuyến khích quấy rối — cấm. Blog cá nhân ít gặp nếu không đăng drama; **comment section** là rủi ro thực tế.

## Nội dung tình dục và bảo vệ trẻ em {#adult-va-csam}

### Sexually explicit content

Cấm nội dung **sexually explicit** — pornography, acts tình dục explicit, nội dung "intended to arouse". Một số chủ đề adult **borderline** thuộc Restrictions (Bài 5) — nhưng explicit = Policies.

Blog lifestyle, sức khỏe giới tính **giáo dục** có thể pass nếu không explicit — vẫn nên đọc kỹ [9335564](https://support.google.com/adsense/answer/9335564?hl=en) và test Policy center sau apply.

### Child sexual abuse material (CSAM)

**Cấm tuyệt đối** — Google báo cáo pháp luật. Không có gray area. UGC và gallery ảnh user upload là điểm cần moderate chặt.

## Scraped content và nội dung không gốc {#scraped-content}

Đây là nhóm publisher Việt Nam hay vi phạm nhất — [Bài 3](/zola/posting/website-san-sang-cho-adsense/) đã cảnh báo.

Google định nghĩa **scraped content** gồm:

- Site **không thêm giá trị gốc** — chỉ copy từ nguồn khác.
- **Auto-generated** content không human review.
- **Rewriting** hoặc paraphrasing tool tạo hàng loạt bài mỏng.
- **Aggregated** content từ RSS không có commentary đáng kể.

| Loại site | Vi phạm? |
|---|---|
| Dịch máy 50 bài/ngày từ blog nước ngoài | **Có** — thường |
| Series gốc tiếng Việt, bám tài liệu Google, có ví dụ Zola | **Không** — nếu không copy nguyên văn |
| Tổng hợp tin + 2 câu intro | **Có** — thường |
| Embed video + phân tích 5 đoạn gốc | **Thường không** — nếu đủ giá trị gốc |

Scraped content vi phạm **cả Publisher Policies lẫn** [Spam policies for Google web search](https://developers.google.com/search/docs/essentials/spam-policies) — mất ads và có thể mất traffic organic. Kết hợp [SEO Foundation Series](/zola/posting/seo-la-gi-huong-dan-co-ban-google-search/) để xây helpful content thay vì aggregate.

## Phần mềm độc hại và nội dung lừa đảo {#malware-va-lua-dao}

### Malicious or unwanted software

Cấm site **phân phối malware**, **unwanted software** (download không rõ ràng, bundle lén), hoặc **social engineering** đánh lừa cài phần mềm. Popup "download driver" giả, redirect chain — vi phạm.

Blog Zola tĩnh ít rủi ro nếu không host file lạ. Cẩn thận **quảng cáo bên thứ ba** (ngoài AdSense) hoặc script embed không tin cậy — có thể khiến site bị flag.

### Misrepresentative content

Cấm **impersonation**, **misleading claims**, **fake engagement** (traffic/click giả). Liên quan [invalid traffic](https://support.google.com/adsense/answer/16737?hl=en) — series Bài 9 sẽ đi sâu; ở đây nhấn: content và hành vi **lừa user hoặc advertiser** = Policies.

Ví dụ: trang giả mạo thương hiệu, "review" sản phẩm không trải nghiệm thật để affiliate lừa đảo — vi phạm misrepresentation.

## Audit site blog Zola theo Policies {#audit-zola}

Áp [Google Publisher Policies](https://support.google.com/adsense/answer/9335564?hl=en) lên blog Zola tôi đang chạy:

**An toàn (hướng series hiện tại)**

- Nội dung giáo dục AdSense, SEO, khoa học uranium — không adult, không hate.
- Series viết gốc, có FAQ, nguồn Google/IAEA/Wikipedia — không scrape.
- HTML tĩnh, không push malware.

**Cần kiểm tra định kỳ**

- **UGC** nếu bật comment — moderate spam/link bất hợp pháp.
- **Ảnh cover** — license SVG tự tạo hoặc nguồn hợp pháp.
- **Bài dịch/tổng hợp** trong tương lai — đảm bảo giá trị gốc, không paraphrase hàng loạt.
- **Trang affiliate** (nếu có) — không misleading claims.

**Liên kết nội bộ cluster**

- Bài 1 → 2 → 3 → **4** giúp reviewer thấy site **chủ đề nhất quán**, không phải MFA (made-for-AdSense) spam — overlap với site readiness Bài 3.

## Sai lầm publisher thường gặp {#sai-lam}

### 1. "Chỉ một bài vi phạm — Google bỏ qua"

Một URL vi phạm có thể **disable ads trên URL đó** hoặc cả site. CSAM, malware — disable account ngay.

### 2. "Dùng AI viết 100 bài = unique"

Auto-generated không review = scraped/spam territory. AI hỗ trợ **có human edit và giá trị gốc** khác — nhưng 100 bài mỏng/ngày vẫn rủi ro.

### 3. "Comment không phải nội dung của tôi"

Google coi **bạn chịu trách nhiệm** UGC trên site. Không moderate = rủi ro policy.

### 4. "Tin tức ảnh graphic = traffic tốt"

Shocking content cấm monetize AdSense — dù có traffic Search. Dùng Restrictions/news guidelines khác hoặc không ads trang đó.

### 5. "Đã duyệt rồi — đăng gì cũng được"

Policies áp dụng **liên tục**. Thêm chuyên mục download crack sau duyệt → account disabled.

### 6. "Policies chỉ áp dụng trang có ad code"

Google policy áp dụng **site/partner properties** bạn khai báo — nội dung vi phạm trên cùng domain có thể ảnh hưởng toàn tài khoản dù chưa gắn ad từng trang.

## Checklist đối chiếu Publisher Policies {#checklist}

Trước apply và **mỗi quý** sau khi monetize, tôi chạy checklist bám [9335564](https://support.google.com/adsense/answer/9335564?hl=en):

- [ ] **Illegal**: Không promote hack, crack, hàng cấm, dịch vụ phi pháp.
- [ ] **IP**: Ảnh, text, video có license hoặc tự tạo; không copy nguyên bài.
- [ ] **Dangerous/hate**: Không kích động thù hận, phân biệt, quấy rối cá nhân.
- [ ] **Shocking**: Không gore/violence gratuitous.
- [ ] **Adult/CSAM**: Không explicit; moderate UGC chặt.
- [ ] **Scraped**: Mỗi bài có giá trị gốc — pass [Bài 3](/zola/posting/website-san-sang-cho-adsense/) readiness.
- [ ] **Malware/misrepresentation**: Không redirect lừa, không fake brand.
- [ ] **UGC**: Có quy trình moderate nếu có comment/forum.
- [ ] **Policy center**: Kiểm tra cảnh báo sau mỗi lần Google email.

## Bạn nên làm gì sau bài 4? {#sau-bai-4}

Sau khi audit **nội dung bị cấm**, bước tiếp theo trong series là [**Bài 5: Google Publisher Restrictions**](/zola/posting/google-publisher-restrictions-noi-dung-han-che/) — chủ đề *được phép* nhưng quảng cáo bị giới hạn (fill rate thấp hơn, không phải disable). Trước mắt:

1. **Quét toàn site** — đặc biệt bài cũ, trang tag, archive trước khi gắn ad code.
2. **Đọc** [Policy center](https://support.google.com/adsense/answer/7003627?hl=en) sau apply — mọi cảnh báo cần xử lý trong deadline Google ghi.
3. **Giữ site readiness** từ [Bài 3](/zola/posting/website-san-sang-cho-adsense/) — policies và readiness song song, không thay thế nhau.

Nếu chưa đủ tư cách, quay [Bài 2](/zola/posting/dieu-kien-du-tu-cach-adsense/). Nếu chưa hiểu khung tổng thể, đọc [Bài 1](/zola/posting/google-adsense-la-gi-chinh-sach-chuong-trinh/).

## Tóm lại {#tom-lai}

**Google Publisher Policies** quy định nội dung **bị cấm hoàn toàn** hiển thị quảng cáo Google — từ illegal, IP abuse, hate, shocking, adult, **scraped content**, đến malware và misrepresentation. Vi phạm → ads disabled hoặc account closed; khác **Restrictions** (Bài 5) là giới hạn một phần.

Publisher blog Zola an toàn khi viết **gốc, giáo dục**, moderate UGC, và audit định kỳ. [Bài 3](/zola/posting/website-san-sang-cho-adsense/) giúp site pass review; **Bài 4** giúp **giữ** tài khoản sau duyệt.

Series: Bài 1 (khung policies) → Bài 2 (eligibility) → Bài 3 (site readiness) → **Bài 4** (nội dung bị cấm). Tiếp theo: [**Bài 5: Google Publisher Restrictions**](/zola/posting/google-publisher-restrictions-noi-dung-han-che/) — phân biệt "cấm" vs "giới hạn quảng cáo".
