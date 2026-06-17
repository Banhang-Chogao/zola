/**
 * F-Dashboard export — JSON + PDF infographic.
 * Sau khi tải: xóa IndexedDB (không lưu tích lũy online).
 */
(function (global) {
  "use strict";

  const BLOG_DOMAIN = (function () {
    try {
      return location.hostname || "banhang-chogao.github.io";
    } catch (e) {
      return "banhang-chogao.github.io";
    }
  })();

  const BLOG_URL = (function () {
    const meta = document.querySelector('meta[name="zola-base-url"]');
    if (meta && meta.getAttribute("content")) return meta.getAttribute("content");
    return location.origin + location.pathname.replace(/\/tools\/f-dashboard\/?$/, "");
  })();

  function seriesId16() {
    const bytes = new Uint8Array(8);
    crypto.getRandomValues(bytes);
    return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  }

  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.rel = "noopener";
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 4000);
  }

  function buildExportPayload(transactions, insightsPayload) {
    const series = seriesId16();
    return {
      series_id: series,
      exported_at: new Date().toISOString(),
      blog_url: BLOG_URL,
      blog_domain: BLOG_DOMAIN,
      source: "f-dashboard",
      transactions,
      summary: insightsPayload.summary,
      health: insightsPayload.health,
      insights: insightsPayload.insights,
      charts_meta: {
        transaction_count: transactions.length,
      },
    };
  }

  function exportJson(transactions, insightsPayload) {
    const payload = buildExportPayload(transactions, insightsPayload);
    const stamp = payload.exported_at.slice(0, 10);
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json;charset=utf-8",
    });
    downloadBlob(blob, `f-dashboard-${stamp}-${payload.series_id}.json`);
    return payload.series_id;
  }

  function watermarkText(series) {
    return series + "_" + BLOG_DOMAIN;
  }

  function addPdfWatermark(doc, series, pageW, pageH) {
    const wm = watermarkText(series);
    doc.setTextColor(200, 205, 212);
    doc.setFontSize(9);
    const cols = 3;
    const rows = 5;
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const x = (c + 0.5) * (pageW / cols);
        const y = (r + 1) * (pageH / (rows + 1));
        doc.text(wm, x, y, { align: "center", angle: 35 });
      }
    }
  }

  function exportPdf(transactions, insightsPayload) {
    const { jsPDF } = global.jspdf || {};
    if (!jsPDF) throw new Error("jsPDF chưa tải — thử lại sau vài giây.");

    const payload = buildExportPayload(transactions, insightsPayload);
    const series = payload.series_id;
    const { summary, health, insights } = payload;
    const fmt = global.FDashboardInsights.formatVnd;

    const doc = new jsPDF({ unit: "mm", format: "a4" });
    const pageW = doc.internal.pageSize.getWidth();
    const pageH = doc.internal.pageSize.getHeight();
    const margin = 14;
    let y = margin;

    addPdfWatermark(doc, series, pageW, pageH);

    doc.setTextColor(30, 41, 59);
    doc.setFontSize(20);
    doc.text("F-Dashboard — Báo cáo tài chính", margin, y);
    y += 8;
    doc.setFontSize(10);
    doc.setTextColor(100, 116, 139);
    doc.text("VietinBank · " + BLOG_URL, margin, y);
    y += 5;
    doc.text("Xuất lúc: " + payload.exported_at.replace("T", " ").slice(0, 19), margin, y);
    y += 10;

    // Summary cards
    const cards = [
      ["Tổng thu", fmt(summary.total_income), [16, 185, 129]],
      ["Tổng chi", fmt(summary.total_expense), [239, 68, 68]],
      ["Chênh lệch", fmt(summary.net_cash_flow), [59, 130, 246]],
      ["Giao dịch", String(summary.transaction_count), [100, 116, 139]],
    ];
    const cardW = (pageW - margin * 2 - 9) / 4;
    cards.forEach((card, i) => {
      const x = margin + i * (cardW + 3);
      doc.setFillColor(248, 250, 252);
      doc.roundedRect(x, y, cardW, 22, 2, 2, "F");
      doc.setFontSize(8);
      doc.setTextColor(100, 116, 139);
      doc.text(card[0], x + 3, y + 7);
      doc.setFontSize(11);
      doc.setTextColor(card[2][0], card[2][1], card[2][2]);
      doc.text(card[1], x + 3, y + 16);
    });
    y += 28;

    // Health block
    doc.setFillColor(0, 55, 132);
    doc.roundedRect(margin, y, pageW - margin * 2, 32, 3, 3, "F");
    doc.setTextColor(255, 255, 255);
    doc.setFontSize(11);
    doc.text("Financial Health Score", margin + 5, y + 9);
    doc.setFontSize(28);
    doc.text(String(health.financial_score), margin + 5, y + 22);
    doc.setFontSize(12);
    doc.text(health.health_label, margin + 45, y + 22);
    doc.setFontSize(9);
    doc.text(
      "Saving " + Math.round(health.saving_rate * 100) + "% · Expense ratio " + Math.round(health.expense_ratio * 100) + "%",
      margin + 5,
      y + 28
    );
    y += 40;

    // Health levels legend
    doc.setTextColor(30, 41, 59);
    doc.setFontSize(12);
    doc.text("Định nghĩa cấp độ sức khỏe tài chính", margin, y);
    y += 6;
    const levels = global.FDashboardInsights.HEALTH_LEVELS || [];
    doc.setFontSize(9);
    levels.forEach((lv) => {
      doc.setTextColor(30, 41, 59);
      doc.text(lv.label + " (≥" + lv.min + ")", margin, y);
      doc.setTextColor(100, 116, 139);
      doc.text(lv.desc, margin + 42, y);
      y += 5;
    });
    y += 4;

    // Insights
    doc.setTextColor(30, 41, 59);
    doc.setFontSize(12);
    doc.text("AI Insights", margin, y);
    y += 6;
    doc.setFontSize(9);
    doc.setTextColor(51, 65, 85);
    (insights || []).slice(0, 8).forEach((line) => {
      const wrapped = doc.splitTextToSize("• " + line, pageW - margin * 2);
      doc.text(wrapped, margin, y);
      y += wrapped.length * 4.2;
    });
    y += 4;

    // Recent transactions table (first page tail)
    if (y > pageH - 50) {
      doc.addPage();
      addPdfWatermark(doc, series, pageW, pageH);
      y = margin;
    }
    doc.setFontSize(12);
    doc.setTextColor(30, 41, 59);
    doc.text("Giao dịch gần nhất (tối đa 15)", margin, y);
    y += 7;
    doc.setFontSize(8);
    const rows = transactions.slice(0, 15);
    rows.forEach((t, idx) => {
      if (y > pageH - 12) {
        doc.addPage();
        addPdfWatermark(doc, series, pageW, pageH);
        y = margin;
      }
      const sign = t.amount > 0 ? "+" : "";
      const line =
        (idx + 1) +
        ". " +
        t.date.slice(0, 10) +
        " · " +
        t.description.slice(0, 42) +
        (t.description.length > 42 ? "…" : "") +
        " · " +
        sign +
        fmt(Math.abs(t.amount));
      doc.setTextColor(t.amount > 0 ? 16 : 239, t.amount > 0 ? 185 : 68, t.amount > 0 ? 129 : 68);
      doc.text(line, margin, y);
      y += 4.5;
    });

    // Footer watermark emphasis
    doc.setFontSize(7);
    doc.setTextColor(148, 163, 184);
    doc.text(
      "Watermark: " + watermarkText(series) + " · Dữ liệu chỉ dùng offline — không lưu trên blog",
      margin,
      pageH - 8
    );

    const stamp = payload.exported_at.slice(0, 10);
    doc.save("f-dashboard-report-" + stamp + "-" + series + ".pdf");
    return series;
  }

  global.FDashboardExport = {
    exportJson,
    exportPdf,
    seriesId16,
    watermarkText,
    BLOG_DOMAIN,
  };
})(typeof window !== "undefined" ? window : globalThis);