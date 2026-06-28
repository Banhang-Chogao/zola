(function () {
  "use strict";

  var app = document.getElementById("editor-app");
  var rail = document.querySelector("[data-seo-insights-rail]");
  var form = app && app.querySelector("[data-form='post']");
  if (!app || !rail || !form) return;

  var VIPZONE_API = "";
  var m = document.querySelector('meta[name="zola-vipzone-api"]');
  if (m) VIPZONE_API = (m.getAttribute("content") || "").replace(/\/$/, "");

  var BASE = "";
  var baseMeta = document.querySelector('meta[name="zola-base-url"]');
  if (baseMeta) BASE = (baseMeta.getAttribute("content") || "").replace(/\/$/, "");

  var SESSION_KEY = "zola-cms-session-id";

  function $(s) { return rail.querySelector(s); }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function fld(n) { return form.querySelector("[name='" + n + "']"); }

  /* ---- GSC page metrics fetch with client-side cache ---- */
  var CACHE_TTL = 15 * 60 * 1000; // 15 min

  function cacheKey(pageUrl) {
    return "gsc:page:" + btoa(pageUrl).replace(/=+$/, "").slice(0, 48);
  }

  function cacheGet(pageUrl) {
    try {
      var raw = sessionStorage.getItem(cacheKey(pageUrl));
      if (!raw) return null;
      var entry = JSON.parse(raw);
      if (Date.now() - entry.ts < CACHE_TTL) return entry.data;
      sessionStorage.removeItem(cacheKey(pageUrl));
    } catch (e) {}
    return null;
  }

  function cacheSet(pageUrl, data) {
    try {
      sessionStorage.setItem(cacheKey(pageUrl), JSON.stringify({ ts: Date.now(), data: data }));
    } catch (e) {}
  }

  function fetchPageMetrics(pageUrl) {
    var cached = cacheGet(pageUrl);
    if (cached) return Promise.resolve(cached);

    var sid = sessionStorage.getItem(SESSION_KEY) || localStorage.getItem(SESSION_KEY) || "";
    var url = VIPZONE_API + "/gsc/page-metrics?url=" + encodeURIComponent(pageUrl);

    return fetch(url, {
      headers: sid ? { Authorization: "Bearer " + sid } : {},
    })
      .then(function (r) {
        if (!r.ok) return { connected: false, status: "api_error" };
        return r.json();
      })
      .then(function (data) {
        cacheSet(pageUrl, data);
        return data;
      })
      .catch(function () {
        return { connected: false, status: "api_error" };
      });
  }

  /* ---- Format helpers ---- */
  function fmtNum(n) {
    if (n == null) return "—";
    if (n >= 1000000) return (n / 1000000).toFixed(1) + "M";
    if (n >= 1000) return (n / 1000).toFixed(1) + "K";
    return String(n);
  }

  function fmtPct(n) {
    if (n == null || isNaN(n)) return "—";
    return n.toFixed(1) + "%";
  }

  function fmtPos(n) {
    if (n == null || isNaN(n) || n === 0) return "—";
    return n.toFixed(1);
  }

  function fmtDateTime(isoStr) {
    if (!isoStr) return "—";
    try {
      var d = new Date(isoStr);
      return d.toLocaleString("vi-VN", {
        day: "2-digit", month: "2-digit", year: "numeric",
        hour: "2-digit", minute: "2-digit",
        timeZone: "Asia/Ho_Chi_Minh",
      });
    } catch (e) { return isoStr; }
  }

  function trendIcon(val, inverse) {
    if (val == null || val === 0) return '<span class="esi-trend esi-trend--flat">→</span>';
    var up = inverse ? val < 0 : val > 0;
    var cls = up ? "esi-trend--up" : "esi-trend--down";
    var sym = up ? "▲" : "▼";
    var abs = Math.abs(val);
    return '<span class="esi-trend ' + cls + '" title="' + (val > 0 ? "+" : "") + abs + '%">' + sym + " " + abs + "%</span>";
  }

  function positionBadge(pos) {
    if (pos == null || pos === 0) return "";
    if (pos <= 3) return '<span class="esi-badge esi-badge--top3">🟢 Top 3</span>';
    if (pos <= 10) return '<span class="esi-badge esi-badge--top10">🟡 Top 10</span>';
    return '<span class="esi-badge esi-badge--out">🔴 >10</span>';
  }

  function queryBadge(pos) {
    if (pos == null || pos === 0) return "";
    if (pos <= 3) return "🟢";
    if (pos <= 10) return "🟡";
    return "🔴";
  }

  /* ---- Render ---- */
  function render(data, pageUrl) {
    var connected = data && data.connected;

    // Loading state
    var loading = $("[data-esi-loading]");
    if (loading) loading.hidden = true;

    if (!connected) {
      var empty = $("[data-esi-empty]");
      if (empty) {
        empty.hidden = false;
        empty.innerHTML =
          '<p class="esi-empty-msg">Chưa có dữ liệu GSC</p>' +
          '<p class="esi-empty-hint">Kết nối Google Search Console để xem insights.</p>';
      }
      return;
    }

    // Has data check
    if (!data.has_data) {
      var empty = $("[data-esi-empty]");
      if (empty) {
        empty.hidden = false;
        empty.innerHTML =
          '<p class="esi-empty-msg">Chưa có dữ liệu GSC</p>' +
          '<p class="esi-empty-hint">Bài viết chưa được Google index hoặc chưa có lượt hiển thị.</p>';
      }
      return;
    }

    // Hide empty state, show content
    var empty = $("[data-esi-empty]");
    if (empty) empty.hidden = true;
    var content = $("[data-esi-content]");
    if (content) content.hidden = false;

    // Indexed status
    var indexedEl = $("[data-esi-indexed]");
    if (indexedEl) {
      indexedEl.innerHTML = data.indexed
        ? '<span class="esi-indexed esi-indexed--ok">✔ Indexed</span>'
        : '<span class="esi-indexed esi-indexed--no">✘ Not indexed</span>';
    }

    // Canonical
    $("[data-esi-canonical]") && ($("[data-esi-canonical]").textContent = pageUrl);

    // Last crawl (from updated_at as proxy since GSC doesn't expose per-page crawl time)
    $("[data-esi-last-crawl]") && ($("[data-esi-last-crawl]").textContent = fmtDateTime(data.updated_at));

    // KPIs
    $("[data-esi-clicks]") && ($("[data-esi-clicks]").textContent = fmtNum(data.clicks));
    $("[data-esi-impressions]") && ($("[data-esi-impressions]").textContent = fmtNum(data.impressions));
    $("[data-esi-ctr]") && ($("[data-esi-ctr]").textContent = fmtPct(data.ctr));
    $("[data-esi-position]") && ($("[data-esi-position]").textContent = fmtPos(data.avg_position));
    $("[data-esi-position-badge]") && ($("[data-esi-position-badge]").innerHTML = positionBadge(data.avg_position));

    // Last synced
    $("[data-esi-synced]") && ($("[data-esi-synced]").textContent = fmtDateTime(data.updated_at));

    // Top queries
    var queriesEl = $("[data-esi-queries]");
    if (queriesEl && data.top_queries && data.top_queries.length) {
      queriesEl.innerHTML = data.top_queries
        .slice(0, 5)
        .map(function (q) {
          return (
            '<a class="esi-query" href="https://search.google.com/search-console/performance/search-analytics?resource_id=' +
            encodeURIComponent(data.page_url || pageUrl) +
            "&query=" +
            encodeURIComponent(q.query) +
            '" target="_blank" rel="noopener">' +
            queryBadge(q.position) +
            " " +
            esc(q.query) +
            ' <span class="esi-query__clicks">' +
            q.clicks +
            " clicks</span>" +
            "</a>"
          );
        })
        .join("");
    }

    // View all link
    var viewAll = $("[data-esi-view-all]");
    if (viewAll) {
      viewAll.href =
        "https://search.google.com/search-console/performance/search-analytics?resource_id=" +
        encodeURIComponent(data.page_url || pageUrl) +
        "&page=" +
        encodeURIComponent(pageUrl);
      viewAll.hidden = false;
    }

    // Trend rows
    var trendEl = $("[data-esi-trend]");
    if (trendEl) {
      var t = data.trend || {};
      trendEl.innerHTML =
        "<tr><td>Clicks 7d</td><td>" +
        trendIcon(t.clicks_delta_pct, false) +
        "</td></tr>" +
        "<tr><td>Impressions 7d</td><td>" +
        trendIcon(t.impressions_delta_pct, false) +
        "</td></tr>" +
        "<tr><td>Position</td><td>" +
        (t.position_delta > 0
          ? '<span class="esi-trend esi-trend--up">▲ Improved ' + t.position_delta + "</span>"
          : t.position_delta < 0
            ? '<span class="esi-trend esi-trend--down">▼ Dropped ' + Math.abs(t.position_delta) + "</span>"
            : '<span class="esi-trend esi-trend--flat">→ Stable</span>') +
        "</td></tr>" +
        "<tr><td>CTR</td><td>" +
        (t.ctr_delta > 0
          ? '<span class="esi-trend esi-trend--up">▲ +' + t.ctr_delta + "%</span>"
          : t.ctr_delta < 0
            ? '<span class="esi-trend esi-trend--down">▼ ' + t.ctr_delta + "%</span>"
            : '<span class="esi-trend esi-trend--flat">→ Stable</span>') +
        "</td></tr>";
    }

    // Recommendations
    var recsEl = $("[data-esi-recs]");
    if (recsEl && data.recommendations && data.recommendations.length) {
      recsEl.innerHTML = data.recommendations
        .map(function (r) {
          return '<li class="esi-rec">' + esc(r) + "</li>";
        })
        .join("");
    } else if (recsEl) {
      recsEl.innerHTML = '<li class="esi-rec esi-rec--ok">✓ Đang hoạt động tốt.</li>';
    }
  }

  function showLoading() {
    var loading = $("[data-esi-loading]");
    if (loading) loading.hidden = false;
    var content = $("[data-esi-content]");
    if (content) content.hidden = true;
    var empty = $("[data-esi-empty]");
    if (empty) empty.hidden = true;
  }

  function loadInsights() {
    var slug = (fld("slug") && fld("slug").value) || "";
    var title = (fld("title") && fld("title").value) || "";
    if (!slug && !title) {
      showLoading();
      var empty = $("[data-esi-empty]");
      if (empty) {
        empty.hidden = false;
        empty.innerHTML = '<p class="esi-empty-msg">Nhập tiêu đề để xem insights.</p>';
      }
      return;
    }

    var resolvedSlug = slug || slugify(title);
    var pageUrl = BASE + "/" + resolvedSlug + "/";

    showLoading();
    fetchPageMetrics(pageUrl).then(function (data) {
      render(data, pageUrl);
    });
  }

  function slugify(s) {
    s = (s || "").toLowerCase();
    s = s.replace(/đ/g, "d");
    try { s = s.normalize("NFD").replace(/[\u0300-\u036f]/g, ""); } catch (e) {}
    return s.replace(/[^a-z0-9\s-]/g, "").trim().replace(/\s+/g, "-").replace(/-+/g, "-");
  }

  /* ---- Wire live updates ---- */
  ["title", "slug"].forEach(function (n) {
    var f = fld(n);
    if (f) f.addEventListener("input", debounce(loadInsights, 800));
  });

  var editView = app.querySelector("[data-view='edit']");
  if (editView && window.MutationObserver) {
    new MutationObserver(function () {
      if (!editView.hidden) setTimeout(loadInsights, 150);
    }).observe(editView, { attributes: true, attributeFilter: ["hidden"] });
  }

  document.addEventListener("cms:hydrated", function () {
    setTimeout(loadInsights, 100);
  });

  loadInsights();

  /* ---- Debounce helper ---- */
  function debounce(fn, delay) {
    var timer = null;
    return function () {
      var args = arguments;
      var ctx = this;
      if (timer) clearTimeout(timer);
      timer = setTimeout(function () {
        fn.apply(ctx, args);
        timer = null;
      }, delay);
    };
  }
})();
