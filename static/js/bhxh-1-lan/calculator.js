/* ============================================================================
   BHXH 1 lần — Công cụ tính Bảo hiểm xã hội một lần 2026
   100% client-side, không phụ thuộc thư viện ngoài, không gửi dữ liệu đi đâu.

   Căn cứ:
   - Luật BHXH 2024 (Luật 41/2024/QH15), hiệu lực 01/07/2025 — Điều 70 (điều
     kiện & mức hưởng BHXH một lần).
   - Hệ số trượt giá 2026: Công văn 340/BHXH-CSXH ngày 03/02/2026.
   - Khoản 4 Điều 19 Thông tư 59/2015/TT-BLĐTBXH — quy tắc tháng lẻ + chuyển
     tháng lẻ trước 2014 sang giai đoạn từ 2014.

   Kết quả CHỈ MANG TÍNH THAM KHẢO. Số chính thức do cơ quan BHXH quyết định.
   ========================================================================== */
(function () {
  'use strict';

  var root = document.querySelector('[data-bhxh]');
  if (!root) return;

  /* ===== Hằng số pháp lý ===== */

  // Hệ số điều chỉnh tiền lương/thu nhập tháng đã đóng BHXH — năm 2026.
  // Dùng chung cho BHXH bắt buộc và tự nguyện (cùng hệ số CPI theo năm).
  // Cập nhật khi BHXH Việt Nam ban hành Công văn hệ số trượt giá năm sau.
  var HE_SO = {
    1995: 4.93, 1996: 4.66, 1997: 4.51, 1998: 4.19, 1999: 4.02, 2000: 4.09,
    2001: 4.10, 2002: 3.94, 2003: 3.82, 2004: 3.55, 2005: 3.27, 2006: 3.04,
    2007: 2.81, 2008: 2.29, 2009: 2.14, 2010: 1.96, 2011: 1.66, 2012: 1.52,
    2013: 1.42, 2014: 1.37, 2015: 1.36, 2016: 1.32, 2017: 1.27, 2018: 1.23,
    2019: 1.20, 2020: 1.16, 2021: 1.14, 2022: 1.10, 2023: 1.07, 2024: 1.03,
    2025: 1.00, 2026: 1.00
  };
  var PRE_1995 = 5.81; // hệ số áp cho mọi tháng trước năm 1995

  var TY_LE_DONG = 0.22;        // tỷ lệ đóng vào quỹ hưu trí & tử tuất
  var CHUAN_NGHEO_NT = 1500000; // chuẩn nghèo nông thôn (đ/tháng) — căn cứ hỗ trợ
  var HO_TRO_RATE = 0.10;       // hỗ trợ Nhà nước hộ thường = 10% (ước tính)

  var MIN_YEAR = 1990;
  var CUR_YEAR = new Date().getFullYear();
  var CUR_MONTH = new Date().getMonth() + 1;
  var MAX_YEAR = Math.max(CUR_YEAR, 2026);

  function heSo(year) {
    if (year <= 1994) return PRE_1995;
    return HE_SO[year] != null ? HE_SO[year] : 1.00;
  }

  /* ===== Helpers ===== */
  var MONTHS = ['Tháng 1', 'Tháng 2', 'Tháng 3', 'Tháng 4', 'Tháng 5', 'Tháng 6',
    'Tháng 7', 'Tháng 8', 'Tháng 9', 'Tháng 10', 'Tháng 11', 'Tháng 12'];

  var nf = new Intl.NumberFormat('vi-VN');
  function vnd(n) { return nf.format(Math.round(n || 0)) + ' đ'; }
  function el(tag, cls) { var e = document.createElement(tag); if (cls) e.className = cls; return e; }

  function fillSelect(sel, items, selected) {
    items.forEach(function (it) {
      var o = document.createElement('option');
      o.value = String(it.v);
      o.textContent = it.t;
      if (it.v === selected) o.selected = true;
      sel.appendChild(o);
    });
  }

  function monthOptions() {
    return MONTHS.map(function (t, i) { return { v: i + 1, t: t }; });
  }
  function yearOptions() {
    var arr = [];
    for (var y = MAX_YEAR; y >= MIN_YEAR; y--) arr.push({ v: y, t: String(y) });
    return arr;
  }

  /* ===== DOM refs ===== */
  var tabsEl = root.querySelector('[data-bhxh-tabs]');
  var periodsEl = root.querySelector('[data-bhxh-periods]');
  var addBtn = root.querySelector('[data-bhxh-add]');
  var calcBtn = root.querySelector('[data-bhxh-calc]');
  var resultEl = root.querySelector('[data-bhxh-result]');
  var formErr = root.querySelector('[data-bhxh-form-error]');

  var state = { mode: 'bat-buoc' }; // bat-buoc | tu-nguyen | ca-hai

  /* ===== Tabs ===== */
  function setMode(mode) {
    state.mode = mode;
    root.setAttribute('data-mode', mode);
    tabsEl.querySelectorAll('[data-bhxh-tab]').forEach(function (b) {
      var on = b.getAttribute('data-bhxh-tab') === mode;
      b.classList.toggle('is-active', on);
      b.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    // Khi không phải "Cả hai" → khoá loại đóng theo tab cho mọi dòng.
    periodsEl.querySelectorAll('[data-bhxh-type]').forEach(function (sel) {
      if (mode !== 'ca-hai') { sel.value = mode; }
      sel.disabled = (mode !== 'ca-hai');
    });
  }

  /* ===== Period rows ===== */
  function addPeriod(preset) {
    preset = preset || {};
    var row = el('div', 'bhxh-period');

    function field(label, build) {
      var wrap = el('label', 'bhxh-period__field');
      var span = el('span', 'bhxh-period__label'); span.textContent = label;
      wrap.appendChild(span);
      var control = build();
      wrap.appendChild(control);
      return { wrap: wrap, control: control };
    }

    var fromM = document.createElement('select');
    fillSelect(fromM, monthOptions(), preset.fromM || 1);
    var fromY = document.createElement('select');
    fillSelect(fromY, yearOptions(), preset.fromY || (CUR_YEAR - 5));

    var toM = document.createElement('select');
    fillSelect(toM, monthOptions(), preset.toM || CUR_MONTH);
    var toY = document.createElement('select');
    fillSelect(toY, yearOptions(), preset.toY || CUR_YEAR);

    var salary = document.createElement('input');
    salary.type = 'text';
    salary.inputMode = 'numeric';
    salary.placeholder = 'VD: 6.000.000';
    salary.className = 'bhxh-period__salary';
    if (preset.salary) salary.value = nf.format(preset.salary);

    var type = document.createElement('select');
    type.setAttribute('data-bhxh-type', '');
    fillSelect(type, [
      { v: 'bat-buoc', t: 'Bắt buộc' },
      { v: 'tu-nguyen', t: 'Tự nguyện' }
    ], state.mode === 'ca-hai' ? (preset.type || 'bat-buoc') : state.mode);
    type.disabled = (state.mode !== 'ca-hai');

    var f1 = field('Từ tháng', function () { return fromM; });
    var f2 = field('Năm', function () { return fromY; });
    var f3 = field('Đến tháng', function () { return toM; });
    var f4 = field('Năm', function () { return toY; });
    var f5 = field('Lương/thu nhập tháng', function () { return salary; });
    var f6 = field('Loại đóng', function () { return type; });
    f6.wrap.classList.add('bhxh-period__type');

    var del = el('button', 'bhxh-period__del');
    del.type = 'button';
    del.setAttribute('aria-label', 'Xoá giai đoạn');
    del.innerHTML = '&times;';
    del.addEventListener('click', function () {
      row.remove();
      if (!periodsEl.querySelector('.bhxh-period')) addPeriod();
    });

    // Định dạng nghìn khi gõ lương.
    salary.addEventListener('input', function () {
      var digits = salary.value.replace(/\D/g, '');
      salary.value = digits ? nf.format(parseInt(digits, 10)) : '';
    });

    [f1.wrap, f2.wrap, f3.wrap, f4.wrap, f5.wrap, f6.wrap].forEach(function (w) { row.appendChild(w); });
    row.appendChild(del);
    periodsEl.appendChild(row);
    return row;
  }

  function readPeriods() {
    var out = [];
    periodsEl.querySelectorAll('.bhxh-period').forEach(function (row) {
      var sels = row.querySelectorAll('select');
      var salaryInput = row.querySelector('.bhxh-period__salary');
      var typeSel = row.querySelector('[data-bhxh-type]');
      out.push({
        fromM: parseInt(sels[0].value, 10),
        fromY: parseInt(sels[1].value, 10),
        toM: parseInt(sels[2].value, 10),
        toY: parseInt(sels[3].value, 10),
        salary: parseInt((salaryInput.value || '').replace(/\D/g, ''), 10) || 0,
        type: typeSel ? typeSel.value : state.mode
      });
    });
    return out;
  }

  /* ===== Tính toán ===== */
  function eachMonth(p, cb) {
    var y = p.fromY, m = p.fromM;
    while (y < p.toY || (y === p.toY && m <= p.toM)) {
      cb(y, m);
      m++; if (m > 12) { m = 1; y++; }
    }
  }

  function validate(periods) {
    if (!periods.length) return 'Vui lòng thêm ít nhất một giai đoạn đóng BHXH.';
    for (var i = 0; i < periods.length; i++) {
      var p = periods[i];
      var start = p.fromY * 12 + p.fromM;
      var end = p.toY * 12 + p.toM;
      if (end < start) return 'Giai đoạn ' + (i + 1) + ': mốc "đến" phải sau hoặc bằng mốc "từ".';
      if (!p.salary || p.salary <= 0) return 'Giai đoạn ' + (i + 1) + ': vui lòng nhập mức lương/thu nhập tháng.';
    }
    return null;
  }

  function compute(periods) {
    var adjustedTotal = 0, totalMonths = 0, monthsBefore2014 = 0, monthsFrom2014 = 0, voluntaryMonths = 0;

    periods.forEach(function (p) {
      eachMonth(p, function (y) {
        var coef = heSo(y);
        adjustedTotal += p.salary * coef;
        totalMonths += 1;
        if (y < 2014) monthsBefore2014 += 1; else monthsFrom2014 += 1;
        if (p.type === 'tu-nguyen') voluntaryMonths += 1;
      });
    });

    var mbqtl = totalMonths ? adjustedTotal / totalMonths : 0;

    // Quy tắc tháng lẻ: tháng lẻ trước 2014 chuyển sang giai đoạn từ 2014.
    var yearsBefore = Math.floor(monthsBefore2014 / 12);
    var oddBefore = monthsBefore2014 % 12;
    var fromBucket = monthsFrom2014 + oddBefore;
    var yearsFromWhole = Math.floor(fromBucket / 12);
    var oddFrom = fromBucket % 12;
    var oddFactor = oddFrom === 0 ? 0 : (oddFrom <= 6 ? 0.5 : 1);
    var yearsFrom = yearsFromWhole + oddFactor;

    var preAmount = 1.5 * mbqtl * yearsBefore;
    var fromAmount = 2 * mbqtl * yearsFrom;
    var gross = preAmount + fromAmount;
    var isShort = totalMonths < 12;

    if (isShort) {
      // < 12 tháng: 22% tổng lương đã đóng (đã điều chỉnh), tối đa 2 tháng MBQTL.
      var benefit = TY_LE_DONG * adjustedTotal;
      var cap = 2 * mbqtl;
      gross = Math.min(benefit, cap);
      preAmount = 0;
      fromAmount = gross;
    }

    return {
      adjustedTotal: adjustedTotal,
      totalMonths: totalMonths,
      totalYears: totalMonths / 12,
      mbqtl: mbqtl,
      yearsBefore: yearsBefore,
      yearsFrom: yearsFrom,
      preAmount: preAmount,
      fromAmount: fromAmount,
      gross: gross,
      isShort: isShort,
      voluntaryMonths: voluntaryMonths
    };
  }

  /* ===== Điều kiện hưởng ===== */
  function chk(name) { var e = root.querySelector('[data-elig="' + name + '"]'); return !!(e && e.checked); }

  function evaluateEligibility(calc) {
    var startedBefore = (root.querySelector('[name="bhxh-start"]:checked') || {}).value !== 'after';
    var stopped12 = chk('stopped12');
    var retire = chk('retire');
    var abroad = chk('abroad');
    var disease = chk('disease');
    var disability81 = chk('disability81');
    var disabilitySevere = chk('disabilitySevere');
    var wants = chk('wants');

    var special = abroad || disease || disability81 || disabilitySevere;
    var years = calc.totalYears;

    // Đủ tuổi hưu + đủ năm đóng → nên hưởng lương hưu.
    if (retire && years >= 15 && !special) {
      return {
        status: 'review',
        title: 'Cần cân nhắc — nên hưởng lương hưu',
        msg: 'Bạn đã đủ tuổi nghỉ hưu và có từ 15 năm đóng BHXH trở lên nên đủ điều kiện hưởng <strong>lương hưu hằng tháng</strong>. Theo Luật BHXH 2024, trường hợp này thường không được giải quyết rút một lần (trừ khi ra nước ngoài định cư hoặc mắc bệnh hiểm nghèo). Lương hưu hằng tháng kèm bảo hiểm y tế gần như luôn có lợi hơn rút một lần.'
      };
    }

    if (!wants) {
      return {
        status: 'review',
        title: 'Chưa có nhu cầu rút',
        msg: 'Bạn chưa chọn "muốn nhận BHXH một lần". Nếu tiếp tục bảo lưu thời gian đã đóng, bạn vẫn giữ cơ hội nhận lương hưu sau này. Tích chọn ô đó nếu muốn xem điều kiện rút một lần.'
      };
    }

    if (special) {
      var reasons = [];
      if (abroad) reasons.push('ra nước ngoài để định cư');
      if (disease) reasons.push('mắc bệnh hiểm nghèo (ung thư, bại liệt, xơ gan mất bù, lao nặng, AIDS…)');
      if (disability81) reasons.push('suy giảm khả năng lao động từ 81% trở lên');
      if (disabilitySevere) reasons.push('người khuyết tật đặc biệt nặng');
      return {
        status: 'eligible',
        title: 'Đủ điều kiện — trường hợp đặc biệt',
        msg: 'Bạn thuộc trường hợp đặc biệt: ' + reasons.join('; ') + '. Theo Điều 70 Luật BHXH 2024, các trường hợp này được hưởng BHXH một lần bất kể tham gia trước hay sau 01/07/2025, và (với bệnh hiểm nghèo / định cư nước ngoài) không bị trừ phần Nhà nước hỗ trợ.'
      };
    }

    if (retire && years < 15) {
      return {
        status: 'eligible',
        title: 'Đủ điều kiện — đủ tuổi hưu nhưng dưới 15 năm đóng',
        msg: 'Bạn đã đủ tuổi nghỉ hưu nhưng chưa đủ 15 năm đóng BHXH và không tiếp tục đóng tự nguyện. Theo Luật BHXH 2024, bạn được rút BHXH một lần. Tuy nhiên, đóng thêm cho đủ 15 năm để hưởng lương hưu thường có lợi hơn.'
      };
    }

    // Tuyến chung (giữ quyền cho người tham gia trước 01/07/2025).
    if (startedBefore) {
      if (!stopped12) {
        return {
          status: 'review',
          title: 'Cần chờ đủ 12 tháng ngừng đóng',
          msg: 'Bạn tham gia BHXH trước 01/07/2025 nên vẫn giữ quyền rút một lần theo tuyến chung. Điều kiện: sau <strong>12 tháng</strong> không thuộc diện đóng BHXH bắt buộc và cũng không đóng tự nguyện. Hiện bạn chưa đủ mốc 12 tháng này.'
        };
      }
      if (years >= 20) {
        return {
          status: 'review',
          title: 'Cần cân nhắc — đã đóng từ 20 năm trở lên',
          msg: 'Bạn đã có từ 20 năm đóng BHXH. Tuyến rút một lần thông thường áp dụng cho trường hợp <strong>chưa đủ 20 năm</strong>. Với thời gian đóng dài như vậy, nên bảo lưu/đóng tiếp để hưởng lương hưu thay vì rút một lần. Hãy liên hệ cơ quan BHXH để được tư vấn chính xác.'
        };
      }
      return {
        status: 'eligible',
        title: 'Đủ điều kiện — tuyến chung (tham gia trước 01/07/2025)',
        msg: 'Bạn tham gia BHXH trước 01/07/2025, đã ngừng đóng từ 12 tháng trở lên và có dưới 20 năm đóng. Theo điều khoản chuyển tiếp của Luật BHXH 2024, bạn đủ điều kiện hưởng BHXH một lần. Cân nhắc kỹ vì rút một lần sẽ mất cơ hội nhận lương hưu.'
      };
    }

    // Tham gia từ 01/07/2025 trở đi, không thuộc trường hợp đặc biệt.
    return {
      status: 'not_eligible',
      title: 'Chưa đủ điều kiện rút một lần',
      msg: 'Bạn bắt đầu tham gia BHXH từ 01/07/2025 trở đi. Theo Luật BHXH 2024, nhóm này <strong>không còn được rút một lần</strong> chỉ vì nghỉ việc 12 tháng. Chỉ được rút khi: đủ tuổi nghỉ hưu mà chưa đủ 15 năm đóng, ra nước ngoài định cư, mắc bệnh hiểm nghèo, hoặc suy giảm khả năng lao động ≥81% / khuyết tật đặc biệt nặng.'
    };
  }

  /* ===== Render kết quả ===== */
  function badge(status) {
    if (status === 'eligible') return { cls: 'is-eligible', icon: '✓', label: 'Đủ điều kiện' };
    if (status === 'not_eligible') return { cls: 'is-not-eligible', icon: '✕', label: 'Chưa đủ điều kiện' };
    return { cls: 'is-review', icon: '!', label: 'Cần xem xét thêm' };
  }

  function checklist(elig) {
    var common = [
      'Sổ BHXH (hoặc thông tin số định danh cá nhân nếu đã liên thông VssID).',
      'Đơn đề nghị hưởng BHXH một lần (Mẫu 14-HSB).',
      'Căn cước công dân / hộ chiếu còn hiệu lực.'
    ];
    if (chk('abroad')) common.push('Bản sao giấy xác nhận của cơ quan có thẩm quyền về việc thôi quốc tịch / hộ chiếu nước ngoài / thị thực định cư.');
    if (chk('disease')) common.push('Trích sao/tóm tắt hồ sơ bệnh án thể hiện đang mắc bệnh hiểm nghèo.');
    if (chk('disability81') || chk('disabilitySevere')) common.push('Biên bản giám định mức suy giảm khả năng lao động của Hội đồng giám định y khoa.');
    common.push('Số tài khoản ngân hàng chính chủ để nhận tiền (nếu nhận qua chuyển khoản).');
    return common;
  }

  function render(calc, elig) {
    var b = badge(elig.status);
    var voluntaryNote = '';
    var stateSupport = 0;
    var net = calc.gross;

    // Trừ hỗ trợ Nhà nước cho phần tự nguyện (trừ trường hợp đặc biệt được miễn trừ).
    var exemptDeduct = chk('abroad') || chk('disease');
    if (calc.voluntaryMonths > 0 && !exemptDeduct) {
      stateSupport = calc.voluntaryMonths * TY_LE_DONG * HO_TRO_RATE * CHUAN_NGHEO_NT;
      net = Math.max(0, calc.gross - stateSupport);
    }

    var yearsLabel = calc.totalMonths + ' tháng (≈ ' + (Math.round(calc.totalYears * 100) / 100) + ' năm)';

    var html = '';

    html += '<div class="bhxh-result__headline">';
    html += '<p class="bhxh-result__eyebrow">Số tiền BHXH một lần ước tính</p>';
    html += '<p class="bhxh-result__amount">' + vnd(net) + '</p>';
    if (stateSupport > 0) {
      html += '<p class="bhxh-result__sub">Đã trừ ước tính ' + vnd(stateSupport) + ' tiền Nhà nước hỗ trợ đóng BHXH tự nguyện.</p>';
    }
    html += '</div>';

    // KPI breakdown
    html += '<div class="bhxh-breakdown">';
    html += kpi('Bình quân tiền lương (MBQTL)', vnd(calc.mbqtl), 'đã nhân hệ số trượt giá 2026');
    html += kpi('Tổng thời gian đóng', yearsLabel, calc.isShort ? 'dưới 12 tháng — áp dụng cách tính riêng' : 'đã làm tròn tháng lẻ');
    html += kpi('Phần trước 2014', vnd(calc.preAmount), '1,5 × MBQTL × ' + calc.yearsBefore + ' năm');
    html += kpi('Phần từ 2014', vnd(calc.fromAmount), (calc.isShort ? '22% lương đã đóng (tối đa 2 tháng MBQTL)' : '2 × MBQTL × ' + calc.yearsFrom + ' năm'));
    if (stateSupport > 0) html += kpi('Trừ hỗ trợ Nhà nước', '− ' + vnd(stateSupport), 'phần tự nguyện (ước tính, hộ thường)');
    html += '</div>';

    // Eligibility
    html += '<div class="bhxh-elig ' + b.cls + '">';
    html += '<div class="bhxh-elig__badge"><span class="bhxh-elig__icon">' + b.icon + '</span>' + b.label + '</div>';
    html += '<h3 class="bhxh-elig__title">' + elig.title + '</h3>';
    html += '<p class="bhxh-elig__msg">' + elig.msg + '</p>';
    html += '</div>';

    // Documents
    var docs = checklist(elig);
    html += '<div class="bhxh-card bhxh-docs"><h3 class="bhxh-subhead">📋 Hồ sơ cần chuẩn bị</h3><ul class="bhxh-checklist">';
    docs.forEach(function (d) { html += '<li>' + d + '</li>'; });
    html += '</ul></div>';

    // Pension loss warning
    html += '<div class="bhxh-warning"><span class="bhxh-warning__icon" aria-hidden="true">⚠️</span><div>';
    html += '<strong>Cảnh báo mất lương hưu.</strong> Khi rút BHXH một lần, bạn xoá toàn bộ thời gian đã đóng và mất cơ hội nhận <strong>lương hưu hằng tháng</strong> cùng <strong>bảo hiểm y tế miễn phí</strong> khi về già, trợ cấp mai táng và tử tuất. Số tiền rút một lần thường thấp hơn nhiều so với tổng quyền lợi hưu trí dài hạn. Hãy cân nhắc bảo lưu hoặc đóng tiếp trước khi quyết định.';
    html += '</div></div>';

    // Disclaimer
    html += '<p class="bhxh-disclaimer">Kết quả chỉ mang tính <strong>tham khảo</strong>, dựa trên hệ số trượt giá 2026 (Công văn 340/BHXH-CSXH ngày 03/02/2026) và quy định Luật BHXH 2024. Phần hỗ trợ Nhà nước cho BHXH tự nguyện là ước tính (chuẩn nghèo nông thôn, hộ thường 10%). Số tiền và điều kiện chính thức do cơ quan Bảo hiểm xã hội nơi bạn nộp hồ sơ quyết định.</p>';

    resultEl.innerHTML = html;
    resultEl.hidden = false;
    resultEl.setAttribute('tabindex', '-1');
    resultEl.focus({ preventScroll: false });
    resultEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function kpi(label, value, note) {
    return '<div class="bhxh-kpi"><span class="bhxh-kpi__label">' + label + '</span>' +
      '<span class="bhxh-kpi__value">' + value + '</span>' +
      (note ? '<span class="bhxh-kpi__note">' + note + '</span>' : '') + '</div>';
  }

  /* ===== Wire up ===== */
  tabsEl.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-bhxh-tab]');
    if (btn) setMode(btn.getAttribute('data-bhxh-tab'));
  });

  addBtn.addEventListener('click', function () { addPeriod(); setMode(state.mode); });

  calcBtn.addEventListener('click', function () {
    var periods = readPeriods();
    var err = validate(periods);
    if (err) {
      formErr.textContent = err;
      formErr.hidden = false;
      formErr.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }
    formErr.hidden = true;
    var calc = compute(periods);
    var elig = evaluateEligibility(calc);
    render(calc, elig);
  });

  // Khởi tạo: 1 giai đoạn mẫu.
  addPeriod({ fromM: 1, fromY: CUR_YEAR - 5, toM: CUR_MONTH, toY: CUR_YEAR, salary: 6000000 });
  setMode('bat-buoc');
})();
