+++
title = "Template engine Tera trong Zola: dùng sao cho đúng"
date = 2026-06-09

[taxonomies]
categories = ["Posting"]
tags = ["zola", "tera", "template"]

[extra]
thumbnail = "https://picsum.photos/seed/tera/600/400"
+++

Tera là template engine mặc định trong Zola, cú pháp gần giống Jinja2 của Python.

<!-- more -->

Tera hỗ trợ:

- **Filter**: `{{ name | upper }}`, `{{ posts | length }}`
- **Block**: `{% block content %}{% endblock %}`
- **Macro**: tái sử dụng UI snippet
- **For loop**: `{% for post in section.pages %}`

Trong Zola, template được đặt ở `templates/` và có 3 file chính: `index.html`, `section.html`, `page.html`.
