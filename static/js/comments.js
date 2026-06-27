/**
 * SEOMONEY native comments — Google-authenticated, moderated, AdSense-safe.
 *
 * Replaces Giscus (GitHub-only). Talks to the VIPZone API:
 *   GET  {API}/comments?path=...   → approved comments (public)
 *   POST {API}/comments            → submit (requires login)
 *   GET  {API}/auth/me             → session role (admin | commenter | anonymous)
 *   {API}/auth/comment/start       → Google login for commenting
 *   {API}/admin/comments...        → moderation (admin only)
 *
 * Security notes:
 *   - All user text is rendered with textContent (never innerHTML) → no XSS.
 *   - A dedicated session key (seomoney-comment-sid) keeps commenter sessions
 *     separate from the CMS editor session, but an existing admin CMS session is
 *     reused so admins don't re-login. Role boundaries are enforced server-side.
 */
(function () {
  "use strict";

  var root = document.querySelector("[data-comments-root]");
  if (!root) return;

  // Single init guard — a duplicate include must not double-wire listeners.
  if (root.getAttribute("data-comments-init") === "1") return;
  root.setAttribute("data-comments-init", "1");

  var API = (root.getAttribute("data-comments-api") || "").replace(/\/$/, "");
  var PATH = root.getAttribute("data-comments-path") || location.pathname;
  var MAXLEN = parseInt(root.getAttribute("data-comments-maxlength"), 10) || 1500;
  var AUTH_TIMEOUT_MS = 7000; // cold Render dynos: never spin the loader forever.

  // Dedicated comment session; fall back to the shared CMS session for admins.
  var COMMENT_SID_KEY = "seomoney-comment-sid";
  var CMS_SID_KEY = "zola-cms-session-id";

  var els = {
    countLabel: root.querySelector("[data-comments-count-label]"),
    list: root.querySelector("[data-comments-list]"),
    empty: root.querySelector("[data-comments-empty]"),
    loading: root.querySelector("[data-comments-loading]"),
    guest: root.querySelector("[data-comments-guest]"),
    loginBtn: root.querySelector("[data-comments-login]"),
    error: root.querySelector("[data-comments-error]"),
    errorText: root.querySelector("[data-comments-error-text]"),
    retryBtn: root.querySelector("[data-comments-retry]"),
    form: root.querySelector("[data-comments-form]"),
    input: root.querySelector("[data-comments-input]"),
    submit: root.querySelector("[data-comments-submit]"),
    counter: root.querySelector("[data-comments-counter]"),
    notice: root.querySelector("[data-comments-notice]"),
    meAvatar: root.querySelector("[data-comments-me-avatar]"),
    meName: root.querySelector("[data-comments-me-name]"),
    adminBadge: root.querySelector("[data-comments-admin-badge]"),
    logout: root.querySelector("[data-comments-logout]"),
    mod: root.querySelector("[data-comments-mod]"),
    modToggle: root.querySelector("[data-comments-mod-toggle]"),
    modBody: root.querySelector("[data-comments-mod-body]"),
    modList: root.querySelector("[data-comments-mod-list]"),
  };

  var me = null; // {comment_role, name, avatar, ...} or null = anonymous
  var mePromise = null; // single-flight guard for /auth/me

  // Auth state machine: idle/guest (no spinner) → checking (spinner) →
  // authenticated | guest | error. Never leaves the spinner running once a
  // request resolves or times out (auth-vaccine A1).
  var AUTH_STATE = {
    CHECKING: "checking",
    AUTHENTICATED: "authenticated",
    GUEST: "guest",
    ERROR: "error",
  };

  // ---------- session helpers ----------
  function getSid() {
    try {
      return (
        sessionStorage.getItem(COMMENT_SID_KEY) ||
        sessionStorage.getItem(CMS_SID_KEY) ||
        ""
      );
    } catch (e) {
      return "";
    }
  }
  function setSid(sid) {
    try {
      sessionStorage.setItem(COMMENT_SID_KEY, sid);
    } catch (e) {}
  }
  function clearSid() {
    try {
      sessionStorage.removeItem(COMMENT_SID_KEY);
    } catch (e) {}
  }
  // Read a #sid=... handed back by the Google comment-login redirect.
  // Also scroll to #comments if present (after login).
  function consumeHashSid() {
    if (!location.hash) return;
    var m = location.hash.match(/(?:^|[#&])sid=([A-Za-z0-9_\-]+)/);
    if (!m) return;
    setSid(m[1]);
    // Check if fragment contains 'comments' (from backend redirect: #sid=...&comments).
    var hasComments = /[#&]comments(?:[#&]|$)/.test(location.hash);
    // Clean URL: drop the OAuth hint params, keep the rest of the query, and add
    // back the #comments anchor if present (auth-vaccine A1 — never leave
    // auth=success lingering or it looks like the flow re-ran).
    var params = new URLSearchParams(location.search);
    params.delete("auth");
    params.delete("auth_error");
    var qs = params.toString();
    var clean = location.pathname + (qs ? "?" + qs : "");
    if (hasComments) {
      clean += "#comments";
    }
    try {
      history.replaceState(null, "", clean);
    } catch (e) {}
    // Scroll smoothly to #comments if anchor exists.
    if (hasComments) {
      scrollToComments();
    }
  }

  // Smooth scroll to comment section, accounting for sticky navbar offset.
  function scrollToComments() {
    if (!root) return;
    try {
      var offset = 60; // Default navbar height; adjust if changed in CSS.
      var top = root.getBoundingClientRect().top + window.scrollY - offset;
      window.scrollTo({ top: top, behavior: "smooth" });
    } catch (e) {}
  }

  // ---------- small DOM helpers ----------
  function show(el) {
    if (el) el.hidden = false;
  }
  function hide(el) {
    if (el) el.hidden = true;
  }
  function fmtDate(iso) {
    if (!iso) return "";
    try {
      return new Date(iso).toLocaleString("vi-VN", {
        timeZone: "Asia/Ho_Chi_Minh",
        hour: "2-digit",
        minute: "2-digit",
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
      });
    } catch (e) {
      return iso;
    }
  }
  function initials(name) {
    var s = (name || "?").trim();
    return s ? s.charAt(0).toUpperCase() : "?";
  }

  function buildComment(c, opts) {
    opts = opts || {};
    var li = document.createElement("li");
    li.className = "comments__item";

    var av = document.createElement("div");
    av.className = "comments__item-avatar";
    if (c.author_avatar) {
      var img = document.createElement("img");
      img.src = c.author_avatar;
      img.alt = "";
      img.width = 40;
      img.height = 40;
      img.loading = "lazy";
      img.referrerPolicy = "no-referrer";
      av.appendChild(img);
    } else {
      av.textContent = initials(c.author_name);
    }

    var main = document.createElement("div");
    main.className = "comments__item-main";

    var meta = document.createElement("div");
    meta.className = "comments__item-meta";
    var nm = document.createElement("span");
    nm.className = "comments__item-name";
    nm.textContent = c.author_name || "Người dùng";
    var dt = document.createElement("time");
    dt.className = "comments__item-date";
    dt.textContent = fmtDate(c.created_at);
    meta.appendChild(nm);
    meta.appendChild(dt);
    if (opts.statusBadge && c.status) {
      var st = document.createElement("span");
      st.className = "comments__item-status comments__item-status--" + c.status;
      st.textContent = c.status;
      meta.appendChild(st);
    }

    var body = document.createElement("p");
    body.className = "comments__item-body";
    body.textContent = c.body || ""; // textContent → safe

    main.appendChild(meta);
    main.appendChild(body);

    if (opts.modActions) {
      main.appendChild(buildModActions(c));
    }

    li.appendChild(av);
    li.appendChild(main);
    return li;
  }

  // ---------- public list ----------
  function loadComments() {
    return fetch(API + "/comments?path=" + encodeURIComponent(PATH), {
      headers: { Accept: "application/json" },
      cache: "no-store",
    })
      .then(function (r) {
        return r.ok ? r.json() : { comments: [], count: 0 };
      })
      .then(function (data) {
        renderList(data.comments || []);
      })
      .catch(function () {
        renderList([]);
      });
  }

  function renderList(comments) {
    els.list.textContent = "";
    if (!comments.length) {
      show(els.empty);
      els.countLabel.textContent = "Chưa có bình luận";
      return;
    }
    hide(els.empty);
    var frag = document.createDocumentFragment();
    comments.forEach(function (c) {
      frag.appendChild(buildComment(c));
    });
    els.list.appendChild(frag);
    els.countLabel.textContent =
      comments.length + (comments.length === 1 ? " bình luận" : " bình luận");
  }

  // ---------- auth / form state ----------
  // Verify the session: single-flight + AbortController timeout. Resolves to
  // { ok, user, error } and NEVER hangs (a cold backend → error, not a stuck
  // spinner). Returns immediately as anonymous when there is no sid.
  function loadMe() {
    if (mePromise) return mePromise;
    var sid = getSid();
    if (!sid) {
      me = null;
      return Promise.resolve({ ok: true, user: null });
    }
    var controller =
      typeof AbortController !== "undefined" ? new AbortController() : null;
    var timer = setTimeout(function () {
      if (controller) controller.abort();
    }, AUTH_TIMEOUT_MS);
    var opts = {
      headers: { Authorization: "Bearer " + sid },
      credentials: "omit",
      cache: "no-store",
    };
    if (controller) opts.signal = controller.signal;
    mePromise = fetch(API + "/auth/me", opts)
      .then(function (r) {
        if (r.status === 401) {
          clearSid();
          me = null;
          return { ok: true, user: null };
        }
        if (!r.ok) return { ok: false, user: null, error: true };
        return r.json().then(function (data) {
          me = data;
          return { ok: true, user: data };
        });
      })
      .catch(function () {
        me = null;
        return { ok: false, user: null, error: true };
      })
      .then(function (res) {
        clearTimeout(timer);
        mePromise = null; // allow an explicit retry from the error view
        return res;
      });
    return mePromise;
  }

  // Toggle exactly one auth-zone view. The spinner only shows for CHECKING.
  function setAuthState(state) {
    hide(els.loading);
    hide(els.guest);
    hide(els.form);
    hide(els.error);
    if (state === AUTH_STATE.CHECKING) {
      show(els.loading);
      hide(els.mod);
      return;
    }
    if (state === AUTH_STATE.ERROR) {
      show(els.error);
      hide(els.mod);
      return;
    }
    if (state === AUTH_STATE.AUTHENTICATED && me) {
      show(els.form);
      els.meName.textContent = me.name || me.email || "Bạn";
      if (me.avatar || me.avatar_url) {
        els.meAvatar.src = me.avatar || me.avatar_url;
        show(els.meAvatar);
      }
      // Comment login is comment-only by default; admin moderation only for
      // accounts the backend marks as admin (whitelist enforced server-side).
      var isAdmin =
        me.comment_role === "admin" || me.account_type === "admin" || me.is_admin;
      if (isAdmin) {
        show(els.adminBadge);
        show(els.mod);
      } else {
        hide(els.adminBadge);
        hide(els.mod);
      }
      updateCounter();
      return;
    }
    // GUEST (default): calm login CTA, no spinner.
    show(els.guest);
    hide(els.mod);
  }

  // Render the resolved auth state from `me` (used after submit/logout).
  function renderAuth() {
    setAuthState(me ? AUTH_STATE.AUTHENTICATED : AUTH_STATE.GUEST);
  }

  // Run one auth check with a visible (but finite) spinner only while a sid is
  // actually being verified. No sid → straight to guest, no spinner flash.
  function runAuthCheck() {
    if (!getSid()) {
      me = null;
      setAuthState(AUTH_STATE.GUEST);
      return;
    }
    setAuthState(AUTH_STATE.CHECKING);
    loadMe().then(function (res) {
      if (res && res.user) {
        setAuthState(AUTH_STATE.AUTHENTICATED);
      } else if (res && res.error) {
        setAuthState(AUTH_STATE.ERROR);
      } else {
        setAuthState(AUTH_STATE.GUEST);
      }
    });
  }

  function loginUrl() {
    var returnTo = PATH + "#comments";
    return (
      API +
      "/auth/comment/start?return_to=" +
      encodeURIComponent(returnTo)
    );
  }

  function updateCounter() {
    var len = (els.input.value || "").length;
    els.counter.textContent = len + " / " + MAXLEN;
    els.counter.classList.toggle("comments__counter--over", len > MAXLEN);
  }

  function setNotice(msg, kind) {
    if (!msg) {
      hide(els.notice);
      return;
    }
    els.notice.textContent = msg;
    els.notice.className =
      "comments__notice comments__notice--" + (kind || "info");
    show(els.notice);
  }

  function submitComment(e) {
    e.preventDefault();
    var text = (els.input.value || "").trim();
    if (!text) {
      setNotice("Vui lòng nhập nội dung bình luận.", "error");
      return;
    }
    if (text.length > MAXLEN) {
      setNotice("Bình luận quá dài (tối đa " + MAXLEN + " ký tự).", "error");
      return;
    }
    els.submit.disabled = true;
    setNotice("Đang gửi…", "info");
    fetch(API + "/comments", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer " + getSid(),
      },
      credentials: "omit",
      body: JSON.stringify({ path: PATH, body: text }),
    })
      .then(function (r) {
        return r.json().then(function (j) {
          return { ok: r.ok, status: r.status, data: j };
        });
      })
      .then(function (res) {
        els.submit.disabled = false;
        if (res.status === 401) {
          clearSid();
          me = null;
          renderAuth();
          setNotice("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.", "error");
          return;
        }
        if (res.status === 429) {
          setNotice("Bạn bình luận quá nhanh. Vui lòng thử lại sau giây lát.", "error");
          return;
        }
        if (!res.ok) {
          setNotice("Không gửi được bình luận. Vui lòng thử lại.", "error");
          return;
        }
        els.input.value = "";
        updateCounter();
        if (res.data.pending) {
          setNotice("Bình luận của bạn đang chờ duyệt.", "success");
        } else {
          setNotice("Đã đăng bình luận.", "success");
          loadComments();
        }
      })
      .catch(function () {
        els.submit.disabled = false;
        setNotice("Lỗi mạng. Vui lòng thử lại.", "error");
      });
  }

  function logout() {
    var sid = getSid();
    clearSid();
    try {
      sessionStorage.removeItem(CMS_SID_KEY);
    } catch (e) {}
    me = null;
    if (sid) {
      fetch(API + "/auth/logout", {
        method: "POST",
        headers: { Authorization: "Bearer " + sid },
        credentials: "omit",
      }).catch(function () {});
    }
    renderAuth();
  }

  // ---------- admin moderation ----------
  function buildModActions(c) {
    var wrap = document.createElement("div");
    wrap.className = "comments__mod-actions";
    function btn(label, cls, fn) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "comments__mod-btn comments__mod-btn--" + cls;
      b.textContent = label;
      b.addEventListener("click", function () {
        b.disabled = true;
        fn().finally(function () {
          b.disabled = false;
        });
      });
      return b;
    }
    if (c.status !== "approved") {
      wrap.appendChild(
        btn("Duyệt", "approve", function () {
          return modAction(c.id, "approve");
        })
      );
    }
    if (c.status !== "hidden") {
      wrap.appendChild(
        btn("Ẩn", "hide", function () {
          return modAction(c.id, "hide");
        })
      );
    }
    wrap.appendChild(
      btn("Xoá", "delete", function () {
        return modDelete(c.id);
      })
    );
    return wrap;
  }

  function modAction(id, action) {
    return fetch(API + "/admin/comments/" + encodeURIComponent(id) + "/" + action, {
      method: "POST",
      headers: { Authorization: "Bearer " + getSid() },
      credentials: "omit",
    })
      .then(function () {
        loadModList();
        loadComments();
      })
      .catch(function () {});
  }
  function modDelete(id) {
    return fetch(API + "/admin/comments/" + encodeURIComponent(id), {
      method: "DELETE",
      headers: { Authorization: "Bearer " + getSid() },
      credentials: "omit",
    })
      .then(function () {
        loadModList();
        loadComments();
      })
      .catch(function () {});
  }

  function loadModList() {
    return fetch(API + "/admin/comments", {
      headers: { Authorization: "Bearer " + getSid() },
      credentials: "omit",
      cache: "no-store",
    })
      .then(function (r) {
        return r.ok ? r.json() : { comments: [] };
      })
      .then(function (data) {
        var rows = (data.comments || []).filter(function (c) {
          return c.page_path === PATH;
        });
        els.modList.textContent = "";
        if (!rows.length) {
          var li = document.createElement("li");
          li.className = "comments__mod-empty";
          li.textContent = "Không có bình luận nào cho trang này.";
          els.modList.appendChild(li);
          return;
        }
        var frag = document.createDocumentFragment();
        rows.forEach(function (c) {
          frag.appendChild(
            buildComment(c, { statusBadge: true, modActions: true })
          );
        });
        els.modList.appendChild(frag);
      })
      .catch(function () {});
  }

  // ---------- wire up ----------
  function init() {
    consumeHashSid();
    els.input.setAttribute("maxlength", String(MAXLEN));
    els.loginBtn.setAttribute("href", loginUrl());
    els.loginBtn.addEventListener("click", function (e) {
      e.preventDefault();
      window.location.href = loginUrl();
    });
    els.form.addEventListener("submit", submitComment);
    els.input.addEventListener("input", function () {
      updateCounter();
      setNotice("");
    });
    els.logout.addEventListener("click", logout);
    if (els.retryBtn) {
      els.retryBtn.addEventListener("click", function (e) {
        e.preventDefault();
        runAuthCheck();
      });
    }
    els.modToggle.addEventListener("click", function () {
      var open = els.modBody.hidden;
      els.modBody.hidden = !open;
      if (open) loadModList();
    });

    loadComments();
    runAuthCheck();

    // Scroll to #comments if anchor is in URL (e.g., direct navigation or bookmark).
    if (location.hash.indexOf("#comments") > -1) {
      setTimeout(function () {
        scrollToComments();
      }, 100); // Defer slightly to allow page layout to settle.
    }
  }

  init();
})();
