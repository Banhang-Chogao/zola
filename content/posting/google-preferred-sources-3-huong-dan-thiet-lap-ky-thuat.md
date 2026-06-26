+++
title = "Setup Guide: Hướng dẫn kỹ thuật Preferred Sources"
description = "5 bước triển khai Preferred Sources trên trang web: code, CTA placement, tracking, và tối ưu hóa."
date = 2026-06-26
aliases = ["/google-preferred-sources-3-huong-dan-thiet-lap-ky-thuat/"]
[taxonomies]
categories = ["Tất cả", "SEO", "Công nghệ"]
tags = ["google search", "preferred sources", "implementation", "html", "javascript"]
[extra]
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
seo_keyword = "preferred sources implementation"
featured = false
series = "google-preferred-sources"
series_part = 3
series_total = 6

[[extra.faq]]
q = "Tôi cần thay đổi gì trên trang web để hỗ trợ Preferred Sources?"
a = "Bạn không cần thay đổi gì trên máy chủ. Tất cả những gì bạn cần là thêm một nút/liên kết hướng người dùng đến google.com/preferences/source?q=YOUR_DOMAIN."

[[extra.faq]]
q = "Tôi nên đặt nút Preferred Sources ở đâu?"
a = "Các vị trí hiệu quả nhất: đầu bài viết (cùng hàng judul), thanh sidebar, trang 'About Us', footer, hoặc modal sau khi tải bài viết xong (popup thân thiện, không spam)."

[[extra.faq]]
q = "Có code template cho WordPress không?"
a = "Có, bài này bao gồm code HTML/CSS/JS thuần (vanilla), cách integrate với WordPress shortcode, và cách tùy chỉnh CSS để match branding của bạn."

[[extra.faq]]
q = "Làm sao để track xem bao nhiêu người bấm nút Preferred Sources?"
a = "Dùng Google Analytics 4 (GA4) với event tracking, hoặc UTM parameter để theo dõi click vào google.com/preferences/source. Bài này bao gồm code tracking đầy đủ."
+++

> 📍 **Google Preferred Sources Series (Bài 3/6)** — Triển khai Preferred Sources trên trang web của bạn theo từng bước.

Bài này cung cấp **hướng dẫn kỹ thuật từng bước** để thêm nút Preferred Sources vào trang web. Không cần thay đổi máy chủ — chỉ cần HTML/CSS/JS đơn giản.

<!-- more -->

## Bước 1: Kiểm tra điều kiện sử dụng

Trước tiên, **xác nhận trang web của bạn đủ điều kiện**:

1. Tên miền của bạn là gì? (ví dụ: `example.com` hoặc `blog.example.com`)
2. Có phải domain-level hay subdomain không? (được ✅)
3. Có phải subdirectory như `example.com/blog` không? (không được ❌)

**Nếu được, tiếp tục. Nếu không, bạn cần cấu hình subdomain riêng** (chẳng hạn `blog.example.com` thay vì `example.com/blog`).

## Bước 2: Tạo đường link Preferred Sources

Google cung cấp URL chuẩn để người dùng chọn trang web của bạn:

```
https://google.com/preferences/source?q=YOUR_DOMAIN
```

**Thay `YOUR_DOMAIN` bằng tên miền thực của bạn**:

| Ví dụ miền | URL đầy đủ |
|-----------|-----------|
| `seomoney.org` | `https://google.com/preferences/source?q=seomoney.org` |
| `blog.seomoney.org` | `https://google.com/preferences/source?q=blog.seomoney.org` |
| `example.com` | `https://google.com/preferences/source?q=example.com` |

**Mẹo**: Bạn có thể tạo **shortcut** hay **redirect** để dễ nhớ:
- `seomoney.org/add-to-google` → redirect đến Google Preferred Sources link
- `seomoney.org/prefer` → shortcut tương tự

## Bước 3: Triển khai nút HTML/CSS/JS

Dưới đây là code hoàn chỉnh để thêm nút Preferred Sources vào trang web.

### Code HTML cơ bản

```html
<!-- Nút Preferred Sources — đặt ở bất kỳ đâu trên trang -->
<div class="preferred-sources-widget">
  <div class="preferred-sources-card">
    <h3 class="preferred-sources-title">
      📌 Thêm vào Preferred Sources
    </h3>
    <p class="preferred-sources-desc">
      Chọn seomoney.org làm nguồn tin ưa thích trong Google Search 
      để nhận bài viết mới trước tiên.
    </p>
    <a 
      href="https://google.com/preferences/source?q=seomoney.org"
      class="preferred-sources-btn"
      target="_blank"
      rel="noopener noreferrer"
      data-tracking-id="preferred-sources-click"
    >
      Thêm vào Preferred Sources →
    </a>
  </div>
</div>
```

### CSS styling (BEM naming)

```css
/* Preferred Sources Widget Styling */
.preferred-sources-widget {
  margin: 2rem 0;
  padding: 0;
}

.preferred-sources-card {
  background: linear-gradient(135deg, #f0f4ff 0%, #e8f1ff 100%);
  border: 2px solid #4285f4;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 4px 12px rgba(66, 133, 244, 0.15);
  transition: all 0.3s ease;
}

.preferred-sources-card:hover {
  box-shadow: 0 8px 24px rgba(66, 133, 244, 0.25);
  transform: translateY(-2px);
}

.preferred-sources-title {
  margin: 0 0 0.75rem 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: #1f2937;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.preferred-sources-desc {
  margin: 0 0 1.25rem 0;
  font-size: 0.95rem;
  line-height: 1.6;
  color: #4b5563;
}

.preferred-sources-btn {
  display: inline-block;
  padding: 0.75rem 1.5rem;
  background: #4285f4;
  color: white;
  text-decoration: none;
  border-radius: 6px;
  font-weight: 600;
  font-size: 0.95rem;
  transition: all 0.2s ease;
  border: none;
  cursor: pointer;
  font-family: inherit;
}

.preferred-sources-btn:hover {
  background: #3367d6;
  transform: scale(1.02);
}

.preferred-sources-btn:active {
  transform: scale(0.98);
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  .preferred-sources-card {
    background: linear-gradient(135deg, #1e2a4a 0%, #253355 100%);
    border-color: #5a9bf5;
  }

  .preferred-sources-title {
    color: #f3f4f6;
  }

  .preferred-sources-desc {
    color: #d1d5db;
  }
}

/* Responsive */
@media (max-width: 640px) {
  .preferred-sources-card {
    padding: 1rem;
  }

  .preferred-sources-title {
    font-size: 1.1rem;
  }

  .preferred-sources-btn {
    display: block;
    width: 100%;
    text-align: center;
  }
}
```

## Bước 4: Thêm tracking với Google Analytics 4

Để theo dõi xem bao nhiêu người bấm nút Preferred Sources, thêm JavaScript tracking:

### Code JavaScript (Google Analytics 4)

```javascript
// Google Analytics 4 Event Tracking — Preferred Sources
(function() {
  'use strict';

  // Đảm bảo gtag có sẵn (Google Analytics 4)
  if (typeof gtag === 'undefined') {
    console.warn('Google Analytics 4 không được load. Tracking sẽ bỏ qua.');
    return;
  }

  // Lấy tất cả nút Preferred Sources
  const preferredSourcesButtons = document.querySelectorAll('[data-tracking-id="preferred-sources-click"]');

  preferredSourcesButtons.forEach(button => {
    button.addEventListener('click', function(event) {
      // Gửi event tới Google Analytics 4
      gtag('event', 'preferred_sources_click', {
        'event_category': 'engagement',
        'event_label': 'preferred_sources_widget',
        'value': 1,
        // Tùy chọn: thêm thông tin tùy chỉnh
        'button_text': this.textContent.trim(),
        'button_location': this.closest('.preferred-sources-widget') ? 'inline' : 'unknown',
        'timestamp': new Date().toISOString()
      });

      // Optional: log vào console (chỉ để debug)
      console.log('Preferred Sources click tracked:', {
        url: this.href,
        domain: 'seomoney.org'
      });
    });
  });

  // Alternative: Track với UTM parameter
  // Nếu bạn muốn track bằng UTM thay vì GA4, dùng:
  /*
  const preferredSourcesButtonsUTM = document.querySelectorAll('[data-utm="preferred-sources"]');
  preferredSourcesButtonsUTM.forEach(button => {
    const domain = button.dataset.domain || 'seomoney.org';
    const baseUrl = `https://google.com/preferences/source?q=${domain}`;
    const utmUrl = `${baseUrl}&utm_source=seomoney.org&utm_medium=preferred_sources&utm_campaign=brand_choice`;
    button.href = utmUrl;
  });
  */
})();
```

### Tích hợp vào template Zola

Nếu bạn dùng **Zola** (như blog này), thêm vào `templates/base.html` hoặc template bài viết:

```html
<!-- Sau <script async src="https://www.googletagmanager.com/gtag/js?id=YOUR_GA_ID"></script> -->
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'YOUR_GA_ID');

  // Preferred Sources tracking
  document.addEventListener('DOMContentLoaded', function() {
    const preferredSourcesButtons = document.querySelectorAll('[data-tracking-id="preferred-sources-click"]');
    preferredSourcesButtons.forEach(button => {
      button.addEventListener('click', function() {
        gtag('event', 'preferred_sources_click', {
          'event_category': 'engagement',
          'event_label': 'preferred_sources',
          'value': 1
        });
      });
    });
  });
</script>
```

### Xem dữ liệu trong Google Analytics 4

1. Vào **Google Analytics 4** → **Reports** → **Engagement**
2. Tìm event **`preferred_sources_click`**
3. Xem số lượng click, tỷ lệ, thời gian…

## Bước 5: Chiến lược CTA & Tối ưu hóa placement

### Vị trí nút hiệu quả nhất

| Vị trí | Pros | Cons |
|-------|------|------|
| **Đầu bài viết** | Người dùng thấy ngay | Có thể spam |
| **Sidebar** | Không làm gián đoạn | Dễ bỏ qua |
| **Footer** | Không xâm phạm | CTR thấp |
| **End of article** | Thích hợp cho E-E-A-T | Người dùng có thể rời trang |
| **Floating button** | Luôn nhìn thấy | Mất điểm UX |
| **Modal sau 30s** | Capture interested users | Có thể spam |

**Khuyến nghị tốt nhất**: 
- **Blog công nghệ**: Đầu bài + sidebar
- **Blog tin tức**: End of article
- **Trang tĩnh (About/Contact)**: Prominent placement (header + footer)

### Copy CTA hiệu quả

Thay vì chỉ "Add to Preferred Sources", hãy dùng copy có giá trị:

```
❌ TRÁNH: "Click here"
✅ TỐTƠN: "Nhận bài viết mới trước tiên trong Google Search"

❌ TRÁNH: "Submit to Google"
✅ TỐTƠN: "📌 Thêm vào Preferred Sources — tôi sẽ viết thêm cho bạn"

❌ TRÁNH: Generic
✅ TỐTƠN: "Muốn bài viết [chủ đề] mới nhất? Chọn seomoney.org"
```

### Chiến lược A/B testing

Thử nhiều cách khác nhau và theo dõi CTR:

```javascript
// A/B test variant tracking
const variant = Math.random() > 0.5 ? 'A' : 'B';
gtag('event', 'preferred_sources_variant_' + variant, {
  'event_category': 'experiment',
  'event_label': 'cta_copy_test'
});
```

Sau 2-4 tuần, chọn variant có CTR cao nhất.

## Bước 6: WordPress shortcode (nếu dùng WordPress)

Nếu trang web của bạn chạy **WordPress**, thêm vào `functions.php`:

```php
<?php
// Preferred Sources Shortcode for WordPress
add_shortcode('preferred_sources', function($atts = []) {
  $domain = isset($atts['domain']) ? sanitize_text_field($atts['domain']) : 'example.com';
  $text = isset($atts['text']) ? sanitize_text_field($atts['text']) : 'Thêm vào Preferred Sources →';
  
  $url = esc_url('https://google.com/preferences/source?q=' . $domain);
  
  ob_start();
  ?>
  <div class="preferred-sources-widget">
    <div class="preferred-sources-card">
      <h3 class="preferred-sources-title">📌 Thêm vào Preferred Sources</h3>
      <p class="preferred-sources-desc">Chọn <?php echo esc_html($domain); ?> làm nguồn tin ưa thích trong Google Search.</p>
      <a href="<?php echo $url; ?>" class="preferred-sources-btn" target="_blank" rel="noopener noreferrer" data-tracking-id="preferred-sources-click">
        <?php echo esc_html($text); ?>
      </a>
    </div>
  </div>
  <?php
  return ob_get_clean();
});
?>
```

**Dùng trong bài viết WordPress:**
```
[preferred_sources domain="example.com" text="Chọn tôi làm Preferred Source"]
```

## Bước 7: Monitor & Optimize

Sau 2-4 tuần triển khai, kiểm tra:

1. **Click rate**: Bao nhiêu người bấm nút?
2. **Conversion**: Bao nhiêu người thực sự chọn Preferred Sources? (Google sẽ công bố số liệu sau)
3. **Bounce**: Có tăng bounce rate khi thêm widget không?
4. **Ranking**: Theo dõi ranking của bạn trong Google Search Console

**Tối ưu hóa**:
- Nếu CTR thấp → thay đổi copy, màu sắc, vị trí
- Nếu CTR cao nhưng conversion thấp → có thể Google chưa sẵn sàng hoặc người dùng không biết cách dùng
- Nếu bounce tăng → di chuyển widget sang chỗ khác hoặc làm nó nhỏ hơn

## Tóm tắt setup

| Bước | Hành động |
|------|---------|
| 1 | Kiểm tra domain-level (✅ domain/subdomain) |
| 2 | Tạo URL Google Preferred Sources: `google.com/preferences/source?q=YOUR_DOMAIN` |
| 3 | Thêm HTML/CSS nút vào trang web (sử dụng code bên trên) |
| 4 | Thêm tracking Google Analytics 4 |
| 5 | Tối ưu placement & copy CTA |
| 6 | Monitor & optimize sau 2-4 tuần |

---

**Bước tiếp theo**: Bài 4 tập trung vào [chiến lược nội dung để tăng lựa chọn Preferred Sources](/google-preferred-sources-4-chien-luoc-noi-dung/).

---

**Tham khảo**:
- [Google Search Documentation](https://developers.google.com/search)
- [Google Analytics 4 Event Tracking](https://support.google.com/analytics/answer/9268042)
