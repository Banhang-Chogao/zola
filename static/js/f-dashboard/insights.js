/**
 * Financial insights — mirrors scripts/f_dashboard_insights.py
 */
(function (global) {
  "use strict";

  const EXPENSE_CATEGORIES = [
    ["Ăn uống", ["an uong", "food", "cafe", "starbucks", "grab food", "shopeefood", "lotteria", "kfc", "pizza", "com ", "bun ", "pho ", "highlands", "the coffee"]],
    ["Chuyển tiền", ["chuyen tien", "chuyen khoan", "qr -", "ck "]],
    ["Mua sắm", ["shopee", "lazada", "tiki", "amazon", "sendo"]],
    ["Di chuyển", ["grab", "be group", "gojek", "xang", "petrol", "shell", "vinfast"]],
    ["Giải trí", ["netflix", "spotify", "game", "cgv", "youtube", "apple.com"]],
    ["Hóa đơn", ["dien ", "nuoc ", "internet", "fpt", "viettel", "mobifone"]],
  ];

  const HEALTH_LABELS = [
    [85, "Excellent"],
    [70, "Good"],
    [50, "Average"],
    [30, "Risky"],
    [0, "Danger"],
  ];

  const HEALTH_LEVELS = [
    { min: 85, label: "Excellent", range: "≥ 85", desc: "Tích lũy mạnh, chi tiêu kiểm soát, dòng tiền dương ổn định." },
    { min: 70, label: "Good", range: "70 – 84", desc: "Cân bằng tốt — tiết kiệm đủ, chi tiêu hợp lý so với thu nhập." },
    { min: 50, label: "Average", range: "50 – 69", desc: "Trung bình — cần theo dõi chi tiêu, tỷ lệ chi/thu còn cao." },
    { min: 30, label: "Risky", range: "30 – 49", desc: "Rủi ro — chi gần hoặc vượt thu, ít dư tiền mặt." },
    { min: 0, label: "Danger", range: "< 30", desc: "Nguy hiểm — thâm hụt kéo dài, cần cắt giảm chi ngay." },
  ];

  function normDesc(text) {
    return String(text).toLowerCase().trim().replace(/\s+/g, " ");
  }

  function categorizeExpense(description) {
    const norm = normDesc(description);
    for (const [label, keywords] of EXPENSE_CATEGORIES) {
      if (keywords.some((kw) => norm.includes(kw))) return label;
    }
    return "Khác";
  }

  function computeSummary(transactions) {
    let income = 0;
    let expense = 0;
    transactions.forEach((t) => {
      if (t.amount > 0) income += t.amount;
      else expense += Math.abs(t.amount);
    });

    const dates = transactions.map((t) => t.date).sort();
    return {
      total_income: income,
      total_expense: expense,
      net_cash_flow: income - expense,
      transaction_count: transactions.length,
      date_from: dates[0] ? dates[0].slice(0, 10) : "",
      date_to: dates.length ? dates[dates.length - 1].slice(0, 10) : "",
    };
  }

  function financialHealth(summary) {
    const income = summary.total_income;
    const expense = summary.total_expense;
    const net = summary.net_cash_flow;

    const savingRate = income > 0 ? net / income : 0;
    const expenseRatio = income > 0 ? expense / income : 1;

    let score = 0;
    if (income > 0) {
      score += Math.min(45, Math.max(0, savingRate * 100 * 0.9));
      score += Math.max(0, 25 - expenseRatio * 25);
    }
    if (net > 0) score += 15;
    else if (net < 0) score -= 10;
    if (summary.transaction_count >= 10) score += 5;
    if (summary.date_from && summary.date_to) {
      const from = new Date(summary.date_from);
      const to = new Date(summary.date_to);
      if ((to - from) / 86400000 >= 60) score += 10;
    }

    score = Math.max(0, Math.min(100, Math.round(score * 10) / 10));
    let label = "Danger";
    for (const [threshold, name] of HEALTH_LABELS) {
      if (score >= threshold) {
        label = name;
        break;
      }
    }

    return {
      saving_rate: Math.round(savingRate * 10000) / 10000,
      expense_ratio: Math.round(expenseRatio * 10000) / 10000,
      net_cash_flow: net,
      financial_score: score,
      health_label: label,
    };
  }

  function monthKey(dateStr) {
    return dateStr.slice(0, 7);
  }

  // --- helpers shared by the new analytics layer ---------------------------
  function safeNum(n) {
    const v = Number(n);
    return Number.isFinite(v) ? v : 0;
  }

  function dayMonth(dateStr) {
    // ISO 'YYYY-MM-DDTHH:MM:SS' -> 'DD/MM' (display, never machine readable).
    const s = String(dateStr || "");
    const d = s.slice(8, 10);
    const m = s.slice(5, 7);
    if (d && m) return `${d}/${m}`;
    return s.slice(0, 10);
  }

  function shortLabel(text, max = 28) {
    const s = String(text == null ? "" : text).replace(/\s+/g, " ").trim();
    if (s.length <= max) return s;
    return s.slice(0, max - 1).trimEnd() + "…";
  }

  function rollingAverage(values, window) {
    // Aligned trailing rolling mean: out[i] = mean(values[max(0,i-w+1)..i]).
    const out = [];
    let sum = 0;
    for (let i = 0; i < values.length; i += 1) {
      sum += values[i];
      if (i >= window) sum -= values[i - window];
      const span = Math.min(i + 1, window);
      out.push(span > 0 ? Math.round(sum / span) : 0);
    }
    return out;
  }

  function chartDatasets(transactions, health) {
    const txns = Array.isArray(transactions) ? transactions : [];
    let income = 0;
    let expense = 0;
    txns.forEach((t) => {
      const amt = safeNum(t.amount);
      if (amt > 0) income += amt;
      else expense += Math.abs(amt);
    });

    // --- balanceTimeline: running balance per txn, sorted by date asc ------
    const byDate = txns
      .slice()
      .sort((a, b) => String(a.date).localeCompare(String(b.date)));
    const balanceLabels = byDate.map((t) => dayMonth(t.date));
    const balanceSeries = byDate.map((t) => safeNum(t.balance));
    const balAvg = balanceSeries.length
      ? Math.round(balanceSeries.reduce((s, v) => s + v, 0) / balanceSeries.length)
      : 0;
    const balMin = balanceSeries.length ? Math.min(...balanceSeries) : 0;
    const balanceTimeline = {
      labels: balanceLabels,
      balance: balanceSeries,
      avg: balAvg,
      min: balMin,
    };

    // --- dailyNet: Σ amount per calendar day + 7-day rolling average -------
    const dayTotals = {};
    txns.forEach((t) => {
      const day = String(t.date || "").slice(0, 10);
      if (!day) return;
      dayTotals[day] = (dayTotals[day] || 0) + safeNum(t.amount);
    });
    const days = Object.keys(dayTotals).sort();
    const netSeries = days.map((d) => Math.round(dayTotals[d]));
    const dailyNet = {
      labels: days.map((d) => dayMonth(d)),
      net: netSeries,
      rolling: rollingAverage(netSeries, 7),
    };

    // --- topTxns: diverging top-5 incomes + top-5 expenses ----------------
    const expenses = txns
      .filter((t) => safeNum(t.amount) < 0)
      .sort((a, b) => Math.abs(safeNum(b.amount)) - Math.abs(safeNum(a.amount)))
      .slice(0, 5);
    const incomes = txns
      .filter((t) => safeNum(t.amount) > 0)
      .sort((a, b) => safeNum(b.amount) - safeNum(a.amount))
      .slice(0, 5);
    const toItem = (t) => ({
      label: shortLabel(t.description),
      date: dayMonth(t.date),
      value: safeNum(t.amount),
    });
    // Incomes (positive/teal) on top, expenses (negative/red) below — sorted
    // so the diverging horizontal bar reads high→low across the zero axis.
    const items = [
      ...incomes.map(toItem).sort((a, b) => b.value - a.value),
      ...expenses.map(toItem).sort((a, b) => b.value - a.value),
    ];

    // recurring: same rounded magnitude + desc prefix appearing >= 2 times.
    const recurringGroups = {};
    txns.forEach((t) => {
      const amt = safeNum(t.amount);
      if (amt === 0) return;
      const bucket = Math.round(Math.abs(amt) / 1000) * 1000;
      const prefix = normDesc(t.description).slice(0, 12);
      const key = `${bucket}|${prefix}`;
      recurringGroups[key] = (recurringGroups[key] || 0) + 1;
    });
    const recurring = Object.values(recurringGroups).filter((c) => c >= 2).length;

    return {
      donut: { labels: ["Thu", "Chi"], values: [income, expense] },
      gauge: { score: health.financial_score, label: health.health_label },
      balanceTimeline,
      dailyNet,
      topTxns: { items, recurring },
    };
  }

  function keywordTrend(transactions, keyword, windowDays = 30) {
    if (!transactions.length) return null;
    const latest = Math.max(...transactions.map((t) => new Date(t.date).getTime()));
    const recentStart = latest - windowDays * 86400000;
    const priorStart = latest - windowDays * 2 * 86400000;
    const kw = keyword.toLowerCase();

    let recent = 0;
    let prior = 0;
    transactions.forEach((t) => {
      if (t.amount >= 0) return;
      if (!normDesc(t.description).includes(kw)) return;
      const ts = new Date(t.date).getTime();
      const amt = Math.abs(t.amount);
      if (ts >= recentStart) recent += amt;
      else if (ts >= priorStart) prior += amt;
    });

    if (recent === 0 && prior === 0) return null;
    return { keyword, recent, prior, delta: recent - prior };
  }

  // ---------------------------------------------------------------------------
  // generateInsights — deterministic, 100% client-side analytics engine.
  //
  // Each rule is a GUARDED push: it only fires when the underlying data exists,
  // every divisor is checked, and no NaN/undefined/empty string can leak (money
  // routed through formatVnd, percentages through Math.round, labels default to
  // "—"). Rules are appended in priority order, then the list is capped to the
  // top 7. `charts` is the SAME payload computed by buildInsightsPayload (keys
  // balanceTimeline / dailyNet / topTxns / donut) — reused, never recomputed.
  // ---------------------------------------------------------------------------
  function generateInsights(transactions, summary, health, charts) {
    const insights = [];
    const txns = Array.isArray(transactions) ? transactions : [];
    const s = summary || {};
    const h = health || {};
    const c = charts || {};

    const income = safeNum(s.total_income);
    const expense = safeNum(s.total_expense);
    const count = safeNum(s.transaction_count);

    const balanceTimeline = c.balanceTimeline || {};
    const balLabels = Array.isArray(balanceTimeline.labels) ? balanceTimeline.labels : [];
    const balSeries = Array.isArray(balanceTimeline.balance) ? balanceTimeline.balance : [];
    // Closing balance: prefer an explicit health field, else the last point of
    // the running balance timeline (the actual end-of-period balance).
    const lastBalance = balSeries.length
      ? safeNum(balSeries[balSeries.length - 1])
      : safeNum(h.last_balance);
    const dailyNet = c.dailyNet || {};
    const dnLabels = Array.isArray(dailyNet.labels) ? dailyNet.labels : [];
    const dnNet = Array.isArray(dailyNet.net) ? dailyNet.net : [];
    const topTxns = c.topTxns || {};
    const topItems = Array.isArray(topTxns.items) ? topTxns.items : [];

    // 1. Net cash flow for the period.
    if (count > 0) {
      const net = income - expense;
      const verb = net >= 0 ? "dư" : "thâm hụt";
      insights.push(
        `Kỳ này bạn ${verb} ${formatVnd(Math.abs(net))} (thu ${formatVnd(income)}, chi ${formatVnd(expense)}).`
      );
    }

    // 2. Saving rate + 20% benchmark.
    if (income > 0) {
      const sr = Math.round(safeNum(h.saving_rate) * 100);
      let verdict;
      if (sr > 20) verdict = "vượt mức khuyến nghị 20% 👍";
      else if (sr >= 18) verdict = "đạt mức khuyến nghị ~20%";
      else verdict = "dưới mức khuyến nghị 20%, nên tiết kiệm thêm";
      insights.push(`Tỷ lệ tiết kiệm ${sr}% — ${verdict}.`);
    }

    // 3. Opening → closing balance + lowest point.
    if (balLabels.length > 0 && balSeries.length > 0) {
      const first = safeNum(balSeries[0]);
      const last = safeNum(balSeries[balSeries.length - 1]);
      const min = safeNum(balanceTimeline.min);
      insights.push(
        `Số dư: ${formatVnd(first)} đầu kỳ → ${formatVnd(last)} cuối kỳ (thấp nhất ${formatVnd(min)}).`
      );
    }

    // 4. Largest single expense (most-negative txn).
    if (expense > 0) {
      let worst = null;
      topItems.forEach((it) => {
        const v = safeNum(it.value);
        if (v < 0 && (worst === null || v < safeNum(worst.value))) worst = it;
      });
      if (worst === null) {
        txns.forEach((t) => {
          const v = safeNum(t.amount);
          if (v < 0 && (worst === null || v < safeNum(worst.value))) {
            worst = { value: v, label: shortLabel(t.description), date: dayMonth(t.date) };
          }
        });
      }
      if (worst) {
        const label = shortLabel(worst.label) || "—";
        const when = worst.date ? ` ngày ${worst.date}` : "";
        insights.push(`Khoản chi lớn nhất: ${formatVnd(Math.abs(safeNum(worst.value)))} — “${label}”${when}.`);
      }
    }

    // 5. Largest single income (most-positive txn).
    if (income > 0) {
      let best = null;
      topItems.forEach((it) => {
        const v = safeNum(it.value);
        if (v > 0 && (best === null || v > safeNum(best.value))) best = it;
      });
      if (best === null) {
        txns.forEach((t) => {
          const v = safeNum(t.amount);
          if (v > 0 && (best === null || v > safeNum(best.value))) {
            best = { value: v, label: shortLabel(t.description) };
          }
        });
      }
      if (best) {
        const label = shortLabel(best.label) || "—";
        insights.push(`Nguồn thu lớn nhất: ${formatVnd(safeNum(best.value))} — “${label}”.`);
      }
    }

    // 6. Expense concentration — top 5 expenses as a share of total spend.
    if (expense > 0) {
      const expMags = txns
        .map((t) => safeNum(t.amount))
        .filter((v) => v < 0)
        .map((v) => Math.abs(v));
      if (expMags.length >= 5) {
        expMags.sort((a, b) => b - a);
        const top5 = expMags.slice(0, 5).reduce((acc, v) => acc + v, 0);
        const pct = Math.round((top5 / expense) * 100);
        let line = `Top 5 khoản chi chiếm ${pct}% tổng chi`;
        if (pct >= 60) line += " — khá tập trung";
        insights.push(line + ".");
      }
    }

    // 7. Burn rate & runway.
    if (expense > 0 && lastBalance > 0) {
      let days = 0;
      if (s.date_from && s.date_to) {
        const from = Date.parse(`${String(s.date_from).slice(0, 10)}T00:00:00`);
        const to = Date.parse(`${String(s.date_to).slice(0, 10)}T00:00:00`);
        if (Number.isFinite(from) && Number.isFinite(to) && to >= from) {
          days = Math.round((to - from) / 86400000) + 1;
        }
      }
      days = Math.max(1, days);
      const burn = expense / days;
      if (burn > 0) {
        const runway = Math.floor(lastBalance / burn);
        const runwayLabel = runway > 999 ? "999+" : String(runway);
        insights.push(
          `Mức chi TB ${formatVnd(Math.round(burn))}/ngày; với số dư hiện tại đủ dùng ~${runwayLabel} ngày.`
        );
      }
    }

    // 8. Heaviest spending day (most-negative daily net).
    if (dnLabels.length > 0 && dnNet.length > 0) {
      let worstIdx = -1;
      let worstVal = 0;
      for (let i = 0; i < dnNet.length; i += 1) {
        const v = safeNum(dnNet[i]);
        if (v < worstVal) {
          worstVal = v;
          worstIdx = i;
        }
      }
      if (worstIdx >= 0) {
        const label = dnLabels[worstIdx] || "—";
        insights.push(`Chi mạnh nhất ngày ${label}: ${formatVnd(Math.abs(worstVal))}.`);
      }
    }

    // 9. Recurring / periodic transactions.
    const recurring = safeNum(topTxns.recurring);
    if (recurring > 0) {
      insights.push(`Phát hiện ${recurring} khoản lặp lại — có thể là chi/thu định kỳ.`);
    }

    // 10. Expense-to-income warning.
    if (income > 0 && safeNum(h.expense_ratio) > 0.9) {
      insights.push("Tỷ lệ chi/thu trên 90% — cần kiểm soát chi tiêu chặt hơn.");
    }

    // 11. Fallback when nothing above fired.
    if (!insights.length) {
      insights.push("Chưa đủ dữ liệu để phân tích sâu — hãy upload thêm sao kê.");
    }

    return insights.slice(0, 7);
  }

  function buildInsightsPayload(transactions) {
    const summary = computeSummary(transactions);
    const health = financialHealth(summary);
    const charts = chartDatasets(transactions, health);
    const insights = generateInsights(transactions, summary, health, charts);
    return { summary, health, charts, insights };
  }

  function formatVnd(n) {
    // Display guard: never surface NaN/undefined/null — fall back to em dash.
    const v = Number(n);
    if (!Number.isFinite(v)) return "—";
    return new Intl.NumberFormat("vi-VN").format(v) + " ₫";
  }

  global.FDashboardInsights = {
    HEALTH_LEVELS,
    buildInsightsPayload,
    categorizeExpense,
    computeSummary,
    financialHealth,
    formatVnd,
  };
})(typeof window !== "undefined" ? window : globalThis);