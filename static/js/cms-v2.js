/**
 * CMS-V2 controller
 *
 * Read-only first version:
 *   - GitHub OAuth admin gate
 *   - tab switching
 *   - live composer validation
 *   - homepage/ad/SEO previews
 *
 * No write/publish API is assumed here.
 */
(function () {
  "use strict";

  if (window.__cmsV2InitDone) return;
  window.__cmsV2InitDone = true;

  var AUTH_API = (function () {
    var meta = document.querySelector('meta[name="zola-cms-auth-api"]');
    if (meta && meta.content) return meta.content.replace(/\/$/, "");
    return "https://blog-vipzone-api.onrender.com";
  })();

  var SESSION_KEY = "zola-cms-session-id";
  var CMS_RETURN_TO = "https://seomoney.org/cms-v2/";
  var root = document.querySelector("[data-cms-v2]");
  if (!root) return;

  var gate = root.querySelector("[data-cms-v2-gate]");
  var shell = root.querySelector("[data-cms-v2-shell]");
  var status = root.querySelector("[data-cms-v2-auth-status]");
  var loginButton = root.querySelector("[data-cms-v2-login]");
  var tabs = Array.prototype.slice.call(root.querySelectorAll("[data-cms-v2-tab]"));
  var panels = Array.prototype.slice.call(root.querySelectorAll("[data-cms-v2-panel]"));

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
  var schemaStatus = root.querySelector("[data-cms-v2-schema-status]");
  var titleLength = root.querySelector("[data-cms-v2-title-length]");
  var metaLength = root.querySelector("[data-cms-v2-meta-length]");
  var slugQuality = root.querySelector("[data-cms-v2-slug-quality]");
  var h1Match = root.querySelector("[data-cms-v2-h1-match]");

  var requiredChecks = {
    external: root.querySelector("[data-cms-v2-check='external'] strong"),
    internal: root.querySelector("[data-cms-v2-check='internal'] strong"),
    copyright: root.querySelector("[data-cms-v2-check='copyright'] strong"),
    editorial: root.querySelector("[data-cms-v2-check='editorial'] strong"),
  };

  function getSid() {
    try {
      var sid = localStorage.getItem(SESSION_KEY) || "";
      if (!sid) {
        var legacySid = sessionStorage.getItem(SESSION_KEY) || "";
        if (legacySid) {
          localStorage.setItem(SESSION_KEY, legacySid);
          sessionStorage.removeItem(SESSION_KEY);
          sid = legacySid;
        }
      }
      return sid;
    } catch (e) {}
    return "";
  }

  function setSid(sid) {
    try { localStorage.setItem(SESSION_KEY, sid); } catch (e) {}
    try { sessionStorage.removeItem(SESSION_KEY); } catch (e) {}
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
    var sid = readHashSid();
    if (sid) setSid(sid);
    var params = new URLSearchParams(location.search);
    var authError = params.get("auth_error") || "";
    var hadAuthParams = params.has("auth") || params.has("auth_error") || !!sid;
    params.delete("auth");
    params.delete("auth_error");
    if (hadAuthParams) {
      try {
        history.replaceState(null, "", location.pathname + (params.toString() ? "?" + params.toString() : ""));
      } catch (e) {}
    }
    return authError;
  }

  function buildLoginUrl() {
    var url = new URL("/auth/login", AUTH_API);
    url.searchParams.set("return_to", CMS_RETURN_TO);
    return url.toString();
  }

  function startOAuth() {
    if (!AUTH_API) return;
    window.location.assign(buildLoginUrl());
  }

  async function meRequest(useBearer) {
    var headers = {};
    if (useBearer) {
      var sid = getSid();
      if (!sid) return { status: 0 };
      headers.Authorization = "Bearer " + sid;
    }

    var controller = new AbortController();
    var timer = setTimeout(function () { controller.abort(); }, 10000);
    try {
      var res = await fetch(AUTH_API + "/auth/me", {
        method: "GET",
        headers: headers,
        credentials: "include",
        cache: "no-store",
        signal: controller.signal,
      });
      if (!res.ok) return { status: res.status };
      return { status: 200, user: await res.json() };
    } catch (e) {
      return { status: -1 };
    } finally {
      clearTimeout(timer);
    }
  }

  async function fetchMe() {
    if (!AUTH_API) return null;
    var sid = getSid();
    var bearer = sid ? await meRequest(true) : { status: 0 };
    if (bearer.status === 200) return bearer.user;

    // The HttpOnly cookie is the durable session source. Cookie-only retry also
    // recovers when an old Bearer sid exists in localStorage.
    var cookie = await meRequest(false);
    if (cookie.status === 200) return cookie.user;
    if (cookie.status === 401 && sid) clearSid();
    if (bearer.status === -1 || cookie.status === -1) {
      return { __error: "backend_unreachable" };
    }
    return null;
  }

  var AUTH_ERROR_MESSAGES = {
    access_denied: "Tài khoản GitHub này không có quyền quản trị CMS-V2.",
    invalid_state: "Phiên đăng nhập GitHub đã hết hạn. Vui lòng thử lại.",
    missing_params: "GitHub callback thiếu tham số. Vui lòng thử lại.",
    token_exchange_failed: "Không thể hoàn tất xác thực GitHub. Vui lòng thử lại.",
    github_unreachable: "Không thể kết nối GitHub. Vui lòng thử lại sau.",
    github_profile_fetch_failed: "Không thể đọc hồ sơ GitHub. Vui lòng thử lại.",
    github_disabled: "Đăng nhập GitHub hiện chưa khả dụng.",
  };

  function showShell() {
    if (gate) gate.hidden = true;
    if (shell) shell.hidden = false;
  }

  function showGate(msg) {
    if (gate) gate.hidden = false;
    if (shell) shell.hidden = true;
    if (status && msg) status.textContent = msg;
  }

  function setActiveTab(name) {
    tabs.forEach(function (tab) {
      var active = tab.getAttribute("data-cms-v2-tab") === name;
      tab.classList.toggle("is-active", active);
      tab.setAttribute("aria-selected", active ? "true" : "false");
    });
    panels.forEach(function (panel) {
      var active = panel.getAttribute("data-cms-v2-panel") === name;
      panel.hidden = !active;
      panel.classList.toggle("is-active", active);
    });
  }

  function updateCanonical() {
    var section = fields.section && fields.section.value ? fields.section.value.trim() : "posting";
    var slug = fields.slug && fields.slug.value ? fields.slug.value.trim() : "";
    var base = root.dataset.baseUrl || location.origin;
    var url = base.replace(/\/$/, "") + "/" + section + "/" + (slug ? slug + "/" : "");
    if (canonical) canonical.textContent = url;
  }

  function analyzeMarkdown(text) {
    var body = (text || "").trim();
    var lines = body.split(/\r?\n/).map(function (line) { return line.trim(); });
    function hasHeading(h) {
      return lines.some(function (line) { return line === h; });
    }
    function hasAnyKeyword(k) {
      return body.toLowerCase().indexOf(k) !== -1;
    }

    var checks = {
      external: hasHeading("## Liên kết bên ngoài được sử dụng trong bài viết"),
      internal: hasHeading("## Liên kết nội bộ liên quan"),
      copyright: hasHeading("## Tuyên bố bản quyền"),
      editorial: hasHeading("## Ghi chú biên tập"),
    };

    Object.keys(requiredChecks).forEach(function (key) {
      var el = requiredChecks[key];
      if (!el) return;
      el.textContent = checks[key] ? "Passed" : "Missing";
      el.parentElement.classList.toggle("is-ok", !!checks[key]);
      el.parentElement.classList.toggle("is-missing", !checks[key]);
    });

    var title = fields.title ? fields.title.value.trim() : "";
    var slug = fields.slug ? fields.slug.value.trim() : "";
    var seoTitle = fields.seoTitle ? fields.seoTitle.value.trim() : "";
    var metaDesc = fields.metaDescription ? fields.metaDescription.value.trim() : "";
    var h1Same = !!title && (!!seoTitle ? seoTitle === title : true);
    var titleOk = title.length >= 30 && title.length <= 70;
    var metaOk = metaDesc.length >= 120 && metaDesc.length <= 160;
    var slugOk = /^[a-z0-9][a-z0-9-]{1,79}$/.test(slug);

    if (titleLength) titleLength.textContent = titleOk ? "Title: good" : "Title: needs work";
    if (metaLength) metaLength.textContent = metaOk ? "Meta: good" : "Meta: needs work";
    if (slugQuality) slugQuality.textContent = slugOk ? "Slug: good" : "Slug: needs work";
    if (h1Match) h1Match.textContent = h1Same ? "H1 match: good" : "H1 match: review";

    if (schemaStatus) {
      var faqOk = !!(fields.faq && fields.faq.value.trim());
      var internalOk = !!(fields.internalLinks && fields.internalLinks.value.trim());
      var extOk = !!(fields.externalSources && fields.externalSources.value.trim());
      schemaStatus.textContent = faqOk || extOk || internalOk ? "Schema: ready to validate" : "Schema: waiting for content";
    }

    if (fields.description && fields.metaDescription) {
      var source = fields.description.value.trim() || fields.metaDescription.value.trim();
      if (source.length > 0 && source.length < 120) {
        metaLength.textContent = "Meta: short";
      }
    }

    if (fields.heroMode && fields.heroImage) {
      var heroMode = fields.heroMode.value;
      if (heroMode === "fallback") {
        // No-op: preview uses internal fallback card.
      }
    }

    if (fields.body) {
      var hasFaq = hasAnyKeyword("faq") || hasHeading("## FAQ");
      if (schemaStatus && hasFaq) {
        schemaStatus.textContent = "Schema: FAQ detected";
      }
    }

    return checks;
  }

  function bindComposer() {
    Object.keys(fields).forEach(function (key) {
      var el = fields[key];
      if (!el) return;
      el.addEventListener("input", function () {
        updateCanonical();
        analyzeMarkdown(fields.body ? fields.body.value : "");
      });
      el.addEventListener("change", function () {
        updateCanonical();
        analyzeMarkdown(fields.body ? fields.body.value : "");
      });
    });
    updateCanonical();
    analyzeMarkdown(fields.body ? fields.body.value : "");
  }

  function bindTabs() {
    tabs.forEach(function (tab) {
      tab.addEventListener("click", function () {
        setActiveTab(tab.getAttribute("data-cms-v2-tab"));
      });
    });
  }

  async function boot() {
    var authError = consumeAuthParams();
    bindTabs();
    bindComposer();
    if (loginButton) {
      loginButton.addEventListener("click", function (event) {
        event.preventDefault();
        startOAuth();
      });
    }

    var me = await fetchMe();
    if (me && me.__error === "backend_unreachable") {
      showGate("Không thể kiểm tra phiên GitHub lúc này. Vui lòng thử lại sau.");
      return;
    }
    if (!me || me.provider !== "github" || !(me.is_admin || me.is_super)) {
      if (authError) {
        showGate(AUTH_ERROR_MESSAGES[authError] || "Đăng nhập GitHub không thành công. Vui lòng thử lại.");
        return;
      }
      showGate("Đăng nhập GitHub bằng tài khoản admin để mở CMS-V2.");
      return;
    }

    showShell();
  }

  boot();
})();

/* CMS-V2 Quick Usable Layer — draft autosave, preview, copy markdown */
(function () {
  "use strict";

  var DRAFT_KEY = "seomoney.cmsv2.quickDraft.v1";

  function ready(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }

  function norm(s) {
    return (s || "").toString().trim();
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

  function esc(value) {
    return norm(value)
      .replace(/\\/g, "\\\\")
      .replace(/"/g, '\\"')
      .replace(/\n/g, " ");
  }

  function findField(names) {
    var selectors = [];
    names.forEach(function (name) {
      selectors.push("[name='" + name + "']");
      selectors.push("#" + name);
      selectors.push("[data-field='" + name + "']");
      selectors.push("[data-cms-v2-field='" + name + "']");
    });
    return document.querySelector(selectors.join(","));
  }

  function valueOf(el) {
    return el ? norm(el.value) : "";
  }

  function setValue(el, value) {
    if (el && typeof el.value !== "undefined") el.value = value || "";
  }

  function collectFields() {
    return {
      title: findField(["title", "post-title", "cms-title", "cms-v2-title"]),
      slug: findField(["slug", "post-slug", "cms-slug", "cms-v2-slug"]),
      category: findField(["category", "categories", "post-category", "cms-category"]),
      tags: findField(["tags", "post-tags", "cms-tags"]),
      seoTitle: findField(["seo_title", "seo-title", "seoTitle", "cms-seo-title"]),
      seoDescription: findField(["seo_description", "seo-description", "seoDescription", "cms-seo-description"]),
      excerpt: findField(["excerpt", "summary", "post-excerpt"]),
      body: findField(["body", "content", "markdown", "post-body", "cms-body", "article-body"]),
      notes: findField(["notes", "editor_notes", "editor-notes"])
    };
  }

  function makePanel() {
    var shell = document.querySelector(".cms-v2__shell, .cms-v2, main, body");
    if (!shell || document.querySelector("[data-cms-v2-quick-panel]")) return;

    var panel = document.createElement("section");
    panel.className = "cms-v2__panel cms-v2__quick-panel";
    panel.setAttribute("data-cms-v2-quick-panel", "true");
    panel.innerHTML =
      '<div class="cms-v2__panel-head">' +
        '<div>' +
          '<p class="cms-v2__eyebrow">Quick usable mode</p>' +
          '<h2>Composer preview & export</h2>' +
        '</div>' +
        '<div class="cms-v2__actions">' +
          '<button type="button" class="cms-v2__button" data-cms-v2-copy-markdown>Copy Markdown</button>' +
          '<button type="button" class="cms-v2__button cms-v2__button--ghost" data-cms-v2-clear-draft>Clear draft</button>' +
        '</div>' +
      '</div>' +
      '<div class="cms-v2__metrics" data-cms-v2-counters></div>' +
      '<p class="cms-v2__notice">Publish trực tiếp chưa bật — dùng Copy Markdown hoặc mở Editor cũ.</p>' +
      '<div class="cms-v2__preview-copy">' +
        '<h3>Markdown preview</h3>' +
        '<pre class="cms-v2__markdown" data-cms-v2-markdown-preview></pre>' +
      '</div>';

    shell.appendChild(panel);
  }

  function splitTags(raw) {
    return norm(raw)
      .split(",")
      .map(function (x) { return norm(x); })
      .filter(Boolean);
  }

  function markdown(fields) {
    var title = valueOf(fields.title);
    var slug = valueOf(fields.slug) || slugify(title);
    var category = valueOf(fields.category) || "Công nghệ";
    var tags = splitTags(valueOf(fields.tags));
    var seoTitle = valueOf(fields.seoTitle) || title;
    var seoDescription = valueOf(fields.seoDescription);
    var excerpt = valueOf(fields.excerpt);
    var body = valueOf(fields.body) || "<!-- Viết nội dung bài tại đây -->";
    var today = new Date().toISOString().slice(0, 10);

    return [
      "+++",
      'title = "' + esc(title || "Bài viết mới") + '"',
      'date = ' + today,
      'updated = ' + today,
      "",
      "[taxonomies]",
      'categories = ["' + esc(category) + '"]',
      "tags = [" + tags.map(function (tag) { return '"' + esc(tag) + '"'; }).join(", ") + "]",
      "",
      "[extra]",
      'slug = "' + esc(slug) + '"',
      'seo_title = "' + esc(seoTitle) + '"',
      'seo_description = "' + esc(seoDescription) + '"',
      'excerpt = "' + esc(excerpt) + '"',
      "+++",
      "",
      body
    ].join("\n");
  }

  function saveDraft(fields) {
    var data = {};
    Object.keys(fields).forEach(function (key) {
      if (fields[key]) data[key] = fields[key].value || "";
    });
    try {
      localStorage.setItem(DRAFT_KEY, JSON.stringify(data));
    } catch (e) {}
  }

  function restoreDraft(fields) {
    var raw = "";
    try {
      raw = localStorage.getItem(DRAFT_KEY) || "";
    } catch (e) {}
    if (!raw) return false;

    try {
      var data = JSON.parse(raw);
      Object.keys(fields).forEach(function (key) {
        if (fields[key] && typeof data[key] !== "undefined" && !fields[key].value) {
          fields[key].value = data[key];
        }
      });
      return true;
    } catch (e) {
      return false;
    }
  }

  function update(fields) {
    if (fields.title && fields.slug && !fields.slug.dataset.cmsV2Touched) {
      fields.slug.value = slugify(fields.title.value);
    }

    var preview = document.querySelector("[data-cms-v2-markdown-preview]");
    if (preview) preview.textContent = markdown(fields);

    var counters = document.querySelector("[data-cms-v2-counters]");
    if (counters) {
      counters.innerHTML = [
        "<span>Title: " + valueOf(fields.title).length + "</span>",
        "<span>SEO title: " + valueOf(fields.seoTitle).length + "/60</span>",
        "<span>SEO desc: " + valueOf(fields.seoDescription).length + "/160</span>",
        "<span>Excerpt: " + valueOf(fields.excerpt).length + "</span>",
        "<span>Body: " + valueOf(fields.body).split(/\s+/).filter(Boolean).length + " words</span>"
      ].join("");
    }

    saveDraft(fields);
  }

  function disableFakePublish() {
    Array.prototype.forEach.call(document.querySelectorAll("button, a"), function (el) {
      var txt = norm(el.textContent).toLowerCase();
      if (txt.indexOf("publish") >= 0 || txt.indexOf("xuất bản") >= 0) {
        el.setAttribute("aria-disabled", "true");
        if (el.tagName === "BUTTON") el.disabled = true;
        el.title = "Publish trực tiếp chưa bật — dùng Copy Markdown hoặc mở Editor cũ.";
      }
    });
  }

  ready(function () {
    makePanel();

    var fields = collectFields();
    restoreDraft(fields);

    if (fields.slug) {
      fields.slug.addEventListener("input", function () {
        fields.slug.dataset.cmsV2Touched = "true";
      });
    }

    Object.keys(fields).forEach(function (key) {
      var el = fields[key];
      if (!el) return;
      el.addEventListener("input", function () { update(fields); });
      el.addEventListener("change", function () { update(fields); });
    });

    var copy = document.querySelector("[data-cms-v2-copy-markdown]");
    if (copy) {
      copy.addEventListener("click", function () {
        var text = markdown(fields);
        navigator.clipboard.writeText(text).then(function () {
          copy.textContent = "Copied Markdown";
          setTimeout(function () { copy.textContent = "Copy Markdown"; }, 1400);
        }).catch(function () {
          window.prompt("Copy Markdown:", text);
        });
      });
    }

    var clear = document.querySelector("[data-cms-v2-clear-draft]");
    if (clear) {
      clear.addEventListener("click", function () {
        if (!window.confirm("Xoá draft local trên trình duyệt này?")) return;
        try { localStorage.removeItem(DRAFT_KEY); } catch (e) {}
        Object.keys(fields).forEach(function (key) { setValue(fields[key], ""); });
        update(fields);
      });
    }

    disableFakePublish();
    update(fields);
  });
})();
