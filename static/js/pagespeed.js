/**
 * Google PageSpeed Insights loader
 * API: https://developers.google.com/speed/docs/insights/v5/get-started
 *
 * Free, 25K req/day, CORS native, không cần key.
 * Cache 1h trong localStorage để giảm tải.
 */
(function () {
  const TARGET_URL = "https://banhang-chogao.github.io/zola/";
  const STRATEGY = "mobile"; // hoặc "desktop"
  const CACHE_KEY = "zola-pagespeed";
  const CACHE_TTL = 60 * 60 * 1000; // 1h

  const apiUrl =
    "https://www.googleapis.com/pagespeedonline/v5/runPagespeed" +
    "?url=" + encodeURIComponent(TARGET_URL) +
    "&strategy=" + STRATEGY +
    "&category=performance&category=accessibility&category=best-practices&category=seo";

  // ===== UTIL =====
  function $(s) { return document.querySelector(s); }
  function escapeHtml(s) {
    return String(s || "").replace(/[&<>"']/g, (c) =>
      ({ "&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;" }[c])
    );
  }

  function formatTime(d) {
    const pad = (n) => (n < 10 ? "0" + n : "" + n);
    return pad(d.getHours()) + ":" + pad(d.getMinutes()) + ":" + pad(d.getSeconds()) +
      " " + pad(d.getDate()) + "/" + (d.getMonth() + 1) + "/" + d.getFullYear();
  }

  function scoreColor(score) {
    if (score == null) return "unknown";
    if (score >= 0.9) return "good";
    if (score >= 0.5) return "ni";
    return "poor";
  }

  // ===== CACHE =====
  function loadCache() {
    try {
      const raw = localStorage.getItem(CACHE_KEY);
      if (!raw) return null;
      const data = JSON.parse(raw);
      if (Date.now() - data.ts > CACHE_TTL) return null;
      return data;
    } catch { return null; }
  }
  function saveCache(payload) {
    try {
      localStorage.setItem(CACHE_KEY, JSON.stringify({ ts: Date.now(), payload }));
    } catch {}
  }

  // ===== RENDER =====
  function renderScores(cats, fetchedAt) {
    const order = [
      { key: "performance",    label: "Hiệu suất",       cls: "perf" },
      { key: "accessibility",  label: "Truy cập",        cls: "a11y" },
      { key: "best-practices", label: "Best Practices",  cls: "best" },
      { key: "seo",            label: "SEO",             cls: "seo" },
    ];
    const html = order.map((c) => {
      const score = cats[c.key] ? Math.round(cats[c.key].score * 100) : null;
      const color = score >= 90 ? "good" : score >= 50 ? "ni" : "poor";
      const pct = score || 0;
      const circ = 2 * Math.PI * 36; // r=36
      const offset = circ - (pct / 100) * circ;
      return `
        <div class="ps-score ps-score--${color}">
          <svg class="ps-score__svg" viewBox="0 0 80 80">
            <circle cx="40" cy="40" r="36" class="ps-score__track"></circle>
            <circle cx="40" cy="40" r="36" class="ps-score__progress"
                    stroke-dasharray="${circ}" stroke-dashoffset="${offset}"></circle>
          </svg>
          <div class="ps-score__value">${score ?? "—"}</div>
          <div class="ps-score__label ps-score__label--${c.cls}">${c.label}</div>
        </div>
      `;
    }).join("");

    $("[data-target='ps-scores']").innerHTML = `
      <div class="ps-scores-row">${html}</div>
      <div class="ps-legend">
        <span class="ps-legend__item"><span class="ps-dot ps-dot--poor"></span> 0–49</span>
        <span class="ps-legend__item"><span class="ps-dot ps-dot--ni"></span> 50–89</span>
        <span class="ps-legend__item"><span class="ps-dot ps-dot--good"></span> 90–100</span>
      </div>
      <p class="ps-fetched">Lighthouse via PageSpeed API · ${formatTime(new Date(fetchedAt))}</p>
    `;
  }

  function renderMetrics(audits) {
    const order = [
      { key: "first-contentful-paint",   label: "First Contentful Paint" },
      { key: "largest-contentful-paint", label: "Largest Contentful Paint" },
      { key: "total-blocking-time",      label: "Total Blocking Time" },
      { key: "cumulative-layout-shift",  label: "Cumulative Layout Shift" },
      { key: "speed-index",              label: "Speed Index" },
      { key: "interactive",              label: "Time to Interactive" },
    ];
    const html = order.map((m) => {
      const a = audits[m.key];
      if (!a) return "";
      const color = scoreColor(a.score);
      return `
        <div class="ps-metric ps-metric--${color}">
          <div class="ps-metric__label">
            <span class="ps-dot ps-dot--${color}"></span>
            ${m.label.toUpperCase()}
          </div>
          <div class="ps-metric__value">${escapeHtml(a.displayValue || "—")}</div>
        </div>
      `;
    }).join("");

    const target = $("[data-target='ps-metrics']");
    target.hidden = false;
    target.innerHTML = html;
  }

  function renderAudits(audits, allRefs, container, type) {
    // Lọc audit theo type (opportunity vs diagnostic) và chỉ lấy những cái có issue
    const items = allRefs
      .map((r) => audits[r.id])
      .filter((a) => a && a.score !== null && a.score < 1)
      .filter((a) => {
        const isOpportunity = a.details && a.details.type === "opportunity";
        return type === "opportunity" ? isOpportunity : !isOpportunity;
      })
      .sort((a, b) => (a.score || 0) - (b.score || 0))
      .slice(0, 10);

    if (!items.length) {
      container.innerHTML = '<li class="ps-audit-empty">✓ Không có vấn đề nào.</li>';
      return;
    }

    container.innerHTML = items.map((a) => {
      const color = scoreColor(a.score);
      const savings = a.details && a.details.overallSavingsMs
        ? `<span class="ps-saving ps-saving--time">−${(a.details.overallSavingsMs / 1000).toFixed(1)}s</span>`
        : "";
      const sizeSaving = a.details && a.details.overallSavingsBytes
        ? `<span class="ps-saving ps-saving--size">−${Math.round(a.details.overallSavingsBytes / 1024)} KB</span>`
        : "";

      return `
        <li class="ps-audit ps-audit--${color}">
          <div class="ps-audit__head">
            <span class="ps-dot ps-dot--${color}"></span>
            <strong class="ps-audit__title">${escapeHtml(a.title)}</strong>
            <span class="ps-audit__savings">${savings}${sizeSaving}</span>
          </div>
          <p class="ps-audit__desc">${escapeHtml(a.description || "")}</p>
        </li>
      `;
    }).join("");
  }

  // ===== FETCH =====
  async function run(force) {
    if (!force) {
      const cached = loadCache();
      if (cached) {
        display(cached.payload, cached.ts, "cache");
        return;
      }
    }

    const metaEl = $("[data-ps-meta]");
    metaEl.textContent = "Đang chạy Lighthouse audit…";
    $("[data-action='ps-refresh']").hidden = true;

    try {
      const res = await fetch(apiUrl);
      if (!res.ok) throw new Error("HTTP " + res.status);
      const json = await res.json();
      saveCache(json);
      display(json, Date.now(), "fresh");
    } catch (err) {
      $("[data-target='ps-scores']").innerHTML = `
        <div class="ps-error">
          ✗ Lỗi gọi PageSpeed API: ${escapeHtml(err.message)}<br>
          <small>API có thể đang chậm/maintain. Đợi vài phút thử lại.</small>
        </div>
      `;
    }
  }

  function display(json, fetchedAt, source) {
    const lh = json.lighthouseResult;
    if (!lh) {
      $("[data-target='ps-scores']").innerHTML = '<div class="ps-error">Không có dữ liệu Lighthouse.</div>';
      return;
    }

    const cats = lh.categories;
    const audits = lh.audits;

    renderScores(cats, fetchedAt);
    renderMetrics(audits);

    // Audit refs từ category "performance"
    const perfRefs = (cats.performance && cats.performance.auditRefs) || [];

    const oppContainer = $("[data-target='ps-opportunities']");
    const oppBox = $("[data-target='ps-opportunities-box']");
    renderAudits(audits, perfRefs, oppContainer, "opportunity");
    oppBox.hidden = false;

    const diagContainer = $("[data-target='ps-diagnostics']");
    const diagBox = $("[data-target='ps-diagnostics-box']");
    renderAudits(audits, perfRefs, diagContainer, "diagnostic");
    diagBox.hidden = false;

    const meta = source === "cache"
      ? "Hiển thị bản cached (1h) · cập nhật " + formatTime(new Date(fetchedAt))
      : "Đo bằng Lighthouse " + (lh.lighthouseVersion || "") + " · " + formatTime(new Date(fetchedAt));
    $("[data-ps-meta]").textContent = meta;
    $("[data-action='ps-refresh']").hidden = false;
  }

  $("[data-action='ps-refresh']").addEventListener("click", () => run(true));

  run(false);
})();
