+++
title = "Zola responsive layout context detection Tera template"
description = "Giải pháp bền vững cho lỗi template context trong Zola. Hướng dẫn tạo responsive layout 30/70 tối ưu AdSense với context detection an toàn."
date = 2026-06-27
aliases = ["/zola-responsive-layout-context-detection/"]
slug = "zola-responsive-layout-context-detection"

[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["adsense", "responsive-design", "static-site-generator", "template-engine", "tera", "zola"]
[extra]
seo_keyword = "zola responsive layout context detection tera template"
thumbnail = "/img/placeholder/placeholder.svg"
author_note = "Từ lỗi build đến giải pháp kiến trúc bền vững — kinh nghiệm thực tế xây dựng template linh hoạt cho Zola"
+++

## Zola responsive layout context detection Tera template

Khi làm việc với **Zola** (static site generator dựa trên Rust), một trong những thách thức lớn nhất là hiểu rõ **context** khi viết Tera template. Context detection là kỹ thuật giúp template hoạt động linh hoạt với nhiều loại context khác nhau mà không gây lỗi build. Đây là hướng dẫn chi tiết về zola responsive layout context detection trong Tera template engine. Trong bài viết này, mình sẽ chia sẻ hành trình từ lỗi build đến giải pháp kiến trúc bền vững khi xây dựng một layout blog responsive 30/70 tối ưu cho AdSense.

## Vấn đề gốc rễ: Khi template chỉ hoạt động trên một loại context

### Hiện tượng lỗi

Khi phát triển layout blog với sidebar trái (30%) và nội dung chính (70%), mình tạo một template tên `posting-left-sidebar.html` với ý định sử dụng cho section pages (trang danh sách bài viết).

Template này sử dụng các biến Tera như:
```tera
{% block title %}{{ section.title }} — {{ config.title }}{% endblock %}
{% if paginator.current_index == 1 %}...{% endif %}
{% for page in section.pages %}...{% endfor %}
```

Tất cả đều hoạt động tốt khi áp dụng cho **section context** (VD: trang `/posting/`). Nhưng khi cố gắng sử dụng template này cho một **page context** (VD: trang demo có nội dung cụ thể), Zola trả lỗi:

```
Error: Failed to render 'posting-left-sidebar.html'
Template error: Variable `section.title` not found in context
```

### Nguyên nhân

Trong Zola:
- **Section context**: Được truyền khi render trang chỉ mục của một section. Có sẵn các biến như `section`, `paginator`, `section.pages`.
- **Page context**: Được truyền khi render một trang đơn lẻ. Có sẵn biến `page`, nhưng KHÔNG có `section` hay `paginator`.

Template được hardcoded cho section context chỉ, nên khi áp dụng cho page context, mọi tham chiếu đến `section` sẽ gây lỗi.

## Giải pháp sai lầm: Workaround tạm thời

Cách xử lý ban đầu là... đơn giản bỏ đi template assignment từ frontmatter của trang demo:

```yaml
# ❌ Trước (gây lỗi)
template = "posting-left-sidebar.html"

# ✅ Sau (bỏ qua, dùng template mặc định)
# Không khai báo template
```

Cách này **giải quyết lỗi ngay tức khì**, nhưng không **giải quyết vấn đề gốc rễ**. Template vẫn không thể được tái sử dụng linh hoạt. Nếu muốn dùng template này cho page context sau này, sẽ phải sửa lại.

## Giải pháp bền vững: Zola context detection trong Tera template

Thay vì tạo nhiều template cho mỗi context type, tôi quyết định **refactor template duy nhất để nó hiểu cả hai loại context**. Đây là cách tốt nhất để xây dựng [Tera template engine](/categories/cong-nghe/) an toàn cho Zola responsive layout.

### Bước 1: Phát hiện context type

Ở đầu template, thêm logic để xác định context type nào đang được sử dụng:

```tera
{# CONTEXT DETECTION: Handle both page and section contexts #}
{% set is_section = section is defined and section.title is defined %}
{% set is_page = page is defined and page.title is defined %}
```

- Nếu biến `section` tồn tại và có `title`, thì đây là **section context**
- Nếu biến `page` tồn tại và có `title`, thì đây là **page context**

### Bước 2: Tạo biến fallback an toàn

Thay vì trực tiếp sử dụng `section.title` (có thể không tồn tại), tạo biến trung gian có giá trị mặc định:

```tera
{% set display_title = section.title if is_section else (page.title if is_page else "Not Found") %}
{% set current_page_index = paginator.current_index | default(value=1) if is_section else 1 %}
```

- `display_title`: Lấy từ `section.title` nếu là section, từ `page.title` nếu là page
- `current_page_index`: Lấy từ `paginator.current_index` nếu là section, nếu không lấy 1

### Bước 3: Render có điều kiện

Thay vì hiển thị sidebar đầy đủ với pagination cho mọi context, chỉ hiển thị khi là section context:

```tera
<!-- SECTION FEED (Section context) -->
{% if is_section and section.pages %}
    {% for p in section.pages | slice(start=(current_page_index - 1) * 5, end=current_page_index * 5) %}
        <!-- ... render post feed ... -->
    {% endfor %}
{% endif %}

<!-- PAGE CONTENT (Page context) -->
{% if is_page %}
    <article class="left-sidebar-layout__page-content">
        <h1>{{ page.title }}</h1>
        {{ page.content | safe }}
    </article>
{% endif %}
```

### Bước 4: Styling cho cả hai trường hợp

Thêm CSS cho `.left-sidebar-layout__page-content` để đảm bảo page content hiển thị đẹp:

```scss
.left-sidebar-layout__page-content {
    background-color: #fff;
    border-radius: 8px;
    padding: 30px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.left-sidebar-layout__page-content h1 {
    font-size: 28px;
    font-weight: bold;
    color: #333;
    margin: 0 0 20px 0;
}
```

## Lợi ích của giải pháp này

### 1. **Tái sử dụng linh hoạt**
Template có thể được áp dụng cho bất kỳ context type nào mà không gây lỗi build. Không cần tạo nhiều template riêng lẻ.

### 2. **Bền vững về kiến trúc**
Giải pháp này xử lý vấn đề ở **tầng template**, không phải tầng configuration. Nếu muốn thay đổi hành vi sau này, chỉ cần sửa logic trong template, không cần điều chỉnh frontmatter của từng trang.

### 3. **Dễ mở rộng**
Nếu muốn thêm context type mới (VD: archive context, tag context), chỉ cần:
- Thêm điều kiện phát hiện: `{% set is_archive = ... %}`
- Thêm nhánh render tương ứng
- Không cần tạo template mới

### 4. **Giảm duplicate code**
Thay vì có `section.html`, `page.html`, `posting-left-sidebar.html`, `posting-left-sidebar-page.html`, giờ chỉ cần một template thông minh.

## Ứng dụng thực tế: Layout AdSense-safe

Trong trường hợp cụ thể này, template được thiết kế cho **monetization AdSense** với:

- **3 ad spots** cố định: 728×90 (header), 300×250 (sidebar), 728×90 (in-article)
- **Anti-Layout-Shift protection**: Tất cả placeholder có min-height + aspect-ratio cố định
- **Responsive design**: 30/70 grid trên desktop → 1 cột trên mobile
- **Semantic HTML5**: Breadcrumb, ARIA labels, proper heading hierarchy

Layout này **an toàn cho AdSense** vì:
- Không có pop-in, overlay, hoặc animation gây shift
- Placeholder có kích thước cố định, Google AdSense có thể inject ads mà không lo layout shift
- Responsive không làm thay đổi ad placement logic

## Best practices khi viết template Zola

Dựa trên kinh nghiệm này, đây là những best practice khi viết template Zola/Tera:

### 1. **Luôn phát hiện context type**
```tera
{% set is_section = section is defined %}
{% set is_page = page is defined %}
```

### 2. **Sử dụng default filter cho giá trị có thể bị thiếu**
```tera
{{ paginator.current_index | default(value=1) }}
```

### 3. **Tách biệt logic rendering theo context**
```tera
{% if is_section %}
    <!-- Section-specific HTML -->
{% elif is_page %}
    <!-- Page-specific HTML -->
{% endif %}
```

### 4. **Tránh hardcode biến context vào block title/meta**
```tera
{# ❌ Tránh #}
{% block title %}{{ section.title }} | Blog{% endblock %}

{# ✅ Thích hợp #}
{% set page_title = section.title if section else page.title %}
{% block title %}{{ page_title }} | Blog{% endblock %}
```

### 5. **Kiểm tra biến tồn tại trước khi sử dụng**
```tera
{# ❌ Tránh #}
{% if section.pages %}...{% endif %}

{# ✅ Thích hợp #}
{% if section is defined and section.pages %}...{% endif %}
```

## Kiểm chứng và testing

Template được kiểm chứng trên:
- ✅ Desktop (1024px+): Layout 30/70 hiển thị đúng
- ✅ Tablet (768px): Grid collapse thành 1 cột, sidebar pindah xuống
- ✅ Mobile (360-480px): Single column, ad spots scale phù hợp
- ✅ Section context: Pagination hoạt động bình thường
- ✅ Page context: Content hiển thị mà không bị mất context

## Kết luận

Việc thiết kế template **thông minh** không chỉ giải quyết vấn đề hiện tại, mà còn tạo nền tảng vững chắc cho phát triển sau này. Context detection trong Tera không phức tạp nhưng rất hiệu quả để tạo template **tái sử dụng** và **bền vững**.

Nếu bạn đang làm việc với Zola và gặp vấn đề tương tự, tôi khuyên bạn **hãy sử dụng context detection** thay vì tạo nhiều template hoặc dùng workaround tạm thời. Đó là cách hiểu sâu hơn về template engine và xây dựng cơ sở dự án bền vững hơn.

---

## FAQ

**Q: Context detection có ảnh hưởng hiệu suất build không?**
A: Không. Context detection chỉ là `is defined` check tại compile time, không có runtime overhead.

**Q: Có thể dùng context detection cho canonical URL hay og:image không?**
A: Có. Bất kỳ biến nào có thể khác nhau giữa context type đều có thể được bảo vệ bằng context detection.

**Q: Khi nào nên tạo template riêng thay vì dùng context detection?**
A: Nếu layout hoàn toàn khác nhau (VD: gallery vs blog), tạo template riêng có ý nghĩa hơn. Nhưng nếu 80% logic chung, context detection là lựa chọn tốt hơn.

**Q: Zola có cung cấp helper function cho context detection không?**
A: Không, bạn phải tự viết logic `is defined` check. Đó là sự linh hoạt của Tera template language.

---

## Tham khảo & Nguồn

- [Zola Documentation - Templates](https://www.getzola.org/documentation/templates/overview/)
- [Tera Template Language - Conditionals](https://tera.netlify.app/docs/#conditionals)
- [Google AdSense - Layout Shift Guidelines](https://support.google.com/adsense/answer/10734659)
- [Web Vitals - Cumulative Layout Shift](https://web.dev/articles/cls)

Bạn có câu hỏi hay muốn thảo luận thêm về Zola template design? Hãy để lại comment bên dưới hoặc liên hệ qua email.

---

*Bài viết này được viết dựa trên kinh nghiệm thực tế xây dựng blog layout với Zola. Hy vọng nó giúp bạn hiểu sâu hơn về template context và thiết kế template linh hoạt.*
