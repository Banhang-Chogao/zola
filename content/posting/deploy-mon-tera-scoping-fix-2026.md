+++
title = "Tera Scoping: Why {% set_global %} Fixed DEPLOY-MON Widget"
description = "Template variable scoping fix that enabled deployment monitoring widget across all pages in Zola static site"
date = 2026-06-26
updated = 2026-06-26T01:15:06Z
slug = "tera-scoping-deploy-monitor-fix"
authors = ["Claude"]
draft = false
categories = ["Công nghệ"]
tags = ["zola", "tera", "templates", "deployment", "debugging"]

[extra]
seo_keyword = "Tera template variable scoping Zola set_global"
thumbnail = "/img/deploy-monitor-widget.png"
series = ""
internal_notes = "Technical case study - DEPLOY-MON infrastructure fix from 2026-06-26"
+++

## Widget Failure: Tera Template Variable Scoping Issue

Vừa rồi chúng tôi triển khai DEPLOY-MON widget (deployment monitoring dashboard) trong footer của blog. Widget này hiển thị số lượng deployment đang chờ xử lý trong pipeline. Nhưng lúc deploy lên production, trang chủ bị đỏ — widget không render được. 

**Root cause:** Lỗi **Tera template variable scoping** — cụ thể là sử dụng `{% set %}` thay vì `{% set_global %}` khi khai báo biến dữ liệu. Đây là một chi tiết dễ bị bỏ qua khi làm việc với [Zola static site generator](https://www.getzola.org/), nhưng ảnh hưởng lớn tới maintenance toàn site.

Bài viết này tìm hiểu **Tera template variable scoping** trong Zola, cách nó gây ra vấn đề, và cách dùng `{% set_global %}` để fix.

## Understanding Tera Template Variable Scoping in Zola

Triệu chứng của lỗi variable scoping:
- Footer widget (deploy-monitor) load thành công (API call ok, JSON parse ok)
- Nhưng widget không hiển thị trên bất kỳ trang nào
- Error log: `Variable 'dm' is not defined in context while rendering 'page.html'`
- Lỗi xuất hiện trên các trang: `page.html`, `about.html`, `dien-anh.html`, `nokia-demo.html`

**Tại sao lại như vậy?**

Trong `base.html` (template chính), tôi đặt:

```html
<!-- ❌ WRONG: Local scope -->
{% set dm = load_data(path="data/deploy-monitor.json", required=false) %}
```

Lệnh `{% set %}` trong Tera tạo ra một **local variable** — chỉ tồn tại trong block hiện tại (footer block). Khi Zola render các trang con (như `page.html`, `about.html`), chúng extend `base.html` nhưng không nhận được biến `dm` vì nó không được pass qua context global.

Hệ quả: Bất kỳ template nào cố gọi `dm.pending_count` trong một trang extend từ `base.html` sẽ gặp lỗi "variable không định nghĩa".

## Root Cause Analysis: Tera Variable Scope Rules

Tera có 3 cấp độ scope:

| Scope | Cú pháp | Phạm vi | Ví dụ |
|-------|--------|--------|-------|
| **Local** | `{% set var = value %}` | Block hiện tại + child blocks | Loop body, if block |
| **Global** | `{% set_global var = value %}` | Toàn bộ render context | Pass dữ liệu qua templates |
| **Parent** | Tham số function/macro | Inherited từ parent | Khi gọi macro với tham số |

**Trong case này:**
- `{% set dm = ... %}` ở `base.html` footer block → local scope
- Template con (page.html) extend base.html nhưng KHÔNG thừa kế biến local
- Footer render được (local scope của footer block), nhưng các template khác không thấy `dm`

## Fix: Sử Dụng `{% set_global %}`

```html
<!-- ✅ CORRECT: Global scope -->
{% set_global dm = load_data(path="data/deploy-monitor.json", required=false) %}

<!-- ✅ CORRECT: Safe access with conditional -->
{% if dm and dm.summary and dm.summary.pending_count > 0 %}
  <div class="deploy-monitor">
    <span class="pending-count">{{ dm.summary.pending_count }}</span>
  </div>
{% endif %}
```

`{% set_global %}` làm cho biến `dm` có sẵn toàn bộ render session, kể cả trong các template con và page-specific templates.

## Secondary Issue: JSON Path Mismatch

Sau khi fix scoping, ta phát hiện lỗi thứ hai:

**Triệu chứng:** Undefined key access
```
Template tried to access `dm.pending_count` but data structure has `dm.summary.pending_count`
```

**Root cause:** JSON structure của `deploy-monitor.json` là:
```json
{
  "summary": {
    "pending_count": 5,
    "stale_count": 0
  },
  "queue": [...]
}
```

Nhưng code template gọi `dm.pending_count` (bỏ qua `summary` layer).

**Fix:**
```html
<!-- Correct path traversal -->
{{ dm.summary.pending_count }}
```

## Tertiary Issue: Tera Filter Syntax Limitation

Ban đầu, tôi cố gắng provide a default value:

```html
<!-- ❌ INVALID Tera syntax -->
{% set dm = load_data(...) | default(value={}) %}
```

**Error:** `Tera filter call 'default' does not accept object literals`

**Root cause:** Tera không hỗ trợ passing object/map literals vào filters như `value={}`. 

**Fix:** Sử dụng function parameter thay vì filter:

```html
<!-- ✅ CORRECT -->
{% set_global dm = load_data(path="data/deploy-monitor.json", required=false) %}
```

Tham số `required=false` trả về `null` nếu file không tồn tại, an toàn hơn cố gắng fallback với object literal.

## Impact & Verification

Sau fix:
1. **Widget render**: ✅ Deploy-monitor widget hiển thị trên footer (tất cả trang)
2. **Variable access**: ✅ Template không gặp "undefined variable" error
3. **Build success**: ✅ Zola build pass (không crash khi render page.html, about.html, v.v.)
4. **QA gates**: ✅ Static-checks, qa-check all pass
5. **Production**: ✅ Deploy thành công, widget live trên seomoney.org

## Lessons for Future: Preventing This Pattern

**Vaccine Detector (V-series):**
```python
# Detect: Unscoped template variables loaded at global level
def check_v34_global_template_variables(template_path):
    """
    Flag: {% set var = load_data(...) %} at top-level of base.html
    Should be: {% set_global var = load_data(...) %}
    """
    pass
```

**Checklist khi thêm dữ liệu vào template:**

1. **Scope Level**: Biến này cần dùng ở đâu?
   - Chỉ footer block → `{% set %}` (local)
   - Tất cả trang → `{% set_global %}` (global)
   
2. **Data Structure**: JSON path là gì?
   - Test `jq '.path.to.value' data/file.json` trước khi code
   - Đừng assume nesting depth

3. **Fallback Strategy**: File không tồn tại thì sao?
   - Dùng `load_data(..., required=false)` + conditional render
   - KHÔNG dùng object literal fallback

4. **Template Testing**: Test render trên multiple pages:
   - Base page (index.html)
   - Single article (page.html)
   - Archive (taxonomy.html)
   - Custom pages (about.html)

## Deployment Timeline

- **00:47:30 UTC** — PR #941 merged (fixes applied)
- **00:55:02 UTC** — Deploy started
- **01:15:06 UTC** — Deploy completed, live ✅

Full deployment pipeline:
```
Code → QA ✅ → Auto-merge ✅ → Deploy ✅ → Live ✅
```

## Kết Luận

Tera template variable scoping không phải lỗi lớn, nhưng khi debug nó khó phát hiện vì:
- Widget "vẫn hoạt động" ở footer block
- Lỗi chỉ xuất hiện trên trang con → có thể nhầm là lỗi page-specific
- Không hiển thị trong local dev nếu không test tất cả page types

**Best practice:** Bất cứ khi nào load dữ liệu ở top-level template (`base.html`), sử dụng `{% set_global %}` để đảm bảo toàn site có access. Variable local chỉ dùng trong block-scoped logic (loop, if statement).

Cách fix này giúp DEPLOY-MON widget hoạt động trên toàn site, giúp team dễ dàng track deployment queue mà không cần check GitHub Actions UI.

---

**Tags:** #zola #tera #templates #infrastructure #deployment-monitoring
