/**
 * OTP gate cho link Admin → /editor/.
 *
 * Dùng SHA-256 hash thay vì plaintext value — source KHÔNG còn chứa mã raw,
 * chỉ giữ hash 64 hex chars. User nhập value, JS hash qua Web Crypto API
 * và so sánh với OTP_HASH.
 *
 * LƯU Ý: Đây KHÔNG phải bảo mật thật — 4 chữ số có 10000 tổ hợp,
 * brute-force hash trivially trong <1s. Mục đích duy nhất là tránh visitor
 * vô tình click vào trang CMS. Tầng bảo vệ thật vẫn là PAT GitHub.
 */
(function () {
  const OTP_HASH = "78c72f67941a420cd4e5ee9fdabcaeaba6d72f16160915085f9802220fd83799";
  const triggers = document.querySelectorAll("[data-auth-trigger]");
  if (!triggers.length) return;

  async function sha256Hex(str) {
    const buf = new TextEncoder().encode(String(str || ""));
    const hash = await crypto.subtle.digest("SHA-256", buf);
    return Array.from(new Uint8Array(hash))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
  }

  triggers.forEach((el) => {
    el.addEventListener("click", async (e) => {
      e.preventDefault();
      const code = window.prompt("Nhập mã truy cập:");
      if (code === null) return; // user bấm Cancel
      const hash = await sha256Hex(code);
      if (hash === OTP_HASH) {
        window.location.href = el.getAttribute("href") || "/";
      } else {
        alert("Sai mã!");
      }
    });
  });
})();
