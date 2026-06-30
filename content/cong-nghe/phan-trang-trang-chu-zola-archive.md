+++
title = "Phân trang trang chủ Zola: khi blog tưởng như mất bài"
description = "Phân trang trang chủ Zola dễ khiến blog chỉ hiện 10 bài mới nhất, tưởng mất bài sau khi đổi theme. Mình kể lại cách truy nguyên và dựng trang lưu trữ để cứu."
date = 2026-06-27
aliases = ["/phan-trang-trang-chu-zola-archive/",
  "/posting/phan-trang-trang-chu-zola-archive/"
]
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["github pages", "phân trang", "seo", "static site generator", "zola"]
[extra]
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
seo_keyword = "phân trang trang chủ Zola"
featured = false

[[extra.faq]]
q = "Vì sao trang chủ Zola chỉ hiển thị 10 bài dù blog có hàng trăm bài?"
a = "Vì trang chủ phân trang theo section gốc (content/_index.md). Nếu mọi bài viết nằm ở các section con như posting/ hay baochi/ thì section gốc gần như không có bài trực tiếp, khiến paginator chỉ tạo đúng 1 trang. Template gộp bài để hiển thị nhưng chỉ cắt được nhóm đầu tiên, nên các bài còn lại không có đường ra từ trang chủ."

[[extra.faq]]
q = "Zola có tự phân trang cho feed gộp từ nhiều section không?"
a = "Không. Zola chỉ phân trang trên các trang trực tiếp của một section theo paginate_by. Nó không tự sinh các trang /page/2/, /page/3/ cho một feed được gộp thủ công từ nhiều section trong template. Vì vậy bạn cần một section thật để phân trang, hoặc một trang lưu trữ liệt kê tất cả."

[[extra.faq]]
q = "Trang lưu trữ (archive) có gây trùng lặp nội dung hại SEO không?"
a = "Không, nếu làm đúng. Trang lưu trữ chỉ liệt kê tiêu đề và link tới bài gốc, không sao chép nội dung. URL bài viết giữ nguyên, canonical vẫn trỏ về bài gốc, nên không tạo duplicate content. Ngược lại nó còn tăng độ sâu thu thập (crawl depth) và liên kết nội bộ."

[[extra.faq]]
q = "Làm sao biết bài viết có thật sự bị mất hay chỉ bị ẩn?"
a = "Chạy zola build rồi đếm số trang sinh ra trong public/, kiểm tra sitemap.xml và feed RSS/Atom. Nếu bài vẫn có file HTML, vẫn nằm trong sitemap và feed thì bài không mất — chỉ là listing (trang chủ/chuyên mục) không hiển thị hết. Đây là lỗi giao diện, không phải mất dữ liệu."
+++

Tuần rồi mình gặp một phen hú vía với blog Zola: sau khi đổi theme, trang chủ chỉ còn hiện đúng 10 bài, trong khi blog có tới hơn 170 bài. Cảm giác đầu tiên là "toang rồi, rollback làm mất bài". Nhưng sau khi bình tĩnh đào sâu, mình phát hiện thủ phạm thật sự là cách **phân trang trang chủ Zola** hoạt động — chứ không bài nào bị mất cả. Bài này mình kể lại nguyên ca: từ lúc hoảng, đến lúc truy ra gốc rễ, rồi cách mình xử lý gọn gàng bằng một trang lưu trữ. Nếu bạn cũng đang chạy blog tĩnh với Zola và một ngày thấy trang chủ "nuốt" mất bài, hy vọng bài này tiết kiệm cho bạn vài tiếng debug.

<!-- more -->

## Triệu chứng: blog tưởng như mất bài sau khi đổi theme

Mọi chuyện bắt đầu khi mình mở trang chủ sau lần cập nhật giao diện. Đập vào mắt là khu "Bài mới nhất" với vỏn vẹn 10 thẻ bài. Cuộn xuống hết trang — không có nút sang trang, không có "trang 2", không có gì cả. Trang chủ kết thúc ở bài thứ 10.

Mình đã viết hơn 170 bài trong nhiều tháng: loạt bài Git & GitHub, học tiếng Hàn, ngân hàng số, du lịch... Vậy mà giờ chỉ thấy 10 bài. Suy nghĩ đầu tiên rất bản năng: "Cái rollback hôm trước làm mất content rồi."

Nhưng trước khi gõ lệnh khôi phục lung tung, mình tự nhắc một nguyên tắc: **đừng sửa khi chưa hiểu**. Phải tách bạch hai khả năng đã:

1. Bài **bị xoá thật** khỏi repo (mất dữ liệu).
2. Bài **vẫn còn** nhưng giao diện không hiển thị hết (lỗi listing).

Hai trường hợp này cách xử lý khác nhau hoàn toàn. Nhầm cái này sang cái kia là dễ phá thêm.

## Bước kiểm tra: bài còn hay mất?

Mình làm vài phép thử nhanh, và đây là phần mình khuyên bạn luôn làm trước khi hốt hoảng.

Đầu tiên, đếm file markdown trong thư mục nội dung:

```bash
find content -name "*.md" | wc -l
```

Con số trả về đúng như kỳ vọng — đủ bài. Vậy file nguồn còn nguyên.

Tiếp theo, build thử rồi soi kết quả thật sự sinh ra:

```bash
zola build
# -> Creating 194 pages (8 orphan) and 12 sections
```

194 trang được tạo. Rồi mình kiểm tra sitemap và feed:

```bash
grep -c "<url>" public/sitemap.xml      # đủ URL bài viết
grep -c "<item>" public/rss.xml         # 174 item trong RSS
```

Đến đây thì rõ: **mọi bài vẫn render, vẫn nằm trong sitemap và RSS**. Không bài nào bị mất. Vấn đề chỉ nằm ở chỗ trang chủ không chịu hiển thị quá 10 bài. Thở phào một nhịp — đây là lỗi giao diện, không phải thảm hoạ dữ liệu. Bài học đầu tiên: trước khi tin là "mất bài", hãy để `zola build`, `sitemap.xml` và feed nói cho bạn nghe sự thật.

## Truy nguyên: vì sao phân trang trang chủ Zola chỉ cho 10 bài

Giờ tới phần thú vị. Mình mở template trang chủ ra đọc kỹ. Cấu trúc của nó đại khái thế này: gộp toàn bộ bài từ section `posting/` và `baochi/` lại, sắp xếp theo ngày, rồi cắt theo trang để hiển thị.

Trong `content/_index.md` có khai báo:

```toml
template = "index.html"
paginate_by = 10
```

Và template dùng đối tượng `paginator` của Zola để biết đang ở trang mấy, có bao nhiêu trang. Vấn đề ẩn nằm ở đúng chỗ này.

Mình kiểm tra thư mục build và thấy điều bất thường:

```bash
ls -d public/page/*/
# chỉ có public/page/1/   (và nó redirect về "/")
```

Chỉ có đúng **một** trang phân trang. Trong khi đó, trang chuyên mục `/categories/tat-ca/` lại có tới 18 trang đầy đủ, hoạt động ngon lành. Cùng một blog, cùng số bài, mà chỗ thì 18 trang, chỗ thì 1 trang. Sự khác biệt này chính là manh mối.

## Gốc rễ: Zola phân trang theo section, không phân trang feed gộp

Đây là điểm cốt lõi mà mình muốn bạn nhớ nếu chỉ đọc một đoạn trong bài này.

Trong Zola, `paginate_by` phân trang dựa trên **các trang trực tiếp của chính section đó**. Trang chủ của mình dùng template gắn vào **section gốc** (`content/_index.md`). Nhưng section gốc này **không chứa bài viết trực tiếp nào** — mọi bài đều nằm trong các section con `posting/` và `baochi/`.

Hệ quả dây chuyền:

- Section gốc có 0 bài trực tiếp → Zola chỉ tạo đúng 1 "pager".
- `paginator.number_pagers = 1` → biến `feed_pages` trong template bằng 1.
- Khối điều kiện hiển thị nút sang trang là `{% if feed_pages > 1 %}` → **không bao giờ chạy**.
- Template vẫn gộp đủ 174 bài vào biến `feed`, nhưng lúc cắt theo trang thì `offset` luôn bằng 0, nên **mãi mãi chỉ lấy được 10 bài đầu**.

Nói cách khác: template "biết" có 174 bài, nhưng cơ chế phân trang của Zola không cho nó đi quá nhóm đầu tiên, vì cái feed đó là **gộp thủ công từ nhiều section** chứ không phải trang thật của một section.

Đây không phải bug của Zola — nó hoạt động đúng thiết kế. Zola không tự sinh ra `/page/2/`, `/page/3/`... cho một feed mà bạn ghép lại trong template. Muốn có những trang đó, bạn cần một **section thật** đủ bài để phân trang. Trang `/categories/tat-ca/` chạy tốt chính vì taxonomy "Tất cả" là một tập hợp thật, được Zola phân trang đàng hoàng thành 18 trang.

Nếu bạn mới làm quen công cụ này, mình có viết riêng bài [tạo blog với Zola từ con số 0](/posting/tao-blog-voi-zola/) và bài so sánh [Zola với Hugo](/posting/zola-vs-hugo/) để bạn nắm mô hình section/taxonomy trước khi đụng vào những ca như thế này. Tài liệu gốc về cơ chế này nằm ở [trang pagination của Zola](https://www.getzola.org/documentation/templates/pagination/), rất đáng đọc.

## Cách mình xử lý: dựng trang lưu trữ cho toàn bộ bài

Tới phần quyết định: sửa thế nào cho an toàn?

Mình cân nhắc vài hướng. Sửa thẳng cơ chế phân trang trang chủ thì rủi ro cao, vì Zola vốn không phân trang được feed gộp — ép nó sẽ sinh ra link `/page/2/` dẫn tới trang 404. Dồn hết bài về section gốc thì đổi URL hàng loạt, hỏng SEO. Cả hai đều không ổn.

Hướng mình chọn vừa an toàn, vừa đúng tinh thần "không đổi URL, không phá theme": **dựng một trang lưu trữ (archive) liệt kê toàn bộ bài trên một trang duy nhất.**

Ý tưởng:

- Tạo `content/archive/_index.md` dùng template riêng.
- Template `archive.html` gộp `posting/` + `baochi/`, loại các trang kỹ thuật, sắp theo ngày giảm dần, **nhóm theo năm** cho dễ quét.
- Thêm bộ lọc danh mục chạy hoàn toàn ở phía trình duyệt (vanilla JS, không thư viện ngoài) để bấm lọc nhanh theo Công nghệ, Du lịch, Ngân hàng...

Phần thu thập bài trong template đại khái thế này:

```jinja
{% set posting = get_section(path="posting/_index.md") %}
{% set baochi = get_section(path="baochi/_index.md") %}
{% set_global all_pages = [] %}
{% for page in posting.pages | concat(with=baochi.pages) %}
    {% if not page.extra.feed_anchor %}
        {% set_global all_pages = all_pages | concat(with=[page]) %}
    {% endif %}
{% endfor %}
{% set all_pages = all_pages | sort(attribute="date") | reverse %}
```

Một lưu ý nhỏ nhưng dễ vấp: khi nối chuỗi trong Tera (engine template của Zola), đừng nhét filter vào giữa biểu thức kiểu `cats ~ (cat | slugify)`. Mình bị lỗi parse đúng chỗ này, phải tách filter ra một câu lệnh `set` riêng rồi mới nối. Tera khó tính hơn bạn tưởng ở mấy chỗ này.

Sau khi có trang lưu trữ, mình gắn lối vào cho nó ở hai chỗ tự nhiên:

- **Trang chủ**: thêm nút "Xem tất cả N bài viết →" ngay dưới khu bài mới nhất, để không ai bị kẹt ở 10 bài.
- **Footer**: thêm link "Tất cả bài viết" trong mục giới thiệu.

Kết quả: mọi bài hợp lệ giờ truy cập được từ một nơi, crawl được từ một nơi, mà **không đổi một URL bài viết nào** và không đụng vào cơ chế phân trang vốn mong manh của trang chủ.

Về mặt SEO, trang lưu trữ này là điểm cộng chứ không phải điểm trừ: nó chỉ chứa tiêu đề và link, không sao chép nội dung nên không gây trùng lặp; đồng thời tăng liên kết nội bộ và độ sâu thu thập. Nếu bạn quan tâm cách mình kiểm soát link nội bộ khỏi gãy, mình có guard riêng — kể trong bài [QA Gatekeeper tự fix lỗi blog](/posting/qa-gatekeeper-tu-fix-loi-blog/).

## Vài bài học khi vận hành blog Zola

Ca này để lại cho mình mấy điều đáng ghi nhớ, áp dụng được cho bất kỳ ai chạy site tĩnh:

**1. "Trang chủ ít bài" không đồng nghĩa "mất bài".** Listing và dữ liệu là hai chuyện khác nhau. Luôn để build, sitemap và feed xác nhận trước khi kết luận.

**2. Hiểu mô hình phân trang của công cụ.** Zola phân trang theo section thật. Mọi thứ bạn gộp thủ công trong template sẽ không được phân trang tự động. Biết giới hạn này thì sẽ không thiết kế trang chủ dựa vào giả định sai.

**3. Sửa kiểu cộng thêm, đừng sửa kiểu phá vỡ.** Thay vì vặn lại cơ chế lõi (rủi ro, dễ tạo link 404), mình thêm một trang lưu trữ bổ trợ. Giao diện cũ vẫn nguyên, URL vẫn nguyên, mà vấn đề được giải quyết.

**4. Giữ URL là giữ SEO.** Mỗi lần đổi đường dẫn là một lần đánh đổi thứ hạng và link cũ. Nếu buộc phải đổi, hãy dùng `aliases` để chuyển hướng.

**5. Tách bạch lỗi nội dung và lỗi hạ tầng.** Trong lúc xử lý, mình còn vướng một lần deploy đỏ vì giới hạn API của GitHub Pages — hoàn toàn không liên quan nội dung. Mình có ghi lại cách phân biệt các lỗi deploy kiểu này trong bài [tự động deploy Zola bằng GitHub Actions](/posting/tu-dong-deploy-zola-github-actions/). Đừng để một lỗi hạ tầng làm bạn nghi oan cho bài viết của mình.

Nếu thích đọc thêm các ghi chép vận hành blog và chỉnh giao diện theo kiểu "vừa làm vừa rút kinh nghiệm", bạn có thể ghé bài [làm theme log, sửa menu công cụ](/posting/lam-theme-log-sua-menu-cong-cu/) hoặc lướt cả chuyên mục [Công nghệ](/categories/cong-nghe/) của blog.

## Bước tiếp theo

Tóm lại một câu: blog của mình chưa từng mất bài — chỉ là **phân trang trang chủ Zola** giới hạn ở 10 bài mới nhất, khiến phần còn lại không có lối ra từ trang chủ. Cách chữa gọn nhất là dựng một trang lưu trữ liệt kê tất cả, đặt lối vào ở trang chủ và footer, giữ nguyên mọi URL.

Nếu bạn đang chạy blog tĩnh và muốn chắc chắn không bài nào bị "ẩn", hãy thử ngay ba việc: chạy `zola build` rồi đếm trang, kiểm tra `sitemap.xml`, và mở [trang lưu trữ tất cả bài viết](/archive/) để soi xem listing có khớp số bài thật không. Còn nếu bạn muốn mình viết tiếp một bài hướng dẫn từng bước dựng trang archive có bộ lọc danh mục cho Zola, để lại góp ý nhé — mình sẽ làm một bài chi tiết kèm full code.
