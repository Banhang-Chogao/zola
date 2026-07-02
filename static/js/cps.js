/**
 * Content Placement System (CPS) — visual, drag-and-drop admin for
 * data/content-placements.json (VIPZone backend `/admin/content-*`).
 *
 * Concept: Placement Registry (stable position IDs, read-only, hard-coded in
 * templates) → Content Blocks (editable title/body/CTA bound to a position) →
 * rendered on the live site by templates/macros/placement.html.
 *
 * This page is a thin client over the SAME endpoints already used by
 * /tools/momo-url/ (admin-momo-url.js) — no new backend routes. Auth state
 * machine mirrors auth-vaccine A1 (checking → authenticated | guest |
 * unauthorized | error), same session key, same /auth/me contract.
 */
(function () {
  if (window.__cpsInitDone) return;
  window.__cpsInitDone = true;

  const AUTH_API = (() => {
    const m = document.querySelector('meta[name="zola-cms-auth-api"]');
    if (m && m.getAttribute("content")) return m.getAttribute("content").replace(/\/$/, "");
    return "https://blog-vipzone-api.onrender.com";
  })();

  const SESSION_KEY = "zola-cms-session-id";
  const AUTH_TIMEOUT_MS = 8000;

  const STATE = { CHECKING: "checking", AUTHENTICATED: "authenticated", GUEST: "guest", UNAUTHORIZED: "unauthorized", ERROR: "error" };

  const TYPE_META = {
    momo_cta:    { label: "MoMo CTA",       icon: "M",    color: "momo",  cta: true,  momoOnly: true },
    donate_box:  { label: "Donate Box",     icon: "♥",    color: "rose",  cta: true,  momoOnly: true },
    premium_cta: { label: "Premium CTA",    icon: "★",    color: "amber", cta: true,  momoOnly: false },
    link_card:   { label: "Link Card",      icon: "↗",    color: "teal",  cta: true,  momoOnly: false },
    banner:      { label: "Banner",         icon: "▤",    color: "violet",cta: false, momoOnly: false },
    notice:      { label: "Thông báo",      icon: "ℹ",    color: "blue",  cta: false, momoOnly: false },
    html_safe:   { label: "HTML tuỳ chỉnh", icon: "</>",  color: "slate", cta: false, momoOnly: false },
  };
  const TYPE_ORDER = ["momo_cta", "donate_box", "premium_cta", "link_card", "banner", "notice", "html_safe"];

  const SCOPE_META = {
    post:    { label: "Bài viết",                 color: "emerald" },
    global:  { label: "Toàn site",                color: "indigo" },
    home:    { label: "Trang chủ",                color: "sky" },
    footer:  { label: "Footer",                   color: "orange" },
    sidebar: { label: "Sidebar (layout demo)",     color: "pink" },
    tools:   { label: "Nội bộ (trang quản trị)",   color: "slate" },
  };
  const SCOPE_ORDER = ["post", "global", "home", "footer", "sidebar", "tools"];

  let authState = null;
  let currentUser = null;
  let mePromise = null;
  let cpData = null; // { placements:[], blocks:[] }
  let editingId = null; // block id being edited, or null when creating
  let draggingBlockId = null;
  let draggingFromPlacement = null;
  const filters = { q: "", types: new Set(), onlyEnabled: false };

  // ============= DOM =============
  const authGate = document.getElementById("auth-gate");
  const adminContent = document.getElementById("admin-content");
  const loadingState = document.getElementById("cps-loading");
  const contentState = document.getElementById("cps-content");
  const errorState = document.getElementById("cps-error");
  const toastHost = document.getElementById("cps-toast-host");

  // ============= Session =============
  function getSid() { try { return localStorage.getItem(SESSION_KEY) || ""; } catch (e) { return ""; } }
  function setSid(sid) { try { localStorage.setItem(SESSION_KEY, sid); } catch (e) {} }
  function clearSid() { try { localStorage.removeItem(SESSION_KEY); } catch (e) {} }

  function consumeAuthCallback() {
    let sidFromHash = "";
    if (location.hash) {
      const m = location.hash.match(/(?:^|[#&])sid=([A-Za-z0-9_-]+)/);
      if (m) sidFromHash = m[1];
    }
    if (sidFromHash) setSid(sidFromHash);
    const params = new URLSearchParams(location.search);
    const authError = params.get("auth_error") || "";
    const authSuccess = params.get("auth") === "success";
    if (sidFromHash || authSuccess || authError) {
      params.delete("auth");
      params.delete("auth_error");
      const qs = params.toString();
      try { history.replaceState(null, "", location.pathname + (qs ? "?" + qs : "")); } catch (e) {}
    }
    return { authSuccess, authError };
  }

  function fetchMe() {
    if (mePromise) return mePromise;
    mePromise = (async () => {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), AUTH_TIMEOUT_MS);
      try {
        const opts = { credentials: "include", cache: "no-store", headers: {}, signal: controller.signal };
        const sid = getSid();
        if (sid) opts.headers["Authorization"] = "Bearer " + sid;
        const res = await fetch(AUTH_API + "/auth/me", opts);
        if (res.status === 401) return { status: 401, user: null };
        if (res.status === 403) return { status: 403, user: null };
        if (!res.ok) return { status: res.status, user: null, error: true };
        const user = await res.json();
        return { status: 200, user };
      } catch (e) {
        return { status: 0, user: null, error: true };
      } finally {
        clearTimeout(timer);
        mePromise = null;
      }
    })();
    return mePromise;
  }

  async function logoutRemote() {
    const sid = getSid();
    if (!sid || !AUTH_API) { clearSid(); return; }
    try {
      await fetch(AUTH_API + "/auth/logout", { method: "POST", headers: { Authorization: "Bearer " + sid }, credentials: "include", keepalive: true });
    } catch (e) {}
    clearSid();
  }

  function showGateView(view) {
    document.querySelectorAll("[data-auth-view]").forEach((el) => { el.hidden = el.getAttribute("data-auth-view") !== view; });
  }

  function setAuthState(state, detail) {
    authState = state;
    if (state === STATE.AUTHENTICATED) {
      authGate.hidden = true;
      adminContent.hidden = false;
      return;
    }
    adminContent.hidden = true;
    authGate.hidden = false;
    showGateView(state);
    if (detail && detail.message) {
      const id = state === STATE.UNAUTHORIZED ? "unauth-message" : "auth-error-message";
      const el = document.getElementById(id);
      if (el) el.textContent = detail.message;
    }
  }

  function startLogin() {
    const returnPath = location.pathname;
    window.location.href = AUTH_API + "/auth/google/start?return_to=" + encodeURIComponent(returnPath);
  }

  async function runAuthCheck(callbackError) {
    setAuthState(STATE.CHECKING);
    const { user, status, error } = await fetchMe();
    if (user && (user.is_admin === true || user.is_super === true)) {
      currentUser = user;
      setAuthState(STATE.AUTHENTICATED);
      loadCps();
      return;
    }
    if (user) {
      setAuthState(STATE.UNAUTHORIZED, { message: (user.email ? "Tài khoản " + user.email + " " : "Tài khoản này ") + "không nằm trong danh sách quản trị." });
      return;
    }
    if (callbackError === "access_denied") {
      setAuthState(STATE.UNAUTHORIZED, { message: "Tài khoản Google của bạn không có quyền quản trị." });
      return;
    }
    if (status === 403) { setAuthState(STATE.UNAUTHORIZED); return; }
    if (status === 401) { setAuthState(STATE.GUEST); return; }
    if (error) { setAuthState(STATE.ERROR, { message: "Không kết nối được máy chủ xác thực (có thể đang khởi động). Vui lòng thử lại." }); return; }
    if (callbackError) { setAuthState(STATE.ERROR, { message: "Đăng nhập không thành công (" + callbackError + ")." }); return; }
    setAuthState(STATE.GUEST);
  }

  // ============= Utils =============
  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str == null ? "" : String(str);
    return div.innerHTML;
  }
  function escapeAttr(str) { return escapeHtml(str).replace(/"/g, "&quot;"); }

  function slugify(value) {
    let s = String(value || "")
      .normalize("NFD").replace(/[̀-ͯ]/g, "")
      .replace(/đ/g, "d").replace(/Đ/g, "D")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_+|_+$/g, "")
      .slice(0, 55);
    if (!/^[a-z0-9]/.test(s)) s = "b" + s;
    return s || "block";
  }

  function uniqueId(base) {
    if (!cpData) return base;
    const ids = new Set((cpData.blocks || []).map((b) => b.id));
    if (!ids.has(base)) return base;
    let i = 2;
    while (ids.has(base + "_" + i)) i++;
    return base + "_" + i;
  }

  function showToast(message, kind) {
    if (!toastHost) return;
    const el = document.createElement("div");
    el.className = "cps-toast cps-toast--" + (kind || "ok");
    el.textContent = message;
    toastHost.appendChild(el);
    requestAnimationFrame(() => el.classList.add("is-visible"));
    setTimeout(() => {
      el.classList.remove("is-visible");
      setTimeout(() => el.remove(), 250);
    }, 4200);
  }

  function apiHeaders(json) {
    const h = {};
    const sid = getSid();
    if (sid) h["Authorization"] = "Bearer " + sid;
    if (json) h["Content-Type"] = "application/json";
    return h;
  }

  // ============= Data loading =============
  async function loadCps() {
    loadingState.hidden = false;
    contentState.hidden = true;
    errorState.hidden = true;
    try {
      const res = await fetch(AUTH_API + "/admin/content-placements", { credentials: "include", cache: "no-store", headers: apiHeaders(false) });
      if (res.status === 401) { setAuthState(STATE.GUEST); return; }
      if (res.status === 403) { setAuthState(STATE.UNAUTHORIZED); return; }
      if (!res.ok) throw new Error("API error: " + res.status);
      cpData = await res.json();
      renderAll();
      loadingState.hidden = true;
      contentState.hidden = false;
    } catch (e) {
      loadingState.hidden = true;
      errorState.hidden = false;
      document.getElementById("cps-error-message").textContent = "Tải dữ liệu thất bại: " + e.message;
    }
  }

  function placementById(id) { return (cpData.placements || []).find((p) => p.id === id) || null; }
  function blocksFor(placementId) {
    return (cpData.blocks || []).filter((b) => b.placement_id === placementId).sort((a, b) => (a.priority || 100) - (b.priority || 100));
  }

  // ============= Render: everything =============
  function renderAll() {
    renderStats();
    renderLibrary();
    renderCanvas();
    renderPreview();
  }

  function renderStats() {
    const blocks = cpData.blocks || [];
    const placements = cpData.placements || [];
    const hooked = placements.filter((p) => p.hooked);
    const usedIds = new Set(blocks.filter((b) => b.enabled).map((b) => b.placement_id));
    const hookedUsed = hooked.filter((p) => usedIds.has(p.id)).length;
    const enabled = blocks.filter((b) => b.enabled).length;

    const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    set("cps-stat-total", String(blocks.length));
    set("cps-stat-enabled", String(enabled));
    set("cps-stat-hooked-used", hookedUsed + " / " + hooked.length);
    set("cps-stat-empty", String(hooked.length - hookedUsed));
  }

  function typeBadge(type) {
    const meta = TYPE_META[type] || { label: type, icon: "?", color: "slate" };
    return '<span class="cps-type cps-type--' + meta.color + '"><i>' + escapeHtml(meta.icon) + '</i>' + escapeHtml(meta.label) + '</span>';
  }

  function pagesLabel(block) {
    const pages = block.pages || ["*"];
    if (pages.length === 1 && pages[0] === "*") return "Toàn site";
    return pages.map((p) => escapeHtml(p)).join(", ");
  }

  function blockCardHtml(block, opts) {
    opts = opts || {};
    const meta = TYPE_META[block.type] || { label: block.type, icon: "?", color: "slate" };
    const placement = placementById(block.placement_id);
    const scheduled = block.start_date || block.end_date;
    return (
      '<article class="cps-block-card cps-block-card--' + meta.color + (block.enabled ? "" : " is-disabled") + '" draggable="true" data-block-id="' + escapeAttr(block.id) + '" data-placement-id="' + escapeAttr(block.placement_id) + '">' +
        '<div class="cps-block-card__top">' +
          typeBadge(block.type) +
          '<label class="cps-switch cps-switch--sm"><input type="checkbox" ' + (block.enabled ? "checked" : "") + ' aria-label="Bật/tắt ' + escapeAttr(block.id) + '" data-cps-toggle="' + escapeAttr(block.id) + '"><span></span></label>' +
        '</div>' +
        '<h3 class="cps-block-card__title">' + (block.title ? escapeHtml(block.title) : "<em>(chưa có tiêu đề)</em>") + '</h3>' +
        (block.body ? '<p class="cps-block-card__body">' + escapeHtml(block.body) + '</p>' : "") +
        '<div class="cps-block-card__meta">' +
          '<code>' + escapeHtml(block.id) + '</code>' +
          (opts.showPlacement !== false ? '<span class="cps-block-card__placement">' + (placement ? escapeHtml(placement.label) : escapeHtml(block.placement_id)) + '</span>' : "") +
        '</div>' +
        '<div class="cps-block-card__meta cps-block-card__meta--sub">' +
          '<span title="Trang áp dụng">' + pagesLabel(block) + '</span>' +
          (scheduled ? '<span class="cps-block-card__sched" title="Lịch hiển thị">⏱ ' + escapeHtml(block.start_date || "…") + ' → ' + escapeHtml(block.end_date || "…") + '</span>' : "") +
        '</div>' +
        '<div class="cps-block-card__actions">' +
          '<button type="button" class="cps-mini-btn" data-cps-edit="' + escapeAttr(block.id) + '">Sửa</button>' +
          '<button type="button" class="cps-mini-btn" data-cps-duplicate="' + escapeAttr(block.id) + '">Nhân bản</button>' +
          '<button type="button" class="cps-mini-btn cps-mini-btn--danger" data-cps-delete="' + escapeAttr(block.id) + '">Xoá</button>' +
        '</div>' +
      '</article>'
    );
  }

  function renderLibrary() {
    const grid = document.getElementById("cps-library-grid");
    const empty = document.getElementById("cps-library-empty");
    if (!grid) return;
    let blocks = (cpData.blocks || []).slice().sort((a, b) => a.id.localeCompare(b.id));
    if (filters.q) {
      const q = filters.q.toLowerCase();
      blocks = blocks.filter((b) => (b.id + " " + (b.title || "") + " " + (b.body || "")).toLowerCase().includes(q));
    }
    if (filters.types.size) blocks = blocks.filter((b) => filters.types.has(b.type));
    if (filters.onlyEnabled) blocks = blocks.filter((b) => b.enabled);

    grid.innerHTML = blocks.map((b) => blockCardHtml(b, { showPlacement: true })).join("");
    if (empty) empty.hidden = blocks.length > 0;
  }

  function renderCanvas() {
    const host = document.getElementById("cps-canvas");
    if (!host) return;
    const byScope = {};
    (cpData.placements || []).forEach((p) => { (byScope[p.scope] = byScope[p.scope] || []).push(p); });

    let html = "";
    SCOPE_ORDER.filter((s) => byScope[s]).forEach((scope) => {
      const meta = SCOPE_META[scope] || { label: scope, color: "slate" };
      html += '<div class="cps-scope-group"><h3 class="cps-scope-group__title"><span class="cps-scope-dot cps-scope-dot--' + meta.color + '"></span>' + escapeHtml(meta.label) + '</h3><div class="cps-slots">';
      byScope[scope].forEach((p) => {
        const blocks = blocksFor(p.id);
        const hooked = !!p.hooked;
        html +=
          '<div class="cps-slot' + (hooked ? "" : " cps-slot--disabled") + '" data-slot-id="' + escapeAttr(p.id) + '" data-hooked="' + hooked + '">' +
            '<div class="cps-slot__head">' +
              '<span class="cps-slot__label">' + escapeHtml(p.label) + '</span>' +
              (hooked ? '<span class="cps-slot__hook cps-slot__hook--on">● live</span>' : '<span class="cps-slot__hook cps-slot__hook--off" title="Chưa gắn hook trong template — nội dung sẽ không hiển thị">chưa gắn hook</span>') +
            '</div>' +
            '<p class="cps-slot__desc">' + escapeHtml(p.description || "") + '</p>' +
            '<div class="cps-slot__drop" data-drop-zone="' + escapeAttr(p.id) + '">' +
              (blocks.length
                ? blocks.map((b) => blockCardHtml(b, { showPlacement: false })).join("")
                : '<div class="cps-slot__placeholder">' + (hooked ? "Kéo nội dung vào đây" : "Vị trí chưa hỗ trợ — không thể thả") + '</div>') +
            '</div>' +
          '</div>';
      });
      html += "</div></div>";
    });
    host.innerHTML = html;
    wireDropZones();
    wireCardDrag(host);
    wireCardActions(host);
  }

  function miniPlacementBlock(block) {
    const type = block.type || "notice";
    const style = block.style || "default";
    const cta = block.url && block.button_text ? '<a class="placement-block__cta placement-block__cta--' + escapeAttr(type) + '" href="#" onclick="return false">' + escapeHtml(block.button_text) + "</a>" : "";
    return (
      '<div class="placement-block placement-block--' + escapeAttr(type) + " placement-block--" + escapeAttr(style) + '" data-block-id="' + escapeAttr(block.id) + '">' +
        (block.title ? '<p class="placement-block__title">' + escapeHtml(block.title) + "</p>" : "") +
        (block.body ? '<p class="placement-block__body">' + escapeHtml(block.body) + "</p>" : "") +
        cta +
      "</div>"
    );
  }

  function renderPreview() {
    const stage = document.getElementById("cps-preview-stage");
    if (!stage) return;
    const order = [
      ["post_after_intro", "Sau đoạn mở đầu"],
      ["post_after_content", "Sau nội dung chính"],
      ["post_before_related", "Trước bài liên quan"],
      ["post_after_related", "Sau bài liên quan"],
    ];
    let html = "";
    order.forEach(([id, label], idx) => {
      const blocks = blocksFor(id).filter((b) => b.enabled);
      html += '<div class="cps-preview-slot"><span class="cps-preview-slot__tag">' + (idx + 1) + " · " + escapeHtml(label) + "</span>";
      if (blocks.length) {
        html += blocks.map(miniPlacementBlock).join("");
      } else {
        html += '<div class="cps-preview-slot__empty">— trống —</div>';
      }
      html += "</div>";
    });
    stage.innerHTML = html;
  }

  // ============= Drag & drop =============
  function wireCardDrag(scope) {
    scope.querySelectorAll(".cps-block-card[draggable]").forEach((card) => {
      card.addEventListener("dragstart", (ev) => {
        draggingBlockId = card.getAttribute("data-block-id");
        draggingFromPlacement = card.getAttribute("data-placement-id") || null;
        card.classList.add("is-dragging");
        try { ev.dataTransfer.setData("text/plain", draggingBlockId); } catch (e) {}
        ev.dataTransfer.effectAllowed = "move";
      });
      card.addEventListener("dragend", () => {
        card.classList.remove("is-dragging");
        draggingBlockId = null;
        draggingFromPlacement = null;
        document.querySelectorAll(".cps-slot__drop.is-over").forEach((z) => z.classList.remove("is-over"));
      });
    });
  }

  function wireDropZones() {
    document.querySelectorAll(".cps-slot__drop").forEach((zone) => {
      const slotId = zone.getAttribute("data-drop-zone");
      const slot = zone.closest(".cps-slot");
      if (slot && slot.getAttribute("data-hooked") !== "true") return; // not-hooked → not a valid target
      zone.addEventListener("dragover", (ev) => {
        if (!draggingBlockId) return;
        ev.preventDefault();
        ev.dataTransfer.dropEffect = "move";
        zone.classList.add("is-over");
      });
      zone.addEventListener("dragleave", () => zone.classList.remove("is-over"));
      zone.addEventListener("drop", async (ev) => {
        ev.preventDefault();
        zone.classList.remove("is-over");
        const blockId = draggingBlockId || (ev.dataTransfer && ev.dataTransfer.getData("text/plain"));
        if (!blockId) return;
        const block = (cpData.blocks || []).find((b) => b.id === blockId);
        if (!block) return;
        if (block.placement_id === slotId) return; // dropped on its own slot — no-op (reordering handled separately)
        await patchBlock(blockId, { placement_id: slotId, enabled: true }, "Đã chuyển “" + blockId + "” vào " + (placementById(slotId) || {}).label);
      });
    });
  }

  // ============= Card actions (toggle / edit / duplicate / delete) =============
  function wireCardActions(scope) {
    scope.querySelectorAll("[data-cps-toggle]").forEach((input) => {
      input.addEventListener("change", async () => {
        const id = input.getAttribute("data-cps-toggle");
        await patchBlock(id, { enabled: input.checked }, input.checked ? "Đã bật" : "Đã tắt");
      });
    });
    scope.querySelectorAll("[data-cps-edit]").forEach((btn) => {
      btn.addEventListener("click", () => openBlockModal(btn.getAttribute("data-cps-edit")));
    });
    scope.querySelectorAll("[data-cps-duplicate]").forEach((btn) => {
      btn.addEventListener("click", () => duplicateBlock(btn.getAttribute("data-cps-duplicate")));
    });
    scope.querySelectorAll("[data-cps-delete]").forEach((btn) => {
      btn.addEventListener("click", () => deleteBlock(btn.getAttribute("data-cps-delete")));
    });
  }

  async function patchBlock(id, patch, successMsg) {
    try {
      const res = await fetch(AUTH_API + "/admin/content-blocks/" + encodeURIComponent(id), {
        method: "PATCH", credentials: "include", headers: apiHeaders(true), body: JSON.stringify(patch),
      });
      if (!res.ok) throw new Error(await res.text());
      const result = await res.json();
      await loadCpsSilent();
      showToast(successMsg || "Đã lưu", "ok");
      reportCommit(result);
    } catch (e) {
      showToast("Lỗi: " + e.message, "error");
    }
  }

  async function loadCpsSilent() {
    const res = await fetch(AUTH_API + "/admin/content-placements", { credentials: "include", cache: "no-store", headers: apiHeaders(false) });
    if (!res.ok) return;
    cpData = await res.json();
    renderAll();
  }

  function reportCommit(result) {
    const strip = document.getElementById("cps-status-strip");
    if (!strip) return;
    if (result.committed) {
      strip.className = "cps-status-strip cps-status-strip--ok";
      strip.innerHTML = "✓ Đã commit <a href=\"" + escapeAttr(result.commit_url) + "\" target=\"_blank\" rel=\"noopener\">" + escapeHtml((result.commit_sha || "").slice(0, 7)) + "</a> · lên site sau " + escapeHtml(result.deploy_eta || "1-2 phút");
    } else {
      strip.className = "cps-status-strip cps-status-strip--warn";
      strip.innerHTML = "⚠ Lưu cục bộ (chưa auto-deploy): " + escapeHtml(result.reason || result.note || "không có token GitHub");
    }
    strip.hidden = false;
  }

  async function duplicateBlock(id) {
    const block = (cpData.blocks || []).find((b) => b.id === id);
    if (!block) return;
    const clone = Object.assign({}, block, { id: uniqueId(block.id + "_copy"), enabled: false });
    delete clone.id; clone.id = uniqueId(block.id + "_copy");
    try {
      const res = await fetch(AUTH_API + "/admin/content-blocks", { method: "POST", credentials: "include", headers: apiHeaders(true), body: JSON.stringify(clone) });
      if (!res.ok) throw new Error(await res.text());
      const result = await res.json();
      await loadCpsSilent();
      showToast("Đã nhân bản thành “" + clone.id + "” (đang tắt)", "ok");
      reportCommit(result);
    } catch (e) {
      showToast("Nhân bản thất bại: " + e.message, "error");
    }
  }

  async function deleteBlock(id) {
    if (!confirm('Xoá nội dung "' + id + '"? Không thể hoàn tác.')) return;
    try {
      const res = await fetch(AUTH_API + "/admin/content-blocks/" + encodeURIComponent(id), { method: "DELETE", credentials: "include", headers: apiHeaders(false) });
      if (!res.ok) throw new Error(await res.text());
      const result = await res.json();
      await loadCpsSilent();
      showToast("Đã xoá “" + id + "”", "ok");
      reportCommit(result);
    } catch (e) {
      showToast("Xoá thất bại: " + e.message, "error");
    }
  }

  // ============= Modal: create / edit block =============
  const modal = document.getElementById("cps-block-modal");
  const form = document.getElementById("cps-block-form");

  function placementOptionsHtml(selected) {
    let html = "";
    SCOPE_ORDER.forEach((scope) => {
      const list = (cpData.placements || []).filter((p) => p.scope === scope);
      if (!list.length) return;
      html += '<optgroup label="' + escapeAttr((SCOPE_META[scope] || {}).label || scope) + '">';
      list.forEach((p) => {
        const dis = !p.hooked ? " disabled" : "";
        const suffix = !p.hooked ? " (chưa gắn hook)" : "";
        html += '<option value="' + escapeAttr(p.id) + '"' + (p.id === selected ? " selected" : "") + dis + ">" + escapeHtml(p.label) + escapeHtml(suffix) + "</option>";
      });
      html += "</optgroup>";
    });
    return html;
  }

  function typeChipsHtml(selected) {
    return TYPE_ORDER.map((t) => {
      const meta = TYPE_META[t];
      return (
        '<label class="cps-type-chip cps-type-chip--' + meta.color + (t === selected ? " is-active" : "") + '">' +
          '<input type="radio" name="cb-type" value="' + t + '"' + (t === selected ? " checked" : "") + ">" +
          "<i>" + escapeHtml(meta.icon) + "</i><span>" + escapeHtml(meta.label) + "</span>" +
        "</label>"
      );
    }).join("");
  }

  function currentType() {
    const checked = form.querySelector('input[name="cb-type"]:checked');
    return checked ? checked.value : "notice";
  }

  window.cpsOpenCreate = function (presetPlacement) { openBlockModal(null, presetPlacement); };

  function openBlockModal(blockId, presetPlacement) {
    editingId = blockId || null;
    document.getElementById("cps-modal-title").textContent = editingId ? "Sửa nội dung" : "Tạo nội dung mới";
    document.getElementById("cps-delete-inline").hidden = !editingId;

    const block = editingId ? (cpData.blocks || []).find((b) => b.id === editingId) : null;

    document.getElementById("cb-type-group").innerHTML = typeChipsHtml(block ? block.type : "notice");
    document.getElementById("cb-placement").innerHTML = placementOptionsHtml(block ? block.placement_id : presetPlacement || "");

    document.getElementById("cb-id").value = block ? block.id : "";
    document.getElementById("cb-id").readOnly = !!editingId;
    document.getElementById("cb-id-auto-hint").hidden = !!editingId;
    document.getElementById("cb-title").value = block ? block.title || "" : "";
    document.getElementById("cb-body").value = block ? block.body || "" : "";
    document.getElementById("cb-button").value = block ? block.button_text || "" : "";
    document.getElementById("cb-url").value = block ? block.url || "" : "";
    document.getElementById("cb-enabled").checked = block ? !!block.enabled : true;
    document.getElementById("cb-style").value = block ? block.style || "default" : "default";
    document.getElementById("cb-priority").value = block ? block.priority || 100 : 100;
    document.getElementById("cb-start").value = (block && block.start_date) || "";
    document.getElementById("cb-end").value = (block && block.end_date) || "";

    const pages = block ? block.pages || ["*"] : ["*"];
    const isAll = pages.length === 1 && pages[0] === "*";
    form.querySelector('input[name="cb-pages-mode"][value="' + (isAll ? "all" : "custom") + '"]').checked = true;
    document.getElementById("cb-pages").value = isAll ? "" : pages.join("\n");
    document.getElementById("cb-exclude").value = block && block.exclude_pages ? block.exclude_pages.join("\n") : "";
    togglePagesCustom();

    updateMomoHint();
    updatePreview();
    modal.showModal();
    document.getElementById("cb-title").focus();
  }

  function togglePagesCustom() {
    const mode = form.querySelector('input[name="cb-pages-mode"]:checked');
    const box = document.getElementById("cb-pages-box");
    box.hidden = !mode || mode.value !== "custom";
  }

  function updateMomoHint() {
    const type = currentType();
    const meta = TYPE_META[type] || {};
    const hint = document.getElementById("cb-momo-hint");
    const unsafeHint = document.getElementById("cb-unsafe-hint");
    hint.hidden = !meta.momoOnly;
    unsafeHint.hidden = type !== "html_safe";
    document.getElementById("cb-cta-fields").classList.toggle("is-required", !!meta.cta);
  }

  function updatePreview() {
    const type = currentType();
    const style = document.getElementById("cb-style").value || "default";
    const title = document.getElementById("cb-title").value;
    const body = document.getElementById("cb-body").value;
    const button = document.getElementById("cb-button").value;
    const url = document.getElementById("cb-url").value;
    const stage = document.getElementById("cb-preview-stage");
    stage.innerHTML = miniPlacementBlock({ type, style, title, body, button_text: button, url, id: "preview" });
  }

  form.addEventListener("input", (ev) => {
    if (ev.target.name === "cb-type") { updateMomoHint(); updatePreview(); return; }
    if (["cb-title", "cb-body", "cb-button", "cb-url", "cb-style"].includes(ev.target.id)) updatePreview();
  });
  form.addEventListener("change", (ev) => {
    if (ev.target.name === "cb-pages-mode") togglePagesCustom();
  });

  async function submitBlockForm(ev) {
    ev.preventDefault();
    const rawId = document.getElementById("cb-id").value.trim();
    const id = editingId || slugify(rawId || document.getElementById("cb-title").value);
    if (!editingId) document.getElementById("cb-id").value = id;

    const type = currentType();
    const placement = document.getElementById("cb-placement").value;
    if (!placement) { showToast("Vui lòng chọn vị trí hiển thị", "error"); return; }

    const mode = form.querySelector('input[name="cb-pages-mode"]:checked').value;
    let pages = ["*"];
    if (mode === "custom") {
      pages = document.getElementById("cb-pages").value.split(/[\n,]/).map((s) => s.trim()).filter(Boolean).map((s) => (s.startsWith("/") || s === "*" ? s : "/" + s));
      if (!pages.length) { showToast("Nhập ít nhất 1 đường dẫn hoặc chọn Toàn site", "error"); return; }
    }
    const exclude = document.getElementById("cb-exclude").value.split(/[\n,]/).map((s) => s.trim()).filter(Boolean).map((s) => (s.startsWith("/") ? s : "/" + s));

    const payload = {
      id,
      placement_id: placement,
      type,
      title: document.getElementById("cb-title").value || null,
      body: document.getElementById("cb-body").value || null,
      button_text: document.getElementById("cb-button").value || null,
      url: document.getElementById("cb-url").value || null,
      style: document.getElementById("cb-style").value || "default",
      priority: parseInt(document.getElementById("cb-priority").value, 10) || 100,
      enabled: document.getElementById("cb-enabled").checked,
      pages,
      exclude_pages: exclude,
      start_date: document.getElementById("cb-start").value || null,
      end_date: document.getElementById("cb-end").value || null,
    };

    const submitBtn = document.getElementById("cb-submit-btn");
    submitBtn.disabled = true;
    try {
      const method = editingId ? "PATCH" : "POST";
      const url_path = editingId ? "/admin/content-blocks/" + encodeURIComponent(editingId) : "/admin/content-blocks";
      const res = await fetch(AUTH_API + url_path, { method, credentials: "include", headers: apiHeaders(true), body: JSON.stringify(payload) });
      if (!res.ok) throw new Error(await res.text());
      const result = await res.json();
      await loadCpsSilent();
      reportCommit(result);
      modal.close();
      showToast(editingId ? "Đã cập nhật “" + id + "”" : "Đã tạo “" + id + "”", "ok");
      editingId = null;
    } catch (e) {
      showToast("Lưu thất bại: " + e.message, "error");
    } finally {
      submitBtn.disabled = false;
    }
  }

  // ============= Init =============
  function wireStaticUI() {
    document.getElementById("google-login-btn").addEventListener("click", (e) => { e.preventDefault(); startLogin(); });
    document.getElementById("switch-account-btn").addEventListener("click", () => startLogin());
    document.getElementById("auth-retry-btn").addEventListener("click", () => runAuthCheck());
    const logoutBtn = document.getElementById("logout-btn");
    if (logoutBtn) logoutBtn.addEventListener("click", async () => { await logoutRemote(); setAuthState(STATE.GUEST); });

    document.getElementById("cps-add-btn").addEventListener("click", () => openBlockModal(null));
    document.getElementById("cps-close-modal").addEventListener("click", () => modal.close());
    form.addEventListener("submit", submitBlockForm);
    document.getElementById("cb-cancel-btn").addEventListener("click", () => modal.close());
    document.getElementById("cps-delete-inline").addEventListener("click", () => { if (editingId) { const id = editingId; modal.close(); deleteBlock(id); } });

    const search = document.getElementById("cps-search");
    search.addEventListener("input", () => { filters.q = search.value.trim(); renderLibrary(); });
    document.getElementById("cps-only-enabled").addEventListener("change", (e) => { filters.onlyEnabled = e.target.checked; renderLibrary(); });
    document.querySelectorAll("[data-cps-type-filter]").forEach((chip) => {
      chip.addEventListener("click", () => {
        const t = chip.getAttribute("data-cps-type-filter");
        if (filters.types.has(t)) { filters.types.delete(t); chip.classList.remove("is-active"); }
        else { filters.types.add(t); chip.classList.add("is-active"); }
        renderLibrary();
      });
    });

    document.getElementById("cps-retry-btn").addEventListener("click", () => loadCps());
  }

  document.addEventListener("DOMContentLoaded", () => {
    wireStaticUI();
    const { authError } = consumeAuthCallback();
    runAuthCheck(authError);
  });
})();
