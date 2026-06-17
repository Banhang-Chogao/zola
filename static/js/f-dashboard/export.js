/**
 * F-Dashboard export — auto-download JSON/PDF, then wipe local storage.
 * PDF: landscape A4, Nokia Pure/Headline embedded, bank-style report layout.
 */
(function (global) {
  "use strict";

  const BLOG_URL = (function () {
    const meta = document.querySelector('meta[name="zola-base-url"]');
    if (meta && meta.getAttribute("content")) return meta.getAttribute("content").trim();
    return (location.origin + location.pathname).replace(/\/tools\/f-dashboard\/?$/, "");
  })();

  const FONT_BASE = BLOG_URL.replace(/\/$/, "") + "/fonts/nokia-pure/";
  const BRAND_NAVY = [0, 55, 132];
  const INK = [30, 41, 59];
  const MUTED = [100, 116, 139];
  const INCOME = [16, 185, 129];
  const EXPENSE = [239, 68, 68];
  const ACCENT = [59, 130, 246];

  let fontsReady = null;

  function normalizeBlogUrl(url) {
    return String(url)
      .replace(/^https?:\/\//i, "")
      .replace(/\/$/, "");
  }

  const BLOG_URL_SLUG = normalizeBlogUrl(BLOG_URL);

  function seriesId16() {
    const bytes = new Uint8Array(8);
    crypto.getRandomValues(bytes);
    return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  }

  function watermarkText(series) {
    return series + "_" + BLOG_URL_SLUG;
  }

  function arrayBufferToBase64(buf) {
    const bytes = new Uint8Array(buf);
    let bin = "";
    const chunk = 0x8000;
    for (let i = 0; i < bytes.length; i += chunk) {
      bin += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
    }
    return btoa(bin);
  }

  async function ensurePdfFonts(doc) {
    if (!fontsReady) {
      fontsReady = (async () => {
        const [regBuf, boldBuf, headBuf] = await Promise.all([
          fetch(FONT_BASE + "NokiaPureText-Regular.ttf").then((r) => {
            if (!r.ok) throw new Error("Không tải được font Nokia Pure Regular.");
            return r.arrayBuffer();
          }),
          fetch(FONT_BASE + "NokiaPureText-Bold.ttf").then((r) => {
            if (!r.ok) throw new Error("Không tải được font Nokia Pure Bold.");
            return r.arrayBuffer();
          }),
          fetch(FONT_BASE + "NokiaPureHeadline-Bold.ttf").then((r) => {
            if (!r.ok) throw new Error("Không tải được font Nokia Headline.");
            return r.arrayBuffer();
          }),
        ]);

        doc.addFileToVFS("NokiaPureText-Regular.ttf", arrayBufferToBase64(regBuf));
        doc.addFont("NokiaPureText-Regular.ttf", "NokiaPure", "normal");
        doc.addFileToVFS("NokiaPureText-Bold.ttf", arrayBufferToBase64(boldBuf));
        doc.addFont("NokiaPureText-Bold.ttf", "NokiaPure", "bold");
        doc.addFileToVFS("NokiaPureHeadline-Bold.ttf", arrayBufferToBase64(headBuf));
        doc.addFont("NokiaPureHeadline-Bold.ttf", "NokiaHeadline", "bold");
      })();
    }
    await fontsReady;
  }

  function setFont(doc, style, size) {
    if (style === "headline") {
      doc.setFont("NokiaHeadline", "bold");
    } else {
      doc.setFont("NokiaPure", style === "bold" ? "bold" : "normal");
    }
    if (size) doc.setFontSize(size);
  }

  function setRgb(doc, rgb) {
    doc.setTextColor(rgb[0], rgb[1], rgb[2]);
  }

  function withOpacity(doc, opacity, fn) {
    const GState = doc.GState || (global.jspdf && global.jspdf.jsPDF && global.jspdf.jsPDF.GState);
    if (typeof GState === "function") {
      doc.saveGraphicsState();
      doc.setGState(new GState({ opacity }));
      fn();
      doc.restoreGraphicsState();
      return;
    }
    fn();
  }

  /** Trace watermark — visible but low-opacity, repeated diagonally */
  function stampWatermark(doc, series, pageW, pageH) {
    const wm = watermarkText(series);

    withOpacity(doc, 0.12, () => {
      setFont(doc, "normal", 18);
      setRgb(doc, [160, 170, 185]);
      doc.text(wm, pageW / 2, pageH / 2, { align: "center", angle: -32 });
    });

    withOpacity(doc, 0.1, () => {
      setFont(doc, "normal", 9);
      setRgb(doc, [175, 184, 198]);
      const cols = 3;
      const rows = 4;
      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          doc.text(wm, (c + 0.55) * (pageW / cols), (r + 1.1) * (pageH / (rows + 0.5)), {
            align: "center",
            angle: 35,
          });
        }
      }
    });

    setRgb(doc, INK);
  }

  function drawHeaderBand(doc, payload, pageW, margin) {
    const bandH = 26;
    doc.setFillColor(BRAND_NAVY[0], BRAND_NAVY[1], BRAND_NAVY[2]);
    doc.rect(0, 0, pageW, bandH, "F");

    setFont(doc, "headline", 16);
    doc.setTextColor(255, 255, 255);
    doc.text("F-Dashboard — Báo cáo tài chính", margin, 11);

    setFont(doc, "normal", 8.5);
    doc.setTextColor(210, 225, 245);
    const exported = payload.exported_at.replace("T", " ").slice(0, 19);
    doc.text("VietinBank · " + BLOG_URL_SLUG, margin, 17);
    doc.text("Xuất lúc: " + exported, margin, 22);

    doc.setTextColor(INK[0], INK[1], INK[2]);
    return bandH + 6;
  }

  function drawKpiCards(doc, summary, fmt, margin, pageW, y) {
    const cards = [
      { label: "Tổng thu", value: fmt(summary.total_income), color: INCOME },
      { label: "Tổng chi", value: fmt(summary.total_expense), color: EXPENSE },
      { label: "Chênh lệch", value: fmt(summary.net_cash_flow), color: ACCENT },
      { label: "Giao dịch", value: String(summary.transaction_count), color: MUTED },
    ];
    const gap = 4;
    const cardW = (pageW - margin * 2 - gap * 3) / 4;
    const cardH = 24;

    cards.forEach((card, i) => {
      const x = margin + i * (cardW + gap);
      doc.setDrawColor(226, 232, 240);
      doc.setFillColor(248, 250, 252);
      doc.roundedRect(x, y, cardW, cardH, 2.5, 2.5, "FD");

      setFont(doc, "normal", 8);
      setRgb(doc, MUTED);
      doc.text(card.label, x + 4, y + 8);

      setFont(doc, "bold", 12);
      setRgb(doc, card.color);
      const valueLines = doc.splitTextToSize(card.value, cardW - 8);
      doc.text(valueLines[0], x + 4, y + 17);
    });

    return y + cardH + 8;
  }

  function healthAccent(label) {
    const key = String(label || "").toLowerCase();
    if (key === "excellent") return [5, 150, 105];
    if (key === "good") return [37, 99, 235];
    if (key === "average") return [217, 119, 6];
    if (key === "risky") return [234, 88, 12];
    if (key === "danger") return [220, 38, 38];
    return BRAND_NAVY;
  }

  function drawHealthBlock(doc, health, margin, pageW, y) {
    const blockW = pageW - margin * 2;
    const blockH = 34;

    doc.setFillColor(BRAND_NAVY[0], BRAND_NAVY[1], BRAND_NAVY[2]);
    doc.roundedRect(margin, y, blockW, blockH, 3, 3, "F");

    setFont(doc, "normal", 9);
    doc.setTextColor(210, 225, 245);
    doc.text("Điểm sức khỏe tài chính", margin + 6, y + 9);

    setFont(doc, "headline", 26);
    doc.setTextColor(255, 255, 255);
    doc.text(String(health.financial_score), margin + 6, y + 24);

    const accent = healthAccent(health.health_label);
    setFont(doc, "bold", 13);
    doc.setTextColor(accent[0], accent[1], accent[2]);
    doc.text(health.health_label, margin + 32, y + 24);

    const sr = Math.round(health.saving_rate * 100);
    const er = Math.round(health.expense_ratio * 100);
    setFont(doc, "normal", 8.5);
    doc.setTextColor(230, 238, 252);
    doc.text(
      "Tỷ lệ tiết kiệm: " + sr + "%  ·  Tỷ lệ chi: " + er + "%  ·  Dòng tiền: " +
        global.FDashboardInsights.formatVnd(health.net_cash_flow),
      margin + 6,
      y + 30
    );

    setRgb(doc, INK);
    return y + blockH + 8;
  }

  function drawHealthTiers(doc, x, colW, y) {
    setFont(doc, "bold", 10);
    setRgb(doc, INK);
    doc.text("Cấp độ sức khỏe tài chính", x, y);
    y += 5;

    const levels = global.FDashboardInsights.HEALTH_LEVELS || [];
    levels.forEach((lv) => {
      setFont(doc, "bold", 7.5);
      setRgb(doc, healthAccent(lv.label));
      doc.text(lv.label + " (" + lv.range + ")", x, y);
      setFont(doc, "normal", 7.5);
      setRgb(doc, MUTED);
      const wrapped = doc.splitTextToSize(lv.desc, colW - 40);
      doc.text(wrapped, x + 40, y);
      y += Math.max(4.5, wrapped.length * 3.6);
    });
    return y + 3;
  }

  function drawInsights(doc, insights, x, colW, y, maxY) {
    setFont(doc, "bold", 10);
    setRgb(doc, INK);
    doc.text("Nhận xét tự động", x, y);
    y += 5;

    setFont(doc, "normal", 8);
    setRgb(doc, [51, 65, 85]);
    (insights || []).slice(0, 6).forEach((line) => {
      if (y > maxY) return;
      const wrapped = doc.splitTextToSize("• " + line, colW);
      doc.text(wrapped, x, y);
      y += wrapped.length * 3.8;
    });
    return y + 4;
  }

  function drawTransactionTable(doc, transactions, fmt, margin, pageW, startY, series) {
    if (typeof doc.autoTable !== "function") {
      setFont(doc, "normal", 9);
      setRgb(doc, MUTED);
      doc.text("Bảng giao dịch: plugin autotable chưa tải.", margin, startY);
      return startY + 8;
    }

    const rows = transactions.slice(0, 25).map((t, idx) => {
      const sign = t.amount > 0 ? "+" : "";
      return [
        String(idx + 1),
        t.date.slice(0, 10),
        t.description.length > 55 ? t.description.slice(0, 52) + "…" : t.description,
        sign + fmt(Math.abs(t.amount)),
        fmt(t.balance),
      ];
    });

    doc.autoTable({
      startY,
      margin: { left: margin, right: margin },
      head: [["STT", "Ngày", "Nội dung", "Số tiền GD", "Số dư"]],
      body: rows,
      styles: {
        font: "NokiaPure",
        fontSize: 8,
        cellPadding: 2.5,
        lineColor: [226, 232, 240],
        lineWidth: 0.2,
        textColor: INK,
        overflow: "linebreak",
      },
      headStyles: {
        font: "NokiaPure",
        fontStyle: "bold",
        fillColor: BRAND_NAVY,
        textColor: [255, 255, 255],
        halign: "left",
      },
      columnStyles: {
        0: { cellWidth: 12, halign: "center" },
        1: { cellWidth: 24 },
        2: { cellWidth: "auto" },
        3: { cellWidth: 38, halign: "right" },
        4: { cellWidth: 38, halign: "right" },
      },
      alternateRowStyles: { fillColor: [248, 250, 252] },
      didDrawPage: (data) => {
        const pageW = doc.internal.pageSize.getWidth();
        const pageH = doc.internal.pageSize.getHeight();
        stampWatermark(doc, series, pageW, pageH);
        if (data.pageNumber > 1) {
          setFont(doc, "normal", 7);
          setRgb(doc, MUTED);
          doc.text("F-Dashboard — Bảng giao dịch (tiếp)", margin, 8);
        }
      },
      didParseCell: (data) => {
        if (data.section !== "body" || data.column.index !== 3) return;
        const raw = transactions[data.row.index];
        if (!raw) return;
        if (raw.amount > 0) data.cell.styles.textColor = INCOME;
        else if (raw.amount < 0) data.cell.styles.textColor = EXPENSE;
      },
    });

    return doc.lastAutoTable ? doc.lastAutoTable.finalY + 6 : startY + 8;
  }

  function drawPdfReport(doc, payload, transactions) {
    const { summary, health, insights, series_id: series } = payload;
    const fmt = global.FDashboardInsights.formatVnd;
    const pageW = doc.internal.pageSize.getWidth();
    const pageH = doc.internal.pageSize.getHeight();
    const margin = 12;

    stampWatermark(doc, series, pageW, pageH);

    let y = drawHeaderBand(doc, payload, pageW, margin);

    if (summary.date_from && summary.date_to) {
      setFont(doc, "normal", 8);
      setRgb(doc, MUTED);
      doc.text("Khoảng thời gian: " + summary.date_from + " → " + summary.date_to, margin, y);
      y += 6;
    }

    y = drawKpiCards(doc, summary, fmt, margin, pageW, y);
    y = drawHealthBlock(doc, health, margin, pageW, y);

    const splitY = y;
    const colW = (pageW - margin * 2 - 8) / 2;
    const tiersEnd = drawHealthTiers(doc, margin, colW, y);
    const insightsEnd = drawInsights(doc, insights, margin + colW + 8, colW, splitY, pageH - 20);

    y = Math.max(tiersEnd, insightsEnd);

    setFont(doc, "bold", 11);
    setRgb(doc, INK);
    doc.text("Bảng giao dịch", margin, y);
    y += 5;

    drawTransactionTable(doc, transactions, fmt, margin, pageW, y, series);
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
    const doc = new jsPDF({ orientation: "landscape", unit: "mm", format: "a4" });
    await ensurePdfFonts(doc);
    drawPdfReport(doc, payload, transactions);

    const stamp = payload.exported_at.slice(0, 10);
    doc.save(`f-dashboard-report-${stamp}-${payload.series_id}.pdf`);
    await new Promise((r) => setTimeout(r, 120));
    return payload;
  }

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