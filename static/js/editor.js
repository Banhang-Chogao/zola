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

  const TOKEN_KEY = "zola-cms-token";
  const root = document.getElementById("editor-app");
  if (!root) return;

  // ============= STATE & UTIL =============
  let state = {
    token: localStorage.getItem(TOKEN_KEY) || null,
    posts: [],     // file metadata list từ GitHub
    editing: null, // { path, sha, frontmatter, body }
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

  // ============= API CALLS =============
  async function api(path, opts) {
    opts = opts || {};
    const res = await fetch(API + path, {
      ...opts,
      headers: {
        Accept: "application/vnd.github+json",
        Authorization: "token " + state.token,
        "X-GitHub-Api-Version": "2022-11-28",
        ...(opts.headers || {}),
      },
    });
    if (res.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      state.token = null;
      showView("login");
      throw new Error("Token không hợp lệ — vui lòng đăng nhập lại");
    }
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.message || "HTTP " + res.status);
    }
    return res.json();
  }

  async function listPosts() {
    // GET contents/content → list file ở root
    const list = await api("/repos/" + OWNER + "/" + REPO + "/contents/" + CONTENT_DIR + "?ref=" + BRANCH);
    // Lọc file .md ở root (không phải _index, không phải subfolder)
    return list
      .filter((f) => f.type === "file" && f.name.endsWith(".md") && !f.name.startsWith("_"))
      .map((f) => ({ name: f.name, path: f.path, sha: f.sha, slug: f.name.replace(/\.md$/, "") }));
  }

  async function getPost(path) {
    const file = await api("/repos/" + OWNER + "/" + REPO + "/contents/" + path + "?ref=" + BRANCH);
    const content = b64decode(file.content);
    return { sha: file.sha, content, path: file.path };
  }

  async function putPost(path, content, sha, message) {
    const body = {
      message: message,
      content: b64encode(content),
      branch: BRANCH,
    };
    if (sha) body.sha = sha;
    return api("/repos/" + OWNER + "/" + REPO + "/contents/" + path, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  }

  async function deletePost(path, sha, message) {
    return api("/repos/" + OWNER + "/" + REPO + "/contents/" + path, {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: message, sha: sha, branch: BRANCH }),
    });
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

  // ============= LOGIN =============
  $("[data-form='login']").addEventListener("submit", (e) => {
    e.preventDefault();
    const token = e.target.token.value.trim();
    if (!token.startsWith("ghp_") && !token.startsWith("github_pat_")) {
      alert("Token không đúng format. Token bắt đầu bằng 'ghp_' hoặc 'github_pat_'.");
      return;
    }
    state.token = token;
    localStorage.setItem(TOKEN_KEY, token);
    enterDashboard();
  });

  async function enterDashboard() {
    showView("list");
    setStatus("[data-status]", "Đang tải danh sách bài viết…", "info");
    try {
      state.posts = await listPosts();
      renderPostList();
      setStatus("[data-status]", "✓ " + state.posts.length + " bài viết", "success");
    } catch (err) {
      setStatus("[data-status]", "✗ " + err.message, "error");
    }
  }

  // ============= LIST VIEW =============
  function renderPostList() {
    const tbody = $("[data-target='post-rows']");
    if (!state.posts.length) {
      tbody.innerHTML = '<tr><td colspan="4" class="editor-empty">Chưa có bài nào. Click "+ Viết bài mới".</td></tr>';
      return;
    }
    tbody.innerHTML = state.posts.map((p) => `
      <tr>
        <td><strong>${escapeHtml(p.slug)}</strong></td>
        <td>—</td>
        <td>—</td>
        <td><button class="editor-btn editor-btn--small" data-edit="${escapeHtml(p.path)}">Sửa</button></td>
      </tr>
    `).join("");

    tbody.querySelectorAll("[data-edit]").forEach((btn) => {
      btn.addEventListener("click", () => openEditor(btn.dataset.edit));
    });
  }

  $("[data-action='reload']").addEventListener("click", enterDashboard);

  $("[data-action='logout']").addEventListener("click", () => {
    if (!confirm("Đăng xuất + xoá token khỏi trình duyệt?")) return;
    localStorage.removeItem(TOKEN_KEY);
    state.token = null;
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
  // Categories baked vào page qua <script id="categories-data"> từ editor.html.
  // User có thể thêm category mới qua option "Tạo mới" — không cần round-trip API.
  let knownCategories = [];
  try {
    const raw = document.getElementById("categories-data");
    if (raw) knownCategories = JSON.parse(raw.textContent || "[]");
  } catch (e) { knownCategories = []; }
  // Luôn đảm bảo có "Posting" làm default fallback
  if (!knownCategories.includes("Posting")) knownCategories.unshift("Posting");

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
    // Bài mới chưa có slug → mở khoá auto-fill. Edit bài cũ sẽ set lại bên dưới.
    slugLocked = false;

    if (!path) {
      // New post
      $("[data-target='edit-title']").textContent = "VIẾT BÀI MỚI";
      $("[data-action='delete']").hidden = true;
      form.date.value = todayIso();
      state.editing = null;
      rebuildCategoryOptions("Posting");
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
      form.slug.value = data.path.replace(new RegExp("^" + CONTENT_DIR + "/"), "").replace(/\.md$/, "");
      form.date.value = fm.date;
      rebuildCategoryOptions(fm.category);
      form.tags.value = fm.tags.join(", ");
      form.thumbnail.value = fm.thumbnail;
      form.featured.checked = fm.featured;
      form.body.value = body.trim();
      setStatus("save-status", "✓ Đã tải bài", "success");
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

    setStatus("save-status", "Đang đẩy file lên GitHub…", "info");
    try {
      await putPost(path, content, state.editing ? state.editing.sha : null, message);
      setStatus("save-status", "✓ Đã lưu lên GitHub. GitHub Actions đang build site (~1 phút) để cập nhật bài lên web.", "success");
      // refresh list trong background
      listPosts().then((posts) => { state.posts = posts; });
    } catch (err) {
      setStatus("save-status", "✗ " + err.message, "error");
    }
  });

  $("[data-action='delete']").addEventListener("click", async () => {
    if (!state.editing) return;
    if (!confirm("Xoá bài này vĩnh viễn?")) return;
    try {
      await deletePost(state.editing.path, state.editing.sha, "Xoá bài");
      setStatus("save-status", "✓ Đã xoá", "success");
      enterDashboard();
    } catch (err) {
      setStatus("save-status", "✗ " + err.message, "error");
    }
  });

  $("[data-action='back']").addEventListener("click", () => {
    enterDashboard();
  });

  // ============= MARKDOWN PREVIEW TABS =============
  $$(".editor-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      $$(".editor-tab").forEach((t) => t.classList.remove("is-active"));
      tab.classList.add("is-active");
      const target = tab.dataset.tab;
      $$("[data-tab-pane]").forEach((p) => p.hidden = p.dataset.tabPane !== target);
      if (target === "preview" && window.marked) {
        const body = $("[name='body']").value;
        $("[data-tab-pane='preview']").innerHTML = window.marked.parse(body || "*(rỗng)*");
      }
    });
  });

  // ============= URL PARAM HANDLING =============
  // Mở trực tiếp 1 bài qua ?slug=cai-dat-zola
  function checkUrlParam() {
    const params = new URLSearchParams(location.search);
    const slug = params.get("slug");
    if (slug && state.token) {
      const path = CONTENT_DIR + "/" + slug + ".md";
      openEditor(path);
      return true;
    }
    return false;
  }

  // ============= INIT =============
  if (state.token) {
    if (!checkUrlParam()) enterDashboard();
  } else {
    showView("login");
  }
})();
