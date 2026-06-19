/**
 * SEO Reality Check — live Google Search Console hydration.
 * Build-time HTML + fetch /gsc/metrics (20m cache) + admin OAuth controls.
 */
(function () {
  "use strict";

  var CACHE_KEY = "zola-gsc-metrics-cache";
  var PENDING_KEY = "zola-gsc-pending-property";
  var TTL_MS = 20 * 60 * 1000;
  var SUCCESS_HOLD_MS = 2800;
  var trendMode = "daily";

  var root = document.querySelector('[data-widget="seo-reality"]');
  if (!root) return;

  function authApi() {
    var m = document.querySelector('meta[name="zola-cms-auth-api"]');
    if (m && m.content) return m.content.replace(/\/$/, "");
    m = document.querySelector('meta[name="zola-visitor-api"]');
    return m && m.content ? m.content.replace(/\/$/, "") : "";
  }

  function sid() {
    try {
      return sessionStorage.getItem("zola-cms-session-id") || "";
    } catch (e) {
      return "";
    }
  }

  function readEmbedded() {
    var el = document.getElementById("seo-reality-gsc-data");
    if (!el) return null;
    try {
      return JSON.parse(el.textContent || "{}");
    } catch (e) {
      return null;
    }
  }

  function cacheGet() {
    try {
      var raw = localStorage.getItem(CACHE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }

  function cacheSet(payload) {
    try {
      localStorage.setItem(CACHE_KEY, JSON.stringify({ at: Date.now(), payload: payload }));
    } catch (e) {}
  }

  function fmtNum(n) {
    if (n == null || n === "") return "—";
    return Number(n).toLocaleString("vi-VN");
  }

  function fmtRelative(iso) {
    if (!iso) return "—";
    var t = Date.parse(iso);
    if (isNaN(t)) return "Updated " + iso;
    var sec = Math.max(0, Math.floor((Date.now() - t) / 1000));
    if (sec < 60) return "Updated " + (sec || 1) + " second" + (sec === 1 ? "" : "s") + " ago";
    var min = Math.floor(sec / 60);
    if (min < 60) return "Updated " + min + " minute" + (min === 1 ? "" : "s") + " ago";
    var hr = Math.floor(min / 60);
    if (hr < 48) return "Updated " + hr + " hour" + (hr === 1 ? "" : "s") + " ago";
    var day = Math.floor(hr / 24);
    return "Updated " + day + " day" + (day === 1 ? "" : "s") + " ago";
  }

  function bundleFromEmbedded(embedded) {
    if (!embedded || !embedded.gsc) return null;
    var idx = embedded.indexing || {};
    return Object.assign({}, embedded.gsc, {
      indexed_pages: idx.pages_indexed != null ? idx.pages_indexed : embedded.gsc.indexed_pages,
      non_indexed_pages: idx.pages_non_indexed != null ? idx.pages_non_indexed : embedded.gsc.non_indexed_pages,
      submitted_pages: idx.submitted_pages,
      pages_waiting: idx.pages_waiting,
      sitemap_status: idx.sitemap_status || embedded.gsc.sitemap_status,
      last_crawl: idx.last_crawl || embedded.gsc.last_crawl,
      index_health: idx.index_health,
      top_pages: embedded.top_pages || [],
      top_queries: embedded.top_queries || [],
      trend: embedded.trend || { daily: [], weekly: [], monthly: [] },
      executive_summary: embedded.executive_summary || [],
    });
  }

  function shortPage(url) {
    if (!url) return "—";
    return String(url).replace("https://banhang-chogao.github.io/zola", "") || url;
  }

  function setVisible(el, on) {
    if (!el) return;
    el.style.display = on ? "" : "none";
  }

  function applyGscBundle(bundle) {
    if (!bundle) return;
    var gsc = {
      connected: !!bundle.connected,
      impressions: bundle.impressions,
      clicks: bundle.clicks,
      ctr: bundle.ctr,
      avg_position: bundle.avg_position,
      updated_at: bundle.updated_at,
      period_days: bundle.period_days || 28,
      indexed_pages: bundle.indexed_pages,
      non_indexed_pages: bundle.non_indexed_pages,
      submitted_pages: bundle.submitted_pages,
      pages_waiting: bundle.pages_waiting,
      sitemap_status: bundle.sitemap_status,
      last_crawl: bundle.last_crawl,
      index_health: bundle.index_health,
      top_pages: bundle.top_pages || [],
      top_queries: bundle.top_queries || [],
      trend: bundle.trend || { daily: [], weekly: [], monthly: [] },
      executive_summary: bundle.executive_summary || [],
      status: bundle.status,
    };

    setVisible(root.querySelector("[data-gsc-connected]"), gsc.connected);
    setVisible(root.querySelector("[data-gsc-disconnected]"), !gsc.connected);
    setVisible(root.querySelector("[data-idx-connected]"), gsc.connected);
    setVisible(root.querySelector("[data-idx-disconnected]"), !gsc.connected);

    var err = root.querySelector("[data-gsc-error]");
    if (err) {
      if (gsc.status === "quota_warning" || gsc.status === "quota_exceeded") {
        err.hidden = false;
        err.textContent = "GSC quota exceeded — showing cached data.";
      } else if (gsc.status === "token_expired") {
        err.hidden = false;
        err.textContent = "Token expired — reconnect Google Search Console.";
      } else {
        err.hidden = true;
      }
    }

    var imp = root.querySelector("[data-gsc-impressions]");
    var clk = root.querySelector("[data-gsc-clicks]");
    var ctr = root.querySelector("[data-gsc-ctr]");
    var pos = root.querySelector("[data-gsc-position]");
    var upd = root.querySelector("[data-gsc-updated]");
    if (imp) imp.textContent = fmtNum(gsc.impressions);
    if (clk) clk.textContent = fmtNum(gsc.clicks);
    if (ctr) ctr.textContent = gsc.ctr != null ? gsc.ctr + "%" : "—";
    if (pos) pos.textContent = gsc.avg_position != null ? gsc.avg_position : "—";
    if (upd && gsc.updated_at) upd.textContent = fmtRelative(gsc.updated_at);

    var propEl = root.querySelector("[data-gsc-prop]");
    if (propEl && bundle.property) propEl.textContent = bundle.property;

    var health = root.querySelector("[data-idx-health]");
    if (health && gsc.index_health) {
      health.textContent = gsc.index_health;
      health.className =
        "seo-reality__health-badge seo-reality__health-badge--" +
        String(gsc.index_health).toLowerCase();
    }
    var indexed = Number(gsc.indexed_pages) || 0;
    var nonIdx = Number(gsc.non_indexed_pages) || 0;
    var submitted = Number(gsc.submitted_pages) || indexed + nonIdx || 1;
    var max = Math.max(submitted, indexed + nonIdx, 1);
    function bar(sel, val) {
      var el = root.querySelector(sel);
      if (el) el.style.width = Math.min(100, Math.round((val / max) * 100)) + "%";
    }
    bar("[data-idx-bar-indexed]", indexed);
    bar("[data-idx-bar-non]", nonIdx);
    bar("[data-idx-bar-sub]", submitted);
    var iEl = root.querySelector("[data-idx-indexed]");
    var nEl = root.querySelector("[data-idx-non]");
    var sEl = root.querySelector("[data-idx-submitted]");
    var sm = root.querySelector("[data-idx-sitemap]");
    if (iEl) iEl.textContent = fmtNum(gsc.indexed_pages);
    if (nEl) nEl.textContent = fmtNum(gsc.non_indexed_pages);
    if (sEl) sEl.textContent = fmtNum(gsc.submitted_pages);
    if (sm) sm.textContent = gsc.sitemap_status || "—";
    var crawl = root.querySelector("[data-idx-crawl]");
    if (crawl) crawl.textContent = gsc.last_crawl ? String(gsc.last_crawl).slice(0, 10) : "—";

    renderTopPages(gsc.top_pages);
    renderQueries(gsc.top_queries);
    renderExec(gsc.executive_summary);
    drawTrend(gsc.trend);
  }

  function renderTopPages(rows) {
    var wrap = root.querySelector("[data-top-pages-wrap]");
    if (!wrap) return;
    if (!rows || !rows.length) {
      wrap.innerHTML = '<p class="seo-reality__empty">Chưa có dữ liệu — kết nối GSC.</p>';
      return;
    }
    var html =
      '<table class="seo-reality__table"><thead><tr><th>Page</th><th>Clk</th><th>Imp</th><th>CTR</th><th>Pos</th></tr></thead><tbody>';
    rows.slice(0, 10).forEach(function (r) {
      html +=
        "<tr><td class=\"seo-reality__cell-page\">" +
        shortPage(r.page) +
        "</td><td>" +
        (r.clicks || 0) +
        "</td><td>" +
        (r.impressions || 0) +
        "</td><td>" +
        (r.ctr || 0) +
        "%</td><td>" +
        (r.position != null ? r.position : "—") +
        "</td></tr>";
    });
    html += "</tbody></table>";
    wrap.innerHTML = html;
  }

  function renderQueries(rows) {
    var list = root.querySelector("[data-queries-list]");
    if (!list) return;
    if (!rows || !rows.length) {
      list.innerHTML = '<li class="seo-reality__empty">Chưa có truy vấn — kết nối GSC.</li>';
      return;
    }
    list.innerHTML = rows
      .slice(0, 10)
      .map(function (r) {
        return (
          "<li><span class=\"seo-reality__query-text\">" +
          (r.query || "") +
          '</span><span class="seo-reality__query-meta">' +
          (r.clicks || 0) +
          " clk · pos " +
          (r.position != null ? r.position : "—") +
          " · CTR " +
          (r.ctr || 0) +
          "%</span></li>"
        );
      })
      .join("");
  }

  function renderExec(lines) {
    var list = root.querySelector("[data-exec-list]");
    if (!list) return;
    if (!lines || !lines.length) {
      list.innerHTML =
        '<li class="seo-reality__empty">Narrative sẽ hiện sau khi có dữ liệu GSC thật.</li>';
      return;
    }
    list.innerHTML = lines.map(function (l) {
      return "<li>" + l + "</li>";
    }).join("");
  }

  function drawTrend(trend) {
    var canvas = root.querySelector("[data-trend-canvas]");
    var empty = root.querySelector("[data-trend-empty]");
    if (!canvas || !canvas.getContext) return;
    var rows = (trend && trend[trendMode]) || [];
    if (!rows.length) {
      if (empty) empty.hidden = false;
      return;
    }
    if (empty) empty.hidden = true;
    var ctx = canvas.getContext("2d");
    var w = canvas.width;
    var h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    var vals = rows.map(function (r) {
      return Number(r.clicks) || 0;
    });
    var max = Math.max.apply(null, vals.concat([1]));
    var pad = 8;
    ctx.strokeStyle = "rgba(0, 167, 160, 0.85)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    vals.forEach(function (v, i) {
      var x = pad + (i / Math.max(vals.length - 1, 1)) * (w - pad * 2);
      var y = h - pad - (v / max) * (h - pad * 2);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
  }

  function fetchLive() {
    var api = authApi();
    if (!api) return Promise.resolve(null);
    return fetch(api + "/gsc/metrics", { credentials: "omit", cache: "no-store" })
      .then(function (res) {
        return res.ok ? res.json() : null;
      })
      .catch(function () {
        return null;
      });
  }

  function fetchStaticFallback() {
    var base = (function () {
      var m = document.querySelector('meta[name="zola-base-url"]');
      return m && m.content ? m.content.replace(/\/$/, "") : "";
    })();
    if (!base) return Promise.resolve(null);
    return fetch(base + "/data/gsc-metrics.json?_=" + Date.now(), { cache: "no-store" })
      .then(function (r) {
        return r.ok ? r.json() : null;
      })
      .catch(function () {
        return null;
      });
  }

  // Accept URL-prefix properties (https://…/) and Domain properties (sc-domain:…).
  function isValidProperty(v) {
    v = String(v || "").trim();
    if (!v) return false;
    if (/^sc-domain:[a-z0-9-]+(\.[a-z0-9-]+)+$/i.test(v)) return true;
    if (/^https?:\/\//i.test(v)) {
      try {
        var u = new URL(v);
        return !!u.hostname && u.hostname.indexOf(".") > 0;
      } catch (e) {
        return false;
      }
    }
    return false;
  }

  // Redirect (with the entered property + CMS session) into Google OAuth.
  // The session id rides as a query param because a top-level navigation
  // cannot set the Authorization header the backend expects.
  function startOAuth(property) {
    var api = authApi();
    if (!api) return false;
    try {
      if (property) sessionStorage.setItem(PENDING_KEY, property);
    } catch (e) {}
    var url = api + "/gsc/oauth/start?return_to=" + encodeURIComponent("/");
    var s = sid();
    if (s) url += "&sid=" + encodeURIComponent(s);
    if (property) url += "&property=" + encodeURIComponent(property);
    location.href = url;
    return true;
  }

  function showSuccess() {
    var success = root.querySelector("[data-gsc-success]");
    if (!success) return;
    success.hidden = false;
    // Re-trigger the entrance animation if it was already shown.
    success.classList.remove("is-active");
    void success.offsetWidth;
    success.classList.add("is-active");
  }

  function hideSuccess() {
    var success = root.querySelector("[data-gsc-success]");
    if (success) success.hidden = true;
  }

  function setupAdmin() {
    var session = sid();
    var api = authApi();
    var form = root.querySelector("[data-gsc-admin]");
    var connectBtn = root.querySelector("[data-gsc-connect]");
    var input = root.querySelector("[data-gsc-property]");
    var validation = root.querySelector("[data-gsc-validation]");
    var discBtn = root.querySelector("[data-gsc-disconnect]");
    var reconnectWrap = root.querySelector("[data-gsc-reconnect]");
    var reconnectBtn = root.querySelector("[data-gsc-reconnect-btn]");

    // Admin-only controls require an authenticated CMS session.
    if (form && session) form.hidden = false;

    function showValidation(msg) {
      if (!validation) return;
      if (msg) {
        validation.hidden = false;
        validation.textContent = msg;
      } else {
        validation.hidden = true;
        validation.textContent = "";
      }
      if (input) input.classList.toggle("is-invalid", !!msg);
    }

    if (input) {
      input.addEventListener("input", function () {
        showValidation("");
      });
    }

    function submitConnect() {
      if (!api || !sid()) return;
      var val = input ? input.value.trim() : "";
      if (!isValidProperty(val)) {
        showValidation("Vui lòng nhập GSC Property ID hợp lệ.");
        if (input) input.focus();
        return;
      }
      showValidation("");
      if (connectBtn) connectBtn.classList.add("is-loading");
      // Enter key and the "Kết nối GSC" button share this single flow.
      startOAuth(val);
    }

    if (form) {
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        submitConnect();
      });
    }

    if (discBtn) {
      discBtn.addEventListener("click", function () {
        if (!api || !sid()) return;
        discBtn.classList.add("is-loading");
        fetch(api + "/gsc/disconnect", {
          method: "POST",
          headers: { Authorization: "Bearer " + sid() },
        })
          .catch(function () {})
          .then(function () {
            discBtn.classList.remove("is-loading");
            handleDisconnected();
          });
      });
    }

    if (reconnectBtn) {
      reconnectBtn.addEventListener("click", function () {
        var prev = "";
        try {
          prev = sessionStorage.getItem(PENDING_KEY) || "";
        } catch (e) {}
        reconnectBtn.classList.add("is-loading");
        startOAuth(prev);
      });
    }

    // Restore the empty/input state locally after a disconnect (no reload).
    function handleDisconnected() {
      try {
        sessionStorage.removeItem(PENDING_KEY);
      } catch (e) {}
      try {
        localStorage.removeItem(CACHE_KEY);
      } catch (e) {}
      hideSuccess();
      applyGscBundle({ connected: false });
      if (input) input.value = "";
      if (discBtn) discBtn.hidden = true;
      if (form && sid()) form.hidden = false;
      if (reconnectWrap) reconnectWrap.hidden = false;
    }

    // Reveal admin-only disconnect + fill the connected property label.
    if (api) {
      fetch(api + "/gsc/status", { cache: "no-store" })
        .then(function (r) {
          return r.ok ? r.json() : null;
        })
        .then(function (st) {
          if (!st) return;
          var propEl = root.querySelector("[data-gsc-prop]");
          if (propEl && st.property) propEl.textContent = st.property;
          if (discBtn && session) discBtn.hidden = !st.connected;
        })
        .catch(function () {});
    }
  }

  function bindTrendTabs() {
    root.querySelectorAll("[data-trend-tab]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        root.querySelectorAll("[data-trend-tab]").forEach(function (b) {
          b.classList.remove("is-active");
        });
        btn.classList.add("is-active");
        trendMode = btn.getAttribute("data-trend-tab") || "daily";
        var c = cacheGet();
        var payload = (c && c.payload) || bundleFromEmbedded(readEmbedded());
        if (payload && payload.trend) drawTrend(payload.trend);
      });
    });
  }

  function init() {
    var embedded = readEmbedded();
    var embeddedBundle = bundleFromEmbedded(embedded);
    if (embeddedBundle) applyGscBundle(embeddedBundle);

    var c = cacheGet();
    var stale = !c || Date.now() - c.at >= TTL_MS;
    if (!stale && c.payload) applyGscBundle(c.payload);

    if (stale) {
      fetchLive().then(function (live) {
        if (live && live.connected) {
          applyGscBundle(live);
          cacheSet(live);
        } else {
          return fetchStaticFallback().then(function (fb) {
            if (fb && fb.connected) {
              applyGscBundle(fb);
              cacheSet(fb);
            }
          });
        }
      });
    }

    bindTrendTabs();
    setupAdmin();

    var connectedSignal =
      location.hash.indexOf("gsc_connected=1") >= 0 ||
      location.search.indexOf("gsc_connected=1") >= 0;
    if (connectedSignal) {
      history.replaceState(null, "", location.pathname);
      // Celebrate immediately, then confirm against the backend so we never
      // fake a success: KPIs only reveal once the API reports connected.
      showSuccess();
      setVisible(root.querySelector("[data-gsc-connected]"), false);
      setVisible(root.querySelector("[data-gsc-disconnected]"), false);
      fetchLive().then(function (live) {
        if (live && live.connected) {
          applyGscBundle(live);
          cacheSet(live);
          try {
            sessionStorage.removeItem(PENDING_KEY);
          } catch (e) {}
          setVisible(root.querySelector("[data-gsc-connected]"), false);
          setVisible(root.querySelector("[data-gsc-disconnected]"), false);
          showSuccess();
          setTimeout(function () {
            hideSuccess();
            setVisible(root.querySelector("[data-gsc-connected]"), true);
          }, SUCCESS_HOLD_MS);
        } else {
          // OAuth did not actually connect — stay honest, restore empty state.
          hideSuccess();
          applyGscBundle({ connected: false });
        }
      });
    }

    // Surface a real OAuth failure instead of silently faking success.
    var errMatch = (location.hash + " " + location.search).match(/gsc_error=([a-z_]+)/i);
    if (errMatch) {
      history.replaceState(null, "", location.pathname);
      hideSuccess();
      var errEl = root.querySelector("[data-gsc-error]");
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = "Kết nối GSC chưa hoàn tất (" + errMatch[1] + "). Vui lòng thử lại.";
      }
      applyGscBundle({ connected: false });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();