(function (global) {
  "use strict";

  function getHost() {
    return document.querySelector("[data-sse-toast-host]");
  }

  function showToast(message, type) {
    const host = getHost();
    if (!host) return;
    const el = document.createElement("div");
    el.className = "shortensea__toast shortensea__toast--" + (type || "success");
    el.setAttribute("role", "status");
    el.textContent = message;
    host.appendChild(el);
    setTimeout(function () {
      el.style.opacity = "0";
      el.style.transition = "opacity 0.3s ease";
      setTimeout(function () { el.remove(); }, 300);
    }, 3500);
  }

  global.ShortenSEAToast = { show: showToast };
})(window);