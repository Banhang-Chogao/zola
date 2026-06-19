(function () {
  "use strict";

  var toast = window.ShortenSEAToast;
  var api = window.ShortenSEAApi;
  var auth = window.ShortenSEAAuth;

  function $(sel) { return document.querySelector(sel); }

  function formatDate(iso) {
    if (!iso) return "—";
    try {
      return new Date(iso).toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" });
    } catch (e) { return iso; }
  }

  function showAdminTab(name) {
    document.querySelectorAll("[data-sse-admin-tab]").forEach(function (btn) {
      btn.classList.toggle("shortensea__nav-tab--active", btn.getAttribute("data-sse-admin-tab") === name);
    });
    document.querySelectorAll("[data-sse-admin-panel]").forEach(function (panel) {
      panel.hidden = panel.getAttribute("data-sse-admin-panel") !== name;
    });
  }

  async function loadCodes() {
    var tbody = $("[data-sse-codes-body]");
    if (!tbody) return;
    try {
      var codes = await api.adminListCodes();
      if (!codes.length) {
        tbody.innerHTML = '<tr><td colspan="4" class="shortensea__empty">Chưa có mã nào.</td></tr>';
        return;
      }
      tbody.innerHTML = codes.map(function (c) {
        return "<tr><td>" + c.plan_type + "</td><td>" + (c.email || "—") + "</td><td>" +
          (c.used ? "✓" : "—") + "</td><td>" + formatDate(c.created_at) + "</td></tr>";
      }).join("");
    } catch (e) {
      toast.show(e.message || "Không tải được mã.", "error");
    }
  }

  async function loadPayments() {
    var tbody = $("[data-sse-payments-body]");
    if (!tbody) return;
    try {
      var rows = await api.adminListPaymentRequests("pending");
      if (!rows.length) {
        tbody.innerHTML = '<tr><td colspan="5" class="shortensea__empty">Không có yêu cầu chờ xử lý.</td></tr>';
        return;
      }
      tbody.innerHTML = rows.map(function (r) {
        return '<tr data-req-id="' + r.request_id + '"><td>' + r.email + '</td><td>' + r.plan_type +
          '</td><td>' + (r.payment_note || "—") + '</td><td>' + r.status +
          '</td><td><button type="button" class="shortensea__btn shortensea__btn--ghost shortensea__btn--sm" data-action="resolve">Đã xử lý</button></td></tr>';
      }).join("");
      tbody.querySelectorAll("[data-action=resolve]").forEach(function (btn) {
        btn.addEventListener("click", async function () {
          var row = btn.closest("tr");
          var id = row.getAttribute("data-req-id");
          try {
            await api.adminResolvePaymentRequest(id);
            toast.show("Đã đánh dấu xử lý.", "success");
            loadPayments();
          } catch (e) {
            toast.show(e.message || "Lỗi.", "error");
          }
        });
      });
    } catch (e) {
      toast.show(e.message || "Không tải được yêu cầu.", "error");
    }
  }

  async function loadUsers() {
    var tbody = $("[data-sse-users-body]");
    if (!tbody) return;
    try {
      var users = await api.adminListUsers();
      tbody.innerHTML = users.map(function (u) {
        return '<tr data-user-id="' + u.user_id + '"><td>' + (u.username || u.email || u.user_id.slice(0, 8)) +
          (u.is_guest ? " (khách)" : "") + '</td><td>' + (u.plan || "free") + '</td><td>' +
          formatDate(u.plan_expires_at) + '</td><td>' + (u.is_super ? "✦" : "—") +
          '</td><td><select class="shortensea__select shortensea__select--sm" data-action="override">' +
          '<option value="">—</option><option value="free">Free</option><option value="monthly">Monthly</option>' +
          '<option value="yearly">Yearly</option><option value="super">Super VIP</option></select></td></tr>';
      }).join("");
      tbody.querySelectorAll("[data-action=override]").forEach(function (sel) {
        sel.addEventListener("change", async function () {
          var plan = sel.value;
          if (!plan) return;
          var row = sel.closest("tr");
          var uid = row.getAttribute("data-user-id");
          try {
            var body = plan === "super"
              ? { plan: "super", is_super: true }
              : { plan: plan, days: plan === "yearly" ? 365 : plan === "monthly" ? 30 : null };
            await api.adminOverrideUser(uid, body);
            toast.show("Đã cập nhật gói.", "success");
            loadUsers();
          } catch (e) {
            toast.show(e.message || "Override thất bại.", "error");
          }
          sel.value = "";
        });
      });
    } catch (e) {
      toast.show(e.message || "Không tải được users.", "error");
    }
  }

  async function onCreateCode() {
    var plan = $("#sse-admin-plan").value;
    var email = $("#sse-admin-email").value.trim();
    var userId = $("#sse-admin-user-id").value.trim();
    try {
      var res = await api.adminCreateCode({
        plan_type: plan,
        email: email,
        user_id: userId,
      });
      var out = $("[data-sse-admin-code-output]");
      if (out) {
        out.hidden = false;
        out.textContent = "Approve code: " + res.approve_code + "\nGói: " + res.plan_type +
          "\nGửi email cho người dùng thủ công.";
      }
      toast.show("Đã tạo mã: " + res.approve_code, "success");
      loadCodes();
    } catch (e) {
      toast.show(e.message || "Tạo mã thất bại.", "error");
    }
  }

  document.addEventListener("DOMContentLoaded", async function () {
    if (!document.querySelector('[data-sse-page="admin"]')) return;

    document.querySelectorAll("[data-sse-admin-tab]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        showAdminTab(btn.getAttribute("data-sse-admin-tab"));
        if (btn.getAttribute("data-sse-admin-tab") === "payments") loadPayments();
        if (btn.getAttribute("data-sse-admin-tab") === "users") loadUsers();
      });
    });

    var createBtn = $('[data-sse-action="admin-create-code"]');
    if (createBtn) createBtn.addEventListener("click", onCreateCode);

    var user = await auth.initAdmin();
    if (!user) return;

    auth.populateUserBar(user);
    await loadCodes();
  });
})();