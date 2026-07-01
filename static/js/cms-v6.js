(function () {
  "use strict";

  /* ─── Config ─── */
  var AUTH_API = (function () {
    var m = document.querySelector('meta[name="zola-cms-auth-api"]');
    return (m && m.getAttribute("content")) || "";
  })();
  var BASE_URL = (function () {
    var m = document.querySelector('meta[name="zola-base-url"]');
    return (m && m.getAttribute("content")) || "";
  })();
  var SID_KEY = "zola-cms-session-id";
  var GH_OWNER = "Banhang-Chogao";
  var GH_REPO = "zola";
  var GH_BRANCH = "main";
  var DRAFT_KEY_PREFIX = "cmsv6-draft-";
  var POSTS_DATA = null;

  /* ─── DOM refs ─── */
  var app = document.getElementById("cmsv6-app");
  var views = {
    login: app.querySelector('[data-cmsv6-view="login"]'),
    denied: app.querySelector('[data-cmsv6-view="denied"]'),
    dashboard: app.querySelector('[data-cmsv6-view="dashboard"]'),
    editor: app.querySelector('[data-cmsv6-view="editor"]'),
  };
  var els = {
    error: app.querySelector('[data-cmsv6-error]'),
    hint: app.querySelector('[data-cmsv6-hint]'),
    deniedDetail: app.querySelector('[data-cmsv6-denied-detail]'),
    loginBtns: app.querySelectorAll('[data-cmsv6-action="github-login"]'),
    logoutBtns: app.querySelectorAll('[data-cmsv6-action="logout"]'),
    search: app.querySelector('[data-cmsv6-search]'),
    sort: app.querySelector('[data-cmsv6-sort]'),
    list: app.querySelector('[data-cmsv6-list]'),
    tabs: app.querySelectorAll('[data-cmsv6-tab]'),
    tabBtns: app.querySelectorAll('[data-cmsv6-filter]'),
    countSpans: {
      published: app.querySelector('[data-cmsv6-count="published"]'),
      scheduled: app.querySelector('[data-cmsv6-count="scheduled"]'),
      drafts: app.querySelector('[data-cmsv6-count="drafts"]'),
    },
    userbar: app.querySelector('[data-cmsv6-userbar]'),
    avatar: app.querySelector('[data-cmsv6-avatar]'),
    username: app.querySelector('[data-cmsv6-username]'),
    useremail: app.querySelector('[data-cmsv6-useremail]'),
    guestbar: app.querySelector('[data-cmsv6-guestbar]'),
    guestTitle: app.querySelector('[data-cmsv6-guest-title]'),
    guestCopy: app.querySelector('[data-cmsv6-guest-copy]'),
    readonlyBanner: app.querySelector('[data-cmsv6-readonly-banner]'),
    readonlyCopy: app.querySelector('[data-cmsv6-readonly-copy]'),
    refreshBtn: app.querySelector('[data-cmsv6-action="refresh"]'),
    sidebarTabs: app.querySelector('[data-cmsv6-sidebar-tabs]'),
    sidebarTabBtns: app.querySelectorAll('[data-cmsv6-sidebar-tab]'),
    newPostBtn: app.querySelectorAll('[data-cmsv6-action="new-post"]'),
    toggleSidebar: app.querySelector('[data-cmsv6-action="toggle-sidebar"]'),
    sidebar: app.querySelector('[data-cmsv6-sidebar]'),
    /* Editor */
    editorTitleInput: app.querySelector('[data-cmsv6-title]'),
    editorSubtitleInput: app.querySelector('[data-cmsv6-subtitle]'),
    editorSlugInput: app.querySelector('[data-cmsv6-slug]'),
    editorCategorySelect: app.querySelector('[data-cmsv6-category]'),
    editorTagsInput: app.querySelector('[data-cmsv6-tags]'),
    editorCoverInput: app.querySelector('[data-cmsv6-cover]'),
    editorBody: app.querySelector('[data-cmsv6-body]'),
    editorSaveStatus: app.querySelector('[data-cmsv6-save-status]'),
    editorBack: app.querySelector('[data-cmsv6-action="back-to-dashboard"]'),
    editorPreviewToggle: app.querySelector('[data-cmsv6-action="preview-toggle"]'),
    editorPreview: app.querySelector('[data-cmsv6-preview]'),
    editorPreviewBody: app.querySelector('[data-cmsv6-preview-body]'),
    editorPublishBtn: app.querySelector('[data-cmsv6-action="publish"]'),
    editorToolbarBtns: app.querySelectorAll('[data-cmsv6-md]'),
    mediaWrap: app.querySelector('[data-cmsv6-media-wrap]'),
    mediaMenu: app.querySelector('[data-cmsv6-media-menu]'),
    mediaBtn: app.querySelector('[data-cmsv6-action="media-dropdown"]'),
    editorTitleDisplay: app.querySelector('[data-cmsv6-editor-title]'),
  };

  var currentFilter = "published";
  var currentSort = "date-desc";
  var currentPost = null;
  var currentProfile = null;

  /* ─── Auth ─── */

  function showView(name) {
    Object.keys(views).forEach(function (k) {
      if (views[k]) views[k].hidden = true;
    });
    if (views[name]) views[name].hidden = false;
  }

  function getSid() {
    var sid = sessionStorage.getItem(SID_KEY);
    if (sid) return sid;
    var match = location.hash.match(/sid=([^&]+)/);
    if (match) {
      sid = decodeURIComponent(match[1]);
      sessionStorage.setItem(SID_KEY, sid);
      history.replaceState(null, "", location.pathname + location.search);
      return sid;
    }
    return null;
  }

  function clearSid() {
    sessionStorage.removeItem(SID_KEY);
    localStorage.removeItem(SID_KEY);
  }

  function isAuthorizedProfile(profile) {
    return !!(
      profile &&
      profile.authenticated &&
      (profile.is_admin || profile.is_super)
    );
  }

  function hasWriteAccess() {
    return isAuthorizedProfile(currentProfile);
  }

  function getProfileHandle(profile) {
    if (!profile) return "unknown";
    return profile.username || profile.login || profile.email || "unknown";
  }

  function defaultReadonlyMessage() {
    return "Browse published metadata and open posts. Log in to create and publish.";
  }

  function updateReadonlyUI(message, title) {
    var canWrite = hasWriteAccess();
    var readonlyMessage = message || defaultReadonlyMessage();
    if (els.userbar) els.userbar.hidden = !canWrite;
    if (els.guestbar) els.guestbar.hidden = canWrite;
    if (els.readonlyBanner) els.readonlyBanner.hidden = canWrite;

    if (els.guestTitle) {
      els.guestTitle.textContent = canWrite ? "" : (title || "Read-only mode");
    }
    if (els.guestCopy) {
      els.guestCopy.textContent = canWrite ? "" : readonlyMessage;
    }
    if (els.readonlyCopy) {
      els.readonlyCopy.textContent = readonlyMessage;
    }

    els.loginBtns.forEach(function (btn) {
      btn.hidden = canWrite || !AUTH_API;
    });
    els.logoutBtns.forEach(function (btn) {
      btn.hidden = !canWrite;
    });

    if (els.editorPublishBtn) {
      els.editorPublishBtn.disabled = !canWrite;
      els.editorPublishBtn.title = canWrite ? "Publish post" : "Log in to publish";
    }

    document.querySelectorAll('[data-cmsv6-action="new-post"]').forEach(function (btn) {
      btn.classList.toggle("cmsv6-is-locked", !canWrite);
      btn.setAttribute("aria-disabled", canWrite ? "false" : "true");
      btn.title = canWrite ? "Create a new post" : "Log in to create and publish";
    });
  }

  function fetchMe(sid) {
    if (!AUTH_API) return Promise.reject(new Error("No auth API"));
    var headers = {};
    if (sid) headers.Authorization = "Bearer " + sid;
    return fetch(AUTH_API + "/auth/me", {
      credentials: "include",
      headers: headers,
    }).then(function (r) {
      if (!r.ok) {
        if (r.status === 401 || r.status === 403) return null;
        throw new Error("Auth check failed: " + r.status);
      }
      return r.json();
    });
  }

  function showReadOnlyDashboard(message, title) {
    currentProfile = null;
    showView("dashboard");
    updateReadonlyUI(message, title);
    initDashboard();
  }

  function initAuth() {
    var sid = getSid();

    if (!AUTH_API) {
      showReadOnlyDashboard("Browse published metadata. Backend auth is not configured for writing.");
      if (els.hint) els.hint.hidden = false;
      return;
    }

    if (!sid) {
      showReadOnlyDashboard();
      return;
    }

    fetchMe(sid).then(function (profile) {
      if (isAuthorizedProfile(profile)) {
        currentProfile = profile;
        renderUserbar(profile);
        showView("dashboard");
        updateReadonlyUI();
        initDashboard();
      } else if (profile) {
        clearSid();
        showReadOnlyDashboard(
          "Logged in as " + getProfileHandle(profile) + ". This account can browse CMS-V6, but create and publish are restricted.",
          "Read-only account"
        );
      } else {
        clearSid();
        showReadOnlyDashboard();
      }
    }).catch(function (err) {
      clearSid();
      showReadOnlyDashboard("Session unavailable. Browse in read-only mode or log in again.");
    });
  }

  function renderUserbar(profile) {
    if (els.userbar) els.userbar.hidden = false;
    if (els.guestbar) els.guestbar.hidden = true;
    if (els.avatar) els.avatar.src = profile.avatar_url || "";
    if (els.username) els.username.textContent = profile.name || getProfileHandle(profile);
    if (els.useremail) els.useremail.textContent = profile.email || "";
  }

  function startLogin() {
    if (!AUTH_API) return;
    var returnTo = location.pathname + location.search;
    window.location.href =
      AUTH_API + "/auth/login?return_to=" + encodeURIComponent(returnTo);
  }

  function logout() {
    if (AUTH_API) {
      var sid = getSid();
      fetch(AUTH_API + "/auth/logout", {
        method: "POST",
        credentials: "include",
        headers: sid ? { Authorization: "Bearer " + sid } : {},
      }).catch(function () {});
    }
    clearSid();
    currentProfile = null;
    showReadOnlyDashboard();
    if (els.error) {
      els.error.hidden = true;
      els.error.textContent = "";
    }
  }

  /* ─── Dashboard ─── */

  function loadPostsData() {
    if (POSTS_DATA) return Promise.resolve(POSTS_DATA);
    try {
      var el = document.getElementById("cmsv6-posts-data");
      if (el) {
        POSTS_DATA = JSON.parse(el.textContent);
        return Promise.resolve(POSTS_DATA);
      }
    } catch (e) {}
    return Promise.resolve([]);
  }

  function loadCategories() {
    try {
      var el = document.getElementById("cmsv6-categories-data");
      if (el) return JSON.parse(el.textContent);
    } catch (e) {}
    return [];
  }

  function formatDate(iso) {
    if (!iso) return "";
    try {
      var d = new Date(iso);
      if (isNaN(d.getTime())) return iso.slice(0, 10);
      return d.toLocaleDateString("vi-VN", {
        day: "2-digit", month: "2-digit", year: "numeric",
        timeZone: "Asia/Ho_Chi_Minh",
      });
    } catch (e) { return iso.slice(0, 10); }
  }

  function getStatus(post) {
    if (post.draft) return "draft";
    if (post.publish_at) return "scheduled";
    return "published";
  }

  function filterPosts(posts, filter, query) {
    var filtered = posts.filter(function (p) {
      var status = getStatus(p);
      if (filter === "published" && status !== "published") return false;
      if (filter === "scheduled" && status !== "scheduled") return false;
      if (filter === "drafts" && status !== "draft") return false;
      if (query) {
        var q = query.toLowerCase();
        return (
          (p.title && p.title.toLowerCase().indexOf(q) !== -1) ||
          (p.slug && p.slug.toLowerCase().indexOf(q) !== -1) ||
          (p.category && p.category.toLowerCase().indexOf(q) !== -1) ||
          (p.tags && p.tags.some(function (t) { return t.toLowerCase().indexOf(q) !== -1; }))
        );
      }
      return true;
    });
    return filtered;
  }

  function sortPosts(posts, sort) {
    var sorted = posts.slice();
    switch (sort) {
      case "date-asc":
        sorted.sort(function (a, b) { return a.date.localeCompare(b.date); });
        break;
      case "title-asc":
        sorted.sort(function (a, b) { return (a.title || "").localeCompare(b.title || "vi"); });
        break;
      case "title-desc":
        sorted.sort(function (a, b) { return (b.title || "").localeCompare(a.title || "vi"); });
        break;
      default:
        sorted.sort(function (a, b) { return b.date.localeCompare(a.date); });
    }
    return sorted;
  }

  function updateCounts(posts) {
    var counts = { published: 0, scheduled: 0, drafts: 0 };
    posts.forEach(function (p) {
      var s = getStatus(p);
      if (counts[s] !== undefined) counts[s]++;
    });
    Object.keys(counts).forEach(function (k) {
      if (els.countSpans[k]) els.countSpans[k].textContent = counts[k];
    });
  }

  function renderPostList() {
    loadPostsData().then(function (posts) {
      updateCounts(posts);
      var canWrite = hasWriteAccess();
      var query = els.search ? els.search.value.trim() : "";
      var filtered = filterPosts(posts, currentFilter, query);
      var sorted = sortPosts(filtered, currentSort);

      if (!els.list) return;
      if (sorted.length === 0) {
        els.list.innerHTML =
          '<div class="cmsv6-list__empty">' +
          '<svg viewBox="0 0 20 20" width="32" height="32" fill="currentColor" aria-hidden="true"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clip-rule="evenodd"/></svg>' +
          "<p>No " + currentFilter + " posts" + (query ? ' matching "' + query + '"' : "") + ".</p>" +
          (canWrite
            ? '<button type="button" class="cmsv6-btn cmsv6-btn--primary" data-cmsv6-action="new-post">Create your first post</button>'
            : (AUTH_API ? '<button type="button" class="cmsv6-btn cmsv6-btn--primary" data-cmsv6-action="github-login">Log in to create</button>' : "")) +
          "</div>";
        updateReadonlyUI();
        return;
      }

      var html = '<div class="cmsv6-list__header">' +
        '<span class="cmsv6-list__header-cell cmsv6-list__header-cell--title">Title</span>' +
        '<span class="cmsv6-list__header-cell cmsv6-list__header-cell--status">Status</span>' +
        '<span class="cmsv6-list__header-cell cmsv6-list__header-cell--date">Date</span>' +
        '<span class="cmsv6-list__header-cell cmsv6-list__header-cell--category">Category</span>' +
        '<span class="cmsv6-list__header-cell cmsv6-list__header-cell--actions"></span>' +
        "</div>";

      sorted.forEach(function (p) {
        var status = getStatus(p);
        var statusLabel = status === "published"
          ? "Published"
          : status === "scheduled" ? "Scheduled" : "Draft";
        var statusClass = status === "published"
          ? "cmsv6-list__badge--green"
          : status === "scheduled" ? "cmsv6-list__badge--amber" : "cmsv6-list__badge--gray";

        var thumb = p.thumbnail || p.image || "";
        var thumbHtml = thumb
          ? '<img class="cmsv6-list__thumb" src="' + thumb + '" alt="" width="40" height="30" loading="lazy" decoding="async">'
          : '<div class="cmsv6-list__thumb cmsv6-list__thumb--placeholder"><span>S</span></div>';

        var actionsHtml = canWrite
          ? (
              '<button type="button" class="cmsv6-list__action" data-action="edit" data-slug="' + p.slug + '" title="Edit">' +
              '<svg viewBox="0 0 20 20" width="16" height="16" fill="currentColor" aria-hidden="true"><path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"/></svg>' +
              "</button>" +
              '<a class="cmsv6-list__action" href="' + p.permalink + '" target="_blank" title="View" rel="noopener">' +
              '<svg viewBox="0 0 20 20" width="16" height="16" fill="currentColor" aria-hidden="true"><path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z"/><path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 100-2H5z"/></svg>' +
              "</a>" +
              '<button type="button" class="cmsv6-list__action" data-action="more" data-slug="' + p.slug + '" title="More">' +
              '<svg viewBox="0 0 20 20" width="16" height="16" fill="currentColor" aria-hidden="true"><path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z"/></svg>' +
              "</button>"
            )
          : (
              '<a class="cmsv6-list__action" href="' + p.permalink + '" target="_blank" title="View" rel="noopener">' +
              '<svg viewBox="0 0 20 20" width="16" height="16" fill="currentColor" aria-hidden="true"><path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z"/><path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 100-2H5z"/></svg>' +
              "</a>"
            );

        html += '<div class="cmsv6-list__row" role="listitem" data-slug="' + p.slug + '">' +
          '<div class="cmsv6-list__cell cmsv6-list__cell--title">' +
          thumbHtml +
          '<div class="cmsv6-list__title-group">' +
          '<span class="cmsv6-list__title-text">' + escapeHtml(p.title || "Untitled") + "</span>" +
          '<span class="cmsv6-list__desc">' + escapeHtml((p.description || "").slice(0, 80)) + "</span>" +
          "</div>" +
          "</div>" +
          '<div class="cmsv6-list__cell cmsv6-list__cell--status">' +
          '<span class="cmsv6-list__badge ' + statusClass + '">' + statusLabel + "</span>" +
          "</div>" +
          '<div class="cmsv6-list__cell cmsv6-list__cell--date">' +
          '<span class="cmsv6-list__date">' + formatDate(p.date) + "</span>" +
          "</div>" +
          '<div class="cmsv6-list__cell cmsv6-list__cell--category">' +
          '<span class="cmsv6-list__cat">' + escapeHtml(p.category || "") + "</span>" +
          "</div>" +
          '<div class="cmsv6-list__cell cmsv6-list__cell--actions">' +
          actionsHtml +
          "</div>" +
          "</div>";
      });

      els.list.innerHTML = html;

      bindPostActions();
      updateReadonlyUI();
    });
  }

  function escapeHtml(str) {
    if (!str) return "";
    var div = document.createElement("div");
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  function bindPostActions() {
    var list = els.list;
    if (!list) return;
    if (list.__cmsv6PostActionsBound) return;
    list.__cmsv6PostActionsBound = true;
    list.addEventListener("click", function (e) {
      var target = e.target.closest("[data-action]");
      if (!target) return;
      var slug = target.getAttribute("data-slug");
      var action = target.getAttribute("data-action");
      if (action === "edit" && slug) {
        openEditor(slug);
      } else if (action === "more" && slug) {
        var row = target.closest('[data-slug]');
        if (row) {
          var menu = row.querySelector(".cmsv6-list__overflow-menu");
          if (menu) {
            menu.hidden = !menu.hidden;
          } else {
            var m = document.createElement("div");
            m.className = "cmsv6-list__overflow-menu";
            m.hidden = false;
            m.innerHTML = '<button type="button" class="cmsv6-list__overflow-item" data-action="edit" data-slug="' + slug + '">Edit</button>' +
              '<a class="cmsv6-list__overflow-item" href="/cms-v6/?edit=' + slug + '">Open in editor</a>';
            target.parentNode.appendChild(m);
          }
        }
      }
    });
  }

  function initDashboard() {
    renderPostList();

    /* Load categories into editor select */
    var cats = loadCategories();
    var select = els.editorCategorySelect;
    if (select && cats.length) {
      select.innerHTML = '<option value="">Category</option>';
      cats.forEach(function (c) {
        var opt = document.createElement("option");
        opt.value = c;
        opt.textContent = c;
        select.appendChild(opt);
      });
    }
  }

  /* ─── Tab switching ─── */

  function switchTab(filter) {
    currentFilter = filter;
    els.tabBtns.forEach(function (btn) {
      var f = btn.getAttribute("data-cmsv6-filter");
      var isActive = f === filter;
      btn.classList.toggle("is-active", isActive);
      btn.setAttribute("aria-selected", isActive ? "true" : "false");
    });
    renderPostList();
  }

  /* ─── Editor ─── */

  var autosaveTimer = null;
  var currentEditingSlug = null;

  function openEditor(slug) {
    if (!hasWriteAccess()) {
      startLogin();
      return;
    }
    currentEditingSlug = slug;
    showView("editor");

    loadPostsData().then(function (posts) {
      var post = null;
      posts.forEach(function (p) {
        if (p.slug === slug) post = p;
      });

      if (els.editorTitleDisplay) {
        els.editorTitleDisplay.textContent = post ? post.title : "New Post";
      }

      /* Check for local draft */
      var draftKey = DRAFT_KEY_PREFIX + (slug || "new");
      var draftData = null;
      try {
        var raw = localStorage.getItem(draftKey);
        if (raw) draftData = JSON.parse(raw);
      } catch (e) {}

      if (post) {
        setEditorValues(post, draftData);
      } else {
        /* New post */
        if (draftData) {
          setEditorValues(draftData, null);
        } else {
          if (els.editorTitleInput) els.editorTitleInput.value = "";
          if (els.editorSubtitleInput) els.editorSubtitleInput.value = "";
          if (els.editorSlugInput) els.editorSlugInput.value = "";
          if (els.editorCategorySelect) els.editorCategorySelect.value = "";
          if (els.editorTagsInput) els.editorTagsInput.value = "";
          if (els.editorCoverInput) els.editorCoverInput.value = "";
          if (els.editorBody) els.editorBody.value = "";
          updateSaveStatus("saved");
        }
      }

      /* Focus title */
      if (els.editorTitleInput) els.editorTitleInput.focus();

      /* Init auto-slug from title */
      autoSlugFromTitle();
    });
  }

  function setEditorValues(post, draftOverride) {
    var values = draftOverride || post;
    if (els.editorTitleInput) els.editorTitleInput.value = values.title || "";
    if (els.editorSubtitleInput) els.editorSubtitleInput.value = values.description || "";
    if (els.editorSlugInput) els.editorSlugInput.value = values.slug || "";
    if (els.editorCategorySelect) {
      var cat = values.category || (values.categories && values.categories[0]) || "";
      els.editorCategorySelect.value = cat;
    }
    if (els.editorTagsInput) {
      var tags = values.tags || [];
      els.editorTagsInput.value = Array.isArray(tags) ? tags.join(", ") : (tags || "");
    }
    if (els.editorCoverInput) els.editorCoverInput.value = values.thumbnail || values.image || "";
    if (els.editorBody) els.editorBody.value = values.body || "";
    updateSaveStatus("saved");
  }

  function autoSlugFromTitle() {
    var titleEl = els.editorTitleInput;
    var slugEl = els.editorSlugInput;
    if (!titleEl || !slugEl) return;

    titleEl.addEventListener("input", function () {
      /* Only auto-generate if slug is empty or matches previous title */
      if (!slugEl.value || slugEl.dataset.auto === "true") {
        var slug = titleEl.value
          .toLowerCase()
          .replace(/[^a-z0-9]+/g, "-")
          .replace(/^-+|-+$/g, "")
          .slice(0, 80);
        slugEl.value = slug;
        slugEl.dataset.auto = "true";
      }
    });

    slugEl.addEventListener("input", function () {
      slugEl.dataset.auto = slugEl.value === "" ? "true" : "false";
    });
  }

  function updateSaveStatus(state) {
    if (!els.editorSaveStatus) return;
    var labels = { saving: "Saving...", saved: "Saved", unsaved: "Unsaved changes" };
    els.editorSaveStatus.textContent = labels[state] || state;
    els.editorSaveStatus.className = "cmsv6-editor__save-status cmsv6-editor__save-status--" + state;
  }

  function autosave() {
    if (autosaveTimer) clearTimeout(autosaveTimer);
    autosaveTimer = setTimeout(function () {
      var slug = els.editorSlugInput ? els.editorSlugInput.value.trim() : "";
      if (!slug) return;
      var key = DRAFT_KEY_PREFIX + slug;
      var data = {
        title: els.editorTitleInput ? els.editorTitleInput.value : "",
        description: els.editorSubtitleInput ? els.editorSubtitleInput.value : "",
        slug: slug,
        category: els.editorCategorySelect ? els.editorCategorySelect.value : "",
        tags: els.editorTagsInput ? els.editorTagsInput.value : "",
        thumbnail: els.editorCoverInput ? els.editorCoverInput.value : "",
        body: els.editorBody ? els.editorBody.value : "",
      };
      try {
        localStorage.setItem(key, JSON.stringify(data));
      } catch (e) {}
      updateSaveStatus("saved");
    }, 800);
  }

  function markUnsaved() {
    updateSaveStatus("unsaved");
    autosave();
  }

  /* ─── Markdown helpers ─── */

  function wrapSelection(prefix, suffix) {
    var textarea = els.editorBody;
    if (!textarea) return;
    var start = textarea.selectionStart;
    var end = textarea.selectionEnd;
    var text = textarea.value;
    var selected = text.substring(start, end);
    var insertion = prefix + selected + suffix;
    textarea.value = text.substring(0, start) + insertion + text.substring(end);
    textarea.selectionStart = start + prefix.length;
    textarea.selectionEnd = start + insertion.length;
    textarea.focus();
    markUnsaved();
  }

  function insertAtCursor(text) {
    var textarea = els.editorBody;
    if (!textarea) return;
    var start = textarea.selectionStart;
    var value = textarea.value;
    textarea.value = value.substring(0, start) + text + value.substring(textarea.selectionEnd);
    textarea.selectionStart = textarea.selectionEnd = start + text.length;
    textarea.focus();
    markUnsaved();
  }

  var MD_ACTIONS = {
    "undo": function () { document.execCommand("undo"); },
    "redo": function () { document.execCommand("redo"); },
    "bold": function () { wrapSelection("**", "**"); },
    "italic": function () { wrapSelection("_", "_"); },
    "strike": function () { wrapSelection("~~", "~~"); },
    "code": function () { wrapSelection("`", "`"); },
    "heading": function () { insertAtCursor("\n## "); },
    "quote": function () { insertAtCursor("\n> "); },
    "bullet-list": function () { insertAtCursor("\n- "); },
    "numbered-list": function () { insertAtCursor("\n1. "); },
    "link": function () {
      var url = prompt("Enter URL:");
      if (url) {
        var textarea = els.editorBody;
        var selected = textarea ? textarea.value.substring(textarea.selectionStart, textarea.selectionEnd) : "";
        wrapSelection("[", "](" + url + ")");
      }
    },
    "image": function () {
      var url = prompt("Enter image URL:");
      if (url) {
        var alt = prompt("Alt text:");
        insertAtCursor("\n![" + (alt || "image") + "](" + url + ")\n");
      }
    },
  };

  /* ─── Publish via GitHub API ─── */

  function publishPost() {
    if (!hasWriteAccess()) {
      startLogin();
      return;
    }
    var sid = getSid();
    if (!sid) {
      startLogin();
      return;
    }

    var title = els.editorTitleInput ? els.editorTitleInput.value.trim() : "";
    if (!title) { alert("Title is required."); return; }
    var body = els.editorBody ? els.editorBody.value.trim() : "";
    if (!body) { alert("Content is required."); return; }
    var slug = els.editorSlugInput ? els.editorSlugInput.value.trim() : "";
    if (!slug) {
      slug = title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 80);
    }

    var category = els.editorCategorySelect ? els.editorCategorySelect.value : "";
    var tagsStr = els.editorTagsInput ? els.editorTagsInput.value.trim() : "";
    var tags = tagsStr ? tagsStr.split(",").map(function (t) { return t.trim(); }).filter(Boolean) : [];
    var description = els.editorSubtitleInput ? els.editorSubtitleInput.value.trim() : "";
    var thumbnail = els.editorCoverInput ? els.editorCoverInput.value.trim() : "";

    var date = new Date().toISOString().split("T")[0];
    var content = "+++\n";
    content += "title = \"" + escapeToml(title) + "\"\n";
    content += "date = " + date + "\n";
    content += "description = \"" + escapeToml(description) + "\"\n";
    content += "slug = \"" + escapeToml(slug) + "\"\n";
    content += "template = \"page.html\"\n";
    if (tags.length) {
      content += "tags = [" + tags.map(function (t) { return "\"" + escapeToml(t) + "\""; }).join(", ") + "]\n";
    }
    if (category) {
      content += "categories = [\"" + escapeToml(category) + "\"]\n";
    }
    content += "draft = false\n";
    if (thumbnail) {
      content += "\n[extra]\n";
      content += "thumbnail = \"" + escapeToml(thumbnail) + "\"\n";
    }
    content += "+++\n\n";
    content += body;

    updateSaveStatus("saving");

    var path = "content/posting/" + slug + ".md";
    var apiUrl = "https://api.github.com/repos/" + GH_OWNER + "/" + GH_REPO + "/contents/" + path;

    /* Get SHA if file exists */
    var token = null;
    fetchMe(sid).then(function (profile) {
      if (!isAuthorizedProfile(profile)) throw new Error("Auth failed");
      /* Use the sid as Bearer token for GitHub API */
      return fetch("https://api.github.com/user", {
        headers: {
          "Authorization": "token " + sid,
          "Accept": "application/vnd.github.v3+json",
        },
      });
    }).then(function (r) {
      if (r.status === 401 || r.status === 403) {
        /* sid is not a GitHub token. Use the session pattern instead. */
        /* Fallback: just try to create file without SHA */
        return null;
      }
      /* We have a valid GitHub token somehow */
      return fetch(apiUrl, {
        headers: {
          "Authorization": "token " + sid,
          "Accept": "application/vnd.github.v3+json",
        },
      });
    }).then(function (r) {
      if (r && r.ok) return r.json();
      return null;
    }).then(function (existing) {
      var sha = existing ? existing.sha : null;
      var bodyData = {
        message: "Publish: " + title,
        content: btoa(unescape(encodeURIComponent(content))),
        branch: GH_BRANCH,
      };
      if (sha) bodyData.sha = sha;

      return fetch(apiUrl, {
        method: "PUT",
        headers: {
          "Authorization": "token " + sid,
          "Accept": "application/vnd.github.v3+json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify(bodyData),
      });
    }).then(function (r) {
      if (!r.ok) {
        return r.json().then(function (err) {
          throw new Error(err.message || "Publish failed");
        });
      }
      return r.json();
    }).then(function () {
      updateSaveStatus("saved");
      /* Clear draft */
      try { localStorage.removeItem(DRAFT_KEY_PREFIX + slug); } catch (e) {}
      alert("Post published successfully!\n\nIt will appear on the site after the next build/deploy.");
      goToDashboard();
    }).catch(function (err) {
      updateSaveStatus("saved");
      alert("Publish failed: " + err.message + "\n\nYour content is saved locally.");
    });
  }

  function escapeToml(str) {
    if (!str) return "";
    return str.replace(/\\/g, "\\\\").replace(/"/g, '\\"').replace(/\n/g, "\\n");
  }

  /* ─── Navigation ─── */

  function goToDashboard() {
    currentEditingSlug = null;
    showView("dashboard");
    renderPostList();
  }

  function createNewPost() {
    if (!hasWriteAccess()) {
      startLogin();
      return;
    }
    currentEditingSlug = null;
    showView("editor");
    if (els.editorTitleDisplay) els.editorTitleDisplay.textContent = "New Post";
    if (els.editorTitleInput) els.editorTitleInput.value = "";
    if (els.editorSubtitleInput) els.editorSubtitleInput.value = "";
    if (els.editorSlugInput) {
      els.editorSlugInput.value = "";
      els.editorSlugInput.dataset.auto = "true";
    }
    if (els.editorCategorySelect) els.editorCategorySelect.value = "";
    if (els.editorTagsInput) els.editorTagsInput.value = "";
    if (els.editorCoverInput) els.editorCoverInput.value = "";
    if (els.editorBody) els.editorBody.value = "";
    if (els.editorPreview) els.editorPreview.hidden = true;
    updateSaveStatus("saved");
    if (els.editorTitleInput) els.editorTitleInput.focus();
  }

  /* ─── Preview toggle ─── */

  function togglePreview() {
    if (!els.editorPreview || !els.editorBody) return;
    var hidden = els.editorPreview.hidden;
    if (hidden) {
      var body = els.editorBody.value;
      var html = body
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/^### (.+)$/gm, "<h3>$1</h3>")
        .replace(/^## (.+)$/gm, "<h2>$1</h2>")
        .replace(/^# (.+)$/gm, "<h1>$1</h1>")
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/_(.+?)_/g, "<em>$1</em>")
        .replace(/`(.+?)`/g, "<code>$1</code>")
        .replace(/^> (.+)$/gm, "<blockquote>$1</blockquote>")
        .replace(/^- (.+)$/gm, "<li>$1</li>")
        .replace(/\n\n/g, "</p><p>")
        .replace(/\n/g, "<br>");
      html = "<p>" + html + "</p>";
      els.editorPreviewBody.innerHTML = html;
      els.editorPreview.hidden = false;
      els.editorBody.hidden = true;
    } else {
      els.editorPreview.hidden = true;
      els.editorBody.hidden = false;
    }
  }

  /* ─── Event binding ─── */

  function bindEvents() {
    /* Logout */
    els.logoutBtns.forEach(function (btn) {
      btn.addEventListener("click", logout);
    });

    /* Tabs */
    els.tabBtns.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var filter = this.getAttribute("data-cmsv6-filter");
        switchTab(filter);
      });
    });

    /* Sidebar sub-tabs */
    var sidebarTabBtns = app.querySelectorAll("[data-cmsv6-tab]");
    sidebarTabBtns.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var tab = this.getAttribute("data-cmsv6-tab");
        switchTab(tab);
      });
    });

    /* Search */
    if (els.search) {
      var searchTimer = null;
      els.search.addEventListener("input", function () {
        if (searchTimer) clearTimeout(searchTimer);
        searchTimer = setTimeout(renderPostList, 200);
      });
    }

    /* Sort */
    if (els.sort) {
      els.sort.addEventListener("change", function () {
        currentSort = this.value;
        renderPostList();
      });
    }

    /* Refresh */
    if (els.refreshBtn) {
      els.refreshBtn.addEventListener("click", function () {
        POSTS_DATA = null;
        renderPostList();
      });
    }

    /* New post (via create button) */
    app.addEventListener("click", function (e) {
      var loginTarget = e.target.closest('[data-cmsv6-action="github-login"]');
      if (loginTarget) {
        e.preventDefault();
        startLogin();
        return;
      }
      var target = e.target.closest('[data-cmsv6-action="new-post"]');
      if (target) createNewPost();
    });

    /* Back to dashboard */
    if (els.editorBack) els.editorBack.addEventListener("click", goToDashboard);

    /* Editor: markdown toolbar */
    els.editorToolbarBtns.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var action = this.getAttribute("data-cmsv6-md");
        if (MD_ACTIONS[action]) MD_ACTIONS[action]();
      });
    });

    /* Editor: autosave on input */
    [els.editorTitleInput, els.editorSubtitleInput, els.editorSlugInput,
     els.editorTagsInput, els.editorCoverInput, els.editorBody].forEach(function (el) {
      if (el) el.addEventListener("input", markUnsaved);
    });
    if (els.editorCategorySelect) {
      els.editorCategorySelect.addEventListener("change", markUnsaved);
    }

    /* Editor: preview toggle */
    if (els.editorPreviewToggle) {
      els.editorPreviewToggle.addEventListener("click", togglePreview);
    }

    /* Editor: publish */
    if (els.editorPublishBtn) {
      els.editorPublishBtn.addEventListener("click", publishPost);
    }

    /* Media dropdown */
    if (els.mediaBtn) {
      els.mediaBtn.addEventListener("click", function (e) {
        e.stopPropagation();
        var expanded = this.getAttribute("aria-expanded") === "true";
        this.setAttribute("aria-expanded", !expanded);
        if (els.mediaMenu) els.mediaMenu.hidden = expanded;
      });
      document.addEventListener("click", function () {
        if (els.mediaMenu && !els.mediaMenu.hidden) {
          els.mediaMenu.hidden = true;
          if (els.mediaBtn) els.mediaBtn.setAttribute("aria-expanded", "false");
        }
      });
    }

    /* Media dropdown items */
    if (els.mediaMenu) {
      els.mediaMenu.addEventListener("click", function (e) {
        var item = e.target.closest("[data-cmsv6-action]");
        if (!item) return;
        var action = item.getAttribute("data-cmsv6-action");
        if (action === "insert-image") {
          var url = prompt("Enter image URL:");
          if (url) {
            var alt = prompt("Alt text:");
            insertAtCursor("\n![" + (alt || "image") + "](" + url + ")\n");
          }
        } else if (action === "insert-gallery") {
          insertAtCursor("\n<!-- Gallery placeholder -->\n");
        }
        els.mediaMenu.hidden = true;
        if (els.mediaBtn) els.mediaBtn.setAttribute("aria-expanded", "false");
      });
    }

    /* Toggle sidebar (mobile) */
    if (els.toggleSidebar && els.sidebar) {
      els.toggleSidebar.addEventListener("click", function () {
        els.sidebar.classList.toggle("is-open");
      });
    }

    /* Keyboard shortcuts */
    document.addEventListener("keydown", function (e) {
      /* Ctrl+S = save only in editor view */
      if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        if (!views.editor.hidden) {
          e.preventDefault();
          markUnsaved();
        }
      }
      /* Escape = close media dropdown */
      if (e.key === "Escape" && els.mediaMenu && !els.mediaMenu.hidden) {
        els.mediaMenu.hidden = true;
        if (els.mediaBtn) els.mediaBtn.setAttribute("aria-expanded", "false");
      }
    });

    /* Check URL for ?edit=slug */
    var params = new URLSearchParams(location.search);
    var editSlug = params.get("edit");
    if (editSlug) {
      /* Defer until auth is ready */
      var checkInterval = setInterval(function () {
        if (!views.dashboard.hidden && hasWriteAccess()) {
          clearInterval(checkInterval);
          openEditor(editSlug);
        } else if (!views.dashboard.hidden && !hasWriteAccess()) {
          clearInterval(checkInterval);
        }
      }, 100);
    }
  }

  /* ─── Init ─── */

  function init() {
    bindEvents();
    initAuth();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

})();
