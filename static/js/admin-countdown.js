/**
 * Footer Countdown admin — GitHub auth + POST /cms/footer-countdown
 */
(function () {
  "use strict";

  var SESSION_KEY = "zola-cms-session-id";
  var AUTH_API = (function () {
    var m1 = document.querySelector('meta[name="zola-cms-auth-api"]');
    if (m1 && m1.getAttribute("content")) return m1.getAttribute("content");
    var m2 = document.querySelector('meta[name="zola-visitor-api"]');
    if (m2 && m2.getAttribute("content")) return m2.getAttribute("content");
    return "https://blog-visitor-api.onrender.com";
  })();

  var root = document.getElementById("admin-countdown-app");
  if (!root) return;

  function $(s) { return root.querySelector(s); }
  function $$(s) { return Array.from(root.querySelectorAll(s)); }

  function getSid() {
    try { return sessionStorage.getItem(SESSION_KEY) || ""; }
    catch (e) { return ""; }
  }
  function setSid(s) { try { sessionStorage.setItem(SESSION_KEY, s); } catch (e) {} }
  function clearSid() { try { sessionStorage.removeItem(SESSION_KEY); } catch (e) {} }

  function showView(name) {
    $$("[data-view]").forEach(function (v) { v.hidden = v.dataset.view !== name; });
  }

  function consumeUrlHashSid() {
    if (!location.hash) return;
    var m = location.hash.match(/(?:^|[#&])sid=([A-Za-z0-9_-]+)/);
    if (!m) return;
    setSid(m[1]);
    history.replaceState(null, "", location.pathname + location.search);
  }

  var AUTH_ERR_MSG = {
    access_denied: "Truy cập bị từ chối.",
    invalid_state: "Phiên hết hạn. Thử lại.",
    missing_params: "GitHub callback thiếu tham số.",
    token_exchange_failed: "Lỗi xác thực GitHub.",
    github_unreachable: "Không kết nối được GitHub.",
    github_profile_fetch_failed: "Không đọc được profile GitHub.",
  };

  function showLoginError(code) {
    var el = $("[data-login-error]");
    if (!el) return;
    el.textContent = AUTH_ERR_MSG[code] || ("Lỗi: " + code);
    el.hidden = false;
  }

  async function fetchMe() {
    var sid = getSid();
    if (!sid || !AUTH_API) return null;
    try {
      var res = await fetch(AUTH_API + "/auth/me", {
        headers: { Authorization: "Bearer " + sid },
        credentials: "omit",
        cache: "no-store",
      });
      if (res.status === 401) { clearSid(); return null; }
      if (!res.ok) return null;
      return await res.json();
    } catch (e) { return null; }
  }

  function populateUserBar(user) {
    var bar = $("[data-user-bar]");
    if (!bar) return;
    var av = $("[data-user-avatar]");
    var nm = $("[data-user-name]");
    var em = $("[data-user-email]");
    if (av && user.avatar) { av.src = user.avatar; av.alt = user.username || ""; }
    if (nm) nm.textContent = user.name || user.username || "";
    if (em) em.textContent = user.email || "";
    bar.hidden = false;
  }

  function readForm() {
    return {
      enabled: !!$('[data-field="enabled"]').checked,
      title: ($('[data-field="title"]').value || "").trim(),
      targetDate: $('[data-field="targetDate"]').value || "",
      targetTime: $('[data-field="targetTime"]').value || "00:00",
      timezone: ($('[data-field="timezone"]').value || "Asia/Ho_Chi_Minh").trim(),
      displayMode: $('[data-field="displayMode"]').value || "days",
      footerTextPrefix: ($('[data-field="footerTextPrefix"]').value || "Còn").trim(),
      footerTextSuffix: ($('[data-field="footerTextSuffix"]').value || "nữa là tới").trim(),
    };
  }

  function fillForm(data) {
    var d = data || {};
    $('[data-field="enabled"]').checked = !!d.enabled;
    $('[data-field="title"]').value = d.title || "";
    $('[data-field="targetDate"]').value = d.targetDate || "";
    $('[data-field="targetTime"]').value = d.targetTime || "00:00";
    $('[data-field="timezone"]').value = d.timezone || "Asia/Ho_Chi_Minh";
    $('[data-field="displayMode"]').value = d.displayMode || "days";
    $('[data-field="footerTextPrefix"]').value = d.footerTextPrefix || "Còn";
    $('[data-field="footerTextSuffix"]').value = d.footerTextSuffix || "nữa là tới";
    updatePreview();
  }

  function targetMs(dateStr, timeStr, timeZone) {
    var parts = dateStr.split("-").map(Number);
    var tparts = timeStr.split(":").map(Number);
    var y = parts[0], mo = parts[1], d = parts[2];
    var hh = tparts[0] || 0, mm = tparts[1] || 0;
    var utc = Date.UTC(y, mo - 1, d, hh, mm, 0);
    for (var i = 0; i < 4; i++) {
      var fmt = new Intl.DateTimeFormat("en-US", {
        timeZone: timeZone,
        year: "numeric", month: "2-digit", day: "2-digit",
        hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false,
      });
      var map = {};
      fmt.formatToParts(new Date(utc)).forEach(function (p) {
        if (p.type !== "literal") map[p.type] = p.value;
      });
      var asUtc = Date.UTC(+map.year, +map.month - 1, +map.day, +map.hour, +map.minute, +map.second);
      utc += Date.UTC(y, mo - 1, d, hh, mm, 0) - asUtc;
    }
    return utc;
  }

  function updatePreview() {
    var el = $("[data-preview-text]");
    if (!el) return;
    var cfg = readForm();
    if (!cfg.enabled) {
      el.textContent = "(Đếm ngược đang tắt — footer sẽ ẩn hoàn toàn)";
      return;
    }
    if (!cfg.title || !cfg.targetDate) {
      el.textContent = "Nhập tên sự kiện và ngày mục tiêu để xem trước.";
      return;
    }
    var end = targetMs(cfg.targetDate, cfg.targetTime, cfg.timezone);
    var left = Math.max(0, end - Date.now());
    if (end <= Date.now()) {
      el.innerHTML =
        '<span class="footer-countdown__past">SỰ KIỆN ĐÃ DIỄN RA: ' +
        '<strong class="footer-countdown__title">' + cfg.title + "</strong></span>";
      return;
    }
    var sec = Math.floor(left / 1000);
    var days = Math.floor(sec / 86400);
    var totalHours = Math.floor(sec / 3600);
    var minutes = Math.floor((sec % 3600) / 60);
    function digit(value) {
      return '<span class="footer-countdown__digit">' + value + "</span>";
    }
    el.innerHTML =
      '<span class="footer-countdown__dual">' +
        '<span class="footer-countdown__segment footer-countdown__segment--days">' +
          '<span class="footer-countdown__word">CÒN</span> ' +
          digit(days) + ' <span class="footer-countdown__word">NGÀY</span>' +
        "</span>" +
        '<span class="footer-countdown__sep" aria-hidden="true">|</span>' +
        '<span class="footer-countdown__segment footer-countdown__segment--rest">' +
          '<span class="footer-countdown__word">CÒN</span> ' +
          digit(totalHours) + ' <span class="footer-countdown__word">GIỜ</span> ' +
          digit(minutes) + ' <span class="footer-countdown__word">PHÚT NỮA LÀ TỚI:</span> ' +
          '<strong class="footer-countdown__title">' + cfg.title + "</strong>" +
        "</span>" +
      "</span>";
  }

  var previewTimer = null;
  function schedulePreview() {
    updatePreview();
    if (previewTimer) clearInterval(previewTimer);
    previewTimer = setInterval(updatePreview, 60000);
  }

  var form = $("[data-form='countdown']");
  var statusEl = $("[data-target='save-status']");

  function setStatus(msg, type) {
    if (!statusEl) return;
    statusEl.className = "editor-status editor-status--" + (type || "info");
    statusEl.innerHTML = msg;
  }

  $$("[data-field]").forEach(function (el) {
    el.addEventListener("input", schedulePreview);
    el.addEventListener("change", schedulePreview);
  });

  $("[data-action='github-login']").addEventListener("click", function () {
    if (!AUTH_API) { $("[data-login-hint]").hidden = false; return; }
    location.href = AUTH_API + "/auth/login?return_to=" + encodeURIComponent(location.pathname);
  });

  var logoutBtn = $("[data-action='logout']");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async function () {
      if (!confirm("Đăng xuất?")) return;
      var sid = getSid();
      if (sid && AUTH_API) {
        try {
          await fetch(AUTH_API + "/auth/logout", {
            method: "POST",
            headers: { Authorization: "Bearer " + sid },
            credentials: "omit",
            keepalive: true,
          });
        } catch (e) {}
      }
      clearSid();
      showView("login");
    });
  }

  var backBtn = $("[data-action='back']");
  if (backBtn) backBtn.addEventListener("click", function () { location.href = "/zola/"; });

  async function loadConfig() {
    var sid = getSid();
    if (!sid || !AUTH_API) return;
    try {
      var res = await fetch(AUTH_API + "/cms/footer-countdown", {
        headers: { Authorization: "Bearer " + sid },
        credentials: "omit",
        cache: "no-store",
      });
      if (!res.ok) return;
      var json = await res.json();
      fillForm(json.data || {});
    } catch (e) {}
  }

  if (form) {
    form.addEventListener("submit", async function (e) {
      e.preventDefault();
      var sid = getSid();
      if (!sid || !AUTH_API) {
        setStatus("✗ Phiên hết hạn. Đăng nhập lại.", "error");
        showView("login");
        return;
      }
      var payload = readForm();
      var btn = form.querySelector("button[type='submit']");
      if (btn) btn.disabled = true;
      setStatus("Đang commit lên repo…", "info");
      try {
        var res = await fetch(AUTH_API + "/cms/footer-countdown", {
          method: "POST",
          headers: {
            Authorization: "Bearer " + sid,
            "Content-Type": "application/json",
          },
          credentials: "omit",
          body: JSON.stringify(payload),
        });
        if (res.status === 401) { clearSid(); showView("login"); return; }
        var data = await res.json().catch(function () { return {}; });
        if (!res.ok) {
          setStatus("✗ " + (data.detail || "API lỗi"), "error");
          return;
        }
        var html = "✓ Đã lưu cấu hình countdown. Deploy ETA: " + (data.deploy_eta || "~2 phút");
        if (data.commit_url) {
          html += ' · <a href="' + data.commit_url + '" target="_blank" rel="noopener">Xem commit</a>';
        }
        setStatus(html, "success");
      } catch (err) {
        setStatus("✗ Lỗi mạng: " + err.message, "error");
      } finally {
        if (btn) btn.disabled = false;
      }
    });
  }

  async function init() {
    consumeUrlHashSid();
    var p = new URLSearchParams(location.search);
    var err = p.get("auth_error");
    if (err) showLoginError(err);
    if (!AUTH_API) {
      $("[data-login-hint]").hidden = false;
      showView("login");
      return;
    }
    var user = await fetchMe();
    if (user) {
      populateUserBar(user);
      showView("main");
      await loadConfig();
      schedulePreview();
    } else {
      showView("login");
    }
  }
  init();
})();