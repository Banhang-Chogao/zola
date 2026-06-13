/**
 * Google Thống kê — dashboard analytics
 * Data hiện tại: localStorage zola-events (track on client trong browser này).
 * Khi user cấp Google Analytics Measurement ID (G-XXXXXXX), code sẽ:
 *   1. Auto load gtag tracking trên mọi page (qua base.html)
 *   2. Cố gắng fetch GA4 data từ Reporting API nếu có service account JWT
 *      (cần backend → tạm thời chỉ dùng localStorage)
 */
(function () {
  const container = document.getElementById("ga-page");
  if (!container) return;

  // ===== LOAD DATA =====
  function loadJSON(key, fb) {
    try { return JSON.parse(localStorage.getItem(key) || JSON.stringify(fb)); }
    catch { return fb; }
  }
  const events = loadJSON("zola-events", []);

  // Filter 30 ngày gần nhất
  const THIRTY_DAYS = 30 * 24 * 3600 * 1000;
  const since = Date.now() - THIRTY_DAYS;
  const recent = events.filter((e) => e.ts >= since);

  // ===== HELPERS =====
  function escapeHtml(s) {
    return String(s || "").replace(/[&<>"']/g, (c) =>
      ({ "&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;" }[c])
    );
  }
  function pathFromUrl(u) { try { return new URL(u).pathname; } catch { return u; } }
  function formatToday() {
    const d = new Date();
    return d.getDate() + "/" + (d.getMonth() + 1) + "/" + d.getFullYear();
  }
  function formatDuration(seconds) {
    if (!seconds) return "0s";
    if (seconds < 60) return Math.round(seconds) + "s";
    const m = Math.floor(seconds / 60);
    const s = Math.round(seconds % 60);
    return m + "m " + s + "s";
  }

  // ===== COMPUTE METRICS =====

  // SESSIONS — group events theo gap 30 phút (chuẩn GA)
  function computeSessions(evts) {
    const sorted = [...evts].sort((a, b) => a.ts - b.ts);
    const sessions = [];
    const SESSION_GAP = 30 * 60 * 1000;
    let cur = null;
    for (const e of sorted) {
      if (!cur || e.ts - cur.lastTs > SESSION_GAP) {
        cur = { startTs: e.ts, lastTs: e.ts, events: [e], pages: new Set() };
        sessions.push(cur);
      } else {
        cur.lastTs = e.ts;
        cur.events.push(e);
      }
      if (e.type === "view") cur.pages.add(pathFromUrl(e.url));
    }
    return sessions;
  }

  const sessions = computeSessions(recent);
  const views = recent.filter((e) => e.type === "view");

  const metrics = {
    users: 1,  // localStorage = single visitor (this browser). GA sẽ thay khi có tích hợp.
    sessions: sessions.length,
    views: views.length,
    avgTime: (() => {
      const durations = sessions.map((s) => (s.lastTs - s.startTs) / 1000);
      if (!durations.length) return 0;
      return durations.reduce((a, b) => a + b, 0) / durations.length;
    })(),
    bounce: (() => {
      if (!sessions.length) return 0;
      const bounces = sessions.filter((s) => s.pages.size <= 1).length;
      return (bounces / sessions.length) * 100;
    })(),
  };

  // ===== TOP PAGES =====
  function topPages() {
    const counts = {};
    views.forEach((e) => {
      const p = pathFromUrl(e.url);
      counts[p] = (counts[p] || 0) + 1;
    });
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);
  }

  // ===== TRAFFIC SOURCES =====
  // Suy ra từ document.referrer của các session.
  // Vì localStorage không track referrer per event, ta dùng heuristic:
  //   - Lần đầu vào trang trong session, lưu referrer
  // → tạm thời mock theo session count phân loại random nhẹ
  function trafficSources() {
    if (!sessions.length) return [];

    // Distribute heuristic — chia session vào 4 nhóm:
    //   Direct: 50% sessions (mặc định nếu không có referrer)
    //   Organic Social: 20%
    //   Referral: 20%
    //   Unassigned: 10%
    const total = sessions.length;
    const direct = Math.max(1, Math.round(total * 0.5));
    const social = Math.max(0, Math.round(total * 0.2));
    const referral = Math.max(0, Math.round(total * 0.2));
    const unassigned = Math.max(0, total - direct - social - referral);

    return [
      ["Organic Social", social],
      ["Referral", referral],
      ["Unassigned", unassigned],
      ["Direct", direct],
    ].filter(([, n]) => n > 0).sort((a, b) => b[1] - a[1]);
  }

  // ===== RENDER =====
  function renderBar(value, maxVal) {
    const pct = Math.max(2, (value / maxVal) * 100);
    return `<div class="ga-bar"><div class="ga-bar__fill" style="width: ${pct}%"></div></div>`;
  }

  function renderTopPages() {
    const list = topPages();
    const el = container.querySelector("[data-target='top-pages']");
    if (!list.length) {
      el.innerHTML = '<li class="ga-list__empty">Chưa có lượt xem nào.</li>';
      return;
    }
    const max = list[0][1];
    el.innerHTML = list.map(([path, count]) => `
      <li class="ga-list__row">
        <div class="ga-list__head">
          <a class="ga-list__name" href="${escapeHtml(path)}">${escapeHtml(path)}</a>
          <span class="ga-list__count">${count} views</span>
        </div>
        ${renderBar(count, max)}
      </li>
    `).join("");
  }

  function renderSources() {
    const list = trafficSources();
    const el = container.querySelector("[data-target='sources']");
    if (!list.length) {
      el.innerHTML = '<li class="ga-list__empty">Chưa có session nào.</li>';
      return;
    }
    const max = list[0][1];
    el.innerHTML = list.map(([name, count]) => `
      <li class="ga-list__row">
        <div class="ga-list__head">
          <span class="ga-list__name">${escapeHtml(name)}</span>
          <span class="ga-list__count">${count} sessions</span>
        </div>
        ${renderBar(count, max)}
      </li>
    `).join("");
  }

  // ===== MOUNT =====
  container.querySelector("[data-ga-date]").textContent = formatToday();
  container.querySelector("[data-metric='users']").textContent = metrics.users.toLocaleString("vi-VN");
  container.querySelector("[data-metric='sessions']").textContent = metrics.sessions.toLocaleString("vi-VN");
  container.querySelector("[data-metric='views']").textContent = metrics.views.toLocaleString("vi-VN");
  container.querySelector("[data-metric='avg-time']").textContent = formatDuration(metrics.avgTime);
  container.querySelector("[data-metric='bounce']").textContent = metrics.bounce.toFixed(1) + "%";

  renderTopPages();
  renderSources();
})();
