(function () {
  "use strict";
  var root = document.querySelector("[data-editorial-desk]");
  var source = document.getElementById("editorial-posts-metadata");
  if (!root || !source) return;

  var API = ((document.querySelector('meta[name="zola-cms-auth-api"]') || {}).content || "https://api.seomoney.org").replace(/\/$/, "");
  var SESSION_KEY = "zola-cms-session-id";
  var posts = [];
  try { posts = JSON.parse(source.textContent || "[]"); } catch (e) { posts = []; }
  var bySlug = new Map(posts.map(function (post) { return [post.slug, post]; }));
  var slots = { version: 1, lead_story: null, featured: null, secondary: [], sidebar_featured: null, allow_duplicates: false };
  var commitMetadata = {};
  var dirty = false;
  var status = root.querySelector("[data-editorial-status]");
  var slotRoot = root.querySelector("[data-editorial-slots]");
  var queue = root.querySelector("[data-editorial-queue]");
  var search = root.querySelector("[data-editorial-search]");
  var count = root.querySelector("[data-editorial-count]");
  var allowDuplicates = root.querySelector("[data-editorial-duplicates]");
  var catalog = document.getElementById("editorial-post-catalog");

  function esc(value) { return String(value || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
  function sid() { try { return sessionStorage.getItem(SESSION_KEY) || localStorage.getItem(SESSION_KEY) || ""; } catch (e) { return ""; } }
  function headers() { var h = { "Content-Type": "application/json" }; if (sid()) h.Authorization = "Bearer " + sid(); return h; }
  function setStatus(message, kind) { status.textContent = message; status.dataset.state = kind || "info"; }
  function slugFromInput(value) { return String(value || "").trim().split(/\s+—\s+/)[0].trim() || null; }
  function label(post) { return post ? post.slug + " — " + post.title : ""; }
  function selectedSlugs() { return [slots.lead_story, slots.featured].concat(slots.secondary || [], [slots.sidebar_featured]).filter(Boolean); }

  function slotCard(key, title, index) {
    var slug = key === "secondary" ? (slots.secondary[index] || null) : slots[key];
    var post = bySlug.get(slug);
    var commit = commitMetadata[slug] || null;
    var broken = slug && !post;
    var id = key + (index == null ? "" : "-" + index);
    return '<article class="editorial-slot' + (broken ? ' is-broken' : '') + '">' +
      '<div><span class="cms-v2__card-label">' + esc(title) + '</span>' +
      '<strong>' + esc(post ? post.title : (slug || "Chưa chọn bài")) + '</strong>' +
      '<small>' + esc(post ? (post.category + " · " + (commit ? (commit.sha + " · " + commit.timestamp) : post.date)) : (broken ? "Broken slot — slug không còn trong catalog" : "Fallback: bài mới nhất hợp lệ")) + '</small></div>' +
      '<input class="cms-v2__input" list="editorial-post-catalog" value="' + esc(label(post) || slug || "") + '" placeholder="Search slug hoặc tiêu đề" data-slot-input="' + esc(id) + '">' +
      '<div class="editorial-slot__actions">' +
      (post ? '<a class="cms-v2__button cms-v2__button--ghost" href="' + esc(post.permalink) + '" target="_blank" rel="noopener">Preview</a>' : '') +
      '<button type="button" class="cms-v2__button cms-v2__button--ghost" data-slot-clear="' + esc(id) + '">Clear</button></div></article>';
  }

  function renderSlots() {
    var html = slotCard("lead_story", "Sticky / Lead Story") + slotCard("featured", "Featured post");
    for (var i = 0; i < 4; i += 1) html += slotCard("secondary", "Secondary " + (i + 1), i);
    html += slotCard("sidebar_featured", "Sidebar Featured");
    slotRoot.innerHTML = html;
    allowDuplicates.checked = slots.allow_duplicates === true;
    slotRoot.querySelectorAll("[data-slot-input]").forEach(function (input) {
      input.addEventListener("change", function () { updateSlot(input.dataset.slotInput, slugFromInput(input.value)); });
    });
    slotRoot.querySelectorAll("[data-slot-clear]").forEach(function (button) {
      button.addEventListener("click", function () { updateSlot(button.dataset.slotClear, null); });
    });
  }

  function updateSlot(id, slug) {
    if (slug && !bySlug.has(slug)) { setStatus("Không thể chọn: slug không tồn tại trong content đã deploy.", "error"); renderSlots(); return; }
    if (id.indexOf("secondary-") === 0) {
      var index = Number(id.split("-")[1]);
      var next = (slots.secondary || []).slice();
      while (next.length <= index) next.push(null);
      next[index] = slug;
      slots.secondary = next.filter(Boolean);
    } else slots[id] = slug;
    dirty = true;
    var duplicates = selectedSlugs().filter(function (item, i, all) { return all.indexOf(item) !== i; });
    setStatus(duplicates.length && !slots.allow_duplicates ? "Cảnh báo: bài đang trùng slot. Bật cho phép trùng hoặc chọn bài khác." : "Có thay đổi chưa lưu.", duplicates.length ? "warning" : "dirty");
    renderSlots(); renderQueue();
  }

  function renderQueue() {
    var q = String(search.value || "").toLowerCase();
    var filtered = posts.filter(function (p) { return (p.title + " " + p.slug + " " + p.category).toLowerCase().indexOf(q) !== -1; });
    count.textContent = "Đang hiển thị " + Math.min(filtered.length, 20) + " / " + posts.length + " bài";
    var pinned = selectedSlugs();
    queue.innerHTML = filtered.slice(0, 20).map(function (p, i) {
      return '<article class="editorial-queue-item"><span>' + String(i + 1).padStart(2, "0") + '</span><div><strong>' + esc(p.title) + '</strong><small>/' + esc(p.section) + '/' + esc(p.slug) + ' · ' + esc(p.category) + ' · ' + esc(p.date) + (pinned.indexOf(p.slug) !== -1 ? ' · PINNED' : '') + '</small></div><a href="' + esc(p.permalink) + '" target="_blank" rel="noopener">Open</a></article>';
    }).join("") || '<p>Không có bài khớp.</p>';
  }

  async function sync() {
    setStatus("Đang đọc cấu hình thật từ GitHub…", "info");
    try {
      var res = await fetch(API + "/cms/editorial-slots", { headers: headers(), credentials: "include", cache: "no-store" });
      var data = await res.json().catch(function () { return {}; });
      if (!res.ok) throw new Error(data.detail || "HTTP " + res.status);
      slots = Object.assign(slots, data.slots || {}); dirty = false;
      commitMetadata = data.commit_metadata || {};
      renderSlots(); renderQueue();
      setStatus(data.broken && data.broken.length ? "Broken slot: " + data.broken.join(", ") : "Đã đồng bộ cấu hình từ GitHub.", data.broken && data.broken.length ? "error" : "success");
    } catch (e) { setStatus("Không thể sync: " + e.message, "error"); }
  }

  async function save() {
    slots.allow_duplicates = allowDuplicates.checked;
    setStatus("Đang validation và commit cấu hình…", "info");
    try {
      var res = await fetch(API + "/cms/editorial-slots", { method: "PUT", headers: headers(), credentials: "include", body: JSON.stringify({ slots: slots }) });
      var data = await res.json().catch(function () { return {}; });
      if (!res.ok) throw new Error(data.detail || "HTTP " + res.status);
      dirty = false;
      setStatus("Đã commit " + String(data.commit_sha || "").slice(0, 7) + ". Deploy ETA: " + (data.deploy_eta || "1–2 phút"), "success");
    } catch (e) { setStatus("Không thể lưu: " + e.message, "error"); }
  }

  catalog.innerHTML = posts.map(function (p) { return '<option value="' + esc(label(p)) + '"></option>'; }).join("");
  root.querySelector("[data-editorial-sync]").addEventListener("click", sync);
  root.querySelector("[data-editorial-save]").addEventListener("click", save);
  allowDuplicates.addEventListener("change", function () { slots.allow_duplicates = allowDuplicates.checked; dirty = true; setStatus("Có thay đổi chưa lưu.", "dirty"); });
  search.addEventListener("input", renderQueue);
  window.addEventListener("beforeunload", function (event) { if (dirty) { event.preventDefault(); event.returnValue = ""; } });
  renderSlots(); renderQueue();
  setTimeout(sync, 800);
})();
