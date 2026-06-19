(function () {
  "use strict";

  var toast = window.ShortenSEAToast;
  var api = window.ShortenSEAApi;
  var auth = window.ShortenSEAAuth;

  function $(sel) { return document.querySelector(sel); }

  function applyAccountUI(account) {
    if (!account) return;
    auth.populateUserBar && auth.populateUserBar(account);

    var quota = $("[data-sse-quota-pill]");
    if (quota) {
      quota.textContent = (account.remaining_links || 0) + " link còn lại · " + (account.plan_label || account.plan);
    }

    var upgradeCta = $("[data-sse-upgrade-cta]");
    if (upgradeCta) upgradeCta.hidden = account.is_super || account.plan === "monthly" || account.plan === "yearly";

    var ghLogin = $('[data-sse-action="github-login"]');
    var logoutBtn = $('[data-sse-action="logout"]');
    if (ghLogin) ghLogin.hidden = auth.isGitHubSession();
    if (logoutBtn) logoutBtn.hidden = !auth.isGitHubSession();

    var premiumField = $("[data-sse-premium-field]");
    var slugInput = $("[data-sse-slug-input]");
    var limits = account.limits || {};
    if (premiumField) {
      premiumField.hidden = !limits.custom_halves && !account.is_super;
    }
    if (slugInput) slugInput.disabled = !limits.custom_halves && !account.is_super;

    document.querySelectorAll("[data-sse-momo-link]").forEach(function (a) {
      if (account.momo_payment_link) a.href = account.momo_payment_link;
    });
  }

  function showResult(url) {
    var box = $("#sse-result");
    var el = $("[data-sse-result-url]");
    if (!box || !el) return;
    el.textContent = url;
    box.hidden = false;
  }

  async function onCreate(e) {
    e.preventDefault();
    var dest = $("#sse-dest").value.trim();
    if (!/^https?:\/\//i.test(dest)) {
      toast.show("URL đích phải bắt đầu bằng http:// hoặc https://", "error");
      return;
    }
    var body = {
      destination_url: dest,
      slug: ($("#sse-slug") && $("#sse-slug").value.trim()) || "",
      title: "",
      tags: [],
      qr_enabled: false,
    };
    try {
      var link = await api.createLink(body);
      toast.show("Đã tạo link!", "success");
      showResult(link.short_url);
      if (navigator.clipboard) {
        try { await navigator.clipboard.writeText(link.short_url); } catch (err) {}
      }
      var account = await api.getAccount();
      applyAccountUI(account);
      $("#sse-create-form").reset();
    } catch (err) {
      if (err.status === 403) {
        toast.show(err.message || "Hết quota hoặc cần VIP.", "error");
        setTimeout(function () {
          window.location.href = api.getBaseUrl() + "/shortensea/upgrade/";
        }, 1500);
        return;
      }
      toast.show(err.message || "Tạo link thất bại.", "error");
    }
  }

  function bindActions() {
    var form = $("#sse-create-form");
    if (form) form.addEventListener("submit", onCreate);

    var copyBtn = $('[data-sse-action="copy-result"]');
    if (copyBtn) {
      copyBtn.addEventListener("click", async function () {
        var url = $("[data-sse-result-url]");
        if (!url || !url.textContent) return;
        if (navigator.clipboard) {
          await navigator.clipboard.writeText(url.textContent);
          toast.show("Đã copy!", "success");
        }
      });
    }

    var ghBtn = $('[data-sse-action="github-login"]');
    if (ghBtn) ghBtn.addEventListener("click", function () { auth.login(); });

    var logoutBtn = $('[data-sse-action="logout"]');
    if (logoutBtn) logoutBtn.addEventListener("click", async function () {
      await auth.logout();
      window.location.reload();
    });
  }

  document.addEventListener("DOMContentLoaded", async function () {
    if (!document.querySelector('[data-sse-page="home"]')) return;
    bindActions();

    if (!api.isConfigured()) {
      var errEl = $("[data-sse-api-error]");
      if (errEl) {
        errEl.textContent = "ShortenSEA API chưa sẵn sàng. Kiểm tra Render service blog-shortensea-api.";
        errEl.hidden = false;
      }
      return;
    }

    var user = await auth.initPublic();
    if (!user) return;

    try {
      var account = await api.getAccount();
      applyAccountUI(account);
    } catch (e) {
      toast.show("Không tải được thông tin tài khoản.", "error");
    }
  });
})();