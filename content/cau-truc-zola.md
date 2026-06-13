+++
title = "Hiểu về Section & Page trong Zola"
date = 2026-06-12

[taxonomies]
categories = ["Bài viết"]
tags = ["zola", "kiến thức cơ bản"]
+++

Trong Zola, mọi thư mục bên trong `content/` chứa file `_index.md` được coi là một **section**,
và mọi file `.md` còn lại là một **page**.

<!-- more -->

Section có thể chứa nhiều page hoặc nhiều section con khác (nested section),
giúp bạn tổ chức nội dung theo bất kỳ cách nào mình muốn.

## Ví dụ cấu trúc

```
content/
├── _index.md            # root section
├── blog/
│   ├── _index.md        # section "blog"
│   └── bai-dau-tien.md  # page trong section "blog"
└── about.md             # page trong root section
```

Mỗi section có thể chỉ định `template`, `sort_by`, `paginate_by` riêng trong front matter.
