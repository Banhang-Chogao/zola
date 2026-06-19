(function () {
  "use strict";

  var toast = window.ShortenSEAToast;
  var api = window.ShortenSEAApi;
  var auth = window.ShortenSEAAuth;

  function $(sel) { return document.querySelector(sel); }

  function formatDate(iso) {
    if (!iso) return "Không hết hạn";
    try {
      return new Date(iso).toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" });
    } catch (e) { return iso; }
  }

  function applyPlanUI(account) {
    if (!account) return;
    var avatar = $("[data-sse-avatar]");
    if (avatar && account.avatar) { avatar.src = account.avatar; avatar.alt = account.name || ""; }
    var set = function (sel, val) { var el = $(sel); if (el) el.textContent = val; };
    set("[data-sse-name]", account.name || account.username || "—");
    set("[data-sse-email]", account.email || account.username || "");
    set("[data-sse-plan]", account.plan_label || account.plan);
    set("[data-sse-remaining-links]", String(account.remaining_links));
    set("[data-sse-remaining-halves]", String(account.remaining_custom_halves));
    set("[data-sse-expiry]", account.is_super ? "Vĩnh viễn" : formatDate(account.plan_expires_at));

    var badge = $("[data-sse-super-badge]");
    if (badge) badge.hidden = !account.is_super;

    var domainInput = $("[data-sse-domain-input]");
    if (domainInput) domainInput.value = account.short_domain || "";

    document.querySelectorAll("[data-sse-momo-link]").forEach(function (a) {
      if (account.momo_payment_link) a.href = account.momo_payment_link;
    });

    var limits = account.limits || {};
    var slugInput = $("[data-sse-slug-input]");
    if (slugInput) slugInput.disabled = !limits.custom_halves && !account.is_super;
    var tagsInput = $("[data-sse-tags-input]");
    if (tagsInput) tagsInput.disabled = !limits.tags && !account.is_super;
    var qrInput = $("[data-sse-qr-input]");
    if (qrInput) qrInput.disabled = !limits.qr && !account.is_super;
    var expToggle = $("[data-sse-exp-toggle]");
    if (expToggle) expToggle.disabled = !limits.expiration && !account.is_super;
    var utmToggle = $("#sse-utm-toggle");
    if (utmToggle) utmToggle.disabled = !limits.utm && !account.is_super;

    var warn = $("[data-sse-expiry-warning]");
    if (warn && account.plan_expires_at && !account.is_super) {
      var daysLeft = Math.ceil((new Date(account.plan_expires_at) - Date.now()) / 86400000);
      if (daysLeft <= 7 && daysLeft > 0) {
        warn.textContent = "⚠ Gói premium hết hạn sau " + daysLeft + " ngày. Gia hạn qua MoMo để giữ quyền lợi.";
        warn.hidden = false;
      } else if (daysLeft <= 0 && account.locked_until) {
        warn.textContent = "⚠ Gói đã hết hạn — đang trong thời gian khóa 1 ngày trước khi hạ về miễn phí.";
        warn.hidden = false;
      } else {
        warn.hidden = true;
      }
    } else if (warn) {
      warn.hidden = true;
    }

    var adminPanel = $("[data-sse-admin-panel]");
    if (adminPanel) adminPanel.hidden = !account.is_super;
  }

  function bindToggles() {
    var utmToggle = $("#sse-utm-toggle");
    var utmPanel = $("#sse-utm-panel");
    if (utmToggle && utmPanel) {
      utmToggle.addEventListener("change", function () {
        utmPanel.hidden = !utmToggle.checked;
      });
    }
    var expToggle = $("#sse-exp-toggle");
    var expField = $("#sse-exp-field");
    if (expToggle && expField) {
      expToggle.addEventListener("change", function () {
        expField.hidden = !expToggle.checked;
      });
    }
  }

  function showQr(url) {
    var box = $("#sse-qr-preview");
    if (!box) return;
    box.hidden = false;
    box.innerHTML = '<p class="shortensea__label">QR Code</p><img src="https://api.qrserver.com/v1/create-qr-code/?size=160x160&data=' +
      encodeURIComponent(url) + '" alt="QR code" width="160" height="160" loading="lazy">';
  }

  async function onCreate(e) {
    e.preventDefault();
    var dest = $("#sse-dest").value.trim();
    if (!/^https?:\/\//i.test(dest)) {
      toast.show("URL đích phải bắt đầu bằng http:// hoặc https://", "error");
      return;
    }
    var tagsRaw = $("#sse-tags").value.trim();
    var tags = tagsRaw ? tagsRaw.split(",").map(function (t) { return t.trim(); }).filter(Boolean) : [];
    var body = {
      destination_url: dest,
      slug: $("#sse-slug").value.trim(),
      title: $("#sse-title").value.trim(),
      tags: tags,
      domain: $("#sse-domain").value.trim(),
      qr_enabled: $("#sse-qr").checked,
      utm_source: $("#sse-utm-source").value.trim(),
      utm_medium: $("#sse-utm-medium").value.trim(),
      utm_campaign: $("#sse-utm-campaign").value.trim(),
      utm_term: $("#sse-utm-term").value.trim(),
      utm_content: $("#sse-utm-content").value.trim(),
      expires_at: ""
    };
    if ($("#sse-exp-toggle").checked && $("#sse-exp-date").value) {
      body.expires_at = new Date($("#sse-exp-date").value).toISOString().replace(/\.\d{3}Z$/, "Z");
    }
    try {
      var link = await api.createLink(body);
      toast.show("Đã tạo link: " + link.short_url, "success");
      if (navigator.clipboard) {
        try { await navigator.clipboard.writeText(link.short_url); } catch (e) {}
      }
      if (link.qr_enabled) showQr(link.short_url);
      var account = await api.getAccount();
      applyPlanUI(account);
      $("#sse-create-form").reset();
      $("#sse-utm-panel").hidden = true;
      $("#sse-exp-field").hidden = true;
    } catch (err) {
      toast.show(err.message || "Tạo link thất bại.", "error");
    }
  }

  async function onRedeem() {
    var code = $("#sse-approve-code").value.trim();
    if (!code) { toast.show("Nhập approve code.", "error"); return; }
    try {
      var res = await api.redeemCode(code);
      applyPlanUI(res.account);
      toast.show("Kích hoạt gói thành công!", "success");
      $("#sse-approve-code").value = "";
    } catch (err) {
      toast.show(err.message || "Mã không hợp lệ.", "error");
    }
  }

  async function onAdminCreateCode() {
    var plan = $("#sse-admin-plan").value;
    var email = $("#sse-admin-email").value.trim();
    try {
      var res = await api.adminCreateCode({ plan_type: plan, email: email });
      var out = $("[data-sse-admin-code-output]");
      if (out) {
        out.hidden = false;
        out.textContent = "Approve code: " + res.approve_code + "\nGói: " + res.plan_type + "\nGửi email cho người dùng thủ công.";
      }
      toast.show("Đã tạo mã: " + res.approve_code, "success");
    } catch (err) {
      toast.show(err.message || "Tạo mã thất bại.", "error");
    }
  }

  function bindActions() {
    document.querySelectorAll('[data-sse-action="login"]').forEach(function (btn) {
      btn.addEventListener("click", function () { auth.login(); });
    });
    document.querySelectorAll('[data-sse-action="logout"]').forEach(function (btn) {
      btn.addEventListener("click", async function () {
        await auth.logout();
        auth.showView("login");
      });
    });
    var redeemBtn = $('[data-sse-action="redeem"]');
    if (redeemBtn) redeemBtn.addEventListener("click", onRedeem);
    var adminBtn = $('[data-sse-action="admin-create-code"]');
    if (adminBtn) adminBtn.addEventListener("click", onAdminCreateCode);
    var form = $("#sse-create-form");
    if (form) form.addEventListener("submit", onCreate);
  }

  document.addEventListener("DOMContentLoaded", async function () {
    if (!document.querySelector('[data-sse-page="home"]')) return;
    bindToggles();
    bindActions();
    var user = await auth.init();
    if (!user) return;
    try {
      var account = await api.getAccount();
      applyPlanUI(account);
    } catch (e) {
      toast.show("Không tải được thông tin tài khoản.", "error");
    }
  });
})();