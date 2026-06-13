+++
title = "Trang chủ"
sort_by = "date"
template = "index.html"
+++

# Chào mừng đến với blog của tôi

Đây là trang chủ của một blog được tạo bằng **Zola** — một static site engine cực kỳ nhanh, gói gọn trong một file binary duy nhất.

## Blog này có gì?

Bên trái là menu chuyên mục. Mọi bài viết, hướng dẫn, ghi chú đều được tổ chức theo cấu trúc thư mục rõ ràng. Hãy chọn một mục bất kỳ để bắt đầu đọc.

> "Quên các dependency đi. Mọi thứ bạn cần đều nằm trong một file binary duy nhất."

## Cấu trúc thư mục

Một site Zola điển hình có cấu trúc như sau:

```
.
├── config.toml
├── content
│   ├── blog
│   │   ├── _index.md
│   │   └── bai-viet-dau-tien.md
│   └── huong-dan
│       ├── _index.md
│       └── cai-dat.md
├── sass
├── static
├── templates
└── themes
```

Mỗi thư mục con của `content/` được Zola gọi là một **section**. File `_index.md` trong mỗi thư mục mô tả cấu hình và nội dung của section đó.
