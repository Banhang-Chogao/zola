/* ============================================================================
   sdna-tokens.js — S-DNA Design Tokens + Icon System
   Shared constants for the infographic generator.
   ============================================================================ */

var SDNA = SDNA || {};

SDNA.Tokens = (function () {
  "use strict";

  /* ---- S-DNA Palette (5 themes matching _editor-sdna.scss) ---- */
  var PALETTES = [
    { id: "teal",   label: "Teal",    navy: "#0f172a", navyLight: "#1e293b",
      accent: "#00a7a0", accentSoft: "#ddf4f2", accentGlow: "rgba(0,167,160,0.12)",
      cardTeal: "#ddf4f2", cardBlue: "#dceaf8", cardPurple: "#ece7fa" },
    { id: "blue",   label: "Blue",    navy: "#0f172a", navyLight: "#1e293b",
      accent: "#5b9bd5", accentSoft: "#dceaf8", accentGlow: "rgba(91,155,213,0.12)",
      cardTeal: "#ddf4f2", cardBlue: "#dceaf8", cardPurple: "#ece7fa" },
    { id: "purple", label: "Purple",  navy: "#0f172a", navyLight: "#1e293b",
      accent: "#9b8fd4", accentSoft: "#ece7fa", accentGlow: "rgba(155,143,212,0.12)",
      cardTeal: "#ddf4f2", cardBlue: "#dceaf8", cardPurple: "#ece7fa" },
    { id: "amber",  label: "Amber",   navy: "#0f172a", navyLight: "#1e293b",
      accent: "#e8a838", accentSoft: "#fdf3e0", accentGlow: "rgba(232,168,56,0.12)",
      cardTeal: "#ddf4f2", cardBlue: "#dceaf8", cardPurple: "#ece7fa" },
    { id: "green",  label: "Green",   navy: "#0f172a", navyLight: "#1e293b",
      accent: "#3fa66a", accentSoft: "#e0f2e8", accentGlow: "rgba(63,166,106,0.12)",
      cardTeal: "#ddf4f2", cardBlue: "#dceaf8", cardPurple: "#ece7fa" }
  ];

  /* ---- Export canvas sizes ---- */
  var SIZES = {
    cover:  { w: 1200, h: 630,  label: "Cover (1200×630)" },
    square: { w: 1080, h: 1080, label: "Square (1080×1080)" },
    banner: { w: 1600, h: 900,  label: "Banner (1600×900)" }
  };

  /* ---- Safe padding (in SVG units) ---- */
  var PAD = { normal: 72, compact: 48 };

  /* ---- Font stacks ---- */
  var FONTS = {
    heading: "'IBM Plex Sans','Inter',system-ui,-apple-system,sans-serif",
    body:    "'Inter',system-ui,-apple-system,'Segoe UI',sans-serif",
    mono:    "'JetBrains Mono','Fira Code',monospace"
  };

  /* ---- Brand mark ---- */
  var BRAND = "SEOMONEY";
  var BRAND_TAG = "S-DNA";

  /* ========================================================================
     Outline icon system — 20 icons in 24×24 coordinate space.
     Each function returns SVG child elements for the icon shape.
     The caller wraps them in a circle container.
     Style: thin stroke (1.5–1.75), round caps/joins, no fill.
     ======================================================================== */
  var ICON_SIZE = 24;

  function _s(n) { return n; } // identity — helps readability

  function _iconRect(w, h, x, y) {
    return '<rect x="' + x + '" y="' + y + '" width="' + w + '" height="' + h + '" rx="2" fill="none" stroke="currentColor" stroke-width="1.6"/>';
  }
  function _iconLine(x1, y1, x2, y2) {
    return '<line x1="' + x1 + '" y1="' + y1 + '" x2="' + x2 + '" y2="' + y2 + '" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>';
  }
  function _iconCircle(cx, cy, r) {
    return '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="none" stroke="currentColor" stroke-width="1.6"/>';
  }
  function _iconPoly(points) {
    return '<polyline points="' + points + '" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>';
  }
  function _iconPath(d) {
    return '<path d="' + d + '" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>';
  }

  var ICONS = {
    /* 1. Bar chart — 3 bars */
    chart: function () {
      return _iconRect(5, 12, 3, 9) + _iconRect(5, 16, 9.5, 5) + _iconRect(5, 8, 16, 13);
    },
    /* 2. Line chart — ascending line */
    chartLine: function () {
      return _iconPoly("3,18 8,12 13,15 21,6");
    },
    /* 3. Pie chart — circle with wedges */
    pie: function () {
      return _iconCircle(12, 12, 9) + _iconLine(12, 12, 12, 3) + _iconLine(12, 12, 19, 8);
    },
    /* 4. Target / bullseye */
    target: function () {
      return _iconCircle(12, 12, 9) + _iconCircle(12, 12, 5) + _iconCircle(12, 12, 2);
    },
    /* 5. Lightbulb */
    lightbulb: function () {
      return _iconPath("M12,3a7,7,0,0,0-4,12.7,5,5,0,0,0,8,0A7,7,0,0,0,12,3Z") +
        _iconLine(10, 17, 14, 17) + _iconLine(11, 20, 13, 20);
    },
    /* 6. Star */
    star: function () {
      return _iconPath("M12,3l2.5,5.1L20,9l-4,3.9L17,20l-5-2.6L7,20l1-7.1L4,9l5.5-.9Z");
    },
    /* 7. Diamond */
    diamond: function () {
      return _iconPath("M12,3L21,12L12,21L3,12Z");
    },
    /* 8. Shield */
    shield: function () {
      return _iconPath("M12,3L3,6v5c0,5,3.9,9.8,9,11c5.1-1.2,9-6,9-11V6L12,3Z");
    },
    /* 9. Document */
    document: function () {
      return _iconPath("M6,3h8l6,6v12a1,1,0,0,1-1,1H6a1,1,0,0,1-1-1V4A1,1,0,0,1,6,3Z") +
        _iconPoly("14,3 14,9 20,9");
    },
    /* 10. Folder */
    folder: function () {
      return _iconPath("M3,7v11a2,2,0,0,0,2,2h14a2,2,0,0,0,2-2V9a2,2,0,0,0-2-2h-7L9,5H5A2,2,0,0,0,3,7Z");
    },
    /* 11. Globe */
    globe: function () {
      return _iconCircle(12, 12, 9) + _iconPath("M3,12h18M12,3a15,15,0,0,1,0,18a15,15,0,0,1,0-18Z");
    },
    /* 12. Users */
    users: function () {
      return _iconCircle(9, 8, 3.5) + _iconCircle(17, 8, 3.5) +
        _iconPath("M3,21v-2a5,5,0,0,1,5-5h2") +
        _iconPath("M15,14h2a5,5,0,0,1,5,5v2");
    },
    /* 13. Clock */
    clock: function () {
      return _iconCircle(12, 12, 9) + _iconLine(12, 8, 12, 12) + _iconLine(12, 12, 15.5, 13.5);
    },
    /* 14. Trending up */
    trendingUp: function () {
      return _iconPoly("3,17 9,11 14,14 21,7") + _iconPoly("15,7 21,7 21,13");
    },
    /* 15. Database */
    database: function () {
      return _iconPath("M4,7c0-2.2,3.6-4,8-4s8,1.8,8,4") +
        _iconPath("M4,7v4c0,2.2,3.6,4,8,4s8-1.8,8-4V7") +
        _iconPath("M4,11v4c0,2.2,3.6,4,8,4s8-1.8,8-4V11");
    },
    /* 16. Settings / Gear */
    settings: function () {
      return _iconCircle(12, 12, 3) +
        _iconPath("M12,1v3M12,20v3M1,12h3M20,12h3M4.2,4.2l2.1,2.1M17.7,17.7l2.1,2.1M4.2,19.8l2.1-2.1M17.7,6.3l2.1-2.1");
    },
    /* 17. Email / envelope */
    email: function () {
      return _iconPath("M4,5h16a1,1,0,0,1,1,1v12a1,1,0,0,1-1,1H4a1,1,0,0,1-1-1V6A1,1,0,0,1,4,5Z") +
        _iconPoly("4,6 12,13 20,6");
    },
    /* 18. Lock */
    lock: function () {
      return _iconPath("M8,11V7a4,4,0,0,1,8,0v4") +
        _iconRect(8, 8, 4, 11, 2) +
        _iconCircle(12, 14.5, 1.5);
    },
    /* 19. Download */
    download: function () {
      return _iconLine(12, 3, 12, 15) + _iconPoly("8,11 12,15 16,11") +
        _iconLine(4, 19, 20, 19);
    },
    /* 20. Search / magnifying glass */
    search: function () {
      return _iconCircle(10, 10, 7) + _iconLine(15, 15, 21, 21);
    }
  };

  /* ---- Helpers ---- */
  function getPalette(index) {
    return PALETTES[index % PALETTES.length];
  }

  function getPaletteById(id) {
    return PALETTES.filter(function (p) { return p.id === id; })[0] || PALETTES[0];
  }

  function randomPalette(seed) {
    var idx = (typeof seed === 'number') ? Math.abs(Math.floor(seed)) % PALETTES.length
                                         : Math.floor(Math.random() * PALETTES.length);
    return PALETTES[idx];
  }

  /* ---- Build a complete icon group (circle container + shape) ---- */
  function buildIcon(iconFn, cx, cy, size, color) {
    if (!iconFn) return '';
    var r = size / 2;
    var pad = 1.5;
    var circleR = r - pad;
    // Scale coordinates: icon is defined in 24×24 space, we scale it to size-6
    var innerSize = size - 6; // leave 3px padding each side
    var scale = innerSize / ICON_SIZE;
    var ox = (size - innerSize) / 2;
    var oy = (size - innerSize) / 2;
    var iconSvg = iconFn();
    return '<g transform="translate(' + cx + ',' + cy + ')">' +
      '<circle cx="' + r + '" cy="' + r + '" r="' + circleR + '" fill="none" stroke="' + color + '" stroke-width="1.5"/>' +
      '<g transform="translate(' + ox + ',' + oy + ') scale(' + scale + ')">' +
      iconSvg +
      '</g>' +
      '</g>';
  }

  /* ---- Build a small accent bar (colored left accent) ---- */
  function accentBar(x, y, w, h, color) {
    return '<rect x="' + x + '" y="' + y + '" width="' + w + '" height="' + h + '" fill="' + color + '" rx="2"/>';
  }

  /* ---- Safe base64/encoding for SVG ---- */
  function escHtml(s) {
    if (!s) return '';
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  /* ================================================================
     Seeded pseudo-random number generator (Mulberry32)
     Deterministic — given same seed, produces same sequence.
     ================================================================ */
  function mulberry32(a) {
    return function () {
      a |= 0; a = a + 0x6D2B79F5 | 0;
      var t = Math.imul(a ^ a >>> 15, 1 | a);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }

  return {
    PALETTES:    PALETTES,
    SIZES:       SIZES,
    PAD:         PAD,
    FONTS:       FONTS,
    BRAND:       BRAND,
    BRAND_TAG:   BRAND_TAG,
    ICON_SIZE:   ICON_SIZE,
    ICONS:       ICONS,
    getPalette:      getPalette,
    getPaletteById:  getPaletteById,
    randomPalette:   randomPalette,
    buildIcon:       buildIcon,
    accentBar:       accentBar,
    escHtml:         escHtml,
    mulberry32:      mulberry32
  };
})();
