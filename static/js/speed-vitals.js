/**
 * Speed Insights — đo Core Web Vitals cho mọi page load.
 * Dữ liệu lưu localStorage (zola-vitals), display ở /stats/.
 *
 * Metrics:
 *   - LCP  (Largest Contentful Paint)      — tốc độ render element lớn nhất
 *   - FCP  (First Contentful Paint)         — text/img đầu tiên xuất hiện
 *   - INP  (Interaction to Next Paint)      — phản hồi tương tác
 *   - CLS  (Cumulative Layout Shift)        — độ "nhảy" layout (UX score)
 *   - TTFB (Time to First Byte)             — server response speed
 */
(function () {
  const KEY = "zola-vitals";
  const MAX_SAMPLES = 500;

  // Đợi web-vitals lib load xong (CDN có defer)
  function init() {
    if (typeof webVitals === "undefined") {
      setTimeout(init, 300);
      return;
    }

    function load() {
      try { return JSON.parse(localStorage.getItem(KEY) || "[]"); }
      catch { return []; }
    }

    function save(events) {
      if (events.length > MAX_SAMPLES) {
        events = events.slice(-MAX_SAMPLES);
      }
      try { localStorage.setItem(KEY, JSON.stringify(events)); } catch {}
    }

    function record(metric) {
      if (sessionStorage.getItem("zola-no-track") === "1") return;
      const events = load();
      events.push({
        name: metric.name,
        value: Math.round(metric.value * 1000) / 1000,
        rating: metric.rating, // "good" | "needs-improvement" | "poor"
        path: location.pathname,
        ts: Date.now(),
      });
      save(events);
    }

    webVitals.onCLS(record);
    webVitals.onLCP(record);
    webVitals.onFCP(record);
    webVitals.onINP(record);
    webVitals.onTTFB(record);
  }

  init();
})();
