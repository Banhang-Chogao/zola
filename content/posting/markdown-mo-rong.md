+++
title = "Markdown mở rộng trong Zola: bảng, footnote, internal link"
date = 2026-06-02
aliases = ["/markdown-mo-rong/"]

[taxonomies]
categories = ["Posting"]
tags = ["zola", "markdown"]

[extra]
thumbnail = "https://picsum.photos/seed/markdown/600/400"
+++

Zola hỗ trợ nhiều cú pháp markdown mở rộng ngoài CommonMark chuẩn.

<!-- more -->

- **Table**: `| col1 | col2 |`
- **Footnote**: `[^1]` và `[^1]: nội dung`
- **Internal link**: `[link](@/post.md)` — kiểm tra link broken lúc build
- **Strikethrough**: `~~chữ gạch ngang~~`
- **Task list**: `- [x] xong` / `- [ ] chưa`
