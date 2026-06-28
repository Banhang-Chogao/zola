/**
 * Mini CMS — viết bài blog, đẩy file .md vào repo GitHub qua REST API.
 *
 * Authentication: GitHub/Google OAuth qua backend FastAPI (services/vipzone).
 * Phiên = cookie HttpOnly `zola_cms_sid` (bền, Max-Age 30 ngày) + sid opaque
 * trong localStorage làm Bearer fallback. Không lưu OAuth token nào ở client.
 *
 * Workflow:
 *   1. User login bằng OAuth (GitHub/Google)
 *   2. List bài viết (GET /contents/content/)
 *   3. Tạo/sửa bài → PUT /contents/content/{slug}.md với base64 content
 *   4. GitHub Actions auto-build + deploy site sau ~1 phút
 */
(function () {
  const OWNER = "Banhang-Chogao";
  const REPO = "zola";
  const BRANCH = "main";
  // Bài viết sống trong content/posting/ (section đã config sort + paginate).
  // Trang chủ (/) và section /posting/ đều đọc từ đây.
  const CONTENT_DIR = "content/posting";
  const API = "https://api.github.com";

  /* ============= AUTH (GitHub OAuth via FastAPI backend) =============
     OAuth flow (replaces OTP):
       1. User click "Đăng nhập GitHub" → redirect BACKEND/auth/login
       2. GitHub OAuth → BACKEND callback → check email white-list
       3. Backend set cookie HttpOnly + redirect /editor/#sid=... → JS đọc hash
          → lưu localStorage (Bearer fallback)
       4. /auth/me validate session mỗi page load (credentials:include → cookie)
       5. Save bài = download .md (DRAFT-ONLY mode giữ nguyên từ PR #34)

     Security:
       - sid là opaque random, KHÔNG carry info (KHÔNG phải OAuth token)
       - access_token GitHub / id_token Google giữ server-side, KHÔNG về client
       - cookie HttpOnly = nguồn phiên bền (Max-Age = SESSION_TTL, mặc định 30d)
       - localStorage sống qua đóng tab + xoá static cache; chỉ mất khi xoá
         cookie/site data → khi đó logout là ĐÚNG kỳ vọng
       - White-list email check server-side, client KHÔNG bypass được */

  const SESSION_KEY = "zola-cms-session-id";
  // Persistence model (fix: "xoá cache xong bị bắt đăng nhập lại"):
  //   - Nguồn phiên BỀN VỮNG là cookie HttpOnly `zola_cms_sid` do backend set
  //     (Secure + SameSite=None, Max-Age = SESSION_TTL). Mọi fetch dùng
  //     credentials:"include" để cookie tự gửi → còn cookie là còn đăng nhập,
  //     kể cả khi xoá "cached images/files" hay đóng/mở lại tab.
  //   - sid cũng lưu localStorage làm Bearer fallback cho trình duyệt CHẶN
  //     cookie bên thứ ba (Safari ITP, Firefox). localStorage sống qua đóng tab
  //     + xoá static cache; CHỈ mất khi user "clear cookies / site data" → khi
  //     đó logout là ĐÚNG kỳ vọng. (Trước đây dùng sessionStorage → mất ngay
  //     khi đóng tab nên hay bị bắt login lại.)
  //   - sid là opaque, KHÔNG phải OAuth token; access_token GitHub luôn ở
  //     server-side. Không lưu OAuth token nào trong trình duyệt.
  // Fallback chain: meta cms-auth → meta visitor-api → hardcode prod URL
  const AUTH_API = (function () {
    const m1 = document.querySelector('meta[name="zola-cms-auth-api"]');
    if (m1 && m1.getAttribute("content")) return m1.getAttribute("content");
    const m2 = document.querySelector('meta[name="zola-visitor-api"]');
    if (m2 && m2.getAttribute("content")) return m2.getAttribute("content");
    return "https://blog-vipzone-api.onrender.com";
  })();

  let currentUser = null; // { email, username, name, avatar }

  function getSid() {
    try {
      // localStorage là nguồn chính (bền qua đóng tab). Migrate sid cũ còn kẹt
      // trong sessionStorage (phiên trước bản vá này) sang localStorage 1 lần.
      let sid = localStorage.getItem(SESSION_KEY) || "";
      if (!sid) {
        const legacy = sessionStorage.getItem(SESSION_KEY) || "";
        if (legacy) {
          localStorage.setItem(SESSION_KEY, legacy);
          sessionStorage.removeItem(SESSION_KEY);
          sid = legacy;
        }
      }
      return sid;
    } catch (e) { return ""; }
  }
  function setSid(sid) {
    try { localStorage.setItem(SESSION_KEY, sid); } catch (e) {}
    try { sessionStorage.removeItem(SESSION_KEY); } catch (e) {}
  }
  function clearSid() {
    try { localStorage.removeItem(SESSION_KEY); } catch (e) {}
    try { sessionStorage.removeItem(SESSION_KEY); } catch (e) {}
  }

  // Đọc #sid=... từ URL fragment sau OAuth callback redirect.
  // Hash KHÔNG được gửi server → an toàn hơn query string với referer leak.
  function consumeUrlHashSid() {
    if (!location.hash) return;
    const m = location.hash.match(/(?:^|[#&])sid=([A-Za-z0-9_-]+)/);
    if (!m) return;
    setSid(m[1]);
    // Xoá hash khỏi URL bar (không reload, không history entry)
    history.replaceState(null, "", location.pathname + location.search);
  }

  // Đọc ?auth_error=... từ query (backend redirect khi denied / fail)
  function consumeUrlAuthError() {
    const params = new URLSearchParams(location.search);
    const err = params.get("auth_error");
    if (!err) return null;
    params.delete("auth_error");
    const newQs = params.toString();
    history.replaceState(null, "", location.pathname + (newQs ? "?" + newQs : ""));
    return err;
  }

  // Xác thực phiên. Thử Bearer (nếu có sid localStorage) TRƯỚC; nếu thiếu sid
  // hoặc Bearer 401 thì thử lại CHỈ bằng cookie HttpOnly (credentials:include)
  // → còn cookie là còn đăng nhập dù localStorage trống (vd vừa xoá static cache
  // ở trình duyệt cho cookie sống nhưng không cho JS đọc sid). Network fail →
  // trả "unknown" để KHÔNG logout phá UI (xem init()).
  async function meRequest(useBearer) {
    const opts = { credentials: "include", cache: "no-store", headers: {} };
    if (useBearer) {
      const sid = getSid();
      if (!sid) return { status: 0 };
      opts.headers["Authorization"] = "Bearer " + sid;
    }
    try {
      const res = await fetch(AUTH_API + "/auth/me", opts);
      if (!res.ok) {
        // Log non-200 auth responses for debugging (but not in console to avoid overwhelming user)
        if (res.status === 401) {
          // Session expired or invalid — expected when not logged in
        } else if (res.status >= 500) {
          // Backend error — transient, should retry
          console.warn("[CMS] /auth/me backend error:", res.status);
        }
        return { status: res.status };
      }
      return { status: 200, user: await res.json() };
    } catch (e) {
      console.warn("[CMS] /auth/me fetch failed (likely CORS or network):", e.message);
      return { status: -1 }; // network/CORS fail → transient, KHÔNG coi là logout
    }
  }

  async function fetchMe() {
    if (!AUTH_API) return null;
    const sid = getSid();
    // 1. Bearer trước (nếu có sid). 2. Cookie-only fallback.
    let r = sid ? await meRequest(true) : { status: 0 };
    if (r.status === 200) return r.user;
    // Bearer thiếu / 401 / lỗi → thử cookie HttpOnly.
    // NHƯNG: nếu network error (-1), KHÔNG retry, chỉ return null để hiện lỗi.
    if (r.status === -1) {
      // Network/CORS error on bearer attempt — backend might be down/slow.
      // Show error instead of redirecting to login (which could cause loop).
      console.warn("[CMS] Backend unreachable (network/CORS). Trying cookie fallback...");
      const c = await meRequest(false);
      if (c.status === 200) return c.user;
      if (c.status === -1) {
        // Both attempts failed due to network → report backend error, don't show login.
        return { __error: "backend_unreachable" };
      }
      return null;
    }
    if (r.status === 0 || r.status === 401) {
      const c = await meRequest(false);
      if (c.status === 200) return c.user;
      // Chỉ clear sid khi backend KHẲNG ĐỊNH 401 (cả Bearer lẫn cookie đều fail).
      if (c.status === 401 && sid) clearSid();
    }
    return null;
  }

  // Phiên hết hạn GIỮA lúc đang soạn (save/publish/list trả 401): lưu bản nháp
  // hiện tại vào localStorage TRƯỚC khi đẩy về màn login, rồi báo rõ cho user.
  // Draft được khôi phục qua draft-recovery banner sau khi đăng nhập lại.
  function handleSessionExpired() {
    try { if (typeof autosaveDraft === "function") autosaveDraft(); } catch (e) {}
    clearSid();
    alert(
      "Phiên đăng nhập đã hết hạn. Bản nháp đã được lưu tạm trước khi đăng nhập lại."
    );
    showView("login");
  }

  async function logoutRemote() {
    const sid = getSid();
    if (!sid || !AUTH_API) { clearSid(); return; }
    try {
      await fetch(AUTH_API + "/auth/logout", {
        method: "POST",
        headers: { "Authorization": "Bearer " + sid },
        credentials: "include",
        keepalive: true,
      });
    } catch (e) { /* network fail OK — session client-side đã clear */ }
    clearSid();
  }

  const AUTH_ERROR_MESSAGES = {
    access_denied:                "Truy cập bị từ chối: Bạn không có quyền quản trị blog này.",
    invalid_state:                "Phiên đăng nhập hết hạn. Vui lòng thử lại.",
    missing_params:               "Callback thiếu tham số. Thử lại.",
    token_exchange_failed:        "Lỗi xác thực. Thử lại sau.",
    github_unreachable:           "Không kết nối được GitHub. Kiểm tra mạng.",
    github_profile_fetch_failed:  "Không đọc được profile GitHub. Thử lại.",
    github_disabled:              "Đăng nhập GitHub đang tắt. Dùng Google.",
    // ----- Google OAuth -----
    google_disabled:              "Đăng nhập Google đang tắt.",
    google_not_configured:        "Backend chưa cấu hình Google OAuth. Liên hệ admin.",
    google_unreachable:           "Không kết nối được Google. Kiểm tra mạng.",
    google_consent_denied:        "Bạn đã huỷ cấp quyền Google. Thử lại nếu muốn đăng nhập.",
    id_token_invalid:             "Không xác thực được Google id_token. Thử lại.",
    id_token_aud_mismatch:        "Google id_token sai client. Liên hệ admin.",
    id_token_iss_mismatch:        "Google id_token sai nguồn phát hành. Liên hệ admin.",
    email_missing:                "Tài khoản Google không có email. Dùng tài khoản khác.",
    email_not_verified:           "Email Google chưa được xác minh. Xác minh rồi thử lại.",
  };

  function showLoginError(code) {
    const el = $("[data-login-error]");
    if (!el) return;
    el.dataset.code = code || "";
    el.textContent = AUTH_ERROR_MESSAGES[code] || ("Lỗi xác thực: " + code);
    el.hidden = false;
  }

  // Dismiss a stale provider warning (e.g. an old ?auth_error=google_disabled)
  // once /auth/config proves that provider is actually available. Only clears the
  // listed codes so genuine errors (access_denied, invalid_state…) stay visible.
  function clearLoginErrorCodes(codes) {
    const el = $("[data-login-error]");
    if (!el || el.hidden) return;
    if (codes.indexOf(el.dataset.code || "") === -1) return;
    el.hidden = true;
    el.textContent = "";
    el.dataset.code = "";
  }

  function showLoginHint() {
    const el = $("[data-login-hint]");
    if (el) el.hidden = false;
  }

  function populateUserBar(user) {
    const bar = $("[data-user-bar]");
    if (!bar) return;
    const avatar = $("[data-user-avatar]");
    const name = $("[data-user-name]");
    const email = $("[data-user-email]");
    if (avatar && user.avatar) {
      avatar.src = user.avatar;
      avatar.alt = user.username || user.name || "Avatar";
    }
    if (name) name.textContent = user.name || user.username || "";
    if (email) email.textContent = user.email || "";
  }

  function showToast(message, type) {
    const host = $("[data-toast-host]");
    if (!host) return;
    const el = document.createElement("div");
    el.className = "ecms-toast ecms-toast--" + (type || "info");
    el.setAttribute("role", "status");
    el.textContent = message;
    host.appendChild(el);
    window.setTimeout(function () {
      el.style.opacity = "0";
      el.style.transition = "opacity 0.2s ease";
      window.setTimeout(function () { el.remove(); }, 220);
    }, 3800);
  }

  function postStatus(p) {
    if (p.draft) return "draft";
    if (p.publish_at) return "scheduled";
    return "published";
  }

  function statusLabel(p) {
    const s = postStatus(p);
    if (s === "draft") return "Bản nháp";
    if (s === "scheduled") return "Lịch đăng";
    return "Đã xuất bản";
  }

  function resolveThumbUrl(post) {
    const raw = (post.thumbnail || post.image || "").trim();
    if (raw && !/\/img\/placeholder\//.test(raw)) {
      if (/^https?:\/\//i.test(raw)) return raw;
      const base = location.pathname.replace(/\/editor\/?$/, "").replace(/\/$/, "");
      if (raw.startsWith("/")) return location.origin + base + raw;
      return location.origin + base + "/" + raw.replace(/^\//, "");
    }
    return PLACEHOLDER_THUMB;
  }

  function formatDisplayDate(iso) {
    if (!iso) return "—";
    try {
      if (window.DateTimeFormat && window.DateTimeFormat.formatDate) {
        return window.DateTimeFormat.formatDate(iso);
      }
    } catch (e) { /* fallback */ }
    const d = String(iso).slice(0, 10);
    const p = d.split("-");
    if (p.length === 3) return p[2] + "/" + p[1] + "/" + p[0];
    return d;
  }

  const root = document.getElementById("editor-app");
  if (!root) return;

  // ============= STATE & UTIL =============
  let state = {
    posts: [],
    bakeMetadata: [],
    editing: null,
    filter: {
      query: "",
      sort: "date-desc",
      placement: "",
      status: "all",
      category: "",
      flags: { sticky: false, featured: false, hasThumb: false, premium: false },
      preset: "",
    },
    pagination: { page: 1, pageSize: 6 },
    drawerSlug: null,
    drawerLoading: false,
  };

  const GOOGLE_CSE_CX = (function () {
    const m = document.querySelector('meta[name="editor-google-cse-cx"]');
    return m && m.getAttribute("content") ? m.getAttribute("content") : "";
  })();

  const PLACEHOLDER_THUMB = (function () {
    const base = document.querySelector('link[rel="canonical"]');
    const origin = base ? new URL(base.href).origin : location.origin;
    const path = location.pathname.replace(/\/editor\/?$/, "");
    return origin + path + "/img/placeholder/placeholder.svg";
  })();

  function $(sel, parent) { return (parent || root).querySelector(sel); }
  function $$(sel, parent) { return Array.from((parent || root).querySelectorAll(sel)); }

  function showView(name) {
    $$("[data-view]").forEach((v) => v.hidden = v.dataset.view !== name);
  }

  function setStatus(el, msg, type) {
    if (typeof el === "string") el = $("[data-target='" + el + "']") || $("[data-status]");
    if (!el) return;
    el.className = "editor-status editor-status--" + (type || "info");
    el.textContent = msg;
  }

  function escapeHtml(s) {
    return String(s || "").replace(/[&<>"']/g, (c) => ({
      "&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"
    }[c]));
  }

  function slugify(s) {
    return String(s).toLowerCase()
      .normalize("NFD").replace(/[̀-ͯ]/g, "")
      .replace(/đ/g, "d")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "");
  }

  function todayIso() {
    const d = new Date();
    return d.toISOString().split("T")[0];
  }

  // Ngày hôm nay theo giờ Việt Nam (GMT+7), dạng YYYY-MM-DD.
  function todayIsoVN() {
    try {
      return new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Ho_Chi_Minh" });
    } catch (e) {
      return todayIso();
    }
  }

  // Thời điểm hiện tại theo giờ Việt Nam, ISO8601 có offset +07:00
  // (vd 2026-06-27T14:30:00+07:00). GMT+7 không có DST nên offset luôn cố định.
  function nowIsoVN() {
    try {
      const parts = new Intl.DateTimeFormat("en-CA", {
        timeZone: "Asia/Ho_Chi_Minh",
        year: "numeric", month: "2-digit", day: "2-digit",
        hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false,
      }).formatToParts(new Date());
      const get = (t) => ((parts.find((p) => p.type === t) || {}).value || "00");
      let hour = get("hour");
      if (hour === "24") hour = "00"; // vài môi trường trả "24" cho nửa đêm
      return get("year") + "-" + get("month") + "-" + get("day") +
        "T" + hour + ":" + get("minute") + ":" + get("second") + "+07:00";
    } catch (e) {
      return todayIsoVN();
    }
  }

  // Tính giá trị `date` frontmatter sao cho hiển thị THỜI GIAN THỰC TẾ, không phải 00:00 giả:
  //  - Giữ nguyên timestamp gốc nếu user không đổi ngày (không ghi đè giờ đã ghi).
  //  - Ngày = hôm nay (GMT+7) mà chưa có giờ → đóng dấu giờ thực tại.
  //  - Ngày khác (quá khứ/tương lai do user chọn) → giữ date-only, KHÔNG bịa giờ.
  function resolvePublishDate(formDate, originalDate) {
    const dateOnly = String(formDate || "").slice(0, 10);
    if (!dateOnly) return formDate;
    if (originalDate && String(originalDate).slice(0, 10) === dateOnly) {
      return originalDate; // bảo toàn giờ gốc của bài
    }
    if (dateOnly === todayIsoVN()) {
      return nowIsoVN(); // đăng/sửa trong hôm nay → giờ thực
    }
    return dateOnly; // ngày khác → không có giờ thực để hiển thị
  }

  // Encode UTF-8 string → base64 (GitHub yêu cầu)
  function b64encode(str) {
    return btoa(unescape(encodeURIComponent(str)));
  }
  function b64decode(b64) {
    return decodeURIComponent(escape(atob(b64.replace(/\n/g, ""))));
  }

  function debounce(fn, ms) {
    let t;
    return function () {
      const args = arguments;
      clearTimeout(t);
      t = setTimeout(() => fn.apply(null, args), ms);
    };
  }

  // Normalize tiếng Việt cho search: bỏ dấu + đ→d + lowercase. Cho phép gõ
  // "doc bao" matched với "Đọc Báo".
  function normalizeStr(s) {
    return String(s || "").toLowerCase()
      .normalize("NFD").replace(/[̀-ͯ]/g, "")
      .replace(/đ/g, "d");
  }

  // ============= LIST METADATA — BAKE + CACHE =============

  // localStorage cache cho slug list lấy từ background refresh.
  // TTL 60s đủ ngắn để bắt bài vừa publish, đủ dài để spam Reload không tốn quota.
  const LIST_CACHE_KEY = "zola-cms-postlist-cache";
  const LIST_CACHE_TTL = 60 * 1000;

  // Parse JSON bake từ <script id="posts-metadata"> embed bởi editor.html.
  // Stale ~1 phút sau khi user publish bài mới (chờ Zola rebuild) — background
  // refresh sẽ phát hiện + mark badge "🆕" lên UI cho bài chưa kịp build.
  function loadBakeMetadata() {
    try {
      const raw = document.getElementById("posts-metadata");
      if (!raw) return [];
      const arr = JSON.parse(raw.textContent || "[]");
      return Array.isArray(arr) ? arr : [];
    } catch (e) {
      console.warn("[CMS] Bake metadata parse fail:", e.message);
      return [];
    }
  }

  function readListCache() {
    try {
      const raw = localStorage.getItem(LIST_CACHE_KEY);
      if (!raw) return null;
      const data = JSON.parse(raw);
      if (!data || (Date.now() - data.timestamp) > LIST_CACHE_TTL) return null;
      return Array.isArray(data.slugs) ? data.slugs : null;
    } catch (e) { return null; }
  }

  function writeListCache(slugs) {
    try {
      localStorage.setItem(LIST_CACHE_KEY, JSON.stringify({
        timestamp: Date.now(),
        slugs: slugs,
      }));
    } catch (e) { /* localStorage full/disabled — skip cache */ }
  }

  function invalidateListCache() {
    try { localStorage.removeItem(LIST_CACHE_KEY); } catch (e) {}
    try { sessionStorage.removeItem(LIST_CACHE_KEY); } catch (e) {}
  }

  function matchesSearch(post, q) {
    if (!q) return true;
    const hay = normalizeStr([
      post.title, post.slug, post.category,
      (post.categories || []).join(" "),
      (post.tags || []).join(" "),
      post.description,
    ].join(" "));
    return hay.includes(q);
  }

  function applyPresetFilter(posts, preset) {
    if (!preset) return posts;
    const now = Date.now();
    const week = 7 * 24 * 60 * 60 * 1000;
    if (preset === "published-7d") {
      return posts.filter((p) => {
        if (postStatus(p) !== "published" || !p.date) return false;
        const t = Date.parse(p.date);
        return !isNaN(t) && (now - t) <= week;
      });
    }
    if (preset === "needs-featured") {
      return posts.filter((p) => !p.featured && postStatus(p) === "published");
    }
    if (preset === "seo-high") {
      return posts.filter((p) => (p.seo_score != null && p.seo_score < 80) || p.seo_score == null);
    }
    return posts;
  }

  function getDisplayPosts() {
    let filtered = state.posts.slice();
    const q = normalizeStr(state.filter.query);
    if (q) filtered = filtered.filter((p) => matchesSearch(p, q));

    const pf = state.filter.placement;
    if (pf === "sticky") filtered = filtered.filter((p) => p.sticky);
    else if (pf === "featured") filtered = filtered.filter((p) => p.featured);

    const st = state.filter.status;
    if (st && st !== "all") {
      filtered = filtered.filter((p) => postStatus(p) === st);
    }

    if (state.filter.category) {
      const cat = normalizeStr(state.filter.category);
      filtered = filtered.filter((p) => {
        const cats = p.categories && p.categories.length ? p.categories : [p.category];
        return cats.some((c) => normalizeStr(c) === cat);
      });
    }

    const fl = state.filter.flags;
    if (fl.sticky) filtered = filtered.filter((p) => p.sticky);
    if (fl.featured) filtered = filtered.filter((p) => p.featured);
    if (fl.hasThumb) filtered = filtered.filter((p) => !!(p.thumbnail || p.image));
    if (fl.premium) filtered = filtered.filter((p) => p.premium);

    filtered = applyPresetFilter(filtered, state.filter.preset);

    switch (state.filter.sort) {
      case "date-asc":
        return filtered.sort((a, b) => (a.date || "").localeCompare(b.date || ""));
      case "title-asc":
        return filtered.sort((a, b) => normalizeStr(a.title).localeCompare(normalizeStr(b.title)));
      case "date-desc":
      default:
        return filtered.sort((a, b) => (b.date || "").localeCompare(a.date || ""));
    }
  }

  function getPaginatedPosts() {
    const all = getDisplayPosts();
    const size = state.pagination.pageSize;
    const totalPages = Math.max(1, Math.ceil(all.length / size));
    if (state.pagination.page > totalPages) state.pagination.page = totalPages;
    if (state.pagination.page < 1) state.pagination.page = 1;
    const start = (state.pagination.page - 1) * size;
    return { all: all, pageItems: all.slice(start, start + size), totalPages: totalPages };
  }

  function postPermalink(post) {
    if (post.permalink) return post.permalink;
    const base = location.pathname.replace(/\/editor\/?$/, "").replace(/\/$/, "");
    return location.origin + base + "/" + CONTENT_DIR.replace(/^content\//, "") + "/" + post.slug + "/";
  }

  function renderKPIs() {
    const posts = state.posts.filter((p) => p && p.slug);
    const totalEl = $("[data-kpi-total]");
    const draftsEl = $("[data-kpi-drafts]");
    const stickyEl = $("[data-kpi-sticky]");
    const featuredEl = $("[data-kpi-featured]");
    if (totalEl) totalEl.textContent = String(posts.length);
    if (draftsEl) draftsEl.textContent = String(posts.filter((p) => p.draft).length);
    if (stickyEl) stickyEl.textContent = String(posts.filter((p) => p.sticky).length);
    if (featuredEl) featuredEl.textContent = String(posts.filter((p) => p.featured).length);
  }

  function renderFilterCounts() {
    const posts = state.posts;
    const set = function (sel, n) {
      const el = $(sel);
      if (el) el.textContent = n ? "(" + n + ")" : "";
    };
    set("[data-count-status-all]", posts.length);
    set("[data-count-status-published]", posts.filter((p) => postStatus(p) === "published").length);
    set("[data-count-status-draft]", posts.filter((p) => postStatus(p) === "draft").length);
    set("[data-count-status-scheduled]", posts.filter((p) => postStatus(p) === "scheduled").length);
  }

  function renderCategoryFilterList() {
    const ul = $("[data-filter-categories]");
    if (!ul) return;
    const q = normalizeStr($("[data-filter-category-search]") && $("[data-filter-category-search]").value);
    const counts = {};
    state.posts.forEach((p) => {
      const cats = p.categories && p.categories.length ? p.categories : [p.category || "Tất cả"];
      cats.forEach((c) => {
        if (!c) return;
        counts[c] = (counts[c] || 0) + 1;
      });
    });
    const cats = Object.keys(counts).sort((a, b) => normalizeStr(a).localeCompare(normalizeStr(b)));
    const filtered = q ? cats.filter((c) => normalizeStr(c).includes(q)) : cats;
    const active = state.filter.category;
    let html = '<li><label><input type="radio" name="ecms-cat" value=""' +
      (!active ? " checked" : "") + '> Tất cả <span>(' + state.posts.length + ')</span></label></li>';
    filtered.slice(0, 24).forEach((c) => {
      const esc = escapeHtml(c);
      html += '<li><label><input type="radio" name="ecms-cat" value="' + esc + '"' +
        (active === c ? " checked" : "") + "> " + esc + " <span>(" + counts[c] + ")</span></label></li>";
    });
    ul.innerHTML = html;
    ul.querySelectorAll('input[name="ecms-cat"]').forEach((inp) => {
      inp.addEventListener("change", () => {
        state.filter.category = inp.value;
        state.pagination.page = 1;
        renderPostList();
      });
    });
  }

  function renderPaginationUI(allCount, totalPages) {
    const wrap = $("[data-pagination]");
    const info = $("[data-pagination-info]");
    const nav = $("[data-pagination-nav]");
    if (!wrap || !info || !nav) return;
    if (allCount === 0) {
      wrap.hidden = true;
      return;
    }
    wrap.hidden = false;
    const size = state.pagination.pageSize;
    const page = state.pagination.page;
    const start = (page - 1) * size + 1;
    const end = Math.min(page * size, allCount);
    info.textContent = "Hiển thị " + start + "–" + end + " trong " + allCount + " bài viết";

    let html = "";
    html += '<button type="button" class="ecms-page-btn" data-page-prev' +
      (page <= 1 ? " disabled" : "") + ">&lt;</button>";
    const pages = [];
    for (let i = 1; i <= totalPages; i++) {
      if (i === 1 || i === totalPages || Math.abs(i - page) <= 1) pages.push(i);
      else if (pages[pages.length - 1] !== "…") pages.push("…");
    }
    pages.forEach((n) => {
      if (n === "…") {
        html += '<span class="ecms-page-btn" style="border:0;background:transparent">…</span>';
      } else {
        html += '<button type="button" class="ecms-page-btn' +
          (n === page ? " is-active" : "") + '" data-page="' + n + '">' + n + "</button>";
      }
    });
    html += '<button type="button" class="ecms-page-btn" data-page-next' +
      (page >= totalPages ? " disabled" : "") + ">&gt;</button>";
    nav.innerHTML = html;
    const prev = nav.querySelector("[data-page-prev]");
    const next = nav.querySelector("[data-page-next]");
    if (prev) prev.addEventListener("click", () => { state.pagination.page--; renderPostList(); });
    if (next) next.addEventListener("click", () => { state.pagination.page++; renderPostList(); });
    nav.querySelectorAll("[data-page]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.pagination.page = parseInt(btn.dataset.page, 10) || 1;
        renderPostList();
      });
    });
  }

  // ============= API CALLS =============

  /* Unauth GitHub API — public repo nên READ (list contents, get file) hoạt
     động không auth. Rate limit 60 req/h cho IP unauth — đủ cho 1 user cá
     nhân chỉnh sửa bài thỉnh thoảng. WRITE (put/delete) đã chuyển sang
     download file thay vì gọi API. */
  async function api(path, opts) {
    opts = opts || {};
    const res = await fetch(API + path, {
      ...opts,
      cache: "no-store",
      headers: {
        Accept: "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        ...(opts.headers || {}),
      },
    });
    if (res.status === 403) {
      const remaining = res.headers.get("X-RateLimit-Remaining");
      if (remaining === "0") {
        throw new Error("GitHub API rate limit 60/h cho IP đã hết — đợi 1h hoặc dùng VPN/mobile network");
      }
    }
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.message || "HTTP " + res.status);
    }
    return res.json();
  }

  // 1 API call: lấy danh sách slug .md trong content/posting/. Dùng để diff với
  // bake metadata, KHÔNG fetch content từng file (tránh N+1).
  async function fetchPostSlugs() {
    const list = await api("/repos/" + OWNER + "/" + REPO + "/contents/" + CONTENT_DIR + "?ref=" + BRANCH);
    return list
      .filter((f) => f.type === "file" && f.name.endsWith(".md") && !f.name.startsWith("_"))
      .map((f) => f.name.replace(/\.md$/, ""));
  }

  // Background refresh: fetch slug list thật từ repo → diff với bake để biết
  // bài nào MỚI publish (chưa build → badge "🆕") và bài nào đã DELETE.
  // Local edits trong state.posts được preserve (ưu tiên cao nhất).
  // Silent fail nếu offline — giữ nguyên bake data.
  async function refreshInBackground(options) {
    const force = !!(options && options.force);
    let apiSlugs = force ? null : readListCache();
    if (!apiSlugs) {
      try {
        apiSlugs = await fetchPostSlugs();
        if (!force) writeListCache(apiSlugs);
      } catch (e) {
        console.warn("[CMS] Background refresh failed:", e.message);
        if (force) throw e;
        return false;
      }
    }

    const bakeBySlug = new Map(state.bakeMetadata.map((p) => [p.slug, p]));
    const localBySlug = new Map(state.posts.map((p) => [p.slug, p]));
    // Force refresh sau login: chỉ tin API (repo hiện tại), không giữ slug đã xoá khỏi repo.
    const mergedSlugs = force
      ? apiSlugs.slice()
      : (function () {
          const slugs = apiSlugs.slice();
          state.bakeMetadata.forEach((p) => {
            if (p.slug && !slugs.includes(p.slug)) slugs.push(p.slug);
          });
          return slugs;
        })();

    // Merge: ưu tiên local > bake > default. isNew=true nếu chưa có trong bake.
    state.posts = mergedSlugs.map((slug) => {
      const inBake = bakeBySlug.has(slug);
      if (localBySlug.has(slug)) {
        return Object.assign({}, localBySlug.get(slug), { isNew: !inBake });
      }
      if (inBake) {
        return Object.assign({}, bakeBySlug.get(slug), { isNew: false });
      }
      return { slug, title: slug, date: "", category: "", featured: false, sticky: false, isNew: true };
    });
    renderPostList();
    return true;
  }

  async function getPost(path) {
    const file = await api("/repos/" + OWNER + "/" + REPO + "/contents/" + path + "?ref=" + BRANCH);
    const content = b64decode(file.content);
    return { sha: file.sha, content, path: file.path };
  }

  /* Draft-only putPost: tải file .md về máy thay vì PUT lên GitHub.
     User chạy thủ công `git add content/posting/{slug}.md && git commit
     && git push` để publish. */
  function putPost(path, content, sha, message) {
    const filename = path.split("/").pop();
    const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.style.display = "none";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
    return Promise.resolve({ downloaded: filename });
  }

  /* Draft-only deletePost: không thể xoá qua API (cần PAT). User phải
     git rm thủ công. Alert hướng dẫn. */
  function deletePost(path, sha, message) {
    alert(
      "Chế độ Draft-only: xoá bài phải làm thủ công.\n\n" +
      "Chạy local trong repo:\n" +
      "  git rm " + path + "\n" +
      "  git commit -m \"" + (message || "Xoá bài") + "\"\n" +
      "  git push"
    );
    return Promise.reject(new Error("delete unavailable in draft-only mode"));
  }

  // ============= FRONTMATTER PARSE/BUILD =============
  const PREMIUM_CATEGORY = "premium";

  function isPremiumCategory(cat) {
    return String(cat || "").trim().toLowerCase() === PREMIUM_CATEGORY;
  }

  function categoryLabel(cat) {
    if (isPremiumCategory(cat)) return "Premium";
    return cat;
  }

  function parseFrontmatter(md) {
    // TOML frontmatter giữa +++ ... +++
    const m = md.match(/^\+\+\+\n([\s\S]*?)\n\+\+\+\n?([\s\S]*)$/);
    if (!m) return { fm: {}, body: md };
    const fmText = m[1];
    const body = m[2] || "";

    const fm = {
      title: "", date: "", category: "Posting", tags: [], thumbnail: "",
      featured: false, featured_at: "", sticky: false,
      premium: false, momo_payment_link: "",
    };

    const lines = fmText.split("\n");
    let section = "root";
    for (const line of lines) {
      const t = line.trim();
      if (!t) continue;
      if (t === "[taxonomies]") { section = "taxonomies"; continue; }
      if (t === "[extra]") { section = "extra"; continue; }

      const kv = t.match(/^(\w+)\s*=\s*(.+)$/);
      if (!kv) continue;
      const key = kv[1];
      let val = kv[2].trim();

      if (val.startsWith('"') && val.endsWith('"')) val = val.slice(1, -1);
      else if (val.startsWith("[") && val.endsWith("]")) {
        val = val.slice(1, -1).split(",").map((s) => s.trim().replace(/^["']|["']$/g, "")).filter(Boolean);
      } else if (val === "true") val = true;
      else if (val === "false") val = false;

      if (section === "root") {
        if (key === "title") fm.title = val;
        else if (key === "date") fm.date = val;
      } else if (section === "taxonomies") {
        if (key === "categories" && Array.isArray(val)) fm.category = val[0] || "Posting";
        else if (key === "tags") fm.tags = Array.isArray(val) ? val : [];
      } else if (section === "extra") {
        if (key === "thumbnail") fm.thumbnail = val;
        else if (key === "featured") fm.featured = val === true;
        else if (key === "featured_at") fm.featured_at = val;
        else if (key === "sticky") fm.sticky = val === true;
        else if (key === "premium") fm.premium = val === true;
        else if (key === "momo_payment_link" || key === "momo_link") fm.momo_payment_link = val;
      }
    }

    return { fm, body };
  }

  function buildFrontmatter(fm, body) {
    const tagsStr = fm.tags.length ? "[" + fm.tags.map((t) => "\"" + t + "\"").join(", ") + "]" : "[]";
    let fmText = `+++
title = "${fm.title.replace(/"/g, '\\"')}"
date = ${fm.date}

[taxonomies]
categories = ["${(fm.category || "Posting").replace(/"/g, '\\"')}"]
tags = ${tagsStr}

[extra]
`;
    if (fm.thumbnail) fmText += `thumbnail = "${fm.thumbnail}"\n`;
    if (fm.featured) {
      fmText += `featured = true\n`;
      // featured_at = thời điểm tick — bài tick sau cùng có timestamp lớn nhất,
      // template sort desc → bài đó lên đầu Featured.
      if (fm.featured_at) fmText += `featured_at = "${fm.featured_at}"\n`;
    }
    // sticky = bài ghim (chỉ 1 bài tại 1 thời điểm — đã validate trước khi save).
    if (fm.sticky) fmText += `sticky = true\n`;
    // Premium category = label only (paywall disabled). Không ghi premium/momo flags.
    fmText += "+++\n\n";
    return fmText + body;
  }

  function collectFormFrontmatter(form) {
    const category = getSelectedCategory();
    const isFeatured = form.featured.checked;
    const isSticky = form.sticky ? form.sticky.checked : false;
    let featuredAt = "";
    if (isFeatured) featuredAt = new Date().toISOString();

    const fm = {
      title: form.title.value.trim(),
      // Đóng dấu thời gian thực (GMT+7) khi đăng hôm nay; giữ timestamp gốc khi sửa
      // bài cũ mà không đổi ngày → "Đăng: HH:MM" hiển thị giờ thật, không phải 00:00.
      date: resolvePublishDate(form.date.value, state.editing && state.editing.originalDate),
      category: category,
      tags: form.tags.value.split(",").map((t) => t.trim()).filter(Boolean),
      thumbnail: form.thumbnail.value.trim(),
      featured: isFeatured,
      featured_at: featuredAt,
      sticky: isSticky,
      premium: false,
      momo_payment_link: "",
    };

    return fm;
  }

  function toggleMomoField(category) {
    const wrap = $("[data-momo-wrap]");
    const input = $("[name='momo_link']");
    if (!wrap) return;
    const show = isPremiumCategory(category);
    wrap.hidden = !show;
    if (!show && input) input.value = "";
  }

  // ============= HOMEPAGE PLACEMENT — Sticky / Featured (single-active) =============
  function findOtherSticky(currentSlug) {
    for (const p of state.posts) {
      if (p.sticky && p.slug !== currentSlug) return p;
    }
    return null;
  }

  function findOtherFeatured(currentSlug) {
    for (const p of state.posts) {
      if (p.featured && p.slug !== currentSlug) return p;
    }
    return null;
  }

  function confirmSlotReplace(slot, other) {
    if (!other) return true;
    const name = other.title || other.slug;
    const label = slot === "sticky" ? "Sticky" : "Featured";
    return confirm(
      'Bài "' + name + '" đang là ' + label + ".\n\n" +
      "Thao tác này sẽ thay thế bài " + label + " hiện tại. Tiếp tục?"
    );
  }

  function reconcileDualPlacement(fm, enabling) {
    if (enabling === "sticky" && fm.featured) {
      if (!confirm("Bài không thể vừa Sticky vừa Featured.\n\nBỏ Featured và đặt làm Sticky?")) return false;
      fm.featured = false;
      fm.featured_at = "";
    }
    if (enabling === "featured" && fm.sticky) {
      if (!confirm("Bài không thể vừa Sticky vừa Featured.\n\nBỏ Sticky và đặt làm Featured?")) return false;
      fm.sticky = false;
    }
    return true;
  }

  function validatePlacementBeforeSave(fm, slug) {
    if (fm.sticky) {
      if (!reconcileDualPlacement(fm, "sticky")) return false;
      if (!confirmSlotReplace("sticky", findOtherSticky(slug))) return false;
    }
    if (fm.featured) {
      if (!reconcileDualPlacement(fm, "featured")) return false;
      if (!confirmSlotReplace("featured", findOtherFeatured(slug))) return false;
    }
    return true;
  }

  function syncPlacementCheckboxes(form, fm) {
    if (form.featured) form.featured.checked = !!fm.featured;
    if (form.sticky) form.sticky.checked = !!fm.sticky;
    updatePlacementUI();
  }

  function updatePlacementUI() {
    const form = $("[data-form='post']");
    if (!form) return;
    const stickyOn = !!(form.sticky && form.sticky.checked);
    const featuredOn = !!(form.featured && form.featured.checked);

    const stickyBadge = $("[data-placement-badge='sticky']");
    const featuredBadge = $("[data-placement-badge='featured']");
    if (stickyBadge) {
      stickyBadge.textContent = stickyOn ? "Currently Sticky" : "Not sticky";
      stickyBadge.classList.toggle("is-active", stickyOn);
    }
    if (featuredBadge) {
      featuredBadge.textContent = featuredOn ? "Currently Featured" : "Not featured";
      featuredBadge.classList.toggle("is-active", featuredOn);
    }

    const stickyOnBtn = $("[data-action='placement-sticky-on']");
    const stickyOffBtn = $("[data-action='placement-sticky-off']");
    const featuredOnBtn = $("[data-action='placement-featured-on']");
    const featuredOffBtn = $("[data-action='placement-featured-off']");
    if (stickyOnBtn) stickyOnBtn.hidden = stickyOn;
    if (stickyOffBtn) stickyOffBtn.hidden = !stickyOn;
    if (featuredOnBtn) featuredOnBtn.hidden = featuredOn;
    if (featuredOffBtn) featuredOffBtn.hidden = !featuredOn;
  }

  function applySavedPostState(slug, fm) {
    if (fm.sticky) {
      state.posts.forEach((p) => { if (p.slug !== slug) p.sticky = false; });
    }
    if (fm.featured) {
      state.posts.forEach((p) => { if (p.slug !== slug) p.featured = false; });
    }
    const savedPost = {
      slug: slug,
      title: fm.title,
      permalink: postPermalink({ slug: slug }),
      date: fm.date,
      category: fm.category,
      featured: fm.featured,
      sticky: fm.sticky,
      isNew: !state.editing,
    };
    const idx = state.posts.findIndex((p) => p.slug === slug);
    if (idx >= 0) state.posts[idx] = savedPost;
    else state.posts.unshift(savedPost);
    invalidateListCache();
    discardDraft(slug);
    lastDraftSlug = slug;
    updatePlacementUI();
  }

  function formatPlacementSaveNote(data) {
    let note = "";
    if (data.demoted_sticky) note += " (đã bỏ ghim " + data.demoted_sticky + " bài cũ)";
    if (data.demoted_featured) note += " (đã bỏ Featured " + data.demoted_featured + " bài cũ)";
    return note;
  }

  async function quickPlacement(slug, mode) {
    const sid = getSid();
    if (!sid || !AUTH_API) {
      alert("Cần đăng nhập để cập nhật placement.");
      return;
    }

    const path = CONTENT_DIR + "/" + slug + ".md";
    setStatus("[data-status]", "Đang cập nhật placement…", "info");

    try {
      const data = await getPost(path);
      const { fm, body } = parseFrontmatter(data.content);

      if (mode === "sticky-on") {
        if (!reconcileDualPlacement(fm, "sticky")) return;
        if (!confirmSlotReplace("sticky", findOtherSticky(slug))) return;
        fm.sticky = true;
      } else if (mode === "sticky-off") {
        fm.sticky = false;
      } else if (mode === "featured-on") {
        if (!reconcileDualPlacement(fm, "featured")) return;
        if (!confirmSlotReplace("featured", findOtherFeatured(slug))) return;
        fm.featured = true;
        fm.featured_at = new Date().toISOString();
      } else if (mode === "featured-off") {
        fm.featured = false;
        fm.featured_at = "";
      }

      const content = buildFrontmatter(fm, body);
      const message = "CMS: placement " + mode + " — " + (fm.title || slug);

      const res = await fetch(AUTH_API + "/cms/save-post", {
        method: "POST",
        headers: {
          "Authorization": "Bearer " + sid,
          "Content-Type": "application/json",
        },
        credentials: "omit",
        body: JSON.stringify({ slug, content, message, sha: data.sha }),
      });

      if (res.status === 401) {
        clearSid();
        alert("Phiên hết hạn. Đăng nhập lại.");
        showView("login");
        return;
      }

      const payload = await res.json();
      if (!res.ok) {
        setStatus("[data-status]", "✗ " + (payload.detail || "Lỗi lưu placement"), "error");
        return;
      }

      applySavedPostState(slug, fm);
      renderPostList();
      let msg = "Đã cập nhật placement cho \"" + (fm.title || slug) + "\"";
      if (mode === "sticky-on") {
        msg = "Đã đặt bài này làm Sticky.";
        if (payload.demoted_sticky) msg += " Bài Sticky cũ đã được bỏ ghim.";
      } else if (mode === "featured-on") {
        msg = "Đã đặt bài này làm Featured.";
        if (payload.demoted_featured) msg += " Bài Featured cũ đã được thay thế.";
      } else if (mode === "sticky-off") msg = "Đã bỏ Sticky.";
      else if (mode === "featured-off") msg = "Đã bỏ Featured.";
      showToast(msg, "success");
      setStatus("[data-status]", "✓ " + msg, "success");
    } catch (err) {
      showToast("Không thể lưu thay đổi. " + err.message, "error");
      setStatus("[data-status]", "✗ " + err.message, "error");
    }
  }

  // ============= LOGIN BUTTONS → REDIRECT OAUTH (GitHub / Google) =============
  function startOAuth(startPath) {
    if (!AUTH_API) { showLoginHint(); return; }
    const returnTo = location.pathname + location.search;
    location.href = AUTH_API + startPath + "?return_to=" + encodeURIComponent(returnTo);
  }

  const loginBtn = $("[data-action='github-login']");
  if (loginBtn) {
    loginBtn.addEventListener("click", function () { startOAuth("/auth/login"); });
  }
  const googleBtn = $("[data-action='google-login']");
  if (googleBtn) {
    googleBtn.addEventListener("click", function () { startOAuth("/auth/google/start"); });
  }

  // Provider availability từ /auth/config — bền với cả schema mới (nested) lẫn cũ.
  //   mới: { provider, google:{enabled,configured}, github:{enabled,configured} }
  //   cũ : { google:true } | { google_enabled:true } | { providers:{google:true} }
  // Theo contract backend hiện tại: available khi enabled===true && configured===true
  // && provider ∈ {dual, <tên>}. Trả null nếu không suy được (giữ default UI).
  function providerAvailable(cfg, name) {
    if (!cfg) return null;
    const provider = cfg.provider || cfg.auth_provider || "";
    // provider gate: dual bật cả hai; ngược lại phải khớp đúng tên provider.
    if (provider && provider !== "dual" && provider !== name) return false;
    const node = cfg[name];
    if (node && typeof node === "object") {
      // Schema mới: yêu cầu enabled; configured mặc định true nếu không khai báo.
      return node.enabled === true && node.configured !== false;
    }
    // Schema cũ (boolean) — backward-compatible, không phá GitHub login.
    if (node === true) return true;
    if (cfg[name + "_enabled"] === true) return true;
    if (cfg.providers && cfg.providers[name] === true) return true;
    if (node === false) return false;
    // Không có thông tin node → suy theo provider gate (dual/đúng tên ⇒ bật).
    return provider === "dual" || provider === name;
  }

  // Fetch /auth/config, render đúng nút (Google primary trong dual/google), và
  // TRẢ availability để init quyết định có nên hiện cảnh báo *_disabled hay không.
  //   dual   → Google (primary) + GitHub (phụ)
  //   google → chỉ Google
  //   github → chỉ GitHub (mặc định, giữ hành vi cũ nếu fetch lỗi)
  async function applyAuthProviders() {
    if (!AUTH_API) return null;
    let cfg = null;
    try {
      const res = await fetch(AUTH_API + "/auth/config", { cache: "no-store" });
      if (res.ok) cfg = await res.json();
    } catch (e) { /* network fail → giữ default (cả 2 nút) */ }
    if (!cfg) return null;
    const googleOk = providerAvailable(cfg, "google");
    const githubOk = providerAvailable(cfg, "github");
    const gBtn = $("[data-provider-btn='google']");
    const ghBtn = $("[data-provider-btn='github']");
    if (gBtn  && googleOk !== null) gBtn.hidden  = !googleOk;
    if (ghBtn && githubOk !== null) ghBtn.hidden = !githubOk;
    // Trong dual/google, Google là primary; hạ GitHub xuống nút phụ (ghost).
    if (googleOk && gBtn && ghBtn) {
      gBtn.classList.add("editor-btn--primary");
      ghBtn.classList.remove("editor-btn--primary");
      ghBtn.classList.add("editor-btn--ghost");
    }
    // Tự sửa cảnh báo cũ mâu thuẫn: nếu config xác nhận provider đang BẬT thì gỡ
    // cảnh báo *_disabled còn sót lại (vd ?auth_error=google_disabled cũ).
    if (googleOk) clearLoginErrorCodes(["google_disabled", "google_not_configured"]);
    if (githubOk) clearLoginErrorCodes(["github_disabled"]);
    return { google: googleOk, github: githubOk };
  }

  let bakeLoaded = false;

  function showDashboardLoading(message) {
    setStatus("[data-status]", message || "Đang tải dữ liệu mới nhất từ GitHub…", "info");
    const list = $("[data-target='post-list']");
    if (list) list.innerHTML = '<div class="ecms-list__empty">Đang tải danh sách bài viết…</div>';
    const kpi = $("[data-kpi-total]");
    if (kpi) kpi.textContent = "…";
  }

  // force=true: sau login / mở CMS — luôn fetch tươi từ GitHub, bỏ cache cũ.
  // force=false: quay lại từ editor — giữ state.posts hiện có (local edits).
  async function enterDashboard(force) {
    showView("list");

    if (force) {
      invalidateListCache();
      selectedSlugs.clear();
      showDashboardLoading();

      // Bake chỉ làm baseline diff (badge 🆕), không dùng làm số liệu hiển thị.
      state.bakeMetadata = loadBakeMetadata();
      bakeLoaded = true;
      state.posts = [];

      try {
        await refreshInBackground({ force: true });
        setStatus(
          "[data-status]",
          "✓ " + state.posts.length + " bài viết (cập nhật từ GitHub)",
          "success"
        );
      } catch (err) {
        state.posts = state.bakeMetadata.slice();
        renderPostList();
        setStatus(
          "[data-status]",
          "⚠ Không tải được GitHub — hiển thị dữ liệu build: " + err.message,
          "error"
        );
      }
      fetchCategoriesFromBackend();
      return;
    }

    // Lần đầu vào (không force): load bake → render instant (0ms). Lần sau giữ
    // state.posts hiện có để preserve local edits chưa propagate qua background refresh.
    if (!bakeLoaded) {
      state.bakeMetadata = loadBakeMetadata();
      state.posts = state.bakeMetadata.slice();
      bakeLoaded = true;
    }
    renderPostList();
    setStatus("[data-status]", state.posts.length + " bài viết", "info");

    setTimeout(() => refreshInBackground({ force: false }), 500);
    setTimeout(() => fetchCategoriesFromBackend(), 200);
  }

  // ============= LIST VIEW =============
  // ============= BULK SELECTION STATE =============
  const selectedSlugs = new Set();

  function updateBulkBar() {
    const bar = $("[data-bulk-bar]");
    const count = $("[data-bulk-count]");
    if (!bar) return;
    const n = selectedSlugs.size;
    bar.hidden = n === 0;
    if (count) count.textContent = String(n);
    const disable = n === 0;
    ["bulk-delete", "bulk-sticky", "bulk-featured"].forEach((act) => {
      const btn = $('[data-action="' + act + '"]');
      if (btn) btn.disabled = disable || (act !== "bulk-delete" && n > 1);
    });
    const selectAll = $("[data-select-all]");
    if (selectAll) {
      const pageItems = getPaginatedPosts().pageItems;
      const visibleSelected = pageItems.filter((p) => selectedSlugs.has(p.slug)).length;
      selectAll.checked = pageItems.length > 0 && visibleSelected === pageItems.length;
      selectAll.indeterminate = visibleSelected > 0 && visibleSelected < pageItems.length;
    }
  }

  function openDrawer(slug) {
    const drawer = $("[data-detail-drawer]");
    const body = $("[data-drawer-body]");
    if (!drawer || !body) return;
    state.drawerSlug = slug;
    drawer.hidden = false;
    drawer.classList.add("is-open");
    const post = state.posts.find((p) => p.slug === slug);
    if (!post) {
      body.innerHTML = '<p class="ecms-drawer__placeholder">Không tìm thấy bài.</p>';
      return;
    }
    const thumb = resolveThumbUrl(post);
    const seo = post.seo_score != null
      ? '<div class="ecms-drawer__seo">SEO ' + post.seo_score + (post.seo_grade ? " · " + escapeHtml(post.seo_grade) : "") + "</div>"
      : "";
    const cats = (function () {
      try {
        const raw = document.getElementById("categories-data");
        return raw ? JSON.parse(raw.textContent || "[]") : [];
      } catch (e) { return []; }
    })();
    let catOpts = cats.map((c) =>
      '<option value="' + escapeHtml(c) + '"' + (post.category === c ? " selected" : "") + ">" + escapeHtml(c) + "</option>"
    ).join("");
    body.innerHTML =
      '<div class="ecms-drawer__thumb"><img src="' + escapeHtml(thumb) + '" alt="" loading="lazy" decoding="async"></div>' +
      seo +
      '<div class="ecms-drawer__field"><label>Tiêu đề</label><input type="text" data-drawer-title value="' + escapeHtml(post.title || "") + '"></div>' +
      '<div class="ecms-drawer__field"><label>Slug</label><div class="ecms-drawer__slug-row">' +
        '<input type="text" data-drawer-slug value="' + escapeHtml(post.slug) + '" readonly>' +
        '<button type="button" class="ecms-btn ecms-btn--ghost ecms-btn--small" data-drawer-copy-slug>Copy</button></div></div>' +
      '<div class="ecms-drawer__field"><label>Category</label><select data-drawer-category>' + catOpts + '</select></div>' +
      '<div class="ecms-drawer__field"><label>Trạng thái</label><select data-drawer-status disabled>' +
        '<option>' + escapeHtml(statusLabel(post)) + '</option></select></div>' +
      '<div class="ecms-drawer__field"><label>Ngày đăng</label><input type="date" data-drawer-date value="' + escapeHtml((post.date || "").slice(0, 10)) + '"></div>' +
      '<div class="ecms-drawer__field"><label>Ảnh thumbnail</label><input type="url" data-drawer-thumb value="' + escapeHtml(post.thumbnail || post.image || "") + '"></div>' +
      '<div class="ecms-drawer__toggles">' +
        '<label class="ecms-drawer__toggle">Sticky<input type="checkbox" data-drawer-sticky' + (post.sticky ? " checked" : "") + "></label>" +
        '<label class="ecms-drawer__toggle">Featured<input type="checkbox" data-drawer-featured' + (post.featured ? " checked" : "") + "></label>" +
        (post.premium ? '<label class="ecms-drawer__toggle">Premium<input type="checkbox" checked disabled></label>' : "") +
      "</div>" +
      '<div class="ecms-drawer__actions">' +
        '<button type="button" class="ecms-btn ecms-btn--primary" data-drawer-save>Lưu</button>' +
        '<a class="ecms-btn ecms-btn--ghost" href="' + escapeHtml(postPermalink(post)) + '" target="_blank" rel="noopener">Xem trước</a>' +
        '<button type="button" class="ecms-btn ecms-btn--ghost" data-drawer-edit>Sửa đầy đủ</button>' +
        '<button type="button" class="ecms-btn ecms-btn--ghost" data-drawer-close>Hủy</button>' +
      "</div>";

    body.querySelector("[data-drawer-copy-slug]").addEventListener("click", () => {
      const slugInp = body.querySelector("[data-drawer-slug]");
      if (slugInp) navigator.clipboard.writeText(slugInp.value).then(() => showToast("Đã copy slug", "success"));
    });
    body.querySelector("[data-drawer-edit]").addEventListener("click", () => {
      closeDrawer();
      openEditor(CONTENT_DIR + "/" + slug + ".md");
    });
    body.querySelectorAll("[data-drawer-close]").forEach((b) => b.addEventListener("click", closeDrawer));
    body.querySelector("[data-drawer-save]").addEventListener("click", () => quickSaveFromDrawer(slug, body));
  }

  function closeDrawer() {
    const drawer = $("[data-detail-drawer]");
    if (!drawer) return;
    drawer.classList.remove("is-open");
    drawer.hidden = true;
    state.drawerSlug = null;
  }

  async function quickSaveFromDrawer(slug, bodyEl) {
    const btn = bodyEl.querySelector("[data-drawer-save]");
    const sid = getSid();
    if (!sid || !AUTH_API) {
      showToast("Cần đăng nhập để lưu.", "error");
      return;
    }
    const path = CONTENT_DIR + "/" + slug + ".md";
    if (btn) { btn.disabled = true; btn.classList.add("is-loading"); btn.textContent = "Đang lưu…"; }
    try {
      const data = await getPost(path);
      const parsed = parseFrontmatter(data.content);
      const fm = parsed.fm;
      const titleInp = bodyEl.querySelector("[data-drawer-title]");
      const catInp = bodyEl.querySelector("[data-drawer-category]");
      const dateInp = bodyEl.querySelector("[data-drawer-date]");
      const thumbInp = bodyEl.querySelector("[data-drawer-thumb]");
      const stickyInp = bodyEl.querySelector("[data-drawer-sticky]");
      const featuredInp = bodyEl.querySelector("[data-drawer-featured]");
      const originalDate = fm.date; // giá trị gốc (có thể kèm giờ thực)
      fm.title = titleInp ? titleInp.value.trim() : fm.title;
      fm.category = catInp ? catInp.value : fm.category;
      // Giữ giờ gốc nếu không đổi ngày; đóng dấu giờ thực nếu chuyển sang hôm nay.
      fm.date = resolvePublishDate(dateInp ? dateInp.value : fm.date, originalDate);
      fm.thumbnail = thumbInp ? thumbInp.value.trim() : fm.thumbnail;
      fm.sticky = !!(stickyInp && stickyInp.checked);
      fm.featured = !!(featuredInp && featuredInp.checked);
      if (fm.featured && !fm.featured_at) fm.featured_at = new Date().toISOString();
      if (!fm.featured) fm.featured_at = "";
      if (!validatePlacementBeforeSave(fm, slug)) return;
      const content = buildFrontmatter(fm, parsed.body);
      const headers = { "Content-Type": "application/json" };
      if (sid) headers.Authorization = "Bearer " + sid;
      const res = await fetch(AUTH_API + "/cms/save-post", {
        method: "POST",
        headers: headers,
        credentials: "include",
        body: JSON.stringify({ slug, content, message: "CMS quick edit: " + fm.title, sha: data.sha }),
      });
      if (res.status === 401) { handleSessionExpired(); return; }
      const payload = await res.json();
      if (!res.ok) {
        showToast("Không thể lưu thay đổi. Vui lòng thử lại.", "error");
        return;
      }
      applySavedPostState(slug, fm);
      renderPostList();
      showToast("Đã lưu thay đổi thành công", "success");
      if (payload.demoted_sticky) showToast("Đã bỏ ghim bài Sticky cũ.", "info");
      if (payload.demoted_featured) showToast("Bài Featured cũ đã được thay thế.", "info");
      openDrawer(slug);
    } catch (err) {
      showToast("Không thể lưu thay đổi. " + err.message, "error");
    } finally {
      if (btn) { btn.disabled = false; btn.classList.remove("is-loading"); btn.textContent = "Lưu"; }
    }
  }

  function renderPostList() {
    const list = $("[data-target='post-list']");
    if (!list) return;
    const paginated = getPaginatedPosts();
    const displayPosts = paginated.pageItems;
    const allCount = paginated.all.length;

    renderKPIs();
    renderFilterCounts();
    renderCategoryFilterList();
    renderPaginationUI(allCount, paginated.totalPages);

    if (!state.posts.length) {
      list.innerHTML = '<div class="ecms-list__empty">Chưa có bài nào. Bấm "+ Viết bài mới".</div>';
      updateBulkBar();
      return;
    }
    if (!allCount) {
      list.innerHTML = '<div class="ecms-list__empty">Không có bài khớp bộ lọc.</div>';
      updateBulkBar();
      return;
    }

    list.innerHTML = displayPosts.map((p) => {
      const path = CONTENT_DIR + "/" + p.slug + ".md";
      const slugEsc = escapeHtml(p.slug);
      const checked = selectedSlugs.has(p.slug) ? " checked" : "";
      const st = postStatus(p);
      const chipClass = st === "draft" ? "ecms-chip--draft" : (st === "scheduled" ? "ecms-chip--scheduled" : "ecms-chip--published");
      const cardClass = "ecms-card" +
        (selectedSlugs.has(p.slug) ? " is-selected" : "") +
        (p.sticky ? " is-sticky" : "") +
        (p.featured ? " is-featured" : "");
      const thumb = resolveThumbUrl(p);
      const readMin = p.reading_time ? p.reading_time + " phút" : "";
      return '<article class="' + cardClass + '" data-card-slug="' + slugEsc + '">' +
        '<div class="ecms-card__check"><input type="checkbox" data-row-select value="' + slugEsc + '"' + checked + ' aria-label="Chọn bài"></div>' +
        '<div class="ecms-card__thumb"><img src="' + escapeHtml(thumb) + '" alt="" loading="lazy" decoding="async"></div>' +
        '<div class="ecms-card__body">' +
          '<h4 class="ecms-card__title"><button type="button" data-open-drawer="' + slugEsc + '">' + escapeHtml(p.title || p.slug) + '</button></h4>' +
          '<div class="ecms-card__slug">/' + slugEsc + '</div>' +
          '<div class="ecms-card__meta">' +
            '<span class="ecms-chip">' + escapeHtml(p.category || "—") + '</span>' +
            '<span class="ecms-chip ' + chipClass + '">' + escapeHtml(statusLabel(p)) + '</span>' +
            (p.isNew ? '<span class="ecms-chip ecms-chip--new">Mới</span>' : "") +
            '<span>' + escapeHtml(formatDisplayDate(p.date)) + '</span>' +
            (readMin ? '<span>' + escapeHtml(readMin) + '</span>' : "") +
            (p.seo_score != null ? '<span>SEO ' + p.seo_score + '</span>' : "") +
          '</div>' +
        '</div>' +
        '<div class="ecms-card__actions">' +
          '<button type="button" class="ecms-pill-toggle ecms-pill-toggle--sticky' + (p.sticky ? " is-on" : "") + '" data-quick-placement="' + (p.sticky ? "sticky-off" : "sticky-on") + '" data-slug="' + slugEsc + '">' +
            '<svg viewBox="0 0 24 24"><path d="M12 17v5"/><path d="M5 7h14l-1 7H6z"/></svg> Sticky</button>' +
          '<button type="button" class="ecms-pill-toggle ecms-pill-toggle--featured' + (p.featured ? " is-on" : "") + '" data-quick-placement="' + (p.featured ? "featured-off" : "featured-on") + '" data-slug="' + slugEsc + '">' +
            '<svg viewBox="0 0 24 24"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg> Featured</button>' +
          '<div class="ecms-card__btns">' +
            '<button type="button" class="ecms-btn ecms-btn--ghost ecms-btn--small" data-edit="' + escapeHtml(path) + '">Edit</button>' +
            '<a class="ecms-btn ecms-btn--ghost ecms-btn--small" href="' + escapeHtml(postPermalink(p)) + '" target="_blank" rel="noopener">Preview</a>' +
            '<button type="button" class="ecms-btn ecms-btn--ghost ecms-btn--small" data-duplicate="' + slugEsc + '">Copy</button>' +
          '</div>' +
        '</div>' +
      '</article>';
    }).join("");

    list.querySelectorAll("[data-edit]").forEach((btn) => {
      btn.addEventListener("click", () => openEditor(btn.dataset.edit));
    });
    list.querySelectorAll("[data-open-drawer]").forEach((btn) => {
      btn.addEventListener("click", () => openDrawer(btn.dataset.openDrawer));
    });
    list.querySelectorAll("[data-quick-placement]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        quickPlacement(btn.dataset.slug, btn.dataset.quickPlacement);
      });
    });
    list.querySelectorAll("[data-duplicate]").forEach((btn) => {
      btn.addEventListener("click", () => duplicatePost(btn.dataset.duplicate));
    });
    list.querySelectorAll("[data-row-select]").forEach((cb) => {
      cb.addEventListener("change", () => {
        if (cb.checked) selectedSlugs.add(cb.value);
        else selectedSlugs.delete(cb.value);
        renderPostList();
      });
    });
    updateBulkBar();
  }

  async function duplicatePost(slug) {
    const path = CONTENT_DIR + "/" + slug + ".md";
    try {
      const data = await getPost(path);
      const { fm, body } = parseFrontmatter(data.content);
      fm.title = (fm.title || slug) + " (bản sao)";
      const newSlug = slugify(fm.title) + "-" + Date.now().toString(36).slice(-4);
      showView("edit");
      const form = $("[data-form='post']");
      form.reset();
      state.editing = null;
      slugLocked = false;
      form.title.value = fm.title;
      form.slug.value = newSlug;
      form.date.value = todayIso();
      rebuildCategoryOptions(fm.category);
      form.tags.value = (fm.tags || []).join(", ");
      form.thumbnail.value = fm.thumbnail || "";
      form.body.value = body.trim();
      if (form.sticky) form.sticky.checked = false;
      form.featured.checked = false;
      updatePlacementUI();
      showToast("Đã tạo bản sao — chỉnh sửa và lưu.", "info");
    } catch (err) {
      showToast("Không copy được bài: " + err.message, "error");
    }
  }

  // ============= BULK ACTIONS =============
  const selectAllCb = $("[data-select-all]");
  if (selectAllCb) {
    selectAllCb.addEventListener("change", () => {
      const pageItems = getPaginatedPosts().pageItems;
      if (selectAllCb.checked) pageItems.forEach((p) => selectedSlugs.add(p.slug));
      else pageItems.forEach((p) => selectedSlugs.delete(p.slug));
      renderPostList();
    });
  }

  // Clear selection button
  const bulkClearBtn = $("[data-action='bulk-clear']");
  if (bulkClearBtn) {
    bulkClearBtn.addEventListener("click", () => {
      selectedSlugs.clear();
      renderPostList();
    });
  }

  const bulkDeleteBtn = $("[data-action='bulk-delete']");
  if (bulkDeleteBtn) {
    bulkDeleteBtn.addEventListener("click", () => {
      if (selectedSlugs.size === 0) return;
      openBulkModal();
    });
  }

  function openBulkModal() {
    const modal = $("[data-modal='bulk-delete']");
    const countEl = $("[data-modal-count]");
    const listEl = $("[data-modal-list]");
    const statusEl = $("[data-modal-status]");
    if (!modal) return;
    countEl.textContent = selectedSlugs.size;
    statusEl.textContent = "";
    statusEl.className = "editor-modal__status";
    // Render list of slugs (max 10 visible, ... + count if more)
    const slugArr = Array.from(selectedSlugs);
    const shown = slugArr.slice(0, 10);
    const extra = slugArr.length - shown.length;
    listEl.innerHTML = shown.map((s) => '<li><code>' + escapeHtml(s) + '.md</code></li>').join("") +
      (extra > 0 ? '<li><em>… và ' + extra + ' bài nữa</em></li>' : "");
    modal.hidden = false;
    document.body.classList.add("editor-modal-open");
  }

  function closeBulkModal() {
    const modal = $("[data-modal='bulk-delete']");
    if (!modal) return;
    modal.hidden = true;
    document.body.classList.remove("editor-modal-open");
  }

  $$("[data-modal-close]").forEach((el) => {
    el.addEventListener("click", closeBulkModal);
  });

  $("[data-modal-confirm]").addEventListener("click", async () => {
    if (!AUTH_API) {
      alert("Backend chưa cấu hình");
      return;
    }
    const sid = getSid();
    if (!sid) {
      alert("Phiên hết hạn");
      showView("login");
      return;
    }
    const slugs = Array.from(selectedSlugs);
    if (slugs.length === 0) return;

    const confirmBtn = $("[data-modal-confirm]");
    const statusEl = $("[data-modal-status]");
    confirmBtn.disabled = true;
    statusEl.className = "editor-modal__status editor-modal__status--info";
    statusEl.textContent = "Đang xoá " + slugs.length + " bài…";

    try {
      const res = await fetch(AUTH_API + "/cms/posts/bulk-delete", {
        method: "POST",
        headers: {
          "Authorization": "Bearer " + sid,
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify({ slugs: slugs }),
      });
      if (res.status === 401) {
        clearSid();
        showView("login");
        return;
      }
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        statusEl.className = "editor-modal__status editor-modal__status--error";
        statusEl.textContent = "✗ " + (data.detail || "API lỗi (" + res.status + ")");
        return;
      }
      // Success: update state, close modal, re-render
      state.posts = state.posts.filter((p) => !selectedSlugs.has(p.slug));
      selectedSlugs.clear();
      invalidateListCache();
      const commitLink = data.commit_url
        ? ' · <a href="' + data.commit_url + '" target="_blank" rel="noopener">Xem commit</a>'
        : "";
      statusEl.className = "editor-modal__status editor-modal__status--success";
      statusEl.innerHTML = "✓ Đã xoá " + data.deleted_count + " bài" + commitLink +
        ". Deploy ETA: " + escapeHtml(data.deploy_eta || "~2 phút");
      renderPostList();
      showToast("Đã xoá " + data.deleted_count + " bài viết", "success");
      setTimeout(closeBulkModal, 2500);
    } catch (err) {
      statusEl.className = "editor-modal__status editor-modal__status--error";
      statusEl.textContent = "✗ Lỗi mạng: " + err.message;
    } finally {
      confirmBtn.disabled = false;
    }
  });

  // Escape key closes modal
  document.addEventListener("keydown", (e) => {
    const modal = $("[data-modal='bulk-delete']");
    if (e.key === "Escape" && modal && !modal.hidden) {
      closeBulkModal();
    }
  });

  function setReloadLoading(btn, isLoading) {
    if (!btn) return;
    if (!btn.dataset.idleHtml) btn.dataset.idleHtml = btn.innerHTML;
    btn.disabled = isLoading;
    btn.classList.toggle("is-loading", isLoading);
    btn.setAttribute("aria-busy", isLoading ? "true" : "false");
    btn.innerHTML = isLoading
      ? '<span class="editor-btn__spinner" aria-hidden="true"></span><span>Đang tải...</span>'
      : btn.dataset.idleHtml;
  }

  async function reloadPostsFromSource(btn) {
    invalidateListCache();
    setReloadLoading(btn, true);
    setStatus("[data-status]", "Đang xoá cache và quét lại GitHub…", "info");
    const list = $("[data-target='post-list']");
    if (list) list.innerHTML = '<div class="ecms-list__empty">Đang tải lại danh sách bài viết…</div>';

    try {
      await refreshInBackground({ force: true });
      setStatus("[data-status]", "✓ Đã cập nhật danh sách mới nhất (" + state.posts.length + " bài)", "success");
    } catch (err) {
      renderPostList();
      setStatus("[data-status]", "✗ Không tải lại được: " + err.message, "error");
    } finally {
      setReloadLoading(btn, false);
    }
  }

  const reloadBtn = $("[data-action='reload']");
  if (reloadBtn) {
    reloadBtn.addEventListener("click", () => reloadPostsFromSource(reloadBtn));
  }

  const searchInput = $("[data-search]");
  const searchForm = $("[data-google-search-form]");
  const searchModeEl = $("[data-search-mode]");

  if (searchModeEl) {
    searchModeEl.textContent = GOOGLE_CSE_CX
      ? "Google CSE + lọc client"
      : "Lọc client-side (title, slug, category, tag)";
  }

  function applyClientSearchQuery(val) {
    state.filter.query = val;
    state.pagination.page = 1;
    renderPostList();
  }

  if (searchInput) {
    searchInput.addEventListener("input", debounce(() => {
      applyClientSearchQuery(searchInput.value);
    }, 120));
  }

  if (searchForm) {
    searchForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const q = searchInput ? searchInput.value.trim() : "";
      applyClientSearchQuery(q);
      if (GOOGLE_CSE_CX && q) {
        const url = "https://cse.google.com/cse?cx=" + encodeURIComponent(GOOGLE_CSE_CX) +
          "&q=" + encodeURIComponent(q + " site:seomoney.org");
        window.open(url, "_blank", "noopener");
      }
    });
  }

  const sortSelect = $("[data-sort]");
  if (sortSelect) {
    sortSelect.addEventListener("change", () => {
      state.filter.sort = sortSelect.value;
      renderPostList();
    });
  }

  const pageSizeSelect = $("[data-page-size]");
  if (pageSizeSelect) {
    pageSizeSelect.addEventListener("change", () => {
      state.pagination.pageSize = parseInt(pageSizeSelect.value, 10) || 6;
      state.pagination.page = 1;
      renderPostList();
    });
  }

  $$("[data-filter-placement]").forEach((chip) => {
    chip.addEventListener("click", () => {
      state.filter.placement = chip.dataset.filterPlacement || "";
      state.pagination.page = 1;
      $$("[data-filter-placement]").forEach((c) => {
        const on = c === chip;
        c.classList.toggle("is-active", on);
        c.setAttribute("aria-selected", on ? "true" : "false");
      });
      renderPostList();
    });
  });

  $$('input[name="ecms-status"]').forEach((inp) => {
    inp.addEventListener("change", () => {
      if (!inp.checked) return;
      state.filter.status = inp.value;
      state.pagination.page = 1;
      renderPostList();
    });
  });

  $$("[data-filter-flag]").forEach((inp) => {
    inp.addEventListener("change", () => {
      const key = inp.dataset.filterFlag;
      if (key && state.filter.flags[key] !== undefined) {
        state.filter.flags[key] = inp.checked;
        state.pagination.page = 1;
        renderPostList();
      }
    });
  });

  $$("[data-filter-preset]").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.filter.preset = btn.dataset.filterPreset || "";
      state.pagination.page = 1;
      renderPostList();
      showToast("Đã áp dụng bộ lọc: " + btn.textContent.trim(), "info");
    });
  });

  const clearFiltersBtn = $("[data-action='clear-filters']");
  if (clearFiltersBtn) {
    clearFiltersBtn.addEventListener("click", () => {
      state.filter.query = "";
      state.filter.status = "all";
      state.filter.category = "";
      state.filter.preset = "";
      state.filter.flags = { sticky: false, featured: false, hasThumb: false, premium: false };
      state.pagination.page = 1;
      if (searchInput) searchInput.value = "";
      const allSt = $('input[name="ecms-status"][value="all"]');
      if (allSt) allSt.checked = true;
      $$("[data-filter-flag]").forEach((inp) => { inp.checked = false; });
      renderPostList();
      showToast("Đã xóa bộ lọc", "info");
    });
  }

  const catSearch = $("[data-filter-category-search]");
  if (catSearch) {
    catSearch.addEventListener("input", debounce(() => renderCategoryFilterList(), 100));
  }

  function toggleFilterSidebar(open) {
    const sidebar = $("[data-filter-sidebar]");
    const backdrop = $("[data-filter-backdrop]");
    if (!sidebar) return;
    const on = open == null ? !sidebar.classList.contains("is-open") : open;
    sidebar.classList.toggle("is-open", on);
    if (backdrop) backdrop.hidden = !on;
  }

  const toggleFiltersBtn = $("[data-action='toggle-filters']");
  if (toggleFiltersBtn) toggleFiltersBtn.addEventListener("click", () => toggleFilterSidebar());

  const filterBackdrop = $("[data-filter-backdrop]");
  if (filterBackdrop) filterBackdrop.addEventListener("click", () => toggleFilterSidebar(false));

  $$("[data-drawer-close]").forEach((el) => el.addEventListener("click", closeDrawer));

  const focusSearchBtn = $("[data-action='focus-search']");
  if (focusSearchBtn) {
    focusSearchBtn.addEventListener("click", () => {
      if (searchInput) { searchInput.focus(); searchInput.scrollIntoView({ behavior: "smooth", block: "center" }); }
    });
  }

  const helpBtn = $("[data-action='help']");
  if (helpBtn) {
    helpBtn.addEventListener("click", () => {
      showToast("Editor CMS: lọc trái · danh sách giữa · chi tiết phải. Sticky/Featured chỉ 1 bài mỗi loại.", "info");
    });
  }

  const userMenuBtn = $("[data-action='user-menu']");
  const userDropdown = $("[data-user-dropdown]");
  if (userMenuBtn && userDropdown) {
    userMenuBtn.addEventListener("click", () => {
      userDropdown.hidden = !userDropdown.hidden;
    });
    document.addEventListener("click", (e) => {
      if (!userMenuBtn.contains(e.target) && !userDropdown.contains(e.target)) {
        userDropdown.hidden = true;
      }
    });
  }

  const importBtn = $("[data-action='import']");
  const importFile = $("[data-import-file]");
  if (importBtn && importFile) {
    importBtn.addEventListener("click", () => importFile.click());
    importFile.addEventListener("change", () => {
      const file = importFile.files && importFile.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        const text = String(reader.result || "");
        const parsed = parseFrontmatter(text);
        showView("edit");
        const form = $("[data-form='post']");
        form.reset();
        state.editing = null;
        slugLocked = false;
        const fm = parsed.fm;
        form.title.value = fm.title || file.name.replace(/\.md$/i, "");
        form.slug.value = slugify(form.title.value);
        form.date.value = String(fm.date || "").slice(0, 10) || todayIso();
        rebuildCategoryOptions(fm.category || "Tất cả");
        form.tags.value = (fm.tags || []).join(", ");
        form.thumbnail.value = fm.thumbnail || "";
        form.body.value = (parsed.body || "").trim();
        showToast("Đã nhập file — kiểm tra và lưu.", "success");
        importFile.value = "";
      };
      reader.readAsText(file, "UTF-8");
    });
  }

  async function bulkSetPlacement(mode) {
    if (selectedSlugs.size !== 1) {
      showToast("Chỉ chọn đúng 1 bài để đặt Sticky/Featured.", "error");
      return;
    }
    const slug = Array.from(selectedSlugs)[0];
    await quickPlacement(slug, mode);
    selectedSlugs.clear();
    renderPostList();
  }

  const bulkStickyBtn = $("[data-action='bulk-sticky']");
  if (bulkStickyBtn) bulkStickyBtn.addEventListener("click", () => bulkSetPlacement("sticky-on"));

  const bulkFeaturedBtn = $("[data-action='bulk-featured']");
  if (bulkFeaturedBtn) bulkFeaturedBtn.addEventListener("click", () => bulkSetPlacement("featured-on"));

  function bindPlacementRail() {
    const form = $("[data-form='post']");
    if (!form) return;

    const stickyOn = $("[data-action='placement-sticky-on']");
    const stickyOff = $("[data-action='placement-sticky-off']");
    const featuredOn = $("[data-action='placement-featured-on']");
    const featuredOff = $("[data-action='placement-featured-off']");

    if (stickyOn) {
      stickyOn.addEventListener("click", () => {
        const slug = (form.slug.value.trim() || slugify(form.title.value)).toLowerCase();
        const fm = collectFormFrontmatter(form);
        fm.sticky = true;
        if (!reconcileDualPlacement(fm, "sticky")) return;
        if (!confirmSlotReplace("sticky", findOtherSticky(slug))) return;
        if (form.sticky) form.sticky.checked = true;
        if (form.featured && !fm.featured) form.featured.checked = false;
        updatePlacementUI();
      });
    }
    if (stickyOff) {
      stickyOff.addEventListener("click", () => {
        if (form.sticky) form.sticky.checked = false;
        updatePlacementUI();
      });
    }
    if (featuredOn) {
      featuredOn.addEventListener("click", () => {
        const slug = (form.slug.value.trim() || slugify(form.title.value)).toLowerCase();
        const fm = collectFormFrontmatter(form);
        fm.featured = true;
        if (!reconcileDualPlacement(fm, "featured")) return;
        if (!confirmSlotReplace("featured", findOtherFeatured(slug))) return;
        if (form.featured) form.featured.checked = true;
        if (form.sticky && !fm.sticky) form.sticky.checked = false;
        updatePlacementUI();
      });
    }
    if (featuredOff) {
      featuredOff.addEventListener("click", () => {
        if (form.featured) form.featured.checked = false;
        updatePlacementUI();
      });
    }
  }
  bindPlacementRail();

  const logoutBtn = $("[data-action='logout']");
  if (logoutBtn) logoutBtn.addEventListener("click", async () => {
    if (!confirm("Đăng xuất khỏi CMS?")) return;
    await logoutRemote();
    currentUser = null;
    const bar = $("[data-user-bar]");
    if (bar) bar.hidden = true;
    showView("login");
  });

  const newBtn = $("[data-action='new']");
  if (newBtn) newBtn.addEventListener("click", () => openEditor(null));

  // ============= AUTO-SLUG FROM TITLE =============
  // Khi user gõ tiêu đề, tự fill slug field theo realtime. Nếu user đã sửa slug
  // bằng tay → khoá auto-fill (slugLocked=true). Xoá rỗng slug → mở khoá lại.
  const titleInput = $("[name='title']");
  const slugInput = $("[name='slug']");
  let slugLocked = false;

  titleInput.addEventListener("input", () => {
    if (slugLocked) return;
    slugInput.value = slugify(titleInput.value);
  });
  slugInput.addEventListener("input", () => {
    // User chủ động sửa slug → khoá auto-fill. Xoá rỗng → mở khoá.
    slugLocked = slugInput.value.trim().length > 0;
  });

  // ============= CATEGORY DROPDOWN =============
  // Source of truth: categories.json trong repo (qua backend
  // /api/categories/list). Bake từ <script id="categories-data"> chỉ làm
  // fallback ban đầu cho FCP nhanh trước khi fetch API trả về.
  // Save bài → backend auto-add nếu category chưa tồn tại trong JSON.
  let knownCategories = [];
  try {
    const raw = document.getElementById("categories-data");
    if (raw) knownCategories = JSON.parse(raw.textContent || "[]");
  } catch (e) { knownCategories = []; }
  if (!knownCategories.includes("Posting")) knownCategories.unshift("Posting");

  async function fetchCategoriesFromBackend() {
    if (!AUTH_API) return;
    const sid = getSid();
    if (!sid) return;
    try {
      const res = await fetch(AUTH_API + "/api/categories/list", {
        headers: { "Authorization": "Bearer " + sid },
        credentials: "include",
        cache: "no-store",
      });
      if (res.status === 401) { clearSid(); return; }
      if (!res.ok) return;
      const data = await res.json();
      if (Array.isArray(data.categories) && data.categories.length) {
        knownCategories = data.categories.slice();
        if (!knownCategories.includes("Posting")) knownCategories.unshift("Posting");
        // Re-render dropdown giữ selection hiện tại
        const cur = catSelect ? catSelect.value : "Posting";
        rebuildCategoryOptions(cur);
      }
    } catch (e) { /* network fail → giữ baked list */ }
  }

  async function saveCategoryToBackend(name) {
    if (!AUTH_API) throw new Error("Backend chưa cấu hình");
    const sid = getSid();
    if (!sid) throw new Error("Phiên hết hạn");
    const res = await fetch(AUTH_API + "/api/categories/add", {
      method: "POST",
      headers: {
        "Authorization": "Bearer " + sid,
        "Content-Type": "application/json",
      },
      credentials: "include",
      body: JSON.stringify({ name }),
    });
    if (res.status === 401) { clearSid(); throw new Error("Phiên hết hạn"); }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "API lỗi");
    return data; // {ok, categories, added}
  }

  const catSelect = $("[data-category-select]");
  const catNewWrap = $("[data-category-new-wrap]");
  const catNewInput = $("[data-category-new]");
  const catAddBtn = $("[data-action='new-category']");

  let inNewMode = false; // true khi user đang gõ category mới

  function rebuildCategoryOptions(selected) {
    catSelect.innerHTML = knownCategories.map((c) =>
      `<option value="${escapeHtml(c)}"${c === selected ? " selected" : ""}>${escapeHtml(categoryLabel(c))}</option>`
    ).join("");
    // Nếu category đã chọn không nằm trong list (đã bị xoá khỏi taxonomy) → thêm vào
    if (selected && !knownCategories.includes(selected)) {
      catSelect.insertAdjacentHTML("afterbegin",
        `<option value="${escapeHtml(selected)}" selected>${escapeHtml(categoryLabel(selected))} (cũ)</option>`);
    }
    toggleMomoField(selected || catSelect.value || "Posting");
    exitNewMode();
  }

  function enterNewMode() {
    inNewMode = true;
    catNewWrap.hidden = false;
    catSelect.disabled = true;
    catNewInput.required = true;
    catNewInput.focus();
    catAddBtn.textContent = "✕ Huỷ";
    catAddBtn.title = "Huỷ tạo category mới";
  }

  function exitNewMode() {
    inNewMode = false;
    catNewWrap.hidden = true;
    catSelect.disabled = false;
    catNewInput.required = false;
    catNewInput.value = "";
    catAddBtn.textContent = "＋ Mới";
    catAddBtn.title = "Thêm category mới";
  }

  catAddBtn.addEventListener("click", () => {
    if (inNewMode) exitNewMode();
    else enterNewMode();
  });

  // ============= LƯU CATEGORY → BACKEND =============
  const catSaveBtn = $("[data-action='save-category']");
  const catSaveMsg = $("[data-category-save-msg]");

  function setCatSaveMsg(msg, type) {
    if (!catSaveMsg) return;
    catSaveMsg.className = "editor-category-new-hint editor-category-new-hint--" + (type || "info");
    catSaveMsg.textContent = msg || "";
  }

  if (catSaveBtn) {
    catSaveBtn.addEventListener("click", async function () {
      const name = (catNewInput.value || "").trim();
      if (!name) {
        setCatSaveMsg("Nhập tên category trước.", "error");
        return;
      }
      catSaveBtn.disabled = true;
      setCatSaveMsg("Đang lưu lên repo…", "info");
      try {
        const data = await saveCategoryToBackend(name);
        if (Array.isArray(data.categories)) {
          knownCategories = data.categories.slice();
          if (!knownCategories.includes("Posting")) knownCategories.unshift("Posting");
        }
        // Rebuild dropdown với category mới được chọn ngay
        rebuildCategoryOptions(name);
        setCatSaveMsg(
          data.added
            ? "✓ Đã lưu '" + name + "' vào categories.json"
            : "ℹ Category '" + name + "' đã tồn tại — đã chọn",
          data.added ? "success" : "info"
        );
        catNewInput.value = "";
        catSelect.value = name;
        // Tự thoát new-mode sau ~1s để user thấy success message
        setTimeout(function () { exitNewMode(); setCatSaveMsg("", "info"); }, 1200);
      } catch (err) {
        setCatSaveMsg("✗ " + err.message, "error");
      } finally {
        catSaveBtn.disabled = false;
      }
    });
  }

  function getSelectedCategory() {
    if (inNewMode) {
      const v = catNewInput.value.trim();
      if (v && !knownCategories.includes(v)) knownCategories.push(v);
      return v || "Posting";
    }
    return catSelect.value || "Posting";
  }

  if (catSelect) {
    catSelect.addEventListener("change", function () {
      toggleMomoField(catSelect.value);
    });
  }
  if (catNewInput) {
    catNewInput.addEventListener("input", function () {
      if (inNewMode) toggleMomoField(catNewInput.value.trim() || "Posting");
    });
  }

  // ============= EDITOR VIEW =============
  function openEditor(path) {
    const form = $("[data-form='post']");
    form.reset();
    $("[data-target='save-status']").textContent = "";
    hideDraftBanner(); // reset banner cũ từ session trước
    // Bài mới chưa có slug → mở khoá auto-fill. Edit bài cũ sẽ set lại bên dưới.
    slugLocked = false;

    if (!path) {
      // New post
      $("[data-target='edit-title']").textContent = "VIẾT BÀI MỚI";
      $("[data-action='delete']").hidden = true;
      form.date.value = todayIso();
      state.editing = null;
      lastDraftSlug = null; // bài mới chưa có slug
      rebuildCategoryOptions("Posting");
      const momoInputNew = form.querySelector("[name='momo_link']");
      if (momoInputNew) momoInputNew.value = "";
      toggleMomoField("Posting");
      updateCounter();
      lastRenderedBody = null;
      renderPreview();
      updatePlacementUI();
      showView("edit");
      return;
    }

    // Edit existing
    $("[data-target='edit-title']").textContent = "SỬA BÀI";
    $("[data-action='delete']").hidden = false;
    setStatus("save-status", "Đang tải nội dung…", "info");
    showView("edit");

    getPost(path).then((data) => {
      const { fm, body } = parseFrontmatter(data.content);
      // originalDate = giá trị `date` gốc (có thể kèm giờ) → bảo toàn khi lưu lại,
      // vì <input type="date"> chỉ giữ phần ngày, không có giờ.
      state.editing = { path: data.path, sha: data.sha, originalDate: fm.date, wasFeatured: fm.featured, featuredAt: fm.featured_at, wasSticky: fm.sticky };
      // Edit bài đã có slug → khoá auto-fill để không phá URL hiện tại khi đổi title
      slugLocked = true;
      form.title.value = fm.title;
      // Loại prefix folder (content/posting/) khỏi slug input
      const slug = data.path.replace(new RegExp("^" + CONTENT_DIR + "/"), "").replace(/\.md$/, "");
      form.slug.value = slug;
      lastDraftSlug = slug; // track để autosave xoá draft cũ khi user đổi slug
      // <input type="date"> chỉ nhận YYYY-MM-DD → cắt phần giờ để không bị xoá trắng.
      form.date.value = String(fm.date || "").slice(0, 10);
      rebuildCategoryOptions(fm.category);
      form.tags.value = fm.tags.join(", ");
      form.thumbnail.value = fm.thumbnail;
      form.featured.checked = fm.featured;
      if (form.sticky) form.sticky.checked = fm.sticky;
      const momoInput = form.querySelector("[name='momo_link']");
      if (momoInput) {
        momoInput.value = isPremiumCategory(fm.category) ? (fm.momo_payment_link || "") : "";
      }
      toggleMomoField(fm.category);
      form.body.value = body.trim();
      updateCounter();
      lastRenderedBody = null;
      renderPreview();
      updatePlacementUI();
      setStatus("save-status", "✓ Đã tải bài", "success");
      // Check có draft chưa lưu cho slug này không — hiển thị banner khôi phục
      checkDraftFor(slug);
    }).catch((err) => {
      setStatus("save-status", "✗ " + err.message, "error");
    });
  }

  $("[data-form='post']").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;

    const fm = collectFormFrontmatter(form);
    const body = form.body.value;
    const slug = (form.slug.value.trim() || slugify(fm.title));

    if (!slug) { alert("Cần tiêu đề hoặc slug"); return; }
    if (!fm.title || !fm.date) { alert("Thiếu tiêu đề hoặc ngày"); return; }
    if (!validatePlacementBeforeSave(fm, slug)) return;
    syncPlacementCheckboxes(form, fm);

    // Validate body có nội dung text thực sự — tránh case Zola không trích được
    // summary → page.summary = null → templates crash với `striptags` filter →
    // toàn bộ site không build → bài viết không lên web.
    // Bỏ markdown markup (URL, ![]() image, #, *, -, [], code fence) trước khi đếm.
    const plainText = body
      .replace(/```[\s\S]*?```/g, "")           // code blocks
      .replace(/!\[[^\]]*\]\([^)]*\)/g, "")     // images
      .replace(/\[[^\]]*\]\([^)]*\)/g, "")      // links
      .replace(/https?:\/\/\S+/g, "")           // raw URLs
      .replace(/[#*_>`\-+|]/g, "")              // markdown markup chars
      .replace(/\s+/g, " ")
      .trim();
    if (plainText.length < 50) {
      alert(
        "Nội dung quá ngắn (cần ≥ 50 ký tự text, hiện có " + plainText.length + ").\n\n" +
        "Bài chỉ có URL/hình → Zola không trích được summary → build fail → " +
        "site không update. Hãy thêm vài câu mô tả."
      );
      return;
    }

    const path = CONTENT_DIR + "/" + slug + ".md";
    const content = buildFrontmatter(fm, body);
    const message = state.editing ? "Sửa bài: " + fm.title : "Bài mới: " + fm.title;

    setStatus("save-status", "Đang tạo file .md…", "info");
    try {
      await putPost(path, content, state.editing ? state.editing.sha : null, message);
      setStatus("save-status",
        "✓ File '" + slug + ".md' đã tải về. Chạy local: " +
        "git add " + path + " && git commit -m \"" + message + "\" && git push",
        "success");
      applySavedPostState(slug, fm);
    } catch (err) {
      setStatus("save-status", "✗ " + err.message, "error");
    }
  });

  // ============= PUBLISH TO GITHUB =============
  // Đẩy bài trực tiếp lên repo qua backend /cms/save-post. Backend dùng
  // access_token GitHub (Redis-side) để PUT content/posting/{slug}.md.
  // Sau push: GitHub Actions auto-build + deploy ~1-2 phút.
  async function handlePublishClick(e) {
    e.preventDefault();
    const form = $("[data-form='post']");
    if (!form.reportValidity()) return; // browser native validation

    const sid = getSid();
    if (!AUTH_API) {
      alert("Backend chưa cấu hình.");
      return;
    }
    // KHÔNG chặn cứng khi thiếu sid: phiên có thể còn sống qua cookie HttpOnly
    // (credentials:include). Backend trả 401 nếu thật sự hết hạn →
    // handleSessionExpired() lưu draft + báo + về login.

    const fm = collectFormFrontmatter(form);
    const body = form.body.value;
    const slug = (form.slug.value.trim() || slugify(fm.title)).toLowerCase();
    if (!slug || !fm.title || !fm.date) {
      alert("Thiếu tiêu đề, slug hoặc ngày.");
      return;
    }
    if (!validatePlacementBeforeSave(fm, slug)) return;
    syncPlacementCheckboxes(form, fm);

    // Same body length validate as Tải .md submit
    const plainText = body
      .replace(/```[\s\S]*?```/g, "")
      .replace(/!\[[^\]]*\]\([^)]*\)/g, "")
      .replace(/\[[^\]]*\]\([^)]*\)/g, "")
      .replace(/https?:\/\/\S+/g, "")
      .replace(/[#*_>`\-+|]/g, "")
      .replace(/\s+/g, " ")
      .trim();
    if (plainText.length < 50) {
      alert("Nội dung quá ngắn (cần ≥ 50 ký tự).");
      return;
    }

    const content = buildFrontmatter(fm, body);
    const message = state.editing
      ? "CMS: cập nhật bài '" + fm.title + "'"
      : "CMS: bài mới '" + fm.title + "'";

    if (!confirm("Đăng bài '" + fm.title + "' lên GitHub?\n\nFile: " +
                 CONTENT_DIR + "/" + slug + ".md\n\nGitHub Actions sẽ tự build + deploy ~1-2 phút.")) {
      return;
    }

    setStatus("save-status", "Đang đẩy lên GitHub…", "info");

    try {
      const headers = { "Content-Type": "application/json" };
      if (sid) headers["Authorization"] = "Bearer " + sid;
      const res = await fetch(AUTH_API + "/cms/save-post", {
        method: "POST",
        headers: headers,
        credentials: "include",
        body: JSON.stringify({ slug, content, message }),
      });

      if (res.status === 401) {
        handleSessionExpired(); // lưu draft + báo + về login
        return;
      }
      if (res.status === 403) {
        setStatus("save-status",
          "✗ GitHub OAuth thiếu scope 'public_repo'. Đăng xuất và đăng nhập lại để cấp quyền.",
          "error");
        return;
      }

      const data = await res.json();
      if (!res.ok) {
        setStatus("save-status", "✗ " + (data.detail || "GitHub API lỗi"), "error");
        return;
      }

      const commitLink = data.commit_url
        ? ' · <a href="' + data.commit_url + '" target="_blank" rel="noopener">Xem commit</a>'
        : "";
      const statusEl = $("[data-target='save-status']");
      statusEl.className = "editor-status editor-status--success";
      statusEl.innerHTML = "✓ Đã " + (data.action === "updated" ? "cập nhật" : "đăng mới") +
        " <strong>" + escapeHtml(data.path) + "</strong>" + formatPlacementSaveNote(data) + ". " +
        "Deploy ETA: " + escapeHtml(data.deploy_eta) + commitLink;

      applySavedPostState(slug, fm);
      const railStatus = $("[data-rail-status]");
      if (railStatus) {
        railStatus.textContent = "Đã đăng — deploy ~1–2 phút.";
      }
    } catch (err) {
      setStatus("save-status", "✗ Lỗi mạng: " + err.message, "error");
    }
  }

  $$("[data-action='publish']").forEach((btn) => {
    btn.addEventListener("click", handlePublishClick);
  });

  $("[data-action='delete']").addEventListener("click", async () => {
    if (!state.editing) return;
    if (!confirm("Xoá bài này vĩnh viễn?")) return;
    try {
      await deletePost(state.editing.path, state.editing.sha, "Xoá bài");
      // Remove khỏi state.posts ngay (bake stale tới khi rebuild).
      const deletedSlug = state.editing.path
        .replace(new RegExp("^" + CONTENT_DIR + "/"), "")
        .replace(/\.md$/, "");
      state.posts = state.posts.filter((p) => p.slug !== deletedSlug);
      invalidateListCache();
      discardDraft(deletedSlug); // dọn draft tương ứng
      setStatus("save-status", "✓ Đã xoá", "success");
      showView("list");
      renderPostList();
    } catch (err) {
      setStatus("save-status", "✗ " + err.message, "error");
    }
  });

  $("[data-action='back']").addEventListener("click", () => {
    enterDashboard();
  });

  // ============= MARKDOWN TOOLBAR + SHORTCUTS + COUNTER =============
  const bodyTextarea = $("[name='body']");

  // Bọc/unbọc selection bằng prefix+suffix. Toggle off nếu selection đã wrapped.
  // Selection rỗng → insert placeholder + highlight để user gõ đè ngay.
  function wrapInline(prefix, suffix, placeholder) {
    const ta = bodyTextarea;
    const start = ta.selectionStart;
    const end = ta.selectionEnd;
    const sel = ta.value.slice(start, end);
    const before = ta.value.slice(0, start);
    const after = ta.value.slice(end);

    if (sel.length >= prefix.length + suffix.length &&
        sel.startsWith(prefix) && sel.endsWith(suffix)) {
      // Toggle off: bỏ wrap
      const inner = sel.slice(prefix.length, sel.length - suffix.length);
      ta.value = before + inner + after;
      ta.selectionStart = start;
      ta.selectionEnd = start + inner.length;
    } else {
      const insert = sel || placeholder;
      ta.value = before + prefix + insert + suffix + after;
      if (sel) {
        ta.selectionStart = start + prefix.length;
        ta.selectionEnd = end + prefix.length;
      } else {
        ta.selectionStart = start + prefix.length;
        ta.selectionEnd = start + prefix.length + placeholder.length;
      }
    }
    ta.focus();
    ta.dispatchEvent(new Event("input", { bubbles: true }));
  }

  // Toggle line-prefix (heading/quote/list). Mở rộng phạm vi sang toàn bộ line
  // chứa cursor → strip nếu đã có prefix, thêm vào nếu chưa.
  function togglePrefix(prefix) {
    const ta = bodyTextarea;
    const start = ta.selectionStart;
    const end = ta.selectionEnd;
    const value = ta.value;

    const lineStart = value.lastIndexOf("\n", start - 1) + 1;
    let lineEnd = value.indexOf("\n", end);
    if (lineEnd === -1) lineEnd = value.length;

    const line = value.slice(lineStart, lineEnd);
    const newLine = line.startsWith(prefix) ? line.slice(prefix.length) : prefix + line;

    ta.value = value.slice(0, lineStart) + newLine + value.slice(lineEnd);
    const delta = newLine.length - line.length;
    ta.selectionStart = Math.max(lineStart, start + delta);
    ta.selectionEnd = end + delta;
    ta.focus();
    ta.dispatchEvent(new Event("input", { bubbles: true }));
  }

  const MD_ACTIONS = {
    bold:      { type: "inline", prefix: "**",    suffix: "**",     placeholder: "đậm" },
    italic:    { type: "inline", prefix: "*",     suffix: "*",      placeholder: "nghiêng" },
    code:      { type: "inline", prefix: "`",     suffix: "`",      placeholder: "code" },
    link:      { type: "inline", prefix: "[",     suffix: "](url)", placeholder: "text" },
    image:     { type: "inline", prefix: "![",    suffix: "](url)", placeholder: "alt" },
    codeblock: { type: "inline", prefix: "```\n", suffix: "\n```",  placeholder: "code" },
    heading:   { type: "prefix", prefix: "## " },  // legacy alias cho toolbar button
    h1:        { type: "prefix", prefix: "# " },
    h2:        { type: "prefix", prefix: "## " },
    h3:        { type: "prefix", prefix: "### " },
    quote:     { type: "prefix", prefix: "> " },
    ul:        { type: "prefix", prefix: "- " },
    ol:        { type: "prefix", prefix: "1. " },
  };

  function applyMdAction(action) {
    const cfg = MD_ACTIONS[action];
    if (!cfg) return;
    if (cfg.type === "inline") wrapInline(cfg.prefix, cfg.suffix, cfg.placeholder);
    else togglePrefix(cfg.prefix);
  }

  $$("[data-md]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      applyMdAction(btn.dataset.md);
    });
  });

  // Keyboard shortcuts — scope: editForm only (tránh hijack browser khi user
  // ở list/login view). Ctrl+S = save anywhere trong form. Ctrl+B/I/K/E = MD
  // chỉ khi textarea body focused. Ctrl+H KHÔNG bind vì xung đột history nguy hiểm.
  const MD_SHORTCUTS = { b: "bold", i: "italic", k: "link", e: "code" };
  const editForm = $("[data-form='post']");

  editForm.addEventListener("keydown", (e) => {
    if (!(e.ctrlKey || e.metaKey)) return;
    if (e.altKey || e.shiftKey) return;
    const key = e.key.toLowerCase();

    if (key === "s") {
      e.preventDefault();
      if (typeof editForm.requestSubmit === "function") editForm.requestSubmit();
      else editForm.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
      return;
    }

    if (document.activeElement !== bodyTextarea) return;
    if (MD_SHORTCUTS[key]) {
      e.preventDefault();
      applyMdAction(MD_SHORTCUTS[key]);
    }
  });

  // Counter realtime — words + chars. Warning state khi <MIN_CHARS để user
  // thấy lỗi trước khi bấm Save (đồng bộ với threshold 50 ở validate submit).
  const MIN_CHARS = 50;
  const counterWords = $("[data-counter-words]");
  const counterChars = $("[data-counter-chars]");
  const counterHint  = $("[data-counter-hint]");
  const counterRoot  = $("[data-counter]");

  function updateCounter() {
    const val = bodyTextarea.value;
    const trimmed = val.trim();
    const words = trimmed ? trimmed.split(/\s+/).filter(Boolean).length : 0;
    const chars = val.length;
    if (counterWords) counterWords.textContent = words.toLocaleString("vi-VN");
    if (counterChars) counterChars.textContent = chars.toLocaleString("vi-VN");

    if (counterRoot) {
      const isWarn = chars > 0 && chars < MIN_CHARS;
      counterRoot.classList.toggle("editor-counter--warning", isWarn);
      if (counterHint) {
        if (isWarn) {
          counterHint.textContent = "(cần thêm " + (MIN_CHARS - chars) + ")";
          counterHint.hidden = false;
        } else {
          counterHint.hidden = true;
        }
      }
    }
  }
  bodyTextarea.addEventListener("input", updateCounter);
  updateCounter(); // initial render khi load page

  // ============= EDITOR MODE (write / split / preview) =============
  // Mode-class system thay cho hidden attr juggling. CSS điều khiển pane visibility,
  // toolbar/counter ẩn ở preview mode qua media query + mode class.
  const MODE_KEY = "zola-cms-editor-mode";
  const contentWrap = $("[data-content-wrap]");

  function getInitialMode() {
    const saved = localStorage.getItem(MODE_KEY);
    if (saved === "write" || saved === "split" || saved === "preview") return saved;
    // Default: split trên desktop ≥900px, write trên mobile (split không vừa)
    return window.matchMedia("(min-width: 900px)").matches ? "split" : "write";
  }

  function setEditorMode(mode) {
    if (!contentWrap) return;
    contentWrap.classList.remove(
      "editor-content-wrap--mode-write",
      "editor-content-wrap--mode-split",
      "editor-content-wrap--mode-preview"
    );
    contentWrap.classList.add("editor-content-wrap--mode-" + mode);
    $$(".editor-tab").forEach((t) => {
      t.classList.toggle("is-active", t.dataset.tab === mode);
    });
    try { localStorage.setItem(MODE_KEY, mode); } catch (e) {}
    // Force re-render preview vì mode mới có thể vừa show preview
    lastRenderedBody = null;
    renderPreview();
  }

  // ============= LIVE PREVIEW RENDER (debounce 500ms) =============
  // Reuse window.marked (loaded từ CDN ở editor.html), không thêm dependency.
  // Render no-op khi mode = write (preview không visible) → 0 waste compute.

  // Security: sanitize HTML từ marked.parse trước khi innerHTML. marked@12 đã
  // bỏ built-in sanitizer; body markdown được author kiểm soát NHƯNG nếu repo
  // bị compromise (leaked PAT), attacker có thể push markdown chứa <script>
  // → khi admin mở /editor/ → script chạy trong context có PAT → exfil PAT.
  // Helper này strip script/iframe/object/embed + on* attrs + javascript:/data:
  // URLs. Không bulletproof bằng DOMPurify nhưng đủ defense-in-depth.
  function sanitizeHtml(html) {
    return String(html)
      .replace(/<script\b[\s\S]*?<\/script\s*>/gi, "")
      .replace(/<style\b[\s\S]*?<\/style\s*>/gi, "")
      .replace(/<(iframe|object|embed|link|meta|base|form)\b[\s\S]*?>/gi, "")
      .replace(/\s+on\w+\s*=\s*"[^"]*"/gi, "")
      .replace(/\s+on\w+\s*=\s*'[^']*'/gi, "")
      .replace(/\s+on\w+\s*=\s*[^\s>]+/gi, "")
      .replace(/\s+(href|src|action|formaction)\s*=\s*"\s*(javascript|data|vbscript):[^"]*"/gi, ' $1="#"')
      .replace(/\s+(href|src|action|formaction)\s*=\s*'\s*(javascript|data|vbscript):[^']*'/gi, " $1='#'");
  }

  let lastRenderedBody = null;
  function renderPreview() {
    if (!contentWrap) return;
    if (contentWrap.classList.contains("editor-content-wrap--mode-write")) return;
    const body = bodyTextarea.value;
    if (body === lastRenderedBody) return;
    lastRenderedBody = body;
    const previewPane = $("[data-tab-pane='preview']");
    if (!previewPane) return;

    // Fallback: nếu marked.min.js fail load (CDN down, SRI mismatch, CSP block,
    // network unstable), preview vẫn hiển thị raw text + warning thay vì câm
    // lặng. Trước đây silent return → user tưởng preview chết.
    if (!window.marked) {
      previewPane.innerHTML =
        '<div class="editor-preview__warn">⚠ marked.min.js chưa load. ' +
        'Kiểm tra Console + Network tab. Tạm thời hiển thị raw text:</div>' +
        '<pre class="editor-preview__raw">' + escapeHtml(body || "(rỗng)") + '</pre>';
      // Retry render khi marked load sau 500ms (defer + slow network)
      setTimeout(() => { if (window.marked) { lastRenderedBody = null; renderPreview(); } }, 500);
      return;
    }

    try {
      const raw = window.marked.parse(body || "*(rỗng)*");
      previewPane.innerHTML = sanitizeHtml(raw);
    } catch (e) {
      previewPane.innerHTML = '<em class="editor-preview__warn">Lỗi parse markdown: ' +
        escapeHtml(e.message) + '</em>';
    }
  }
  const debouncedRender = debounce(renderPreview, 500);

  bodyTextarea.addEventListener("input", debouncedRender);

  // Trigger lại 1 lần sau khi defer scripts đã chắc chắn load xong — phòng case
  // editor.js init trước marked.min.js (rare nhưng có thể nếu CDN slow).
  if (document.readyState === "complete") {
    setTimeout(() => { lastRenderedBody = null; renderPreview(); }, 100);
  } else {
    window.addEventListener("load", () => {
      lastRenderedBody = null;
      renderPreview();
    });
  }

  $$(".editor-tab").forEach((tab) => {
    tab.addEventListener("click", () => setEditorMode(tab.dataset.tab));
  });

  // ============= AUTOSAVE DRAFT (debounce 1s) =============
  // Lưu mọi field hiện tại vào localStorage theo slug. Skip nếu slug rỗng
  // (không có key để truy xuất sau). Track lastDraftSlug để dọn draft cũ
  // khi user đổi title → slug đổi theo (tránh sinh ghost draft).
  const DRAFT_PREFIX = "zola-cms-draft-";
  let lastDraftSlug = null;

  function autosaveDraft() {
    const slug = ($("[name='slug']").value || "").trim();
    if (!slug) return;
    if (lastDraftSlug && lastDraftSlug !== slug) {
      try { localStorage.removeItem(DRAFT_PREFIX + lastDraftSlug); } catch (e) {}
    }
    lastDraftSlug = slug;
    const form = editForm;
    const fmDraft = collectFormFrontmatter(form);
    const payload = {
      timestamp: Date.now(),
      title: form.title.value,
      slug: slug,
      date: form.date.value,
      category: fmDraft.category,
      tags: form.tags.value,
      thumbnail: form.thumbnail.value,
      featured: form.featured.checked,
      sticky: form.sticky ? form.sticky.checked : false,
      momo_link: fmDraft.momo_payment_link || "",
      body: form.body.value,
    };
    try {
      localStorage.setItem(DRAFT_PREFIX + slug, JSON.stringify(payload));
    } catch (e) { /* quota exceeded — silent fail */ }
  }
  const debouncedAutosave = debounce(autosaveDraft, 1000);

  // Listen mọi thay đổi form (input/change), skip click trên draft-banner buttons
  ["input", "change"].forEach((evt) => {
    editForm.addEventListener(evt, (e) => {
      if (e.target && e.target.closest && e.target.closest("[data-draft-banner]")) return;
      debouncedAutosave();
    });
  });

  // ============= DRAFT RECOVERY BANNER =============
  const draftBanner = $("[data-draft-banner]");
  const draftBannerMsg = $("[data-draft-banner-msg]");
  let pendingDraft = null;

  function formatAgo(timestamp) {
    const mins = Math.round((Date.now() - timestamp) / 60000);
    if (mins < 1) return "vừa xong";
    if (mins < 60) return mins + " phút trước";
    const hours = Math.round(mins / 60);
    if (hours < 24) return hours + " giờ trước";
    return Math.round(hours / 24) + " ngày trước";
  }

  function showDraftBanner(draft) {
    if (!draftBanner || !draftBannerMsg) return;
    pendingDraft = draft;
    const ts = new Date(draft.timestamp);
    const timeStr = (window.ZolaDateTime && window.ZolaDateTime.formatDisplayDateTime(draft.timestamp))
      || draft.timestamp;
    draftBannerMsg.textContent = "Có bản nháp chưa lưu (lúc " + timeStr + ", " + formatAgo(draft.timestamp) + ")";
    draftBanner.hidden = false;
  }

  function hideDraftBanner() {
    if (draftBanner) draftBanner.hidden = true;
    pendingDraft = null;
  }

  function applyDraftToForm(draft) {
    const form = editForm;
    form.title.value = draft.title || "";
    form.slug.value = draft.slug || "";
    form.date.value = draft.date || "";
    form.tags.value = draft.tags || "";
    form.thumbnail.value = draft.thumbnail || "";
    form.featured.checked = !!draft.featured;
    if (form.sticky) form.sticky.checked = !!draft.sticky;
    form.body.value = draft.body || "";
    rebuildCategoryOptions(draft.category || "Posting");
    const momoInput = form.querySelector("[name='momo_link']");
    if (momoInput) {
      momoInput.value = isPremiumCategory(draft.category) ? (draft.momo_link || "") : "";
    }
    toggleMomoField(draft.category || "Posting");
    slugLocked = true; // draft đã có slug → khoá auto-fill từ title
    updateCounter();
    lastRenderedBody = null;
    renderPreview();
  }

  function checkDraftFor(slug) {
    if (!slug) return;
    try {
      const raw = localStorage.getItem(DRAFT_PREFIX + slug);
      if (!raw) return;
      const draft = JSON.parse(raw);
      if (!draft || !draft.timestamp || !draft.slug) return;
      showDraftBanner(draft);
    } catch (e) { /* silent */ }
  }

  function discardDraft(slug) {
    if (!slug) return;
    try { localStorage.removeItem(DRAFT_PREFIX + slug); } catch (e) {}
  }

  $("[data-action='draft-restore']").addEventListener("click", () => {
    if (pendingDraft) applyDraftToForm(pendingDraft);
    hideDraftBanner();
  });

  $("[data-action='draft-discard']").addEventListener("click", () => {
    if (pendingDraft) discardDraft(pendingDraft.slug);
    hideDraftBanner();
  });

  // ============= SLASH COMMAND MENU =============
  // Gõ "/" ở line-start hoặc sau whitespace → hiện floating menu suggest
  // các block markdown. Tận dụng applyMdAction đã có — không duplicate wrap logic.
  // Position cursor: mirror div technique, 0 dependency.

  const SLASH_ITEMS = [
    { keys: ["h1", "heading-1"],          label: "Heading 1",     icon: "H1",  action: "h1",        hint: "#" },
    { keys: ["h2", "heading-2", "heading"], label: "Heading 2",   icon: "H2",  action: "h2",        hint: "##" },
    { keys: ["h3", "heading-3"],          label: "Heading 3",     icon: "H3",  action: "h3",        hint: "###" },
    { keys: ["quote", "blockquote", "trich-dan"], label: "Quote", icon: "❝",   action: "quote",     hint: ">" },
    { keys: ["code", "inline-code"],      label: "Code inline",   icon: "</>",  action: "code",     hint: "`code`" },
    { keys: ["codeblock", "code-block", "cb"], label: "Code block", icon: "{}", action: "codeblock", hint: "```" },
    { keys: ["list", "ul", "bullet", "danh-sach"], label: "Bullet list", icon: "•", action: "ul",  hint: "-" },
    { keys: ["numbered", "ol", "ordered", "so-thu-tu"], label: "Numbered list", icon: "1.", action: "ol", hint: "1." },
    { keys: ["image", "img", "anh", "hinh"], label: "Image",      icon: "🖼",  action: "image",     hint: "![]()" },
    { keys: ["link", "url"],              label: "Link",          icon: "🔗",  action: "link",      hint: "[]()" },
    { keys: ["bold", "b", "dam"],         label: "Bold",          icon: "B",   action: "bold",      hint: "**" },
    { keys: ["italic", "i", "nghieng"],   label: "Italic",        icon: "I",   action: "italic",    hint: "*" },
  ];

  const slashState = { open: false, triggerStart: -1, filter: "", activeIndex: 0 };
  const slashMenu = $("[data-slash-menu]");
  const slashList = $("[data-slash-list]");

  // Mirror div technique — clone style của textarea vào hidden div, đo position
  // của span sentinel để lấy pixel coords của caret. Return viewport coords để
  // dùng với position:fixed (không bị scroll-offset ngoài context).
  function getCaretCoordinates(ta, caretPos) {
    const div = document.createElement("div");
    const style = window.getComputedStyle(ta);
    const props = [
      "boxSizing", "width", "height",
      "fontSize", "fontFamily", "fontWeight", "fontStyle",
      "lineHeight", "letterSpacing", "wordSpacing", "textAlign",
      "paddingTop", "paddingRight", "paddingBottom", "paddingLeft",
      "borderTopWidth", "borderRightWidth", "borderBottomWidth", "borderLeftWidth",
    ];
    props.forEach((p) => { div.style[p] = style[p]; });
    div.style.position = "absolute";
    div.style.visibility = "hidden";
    div.style.top = "-9999px";
    div.style.left = "-9999px";
    div.style.whiteSpace = "pre-wrap";
    div.style.wordWrap = "break-word";
    div.style.overflow = "hidden";

    div.textContent = ta.value.substring(0, caretPos);
    const span = document.createElement("span");
    span.textContent = "."; // sentinel để đo, không matter content
    div.appendChild(span);
    document.body.appendChild(div);

    const spanRect = span.getBoundingClientRect();
    const divRect = div.getBoundingClientRect();
    const taRect = ta.getBoundingClientRect();
    document.body.removeChild(div);

    return {
      left: taRect.left + (spanRect.left - divRect.left) - ta.scrollLeft,
      top:  taRect.top  + (spanRect.top  - divRect.top)  - ta.scrollTop,
      lineHeight: parseFloat(style.lineHeight) || 20,
    };
  }

  function getFilteredSlashItems() {
    if (!slashState.filter) return SLASH_ITEMS;
    const q = normalizeStr(slashState.filter);
    return SLASH_ITEMS.filter((item) => {
      if (normalizeStr(item.label).includes(q)) return true;
      return item.keys.some((k) => k.includes(q));
    });
  }

  function renderSlashMenu() {
    if (!slashList) return;
    const items = getFilteredSlashItems();
    if (slashState.activeIndex >= items.length) {
      slashState.activeIndex = items.length ? items.length - 1 : 0;
    }
    if (!items.length) {
      slashList.innerHTML = '<li class="editor-slash-menu__empty">Không có lệnh nào khớp</li>';
      return;
    }
    slashList.innerHTML = items.map((item, idx) =>
      '<li class="editor-slash-menu__item' + (idx === slashState.activeIndex ? ' is-active' : '') +
      '" data-slash-action="' + escapeHtml(item.action) + '" role="option"' +
      (idx === slashState.activeIndex ? ' aria-selected="true"' : '') + '>' +
        '<span class="editor-slash-menu__icon">' + escapeHtml(item.icon) + '</span>' +
        '<span class="editor-slash-menu__label">' + escapeHtml(item.label) + '</span>' +
        '<span class="editor-slash-menu__hint">' + escapeHtml(item.hint) + '</span>' +
      '</li>'
    ).join("");

    // mousedown + preventDefault giữ focus textarea (không dùng click vì click
    // làm blur textarea trước khi handler chạy).
    slashList.querySelectorAll("[data-slash-action]").forEach((li) => {
      li.addEventListener("mousedown", (e) => {
        e.preventDefault();
        selectSlashItem(li.dataset.slashAction);
      });
    });
  }

  function positionSlashMenu() {
    if (!slashMenu || !slashState.open) return;
    const coords = getCaretCoordinates(bodyTextarea, slashState.triggerStart);
    slashMenu.style.left = Math.max(8, coords.left) + "px";
    // Tentative: dưới cursor 4px
    let top = coords.top + coords.lineHeight + 4;
    slashMenu.style.top = top + "px";
    // Sau khi render, check overflow viewport bottom → flip lên trên
    const menuRect = slashMenu.getBoundingClientRect();
    if (menuRect.bottom > window.innerHeight - 8) {
      const flipped = coords.top - menuRect.height - 4;
      slashMenu.style.top = Math.max(8, flipped) + "px";
    }
    // Horizontal overflow: đẩy vào trong
    if (menuRect.right > window.innerWidth - 8) {
      const newLeft = window.innerWidth - menuRect.width - 8;
      slashMenu.style.left = Math.max(8, newLeft) + "px";
    }
  }

  function openSlashMenu(triggerStart) {
    if (!slashMenu) return;
    slashState.open = true;
    slashState.triggerStart = triggerStart;
    slashState.filter = "";
    slashState.activeIndex = 0;
    slashMenu.hidden = false;
    renderSlashMenu();
    positionSlashMenu();
  }

  function closeSlashMenu() {
    if (!slashMenu || !slashState.open) return;
    slashState.open = false;
    slashState.triggerStart = -1;
    slashState.filter = "";
    slashState.activeIndex = 0;
    slashMenu.hidden = true;
  }

  function updateSlashFilter() {
    if (!slashState.open) return;
    const ta = bodyTextarea;
    const cursorPos = ta.selectionStart;

    // Backspace xoá xuống dưới trigger → đóng menu
    if (cursorPos <= slashState.triggerStart) {
      closeSlashMenu();
      return;
    }

    const filterText = ta.value.substring(slashState.triggerStart + 1, cursorPos);
    // Whitespace hoặc newline trong filter → đóng menu (user đã thoát context "/")
    if (/[\s\n]/.test(filterText)) {
      closeSlashMenu();
      return;
    }

    slashState.filter = filterText;
    slashState.activeIndex = 0;
    renderSlashMenu();
    // Không cần re-position — giữ menu ở triggerStart để tránh nhảy theo filter
  }

  function selectSlashItem(action) {
    const ta = bodyTextarea;
    const triggerStart = slashState.triggerStart;
    const cursorPos = ta.selectionStart;

    // Xoá đoạn "/<filter>" khỏi textarea trước khi apply action
    ta.value = ta.value.slice(0, triggerStart) + ta.value.slice(cursorPos);
    ta.selectionStart = ta.selectionEnd = triggerStart;

    closeSlashMenu();
    // applyMdAction sẽ tự dispatch input event → counter + preview cập nhật
    applyMdAction(action);
  }

  // Trigger detection — input event (sau khi "/" đã vào value)
  bodyTextarea.addEventListener("input", (e) => {
    if (slashState.open) {
      updateSlashFilter();
      return;
    }
    // Chỉ trigger khi user gõ thẳng "/" (không paste, không IME compose)
    if (e.inputType !== "insertText" || e.data !== "/") return;
    const pos = bodyTextarea.selectionStart;
    const triggerPos = pos - 1; // index của "/" vừa typed
    // Trigger only khi "/" ở đầu textarea hoặc sau \n hoặc sau whitespace
    if (triggerPos === 0) {
      openSlashMenu(triggerPos);
      return;
    }
    const charBefore = bodyTextarea.value[triggerPos - 1];
    if (charBefore === "\n" || /\s/.test(charBefore)) {
      openSlashMenu(triggerPos);
    }
  });

  // Keyboard nav — bind trên bodyTextarea (capture phase trước editForm bubble)
  bodyTextarea.addEventListener("keydown", (e) => {
    if (!slashState.open) return;
    const items = getFilteredSlashItems();
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (items.length) slashState.activeIndex = (slashState.activeIndex + 1) % items.length;
      renderSlashMenu();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (items.length) slashState.activeIndex = (slashState.activeIndex - 1 + items.length) % items.length;
      renderSlashMenu();
    } else if (e.key === "Enter" || e.key === "Tab") {
      e.preventDefault();
      if (items.length) selectSlashItem(items[slashState.activeIndex].action);
    } else if (e.key === "Escape") {
      e.preventDefault();
      closeSlashMenu();
    }
  });

  // Click outside menu → đóng. Skip nếu click vào textarea (user có thể click
  // để di chuyển cursor mà vẫn giữ menu — nhưng filter sẽ stale → đóng cho gọn).
  document.addEventListener("mousedown", (e) => {
    if (!slashState.open) return;
    if (slashMenu && slashMenu.contains(e.target)) return;
    closeSlashMenu();
  });

  // Scroll viewport hoặc textarea → đóng menu (position:fixed không follow scroll)
  // Throttle scroll handler to avoid jank during high-frequency scroll events
  let lastScrollClose = 0;
  const throttledScrollClose = () => {
    const now = Date.now();
    if (now - lastScrollClose >= 100) {
      if (slashState.open) closeSlashMenu();
      lastScrollClose = now;
    }
  };
  bodyTextarea.addEventListener("scroll", throttledScrollClose);
  window.addEventListener("scroll", throttledScrollClose, { passive: true });

  // Init mode trên contentWrap — phải gọi sau khi renderPreview defined.
  setEditorMode(getInitialMode());

  // ============= URL PARAM HANDLING =============
  // Mở trực tiếp 1 bài qua ?slug=cai-dat-zola — yêu cầu session valid trước
  function checkUrlParam() {
    const params = new URLSearchParams(location.search);
    const slug = params.get("slug");
    if (slug) {
      const path = CONTENT_DIR + "/" + slug + ".md";
      openEditor(path);
      return true;
    }
    return false;
  }

  // ============= INIT — GitHub/Google OAuth Flow =============
  // Cảnh báo *_disabled chỉ hợp lệ nếu /auth/config xác nhận provider đang tắt.
  const _CONTRADICTABLE = {
    google_disabled: "google",
    google_not_configured: "google",
    github_disabled: "github",
  };
  function _isContradictedError(code, avail) {
    const p = _CONTRADICTABLE[code];
    return !!(p && avail && avail[p] === true);
  }

  async function init() {
    // 1. Consume #sid=... từ callback redirect (nếu vừa OAuth xong)
    consumeUrlHashSid();
    // 2. Consume ?auth_error=... (luôn strip param khỏi URL qua replaceState).
    //    KHÔNG hiện ngay — chờ /auth/config để bỏ cảnh báo mâu thuẫn (vd
    //    google_disabled cũ trong khi backend đã bật Google ở chế độ dual).
    const errCode = consumeUrlAuthError();

    // 3. Nếu backend chưa configure → không verify được config, hiện lỗi thô.
    if (!AUTH_API) {
      if (errCode) showLoginError(errCode);
      showLoginHint();
      showView("login");
      return;
    }

    // 4. Validate phiên qua /auth/me — thử Bearer (localStorage) RỒI cookie
    //    HttpOnly. Gọi cả khi localStorage trống: nếu cookie còn sống (vd user
    //    chỉ xoá static cache, không xoá site data) thì vẫn đăng nhập được,
    //    KHÔNG bắt login lại.
    const user = await fetchMe();
    if (user && user.__error === "backend_unreachable") {
      // Backend không kết nối → hiển thị lỗi rõ, KHÔNG redirect (chống loop).
      setStatus("[data-status]", "❌ Backend không kết nối. Vui lòng kiểm tra lại sau.", "error");
      showView("login");
      return;
    }
    if (user) {
      currentUser = user;
      populateUserBar(user);
      if (!checkUrlParam()) await enterDashboard(true);
      return;
    }
    // Hết phiên thật (cả Bearer lẫn cookie fail) → rơi xuống màn login.

    // 5. Chưa login → fetch /auth/config TRƯỚC (render đúng nút + biết provider
    //    nào đang bật), rồi mới quyết định có hiện cảnh báo *_disabled không.
    const avail = await applyAuthProviders();
    if (errCode && !_isContradictedError(errCode, avail)) {
      showLoginError(errCode);
    }
    showView("login");
  }

  // Shortcut Ctrl+Alt+9: mở manual Auto Draft workflow
  document.addEventListener("keydown", (e) => {
    if (e.ctrlKey && e.altKey && (e.key === "9" || e.key === "(")) {
      e.preventDefault();
      window.open("https://github.com/Banhang-Chogao/zola/actions/workflows/auto-draft.yml", "_blank");
      const status = document.querySelector("[data-status]");
      if (status) {
        status.textContent = 'Đã mở tab Auto Draft workflow — bấm "Run workflow" để tạo draft thủ công';
        status.className = "editor-status editor-status--info";
        setTimeout(() => { if (status) status.textContent = ""; }, 4000);
      }
    }
  });

  init();
})();
