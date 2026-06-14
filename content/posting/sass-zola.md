+++
title = "MUỐN Dùng Sass/SCSS trong Zola: tự build CSS không cần Node"
date = 2026-06-03

[taxonomies]
categories = ["Posting"]
tags = ["zola", "sass", "css"]

[extra]
thumbnail = "https://picsum.photos/seed/sass/600/400"
featured = true
+++

Zola tích hợp sẵn trình biên dịch Sass — bỏ thư mục `sass/` vào project và bật flag.

<!-- more -->

```toml
compile_sass = true
```

Mọi file `.scss` (không bắt đầu bằng `_`) trong `sass/` sẽ được biên dịch ra CSS cùng cấu trúc thư mục.
File bắt đầu bằng `_` là partial — chỉ được include vào file khác.