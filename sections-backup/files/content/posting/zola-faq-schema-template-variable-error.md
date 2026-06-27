+++
title = "Fix 'Variable not found' lỗi FAQ schema trong Zola"
description = "Hướng dẫn debug và khắc phục lỗi 'Variable item.q not found' khi render FAQ schema trong Zola. Học cách sử dụng đúng frontmatter fields cho FAQ."
date = 2026-06-27
aliases = ["/zola-faq-schema-template-variable-error/"]
slug = "zola-faq-schema-template-variable-error"

[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["bug-fix", "debug", "faq-schema", "frontmatter", "static-site", "template", "zola"]
[extra]
seo_keyword = "zola faq schema variable not found"
thumbnail = "img/placeholder/placeholder.svg"
toc = true

[[extra.faq]]
q = "Lỗi 'Variable item.q not found' là gì?"
a = "Đây là lỗi khi Zola template (page.html) cố gắng truy cập biến `q` từ FAQ object, nhưng frontmatter của bài sử dụng tên field khác (ví dụ `question` thay vì `q`)."

[[extra.faq]]
q = "Tại sao frontmatter FAQ lại dùng `q` và `a`?"
a = "Zola template sử dụng tên field ngắn `q` (question) và `a` (answer) để tạo FAQPage schema JSON-LD. Tên này được hardcode trong template page.html, nên frontmatter phải khớp đúng."

[[extra.faq]]
q = "Làm sao fix lỗi 'Variable not found' trong Zola?"
a = "Kiểm tra tên field trong frontmatter [[extra.faq]] — phải dùng `q` và `a`, không phải `question`/`answer`. Nếu dùng tên khác, template sẽ báo lỗi 'variable not found'."

[[extra.faq]]
q = "Có thể custom tên field FAQ không?"
a = "Được, nhưng phải sửa cả template page.html để khớp với tên field mới. Cách dễ nhất là tuân theo convention `q`/`a` của Zola để tương thích."

[[extra.faq]]
q = "CI sẽ báo lỗi gì khi FAQ field sai?"
a = "Zola build sẽ báo: 'ERROR Failed to render page' → 'Variable `item.q` not found in context while rendering page.html'. Exit code 1, chặn deploy."

[[extra.faq]]
q = "Làm sao debug template variable errors nhanh?"
a = "Đọc error message từ `zola build` output — nó chỉ ra chính xác variable name và template file. So sánh với frontmatter để tìm tên field sai."
+++

## Giới thiệu: Lỗi Template Variable trong Zola

Khi làm việc với **Zola static site generator**, một trong những lỗi phổ biến nhất là **template variable errors** — khi template cố gắng truy cập một biến không tồn tại hoặc có tên sai. Lỗi này có vẻ đơn giản nhưng có thể làm đỏ CI/CD pipeline nếu không debug kỹ.

Bài viết này sẽ hướng dẫn bạn **cách chẩn đoán và khắc phục** lỗi "Variable not found" trong FAQ schema — một trong những tình huống hay gặp nhất trong Zola.

## Trường hợp thực tế: Zola FAQ schema variable not found error

Khi thêm FAQ schema vào một bài viết Zola, bạn có thể gặp lỗi "variable not found" như thế này:

```
ERROR Failed to render page 'content/posting/example.md'
ERROR Reason: Failed to render 'page.html'
ERROR Reason: Variable `item.q` not found in context while rendering 'page.html'
```

Lỗi này **không liên quan tới bài viết nội dung của bạn** — nó là lỗi **template rendering**, có nghĩa là Zola template đang cố truy cập một biến mà không tìm thấy.

### Nguyên nhân gốc rễ

Vấn đề nằm ở **mismatch giữa tên field trong frontmatter và tên biến mà template mong đợi**. Khi bạn định nghĩa FAQ trong frontmatter như thế này:

```toml
[[extra.faq]]
question = "Câu hỏi của tôi?"
answer = "Câu trả lời của tôi"
```

Nhưng template `page.html` lại mong đợi:

```tera
{% for item in page.extra.faq %}
  <dt>{{ item.q }}</dt>
  <dd>{{ item.a }}</dd>
{% endfor %}
```

Zola sẽ **không tìm thấy** biến `item.q` vì object FAQ chỉ có fields `question` và `answer` — không có `q` và `a`. Kết quả là build fail.

## Cách khắc phục: Sử dụng đúng tên field trong Zola FAQ schema

Zola FAQ schema yêu cầu tên field cụ thể để render đúng. Nếu bạn đang học về template syntax trong Zola, hãy xem thêm [bài viết về Tera template errors](/categories/cong-nghe/) để hiểu rõ hơn về cách Zola xử lý template.

### ❌ Sai — tên field không khớp template

```toml
[[extra.faq]]
question = "Tại sao lại có lỗi?"
answer = "Vì tên field sai"
```

Khi Zola render template và cố truy cập `item.q`, nó sẽ báo:
```
Variable `item.q` not found in context
```

### ✅ Đúng — tên field khớp template

```toml
[[extra.faq]]
q = "Tại sao lại có lỗi?"
a = "Vì tên field sai"
```

Bây giờ template sẽ tìm thấy `item.q` và `item.a` — không còn lỗi.

## Vì sao Zola lại dùng tên field ngắn `q`/`a`?

Tên field ngắn này được chọn vì:

1. **JSON-LD FAQPage schema:** Tên field `q` và `a` được dùng trong [FAQPage schema của Google](https://schema.org/FAQPage) để tạo rich snippets. Zola template sử dụng tên này trực tiếp khi sinh JSON-LD. Xem thêm tài liệu [Zola frontmatter documentation](https://www.getzola.org/documentation/content/page/) để hiểu rõ cách định nghĩa extra fields.

2. **Convention của Zola:** Các theme Zola mặc định sử dụng `q` và `a` — nếu dùng tên khác, bạn phải custom template.

3. **Consistency:** Tất cả các ví dụ và tài liệu Zola đều dùng `q`/`a`, nên dev dễ nhớ và tuân thủ.

## Template rendering trong Zola: Cách nó hoạt động

Để hiểu rõ hơn tại sao lỗi này xảy ra, cần biết **Zola render pages như thế nào**:

```
1. Zola đọc frontmatter: [[extra.faq]] → tạo object { q: "...", a: "..." }
2. Zola truyền object này tới template page.html
3. Template loop qua `page.extra.faq` array
4. Mỗi iteration, template cố truy cập `item.q` và `item.a`
5. Nếu field không tồn tại → "Variable not found" error
```

Điểm quan trọng là **template được hardcode để dùng tên field cụ thể** — bạn không thể dùng tên bất kỳ mà phải khớp với gì template mong đợi.

## Cách debug template variable errors hiệu quả

Khi gặp lỗi "Variable not found", làm theo các bước này:

### Bước 1: Đọc error message kỹ lưỡng

Zola sẽ báo chính xác **variable name**, **template file**, và **dòng lỗi** (nếu có):

```
ERROR Reason: Variable `item.q` not found in context while rendering 'page.html'
```

Từ đây bạn biết:
- Template file: `page.html`
- Variable name: `item.q`
- Object: `item` (từ array loop)

### Bước 2: Tìm nơi template sử dụng biến đó

Mở `templates/page.html` và search `item.q`:

```tera
{% for item in page.extra.faq %}
  <dt>{{ item.q }}</dt>
  <dd>{{ item.a }}</dd>
{% endfor %}
```

Bây giờ bạn biết template **mong đợi** FAQ object có fields `q` và `a`.

### Bước 3: Check frontmatter của bài viết

Xem frontmatter của bài viết lỗi:

```toml
[[extra.faq]]
question = "...?"
answer = "..."
```

So sánh với template — **tên field không khớp**! Template dùng `q` nhưng frontmatter dùng `question`.

### Bước 4: Fix frontmatter

Thay đổi tên field từ `question`/`answer` thành `q`/`a`:

```toml
[[extra.faq]]
q = "...?"
a = "..."
```

### Bước 5: Test build lại

Chạy `zola build` để xác nhận lỗi đã fix:

```bash
zola build
# Output: "Building site..."
# No errors!
```

## Các lỗi template variable khác thường gặp

Ngoài FAQ schema, có nhiều lỗi "variable not found" khác:

| Lỗi | Nguyên nhân | Cách fix |
|-----|-------------|---------|
| `item.slug` not found | Dùng `item.url` thay vì `item.slug` | Check template đúng field name |
| `page.author` not found | Field không tồn tại trong page context | Thêm vào frontmatter hoặc config |
| `section.title` not found | Template dùng trong page context, không section context | Kiểm tra if condition `is_section` trước |
| `item.date` not found | Format date sai hoặc field có tên khác | Dùng `page.date` hoặc field đúng |

## Best practices khi làm việc với FAQ schema

### 1. Luôn kiểm tra template trước khi viết frontmatter

Mở `page.html` hoặc `base.html` và tìm FAQ rendering code:

```bash
grep -n "extra.faq" templates/page.html
```

Xem chính xác tên field mà template dùng.

### 2. Dùng editor validation

Nếu editor của bạn hỗ trợ TOML validation, nó sẽ cảnh báo tên field sai.

### 3. Test build local trước khi push

Luôn chạy `zola build` trên máy local để catch lỗi template trước push:

```bash
zola build  # Exit code 0 = OK, 1 = lỗi
```

### 4. Tuân thủ convention Zola

Dùng tên field **chuẩn của Zola** — `q` và `a` cho FAQ — thay vì tự bịa tên khác.

## Kinh nghiệm từ debugging: Lỗi FAQ schema trong CI/CD

Khi thêm bài viết mới với FAQ schema vào PR:

1. **Local build pass** ✅ — bài viết sạch, lỗi chính tả OK
2. **Push PR** → CI chạy `zola build` 
3. **CI báo đỏ** ❌ — `Variable item.q not found`
4. **Nguyên nhân:** Frontmatter dùng `question`/`answer`, nhưng template mong `q`/`a`
5. **Fix:** Sửa frontmatter, push lại
6. **CI xanh** ✅ — PR merge được

Bài học: **Luôn kiểm tra template trước khi định nghĩa frontmatter fields**.

## Cách test FAQ schema render đúng

Sau khi fix, xác nhận FAQ schema render đúng:

```bash
# Build site
zola build

# Kiểm tra HTML output có FAQ tag
grep -i "faq" public/posting/example/index.html

# Hoặc dùng browser DevTools inspect JSON-LD schema
```

Bạn sẽ thấy JSON-LD FAQPage schema được sinh đúng:

```json
{
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "Câu hỏi của tôi?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Câu trả lời của tôi"
      }
    }
  ]
}
```

## Kết luận: Template variable errors không phải khó

- **Nguyên nhân gốc:** Tên field trong frontmatter không khớp tên biến mà template mong đợi
- **Cách debug:** Đọc error message → tìm template → so sánh tên field → fix frontmatter
- **Best practice:** Kiểm tra template **trước** khi viết frontmatter
- **Convention Zola:** Dùng `q`/`a` cho FAQ schema, không tự bịa tên khác

Bằng cách hiểu rõ cách Zola render template và validate frontmatter, bạn sẽ tránh được những lỗi "variable not found" phiền phức và đẩy PR lên lần đầu tiên mà không lỗi.

Nếu bạn gặp các lỗi template khác, hãy áp dụng quy trình debug tương tự: **đọc error → tìm template → so sánh → fix**.
