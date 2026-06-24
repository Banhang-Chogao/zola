(function () {
  "use strict";

  var REPO = "Banhang-Chogao/zola";
  var API_URL = window.SEOMONEY_HEARTBEAT_API || "https://blog-vipzone-api.onrender.com/api/blog-heartbeat";
  var RUNS_URL = "https://api.github.com/repos/" + REPO + "/actions/runs?per_page=10";
  var PRS_URL = "https://api.github.com/repos/" + REPO + "/pulls?state=open&per_page=10";
  var STATIC_URL = "/data/blog-heartbeat.json";
  var CACHE_KEY = "seomoney.blogHeartbeat.payload.v2";

  function esc(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function pick(obj, keys) {
    for (var i = 0; i < keys.length; i++) {
      var key = keys[i];
      if (obj && obj[key] !== undefined && obj[key] !== null && obj[key] !== "") return obj[key];
    }
    return "";
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
    if (!iso || typeof iso !== "string") return "chưa rõ";
    try {
      return new Date(iso).toLocaleString("vi-VN", {
        hour: "2-digit",
        minute: "2-digit",
        day: "2-digit",
        month: "2-digit"
      });
    } catch (e) {
      return "chưa rõ";
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

    var status = String(
      pick(payload, ["status", "state", "health", "result"]) || "ok"
    ).toLowerCase();
    var message = pick(payload, ["message", "title", "description", "name"]) || "Blog đang hoạt động";
    var lastCheck = pick(payload, ["last_check", "generated_at", "updated_at", "last_updated", "timestamp"]);
    var totalPosts = pick(payload, ["total_posts", "posts_total", "live_posts"]);

    var ok = (
      status.indexOf("ok") !== -1 ||
      status.indexOf("pass") !== -1 ||
      status.indexOf("success") !== -1 ||
      status.indexOf("healthy") !== -1 ||
      status === "live"
    );

    bar.className = "sm-heartbeat-bar sm-heartbeat-bar--" + (ok ? "ok" : "warn");

    var sourceLabel = payload.source === "render-api"
      ? "Render live"
      : payload.source === "github-browser-api"
        ? "GitHub live"
        : payload.source === "static-json"
          ? "JSON fallback"
          : payload.source === "browser-cache"
            ? "cache"
            : "chờ dữ liệu";

    var metaParts = [];
    if (totalPosts) metaParts.push(totalPosts + " bài");
    metaParts.push(sourceLabel);
    if (lastCheck) metaParts.push(formatTime(lastCheck));

    bar.innerHTML =
      '<a class="sm-heartbeat-bar__link" href="/tools/blog-heart-beat/">' +
        '<span class="sm-heartbeat-bar__dot" aria-hidden="true"></span>' +
        '<span class="sm-heartbeat-bar__main">' + esc(message) + '</span>' +
        '<span class="sm-heartbeat-bar__meta">' +
          esc(metaParts.join(" · ")) +
        '</span>' +
        '<span class="sm-heartbeat-bar__latest">' + (ok ? "Đang ổn" : "Cần xem") + '</span>' +
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
