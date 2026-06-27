+++
title = "Lỗi nhiều thẻ H1: chẩn đoán và sửa SEO toàn site"
description = "Câu chuyện thật về lỗi nhiều thẻ H1 trên 35 trang blog: cách mình build và chấm điểm HTML thật để phát hiện, sửa hàng loạt và rút ra bài học về CI toàn repo."
date = 2026-06-27
aliases = ["/loi-nhieu-the-h1-sua-seo-toan-site/"]

[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["seo", "thẻ h1", "lighthouse", "html", "zola", "ci/cd", "audit seo", "kỹ thuật blog"]
[extra]
seo_keyword = "lỗi nhiều thẻ H1"
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
featured = false
[[extra.faq]]
q = "Lỗi nhiều thẻ H1 có làm tụt hạng Google không?"
a = "Google đã nói rằng nhiều thẻ H1 không trực tiếp gây phạt xếp hạng. Tuy nhiên nó làm rối cấu trúc dàn bài (document outline), gây khó cho trình đọc màn hình và bị các công cụ audit như Lighthouse hay script chấm điểm nội bộ trừ điểm. Vì vậy đây vẫn là lỗi nên sửa để trang sạch và dễ hiểu hơn."

[[extra.faq]]
q = "Một trang nên có bao nhiêu thẻ H1?"
a = "Quy ước thực hành tốt nhất là đúng một thẻ H1 cho mỗi trang, thường là tiêu đề bài viết. Các đề mục còn lại dùng H2, H3 theo thứ tự giảm dần. Trong template thì để hệ thống render H1 từ title, còn trong thân bài chỉ viết từ H2 trở xuống."

[[extra.faq]]
q = "Làm sao phát hiện lỗi nhiều thẻ H1 trên cả blog?"
a = "Đừng kiểm tra trên file Markdown nguồn mà hãy build ra HTML rồi quét chính HTML đó, vì đó là thứ crawler thật sự nhìn thấy. Mình dùng một script Python chấm điểm SEO duyệt toàn bộ thư mục public/, đếm số thẻ H1 mỗi trang và liệt kê trang nào vi phạm."

[[extra.faq]]
q = "Vì sao bài viết Markdown lại sinh ra nhiều H1?"
a = "Thường do trong thân bài bạn gõ heading bằng một dấu thăng (# Tiêu đề), trong khi template đã tự render một H1 từ trường title. Hai cái cộng lại thành hai H1. Chỉ cần hạ cấp heading trong thân bài xuống ## là xong."

+++

![Sơ đồ dàn bài heading H1 H2 H3 trong một trang web](https://seomoney.org/img/placeholder/placeholder-wide.svg)

Tuần này mình gặp một lỗi tưởng nhỏ mà hoá ra rải đều khắp blog: **lỗi nhiều thẻ H1**. Có trang còn tới ba thẻ `<h1>` cùng lúc. Trang vẫn hiển thị bình thường, người đọc không nhận ra gì, nhưng công cụ chấm điểm SEO thì kêu inh ỏi. Câu chuyện này không chỉ là chuyện sửa một thẻ HTML, mà còn là cách mình truy ra gốc rễ, sửa hàng loạt 59 file một lúc, và một bài học khá đau về cách CI kiểm tra toàn bộ kho mã chứ không riêng phần mình vừa đụng vào.

Mình viết lại đúng những gì đã làm trên blog cá nhân này, kèm số liệu thật và đoạn code thật, để bạn nào đang tự vận hành một site tĩnh có thể tránh lặp lại.

<!-- more -->

## Vấn đề: một trang nhưng có tới ba thẻ H1

Mọi chuyện bắt đầu khi mình chạy một lượt chấm điểm SEO trên toàn bộ HTML đã build. Điểm tổng của site là 99,4/100 — nghe thì cao, nhưng trong danh sách chi tiết có một nhóm trang bị đánh dấu đỏ với lý do lặp đi lặp lại: `có 2 thẻ <h1>`, thậm chí một trang `có 3 thẻ <h1>`.

Nhóm dính lỗi đều là các bài trong series tự học tiếng Hàn. Mình mở thử HTML đã build của một bài để xem tận mắt:

```html
<h1 class="post-single__title">Học tiếng Hàn ngày 5: Patchim &amp; 7 âm đại diện</h1>
...
<h1 id="kr-ngay-5">🇰🇷 Ngày 5 — Patchim (받침) &amp; 7 âm đại diện</h1>
...
<h1 id="g-n-d-r-m-b">[ ㄱ · ㄴ · ㄷ · ㄹ · ㅁ · ㅂ · ㅇ ]</h1>
```

Thẻ H1 đầu tiên là tiêu đề bài, do template tự render — cái này đúng. Hai thẻ H1 còn lại đến từ thân bài Markdown. Tác giả (cũng là mình của vài tháng trước) đã gõ một dòng biểu ngữ kiểu `# 🇰🇷 Ngày 5 — Patchim` ngay đầu bài, cộng thêm một dòng trang trí `# [ ㄱ · ㄴ ... ]` ở giữa. Mỗi dấu thăng đơn đó biến thành một `<h1>` khi Zola render Markdown.

Vậy là cùng một trang có ba thẻ H1 chồng lên nhau. Nhìn ra thì đơn giản, nhưng nó nằm im ở đó từ lâu vì không ai để ý — trang vẫn đẹp, vẫn chạy.

## Vì sao một trang chỉ nên có một thẻ H1

Trước khi sửa, mình muốn nói rõ để tránh hiểu lầm phổ biến: Google **không** trực tiếp phạt xếp hạng vì trang có nhiều H1. Đại diện của Google đã xác nhận điều này nhiều lần. Nếu bạn đọc kỹ tài liệu về thẻ heading trên [MDN Web Docs](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/Heading_Elements), HTML5 về mặt kỹ thuật cho phép nhiều H1 trong các section khác nhau.

Nhưng "không bị phạt" không có nghĩa là "nên làm". Mình vẫn coi đây là lỗi cần sửa vì ba lý do thực tế:

- **Dàn bài rối.** Một trang có nhiều H1 khiến document outline mất trật tự. Crawler và các công cụ phân tích cấu trúc khó xác định đâu là chủ đề chính của trang. Tài liệu của [Google Search Central](https://developers.google.com/search/docs/fundamentals/seo-starter-guide) luôn khuyến khích heading rõ ràng, có thứ bậc.
- **Khó tiếp cận (accessibility).** Người dùng trình đọc màn hình thường nhảy theo cấp heading. Ba H1 trong một trang làm họ tưởng có ba "trang con" riêng biệt. Bài viết hay về chủ đề này trên [web.dev](https://web.dev/learn/html/headings-and-sections/) giải thích rất kỹ phần này.
- **Bị công cụ audit trừ điểm.** Cả Lighthouse lẫn script chấm điểm SEO của riêng mình đều coi "đúng một H1" là một tiêu chí. Mà đã đặt ra thước đo thì mình muốn đạt cho sạch.

Nói ngắn gọn: quy ước **một trang, một H1** giúp trang dễ hiểu cho cả máy lẫn người. Phần còn lại của bài nên dùng H2, H3 theo thứ tự giảm dần.

## Cách mình phát hiện lỗi nhiều thẻ H1 trên toàn site

Đây là phần mình muốn nhấn mạnh nhất, vì nó áp dụng được cho mọi loại audit chứ không riêng thẻ H1.

Sai lầm thường gặp là đi soi file Markdown nguồn. Nhưng nguồn không phải thứ crawler nhìn thấy. Cái Google đọc là **HTML đã build**. Với một site Zola, hai thứ này có thể khác nhau khá nhiều: template chèn thêm header, sidebar, schema, và quan trọng nhất là cái thẻ H1 tiêu đề mà bạn không hề thấy trong file `.md`.

Nên quy trình của mình luôn là: build trước, chấm điểm trên `public/` sau.

```bash
# Build ra HTML thật rồi mới chấm điểm
zola build
python3 scripts/seo_score.py
```

Script chấm điểm duyệt toàn bộ HTML trong `public/`, bỏ qua các trang alias/redirect, và với mỗi trang nó đếm số thẻ H1. Kết quả in ra một bảng "trang nào lỗi gì", sắp xếp từ điểm thấp đến cao. Nhờ vậy mình không phải đoán — danh sách 35 trang dính lỗi hiện ra ngay, kèm lý do cụ thể.

Để tìm chính xác file nguồn nào chứa H1 trong thân bài, mình viết một đoạn Python nhỏ. Điểm mấu chốt: phải bỏ qua phần front matter và **bỏ qua các dòng nằm trong code block**, vì một dòng `# comment` trong khối shell hay Python không phải là heading.

```python
import re, glob
for f in glob.glob("content/**/*.md", recursive=True):
    plus, in_fence = 0, False
    for line in open(f, encoding="utf-8"):
        s = line.rstrip("\n")
        if s.strip() == "+++":
            plus += 1; continue
        if plus < 2:           # còn trong front matter
            continue
        if re.match(r"^\s*(```|~~~)", s):
            in_fence = not in_fence; continue
        if not in_fence and re.match(r"^# (?!#)", s):
            print(f, "→", s[:40])
            break
```

Bước "bỏ qua code fence" này cứu mình một bàn thua. Có bốn bài kỹ thuật chứa `# comment` trong các khối bash/Python — nếu sửa nhầm chúng thành `##` thì vừa hỏng nội dung code, vừa chẳng liên quan gì đến H1 thật. Nếu bạn thích đọc thêm về việc dựng pipeline kiểm tra tự động kiểu này, mình có viết riêng một bài về [QA Gatekeeper giúp blog tự fix lỗi 24/7](/zola/posting/qa-gatekeeper-tu-fix-loi-blog/).

## Sửa hàng loạt: hạ cấp H1 thừa xuống H2

Khi đã có danh sách chính xác, việc sửa khá gọn: hạ mọi H1 trong thân bài xuống H2 (`#` → `##`), giữ nguyên text, chỉ đổi cấp. Mình tái dùng đúng logic phát hiện ở trên, chỉ thêm bước ghi đè:

```python
out.append("#" + line)   # # → ## , giữ nguyên nội dung
```

Cách này an toàn vì nó không đụng vào câu chữ, chỉ thay đúng một ký tự ở đầu dòng heading. Sau khi chạy, dàn bài của mỗi bài trở nên hợp lý: một H1 tiêu đề (do template), rồi các mục `## 1.`, `## 2.` bên dưới.

### Cái bẫy nội dung premium

Đây là chỗ mình suýt mất công vô ích. Các bài tiếng Hàn này là nội dung trả phí (premium). Trong pipeline build, có một bước "strip" thay phần thân đầy đủ bằng đoạn teaser, và một bước "restore" ghép lại phần thân đầy đủ từ thư mục riêng `private_content/`.

Mình sửa H1 trong `content/`, nhưng sau khi chạy "restore", các sửa đổi bị ghi đè ngược lại — vì bản đầy đủ trong `private_content/` vẫn còn H1 cũ. Bài học: khi nội dung có **hai nguồn sự thật**, phải sửa cả hai. Cuối cùng mình hạ cấp H1 ở cả `content/` (29 file) lẫn `private_content/` (30 file) để chúng đồng bộ, bất kể pipeline strip/restore chạy theo chiều nào.

Kết quả sau khi build lại và chấm điểm:

| Chỉ số | Trước | Sau |
|---|---|---|
| Điểm SEO site | 99,4/100 | 99,8/100 |
| Trang hạng A+ | 672 | 701 |
| Trang hạng B | 2 | 0 |
| Trang nhiều H1 | ~35 | 0 |

## Bài học lớn hơn: CI kiểm tra cả repo, không chỉ phần mình sửa

Tưởng xong rồi, nhưng khi mở Pull Request thì CI báo đỏ. Điều trớ trêu: nó đỏ ở một file mình **chưa hề đụng tới** — một bài về sân bay Incheon. Gate kiểm tra link nội bộ phát hiện hai đường dẫn `/categories/du-lich/` và `/archive/` thiếu tiền tố `/zola/`, sẽ 404 trên GitHub Pages.

Vì sao một lỗi không liên quan lại làm hỏng PR của mình? Vì **CI build và kiểm tra toàn bộ repo, không chỉ phần khác biệt trong diff**. Bài Incheon đã mang sẵn link hỏng từ trước; nó chỉ "ngủ đông" cho đến khi một lần build sạch dựng lại toàn site và lôi nó ra ánh sáng. Đây đúng là kiểu lỗi mà mình từng ghi vào sổ tay nội bộ: một bug có sẵn ở nhánh gốc, lộ diện qua CI chạy trên cả kho mã.

Cách xử lý đúng không phải là cằn nhằn "không phải lỗi của tôi", mà là sửa luôn để PR xanh. Mình thêm tiền tố `/zola/` cho đúng quy ước:

```text
/categories/du-lich/  →  /zola/categories/du-lich/
/archive/             →  /zola/archive/
```

Build lại, chạy lại đúng gate đó, lần này nó in `OK: no internal links missing /zola/ prefix`. PR xanh, tự động merge. Nếu bạn quan tâm cách một blog tĩnh deploy lên GitHub Pages và vì sao có cái tiền tố `/zola/` này, mình giải thích trong bài [tạo blog với Zola từ A đến Z](/zola/posting/tao-blog-voi-zola/).

## Tự động hoá để lỗi H1 không quay lại

Sửa một lần thì dễ, nhưng vài tháng sau viết bài mới, rất có thể mình lại quen tay gõ một dấu thăng ở đầu bài. Cách bền vững duy nhất là biến quy ước "một trang một H1" thành một bước kiểm tra tự động, chạy mỗi lần build.

Mình thêm đúng phép đếm này vào script chấm điểm: với mỗi trang trong `public/`, nếu số thẻ H1 khác 1 thì trừ điểm và ghi rõ trang nào. Vì gate này chạy trong CI, một bài mới mắc lỗi sẽ làm Pull Request đỏ ngay, trước khi kịp lên production. Đây cũng là triết lý mình theo đuổi cho cả blog: thà để máy chặn lỗi sớm còn hơn phát hiện khi người đọc đã thấy.

Ý tưởng cốt lõi rất gọn, bạn có thể tự thêm vào quy trình của mình:

```python
from html.parser import HTMLParser

class H1Counter(HTMLParser):
    def __init__(self):
        super().__init__()
        self.count = 0
    def handle_starttag(self, tag, attrs):
        if tag == "h1":
            self.count += 1

def count_h1(html_text):
    p = H1Counter()
    p.feed(html_text)
    return p.count   # đúng 1 là đạt, khác 1 là cảnh báo
```

Cái hay của việc đếm trên DOM đã parse (thay vì regex thô) là nó không bị đánh lừa bởi chữ "h1" nằm trong văn bản hay trong khối code. Nó chỉ đếm đúng thẻ `<h1>` thật sự. Nếu bạn muốn đi xa hơn, có thể kiểm tra luôn thứ tự heading có giảm dần không (không nhảy từ H2 thẳng xuống H4), nhưng riêng phép đếm H1 đã chặn được phần lớn rắc rối phổ biến nhất.

Điểm mấu chốt mình muốn bạn nhớ: một quy ước chỉ thật sự tồn tại khi có công cụ ép tuân thủ nó. Ghi vào tài liệu thì dễ quên; gắn vào CI thì không bao giờ quên.

## Checklist tránh lỗi thẻ H1 cho blog của bạn

Từ vụ này, mình rút ra mấy nguyên tắc tự dặn để không lặp lại:

- **Trong thân bài Markdown, không bao giờ gõ `#`.** Bắt đầu từ `##` trở xuống. Cái H1 đã có template lo.
- **Chấm điểm trên HTML đã build, không chấm trên nguồn.** Crawler đọc `public/`, bạn cũng nên thế.
- **Khi audit một mẫu lỗi, quét toàn bộ site cùng lúc.** Một lỗi hiếm khi đứng một mình; nhóm bài tiếng Hàn của mình dính y hệt nhau vì cùng một khuôn.
- **Bỏ qua code block khi soi heading.** Một dòng `# comment` trong khối code không phải H1.
- **Nội dung nhiều nguồn thì sửa hết các nguồn.** Đừng để bước restore ghi đè công sức của bạn.
- **Coi CI là kiểm tra cả repo.** Nhánh cũ có thể "hồi sinh" bug đã ngủ; rebase lên bản mới nhất trước khi tin vào kết quả CI.

Mấy nguyên tắc này nghe hiển nhiên, nhưng chính sự hiển nhiên khiến mình lơ là. Tự động hoá việc kiểm tra — như cách mình dựng các script chấm điểm và gate link — là cách bền vững nhất để chúng không bị quên. Bạn có thể xem thêm góc nhìn kỹ thuật ở bài [giúp Google tìm thấy nội dung của site](/zola/posting/giup-google-tim-noi-dung-site/) hoặc bài chia sẻ về [cài đặt Git lần đầu](/zola/posting/cai-dat-git-cau-hinh-lan-dau/) nếu bạn mới bắt đầu tự quản lý mã nguồn blog.

## Kết luận

Lỗi nhiều thẻ H1 là kiểu lỗi "vô hình": không làm gãy trang, không làm người đọc khó chịu, nên rất dễ sống sót qua nhiều tháng. Nhưng nó phản ánh một thói quen tốt hay xấu trong cách bạn viết và build nội dung. Sửa nó không khó — hạ một dấu thăng là xong — cái khó là **phát hiện đúng và sửa trọn vẹn** trên toàn site, kèm việc dọn luôn những bug ngủ đông mà CI lôi ra.

Nếu blog của bạn cũng là một site tĩnh tự vận hành, mình khuyên bạn dành một buổi build sạch rồi chấm điểm toàn bộ HTML. Bạn sẽ ngạc nhiên vì những thứ "vẫn chạy" nhưng không hề sạch. Và nếu thấy bài này hữu ích, ghé thêm chuyên mục [Công nghệ](/zola/categories/cong-nghe/) của mình — nơi mình ghi lại những lần debug thật như thế này, hoặc đọc tiếp bài kỹ thuật về [Sentence Transformers (SBERT)](/zola/posting/sentence-transformers-sbert-deep-dive/) nếu bạn quan tâm tới phần AI đằng sau blog. Bạn đang vướng lỗi SEO kỹ thuật nào? Cứ để lại bình luận, mình rất sẵn lòng mổ xẻ cùng.
