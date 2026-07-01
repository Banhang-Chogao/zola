/* ============================================================================
   sdna-templates.js — 6 deterministic S-DNA SVG template generators.
   Each template returns a complete SVG string with:
     - viewBox matching requested export size
     - proper padding / safe zones
     - auto-wrapped & scaled title
     - S-DNA outline icons in circle containers
     - validation-friendly structure
   ============================================================================ */

var SDNA = SDNA || {};

SDNA.Templates = (function () {
  "use strict";

  var T = SDNA.Tokens;
  var L = SDNA.Layout;
  var PAD = T.PAD;
  var F = T.FONTS;

  /* ---- Helper: SVG text block with auto-wrapping and font scaling ---- */
  function renderTextBlock(text, opts) {
    var defaults = {
      x: 72, y: 180, maxWidth: 1056, maxLines: 3,
      fontFamily: F.heading, fontSize: 48, fontWeight: 700,
      fill: "#ffffff", lineHeight: 1.25, textAnchor: "start"
    };
    var o = {};
    for (var k in defaults) o[k] = defaults[k];
    if (opts) { for (var k2 in opts) o[k2] = opts[k2]; }

    if (!text) return { svg: "", lines: [], count: 0, overflow: false, endY: o.y };

    var scaled = L.scaleFont(text, o.maxWidth, o.maxLines, o.fontFamily, 16, o.fontSize, o.fontWeight, o.lineHeight);
    var lineH = scaled.fontSize * scaled.lineHeight;
    var svg = "";
    var yPos = o.y;

    for (var i = 0; i < scaled.lines.length; i++) {
      var attr = 'x="' + o.x + '" y="' + yPos + '"';
      if (i > 0) attr = 'x="' + o.x + '" dy="' + lineH + '"';
      svg += '  <text ' + attr + ' text-anchor="' + o.textAnchor + '" ' +
        'font-family="' + o.fontFamily + '" font-size="' + scaled.fontSize + '" ' +
        'font-weight="' + o.fontWeight + '" fill="' + o.fill + '">' +
        T.escHtml(scaled.lines[i]) + '</text>\n';
    }

    return {
      svg: svg,
      lines: scaled.lines,
      count: scaled.lines.length,
      fontSize: scaled.fontSize,
      overflow: scaled.overflow || false,
      endY: o.y + scaled.lines.length * lineH
    };
  }

  /* ---- Helper: KPI card with left accent bar + circle icon + value ---- */
  function kpiCard(x, y, w, h, accentColor, bgColor, iconFn, value, unit, label) {
    var iconSize = 30;
    var iconX = x + 16;
    var iconY = y + 16;
    var valueSize = 28;
    var textX = x + 16 + iconSize + 8;

    return '' +
      '<rect x="' + x + '" y="' + y + '" width="' + w + '" height="' + h + '" fill="' + bgColor + '" rx="14"/>' +
      '<rect x="' + x + '" y="' + y + '" width="4" height="' + h + '" fill="' + accentColor + '" rx="2"/>' +
      T.buildIcon(iconFn, iconX, iconY, iconSize, accentColor) +
      '<text x="' + textX + '" y="' + (y + 28) + '" ' +
        'font-family="' + F.heading + '" font-size="' + valueSize + '" font-weight="800" fill="' + T.PALETTES[0].navy + '">' +
        T.escHtml(value) + '</text>' +
      (unit ? '<text x="' + textX + '" y="' + (y + 46) + '" ' +
        'font-family="' + F.body + '" font-size="' + (valueSize - 10) + '" fill="' + T.PALETTES[0].navy + '" opacity="0.55">' +
        T.escHtml(unit) + '</text>' : '') +
      '<text x="' + textX + '" y="' + (y + h - 10) + '" ' +
        'font-family="' + F.body + '" font-size="11" font-weight="600" fill="' + accentColor + '" letter-spacing="0.5">' +
        T.escHtml(label) + '</text>';
  }

  /* ---- Helper: insight card (analysis bullet with icon) ---- */
  function insightCard(x, y, w, h, accentColor, bgColor, iconFn, text) {
    var iconSize = 26;
    var iconX = x + 14;
    var iconY = y + (h - iconSize) / 2;
    var tx = x + 14 + iconSize + 10;
    var scaled = L.scaleFont(text, w - iconSize - 40, 2, F.body, 12, 14, 500, 1.35);

    return '' +
      '<rect x="' + x + '" y="' + y + '" width="' + w + '" height="' + h + '" fill="' + bgColor + '" rx="10"/>' +
      '<rect x="' + x + '" y="' + y + '" width="3" height="' + h + '" fill="' + accentColor + '" rx="1.5"/>' +
      T.buildIcon(iconFn, iconX, iconY, iconSize, accentColor) +
      (scaled.lines.length > 0
        ? '<text x="' + tx + '" y="' + (y + h/2 - 4) + '" font-family="' + F.body + '" font-size="' + scaled.fontSize + '" font-weight="500" fill="' + T.PALETTES[0].navy + '">' +
          T.escHtml(scaled.lines[0]) + '</text>'
        : '') +
      (scaled.lines.length > 1
        ? '<text x="' + tx + '" dy="' + (scaled.fontSize * 1.35) + '" font-family="' + F.body + '" font-size="' + scaled.fontSize + '" font-weight="400" fill="' + T.PALETTES[0].navy + '" opacity="0.65">' +
          T.escHtml(scaled.lines[1]) + '</text>'
        : '');
  }

  /* ---- Helper: summary row with numbered circle ---- */
  function summaryRow(x, y, w, h, index, accentColor, label, value) {
    var numCx = x + 20;
    var numCy = y + h / 2;
    var labelX = x + 44;
    var labelY = y + h / 2 + 4;
    var valX = x + w - 20;
    var valY = y + h / 2 + 4;

    return '' +
      '<circle cx="' + numCx + '" cy="' + numCy + '" r="12" fill="' + accentColor + '" opacity="0.15"/>' +
      '<text x="' + numCx + '" y="' + (numCy + 4) + '" text-anchor="middle" ' +
        'font-family="' + F.body + '" font-size="11" font-weight="700" fill="' + accentColor + '">' + (index + 1) + '</text>' +
      '<text x="' + labelX + '" y="' + labelY + '" font-family="' + F.heading + '" font-size="15" font-weight="600" fill="' + T.PALETTES[0].navy + '">' +
        T.escHtml(label) + '</text>' +
      (value ? '<text x="' + valX + '" y="' + valY + '" text-anchor="end" ' +
        'font-family="' + F.heading + '" font-size="16" font-weight="700" fill="' + accentColor + '">' +
        T.escHtml(value) + '</text>' : '');
  }

  /* ========================================================================
     TEMPLATE A: Cover / Hero — dark navy editorial
     ======================================================================== */
  function templateCover(data, palette, size) {
    var w = size.w, h = size.h;
    var p = PAD.normal;
    var accent = palette.accent;
    var maxTitleW = w - 2 * p;
    var maxSubW = w - 2 * p - 100;

    var titleResult = renderTextBlock(data.title, {
      x: p, y: 220, maxWidth: maxTitleW, maxLines: 3,
      fontFamily: F.heading, fontSize: 52, fontWeight: 700, fill: "#ffffff"
    });

    var subResult = data.subtitle ? renderTextBlock(data.subtitle, {
      x: p, y: Math.max(titleResult.endY + 20, 310), maxWidth: maxSubW, maxLines: 2,
      fontFamily: F.body, fontSize: 20, fontWeight: 400, fill: "#94a3b8"
    }) : null;

    var footerY = h - p;

    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + w + ' ' + h + '">\n' +
      '  <defs>\n' +
      '    <linearGradient id="cvrBg" x1="0%" y1="0%" x2="100%" y2="100%">\n' +
      '      <stop offset="0%" stop-color="' + palette.navy + '"/>\n' +
      '      <stop offset="100%" stop-color="' + palette.navyLight + '"/>\n' +
      '    </linearGradient>\n' +
      '  </defs>\n' +
      '  <rect width="' + w + '" height="' + h + '" fill="url(#cvrBg)"/>\n' +
      '  <circle cx="920" cy="80" r="320" fill="' + accent + '" opacity="0.05"/>\n' +
      '  <circle cx="150" cy="560" r="280" fill="' + accent + '" opacity="0.03"/>\n' +
      '  <circle cx="1100" cy="480" r="180" fill="' + accent + '" opacity="0.06"/>\n' +
      '  <circle cx="600" cy="315" r="400" fill="none" stroke="' + accent + '" stroke-width="0.5" opacity="0.08"/>\n' +
      '  <rect x="' + p + '" y="' + (p - 20) + '" width="60" height="3" fill="' + accent + '" rx="1.5"/>\n' +
      '  <text x="' + p + '" y="' + (p + 10) + '" font-family="' + F.body + '" font-size="13" font-weight="600" fill="' + accent + '" letter-spacing="4">INFOGRAPHIC</text>\n' +
      T.buildIcon(T.ICONS.chart, w - p - 36, p - 20, 36, accent) +
      titleResult.svg +
      (subResult ? subResult.svg : '') +
      '  <text x="' + p + '" y="' + footerY + '" font-family="' + F.body + '" font-size="11" fill="#475569">' + T.BRAND + ' \u25C7 ' + T.BRAND_TAG + '</text>\n' +
      '  <text x="' + (w - p) + '" y="' + footerY + '" text-anchor="end" font-family="' + F.body + '" font-size="10" fill="#475569">' + new Date().toLocaleDateString("vi-VN") + '</text>\n' +
      '</svg>';
  }

  /* ========================================================================
     TEMPLATE B: KPI Cards — pastel KPI cards with icons
     ======================================================================== */
  function templateKPI(data, palette, size) {
    var w = size.w, h = size.h;
    var p = PAD.normal;
    var accent = palette.accent;
    var cardColors = [palette.cardTeal, palette.cardBlue, palette.cardPurple, palette.cardTeal];
    var cardAccents = [accent, accent, accent, accent];

    var kpis = data.kpis || [];
    if (kpis.length === 0) {
      kpis = [ { value: "\u2014", unit: "", label: "Ch\u01B0a c\u00F3 d\u1EEF li\u1EC7u", icon: "chart" } ];
    }
    kpis = kpis.slice(0, 4);

    var maxTitleW = w - 2 * p;
    var titleResult = renderTextBlock(data.title, {
      x: p, y: 140, maxWidth: maxTitleW, maxLines: 2,
      fontFamily: F.heading, fontSize: 36, fontWeight: 700,
      fill: "#0f172a"
    });

    var cardY = Math.max(titleResult.endY + 30, 200);
    var cardH = Math.min(220, h - cardY - p - 40);
    var nCards = kpis.length;
    var cardGap = 16;
    var cardW = (w - 2 * p - (nCards - 1) * cardGap) / nCards;
    var footerY = h - p;

    var cardsSvg = "";
    for (var i = 0; i < nCards; i++) {
      var cx = p + i * (cardW + cardGap);
      var ci = T.ICONS[kpis[i].icon] || T.ICONS.chart;
      cardsSvg += kpiCard(cx, cardY, cardW, cardH, cardAccents[i % cardAccents.length],
        cardColors[i % cardColors.length], ci, kpis[i].value, kpis[i].unit, kpis[i].label);
    }

    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + w + ' ' + h + '">\n' +
      '  <rect width="' + w + '" height="' + h + '" fill="#f8fafc"/>\n' +
      '  <text x="' + p + '" y="90" font-family="' + F.body + '" font-size="12" font-weight="600" fill="' + accent + '" letter-spacing="4">CH\u1EC8 S\u1ED0</text>\n' +
      titleResult.svg +
      cardsSvg +
      '  <text x="' + p + '" y="' + footerY + '" font-family="' + F.body + '" font-size="11" fill="#94a3b8">' + T.BRAND + ' \u25C7 ' + T.BRAND_TAG + '</text>\n' +
      '</svg>';
  }

  /* ========================================================================
     TEMPLATE C: Analysis — white canvas, bullet insights
     ======================================================================== */
  function templateAnalysis(data, palette, size) {
    var w = size.w, h = size.h;
    var p = PAD.normal;
    var accent = palette.accent;
    var bullets = data.bullets || [];
    if (bullets.length === 0) {
      if (data.subtitle) bullets = [data.subtitle];
      else bullets = ["N\u1ED9i dung \u0111ang \u0111\u01B0\u1EE3c c\u1EADp nh\u1EADt"];
    }
    bullets = bullets.slice(0, 5);

    var maxTitleW = w - 2 * p;
    var titleResult = renderTextBlock(data.title, {
      x: p, y: 140, maxWidth: maxTitleW, maxLines: 2,
      fontFamily: F.heading, fontSize: 32, fontWeight: 700,
      fill: "#0f172a"
    });

    var cardStartY = Math.max(titleResult.endY + 24, 190);
    var cardH = Math.min(56, (h - cardStartY - p - 20) / bullets.length);
    cardH = Math.max(cardH, 40);
    var cardGap = 10;
    var cardW = w - 2 * p;
    var icons = [T.ICONS.lightbulb, T.ICONS.trendingUp, T.ICONS.target, T.ICONS.shield, T.ICONS.star];
    var footerY = h - p;

    var cardsSvg = "";
    for (var i = 0; i < bullets.length; i++) {
      var cy = cardStartY + i * (cardH + cardGap);
      var bg = (i % 2 === 0) ? "#f8fafc" : "#ffffff";
      cardsSvg += insightCard(p, cy, cardW, cardH, accent, bg, icons[i % icons.length], bullets[i]);
    }

    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + w + ' ' + h + '">\n' +
      '  <rect width="' + w + '" height="' + h + '" fill="#ffffff"/>\n' +
      '  <rect x="0" y="0" width="' + w + '" height="3" fill="' + accent + '" opacity="0.3"/>\n' +
      '  <text x="' + p + '" y="90" font-family="' + F.body + '" font-size="12" font-weight="600" fill="' + accent + '" letter-spacing="4">PH\u00C2N T\u00CDCH</text>\n' +
      titleResult.svg +
      cardsSvg +
      '  <text x="' + p + '" y="' + footerY + '" font-family="' + F.body + '" font-size="11" fill="#94a3b8">' + T.BRAND + ' \u25C7 ' + T.BRAND_TAG + '</text>\n' +
      '</svg>';
  }

  /* ========================================================================
     TEMPLATE D: Quote / Key Insight
     ======================================================================== */
  function templateQuote(data, palette, size) {
    var w = size.w, h = size.h;
    var p = PAD.normal;
    var accent = palette.accent;

    var quoteText = data.quoteText || data.subtitle || (data.bullets ? data.bullets[0] : "") || "\u2026";
    var source = data.quoteSource || data.title || "";

    var maxQW = w - 2 * p - 60;
    var qScaled = L.scaleFont(quoteText, maxQW, 4, F.heading, 18, 38, 600, 1.3);
    var qLineH = qScaled.fontSize * qScaled.lineHeight;
    var qTotal = qScaled.lines.length * qLineH;
    var quoteY = (h - qTotal) / 2 + qScaled.fontSize;
    var sourceY = quoteY + qTotal + 30;

    var quoteSvg = "";
    for (var i = 0; i < qScaled.lines.length; i++) {
      var yPos = quoteY + i * qLineH;
      quoteSvg += '  <text x="' + (w / 2) + '" y="' + yPos + '" text-anchor="middle" ' +
        'font-family="' + F.heading + '" font-size="' + qScaled.fontSize + '" font-weight="600" fill="#0f172a">' +
        T.escHtml(qScaled.lines[i]) + '</text>\n';
    }

    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + w + ' ' + h + '">\n' +
      '  <rect width="' + w + '" height="' + h + '" fill="#f8fafc"/>\n' +
      '  <rect x="' + (w/2 - 40) + '" y="60" width="80" height="3" fill="' + accent + '" rx="1.5"/>\n' +
      '  <text x="' + (w / 2) + '" y="110" text-anchor="middle" font-family="Georgia,serif" font-size="80" fill="' + accent + '" opacity="0.2">\u201C</text>\n' +
      quoteSvg +
      (source ? '  <text x="' + (w / 2) + '" y="' + sourceY + '" text-anchor="middle" ' +
        'font-family="' + F.body + '" font-size="14" fill="#94a3b8">\u2014 ' + T.escHtml(source) + '</text>\n' : '') +
      '  <text x="' + p + '" y="' + (h - p) + '" font-family="' + F.body + '" font-size="11" fill="#cbd5e1">' + T.BRAND + ' \u25C7 ' + T.BRAND_TAG + '</text>\n' +
      '</svg>';
  }

  /* ========================================================================
     TEMPLATE E: Summary — dark header + white body summary rows
     ======================================================================== */
  function templateSummary(data, palette, size) {
    var w = size.w, h = size.h;
    var p = PAD.normal;
    var accent = palette.accent;
    var headerH = 130;

    var summaryRows = data.summaryRows || [];
    if (summaryRows.length === 0) {
      var bullets = data.bullets || [];
      if (bullets.length > 0) {
        summaryRows = bullets.map(function (b) { return { label: b, value: "" }; });
      } else {
        summaryRows = [{ label: "Ch\u01B0a c\u00F3 n\u1ED9i dung t\u00F3m t\u1EAFt", value: "" }];
      }
    }
    summaryRows = summaryRows.slice(0, 6);

    var maxTitleW = w - 2 * p - 200;
    var titleScaled = L.scaleFont(data.title, maxTitleW, 1, F.heading, 14, 24, 700, 1.2);
    var titleY = headerH / 2 + 5;

    var rowsY = headerH + 30;
    var rowH = Math.min(50, (h - rowsY - p - 20) / summaryRows.length);
    rowH = Math.max(rowH, 34);
    var rowGap = 6;
    var rowW = w - 2 * p;
    var footerY = h - p;

    var rowsSvg = "";
    for (var i = 0; i < summaryRows.length; i++) {
      var ry = rowsY + i * (rowH + rowGap);
      rowsSvg += summaryRow(p, ry, rowW, rowH, i, accent, summaryRows[i].label, summaryRows[i].value);
      if (i < summaryRows.length - 1) {
        var sepY = ry + rowH + rowGap / 2;
        rowsSvg += '  <line x1="' + (p + 44) + '" y1="' + sepY + '" x2="' + (w - p) + '" y2="' + sepY + '" stroke="#e2e8f0" stroke-width="1"/>\n';
      }
    }

    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + w + ' ' + h + '">\n' +
      '  <rect width="' + w + '" height="' + headerH + '" fill="' + palette.navy + '"/>\n' +
      '  <text x="' + p + '" y="50" font-family="' + F.body + '" font-size="11" font-weight="600" fill="' + accent + '" letter-spacing="4">T\u00D3M T\u1EAET</text>\n' +
      (titleScaled.lines.length > 0
        ? '  <text x="' + p + '" y="' + titleY + '" font-family="' + F.heading + '" font-size="' + titleScaled.fontSize + '" font-weight="700" fill="#ffffff">' +
          T.escHtml(titleScaled.lines[0]) + '</text>\n'
        : '') +
      T.buildIcon(T.ICONS.document, w - p - 40, headerH / 2 - 18, 36, accent) +
      '  <rect x="0" y="' + headerH + '" width="' + w + '" height="' + (h - headerH) + '" fill="#ffffff"/>\n' +
      rowsSvg +
      '  <text x="' + p + '" y="' + footerY + '" font-family="' + F.body + '" font-size="11" fill="#94a3b8">' + T.BRAND + ' \u25C7 ' + T.BRAND_TAG + '</text>\n' +
      '</svg>';
  }

  /* ========================================================================
     TEMPLATE F: Banner — oversized headline, abstract, minimal
     ======================================================================== */
  function templateBanner(data, palette, size) {
    var w = size.w, h = size.h;
    var p = PAD.compact;
    var accent = palette.accent;

    var maxTitleW = w - 2 * p - 80;
    var titleResult = renderTextBlock(data.title, {
      x: p + 40, y: h * 0.5 + 10, maxWidth: maxTitleW, maxLines: 2,
      fontFamily: F.heading, fontSize: 56, fontWeight: 800, fill: "#ffffff"
    });

    var subResult = data.subtitle ? renderTextBlock(data.subtitle, {
      x: p + 40, y: Math.min(titleResult.endY + 16, h - 50), maxWidth: maxTitleW * 0.6, maxLines: 1,
      fontFamily: F.body, fontSize: 18, fontWeight: 400, fill: "#94a3b8"
    }) : null;

    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + w + ' ' + h + '">\n' +
      '  <defs>\n' +
      '    <linearGradient id="banBg" x1="0%" y1="0%" x2="100%" y2="100%">\n' +
      '      <stop offset="0%" stop-color="' + palette.navy + '"/>\n' +
      '      <stop offset="100%" stop-color="' + palette.navyLight + '"/>\n' +
      '    </linearGradient>\n' +
      '  </defs>\n' +
      '  <rect width="' + w + '" height="' + h + '" fill="url(#banBg)"/>\n' +
      '  <circle cx="' + (w - 100) + '" cy="80" r="250" fill="' + accent + '" opacity="0.04"/>\n' +
      '  <circle cx="120" cy="' + (h - 80) + '" r="200" fill="' + accent + '" opacity="0.03"/>\n' +
      '  <circle cx="' + (w / 2) + '" cy="' + (h / 2) + '" r="350" fill="none" stroke="' + accent + '" stroke-width="0.5" opacity="0.06"/>\n' +
      '  <text x="' + (p + 40) + '" y="' + (p + 20) + '" font-family="' + F.body + '" font-size="12" font-weight="600" fill="' + accent + '" letter-spacing="5">INFOGRAPHIC</text>\n' +
      titleResult.svg +
      (subResult ? subResult.svg : '') +
      '  <text x="' + (p + 40) + '" y="' + (h - p) + '" font-family="' + F.body + '" font-size="11" fill="#475569">' + T.BRAND + ' \u25C7 ' + T.BRAND_TAG + '</text>\n' +
      '</svg>';
  }

  /* ---- Templates registry ---- */
  var TEMPLATES = {
    cover:    { fn: templateCover,    label: "Cover",    desc: "B\u00ECa ch\u00EDnh" },
    kpi:      { fn: templateKPI,      label: "KPI",      desc: "Ch\u1EC9 s\u1ED1" },
    analysis: { fn: templateAnalysis, label: "Analysis", desc: "Ph\u00E2n t\u00EDch" },
    quote:    { fn: templateQuote,    label: "Quote",    desc: "Tr\u00EDch d\u1EABn" },
    summary:  { fn: templateSummary,  label: "Summary",  desc: "T\u00F3m t\u1EAFt" },
    banner:   { fn: templateBanner,   label: "Banner",   desc: "Banner" }
  };

  /* ---- Auto-select best template based on input data ---- */
  function autoSelectTemplate(data) {
    var hasKPI = data.kpis && data.kpis.length > 0;
    var hasBullets = data.bullets && data.bullets.length >= 3;
    var hasQuote = data.quoteText && data.quoteText.length > 0;
    var hasSummary = data.summaryRows && data.summaryRows.length > 0;
    var titleLen = (data.title || "").length;

    if (hasQuote) return "quote";
    if (hasKPI) return "kpi";
    if (hasSummary) return "summary";
    if (hasBullets) return "analysis";
    if (titleLen > 80) return "analysis";
    return "cover";
  }

  /* ---- Extract structure from raw text input ---- */
  function parseInput(title, subtitle, content, kpiValues, quoteSource) {
    var data = { title: title || "", subtitle: subtitle || "" };

    // Extract bullets from content
    if (content) {
      var lines = content.split("\n").map(function (l) {
        return l.replace(/^[-*\u2022]\s*/, "").replace(/^#+\s*/, "").trim();
      }).filter(Boolean);
      if (lines.length >= 2) {
        data.bullets = lines.slice(0, 5);
      } else {
        // Split by sentence
        var sentences = content.match(/[^.!?\n]+[.!?]+/g) || [content];
        data.bullets = sentences.map(function (s) { return s.trim(); }).filter(Boolean).slice(0, 5);
      }
    }

    // Parse KPI values if provided
    if (kpiValues && kpiValues.length > 0) {
      data.kpis = kpiValues;
    }

    // Quote source
    if (quoteSource) {
      data.quoteSource = quoteSource;
    }
    if (quoteSource || subtitle) {
      // Use first bullet as quote text if no explicit quote
      if (data.bullets && data.bullets.length > 0) {
        data.quoteText = data.bullets[0];
      }
    }

    // Summary rows (use bullets)
    if (data.bullets && data.bullets.length > 0) {
      data.summaryRows = data.bullets.map(function (b) { return { label: b, value: "" }; });
    }

    return data;
  }

  /* ---- Generate SVG for given template + data ---- */
  function generate(templateId, data, palette, size) {
    var tmpl = TEMPLATES[templateId];
    if (!tmpl) return null;
    var svg = tmpl.fn(data, palette, size);
    return svg;
  }

  /* ---- Generate all templates for gallery ---- */
  function generateAll(data, palette, size) {
    var results = [];
    for (var id in TEMPLATES) {
      if (TEMPLATES.hasOwnProperty(id)) {
        var svg = TEMPLATES[id].fn(data, palette, size);
        results.push({ id: id, label: TEMPLATES[id].label, desc: TEMPLATES[id].desc, svg: svg });
      }
    }
    return results;
  }

  return {
    TEMPLATES:        TEMPLATES,
    autoSelectTemplate: autoSelectTemplate,
    parseInput:         parseInput,
    generate:           generate,
    generateAll:        generateAll
  };
})();
