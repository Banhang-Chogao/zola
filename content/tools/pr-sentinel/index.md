+++
title = "PR Sentinel — CI Radar"
description = "Theo dõi toàn bộ Pull Request và trạng thái CI trên một màn hình."
date = 2026-06-21

[taxonomies]
categories = ["Tất cả", "Tiện ích & tài liệu"]
+++

<section class="pr-sentinel" data-pr-sentinel>

  <div class="pr-sentinel-hero">
    <p>SEOMONEY · S-DNA Tools</p>
    <h1>PR Sentinel — CI Radar</h1>
    <p>
      Theo dõi toàn bộ Pull Request, trạng thái CI/CD,
      branch, author và tín hiệu cần xử lý trong một dashboard duy nhất.
    </p>
  </div>

  <div class="pr-sentinel-grid">
    <div class="pr-sentinel-kpi">
      <span>Open PRs</span>
      <strong data-kpi="open">0</strong>
    </div>

    <div class="pr-sentinel-kpi">
      <span>Passing</span>
      <strong data-kpi="passing">0</strong>
    </div>

    <div class="pr-sentinel-kpi">
      <span>Failing</span>
      <strong data-kpi="failing">0</strong>
    </div>

    <div class="pr-sentinel-kpi">
      <span>Pending</span>
      <strong data-kpi="pending">0</strong>
    </div>

    <div class="pr-sentinel-kpi">
      <span>Draft</span>
      <strong data-kpi="draft">0</strong>
    </div>
  </div>

  <div class="pr-sentinel-filters">
    <button class="is-active" data-filter="all">All</button>
    <button data-filter="failure">Failing</button>
    <button data-filter="pending">Pending</button>
    <button data-filter="success">Passing</button>
    <button data-filter="draft">Draft</button>
  </div>

  <div data-pr-list>
    <p class="pr-sentinel-empty">
      Đang tải dữ liệu PR Sentinel...
    </p>
  </div>

</section>

<script src="/js/pr-sentinel.js" defer></script>
