+++
title = "Blog Heart Beat"
description = "Theo dõi nhịp tim CI/CD của blog: PR, GitHub Actions, deploy và trạng thái workflow gần thời gian thực."
template = "page.html"

[taxonomies]
categories = ["Tất cả", "Công nghệ"]

[extra]
s_dna = true
tool = true
+++

<link rel="stylesheet" href="/css/blog-heartbeat.css">

<section class="bhb-page" data-blog-heartbeat>
  <header class="bhb-hero">
    <div class="bhb-mark">S</div>
    <div>
      <p class="bhb-kicker">S-DNA · CI/CD MONITOR</p>
      <h1>Blog Heart Beat</h1>
      <p class="bhb-subtitle">
        Theo dõi nhịp tim vận hành của SEOMONEY: PR, workflow, deploy và trạng thái WebOps gần thời gian thực.
      </p>
    </div>
    <div class="bhb-status-pill" id="bhb-status-pill">syncing</div>
  </header>

  <section class="bhb-terminal-card">
    <div class="bhb-terminal-top">
      <span class="bhb-dot bhb-dot-red"></span>
      <span class="bhb-dot bhb-dot-yellow"></span>
      <span class="bhb-dot bhb-dot-green"></span>
      <span class="bhb-terminal-title">blog-heart-beat@github-actions</span>
    </div>

    <div class="bhb-terminal-body">
      <p id="bhb-summary">Đang tải Blog Heart Beat…</p>
      <pre id="bhb-table" aria-live="polite">Loading...</pre>
    </div>

    <footer class="bhb-terminal-footer">
      <a href="https://github.com/Banhang-Chogao/zola/actions" target="_blank" rel="noopener">
        Xem GitHub Actions →
      </a>
      <span id="bhb-refresh-note">Auto-refresh 15s</span>
    </footer>
  </section>

  <section class="bhb-grid">
    <article class="bhb-panel">
      <h2>Current PRs</h2>
      <div id="bhb-prs">Đang tải…</div>
    </article>

    <article class="bhb-panel">
      <h2>Deploy Main</h2>
      <div id="bhb-deploys">Đang tải…</div>
    </article>
  </section>
</section>

<script src="/js/blog-heartbeat.js" defer></script>
