+++
title = "Shortcode trong Zola: nhúng nội dung động vào Markdown"
date = 2026-06-08

[taxonomies]
categories = ["Posting"]
tags = ["zola", "shortcode"]

[extra]
thumbnail = "https://picsum.photos/seed/shortcode/600/400"
+++

Shortcode cho phép nhúng các thành phần phức tạp vào markdown một cách gọn gàng.

<!-- more -->

Ví dụ shortcode `youtube.html`:

```html
<iframe src="https://www.youtube.com/embed/{{ id }}"></iframe>
```

Trong markdown:

```
{{/* youtube(id="abc123") */}}
```
