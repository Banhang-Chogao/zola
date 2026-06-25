+++
title = "Blog Heart Beat"
description = "Bảng theo dõi nhịp tim CI/CD của SEOMONEY: PR, workflow, deploy, elapsed time và trạng thái GitHub Actions."
date = 2026-06-23

[taxonomies]
categories = ["Tất cả", "Công nghệ"]

[extra]
s_dna = true
tool = true
+++

<link rel="stylesheet" href="/css/blog-heartbeat.css">

<section class="bhb-page" data-blog-heartbeat>
  <header class="bhb-hero">
    <div class="bhb-orb">S</div>
    <div>
      <p class="bhb-kicker">S-DNA · CI/CD MONITOR</p>
      <h1>Blog Heart Beat</h1>
      <p class="bhb-subtitle">
        Nhịp tim vận hành của SEOMONEY: PR, GitHub Actions, deploy, elapsed time và tuổi của từng workflow run.
      </p>
    </div>
    <a class="bhb-source" href="https://github.com/Banhang-Chogao/zola/actions" target="_blank" rel="noopener">
      Source Code →
    </a>
  </header>

  <section class="bhb-showcase">
    <div class="bhb-console">
      <div class="bhb-console__top">
        <span class="bhb-dot bhb-dot--red"></span>
        <span class="bhb-dot bhb-dot--yellow"></span>
        <span class="bhb-dot bhb-dot--green"></span>
        <span class="bhb-console__title">blog-heart-beat@github-actions</span>
        <span class="bhb-console__state" data-bhb-state>syncing</span>
      </div>

      <div class="bhb-console__body">
        <div class="bhb-live-row">
          <span class="bhb-chip bhb-chip--green">Hoạt động</span>
          <span class="bhb-chip bhb-chip--purple">GitHub</span>
          <span class="bhb-live-clock" data-bhb-clock>--:--:--</span>
        </div>

        <h2 data-bhb-main-title>Đang tải dữ liệu CI/CD…</h2>
        <p class="bhb-main-desc" data-bhb-main-desc>
          Đang đọc /data/blog-heartbeat.json.
        </p>

        <pre class="bhb-table" data-bhb-table>Loading...</pre>

        <div class="bhb-console__footer">
          <a href="https://github.com/Banhang-Chogao/zola/actions" target="_blank" rel="noopener">
            Xem GitHub Actions →
          </a>
          <span data-bhb-updated>Auto-refresh 15s</span>
        </div>
      </div>
    </div>
  </section>

  <section class="bhb-grid">
    <article class="bhb-panel">
      <p class="bhb-panel__label">Open PRs</p>
      <h2>Pull requests đang mở</h2>
      <div data-bhb-prs>Đang tải…</div>
    </article>

    <article class="bhb-panel">
      <p class="bhb-panel__label">Deploy</p>
      <h2>GitHub Pages / main</h2>
      <div data-bhb-deploys>Đang tải…</div>
    </article>

    <article class="bhb-panel bhb-panel--wide">
      <p class="bhb-panel__label">Terminal command</p>
      <h2>Lệnh local tương ứng</h2>
      <pre class="bhb-code">gh run list --branch "$(git branch --show-current)" --limit 5</pre>
    </article>
  </section>
</section>

<script src="/js/blog-heartbeat.js" defer></script>
