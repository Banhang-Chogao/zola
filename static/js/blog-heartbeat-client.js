(function () {
  "use strict";

  var REPO = "Banhang-Chogao/zola";
  var API_URL = window.SEOMONEY_HEARTBEAT_API || "https://blog-vipzone-api.onrender.com/api/blog-heartbeat";
  var RUNS_URL = "https://api.github.com/repos/" + REPO + "/actions/runs?per_page=10";
  var PRS_URL = "https://api.github.com/repos/" + REPO + "/pulls?state=open&per_page=10";
  var STATIC_URL = "/static/data/blog-heartbeat.json";
  var CACHE_KEY = "seomoney.blogHeartbeat.payload.v2";

  function esc(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function fetchJson(url) {
    return fetch(url, {
      cache: "no-store",
      headers: { "Accept": "application/json" }
    }).then(function (res) {
      if (!res.ok) throw new Error("HTTP " + res.status + " " + url);
      return res.json();
    });
  }

  function runItem(x) {
    return {
      id: x.id || x.databaseId || null,
      title: x.display_title || x.displayTitle || x.name || "Workflow run",
      workflow: x.name || x.workflowName || "GitHub Actions",
      branch: x.head_branch || x.headBranch || "",
      sha: String(x.head_sha || x.headSha || "").slice(0, 7),
      event: x.event || "",
      status: x.status || "",
      conclusion: x.conclusion || "",
      created_at: x.created_at || x.createdAt || "",
      updated_at: x.updated_at || x.updatedAt || "",
      url: x.html_url || x.url || ""
    };
  }

  function prItem(x) {
    return {
      number: x.number,
      title: x.title || "Pull request",
      head: x.head && x.head.ref ? x.head.ref : x.headRefName || "",
      base: x.base && x.base.ref ? x.base.ref : x.baseRefName || "",
      state: x.state || "",
      draft: Boolean(x.draft || x.isDraft),
      merge_state: x.mergeable_state || x.mergeStateStatus || "",
      created_at: x.created_at || x.createdAt || "",
      updated_at: x.updated_at || x.updatedAt || "",
      url: x.html_url || x.url || ""
    };
  }

  function summarize(runs) {
    return {
      in_progress: runs.filter(function (r) { return r.status === "in_progress"; }).length,
      queued: runs.filter(function (r) { return ["queued", "waiting", "requested", "pending"].indexOf(r.status) >= 0; }).length,
      success: runs.filter(function (r) { return r.conclusion === "success"; }).length,
      failure: runs.filter(function (r) { return ["failure", "cancelled", "timed_out", "action_required"].indexOf(r.conclusion) >= 0; }).length
    };
  }

  function normalizeGithub(runsData, prsData) {
    var runs = (runsData.workflow_runs || []).map(runItem);
    var prs = (prsData || []).map(prItem);

    return {
      schema_version: 2,
      ok: true,
      source: "github-browser-api",
      name: "Blog Heart Beat",
      repository: REPO,
      generated_at: new Date().toISOString(),
      summary: summarize(runs),
      pull_requests: prs,
      runs: runs,
      deploy_runs: runs.filter(function (r) {
        return String(r.workflow || "").toLowerCase().indexOf("deploy") >= 0;
      })
    };
  }

  function saveCache(payload) {
    try {
      localStorage.setItem(CACHE_KEY, JSON.stringify({
        saved_at: new Date().toISOString(),
        payload: payload
      }));
    } catch (e) {}
  }

  function readCache() {
    try {
      var raw = localStorage.getItem(CACHE_KEY);
      if (!raw) return null;
      var parsed = JSON.parse(raw);
      if (!parsed || !parsed.payload) return null;
      parsed.payload.source = parsed.payload.source || "browser-cache";
      parsed.payload.cache_saved_at = parsed.saved_at;
      return parsed.payload;
    } catch (e) {
      return null;
    }
  }

  function neutralPayload() {
    return {
      schema_version: 2,
      ok: false,
      source: "neutral",
      name: "Blog Heart Beat",
      repository: REPO,
      generated_at: new Date().toISOString(),
      summary: { in_progress: 0, queued: 0, success: 0, failure: 0 },
      pull_requests: [],
      runs: [],
      deploy_runs: []
    };
  }

  function loadHeartbeat() {
    return fetchJson(API_URL)
      .then(function (payload) {
        payload.source = payload.source || "render-api";
        saveCache(payload);
        return payload;
      })
      .catch(function () {
        return Promise.all([fetchJson(RUNS_URL), fetchJson(PRS_URL)]).then(function (pair) {
          var payload = normalizeGithub(pair[0], pair[1]);
          saveCache(payload);
          return payload;
        });
      })
      .catch(function () {
        return fetchJson(STATIC_URL).then(function (payload) {
          payload.source = payload.source || "static-json";
          saveCache(payload);
          return payload;
        });
      })
      .catch(function () {
        return readCache() || neutralPayload();
      });
  }

  function formatTime(iso) {
    if (!iso) return "chưa rõ";
    try {
      return new Date(iso).toLocaleString("vi-VN", {
        hour: "2-digit",
        minute: "2-digit",
        day: "2-digit",
        month: "2-digit"
      });
    } catch (e) {
      return iso;
    }
  }

  function ensureBar() {
    var bar = document.getElementById("sm-heartbeat-bar");
    if (bar) return bar;

    bar = document.createElement("section");
    bar.id = "sm-heartbeat-bar";
    bar.setAttribute("aria-label", "Blog Heart Beat");

    var footer = document.querySelector("footer, .site-footer, #footer");
    if (footer) {
      footer.prepend(bar);
    } else {
      document.body.prepend(bar);
    }

    return bar;
  }

  function render(payload) {
    var bar = ensureBar();
    var summary = payload.summary || {};
    var prs = payload.pull_requests || [];
    var runs = payload.runs || [];

    var failures = Number(summary.failure || 0);
    var active = Number(summary.in_progress || 0) + Number(summary.queued || 0);
    var state = failures > 0 ? "warn" : active > 0 ? "live" : "ok";

    bar.className = "sm-heartbeat-bar sm-heartbeat-bar--" + state;

    var sourceLabel = payload.source === "render-api"
      ? "Render live"
      : payload.source === "github-browser-api"
        ? "GitHub live"
        : payload.source === "static-json"
          ? "JSON fallback"
          : payload.source === "browser-cache"
            ? "cache"
            : "chờ dữ liệu";

    var title = failures > 0
      ? "Heartbeat: có workflow cần xem"
      : active > 0
        ? "Heartbeat: đang có pipeline chạy"
        : "Heartbeat: blog đang ổn";

    var latestRun = runs[0];
    var latestText = latestRun
      ? ((latestRun.workflow || "GitHub Actions") + " · " + (latestRun.conclusion || latestRun.status || "unknown"))
      : "chưa có run mới";

    bar.innerHTML =
      '<a class="sm-heartbeat-bar__link" href="/tools/blog-heart-beat/">' +
        '<span class="sm-heartbeat-bar__dot" aria-hidden="true"></span>' +
        '<span class="sm-heartbeat-bar__main">' + esc(title) + '</span>' +
        '<span class="sm-heartbeat-bar__meta">' +
          esc(active + ' chạy/chờ · ' + failures + ' lỗi · ' + prs.length + ' PR mở · ' + sourceLabel + ' · cập nhật ' + formatTime(payload.generated_at)) +
        '</span>' +
        '<span class="sm-heartbeat-bar__latest">' + esc(latestText) + '</span>' +
      '</a>';
  }

  function boot() {
    if (!document.body) return;
    render(neutralPayload());
    loadHeartbeat().then(render).catch(function () {
      render(readCache() || neutralPayload());
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
