+++
title = "CMS-V2"
date = 2026-06-29
description = "CMS-V2 là lớp điều phối biên tập của SEOMONEY: dashboard editorial, composer, homepage preview, SEO lab, internal links, ad map và publish queue."
template = "cms-v2.html"
aliases = ["/tools/cms-v2/"]

[extra]
skip_feed = true
noindex = true
toc = false
+++

CMS-V2 là lớp điều phối biên tập riêng cho SEOMONEY. Trang này chỉ dùng để
soát workflow editorial, không chạm vào homepage production hiện tại.

Mọi draft phải tuân thủ `global-rule-og.md` và `global-rule-writing.md`. Field ảnh
chuẩn UI xuất là `[extra].thumbnail`; resolver cũng nhận `image`, `cover` và
`image_alt`. Nếu ảnh không rõ nguồn/license hoặc không AdSense-safe, chọn internal
fallback. Trước publish phải kiểm tra alt tiếng Việt, nguồn/license ảnh và đủ bốn
section kết bài bắt buộc.
