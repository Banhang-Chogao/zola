(function () {
  "use strict";

  var root = document.querySelector("[data-cms-v2]");
  if (!root) return;

  var AUTH_API = (function () {
    var meta = document.querySelector('meta[name="zola-cms-auth-api"]');
    return meta && meta.content ? meta.content.trim().replace(/\/$/, "") : "";
  })();

  var SESSION_KEY = "zola-cms-session-id";
  var DRAFT_KEY = "seomoney.cmsv2.draft.v1";
  var HISTORY_KEY = "seomoney.cmsv2.publish-history.v1";
  var AUTOGEN_DEBOUNCE_MS = 350;
  var CMS_RETURN_TO = "https://seomoney.org/cms-v6/";

  var field = {
    title: root.querySelector("[data-cms-v2-title]"),
    slug: root.querySelector("[data-cms-v2-slug]"),
    section: root.querySelector("[data-cms-v2-section]"),
    category: root.querySelector("[data-cms-v2-category]"),
    author: root.querySelector("[data-cms-v2-author]"),
    description: root.querySelector("[data-cms-v2-description]"),
    metaDescription: root.querySelector("[data-cms-v2-meta-description]"),
    seoTitle: root.querySelector("[data-cms-v2-seo-title]"),
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

  var ui = {
    authGateStatus: root.querySelector("[data-cms-v2-auth-status]"),
    authState: root.querySelector("[data-cms-v2-auth-state]"),
    sessionStatus: root.querySelector("[data-cms-v2-session-status]"),
    sessionState: root.querySelector("[data-cms-v2-session-state]"),
    draftStatus: root.querySelector("[data-cms-v2-draft-state]"),
    publishStatus: root.querySelector("[data-cms-v2-publish-state]"),
    authDot: root.querySelector("[data-cms-v2-auth-dot]"),
    sessionDot: root.querySelector("[data-cms-v2-session-dot]"),
    draftDot: root.querySelector("[data-cms-v2-draft-dot]"),
    publishDot: root.querySelector("[data-cms-v2-publish-dot]"),
    gateLogin: root.querySelector("[data-cms-v2-login]"),
    authModal: root.querySelector("[data-cms-v2-auth-modal]"),
    authModalMessage: root.querySelector("[data-cms-v2-auth-modal-message]"),
    authModalLogin: root.querySelector("[data-cms-v2-auth-modal-login]"),
    authModalClose: root.querySelector("[data-cms-v2-auth-modal-close]"),
    reviewHistory: root.querySelector("[data-cms-v2-review-history]"),
    preview: {
      category: root.querySelector("[data-cms-v2-preview-category]"),
      date: root.querySelector("[data-cms-v2-preview-date]"),
      author: root.querySelector("[data-cms-v2-preview-author]"),
      title: root.querySelector("[data-cms-v2-preview-title]"),
      excerpt: root.querySelector("[data-cms-v2-preview-excerpt]"),
      body: root.querySelector("[data-cms-v2-preview-body]"),
    },
    checks: {
      external: root.querySelector("[data-cms-v2-check='external']"),
      internal: root.querySelector("[data-cms-v2-check='internal']"),
      copyright: root.querySelector("[data-cms-v2-check='copyright']"),
      editorial: root.querySelector("[data-cms-v2-check='editorial']"),
    },
    publishButtons: Array.prototype.slice.call(root.querySelectorAll("[data-cms-v2-publish]")),
    counters: {
      title: root.querySelector("[data-cms-v2-title-length]"),
      meta: root.querySelector("[data-cms-v2-meta-length]"),
      slug: root.querySelector("[data-cms-v2-slug-quality]"),
      schema: root.querySelector("[data-cms-v2-schema-status]"),
      h1: root.querySelector("[data-cms-v2-h1-match]"),
    },
  };

  var state = {
    auth: null,
    authTimer: null,
    autoTimer: null,
    slugManual: false,
    slugUpdating: false,
    publishBusy: false,
  };

  function norm(value) {
    return (value || "").toString().trim();
  }

  function setText(el, value) {
    if (el) el.textContent = value == null ? "" : String(value);
  }

  function setHidden(el, hidden) {
    if (!el) return;
    el.hidden = !!hidden;
    el.setAttribute("aria-hidden", hidden ? "true" : "false");
  }

  function escapeHtml(value) {
    return norm(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function getCsrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"], meta[name="csrf"], meta[name="x-csrf-token"]');
    return meta && meta.content ? meta.content.trim() : "";
  }

  function getBaseUrl() {
    return (root.getAttribute("data-base-url") || location.origin).replace(/\/$/, "");
  }

  function getSid() {
    try {
      return sessionStorage.getItem(SESSION_KEY) || localStorage.getItem(SESSION_KEY) || "";
    } catch (e) {
      return "";
    }
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
    var error = params.get("auth_error") || "";
    if (sid) saveSid(sid);
    if (params.has("auth") || params.has("auth_error") || sid) {
      params.delete("auth");
      params.delete("auth_error");
      try {
        history.replaceState(null, "", location.pathname + (params.toString() ? "?" + params.toString() : ""));
      } catch (e) {}
      if (sid && location.hash) {
        try {
          history.replaceState(null, "", location.pathname + location.search);
        } catch (e) {}
      }
    }
    return error;
  }

  function removeAccents(value) {
    return norm(value)
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/đ/g, "d")
      .replace(/Đ/g, "D");
  }

  function generateSlug(value) {
    return removeAccents(value)
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 90);
  }

  function splitList(value) {
    return norm(value)
      .split(",")
      .map(function (item) { return norm(item); })
      .filter(Boolean);
  }

  function splitLines(value) {
    return norm(value)
      .split(/\r?\n/)
      .map(function (item) { return norm(item); })
      .filter(Boolean);
  }

  function extractKeywords(text) {
    var freq = {};
    norm(text)
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, " ")
      .split(/\s+/)
      .filter(function (word) { return word && word.length > 3; })
      .forEach(function (word) {
        freq[word] = (freq[word] || 0) + 1;
      });
    return Object.keys(freq).sort(function (a, b) { return freq[b] - freq[a]; }).slice(0, 5);
  }

  function fallbackSEO(title, excerpt, content) {
    var cleanTitle = norm(title) || "SEOMONEY";
    var cleanExcerpt = norm(excerpt) || norm(content).slice(0, 160);
    var seoTitle = (cleanTitle + " | SEOMONEY").slice(0, 60);
    var meta = cleanTitle + ". " + cleanExcerpt;
    if (meta.length < 150) {
      var keywords = extractKeywords(cleanTitle + " " + content).join(", ");
      if (keywords) meta = (meta + " " + keywords).trim();
    }
    if (meta.length > 160) meta = meta.slice(0, 157).replace(/\s+$/g, "") + "...";
    return { seoTitle: seoTitle, metaDescription: meta };
  }

  function fallbackFaq(content) {
    var lines = splitLines(content);
    var items = [];
    var current = null;

    function push() {
      if (current && current.question && current.answer) items.push(current);
      current = null;
    }

    lines.forEach(function (line) {
      var q = line.match(/^(?:Q|Question|Hỏi)\s*[:.]\s*(.+)$/i);
      var a = line.match(/^(?:A|Answer|Trả lời)\s*[:.]\s*(.+)$/i);
      if (q) {
        push();
        current = { question: q[1].trim(), answer: "" };
        return;
      }
      if (a && current) {
        current.answer = a[1].trim();
        return;
      }
      if (current && line) {
        current.answer = current.answer ? current.answer + " " + line : line;
      }
    });
    push();

    if (!items.length) {
      var heading = lines.find(function (line) { return /^#{2,4}\s+/.test(line); });
      if (heading) {
        items.push({
          question: heading.replace(/^#{2,4}\s+/, "").trim(),
          answer: lines.slice(1, 4).join(" ").slice(0, 180) || "Nội dung đang được trích xuất tự động.",
        });
      }
    }

    return items;
  }

  function formatFaq(items) {
    return items.map(function (item) {
      return "Q: " + item.question + "\nA: " + item.answer;
    }).join("\n\n");
  }

  function detectLinksFallback(content) {
    var urls = norm(content).match(/https?:\/\/[^\s"']+/g) || [];
    var internal = [];
    var external = [];

    urls.forEach(function (url) {
      if (/seomoney\.org/i.test(url)) internal.push(url);
      else external.push(url);
    });

    return {
      internalLinks: Array.from(new Set(internal)),
      externalSources: Array.from(new Set(external)),
      canonicalUrl: getBaseUrl() + "/" + norm(field.section && field.section.value || "posting") + "/" + (norm(field.slug && field.slug.value) ? norm(field.slug && field.slug.value) + "/" : ""),
    };
  }

  function formatLinkLines(items) {
    return items.map(function (item) {
      if (typeof item === "string") return item;
      var title = item.title || item.url || "";
      var url = item.url || item.href || item.link || item.title || "";
      if (!url) return title;
      return title + " | " + url;
    }).join("\n");
  }

  function formatRelated(items) {
    return items.map(function (item) {
      if (typeof item === "string") return item;
      var value = item.slug || item.title || "";
      if (typeof item.score === "number" && !isNaN(item.score)) {
        value += " | " + Math.round(item.score * 100) + "%";
      }
      return value;
    }).filter(Boolean).join("\n");
  }

  function applyValue(el, value, suppressSlugManual) {
    if (!el) return;
    var next = value == null ? "" : String(value);
    if (el.value === next) return;
    var previousSlugUpdating = state.slugUpdating;
    if (suppressSlugManual) state.slugUpdating = true;
    el.value = next;
    state.slugUpdating = previousSlugUpdating;
  }

  function setDot(dot, stateName) {
    if (!dot) return;
    dot.className = "cms-v2__status-dot cms-v2__status-dot--" + stateName;
  }

  function updateCounters() {
    var title = norm(field.title && field.title.value);
    var seoTitle = norm(field.seoTitle && field.seoTitle.value) || title;
    var meta = norm(field.metaDescription && field.metaDescription.value);
    setText(ui.counters.title, Math.min(seoTitle.length, 60) + "/60");
    setText(ui.counters.meta, Math.min(meta.length, 160) + "/160");
    setText(ui.counters.slug, /^[a-z0-9][a-z0-9-]{1,79}$/.test(norm(field.slug && field.slug.value)) ? "Slug: good" : "Slug: needs work");
    setText(ui.counters.h1, seoTitle === title ? "H1 match: good" : "H1 match: review");
    setText(ui.counters.schema, norm(field.faq && field.faq.value) ? "Schema: FAQ ready" : "Waiting for body and FAQ content.");
  }

  function serializeDraft() {
    var data = {};
    Object.keys(field).forEach(function (key) {
      var el = field[key];
      if (el) data[key] = el.value || "";
    });
    data.lastAutosaveAt = new Date().toISOString();
    return data;
  }

  function saveDraft() {
    try {
      localStorage.setItem(DRAFT_KEY, JSON.stringify(serializeDraft()));
    } catch (e) {}
  }

  function currentDisplayDate() {
    try {
      return new Intl.DateTimeFormat("vi-VN", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        timeZone: "Asia/Ho_Chi_Minh",
      }).format(new Date());
    } catch (e) {
      return new Date().toISOString().slice(0, 10);
    }
  }

  function renderPreview() {
    if (ui.preview.category) {
      ui.preview.category.textContent = norm(field.category && field.category.value) || "SEOMONEY";
    }
    if (ui.preview.date) {
      ui.preview.date.textContent = currentDisplayDate();
    }
    if (ui.preview.author) {
      ui.preview.author.textContent = norm(field.author && field.author.value) || norm(root.getAttribute("data-cms-v2-author-default")) || "SEOMONEY";
    }
    if (ui.preview.title) {
      ui.preview.title.textContent = norm(field.title && field.title.value) || "CMS-V2 workspace draft";
    }
    if (ui.preview.excerpt) {
      ui.preview.excerpt.textContent = norm(field.description && field.description.value) || norm(field.metaDescription && field.metaDescription.value) || "Excerpt preview will reflect the draft summary and metadata flow.";
    }
    if (ui.preview.body) {
      var md = norm(field.body && field.body.value) || "# Draft body\n\nLive markdown source will appear here.";
      if (window.marked && typeof window.marked.parse === "function") {
        try {
          ui.preview.body.innerHTML = window.marked.parse(md);
        } catch (e) {
          ui.preview.body.textContent = md;
        }
      } else {
        ui.preview.body.textContent = md;
      }
    }
  }

  function updateChecklist() {
    var checklist = {
      external: splitLines(field.externalSources && field.externalSources.value).length > 0,
      internal: splitLines(field.internalLinks && field.internalLinks.value).length > 0,
      copyright: !!norm(field.copyright && field.copyright.value),
      editorial: !!norm(field.editorialNote && field.editorialNote.value),
    };

    Object.keys(checklist).forEach(function (key) {
      var row = ui.checks[key];
      if (!row) return;
      var valueEl = row.querySelector("strong");
      if (valueEl) valueEl.textContent = checklist[key] ? "Passed" : "Missing";
      row.classList.toggle("is-ok", !!checklist[key]);
      row.classList.toggle("is-missing", !checklist[key]);
    });
  }

  function syncWorkspace(isDirty) {
    if (typeof isDirty === "boolean") {
      state.dirty = isDirty;
    }
    updateCounters();
    renderPreview();
    updateChecklist();
    saveDraft();
    if (state.dirty) {
      setText(ui.draftStatus, "Unsaved changes since " + currentDisplayDate());
      setDot(ui.draftDot, "warn");
    } else {
      setText(ui.draftStatus, "Local draft idle");
      setDot(ui.draftDot, "idle");
    }
  }

  async function requestJson(url, options) {
    var controller = new AbortController();
    var timer = setTimeout(function () { controller.abort(); }, 9000);
    try {
      var res = await fetch(url, Object.assign({
        credentials: "include",
        cache: "no-store",
        signal: controller.signal,
      }, options || {}));
      var payload = {};
      try { payload = await res.json(); } catch (e) {}
      return { ok: res.ok, status: res.status, payload: payload };
    } catch (e) {
      return { ok: false, status: -1, payload: null, error: e };
    } finally {
      clearTimeout(timer);
    }
  }

  async function getAuthState() {
    if (!AUTH_API) return { authenticated: false, githubConnected: false, error: "missing_auth_api" };
    var headers = { "X-Requested-With": "XMLHttpRequest" };
    var sid = getSid();
    if (sid) headers.Authorization = "Bearer " + sid;
    var res = await requestJson(AUTH_API + "/auth/me", {
      method: "GET",
      headers: headers,
    });
    if (res.status === 401 || res.status === 403) {
      clearSid();
      return { authenticated: false, githubConnected: false, error: "session_expired" };
    }
    if (!res.ok) {
      return { authenticated: false, githubConnected: false, error: "auth_check_failed" };
    }
    var user = res.payload || {};
    var githubConnected = true;
    if (typeof user.github_connected !== "undefined") {
      githubConnected = !!user.github_connected;
    } else if (typeof user.githubConnected !== "undefined") {
      githubConnected = !!user.githubConnected;
    } else if (user.provider) {
      githubConnected = user.provider === "github";
    }
    return {
      authenticated: user.authenticated !== false,
      githubConnected: githubConnected,
      user: user,
    };
  }

  function updateAuthUI(auth) {
    state.auth = auth;
    var ready = !!(auth && auth.authenticated && auth.githubConnected);
    if (ready) {
      setText(ui.authGateStatus, "GitHub connected");
      setText(ui.authState, "GitHub connected");
      setText(ui.sessionStatus, auth.user && (auth.user.name || auth.user.username || auth.user.email) ? (auth.user.name || auth.user.username || auth.user.email) : "superadmin OK");
      setText(ui.sessionState, auth.user && (auth.user.name || auth.user.username || auth.user.email) ? (auth.user.name || auth.user.username || auth.user.email) : "superadmin OK");
      setText(ui.publishStatus, "Ready to publish");
      setDot(ui.authDot, "ok");
      setDot(ui.sessionDot, "ok");
      setDot(ui.publishDot, "ok");
    } else if (auth && auth.authenticated) {
      setText(ui.authGateStatus, "GitHub not connected");
      setText(ui.authState, "GitHub not connected");
      setText(ui.sessionStatus, auth.user && (auth.user.name || auth.user.username || auth.user.email) ? (auth.user.name || auth.user.username || auth.user.email) : "Logged in");
      setText(ui.sessionState, auth.user && (auth.user.name || auth.user.username || auth.user.email) ? (auth.user.name || auth.user.username || auth.user.email) : "Logged in");
      setText(ui.publishStatus, "GitHub not connected");
      setDot(ui.authDot, "warn");
      setDot(ui.sessionDot, "ok");
      setDot(ui.publishDot, "warn");
    } else {
      setText(ui.authGateStatus, "Not connected");
      setText(ui.authState, "Waiting for login");
      setText(ui.sessionStatus, "Session expired");
      setText(ui.sessionState, "No active session");
      setText(ui.publishStatus, "Not published yet");
      setDot(ui.authDot, "error");
      setDot(ui.sessionDot, "error");
      setDot(ui.publishDot, "idle");
    }
    ui.publishButtons.forEach(function (btn) {
      btn.disabled = !ready || state.publishBusy;
      btn.title = ready ? "Publish bài viết lên GitHub" : "Vui lòng đăng nhập GitHub để publish";
    });
  }

  function showAuthModal(message) {
    if (ui.authModalMessage) {
      setText(ui.authModalMessage, message || "Phiên đăng nhập đã hết hạn hoặc GitHub chưa kết nối. Vui lòng đăng nhập lại để tiếp tục publish.");
    }
    setHidden(ui.authModal, false);
  }

  function hideAuthModal() {
    setHidden(ui.authModal, true);
  }

  async function generateSEO(title, excerpt, content) {
    var res = await requestJson("/api/ai/generate-seo", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({
        title: title,
        excerpt: excerpt,
        content: content,
        action: "generate_seo",
      }),
    });
    if (res.ok && res.payload) {
      return {
        seoTitle: res.payload.seo_title || res.payload.seoTitle || (title + " | SEOMONEY"),
        metaDescription: res.payload.meta_description || res.payload.metaDescription || fallbackSEO(title, excerpt, content).metaDescription,
      };
    }
    return fallbackSEO(title, excerpt, content);
  }

  async function generateFaq(content) {
    var res = await requestJson("/api/ai/extract-faq", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({
        content: content,
        action: "extract_faq",
      }),
    });
    if (res.ok && res.payload) {
      var list = res.payload.faqs || res.payload.items || [];
      if (Array.isArray(list) && list.length) {
        return list.map(function (item) {
          return {
            question: item.question || item.q || "",
            answer: item.answer || item.a || "",
          };
        }).filter(function (item) { return item.question && item.answer; });
      }
    }
    return fallbackFaq(content);
  }

  async function generateRelated(content, slug) {
    var res = await requestJson("/scoring/api/related", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({
        content: content,
        slug: slug,
        threshold: 0.7,
        action: "find_related",
      }),
    });
    if (res.ok && res.payload) {
      var posts = res.payload.related_posts || res.payload.posts || [];
      if (Array.isArray(posts)) {
        return posts.map(function (post) {
          return {
            slug: post.slug || "",
            title: post.title || post.slug || "",
            score: typeof post.score === "number" ? post.score : Number(post.score || 0),
          };
        }).filter(function (post) { return post.slug || post.title; });
      }
    }
    return [];
  }

  async function detectLinks(content) {
    var res = await requestJson("/api/ai/detect-links", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({
        content: content,
        action: "detect_links",
      }),
    });
    if (res.ok && res.payload) {
      return {
        internalLinks: res.payload.internal_links || res.payload.internalLinks || [],
        externalSources: res.payload.external_sources || res.payload.externalSources || [],
        canonicalUrl: res.payload.canonical_url || res.payload.canonicalUrl || detectLinksFallback(content).canonicalUrl,
      };
    }
    return detectLinksFallback(content);
  }

  function renderAutoFields(data) {
    if (data.seo) {
      applyValue(field.seoTitle, data.seo.seoTitle || "");
      applyValue(field.metaDescription, data.seo.metaDescription || "");
    }
    if (data.faq) applyValue(field.faq, formatFaq(data.faq));
    if (data.related) applyValue(field.related, formatRelated(data.related));
    if (data.links) {
      applyValue(field.internalLinks, formatLinkLines(data.links.internalLinks || []));
      applyValue(field.externalSources, formatLinkLines(data.links.externalSources || []));
      var canonical = root.querySelector("[data-cms-v2-canonical]");
      if (canonical && data.links.canonicalUrl) canonical.textContent = data.links.canonicalUrl;
    }
    applyValue(field.copyright, "© 2024 SEOMONEY. All rights reserved.");
    applyValue(field.editorialNote, "Bài viết được biên soạn bởi đội ngũ SEOMONEY.");
    syncWorkspace();
  }

  function scheduleAutoGeneration() {
    clearTimeout(state.autoTimer);
    state.autoTimer = setTimeout(async function () {
      var title = norm(field.title && field.title.value);
      var excerpt = norm(field.description && field.description.value);
      var content = norm(field.body && field.body.value);
      var slug = norm(field.slug && field.slug.value) || generateSlug(title);

      if (field.slug && !state.slugManual && slug) {
        applyValue(field.slug, slug, true);
      }

      if (!title && !excerpt && !content) {
        renderAutoFields({});
        return;
      }

      try {
        var results = await Promise.all([
          generateSEO(title, excerpt, content),
          generateFaq(content),
          generateRelated(content, slug),
          detectLinks(content),
        ]);
        renderAutoFields({
          seo: results[0],
          faq: results[1],
          related: results[2],
          links: results[3],
        });
      } catch (error) {
        renderAutoFields({
          seo: fallbackSEO(title, excerpt, content),
          faq: fallbackFaq(content),
          related: [],
          links: detectLinksFallback(content),
        });
      }
    }, AUTOGEN_DEBOUNCE_MS);
  }

  function updateSeriesState(yesSelected, focusOnEnable) {
    var seriesButtons = Array.prototype.slice.call(root.querySelectorAll("[data-cms-v2-series-toggle]"));
    seriesButtons.forEach(function (button) {
      button.classList.toggle("is-active", button.getAttribute("data-cms-v2-series-toggle") === (yesSelected ? "yes" : "no"));
    });
    if (!field.series) return;
    if (yesSelected) {
      field.series.disabled = false;
      field.series.placeholder = "Nhập tên Series...";
      field.series.classList.remove("is-disabled");
      if (focusOnEnable !== false) field.series.focus();
    } else {
      field.series.disabled = true;
      field.series.value = "";
      field.series.placeholder = "Không có Series (chọn Y để thêm)";
      field.series.classList.add("is-disabled");
      field.series.dispatchEvent(new Event("input", { bubbles: true }));
    }
  }

  function buildFrontmatter() {
    var title = norm(field.title && field.title.value) || "Bài viết mới";
    var slug = norm(field.slug && field.slug.value) || generateSlug(title);
    var section = norm(field.section && field.section.value) || "posting";
    var category = norm(field.category && field.category.value) || "Công nghệ";
    var author = norm(field.author && field.author.value) || norm(root.getAttribute("data-cms-v2-author-default")) || "SEOMONEY";
    var seoTitle = norm(field.seoTitle && field.seoTitle.value) || title + " | SEOMONEY";
    var excerpt = norm(field.description && field.description.value) || norm(field.metaDescription && field.metaDescription.value);
    var metaDescription = norm(field.metaDescription && field.metaDescription.value) || excerpt;
    var heroImage = norm(field.heroImage && field.heroImage.value);
    var heroMode = norm(field.heroMode && field.heroMode.value) || "fallback";
    var tags = splitList(field.tags && field.tags.value);
    var series = norm(field.series && field.series.value);
    var body = norm(field.body && field.body.value);
    var related = splitLines(field.related && field.related.value).map(function (line) { return line.split("|")[0].trim(); }).filter(Boolean);
    var internalLinks = splitLines(field.internalLinks && field.internalLinks.value);
    var externalSources = splitLines(field.externalSources && field.externalSources.value);
    var copyright = norm(field.copyright && field.copyright.value);
    var editorialNote = norm(field.editorialNote && field.editorialNote.value);
    var faqLines = splitLines(field.faq && field.faq.value);
    var today = new Date().toISOString().slice(0, 10);
    var lines = [
      "+++",
      'title = "' + title.replace(/"/g, '\\"') + '"',
      'description = "' + (excerpt || metaDescription || "").replace(/"/g, '\\"') + '"',
      "date = " + today,
      "updated = " + today,
    ];

    if (heroImage && heroMode === "image") lines.push('thumbnail = "' + heroImage.replace(/"/g, '\\"') + '"');
    if (series) lines.push('series = "' + series.replace(/"/g, '\\"') + '"');
    if (related.length) lines.push('related = [' + related.map(function (item) { return '"' + item.replace(/"/g, '\\"') + '"'; }).join(", ") + "]");
    lines.push("");
    lines.push("[taxonomies]");
    lines.push('categories = ["' + category.replace(/"/g, '\\"') + '"]');
    lines.push('tags = [' + tags.map(function (item) { return '"' + item.replace(/"/g, '\\"') + '"'; }).join(", ") + "]");
    lines.push("");
    lines.push("[extra]");
    lines.push('excerpt = "' + (excerpt || metaDescription || "").replace(/"/g, '\\"') + '"');
    lines.push('slug = "' + slug.replace(/"/g, '\\"') + '"');
    lines.push('seo_title = "' + seoTitle.replace(/"/g, '\\"') + '"');
    lines.push('seo_description = "' + metaDescription.replace(/"/g, '\\"') + '"');
    lines.push('author = "' + author.replace(/"/g, '\\"') + '"');
    lines.push('hero_mode = "' + heroMode.replace(/"/g, '\\"') + '"');
    if (heroImage) lines.push('hero_image = "' + heroImage.replace(/"/g, '\\"') + '"');
    if (copyright) lines.push('references_copyright = "' + copyright.replace(/"/g, '\\"') + '"');
    if (editorialNote) lines.push('editorial_note = "' + editorialNote.replace(/"/g, '\\"') + '"');
    if (!internalLinks.length && !externalSources.length) lines.push("references_skip = false");
    internalLinks.forEach(function (item) {
      lines.push("");
      lines.push("[[extra.references_internal]]");
      var parts = item.split("|").map(function (part) { return part.trim(); }).filter(Boolean);
      lines.push('title = "' + (parts[0] || item).replace(/"/g, '\\"') + '"');
      lines.push('url = "' + (parts[1] || parts[0] || item).replace(/"/g, '\\"') + '"');
    });
    externalSources.forEach(function (item) {
      lines.push("");
      lines.push("[[extra.references_external]]");
      var parts = item.split("|").map(function (part) { return part.trim(); }).filter(Boolean);
      lines.push('title = "' + (parts[0] || item).replace(/"/g, '\\"') + '"');
      lines.push('url = "' + (parts[1] || parts[0] || item).replace(/"/g, '\\"') + '"');
    });
    faqLines.forEach(function (line) {
      lines.push("");
      lines.push('faq = "' + line.replace(/"/g, '\\"') + '"');
    });
    lines.push("+++");
    lines.push("");
    lines.push(body || "<!-- Viết nội dung bài tại đây -->");
    return {
      title: title,
      slug: slug,
      section: section,
      content: lines.join("\n"),
    };
  }

  function readHistory() {
    try {
      var data = JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
      return Array.isArray(data) ? data : [];
    } catch (e) {
      return [];
    }
  }

  function saveHistory(list) {
    try {
      localStorage.setItem(HISTORY_KEY, JSON.stringify((list || []).slice(0, 8)));
    } catch (e) {}
  }

  function renderHistory(list) {
    if (!ui.reviewHistory) return;
    var items = list || readHistory();
    if (!items.length) {
      ui.reviewHistory.innerHTML = '<p class="cms-v2__card-note">Chưa có publish nào trong phiên này.</p>';
      return;
    }
    ui.reviewHistory.innerHTML = items.slice(0, 5).map(function (item) {
      var commitLink = item.commitUrl ? '<a href="' + escapeHtml(item.commitUrl) + '" target="_blank" rel="noopener">Xem commit</a>' : "";
      return '<div class="cms-v2__review-item">' +
        '<strong>' + escapeHtml(item.title || item.slug || "Untitled") + '</strong>' +
        '<span>' + escapeHtml(item.path || "") + '</span>' +
        '<span>' + escapeHtml(item.at || "") + (commitLink ? " " + commitLink : "") + '</span>' +
      '</div>';
    }).join("");
  }

  function setPublishBusy(isBusy) {
    state.publishBusy = !!isBusy;
    var ready = !!(state.auth && state.auth.authenticated && state.auth.githubConnected);
    ui.publishButtons.forEach(function (button) {
      var text = button.querySelector(".cms-v2__publish-text");
      var loading = button.querySelector(".cms-v2__publish-loading");
      if (text && loading) {
        text.hidden = !!isBusy;
        loading.hidden = !isBusy;
      }
      button.disabled = isBusy || !ready;
    });
    setDot(ui.publishDot, isBusy ? "warn" : (state.auth && state.auth.authenticated && state.auth.githubConnected ? "ok" : "idle"));
  }

  async function publishDraft() {
    var auth = state.auth || await getAuthState();
    state.auth = auth;
    updateAuthUI(auth);
    if (!auth.authenticated || !auth.githubConnected) {
      showAuthModal(auth.authenticated ? "GitHub chưa được kết nối. Vui lòng đăng nhập lại." : "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.");
      return;
    }

    var sid = getSid();
    if (!sid) {
      clearSid();
      updateAuthUI({ authenticated: false, githubConnected: false });
      showAuthModal("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.");
      return;
    }

    var data = buildFrontmatter();
    if (!data.title || !data.slug) {
      window.alert("Thiếu tiêu đề hoặc slug.");
      return;
    }
    if (!norm(field.body && field.body.value)) {
      window.alert("Vui lòng nhập nội dung bài viết.");
      return;
    }

    setPublishBusy(true);
    setText(ui.publishStatus, "Publishing...");
    try {
      var res = await requestJson(AUTH_API + "/cms/save-post", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(),
          Authorization: "Bearer " + sid,
        },
        body: JSON.stringify({
          slug: data.slug,
          section: data.section,
          content: data.content,
          message: "CMS-V2: " + data.title,
        }),
      });

      if (res.status === 401) {
        clearSid();
        updateAuthUI({ authenticated: false, githubConnected: false });
        showAuthModal("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.");
        return;
      }

      if (!res.ok) {
        window.alert((res.payload && (res.payload.detail || res.payload.message)) || "Không thể publish bài.");
        return;
      }

      var nowLabel = new Date().toLocaleDateString("vi-VN", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        timeZone: "Asia/Ho_Chi_Minh",
      });
      var history = readHistory();
      history.unshift({
        title: data.title,
        slug: data.slug,
        path: res.payload && res.payload.path ? res.payload.path : "",
        commitUrl: res.payload && res.payload.commit_url ? res.payload.commit_url : "",
        at: nowLabel,
      });
      saveHistory(history);
      renderHistory(history);
      setText(ui.publishStatus, "Published");
      setDot(ui.publishDot, "ok");
      hideAuthModal();
      window.alert("Bài viết đã được xuất bản thành công!");
    } catch (error) {
      window.alert("Lỗi kết nối. Vui lòng thử lại.");
    } finally {
      setPublishBusy(false);
    }
  }

  function clearDraft() {
    if (!window.confirm("Xoá draft local trên trình duyệt này?")) return;
    try { localStorage.removeItem(DRAFT_KEY); } catch (e) {}
    state.slugManual = false;
    [field.title, field.slug, field.description, field.metaDescription, field.seoTitle, field.heroImage, field.tags, field.body, field.faq, field.related, field.internalLinks, field.externalSources, field.copyright, field.editorialNote].forEach(function (el) {
      if (el) el.value = "";
    });
    applyValue(field.copyright, "© 2024 SEOMONEY. All rights reserved.");
    applyValue(field.editorialNote, "Bài viết được biên soạn bởi đội ngũ SEOMONEY.");
    updateSeriesState(false, false);
    syncWorkspace(false);
    renderAutoFields({});
    setText(ui.draftStatus, "Local draft cleared");
    setDot(ui.draftDot, "idle");
    scheduleAutoGeneration();
  }

  function newDraft() {
    if (!window.confirm("Tạo draft mới và bỏ nội dung hiện tại?")) return;
    state.slugManual = false;
    [field.title, field.slug, field.description, field.metaDescription, field.seoTitle, field.heroImage, field.tags, field.body, field.faq, field.related, field.internalLinks, field.externalSources, field.copyright, field.editorialNote].forEach(function (el) {
      if (el) el.value = "";
    });
    applyValue(field.copyright, "© 2024 SEOMONEY. All rights reserved.");
    applyValue(field.editorialNote, "Bài viết được biên soạn bởi đội ngũ SEOMONEY.");
    updateSeriesState(false, false);
    syncWorkspace(false);
    renderAutoFields({});
    setText(ui.draftStatus, "New blank draft ready");
    setDot(ui.draftDot, "ok");
    scheduleAutoGeneration();
  }

  function wireSeries() {
    Array.prototype.slice.call(root.querySelectorAll("[data-cms-v2-series-toggle]")).forEach(function (button) {
      button.addEventListener("click", function () {
        updateSeriesState(button.getAttribute("data-cms-v2-series-toggle") === "yes", true);
      });
    });
  }

  function wireSlug() {
    if (!field.slug) return;
    field.slug.addEventListener("input", function () {
      if (!state.slugUpdating) state.slugManual = true;
    });
    if (field.title) {
      field.title.addEventListener("input", function () {
        if (!state.slugManual || !norm(field.slug.value)) {
          applyValue(field.slug, generateSlug(field.title.value), true);
        }
        scheduleAutoGeneration();
      });
    }
  }

  function wireGeneration() {
    [field.description, field.body, field.section, field.category, field.tags, field.series].forEach(function (el) {
      if (!el) return;
      el.addEventListener("input", scheduleAutoGeneration);
      el.addEventListener("change", scheduleAutoGeneration);
    });
    scheduleAutoGeneration();
  }

  function wireAuthModal() {
    if (ui.authModalLogin) {
      ui.authModalLogin.addEventListener("click", function () {
        if (ui.gateLogin) {
          ui.gateLogin.click();
          return;
        }
        if (AUTH_API) {
          var url = new URL("/auth/login", AUTH_API);
          url.searchParams.set("return_to", CMS_RETURN_TO);
          location.href = url.toString();
        }
      });
    }
    if (ui.authModalClose) {
      ui.authModalClose.addEventListener("click", hideAuthModal);
    }
    if (ui.authModal) {
      ui.authModal.addEventListener("click", function (event) {
        if (event.target === ui.authModal) hideAuthModal();
      });
    }
  }

  function wireWorkspaceInputs() {
    var selectors = [
      "[data-cms-v2-title]",
      "[data-cms-v2-slug]",
      "[data-cms-v2-section]",
      "[data-cms-v2-category]",
      "[data-cms-v2-author]",
      "[data-cms-v2-description]",
      "[data-cms-v2-hero-image]",
      "[data-cms-v2-hero-mode]",
      "[data-cms-v2-series]",
      "[data-cms-v2-tags]",
      "[data-cms-v2-body]",
    ].join(",");

    function handle(event) {
      var target = event.target && event.target.closest ? event.target.closest(selectors) : null;
      if (!target || !root.contains(target)) return;
      event.stopImmediatePropagation();

      if (target === field.slug) {
        state.slugManual = true;
      }
      if (target === field.title) {
        if (!state.slugManual || !norm(field.slug && field.slug.value)) {
          field.slug.value = generateSlug(field.title.value);
        }
      }

      syncWorkspace(true);
      scheduleAutoGeneration();
    }

    root.addEventListener("input", handle, true);
    root.addEventListener("change", handle, true);
  }

  function wireIntercepts() {
    document.addEventListener("click", function (event) {
      var publish = event.target.closest("[data-cms-v2-publish]");
      var clearBtn = event.target.closest("[data-cms-v2-clear-draft]");
      var newBtn = event.target.closest("[data-cms-v2-new-draft]");
      if (publish) {
        event.preventDefault();
        event.stopImmediatePropagation();
        publishDraft();
        return;
      }
      if (clearBtn) {
        event.preventDefault();
        event.stopImmediatePropagation();
        clearDraft();
        return;
      }
      if (newBtn) {
        event.preventDefault();
        event.stopImmediatePropagation();
        newDraft();
      }
    }, true);

    document.addEventListener("submit", function (event) {
      var form = event.target.closest ? event.target.closest("[data-cms-v2-form]") : event.target;
      if (!form) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      publishDraft();
    }, true);

    document.addEventListener("keydown", function (event) {
      var key = event.key && event.key.toLowerCase();
      if ((event.metaKey || event.ctrlKey) && key === "enter") {
        event.preventDefault();
        event.stopImmediatePropagation();
        publishDraft();
      }
    }, true);
  }

  function bootAuth() {
    var error = consumeAuthParams();
    if (error && ui.authModalMessage) {
      setText(ui.authModalMessage, "Phiên đăng nhập GitHub đã hết hạn. Vui lòng thử lại.");
    }
    clearInterval(state.authTimer);
    state.authTimer = setInterval(async function () {
      var auth = await getAuthState();
      updateAuthUI(auth);
    }, 30000);
    return getAuthState().then(function (auth) {
      updateAuthUI(auth);
      return auth;
    }).catch(function () {
      updateAuthUI({ authenticated: false, githubConnected: false });
    });
  }

  function boot() {
    wireSeries();
    wireSlug();
    wireGeneration();
    wireAuthModal();
    wireWorkspaceInputs();
    wireIntercepts();
    updateSeriesState(!!norm(field.series && field.series.value), false);
    renderHistory();
    [field.seoTitle, field.metaDescription, field.faq, field.related, field.internalLinks, field.externalSources, field.copyright, field.editorialNote].forEach(function (el) {
      if (el) el.setAttribute("readonly", "readonly");
    });
    syncWorkspace(false);
    bootAuth();
  }

  boot();
})();
