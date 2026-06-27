+++
title = "Debug Lỗi Zola Series Navigation: Từ 11 Broken Links Đến Fix"
description = "Debug 11 broken links trong Zola series navigation — phân tích 3 nguyên nhân chính (frontmatter, date, URL) và cách fix từng cái."
date = 2026-06-27
aliases = ["/debug-zola-series-navigation-links/"]

[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["debug", "internal links", "seo", "series navigation", "static site generator", "zola"]
[extra]
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
seo_keyword = "zola series navigation debug"
featured = false

[[extra.faq]]
q = "Tại sao internal links checker lại báo 11 broken hrefs nếu tất cả file đã được tạo?"
a = "Có 3 lý do chính: (1) frontmatter bị thiếu hay không đúng — series field, series_part bị xóa; (2) ngày tháng giống nhau — Zola dùng date để sort, nên page.lower/page.higher không hoạt động; (3) URL prefix không khớp — base_url không có /zola/ nhưng link có."

[[extra.faq]]
q = "page.lower và page.higher là gì trong Zola?"
a = "Đó là các field tự động của Zola dùng để liên kết tới bài viết trước/sau trong cùng section, dựa vào ngày tháng (date). Nếu 2 bài cùng ngày, Zola không biết cái nào trước cái nào sau, nên không generate link."

[[extra.faq]]
q = "Tại sao base_url lại quan trọng với internal links?"
a = "base_url quyết định cách Zola sinh ra đường dẫn tuyệt đối. Nếu base_url là https://seomoney.org (không /zola/), thì Zola sinh /posting/..., KHÔNG /zola/posting/.... Khi link thủ công khác base_url, checker sẽ báo xung đột."

[[extra.faq]]
q = "Làm sao phát hiện được lỗi này nhanh hơn?"
a = "Chạy `python3 scripts/check_internal_links.py` ngay sau khi thêm bài mới hoặc sửa series. Đừng chờ CI chạy trên remote. Kiểm tra local trước sẽ tiết kiệm thời gian."

[[extra.faq]]
q = "Có công cụ nào để tự động sửa các lỗi này không?"
a = "Có — Zola có thể sinh schema JSON từ frontmatter, Python script có thể validate ngày và detect duplicate, sed/regex có thể fix link prefix. Nhưng debug thủ công thường nhanh hơn vì phải hiểu bối cảnh."

[[extra.faq]]
q = "Điều này áp dụng cho các static site generator khác được không?"
a = "Có. Hugo, Jekyll, Astro đều dùng date để sort posts. Bất kỳ CMS nào dùng frontmatter cũng có risk lỗi tương tự. Quy tắc chung: validate schema, kiểm tra date unique, test local trước push."
+++

> 🔍 **Bài này là case study thực tế** — hành trình từ "CI báo 11 broken links" tới "tất cả link xanh" trong 3 bước debug.

Khi viết content series (bài viết theo chương), việc liên kết giữa các phần rất quan trọng cho UX, SEO, và "crawl depth" (giúp bots tìm hết bài). Nhưng setup lỗi ở frontmatter, date, hay URL config có thể làm toàn bộ navigation vỡ — và lỗi sẽ chỉ hiện khi build production.

Bài này dùng một trường hợp thực tế từ dự án Zola để giải thích cách debug, root cause, và cách fix. Nếu bạn cũng dùng Zola hoặc static site generator tương tự, bài này sẽ giúp bạn tránh sai lầm tương tự.

<!-- more -->

## Vấn đề: CI báo "11 broken hrefs" trong series 6 bài

Khi triển khai một series gồm 6 bài về "Google Preferred Sources", tất cả content đã viết xong, slug đã setup, file markdown đã commit lên repository. Build local chạy tốt, nhưng khi CI chạy trên remote, nó báo lỗi lạ:

```
FAIL: 11 bad href(s) in 6 file(s)
```

Điều này lạ bởi vì **tất cả 6 bài đều đã tạo xong**, file HTML được sinh đúng, slug đúng. Vậy tại sao link lại "broken"?

### Dấu hiệu

```
FAIL: 11 bad href(s) in 6 file(s)

  public/posting/google-preferred-sources-1-tu-thuat-toi-giao-dien-tim-kiem/index.html
    - /posting/google-preferred-sources-2-dieu-kien-va-giac-nay-hoat-dong/
  
  public/posting/google-preferred-sources-2-dieu-kien-va-giac-nay-hoat-dong/index.html
    - /posting/google-preferred-sources-3-huong-dan-thiet-lap-ky-thuat/
  
  [...còn 9 lỗi tương tự...]
```

**Lúc này, tất cả 6 bài đều đã tạo xong, nội dung có sẵn.** Không có bài nào "thiếu" hay "chưa publish". Vậy tại sao link lại "broken"?

Bằng trực giác, có thể là:
1. URL slug sai?
2. Link prefix sai?
3. Build chưa tạo file?
4. Frontmatter bị xóa?

Tất cả đều cần debug. Bắt đầu từ dấu hiệu hiển thị.

## Root Cause 1: Frontmatter bị thiếu → Series metadata không đúng

### Phát hiện

Khi mở file markdown `google-preferred-sources-1-tu-thuat-toi-giao-dien-tim-kiem.md`, frontmatter chỉ có:

```toml
+++
title = "..."
date = 2026-06-26

[taxonomies]
categories = ["Tất cả"]
tags = ["..."]
[extra]
thumbnail = "..."
sticky = true
+++
```

**Thiếu**:
- `description` (meta description cho Google)
- `seo_keyword` (từ khoá chính)
- `series = "google-preferred-sources"` (label bài làm phần của series)
- `series_part = 1` (đánh số thứ tự)
- `[[extra.faq]]` (FAQ blocks)

Mà **tất cả những field này đều cần thiết** để Zola tìm được bài và liên kết tới template series-nav + series-listing.

### Cách fix

Restore đầy đủ frontmatter:

```toml
+++
title = "..."
description = "Hiểu về Preferred Sources..."
date = 2026-06-21  # ← lưu ý: ngày sẽ sửa sau

[taxonomies]
categories = ["Tất cả", "SEO"]
tags = ["..."]
[extra]
seo_keyword = "google preferred sources"
series = "google-preferred-sources"
series_part = 1
series_total = 6

[[extra.faq]]
q = "Preferred Sources là gì?"
a = "..."
+++
```

**Sau fix này:** SEO QA checker pass, frontmatter hợp lệ.

## Root Cause 2: Tất cả 6 bài cùng ngày → Zola không biết thứ tự

### Phát hiện

Tất cả 6 bài đều có:

```toml
date = 2026-06-26
```

**Tại sao vấn đề?** Zola dùng `date` để sort posts trong section. Nếu 2 bài cùng ngày, Zola không biết bài nào "trước" bài nào "sau" → không tạo được `page.lower` (bài cũ hơn) và `page.higher` (bài mới hơn).

Mà template `page.html` dùng `{{ page.lower.permalink }}` để sinh ra link "Bài trước". Nếu `page.lower = null`, link sẽ missing.

```html
{# page.html #}
{% if page.lower %}
  <a href="{{ page.lower.permalink }}">← Bài trước</a>
{% else %}
  <span>Không có bài trước</span>
{% endif %}
```

### Cách fix

Set **sequential dates** cho từng bài:

```toml
# Part 1
date = 2026-06-21

# Part 2
date = 2026-06-22

# Part 3
date = 2026-06-23

# ... và cứ thế
```

**Tại sao sequential?** Vì người dùng sẽ đọc bài 1 → 2 → 3... Nên ngày phát hành cũng nên 1, 2, 3... Điều này cũng giúp SEO (mỗi bài có ngày riêng biệt trong sitemap).

## Root Cause 3: URL prefix mismatch → Base URL config lỗi

### Phát hiện

Sau khi fix 2 vấn đề trên, CI vẫn báo broken links. Lần này lỗi khác:

```
Internal links checker: FAIL
Bad link: /posting/google-preferred-sources-2-...
```

Mà trong markdown, tất cả link đều là:

```markdown
[Bài tiếp theo](/posting/google-preferred-sources-2-...)
```

**Có `/zola/` prefix, nhưng checker báo missing?**

Vấn đề là: `base_url` trong `config.toml`:

```toml
base_url = "https://seomoney.org"
```

**KHÔNG có `/zola/`.**

Nên khi Zola build:
- Markdown link: `/zola/posting/...` → được render y nguyên vào HTML
- Zola-generated link (từ `page.lower`): `/posting/...` (đi từ base_url)

→ Hai URL không khớp → checker báo xung đột.

### Cách fix

**Option 1:** Đổi base_url (nếu site thực sự ở `/zola/`)

```toml
base_url = "https://seomoney.org/zola"
```

**Option 2:** Xóa `/zola/` từ markdown links (nếu site ở root)

Vì config cho base_url là `https://seomoney.org` (root), nên link phải là:

```markdown
[Bài tiếp theo](/posting/google-preferred-sources-2-...)
```

**Chọn cách nào?** Phụ thuộc vào actual deployment. Nếu:
- Site deploy ở `https://seomoney.org/` (root) → xóa `/zola/`
- Site deploy ở `https://seomoney.org/zola/` → thêm `/zola/` vào base_url

Trong trường hợp này, site deploy ở root → fix: xóa `/zola/` từ markdown.

Cách fix:

```bash
# Loop qua tất cả file series
for file in content/posting/google-preferred-sources-*.md; do
  sed -i 's|/zola/posting/|/posting/|g' "$file"
done
```

## Hệ thống debug Zola series navigation debug toàn diện

Sau khi giải quyết 3 lỗi chính, tôi nhận ra cách debug này có thể áp dụng cho bất kỳ series nào. Dưới đây là checklist hoàn chỉnh để **setup series navigation debug** cho Zola:

### Bước 1: Validate Frontmatter Schema

Trước khi commit, kiểm tra từng file series:

```bash
# Kiểm tra series field tồn tại
grep -l "series = " content/posting/your-series-*.md

# Kiểm tra series_part đầy đủ
for file in content/posting/your-series-*.md; do
  part=$(grep "series_part" "$file" | cut -d= -f2 | tr -d ' "')
  echo "$file: part $part"
done | sort -t: -k2 -n
```

**Các field bắt buộc:**
- `series` — ID của series (dùng để liên kết)
- `series_part` — số thứ tự (1, 2, 3...)
- `series_total` — tổng số bài
- `description` — meta description (50–160 ký tự)
- `date` — **unique và sequential**

### Bước 2: Kiểm tra Date Sorting

Zola sắp xếp posts theo date. Nếu 2 bài cùng ngày, `page.lower` và `page.higher` sẽ undefined:

```bash
# Hiển thị tất cả dates, sắp xếp để dễ phát hiện duplicate
grep "^date = " content/posting/your-series-*.md | sort -t= -k2

# Output mong muốn:
# date = 2026-06-21
# date = 2026-06-22
# date = 2026-06-23
# ... (unique, sequential)
```

Nếu thấy date duplicate, fix ngay:

```bash
# Ví dụ: tất cả bài đều 2026-06-26
# Cần sửa thành 2026-06-21, 22, 23...

sed -i 's/date = 2026-06-26$/date = 2026-06-21/' content/posting/your-series-1-*.md
sed -i 's/date = 2026-06-26$/date = 2026-06-22/' content/posting/your-series-2-*.md
# ... cứ thế
```

### Bước 3: Kiểm tra URL Consistency

Link trong markdown phải khớp với base_url config:

```toml
# config.toml
base_url = "https://seomoney.org"  # KHÔNG có /zola/
```

Thì markdown link phải là:

```markdown
[Bài tiếp theo](/posting/series-2-title/)  # KHÔNG /zola/
```

Kiểm tra:

```bash
# Tìm link chứa /zola/ nếu base_url không có /zola/
grep -r "/posting/" content/posting/your-series-*.md

# Nếu có kết quả, cần fix:
sed -i 's|/zola/posting/|/posting/|g' content/posting/your-series-*.md
```

## Tóm tắt: 3 bước debug

| Bước | Vấn đề | Triệu chứng | Fix |
|------|--------|-----------|-----|
| **1** | Frontmatter thiếu | SEO QA score thấp, series nav không render | Restore `series`, `series_part`, `description`, FAQ |
| **2** | Ngày giống nhau | Zola không sort, `page.lower`/`page.higher` = null | Set sequential dates (21, 22, 23, ..., 26) |
| **3** | URL prefix mismatch | Link checker báo `/posting/...` xung đ突 | Kiểm tra base_url, xóa `/zola/` từ markdown nếu cần |

## Cách debug nhanh hơn — Kiểm tra local trước push

Thay vì chờ CI chạy remote rồi mới phát hiện lỗi (mất 5–10 phút mỗi lần), hãy debug local ngay:

### Workflow debug local (< 1 phút)

**Bước 1: Kiểm tra schema**

**Bước 2: Chạy build local & kiểm tra**

```bash
# 1. Build site local
zola build

# 2. Chạy internal links checker
python3 scripts/check_internal_links.py

# Output mong muốn:
# OK: no internal links missing /zola/ prefix
```

**Bước 3: Kiểm tra template render**

Zola có 2 cách series nav được sinh:
- **Manual links** (trong markdown): bạn viết
- **Auto links** (từ Zola): `page.lower`, `page.higher` được sinh tự động

Cả 2 phải khớp:

```bash
# Kiểm tra HTML được sinh
grep -o 'href="[^"]*google-preferred-sources[^"]*"' public/posting/google-preferred-sources-1-*/index.html

# Output phải có cả:
# href="/posting/google-preferred-sources-2-..."  (manual link)
# href="/posting/google-preferred-sources-..." (auto nav)
```

**Nếu 3 bước trên all pass, series nav sẽ hoạt động perfectly.**

### Tại sao test local quan trọng?

- **Speed**: Local build < 10 giây, remote CI > 5 phút
- **Feedback loop**: Sửa lỗi, test, push — không chờ CI
- **Cost**: Giảm số lần CI chạy → tiết kiệm tài nguyên
- **Debugging**: Log local rõ hơn, dễ trace lỗi

Hầu hết team chỉ chạy `zola build` trước push, nhưng bạn nên chạy thêm:

```bash
# Setup alias để nhanh hơn
alias zola-check="zola build && python3 scripts/check_internal_links.py"

# Mỗi khi thêm bài series:
zola-check
```

## Nguyên nhân gốc rễ & phòng tránh

Tại sao lỗi này xảy ra? Vì thiết kế Zola (và hầu hết static generators) rely vào **metadata consistency**:

- **Frontmatter** là single source of truth cho mỗi bài
- **Date** dùng để sort posts, không có "order" field thay thế
- **base_url** quyết định tất cả absolute links

Khi bất kỳ thành phần nào không khớp nhau → links vỡ. Điều này không phải "bug" của Zola, mà là **expected behavior** khi config sai.

### Phòng tránh lỗi tương tự

**1. Schema validation sớm**

Trước khi add bài mới vào series, kiểm tra:
- Frontmatter fields bắt buộc tồn tại
- Dates không duplicate
- URL format khớp base_url

```bash
# Tự viết script validate frontmatter YAML
python3 -c "
import frontmatter
f = frontmatter.load('content/posting/your-post.md')
assert 'series' in f.metadata, 'Missing series field'
assert 'series_part' in f.metadata, 'Missing series_part'
"
```

**2. CI linting cho frontmatter**

Một số project dùng [frontmatter-linters](https://github.com/topics/frontmatter-linter) để validate YAML structure trước commit. Bạn có thể setup pre-commit hook:

```bash
# .git/hooks/pre-commit
#!/bin/bash
for file in content/posting/*series*.md; do
  python3 validate_series.py "$file" || exit 1
done
```

**3. Test local before push**

```bash
zola build  # Build to public/
python3 scripts/check_internal_links.py  # Check built HTML
```

Nếu local pass, remote cũng pass — không cần CI validate lại.

**4. Documentation rõ ràng**

Thêm guide cho series setup vào `README` hoặc `CONTRIBUTING.md`:

```markdown
## Writing Series

1. Create files: `content/posting/series-name-N-slug.md` (N = 1, 2, 3...)
2. Frontmatter required:
   - date: unique, sequential (YYYY-MM-DD)
   - series: "series-name"
   - series_part: 1, 2, 3...
   - series_total: total number
3. Links: must match base_url config
4. Test: run `zola build && python3 check_internal_links.py` before push
```

## Tài liệu & Nguồn tham khảo

- [Zola Documentation - Content Organization](https://www.getzola.org/documentation/content/overview/) — cách tổ chức section, pagination, sorting
- [Zola Tera Template Variables](https://www.getzola.org/documentation/templates/pages/) — chi tiết về `page.lower`, `page.higher`
- [Static Site Generator Comparison](https://jamstack.org/generators/) — so sánh Zola với Hugo, Jekyll, Astro
- [SEO Best Practices for Multi-Part Content](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls) — Google's guide on series/pagination
- [Internal Linking Strategy](https://www.semrush.com/blog/internal-linking/) — tại sao internal links quan trọng cho SEO

Nếu bạn dùng **Hugo** thay vì Zola, concept vẫn giống — check `hugo config.toml`, `weights`, `.Params` trong templates, và chạy local test trước push.

## Áp dụng vào dự án của bạn

Nếu bạn đang dùng Zola hoặc static site generator tương tự, đây là những bước để tránh lỗi series navigation:

**Ngay lập tức:**
1. Kiểm tra tất cả series hiện tại — có bài nào cùng date không?
2. Chạy `python3 scripts/check_internal_links.py` để phát hiện lỗi
3. Sửa frontmatter theo template bên dưới

**Template frontmatter cho series posts:**

```toml
+++
title = "Series Name: Part N — Subtitle"
description = "50-160 ký tự, chứa keyword, tóm tắt nội dung bài này."
date = 2026-06-21  # UNIQUE, SEQUENTIAL!

[taxonomies]
categories = ["Tất cả", "Category Name"]
tags = ["series-name", "tag1", "tag2"]
[extra]
seo_keyword = "your main keyword"
series = "series-name"
series_part = 1
series_total = 6  # total parts

[[extra.faq]]
q = "Question 1?"
a = "Answer 1..."

[[extra.faq]]
q = "Question 2?"
a = "Answer 2..."
+++
```

**Setup CI/local testing:**

Thêm vào CI pipeline:

```yaml
# .github/workflows/qa.yml
- name: Check internal links
  run: |
    zola build
    python3 scripts/check_internal_links.py
```

Hoặc setup pre-commit hook trên local:

```bash
#!/bin/bash
# .git/hooks/pre-commit
zola build && python3 scripts/check_internal_links.py || exit 1
```

## Kết luận

Debug lỗi internal links trong series navigation không khó — nó chỉ cần **systematic approach** và **local testing**:

1. **Kiểm tra frontmatter** — validate schema
2. **Kiểm tra ngày** — ensure unique, sequential
3. **Kiểm tra URL** — match base_url config
4. **Test local** — trước khi push

Với quy trình này, "11 broken links" → "0 broken links" chỉ trong vài phút, và bạn sẽ tránh được các lỗi tương tự trong tương lai.

---

## Bài viết liên quan

- [Tạo blog với Zola từ A–Z](/posting/tao-blog-voi-zola/) — guide chi tiết cấu trúc và cấu hình Zola
- [Tự động deploy Zola với GitHub Actions](/posting/tu-dong-deploy-zola-github-actions/) — CI/CD cho static site
- [Zola vs Hugo: so sánh chi tiết](/posting/zola-vs-hugo/) — chọn static site generator phù hợp

---

**Lấy bài học này để tránh sai lầm tương tự** — validate schema sớm, test local thường xuyên, và match config giữa code và settings.
