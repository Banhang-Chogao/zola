+++
title = "Chặn trang khỏi Google Search khi cần (noindex, robots)"
description = "Chặn trang khỏi Google Search: noindex, robots.txt, X-Robots-Tag và khi nào nên dùng. Series SEO Bài 6/15 — bám Google SEO Starter Guide."
date = 2026-06-18
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["blog", "google search", "seo", "seo foundation series", "noindex", "robots.txt", "search console", "zola"]
[extra]
thumbnail = "https://banhang-chogao.github.io/zola/img/covers/tao-blog-voi-zola.svg"
seo_keyword = "chặn trang khỏi google search"
featured = false
series = "seo-foundation"
series_part = 6
series_total = 15
references_copyright = "Nội dung dựa trên tài liệu chính thức Google Search Central (SEO Starter Guide, robots meta tag, robots.txt). Google có thể cập nhật khuyến nghị bất cứ lúc nào — nên đối chiếu phiên bản mới nhất trên developers.google.com/search."

[[extra.faq]]
q = "noindex và Disallow trong robots.txt khác nhau thế nào?"
a = "noindex (meta robots hoặc X-Robots-Tag) báo Google không lưu URL vào index sau khi crawl — khuyến nghị khi muốn chặn index. Disallow trong robots.txt chỉ hướng dẫn không crawl — Google có thể vẫn index URL nếu có link từ nơi khác (URL-only index). Muốn chắc không hiện trên Search → dùng noindex, không chỉ Disallow."

[[extra.faq]]
q = "Trang admin hoặc draft nên chặn bằng cách nào?"
a = "Kết hợp: không publish draft lên production (Zola draft=true), robots.txt Disallow path admin (tín hiệu phụ), và noindex trên template admin nếu URL vẫn public. Blog Zola: /editor/, /admin-author/, /admin/paywall/ đã Disallow trong robots.txt — bài posting public không noindex."

[[extra.faq]]
q = "Chặn trang staging có cần noindex không?"
a = "Có — staging/production mirror nên noindex toàn site hoặc password-protect; robots.txt Disallow một mình không đủ nếu URL lộ (backlink, sitemap nhầm). Production blog chính thức: bỏ noindex, kiểm tra Search Console sau deploy ([Bài 5](/zola/posting/google-nhin-trang-giong-nguoi-dung/))."
+++

> 📚 **SEO Foundation Series (Bài 6/15)** — Sau [Bài 1: SEO là gì & Search Essentials](/zola/posting/seo-la-gi-huong-dan-co-ban-google-search/), [Bài 2: Google Search hoạt động — crawl, index, ranking](/zola/posting/google-search-hoat-dong-the-nao/), [Bài 3: Bao lâu để thấy kết quả SEO?](/zola/posting/bao-lau-de-thay-ket-qua-seo/), [Bài 4: Giúp Google tìm nội dung](/zola/posting/giup-google-tim-noi-dung-site/) và [Bài 5: Google có nhìn thấy trang giống người dùng?](/zola/posting/google-nhin-trang-giong-nguoi-dung/), bài này trả lời câu hỏi đối lập discovery: **khi nào và làm sao chặn trang khỏi Google Search?** Tôi bám mục *Don't want a page in search results?* trong [Google SEO Starter Guide](https://developers.google.com/search/docs/fundamentals/seo-starter-guide) và [block search indexing](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag).

[Bài 4](/zola/posting/giup-google-tim-noi-dung-site/) giúp Google **tìm** URL. [Bài 5](/zola/posting/google-nhin-trang-giong-nguoi-dung/) đảm bảo Google **đọc đủ** nội dung. **Bài 6** = kiểm soát **không** muốn URL trên SERP — admin, duplicate, thin utility, staging.

<!-- more -->

## Vì sao cần chặn index — không phải "SEO ngược" {#vi-sao-can-chan}

SEO không phải "index mọi thứ". Google [SEO Starter Guide](https://developers.google.com/search/docs/fundamentals/seo-starter-guide) khuyên **chủ động** loại URL không mang giá trị search hoặc **không nên public**:

- Trang admin, login, internal tool
- Kết quả search nội bộ, filter URL vô nghĩa
- Staging / preview deploy
- Duplicate hoặc printer-friendly (series Bài 10 canonical)
- Trang cảm ơn sau form — thin, không intent

[Bài 2](/zola/posting/google-search-hoat-dong-the-nao/) đã tách crawl vs index. **Chặn index** = quyết định ở bước **index**, sau khi Google **có thể** đã crawl ([Bài 5](/zola/posting/google-nhin-trang-giong-nguoi-dung/)).

Không chặn đúng → **crawl budget** lãng phí ([Bài 4](/zola/posting/giup-google-tim-noi-dung-site/)), duplicate loãng topical authority, hoặc **lộ** path admin trên SERP.

## Ba cơ chế: robots.txt, noindex, X-Robots-Tag {#ba-co-che}

| Cơ chế | Tác dụng chính | Chặn index đáng tin? |
|---|---|---|
| **robots.txt Disallow** | Hướng dẫn **không crawl** path | **Không đủ** một mình |
| **meta robots noindex** | Báo **không index** sau crawl | **Có** — khuyến nghị |
| **X-Robots-Tag header** | Giống noindex ở HTTP header | **Có** — file PDF, API |

Google [documentation](https://developers.google.com/search/docs/crawling-indexing/robots/robots_txt) ghi: URL **Disallow** vẫn có thể **indexed** nếu Google biết URL qua link ngoài — hiển thị **URL only** không snippet.

**Quy tắc vàng:** Muốn **không trên SERP** → **noindex** (hoặc password + không link). Disallow là **bổ sung**, không thay thế.

## Chặn trang khỏi Google Search bằng noindex {#noindex}

### Meta robots trong HTML

```html
<meta name="robots" content="noindex, nofollow">
```

Hoặc chỉ `noindex` nếu vẫn muốn Google follow link trên trang (hiếm).

Theo [robots meta tag](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag):

- Googlebot **phải crawl** trang mới thấy thẻ → **không** dùng robots.txt chặn crawl **và** kỳ vọng noindex cùng lúc (bot không đọc được meta).
- `noindex` có hiệu lực khi Google **fetch lại** — timeline [Bài 3](/zola/posting/bao-lau-de-thay-ket-qua-seo/).

### Các giá trị liên quan

| Directive | Ý nghĩa |
|---|---|
| `noindex` | Không lưu vào index |
| `nofollow` | Không follow link trên trang (legacy; Google vẫn crawl URL nếu biết nguồn khác) |
| `none` | = noindex + nofollow |
| `noarchive` | Không cache snapshot |

### Zola / SSG

Thêm vào frontmatter hoặc template:

```toml
[extra]  # trang utility — không dùng trên bài posting series

seo_noindex = true
```

Template `base.html` render `<meta name="robots" content="noindex">` khi flag bật — pattern phổ biến blog tĩnh. **Bài posting series** giữ **index** — không bật flag.

## robots.txt Disallow — giới hạn và use case {#robots-txt}

### robots.txt làm gì

File tại root (`/robots.txt`) — blog tôi: [static/robots.txt](https://banhang-chogao.github.io/zola/robots.txt) deploy cùng site.

```
User-agent: *
Allow: /

Disallow: /editor/
Disallow: /admin-author/
Disallow: /admin/paywall/
Disallow: /data/

Sitemap: https://banhang-chogao.github.io/zola/sitemap.xml
```

[Bài 4](/zola/posting/giup-google-tim-noi-dung-site/) đã nhắc sitemap + robots. **Bài 6** nhấn **Disallow** = giảm crawl path utility — **không** thay noindex nếu URL vẫn cần "chắc chắn không SERP".

### Khi Disallow đủ

- Bot **không cần** vào path (tiết kiệm crawl).
- URL **không có** internal link public — rủi ro index thấp.
- Kết hợp **auth backend** — Googlebot không login được.

### Khi Disallow không đủ

- URL có backlink hoặc trong sitemap nhầm → vẫn có thể index.
- Cần **gỡ nhanh khỏi SERP** → noindex + [Removals tool](https://search.google.com/search-console/removals) tạm thời.

## X-Robots-Tag và header HTTP {#x-robots-tag}

Với file **không phải HTML** — PDF, JSON export:

```
X-Robots-Tag: noindex
```

GitHub Pages static — ít dùng; nếu host PDF báo cáo, set header qua CDN/host config.

**Search Console** URL Inspection hiển thị cả meta và header — [Bài 5](/zola/posting/google-nhin-trang-giong-nguoi-dung/) workflow vẫn áp dụng để verify.

## Khi nào chặn trang nào — ma trận quyết định {#ma-tran-quyet-dinh}

| Loại trang | Khuyến nghị | Công cụ |
|---|---|---|
| **Bài blog chính** | **Index** | Sitemap, internal link |
| **Admin / editor** | **Không index** | Disallow + noindex template + auth |
| **Staging** | **Không index** | noindex toàn site hoặc HTTP auth |
| **Tag/archive trùng lặp** | Tùy chiến lược | noindex hoặc canonical (Bài 10) |
| **Trang cảm ơn / cart** | **noindex** | meta robots |
| **API / JSON data** | Disallow + noindex | robots.txt + header |
| **Draft Zola** | Không publish | `draft = true` — không lên build |

### Đối lập [Bài 4](/zola/posting/giup-google-tim-noi-dung-site/)

- **Muốn index:** internal link, sitemap, không noindex.
- **Không muốn index:** noindex, không đẩy sitemap, không link nội bộ từ pillar.

Series posting `/zola/posting/seo-la-gi...` — **cố ý index** — checklist Bài 4 ngược lại với Bài 6 cho utility path.

## Remove URL vs chặn lâu dài {#remove-vs-chan}

### Removals tool (tạm thời)

Search Console → **Removals** — ẩn URL khỏi SERP **~6 tháng** — **không** thay thế noindex. Dùng khi:

- Lộ thông tin nhạy cảm — cần ẩn nhanh.
- Đã noindex nhưng cache SERP còn.

### Chặn lâu dài

1. **noindex** trên trang.
2. **Gỡ** internal link tới URL.
3. **Gỡ** khỏi sitemap.
4. Đợi Google recrawl — [Bài 3](/zola/posting/bao-lau-de-thay-ket-qua-seo/) timeline.

**410 Gone** hoặc **404** — URL biến mất khỏi index theo thời gian — khác noindex (URL vẫn tồn tại nhưng không lưu).

## Blog Zola — robots.txt và template thực tế {#zola-thuc-te}

### robots.txt production

Blog tôi **Allow** Googlebot toàn site posting, **Disallow** chỉ utility:

- `/editor/`, `/admin-author/`, `/admin/paywall/`
- `/data/` — báo cáo nội bộ

**Mediapartners-Google**, **AdsBot-Google** Allow — đồng bộ [AdSense series](/zola/posting/google-adsense-la-gi-chinh-sach-chuong-trinh/) crawl ad relevance.

### Bài posting series

- **Không** noindex — `draft = false`, trong sitemap.
- Sau publish: URL Inspection [Bài 5](/zola/posting/google-nhin-trang-giong-nguoi-dung/) — xác nhận **không** có `noindex` nhầm.

### Kiểm tra nhanh

```bash
curl -sI https://banhang-chogao.github.io/zola/posting/seo-la-gi-huong-dan-co-ban-google-search/ | grep -i robots
curl -s https://banhang-chogao.github.io/zola/posting/seo-la-gi-huong-dan-co-ban-google-search/ | grep -i 'meta name="robots"'
```

Kỳ vọng: **không** noindex trên bài pillar.

```bash
curl -s https://banhang-chogao.github.io/zola/robots.txt | grep -i disallow
```

→ Thấy path admin đã chặn crawl.

### Subpath `/zola/`

Production `base_url` — internal link và sitemap dùng `/zola/...` — robots và noindex áp cùng path ([Bài 4](/zola/posting/giup-google-tim-noi-dung-site/)).

## Sai lầm thường gặp {#sai-lam}

**"Disallow = không lên Google"** — Có thể vẫn index URL-only. Dùng **noindex**.

**"noindex toàn site trên production"** — Template staging quên gỡ — disaster SEO. Audit sau mỗi deploy.

**"Chặn crawl + noindex cùng path"** — Bot không đọc meta → noindex **không** áp dụng. Chọn một: cho crawl đọc noindex, hoặc 401/404.

**"noindex trang đang muốn rank"** — Nhầm frontmatter — kiểm tra URL Inspection.

**"Xóa URL khỏi sitemap = deindex ngay"** — Chỉ giảm tín hiệu discover; cần noindex hoặc 404.

**"nofollow internal link pillar"** — Không thay noindex; làm yếu [Bài 4](/zola/posting/giup-google-tim-noi-dung-site/) cluster.

**"robots.txt chặn /zola/ nhầm"** — Cả site không crawl — lỗi staging copy production.

## Checklist chặn index đúng cách {#checklist}

### Trang **không** muốn trên SERP

- [ ] **`noindex`** (meta hoặc X-Robots-Tag) — không chỉ Disallow.
- [ ] **robots.txt Disallow** — giảm crawl (tùy chọn bổ sung).
- [ ] **Không** link nội bộ từ bài index.
- [ ] **Không** có trong sitemap.xml.
- [ ] **Auth** nếu dữ liệu nhạy cảm.
- [ ] Search Console **Removals** nếu cần ẩn khẩn.

### Trang **muốn** rank (bài posting)

- [ ] **Không** noindex — verify URL Inspection [Bài 5](/zola/posting/google-nhin-trang-giong-nguoi-dung/).
- [ ] **robots.txt** không Disallow path bài.
- [ ] Trong **sitemap** — [Bài 4](/zola/posting/giup-google-tim-noi-dung-site/).
- [ ] **Internal link** từ series 1–5.

### Sau deploy

- [ ] Test 1 URL posting + 1 URL admin.
- [ ] Ghi ngày — recheck nếu đổi template ([Bài 3](/zola/posting/bao-lau-de-thay-ket-qua-seo/)).

## Bạn nên làm gì sau bài 6? {#sau-bai-6}

Khi đã biết **chặn** URL đúng cách, bước tiếp trong [SEO Starter Guide](https://developers.google.com/search/docs/fundamentals/seo-starter-guide) là **tổ chức website** — cấu trúc thư mục, navigation (series Bài 7). Trước mắt:

1. **Audit robots.txt** production — Disallow chỉ utility, không chặn `/posting/`.
2. **URL Inspection** 2–3 bài pillar — xác nhận **indexable**, không noindex nhầm.
3. **Liệt kê** path cần noindex lâu dài — admin, data — đối chiếu template.

Chưa giúp Google tìm URL? [Bài 4](/zola/posting/giup-google-tim-noi-dung-site/). Chưa verify render? [Bài 5](/zola/posting/google-nhin-trang-giong-nguoi-dung/).

## Tóm lại {#tom-lai}

**Chặn trang khỏi Google Search** khi URL **không nên** trên SERP — dùng **`noindex`** (meta hoặc header) là cách Google khuyến nghị; **`robots.txt` Disallow** chỉ hạn chế crawl, **không đủ** một mình để chắc không index. Bài posting series **cố ý index** — ngược lại với admin, staging, data.

Pipeline: tìm URL ([Bài 4](/zola/posting/giup-google-tim-noi-dung-site/)) → Google thấy nội dung ([Bài 5](/zola/posting/google-nhin-trang-giong-nguoi-dung/)) → **quyết định index hay noindex** (**Bài 6**) → tổ chức site (Bài 7). Blog Zola: robots.txt chặn utility, posting public trong sitemap — kiểm tra bằng URL Inspection sau deploy.

Series: Bài 1 (Essentials) → Bài 2 (crawl/index) → Bài 3 (thời gian) → Bài 4 (giúp Google tìm) → Bài 5 (Google thấy trang) → **Bài 6** (chặn index khi cần). Tiếp theo: **tổ chức website hợp lý cho SEO** — cấu trúc site và navigation (Bài 7).