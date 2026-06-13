/**
 * Trang Thống kê — tổng hợp data từ:
 *   localStorage.zola-vitals  → Core Web Vitals samples
 *   localStorage.zola-events  → view/click/full events
 */
(function () {
  const container = document.getElementById("stats-app");
  if (!container) return;

  const vitals = loadJSON("zola-vitals", []);
  const events = loadJSON("zola-events", []);

  // ===== UTIL =====
  function loadJSON(key, fallback) {
    try { return JSON.parse(localStorage.getItem(key) || JSON.stringify(fallback)); }
    catch { return fallback; }
  }

  function escapeHtml(s) {
    return String(s || "").replace(/[&<>"']/g, (c) =>
      ({ "&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;" }[c])
    );
  }

  function fmtMs(v) {
    if (v == null) return "—";
    if (v < 1000) return Math.round(v) + " ms";
    return (v / 1000).toFixed(2) + " s";
  }

  function fmtCls(v) {
    return (v ?? 0).toFixed(3);
  }

  // ===== WEB VITALS THRESHOLDS (Google's) =====
  // [good, needs-improvement] (units ms unless CLS which is unitless)
  const THRESHOLDS = {
    LCP:  [2500, 4000],
    FCP:  [1800, 3000],
    INP:  [200, 500],
    TTFB: [800, 1800],
    CLS:  [0.1, 0.25],
  };

  function rateValue(name, v) {
    if (v == null || !THRESHOLDS[name]) return "unknown";
    const [good, ni] = THRESHOLDS[name];
    if (v <= good) return "good";
    if (v <= ni) return "needs-improvement";
    return "poor";
  }

  function rateLabel(r) {
    return ({ good: "Tốt", "needs-improvement": "Cần cải thiện", poor: "Kém", unknown: "—" }[r] || r);
  }

  // ===== AGGREGATE =====
  function avg(arr) {
    if (!arr.length) return null;
    return arr.reduce((s, v) => s + v, 0) / arr.length;
  }

  function median(arr) {
    if (!arr.length) return null;
    const sorted = [...arr].sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
  }

  function p75(arr) {
    if (!arr.length) return null;
    const sorted = [...arr].sort((a, b) => a - b);
    return sorted[Math.floor(sorted.length * 0.75)];
  }

  function groupByName(samples) {
    const out = {};
    samples.forEach((s) => {
      out[s.name] = out[s.name] || [];
      out[s.name].push(s.value);
    });
    return out;
  }

  function distribution(samples, name) {
    const arr = samples.filter((s) => s.name === name).map((s) => s.value);
    const dist = { good: 0, "needs-improvement": 0, poor: 0 };
    arr.forEach((v) => {
      dist[rateValue(name, v)]++;
    });
    return { total: arr.length, dist };
  }

  // ===== RENDERERS =====
  function renderVitalCard(name) {
    const samples = vitals.filter((s) => s.name === name).map((s) => s.value);
    const fmt = name === "CLS" ? fmtCls : fmtMs;
    const p75v = p75(samples);
    const rating = rateValue(name, p75v);
    const dist = distribution(vitals, name);
    const total = dist.total;

    const bar = total
      ? `<div class="vital-bar">
          ${dist.dist.good ? `<div class="vital-bar__seg vital-bar__seg--good" style="flex: ${dist.dist.good}" title="Tốt: ${dist.dist.good}"></div>` : ""}
          ${dist.dist["needs-improvement"] ? `<div class="vital-bar__seg vital-bar__seg--ni" style="flex: ${dist.dist["needs-improvement"]}" title="Cần cải thiện: ${dist.dist["needs-improvement"]}"></div>` : ""}
          ${dist.dist.poor ? `<div class="vital-bar__seg vital-bar__seg--poor" style="flex: ${dist.dist.poor}" title="Kém: ${dist.dist.poor}"></div>` : ""}
        </div>`
      : `<div class="vital-bar vital-bar--empty">Chưa có dữ liệu</div>`;

    const [good, ni] = THRESHOLDS[name] || [];

    return `
      <article class="vital-card vital-card--${rating}">
        <div class="vital-card__name">${name}</div>
        <div class="vital-card__value">${fmt(p75v)}</div>
        <div class="vital-card__label">${rateLabel(rating)}</div>
        <div class="vital-card__meta">
          P75 từ <strong>${total}</strong> mẫu<br>
          Median: ${fmt(median(samples))}<br>
          Trung bình: ${fmt(avg(samples))}
        </div>
        ${bar}
        <div class="vital-card__thresholds">
          <span class="vital-th vital-th--good">≤ ${name === "CLS" ? fmtCls(good) : fmtMs(good)}</span>
          <span class="vital-th vital-th--ni">≤ ${name === "CLS" ? fmtCls(ni) : fmtMs(ni)}</span>
          <span class="vital-th vital-th--poor">&gt; ${name === "CLS" ? fmtCls(ni) : fmtMs(ni)}</span>
        </div>
      </article>
    `;
  }

  function renderTopPages() {
    // Aggregate views per path from zola-events
    const counts = {};
    events.filter((e) => e.type === "view").forEach((e) => {
      const path = new URL(e.url).pathname;
      counts[path] = (counts[path] || 0) + 1;
    });
    const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 10);
    if (!sorted.length) return `<p class="stats-empty">Chưa có lượt xem nào được ghi nhận.</p>`;
    return `
      <table class="stats-table">
        <thead><tr><th>#</th><th>Đường dẫn</th><th>Lượt xem</th></tr></thead>
        <tbody>
          ${sorted.map((row, i) => `
            <tr>
              <td>${i + 1}</td>
              <td><a href="${escapeHtml(row[0])}"><code>${escapeHtml(row[0])}</code></a></td>
              <td><strong>${row[1]}</strong></td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    `;
  }

  function renderActivityChart() {
    // Hourly histogram for last 24h
    const now = Date.now();
    const ONE_HOUR = 3600000;
    const buckets = new Array(24).fill(0);
    events.forEach((e) => {
      const hoursAgo = Math.floor((now - e.ts) / ONE_HOUR);
      if (hoursAgo >= 0 && hoursAgo < 24) buckets[23 - hoursAgo]++;
    });
    const max = Math.max(...buckets, 1);
    return `
      <div class="activity-chart">
        ${buckets.map((v, i) => `
          <div class="activity-bar" title="${v} event ${23 - i}h trước">
            <div class="activity-bar__fill" style="height: ${(v / max) * 100}%"></div>
            <span class="activity-bar__label">${23 - i}h</span>
          </div>
        `).join("")}
      </div>
    `;
  }

  function renderEventTypes() {
    const typeCounts = {};
    events.forEach((e) => { typeCounts[e.type] = (typeCounts[e.type] || 0) + 1; });
    const types = ["click", "view", "full"];
    return `
      <div class="event-types">
        ${types.map((t) => `
          <div class="event-type event-type--${t}">
            <div class="event-type__count">${typeCounts[t] || 0}</div>
            <div class="event-type__label">${t === "click" ? "Click" : t === "view" ? "Xem" : "Đọc hết"}</div>
          </div>
        `).join("")}
      </div>
    `;
  }

  function renderSummary() {
    return `
      <div class="stats-summary">
        <div class="summary-card">
          <div class="summary-card__value">${vitals.length}</div>
          <div class="summary-card__label">Mẫu Web Vitals</div>
        </div>
        <div class="summary-card">
          <div class="summary-card__value">${events.length}</div>
          <div class="summary-card__label">Event tổng</div>
        </div>
        <div class="summary-card">
          <div class="summary-card__value">${events.filter((e) => e.type === "view").length}</div>
          <div class="summary-card__label">Lượt xem</div>
        </div>
        <div class="summary-card">
          <div class="summary-card__value">${new Set(events.map((e) => e.url)).size}</div>
          <div class="summary-card__label">Trang khác nhau</div>
        </div>
      </div>
    `;
  }

  // ===== RENDER =====
  container.innerHTML = `
    <section class="stats-section">
      <h3 class="stats-heading">Tổng quan</h3>
      ${renderSummary()}
    </section>

    <section class="stats-section">
      <h3 class="stats-heading">⚡ Speed Insights — Core Web Vitals</h3>
      <p class="stats-help">
        Đo trực tiếp trên trình duyệt này theo
        <a href="https://web.dev/vitals/" target="_blank" rel="noopener">chuẩn Google Web Vitals</a>.
        Giá trị hiển thị là <strong>P75</strong> (percentile thứ 75) — Google dùng P75 để xếp hạng PageSpeed.
      </p>
      <div class="vitals-grid">
        ${["LCP", "FCP", "INP", "TTFB", "CLS"].map(renderVitalCard).join("")}
      </div>
    </section>

    <section class="stats-section">
      <h3 class="stats-heading">📈 Hoạt động 24h gần đây</h3>
      ${renderActivityChart()}
    </section>

    <section class="stats-section">
      <h3 class="stats-heading">🎯 Phân loại event</h3>
      ${renderEventTypes()}
    </section>

    <section class="stats-section">
      <h3 class="stats-heading">🔥 Top trang xem nhiều</h3>
      ${renderTopPages()}
    </section>

    <section class="stats-section">
      <h3 class="stats-heading">⚙ Quản lý dữ liệu</h3>
      <p class="stats-help">
        Dữ liệu chỉ lưu ở localStorage của trình duyệt này (per-visitor).
        Truy cập trang khác hoặc clear browser data sẽ mất.
      </p>
      <button class="editor-btn editor-btn--danger" id="clear-stats">🗑 Xoá toàn bộ dữ liệu thống kê</button>
    </section>
  `;

  document.getElementById("clear-stats")?.addEventListener("click", () => {
    if (!confirm("Xoá toàn bộ Web Vitals + events khỏi browser này?")) return;
    localStorage.removeItem("zola-vitals");
    localStorage.removeItem("zola-events");
    location.reload();
  });
})();
