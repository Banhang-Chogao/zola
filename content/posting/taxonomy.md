+++
title = "Taxonomy: phân loại bài viết với categories và tags"
date = 2026-06-05

[taxonomies]
categories = ["Posting"]
tags = ["zola", "taxonomy"]

[extra]
thumbnail = "https://picsum.photos/seed/taxonomy/600/400"
+++

Taxonomy giúp tổ chức bài viết theo chủ đề và từ khoá.

<!-- more -->

Cấu hình trong `config.toml`:

```toml
taxonomies = [
    {name = "categories", paginate_by = 10},
    {name = "tags", paginate_by = 10},
]
```

Sau đó mỗi bài viết khai báo:

```toml
[taxonomies]
categories = ["Bài viết"]
tags = ["zola"]
```
