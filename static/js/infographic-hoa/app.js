(function (global) {
  "use strict";

  var BRAND = "SEOMONEY";
  var BRAND_TAG = "S-DNA \u25C7";

  function el(id) { return document.getElementById(id); }
  function qs(s, p) { return (p || document).querySelector(s); }
  function qsa(s, p) { return (p || document).querySelectorAll(s); }

  function escHtml(s) {
    if (!s) return "";
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  function escAttr(s) { return escHtml(s).replace(/"/g, "&quot;"); }

  function shorten(s, max) {
    if (!s) return "";
    return s.length > max ? s.slice(0, max) + "\u2026" : s;
  }

  function extractBullets(text) {
    if (!text) return [];
    var lines = text.split("\n").map(function (l) { return l.replace(/^[-*]\s*/, "").replace(/^#+\s*/, "").trim(); }).filter(Boolean);
    if (lines.length < 3) {
      lines = text.match(/[^.!?]+[.!?]+/g) || [text];
      lines = lines.map(function (l) { return l.trim(); }).filter(Boolean);
    }
    return lines.slice(0, 6);
  }

  function wrapSvgText(svg, text, x, y, maxWidth, lineHeight, maxLines, color, fontSize, fontWeight) {
    var words = text.split("");
    var lines = [];
    var current = "";
    for (var i = 0; i < words.length; i++) {
      var test = current + words[i];
      svg += '      <text x="' + x + '" y="' + y + '" font-family="system-ui,sans-serif" font-size="' + fontSize + '" font-weight="' + (fontWeight || 400) + '" fill="' + color + '">' + escHtml(current) + '</text>\n';
      current = words[i];
      y += lineHeight;
    }
    return { svg: svg, linesCount: 1, y: y };
  }

  function wordWrap(text, maxChars) {
    var words = text.split(" ");
    var lines = [];
    var current = "";
    for (var i = 0; i < words.length; i++) {
      if ((current + " " + words[i]).trim().length <= maxChars) {
        current = (current + " " + words[i]).trim();
      } else {
        if (current) lines.push(current);
        current = words[i];
      }
    }
    if (current) lines.push(current);
    return lines;
  }

  function generateCoverSVG(title, description) {
    var w = 800, h = 500;
    var bg = "#0f172a";
    var accent = "#38bdf8";
    var textColor = "#ffffff";

    var titleLines = wordWrap(title || "Infographic", 35);
    var desc = description ? shorten(description, 120) : "";

    var y = 180;
    var titleSvg = "";
    titleLines.slice(0, 3).forEach(function (line) {
      titleSvg += '    <text x="400" y="' + y + '" text-anchor="middle" font-family="system-ui,sans-serif" font-size="36" font-weight="700" fill="' + textColor + '">' + escHtml(line) + '</text>\n';
      y += 46;
    });

    return '<svg xmlns="http://www.w3.org/2000/svg" width="' + w + '" height="' + h + '" viewBox="0 0 ' + w + ' ' + h + '">\n' +
      '  <defs>\n' +
      '    <linearGradient id="cover-bg" x1="0%" y1="0%" x2="100%" y2="100%">\n' +
      '      <stop offset="0%" stop-color="#0f172a"/>\n' +
      '      <stop offset="100%" stop-color="#1e293b"/>\n' +
      '    </linearGradient>\n' +
      '  </defs>\n' +
      '  <rect width="' + w + '" height="' + h + '" fill="url(#cover-bg)"/>\n' +
      '  <circle cx="680" cy="80" r="180" fill="' + accent + '" opacity="0.08"/>\n' +
      '  <circle cx="120" cy="420" r="140" fill="' + accent + '" opacity="0.06"/>\n' +
      '  <line x1="50" y1="100" x2="200" y2="100" stroke="' + accent + '" stroke-width="3" opacity="0.5"/>\n' +
      '  <text x="400" y="140" text-anchor="middle" font-family="system-ui,sans-serif" font-size="14" font-weight="600" fill="' + accent + '" letter-spacing="4">INFOGRAPHIC</text>\n' +
      titleSvg +
      (desc ? '    <text x="400" y="' + (y + 30) + '" text-anchor="middle" font-family="system-ui,sans-serif" font-size="15" fill="#94a3b8">' + escHtml(desc) + '</text>\n' : '') +
      '  <text x="400" y="460" text-anchor="middle" font-family="system-ui,sans-serif" font-size="11" fill="#475569">' + BRAND + ' \u25C7 ' + BRAND_TAG + '</text>\n' +
      '</svg>';
  }

  function generateQuoteSVG(title, content) {
    var w = 600, h = 500;
    var quote = shorten(content || title || "", 200);
    var source = title || "Infographic";

    return '<svg xmlns="http://www.w3.org/2000/svg" width="' + w + '" height="' + h + '" viewBox="0 0 ' + w + ' ' + h + '">\n' +
      '  <rect width="' + w + '" height="' + h + '" fill="#ffffff"/>\n' +
      '  <rect x="0" y="0" width="8" height="' + h + '" fill="#38bdf8"/>\n' +
      '  <text x="60" y="100" font-family="Georgia,serif" font-size="72" fill="#38bdf8" opacity="0.3">\u201C</text>\n' +
      '  <text x="60" y="180" font-family="system-ui,sans-serif" font-size="22" font-weight="600" fill="#0f172a" width="480">' + escHtml(shorten(quote, 150)) + '</text>\n' +
      '  <text x="60" y="420" font-family="system-ui,sans-serif" font-size="14" fill="#64748b">\u2014 ' + escHtml(shorten(source, 60)) + '</text>\n' +
      '  <text x="60" y="460" font-family="system-ui,sans-serif" font-size="10" fill="#cbd5e1">' + BRAND + ' \u25C7 ' + BRAND_TAG + '</text>\n' +
      '</svg>';
  }

  function generateInsightSVG(title, content) {
    var w = 800, h = 500;
    var bullets = extractBullets(content || "");
    if (bullets.length === 0) bullets = ["N\u1ED9i dung ch\u01B0a \u0111\u01B0\u1EE3c nh\u1EADp"];

    var bulletSvg = "";
    var by = 155;
    bullets.slice(0, 5).forEach(function (b) {
      var lines = wordWrap(b, 55);
      lines.slice(0, 2).forEach(function (line) {
        bulletSvg += '    <text x="80" y="' + by + '" font-family="system-ui,sans-serif" font-size="13" fill="#334155">\u2022 ' + escHtml(line) + '</text>\n';
        by += 22;
      });
    });

    return '<svg xmlns="http://www.w3.org/2000/svg" width="' + w + '" height="' + h + '" viewBox="0 0 ' + w + ' ' + h + '">\n' +
      '  <rect width="' + w + '" height="' + h + '" fill="#f8fafc"/>\n' +
      '  <rect x="0" y="0" width="' + w + '" height="4" fill="url(#insight-accent)"/>\n' +
      '  <defs>\n' +
      '    <linearGradient id="insight-accent" x1="0%" y1="0%" x2="100%" y2="0%">\n' +
      '      <stop offset="0%" stop-color="#38bdf8"/>\n' +
      '      <stop offset="100%" stop-color="#1d4ed8"/>\n' +
      '    </linearGradient>\n' +
      '  </defs>\n' +
      '  <text x="40" y="55" font-family="system-ui,sans-serif" font-size="11" font-weight="600" fill="#38bdf8" letter-spacing="3">PH\u00C2N T\u00CDCH</text>\n' +
      '  <text x="40" y="85" font-family="system-ui,sans-serif" font-size="20" font-weight="700" fill="#0f172a">' + escHtml(shorten(title || "Infographic", 60)) + '</text>\n' +
      '  <line x1="40" y1="105" x2="180" y2="105" stroke="#e2e8f0" stroke-width="2"/>\n' +
      bulletSvg +
      '  <text x="40" y="470" font-family="system-ui,sans-serif" font-size="10" fill="#94a3b8">' + BRAND + ' \u25C7 ' + BRAND_TAG + '</text>\n' +
      '</svg>';
  }

  function generateSummarySVG(title, content) {
    var w = 800, h = 500;
    var bullets = extractBullets(content || "");
    if (bullets.length === 0) bullets = ["Ch\u01B0a c\u00F3 n\u1ED9i dung"];

    var bulletSvg = "";
    var by = 155;
    bullets.slice(0, 5).forEach(function (b) {
      var lines = wordWrap(b, 50);
      lines.slice(0, 2).forEach(function (line) {
        var num = bullets.indexOf(b) + 1;
        bulletSvg += '    <circle cx="55" cy="' + (by - 5) + '" r="10" fill="#38bdf8" opacity="0.15"/>\n';
        bulletSvg += '    <text x="55" y="' + (by + 2) + '" text-anchor="middle" font-family="system-ui,sans-serif" font-size="11" font-weight="700" fill="#0284c7">' + num + '</text>\n';
        bulletSvg += '    <text x="80" y="' + by + '" font-family="system-ui,sans-serif" font-size="13" fill="#334155">' + escHtml(line) + '</text>\n';
        by += 26;
      });
    });

    return '<svg xmlns="http://www.w3.org/2000/svg" width="' + w + '" height="' + h + '" viewBox="0 0 ' + w + ' ' + h + '">\n' +
      '  <rect width="' + w + '" height="' + h + '" fill="#ffffff"/>\n' +
      '  <rect x="0" y="0" width="' + w + '" height="120" fill="#0f172a"/>\n' +
      '  <text x="40" y="45" font-family="system-ui,sans-serif" font-size="11" font-weight="600" fill="#38bdf8" letter-spacing="3">T\u1ED4NG K\u1EBET</text>\n' +
      '  <text x="40" y="80" font-family="system-ui,sans-serif" font-size="22" font-weight="700" fill="#ffffff">' + escHtml(shorten(title || "Infographic", 50)) + '</text>\n' +
      bulletSvg +
      '  <text x="40" y="475" font-family="system-ui,sans-serif" font-size="10" fill="#94a3b8">' + BRAND + ' \u25C7 ' + BRAND_TAG + '</text>\n' +
      '</svg>';
  }

  function generateBannerSVG(title) {
    var w = 800, h = 200;
    return '<svg xmlns="http://www.w3.org/2000/svg" width="' + w + '" height="' + h + '" viewBox="0 0 ' + w + ' ' + h + '">\n' +
      '  <rect width="' + w + '" height="' + h + '" fill="url(#banner-bg)"/>\n' +
      '  <defs>\n' +
      '    <linearGradient id="banner-bg" x1="0%" y1="0%" x2="100%" y2="0%">\n' +
      '      <stop offset="0%" stop-color="#1e293b"/>\n' +
      '      <stop offset="100%" stop-color="#0f172a"/>\n' +
      '    </linearGradient>\n' +
      '  </defs>\n' +
      '  <circle cx="700" cy="100" r="120" fill="#38bdf8" opacity="0.06"/>\n' +
      '  <text x="50" y="65" font-family="system-ui,sans-serif" font-size="13" font-weight="600" fill="#38bdf8" letter-spacing="3">INFOGRAPHIC</text>\n' +
      '  <text x="50" y="110" font-family="system-ui,sans-serif" font-size="26" font-weight="700" fill="#ffffff">' + escHtml(shorten(title || "Infographic", 70)) + '</text>\n' +
      '  <text x="50" y="175" font-family="system-ui,sans-serif" font-size="10" fill="#475569">' + BRAND + ' \u25C7 ' + BRAND_TAG + '</text>\n' +
      '</svg>';
  }

  function svgToBlobURL(svg) {
    var blob = new Blob([svg], { type: "image/svg+xml;charset=utf-8" });
    return URL.createObjectURL(blob);
  }

  function svgToDataURL(svg) {
    return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
  }

  function downloadURL(url, filename) {
    var a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }

  function downloadPNG(svg, filename) {
    var img = new Image();
    var canvas = document.createElement("canvas");
    var ctx = canvas.getContext("2d");
    var svgBlob = new Blob([svg], { type: "image/svg+xml;charset=utf-8" });
    var url = URL.createObjectURL(svgBlob);

    img.onload = function () {
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      ctx.drawImage(img, 0, 0);
      canvas.toBlob(function (blob) {
        if (blob) {
          var blobUrl = URL.createObjectURL(blob);
          downloadURL(blobUrl, filename.replace(/\.svg$/i, ".png"));
          URL.revokeObjectURL(blobUrl);
        }
      }, "image/png");
      URL.revokeObjectURL(url);
    };
    img.src = url;
  }

  var generators = [
    { type: "cover",     label: "Cover",       fn: generateCoverSVG },
    { type: "quote",     label: "Tr\u00EDch d\u1EABn", fn: generateQuoteSVG },
    { type: "insight",   label: "Ph\u00E2n t\u00EDch", fn: generateInsightSVG },
    { type: "summary",   label: "T\u1ED5ng k\u1EBFt",   fn: generateSummarySVG },
    { type: "banner",    label: "Banner",      fn: generateBannerSVG },
  ];

  var generatedImages = [];

  function renderGallery(title, description, content) {
    var panel = el("ih-result-panel");
    panel.hidden = false;

    var gallery = el("ih-gallery");
    gallery.innerHTML = "";

    var group = document.createElement("div");
    group.className = "ih-gallery__grid";

    generators.forEach(function (gen) {
      var svg = gen.fn(title, description || content);
      var svgUrl = svgToDataURL(svg);

      var card = document.createElement("div");
      card.className = "ih-gallery__card";

      var preview = document.createElement("div");
      preview.className = "ih-gallery__preview";
      var img = document.createElement("img");
      img.src = svgUrl;
      img.alt = gen.label + " infographic";
      img.loading = "lazy";
      img.decoding = "async";
      img.width = 400;
      img.height = 250;
      preview.appendChild(img);

      var meta = document.createElement("div");
      meta.className = "ih-gallery__meta";
      meta.innerHTML = '<span class="ih-gallery__type">' + gen.label + '</span><span class="ih-gallery__palette">SVG</span>';

      var actions = document.createElement("div");
      actions.className = "ih-gallery__actions";
      var svgBtn = document.createElement("button");
      svgBtn.className = "ih-btn ih-btn--sm ih-btn--ghost";
      svgBtn.textContent = "SVG";
      svgBtn.addEventListener("click", function () {
        var url = svgToDataURL(svg);
        downloadURL(url, "infographic-" + gen.type + ".svg");
      });
      var pngBtn = document.createElement("button");
      pngBtn.className = "ih-btn ih-btn--sm ih-btn--outline";
      pngBtn.textContent = "PNG";
      pngBtn.addEventListener("click", function () {
        downloadPNG(svg, "infographic-" + gen.type + ".svg");
      });

      actions.appendChild(svgBtn);
      actions.appendChild(pngBtn);

      card.appendChild(preview);
      card.appendChild(meta);
      card.appendChild(actions);
      group.appendChild(card);

      generatedImages.push({ type: gen.type, svg: svg, svgUrl: svgUrl });
    });

    gallery.appendChild(group);

    var downloadAllBtn = document.createElement("div");
    downloadAllBtn.className = "ih-gallery__all";
    downloadAllBtn.innerHTML = '<button type="button" class="ih-btn ih-btn--primary" id="ih-download-all"><span aria-hidden="true">\u2B07</span> T\u1EA3i xu\u1ED1ng t\u1EA5t c\u1EA3 PNG</button>';
    gallery.appendChild(downloadAllBtn);

    el("ih-download-all").addEventListener("click", function () {
      generatedImages.forEach(function (gi) {
        downloadPNG(gi.svg, "infographic-" + gi.type + ".svg");
      });
    });
  }

  function onSubmit(e) {
    e.preventDefault();

    var title = el("ih-title").value.trim();
    var description = el("ih-description").value.trim();
    var content = el("ih-content").value.trim();

    if (!title) {
      el("ih-title").focus();
      return;
    }

    var submitBtn = el("ih-submit");
    submitBtn.disabled = true;
    submitBtn.textContent = "\u25B6 \u0110ang t\u1EA1o\u2026";

    var progress = el("ih-progress");
    progress.hidden = false;
    el("ih-progress-bar").style.width = "20%";
    el("ih-progress-text").textContent = "\u0110ang t\u1EA1o infographic\u2026";

    setTimeout(function () {
      el("ih-progress-bar").style.width = "60%";
    }, 100);

    setTimeout(function () {
      generatedImages = [];
      renderGallery(title, description, content);
      el("ih-progress-bar").style.width = "100%";
      el("ih-progress-text").textContent = "Ho\u00E0n t\u1EA5t!";

      submitBtn.disabled = false;
      submitBtn.textContent = "\u25C6 T\u1EA1o infographic";

      setTimeout(function () {
        progress.hidden = true;
        el("ih-progress-bar").style.width = "0%";
        el("ih-progress-bar").style.background = "";
      }, 2000);
    }, 400);
  }

  function init() {
    var form = el("ih-form");
    if (form) form.addEventListener("submit", onSubmit);
  }

  document.addEventListener("DOMContentLoaded", init);
})(window);
