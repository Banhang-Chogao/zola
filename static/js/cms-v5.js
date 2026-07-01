(function () {
  "use strict";

  var root = document.querySelector("[data-cms5]");
  if (!root || window.__cmsV5Initialized) return;
  window.__cmsV5Initialized = true;

  var apiMeta = document.querySelector('meta[name="zola-cms-auth-api"]');
  var API = (apiMeta && apiMeta.content ? apiMeta.content : "https://api.seomoney.org").replace(/\/$/, "");
  var CMS_API = API + "/api/cms-v5";
  var RETURN_TO = window.location.origin + "/cms-v5/";
  var SESSION_KEY = "zola-cms-session-id";

  function q(selector, scope) { return (scope || root).querySelector(selector); }
  function qa(selector, scope) { return Array.prototype.slice.call((scope || root).querySelectorAll(selector)); }
  function text(el, value) { if (el) el.textContent = value == null ? "" : String(value); }
  function hidden(el, value) { if (el) el.hidden = !!value; }
  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#039;");
  }
  function slugify(value) {
    return String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "")
      .replace(/đ/g, "d").replace(/Đ/g, "D").toLowerCase()
      .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 90);
  }
  function showAuthStatus(message, kind) {
    text(el.authStatus, message);
    el.authStatus.className = "cms5-alert" + (kind ? " is-" + kind : "");
  }
  function getSid() {
    try { return localStorage.getItem(SESSION_KEY) || sessionStorage.getItem(SESSION_KEY) || ""; }
    catch (_) { return ""; }
  }
  function clearSid() {
    try { localStorage.removeItem(SESSION_KEY); sessionStorage.removeItem(SESSION_KEY); } catch (_) {}
  }
  function consumeAuthResult() {
    var params = new URLSearchParams(location.search);
    var hash = location.hash.match(/(?:^|[#&])sid=([A-Za-z0-9_-]+)/);
    if (hash) {
      try {
        localStorage.setItem(SESSION_KEY, hash[1]);
        sessionStorage.setItem(SESSION_KEY, hash[1]);
      } catch (_) {}
    }
    if (params.has("success") || params.has("auth_error") || hash) {
      var error = params.get("auth_error") || "";
      params.delete("success"); params.delete("auth_error");
      history.replaceState(null, "", location.pathname + (params.toString() ? "?" + params : ""));
      return error;
    }
    return "";
  }

  var el = {
    gate: q("[data-cms5-gate]"),
    shell: q("[data-cms5-shell]"),
    authStatus: q("[data-cms5-auth-status]"),
    login: q("[data-cms5-login]"),
    avatar: q("[data-cms5-avatar]"),
    userName: q("[data-cms5-user-name]"),
    userShort: q("[data-cms5-user-short]"),
    toast: q("[data-cms5-toast]"),
    queue: q("[data-cms5-post-queue]"),
    form: q("[data-cms5-editor-form]"),
    postId: q("[data-cms5-post-id]"),
    title: q("[data-cms5-title]"),
    slug: q("[data-cms5-slug]"),
    excerpt: q("[data-cms5-excerpt]"),
    blocks: q("[data-cms5-blocks]"),
    category: q("[data-cms5-category]"),
    tags: q("[data-cms5-tags]"),
    featured: q("[data-cms5-featured]"),
    featuredName: q("[data-cms5-featured-name]"),
    status: q("[data-cms5-status]"),
    visibility: q("[data-cms5-visibility]"),
    scheduleWrap: q("[data-cms5-schedule-wrap]"),
    scheduledAt: q("[data-cms5-scheduled-at]"),
    saveState: q("[data-cms5-save-state]"),
    editorHeading: q("[data-cms5-editor-heading]"),
    fileInput: q("[data-cms5-file-input]"),
    mediaGrid: q("[data-cms5-media-grid]"),
    dropzone: q("[data-cms5-dropzone]"),
    mediaSearch: q("[data-cms5-media-search]"),
    search: q("[data-cms5-search]"),
    categories: q("[data-cms5-categories]"),
    tagsCloud: q("[data-cms5-tags-cloud]"),
    previewFrame: q("[data-cms5-preview-frame]"),
    previewHero: q("[data-cms5-preview-hero]"),
    previewCategory: q("[data-cms5-preview-category]"),
    previewTitle: q("[data-cms5-preview-title]"),
    previewExcerpt: q("[data-cms5-preview-excerpt]"),
    previewDate: q("[data-cms5-preview-date]"),
    previewContent: q("[data-cms5-preview-content]"),
    previewUrl: q("[data-cms5-preview-url]"),
    liveUrl: q("[data-cms5-live-url]"),
  };

  var state = {
    user: null,
    blocks: [],
    media: [],
    categories: [],
    tags: [],
    featuredMediaId: "",
    pendingBlockUpload: null,
    dirty: false,
    titleTouched: false,
  };

  var toastTimer;
  function toast(message, kind) {
    text(el.toast, message);
    el.toast.className = "cms5-toast" + (kind ? " is-" + kind : "");
    hidden(el.toast, false);
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { hidden(el.toast, true); }, 4500);
  }

  async function request(path, options) {
    options = options || {};
    var headers = new Headers(options.headers || {});
    var sid = getSid();
    if (sid) headers.set("Authorization", "Bearer " + sid);
    if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    var fetchOpts = {
      method: options.method || "GET",
      headers: headers,
      body: options.body,
      credentials: "include",
      mode: "cors",
    };
    if (options.signal) fetchOpts.signal = options.signal;
    var response = await fetch((path.indexOf("http") === 0 ? "" : CMS_API) + path, fetchOpts);
    var data = null;
    try { data = await response.json(); } catch (_) {}
    if (!response.ok) {
      var detail = data && data.detail ? data.detail : "HTTP " + response.status;
      var error = new Error(detail);
      error.status = response.status;
      throw error;
    }
    return data;
  }

  function startLogin() {
    clearSid();
    var url = new URL(API + "/auth/login");
    url.searchParams.set("return_to", RETURN_TO);
    location.assign(url.toString());
  }

  async function authenticate() {
    var authError = consumeAuthResult();
    if (authError) showAuthStatus("Đăng nhập thất bại: " + authError, "error");
    hidden(el.gate, false);
    hidden(el.shell, true);
    try {
      var controller = new AbortController();
      var timeout = setTimeout(function () { controller.abort(); }, 8000);
      var user = await request(API + "/auth/me", { signal: controller.signal });
      clearTimeout(timeout);
      if (user.provider !== "github") throw new Error("CMS-V5 chỉ chấp nhận GitHub OAuth. Vui lòng đăng nhập bằng GitHub bên dưới.");
      if (!user.is_admin && !user.is_super) throw new Error("Tài khoản không có quyền quản trị CMS");
      state.user = user;
      text(el.userName, user.name || user.username);
      text(el.userShort, (user.name || user.username || "").split(/\s+/)[0]);
      if (user.avatar_url || user.avatar) {
        el.avatar.src = user.avatar_url || user.avatar;
        el.avatar.alt = user.name || user.username || "GitHub avatar";
        hidden(el.avatar, false);
      }
      hidden(el.gate, true);
      hidden(el.shell, false);
      await loadAll();
    } catch (error) {
      hidden(el.shell, true);
      hidden(el.gate, false);
      if (error.name === "AbortError") {
        showAuthStatus("Không thể kết nối đến máy chủ xác thực. Vui lòng thử lại sau.", "error");
      } else if (error.status === 401) {
        showAuthStatus("Bạn cần đăng nhập để truy cập CMS-V5.", "info");
      } else if (error.status === 403) {
        showAuthStatus(error.message, "error");
      } else if (error.status === 0 || error.message === "Failed to fetch" || error.message.indexOf("NetworkError") >= 0) {
        showAuthStatus("Không thể kết nối đến máy chủ API. Kiểm tra kết nối mạng hoặc thử lại sau.", "error");
      } else {
        showAuthStatus(error.message, "error");
      }
    }
  }

  function formatNumber(value) {
    try { return new Intl.NumberFormat("vi-VN").format(Number(value) || 0); }
    catch (_) { return String(value || 0); }
  }
  function formatBytes(value) {
    var bytes = Number(value) || 0;
    if (bytes < 1024) return bytes + " B";
    var units = ["KB", "MB", "GB"];
    var size = bytes;
    var unit = 0;
    do { size /= 1024; unit += 1; } while (size >= 1024 && unit < units.length - 1);
    return size.toFixed(size >= 10 ? 1 : 2) + " " + units[unit - 1];
  }
  function formatDate(value) {
    if (!value) return "—";
    try { return new Intl.DateTimeFormat("vi-VN", { dateStyle: "short", timeStyle: "short" }).format(new Date(value)); }
    catch (_) { return value; }
  }

  function statusInfo(status) {
    return {
      draft: ["is-draft", "Bản nháp"],
      review: ["is-review", "Chờ duyệt"],
      scheduled: ["is-scheduled", "Đã lên lịch"],
      published: ["is-published", "Đã xuất bản"],
    }[status] || ["is-draft", status];
  }

  function renderDashboard(data) {
    Object.keys(data.stats || {}).forEach(function (key) {
      qa('[data-stat="' + key + '"]').forEach(function (node) { text(node, formatNumber(data.stats[key])); });
    });
    Object.keys(data.counts || {}).forEach(function (key) {
      qa('[data-count="' + key + '"]').forEach(function (node) { text(node, formatNumber(data.counts[key])); });
    });
    var posts = data.queue || [];
    el.queue.innerHTML = posts.length ? posts.map(function (post) {
      var info = statusInfo(post.status);
      var initials = (post.author_name || post.author_username || "Admin").split(/\s+/).map(function (x) { return x.charAt(0); }).join("").slice(0, 2);
      return '<tr data-post-row="' + escapeHtml(post.id) + '">' +
        '<td><span class="cms5-status ' + info[0] + '">● ' + info[1] + '</span></td>' +
        '<td><strong>' + escapeHtml(post.title) + '</strong><small>Cập nhật ' + escapeHtml(formatDate(post.updated_at)) + '</small></td>' +
        '<td><span class="cms5-mini-author"><i>' + escapeHtml(initials) + '</i>' + escapeHtml(post.author_name || post.author_username) + '</span></td>' +
        '<td>' + escapeHtml(post.scheduled_at ? formatDate(post.scheduled_at) : "—") + '</td>' +
        '<td><button type="button" data-edit-post="' + escapeHtml(post.id) + '" title="Sửa">✎</button> <button type="button" data-delete-post="' + escapeHtml(post.id) + '" title="Xóa">⌫</button></td></tr>';
    }).join("") : '<tr><td colspan="5">Không có bài viết đang chờ xử lý.</td></tr>';
  }

  async function loadDashboard() {
    var data = await request("/dashboard");
    renderDashboard(data);
  }

  function mediaPreview(item) {
    if (item.media_type === "image") return '<img src="' + escapeHtml(item.url) + '" alt="' + escapeHtml(item.alt_text || item.filename) + '" loading="lazy">';
    if (item.media_type === "video") return '<video src="' + escapeHtml(item.url) + '" controls preload="metadata"></video>';
    if (item.media_type === "audio") return '<span>♫</span><audio src="' + escapeHtml(item.url) + '" controls preload="none"></audio>';
    return '<span>PDF</span>';
  }

  function renderMedia(filter) {
    var needle = String(filter || "").toLowerCase();
    var items = state.media.filter(function (item) { return !needle || item.filename.toLowerCase().indexOf(needle) >= 0; });
    var upload = '<button class="cms5-media-upload" type="button" data-cms5-dropzone><span>＋</span><strong>Kéo thả hoặc chọn file</strong><small>Ảnh, video, audio hoặc PDF · tối đa 30 MB/file</small></button>';
    el.mediaGrid.innerHTML = items.map(function (item) {
      return '<article data-media-id="' + escapeHtml(item.id) + '"><div class="cms5-media-thumb is-' + escapeHtml(item.media_type) + '">' +
        mediaPreview(item) + '</div><h3>' + escapeHtml(item.filename) + '</h3><p>' + formatBytes(item.size_bytes) + ' · ' + escapeHtml(item.media_type.toUpperCase()) + '</p>' +
        '<div class="cms5-media-actions"><button type="button" data-insert-media="' + escapeHtml(item.id) + '">Chèn</button><button type="button" data-delete-media="' + escapeHtml(item.id) + '">Xóa</button></div></article>';
    }).join("") + upload;
    el.dropzone = q("[data-cms5-dropzone]");
    bindDropzone(el.dropzone);
  }

  async function loadMedia() {
    var data = await request("/media");
    state.media = data.media || [];
    renderMedia(el.mediaSearch ? el.mediaSearch.value : "");
    text(q("[data-cms5-storage-used]"), formatBytes(data.total_bytes));
    var percent = Math.min(100, (Number(data.total_bytes) || 0) / (1024 * 1024 * 1024) * 100);
    q("[data-cms5-storage-bar]").style.width = percent.toFixed(2) + "%";
    text(q("[data-cms5-storage-percent]"), percent.toFixed(1) + "%");
  }

  function renderTaxonomy() {
    text(q('[data-tax-count="categories"]'), state.categories.length);
    text(q('[data-tax-count="tags"]'), state.tags.length);
    el.categories.innerHTML = state.categories.length ? state.categories.map(function (item) {
      return '<tr><td><span class="cms5-category"><i class="is-blue">' + escapeHtml(item.name.charAt(0).toUpperCase()) + '</i><span><strong>' +
        escapeHtml(item.name) + '</strong><small>' + escapeHtml(item.description || "—") + '</small></span></span></td><td><code>' +
        escapeHtml(item.slug) + '</code></td><td><b>' + formatNumber(item.post_count) + '</b></td><td>' +
        (item.id ? '<button type="button" data-delete-tax="categories:' + escapeHtml(item.id) + '">⌫</button>' : "") + '</td></tr>';
    }).join("") : '<tr><td colspan="4">Chưa có chuyên mục.</td></tr>';
    el.tagsCloud.innerHTML = state.tags.length ? state.tags.map(function (item) {
      return '<button type="button" title="' + (item.id ? "Bấm để xóa thẻ" : "Thẻ lấy từ nội dung GitHub") + '" ' +
        (item.id ? 'data-delete-tax="tags:' + escapeHtml(item.id) + '"' : "") + '><span>#' + escapeHtml(item.name) + '</span><b>' +
        formatNumber(item.post_count) + '</b></button>';
    }).join("") : "<p>Chưa có thẻ.</p>";
    var current = el.category.value;
    el.category.innerHTML = '<option value="">Chọn chuyên mục</option>' + state.categories.map(function (item) {
      return '<option value="' + escapeHtml(item.name) + '">' + escapeHtml(item.name) + '</option>';
    }).join("");
    el.category.value = current;
  }

  async function loadTaxonomy() {
    var data = await request("/taxonomy");
    state.categories = data.categories || [];
    state.tags = data.tags || [];
    renderTaxonomy();
  }

  async function loadAll() {
    try {
      await Promise.all([loadDashboard(), loadMedia(), loadTaxonomy()]);
      if (!state.blocks.length) addBlock("text", "");
    } catch (error) {
      toast("Không tải được dữ liệu: " + error.message, "error");
    }
  }

  function blockLabel(type) {
    return { text: ["T", "Khối văn bản"], heading: ["H", "Tiêu đề phụ"], quote: ["❝", "Trích dẫn"], list: ["☷", "Danh sách"], image: ["▧", "Hình ảnh"] }[type];
  }

  function renderBlocks() {
    el.blocks.innerHTML = state.blocks.map(function (block, index) {
      var label = blockLabel(block.type);
      var typeClass = block.type === "text" ? "" : " is-" + block.type;
      var body;
      if (block.type === "image") {
        var media = state.media.find(function (item) { return item.id === block.media_id; });
        body = media ? '<div class="cms5-block-image"><img src="' + escapeHtml(media.url) + '" alt="' + escapeHtml(block.alt || media.filename) + '"><input value="' +
          escapeHtml(block.alt || "") + '" placeholder="Mô tả ảnh (alt text)" data-block-alt="' + index + '"></div>' :
          '<div class="cms5-image-placeholder" data-block-drop="' + index + '"><span>▧</span><strong>Kéo thả ảnh vào đây</strong><em>hoặc chọn một nguồn bên dưới</em><div><button type="button" data-block-upload-file="' +
          index + '">Chọn từ máy</button><button type="button" data-block-library="' + index + '">Chọn thư viện</button></div></div>';
      } else {
        var placeholder = block.type === "list" ? "Mỗi dòng là một mục danh sách" : "Nhập hoặc dán nội dung tại đây…";
        body = '<textarea rows="' + (block.type === "text" ? "7" : "3") + '" placeholder="' + placeholder + '" data-block-text="' + index + '">' + escapeHtml(block.text || "") + '</textarea>';
      }
      return '<div class="cms5-block" data-block-index="' + index + '"><span class="cms5-block__handle">⠿</span><span class="cms5-block__type' + typeClass + '">' +
        label[0] + '</span><div><small>' + label[1] + '</small>' + body + '</div><button type="button" data-remove-block="' + index + '" aria-label="Xóa khối">×</button></div>';
    }).join("") + '<button class="cms5-add-block" type="button" data-add-block="text">＋ <span>Thêm khối văn bản</span></button>';
    updatePreview();
  }

  function syncBlocksFromDom() {
    qa("[data-block-text]", el.blocks).forEach(function (field) {
      var index = Number(field.getAttribute("data-block-text"));
      if (state.blocks[index]) state.blocks[index].text = field.value;
    });
    qa("[data-block-alt]", el.blocks).forEach(function (field) {
      var index = Number(field.getAttribute("data-block-alt"));
      if (state.blocks[index]) state.blocks[index].alt = field.value;
    });
  }

  function addBlock(type, value, mediaId) {
    syncBlocksFromDom();
    state.blocks.push({ type: type, text: value || "", media_id: mediaId || null, alt: "" });
    state.dirty = true;
    renderBlocks();
    var fields = qa("[data-block-text]", el.blocks);
    if (fields.length && type !== "image") fields[fields.length - 1].focus();
  }

  function resetEditor() {
    el.form.reset();
    el.postId.value = "";
    state.featuredMediaId = "";
    state.blocks = [];
    state.dirty = false;
    state.titleTouched = false;
    text(el.featuredName, "1200 × 630px đề xuất");
    text(el.editorHeading, "Soạn thảo bài viết mới");
    text(el.saveState, "Chưa lưu");
    hidden(el.scheduleWrap, true);
    addBlock("text", "");
  }

  function payload(statusOverride) {
    syncBlocksFromDom();
    return {
      id: el.postId.value || null,
      title: el.title.value.trim(),
      slug: el.slug.value.trim(),
      excerpt: el.excerpt.value.trim(),
      blocks: state.blocks,
      category: el.category.value,
      tags: el.tags.value.split(",").map(function (x) { return x.trim(); }).filter(Boolean),
      featured_media_id: state.featuredMediaId || null,
      status: statusOverride || el.status.value,
      visibility: el.visibility.value,
      scheduled_at: (statusOverride || el.status.value) === "scheduled" && el.scheduledAt.value ? new Date(el.scheduledAt.value).toISOString() : null,
    };
  }

  async function savePost(statusOverride, quiet) {
    var data = payload(statusOverride);
    if (!data.title) {
      toast("Vui lòng nhập tiêu đề bài viết.", "error");
      el.title.focus();
      throw new Error("missing_title");
    }
    text(el.saveState, "Đang lưu…");
    var result = await request("/posts", { method: "POST", body: JSON.stringify(data) });
    el.postId.value = result.post.id;
    el.slug.value = result.post.slug;
    el.status.value = result.post.status;
    state.dirty = false;
    text(el.saveState, "Đã lưu " + new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" }));
    if (!quiet) toast(result.created ? "Đã tạo bài viết." : "Đã cập nhật bài viết.", "success");
    await Promise.all([loadDashboard(), loadTaxonomy()]);
    return result.post;
  }

  async function editPost(id) {
    try {
      var post = await request("/posts/" + encodeURIComponent(id));
      el.postId.value = post.id;
      el.title.value = post.title;
      el.slug.value = post.slug;
      el.excerpt.value = post.excerpt || "";
      el.category.value = post.category || "";
      el.tags.value = (post.tags || []).join(", ");
      el.status.value = post.status;
      el.visibility.value = post.visibility;
      state.featuredMediaId = post.featured_media_id || "";
      state.blocks = post.blocks || [];
      if (post.scheduled_at) {
        var local = new Date(post.scheduled_at);
        local.setMinutes(local.getMinutes() - local.getTimezoneOffset());
        el.scheduledAt.value = local.toISOString().slice(0, 16);
      }
      hidden(el.scheduleWrap, post.status !== "scheduled");
      var featured = state.media.find(function (item) { return item.id === state.featuredMediaId; });
      text(el.featuredName, featured ? featured.filename : "Chọn ảnh từ thư viện");
      text(el.editorHeading, "Chỉnh sửa: " + post.title);
      text(el.saveState, "Đã tải bản lưu " + formatDate(post.updated_at));
      renderBlocks();
      location.hash = "editor";
    } catch (error) { toast("Không mở được bài viết: " + error.message, "error"); }
  }

  async function publishCurrent() {
    try {
      if (el.visibility.value !== "public") {
        toast("Chỉ bài viết công khai mới có thể xuất bản.", "error");
        return;
      }
      var post = await savePost("draft", true);
      if (!confirm("Xuất bản “" + post.title + "” lên blog qua GitHub?")) return;
      text(el.saveState, "Đang xuất bản qua GitHub…");
      var result = await request("/posts/" + encodeURIComponent(post.id) + "/publish", { method: "POST" });
      text(el.saveState, "Đã xuất bản");
      el.liveUrl.href = result.url;
      text(el.previewUrl, result.url.replace(/^https?:\/\//, ""));
      toast("Đã xuất bản. GitHub Pages sẽ triển khai bài viết sau khi build hoàn tất.", "success");
      await loadDashboard();
    } catch (error) { toast("Xuất bản thất bại: " + error.message, "error"); text(el.saveState, "Xuất bản thất bại"); }
  }

  function chooseImage(callback) {
    var images = state.media.filter(function (item) { return item.media_type === "image"; });
    if (!images.length) {
      toast("Thư viện chưa có ảnh. Hãy upload ảnh từ máy trước.", "error");
      location.hash = "media";
      return;
    }
    var answer = prompt("Chọn số ảnh:\n" + images.map(function (item, i) { return (i + 1) + ". " + item.filename; }).join("\n"), "1");
    var selected = images[Number(answer) - 1];
    if (selected) callback(selected);
  }

  async function uploadFiles(files, blockIndex) {
    if (!files || !files.length) return;
    var form = new FormData();
    Array.prototype.slice.call(files).forEach(function (file) { form.append("files", file); });
    try {
      toast("Đang tải " + files.length + " file…");
      var result = await request("/media", { method: "POST", body: form });
      state.media = (result.media || []).concat(state.media);
      if (typeof blockIndex === "number") {
        var image = (result.media || []).find(function (item) { return item.media_type === "image"; });
        if (image && state.blocks[blockIndex]) state.blocks[blockIndex].media_id = image.id;
      }
      renderMedia();
      renderBlocks();
      toast("Upload thành công " + (result.media || []).length + " file.", "success");
      await loadDashboard();
    } catch (error) { toast("Upload thất bại: " + error.message, "error"); }
    el.fileInput.value = "";
  }

  function bindDropzone(zone) {
    if (!zone) return;
    zone.addEventListener("click", function () { el.fileInput.click(); });
    ["dragenter", "dragover"].forEach(function (name) {
      zone.addEventListener(name, function (event) { event.preventDefault(); zone.classList.add("is-dragging"); });
    });
    ["dragleave", "drop"].forEach(function (name) {
      zone.addEventListener(name, function (event) { event.preventDefault(); zone.classList.remove("is-dragging"); });
    });
    zone.addEventListener("drop", function (event) { uploadFiles(event.dataTransfer.files); });
  }

  function updatePreview() {
    syncBlocksFromDom();
    text(el.previewTitle, el.title.value.trim() || "Tiêu đề bài viết");
    text(el.previewExcerpt, el.excerpt.value.trim());
    text(el.previewCategory, el.category.value || "Chuyên mục");
    text(el.previewDate, new Date().toLocaleDateString("vi-VN"));
    var featured = state.media.find(function (item) { return item.id === state.featuredMediaId; });
    el.previewHero.innerHTML = featured ? '<img src="' + escapeHtml(featured.url) + '" alt="' + escapeHtml(featured.alt_text || el.title.value) + '">' : '<div class="cms5-preview-placeholder">SEOMONEY</div>';
    el.previewContent.innerHTML = state.blocks.map(function (block) {
      var value = escapeHtml(block.text || "").replace(/\n/g, "<br>");
      if (block.type === "heading") return "<h2>" + value + "</h2>";
      if (block.type === "quote") return "<blockquote>" + value + "</blockquote>";
      if (block.type === "list") return "<ul>" + String(block.text || "").split(/\n/).filter(Boolean).map(function (item) { return "<li>" + escapeHtml(item.replace(/^[-*•]\s*/, "")) + "</li>"; }).join("") + "</ul>";
      if (block.type === "image") {
        var media = state.media.find(function (item) { return item.id === block.media_id; });
        return media ? '<figure><img src="' + escapeHtml(media.url) + '" alt="' + escapeHtml(block.alt || media.filename) + '"></figure>' : "";
      }
      return value ? "<p>" + value + "</p>" : "";
    }).join("") || "<p>Nội dung preview sẽ xuất hiện tại đây.</p>";
    var slug = el.slug.value || slugify(el.title.value);
    text(el.previewUrl, "seomoney.org/preview/" + (slug || "bai-viet"));
  }

  async function createTaxonomy(kind) {
    var label = kind === "categories" ? "chuyên mục" : "thẻ";
    var name = prompt("Tên " + label + " mới:");
    if (!name || !name.trim()) return;
    try {
      await request("/taxonomy/" + kind, { method: "POST", body: JSON.stringify({ name: name.trim() }) });
      await Promise.all([loadTaxonomy(), loadDashboard()]);
      toast("Đã thêm " + label + ".", "success");
    } catch (error) { toast("Không thể thêm " + label + ": " + error.message, "error"); }
  }

  root.addEventListener("click", async function (event) {
    var target = event.target.closest("button, a");
    if (!target) return;
    if (target.matches("[data-cms5-login]")) return startLogin();
    if (target.matches("[data-cms5-logout]")) {
      try { await request(API + "/auth/logout", { method: "POST" }); } catch (_) {}
      clearSid(); location.reload(); return;
    }
    if (target.matches("[data-cms5-refresh]")) {
      try { await loadAll(); toast("Đã đồng bộ dữ liệu.", "success"); } catch (error) { toast(error.message, "error"); }
      return;
    }
    if (target.matches("[data-cms5-new]")) { resetEditor(); location.hash = "editor"; return; }
    if (target.hasAttribute("data-add-block")) { addBlock(target.getAttribute("data-add-block"), ""); return; }
    if (target.hasAttribute("data-remove-block")) {
      syncBlocksFromDom(); state.blocks.splice(Number(target.getAttribute("data-remove-block")), 1); renderBlocks(); return;
    }
    if (target.hasAttribute("data-block-library")) {
      var index = Number(target.getAttribute("data-block-library"));
      chooseImage(function (item) { state.blocks[index].media_id = item.id; renderBlocks(); });
      return;
    }
    if (target.hasAttribute("data-block-upload-file")) {
      state.pendingBlockUpload = Number(target.getAttribute("data-block-upload-file"));
      el.fileInput.click();
      return;
    }
    if (target.matches("[data-cms5-featured]")) {
      chooseImage(function (item) { state.featuredMediaId = item.id; text(el.featuredName, item.filename); updatePreview(); });
      return;
    }
    if (target.matches("[data-cms5-open-upload]")) {
      state.pendingBlockUpload = null;
      el.fileInput.click();
      return;
    }
    if (target.hasAttribute("data-insert-media")) {
      var mediaId = target.getAttribute("data-insert-media");
      var item = state.media.find(function (x) { return x.id === mediaId; });
      if (item && item.media_type === "image") { addBlock("image", "", item.id); location.hash = "editor"; }
      else toast("Chỉ ảnh có thể chèn trực tiếp vào nội dung bài viết.", "error");
      return;
    }
    if (target.hasAttribute("data-delete-media")) {
      if (!confirm("Xóa file này khỏi thư viện?")) return;
      try { await request("/media/" + encodeURIComponent(target.getAttribute("data-delete-media")), { method: "DELETE" }); await loadMedia(); await loadDashboard(); toast("Đã xóa file.", "success"); }
      catch (error) { toast("Không thể xóa: " + error.message, "error"); }
      return;
    }
    if (target.hasAttribute("data-edit-post")) { editPost(target.getAttribute("data-edit-post")); return; }
    if (target.hasAttribute("data-delete-post")) {
      if (!confirm("Xóa bản nháp này?")) return;
      try { await request("/posts/" + encodeURIComponent(target.getAttribute("data-delete-post")), { method: "DELETE" }); await loadDashboard(); toast("Đã xóa bài viết.", "success"); }
      catch (error) { toast("Không thể xóa: " + error.message, "error"); }
      return;
    }
    if (target.matches("[data-cms5-reset]")) { resetEditor(); return; }
    if (target.matches("[data-cms5-review]")) {
      try { el.status.value = "review"; await savePost("review"); } catch (_) {} return;
    }
    if (target.matches("[data-cms5-publish]")) { publishCurrent(); return; }
    if (target.matches("[data-cms5-show-preview]")) { updatePreview(); location.hash = "frontend"; return; }
    if (target.matches("[data-cms5-add-category]")) { createTaxonomy("categories"); return; }
    if (target.matches("[data-cms5-add-tag]")) { createTaxonomy("tags"); return; }
    if (target.hasAttribute("data-delete-tax")) {
      var parts = target.getAttribute("data-delete-tax").split(":");
      if (!confirm("Xóa taxonomy này? Bài viết hiện có không bị xóa.")) return;
      try { await request("/taxonomy/" + parts[0] + "/" + encodeURIComponent(parts[1]), { method: "DELETE" }); await loadTaxonomy(); toast("Đã xóa taxonomy.", "success"); }
      catch (error) { toast("Không thể xóa: " + error.message, "error"); }
      return;
    }
    if (target.matches("[data-cms5-nav]")) {
      qa("[data-cms5-nav]").forEach(function (link) { link.classList.remove("is-active"); });
      target.classList.add("is-active");
      return;
    }
    if (target.hasAttribute("data-preview-size")) {
      qa("[data-preview-size]").forEach(function (button) { button.classList.toggle("is-active", button === target); });
      el.previewFrame.setAttribute("data-size", target.getAttribute("data-preview-size"));
    }
  });

  el.form.addEventListener("submit", function (event) {
    event.preventDefault();
    savePost().catch(function (error) { if (error.message !== "missing_title") toast("Lưu thất bại: " + error.message, "error"); });
  });
  el.fileInput.addEventListener("change", function () {
    var index = state.pendingBlockUpload;
    state.pendingBlockUpload = null;
    uploadFiles(el.fileInput.files, typeof index === "number" ? index : undefined);
  });
  el.status.addEventListener("change", function () { hidden(el.scheduleWrap, el.status.value !== "scheduled"); });
  el.title.addEventListener("input", function () {
    if (!state.titleTouched || !el.slug.value) el.slug.value = slugify(el.title.value);
    state.dirty = true; updatePreview();
  });
  el.slug.addEventListener("input", function () { state.titleTouched = true; updatePreview(); });
  [el.excerpt, el.category, el.tags].forEach(function (field) {
    field.addEventListener("input", function () { state.dirty = true; updatePreview(); });
  });
  el.blocks.addEventListener("input", function () { state.dirty = true; updatePreview(); });
  el.blocks.addEventListener("dragover", function (event) {
    var zone = event.target.closest("[data-block-drop]");
    if (!zone) return;
    event.preventDefault();
    zone.classList.add("is-dragging");
  });
  el.blocks.addEventListener("dragleave", function (event) {
    var zone = event.target.closest("[data-block-drop]");
    if (zone) zone.classList.remove("is-dragging");
  });
  el.blocks.addEventListener("drop", function (event) {
    var zone = event.target.closest("[data-block-drop]");
    if (!zone) return;
    event.preventDefault();
    zone.classList.remove("is-dragging");
    uploadFiles(event.dataTransfer.files, Number(zone.getAttribute("data-block-drop")));
  });
  el.mediaSearch.addEventListener("input", function () { renderMedia(el.mediaSearch.value); });
  var searchTimer;
  el.search.addEventListener("input", function () {
    clearTimeout(searchTimer);
    var value = this.value.trim();
    searchTimer = setTimeout(function () {
      if (!value) { loadDashboard(); return; }
      request("/posts?q=" + encodeURIComponent(value) + "&limit=30").then(function (data) {
        renderDashboard({ stats: {}, counts: {}, queue: data.posts || [] });
      }).catch(function () {});
    }, 300);
  });
  bindDropzone(el.dropzone);
  window.addEventListener("beforeunload", function (event) {
    if (state.dirty) { event.preventDefault(); event.returnValue = ""; }
  });

  authenticate();
})();
