/* ============================================================
   CMS-V7 — SEOMONEY Publishing Console (client)
   ============================================================
   Built from scratch. Talks to the site's single first-party auth
   backend (config.extra.cms_auth_url → meta zola-cms-auth-api):
     GET  /auth/login?return_to=…   → GitHub OAuth round trip
     GET  /auth/me                  → current session profile
     POST /auth/logout              → end session
     POST /cms/save-post            → commit a post to the repo (server holds
                                       the GitHub token; we send Bearer <sid>)
   Post metadata is baked at build time into <script type="application/json">
   blocks (the standard Zola way to hand server data to client JS).
   ------------------------------------------------------------ */
(function () {
  "use strict";

  /* ─────────── Config ─────────── */
  function meta(name) {
    var m = document.querySelector('meta[name="' + name + '"]');
    return (m && m.getAttribute("content")) || "";
  }
  var AUTH_API = meta("zola-cms-auth-api").replace(/\/$/, "");
  var SID_KEY = "zola-cms-session-id";
  var DRAFT_PREFIX = "cmsv7-draft-";
  var ME_TIMEOUT_MS = 8000;

  var app = document.getElementById("cmsv7-app");
  if (!app) return;

  /* ─────────── DOM ─────────── */
  var views = {
    login: app.querySelector('[data-cmsv7-view="login"]'),
    denied: app.querySelector('[data-cmsv7-view="denied"]'),
    app: app.querySelector('[data-cmsv7-view="app"]'),
  };
  var panels = {
    dashboard: app.querySelector('[data-cmsv7-panel="dashboard"]'),
    editor: app.querySelector('[data-cmsv7-panel="editor"]'),
  };
  var el = {
    error: app.querySelector("[data-cmsv7-error]"),
    hint: app.querySelector("[data-cmsv7-hint]"),
    deniedDetail: app.querySelector("[data-cmsv7-denied-detail]"),
    rail: app.querySelector("[data-cmsv7-rail]"),
    topbarTitle: app.querySelector("[data-cmsv7-topbar-title]"),
    userbar: app.querySelector("[data-cmsv7-userbar]"),
    avatar: app.querySelector("[data-cmsv7-avatar]"),
    username: app.querySelector("[data-cmsv7-username]"),
    useremail: app.querySelector("[data-cmsv7-useremail]"),
    guestbar: app.querySelector("[data-cmsv7-guestbar]"),
    readonlyBanner: app.querySelector("[data-cmsv7-readonly-banner]"),
    loginBtns: app.querySelectorAll('[data-cmsv7-action="github-login"]'),
    list: app.querySelector("[data-cmsv7-list]"),
    search: app.querySelector("[data-cmsv7-search]"),
    sort: app.querySelector("[data-cmsv7-sort]"),
    tabs: app.querySelectorAll("[data-cmsv7-filter]"),
    counts: {
      all: app.querySelector('[data-cmsv7-count="all"]'),
      published: app.querySelector('[data-cmsv7-count="published"]'),
      scheduled: app.querySelector('[data-cmsv7-count="scheduled"]'),
      drafts: app.querySelector('[data-cmsv7-count="drafts"]'),
    },
    kpi: {
      total: app.querySelector('[data-cmsv7-kpi="total"]'),
      published: app.querySelector('[data-cmsv7-kpi="published"]'),
      scheduled: app.querySelector('[data-cmsv7-kpi="scheduled"]'),
      drafts: app.querySelector('[data-cmsv7-kpi="drafts"]'),
      seo: app.querySelector('[data-cmsv7-kpi="seo"]'),
      seoSub: app.querySelector('[data-cmsv7-kpi-sub="seo"]'),
    },
    /* editor */
    f: {
      title: app.querySelector('[data-cmsv7-field="title"]'),
      description: app.querySelector('[data-cmsv7-field="description"]'),
      slug: app.querySelector('[data-cmsv7-field="slug"]'),
      section: app.querySelector('[data-cmsv7-field="section"]'),
      category: app.querySelector('[data-cmsv7-field="category"]'),
      tags: app.querySelector('[data-cmsv7-field="tags"]'),
      cover: app.querySelector('[data-cmsv7-field="cover"]'),
      body: app.querySelector('[data-cmsv7-field="body"]'),
    },
    saveStatus: app.querySelector("[data-cmsv7-save-status]"),
    preview: app.querySelector("[data-cmsv7-preview]"),
    previewBody: app.querySelector("[data-cmsv7-preview-body]"),
    previewLabel: app.querySelector("[data-cmsv7-preview-label]"),
    editorNote: app.querySelector("[data-cmsv7-editor-note]"),
  };

  /* ─────────── State ─────────── */
  var state = {
    profile: null,
    posts: [],
    filter: "all",
    sort: "date-desc",
    query: "",
    editingSlug: null,
    editingSection: null,
    slugAuto: true,
    autosaveTimer: null,
  };

  /* ─────────── Baked data ─────────── */
  function parseJson(id, fallback) {
    try {
      var node = document.getElementById(id);
      return node ? JSON.parse(node.textContent) : fallback;
    } catch (e) {
      return fallback;
    }
  }
  var CATEGORIES = parseJson("cmsv7-categories-data", []);
  var SECTIONS = parseJson("cmsv7-sections-data", ["posting"]);

  /* ─────────── Helpers ─────────── */
  function esc(s) {
    if (s == null) return "";
    var d = document.createElement("div");
    d.appendChild(document.createTextNode(String(s)));
    return d.innerHTML;
  }
  function tomlStr(s) {
    return String(s || "").replace(/\\/g, "\\\\").replace(/"/g, '\\"').replace(/\r?\n/g, "\\n");
  }
  function slugify(s) {
    return String(s || "")
      .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
      .replace(/đ/g, "d").replace(/Đ/g, "d")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 80);
  }
  var VALID_SLUG = /^[a-z0-9][a-z0-9-]{1,79}$/;
  function todayVN() {
    // en-CA locale → "YYYY-MM-DD"; pinned to GMT+7 per the site date rules.
    try {
      return new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Ho_Chi_Minh" });
    } catch (e) {
      return new Date().toISOString().slice(0, 10);
    }
  }
  function fmtDate(iso) {
    if (!iso) return "—";
    try {
      var d = new Date(iso);
      if (isNaN(d.getTime())) return String(iso).slice(0, 10);
      return d.toLocaleDateString("vi-VN", {
        day: "2-digit", month: "2-digit", year: "numeric", timeZone: "Asia/Ho_Chi_Minh",
      });
    } catch (e) { return String(iso).slice(0, 10); }
  }
  function statusOf(p) {
    if (p.draft) return "draft";
    if (p.publish_at) return "scheduled";
    return "published";
  }

  /* ─────────── Session ─────────── */
  function getSid() {
    return sessionStorage.getItem(SID_KEY) || localStorage.getItem(SID_KEY) || "";
  }
  function setSid(sid) {
    try { sessionStorage.setItem(SID_KEY, sid); } catch (e) {}
    try { localStorage.setItem(SID_KEY, sid); } catch (e) {}
  }
  function clearSid() {
    try { sessionStorage.removeItem(SID_KEY); } catch (e) {}
    try { localStorage.removeItem(SID_KEY); } catch (e) {}
  }
  /* Consume #sid= fragment + ?success/?auth_error left by the OAuth callback,
     then scrub the URL so a refresh doesn't re-trigger anything. */
  function consumeAuthParams() {
    var authError = "";
    var params = new URLSearchParams(location.search);
    if (params.get("auth_error")) authError = params.get("auth_error");

    var hashSid = "";
    var m = location.hash.match(/sid=([^&]+)/);
    if (m) hashSid = decodeURIComponent(m[1]);
    if (hashSid) setSid(hashSid);

    if (hashSid || params.has("success") || params.has("auth") || params.has("auth_error")) {
      history.replaceState(null, "", location.pathname);
    }
    return authError;
  }

  function fetchMe(sid) {
    if (!AUTH_API) return Promise.reject(new Error("no-auth-api"));
    var ctrl = new AbortController();
    var timer = setTimeout(function () { ctrl.abort(); }, ME_TIMEOUT_MS);
    var headers = {};
    if (sid) headers.Authorization = "Bearer " + sid;
    return fetch(AUTH_API + "/auth/me", {
      credentials: "include", headers: headers, signal: ctrl.signal,
    }).then(function (r) {
      clearTimeout(timer);
      if (r.status === 401 || r.status === 403) return null;
      if (!r.ok) throw new Error("me-" + r.status);
      return r.json();
    }).catch(function (e) {
      clearTimeout(timer);
      throw e;
    });
  }

  function isAdmin(profile) {
    return !!(profile && profile.authenticated &&
      (profile.is_admin || profile.is_super) &&
      profile.account_type !== "commenter");
  }
  function canWrite() { return isAdmin(state.profile); }
  function handle(profile) {
    if (!profile) return "khách";
    return profile.username || profile.name || profile.email || "khách";
  }

  function startLogin() {
    if (!AUTH_API) { showLoginHint(); return; }
    var returnTo = location.origin + location.pathname; // e.g. https://seomoney.org/cms-v7/
    location.href = AUTH_API + "/auth/login?return_to=" + encodeURIComponent(returnTo);
  }
  function showLoginHint() { if (el.hint) el.hint.hidden = false; }

  function logout() {
    var sid = getSid();
    if (AUTH_API && sid) {
      fetch(AUTH_API + "/auth/logout", {
        method: "POST", credentials: "include",
        headers: { Authorization: "Bearer " + sid },
      }).catch(function () {});
    }
    clearSid();
    state.profile = null;
    showLogin();
  }

  /* ─────────── View routing ─────────── */
  function showView(name) {
    Object.keys(views).forEach(function (k) { if (views[k]) views[k].hidden = k !== name; });
  }
  function showPanel(name) {
    Object.keys(panels).forEach(function (k) { if (panels[k]) panels[k].hidden = k !== name; });
    if (el.topbarTitle) el.topbarTitle.textContent = name === "editor" ? "Trình soạn thảo" : "Tổng quan";
    app.querySelectorAll("[data-cmsv7-nav]").forEach(function (b) {
      b.classList.toggle("is-active", b.getAttribute("data-cmsv7-nav") === (name === "editor" ? "" : "overview"));
    });
  }

  function showLogin(errorMsg) {
    showView("login");
    if (el.error) {
      el.error.hidden = !errorMsg;
      el.error.textContent = errorMsg || "";
    }
    if (!AUTH_API) showLoginHint();
  }
  function showDenied(profile) {
    showView("denied");
    if (el.deniedDetail) {
      el.deniedDetail.textContent = "Đăng nhập với: " + handle(profile) +
        (profile && profile.email ? " (" + profile.email + ")" : "");
    }
  }
  function showApp() {
    showView("app");
    showPanel("dashboard");
    reflectAuthUI();
    renderDashboard();
    populateEditorSelectors();
  }

  function reflectAuthUI() {
    var write = canWrite();
    if (el.userbar) el.userbar.hidden = !write;
    if (el.guestbar) el.guestbar.hidden = write;
    if (el.readonlyBanner) el.readonlyBanner.hidden = write;
    el.loginBtns.forEach(function (b) { b.hidden = write || !AUTH_API; });
    if (write && state.profile) {
      if (el.avatar) el.avatar.src = state.profile.avatar_url || state.profile.avatar || "";
      if (el.username) el.username.textContent = state.profile.name || handle(state.profile);
      if (el.useremail) el.useremail.textContent = state.profile.email || "";
    }
    app.querySelectorAll('[data-cmsv7-action="new-post"]').forEach(function (b) {
      b.setAttribute("aria-disabled", write ? "false" : "true");
      b.title = write ? "Viết bài mới" : "Đăng nhập để tạo bài";
    });
  }

  /* ─────────── Dashboard ─────────── */
  function loadPosts() {
    if (state.posts.length) return state.posts;
    state.posts = parseJson("cmsv7-posts-data", []);
    return state.posts;
  }

  function computeKpi() {
    var posts = loadPosts();
    var k = { total: posts.length, published: 0, scheduled: 0, drafts: 0, seoSum: 0, seoN: 0 };
    posts.forEach(function (p) {
      var s = statusOf(p);
      if (s === "published") k.published++;
      else if (s === "scheduled") k.scheduled++;
      else k.drafts++;
      if (typeof p.seo_score === "number") { k.seoSum += p.seo_score; k.seoN++; }
    });
    return k;
  }
  function renderKpi() {
    var k = computeKpi();
    if (el.kpi.total) el.kpi.total.textContent = k.total;
    if (el.kpi.published) el.kpi.published.textContent = k.published;
    if (el.kpi.scheduled) el.kpi.scheduled.textContent = k.scheduled;
    if (el.kpi.drafts) el.kpi.drafts.textContent = k.drafts;
    if (el.kpi.seo) el.kpi.seo.textContent = k.seoN ? Math.round(k.seoSum / k.seoN) : "—";
    if (el.kpi.seoSub) el.kpi.seoSub.textContent = k.seoN ? ("từ " + k.seoN + " bài đã chấm") : "chưa có dữ liệu chấm";
  }

  function updateCounts() {
    var posts = loadPosts();
    var c = { all: posts.length, published: 0, scheduled: 0, drafts: 0 };
    posts.forEach(function (p) {
      var s = statusOf(p);
      if (s === "published") c.published++;
      else if (s === "scheduled") c.scheduled++;
      else c.drafts++;
    });
    Object.keys(el.counts).forEach(function (k) { if (el.counts[k]) el.counts[k].textContent = c[k]; });
  }

  function filteredPosts() {
    var q = state.query.toLowerCase();
    var out = loadPosts().filter(function (p) {
      var s = statusOf(p);
      if (state.filter === "published" && s !== "published") return false;
      if (state.filter === "scheduled" && s !== "scheduled") return false;
      if (state.filter === "drafts" && s !== "draft") return false;
      if (!q) return true;
      return (p.title && p.title.toLowerCase().indexOf(q) !== -1) ||
        (p.slug && p.slug.toLowerCase().indexOf(q) !== -1) ||
        (p.category && p.category.toLowerCase().indexOf(q) !== -1) ||
        (p.tags && p.tags.some(function (t) { return t.toLowerCase().indexOf(q) !== -1; }));
    });
    out.sort(function (a, b) {
      switch (state.sort) {
        case "date-asc": return String(a.date).localeCompare(String(b.date));
        case "title-asc": return String(a.title || "").localeCompare(String(b.title || ""), "vi");
        case "title-desc": return String(b.title || "").localeCompare(String(a.title || ""), "vi");
        case "seo-desc": return (b.seo_score || 0) - (a.seo_score || 0);
        default: return String(b.date).localeCompare(String(a.date));
      }
    });
    return out;
  }

  function seoClass(grade, score) {
    var g = (grade || "").charAt(0).toUpperCase();
    if (g === "A" || score >= 90) return "cmsv7-seo--a";
    if (g === "B" || score >= 80) return "cmsv7-seo--b";
    if (g === "C" || score >= 65) return "cmsv7-seo--c";
    if (score != null) return "cmsv7-seo--d";
    return "";
  }

  function renderList() {
    if (!el.list) return;
    var write = canWrite();
    var rows = filteredPosts();
    if (!rows.length) {
      el.list.innerHTML =
        '<div class="cmsv7-list__empty">' +
        '<svg viewBox="0 0 20 20" width="34" height="34" fill="currentColor" aria-hidden="true"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clip-rule="evenodd"/></svg>' +
        "<p>Không có bài" + (state.query ? ' khớp "' + esc(state.query) + '"' : " trong nhóm này") + ".</p>" +
        (write ? '<button type="button" class="cmsv7-btn cmsv7-btn--primary cmsv7-btn--sm" data-cmsv7-action="new-post">Viết bài đầu tiên</button>'
               : (AUTH_API ? '<button type="button" class="cmsv7-btn cmsv7-btn--primary cmsv7-btn--sm" data-cmsv7-action="github-login">Đăng nhập để viết</button>' : "")) +
        "</div>";
      return;
    }
    var html = "";
    rows.forEach(function (p) {
      var s = statusOf(p);
      var badge = s === "published"
        ? '<span class="cmsv7-badge cmsv7-badge--green">Đã đăng</span>'
        : s === "scheduled" ? '<span class="cmsv7-badge cmsv7-badge--amber">Lên lịch</span>'
                            : '<span class="cmsv7-badge cmsv7-badge--gray">Nháp</span>';
      var thumb = (p.thumbnail || p.image || "").trim();
      var thumbHtml = thumb
        ? '<img class="cmsv7-row__thumb" src="' + esc(thumb) + '" alt="" width="46" height="34" loading="lazy" decoding="async">'
        : '<span class="cmsv7-row__thumb cmsv7-row__thumb--ph">S</span>';
      var seoHtml = (p.seo_score != null || p.seo_grade)
        ? '<span class="cmsv7-seo ' + seoClass(p.seo_grade, p.seo_score) + '">' + (p.seo_grade ? esc(p.seo_grade) : Math.round(p.seo_score)) + "</span>"
        : '<span class="cmsv7-seo">–</span>';
      var actions = '<a class="cmsv7-row__act" href="' + esc(p.permalink) + '" target="_blank" rel="noopener" title="Xem trên site" aria-label="Xem">' +
        '<svg viewBox="0 0 20 20" width="16" height="16" fill="currentColor" aria-hidden="true"><path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z"/><path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 100-2H5z"/></svg></a>';
      if (write) {
        actions = '<button type="button" class="cmsv7-row__act" data-cmsv7-edit="' + esc(p.slug) + '" data-cmsv7-edit-section="' + esc(p.section) + '" title="Chỉnh sửa" aria-label="Chỉnh sửa">' +
          '<svg viewBox="0 0 20 20" width="16" height="16" fill="currentColor" aria-hidden="true"><path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"/></svg></button>' + actions;
      }
      html += '<div class="cmsv7-row" role="listitem">' +
        '<div class="cmsv7-row__main">' + thumbHtml +
        '<span class="cmsv7-row__titles"><span class="cmsv7-row__title">' + esc(p.title || "(không tiêu đề)") + "</span>" +
        '<span class="cmsv7-row__desc">' + esc((p.description || "").slice(0, 90)) + "</span></span></div>" +
        '<span class="cmsv7-row__status">' + badge + "</span>" +
        '<span class="cmsv7-row__date">' + fmtDate(p.date) + "</span>" +
        '<span class="cmsv7-row__seo">' + seoHtml + "</span>" +
        '<span class="cmsv7-row__actions">' + actions + "</span>" +
        "</div>";
    });
    el.list.innerHTML = html;
  }

  function renderDashboard() {
    loadPosts();
    renderKpi();
    updateCounts();
    renderList();
  }

  /* ─────────── Editor selectors ─────────── */
  function populateEditorSelectors() {
    if (el.f.section && !el.f.section.options.length) {
      SECTIONS.forEach(function (s) {
        var o = document.createElement("option");
        o.value = s; o.textContent = s;
        el.f.section.appendChild(o);
      });
    }
    if (el.f.category && el.f.category.options.length <= 1) {
      CATEGORIES.forEach(function (c) {
        if (c === "Tất cả") return; // added automatically at publish time
        var o = document.createElement("option");
        o.value = c; o.textContent = c;
        el.f.category.appendChild(o);
      });
    }
  }

  /* ─────────── Editor ─────────── */
  function setStatus(kind) {
    if (!el.saveStatus) return;
    var labels = { saving: "Đang lưu…", saved: "Đã lưu nháp", unsaved: "Chưa lưu" };
    el.saveStatus.textContent = labels[kind] || kind;
    el.saveStatus.className = "cmsv7-editor__status cmsv7-editor__status--" + kind;
  }
  function draftKey() { return DRAFT_PREFIX + (state.editingSlug || "new"); }
  function readDraft() {
    try { var raw = localStorage.getItem(draftKey()); return raw ? JSON.parse(raw) : null; } catch (e) { return null; }
  }
  function saveDraft() {
    try { localStorage.setItem(draftKey(), JSON.stringify(collect())); } catch (e) {}
  }
  function clearDraft(slug) {
    try { localStorage.removeItem(DRAFT_PREFIX + (slug || "new")); } catch (e) {}
  }
  function collect() {
    return {
      title: el.f.title ? el.f.title.value : "",
      description: el.f.description ? el.f.description.value : "",
      slug: el.f.slug ? el.f.slug.value : "",
      section: el.f.section ? el.f.section.value : "posting",
      category: el.f.category ? el.f.category.value : "",
      tags: el.f.tags ? el.f.tags.value : "",
      cover: el.f.cover ? el.f.cover.value : "",
      body: el.f.body ? el.f.body.value : "",
    };
  }
  function apply(values) {
    if (el.f.title) el.f.title.value = values.title || "";
    if (el.f.description) el.f.description.value = values.description || "";
    if (el.f.slug) el.f.slug.value = values.slug || "";
    if (el.f.section) el.f.section.value = values.section || "posting";
    if (el.f.category) {
      var cat = values.category || (values.categories || []).filter(function (c) { return c !== "Tất cả"; })[0] || "";
      el.f.category.value = cat;
    }
    if (el.f.tags) el.f.tags.value = Array.isArray(values.tags) ? values.tags.join(", ") : (values.tags || "");
    if (el.f.cover) el.f.cover.value = values.cover || values.thumbnail || values.image || "";
    if (el.f.body) el.f.body.value = values.body || "";
  }

  function setNote(text) {
    if (!el.editorNote) return;
    el.editorNote.hidden = !text;
    el.editorNote.textContent = text || "";
  }

  /* Load an existing post's raw markdown from the public repo via the GitHub
     Contents API (api.github.com is on the site CSP allowlist; raw.githubusercontent
     is not). Unauthenticated + rate-limited to 60/hr per IP — plenty for editing. */
  var GH_CONTENTS = "https://api.github.com/repos/Banhang-Chogao/zola/contents/content/";
  function fetchRawPost(section, slug) {
    var url = GH_CONTENTS + section + "/" + slug + ".md?ref=main";
    return fetch(url, { headers: { Accept: "application/vnd.github.raw" }, cache: "no-store" })
      .then(function (r) { if (!r.ok) throw new Error("gh-" + r.status); return r.text(); });
  }
  function splitFrontmatter(text) {
    var t = String(text || "").replace(/^﻿/, "");
    if (t.slice(0, 3) === "+++") {
      var end = t.indexOf("\n+++", 3);
      if (end !== -1) return { fm: t.slice(3, end), body: t.slice(end + 4).replace(/^\s*\n/, "") };
    }
    return { fm: "", body: t };
  }
  function parseFm(fm) {
    var out = { title: "", description: "", categories: [], tags: [], thumbnail: "" };
    var sec = "root";
    function unq(v) { var m = v.match(/^"([\s\S]*)"$/); return m ? m[1].replace(/\\"/g, '"').replace(/\\n/g, "\n").replace(/\\\\/g, "\\") : v; }
    function arr(v) { return v.replace(/^\[|\]$/g, "").split(",").map(function (x) { return unq(x.trim()); }).filter(Boolean); }
    String(fm).split(/\r?\n/).forEach(function (line) {
      var l = line.trim();
      if (l === "[taxonomies]") { sec = "tax"; return; }
      if (l === "[extra]") { sec = "extra"; return; }
      if (l.charAt(0) === "[") { sec = "other"; return; }
      var eq = l.indexOf("=");
      if (eq === -1) return;
      var key = l.slice(0, eq).trim(), val = l.slice(eq + 1).trim();
      if (sec === "root") {
        if (key === "title") out.title = unq(val);
        else if (key === "description") out.description = unq(val);
      } else if (sec === "tax") {
        if (key === "categories") out.categories = arr(val);
        else if (key === "tags") out.tags = arr(val);
      } else if (sec === "extra") {
        if (key === "thumbnail") out.thumbnail = unq(val);
      }
    });
    return out;
  }

  function openEditor(slug, section) {
    if (!canWrite()) { startLogin(); return; }
    state.editingSlug = slug || null;
    state.editingSection = section || null;
    state.slugAuto = !slug;
    populateEditorSelectors();
    hidePreview();
    showPanel("editor");

    var post = slug ? loadPosts().filter(function (p) { return p.slug === slug && p.section === section; })[0] : null;
    var draft = readDraft();

    if (!post) {
      if (draft) apply(draft); else apply({ section: "posting" });
      setNote("");
      if (el.f.title) el.f.title.focus();
      setStatus("saved");
      return;
    }

    /* Seed fields from baked metadata immediately. */
    apply({
      title: post.title, description: post.description, slug: post.slug,
      section: post.section, category: post.category, categories: post.categories,
      tags: post.tags, cover: post.thumbnail || post.image, body: "",
    });

    if (draft && draft.body) {
      apply(draft);
      setNote("Đang dùng bản nháp cục bộ chưa xuất bản của bài này.");
      setStatus("saved");
      return;
    }

    /* Pull the real body (and authoritative frontmatter) from the repo. */
    setNote("Đang tải nội dung bài từ GitHub…");
    fetchRawPost(post.section, post.slug).then(function (text) {
      var parts = splitFrontmatter(text);
      var pf = parseFm(parts.fm);
      apply({
        title: pf.title || post.title,
        description: pf.description || post.description,
        slug: post.slug, section: post.section,
        categories: pf.categories.length ? pf.categories : post.categories,
        category: pf.categories.filter(function (c) { return c !== "Tất cả"; })[0] || post.category,
        tags: pf.tags, cover: pf.thumbnail || post.thumbnail || post.image,
        body: parts.body,
      });
      setNote("");
      setStatus("saved");
    }).catch(function () {
      setNote("Không tải được nội dung bài từ GitHub (giới hạn tần suất hoặc mạng). Dán lại nội dung rồi Xuất bản để ghi đè.");
    });

    if (el.f.title) el.f.title.focus();
    setStatus("saved");
  }

  function newPost() {
    if (!canWrite()) { startLogin(); return; }
    state.editingSlug = null;
    state.editingSection = null;
    state.slugAuto = true;
    populateEditorSelectors();
    hidePreview();
    apply({ section: "posting" });
    setNote("");
    showPanel("editor");
    if (el.f.title) el.f.title.focus();
    setStatus("saved");
  }

  function backToDashboard() {
    showPanel("dashboard");
    renderDashboard();
  }

  /* markdown toolbar */
  function surround(pre, post) {
    var t = el.f.body; if (!t) return;
    var a = t.selectionStart, b = t.selectionEnd, v = t.value;
    var sel = v.slice(a, b);
    t.value = v.slice(0, a) + pre + sel + post + v.slice(b);
    t.selectionStart = a + pre.length;
    t.selectionEnd = a + pre.length + sel.length;
    t.focus();
    markUnsaved();
  }
  function insert(text) {
    var t = el.f.body; if (!t) return;
    var a = t.selectionStart, v = t.value;
    t.value = v.slice(0, a) + text + v.slice(t.selectionEnd);
    t.selectionStart = t.selectionEnd = a + text.length;
    t.focus();
    markUnsaved();
  }
  var MD = {
    bold: function () { surround("**", "**"); },
    italic: function () { surround("_", "_"); },
    code: function () { surround("`", "`"); },
    heading: function () { insert("\n## "); },
    quote: function () { insert("\n> "); },
    "bullet-list": function () { insert("\n- "); },
    "numbered-list": function () { insert("\n1. "); },
    link: function () {
      var u = prompt("URL liên kết:"); if (!u) return;
      surround("[", "](" + u + ")");
    },
    image: function () {
      var u = prompt("URL ảnh:"); if (!u) return;
      var alt = prompt("Alt text (mô tả ảnh):") || "ảnh minh hoạ";
      insert("\n![" + alt + "](" + u + ")\n");
    },
  };

  /* preview */
  function mdToHtml(src) {
    var h = esc(src);
    h = h
      .replace(/^### (.+)$/gm, "<h3>$1</h3>")
      .replace(/^## (.+)$/gm, "<h2>$1</h2>")
      .replace(/^# (.+)$/gm, "<h1>$1</h1>")
      .replace(/^&gt; (.+)$/gm, "<blockquote>$1</blockquote>")
      .replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" loading="lazy">')
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" rel="noopener">$1</a>')
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>")
      .replace(/_([^_]+)_/g, "<em>$1</em>")
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/^- (.+)$/gm, "<li>$1</li>")
      .replace(/(<li>[\s\S]*?<\/li>)/g, "<ul>$1</ul>")
      .replace(/\n{2,}/g, "</p><p>")
      .replace(/\n/g, "<br>");
    return "<p>" + h + "</p>";
  }
  function hidePreview() {
    if (el.preview) el.preview.hidden = true;
    if (el.f.body) el.f.body.hidden = false;
    if (el.previewLabel) el.previewLabel.textContent = "Xem trước";
  }
  function togglePreview() {
    if (!el.preview || !el.f.body) return;
    if (el.preview.hidden) {
      el.previewBody.innerHTML = mdToHtml(el.f.body.value);
      el.preview.hidden = false;
      el.f.body.hidden = true;
      if (el.previewLabel) el.previewLabel.textContent = "Soạn thảo";
    } else {
      hidePreview();
    }
  }

  /* autosave */
  function markUnsaved() {
    setStatus("unsaved");
    if (state.autosaveTimer) clearTimeout(state.autosaveTimer);
    state.autosaveTimer = setTimeout(function () { saveDraft(); setStatus("saved"); }, 800);
  }

  /* build repo-conformant markdown */
  function buildMarkdown(v, slug) {
    var cats = ["Tất cả"];
    var chosen = (v.category || "").trim();
    if (chosen && chosen !== "Tất cả") cats.push(chosen);
    var catStr = cats.map(function (c) { return '"' + tomlStr(c) + '"'; }).join(", ");
    var tags = (v.tags || "").split(",").map(function (t) { return t.trim(); }).filter(Boolean);
    var tagStr = tags.length ? "[" + tags.map(function (t) { return '"' + tomlStr(t) + '"'; }).join(", ") + "]" : "[]";

    var fm = "+++\n";
    fm += 'title = "' + tomlStr(v.title) + '"\n';
    fm += "date = " + todayVN() + "\n";
    if (v.description && v.description.trim()) fm += 'description = "' + tomlStr(v.description.trim()) + '"\n';
    fm += "\n[taxonomies]\n";
    fm += "categories = [" + catStr + "]\n";
    fm += "tags = " + tagStr + "\n";
    fm += "\n[extra]\n";
    if (v.cover && v.cover.trim()) fm += 'thumbnail = "' + tomlStr(v.cover.trim()) + '"\n';
    fm += "+++\n\n";
    return fm + (v.body || "").trim() + "\n";
  }

  function publish() {
    if (!canWrite()) { startLogin(); return; }
    var sid = getSid();
    if (!sid) { startLogin(); return; }
    var v = collect();
    if (!v.title.trim()) { alert("Cần có tiêu đề."); if (el.f.title) el.f.title.focus(); return; }
    if (!v.body.trim()) { alert("Cần có nội dung thân bài."); if (el.f.body) el.f.body.focus(); return; }
    var slug = (v.slug || "").trim().toLowerCase() || slugify(v.title);
    if (!VALID_SLUG.test(slug)) { alert("Slug không hợp lệ. Chỉ gồm a-z, 0-9 và dấu gạch ngang (2–80 ký tự)."); return; }
    var section = (v.section || "posting").trim();
    var content = buildMarkdown(v, slug);
    var message = "CMS-V7: " + v.title.trim();

    setStatus("saving");
    fetch(AUTH_API + "/cms/save-post", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json", Authorization: "Bearer " + sid },
      body: JSON.stringify({ slug: slug, section: section, content: content, message: message }),
    }).then(function (r) {
      if (r.status === 401 || r.status === 403) {
        clearSid();
        throw new Error("Phiên đăng nhập đã hết hạn. Hãy đăng nhập lại.");
      }
      return r.json().then(function (data) {
        if (!r.ok) throw new Error(data.detail || ("Lỗi " + r.status));
        return data;
      });
    }).then(function (data) {
      setStatus("saved");
      clearDraft(slug);
      alert("Đã xuất bản \"" + v.title.trim() + "\".\n" +
        (data.action === "updated" ? "Bài đã được cập nhật." : "Bài mới đã được tạo.") +
        "\nSite sẽ cập nhật sau 1–2 phút (GitHub Actions build + deploy).");
      backToDashboard();
    }).catch(function (err) {
      setStatus("unsaved");
      alert("Xuất bản thất bại: " + err.message + "\nNội dung của bạn vẫn được lưu nháp cục bộ.");
    });
  }

  /* ─────────── Events ─────────── */
  function bind() {
    /* global click delegation for actions */
    document.addEventListener("click", function (e) {
      var t = e.target.closest("[data-cmsv7-action]");
      if (t) {
        var action = t.getAttribute("data-cmsv7-action");
        if (action === "github-login") { e.preventDefault(); startLogin(); return; }
        if (action === "browse-readonly") { e.preventDefault(); state.profile = null; showApp(); return; }
        if (action === "logout") { e.preventDefault(); logout(); return; }
        if (action === "new-post") { e.preventDefault(); newPost(); return; }
        if (action === "back") { e.preventDefault(); backToDashboard(); return; }
        if (action === "refresh") { e.preventDefault(); state.posts = []; renderDashboard(); return; }
        if (action === "preview-toggle") { e.preventDefault(); togglePreview(); return; }
        if (action === "publish") { e.preventDefault(); publish(); return; }
        if (action === "toggle-rail") { e.preventDefault(); if (el.rail) el.rail.classList.toggle("is-open"); return; }
      }
      var nav = e.target.closest("[data-cmsv7-nav]");
      if (nav) {
        var target = nav.getAttribute("data-cmsv7-nav");
        if (target === "posts" || target === "overview") {
          backToDashboard();
          app.querySelectorAll("[data-cmsv7-nav]").forEach(function (b) { b.classList.remove("is-active"); });
          nav.classList.add("is-active");
          if (target === "posts" && el.search) el.search.scrollIntoView({ behavior: "smooth", block: "center" });
        }
        if (window.innerWidth <= 820 && el.rail) el.rail.classList.remove("is-open");
        return;
      }
      var edit = e.target.closest("[data-cmsv7-edit]");
      if (edit) {
        e.preventDefault();
        openEditor(edit.getAttribute("data-cmsv7-edit"), edit.getAttribute("data-cmsv7-edit-section"));
      }
    });

    /* tabs */
    el.tabs.forEach(function (tab) {
      tab.addEventListener("click", function () {
        state.filter = tab.getAttribute("data-cmsv7-filter");
        el.tabs.forEach(function (b) {
          var on = b === tab;
          b.classList.toggle("is-active", on);
          b.setAttribute("aria-selected", on ? "true" : "false");
        });
        renderList();
      });
    });

    /* search (debounced) */
    if (el.search) {
      var st = null;
      el.search.addEventListener("input", function () {
        clearTimeout(st);
        st = setTimeout(function () { state.query = el.search.value.trim(); renderList(); }, 180);
      });
    }
    /* sort */
    if (el.sort) el.sort.addEventListener("change", function () { state.sort = el.sort.value; renderList(); });

    /* editor: toolbar */
    app.querySelectorAll("[data-cmsv7-md]").forEach(function (b) {
      b.addEventListener("click", function () { var fn = MD[b.getAttribute("data-cmsv7-md")]; if (fn) fn(); });
    });

    /* editor: autosave + auto-slug */
    Object.keys(el.f).forEach(function (key) {
      var node = el.f[key];
      if (!node) return;
      var evt = node.tagName === "SELECT" ? "change" : "input";
      node.addEventListener(evt, markUnsaved);
    });
    if (el.f.title && el.f.slug) {
      el.f.title.addEventListener("input", function () {
        if (state.slugAuto) el.f.slug.value = slugify(el.f.title.value);
      });
      el.f.slug.addEventListener("input", function () {
        state.slugAuto = el.f.slug.value.trim() === "";
      });
    }

    /* keyboard shortcuts (editor only) */
    document.addEventListener("keydown", function (e) {
      if (panels.editor && panels.editor.hidden) return;
      if (!(e.ctrlKey || e.metaKey)) return;
      var k = e.key.toLowerCase();
      if (k === "b") { e.preventDefault(); MD.bold(); }
      else if (k === "i") { e.preventDefault(); MD.italic(); }
      else if (k === "k") { e.preventDefault(); MD.link(); }
      else if (k === "s") { e.preventDefault(); saveDraft(); setStatus("saved"); }
    });
  }

  /* ─────────── Init ─────────── */
  function init() {
    bind();
    var authError = consumeAuthParams();
    var sid = getSid();

    if (!AUTH_API) { showLogin(); return; }
    if (authError) { clearSid(); showLogin("Đăng nhập thất bại: " + authError); return; }

    if (!sid) { showLogin(); return; }

    fetchMe(sid).then(function (profile) {
      if (isAdmin(profile)) {
        state.profile = profile;
        showApp();
      } else if (profile) {
        // Authenticated but not an authorized editor.
        showDenied(profile);
      } else {
        clearSid();
        showLogin();
      }
    }).catch(function () {
      // Backend unreachable / timeout — don't hard-fail; let the user retry or browse.
      showLogin("Không kết nối được máy chủ xác thực. Thử lại hoặc xem ở chế độ chỉ đọc.");
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
