/**
 * Content hub (/content) — chỉ là LỚP HIỂN THỊ.
 * Khối là link thường: gate thật (VIP tool / premium article) đã do VIPZone
 * (vipzone.js) + paywall.js fire khi điều hướng tới trang đích → KHÔNG nhân
 * bản logic gate ở đây. Việc duy nhất: gỡ badge 🔒 cho user đã VIP/superuser
 * để UI khỏi gây hiểu nhầm.
 */
(function () {
  "use strict";

  function unlock() {
    document.querySelectorAll("[data-vip-lock]").forEach(function (el) { el.remove(); });
    document.querySelectorAll(".content-block--locked[data-gate='vip']").forEach(function (b) {
      b.classList.remove("content-block--locked");
    });
  }

  function run() {
    var VZ = window.VIPZone;
    if (!VZ) return; // vipzone.js chưa sẵn sàng → giữ badge, không phá gì
    try {
      if (VZ.isVipActive && VZ.isVipActive()) { unlock(); return; }
      if (VZ.isSuperuser) {
        VZ.isSuperuser().then(function (ok) { if (ok) unlock(); }).catch(function () {});
      }
    } catch (e) { /* never break the page */ }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }
})();
