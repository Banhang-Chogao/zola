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
    try { return sessionStorage.getItem(SESSION_KEY) || ""; } catch (e) {}
    try { return localStorage.getItem(SESSION_KEY) || ""; } catch (e) {}
    return "";
  }

  function setSid(sid) {
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
    var sid = readHashSid();
    if (sid) setSid(sid);
    if (!location.search && !location.hash) return;
    var params = new URLSearchParams(location.search);
    params.delete("auth");
    params.delete("auth_error");
    if (sid) {
      try {
        history.replaceState(null, "", location.pathname + (params.toString() ? "?" + params.toString() : ""));
      } catch (e) {}
    }
  }

  function login() {
    if (!AUTH_API) return;
    location.href = AUTH_API + "/auth/login?return_to=" + encodeURIComponent(location.pathname);
  }

  async function fetchMe() {
    var sid = getSid();
    if (!sid || !AUTH_API) return null;
    try {
      var controller = new AbortController();
      var timer = setTimeout(function () { controller.abort(); }, 10000);
      var res = await fetch(AUTH_API + "/auth/me", {
        method: "GET",
        headers: { Authorization: "Bearer " + sid },
        credentials: "omit",
        cache: "no-store",
        signal: controller.signal,
      });
      clearTimeout(timer);
      if (res.status === 401) {
        clearSid();
        return null;
      }
      if (!res.ok) return null;
      return await res.json();
    } catch (e) {
      return null;
    }
  }

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
    consumeAuthParams();
    bindTabs();
    bindComposer();
    if (loginButton) loginButton.addEventListener("click", login);

    var me = await fetchMe();
    if (!me || !(me.is_admin || me.is_super)) {
      showGate("Đăng nhập GitHub bằng tài khoản admin để mở CMS-V2.");
      return;
    }

    showShell();
  }

  boot();
})();
