/**
 * Stats badge cho trang bài viết: lượt đọc + thời gian đọc trung bình
 * Data: localStorage zola-events (đã có sẵn từ sidebar.js tracking)
 *
 * Hiển thị stats CỦA RIÊNG VISITOR NÀY (không cross-user).
 * Để stats cross-user, cần Firebase/CountAPI — sẽ làm sau nếu cần.
 */
(function () {
  const container = document.querySelector("[data-post-stats]");
  if (!container) return;

  function loadEvents() {
    try { return JSON.parse(localStorage.getItem("zola-events") || "[]"); }
    catch { return []; }
  }

  function fmtDuration(sec) {
    if (!sec || sec < 1) return "—";
    if (sec < 60) return Math.round(sec) + "s";
    const m = Math.floor(sec / 60);
    const s = Math.round(sec % 60);
    return m + "m " + s + "s";
  }

  const events = loadEvents();
  const currentUrl = location.href;

  // Lọc events của trang này
  const myEvents = events.filter((e) => e.url === currentUrl);
  const views = myEvents.filter((e) => e.type === "view");
  const fulls = myEvents.filter((e) => e.type === "full");

  // Compute reading time: với mỗi 'view', tìm 'full' gần nhất sau đó trong cùng session (30 min window)
  const SESSION_MAX = 30 * 60 * 1000;
  let totalReadMs = 0;
  let completedReads = 0;
  views.forEach((v) => {
    const matching = fulls.find((f) => f.ts > v.ts && f.ts - v.ts < SESSION_MAX);
    if (matching) {
      totalReadMs += matching.ts - v.ts;
      completedReads++;
    }
  });
  const avgSec = completedReads ? (totalReadMs / completedReads) / 1000 : 0;
  const builtInStats = container.innerHTML.trim();

  // Render
  container.innerHTML = builtInStats + `
    <span class="post-stat" title="Lượt mở bài này">
      <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
      </svg>
      <strong data-stat-views>${views.length}</strong> lượt đọc
    </span>
    <span class="post-stat" title="Đã đọc hết tới cuối bài">
      <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="20 6 9 17 4 12"/>
      </svg>
      <strong data-stat-completed>${completedReads}</strong> đọc trọn
    </span>
    <span class="post-stat" title="Thời gian trung bình mỗi lần đọc">
      <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
      </svg>
      <strong data-stat-time>${fmtDuration(avgSec)}</strong>/lần
    </span>
  `;
})();
