(function () {
  "use strict";

  var VZ = window.VIPZone;
  if (!VZ) return;

  var AUTH_API = VZ.API || (function () {
    var m = document.querySelector('meta[name="zola-vipzone-api"]');
    if (m && m.getAttribute("content")) return m.getAttribute("content").replace(/\/$/, "");
    m = document.querySelector('meta[name="vipzone-auth-api"]');
    return m && m.getAttribute("content") ? m.getAttribute("content").replace(/\/$/, "") : "https://blog-vipzone-api.onrender.com";
  })();

  var CMS_KEY = "zola-cms-session-id";
  var pickerCatalog = null;
  var pickerFilter = "";

  function $(s) { return document.querySelector(s); }

  function useApi() { return !!VZ.API; }

  function getSid() {
    try { return sessionStorage.getItem(CMS_KEY) || ""; } catch (e) { return ""; }
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
    if (useApi()) {
      try {
        var stats = await VZ.apiFetch("/api/vipzone/admin/stats");
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
    if (useApi()) {
      try {
        var rows = await VZ.apiFetch("/api/vipzone/admin/requests");
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
        var id = btn.closest("tr").getAttribute("data-pay-id");
        if (useApi()) {
          try {
            await VZ.apiFetch("/api/vipzone/admin/requests/" + encodeURIComponent(id) + "/resolve", { method: "POST" });
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
    if (useApi()) {
      try {
        var rows = await VZ.apiFetch("/api/vipzone/admin/codes");
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
    if (useApi()) {
      try {
        var rows = await VZ.apiFetch("/api/vipzone/admin/users");
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
        var email = decodeURIComponent(btn.closest("tr").getAttribute("data-vip-email"));
        if (useApi()) {
          try {
            await VZ.apiFetch("/api/vipzone/admin/users/" + encodeURIComponent(email) + "/deactivate", { method: "POST" });
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

  function accessForUrl(items, url) {
    var u = normPickUrl(url);
    for (var i = 0; i < (items || []).length; i++) {
      if (normPickUrl(items[i].url) === u) return items[i].access || "public";
    }
    return "public";
  }

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
    if (!html) html = '<p class="vipzone__empty">Không có mục khớp tìm kiếm.</p>';
    host.innerHTML = html;
    host.querySelectorAll(".vipzone__picker-access-group").forEach(function (group) {
      group.querySelectorAll("[data-vz-access]").forEach(function (btn) {
        btn.addEventListener("click", function () {
          group.querySelectorAll("[data-vz-access]").forEach(function (b) {
            b.classList.toggle("vipzone__picker-access--active", b === btn);
          });
        });
      });
    });
  }

  async function fetchPickerCatalog() {
    if (useApi()) {
      return VZ.apiFetch("/api/vipzone/admin/picker/catalog");
    }
    var base = VZ.BASE || "/zola";
    var res = await fetch(base + "/data/vipzone-picker-catalog.json", { cache: "no-store" });
    if (!res.ok) throw new Error("Không tải catalog JSON.");
    return res.json();
  }

  async function loadPicker() {
    var host = $("[data-vz-picker-catalog]");
    var loading = $("[data-vz-picker-loading]");
    if (!host) return;
    try {
      pickerCatalog = await fetchPickerCatalog();
      var items;
      if (useApi()) {
        var data = await VZ.apiFetch("/api/vipzone/admin/picker");
        items = mergeCatalogItems(pickerCatalog, data.items || []);
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
    if (!AUTH_API || !getSid()) return null;
    var res = await fetch(AUTH_API + "/auth/me", {
      headers: { Authorization: "Bearer " + getSid() },
      credentials: "omit",
      cache: "no-store",
    });
    if (!res.ok) return null;
    return res.json();
  }

  async function initAdmin() {
    var root = document.querySelector('[data-vz-page="admin"]');
    if (!root) return;

    consumeHashSid();

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
          if (AUTH_API && getSid()) {
            await fetch(AUTH_API + "/auth/logout", { method: "POST", headers: { Authorization: "Bearer " + getSid() } });
          }
        } catch (e) {}
        clearSid();
        showView("login");
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
        var plan = $("#vz-admin-plan").value;
        var email = $("#vz-admin-email").value.trim();
        if (useApi()) {
          try {
            var out = await VZ.apiFetch("/api/vipzone/admin/codes", {
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
        var items = readPickerItemsFromDom().map(function (i) {
          return { url: i.url, access: i.access || "public" };
        });
        if (useApi()) {
          try {
            await VZ.apiFetch("/api/vipzone/admin/picker", { method: "PUT", body: { items: items } });
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

    var me = await fetchMe();
    var superOk = me && await VZ.isSuperuser();
    if (!superOk) {
      showView(getSid() ? "denied" : "login");
      return;
    }

    showView("app");
    var bar = $("[data-vz-user-bar]");
    if (bar) {
      bar.hidden = false;
      var nm = $("[data-vz-admin-name]");
      if (nm) nm.textContent = me.username || me.email || "Admin";
    }

    await refreshStats();
    await loadPayments();
    await loadCodes();
    await loadUsers();
    await loadPicker();
  }

  document.addEventListener("DOMContentLoaded", initAdmin);
})();
