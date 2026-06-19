/**
 * H-Dashboard V2 — Coffee Life Analytics UI renderer (S-DNA).
 */
(function (global) {
  "use strict";

  const ICONS = {
    visits: "○",
    week: "◇",
    month: "□",
    year: "△",
    bill: "◈",
    store: "◎",
    drink: "☕",
    streak: "⚡",
    order: "◆",
    item: "▣",
    morning: "☀",
    weekend: "◇",
    night: "☾",
  };

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function fmt(n) {
    return global.HDashboardCoffee ? global.HDashboardCoffee.formatVnd(n) : String(n);
  }

  function kpiCard(label, value, unit, icon, accent) {
    const cls = accent ? ` hd-kpi--${accent}` : "";
    return `<article class="hd-kpi${cls}">
      <span class="hd-kpi__icon" aria-hidden="true">${icon}</span>
      <span class="hd-kpi__label">${esc(label)}</span>
      <span class="hd-kpi__value">${esc(value)}</span>
      ${unit ? `<span class="hd-kpi__unit">${esc(unit)}</span>` : ""}
    </article>`;
  }

  function renderDna(dna, el) {
    if (!el) return;
    if (!dna || !dna.totalVisits) {
      el.innerHTML = '<p class="hd-empty">Upload hóa đơn Highlands để xem Coffee DNA.</p>';
      return;
    }
    el.innerHTML = `<div class="hd-kpi-grid">
      ${kpiCard("Tổng lần ghé", dna.totalVisits, "visits", ICONS.visits, "teal")}
      ${kpiCard("Tuần này", dna.thisWeek, "", ICONS.week, "blue")}
      ${kpiCard("Tháng này", dna.thisMonth, "", ICONS.month, "purple")}
      ${kpiCard("Năm nay", dna.thisYear, "", ICONS.year, "teal")}
      ${kpiCard("Hóa đơn TB", fmt(dna.avgBill).replace(" ₫", ""), "₫", ICONS.bill)}
      ${kpiCard("Cửa hàng yêu thích", esc(dna.favoriteStore), `${dna.favoriteStoreVisits} lần`, ICONS.store)}
      ${kpiCard("Đồ uống yêu thích", esc(dna.favoriteDrink), `${dna.favoriteDrinkCount} lần`, ICONS.drink)}
      ${kpiCard("Chuỗi dài nhất", dna.longestStreak, "ngày liên tiếp", ICONS.streak)}
      ${kpiCard("Đơn đắt nhất", fmt(dna.mostExpensiveOrder.total).replace(" ₫", ""), "₫", ICONS.order)}
      ${kpiCard("Món gọi nhiều", esc(dna.favoriteDrink), "", ICONS.item)}
      ${kpiCard("Buổi sáng", `${dna.morningRatio}%`, "tỷ lệ", ICONS.morning)}
      ${kpiCard("Ngày thường", `${dna.weekdayRatio}%`, "vs cuối tuần", ICONS.weekend)}
      ${kpiCard("Khuya", `${dna.lateNightRatio}%`, "sau 22h", ICONS.night)}
    </div>`;
  }

  function renderExecutiveSummary(text, el) {
    if (!el) return;
    el.innerHTML = text
      ? `<div class="hd-exec"><p class="hd-exec__text">${esc(text)}</p></div>`
      : '<p class="hd-empty">Upload hóa đơn để nhận Coffee Executive Summary.</p>';
  }

  function renderDrinks(drinks, el) {
    if (!el || !drinks?.topDrinks?.length) {
      if (el) el.innerHTML = '<p class="hd-empty">Chưa có dữ liệu đồ uống.</p>';
      return;
    }
    const max = drinks.topDrinks[0].count || 1;
    const rows = drinks.topDrinks.slice(0, 12).map((d) => {
      const w = Math.max(6, Math.round((d.count / max) * 100));
      return `<li class="hd-drink-row">
        <span class="hd-drink-row__name">${esc(d.name)}</span>
        <span class="hd-drink-row__bar"><span style="width:${w}%"></span></span>
        <span class="hd-drink-row__meta">
          <strong>${d.count}</strong> lần · ${fmt(d.spend)} · TB ${fmt(d.avgPrice)}
          <em>${d.firstDate} → ${d.lastDate} · ${esc(d.favoriteTime)}</em>
        </span>
      </li>`;
    }).join("");

    const cats = (drinks.topCategories || []).map((c) =>
      `<span class="hd-chip hd-chip--teal">${esc(c.category)} <strong>${c.count}</strong></span>`
    ).join("");

    el.innerHTML = `
      <p class="hd-signature">My signature drink is <strong>${esc(drinks.signature)}</strong></p>
      <div class="hd-chips">${cats}</div>
      <ul class="hd-drink-list">${rows}</ul>`;
  }

  function renderHeatmap(clock, el) {
    if (!el || !clock?.grid) {
      if (el) el.innerHTML = '<p class="hd-empty">Chưa có dữ liệu Coffee Clock.</p>';
      return;
    }

    const hourHeader = Array.from({ length: 24 }, (_, h) =>
      h % 3 === 0 ? `<span>${String(h).padStart(2, "0")}</span>` : "<span></span>"
    ).join("");

    const rows = clock.grid.map((row, dow) => {
      const cells = row.map((val, h) => {
        const level = val === 0 ? 0 : Math.min(4, Math.ceil((val / clock.max) * 4));
        return `<div class="hd-heat__cell hd-heat__cell--${level}" title="${clock.dayNames[dow]} ${h}:00 — ${val} lần"></div>`;
      }).join("");
      return `<div class="hd-heat__row"><span class="hd-heat__dow">${clock.dayNames[dow]}</span>${cells}</div>`;
    }).join("");

    el.innerHTML = `
      <div class="hd-heat">
        <div class="hd-heat__header"><span class="hd-heat__dow"></span>${hourHeader}</div>
        <div class="hd-heat__body">${rows}</div>
        <div class="hd-heat__legend">
          <span>Ít</span><span class="hd-heat__cell hd-heat__cell--1"></span><span class="hd-heat__cell hd-heat__cell--2"></span><span class="hd-heat__cell hd-heat__cell--3"></span><span class="hd-heat__cell hd-heat__cell--4"></span><span>Nhiều</span>
        </div>
      </div>`;
  }

  function renderSeasonality(seasonality, el) {
    if (!el || !seasonality) {
      if (el) el.innerHTML = '<p class="hd-empty">Chưa có dữ liệu mùa.</p>';
      return;
    }
    const blocks = ["dry", "hot", "rainy"].map((sid) => {
      const s = seasonality.seasons[sid === "dry" ? "dry" : sid === "hot" ? "hot" : "rainy"];
      const pref = seasonality.prefs[sid];
      const spend = seasonality.seasonSpend[sid] || 0;
      const visits = seasonality.seasonVisits[sid] || 0;
      const cats = Object.entries(seasonality.bySeason[sid] || {})
        .sort((a, b) => b[1] - a[1])
        .slice(0, 4)
        .map(([cat, n]) => `<li>${esc(cat)} — ${n}</li>`)
        .join("");
      return `<article class="hd-season-card hd-season-card--${sid}">
        <h4>${esc(s.label)}</h4>
        <p class="hd-season-card__pref">${pref ? `Ưa thích: <strong>${esc(pref.category)}</strong>` : "—"}</p>
        <p class="hd-season-card__stats">${visits} lần ghé · ${fmt(spend)}</p>
        <ul>${cats || "<li>—</li>"}</ul>
      </article>`;
    }).join("");

    el.innerHTML = `<div class="hd-season-grid">${blocks}</div>`;
  }

  function renderPersonality(traits, el) {
    if (!el) return;
    if (!traits?.length) {
      el.innerHTML = '<p class="hd-empty">Chưa đủ dữ liệu để tạo Coffee Personality.</p>';
      return;
    }
    el.innerHTML = traits.map((t) =>
      `<article class="hd-personality-card"><p>${esc(t)}</p></article>`
    ).join("");
  }

  function renderMonthlyReports(reports, el) {
    if (!el) return;
    if (!reports?.length) {
      el.innerHTML = '<p class="hd-empty">Chưa có báo cáo tháng.</p>';
      return;
    }
    el.innerHTML = reports.map((r) => `
      <article class="hd-month-card">
        <header><span class="hd-month-card__num">${esc(r.monthLabel)}</span><span class="hd-month-card__year">${r.month.slice(0, 4)}</span></header>
        <div class="hd-month-card__grid">
          <div><span>Lần ghé</span><strong>${r.visits}</strong></div>
          <div><span>Chi tiêu</span><strong>${fmt(r.spend)}</strong></div>
          <div><span>Cửa hàng</span><strong>${esc(r.favoriteStore)}</strong></div>
          <div><span>Đồ uống</span><strong>${esc(r.favoriteDrink)}</strong></div>
          <div><span>Giờ cao điểm</span><strong>${esc(r.peakTime)}</strong></div>
        </div>
      </article>`).join("");
  }

  function renderAnnualReport(report, el) {
    if (!el) return;
    if (!report) {
      el.innerHTML = '<p class="hd-empty">Chưa có Annual Report.</p>';
      return;
    }
    const highlights = (report.highlights || []).map((h) =>
      `<div class="hd-annual-kpi"><span>${esc(h.label)}</span><strong>${esc(String(h.value))}</strong></div>`
    ).join("");
    const drinks = (report.favoriteDrinks || []).map((d) =>
      `<li>${esc(d.name)} — ${d.count} lần</li>`
    ).join("");

    el.innerHTML = `
      <div class="hd-annual">
        <section class="hd-annual__exec"><h4>Executive Summary</h4><p>${esc(report.executiveSummary)}</p></section>
        <section class="hd-annual__highlights"><h4>${report.year} Highlights</h4><div class="hd-annual-kpi-row">${highlights}</div></section>
        <section class="hd-annual__drinks"><h4>Favorite Drinks</h4><ul>${drinks || "<li>—</li>"}</ul></section>
        <section class="hd-annual__store"><h4>Favorite Store</h4><p>${esc(report.favoriteStores)}</p></section>
      </div>`;
  }

  function renderFunInsights(insights, el) {
    if (!el) return;
    if (!insights?.length) {
      el.innerHTML = "<li>Upload hóa đơn để nhận fun insights.</li>";
      return;
    }
    el.innerHTML = insights.map((t) => `<li>${esc(t)}</li>`).join("");
  }

  function renderDiscoveries(discoveries, el) {
    if (!el) return;
    if (!discoveries?.length) {
      el.innerHTML = '<p class="hd-empty">Chưa phát hiện thay đổi thói quen.</p>';
      return;
    }
    el.innerHTML = discoveries.map((d) =>
      `<article class="hd-discovery hd-discovery--${esc(d.type)}"><p>${esc(d.text)}</p></article>`
    ).join("");
  }

  function renderJourney(milestones, el) {
    if (!el) return;
    if (!milestones?.length) {
      el.innerHTML = '<p class="hd-empty">Coffee Journey sẽ hiện sau khi có dữ liệu.</p>';
      return;
    }
    el.innerHTML = `<div class="hd-journey">${milestones.map((m) => `
      <article class="hd-journey__mile">
        <span class="hd-journey__n">${m.n}</span>
        <div><strong>${esc(m.label)}</strong><em>${esc(m.date)} · ${esc(m.detail)}</em></div>
      </article>`).join("")}</div>`;
  }

  function renderInsightsList(insights, el) {
    if (!el) return;
    if (!insights?.length) {
      el.innerHTML = "<li>Upload hóa đơn Highlands để nhận AI insights.</li>";
      return;
    }
    el.innerHTML = insights.map((t) => `<li>${esc(t)}</li>`).join("");
  }

  function renderAll(payload) {
    const p = payload || {};
    renderExecutiveSummary(p.executiveSummary, document.getElementById("hd-exec-summary"));
    renderDna(p.dna, document.getElementById("hd-coffee-dna"));
    renderDrinks(p.drinks, document.getElementById("hd-favorite-drinks"));
    renderHeatmap(p.clock, document.getElementById("hd-coffee-clock"));
    renderSeasonality(p.seasonality, document.getElementById("hd-seasonality"));
    renderPersonality(p.personality, document.getElementById("hd-personality"));
    renderMonthlyReports(p.monthlyReports, document.getElementById("hd-monthly-reports"));
    renderAnnualReport(p.annualReport, document.getElementById("hd-annual-report"));
    renderFunInsights(p.funInsights, document.getElementById("hd-fun-insights"));
    renderDiscoveries(p.discoveries, document.getElementById("hd-discoveries"));
    renderJourney(p.journey, document.getElementById("hd-journey"));
    renderInsightsList(p.narrativeInsights, document.getElementById("hd-insights-list"));
  }

  global.HDashboardCoffeeUI = { renderAll, renderDna, renderExecutiveSummary };
})(typeof window !== "undefined" ? window : globalThis);