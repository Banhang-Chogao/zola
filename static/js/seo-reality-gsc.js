/**
 * SEO Reality Check — live Google Search Console hydration.
 * Build-time HTML + fetch /gsc/metrics (20m cache) + admin OAuth controls.
 */
(function () {
  "use strict";

  var CACHE_KEY = "zola-gsc-metrics-cache";
  var TTL_MS = 20 * 60 * 1000;
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

  function setupAdmin() {
    var panel = root.querySelector("[data-gsc-admin]");
    if (!panel || !sid()) return;
    panel.hidden = false;
    var api = authApi();
    var connectBtn = root.querySelector("[data-gsc-connect]");
    var discBtn = root.querySelector("[data-gsc-disconnect]");
    var sel = root.querySelector("[data-gsc-property]");

    if (connectBtn && api) {
      connectBtn.addEventListener("click", function () {
        var rt = encodeURIComponent(location.pathname + location.search);
        location.href = api + "/gsc/oauth/start?return_to=" + rt;
      });
    }
    if (discBtn && api) {
      discBtn.addEventListener("click", function () {
        fetch(api + "/gsc/disconnect", {
          method: "POST",
          headers: { Authorization: "Bearer " + sid() },
        }).then(function () {
          location.reload();
        });
      });
    }
    if (sel && api && sid()) {
      fetch(api + "/gsc/properties", { headers: { Authorization: "Bearer " + sid() } })
        .then(function (r) {
          return r.ok ? r.json() : null;
        })
        .then(function (data) {
          if (!data || !data.properties) return;
          sel.innerHTML = data.properties
            .map(function (p) {
              return '<option value="' + p + '">' + p + "</option>";
            })
            .join("");
          return fetch(api + "/gsc/status").then(function (r) {
            return r.json();
          });
        })
        .then(function (st) {
          if (st && st.property) sel.value = st.property;
          if (discBtn) discBtn.hidden = !(st && st.connected);
        });
      sel.addEventListener("change", function () {
        fetch(api + "/gsc/property", {
          method: "POST",
          headers: {
            Authorization: "Bearer " + sid(),
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ siteUrl: sel.value }),
        }).then(function (r) {
          return r.json();
        }).then(function (data) {
          if (data && data.metrics) {
            applyGscBundle(data.metrics);
            cacheSet(data.metrics);
          }
        });
      });
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

    if (location.hash.indexOf("gsc_connected=1") >= 0) {
      history.replaceState(null, "", location.pathname + location.search);
      fetchLive().then(function (live) {
        if (live) {
          applyGscBundle(live);
          cacheSet(live);
        }
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();