/**
 * World Cup 2026 — Content Manager (client-side CMS)
 * Loads the page's current data/worldcup_2026.json (embedded by Tera),
 * lets an editor add/edit/delete/reorder every content type via forms,
 * autosaves a draft to localStorage, and exports the updated JSON
 * (download or copy) to feed the public /worldcup-2026/ page.
 * 100% front-end — no backend needed on the static host.
 */
(function () {
  'use strict';

  var root = document.getElementById('wcm-root');
  if (!root) return;
  var DRAFT_KEY = 'wcm-draft-v1';

  /* ---------- Original embedded data ---------- */
  var ORIGINAL = {};
  try { ORIGINAL = JSON.parse(document.getElementById('wcm-data').textContent || '{}'); }
  catch (e) { ORIGINAL = {}; }

  /* ---------- Schema describing every section ---------- */
  var CATS = [
    { v: 'tin-nong', t: 'Tin nóng' }, { v: 'nhan-dinh', t: 'Nhận định' },
    { v: 'vui', t: 'Vui cùng WC' }, { v: 'lich-thi-dau', t: 'Lịch thi đấu' },
    { v: 'doi-tuyen', t: 'Đội tuyển' }, { v: 'ben-le', t: 'Bên lề' },
    { v: 'goc-nhin-doi-song', t: 'Góc nhìn đời sống' }
  ];
  var STATUSES = [{ v: 'done', t: 'Đã đá (FT)' }, { v: 'live', t: 'Đang đá (LIVE)' }, { v: 'upcoming', t: 'Sắp đá' }];

  var SCHEMA = {
    news: {
      tab: '📰 Tin tức', kind: 'list', key: 'news', titleField: 'title',
      help: 'Bài viết hiển thị ở khu nội dung chính. Đánh dấu “Bài nổi bật” cho 1 bài để lên khung lớn đầu trang.',
      fields: [
        { k: 'title', l: 'Tiêu đề', type: 'text', req: true },
        { k: 'summary', l: 'Tóm tắt / mô tả ngắn', type: 'textarea' },
        { k: 'category', l: 'Chuyên mục', type: 'select', options: CATS },
        { k: 'date', l: 'Ngày đăng', type: 'date' },
        { k: 'image', l: 'Ảnh (seed hoặc đường dẫn)', type: 'text', hint: 'vd: messi-argentina — dùng làm ảnh minh hoạ' },
        { k: 'views', l: 'Lượt xem (hiển thị)', type: 'text', hint: 'vd: 24.512' },
        { k: 'comments', l: 'Số bình luận', type: 'text' },
        { k: 'source_label', l: 'Nguồn', type: 'text' },
        { k: 'url', l: 'Link bài gốc (tuỳ chọn)', type: 'text', hint: 'để trống nếu không có' },
        { k: 'is_featured', l: '⭐ Bài nổi bật (lên khung lớn)', type: 'checkbox' }
      ],
      defaults: function () { return { id: 'wc-' + Date.now(), title: 'Bài viết mới', summary: '', category: 'tin-nong', date: today(), source_label: 'SEOMONEY Editorial', image: 'wc-' + Date.now(), views: '0', comments: '0', url: null, is_featured: false }; }
    },
    matches: {
      tab: '⚽ Lịch & kết quả', kind: 'list', key: 'matches', titleField: 'home',
      help: 'Các trận hiển thị ở khung “Lịch thi đấu & Kết quả” trong sidebar.',
      summary: function (m) { return (m.home_flag || '') + ' ' + (m.home || '?') + '  ' + (m.score || 'VS') + '  ' + (m.away || '?') + ' ' + (m.away_flag || ''); },
      fields: [
        { k: 'stage', l: 'Bảng / vòng', type: 'text', hint: 'vd: Bảng H, Tứ kết' },
        { k: 'home', l: 'Đội nhà', type: 'text', req: true },
        { k: 'home_flag', l: 'Cờ đội nhà (emoji)', type: 'text', hint: 'vd: 🇦🇷' },
        { k: 'away', l: 'Đội khách', type: 'text', req: true },
        { k: 'away_flag', l: 'Cờ đội khách (emoji)', type: 'text' },
        { k: 'score', l: 'Tỉ số', type: 'text', hint: 'vd: 2 - 0 — để trống nếu chưa đá' },
        { k: 'status', l: 'Trạng thái', type: 'select', options: STATUSES },
        { k: 'date', l: 'Ngày', type: 'date' },
        { k: 'time_vn', l: 'Giờ VN', type: 'text', hint: 'vd: 20:00' },
        { k: 'venue', l: 'Sân / địa điểm', type: 'text' }
      ],
      defaults: function () { return { id: 'm-' + Date.now(), stage: 'Bảng H', home: 'Đội A', home_flag: '🏳️', away: 'Đội B', away_flag: '🏳️', date: today(), time_vn: '20:00', venue: '', status: 'upcoming', score: null }; }
    },
    scorers: {
      tab: '👑 Vua phá lưới', kind: 'list', key: 'scorers', titleField: 'name',
      help: 'Bảng xếp hạng ghi bàn. Thanh tiến độ tự tính theo người dẫn đầu (mục đầu danh sách).',
      summary: function (s) { return (s.emoji || '') + ' ' + (s.name || '?') + ' — ' + (s.goals || 0) + ' bàn'; },
      fields: [
        { k: 'name', l: 'Tên cầu thủ', type: 'text', req: true },
        { k: 'country', l: 'Quốc gia (kèm cờ)', type: 'text', hint: 'vd: 🇫🇷 Pháp' },
        { k: 'goals', l: 'Số bàn', type: 'number' },
        { k: 'emoji', l: 'Biểu tượng', type: 'text', hint: 'vd: ⚡ 🐐 🔥' }
      ],
      defaults: function () { return { name: 'Cầu thủ mới', country: '🏳️ ?', goals: 0, emoji: '⚽' }; }
    },
    stats: {
      tab: '📈 Thống kê', kind: 'list', key: 'stats', titleField: 'label',
      help: 'Ô số liệu nhanh trong sidebar. Điền “Số” để chạy hiệu ứng đếm, hoặc “Chữ” cho dòng văn bản (vd: Mbappe — 8 bàn).',
      summary: function (s) { return (s.icon || '') + ' ' + (s.label || '?') + ': ' + (s.text || s.value || ''); },
      fields: [
        { k: 'icon', l: 'Biểu tượng', type: 'text', hint: 'vd: ⚽ 🟨' },
        { k: 'label', l: 'Nhãn', type: 'text', req: true },
        { k: 'value', l: 'Số (để chạy đếm)', type: 'number', hint: 'để trống nếu dùng “Chữ”' },
        { k: 'text', l: 'Chữ (ô rộng)', type: 'text', hint: 'để trống nếu dùng “Số”' }
      ],
      defaults: function () { return { icon: '⚽', label: 'Chỉ số mới', value: 0 }; }
    },
    ticker: {
      tab: '📣 Tin chạy', kind: 'strings', key: 'ticker',
      help: 'Dòng tin chạy (marquee) màu nổi bật ở đầu trang. Mỗi dòng là một mẩu tin ngắn.'
    },
    videos: {
      tab: '🎬 Video', kind: 'list', key: 'videos', titleField: 'title',
      help: 'Video nổi bật trong sidebar (mở YouTube ở tab mới).',
      summary: function (v) { return '🎬 ' + (v.title || '?'); },
      fields: [
        { k: 'title', l: 'Tiêu đề video', type: 'text', req: true },
        { k: 'seed', l: 'Ảnh thumbnail (seed)', type: 'text', hint: 'vd: wcvideo1' },
        { k: 'yt', l: 'YouTube video ID', type: 'text', hint: 'phần sau v= trong link YouTube' }
      ],
      defaults: function () { return { title: 'Video mới', seed: 'wcvideo' + Date.now(), yt: 'dQw4w9WgXcQ' }; }
    },
    teams: {
      tab: '🏆 Đội tuyển', kind: 'list', key: 'teams', titleField: 'name',
      help: 'Danh sách đội tuyển theo dõi (hiển thị nếu trang có khu vực đội tuyển).',
      summary: function (t) { return (t.flag || '') + ' ' + (t.name || '?') + ' — ' + (t.note || ''); },
      fields: [
        { k: 'name', l: 'Tên đội', type: 'text', req: true },
        { k: 'flag', l: 'Cờ (emoji)', type: 'text' },
        { k: 'note', l: 'Ghi chú', type: 'text', hint: 'vd: Đương kim vô địch' }
      ],
      defaults: function () { return { name: 'Đội mới', flag: '🏳️', note: '' }; }
    },
    editorials: {
      tab: '💭 Bên lề', kind: 'list', key: 'editorials', titleField: 'title',
      help: 'Bài “Bên lề & đời sống” ở cuối khu nội dung chính.',
      summary: function (e) { return '💭 ' + (e.title || '?'); },
      fields: [
        { k: 'title', l: 'Tiêu đề', type: 'text', req: true },
        { k: 'excerpt', l: 'Trích dẫn ngắn', type: 'textarea' },
        { k: 'slug', l: 'Slug (định danh)', type: 'text' }
      ],
      defaults: function () { return { title: 'Bài bên lề mới', excerpt: '', slug: 'bai-moi-' + Date.now() }; }
    },
    standings: {
      tab: '📊 Bảng xếp hạng', kind: 'standings', key: 'standings',
      help: 'Các bảng đấu (vd Bảng H, Bảng G). Mỗi đội: T(rận) Th(ắng) H(oà) B(ại) HS(hiệu số) Đ(iểm).',
      fields: [
        { k: 'team', l: 'Đội', type: 'text', req: true },
        { k: 'flag', l: 'Cờ', type: 'text' },
        { k: 'p', l: 'Trận', type: 'number' }, { k: 'w', l: 'Thắng', type: 'number' },
        { k: 'd', l: 'Hoà', type: 'number' }, { k: 'l', l: 'Bại', type: 'number' },
        { k: 'gd', l: 'Hiệu số', type: 'text', hint: 'vd: +6' }, { k: 'pts', l: 'Điểm', type: 'number' }
      ],
      rowDefaults: function () { return { team: 'Đội mới', flag: '🏳️', p: 0, w: 0, d: 0, l: 0, gd: '0', pts: 0 }; }
    },
    meta: {
      tab: '⚙️ Thông tin giải', kind: 'object', key: 'meta',
      help: 'Thông tin chung của giải. (updated_at sẽ tự cập nhật khi bạn xuất JSON.)',
      fields: [
        { k: 'tournament', l: 'Tên giải', type: 'text' },
        { k: 'hosts', l: 'Nước chủ nhà (ngăn bởi dấu phẩy)', type: 'text', list: true },
        { k: 'teams_count', l: 'Số đội', type: 'number' },
        { k: 'groups_count', l: 'Số bảng', type: 'number' },
        { k: 'start_date', l: 'Ngày khai mạc', type: 'date' },
        { k: 'end_date', l: 'Ngày bế mạc', type: 'date' }
      ]
    }
  };
  var ORDER = ['news', 'matches', 'standings', 'scorers', 'stats', 'ticker', 'videos', 'teams', 'editorials', 'meta'];

  /* ---------- State ---------- */
  var state = { data: null, active: 'news' };

  function today() {
    var d = new Date();
    return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
  }
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function clone(o) { return JSON.parse(JSON.stringify(o)); }
  function el(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  /* ---------- Load (draft or original) ---------- */
  function loadInitial() {
    var draft = null;
    try { draft = JSON.parse(localStorage.getItem(DRAFT_KEY)); } catch (e) {}
    if (draft && typeof draft === 'object') {
      state.data = draft;
      show('#wcm-restore', false);
      toast('Đã khôi phục bản nháp trong trình duyệt 📝');
    } else {
      state.data = clone(ORIGINAL);
    }
    ensureShape();
  }
  function ensureShape() {
    var d = state.data;
    d.meta = d.meta || {};
    ['news', 'matches', 'scorers', 'stats', 'ticker', 'videos', 'teams', 'editorials'].forEach(function (k) {
      if (!Array.isArray(d[k])) d[k] = [];
    });
    if (!d.standings || typeof d.standings !== 'object' || Array.isArray(d.standings)) d.standings = {};
  }

  /* ---------- Persist ---------- */
  var saveTimer;
  function autosave() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(function () {
      try { localStorage.setItem(DRAFT_KEY, JSON.stringify(state.data)); setSaved('Đã lưu nháp ✓'); } catch (e) { setSaved('Không lưu được nháp'); }
    }, 400);
  }
  function setSaved(msg) { var s = document.getElementById('wcm-saved'); if (s) s.textContent = msg; }

  /* ---------- Outputs ---------- */
  function exportData() {
    var out = clone(state.data);
    out.meta = out.meta || {};
    out.meta.updated_at = new Date().toISOString();
    return out;
  }
  function refreshOutputs() {
    var pre = document.getElementById('wcm-json');
    if (pre) pre.textContent = JSON.stringify(state.data, null, 2);
    renderPreview();
    autosave();
  }

  /* ---------- Tabs ---------- */
  function renderTabs() {
    var nav = document.getElementById('wcm-tabs');
    nav.innerHTML = '';
    ORDER.forEach(function (key) {
      var sec = SCHEMA[key];
      var count = countOf(key);
      var b = el('button', 'wcm__tab' + (state.active === key ? ' wcm__tab--active' : ''));
      b.type = 'button';
      b.innerHTML = esc(sec.tab) + (count != null ? ' <span class="wcm__count">' + count + '</span>' : '');
      b.addEventListener('click', function () { state.active = key; renderTabs(); renderEditor(); });
      nav.appendChild(b);
    });
  }
  function countOf(key) {
    var sec = SCHEMA[key], d = state.data;
    if (sec.kind === 'list' || sec.kind === 'strings') return (d[key] || []).length;
    if (sec.kind === 'standings') { var n = 0; Object.keys(d.standings || {}).forEach(function (g) { n += (d.standings[g] || []).length; }); return n; }
    return null;
  }

  /* ---------- Field input builder ---------- */
  function buildField(field, value, onChange) {
    var wrap = el('label', 'wcm__field');
    var lab = el('span', 'wcm__label', esc(field.l) + (field.req ? ' <i>*</i>' : ''));
    wrap.appendChild(lab);
    var input;
    if (field.type === 'textarea') {
      input = el('textarea'); input.rows = 3; input.value = value == null ? '' : value;
    } else if (field.type === 'select') {
      input = el('select');
      field.options.forEach(function (o) {
        var op = el('option'); op.value = o.v; op.textContent = o.t; if (value === o.v) op.selected = true; input.appendChild(op);
      });
    } else if (field.type === 'checkbox') {
      wrap.className = 'wcm__field wcm__field--check';
      input = el('input'); input.type = 'checkbox'; input.checked = !!value;
      wrap.insertBefore(input, lab);
    } else {
      input = el('input');
      input.type = field.type === 'number' ? 'number' : (field.type === 'date' ? 'date' : 'text');
      input.value = value == null ? '' : value;
    }
    input.className = 'wcm__input';
    if (field.hint) { var h = el('span', 'wcm__hint-sm', esc(field.hint)); wrap.appendChild(h); }
    input.addEventListener('input', function () { onChange(readInput(input, field)); });
    input.addEventListener('change', function () { onChange(readInput(input, field)); });
    return wrap;
  }
  function readInput(input, field) {
    if (field.type === 'checkbox') return input.checked;
    if (field.type === 'number') return input.value === '' ? null : Number(input.value);
    if (field.list) return input.value.split(',').map(function (s) { return s.trim(); }).filter(Boolean);
    if (field.k === 'url' && input.value.trim() === '') return null;
    return input.value;
  }

  /* ---------- Editor render ---------- */
  function renderEditor() {
    var host = document.getElementById('wcm-editor');
    host.innerHTML = '';
    var sec = SCHEMA[state.active];
    var head = el('div', 'wcm__sec-head');
    head.appendChild(el('p', 'wcm__sec-help', esc(sec.help || '')));
    host.appendChild(head);

    if (sec.kind === 'list') renderList(host, sec);
    else if (sec.kind === 'strings') renderStrings(host, sec);
    else if (sec.kind === 'standings') renderStandings(host, sec);
    else if (sec.kind === 'object') renderObject(host, sec);
  }

  function itemActions(arr, idx, onChange) {
    var row = el('div', 'wcm__item-acts');
    function mk(label, title, fn, cls) { var b = el('button', 'wcm__mini-btn' + (cls ? ' ' + cls : ''), label); b.type = 'button'; b.title = title; b.addEventListener('click', function (e) { e.stopPropagation(); fn(); }); return b; }
    row.appendChild(mk('↑', 'Lên', function () { if (idx > 0) { var t = arr[idx - 1]; arr[idx - 1] = arr[idx]; arr[idx] = t; onChange(); } }));
    row.appendChild(mk('↓', 'Xuống', function () { if (idx < arr.length - 1) { var t = arr[idx + 1]; arr[idx + 1] = arr[idx]; arr[idx] = t; onChange(); } }));
    row.appendChild(mk('⧉', 'Nhân bản', function () { arr.splice(idx + 1, 0, clone(arr[idx])); onChange(); }));
    row.appendChild(mk('🗑', 'Xoá', function () { if (confirm('Xoá mục này?')) { arr.splice(idx, 1); onChange(); } }, 'wcm__mini-btn--danger'));
    return row;
  }

  function renderList(host, sec) {
    var arr = state.data[sec.key];
    var addBar = el('div', 'wcm__addbar');
    var add = el('button', 'wcm__btn wcm__btn--primary', '＋ Thêm mục mới');
    add.type = 'button';
    add.addEventListener('click', function () {
      arr.unshift(sec.defaults());
      renderTabs(); renderEditor(); refreshOutputs();
      var first = host.querySelector('.wcm__card'); if (first) { first.classList.add('wcm__card--open'); first.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
    });
    addBar.appendChild(add);
    host.appendChild(addBar);

    if (!arr.length) { host.appendChild(el('div', 'wcm__empty', 'Chưa có mục nào. Bấm “＋ Thêm mục mới”.')); return; }

    arr.forEach(function (item, idx) {
      var card = el('div', 'wcm__card');
      var header = el('button', 'wcm__card-head'); header.type = 'button';
      var sumText = sec.summary ? sec.summary(item) : (item[sec.titleField] || '(chưa có tiêu đề)');
      header.innerHTML = '<span class="wcm__card-sum">' + esc(sumText) + '</span><span class="wcm__card-toggle">✏️</span>';
      header.addEventListener('click', function () { card.classList.toggle('wcm__card--open'); });
      if (item.is_featured) card.classList.add('wcm__card--featured');
      card.appendChild(header);

      var body = el('div', 'wcm__card-body');
      var grid = el('div', 'wcm__grid');
      sec.fields.forEach(function (f) {
        if (f.type === 'textarea' || f.k === 'url') {} // full width handled by css class
        var fieldEl = buildField(f, item[f.k], function (val) {
          if (f.k === 'is_featured' && val === true) { arr.forEach(function (o) { if (o !== item) o.is_featured = false; }); }
          item[f.k] = val;
          var sumEl = header.querySelector('.wcm__card-sum');
          if (sumEl) sumEl.textContent = sec.summary ? sec.summary(item) : (item[sec.titleField] || '(chưa có tiêu đề)');
          card.classList.toggle('wcm__card--featured', !!item.is_featured);
          refreshOutputs();
        });
        if (f.type === 'textarea' || f.type === 'checkbox') fieldEl.classList.add('wcm__field--wide');
        grid.appendChild(fieldEl);
      });
      body.appendChild(grid);
      body.appendChild(itemActions(arr, idx, function () { renderTabs(); renderEditor(); refreshOutputs(); }));
      card.appendChild(body);
      host.appendChild(card);
    });
  }

  function renderStrings(host, sec) {
    var arr = state.data[sec.key];
    var addBar = el('div', 'wcm__addbar');
    var add = el('button', 'wcm__btn wcm__btn--primary', '＋ Thêm dòng tin');
    add.type = 'button';
    add.addEventListener('click', function () { arr.unshift('Tin mới'); renderTabs(); renderEditor(); refreshOutputs(); });
    addBar.appendChild(add); host.appendChild(addBar);
    if (!arr.length) { host.appendChild(el('div', 'wcm__empty', 'Chưa có dòng tin nào.')); return; }
    arr.forEach(function (str, idx) {
      var row = el('div', 'wcm__strrow');
      var input = el('input', 'wcm__input'); input.type = 'text'; input.value = str;
      input.addEventListener('input', function () { arr[idx] = input.value; refreshOutputs(); });
      row.appendChild(input);
      row.appendChild(itemActions(arr, idx, function () { renderEditor(); refreshOutputs(); }));
      host.appendChild(row);
    });
  }

  function renderStandings(host, sec) {
    var groups = state.data.standings;
    var addG = el('div', 'wcm__addbar');
    var ng = el('input', 'wcm__input wcm__input--inline'); ng.type = 'text'; ng.placeholder = 'Tên bảng mới (vd: F)';
    var addBtn = el('button', 'wcm__btn wcm__btn--soft', '＋ Thêm bảng');
    addBtn.type = 'button';
    addBtn.addEventListener('click', function () {
      var name = (ng.value || '').trim(); if (!name) { toast('Nhập tên bảng'); return; }
      if (groups[name]) { toast('Bảng đã tồn tại'); return; }
      groups[name] = []; renderTabs(); renderEditor(); refreshOutputs();
    });
    addG.appendChild(ng); addG.appendChild(addBtn); host.appendChild(addG);

    var keys = Object.keys(groups);
    if (!keys.length) { host.appendChild(el('div', 'wcm__empty', 'Chưa có bảng nào.')); return; }

    keys.forEach(function (g) {
      var rows = groups[g];
      var block = el('div', 'wcm__group');
      var gh = el('div', 'wcm__group-head');
      gh.innerHTML = '<b>Bảng ' + esc(g) + '</b>';
      var delG = el('button', 'wcm__mini-btn wcm__mini-btn--danger', '🗑 Xoá bảng'); delG.type = 'button';
      delG.addEventListener('click', function () { if (confirm('Xoá cả bảng ' + g + '?')) { delete groups[g]; renderTabs(); renderEditor(); refreshOutputs(); } });
      gh.appendChild(delG);
      block.appendChild(gh);

      rows.forEach(function (rowData, idx) {
        var rcard = el('div', 'wcm__standrow');
        var grid = el('div', 'wcm__grid wcm__grid--tight');
        sec.fields.forEach(function (f) {
          var fe = buildField(f, rowData[f.k], function (val) { rowData[f.k] = val; refreshOutputs(); });
          grid.appendChild(fe);
        });
        rcard.appendChild(grid);
        rcard.appendChild(itemActions(rows, idx, function () { renderEditor(); refreshOutputs(); }));
        block.appendChild(rcard);
      });

      var addRow = el('button', 'wcm__btn wcm__btn--ghost', '＋ Thêm đội vào bảng ' + g); addRow.type = 'button';
      addRow.addEventListener('click', function () { rows.push(sec.rowDefaults()); renderTabs(); renderEditor(); refreshOutputs(); });
      block.appendChild(addRow);
      host.appendChild(block);
    });
  }

  function renderObject(host, sec) {
    var obj = state.data[sec.key] = state.data[sec.key] || {};
    var grid = el('div', 'wcm__grid');
    sec.fields.forEach(function (f) {
      var val = obj[f.k];
      if (f.list && Array.isArray(val)) val = val.join(', ');
      var fe = buildField(f, val, function (v) { obj[f.k] = v; refreshOutputs(); });
      grid.appendChild(fe);
    });
    host.appendChild(grid);
  }

  /* ---------- Preview ---------- */
  function renderPreview() {
    var host = document.getElementById('wcm-preview');
    if (!host) return;
    var d = state.data;
    var featured = (d.news || []).filter(function (n) { return n.is_featured; })[0];
    var rest = (d.news || []).filter(function (n) { return !n.is_featured; });
    var html = '';
    if (featured) {
      html += '<div class="wcm-pv-featured"><span class="wcm-pv-tag">⭐ Nổi bật</span><h4>' + esc(featured.title) + '</h4><p>' + esc(featured.summary || '') + '</p></div>';
    }
    if (rest.length) {
      html += '<div class="wcm-pv-grid">' + rest.slice(0, 6).map(function (n) {
        return '<div class="wcm-pv-card"><span class="wcm-pv-cat">' + esc(catLabel(n.category)) + '</span><h5>' + esc(n.title) + '</h5><p>' + esc((n.summary || '').slice(0, 90)) + '</p></div>';
      }).join('') + '</div>';
    }
    var matches = d.matches || [];
    if (matches.length) {
      html += '<div class="wcm-pv-matches"><b>⚽ Lịch & kết quả</b>' + matches.map(function (m) {
        var st = m.status === 'live' ? '<i class="wcm-pv-live">LIVE</i>' : (m.status === 'done' ? '<i class="wcm-pv-ft">FT</i>' : '<i class="wcm-pv-soon">SẮP</i>');
        return '<div class="wcm-pv-match"><span>' + esc((m.home_flag || '') + ' ' + (m.home || '')) + '</span><b>' + esc(m.score || 'VS') + '</b><span>' + esc((m.away || '') + ' ' + (m.away_flag || '')) + '</span>' + st + '</div>';
      }).join('') + '</div>';
    }
    var warn = '';
    var feats = (d.news || []).filter(function (n) { return n.is_featured; }).length;
    if (feats === 0) warn = '⚠️ Chưa có bài nổi bật — khu khung lớn sẽ trống.';
    else if (feats > 1) warn = '⚠️ Có ' + feats + ' bài đánh dấu nổi bật — trang chỉ nên có 1.';
    host.innerHTML = (warn ? '<div class="wcm-pv-warn">' + warn + '</div>' : '') + (html || '<p class="wcm__empty">Chưa có nội dung để xem trước.</p>');
  }
  function catLabel(v) { for (var i = 0; i < CATS.length; i++) if (CATS[i].v === v) return CATS[i].t; return v || ''; }

  /* ---------- Toolbar ---------- */
  function toast(msg) {
    var t = document.getElementById('wcm-toast');
    t.textContent = msg; t.classList.add('wcm__toast--show');
    clearTimeout(t._tm); t._tm = setTimeout(function () { t.classList.remove('wcm__toast--show'); }, 2400);
  }
  function show(sel, on) { var e = document.querySelector(sel); if (e) e.hidden = !on; }

  document.getElementById('wcm-download').addEventListener('click', function () {
    var blob = new Blob([JSON.stringify(exportData(), null, 2)], { type: 'application/json' });
    var a = el('a'); a.href = URL.createObjectURL(blob); a.download = 'worldcup_2026.json';
    document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(a.href);
    toast('Đã tải worldcup_2026.json ⬇️');
  });

  document.getElementById('wcm-copy').addEventListener('click', function () {
    var text = JSON.stringify(exportData(), null, 2);
    var done = function () { toast('Đã sao chép JSON — dán cho Claude để đăng 📋'); };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, function () { fallbackCopy(text); done(); });
    else { fallbackCopy(text); done(); }
  });
  function fallbackCopy(text) {
    var ta = el('textarea'); ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
    document.body.appendChild(ta); ta.select(); try { document.execCommand('copy'); } catch (e) {} ta.remove();
  }

  document.getElementById('wcm-reload').addEventListener('click', function () {
    if (!confirm('Tải lại dữ liệu gốc đang chạy trên site? Mọi chỉnh sửa chưa xuất sẽ mất.')) return;
    state.data = clone(ORIGINAL); ensureShape();
    try { localStorage.removeItem(DRAFT_KEY); } catch (e) {}
    show('#wcm-restore', false);
    renderTabs(); renderEditor(); refreshOutputs(); toast('Đã nạp lại dữ liệu gốc ↺');
  });

  document.getElementById('wcm-restore').addEventListener('click', function () {
    var draft = null; try { draft = JSON.parse(localStorage.getItem(DRAFT_KEY)); } catch (e) {}
    if (draft) { state.data = draft; ensureShape(); renderTabs(); renderEditor(); refreshOutputs(); toast('Đã khôi phục nháp 📝'); }
  });

  /* ---------- Init ---------- */
  loadInitial();
  renderTabs(); renderEditor(); refreshOutputs();
  // offer restore if a draft differs from original
  try {
    var draftRaw = localStorage.getItem(DRAFT_KEY);
    if (draftRaw && draftRaw !== JSON.stringify(ORIGINAL)) show('#wcm-restore', true);
  } catch (e) {}
})();
