/**
 * Du lịch news loader — fetch /api/news/du-lich và render cards.
 *
 * Backend caching Redis 30 phút → page chỉ fetch khi cache stale, không
 * hammer Znews. Empty result → fallback "tạm thời không có tin", không crash UI.
 *
 * Performance:
 *   - requestIdleCallback → fetch sau LCP, không block paint
 *   - Silent fail nếu API down → giữ skeleton hoặc swap error state
 *   - No retry loop (avoid spam backend) — user bấm "Tải lại" thủ công nếu cần
 */
(function () {
  "use strict";

  const meta = document.querySelector('meta[name="zola-visitor-api"]');
  const API = (meta && meta.getAttribute("content")) || "";

  const root = document.querySelector(".du-lich");
  if (!root) return;

  const statusEl   = root.querySelector("[data-status]");
  const listEl     = root.querySelector("[data-list]");
  const errorEl    = root.querySelector("[data-error]");
  const footerEl   = root.querySelector("[data-footer]");
  const cacheInfoEl = root.querySelector("[data-cache-info]");
  const reloadBtn  = root.querySelector("[data-reload]");

  function escapeHtml(s) {
    return String(s || "").replace(/[&<>"']/g, function (c) {
      return ({ "&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;" }[c]);
    });
  }

  // Strip HTML tags từ summary nếu Znews trả về raw HTML (an toàn 2 lớp:
  // strip HTML khỏi text + escape lại trước render).
  function stripHtml(s) {
    return String(s || "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
  }

  function formatDate(s) {
    if (!s) return "";
    // Try parse Znews format hoặc ISO 8601, fallback raw string
    const d = new Date(s);
    if (isNaN(d.getTime())) return s;
    return d.toLocaleString("vi-VN", {
      hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit", year: "numeric",
    });
  }

  function showCards(data) {
    statusEl.hidden = true;
    errorEl.hidden = true;

    if (!data.items || !data.items.length) {
      errorEl.hidden = false;
      footerEl.hidden = false;
      cacheInfoEl.textContent = data.from_cache
        ? "(cached, không có tin)"
        : "(không có tin)";
      return;
    }

    const sourceLabel = data.source ? escapeHtml(data.source) : "Nguồn";

    listEl.innerHTML = data.items.map(function (it, idx) {
      const summary = stripHtml(it.summary).slice(0, 220);
      const dateStr = formatDate(it.published);
      const thumb   = it.thumbnail ? escapeHtml(it.thumbnail) : "";
      const rating  = it.rating ? escapeHtml(it.rating) : "";

      // Thumbnail: hide if image fail load → graceful degrade
      const thumbHtml = thumb
        ? '<div class="du-lich-card__thumb"><img src="' + thumb +
          '" alt="" loading="lazy" onerror="this.parentNode.style.display=\'none\'"></div>'
        : "";

      const ratingHtml = rating
        ? '<span class="du-lich-card__rating" title="Đánh giá từ ' + sourceLabel +
          '">⭐ ' + rating + '</span>'
        : "";

      return '<a class="du-lich-card' + (thumb ? ' du-lich-card--has-thumb' : '') +
        '" href="' + escapeHtml(it.link) + '" target="_blank" rel="noopener noreferrer">' +
        '<div class="du-lich-card__rank" aria-hidden="true">' + (idx + 1) + '</div>' +
        thumbHtml +
        '<div class="du-lich-card__body">' +
          '<h3 class="du-lich-card__title">' + escapeHtml(it.title) + '</h3>' +
          (summary ? '<p class="du-lich-card__summary">' + escapeHtml(summary) + '…</p>' : "") +
          '<div class="du-lich-card__meta">' +
            ratingHtml +
            (dateStr ? '<span class="du-lich-card__date">📅 ' + escapeHtml(dateStr) + '</span>' : "") +
            '<span class="du-lich-card__source">' + sourceLabel + ' · Du lịch</span>' +
          '</div>' +
        '</div>' +
        '<div class="du-lich-card__arrow" aria-hidden="true">→</div>' +
      '</a>';
    }).join("");
    listEl.hidden = false;

    footerEl.hidden = false;
    cacheInfoEl.textContent = data.from_cache
      ? "📦 Hiển thị từ cache (refresh mỗi 24h)"
      : "🔄 Vừa fetch mới từ " + sourceLabel;
  }

  function showError(sourceName) {
    statusEl.hidden = true;
    listEl.hidden = true;
    errorEl.hidden = false;
    footerEl.hidden = false;
    cacheInfoEl.textContent = "";
    const titleEl = root.querySelector("[data-error-title]");
    if (titleEl && sourceName) {
      titleEl.textContent = "Tạm thời không lấy được tin từ " + sourceName;
    }
  }

  async function load() {
    if (!API) { showError(); return; }
    statusEl.hidden = false;
    listEl.hidden = true;
    errorEl.hidden = true;
    footerEl.hidden = true;

    try {
      const res = await fetch(API + "/api/news/du-lich", {
        credentials: "omit",
        cache: "no-store",
      });
      if (!res.ok) { showError("nguồn"); return; }
      const data = await res.json();
      if (data.error || !data.items || !data.items.length) {
        showError(data.source || "nguồn");
        return;
      }
      showCards(data);
    } catch (e) {
      showError("backend");
    }
  }

  if (reloadBtn) {
    reloadBtn.addEventListener("click", load);
  }

  // Defer fetch tới sau LCP để không cạnh tranh critical render
  if (typeof requestIdleCallback === "function") {
    requestIdleCallback(load, { timeout: 2000 });
  } else {
    setTimeout(load, 200);
  }
})();
