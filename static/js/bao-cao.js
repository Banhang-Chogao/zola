/**
 * Báo cáo tổng kết — auth gate cho download buttons.
 *
 * Logic:
 *   - Check GitHub PAT trong sessionStorage (set bởi /editor/ login flow)
 *   - PAT có → show download buttons, hide locked icon
 *   - PAT không → keep buttons hidden, show locked icon, show anon banner
 *
 * Lưu ý: Đây là CLIENT-SIDE gate. File .md nằm tại /data/reports/ vẫn
 * public theo design GitHub Pages — ai biết URL vẫn truy cập trực tiếp.
 * Để security THẬT, cần phase 2: backend endpoint check OAuth GitHub.
 */
(function () {
  "use strict";

  const PAT_KEY = "zola-cms-pat";   // key giống editor.js
  const pat = (function () {
    try {
      return sessionStorage.getItem(PAT_KEY) || "";
    } catch (e) {
      return "";
    }
  })();

  const isAdmin = pat && pat.length > 20;   // basic check

  const gate = document.querySelector("[data-auth-gate]");
  if (gate) {
    const anonBox = gate.querySelector("[data-auth-anon]");
    const adminBox = gate.querySelector("[data-auth-admin]");
    if (isAdmin) {
      if (anonBox) anonBox.hidden = true;
      if (adminBox) adminBox.hidden = false;
    }
  }

  document.querySelectorAll("[data-auth-required]").forEach((el) => {
    el.hidden = !isAdmin;
  });

  document.querySelectorAll("[data-auth-locked]").forEach((el) => {
    el.hidden = isAdmin;
  });

  if (isAdmin) {
    console.info("[bao-cao] admin auth detected — download buttons enabled");
  } else {
    console.info("[bao-cao] anon mode — login at /editor/ to download");
  }
})();
