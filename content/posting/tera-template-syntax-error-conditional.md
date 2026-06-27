+++
title = "Lỗi Tera Template Syntax Error: Cách khắc phục"
description = "Hướng dẫn fix lỗi tera template syntax error khi sử dụng conditional operators. Học cách viết template Tera đúng cách để tránh lỗi build Zola."
date = 2026-06-27
slug = "tera-template-syntax-error-conditional"

[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["tera", "zola", "template", "syntax-error", "debug", "static-site", "web-development"]

[extra]
seo_keyword = "tera template syntax error"
thumbnail = "img/placeholder/placeholder.svg"
toc = true

[[extra.faq]]
q = "Tại sao Tera không hỗ trợ Python ternary operators?"
a = "Tera là template engine độc lập (không phải dịch từ Python). Nó có syntax riêng, khác với Python. Python dùng `a if condition else b`, nhưng Tera không hỗ trợ cú pháp này trong `set` statements."

[[extra.faq]]
q = "Làm sao xử lý conditional logic trong Tera templates?"
a = "Dùng multi-line `if-elif-else` blocks để gán biến. Ví dụ: {% if condition %} {% set var = value1 %} {% elif other %} {% set var = value2 %} {% else %} {% set var = value3 %} {% endif %}"

[[extra.faq]]
q = "Có cách nào viết ternary ngắn gọn trong Tera?"
a = "Tera không hỗ trợ ternary operators. Cách ngắn gọn nhất là dùng filter `default` hoặc logic `if` inline trong text output. Để gán biến thì chỉ có if-elif-else block."

[[extra.faq]]
q = "Sai cú pháp Tera template sẽ báo lỗi gì?"
a = "Zola sẽ báo `Failed to parse template` với thông báo mong muốn operator hoặc filter. Lỗi sẽ chỉ ra dòng và vị trí chính xác gặp sự cố."

[[extra.faq]]
q = "Có thể dùng `or`, `and`, `default` filter thay thế ternary không?"
a = "Có thể dùng `default` filter cho giá trị mặc định: `page.title | default(value=\"Untitled\")`. Nhưng nếu cần logic phức tạp (nested conditions), chỉ có if-elif-else block mới khả dụng."
+++

## Lỗi Tera Template Syntax Error: Nguyên nhân và giải pháp

Khi làm việc với **Zola static site generator**, bạn có thể gặp lỗi build như này, đây là **tera template syntax error** phổ biến:

```
ERROR Failed to parse "/templates/posting-left-sidebar.html"
  --> 11:38
   |
11 | {% set display_title = section.title if is_section else (page.title if is_page else "Not Found") %}
    |                                      ^---
    |
    = expected `or`, `and`, `not`, `<=`, `>=`, `<`, `>`, `==`, `!=`, `+`, `-`, `*`, `/`, `%`, a filter, or `%}` or `-%}`
```

**Lỗi này xảy ra vì:** Tera template engine không hỗ trợ Python-style ternary operators (`a if condition else b`). Đây là lỗi rất hay gặp khi những developer quen với Python cố gắng viết template Zola. Hiểu rõ lỗi này sẽ giúp bạn viết template chính xác và tránh những lỗi build không cần thiết.

## Tại sao lại không hoạt động?

Nếu bạn từng lập trình Python, cú pháp ternary operators rất quen thuộc:

```python
# Python — hoạt động bình thường
value = section.title if is_section else (page.title if is_page else "Not Found")
```

Nhưng **Tera là một template engine độc lập**, có syntax riêng. Nó không phải dịch từ Python, nên cú pháp khác biệt:

- **Python:** `value if condition else default`
- **Tera:** `{% if condition %}value{% else %}default{% endif %}`

Tera được thiết kế để **an toàn** (safe) khi render HTML từ dữ liệu, nên chỉ hỗ trợ một tập hợp operator cụ thể trong `set` statements: `or`, `and`, `not`, các operator so sánh (`==`, `<`, `>`, …), toán học (`+`, `-`, `*`, `/`, `%`), và **filters**.

## Cách khắc phục tera template syntax error: Dùng if-elif-else blocks

Thay vì viết trên 1 dòng, hãy tách ra thành multi-line if-elif-else blocks. Đây là cách **bắt buộc** khi bạn cần gán biến có điều kiện trong Tera:

### ❌ Sai — Python ternary (Tera không hỗ trợ)

```tera
{% set display_title = section.title if is_section else (page.title if is_page else "Not Found") %}
```

Khi viết cách này, Zola sẽ báo lỗi `tera template syntax error` ngay ở vị trí từ khóa `if` bên trong expression.

### ✅ Đúng — Tera if-elif-else blocks

```tera
{% if is_section %}
  {% set display_title = section.title %}
{% elif is_page %}
  {% set display_title = page.title %}
{% else %}
  {% set display_title = "Not Found" %}
{% endif %}
```

Cách này có thể dài hơn, nhưng **clear**, **rõ ràng**, và **Tera hoàn toàn hỗ trợ**. Đây là cách duy nhất để gán biến có điều kiện trong Tera template.

### Tại sao lại phải tách ra?

Tera parser được thiết kế để parse **từ trái sang phải** và chỉ chấp nhận các operator/filter cụ thể trong `set` statement. Khi nó gặp từ khóa `if` mà không phải ở đầu block, nó sẽ báo lỗi vì không biết đó là gì.

## Các cách xử lý conditional khác

### 1. Output trực tiếp (không gán biến)

Nếu chỉ cần in giá trị ra, bạn có thể viết trực tiếp:

```tera
{% if is_section %}
  {{ section.title }}
{% elif is_page %}
  {{ page.title }}
{% else %}
  Not Found
{% endif %}
```

### 2. Dùng filter `default`

Khi chỉ cần giá trị mặc định (không nested conditions), filter `default` tiện hơn:

```tera
{% set display_title = page.title | default(value="Not Found") %}
```

⚠️ **Giới hạn:** `default` chỉ xử lý 1 lần fallback, không hỗ trợ nested conditions như ternary.

### 3. Kết hợp `or` operator (cho simple cases)

Tera hỗ trợ `or` operator, tuy nhiên nó kiểm tra **truthiness**, không phải giá trị rỗng:

```tera
{% set display_title = page.title or section.title or "Not Found" %}
```

Điều này có thể không hoạt động như mong đợi nếu `page.title` là string rỗng (bỏi `""` vẫn thỏa mãn `or`).

## Ví dụ thực tế trong Zola: Xử lý Page và Section Context

Đây là pattern hay gặp khi xử lý cả **page context** và **section context** trong cùng một template. Nó rất phổ biến trong Zola khi bạn muốn dùng một template cho cả page đơn lẻ lẫn section (danh sách bài viết):

```tera
{# Xác định context: page hay section? #}
{% set is_section = section is defined and section.title is defined %}
{% set is_page = page is defined and page.title is defined %}

{# Gán biến theo context #}
{% if is_section %}
  {% set display_title = section.title %}
  {% set items = section.pages %}
{% elif is_page %}
  {% set display_title = page.title %}
  {% set items = [] %}
{% else %}
  {% set display_title = "Not Found" %}
  {% set items = [] %}
{% endif %}

{# Dùng biến đã gán #}
<h1>{{ display_title }}</h1>
{% for item in items %}
  <article>{{ item.title }}</article>
{% endfor %}
```

## Mẹo debug lỗi Tera template

Khi gặp lỗi parse Tera:

1. **Đọc thông báo lỗi kỹ lưỡng** — nó chỉ ra dòng, vị trí, và operator/filter được mong đợi
2. **Kiểm tra syntax Tera** — Tera có syntax khác Python, Jinja2. Tham khảo [docs chính thức](https://keats.github.io/tera/)
3. **Tránh Python operators** — các cú pháp Python như ternary, list comprehension, lambda KHÔNG hoạt động. Những lỗi này thường xảy ra khi bạn từ có kinh nghiệm với backend web development
4. **Dùng if-elif-else cho conditional logic** — đây là cách **bắt buộc** để gán biến có điều kiện
5. **Test build local** — chạy `zola build` trên máy để catch lỗi trước khi push

Nếu bạn đang học về static site generation hoặc tìm hiểu thêm về web development, hãy xem các tài liệu khác trong chuyên mục [Công nghệ](/categories/cong-nghe/) của blog.

## Tránh lỗi phổ biến khác khi viết Tera template

Ngoài tera template syntax error về ternary operators, bạn có thể gặp các lỗi khác:

- **Sai cú pháp filter:** Tera dùng `from=` và `to=` thay vì Python `old=` và `new=` (lỗi hay gặp khi viết filter `replace`)
- **Biến không được định nghĩa:** Kiểm tra xem biến đã được `set` chưa trước khi dùng
- **Sai context:** Dùng `page` khi template đang ở `section` context sẽ gây lỗi

Hiểu rõ các khác biệt giữa Tera và các template engine khác sẽ giúp bạn debug nhanh hơn.

## Kết luận

- **Tera template engines có syntax riêng**, khác biệt với Python và các ngôn ngữ lập trình thông thường
- **Python ternary operators không hoạt động** trong Tera `set` statements — đây là sai lầm phổ biến
- **Giải pháp là dùng if-elif-else blocks** — cách duy nhất để gán biến có điều kiện trong Tera
- Luôn kiểm tra [tài liệu Tera chính thức](https://keats.github.io/tera/) khi làm việc với Zola static site generator
- Test build local với `zola build` để catch lỗi trước khi deploy lên production

Bằng cách hiểu rõ các giới hạn của Tera, bạn sẽ tránh được lỗi syntax thường gặp này và viết template sạch, bền vững hơn. Nếu bạn đang xây dựng static site với Zola, hãy lưu ý các quy tắc này để có trải nghiệm dev mượt mà hơn.
