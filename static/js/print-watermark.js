/**
 * print-watermark — chèn watermark trace lên MỌI PDF xuất từ site qua trình duyệt
 * (Ctrl/Cmd+P → Save as PDF). Watermark = {16 hex random/blockchain-style ID}_{domain blog}.
 * Lặp chéo + trung tâm, chỉ hiển thị khi @media print (xem _print-watermark.scss).
 *
 * Lưu ý: đây là dấu vết bản quyền in/PDF, KHÔNG phải bảo mật tuyệt đối.
 * Các dashboard (F/L/O/H) đã tự nhúng watermark cùng định dạng trong PDF jsPDF.
 */
(function () {
  "use strict";

  function id16() {
    var bytes = new Uint8Array(8); // 8 byte = 16 hex
    (window.crypto || window.msCrypto).getRandomValues(bytes);
    return Array.prototype.map
      .call(bytes, function (b) { return ("0" + b.toString(16)).slice(-2); })
      .join("");
  }

  function blogDomain() {
    var meta = document.querySelector('meta[name="zola-base-url"]');
    var url = meta && meta.getAttribute("content") ? meta.getAttribute("content") : location.origin;
    return String(url).replace(/^https?:\/\//i, "").replace(/\/$/, "");
  }

  function build() {
    if (document.getElementById("print-watermark")) return;
    var wm = id16() + "_" + blogDomain();

    var root = document.createElement("div");
    root.id = "print-watermark";
    root.setAttribute("aria-hidden", "true");

    // Trung tâm + lưới chéo lặp lại để khó che/crop.
    var cells = 12;
    for (var i = 0; i < cells; i++) {
      var span = document.createElement("span");
      span.className = "print-watermark__tile";
      span.textContent = wm;
      root.appendChild(span);
    }
    var center = document.createElement("span");
    center.className = "print-watermark__center";
    center.textContent = wm;
    root.appendChild(center);

    (document.body || document.documentElement).appendChild(root);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", build);
  } else {
    build();
  }
})();
