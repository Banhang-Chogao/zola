+++
title = "Cài đặt Zola"
date = 2026-06-11

[taxonomies]
categories = ["Hướng dẫn"]
tags = ["zola", "cài đặt"]
+++

Zola được phân phối dưới dạng một file binary duy nhất, không có dependency.
Tải về và bỏ vào thư mục `PATH` là dùng được ngay.

<!-- more -->

## Cài trên Linux

```bash
curl -sLO https://github.com/getzola/zola/releases/latest/download/zola-v0.20.0-x86_64-unknown-linux-gnu.tar.gz
tar xzf zola-*.tar.gz
sudo mv zola /usr/local/bin/
```

## Cài trên macOS

```bash
brew install zola
```

## Cài trên Windows

Dùng `scoop`:

```powershell
scoop install zola
```

Hoặc tải file `.zip` ở trang releases và giải nén vào thư mục bạn muốn.
