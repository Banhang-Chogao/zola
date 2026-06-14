+++
title = "Bật syntax highlighting cho code block trong Zola"
date = 2026-06-06
aliases = ["/syntax-highlight/"]

[taxonomies]
categories = ["Posting"]
tags = ["zola", "syntax", "highlight"]

[extra]
thumbnail = "https://picsum.photos/seed/syntax/600/400"
+++

Zola tích hợp sẵn syntax highlighter Syntect. Bật bằng cách thêm vào config.

<!-- more -->

```toml
[markdown]
highlight_code = true
highlight_theme = "base16-ocean-dark"
```

Theme tuỳ chỉnh có thể thêm qua `extra_syntaxes_and_themes`.
