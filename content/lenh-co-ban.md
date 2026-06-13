+++
title = "Các lệnh cơ bản của Zola"
date = 2026-06-10

[taxonomies]
categories = ["Hướng dẫn"]
tags = ["zola", "CLI"]
+++

Zola chỉ có vài lệnh chính, dễ nhớ.

<!-- more -->

| Lệnh | Tác dụng |
|---|---|
| `zola init <thư-mục>` | Khởi tạo project mới |
| `zola serve` | Chạy dev server, tự reload khi đổi file |
| `zola build` | Build site tĩnh ra thư mục `public/` |
| `zola check` | Kiểm tra liên kết nội bộ + cấu hình mà không build |

Khi deploy lên production, chỉ cần chạy `zola build` rồi serve thư mục `public/` qua bất kỳ web server tĩnh nào.
