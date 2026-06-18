+++
title = "Google Publisher Restrictions — nội dung có giới hạn quảng cáo"
description = "Google Publisher Restrictions: nội dung hạn chế quảng cáo, fill rate thấp hơn Policies. Series AdSense Bài 5/15 — bám Google Help."
date = 2026-06-18
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["google adsense", "adsense", "adsense foundation series", "publisher restrictions", "monetization", "nội dung hạn chế"]
[extra]
thumbnail = "https://banhang-chogao.github.io/zola/img/covers/tao-blog-voi-zola.svg"
seo_keyword = "google publisher restrictions"
featured = false
series = "adsense-foundation"
series_part = 5
series_total = 15
references_copyright = "Nội dung dựa trên tài liệu chính thức Google AdSense Help (Google Publisher Restrictions, AdSense Program policies). Google có thể cập nhật danh mục Restrictions bất cứ lúc nào — publisher có trách nhiệm theo dõi phiên bản mới nhất theo Terms and Conditions."

[[extra.faq]]
q = "Google Publisher Restrictions khác Publisher Policies ở điểm nào?"
a = "Policies = nội dung bị cấm hoàn toàn đặt quảng cáo Google — vi phạm có thể disable ads hoặc đóng tài khoản. Restrictions = nội dung được phép publish nhưng bị gắn inventory restriction — ít nguồn quảng cáo bid hơn, fill rate/RPM thấp hơn, đôi khi không có ad. Không chặn đăng ký AdSense như Policies nghiêm trọng."

[[extra.faq]]
q = "Blog công nghệ SEO/AdSense có bị Restrictions không?"
a = "Thường không — nếu không có sexual content, shocking graphic, gambling, tobacco, vũ khí, thuốc không phê duyệt. Blog giáo dục gốc tiếng Việt như series AdSense/SEO của tôi nằm ngoài hầu hết content restrictions. Cần tránh behavioral restrictions: ad che nội dung hoặc nội dung che ad."

[[extra.faq]]
q = "Restrictions có làm AdSense từ chối duyệt không?"
a = "Không theo nghĩa eligibility fail như Policies (illegal, scraped, CSAM). Site chủ yếu nội dung restricted vẫn có thể được duyệt — nhưng doanh thu kém vì Google Ads và nhiều advertiser không bid. Một số chủ đề borderline (tin nhạy cảm, sức khỏe) nên tách section hoặc không gắn ad code trang đó."
+++

> 📚 **Google AdSense Foundation Series (Bài 5/15)** — Sau [Bài 1: Google AdSense là gì & khung Program policies](/zola/posting/google-adsense-la-gi-chinh-sach-chuong-trinh/), [Bài 2: Điều kiện đủ tư cách AdSense](/zola/posting/dieu-kien-du-tu-cach-adsense/), [Bài 3: Website sẵn sàng cho AdSense](/zola/posting/website-san-sang-cho-adsense/) và [Bài 4: Google Publisher Policies — nội dung bị cấm](/zola/posting/google-publisher-policies-noi-dung-bi-cam/), bài này đi vào **google publisher restrictions** — lớp chính sách thứ hai: **Google Publisher Restrictions — nội dung có giới hạn quảng cáo**. Tôi bám [Google Publisher Restrictions](https://support.google.com/adsense/answer/10437795?hl=en) — không phải diễn giải forum "AdSense không chạy chủ đề X".

[Bài 4](/zola/posting/google-publisher-policies-noi-dung-bi-cam/) đã phân tích nội dung **bị cấm tuyệt đối** — illegal, scraped, CSAM, malware. Bài 5 trả lời câu hỏi publisher hay gặp sau khi pass review: **"Site hợp pháp, không vi phạm Policies — sao RPM thấp hoặc một số trang không có ad?"** — có thể do **inventory restriction**, không phải account disabled.

<!-- more -->

## Google Publisher Restrictions là gì — khác Policies thế nào? {#restrictions-la-gi}

Theo [Google Publisher Restrictions](https://support.google.com/adsense/answer/10437795?hl=en), **publisher restrictions** xác định nội dung **bị hạn chế nhận quảng cáo từ một số nguồn** — không phải nội dung bị cấm publish.

Google ghi rõ:

- Nội dung bị gắn **inventory restriction** → **ít advertising source** eligible bid.
- Trong một số trường hợp **không có nguồn nào bid** → **không có ad** trên trang đó.
- **Google Ads** (trước đây AdWords) **không serve** trên content labeled với các restriction này.

Bạn **có thể chọn** monetize nội dung thuộc Restrictions — nhưng doanh thu **thường thấp hơn** nội dung không restricted.

[Bài 1](/zola/posting/google-adsense-la-gi-chinh-sach-chuong-trinh/) đã vẽ khung Program policies. [Bài 4](/zola/posting/google-publisher-policies-noi-dung-bi-cam/) = **cấm**. **Bài 5** = **giới hạn** — ranh giới mỏng nhưng quan trọng cho publisher tin tức, sức khỏe, lifestyle.

Google đang **migrate** Policies và Restrictions sang [Publisher Policies Help Center](https://support.google.com/publisherpolicies/) — publisher nên theo dõi cả AdSense Help và Help Center mới.

## Hậu quả thực tế: fill rate, RPM, Google Ads {#hau-qua-thuc-te}

Restrictions **không** đồng nghĩa:

- Account disabled (thường thuộc [Policies — Bài 4](/zola/posting/google-publisher-policies-noi-dung-bi-cam/))
- Từ chối đăng ký lần đầu (thường do eligibility + Policies — [Bài 2](/zola/posting/dieu-kien-du-tu-cach-adsense/))

Restrictions **có nghĩa**:

| Hiện tượng | Giải thích |
|---|---|
| **Fill rate thấp** trên URL cụ thể | Ít advertiser bid vì inventory label |
| **RPM/CPM thấp** | Chỉ network giá thấp hoặc limited demand còn lại |
| **Trang trắng ad slot** | Không bid nào — vẫn "hợp pháp" theo Restrictions |
| **Policy center** có thể báo **restriction** | Khác "Must fix" violation Policies |

Publisher niche tin tức (bạo lực, tai nạn), sức khỏe (thuốc), tài chính mạo hiểm — hay thấy pattern: **index SEO tốt, traffic có, ad revenue kém** trên đúng các URL đó.

[Bài 3](/zola/posting/website-san-sang-cho-adsense/) nhấn site readiness — unique content, navigation. Readiness pass **không** bảo vệ RPM nếu chủ đề restricted.

## Content restrictions — danh mục chính {#content-restrictions}

[10437795](https://support.google.com/adsense/answer/10437795?hl=en) nhóm **content restrictions** gồm (không exhaustive — đối chiếu trang chính thức):

### Sexual content

Nội dung gợi cảm, nudity, fetish, sexual entertainment, sex tips, enhancement drugs — **không** explicit như Policies (porn) nhưng vẫn **restricted**. Ranh giới Policies vs Restrictions ở adult: **explicit = Policies** ([Bài 4](/zola/posting/google-publisher-policies-noi-dung-bi-cam/)); **suggestive/gratifying = Restrictions**.

### Shocking content

Gore, graphic violence accounts, profanity nặng — **restricted**. Policies cấm **gratuitous** shocking không ngữ cảnh; Restrictions cover **mức độ** thấp hơn vẫn hạn chế ad. Tin tức tai nạn có ảnh graphic — restricted dù journalistic.

### Explosives, guns, other weapons

Promote sale hoặc hướng dẫn lắp ráp — restricted. Blog review súng săn, hướng dẫn nổ — không phải lúc nào cũng Policies disable, nhưng **ad limited**.

### Tobacco, recreational drugs, alcohol

Bán thuốc lá, cần sa, cocaine; bán rượu online; khuyến khích uống bia thi đấu — restricted.

### Online gambling, prescription drugs, unapproved supplements

Casino online, pharmacy không license, supplement Ephedra — restricted. Affiliate gambling ở VN cần cẩn thận — có exclusion theo quốc gia trong policy, đối chiếu [online gambling](https://support.google.com/publisherpolicies/answer/10437963).

### App removed from Google Play

App bị gỡ Play vì vi phạm — inventory restricted nếu monetize app đó.

**Publisher blog công nghệ** (AdSense, SEO, Zola) thường **không** chạm các nhóm trên — đó là lý do series của tôi ít lo Restrictions content, nhưng vẫn cần biết khi mở rộng chủ đề.

## Behavioral restrictions — ad và nội dung che nhau {#behavioral-restrictions}

Ngoài **nội dung**, Restrictions có **behavioral**:

### Google-served ads obscuring content

Ad **che một phần hoặc toàn bộ** nội dung — không được. Liên quan ad placement UX — series Bài 8 sẽ đi sâu; ở đây nhấn: popup ad, sticky che chữ, interstitial không dismiss — **restriction/violation** tùy mức.

### Content obscuring Google-served ads

Nội dung **che ad** — ví dụ overlay, CSS ẩn ad, fake content đè lên ad unit. Google coi là manipulation inventory.

[Bài 3](/zola/posting/website-san-sang-cho-adsense/) yêu cầu layout không che nội dung — đồng thời **không che ad** sau khi gắn code.

## Video inventory restrictions (tóm tắt) {#video-restrictions}

Nếu bạn monetize **video** (AdSense in-stream, Ad Manager), [10437795](https://support.google.com/adsense/answer/10437795?hl=en) có **video inventory restrictions**: khai báo đúng in-stream vs accompanying content, dùng IMA SDK, không obstruct controls, autoplay rules…

Blog Zola tĩnh chủ yếu **article** — phần video ít áp dụng. Nếu nhúng YouTube + ad overlay riêng, đọc [video inventory restrictions](https://support.google.com/publisherpolicies/answer/15208072) trước monetize video page.

## So sánh Policies vs Restrictions — bảng nhanh {#so-sanh-policies-restrictions}

| | **Publisher Policies** ([Bài 4](/zola/posting/google-publisher-policies-noi-dung-bi-cam/)) | **Publisher Restrictions** (Bài 5) |
|---|---|---|
| **Nội dung** | Bị **cấm** ads | **Được phép** nhưng ad **hạn chế** |
| **Hậu quả nặng** | Disable ads, đóng account | Fill/RPM thấp, có thể no ad |
| **Ví dụ** | Scraped, CSAM, malware | Tobacco, gambling, shocking news |
| **Eligibility apply** | Fail nếu site chủ yếu vi phạm | Thường vẫn apply được |
| **Google Ads** | Không serve (vi phạm) | Không serve trên restricted label |

Ranh giới **shocking/adult**: một bài có thể từ Restrictions → Policies nếu **mức độ** tăng (explicit, gratuitous gore). Khi nghi ngờ, ưu tiên **không gắn ad** trang đó hoặc làm mềm nội dung.

## Audit blog Zola theo Restrictions {#audit-zola}

Áp Restrictions lên blog tôi đang chạy:

**Thấp rủi ro content restriction**

- Series AdSense, SEO — giáo dục, không adult/gambling/weapons.
- Uranium series — khoa học; [Bài 4](/zola/posting/google-publisher-policies-noi-dung-bi-cam/) đã tách khỏi shocking war graphic.
- Hub báo chí Iran — chính trị, không graphic; vẫn theo dõi nếu thêm ảnh nhạy cảm.

**Cần tránh khi mở rộng**

- Chuyên mục review **vũ khí, CBD, vape** — restricted.
- **Affiliate casino, thuốc** — restricted + có thể Policies.
- Tin **tai nạn graphic** — shocking restriction.

**Behavioral**

- Không sticky ad che TOC/menu ([Bài 3](/zola/posting/website-san-sang-cho-adsense/) UX).
- Không CSS `z-index` che ad unit.

Kết hợp [SEO Foundation](/zola/posting/seo-la-gi-huong-dan-co-ban-google-search/) — traffic đến URL restricted vẫn có giá trị brand/affiliate khác, không chỉ AdSense.

## Sai lầm publisher thường gặp {#sai-lam}

### 1. "Restrictions = bị ban AdSense"

Nhầm với Policies. Restrictions = monetize **được** nhưng **kém**.

### 2. "Tin tức bạo lực = Policies, không phải Restrictions"

Tùy mức graphic và ngữ cảnh — có thể Restrictions trước, Policies nếu quá gore.

### 3. "Chỉ trang có ad code mới bị đánh giá"

Google đánh giá **inventory/site** — nội dung restricted trên domain có thể ảnh hưởng labeling.

### 4. "Bỏ qua Policy center warning 'limited ads'"

Đó là tín hiệu Restrictions — cần quyết định: sửa nội dung, tách URL, hoặc chấp nhận RPM thấp.

### 5. "Gambling OK vì server ở nước cho phép"

Policy có **exclusion theo geo** — publisher VN vẫn cần đọc [online gambling restriction](https://support.google.com/publisherpolicies/answer/10437963), không assume.

### 6. "Ad che nội dung một chút để tăng viewability"

Behavioral restriction — có thể policy issue, không chỉ RPM.

## Checklist đối chiếu Restrictions {#checklist}

Sau [audit Policies Bài 4](/zola/posting/google-publisher-policies-noi-dung-bi-cam/), tôi chạy thêm checklist bám [10437795](https://support.google.com/adsense/answer/10437795?hl=en):

- [ ] **Sexual/suggestive**: Không nudity, fetish, sex tips trên trang có ad.
- [ ] **Shocking**: Tránh graphic gore/profanity nặng; tin nhạy cảm tách section hoặc no-ad.
- [ ] **Weapons/drugs/tobacco/alcohol**: Không promote sale hoặc hướng dẫn lắp ráp.
- [ ] **Gambling/pharmacy/supplements**: Không affiliate casino hoặc thuốc không phê duyệt.
- [ ] **Behavioral**: Ad không che content; content không che ad.
- [ ] **Video** (nếu có): Đúng SDK và placement declaration.
- [ ] **Policy center**: Đọc "limited" vs "must fix" — xử lý đúng loại.

## Bạn nên làm gì sau bài 5? {#sau-bai-5}

Sau khi hiểu **Restrictions**, bước tiếp trong series là [**Bài 6: Phân biệt Policies và Restrictions**](/zola/posting/phan-biet-policies-va-restrictions-adsense/) thực chiến và **helpful content** (Bài 7). Trước mắt:

1. **Map từng section site** — tag mental "restricted" vs "safe for full fill".
2. **Đọc** [Policy center](https://support.google.com/adsense/answer/7003627?hl=en) — phân biệt violation vs limited ads.
3. **Giữ readiness** [Bài 3](/zola/posting/website-san-sang-cho-adsense/) — Restrictions không thay thế unique content.

Chưa pass eligibility? [Bài 2](/zola/posting/dieu-kien-du-tu-cach-adsense/). Chưa audit Policies? [Bài 4](/zola/posting/google-publisher-policies-noi-dung-bi-cam/).

## Tóm lại {#tom-lai}

**Google Publisher Restrictions** đánh dấu nội dung **được phép** nhưng **quảng cáo bị giới hạn** — ít bid, Google Ads không serve, RPM/fill thấp hơn. Khác **Publisher Policies** ([Bài 4](/zola/posting/google-publisher-policies-noi-dung-bi-cam/)) là **cấm tuyệt đối** và rủi ro disable account.

Publisher blog giáo dục AdSense/SEO ít chạm content restrictions — nhưng cần tránh behavioral (ad/content che nhau) và biết khi mở rộng chủ đề nhạy cảm. Hiểu Restrictions giúp giải thích **"đã duyệt mà ad ít"** — không phải lúc nào cũng do SEO hay invalid traffic.

Series: Bài 1 (khung) → Bài 2 (eligibility) → Bài 3 (readiness) → Bài 4 (Policies cấm) → **Bài 5** (Restrictions giới hạn). Tiếp theo: [**Bài 6: Phân biệt Policies và Restrictions**](/zola/posting/phan-biet-policies-va-restrictions-adsense/) — đọc Policy center và lên kế hoạch chủ đề site.