/**
 * Điện ảnh page — fetch /api/movies từ backend (TMDB cache 24h).
 *
 * Reuse layout + skeleton + cards của /du-lich/ (cùng class .du-lich-*).
 * Endpoint khác (movies thay news), copy text khác (refresh 24h, source TMDB).
 */
(function () {
  "use strict";

  const meta = document.querySelector('meta[name="zola-visitor-api"]');
  const API = (meta && meta.getAttribute("content")) || "";

  const root = document.querySelector(".du-lich");
  if (!root) return;

  const statusEl    = root.querySelector("[data-status]");
  const listEl      = root.querySelector("[data-list]");
  const errorEl     = root.querySelector("[data-error]");
  const footerEl    = root.querySelector("[data-footer]");
  const cacheInfoEl = root.querySelector("[data-cache-info]");
  const reloadBtn   = root.querySelector("[data-reload]");

  function escapeHtml(s) {
    return String(s || "").replace(/[&<>"']/g, function (c) {
      return ({ "&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;" }[c]);
    });
  }

  function stripHtml(s) {
    return String(s || "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
  }

  function formatYear(s) {
    if (!s) return "";
    // TMDB release_date format: YYYY-MM-DD → extract year cho compact card
    const m = String(s).match(/^(\d{4})/);
    return m ? m[1] : s;
  }

  function showCards(data) {
    statusEl.hidden = true;
    errorEl.hidden = true;

    if (!data.items || !data.items.length) {
      errorEl.hidden = false;
      footerEl.hidden = false;
      cacheInfoEl.textContent = data.from_cache
        ? "(cached, không có phim)"
        : "(không có phim)";
      return;
    }

    const sourceLabel = data.source ? escapeHtml(data.source) : "TMDB";

    listEl.innerHTML = data.items.map(function (it, idx) {
      const summary = stripHtml(it.summary).slice(0, 220);
      const year    = formatYear(it.published);
      const thumb   = it.thumbnail ? escapeHtml(it.thumbnail) : "";
      const rating  = it.rating ? escapeHtml(it.rating) : "";

      const thumbHtml = thumb
        ? '<div class="du-lich-card__thumb"><img src="' + thumb +
          '" alt="" loading="lazy" onerror="this.parentNode.style.display=\'none\'"></div>'
        : "";

      const ratingHtml = rating
        ? '<span class="du-lich-card__rating" title="Điểm đánh giá TMDB">⭐ ' + rating + '</span>'
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
            (year ? '<span class="du-lich-card__date">🎬 ' + escapeHtml(year) + '</span>' : "") +
            '<span class="du-lich-card__source">' + sourceLabel + '</span>' +
          '</div>' +
        '</div>' +
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
      titleEl.textContent = "Tạm thời không lấy được phim từ " + sourceName;
    }
  }

  async function load() {
    if (!API) { showError("backend"); return; }
    statusEl.hidden = false;
    listEl.hidden = true;
    errorEl.hidden = true;
    footerEl.hidden = true;

    try {
      const res = await fetch(API + "/api/movies", {
        credentials: "omit",
        cache: "no-store",
      });
      if (!res.ok) { showError("IMDB"); return; }
      const data = await res.json();
      if (data.error || !data.items || !data.items.length) {
        showError(data.source || "IMDB");
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

  if (typeof requestIdleCallback === "function") {
    requestIdleCallback(load, { timeout: 2000 });
  } else {
    setTimeout(load, 200);
  }
})();
