/**
 * Stats page — aggregates browser-local analytics:
 *   localStorage.zola-vitals  → Core Web Vitals samples
 *   localStorage.zola-events  → view/click/full events
 */
(function () {
  const container = document.getElementById("stats-app");
  if (!container) return;

  const THIRTY_DAYS_MS = 30 * 24 * 60 * 60 * 1000;
  const cutoff = Date.now() - THIRTY_DAYS_MS;

  const vitals = loadJSON("zola-vitals", []).filter(
    (s) => s && typeof s.name === "string" && typeof s.value === "number"
  );
  const events = loadJSON("zola-events", []).filter(
    (e) => e && typeof e.ts === "number" && e.ts >= cutoff
  );

  // ===== UTIL =====
  function loadJSON(key, fallback) {
    try {
      const raw = JSON.parse(localStorage.getItem(key) || JSON.stringify(fallback));
      return Array.isArray(raw) ? raw : fallback;
    } catch {
      return fallback;
    }
  }

  function escapeHtml(s) {
    return String(s || "").replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[c])
    );
  }

  function pathFromUrl(url) {
    try {
      return new URL(url, window.location.origin).pathname;
    } catch {
      return String(url || "/");
    }
  }

  function fmtMs(v) {
    if (v == null) return "—";
    if (v < 1000) return Math.round(v) + " ms";
    return (v / 1000).toFixed(2) + " s";
  }

  function fmtCls(v) {
    return (v ?? 0).toFixed(3);
  }

  function fmtWhen(ts) {
    if (!ts) return "—";
    try {
      return new Date(ts).toLocaleString("vi-VN", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return "—";
    }
  }

  // ===== WEB VITALS THRESHOLDS (Google) =====
  const THRESHOLDS = {
    LCP: [2500, 4000],
    FCP: [1800, 3000],
    INP: [200, 500],
    TTFB: [800, 1800],
    CLS: [0.1, 0.25],
  };

  function rateValue(name, v) {
    if (v == null || !THRESHOLDS[name]) return "unknown";
    const [good, ni] = THRESHOLDS[name];
    if (v <= good) return "good";
    if (v <= ni) return "needs-improvement";
    return "poor";
  }

  function rateLabel(r) {
    return (
      { good: "Tốt", "needs-improvement": "Cần cải thiện", poor: "Kém", unknown: "—" }[r] || r
    );
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

  function distribution(samples, name) {
    const arr = samples.filter((s) => s.name === name).map((s) => s.value);
    const dist = { good: 0, "needs-improvement": 0, poor: 0 };
    arr.forEach((v) => {
      const bucket = rateValue(name, v);
      if (bucket in dist) dist[bucket]++;
    });
    return { total: arr.length, dist };
  }

  function latestTimestamp() {
    const ts = [
      ...vitals.map((s) => s.ts).filter(Boolean),
      ...events.map((e) => e.ts).filter(Boolean),
    ];
    return ts.length ? Math.max(...ts) : null;
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
      ? `<div class="vital-bar" role="img" aria-label="Phân bố ${name}">
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
    const counts = {};
    events
      .filter((e) => e.type === "view")
      .forEach((e) => {
        const path = pathFromUrl(e.url);
        counts[path] = (counts[path] || 0) + 1;
      });
    const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 10);
    if (!sorted.length) {
      return `<p class="stats-empty">Chưa có lượt xem nào được ghi nhận.</p>`;
    }
    return `
      <div class="stats-table-wrap">
        <table class="stats-table">
          <thead><tr><th>#</th><th>Đường dẫn</th><th>Lượt xem</th></tr></thead>
          <tbody>
            ${sorted
              .map(
                (row, i) => `
              <tr>
                <td>${i + 1}</td>
                <td><a href="${escapeHtml(row[0])}"><code>${escapeHtml(row[0])}</code></a></td>
                <td><strong>${row[1]}</strong></td>
              </tr>
            `
              )
              .join("")}
          </tbody>
        </table>
      </div>
    `;
  }

  function renderActivityChart() {
    const now = Date.now();
    const ONE_HOUR = 3600000;
    const buckets = new Array(24).fill(0);
    events.forEach((e) => {
      const hoursAgo = Math.floor((now - e.ts) / ONE_HOUR);
      if (hoursAgo >= 0 && hoursAgo < 24) buckets[23 - hoursAgo]++;
    });
    const max = Math.max(...buckets, 1);
    return `
      <div class="activity-chart" role="img" aria-label="Hoạt động 24 giờ gần đây">
        <div class="activity-chart__gridlines" aria-hidden="true"></div>
        <div class="activity-chart__bars">
          ${buckets
            .map((v, i) => {
              const hoursAgo = 23 - i;
              const showLabel = hoursAgo % 3 === 0 || hoursAgo === 23;
              return `
            <div class="activity-bar" title="${v} event ${hoursAgo}h trước">
              <div class="activity-bar__fill" style="height: ${(v / max) * 100}%"></div>
              <span class="activity-bar__label${showLabel ? "" : " activity-bar__label--hidden"}">${hoursAgo}h</span>
            </div>
          `;
            })
            .join("")}
        </div>
      </div>
    `;
  }

  function renderEventTypes() {
    const typeCounts = {};
    events.forEach((e) => {
      typeCounts[e.type] = (typeCounts[e.type] || 0) + 1;
    });
    const types = ["click", "view", "full"];
    return `
      <div class="event-types">
        ${types
          .map(
            (t) => `
          <div class="event-type event-type--${t}">
            <div class="event-type__count">${typeCounts[t] || 0}</div>
            <div class="event-type__label">${t === "click" ? "Click" : t === "view" ? "Xem" : "Đọc hết"}</div>
          </div>
        `
          )
          .join("")}
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

  const lastUpdated = latestTimestamp();

  // ===== RENDER =====
  container.innerHTML = `
    <p class="stats-meta" aria-live="polite">
      Cập nhật lần cuối: <time datetime="${lastUpdated || ""}">${fmtWhen(lastUpdated)}</time>
      · Cửa sổ dữ liệu: 30 ngày
    </p>

    <section class="stats-section">
      <h2 class="stats-heading">Tổng quan</h2>
      ${renderSummary()}
    </section>

    <section class="stats-section">
      <h2 class="stats-heading">Speed Insights — Core Web Vitals</h2>
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
      <h2 class="stats-heading">Hoạt động 24h gần đây</h2>
      ${renderActivityChart()}
    </section>

    <section class="stats-section stats-section--split">
      <div class="stats-panel">
        <h2 class="stats-heading">Phân loại event</h2>
        ${renderEventTypes()}
      </div>
      <div class="stats-panel">
        <h2 class="stats-heading">Top trang xem nhiều</h2>
        ${renderTopPages()}
      </div>
    </section>

    <section class="stats-section stats-section--manage">
      <h2 class="stats-heading">Quản lý dữ liệu</h2>
      <p class="stats-help">
        Dữ liệu chỉ lưu ở localStorage của trình duyệt này (per-visitor).
        Truy cập trang khác hoặc clear browser data sẽ mất.
      </p>
      <button type="button" class="stats-btn stats-btn--danger" id="clear-stats">Xoá toàn bộ dữ liệu thống kê</button>
    </section>
  `;

  document.getElementById("clear-stats")?.addEventListener("click", () => {
    if (!confirm("Xoá toàn bộ Web Vitals + events khỏi browser này?")) return;
    localStorage.removeItem("zola-vitals");
    localStorage.removeItem("zola-events");
    location.reload();
  });
})();