+++
title = "Deploy Zola lên GitHub Pages bằng GitHub Actions"
date = 2026-06-07

[taxonomies]
categories = ["Posting"]
tags = ["zola", "deploy", "github"]

[extra]
thumbnail = "https://picsum.photos/seed/deploy/600/400"
+++

Cách deploy Zola lên GitHub Pages tự động mỗi khi push code.

<!-- more -->

Workflow đơn giản:

```yaml
name: Build and deploy
on:
  push:
    branches: [main]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: zola build
      - uses: actions/deploy-pages@v4
```
