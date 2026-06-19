/**
 * SEO Reality Check — live Google Search Console hydration.
 * Build-time HTML + fetch /gsc/metrics (20m cache) + admin OAuth controls.
 */
(function () {
  "use strict";

  var CACHE_KEY = "zola-gsc-metrics-cache";
  var PROPERTY_KEY = "zola-gsc-property-id";
  var PENDING_KEY = "zola-gsc-pending-property";
  var DEFAULT_PROPERTY = "https://banhang-chogao.github.io/zola/";
  var TTL_MS = 20 * 60 * 1000;
  var SUCCESS_HOLD_MS = 2800;
  var PENDING_MSG = "⏳ Đang chờ dữ liệu GSC";
  var trendMode = "daily";

  var root = document.querySelector('[data-widget="seo-reality"]');
  if (!root) return;

  function authApi() {
    var m = document.querySelector('meta[name="vipzone-auth-api"]');
    return m && m.content ? m.content.replace(/\/$/, "") : "https://blog-vipzone-api.onrender.com";
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

  function getSavedProperty() {
    try {
      var raw = localStorage.getItem(PROPERTY_KEY) || "";
      return isValidProperty(raw) ? String(raw).trim() : "";
    } catch (e) {
      return "";
    }
  }

  function setSavedProperty(value) {
    try {
      localStorage.setItem(PROPERTY_KEY, String(value).trim());
    } catch (e) {}
  }

  function clearSavedProperty() {
    try {
      localStorage.removeItem(PROPERTY_KEY);
    } catch (e) {}
  }

  function hasApiData(bundle) {
    if (!bundle || !bundle.connected) return false;
    if (bundle.impressions != null || bundle.clicks != null) return true;
    if (bundle.indexed_pages != null || bundle.non_indexed_pages != null) return true;
    if (bundle.top_pages && bundle.top_pages.length) return true;
    if (bundle.top_queries && bundle.top_queries.length) return true;
    var trend = bundle.trend || {};
    return !!(
      (trend.daily && trend.daily.length) ||
      (trend.weekly && trend.weekly.length) ||
      (trend.monthly && trend.monthly.length)
    );
  }

  function applyPropertyState(propertyId) {
    var hasProperty = isValidProperty(propertyId);
    setVisible(root.querySelector("[data-gsc-property-connected]"), hasProperty);
    setVisible(root.querySelector("[data-gsc-property-disconnected]"), !hasProperty);

    var propEl = root.querySelector("[data-gsc-prop]");
    if (propEl) propEl.textContent = hasProperty ? propertyId : "—";

    var form = root.querySelector("[data-gsc-admin]");
    if (form && hasProperty) form.hidden = true;

    var discBtn = root.querySelector("[data-gsc-disconnect]");
    if (discBtn) discBtn.hidden = !hasProperty;
  }

  function applyDataPendingState(propertyId, apiReady) {
    var hasProperty = isValidProperty(propertyId);
    var pending = hasProperty && !apiReady;

    setVisible(root.querySelector("[data-gsc-api-data]"), apiReady);
    setVisible(root.querySelector("[data-gsc-api-pending]"), pending);
    setVisible(root.querySelector("[data-idx-api-data]"), apiReady);
    setVisible(root.querySelector("[data-idx-api-pending]"), pending);
    setVisible(root.querySelector("[data-idx-disconnected]"), !hasProperty);

    if (!apiReady) {
      renderTopPages(pending ? "pending" : "empty");
      renderQueries(pending ? "pending" : "empty");
      renderExec(pending ? "pending" : "empty");
      setTrendPending(pending);
    } else {
      var trendEmpty = root.querySelector("[data-trend-empty]");
      if (trendEmpty) trendEmpty.hidden = true;
    }

    if (pending) {
      var idxPending = root.querySelector("[data-idx-api-pending]");
      if (idxPending) idxPending.textContent = PENDING_MSG;
    }
  }

  function applyGscBundle(bundle) {
    var propertyId = getSavedProperty() || (bundle && bundle.property) || "";
    var apiReady = hasApiData(bundle);

    applyPropertyState(propertyId);
    applyDataPendingState(propertyId, apiReady);

    if (!apiReady) return;

    var gsc = {
      connected: true,
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

  function pendingHtml() {
    return '<p class="seo-reality__pending">' + PENDING_MSG + "</p>";
  }

  function renderTopPages(rows) {
    var wrap = root.querySelector("[data-top-pages-wrap]");
    if (!wrap) return;
    if (rows === "pending") {
      wrap.innerHTML = pendingHtml();
      return;
    }
    if (rows === "empty") {
      wrap.innerHTML =
        '<p class="seo-reality__empty">Lưu Property ID để theo dõi top pages.</p>';
      return;
    }
    if (!rows || !rows.length) {
      wrap.innerHTML = pendingHtml();
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
    if (rows === "pending") {
      list.innerHTML = '<li class="seo-reality__pending">' + PENDING_MSG + "</li>";
      return;
    }
    if (rows === "empty") {
      list.innerHTML =
        '<li class="seo-reality__empty">Lưu Property ID để theo dõi query insights.</li>';
      return;
    }
    if (!rows || !rows.length) {
      list.innerHTML = '<li class="seo-reality__pending">' + PENDING_MSG + "</li>";
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
    if (lines === "pending") {
      list.innerHTML = '<li class="seo-reality__pending">' + PENDING_MSG + "</li>";
      return;
    }
    if (lines === "empty") {
      list.innerHTML =
        '<li class="seo-reality__empty">Lưu Property ID để nhận executive summary.</li>';
      return;
    }
    if (!lines || !lines.length) {
      list.innerHTML = '<li class="seo-reality__pending">' + PENDING_MSG + "</li>";
      return;
    }
    list.innerHTML = lines.map(function (l) {
      return "<li>" + l + "</li>";
    }).join("");
  }

  function setTrendPending(pending) {
    var empty = root.querySelector("[data-trend-empty]");
    var canvas = root.querySelector("[data-trend-canvas]");
    if (empty) {
      empty.hidden = false;
      empty.className = pending ? "seo-reality__pending" : "seo-reality__empty";
      empty.textContent = pending
        ? PENDING_MSG
        : "Lưu Property ID để xem growth trend.";
    }
    if (canvas) canvas.style.opacity = pending ? "0.35" : "";
  }

  function drawTrend(trend) {
    var canvas = root.querySelector("[data-trend-canvas]");
    var empty = root.querySelector("[data-trend-empty]");
    if (!canvas || !canvas.getContext) return;
    var rows = (trend && trend[trendMode]) || [];
    if (!rows.length) {
      setTrendPending(!!getSavedProperty());
      return;
    }
    if (empty) empty.hidden = true;
    canvas.style.opacity = "";
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
      var val = input ? input.value.trim() : "";
      if (!isValidProperty(val)) {
        showValidation("Vui lòng nhập GSC Property ID hợp lệ.");
        if (input) input.focus();
        return;
      }
      showValidation("");
      if (connectBtn) connectBtn.classList.add("is-loading");
      setSavedProperty(val);
      applyPropertyState(val);
      applyDataPendingState(val, false);
      showSuccess();
      setTimeout(hideSuccess, SUCCESS_HOLD_MS);
      if (connectBtn) connectBtn.classList.remove("is-loading");
      // Optional server sync when admin session + API credentials exist.
      if (api && sid()) {
        fetch(api + "/gsc/property", {
          method: "POST",
          headers: {
            Authorization: "Bearer " + sid(),
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ property: val }),
        })
          .then(function (res) {
            return res.ok ? res.json() : null;
          })
          .then(function (body) {
            if (body && body.metrics) {
              applyGscBundle(body.metrics);
              cacheSet(body.metrics);
            } else {
              refreshApiData();
            }
          })
          .catch(function () {
            refreshApiData();
          });
      } else {
        refreshApiData();
      }
    }

    if (form) {
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        submitConnect();
      });
    }

    if (discBtn) {
      discBtn.addEventListener("click", function () {
        discBtn.classList.add("is-loading");
        var apiCall =
          api && sid()
            ? fetch(api + "/gsc/disconnect", {
                method: "POST",
                headers: { Authorization: "Bearer " + sid() },
              }).catch(function () {})
            : Promise.resolve();
        apiCall.then(function () {
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

    function handleDisconnected() {
      try {
        sessionStorage.removeItem(PENDING_KEY);
      } catch (e) {}
      try {
        localStorage.removeItem(CACHE_KEY);
      } catch (e) {}
      clearSavedProperty();
      hideSuccess();
      applyPropertyState("");
      applyDataPendingState("", false);
      if (input) input.value = DEFAULT_PROPERTY;
      if (discBtn) discBtn.hidden = true;
      if (form) form.hidden = false;
      if (reconnectWrap) reconnectWrap.hidden = true;
    }

    var saved = getSavedProperty();
    if (input && !saved) input.value = DEFAULT_PROPERTY;
    if (saved) {
      applyPropertyState(saved);
      applyDataPendingState(saved, false);
    }
    if (reconnectWrap && session && saved) reconnectWrap.hidden = false;

    if (api) {
      fetch(api + "/gsc/status", { cache: "no-store" })
        .then(function (r) {
          return r.ok ? r.json() : null;
        })
        .then(function (st) {
          if (!st) return;
          if (!getSavedProperty() && isValidProperty(st.property)) {
            setSavedProperty(st.property);
            applyPropertyState(st.property);
            applyDataPendingState(st.property, false);
            if (input) input.value = st.property;
          }
        })
        .catch(function () {});
    }
  }

  function refreshApiData() {
    fetchLive()
      .then(function (live) {
        if (live && hasApiData(live)) {
          applyGscBundle(live);
          cacheSet(live);
          return;
        }
        return fetchStaticFallback().then(function (fb) {
          if (fb && hasApiData(fb)) {
            applyGscBundle(fb);
            cacheSet(fb);
          } else {
            var prop = getSavedProperty();
            applyPropertyState(prop);
            applyDataPendingState(prop, false);
          }
        });
      })
      .catch(function () {
        var prop = getSavedProperty();
        applyPropertyState(prop);
        applyDataPendingState(prop, false);
      });
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
    var saved = getSavedProperty();
    if (saved) {
      applyPropertyState(saved);
      applyDataPendingState(saved, false);
    }

    var embedded = readEmbedded();
    var embeddedBundle = bundleFromEmbedded(embedded);
    if (embeddedBundle && hasApiData(embeddedBundle)) applyGscBundle(embeddedBundle);

    var c = cacheGet();
    var stale = !c || Date.now() - c.at >= TTL_MS;
    if (!stale && c.payload && hasApiData(c.payload)) applyGscBundle(c.payload);

    if (stale || !c || !hasApiData(c && c.payload)) refreshApiData();

    bindTrendTabs();
    setupAdmin();

    var connectedSignal =
      location.hash.indexOf("gsc_connected=1") >= 0 ||
      location.search.indexOf("gsc_connected=1") >= 0;
    if (connectedSignal) {
      history.replaceState(null, "", location.pathname);
      try {
        sessionStorage.removeItem(PENDING_KEY);
      } catch (e) {}
      refreshApiData();
    }

    var errMatch = (location.hash + " " + location.search).match(/gsc_error=([a-z_]+)/i);
    if (errMatch) {
      history.replaceState(null, "", location.pathname);
      var errEl = root.querySelector("[data-gsc-error]");
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent =
          "Đồng bộ GSC API chưa hoàn tất (" +
          errMatch[1] +
          "). Property ID vẫn được lưu cục bộ.";
      }
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
