+++
title = "Section & Page trong Zola"
date = 2026-06-12
aliases = ["/cau-truc-zola/"]

[taxonomies]
categories = ["Posting"]
tags = ["zola", "kiến thức cơ bản"]

[extra]
thumbnail = "https://picsum.photos/seed/cau-truc/600/400"
+++

Trong Zola, mọi thư mục bên trong `content/` chứa file `_index.md` được coi là một **section**,
và mọi file `.md` còn lại là một **page**.

<!-- more -->

Section có thể chứa nhiều page hoặc nhiều section con khác, giúp tổ chức nội dung linh hoạt.

```
content/
├── _index.md            # root section
├── blog/
│   ├── _index.md        # section "blog"
│   └── bai-dau-tien.md
└── about.md
```