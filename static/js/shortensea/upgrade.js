(function () {
  "use strict";

  var toast = window.ShortenSEAToast;
  var api = window.ShortenSEAApi;
  var auth = window.ShortenSEAAuth;

  var PLAN_LABELS = {
    monthly: "Gói Tháng — 50.000 VND / tháng",
    yearly: "Gói Năm — 500.000 VND / năm",
  };

  function $(sel) { return document.querySelector(sel); }

  function setPlan(plan) {
    var input = $("#sse-selected-plan");
    if (input) input.value = plan;
    var label = $("[data-sse-selected-plan-label]");
    if (label) label.textContent = PLAN_LABELS[plan] || plan;
    document.querySelectorAll("[data-sse-plan-card]").forEach(function (card) {
      var p = card.getAttribute("data-sse-plan-card");
      card.classList.toggle("shortensea__price-card--featured", p === plan);
    });
  }

  async function onPaymentSubmit(e) {
    e.preventDefault();
    var email = $("#sse-pay-email").value.trim();
    var note = $("#sse-pay-note").value.trim();
    var plan = $("#sse-selected-plan").value;
    if (!email) { toast.show("Nhập email.", "error"); return; }
    try {
      var res = await api.submitPaymentRequest({
        email: email,
        plan_type: plan,
        payment_note: note,
      });
      toast.show(res.message || "Đã gửi yêu cầu kích hoạt.", "success");
    } catch (err) {
      toast.show(err.message || "Gửi yêu cầu thất bại.", "error");
    }
  }

  async function onRedeem() {
    var code = $("#sse-approve-code").value.trim();
    if (!code) { toast.show("Nhập approve code.", "error"); return; }
    try {
      var res = await api.redeemCode(code);
      var success = $("#sse-success");
      var flow = $("#sse-paywall-flow");
      var msg = $("[data-sse-success-msg]");
      if (msg && res.account) {
        msg.textContent = "Gói " + (res.account.plan_label || res.account.plan) + " đã kích hoạt. Hết hạn: " +
          (res.account.plan_expires_at ? new Date(res.account.plan_expires_at).toLocaleDateString("vi-VN") : "—");
      }
      if (flow) flow.hidden = true;
      if (success) success.hidden = false;
      toast.show("Kích hoạt VIP thành công!", "success");
    } catch (err) {
      toast.show(err.message || "Mã không hợp lệ.", "error");
    }
  }

  document.addEventListener("DOMContentLoaded", async function () {
    if (!document.querySelector('[data-sse-page="upgrade"]')) return;

    if (!api.isConfigured()) {
      toast.show("ShortenSEA API chưa sẵn sàng.", "error");
      return;
    }

    await auth.initUpgrade();
    setPlan("yearly");

    document.querySelectorAll("[data-sse-select-plan]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        setPlan(btn.getAttribute("data-sse-select-plan"));
      });
    });

    var payForm = $("#sse-payment-form");
    if (payForm) payForm.addEventListener("submit", onPaymentSubmit);

    var redeemBtn = $('[data-sse-action="redeem"]');
    if (redeemBtn) redeemBtn.addEventListener("click", onRedeem);

    try {
      var account = await api.getAccount();
      if (account && account.momo_payment_link) {
        document.querySelectorAll("[data-sse-momo-link]").forEach(function (a) {
          a.href = account.momo_payment_link;
        });
      }
    } catch (e) {}
  });
})();