/**
 * Visitor Counter — fetch backend API, display in #visitor-count.
 *
 * URL được Zola bake từ config.extra.visitor_api_url vào
 * <meta name="zola-visitor-api">. Nếu config chưa set → script silent
 * skip, không có gì xảy ra.
 *
 * Performance:
 *   - Script load qua defer → KHÔNG block HTML parse
 *   - requestIdleCallback → fetch chạy lúc browser idle (sau LCP)
 *   - Promise.all → POST track + GET stats song song
 *   - keepalive: true → request hoàn thành ngay cả khi user điều hướng đi
 *   - Silent fail nếu API down → KHÔNG phá UX
 *
 * Adblock workaround:
 *   - Tên file 'visitor-counter.js' không match common blocklist (như
 *     'analytics', 'tracker'). Nếu bị block, đổi tên file.
 *   - Không gọi tới domain known-tracker (chỉ gọi API riêng của bạn)
 */
(function () {
  "use strict";

  // URL backend lấy từ meta tag (Zola bake build-time)
  const meta = document.querySelector('meta[name="zola-visitor-api"]');
  const apiUrl = (meta && meta.getAttribute("content")) || "";
  if (!apiUrl) return; // chưa configure → no-op

  const el = document.getElementById("visitor-count");
  if (!el) return; // không có thẻ display → no-op

  // Format số với dấu phẩy ngăn cách hàng nghìn theo locale VN
  function fmt(n) {
    try { return Number(n).toLocaleString("vi-VN"); }
    catch (e) { return String(n); }
  }

  // Schedule sau khi browser idle để không cạnh tranh với critical render path
  function schedule(cb) {
    if (typeof requestIdleCallback === "function") {
      requestIdleCallback(cb, { timeout: 2500 });
    } else {
      setTimeout(cb, 200);
    }
  }

  async function trackAndDisplay() {
    try {
      // Gửi POST track + GET stats song song để giảm latency.
      // keepalive: true → request hoàn thành dù user navigate khỏi page.
      const [, statsRes] = await Promise.all([
        fetch(apiUrl + "/track", {
          method: "POST",
          keepalive: true,
          credentials: "omit",
          cache: "no-store",
        }),
        fetch(apiUrl + "/stats", {
          credentials: "omit",
          cache: "no-store",
        }),
      ]);

      if (!statsRes.ok) throw new Error("HTTP " + statsRes.status);
      const data = await statsRes.json();
      if (typeof data.count === "number") {
        el.textContent = fmt(data.count);
      }
    } catch (e) {
      // Silent fail — giữ placeholder '—', không phá UI
      // (cũng KHÔNG console.error để không làm bẩn DevTools của visitor)
      el.textContent = "—";
    }
  }

  schedule(trackAndDisplay);
})();
