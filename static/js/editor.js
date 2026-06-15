/**
 * Mini CMS — viết bài blog, đẩy file .md vào repo GitHub qua REST API.
 *
 * Authentication: GitHub Personal Access Token (PAT) lưu localStorage.
 * Token chỉ ở trình duyệt này, không gửi đi đâu khác (chỉ tới api.github.com).
 *
 * Workflow:
 *   1. User login bằng PAT
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
       3. Backend redirect /editor/#sid=... → JS đọc hash → sessionStorage
       4. /auth/me validate session mỗi page load
       5. Save bài = download .md (DRAFT-ONLY mode giữ nguyên từ PR #34)

     Security:
       - sid là opaque random 32-byte, KHÔNG carry info
       - access_token GitHub giữ Redis-side trên backend, KHÔNG về client
       - sessionStorage → auto-clear khi đóng tab
       - Backend TTL 2h → idle quá tự logout
       - White-list email check server-side, client KHÔNG bypass được */

  const SESSION_KEY = "zola-cms-session-id";
  const AUTH_API = (function () {
    const meta = document.querySelector('meta[name="zola-cms-auth-api"]');
    return (meta && meta.getAttribute("content")) || "";
  })();

  let currentUser = null; // { email, username, name, avatar }

  function getSid() {
    try { return sessionStorage.getItem(SESSION_KEY) || ""; }
    catch (e) { return ""; }
  }
  function setSid(sid) {
    try { sessionStorage.setItem(SESSION_KEY, sid); } catch (e) {}
  }
  function clearSid() {
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
    } catch (e) {
      return null; // network fail → coi như chưa login, không phá UI
    }
  }

  async function logoutRemote() {
    const sid = getSid();
    if (!sid || !AUTH_API) { clearSid(); return; }
    try {
      await fetch(AUTH_API + "/auth/logout", {
        method: "POST",
        headers: { "Authorization": "Bearer " + sid },
        credentials: "omit",
        keepalive: true,
      });
    } catch (e) { /* network fail OK — session client-side đã clear */ }
    clearSid();
  }

  const AUTH_ERROR_MESSAGES = {
    access_denied:                "Truy cập bị từ chối: Bạn không có quyền quản trị blog này.",
    invalid_state:                "Phiên đăng nhập hết hạn. Vui lòng thử lại.",
    missing_params:               "GitHub callback thiếu tham số. Thử lại.",
    token_exchange_failed:        "Lỗi xác thực GitHub. Thử lại sau.",
    github_unreachable:           "Không kết nối được GitHub. Kiểm tra mạng.",
    github_profile_fetch_failed:  "Không đọc được profile GitHub. Thử lại.",
  };

  function showLoginError(code) {
    const el = $("[data-login-error]");
    if (!el) return;
    el.textContent = AUTH_ERROR_MESSAGES[code] || ("Lỗi xác thực: " + code);
    el.hidden = false;
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
      avatar.alt = user.username || "";
    }
    if (name)  name.textContent  = user.name || user.username || "";
    if (email) email.textContent = user.email || "";
    bar.hidden = false;
  }

  const root = document.getElementById("editor-app");
  if (!root) return;

  // ============= STATE & UTIL =============
  let state = {
    posts: [],          // unified display list: { slug, title, date, category, featured, isNew? }
    bakeMetadata: [],   // raw bake từ <script id="posts-metadata">, immutable trong session
    editing: null,      // { path, sha, wasFeatured, featuredAt }
    filter: { query: "", sort: "date-desc" },
  };

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
  }

  // Pure: filter + sort state.posts theo state.filter, return array mới.
  function getDisplayPosts() {
    const posts = state.posts.slice();
    const q = normalizeStr(state.filter.query);
    const filtered = q ? posts.filter((p) => {
      const hay = normalizeStr((p.title || "") + " " + (p.slug || "") + " " + (p.category || ""));
      return hay.includes(q);
    }) : posts;

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

  // ============= API CALLS =============

  /* Unauth GitHub API — public repo nên READ (list contents, get file) hoạt
     động không auth. Rate limit 60 req/h cho IP unauth — đủ cho 1 user cá
     nhân chỉnh sửa bài thỉnh thoảng. WRITE (put/delete) đã chuyển sang
     download file thay vì gọi API. */
  async function api(path, opts) {
    opts = opts || {};
    const res = await fetch(API + path, {
      ...opts,
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
  async function refreshInBackground() {
    let apiSlugs = readListCache();
    if (!apiSlugs) {
      try {
        apiSlugs = await fetchPostSlugs();
        writeListCache(apiSlugs);
      } catch (e) {
        console.warn("[CMS] Background refresh failed:", e.message);
        return;
      }
    }

    const bakeBySlug = new Map(state.bakeMetadata.map((p) => [p.slug, p]));
    const localBySlug = new Map(state.posts.map((p) => [p.slug, p]));

    // Merge: ưu tiên local > bake > default. isNew=true nếu chưa có trong bake.
    state.posts = apiSlugs.map((slug) => {
      const inBake = bakeBySlug.has(slug);
      if (localBySlug.has(slug)) {
        return Object.assign({}, localBySlug.get(slug), { isNew: !inBake });
      }
      if (inBake) {
        return Object.assign({}, bakeBySlug.get(slug), { isNew: false });
      }
      return { slug, title: slug, date: "", category: "", featured: false, isNew: true };
    });
    renderPostList();
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
  function parseFrontmatter(md) {
    // TOML frontmatter giữa +++ ... +++
    const m = md.match(/^\+\+\+\n([\s\S]*?)\n\+\+\+\n?([\s\S]*)$/);
    if (!m) return { fm: {}, body: md };
    const fmText = m[1];
    const body = m[2] || "";

    const fm = { title: "", date: "", category: "Posting", tags: [], thumbnail: "", featured: false, featured_at: "" };

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
    fmText += "+++\n\n";
    return fmText + body;
  }

  // ============= LOGIN BUTTON → REDIRECT GITHUB OAUTH =============
  const loginBtn = $("[data-action='github-login']");
  if (loginBtn) {
    loginBtn.addEventListener("click", function () {
      if (!AUTH_API) { showLoginHint(); return; }
      const returnTo = location.pathname + location.search;
      location.href = AUTH_API + "/auth/login?return_to=" + encodeURIComponent(returnTo);
    });
  }

  let bakeLoaded = false;
  function enterDashboard(force) {
    showView("list");

    // Lần đầu vào: load bake → render instant (0ms). Lần sau giữ state.posts hiện có
    // để preserve local edits chưa propagate qua background refresh.
    if (!bakeLoaded) {
      state.bakeMetadata = loadBakeMetadata();
      state.posts = state.bakeMetadata.slice();
      bakeLoaded = true;
    }
    renderPostList();
    setStatus("[data-status]", state.posts.length + " bài viết", "info");

    if (force) invalidateListCache();
    // Idle delay 500ms cho first paint không bị block. Force = fetch ngay.
    setTimeout(() => refreshInBackground(), force ? 0 : 500);
    // Fetch categories tươi từ repo (categories.json). Run idle parallel.
    setTimeout(() => fetchCategoriesFromBackend(), 200);
  }

  // ============= LIST VIEW =============
  function renderPostList() {
    const tbody = $("[data-target='post-rows']");
    const counter = $("[data-target='post-count']");
    const displayPosts = getDisplayPosts();

    if (counter) counter.textContent = displayPosts.length + "/" + state.posts.length;

    if (!state.posts.length) {
      tbody.innerHTML = '<tr><td colspan="4" class="editor-empty">Chưa có bài nào. Click "+ Viết bài mới".</td></tr>';
      return;
    }
    if (!displayPosts.length) {
      tbody.innerHTML = '<tr><td colspan="4" class="editor-empty">Không có bài khớp.</td></tr>';
      return;
    }

    tbody.innerHTML = displayPosts.map((p) => {
      const badges = [];
      if (p.featured) badges.push('<span class="editor-badge editor-badge--featured" title="Bài nổi bật">⭐</span>');
      if (p.isNew) badges.push('<span class="editor-badge editor-badge--new" title="Vừa publish, đang build (~1 phút)">🆕</span>');
      const path = CONTENT_DIR + "/" + p.slug + ".md";
      const dateCell = p.date ? escapeHtml(p.date) : '<em class="editor-pending">đang build…</em>';
      return '<tr>' +
        '<td><strong>' + escapeHtml(p.title || p.slug) + '</strong>' + badges.join("") + '</td>' +
        '<td>' + dateCell + '</td>' +
        '<td>' + escapeHtml(p.category || "—") + '</td>' +
        '<td><button class="editor-btn editor-btn--small" data-edit="' + escapeHtml(path) + '">Sửa</button></td>' +
      '</tr>';
    }).join("");

    tbody.querySelectorAll("[data-edit]").forEach((btn) => {
      btn.addEventListener("click", () => openEditor(btn.dataset.edit));
    });
  }

  $("[data-action='reload']").addEventListener("click", () => enterDashboard(true));

  // Search input — debounce 100ms để không lag khi gõ nhanh.
  const searchInput = $("[data-search]");
  if (searchInput) {
    searchInput.addEventListener("input", debounce(() => {
      state.filter.query = searchInput.value;
      renderPostList();
    }, 100));
  }

  // Sort dropdown — re-render ngay khi đổi.
  const sortSelect = $("[data-sort]");
  if (sortSelect) {
    sortSelect.addEventListener("change", () => {
      state.filter.sort = sortSelect.value;
      renderPostList();
    });
  }

  $("[data-action='logout']").addEventListener("click", async () => {
    if (!confirm("Đăng xuất khỏi CMS?")) return;
    await logoutRemote();
    currentUser = null;
    const bar = $("[data-user-bar]");
    if (bar) bar.hidden = true;
    showView("login");
  });

  $("[data-action='new']").addEventListener("click", () => openEditor(null));

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
        credentials: "omit",
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
      credentials: "omit",
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
      `<option value="${escapeHtml(c)}"${c === selected ? " selected" : ""}>${escapeHtml(c)}</option>`
    ).join("");
    // Nếu category đã chọn không nằm trong list (đã bị xoá khỏi taxonomy) → thêm vào
    if (selected && !knownCategories.includes(selected)) {
      catSelect.insertAdjacentHTML("afterbegin",
        `<option value="${escapeHtml(selected)}" selected>${escapeHtml(selected)} (cũ)</option>`);
    }
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
      updateCounter();
      lastRenderedBody = null;
      renderPreview();
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
      state.editing = { path: data.path, sha: data.sha, wasFeatured: fm.featured, featuredAt: fm.featured_at };
      // Edit bài đã có slug → khoá auto-fill để không phá URL hiện tại khi đổi title
      slugLocked = true;
      form.title.value = fm.title;
      // Loại prefix folder (content/posting/) khỏi slug input
      const slug = data.path.replace(new RegExp("^" + CONTENT_DIR + "/"), "").replace(/\.md$/, "");
      form.slug.value = slug;
      lastDraftSlug = slug; // track để autosave xoá draft cũ khi user đổi slug
      form.date.value = fm.date;
      rebuildCategoryOptions(fm.category);
      form.tags.value = fm.tags.join(", ");
      form.thumbnail.value = fm.thumbnail;
      form.featured.checked = fm.featured;
      form.body.value = body.trim();
      updateCounter();
      lastRenderedBody = null;
      renderPreview();
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

    const isFeatured = form.featured.checked;
    // Featured-at logic: chỉ STAMP timestamp khi transition false→true (lần đầu tick),
    // hoặc khi tạo bài mới đã tick sẵn. Đã featured rồi mà save lại → giữ timestamp cũ
    // để không đẩy bài lên đầu mỗi lần edit. Untick → xoá luôn.
    let featuredAt = "";
    if (isFeatured) {
      const wasFeatured = state.editing && state.editing.wasFeatured;
      const oldStamp = state.editing && state.editing.featuredAt;
      featuredAt = (wasFeatured && oldStamp) ? oldStamp : new Date().toISOString();
    }

    const fm = {
      title: form.title.value.trim(),
      date: form.date.value,
      category: getSelectedCategory(),
      tags: form.tags.value.split(",").map((t) => t.trim()).filter(Boolean),
      thumbnail: form.thumbnail.value.trim(),
      featured: isFeatured,
      featured_at: featuredAt,
    };
    const body = form.body.value;
    const slug = (form.slug.value.trim() || slugify(fm.title));

    if (!slug) { alert("Cần tiêu đề hoặc slug"); return; }
    if (!fm.title || !fm.date) { alert("Thiếu tiêu đề hoặc ngày"); return; }

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
      // Update state.posts in-place — preserve UI position khi user "Quay lại" list.
      // Bake metadata stale ~1 phút cho đến rebuild, nhưng UI hiển thị metadata mới gõ.
      const savedPost = {
        slug: slug,
        title: fm.title,
        date: fm.date,
        category: fm.category,
        featured: fm.featured,
        isNew: !state.editing,
      };
      const idx = state.posts.findIndex((p) => p.slug === slug);
      if (idx >= 0) state.posts[idx] = savedPost;
      else state.posts.unshift(savedPost);
      invalidateListCache(); // ép background refresh tiếp theo fetch tươi
      // Cleanup draft localStorage — bài đã commit lên repo, không cần giữ draft
      discardDraft(slug);
      lastDraftSlug = slug;
    } catch (err) {
      setStatus("save-status", "✗ " + err.message, "error");
    }
  });

  // ============= PUBLISH TO GITHUB =============
  // Đẩy bài trực tiếp lên repo qua backend /cms/save-post. Backend dùng
  // access_token GitHub (Redis-side) để PUT content/posting/{slug}.md.
  // Sau push: GitHub Actions auto-build + deploy ~1-2 phút.
  $("[data-action='publish']").addEventListener("click", async (e) => {
    e.preventDefault();
    const form = $("[data-form='post']");
    if (!form.reportValidity()) return; // browser native validation

    const sid = getSid();
    if (!sid) {
      alert("Phiên đăng nhập đã hết. Đăng nhập lại để publish.");
      showView("login");
      return;
    }
    if (!AUTH_API) {
      alert("Backend chưa cấu hình.");
      return;
    }

    // Collect form data (giống logic submit Tải .md)
    const isFeatured = form.featured.checked;
    let featuredAt = "";
    if (isFeatured) {
      const wasFeatured = state.editing && state.editing.wasFeatured;
      const oldStamp = state.editing && state.editing.featuredAt;
      featuredAt = (wasFeatured && oldStamp) ? oldStamp : new Date().toISOString();
    }
    const fm = {
      title: form.title.value.trim(),
      date: form.date.value,
      category: getSelectedCategory(),
      tags: form.tags.value.split(",").map((t) => t.trim()).filter(Boolean),
      thumbnail: form.thumbnail.value.trim(),
      featured: isFeatured,
      featured_at: featuredAt,
    };
    const body = form.body.value;
    const slug = (form.slug.value.trim() || slugify(fm.title)).toLowerCase();
    if (!slug || !fm.title || !fm.date) {
      alert("Thiếu tiêu đề, slug hoặc ngày.");
      return;
    }

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
      const res = await fetch(AUTH_API + "/cms/save-post", {
        method: "POST",
        headers: {
          "Authorization": "Bearer " + sid,
          "Content-Type": "application/json",
        },
        credentials: "omit",
        body: JSON.stringify({ slug, content, message }),
      });

      if (res.status === 401) {
        clearSid();
        alert("Phiên hết hạn. Đăng nhập lại.");
        showView("login");
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
        " <strong>" + escapeHtml(data.path) + "</strong>. " +
        "Deploy ETA: " + escapeHtml(data.deploy_eta) + commitLink;

      // Update state.posts in-place — preserve UI position
      const savedPost = {
        slug: slug,
        title: fm.title,
        date: fm.date,
        category: fm.category,
        featured: fm.featured,
        isNew: !state.editing,
      };
      const idx = state.posts.findIndex((p) => p.slug === slug);
      if (idx >= 0) state.posts[idx] = savedPost;
      else state.posts.unshift(savedPost);
      invalidateListCache();
      discardDraft(slug);
      lastDraftSlug = slug;
    } catch (err) {
      setStatus("save-status", "✗ Lỗi mạng: " + err.message, "error");
    }
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
    const payload = {
      timestamp: Date.now(),
      title: form.title.value,
      slug: slug,
      date: form.date.value,
      category: getSelectedCategory(),
      tags: form.tags.value,
      thumbnail: form.thumbnail.value,
      featured: form.featured.checked,
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
    const timeStr = ts.toLocaleString("vi-VN", {
      hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit",
    });
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
    form.body.value = draft.body || "";
    rebuildCategoryOptions(draft.category || "Posting");
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
  bodyTextarea.addEventListener("scroll", () => { if (slashState.open) closeSlashMenu(); });
  window.addEventListener("scroll", () => { if (slashState.open) closeSlashMenu(); }, { passive: true });

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

  // ============= INIT — GitHub OAuth Flow =============
  async function init() {
    // 1. Consume #sid=... từ callback redirect (nếu vừa OAuth xong)
    consumeUrlHashSid();
    // 2. Consume ?auth_error=... (backend redirect khi denied)
    const errCode = consumeUrlAuthError();
    if (errCode) showLoginError(errCode);

    // 3. Nếu backend chưa configure → hiển thị hint trên login view
    if (!AUTH_API) {
      showLoginHint();
      showView("login");
      return;
    }

    // 4. Có sid → validate qua backend /auth/me
    const sid = getSid();
    if (sid) {
      const user = await fetchMe();
      if (user) {
        currentUser = user;
        populateUserBar(user);
        if (!checkUrlParam()) enterDashboard();
        return;
      }
      // Session expired/invalid → đã clearSid trong fetchMe
    }

    // 5. Chưa login → show login screen
    showView("login");
  }

  init();
})();
