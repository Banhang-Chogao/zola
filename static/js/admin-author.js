/**
 * Author Management page logic.
 * Reuse pattern auth của /editor/, /baochi/:
 *   - GET sid từ sessionStorage
 *   - validate qua /auth/me
 *   - Form: avatar file + name/url/bio text → POST multipart /cms/author
 */
(function () {
  "use strict";

  const SESSION_KEY = "zola-cms-session-id";
  // Đọc URL backend qua VIPZone meta, fallback production để FE work kể cả khi Tera build issue.
  const AUTH_API = (function () {
    const m1 = document.querySelector('meta[name="vipzone-auth-api"]');
    if (m1 && m1.getAttribute("content")) return m1.getAttribute("content");
    return "https://blog-vipzone-api.onrender.com";
  })();

  const root = document.getElementById("admin-author-app");
  if (!root) return;

  function $(s) { return root.querySelector(s); }
  function $$(s) { return Array.from(root.querySelectorAll(s)); }

  function getSid() {
    try { return sessionStorage.getItem(SESSION_KEY) || ""; }
    catch (e) { return ""; }
  }
  function setSid(s) { try { sessionStorage.setItem(SESSION_KEY, s); localStorage.setItem(SESSION_KEY, s); } catch (e) {} }
  function clearSid() { try { sessionStorage.removeItem(SESSION_KEY); localStorage.removeItem(SESSION_KEY); } catch (e) {} }

  function showView(name) {
    $$("[data-view]").forEach(function (v) { v.hidden = v.dataset.view !== name; });
  }

  function consumeUrlHashSid() {
    if (!location.hash) return;
    const m = location.hash.match(/(?:^|[#&])sid=([A-Za-z0-9_-]+)/);
    if (!m) return;
    setSid(m[1]);
    history.replaceState(null, "", location.pathname + location.search);
  }
  function consumeUrlAuthError() {
    const p = new URLSearchParams(location.search);
    const e = p.get("auth_error");
    if (!e) return null;
    p.delete("auth_error");
    history.replaceState(null, "", location.pathname + (p.toString() ? "?" + p.toString() : ""));
    return e;
  }

  const AUTH_ERR_MSG = {
    access_denied: "Truy cập bị từ chối: Bạn không có quyền quản trị blog này.",
    invalid_state: "Phiên đăng nhập hết hạn. Thử lại.",
    missing_params: "GitHub callback thiếu tham số.",
    token_exchange_failed: "Lỗi xác thực GitHub.",
    github_unreachable: "Không kết nối được GitHub.",
    github_profile_fetch_failed: "Không đọc được profile GitHub.",
  };

  function showLoginError(code) {
    const el = $("[data-login-error]");
    if (!el) return;
    el.textContent = AUTH_ERR_MSG[code] || ("Lỗi: " + code);
    el.hidden = false;
  }

  async function fetchMe() {
    const sid = getSid();
    if (!sid || !AUTH_API) return null;
    try {
      const res = await fetch(AUTH_API + "/auth/me", {
        headers: { "Authorization": "Bearer " + sid },
        credentials: "omit",
        cache: "no-store",
      });
      if (res.status === 401) { clearSid(); return null; }
      if (!res.ok) return null;
      return await res.json();
    } catch (e) { return null; }
  }

  function populateUserBar(user) {
    const bar = $("[data-user-bar]");
    if (!bar) return;
    const av = $("[data-user-avatar]");
    const nm = $("[data-user-name]");
    const em = $("[data-user-email]");
    if (av && user.avatar) { av.src = user.avatar; av.alt = user.username || ""; }
    if (nm) nm.textContent = user.name || user.username || "";
    if (em) em.textContent = user.email || "";
    bar.hidden = false;
  }

  // ============= LOGIN / LOGOUT =============
  $("[data-action='github-login']").addEventListener("click", function () {
    if (!AUTH_API) { $("[data-login-hint]").hidden = false; return; }
    location.href = AUTH_API + "/auth/login?return_to=" + encodeURIComponent(location.pathname);
  });

  const logoutBtn = $("[data-action='logout']");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async function () {
      if (!confirm("Đăng xuất?")) return;
      const sid = getSid();
      if (sid && AUTH_API) {
        try {
          await fetch(AUTH_API + "/auth/logout", {
            method: "POST",
            headers: { "Authorization": "Bearer " + sid },
            credentials: "omit",
            keepalive: true,
          });
        } catch (e) {}
      }
      clearSid();
      $("[data-user-bar]").hidden = true;
      showView("login");
    });
  }

  const backBtn = $("[data-action='back']");
  if (backBtn) backBtn.addEventListener("click", function () {
    location.href = "/zola/";
  });

  // ============= FORM HANDLING =============
  const form           = $("[data-form='author']");
  const avatarInput    = $("[data-avatar-input]");
  const avatarPreview  = $("[data-avatar-preview]");
  const avatarEmpty    = $("[data-avatar-empty]");
  const bioInput       = form ? form.bio : null;
  const bioCount       = $("[data-bio-count]");
  const statusEl       = $("[data-target='save-status']");

  function setStatus(msg, type) {
    if (!statusEl) return;
    statusEl.className = "editor-status editor-status--" + (type || "info");
    statusEl.innerHTML = msg;
  }
  function clearStatus() {
    if (statusEl) { statusEl.className = "editor-status"; statusEl.textContent = ""; }
  }

  function updateBioCount() {
    if (bioInput && bioCount) {
      bioCount.textContent = bioInput.value.length + " / 5000";
    }
  }
  if (bioInput) bioInput.addEventListener("input", updateBioCount);

  if (avatarInput) {
    avatarInput.addEventListener("change", function () {
      const f = avatarInput.files && avatarInput.files[0];
      if (!f) return;
      if (f.size > 5 * 1024 * 1024) {
        setStatus("✗ Ảnh quá lớn (max 5MB). Resize trước khi upload.", "error");
        avatarInput.value = "";
        return;
      }
      clearStatus();
      const reader = new FileReader();
      reader.onload = function (e) {
        avatarPreview.src = e.target.result;
        avatarPreview.style.display = "block";
        if (avatarEmpty) avatarEmpty.style.display = "none";
      };
      reader.readAsDataURL(f);
    });
  }

  async function loadAuthorData() {
    const sid = getSid();
    if (!sid || !AUTH_API) return;
    try {
      const res = await fetch(AUTH_API + "/cms/author", {
        headers: { "Authorization": "Bearer " + sid },
        credentials: "omit",
        cache: "no-store",
      });
      if (!res.ok) return;
      const json = await res.json();
      const d = json.data || {};
      if (form) {
        form.name.value = d.name || "";
        form.url.value  = d.url  || "";
        form.bio.value  = d.bio  || "";
      }
      updateBioCount();
      // Preview existing avatar
      if (d.avatar_path) {
        const url = d.avatar_path.startsWith("http")
          ? d.avatar_path
          : ("/zola" + d.avatar_path);
        // Cache-bust qua timestamp để FE thấy ngay sau upload
        avatarPreview.src = url + "?t=" + Date.now();
        avatarPreview.style.display = "block";
        if (avatarEmpty) avatarEmpty.style.display = "none";
      }
    } catch (e) { /* silent */ }
  }

  if (form) {
    form.addEventListener("submit", async function (e) {
      e.preventDefault();
      const sid = getSid();
      if (!sid || !AUTH_API) {
        setStatus("✗ Phiên hết hạn. Đăng nhập lại.", "error");
        showView("login");
        return;
      }

      const fd = new FormData();
      const f = avatarInput.files && avatarInput.files[0];
      if (f) fd.append("avatar", f);
      if (form.name.value.trim()) fd.append("name", form.name.value.trim());
      if (form.url.value.trim())  fd.append("url",  form.url.value.trim());
      if (form.bio.value.trim())  fd.append("bio",  form.bio.value.trim());

      // Submit lock
      const submitBtn = form.querySelector("button[type='submit']");
      if (submitBtn) submitBtn.disabled = true;
      setStatus("Đang upload + commit lên repo…", "info");

      try {
        const res = await fetch(AUTH_API + "/cms/author", {
          method: "POST",
          headers: { "Authorization": "Bearer " + sid },
          credentials: "omit",
          body: fd,
        });
        if (res.status === 401) {
          clearSid();
          showView("login");
          return;
        }
        const data = await res.json().catch(function () { return {}; });
        if (!res.ok) {
          setStatus("✗ " + (data.detail || "API lỗi"), "error");
          return;
        }
        let html = "✓ ";
        if (data.updated_avatar && data.updated_meta) html += "Đã cập nhật avatar + thông tin";
        else if (data.updated_avatar) html += "Đã cập nhật avatar";
        else html += "Đã cập nhật thông tin";
        html += ". Deploy ETA: " + (data.deploy_eta || "~2 phút");
        if (data.commits && data.commits.length) {
          const links = data.commits.map(function (c) {
            return c.url
              ? '<a href="' + c.url + '" target="_blank" rel="noopener">' + c.type + '</a>'
              : c.type;
          }).join(", ");
          html += " · Commits: " + links;
        }
        setStatus(html, "success");
        // Reset avatar input (file consumed)
        avatarInput.value = "";
      } catch (err) {
        setStatus("✗ Lỗi mạng: " + err.message, "error");
      } finally {
        if (submitBtn) submitBtn.disabled = false;
      }
    });
  }

  // ============= GISCUS SETUP =============
  const giscusBtn = $("[data-action='giscus-fetch']");
  const giscusOut = $("[data-giscus-out]");
  if (giscusBtn && giscusOut) {
    giscusBtn.addEventListener("click", async function () {
      const sid = getSid();
      if (!sid) { alert("Đăng nhập trước"); return; }
      giscusBtn.disabled = true;
      giscusOut.hidden = false;
      giscusOut.textContent = "Đang query GraphQL...";
      try {
        const res = await fetch(AUTH_API + "/cms/giscus/setup", {
          headers: { "Authorization": "Bearer " + sid },
          credentials: "omit",
        });
        const data = await res.json().catch(function () { return {}; });
        if (!res.ok) {
          giscusOut.textContent = "❌ " + (data.detail || "Lỗi: kiểm tra Discussions đã bật + Giscus app installed chưa.");
          return;
        }
        const s = data.suggested || {};
        const snippet =
          "[extra.giscus]\n" +
          'repo        = "Banhang-Chogao/zola"\n' +
          'repo_id     = "' + (s.repo_id || "") + '"\n' +
          'category    = "' + (s.category || "General") + '"\n' +
          'category_id = "' + (s.category_id || "") + '"';
        giscusOut.textContent = snippet + "\n\n# Copy block trên paste vào config.toml + push";
      } catch (e) {
        giscusOut.textContent = "❌ Network error: " + e.message;
      } finally {
        giscusBtn.disabled = false;
      }
    });
  }

  // ============= INIT =============
  async function init() {
    consumeUrlHashSid();
    const err = consumeUrlAuthError();
    if (err) showLoginError(err);
    if (!AUTH_API) {
      $("[data-login-hint]").hidden = false;
      showView("login");
      return;
    }
    const user = await fetchMe();
    if (user) {
      populateUserBar(user);
      showView("main");
      await loadAuthorData();
    } else {
      showView("login");
    }
  }
  init();
})();
