/**
 * CMS-V2 controller
 *
 * Connects the CMS-V2 workspace shell to:
 * - GitHub auth gate
 * - draft autosave / restore
 * - live preview + QA
 * - GitHub repo publish via /cms/save-post
 * - review queue modal backed by local history
 */
(function () {
  "use strict";

  if (window.__cmsV2InitDone) return;
  window.__cmsV2InitDone = true;

  var AUTH_API = (function () {
    var meta = document.querySelector('meta[name="zola-cms-auth-api"]');
    if (meta && meta.content) return meta.content.replace(/\/$/, "");
    return "https://api.seomoney.org";
  })();

  var SESSION_KEY = "zola-cms-session-id";
  var DRAFT_KEY = "seomoney.cmsv2.draft.v1";
  var HISTORY_KEY = "seomoney.cmsv2.publish-history.v1";
  var CMS_RETURN_TO = "https://seomoney.org/cms-v2/";
  var AUTH_TIMEOUT_MS = 10000;
  var MARKED = window.marked || null;

  var root = document.querySelector("[data-cms-v2]");
  if (!root) return;

  var gate = root.querySelector("[data-cms-v2-gate]");
  var shell = root.querySelector("[data-cms-v2-shell]");
  var status = root.querySelector("[data-cms-v2-auth-status]");
  var loginButton = root.querySelector("[data-cms-v2-login]");
  var logoutButton = root.querySelector("[data-cms-v2-logout]");
  var userCard = root.querySelector("[data-cms-v2-usercard]");
  var userAvatar = root.querySelector("[data-cms-v2-user-avatar]");
  var userName = root.querySelector("[data-cms-v2-user-name]");
  var userEmail = root.querySelector("[data-cms-v2-user-email]");
  var tabs = Array.prototype.slice.call(root.querySelectorAll("[data-cms-v2-tab]"));
  var panels = Array.prototype.slice.call(root.querySelectorAll("[data-cms-v2-panel]"));

  var topbarPill = root.querySelector("[data-cms-v2-backend-pill]");
  var rolePill = root.querySelector("[data-cms-v2-role-pill]");
  var authState = root.querySelector("[data-cms-v2-auth-state]");
  var sessionState = root.querySelector("[data-cms-v2-session-state]");
  var draftState = root.querySelector("[data-cms-v2-draft-state]");
  var publishState = root.querySelector("[data-cms-v2-publish-state]");
  var reviewAuth = root.querySelector("[data-cms-v2-review-auth]");
  var reviewDraft = root.querySelector("[data-cms-v2-review-draft]");
  var reviewQa = root.querySelector("[data-cms-v2-review-qa]");
  var reviewPublish = root.querySelector("[data-cms-v2-review-publish]");
  var reviewModal = root.querySelector("[data-cms-v2-review-modal]");
  var reviewHistory = root.querySelector("[data-cms-v2-review-history]");

  var preview = {
    category: root.querySelector("[data-cms-v2-preview-category]"),
    date: root.querySelector("[data-cms-v2-preview-date]"),
    author: root.querySelector("[data-cms-v2-preview-author]"),
    title: root.querySelector("[data-cms-v2-preview-title]"),
    excerpt: root.querySelector("[data-cms-v2-preview-excerpt]"),
    body: root.querySelector("[data-cms-v2-preview-body]"),
  };

  var qa = {
    titleLength: root.querySelector("[data-cms-v2-title-length]"),
    metaLength: root.querySelector("[data-cms-v2-meta-length]"),
    slugQuality: root.querySelector("[data-cms-v2-slug-quality]"),
    schemaStatus: root.querySelector("[data-cms-v2-schema-status]"),
    h1Match: root.querySelector("[data-cms-v2-h1-match]"),
    checks: {
      external: root.querySelector("[data-cms-v2-check='external'] strong"),
      internal: root.querySelector("[data-cms-v2-check='internal'] strong"),
      copyright: root.querySelector("[data-cms-v2-check='copyright'] strong"),
      editorial: root.querySelector("[data-cms-v2-check='editorial'] strong"),
    },
  };

  var fields = {
    title: root.querySelector("[data-cms-v2-title]"),
    slug: root.querySelector("[data-cms-v2-slug]"),
    section: root.querySelector("[data-cms-v2-section]"),
    category: root.querySelector("[data-cms-v2-category]"),
    author: root.querySelector("[data-cms-v2-author]"),
    seoTitle: root.querySelector("[data-cms-v2-seo-title]"),
    description: root.querySelector("[data-cms-v2-description]"),
    metaDescription: root.querySelector("[data-cms-v2-meta-description]"),
    heroImage: root.querySelector("[data-cms-v2-hero-image]"),
    heroMode: root.querySelector("[data-cms-v2-hero-mode]"),
    series: root.querySelector("[data-cms-v2-series]"),
    tags: root.querySelector("[data-cms-v2-tags]"),
    body: root.querySelector("[data-cms-v2-body]"),
    faq: root.querySelector("[data-cms-v2-faq]"),
    related: root.querySelector("[data-cms-v2-related]"),
    internalLinks: root.querySelector("[data-cms-v2-internal-links]"),
    externalSources: root.querySelector("[data-cms-v2-external-sources]"),
    copyright: root.querySelector("[data-cms-v2-copyright]"),
    editorialNote: root.querySelector("[data-cms-v2-editorial-note]"),
  };

  var canonical = root.querySelector("[data-cms-v2-canonical]");
  var reviewOpenButtons = Array.prototype.slice.call(root.querySelectorAll("[data-cms-v2-review-queue]"));
  var reviewCloseButton = root.querySelector("[data-cms-v2-close-review]");
  var newDraftButtons = Array.prototype.slice.call(root.querySelectorAll("[data-cms-v2-new-draft]"));
  var publishButtons = Array.prototype.slice.call(root.querySelectorAll("[data-cms-v2-publish]"));
  var copyButtons = Array.prototype.slice.call(root.querySelectorAll("[data-cms-v2-copy-markdown]"));
  var clearButtons = Array.prototype.slice.call(root.querySelectorAll("[data-cms-v2-clear-draft]"));
  var copyrightNote = root.querySelector("[data-cms-v2-shortcut-note]");

  var state = {
    user: null,
    authError: "",
    authenticated: false,
    provider: "",
    dirty: false,
    lastAutosaveAt: "",
    lastPublishAt: "",
    lastPublishCommit: "",
    lastPublishUrl: "",
    lastPublishPath: "",
    lastPublishTitle: "",
    history: [],
    categories: [],
  };

  function setHidden(el, hidden) {
    if (!el) return;
    el.hidden = !!hidden;
    el.setAttribute("aria-hidden", hidden ? "true" : "false");
  }

  function norm(value) {
    return (value || "").toString().trim();
  }

  function escapeHtml(value) {
    return norm(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function tomlEscape(value) {
    return norm(value)
      .replace(/\\/g, "\\\\")
      .replace(/"/g, '\\"')
      .replace(/\r?\n/g, " ")
      .replace(/\t/g, " ");
  }

  function tomlQuoted(value) {
    return '"' + tomlEscape(value) + '"';
  }

  function setText(el, value) {
    if (el) el.textContent = value == null ? "" : String(value);
  }

  function todayIso() {
    return new Date().toISOString().slice(0, 10);
  }

  function todayDisplay() {
    try {
      return new Intl.DateTimeFormat("vi-VN", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        timeZone: "Asia/Ho_Chi_Minh",
      }).format(new Date());
    } catch (e) {
      return todayIso();
    }
  }

  function slugify(value) {
    return norm(value)
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/đ/g, "d")
      .replace(/Đ/g, "d")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 90);
  }

  function splitCommaList(raw) {
    return norm(raw)
      .split(",")
      .map(function (item) { return norm(item); })
      .filter(Boolean);
  }

  function splitMultiline(raw) {
    return norm(raw)
      .split(/\r?\n/)
      .map(function (item) { return norm(item); })
      .filter(Boolean);
  }

  function getSid() {
    try {
      return localStorage.getItem(SESSION_KEY) || sessionStorage.getItem(SESSION_KEY) || "";
    } catch (e) {}
    return "";
  }

  function saveSid(sid) {
    if (!sid) return;
    try { sessionStorage.setItem(SESSION_KEY, sid); } catch (e) {}
    try { localStorage.setItem(SESSION_KEY, sid); } catch (e) {}
  }

  function clearSid() {
    try { sessionStorage.removeItem(SESSION_KEY); } catch (e) {}
    try { localStorage.removeItem(SESSION_KEY); } catch (e) {}
  }

  function readHashSid() {
    if (!location.hash) return "";
    var match = location.hash.match(/(?:^|[#&])sid=([A-Za-z0-9_-]+)/);
    return match ? match[1] : "";
  }

  function consumeAuthParams() {
    var params = new URLSearchParams(location.search);
    var sid = readHashSid();
    var authError = params.get("auth_error") || "";
    var changed = false;

    if (sid) {
      saveSid(sid);
      changed = true;
    }

    if (params.has("auth") || params.has("auth_error") || sid) {
      params.delete("auth");
      params.delete("auth_error");
      try {
        history.replaceState(null, "", location.pathname + (params.toString() ? "?" + params.toString() : ""));
      } catch (e) {}
    }

    if (location.hash && sid) {
      try {
        history.replaceState(null, "", location.pathname + location.search);
      } catch (e) {}
    }

    return authError;
  }

  function buildLoginUrl() {
    var url = new URL("/auth/login", AUTH_API);
    url.searchParams.set("return_to", CMS_RETURN_TO);
    return url.toString();
  }

  function startOAuth(event) {
    if (event) event.preventDefault();
    if (!AUTH_API) return;
    window.location.assign(buildLoginUrl());
  }

  function normalizeUser(user) {
    if (!user || typeof user !== "object") return null;
    return {
      authenticated: user.authenticated !== false,
      provider: user.provider || "",
      email: user.email || "",
      username: user.username || "",
      name: user.name || user.username || "",
      avatar: user.avatar_url || user.avatar || "",
      avatar_url: user.avatar_url || user.avatar || "",
      role: user.role || "",
      is_admin: user.is_admin === true,
      is_super: user.is_super === true,
      account_type: user.account_type || "",
      comment_role: user.comment_role || "",
    };
  }

  function isAdminUser(user) {
    return !!user && (
      user.is_super === true ||
      user.is_admin === true ||
      user.role === "superadmin" ||
      user.role === "admin" ||
      user.account_type === "admin"
    );
  }

  async function meRequest() {
    var controller = new AbortController();
    var timer = setTimeout(function () { controller.abort(); }, AUTH_TIMEOUT_MS);
    try {
      var res = await fetch(AUTH_API + "/auth/me", {
        method: "GET",
        credentials: "include",
        cache: "no-store",
        signal: controller.signal,
      });
      if (res.status === 401 || res.status === 403) return { status: res.status, user: null };
      if (!res.ok) return { status: res.status, user: null, error: true };
      var user = await res.json();
      return { status: 200, user: user };
    } catch (e) {
      return { status: -1, user: null, error: true };
    } finally {
      clearTimeout(timer);
    }
  }

  async function fetchMe() {
    if (!AUTH_API) return null;
    var res = await meRequest();
    if (res.status === 200 && res.user) return normalizeUser(res.user);
    if (res.status === 401 || res.status === 403) {
      clearSid();
      return null;
    }
    if (res.status === -1) return { __error: "backend_unreachable" };
    return null;
  }

  function authProviderLabel(user) {
    if (!user) return "GitHub";
    if (user.provider === "google") return "Google";
    return "GitHub";
  }

  function updatePublishButtons() {
    var disabled = !state.authenticated || !state.user || state.user.provider !== "github";
    publishButtons.forEach(function (btn) {
      btn.disabled = disabled;
      btn.title = disabled ? "Cần session GitHub admin để publish lên repo." : "Publish bài lên GitHub";
    });
  }

  function renderHistory() {
    if (!reviewHistory) return;
    if (!state.history.length) {
      reviewHistory.innerHTML = '<p class="cms-v2__card-note">Chưa có publish nào trong phiên này.</p>';
      return;
    }
    reviewHistory.innerHTML = state.history.slice(0, 5).map(function (item) {
      var commitLink = item.commitUrl
        ? '<a href="' + escapeHtml(item.commitUrl) + '" target="_blank" rel="noopener">Xem commit</a>'
        : '';
      return (
        '<div class="cms-v2__review-item">' +
          '<strong>' + escapeHtml(item.title || item.slug || "Untitled") + '</strong>' +
          '<span>' + escapeHtml(item.path || "") + '</span>' +
          '<span>' + escapeHtml(item.at || "") + commitLink + '</span>' +
        '</div>'
      );
    }).join("");
  }

  function loadHistory() {
    try {
      var raw = localStorage.getItem(HISTORY_KEY) || "";
      if (!raw) return [];
      var data = JSON.parse(raw);
      return Array.isArray(data) ? data : [];
    } catch (e) {
      return [];
    }
  }

  function saveHistory() {
    try {
      localStorage.setItem(HISTORY_KEY, JSON.stringify(state.history.slice(0, 8)));
    } catch (e) {}
  }

  function loadDraft() {
    try {
      var raw = localStorage.getItem(DRAFT_KEY) || "";
      if (!raw) return null;
      var data = JSON.parse(raw);
      return data && typeof data === "object" ? data : null;
    } catch (e) {
      return null;
    }
  }

  function serializeDraft() {
    var data = {};
    Object.keys(fields).forEach(function (key) {
      var el = fields[key];
      if (el) data[key] = el.value || "";
    });
    data.lastAutosaveAt = state.lastAutosaveAt;
    data.lastPublishAt = state.lastPublishAt;
    data.lastPublishCommit = state.lastPublishCommit;
    data.lastPublishUrl = state.lastPublishUrl;
    data.lastPublishPath = state.lastPublishPath;
    data.lastPublishTitle = state.lastPublishTitle;
    return data;
  }

  function saveDraft() {
    try {
      localStorage.setItem(DRAFT_KEY, JSON.stringify(serializeDraft()));
    } catch (e) {}
  }

  function applyDraft(data) {
    if (!data) return false;
    Object.keys(fields).forEach(function (key) {
      var el = fields[key];
      if (el && typeof data[key] !== "undefined") {
        el.value = data[key];
      }
    });
    if (fields.slug) {
      fields.slug.dataset.cmsV2Touched = norm(data.slug) ? "true" : "";
    }
    if (data.lastAutosaveAt) state.lastAutosaveAt = data.lastAutosaveAt;
    if (data.lastPublishAt) state.lastPublishAt = data.lastPublishAt;
    if (data.lastPublishCommit) state.lastPublishCommit = data.lastPublishCommit;
    if (data.lastPublishUrl) state.lastPublishUrl = data.lastPublishUrl;
    if (data.lastPublishPath) state.lastPublishPath = data.lastPublishPath;
    if (data.lastPublishTitle) state.lastPublishTitle = data.lastPublishTitle;
    return true;
  }

  function resetFields() {
    var authorDefault = (fields.author && (fields.author.getAttribute("value") || fields.author.getAttribute("placeholder"))) || "SEOMONEY";
    Object.keys(fields).forEach(function (key) {
      var el = fields[key];
      if (!el) return;
      if (key === "author") {
        el.value = authorDefault;
      } else if (key === "section") {
        el.value = "posting";
      } else if (key === "category") {
        el.value = "Công nghệ";
      } else if (key === "heroMode") {
        el.value = "fallback";
      } else if (key === "series") {
        el.value = "";
      } else {
        el.value = "";
      }
    });
    if (fields.slug) {
      fields.slug.dataset.cmsV2Touched = "";
    }
    state.dirty = false;
    state.lastAutosaveAt = "";
    updateCanonical();
    updatePreview();
    updateQA();
    updateCommandPanel();
    saveDraft();
  }

  function clearDraft() {
    if (!window.confirm("Xoá draft local trên trình duyệt này?")) return;
    try { localStorage.removeItem(DRAFT_KEY); } catch (e) {}
    resetFields();
    state.lastAutosaveAt = "";
    state.dirty = false;
    setCommandState("Draft", "Local draft cleared");
  }

  function newDraft() {
    if (!window.confirm("Tạo draft mới và bỏ nội dung hiện tại?")) return;
    resetFields();
    state.dirty = false;
    setCommandState("Draft", "New blank draft ready");
  }

  function setCommandState(kind, message) {
    if (kind === "Auth") setText(authState, message);
    else if (kind === "Session") setText(sessionState, message);
    else if (kind === "Draft") setText(draftState, message);
    else if (kind === "Publish") setText(publishState, message);

    if (reviewAuth) setText(reviewAuth, authState ? authState.textContent : "");
    if (reviewDraft) setText(reviewDraft, draftState ? draftState.textContent : "");
    if (reviewPublish) setText(reviewPublish, publishState ? publishState.textContent : "");
  }

  function buildReferenceItems(raw, isInternal) {
    var lines = splitMultiline(raw);
    return lines.map(function (line) {
      var title = "";
      var url = "";
      if (line.indexOf("|") !== -1) {
        var parts = line.split("|").map(function (part) { return part.trim(); }).filter(Boolean);
        if (parts.length >= 2) {
          title = parts[0];
          url = parts.slice(1).join(" | ");
        }
      }
      if (!url) {
        url = line;
      }
      if (!title) {
        if (isInternal) {
          title = url.replace(/^https?:\/\/[^/]+/i, "").replace(/^\/+/, "") || url;
        } else {
          try {
            title = new URL(url, location.origin).hostname.replace(/^www\./, "");
          } catch (e) {
            title = url;
          }
        }
      }
      return {
        title: title.trim() || url,
        url: url.trim(),
      };
    }).filter(function (item) {
      return !!item.url;
    });
  }

  function buildFaqItems(raw) {
    var lines = splitMultiline(raw);
    var items = [];
    var current = null;

    function pushCurrent() {
      if (current && current.q && current.a) items.push(current);
      current = null;
    }

    lines.forEach(function (line) {
      var qMatch = line.match(/^(?:-\s*)?Q:\s*(.+)$/i);
      var aMatch = line.match(/^A:\s*(.+)$/i);
      if (qMatch) {
        pushCurrent();
        current = { q: qMatch[1].trim(), a: "" };
        return;
      }
      if (aMatch && current) {
        current.a = aMatch[1].trim();
        return;
      }
      if (current && line) {
        current.a = current.a ? current.a + " " + line : line;
      }
    });
    pushCurrent();
    return items;
  }

  function renderFaqSnippet(items) {
    if (!items.length) return "Waiting for body and FAQ content.";
    return "FAQ ready: " + items.length + " block(s)";
  }

  function buildFrontmatter() {
    var title = norm(fields.title && fields.title.value) || "Bài viết mới";
    var slug = norm(fields.slug && fields.slug.value) || slugify(title);
    var section = norm(fields.section && fields.section.value) || "posting";
    var category = norm(fields.category && fields.category.value) || "Công nghệ";
    var author = norm(fields.author && fields.author.value) || (fields.author && (fields.author.getAttribute("placeholder") || fields.author.value)) || "SEOMONEY";
    var seoTitle = norm(fields.seoTitle && fields.seoTitle.value) || title;
    var description = norm(fields.description && fields.description.value) || norm(fields.metaDescription && fields.metaDescription.value);
    var metaDescription = norm(fields.metaDescription && fields.metaDescription.value) || description;
    var heroImage = norm(fields.heroImage && fields.heroImage.value);
    var heroMode = norm(fields.heroMode && fields.heroMode.value) || "fallback";
    var tags = splitCommaList(fields.tags && fields.tags.value);
    var series = norm(fields.series && fields.series.value);
    var body = norm(fields.body && fields.body.value);
    var referencesExternal = buildReferenceItems(fields.externalSources && fields.externalSources.value, false);
    var referencesInternal = buildReferenceItems(fields.internalLinks && fields.internalLinks.value, true);
    var faqItems = buildFaqItems(fields.faq && fields.faq.value);
    var copyright = norm(fields.copyright && fields.copyright.value);
    var editorialNote = norm(fields.editorialNote && fields.editorialNote.value);
    var related = splitCommaList(fields.related && fields.related.value);
    var today = todayIso();
    var lines = [
      "+++",
      'title = ' + tomlQuoted(title),
      'description = ' + tomlQuoted(description || metaDescription || ""),
      "date = " + today,
      "updated = " + today,
    ];

    if (series) {
      lines.push('series = ' + tomlQuoted(series));
    }
    if (related.length) {
      lines.push('related = [' + related.map(tomlQuoted).join(", ") + ']');
    }

    lines.push("");
    lines.push("[taxonomies]");
    lines.push("categories = [" + [category].map(tomlQuoted).join(", ") + "]");
    lines.push("tags = [" + tags.map(tomlQuoted).join(", ") + "]");
    lines.push("");
    lines.push("[extra]");
    lines.push('excerpt = ' + tomlQuoted(description || metaDescription || ""));
    lines.push('slug = ' + tomlQuoted(slug));
    lines.push('seo_title = ' + tomlQuoted(seoTitle));
    lines.push('seo_description = ' + tomlQuoted(metaDescription));
    lines.push('author = ' + tomlQuoted(author));
    lines.push('hero_mode = ' + tomlQuoted(heroMode));
    if (heroImage && heroMode === "image") lines.push('thumbnail = ' + tomlQuoted(heroImage));
    if (copyright) lines.push('references_copyright = ' + tomlQuoted(copyright));
    if (editorialNote) lines.push('editorial_note = ' + tomlQuoted(editorialNote));
    if (!referencesExternal.length && !referencesInternal.length) {
      lines.push('references_skip = false');
    }
    referencesExternal.forEach(function (item) {
      lines.push("");
      lines.push("[[extra.references_external]]");
      lines.push('title = ' + tomlQuoted(item.title));
      lines.push('url = ' + tomlQuoted(item.url));
    });
    referencesInternal.forEach(function (item) {
      lines.push("");
      lines.push("[[extra.references_internal]]");
      lines.push('title = ' + tomlQuoted(item.title));
      lines.push('url = ' + tomlQuoted(item.url));
    });
    faqItems.forEach(function (item) {
      lines.push("");
      lines.push("[[extra.faq]]");
      lines.push('q = ' + tomlQuoted(item.q));
      lines.push('a = ' + tomlQuoted(item.a));
    });
    lines.push("+++");
    lines.push("");
    var ending = body || "<!-- Viết nội dung bài tại đây -->";
    var requiredEndings = [
      ["## Liên kết nội bộ", referencesInternal.length
        ? referencesInternal.map(function (item) { return "- [" + item.title + "](" + item.url + ")"; }).join("\n")
        : "- TODO: kiểm tra và bổ sung liên kết nội bộ trước publish"],
      ["## Liên kết bên ngoài", referencesExternal.length
        ? referencesExternal.map(function (item) { return "- [" + item.title + "](" + item.url + ")"; }).join("\n")
        : "- TODO: kiểm tra và bổ sung nguồn uy tín trước publish"],
      ["## Bản quyền và ghi nguồn", copyright || "TODO: ghi rõ bản quyền, nguồn nội dung và nguồn/license ảnh trước publish"],
      ["## FAQ - Câu hỏi thường gặp", faqItems.length >= 3
        ? faqItems.map(function (item) { return "### " + item.q + "\n\n" + item.a; }).join("\n\n")
        : "TODO: bổ sung ít nhất 3 câu hỏi-trả lời tự nhiên trước publish"],
    ];
    requiredEndings.forEach(function (section) {
      if (ending.indexOf(section[0]) === -1) ending += "\n\n" + section[0] + "\n\n" + section[1];
    });
    lines.push(ending);
    return {
      slug: slug,
      section: section,
      category: category,
      author: author,
      seoTitle: seoTitle,
      description: description || metaDescription,
      metaDescription: metaDescription,
      body: body,
      faqItems: faqItems,
      referencesExternal: referencesExternal,
      referencesInternal: referencesInternal,
      content: lines.join("\n"),
      title: title,
    };
  }

  function plainTextLength(body) {
    return (body || "")
      .replace(/```[\s\S]*?```/g, "")
      .replace(/!\[[^\]]*\]\([^)]*\)/g, "")
      .replace(/\[[^\]]*\]\([^)]*\)/g, "")
      .replace(/https?:\/\/\S+/g, "")
      .replace(/[#*_>`\-+|]/g, "")
      .replace(/\s+/g, " ")
      .trim().length;
  }

  function updateCanonical() {
    var section = norm(fields.section && fields.section.value) || "posting";
    var slug = norm(fields.slug && fields.slug.value);
    var base = root.dataset.baseUrl || location.origin;
    var url = base.replace(/\/$/, "") + "/" + section + "/" + (slug ? slug + "/" : "");
    if (canonical) canonical.textContent = url;
  }

  function renderPreview() {
    var data = buildFrontmatter();
    var title = norm(fields.title && fields.title.value) || "CMS-V2 workspace draft";
    var excerpt = norm(fields.description && fields.description.value) || norm(fields.metaDescription && fields.metaDescription.value) || "Excerpt preview will reflect the draft summary and metadata flow.";
    if (preview.category) preview.category.textContent = data.category || "SEOMONEY";
    if (preview.date) preview.date.textContent = todayDisplay();
    if (preview.author) preview.author.textContent = data.author || "SEOMONEY";
    if (preview.title) preview.title.textContent = title;
    if (preview.excerpt) preview.excerpt.textContent = excerpt;
    if (preview.body) {
      var md = data.body || "# Draft body\n\nLive markdown source will appear here.";
      if (MARKED && typeof MARKED.parse === "function") {
        try {
          preview.body.innerHTML = MARKED.parse(md);
        } catch (e) {
          preview.body.textContent = md;
        }
      } else {
        preview.body.textContent = md;
      }
    }
  }

  function updatePreview() {
    renderPreview();
  }

  function analyzeMarkdown() {
    var body = norm(fields.body && fields.body.value);
    var lines = body.split(/\r?\n/).map(function (line) { return line.trim(); });
    var title = norm(fields.title && fields.title.value);
    var seoTitle = norm(fields.seoTitle && fields.seoTitle.value) || title;
    var metaDesc = norm(fields.metaDescription && fields.metaDescription.value);
    var slug = norm(fields.slug && fields.slug.value);
    var faqItems = buildFaqItems(fields.faq && fields.faq.value);
    var referencesExternal = buildReferenceItems(fields.externalSources && fields.externalSources.value, false);
    var referencesInternal = buildReferenceItems(fields.internalLinks && fields.internalLinks.value, true);
    var copyright = norm(fields.copyright && fields.copyright.value);
    var editorialNote = norm(fields.editorialNote && fields.editorialNote.value);

    function hasHeading(text) {
      return lines.some(function (line) { return line === text; });
    }

    function setCheck(name, ok) {
      var el = qa.checks[name];
      if (!el) return;
      el.textContent = ok ? "Passed" : "Missing";
      el.parentElement.classList.toggle("is-ok", !!ok);
      el.parentElement.classList.toggle("is-missing", !ok);
    }

    var checks = {
      external: referencesExternal.length > 0,
      internal: referencesInternal.length > 0,
      copyright: !!copyright,
      editorial: !!editorialNote,
    };

    Object.keys(checks).forEach(function (key) {
      setCheck(key, checks[key]);
    });

    if (qa.titleLength) {
      var titleOk = title.length >= 30 && title.length <= 70;
      qa.titleLength.textContent = titleOk ? "Title: good" : "Title: needs work";
    }

    if (qa.metaLength) {
      var metaOk = metaDesc.length >= 120 && metaDesc.length <= 160;
      if (!metaDesc.length) {
        qa.metaLength.textContent = "Meta: pending";
      } else {
        qa.metaLength.textContent = metaOk ? "Meta: good" : "Meta: needs work";
      }
    }

    if (qa.slugQuality) {
      var slugOk = /^[a-z0-9][a-z0-9-]{1,79}$/.test(slug);
      qa.slugQuality.textContent = slugOk ? "Slug: good" : "Slug: needs work";
    }

    if (qa.h1Match) {
      var h1Same = !!title && (!!seoTitle ? seoTitle === title : true);
      qa.h1Match.textContent = h1Same ? "H1 match: good" : "H1 match: review";
    }

    if (qa.schemaStatus) {
      var schemaReady = faqItems.length > 0 || hasHeading("## FAQ") || hasHeading("## Câu hỏi thường gặp");
      if (schemaReady) {
        qa.schemaStatus.textContent = "Schema: FAQ ready";
      } else if (body || referencesExternal.length || referencesInternal.length) {
        qa.schemaStatus.textContent = renderFaqSnippet(faqItems);
      } else {
        qa.schemaStatus.textContent = "Waiting for body and FAQ content.";
      }
    }

    return checks;
  }

  function updateCommandPanel() {
    var provider = authProviderLabel(state.user);
    var sessionLabel = state.authenticated
      ? provider + " session active"
      : "No active session";
    var draftLabel = state.dirty
      ? "Unsaved changes since " + (state.lastAutosaveAt || "latest input")
      : (state.lastAutosaveAt ? "Autosaved " + state.lastAutosaveAt : "Local draft idle");
    var publishLabel = state.lastPublishAt
      ? "Published " + state.lastPublishAt + (state.lastPublishCommit ? " · " + state.lastPublishCommit.slice(0, 7) : "")
      : "Not published yet";

    if (topbarPill) topbarPill.textContent = provider + " connected";
    if (rolePill) {
      rolePill.textContent = state.user ? ("User role / " + (state.user.role || (state.user.is_super ? "superadmin" : "admin"))) : "User role / guest";
    }
    setCommandState("Auth", state.authenticated ? provider + " admin connected" : "Waiting for login");
    setCommandState("Session", sessionLabel);
    setCommandState("Draft", draftLabel);
    setCommandState("Publish", publishLabel);

    if (reviewAuth) setText(reviewAuth, state.authenticated ? provider + " admin ready" : "Waiting");
    if (reviewDraft) setText(reviewDraft, state.dirty ? "Draft has unsaved changes" : "Blank / autosaved");
    if (reviewQa) setText(reviewQa, renderFaqSnippet(buildFaqItems(fields.faq && fields.faq.value)));
    if (reviewPublish) setText(reviewPublish, publishLabel);

    updatePublishButtons();
    renderHistory();
  }

  function setGuestState(message) {
    setHidden(gate, false);
    setHidden(shell, true);
    setHidden(reviewModal, true);
    setHidden(loginButton, false);
    if (loginButton) loginButton.disabled = false;
    if (status) status.textContent = message || "Đăng nhập GitHub bằng tài khoản admin để mở CMS-V2.";
    setHidden(userCard, true);
    setHidden(logoutButton, true);
    state.authenticated = false;
    state.user = null;
    state.provider = "";
    updateCommandPanel();
  }

  function populateUserCard(user) {
    setHidden(userCard, false);
    if (userAvatar) {
      if (user.avatar) {
        userAvatar.src = user.avatar;
        userAvatar.alt = user.username || user.name || "GitHub avatar";
        setHidden(userAvatar, false);
      } else {
        setHidden(userAvatar, true);
      }
    }
    if (userName) userName.textContent = user.name || user.username || "GitHub user";
    if (userEmail) userEmail.textContent = user.email || "";
    setHidden(logoutButton, false);
  }

  function showShell() {
    setHidden(gate, true);
    setHidden(shell, false);
    setHidden(loginButton, true);
    if (loginButton) loginButton.disabled = true;
  }

  function setAuthState(me) {
    state.user = me;
    state.authenticated = true;
    state.provider = me.provider || "github";
    populateUserCard(me);
    if (status) status.textContent = "Đã đăng nhập bằng GitHub admin.";
    showShell();
    updateCommandPanel();
  }

  async function logout() {
    try {
      await fetch(AUTH_API + "/auth/logout", {
        method: "POST",
        credentials: "include",
        cache: "no-store",
      });
    } catch (e) {}
    clearSid();
    setGuestState("Đã đăng xuất. Vui lòng đăng nhập GitHub để vào CMS-V2.");
  }

  function bindTabs() {
    tabs.forEach(function (tab) {
      tab.addEventListener("click", function () {
        var name = tab.getAttribute("data-cms-v2-tab");
        tabs.forEach(function (node) {
          var active = node === tab;
          node.classList.toggle("is-active", active);
          node.setAttribute("aria-selected", active ? "true" : "false");
        });
        panels.forEach(function (panel) {
          var active = panel.getAttribute("data-cms-v2-panel") === name;
          panel.hidden = !active;
          panel.classList.toggle("is-active", active);
        });
      });
    });
  }

  function populateCategories() {
    var select = fields.category;
    if (!select) return;
    var current = select.value || "Công nghệ";
    var baseOptions = Array.prototype.slice.call(select.options).map(function (opt) {
      return opt.value;
    }).filter(Boolean);
    var merged = [];

    function pushUnique(value) {
      if (!value) return;
      if (merged.indexOf(value) === -1) merged.push(value);
    }

    state.categories.forEach(pushUnique);
    baseOptions.forEach(pushUnique);
    if (!merged.length) merged = ["Công nghệ", "Ngân hàng", "Đời sống", "Du lịch", "Thể thao", "Báo chí"];

    select.innerHTML = merged.map(function (item) {
      return '<option value="' + escapeHtml(item) + '"' + (item === current ? ' selected' : '') + '>' + escapeHtml(item) + '</option>';
    }).join("");
    select.value = current;
  }

  async function loadCategories() {
    var sid = getSid();
    if (!AUTH_API || !sid) return;
    try {
      var res = await fetch(AUTH_API + "/api/categories/list", {
        method: "GET",
        headers: { Authorization: "Bearer " + sid },
        credentials: "include",
        cache: "no-store",
      });
      if (res.status === 401) {
        clearSid();
        return;
      }
      if (!res.ok) return;
      var data = await res.json();
      if (Array.isArray(data.categories)) {
        state.categories = data.categories.slice();
        if (state.categories.indexOf("Posting") === -1) state.categories.unshift("Posting");
        populateCategories();
      }
    } catch (e) {}
  }

  function updateCanonicalAndState() {
    updateCanonical();
    updatePreview();
    analyzeMarkdown();
    state.lastAutosaveAt = todayDisplay();
    state.dirty = true;
    setCommandState("Draft", "Unsaved changes since " + state.lastAutosaveAt);
    saveDraft();
    updateCommandPanel();
  }

  function wireField(el) {
    if (!el) return;
    el.addEventListener("input", updateCanonicalAndState);
    el.addEventListener("change", updateCanonicalAndState);
  }

  function bindComposer() {
    Object.keys(fields).forEach(function (key) {
      wireField(fields[key]);
    });

    if (fields.slug) {
      fields.slug.addEventListener("input", function () {
        fields.slug.dataset.cmsV2Touched = "true";
      });
    }

    if (fields.title && fields.slug) {
      fields.title.addEventListener("input", function () {
        if (fields.slug.dataset.cmsV2Touched === "true") return;
        fields.slug.value = slugify(fields.title.value);
        updateCanonicalAndState();
      });
    }

    if (fields.body) {
      fields.body.addEventListener("input", function () {
        updatePreview();
        analyzeMarkdown();
        state.lastAutosaveAt = todayDisplay();
        state.dirty = true;
        setCommandState("Draft", "Unsaved changes since " + state.lastAutosaveAt);
        saveDraft();
        updateCommandPanel();
      });
    }
  }

  function bindActions() {
    if (loginButton) {
      loginButton.addEventListener("click", startOAuth);
    }
    if (logoutButton) {
      logoutButton.addEventListener("click", async function (event) {
        event.preventDefault();
        await logout();
      });
    }

    reviewOpenButtons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        setHidden(reviewModal, false);
        updateCommandPanel();
      });
    });

    if (reviewCloseButton) {
      reviewCloseButton.addEventListener("click", function () {
        setHidden(reviewModal, true);
      });
    }

    if (reviewModal) {
      reviewModal.addEventListener("click", function (event) {
        if (event.target === reviewModal) setHidden(reviewModal, true);
      });
    }

    newDraftButtons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        newDraft();
      });
    });

    clearButtons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        clearDraft();
      });
    });

    publishButtons.forEach(function (btn) {
      btn.addEventListener("click", function (event) {
        event.preventDefault();
        publishDraft();
      });
    });

    copyButtons.forEach(function (btn) {
      btn.addEventListener("click", function (event) {
        event.preventDefault();
        copyMarkdown(btn);
      });
    });

    if (fields.body) {
      fields.body.addEventListener("keydown", function (event) {
        var key = event.key.toLowerCase();
        if ((event.metaKey || event.ctrlKey) && event.shiftKey && key === "c") {
          event.preventDefault();
          copyMarkdown();
        }
        if ((event.metaKey || event.ctrlKey) && key === "enter") {
          event.preventDefault();
          publishDraft();
        }
      });
    }

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && reviewModal && !reviewModal.hidden) {
        setHidden(reviewModal, true);
      }
    });
  }

  function validateBeforePublish() {
    var data = buildFrontmatter();
    if (!data.title || !data.slug) {
      window.alert("Thiếu tiêu đề hoặc slug.");
      return null;
    }
    if (!data.body || plainTextLength(data.body) < 50) {
      window.alert("Nội dung quá ngắn (cần >= 50 ký tự text).");
      return null;
    }
    if (!state.user || state.user.provider !== "github") {
      window.alert("Cần session GitHub admin để publish lên repo.");
      return null;
    }
    return data;
  }

  async function publishDraft() {
    var data = validateBeforePublish();
    if (!data) return;
    var sid = getSid();
    if (!sid) {
      window.alert("Phiên hết hạn. Vui lòng đăng nhập lại.");
      setGuestState("Phiên hết hạn. Vui lòng đăng nhập GitHub để vào CMS-V2.");
      return;
    }

    var content = data.content;
    var message = "CMS-V2: " + data.title;
    setCommandState("Publish", "Publishing to GitHub...");
    updateCommandPanel();

    try {
      var headers = {
        "Content-Type": "application/json",
        Authorization: "Bearer " + sid,
      };
      var res = await fetch(AUTH_API + "/cms/save-post", {
        method: "POST",
        headers: headers,
        credentials: "include",
        body: JSON.stringify({
          slug: data.slug,
          section: data.section,
          content: content,
          message: message,
        }),
      });

      if (res.status === 401) {
        clearSid();
        setGuestState("Phiên hết hạn. Vui lòng đăng nhập GitHub để vào CMS-V2.");
        return;
      }
      var payload = await res.json().catch(function () { return {}; });
      if (!res.ok) {
        setCommandState("Publish", "Publish failed");
        updateCommandPanel();
        window.alert(payload.detail || "Không thể publish bài.");
        return;
      }

      state.dirty = false;
      state.lastAutosaveAt = todayDisplay();
      state.lastPublishAt = todayDisplay();
      state.lastPublishCommit = payload.commit_sha || "";
      state.lastPublishUrl = payload.commit_url || "";
      state.lastPublishPath = payload.path || "";
      state.lastPublishTitle = data.title;
      state.history.unshift({
        title: data.title,
        slug: data.slug,
        path: payload.path || "",
        commitUrl: payload.commit_url || "",
        at: state.lastPublishAt,
      });
      state.history = state.history.slice(0, 8);
      saveHistory();
      saveDraft();
      setCommandState("Draft", "Autosaved " + state.lastAutosaveAt);
      setCommandState("Publish", "Published " + (payload.commit_sha ? payload.commit_sha.slice(0, 7) : data.slug));
      renderHistory();
      updateCommandPanel();
      if (reviewModal && !reviewModal.hidden) {
        setHidden(reviewModal, false);
      }
    } catch (err) {
      setCommandState("Publish", "Publish error");
      updateCommandPanel();
      window.alert("Không thể publish bài. " + err.message);
    }
  }

  function copyMarkdown(button) {
    var data = buildFrontmatter();
    var text = data.content;
    var done = function () {
      if (button) {
        var label = button.textContent;
        button.textContent = "Copied Markdown";
        setTimeout(function () { button.textContent = label; }, 1400);
      }
      setCommandState("Draft", state.dirty ? "Unsaved changes since " + state.lastAutosaveAt : "Markdown copied");
      updateCommandPanel();
    };

    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done).catch(function () {
        window.prompt("Copy Markdown:", text);
      });
      return;
    }
    window.prompt("Copy Markdown:", text);
    done();
  }

  function maybeRestoreState() {
    var draft = loadDraft();
    if (draft) {
      applyDraft(draft);
    }
    state.history = loadHistory();
    updateCommandPanel();
    renderHistory();
  }

  function boot() {
    state.authError = consumeAuthParams();
    bindTabs();
    bindComposer();
    bindActions();
    maybeRestoreState();
    setGuestState("Đang kiểm tra phiên GitHub…");
    updateCanonical();
    renderPreview();
    analyzeMarkdown();
    populateCategories();

    if (copyrightNote) {
      setText(copyrightNote, "Shortcut: Ctrl/Cmd + Shift + C để copy Markdown nhanh.");
    }

    if (fields.slug) {
      fields.slug.addEventListener("input", function () {
        if (fields.slug.value) fields.slug.dataset.cmsV2Touched = "true";
      });
    }

    var authPromise = fetchMe();
    authPromise.then(function (me) {
      if (me && me.__error === "backend_unreachable") {
        setGuestState("Không thể kiểm tra phiên GitHub lúc này. Vui lòng thử lại sau.");
        return;
      }
      if (!me || me.authenticated === false || !isAdminUser(me)) {
        clearSid();
        if (state.authError) {
          var authErrors = {
            access_denied: "Tài khoản GitHub này không có quyền quản trị CMS-V2.",
            invalid_state: "Phiên đăng nhập GitHub đã hết hạn. Vui lòng thử lại.",
            missing_params: "GitHub callback thiếu tham số. Vui lòng thử lại.",
            token_exchange_failed: "Không thể hoàn tất xác thực GitHub. Vui lòng thử lại.",
            github_unreachable: "Không thể kết nối GitHub. Vui lòng thử lại sau.",
            github_profile_fetch_failed: "Không thể đọc hồ sơ GitHub. Vui lòng thử lại.",
            github_disabled: "Đăng nhập GitHub hiện chưa khả dụng.",
          };
          setGuestState(authErrors[state.authError] || "Đăng nhập GitHub không thành công. Vui lòng thử lại.");
          return;
        }
        setGuestState("Đăng nhập GitHub bằng tài khoản admin để mở CMS-V2.");
        return;
      }

      setAuthState(me);
      loadCategories();
      updateCommandPanel();
    });

    if (fields.description && !fields.description.value && fields.metaDescription && fields.metaDescription.value) {
      fields.description.value = fields.metaDescription.value;
    }

    updateCommandPanel();
  }

  boot();
})();
