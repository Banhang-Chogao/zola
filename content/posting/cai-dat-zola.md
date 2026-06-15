+++
title = "Feature: Cài đặt Zola trên các hệ điều hành phổ biến"
date = 2026-06-11
aliases = ["/cai-dat-zola/"]

[taxonomies]
categories = ["Posting"]
tags = ["cài đặt", "zola"]
[extra]
thumbnail = "https://picsum.photos/seed/cai-dat/600/400"
featured = true
+++

Zola được phân phối dưới dạng một file binary duy nhất, không có dependency.
Tải về và bỏ vào `PATH` là dùng được ngay.

<!-- more -->

## HE DIEU HANH LINUX

```bash
curl -sLO https://github.com/getzola/zola/releases/latest/download/zola-v0.20.0-x86_64-unknown-linux-gnu.tar.gz
tar xzf zola-*.tar.gz
sudo mv zola /usr/local/bin/
```

## macOS

```bash
brew install zola
```
