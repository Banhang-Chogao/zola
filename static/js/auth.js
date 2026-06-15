/**
 * OTP gate cho link Admin → /editor/.
 *
 * LƯU Ý: Đây KHÔNG phải bảo mật thật — file này, mã OTP, và mọi logic đều
 * client-side, ai mở DevTools là thấy. Mục đích duy nhất là tránh visitor
 * vô tình click vào trang CMS.
 *
 * Tầng bảo vệ thật của CMS:
 *   - editor.js yêu cầu GitHub PAT để gọi REST API
 *   - Không có PAT thì không save/sửa/xoá được bài viết
 *
 * Nếu cần bảo mật thật, deploy CMS sau auth proxy (Cloudflare Access,
 * GitHub Pages private, ...) chứ không phải client-side OTP.
 */
(function () {
  const OTP = "0512";
  const triggers = document.querySelectorAll("[data-auth-trigger]");
  if (!triggers.length) return;

  triggers.forEach((el) => {
    el.addEventListener("click", (e) => {
      e.preventDefault();
      const code = window.prompt("Nhập mã truy cập:");
      if (code === null) return; // user bấm Cancel
      if (code === OTP) {
        window.location.href = el.getAttribute("href") || "/";
      } else {
        alert("Sai mã!");
      }
    });
  });
})();
