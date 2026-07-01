(function (global) {
  "use strict";

  var SESSION_KEY = "zola-cms-session-id";

  var AUTH_API = (function () {
    var m1 = document.querySelector('meta[name="zola-cms-auth-api"]');
    if (m1 && m1.getAttribute("content")) return m1.getAttribute("content").replace(/\/+$/, "");
    var m2 = document.querySelector('meta[name="zola-visitor-api"]');
    if (m2 && m2.getAttribute("content")) return m2.getAttribute("content").replace(/\/+$/, "");
    return "https://blog-vipzone-api.onrender.com";
  })();

  var currentUser = null;
  var appReady = false;
  var MOUNTED = false;

  function el(id) { return document.getElementById(id); }
  function qs(s, p) { return (p || document).querySelector(s); }
  function qsa(s, p) { return (p || document).querySelectorAll(s); }

  function getSid() {
    try { return sessionStorage.getItem(SESSION_KEY) || ""; } catch (e) { return ""; }
  }
  function setSid(sid) {
    try { sessionStorage.setItem(SESSION_KEY, sid); } catch (e) {}
  }
  function clearSid() {
    try { sessionStorage.removeItem(SESSION_KEY); } catch (e) {}
  }

  function consumeUrlHashSid() {
    if (!location.hash) return;
    var m = location.hash.match(/(?:^|[#&])sid=([A-Za-z0-9_-]+)/);
    if (!m) return;
    setSid(m[1]);
    history.replaceState(null, "", location.pathname + location.search);
  }

  function showView(name) {
    qsa("[data-ih-view]").forEach(function (v) {
      v.hidden = v.getAttribute("data-ih-view") !== name;
    });
  }

  function updateUserBar(profile) {
    var bar = qs("[data-ih-user-bar]");
    if (!profile) {
      bar && (bar.hidden = true);
      return;
    }
    if (!bar) return;
    qs("[data-ih-user-avatar]", bar).src = profile.avatar_url || "";
    qs("[data-ih-user-name]", bar).textContent = profile.name || profile.username || profile.email || "Admin";
    qs("[data-ih-user-email]", bar).textContent = profile.email || "";
    bar.hidden = false;
  }

  function fetchMe() {
    var sid = getSid();
    if (!sid) return Promise.reject("no_sid");
    return fetch(AUTH_API + "/auth/me", {
      headers: { Authorization: "Bearer " + sid },
      credentials: "include",
    }).then(function (r) {
      if (!r.ok) throw new Error("auth_failed");
      return r.json();
    });
  }

  function login() {
    var returnTo = encodeURIComponent(location.pathname + location.search);
    location.href = AUTH_API + "/auth/login?return_to=" + returnTo;
  }

  function logout() {
    clearSid();
    currentUser = null;
    updateUserBar(null);
    showView("login");
  }

  function showError(msg) {
    var el = qs("[data-ih-login-error]");
    if (el) { el.textContent = msg; el.hidden = false; }
  }
  function hideError() {
    var el = qs("[data-ih-login-error]");
    if (el) el.hidden = true;
  }

  function initAuth() {
    consumeUrlHashSid();

    var params = new URLSearchParams(location.search);
    var authErr = params.get("auth_error");
    if (authErr) {
      var msgs = {
        access_denied: "Truy c\u1eadp b\u1ecb t\u1eeb ch\u1ed1i: t\u00e0i kho\u1ea3n GitHub kh\u00f4ng trong white-list admin.",
        invalid_state: "Phi\u00ean \u0111\u0103ng nh\u1eadp h\u1ebft h\u1ea1n. Vui l\u00f2ng th\u1eed l\u1ea1i.",
        token_exchange_failed: "L\u1ed7i x\u00e1c th\u1ef1c GitHub. Th\u1eed l\u1ea1i sau.",
      };
      showError(msgs[authErr] || authErr);
      history.replaceState(null, "", location.pathname);
    }

    if (location.search.includes("auth=success")) {
      history.replaceState(null, "", location.pathname);
    }

    var sid = getSid();
    if (!sid) {
      showView("login");
      return;
    }

    fetchMe()
      .then(function (profile) {
        currentUser = profile;
        updateUserBar(profile);
        hideError();
        showView("dashboard");
        if (!MOUNTED) {
          mountApp();
          MOUNTED = true;
        }
        loadHistory();
      })
      .catch(function () {
        clearSid();
        showView("login");
      });
  }

  /* ---- Login button ---- */
  qs("[data-ih-action='github-login']").addEventListener("click", login);

  /* ---- Logout button ---- */
  global.document.addEventListener("click", function (e) {
    var btn = e.target.closest("[data-ih-action='logout']");
    if (btn) logout();
  });

  /* ======== APP LOGIC ======== */

  function mountApp() {
    var form = el("ih-form");
    form.addEventListener("submit", onSubmit);
  }

  function onSubmit(e) {
    e.preventDefault();

    var title = el("ih-title").value.trim();
    var description = el("ih-description").value.trim();
    var content = el("ih-content").value.trim();

    if (!title) {
      el("ih-title").focus();
      return;
    }

    var submitBtn = el("ih-submit");
    submitBtn.disabled = true;
    submitBtn.textContent = "\u25B6 \u0110ang t\u1ea1o\u2026";

    var progress = el("ih-progress");
    progress.hidden = false;
    el("ih-progress-bar").style.width = "20%";
    el("ih-progress-text").textContent = "\u0110ang g\u1eedi d\u1eef li\u1ec7u\u2026";

    var sid = getSid();
    fetch(AUTH_API + "/api/infographic-hoa/generate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer " + sid,
      },
      body: JSON.stringify({ title: title, description: description, content: content }),
      credentials: "include",
    })
      .then(function (r) {
        if (!r.ok) return r.json().then(function (d) { throw new Error(d.detail || "generate_failed"); });
        return r.json();
      })
      .then(function (data) {
        el("ih-progress-bar").style.width = "100%";
        el("ih-progress-text").textContent = "Ho\u00e0n t\u1ea5t!";
        renderGallery(data.images);
        loadHistory();
      })
      .catch(function (err) {
        el("ih-progress-text").textContent = "L\u1ed7i: " + err.message;
        el("ih-progress-bar").style.width = "100%";
        el("ih-progress-bar").style.background = "var(--c-danger, #e74c3c)";
      })
      .finally(function () {
        submitBtn.disabled = false;
        submitBtn.textContent = "\u25C6 T\u1ea1o infographic";
        setTimeout(function () {
          progress.hidden = true;
          el("ih-progress-bar").style.width = "0%";
          el("ih-progress-bar").style.background = "";
        }, 3000);
      });
  }

  function renderGallery(images) {
    var panel = el("ih-result-panel");
    panel.hidden = false;

    var gallery = el("ih-gallery");
    gallery.innerHTML = "";

    var group = document.createElement("div");
    group.className = "ih-gallery__grid";

    var typeLabels = {
      cover: "Cover",
      quote: "Trich d\u1eabn",
      insight: "Ph\u00e2n t\u00edch",
      summary: "T\u1ed5ng k\u1ebft",
      banner: "Banner",
    };

    images.forEach(function (img) {
      var card = document.createElement("div");
      card.className = "ih-gallery__card";

      card.innerHTML =
        '<div class="ih-gallery__preview">' +
          '<img src="' + (img.webp_url || img.svg_url) + '" alt="' + escAttr(img.alt_text) + '" loading="lazy" decoding="async" width="400" height="300">' +
        "</div>" +
        '<div class="ih-gallery__meta">' +
          '<span class="ih-gallery__type">' + (typeLabels[img.type] || img.type) + "</span>" +
          '<span class="ih-gallery__palette">' + escHtml(img.palette) + "</span>" +
        "</div>" +
        '<div class="ih-gallery__actions">' +
          (img.cms_media_id
            ? '<a href="' + AUTH_API + '/cms-v5/#!/media/' + img.cms_media_id + '" class="ih-btn ih-btn--sm ih-btn--outline" target="_blank">Xem trong CMS</a>'
            : "") +
          '<a href="' + img.svg_url + '" class="ih-btn ih-btn--sm ih-btn--ghost" download>SVG</a>' +
          '<a href="' + img.webp_url + '" class="ih-btn ih-btn--sm ih-btn--ghost" download>WebP</a>' +
        "</div>";

      group.appendChild(card);
    });

    gallery.appendChild(group);
  }

  function loadHistory() {
    var sid = getSid();
    var container = el("ih-history");
    if (!container) return;

    fetch(AUTH_API + "/api/infographic-hoa/images", {
      headers: { Authorization: "Bearer " + sid },
      credentials: "include",
    })
      .then(function (r) {
        if (!r.ok) return;
        return r.json();
      })
      .then(function (data) {
        if (!data || !data.generations || data.generations.length === 0) {
          container.innerHTML = '<p class="ih-history__empty">Chưa có lần tạo infographic nào.</p>';
          return;
        }

        var html = "";
        data.generations.slice(0, 10).forEach(function (gen) {
          html += '<div class="ih-history__gen">' +
            '<div class="ih-history__gen-header">' +
              '<strong>' + escHtml(gen.title || "(không tiêu đề)") + "</strong> " +
              '<span class="ih-history__gen-meta">' + gen.images.length + " \u1EA3nh \u00B7 " + formatDate(gen.created_at) + "</span>" +
            "</div>" +
            '<div class="ih-history__gen-thumbs">';
          gen.images.forEach(function (img) {
            html += '<a href="' + (img.webp_url || img.svg_url) + '" target="_blank" title="' + escAttr(img.alt_text) + '">' +
              '<img src="' + (img.webp_url || img.svg_url) + '" alt="' + escAttr(img.alt_text) + '" loading="lazy" decoding="async" width="120" height="90">' +
              "</a>";
          });
          html += "</div></div>";
        });
        container.innerHTML = html;
      })
      .catch(function () {});
  }

  function formatDate(iso) {
    if (!iso) return "";
    try {
      var d = new Date(iso);
      return d.toLocaleDateString("vi-VN", {
        day: "2-digit", month: "2-digit", year: "numeric",
        hour: "2-digit", minute: "2-digit",
        timeZone: "Asia/Ho_Chi_Minh",
      });
    } catch (e) { return iso; }
  }

  function escHtml(s) {
    if (!s) return "";
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  function escAttr(s) {
    return escHtml(s).replace(/"/g, "&quot;");
  }

  /* ---- Init ---- */
  document.addEventListener("DOMContentLoaded", initAuth);
})(window);
