/**
 * F-Dashboard export — auto-download JSON/PDF, then wipe local storage.
 * No persistent online storage (IndexedDB only, cleared after export).
 */
(function (global) {
  "use strict";

  const BLOG_URL = (function () {
    const meta = document.querySelector('meta[name="zola-base-url"]');
    if (meta && meta.getAttribute("content")) return meta.getAttribute("content").trim();
    return (location.origin + location.pathname).replace(/\/tools\/f-dashboard\/?$/, "");
  })();

  function normalizeBlogUrl(url) {
    return String(url)
      .replace(/^https?:\/\//i, "")
      .replace(/\/$/, "");
  }

  const BLOG_URL_SLUG = normalizeBlogUrl(BLOG_URL);

  /** 16-char lowercase hex blockchain series ID */
  function seriesId16() {
    const bytes = new Uint8Array(8);
    crypto.getRandomValues(bytes);
    return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  }

  function watermarkText(series) {
    return series + "_" + BLOG_URL_SLUG;
  }

  function downloadBlob(blob, filename) {
    return new Promise((resolve) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.rel = "noopener";
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => {
        URL.revokeObjectURL(url);
        resolve();
      }, 120);
    });
  }

  function buildPayload(transactions, insightsPayload) {
    const series = seriesId16();
    return {
      series_id: series,
      watermark: watermarkText(series),
      exported_at: new Date().toISOString(),
      blog_url: BLOG_URL,
      source: "f-dashboard",
      transactions,
      summary: insightsPayload.summary,
      health: insightsPayload.health,
      insights: insightsPayload.insights,
    };
  }

  /** Invisible faint watermark — forensic trace, not visible to casual reader */
  function stampInvisibleWatermark(doc, series, pageW, pageH) {
    const wm = watermarkText(series);
    doc.setFontSize(6);
    doc.setTextColor(242, 244, 248);
    const cols = 4;
    const rows = 7;
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        doc.text(wm, (c + 0.5) * (pageW / cols), (r + 1) * (pageH / (rows + 1)), {
          align: "center",
          angle: 32,
        });
      }
    }
  }

  function drawPdfReport(doc, payload, transactions) {
    const { summary, health, insights, series_id: series } = payload;
    const fmt = global.FDashboardInsights.formatVnd;
    const pageW = doc.internal.pageSize.getWidth();
    const pageH = doc.internal.pageSize.getHeight();
    const margin = 14;
    let y = margin;

    stampInvisibleWatermark(doc, series, pageW, pageH);

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
      "Saving " + Math.round(health.saving_rate * 100) + "% · Expense ratio " +
        Math.round(health.expense_ratio * 100) + "%",
      margin + 5,
      y + 28
    );
    y += 40;

    doc.setTextColor(30, 41, 59);
    doc.setFontSize(12);
    doc.text("Financial Health tiers", margin, y);
    y += 6;
    doc.setFontSize(9);
    (global.FDashboardInsights.HEALTH_LEVELS || []).forEach((lv) => {
      doc.setTextColor(30, 41, 59);
      doc.text(lv.label + " — " + lv.range, margin, y);
      doc.setTextColor(100, 116, 139);
      const wrapped = doc.splitTextToSize(lv.desc, pageW - margin * 2 - 40);
      doc.text(wrapped, margin + 38, y);
      y += Math.max(5, wrapped.length * 4);
    });
    y += 4;

    doc.setFontSize(12);
    doc.setTextColor(30, 41, 59);
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

    if (y > pageH - 50) {
      doc.addPage();
      stampInvisibleWatermark(doc, series, pageW, pageH);
      y = margin;
    }

    doc.setFontSize(12);
    doc.text("Giao dịch gần nhất (tối đa 15)", margin, y);
    y += 7;
    doc.setFontSize(8);
    transactions.slice(0, 15).forEach((t, idx) => {
      if (y > pageH - 12) {
        doc.addPage();
        stampInvisibleWatermark(doc, series, pageW, pageH);
        y = margin;
      }
      const sign = t.amount > 0 ? "+" : "";
      const line =
        idx + 1 + ". " + t.date.slice(0, 10) + " · " +
        t.description.slice(0, 40) + (t.description.length > 40 ? "…" : "") +
        " · " + sign + fmt(Math.abs(t.amount));
      doc.setTextColor(
        t.amount > 0 ? 16 : 239,
        t.amount > 0 ? 185 : 68,
        t.amount > 0 ? 129 : 68
      );
      doc.text(line, margin, y);
      y += 4.5;
    });
  }

  async function exportJson(transactions, insightsPayload) {
    const payload = buildPayload(transactions, insightsPayload);
    const stamp = payload.exported_at.slice(0, 10);
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json;charset=utf-8",
    });
    await downloadBlob(blob, `f-dashboard-${stamp}-${payload.series_id}.json`);
    return payload;
  }

  async function exportPdf(transactions, insightsPayload) {
    const { jsPDF } = global.jspdf || {};
    if (!jsPDF) throw new Error("jsPDF chưa tải — thử lại sau vài giây.");

    const payload = buildPayload(transactions, insightsPayload);
    const doc = new jsPDF({ unit: "mm", format: "a4" });
    drawPdfReport(doc, payload, transactions);

    const stamp = payload.exported_at.slice(0, 10);
    doc.save(`f-dashboard-report-${stamp}-${payload.series_id}.pdf`);
    await new Promise((r) => setTimeout(r, 120));
    return payload;
  }

  /**
   * Auto-download then wipe callback (caller clears IndexedDB).
   * @returns {Promise<{series_id, watermark}>}
   */
  async function exportAndWipe(format, transactions, insightsPayload, wipeFn) {
    const exporter = format === "pdf" ? exportPdf : exportJson;
    const payload = await exporter(transactions, insightsPayload);
    if (typeof wipeFn === "function") await wipeFn();
    return { series_id: payload.series_id, watermark: payload.watermark };
  }

  global.FDashboardExport = {
    exportJson,
    exportPdf,
    exportAndWipe,
    seriesId16,
    watermarkText,
    BLOG_URL,
    BLOG_URL_SLUG,
  };
})(typeof window !== "undefined" ? window : globalThis);