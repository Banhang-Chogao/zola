(function () {
  "use strict";

  const root = document.getElementById("notice-board-app");
  if (!root) return;

  const AUTH_API = ((document.querySelector('meta[name="zola-cms-auth-api"]') || {}).content ||
    "https://blog-vipzone-api.onrender.com").replace(/\/$/, "");
  const SESSION_KEY = "zola-cms-session-id";
  const STORAGE_KEY = "zola-notice-board-v1";
  const PAGE_SIZE = 10;
  const REQUIRED_UTM = ["utm_source", "utm_medium", "utm_campaign"];
  const TOKEN_NAMES = ["SOURCE", "MEDIUM", "CAMPAIGN_NAME", "CAMPAIGN_ID", "PLACEMENT", "AD_ID", "KEYWORD"];
  const AUTH_ERRORS = {
    access_denied: "Truy cập bị từ chối: tài khoản không có quyền quản trị.",
    invalid_state: "Phiên đăng nhập hết hạn. Vui lòng thử lại.",
    missing_params: "Callback thiếu tham số. Vui lòng thử lại.",
    token_exchange_failed: "Lỗi xác thực. Vui lòng thử lại sau.",
    github_unreachable: "Không kết nối được tới GitHub. Kiểm tra mạng.",
    github_profile_fetch_failed: "Không đọc được profile đăng nhập. Vui lòng thử lại.",
  };

  let state = { placements: [], utmTemplates: [] };
  let filtered = [];
  let page = 1;
  let activePlacement = null;

  const content = root.querySelector("[data-nb-content]");
  const auth = root.querySelector("[data-nb-auth]");
  const placementDialog = root.querySelector("[data-nb-placement-dialog]");
  const placementForm = root.querySelector("[data-nb-placement-form]");
  const utmDialog = root.querySelector("[data-nb-utm-dialog]");
  const utmForm = root.querySelector("[data-nb-utm-form]");

  function getSid() {
    try { return sessionStorage.getItem(SESSION_KEY) || localStorage.getItem(SESSION_KEY) || ""; }
    catch (_) { return ""; }
  }

  function setSid(sid) {
    try { sessionStorage.setItem(SESSION_KEY, sid); } catch (_) {}
    try { localStorage.setItem(SESSION_KEY, sid); } catch (_) {}
  }

  function clearSid() {
    try { sessionStorage.removeItem(SESSION_KEY); } catch (_) {}
    try { localStorage.removeItem(SESSION_KEY); } catch (_) {}
  }

  function consumeSid() {
    const match = location.hash.match(/(?:^|[#&])sid=([A-Za-z0-9_-]+)/);
    if (!match) return;
    setSid(match[1]);
    history.replaceState(null, "", location.pathname + location.search);
  }

  function consumeAuthError() {
    const params = new URLSearchParams(location.search);
    const err = params.get("auth_error");
    if (!err) return null;
    params.delete("auth_error");
    const qs = params.toString();
    history.replaceState(null, "", location.pathname + (qs ? "?" + qs : ""));
    return err;
  }

  function setAuthView(view, message) {
    auth.dataset.nbAuth = view;
    auth.querySelector("[data-nb-auth-title]").textContent = {
      checking: "Đang kiểm tra quyền quản trị…",
      guest: "Đăng nhập để mở Notice Board",
      denied: "Không có quyền truy cập",
      error: "Không thể xác minh quyền truy cập",
    }[view];
    auth.querySelector("[data-nb-auth-message]").textContent = message || {
      checking: "Notice Board chỉ dành cho admin.",
      guest: "Vui lòng đăng nhập bằng tài khoản nằm trong admin allowlist.",
      denied: "Tài khoản hiện tại không có quyền Admin.",
      error: "Backend xác thực chưa phản hồi. Không mở dữ liệu quản trị khi chưa xác minh.",
    }[view];
    root.querySelector("[data-nb-login]").hidden = view !== "guest" && view !== "denied";
    root.querySelector("[data-nb-retry]").hidden = view !== "error";
    auth.hidden = false;
    content.hidden = true;
  }

  async function authenticate() {
    setAuthView("checking");
    const errCode = consumeAuthError();
    if (errCode) {
      setAuthView("denied", AUTH_ERRORS[errCode] || ("Lỗi xác thực: " + errCode));
      return;
    }
    const sid = getSid();
    if (!sid) return setAuthView("guest");
    const controller = new AbortController();
    const timer = setTimeout(function () { controller.abort(); }, 9000);
    try {
      const response = await fetch(AUTH_API + "/auth/me", {
        headers: { Authorization: "Bearer " + sid },
        credentials: "include",
        cache: "no-store",
        signal: controller.signal,
      });
      if (response.status === 401) return setAuthView("guest");
      if (!response.ok) return setAuthView("error");
      const user = await response.json();
      if (user.is_admin !== true && user.is_super !== true) return setAuthView("denied");
      auth.hidden = true;
      content.hidden = false;
      await loadData();
    } catch (_) {
      setAuthView("error");
    } finally {
      clearTimeout(timer);
    }
  }

  function login() {
    if (!AUTH_API) return;
    const params = new URLSearchParams(location.search);
    params.delete("auth_error");
    const returnTo = location.pathname + (params.toString() ? "?" + params.toString() : "");
    location.href = AUTH_API + "/auth/login?return_to=" + encodeURIComponent(returnTo);
  }

  async function loadData() {
    const saved = readLocal();
    if (saved) {
      state = saved;
    } else {
      const response = await fetch(root.dataset.source, { cache: "no-store" });
      if (!response.ok) throw new Error("Cannot load Notice Board data");
      state = await response.json();
    }
    renderAll();
  }

  function readLocal() {
    try {
      const value = JSON.parse(localStorage.getItem(STORAGE_KEY));
      return value && Array.isArray(value.placements) ? value : null;
    } catch (_) { return null; }
  }

  function saveLocal() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (_) {}
  }

  function totals(item) {
    const days = (item.daily || []).slice(0, 7);
    return days.reduce(function (sum, row) {
      sum.impressions += Number(row.impressions) || 0;
      sum.clicks += Number(row.clicks) || 0;
      sum.revenue += Number(row.revenue) || 0;
      sum.conversions += Number(row.conversions) || 0;
      return sum;
    }, { impressions: 0, clicks: 0, revenue: 0, conversions: 0 });
  }

  function metrics(item) {
    const total = totals(item);
    const cost = Number(item.cost) || 0;
    return Object.assign(total, {
      ctr: total.impressions ? total.clicks / total.impressions * 100 : 0,
      cpc: total.clicks ? cost / total.clicks : 0,
      cpm: total.impressions ? cost / total.impressions * 1000 : 0,
      roas: cost ? total.revenue / cost : 0,
      conversionRate: total.clicks ? total.conversions / total.clicks * 100 : 0,
      rpm: total.impressions ? total.revenue / total.impressions * 1000 : 0,
    });
  }

  function renderAll() {
    populateFilters();
    applyFilters();
    renderKpis();
    renderReports();
    renderIntegrations();
  }

  function renderKpis() {
    const aggregate = state.placements.reduce(function (sum, item) {
      const m = metrics(item);
      sum.impressions += m.impressions; sum.clicks += m.clicks;
      sum.revenue += m.revenue; sum.conversions += m.conversions;
      sum.cost += Number(item.cost) || 0;
      return sum;
    }, { impressions: 0, clicks: 0, revenue: 0, conversions: 0, cost: 0 });
    const values = [
      ["Tổng số", state.placements.length],
      ["Đang hoạt động", state.placements.filter(function (x) { return x.status === "active"; }).length],
      ["CTR TB", pct(aggregate.impressions ? aggregate.clicks / aggregate.impressions * 100 : 0)],
      ["RPM TB", money(aggregate.impressions ? aggregate.revenue / aggregate.impressions * 1000 : 0)],
      ["Total Revenue", money(aggregate.revenue)],
      ["ROAS", (aggregate.cost ? aggregate.revenue / aggregate.cost : 0).toFixed(2) + "x"],
      ["Conversion Rate", pct(aggregate.clicks ? aggregate.conversions / aggregate.clicks * 100 : 0)],
    ];
    root.querySelector("[data-nb-kpis]").innerHTML = values.map(function (value) {
      return '<article><span>' + escapeHtml(value[0]) + '</span><strong>' + escapeHtml(value[1]) + "</strong></article>";
    }).join("");
  }

  function populateFilters() {
    const select = root.querySelector('[data-nb-filter="site"]');
    const current = select.value;
    const sites = Array.from(new Set(state.placements.map(function (x) { return x.site; })));
    select.innerHTML = '<option value="">Tất cả site</option>' + sites.map(function (site) {
      return '<option value="' + escapeHtml(site) + '">' + escapeHtml(site) + "</option>";
    }).join("");
    select.value = current;
  }

  function applyFilters() {
    const query = root.querySelector("[data-nb-search]").value.trim().toLowerCase();
    const site = root.querySelector('[data-nb-filter="site"]').value;
    const status = root.querySelector('[data-nb-filter="status"]').value;
    const type = root.querySelector('[data-nb-filter="type"]').value;
    filtered = state.placements.filter(function (item) {
      return (!query || (item.name + " " + item.zone + " " + item.site).toLowerCase().includes(query)) &&
        (!site || item.site === site) && (!status || item.status === status) && (!type || item.type === type);
    });
    const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
    page = Math.min(page, pages);
    renderPlacementList();
    renderPagination(pages);
  }

  function renderPlacementList() {
    const items = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
    const rows = items.map(function (item) {
      const m = metrics(item);
      return '<tr><td><strong>' + escapeHtml(item.name) + '</strong><small>' + escapeHtml(item.site) + '</small></td>' +
        "<td>" + escapeHtml(item.type) + "<small>" + escapeHtml(item.size) + "</small></td>" +
        "<td>" + escapeHtml(item.zone) + "<small>" + escapeHtml(item.device) + "</small></td>" +
        '<td><span class="notice-status notice-status--' + item.status + '">' + escapeHtml(item.status) + "</span></td>" +
        '<td><div class="notice-performance"><span>Imp <b>' + compact(m.impressions) + "</b></span><span>Clicks <b>" + compact(m.clicks) +
        "</b></span><span>CTR <b>" + pct(m.ctr) + "</b></span><span>Revenue <b>" + money(m.revenue) + "</b></span></div></td>" +
        '<td><div class="notice-row-actions">' + actions(item) + "</div></td></tr>";
    }).join("");
    root.querySelector("[data-nb-placement-list]").innerHTML = rows || '<tr><td colspan="6">Không tìm thấy placement.</td></tr>';
    root.querySelector("[data-nb-mobile-list]").innerHTML = items.map(function (item) {
      const m = metrics(item);
      return '<article class="notice-mobile-card"><header><strong>📍 ' + escapeHtml(item.name) + '</strong><span class="notice-status notice-status--' +
        item.status + '">' + escapeHtml(item.status) + '</span></header><p>' + escapeHtml(item.size) + " · " + escapeHtml(item.zone) +
        '</p><div class="notice-performance"><span>Imp <b>' + compact(m.impressions) + "</b></span><span>CTR <b>" + pct(m.ctr) +
        "</b></span><span>Rev <b>" + money(m.revenue) + '</b></span></div><footer class="notice-row-actions">' + actions(item) + "</footer></article>";
    }).join("");
  }

  function actions(item) {
    return '<button data-nb-row-action="utm" data-id="' + item.id + '">🔗 UTM</button>' +
      '<button data-nb-row-action="report" data-id="' + item.id + '">📊 Stats</button>' +
      '<button data-nb-row-action="edit" data-id="' + item.id + '">✏️ Sửa</button>' +
      '<button data-nb-row-action="toggle" data-id="' + item.id + '">' + (item.status === "active" ? "⏸️" : "▶️") + "</button>" +
      '<button data-nb-row-action="delete" data-id="' + item.id + '">🗑️</button>';
  }

  function renderPagination(pages) {
    let html = '<button data-page="' + (page - 1) + '" ' + (page === 1 ? "disabled" : "") + ">◀</button>";
    for (let i = 1; i <= pages; i += 1) html += '<button data-page="' + i + '" class="' + (i === page ? "is-active" : "") + '">' + i + "</button>";
    html += '<button data-page="' + (page + 1) + '" ' + (page === pages ? "disabled" : "") + ">▶</button><span>Trang " + page + "/" + pages + "</span>";
    root.querySelector("[data-nb-pagination]").innerHTML = html;
  }

  function openPlacement(item) {
    placementForm.reset();
    root.querySelector("[data-nb-placement-form-title]").textContent = item ? "Sửa vị trí" : "Thêm vị trí";
    ["id", "name", "site", "type", "size", "zone", "device", "status", "targetUrl", "targeting", "startDate", "endDate", "adCode"].forEach(function (key) {
      if (item && placementForm.elements[key]) placementForm.elements[key].value = item[key] || "";
    });
    placementDialog.showModal();
  }

  function savePlacement() {
    if (!placementForm.reportValidity()) return;
    const values = Object.fromEntries(new FormData(placementForm).entries());
    let item = state.placements.find(function (x) { return x.id === values.id; });
    if (!item) {
      item = { id: "placement_" + Date.now(), daily: [], cost: 0, utmTemplate: "", tokens: {} };
      state.placements.unshift(item);
    }
    Object.assign(item, values, { id: item.id });
    saveLocal(); placementDialog.close(); renderAll();
  }

  function openUtm(item) {
    activePlacement = item;
    utmForm.reset();
    utmForm.elements.placementId.value = item.id;
    utmForm.elements.utmTemplate.value = item.utmTemplate || "";
    root.querySelector("[data-nb-utm-title]").textContent = item.name;
    const templateSelect = root.querySelector("[data-nb-template-select]");
    templateSelect.innerHTML = '<option value="">Chọn template…</option>' + state.utmTemplates.map(function (template) {
      return '<option value="' + template.id + '">' + escapeHtml(template.name) + "</option>";
    }).join("");
    root.querySelector("[data-nb-token-fields]").innerHTML = TOKEN_NAMES.map(function (name) {
      return '<label>' + name + '<input name="token_' + name + '" value="' + escapeHtml((item.tokens || {})[name] || "") + '"></label>';
    }).join("");
    renderUtmPerformance(item);
    refreshPreview();
    utmDialog.showModal();
  }

  function buildPreview() {
    let template = utmForm.elements.utmTemplate.value.trim();
    template = template.replace(/\{lpurl\}/gi, activePlacement.targetUrl || "");
    TOKEN_NAMES.forEach(function (name) {
      const input = utmForm.elements["token_" + name];
      template = template.replace(new RegExp("\\{\\{" + name + "\\}\\}", "g"), encodeURIComponent(input ? input.value.trim() : ""));
    });
    return template;
  }

  function validateUtm(url) {
    const errors = [];
    const unresolved = url.match(/\{\{[^}]+\}\}|\{lpurl\}/g);
    if (unresolved) errors.push("Token chưa có giá trị: " + unresolved.join(", "));
    try {
      const parsed = new URL(url);
      REQUIRED_UTM.forEach(function (key) { if (!parsed.searchParams.get(key)) errors.push("Thiếu " + key); });
      parsed.searchParams.forEach(function (value, key) {
        if (key.indexOf("utm_") === 0 && /\s/.test(value)) errors.push(key + " chứa khoảng trắng");
      });
    } catch (_) { errors.push("URL không hợp lệ"); }
    return errors;
  }

  function refreshPreview() {
    const preview = buildPreview();
    const errors = validateUtm(preview);
    root.querySelector("[data-nb-preview]").value = preview;
    const validation = root.querySelector("[data-nb-validation]");
    validation.className = "notice-validation " + (errors.length ? "is-error" : "is-valid");
    validation.textContent = errors.length ? errors.join(" · ") : "✓ UTM hợp lệ";
    root.querySelector("[data-nb-open-preview]").href = errors.length ? "#" : preview;
  }

  function saveUtm() {
    refreshPreview();
    if (validateUtm(buildPreview()).length) return;
    activePlacement.utmTemplate = utmForm.elements.utmTemplate.value.trim();
    activePlacement.tokens = {};
    TOKEN_NAMES.forEach(function (name) { activePlacement.tokens[name] = utmForm.elements["token_" + name].value.trim(); });
    saveLocal(); utmDialog.close(); renderAll();
  }

  function renderUtmPerformance(item) {
    const costPerDay = (Number(item.cost) || 0) / Math.max(1, (item.daily || []).length);
    root.querySelector("[data-nb-utm-performance]").innerHTML = (item.daily || []).slice(0, 7).map(function (row) {
      const ctr = row.impressions ? row.clicks / row.impressions * 100 : 0;
      return "<tr><td>" + row.date + "</td><td>" + compact(row.impressions) + "</td><td>" + compact(row.clicks) +
        "</td><td>" + pct(ctr) + "</td><td>" + money(row.revenue) + "</td><td>" +
        (costPerDay ? row.revenue / costPerDay : 0).toFixed(2) + "x</td></tr>";
    }).join("");
  }

  function renderReports() {
    const ranked = state.placements.slice().sort(function (a, b) { return metrics(b).revenue - metrics(a).revenue; });
    root.querySelector("[data-nb-top-list]").innerHTML = ranked.slice(0, 10).map(function (item) {
      return "<li><span>" + escapeHtml(item.name) + "</span><strong>" + money(metrics(item).revenue) + "</strong></li>";
    }).join("");
    renderGroupReport("zone", "[data-nb-zone-report]");
    renderGroupReport("device", "[data-nb-device-report]");
    const utmGroups = {};
    state.placements.forEach(function (item) {
      const key = (item.tokens || {}).PLACEMENT || "not-set";
      utmGroups[key] = (utmGroups[key] || 0) + metrics(item).revenue;
    });
    root.querySelector("[data-nb-utm-report]").innerHTML = reportBars(utmGroups);
    drawChart();
  }

  function renderGroupReport(key, selector) {
    const groups = {};
    state.placements.forEach(function (item) {
      groups[item[key] || "Unknown"] = (groups[item[key] || "Unknown"] || 0) + metrics(item).revenue;
    });
    root.querySelector(selector).innerHTML = reportBars(groups);
  }

  function reportBars(groups) {
    const max = Math.max.apply(null, Object.values(groups).concat([1]));
    return Object.entries(groups).map(function (entry) {
      return '<div class="notice-report-bar"><span>' + escapeHtml(entry[0]) + '</span><i style="width:' +
        Math.max(4, entry[1] / max * 100) + '%"></i><strong>' + money(entry[1]) + "</strong></div>";
    }).join("");
  }

  function drawChart() {
    const canvas = root.querySelector("[data-nb-chart]");
    const ctx = canvas.getContext("2d");
    const byDate = {};
    state.placements.forEach(function (item) {
      (item.daily || []).forEach(function (row) {
        byDate[row.date] = byDate[row.date] || { revenue: 0, clicks: 0 };
        byDate[row.date].revenue += Number(row.revenue) || 0;
        byDate[row.date].clicks += Number(row.clicks) || 0;
      });
    });
    const rows = Object.entries(byDate).sort().slice(-14);
    const width = canvas.width, height = canvas.height, pad = 42;
    ctx.clearRect(0, 0, width, height); ctx.font = "12px sans-serif";
    ctx.strokeStyle = "#d0d7de"; ctx.beginPath(); ctx.moveTo(pad, 10); ctx.lineTo(pad, height - pad); ctx.lineTo(width - 10, height - pad); ctx.stroke();
    if (!rows.length) return;
    const max = Math.max.apply(null, rows.map(function (x) { return x[1].revenue; }).concat([1]));
    const gap = (width - pad - 20) / rows.length;
    rows.forEach(function (entry, index) {
      const barHeight = entry[1].revenue / max * (height - pad - 25);
      ctx.fillStyle = "#0969da"; ctx.fillRect(pad + index * gap + 5, height - pad - barHeight, Math.max(8, gap - 12), barHeight);
      ctx.fillStyle = "#57606a"; ctx.fillText(entry[0].slice(5), pad + index * gap, height - 18);
    });
  }

  function renderIntegrations() {
    const platforms = [["Google Ads", "Tracking template"], ["Facebook Ads", "URL parameters"], ["TikTok Ads", "URL parameters"]];
    root.querySelector("[data-nb-integrations]").innerHTML = platforms.map(function (item) {
      return '<article><div><h3>' + item[0] + '</h3><p>' + item[1] + ' adapter</p></div><span>Chưa cấu hình</span>' +
        '<button class="notice-btn" data-nb-copy-payload="' + item[0] + '">Copy tracking payload</button></article>';
    }).join("");
  }

  function exportRows() {
    return state.placements.map(function (item) {
      const m = metrics(item);
      return [item.name, item.site, item.type, item.size, item.zone, item.device, item.status, m.impressions, m.clicks,
        m.ctr.toFixed(2), m.cpc.toFixed(2), m.cpm.toFixed(2), m.revenue.toFixed(2), m.roas.toFixed(2), m.conversionRate.toFixed(2)];
    });
  }

  function exportReport(type) {
    const headers = ["Placement", "Site", "Type", "Size", "Zone", "Device", "Status", "Impressions", "Clicks", "CTR", "CPC", "CPM", "Revenue", "ROAS", "Conversion Rate"];
    if (type === "pdf") return window.print();
    if (type === "excel") {
      const table = "<table><tr><th>" + headers.join("</th><th>") + "</th></tr>" + exportRows().map(function (row) {
        return "<tr><td>" + row.map(escapeHtml).join("</td><td>") + "</td></tr>";
      }).join("") + "</table>";
      return download("notice-board-report.xls", "application/vnd.ms-excel", table);
    }
    const csv = [headers].concat(exportRows()).map(function (row) {
      return row.map(function (cell) { return '"' + String(cell).replace(/"/g, '""') + '"'; }).join(",");
    }).join("\n");
    download("notice-board-report.csv", "text/csv;charset=utf-8", "\ufeff" + csv);
  }

  function download(name, type, text) {
    const url = URL.createObjectURL(new Blob([text], { type: type }));
    const link = document.createElement("a"); link.href = url; link.download = name; link.click();
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  }

  function selectTab(name) {
    root.querySelectorAll("[data-nb-tab]").forEach(function (button) { button.classList.toggle("is-active", button.dataset.nbTab === name); });
    root.querySelectorAll("[data-nb-panel]").forEach(function (panel) { panel.hidden = panel.dataset.nbPanel !== name; });
    if (name === "reports") setTimeout(drawChart, 0);
  }

  root.addEventListener("click", function (event) {
    const tab = event.target.closest("[data-nb-tab]");
    if (tab) return selectTab(tab.dataset.nbTab);
    const rowAction = event.target.closest("[data-nb-row-action]");
    if (rowAction) {
      const item = state.placements.find(function (x) { return x.id === rowAction.dataset.id; });
      if (!item) return;
      if (rowAction.dataset.nbRowAction === "utm") return openUtm(item);
      if (rowAction.dataset.nbRowAction === "report") { selectTab("reports"); return; }
      if (rowAction.dataset.nbRowAction === "edit") return openPlacement(item);
      if (rowAction.dataset.nbRowAction === "toggle") {
        item.status = item.status === "active" ? "inactive" : "active"; saveLocal(); return renderAll();
      }
      if (rowAction.dataset.nbRowAction === "delete" && confirm("Xoá placement " + item.name + "?")) {
        state.placements = state.placements.filter(function (x) { return x.id !== item.id; }); saveLocal(); renderAll();
      }
    }
    const pageButton = event.target.closest("[data-page]");
    if (pageButton && !pageButton.disabled) { page = Number(pageButton.dataset.page); renderPlacementList(); renderPagination(Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))); }
    const action = event.target.closest("[data-nb-action]");
    if (action) {
      if (action.dataset.nbAction === "new") openPlacement(null);
      if (action.dataset.nbAction === "search") root.querySelector("[data-nb-search]").focus();
      if (action.dataset.nbAction === "first-utm" && state.placements[0]) openUtm(state.placements[0]);
    }
    const exportButton = event.target.closest("[data-nb-export]");
    if (exportButton) exportReport(exportButton.dataset.nbExport);
    const payloadButton = event.target.closest("[data-nb-copy-payload]");
    if (payloadButton) navigator.clipboard.writeText(JSON.stringify({
      platform: payloadButton.dataset.nbCopyPayload,
      templates: state.placements.map(function (item) { return { placement: item.id, tracking_template: item.utmTemplate }; }),
    }, null, 2));
  });

  root.querySelector("[data-nb-search]").addEventListener("input", function () { page = 1; applyFilters(); });
  root.querySelectorAll("[data-nb-filter]").forEach(function (select) { select.addEventListener("change", function () { page = 1; applyFilters(); }); });
  root.querySelector("[data-nb-login]").addEventListener("click", login);
  root.querySelector("[data-nb-retry]").addEventListener("click", authenticate);
  root.querySelector("[data-nb-save-placement]").addEventListener("click", function (event) { event.preventDefault(); savePlacement(); });
  root.querySelector("[data-nb-save-utm]").addEventListener("click", function (event) { event.preventDefault(); saveUtm(); });
  root.querySelector("[data-nb-refresh-preview]").addEventListener("click", refreshPreview);
  root.querySelector("[data-nb-copy-template]").addEventListener("click", function () { navigator.clipboard.writeText(utmForm.elements.utmTemplate.value); });
  root.querySelector("[data-nb-template-select]").addEventListener("change", function (event) {
    const template = state.utmTemplates.find(function (x) { return x.id === event.target.value; });
    if (template) { utmForm.elements.utmTemplate.value = template.value; refreshPreview(); }
  });
  utmForm.addEventListener("input", refreshPreview);

  function compact(value) { return new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 }).format(value || 0); }
  function money(value) { return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(value || 0); }
  function pct(value) { return (Number(value) || 0).toFixed(2) + "%"; }
  function escapeHtml(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, function (char) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[char];
    });
  }

  consumeSid();
  authenticate();
}());
