/* View switcher — nút chuyển "bản desktop ↔ bản mobile" trên trang chủ.
 *
 * Cách hoạt động: trên điện thoại, đổi thẻ <meta name="viewport"> sang
 * width=1024 buộc trình duyệt render layout desktop (thu nhỏ vừa màn hình).
 * Bấm lại → trả về width=device-width (bản mobile thật). Lựa chọn lưu trong
 * localStorage (key 'seomoney-view-mode') nên giữ nguyên khi chuyển trang —
 * base.html áp dụng sớm trước paint để tránh nháy layout.
 *
 * Không đụng CSS desktop global / media query mobile: chỉ thay viewport meta.
 */
(function () {
  'use strict';

  var STORAGE_KEY = 'seomoney-view-mode';
  var VIEWPORT_DESKTOP = 'width=1024';
  var VIEWPORT_MOBILE = 'width=device-width, initial-scale=1, viewport-fit=cover';

  function getMeta() {
    return document.querySelector('meta[name="viewport"]');
  }

  function readMode() {
    try {
      return localStorage.getItem(STORAGE_KEY) === 'desktop' ? 'desktop' : 'mobile';
    } catch (e) {
      return 'mobile';
    }
  }

  function saveMode(mode) {
    try {
      localStorage.setItem(STORAGE_KEY, mode);
    } catch (e) { /* private mode / quota — bỏ qua */ }
  }

  function applyMode(mode) {
    var meta = getMeta();
    if (meta) {
      meta.setAttribute('content', mode === 'desktop' ? VIEWPORT_DESKTOP : VIEWPORT_MOBILE);
    }
  }

  function renderButton(btn, mode) {
    var icon = btn.querySelector('.view-switcher__icon');
    var label = btn.querySelector('.view-switcher__label');
    if (mode === 'desktop') {
      // Đang ở bản desktop → nút mời quay lại bản mobile
      if (icon) icon.textContent = '📱';
      if (label) label.textContent = 'Xem bản điện thoại';
      btn.setAttribute('aria-pressed', 'true');
      btn.setAttribute('title', 'Đang xem bản desktop — bấm để về bản điện thoại');
    } else {
      if (icon) icon.textContent = '🖥️';
      if (label) label.textContent = 'Xem bản desktop';
      btn.setAttribute('aria-pressed', 'false');
      btn.setAttribute('title', 'Bấm để xem giao diện desktop trên điện thoại');
    }
  }

  function init() {
    var btn = document.querySelector('[data-view-toggle]');
    if (!btn) return;

    var mode = readMode();
    applyMode(mode);          // đồng bộ phòng trường hợp meta chưa được set sớm
    renderButton(btn, mode);

    btn.addEventListener('click', function () {
      mode = mode === 'desktop' ? 'mobile' : 'desktop';
      saveMode(mode);
      applyMode(mode);
      renderButton(btn, mode);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
