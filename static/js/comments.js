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

  var API = (root.getAttribute("data-comments-api") || "").replace(/\/$/, "");
  var PATH = root.getAttribute("data-comments-path") || location.pathname;
  var MAXLEN = parseInt(root.getAttribute("data-comments-maxlength"), 10) || 1500;

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
  function consumeHashSid() {
    if (!location.hash) return;
    var m = location.hash.match(/(?:^|[#&])sid=([A-Za-z0-9_\-]+)/);
    if (!m) return;
    setSid(m[1]);
    // Preserve #comments anchor if present, otherwise clean the hash.
    var clean = location.pathname + location.search;
    if (location.hash.indexOf("#comments") !== -1) {
      clean += "#comments";
    }
    try {
      history.replaceState(null, "", clean);
    } catch (e) {}
  }

  // Auto-scroll to comment section if user was redirected back after login.
  // Detects either:
  //   - Query param ?from=comment (set by loginUrl when user starts comment login)
  //   - Anchor #comments (preserved from the redirect or from user navigation)
  function scrollToCommentIfNeeded() {
    var shouldScroll = false;

    // Check for ?from=comment query param (indicates post-login redirect)
    if (location.search.indexOf("from=comment") !== -1) {
      shouldScroll = true;
    }

    // Check for #comments anchor
    if (location.hash === "#comments") {
      shouldScroll = true;
    }

    if (!shouldScroll || !root) return;

    // Schedule scroll after DOM settles and images start loading.
    // Use a small timeout to allow layout to stabilize.
    setTimeout(function () {
      try {
        root.scrollIntoView({ behavior: "smooth", block: "start" });
      } catch (e) {
        // Fallback for browsers without smooth scrolling support.
        root.scrollIntoView();
      }
    }, 100);
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
  function loadMe() {
    var sid = getSid();
    if (!sid) {
      me = null;
      return Promise.resolve(null);
    }
    return fetch(API + "/auth/me", {
      headers: { Authorization: "Bearer " + sid },
      credentials: "omit",
      cache: "no-store",
    })
      .then(function (r) {
        if (r.status === 401) {
          clearSid();
          return null;
        }
        return r.ok ? r.json() : null;
      })
      .then(function (data) {
        me = data;
        return data;
      })
      .catch(function () {
        me = null;
        return null;
      });
  }

  function renderAuth() {
    hide(els.loading);
    if (!me) {
      // Anonymous → login CTA.
      hide(els.form);
      show(els.guest);
      hide(els.mod);
      return;
    }
    // Logged in.
    hide(els.guest);
    show(els.form);
    els.meName.textContent = me.name || me.email || "Bạn";
    if (me.avatar || me.avatar_url) {
      els.meAvatar.src = me.avatar || me.avatar_url;
      show(els.meAvatar);
    }
    var isAdmin = me.comment_role === "admin" || me.account_type === "admin" || me.is_admin;
    if (isAdmin) {
      show(els.adminBadge);
      show(els.mod);
    } else {
      hide(els.adminBadge);
      hide(els.mod);
    }
    updateCounter();
  }

  function loginUrl() {
    // Include ?from=comment so after OAuth callback, the frontend knows to
    // scroll back to the comment section. Backend's normalize_return_to will
    // preserve the query param in the return URL.
    var returnPath = PATH;
    if (PATH.indexOf("?") === -1) {
      returnPath += "?from=comment";
    } else {
      returnPath += "&from=comment";
    }
    // Add anchor to help identify comment section on page load.
    returnPath += "#comments";
    return (
      API +
      "/auth/comment/start?return_to=" +
      encodeURIComponent(returnPath)
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
    scrollToCommentIfNeeded();
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
    els.modToggle.addEventListener("click", function () {
      var open = els.modBody.hidden;
      els.modBody.hidden = !open;
      if (open) loadModList();
    });

    loadComments();
    loadMe().then(renderAuth);
  }

  init();
})();
