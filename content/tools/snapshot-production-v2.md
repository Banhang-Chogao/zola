+++
title = "Snapshot Production V2"
date = 2026-06-28
description = "Báo cáo nhanh tình trạng deploy, main, dev và production live của SEOMONEY."
template = "snapshot-production-v2.html"
aliases = ["/tools/snapshot-production-v2"]

[extra]
skip_feed = true
noindex = true
+++

Trang snapshot production — hiển thị báo cáo deploy từ data/prod-snapshot.json và data/deploy-monitor.json, được sinh bởi scripts/build_prod_snapshot.py (shortcut `??`). Dữ liệu chỉ đọc, sinh tại build-time; trình duyệt không gọi GitHub API.
