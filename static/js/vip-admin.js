(function () {
  "use strict";

  var VZ = window.VIPZone;
  if (!VZ) return;

  var AUTH_API = (function () {
    var m = document.querySelector('meta[name="zola-cms-auth-api"]');
    return m && m.getAttribute("content") ? m.getAttribute("content").replace(/\/$/, "") : "";
  })();

  var CMS_KEY = "zola-cms-session-id";
  var PICKER_ITEMS = [
    { title: "F-Dashboard", url: "/tools/f-dashboard/" },
    { title: "Content Creator", url: "/tools/content-creator/" },
    { title: "Flight DB", url: "/tools/flight-db/" },
    { title: "Insights", url: "/insights/" },
    { title: "Premium hub", url: "/categories/premium/" },
  ];

  function $(s) { return document.querySelector(s); }

  function getSid() {
    try { return sessionStorage.getItem(CMS_KEY) || ""; } catch (e) { return ""; }
  }

  function setSid(sid) {
    try { sessionStorage.setItem(CMS_KEY, sid); } catch (e) {}
  }

  function clearSid() {
    try { sessionStorage.removeItem(CMS_KEY); } catch (e) {}
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

  function updateStats(store) {
    var pending = (store.payments || []).filter(function (p) { return p.status === "pending"; }).length;
    var active = VZ.activeVipCount();
    var rev = store.revenue || 0;
    var elP = $("[data-vz-stat-pending]");
    var elA = $("[data-vz-stat-active]");
    var elR = $("[data-vz-stat-revenue]");
    if (elP) elP.textContent = String(pending);
    if (elA) elA.textContent = String(active);
    if (elR) elR.textContent = rev.toLocaleString("vi-VN") + "đ";
  }

  function loadPayments(store) {
    var tbody = $("[data-vz-payments-body]");
    if (!tbody) return;
    var rows = (store.payments || []).slice().reverse();
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="vipzone__empty">Không có yêu cầu.</td></tr>';
      return;
    }
    tbody.innerHTML = rows.map(function (r) {
      return '<tr data-pay-id="' + r.id + '"><td>' + r.email + '</td><td>' + r.plan +
        '</td><td>' + (r.note || "—") + '</td><td>' + r.status +
        '</td><td><button type="button" class="vipzone__btn vipzone__btn--sm vipzone__btn--ghost" data-vz-resolve>Đã xử lý</button></td></tr>';
    }).join("");
    tbody.querySelectorAll("[data-vz-resolve]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var id = btn.closest("tr").getAttribute("data-pay-id");
        var s = VZ.readStore();
        (s.payments || []).forEach(function (p) {
          if (p.id === id) p.status = "resolved";
        });
        VZ.writeStore(s);
        loadPayments(s);
        updateStats(s);
        VZ.toast("Đã đánh dấu xử lý.", "success");
      });
    });
  }

  function loadCodes(store) {
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

  function loadUsers(store) {
    var tbody = $("[data-vz-users-body]");
    if (!tbody) return;
    var rows = (store.vips || []).slice().reverse();
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="vipzone__empty">Chưa có VIP.</td></tr>';
      return;
    }
    tbody.innerHTML = rows.map(function (u, idx) {
      return '<tr data-vip-idx="' + idx + '"><td>' + u.email + '</td><td>' + u.plan +
        '</td><td>' + formatDt(u.expires_at) + '</td><td data-vz-user-cd="' + idx + '">—</td>' +
        '<td><button type="button" class="vipzone__btn vipzone__btn--sm vipzone__btn--ghost" data-vz-deactivate>Vô hiệu</button></td></tr>';
    }).join("");
    rows.forEach(function (u, idx) {
      var cd = document.querySelector('[data-vz-user-cd="' + idx + '"]');
      if (cd && u.expires_at) VZ.startCountdown(u.expires_at, cd);
    });
    tbody.querySelectorAll("[data-vz-deactivate]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var idx = parseInt(btn.closest("tr").getAttribute("data-vip-idx"), 10);
        var s = VZ.readStore();
        if (s.vips[idx]) s.vips[idx].active = false;
        VZ.writeStore(s);
        loadUsers(s);
        updateStats(s);
        VZ.toast("Đã vô hiệu VIP.", "success");
      });
    });
  }

  function loadPicker(store) {
    var list = $("[data-vz-picker-list]");
    if (!list) return;
    var picks = store.picks || [];
    list.innerHTML = PICKER_ITEMS.map(function (item) {
      var checked = picks.indexOf(item.url) >= 0 ? " checked" : "";
      return '<label class="vipzone__picker-item"><input type="checkbox" value="' + item.url + '"' + checked + '> ' + item.title + '</label>';
    }).join("");
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
        if (!AUTH_API) { VZ.toast("CMS auth chưa cấu hình.", "error"); return; }
        var ret = location.pathname + location.search;
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
      createBtn.addEventListener("click", function () {
        var plan = $("#vz-admin-plan").value;
        var email = $("#vz-admin-email").value.trim();
        var code = VZ.genCode16();
        var s = VZ.readStore();
        s.codes = s.codes || [];
        s.codes.push({ code: code, plan: plan, email: email, used: false, created_at: new Date().toISOString() });
        VZ.writeStore(s);
        var out = $("[data-vz-code-output]");
        if (out) { out.hidden = false; out.textContent = "Mã: " + code + " (gửi email " + (email || "—") + ")"; }
        loadCodes(s);
        VZ.toast("Đã tạo mã 16 số.", "success");
      });
    }

    var savePicker = $('[data-vz-action="save-picker"]');
    if (savePicker) {
      savePicker.addEventListener("click", function () {
        var urls = [];
        document.querySelectorAll(".vipzone__picker-item input:checked").forEach(function (cb) {
          urls.push(cb.value);
        });
        var s = VZ.readStore();
        s.picks = urls;
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

    var store = VZ.readStore();
    updateStats(store);
    loadPayments(store);
    loadCodes(store);
    loadUsers(store);
    loadPicker(store);
  }

  document.addEventListener("DOMContentLoaded", initAdmin);
})();