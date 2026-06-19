(function () {
  "use strict";

  var VZ = window.VIPZone;
  if (!VZ) return;

  var AUTH_API = (function () {
    var m = document.querySelector('meta[name="vipzone-auth-api"]');
    if (m && m.getAttribute("content")) return m.getAttribute("content").replace(/\/$/, "");
    m = document.querySelector('meta[name="zola-vipzone-api"]');
    return m && m.getAttribute("content") ? m.getAttribute("content").replace(/\/$/, "") : "https://blog-vipzone-api.onrender.com";
  })();

  var API = VZ.API || AUTH_API;
  var CMS_KEY = "zola-cms-session-id";
  var GUEST_USER = { role: "guest", username: "", email: "", name: "Khách", is_super: false, is_admin: false };
  var pickerCatalog = null;
  var pickerFilter = "";
  var currentUser = null;

  function $(s) { return document.querySelector(s); }

  function useApi() { return !!API; }

  function authHeaders() {
    var h = { "Content-Type": "application/json" };
    var sid = getSid();
    if (sid) h.Authorization = "Bearer " + sid;
    return h;
  }

  function getSid() {
    try {
      var sid = sessionStorage.getItem(CMS_KEY) || localStorage.getItem(CMS_KEY) || "";
      if (sid && !sessionStorage.getItem(CMS_KEY)) {
        try { sessionStorage.setItem(CMS_KEY, sid); } catch (e) {}
      }
      return sid;
    } catch (e) { return ""; }
  }

  function setSid(sid) {
    try { sessionStorage.setItem(CMS_KEY, sid); } catch (e) {}
    try { localStorage.setItem(CMS_KEY, sid); } catch (e) {}
  }

  function clearSid() {
    try { sessionStorage.removeItem(CMS_KEY); } catch (e) {}
    try { localStorage.removeItem(CMS_KEY); } catch (e) {}
  }

  function consumeHashSid() {
    if (!location.hash) return;
    var m = location.hash.match(/(?:^|[#&])sid=([A-Za-z0-9_-]+)/);
    if (!m) return;
    setSid(m[1]);
    history.replaceState(null, "", location.pathname + location.search);
  }

  function consumeAuthQuery() {
    var params = new URLSearchParams(location.search);
    if (params.get("auth") === "success") {
      params.delete("auth");
      var qs = params.toString();
      history.replaceState(null, "", location.pathname + (qs ? "?" + qs : ""));
    }
    var err = params.get("auth_error");
    if (!err) return null;
    params.delete("auth_error");
    var qs2 = params.toString();
    history.replaceState(null, "", location.pathname + (qs2 ? "?" + qs2 : ""));
    return err;
  }

  function showView(name) {
    document.querySelectorAll("[data-vz-view]").forEach(function (el) {
      el.hidden = el.getAttribute("data-vz-view") !== name;
    });
  }

  function formatDt(iso) {
    if (!iso) return "—";
    try {
      return new Date(iso).toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh", day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
    } catch (e) { return iso; }
  }

  function showTab(name) {
    document.querySelectorAll("[data-vz-tab]").forEach(function (b) {
      b.classList.toggle("vipzone__tab--active", b.getAttribute("data-vz-tab") === name);
    });
    document.querySelectorAll("[data-vz-panel]").forEach(function (p) {
      p.hidden = p.getAttribute("data-vz-panel") !== name;
    });
  }

  // Render from the API's permission object — single source of truth (roles.py).
  // Legacy role/flag fallback kept ONLY for a backend lagging behind `main` (V16).
  function roleIsAdmin(user) {
    if (!user || user.role === "guest") return false;
    if (user.permissions) return !!user.permissions.can_admin;
    return user.role === "superadmin" || user.role === "supervip" ||
      !!user.is_super || !!user.is_superadmin || !!user.is_admin;
  }

  function isAuthenticated(user) {
    return !!(user && user.role && user.role !== "guest");
  }

  function applyRoleUI(user, canAdmin) {
    var root = document.querySelector('[data-vz-page="admin"]');
    if (root) root.classList.toggle("vipzone--readonly", !canAdmin);

    var loginSection = $('[data-vz-view="login"]');
    if (loginSection) loginSection.hidden = isAuthenticated(user) || canAdmin;

    var bar = $("[data-vz-user-bar]");
    if (bar) {
      bar.hidden = !isAuthenticated(user);
      var nm = $("[data-vz-admin-name]");
      if (nm) {
        nm.textContent = (user && (user.username || user.email || user.name)) || "Khách";
        if (user && user.role && user.role !== "guest") {
          nm.textContent += " · " + user.role;
        }
      }
    }

    document.querySelectorAll(
      '[data-vz-action="create-code"], [data-vz-action="save-picker"], [data-vz-resolve], [data-vz-deactivate]'
    ).forEach(function (el) {
      if (el.matches("button, input, select")) el.disabled = !canAdmin;
    });

    document.querySelectorAll(".vipzone__picker-access").forEach(function (btn) {
      btn.disabled = !canAdmin;
      if (!canAdmin) btn.setAttribute("aria-disabled", "true");
    });

    var savePicker = $('[data-vz-action="save-picker"]');
    if (savePicker && !canAdmin) savePicker.title = "Cần quyền admin để lưu";
  }

  async function apiFetch(path, opts) {
    opts = opts || {};
    var res = await fetch(API + path, {
      method: opts.method || "GET",
      headers: Object.assign(authHeaders(), opts.headers || {}),
      body: opts.body ? JSON.stringify(opts.body) : undefined,
      credentials: "include",
      cache: "no-store",
    });
    var data = null;
    try { data = await res.json(); } catch (e) {}
    if (!res.ok) throw new Error((data && data.detail) || res.statusText);
    return data;
  }

  function updateStatsFromData(stats) {
    var elP = $("[data-vz-stat-pending]");
    var elA = $("[data-vz-stat-active]");
    var elR = $("[data-vz-stat-revenue]");
    if (elP) elP.textContent = String(stats.pending || 0);
    if (elA) elA.textContent = String(stats.active_vips != null ? stats.active_vips : stats.active || 0);
    if (elR) {
      var rev = stats.revenue_estimate != null ? stats.revenue_estimate : stats.revenue || 0;
      elR.textContent = rev.toLocaleString("vi-VN") + "đ";
    }
  }

  async function refreshStats() {
    if (!roleIsAdmin(currentUser)) return;
    if (useApi()) {
      try {
        var stats = await apiFetch("/api/vipzone/admin/stats");
        updateStatsFromData(stats);
        return;
      } catch (e) { VZ.toast(e.message || "Không tải stats.", "error"); }
    }
    var store = VZ.readStore();
    var pending = (store.payments || []).filter(function (p) { return p.status === "pending"; }).length;
    updateStatsFromData({ pending: pending, active: VZ.activeVipCount(), revenue: store.revenue || 0 });
  }

  function loadPaymentsLocal(store) {
    var tbody = $("[data-vz-payments-body]");
    if (!tbody) return;
    var rows = (store.payments || []).slice().reverse();
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="vipzone__empty">Không có yêu cầu.</td></tr>';
      return;
    }
    tbody.innerHTML = rows.map(function (r) {
      return '<tr data-pay-id="' + r.id + '"><td>' + r.email + '</td><td>' + r.plan +
        '</td><td>' + (r.note || r.payment_note || "—") + '</td><td>' + r.status +
        '</td><td><button type="button" class="vipzone__btn vipzone__btn--sm vipzone__btn--ghost" data-vz-resolve>Đã xử lý</button></td></tr>';
    }).join("");
    bindResolveButtons();
  }

  async function loadPayments() {
    if (!roleIsAdmin(currentUser)) return;
    if (useApi()) {
      try {
        var rows = await apiFetch("/api/vipzone/admin/requests");
        var tbody = $("[data-vz-payments-body]");
        if (!tbody) return;
        if (!rows.length) {
          tbody.innerHTML = '<tr><td colspan="5" class="vipzone__empty">Không có yêu cầu.</td></tr>';
          return;
        }
        tbody.innerHTML = rows.map(function (r) {
          var btn = r.status === "pending"
            ? '<button type="button" class="vipzone__btn vipzone__btn--sm vipzone__btn--ghost" data-vz-resolve>Đã xử lý</button>'
            : "";
          return '<tr data-pay-id="' + r.id + '"><td>' + r.email + '</td><td>' + r.plan +
            '</td><td>' + (r.payment_note || "—") + '</td><td>' + r.status + '</td><td>' + btn + '</td></tr>';
        }).join("");
        bindResolveButtons();
        return;
      } catch (e) { VZ.toast(e.message || "Không tải yêu cầu.", "error"); }
    }
    loadPaymentsLocal(VZ.readStore());
  }

  function bindResolveButtons() {
    var tbody = $("[data-vz-payments-body]");
    if (!tbody) return;
    tbody.querySelectorAll("[data-vz-resolve]").forEach(function (btn) {
      btn.addEventListener("click", async function () {
        if (!roleIsAdmin(currentUser)) return;
        var id = btn.closest("tr").getAttribute("data-pay-id");
        if (useApi()) {
          try {
            await apiFetch("/api/vipzone/admin/requests/" + encodeURIComponent(id) + "/resolve", { method: "POST" });
            await loadPayments();
            await refreshStats();
            VZ.toast("Đã đánh dấu xử lý.", "success");
          } catch (e) { VZ.toast(e.message || "Lỗi.", "error"); }
          return;
        }
        var s = VZ.readStore();
        (s.payments || []).forEach(function (p) {
          if (p.id === id) p.status = "resolved";
        });
        VZ.writeStore(s);
        loadPaymentsLocal(s);
        refreshStats();
        VZ.toast("Đã đánh dấu xử lý.", "success");
      });
    });
  }

  function loadCodesLocal(store) {
    var tbody = $("[data-vz-codes-body]");
    if (!tbody) return;
    var rows = (store.codes || []).slice().reverse();
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="vipzone__empty">Chưa có mã.</td></tr>';
      return;
    }
    tbody.innerHTML = rows.map(function (c) {
      return "<tr><td><code>" + c.code + "</code></td><td>" + c.plan + "</td><td>" +
        (c.email || "—") + "</td><td>" + (c.used ? "✓" : "—") + "</td><td>" + formatDt(c.created_at) + "</td></tr>";
    }).join("");
  }

  async function loadCodes() {
    if (!roleIsAdmin(currentUser)) return;
    if (useApi()) {
      try {
        var rows = await apiFetch("/api/vipzone/admin/codes");
        var tbody = $("[data-vz-codes-body]");
        if (!tbody) return;
        if (!rows.length) {
          tbody.innerHTML = '<tr><td colspan="5" class="vipzone__empty">Chưa có mã.</td></tr>';
          return;
        }
        tbody.innerHTML = rows.map(function (c) {
          return "<tr><td><code>" + (c.code || "••••") + "</code></td><td>" + c.plan + "</td><td>" +
            (c.email || "—") + "</td><td>" + (c.used ? "✓" : "—") + "</td><td>" + formatDt(c.created_at) + "</td></tr>";
        }).join("");
        return;
      } catch (e) { VZ.toast(e.message || "Không tải mã.", "error"); }
    }
    loadCodesLocal(VZ.readStore());
  }

  function loadUsersLocal(store) {
    var tbody = $("[data-vz-users-body]");
    if (!tbody) return;
    var rows = (store.vips || []).slice().reverse();
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="vipzone__empty">Chưa có VIP.</td></tr>';
      return;
    }
    tbody.innerHTML = rows.map(function (u, idx) {
      return '<tr data-vip-email="' + encodeURIComponent(u.email) + '"><td>' + u.email + '</td><td>' + u.plan +
        '</td><td>' + formatDt(u.expires_at) + '</td><td data-vz-user-cd="' + idx + '">—</td>' +
        '<td><button type="button" class="vipzone__btn vipzone__btn--sm vipzone__btn--ghost" data-vz-deactivate>Vô hiệu</button></td></tr>';
    }).join("");
    rows.forEach(function (u, idx) {
      var cd = document.querySelector('[data-vz-user-cd="' + idx + '"]');
      if (cd && u.expires_at) VZ.startCountdown(u.expires_at, cd);
    });
    bindDeactivateButtons();
  }

  async function loadUsers() {
    if (!roleIsAdmin(currentUser)) return;
    if (useApi()) {
      try {
        var rows = await apiFetch("/api/vipzone/admin/users");
        var tbody = $("[data-vz-users-body]");
        if (!tbody) return;
        if (!rows.length) {
          tbody.innerHTML = '<tr><td colspan="5" class="vipzone__empty">Chưa có VIP.</td></tr>';
          return;
        }
        tbody.innerHTML = rows.map(function (u, idx) {
          var inactive = !u.active;
          return '<tr data-vip-email="' + encodeURIComponent(u.email) + '"><td>' + u.email + '</td><td>' + u.plan +
            '</td><td>' + formatDt(u.expires_at) + '</td><td data-vz-user-cd="' + idx + '">—</td>' +
            '<td>' + (inactive ? "—" : '<button type="button" class="vipzone__btn vipzone__btn--sm vipzone__btn--ghost" data-vz-deactivate>Vô hiệu</button>') + '</td></tr>';
        }).join("");
        rows.forEach(function (u, idx) {
          if (u.active) {
            var cd = document.querySelector('[data-vz-user-cd="' + idx + '"]');
            if (cd && u.expires_at) VZ.startCountdown(u.expires_at, cd);
          }
        });
        bindDeactivateButtons();
        return;
      } catch (e) { VZ.toast(e.message || "Không tải users.", "error"); }
    }
    loadUsersLocal(VZ.readStore());
  }

  function bindDeactivateButtons() {
    var tbody = $("[data-vz-users-body]");
    if (!tbody) return;
    tbody.querySelectorAll("[data-vz-deactivate]").forEach(function (btn) {
      btn.addEventListener("click", async function () {
        if (!roleIsAdmin(currentUser)) return;
        var email = decodeURIComponent(btn.closest("tr").getAttribute("data-vip-email"));
        if (useApi()) {
          try {
            await apiFetch("/api/vipzone/admin/users/" + encodeURIComponent(email) + "/deactivate", { method: "POST" });
            await loadUsers();
            await refreshStats();
            VZ.toast("Đã vô hiệu VIP.", "success");
          } catch (e) { VZ.toast(e.message || "Lỗi.", "error"); }
          return;
        }
        var s = VZ.readStore();
        (s.vips || []).forEach(function (v) {
          if (v.email === email) v.active = false;
        });
        VZ.writeStore(s);
        loadUsersLocal(s);
        refreshStats();
        VZ.toast("Đã vô hiệu VIP.", "success");
      });
    });
  }

  function normPickUrl(u) {
    var x = (u || "").trim();
    if (VZ.BASE && x.indexOf(VZ.BASE) === 0) x = x.slice(VZ.BASE.length) || "/";
    if (!x.startsWith("/")) x = "/" + x;
    return x.endsWith("/") ? x : x + "/";
  }

  var ACCESS_LEVELS = ["public", "premium", "admin_only"];
  var ACCESS_LABELS = { public: "Public", premium: "Premium", admin_only: "Admin only" };

  function mergeCatalogItems(catalog, saved) {
    var map = {};
    (saved || []).forEach(function (row) {
      map[normPickUrl(row.url)] = row.access || "public";
    });
    var out = [];
    ["tools", "premium"].forEach(function (g) {
      (catalog[g] || []).forEach(function (item) {
        var url = normPickUrl(item.url);
        out.push({ url: url, title: item.title, access: map[url] || "public" });
      });
    });
    return out;
  }

  function migrateLocalItems(raw, catalog) {
    if (!raw || !raw.length) return mergeCatalogItems(catalog, []);
    if (typeof raw[0] === "string") {
      var legacy = raw.map(function (u) { return { url: normPickUrl(u), access: "premium" }; });
      return mergeCatalogItems(catalog, legacy);
    }
    return mergeCatalogItems(catalog, raw);
  }

  function readPickerItemsFromDom() {
    var out = [];
    document.querySelectorAll("[data-vz-picker-row]").forEach(function (row) {
      var url = row.getAttribute("data-vz-picker-url");
      var active = row.querySelector(".vipzone__picker-access--active");
      var access = active ? active.getAttribute("data-vz-access") : "public";
      if (url) out.push({ url: normPickUrl(url), access: access || "public" });
    });
    return out;
  }

  function accessPills(url, access) {
    return ACCESS_LEVELS.map(function (level) {
      var cls = "vipzone__picker-access" + (level === access ? " vipzone__picker-access--active" : "");
      return '<button type="button" class="' + cls + '" data-vz-access="' + level + '">' +
        ACCESS_LABELS[level] + "</button>";
    }).join("");
  }

  function renderPickerGroups(items) {
    var host = $("[data-vz-picker-catalog]");
    var loading = $("[data-vz-picker-loading]");
    if (!host || !pickerCatalog) return;
    if (loading) loading.hidden = true;
    var q = (pickerFilter || "").toLowerCase().trim();
    function match(item) {
      if (!q) return true;
      return (item.title || "").toLowerCase().indexOf(q) >= 0 ||
        (item.url || "").toLowerCase().indexOf(q) >= 0;
    }
    function groupHtml(title, groupItems) {
      var filtered = (groupItems || []).filter(match);
      if (!filtered.length) return "";
      var rows = filtered.map(function (item) {
        var url = normPickUrl(item.url);
        var level = item.access || "public";
        return '<div class="vipzone__picker-item" data-vz-picker-row data-vz-picker-url="' + url + '">' +
          '<span class="vipzone__picker-item-title">' + (item.title || url) + "</span>" +
          '<div class="vipzone__picker-access-group" role="group" aria-label="Access level">' +
          accessPills(url, level) + "</div></div>";
      }).join("");
      return '<section class="vipzone__picker-group"><h3 class="vipzone__picker-group-title">' + title +
        '</h3><div class="vipzone__picker-group-list">' + rows + "</div></section>";
    }
    var tools = items.filter(function (i) { return i.url.indexOf("/tools/") === 0; });
    var premium = items.filter(function (i) { return i.url.indexOf("/tools/") !== 0; });
    var html = groupHtml("Công cụ", tools) + groupHtml("Premium articles", premium);
    if (!html) {
      html = q
        ? '<p class="vipzone__empty">Không có mục khớp tìm kiếm.</p>'
        : '<p class="vipzone__empty">Danh mục picker chưa tải được. Hãy đăng nhập lại hoặc tải lại trang.</p>';
    }
    host.innerHTML = html;
    host.querySelectorAll(".vipzone__picker-access-group").forEach(function (group) {
      group.querySelectorAll("[data-vz-access]").forEach(function (btn) {
        btn.addEventListener("click", function () {
          if (!roleIsAdmin(currentUser)) return;
          group.querySelectorAll("[data-vz-access]").forEach(function (b) {
            b.classList.toggle("vipzone__picker-access--active", b === btn);
          });
        });
      });
    });
    applyRoleUI(currentUser || GUEST_USER, roleIsAdmin(currentUser));
  }

  async function fetchPickerCatalog() {
    // Primary: authenticated admin API (sends cookie + Bearer via credentials:include).
    // The static /data/*.json is not published to the site (robots Disallow /data/),
    // so the API endpoint is the source of truth for the catalog.
    if (useApi() && roleIsAdmin(currentUser)) {
      try {
        var data = await apiFetch("/api/vipzone/admin/picker/catalog");
        if (data && (data.tools || data.premium)) return data;
      } catch (e) {}
    }
    // Fallback: published static catalog JSON (non-admin viewers / API offline).
    try {
      var base = VZ.BASE || "/zola";
      var res = await fetch(base + "/data/vipzone-picker-catalog.json", {
        credentials: "include",
        cache: "no-store",
      });
      if (res.ok) return res.json();
    } catch (e) {}
    // Last resort: empty catalog so the picker degrades gracefully instead of crashing.
    return { updated_at: null, tools: [], premium: [] };
  }

  async function loadPicker() {
    var host = $("[data-vz-picker-catalog]");
    var loading = $("[data-vz-picker-loading]");
    if (!host) return;
    try {
      pickerCatalog = await fetchPickerCatalog();
      var items;
      if (useApi()) {
        try {
          if (roleIsAdmin(currentUser)) {
            var data = await apiFetch("/api/vipzone/admin/picker");
            items = mergeCatalogItems(pickerCatalog, data.items || []);
          } else {
            var pub = await fetch(API + "/api/vipzone/picker", { credentials: "include", cache: "no-store" });
            var pubData = pub.ok ? await pub.json() : { items: [] };
            items = mergeCatalogItems(pickerCatalog, pubData.items || []);
          }
        } catch (e) {
          items = mergeCatalogItems(pickerCatalog, []);
        }
      } else {
        var store = VZ.readStore();
        items = migrateLocalItems(store.pickerItems || store.picks || [], pickerCatalog);
        store.pickerItems = items;
        VZ.writeStore(store);
      }
      renderPickerGroups(items);
    } catch (e) {
      if (loading) {
        loading.textContent = "Không tải danh mục picker.";
        loading.hidden = false;
      }
      VZ.toast(e.message || "Không tải picker.", "error");
    }
  }

  async function fetchMe() {
    if (!API) return GUEST_USER;
    try {
      var res = await fetch(API + "/api/vipzone/me", {
        headers: authHeaders(),
        credentials: "include",
        cache: "no-store",
      });
      if (res.status === 401) {
        if (!getSid()) return GUEST_USER;
        clearSid();
        return GUEST_USER;
      }
      if (!res.ok) return GUEST_USER;
      return await res.json();
    } catch (e) {
      return GUEST_USER;
    }
  }

  async function initAdmin() {
    var root = document.querySelector('[data-vz-page="admin"]');
    if (!root) return;

    consumeHashSid();
    var authErr = consumeAuthQuery();
    if (authErr) {
      var errEl = $("[data-vz-login-error]");
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = "Đăng nhập thất bại: " + authErr;
      }
    }

    var loginBtn = $('[data-vz-action="login"]');
    if (loginBtn) {
      loginBtn.addEventListener("click", function () {
        if (!AUTH_API) { VZ.toast("VIPZone API chưa cấu hình.", "error"); return; }
        var ret = location.origin + location.pathname + location.search;
        location.href = AUTH_API + "/auth/login?return_to=" + encodeURIComponent(ret);
      });
    }

    var logoutBtn = $('[data-vz-action="logout"]');
    if (logoutBtn) {
      logoutBtn.addEventListener("click", async function () {
        try {
          if (AUTH_API) {
            await fetch(AUTH_API + "/auth/logout", {
              method: "POST",
              headers: authHeaders(),
              credentials: "include",
            });
          }
        } catch (e) {}
        clearSid();
        currentUser = GUEST_USER;
        showView("app");
        showTab("picker");
        applyRoleUI(GUEST_USER, false);
        await loadPicker();
      });
    }

    document.querySelectorAll("[data-vz-tab]").forEach(function (tab) {
      tab.addEventListener("click", function () {
        showTab(tab.getAttribute("data-vz-tab"));
      });
    });

    var createBtn = $('[data-vz-action="create-code"]');
    if (createBtn) {
      createBtn.addEventListener("click", async function () {
        if (!roleIsAdmin(currentUser)) return;
        var plan = $("#vz-admin-plan").value;
        var email = $("#vz-admin-email").value.trim();
        if (useApi()) {
          try {
            var out = await apiFetch("/api/vipzone/admin/codes", {
              method: "POST",
              body: { plan: plan, email: email || null },
            });
            var box = $("[data-vz-code-output]");
            if (box) { box.hidden = false; box.textContent = "Mã: " + out.code + " (gửi email " + (email || "—") + ")"; }
            await loadCodes();
            VZ.toast("Đã tạo mã 16 số.", "success");
          } catch (e) { VZ.toast(e.message || "Lỗi.", "error"); }
          return;
        }
        var code = VZ.genCode16();
        var s = VZ.readStore();
        s.codes = s.codes || [];
        s.codes.push({ code: code, plan: plan, email: email, used: false, created_at: new Date().toISOString() });
        VZ.writeStore(s);
        var outLocal = $("[data-vz-code-output]");
        if (outLocal) { outLocal.hidden = false; outLocal.textContent = "Mã: " + code + " (gửi email " + (email || "—") + ")"; }
        loadCodesLocal(s);
        VZ.toast("Đã tạo mã 16 số.", "success");
      });
    }

    var searchInput = $("[data-vz-picker-search]");
    if (searchInput) {
      searchInput.addEventListener("input", function () {
        pickerFilter = searchInput.value;
        if (!pickerCatalog) return;
        renderPickerGroups(readPickerItemsFromDom());
      });
    }

    var savePicker = $('[data-vz-action="save-picker"]');
    if (savePicker) {
      savePicker.addEventListener("click", async function () {
        if (!roleIsAdmin(currentUser)) {
          VZ.toast("Cần quyền admin để lưu.", "error");
          return;
        }
        var items = readPickerItemsFromDom().map(function (i) {
          return { url: i.url, access: i.access || "public" };
        });
        if (useApi()) {
          try {
            await apiFetch("/api/vipzone/admin/picker", { method: "PUT", body: { items: items } });
            VZ.toast("Đã lưu Content Picker.", "success");
          } catch (e) { VZ.toast(e.message || "Lỗi.", "error"); }
          return;
        }
        var s = VZ.readStore();
        s.pickerItems = items;
        VZ.writeStore(s);
        VZ.toast("Đã lưu Content Picker.", "success");
      });
    }

    currentUser = await fetchMe();
    var canAdmin = roleIsAdmin(currentUser);

    showView("app");
    showTab(canAdmin ? "payments" : "picker");
    applyRoleUI(currentUser, canAdmin);

    await loadPicker();
    if (canAdmin) {
      await refreshStats();
      await loadPayments();
      await loadCodes();
      await loadUsers();
    }
  }

  document.addEventListener("DOMContentLoaded", initAdmin);
})();