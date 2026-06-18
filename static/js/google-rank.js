/**
 * Google Rank sidebar — optional 12h refresh from static/data/google-rank.json.
 * Build-time HTML is the source of truth; fetch only updates if newer file exists.
 */
(function () {
  "use strict";

  var CACHE_KEY = "zola-google-rank-cache";
  var TTL_MS = 12 * 60 * 60 * 1000;

  var root = document.querySelector("[data-google-rank-root]");
  if (!root) return;

  var dataEl = document.getElementById("google-rank-data");
  var base = (function () {
    var m = document.querySelector('meta[name="zola-base-url"]');
    return m && m.content ? m.content.replace(/\/$/, "") : "";
  })();

  function tierForScore(score) {
    if (score >= 81) return "elite";
    if (score >= 61) return "high";
    if (score >= 41) return "mid-high";
    if (score >= 31) return "mid";
    if (score >= 11) return "mid-low";
    return "low";
  }

  function applyPayload(payload) {
    if (!payload || payload.score == null) return;

    var score = Number(payload.score);
    root.setAttribute("data-score-tier", tierForScore(score));

    var scoreNum = root.querySelector("[data-gr-score]");
    var levelEl = root.querySelector("[data-gr-level]");
    var emojiEl = root.querySelector("[data-gr-emoji]");
    var bar = root.querySelector("[data-gr-bar]");
    var barFill = root.querySelector("[data-gr-bar-fill]");
    var badge = root.querySelector("[data-gr-badge]");

    if (scoreNum) scoreNum.textContent = String(score);
    if (levelEl && payload.level) levelEl.textContent = String(payload.level).toUpperCase();
    if (emojiEl && payload.level_emoji) emojiEl.textContent = payload.level_emoji;
    if (bar) {
      bar.setAttribute("aria-valuenow", String(score));
      bar.setAttribute("data-score", String(score));
    }
    if (barFill) barFill.style.width = score + "%";
    if (badge && payload.level_slug) {
      badge.className = "google-rank__badge google-rank__badge--" + payload.level_slug;
    }

    var d = payload.details || {};
    var map = [
      ["data-gr-pages", d.pages_indexed],
      ["data-gr-articles", d.articles],
      ["data-gr-categories", d.categories],
      ["data-gr-links", d.internal_links],
      ["data-gr-schema", d.schema_coverage_pct != null ? d.schema_coverage_pct + "%" : null],
      ["data-gr-audit", d.seo_audit != null ? d.seo_audit + "/100" : null],
    ];
    map.forEach(function (pair) {
      var el = root.querySelector("[" + pair[0] + "]");
      if (el && pair[1] != null) el.textContent = String(pair[1]);
    });
  }

  function readEmbedded() {
    if (!dataEl) return null;
    try {
      return JSON.parse(dataEl.textContent || "{}");
    } catch (e) {
      return null;
    }
  }

  function cacheGet() {
    try {
      var raw = localStorage.getItem(CACHE_KEY);
      if (!raw) return null;
      return JSON.parse(raw);
    } catch (e) {
      return null;
    }
  }

  function cacheSet(payload) {
    try {
      localStorage.setItem(
        CACHE_KEY,
        JSON.stringify({ fetched_at: Date.now(), payload: payload })
      );
    } catch (e) {}
  }

  function shouldRefresh() {
    var c = cacheGet();
    if (!c || !c.fetched_at) return true;
    return Date.now() - c.fetched_at >= TTL_MS;
  }

  function fetchRemote() {
    if (!base) return Promise.resolve(null);
    var url = base + "/data/google-rank.json?_=" + Date.now();
    return fetch(url, { credentials: "omit", cache: "no-store" })
      .then(function (res) {
        if (!res.ok) return null;
        return res.json();
      })
      .catch(function () {
        return null;
      });
  }

  function init() {
    var embedded = readEmbedded();
    if (embedded) applyPayload(embedded);

    if (!shouldRefresh()) {
      var cached = cacheGet();
      if (cached && cached.payload) applyPayload(cached.payload);
    } else {
      fetchRemote().then(function (remote) {
        if (remote && remote.score != null) {
          applyPayload(remote);
          cacheSet(remote);
        } else if (embedded) {
          cacheSet(embedded);
        }
      });
    }

    fetchAutofixReport();
  }

  function applyAutofixReport(report) {
    if (!report || report.progressPercent == null) return;
    var pct = Number(report.progressPercent);
    var pctEl = root.querySelector("[data-gr-af-pct]");
    var fill = root.querySelector("[data-gr-af-fill]");
    var bar = root.querySelector("[data-gr-af-bar]");
    if (pctEl) pctEl.textContent = String(pct);
    if (fill) fill.style.width = pct + "%";
    if (bar) bar.setAttribute("aria-valuenow", String(pct));

    var map = [
      ["data-gr-af-status", report.statusLabel || report.status],
      ["data-gr-af-before", report.scoreBefore],
      ["data-gr-af-after", report.scoreAfterEstimate],
      ["data-gr-af-fixed", report.fixedCount != null ? report.fixedCount + " lỗi" : null],
      ["data-gr-af-unfixed", report.unfixedCount != null ? report.unfixedCount + " lỗi" : null],
      ["data-gr-af-manual", report.manualReviewCount != null ? report.manualReviewCount + " mục" : null],
      ["data-gr-af-task", report.currentTask],
      ["data-gr-af-reason", report.blockerReason ? "Lý do: " + report.blockerReason : null],
    ];
    map.forEach(function (pair) {
      var el = root.querySelector("[" + pair[0] + "]");
      if (el && pair[1] != null) el.textContent = String(pair[1]);
    });
  }

  function fetchAutofixReport() {
    if (!base) return;
    var url = base + "/data/seo-rank-autofix-report.json?_=" + Date.now();
    fetch(url, { credentials: "omit", cache: "no-store" })
      .then(function (res) {
        if (!res.ok) return null;
        return res.json();
      })
      .then(function (report) {
        if (report) applyAutofixReport(report);
      })
      .catch(function () {});
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();