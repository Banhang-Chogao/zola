+++
title = "Tạo RSS feed cho blog Zola không cần plugin"
date = 2026-06-04
aliases = ["/rss-feed/"]

[taxonomies]
categories = ["Posting"]
tags = ["rss", "zola"]
[extra]
thumbnail = "https://picsum.photos/seed/rss/600/400"
+++

Zola hỗ trợ RSS sẵn — chỉ cần bật `generate_feeds = true`.

<!-- more -->

```toml
generate_feeds = true
feed_filenames = ["rss.xml"]
```

Feed sẽ xuất hiện ở `https://yoursite.com/rss.xml`, sẵn sàng cho mọi RSS reader.
