/* BHTN — Unemployment-insurance calculator
   Căn cứ: Luật Việc làm 2025 · Nghị định 293/2025/NĐ-CP
   100% client-side, không gửi dữ liệu lên server. */
(function () {
  "use strict";

  // 2026 regional minimum wages (đồng/tháng)
  var MIN_WAGE = { I: 5310000, II: 4730000, III: 4140000, IV: 3700000 };
  var RATE = 0.6;           // 60% bình quân lương 6 tháng cuối
  var CAP_X = 5;            // trần = 5 × lương tối thiểu vùng
  var MAX_MONTHS = 12;      // tối đa 12 tháng hưởng
  var MIN_QUALIFY = 12;     // đóng tối thiểu 12 tháng
  var BASE_MONTHS = 36;     // 36 tháng đầu → 3 tháng hưởng
  var BASE_BENEFIT = 3;
  var DEADLINE_MONTHS = 3;  // nộp hồ sơ trong 3 tháng

  var DOCS = [
    "Đơn đề nghị hưởng trợ cấp thất nghiệp (theo mẫu ban hành kèm nghị định).",
    "Bản chính hoặc bản sao có chứng thực giấy tờ chấm dứt HĐLĐ (quyết định thôi việc, HĐLĐ hết hạn, quyết định sa thải hợp pháp…).",
    "Sổ BHXH đã được chốt đến thời điểm nghỉ việc.",
    "Căn cước công dân (xuất trình khi nộp hồ sơ).",
    "Thông tin tài khoản ngân hàng để nhận trợ cấp (nếu nhận qua thẻ)."
  ];
  var STEPS = [
    "Yêu cầu công ty chốt sổ BHXH ngay sau khi nghỉ việc.",
    "Nộp hồ sơ tại Trung tâm Dịch vụ việc làm trong vòng 3 tháng kể từ ngày chấm dứt HĐLĐ.",
    "Sau khi có quyết định hưởng, thông báo tìm kiếm việc làm hằng tháng để tiếp tục nhận trợ cấp.",
    "Theo dõi chi trả (thường từ tháng thứ 2 sau khi nộp đủ hồ sơ hợp lệ)."
  ];

  var app = document.getElementById("bhtn-app");
  if (!app) return;

  var $ = function (id) { return document.getElementById(id); };
  var nf = new Intl.NumberFormat("vi-VN");
  var money = function (n) { return nf.format(Math.round(n || 0)) + " đ"; };

  /* ---- money input live formatting ---- */
  function parseMoney(s) { var d = (s || "").replace(/[^\d]/g, ""); return d ? parseInt(d, 10) : 0; }
  var moneyInputs = app.querySelectorAll(".bhtn__money");
  for (var i = 0; i < moneyInputs.length; i++) {
    moneyInputs[i].addEventListener("input", function () {
      var v = parseMoney(this.value);
      this.value = v ? nf.format(v) : "";
    });
  }

  /* ---- salary mode toggle ---- */
  var monthsBox = $("bhtn-salary-months");
  var avgBox = $("bhtn-salary-avg");
  function currentMode() {
    var r = app.querySelector('input[name="bhtn-salary-mode"]:checked');
    return r ? r.value : "months";
  }
  function syncMode() {
    var isMonths = currentMode() === "months";
    monthsBox.hidden = !isMonths;
    avgBox.hidden = isMonths;
  }
  var radios = app.querySelectorAll('input[name="bhtn-salary-mode"]');
  for (var j = 0; j < radios.length; j++) radios[j].addEventListener("change", syncMode);
  syncMode();

  /* ---- helpers ---- */
  function avgSalary() {
    if (currentMode() === "avg") return parseMoney($("bhtn-avg").value);
    var sum = 0, cnt = 0;
    for (var k = 1; k <= 6; k++) {
      var v = parseMoney($("bhtn-m" + k).value);
      if (v > 0) { sum += v; cnt++; }
    }
    return cnt ? sum / cnt : 0;
  }

  // Benefit months: 12–36 tháng → 3 tháng; sau 36, mỗi 12 tháng đủ → +1; tối đa 12; dư bảo lưu.
  function benefitMonths(total) {
    if (total < MIN_QUALIFY) return { months: 0, consumed: 0, leftover: Math.max(0, total) };
    var raw = BASE_BENEFIT;
    if (total > BASE_MONTHS) raw += Math.floor((total - BASE_MONTHS) / 12);
    var months = Math.min(raw, MAX_MONTHS);
    var consumed = (months >= MAX_MONTHS)
      ? BASE_MONTHS + (MAX_MONTHS - BASE_BENEFIT) * 12   // 144 tháng cho trần 12 tháng
      : BASE_MONTHS + (months - BASE_BENEFIT) * 12;
    return { months: months, consumed: consumed, leftover: Math.max(0, total - consumed) };
  }

  function parseDate(v) { if (!v) return null; var d = new Date(v + "T00:00:00"); return isNaN(d.getTime()) ? null : d; }
  function addMonths(d, m) { var x = new Date(d.getTime()); var day = x.getDate(); x.setMonth(x.getMonth() + m); if (x.getDate() < day) x.setDate(0); return x; }
  function dayDiff(a, b) { return Math.round((b - a) / 86400000); }
  function pad(n) { return (n < 10 ? "0" : "") + n; }
  function fmtDate(d) { return pad(d.getDate()) + "/" + pad(d.getMonth() + 1) + "/" + d.getFullYear(); }

  /* ---- core compute ---- */
  function compute() {
    var region = $("bhtn-region").value || "I";
    var minWage = MIN_WAGE[region];
    var cap = CAP_X * minWage;
    var avg = avgSalary();
    var rawBenefit = avg * RATE;
    var capped = rawBenefit > cap;
    var monthly = capped ? cap : rawBenefit;

    var totalMonths = parseInt($("bhtn-total-months").value, 10) || 0;
    var usedMonths = parseInt($("bhtn-used-months").value, 10) || 0;
    var bm = benefitMonths(totalMonths);
    var totalBenefit = monthly * bm.months;

    var legal = $("bhtn-legal").value;
    var employed = $("bhtn-employed").value;
    var pension = $("bhtn-pension").value;
    var endDate = parseDate($("bhtn-end-date").value);
    var submitDate = parseDate($("bhtn-submit-date").value);
    var today = new Date(); today.setHours(0, 0, 0, 0);

    var fails = [], reviews = [], oks = [], deadlineNote = "";

    if (legal === "no") fails.push("Hợp đồng lao động không chấm dứt hợp pháp (đơn phương trái luật, bị sa thải, kỷ luật buộc thôi việc…).");
    else oks.push("Hợp đồng/việc làm chấm dứt hợp pháp.");

    if (pension === "yes") fails.push("Đang hưởng lương hưu hoặc trợ cấp mất sức lao động hằng tháng — không thuộc diện hưởng BHTN.");
    else oks.push("Không hưởng lương hưu / trợ cấp mất sức lao động.");

    if (totalMonths < MIN_QUALIFY) fails.push("Chưa đóng đủ 12 tháng BHTN trong thời gian quy định (hiện khai báo " + totalMonths + " tháng).");
    else oks.push("Đã đóng đủ " + totalMonths + " tháng BHTN (≥ 12 tháng).");

    if (endDate) {
      var deadline = addMonths(endDate, DEADLINE_MONTHS);
      deadlineNote = "Hạn nộp hồ sơ: <strong>" + fmtDate(deadline) + "</strong> (trong 3 tháng kể từ ngày chấm dứt HĐLĐ).";
      if (submitDate) {
        if (submitDate > deadline) fails.push("Nộp hồ sơ ngày " + fmtDate(submitDate) + " — quá hạn 3 tháng (hạn chót " + fmtDate(deadline) + ").");
        else oks.push("Nộp hồ sơ trong hạn 3 tháng.");
      } else {
        var left = dayDiff(today, deadline);
        if (left < 0) fails.push("Đã quá hạn nộp hồ sơ (hạn chót " + fmtDate(deadline) + "). Liên hệ Trung tâm DVVL để được hướng dẫn.");
        else if (left <= 30) deadlineNote += " ⚠️ Chỉ còn <strong>" + left + " ngày</strong> — nên nộp sớm.";
      }
    } else {
      reviews.push("Chưa nhập ngày chấm dứt HĐLĐ — không kiểm tra được hạn nộp hồ sơ 3 tháng.");
    }

    if (employed === "yes") reviews.push("Hiện đang có việc làm / đã ký HĐLĐ mới — thường không đủ điều kiện, trừ một số ngoại lệ theo luật. Cần xác minh với cơ quan BHXH.");
    else oks.push("Hiện chưa có việc làm sau thời gian chờ.");

    var status = fails.length ? "not" : (reviews.length ? "review" : "eligible");

    return {
      region: region, cap: cap, avg: avg, rawBenefit: rawBenefit, capped: capped, monthly: monthly,
      totalMonths: totalMonths, usedMonths: usedMonths, bm: bm, totalBenefit: totalBenefit,
      fails: fails, reviews: reviews, oks: oks, status: status, deadlineNote: deadlineNote
    };
  }

  /* ---- AI-style explanation ---- */
  function explain(r) {
    var p = [];
    if (r.avg > 0) {
      p.push("Với lương bình quân 6 tháng cuối <strong>" + money(r.avg) + "</strong>, mức hưởng theo công thức 60% là <strong>" + money(r.rawBenefit) + "/tháng</strong>.");
      if (r.capped) p.push("Mức này vượt trần (5 × lương tối thiểu vùng " + r.region + " = " + money(r.cap) + ") nên bị khống chế còn <strong>" + money(r.monthly) + "/tháng</strong>.");
      else p.push("Mức này nằm dưới trần (5 × lương tối thiểu vùng " + r.region + " = " + money(r.cap) + ") nên được hưởng đủ <strong>" + money(r.monthly) + "/tháng</strong>.");
    }
    if (r.bm.months > 0) {
      p.push("Đóng " + r.totalMonths + " tháng BHTN → được hưởng <strong>" + r.bm.months + " tháng</strong> trợ cấp" +
        (r.bm.leftover > 0 ? ", còn <strong>" + r.bm.leftover + " tháng</strong> được bảo lưu cho lần hưởng sau." : "."));
      p.push("Tổng trợ cấp ước tính khoảng <strong>" + money(r.totalBenefit) + "</strong>.");
    } else {
      p.push("Số tháng đóng chưa đạt mốc 12 tháng nên chưa phát sinh tháng hưởng trợ cấp.");
    }
    if (r.usedMonths > 0) p.push("Bạn đã hưởng " + r.usedMonths + " tháng trước đó (chỉ tính trên số tháng đóng chưa hưởng).");
    if (r.status === "eligible") p.push("Theo thông tin khai báo, bạn <strong>đủ điều kiện</strong> nộp hồ sơ hưởng BHTN — nên hoàn tất hồ sơ và nộp đúng hạn.");
    else if (r.status === "review") p.push("Hồ sơ của bạn <strong>cần xem xét thêm</strong> ở một vài điểm trước khi kết luận chắc chắn.");
    else p.push("Theo thông tin khai báo, bạn <strong>chưa đủ điều kiện</strong> hưởng BHTN — xem lý do bên dưới.");
    return p.join(" ");
  }

  /* ---- render ---- */
  var MAP = {
    eligible: { cls: "eligible", icon: "✅", label: "Đủ điều kiện" },
    review:   { cls: "review",   icon: "⚠️", label: "Cần xem xét thêm" },
    not:      { cls: "not",      icon: "⛔", label: "Chưa đủ điều kiện" }
  };

  function li(items) { return items.map(function (x) { return "<li>" + x + "</li>"; }).join(""); }

  function render(r) {
    var box = $("bhtn-result");
    if (r.avg <= 0) {
      box.innerHTML = '<div class="bhtn__warn">Vui lòng nhập lương bình quân hoặc lương các tháng để tính mức hưởng.</div>';
      box.hidden = false;
      box.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }
    var s = MAP[r.status];
    var reasons = r.status === "not" ? r.fails : (r.status === "review" ? r.reviews : r.oks);
    var reasonTitle = r.status === "not" ? "Lý do chưa đủ điều kiện" : (r.status === "review" ? "Điểm cần xác minh" : "Điều kiện đã đạt");

    box.innerHTML =
      '<div class="bhtn__status bhtn__status--' + s.cls + '">' +
        '<span class="bhtn__status-icon" aria-hidden="true">' + s.icon + '</span>' +
        '<span class="bhtn__status-label">' + s.label + '</span>' +
      '</div>' +

      '<div class="bhtn__bignum-card">' +
        '<p class="bhtn__bignum-label">Mức hưởng hằng tháng</p>' +
        '<p class="bhtn__bignum">' + money(r.monthly) + '</p>' +
        '<p class="bhtn__bignum-note">' +
          (r.capped
            ? 'Đã áp trần 5 × lương tối thiểu vùng ' + r.region + ' (' + money(r.cap) + '). Mức 60% gốc: ' + money(r.rawBenefit) + '.'
            : 'Bằng 60% lương bình quân, dưới trần ' + money(r.cap) + ' (vùng ' + r.region + ').') +
        '</p>' +
      '</div>' +

      '<div class="bhtn__metrics">' +
        '<div class="bhtn__metric"><span class="bhtn__metric-label">Số tháng hưởng</span><span class="bhtn__metric-val">' + r.bm.months + ' tháng</span></div>' +
        '<div class="bhtn__metric"><span class="bhtn__metric-label">Tổng trợ cấp ước tính</span><span class="bhtn__metric-val">' + money(r.totalBenefit) + '</span></div>' +
        '<div class="bhtn__metric"><span class="bhtn__metric-label">Tháng bảo lưu</span><span class="bhtn__metric-val">' + r.bm.leftover + ' tháng</span></div>' +
        '<div class="bhtn__metric"><span class="bhtn__metric-label">Lương bình quân</span><span class="bhtn__metric-val">' + money(r.avg) + '</span></div>' +
      '</div>' +

      (r.deadlineNote ? '<div class="bhtn__warn">⏰ ' + r.deadlineNote + '</div>' : '') +

      '<div class="bhtn__explain">' +
        '<p class="bhtn__explain-tag">🤖 Giải thích</p>' +
        '<p class="bhtn__explain-body">' + explain(r) + '</p>' +
      '</div>' +

      '<div class="bhtn__reasons bhtn__reasons--' + s.cls + '">' +
        '<h3 class="bhtn__sub">' + reasonTitle + '</h3>' +
        '<ul>' + li(reasons) + '</ul>' +
      '</div>' +

      '<div class="bhtn__cols">' +
        '<div class="bhtn__col"><h3 class="bhtn__sub">📄 Hồ sơ cần chuẩn bị</h3><ul class="bhtn__checklist">' + li(DOCS) + '</ul></div>' +
        '<div class="bhtn__col"><h3 class="bhtn__sub">🧭 Bước tiếp theo</h3><ol class="bhtn__steps">' + li(STEPS) + '</ol></div>' +
      '</div>' +

      '<p class="bhtn__disclaimer">Kết quả chỉ mang tính tham khảo, cần đối chiếu cơ quan BHXH/Trung tâm dịch vụ việc làm.</p>';

    box.hidden = false;
    box.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  /* ---- events ---- */
  $("bhtn-form").addEventListener("submit", function (e) {
    e.preventDefault();
    render(compute());
  });
  $("bhtn-form").addEventListener("reset", function () {
    var box = $("bhtn-result");
    box.hidden = true;
    box.innerHTML = "";
    setTimeout(syncMode, 0);
  });
})();
