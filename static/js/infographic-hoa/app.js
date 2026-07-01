/* ============================================================================
   app.js — INFographic hoá S-DNA infographic generator
   Full editor with template selector, preview, export.
   Depends on: sdna-tokens.js, sdna-layout.js, sdna-templates.js, sdna-export.js
   ============================================================================ */

(function (global) {
  "use strict";

  var T = SDNA.Tokens;
  var TMPL = SDNA.Templates;
  var EXP = SDNA.Export;

  /* ---- DOM helpers ---- */
  var $ = function (id) { return document.getElementById(id); };
  var qs = function (s, p) { return (p || document).querySelector(s); };
  var qsa = function (s, p) { return (p || document).querySelectorAll(s); };

  /* ---- State ---- */
  var state = {
    currentSVG: null,
    currentTemplate: "cover",
    currentSize: "cover",
    currentPalette: T.PALETTES[0],
    seed: Date.now(),
    isGenerating: false
  };

  /* ---- Render preview from SVG string ---- */
  function renderPreview(svg) {
    var container = $("ih-preview");
    if (!container) return;
    container.innerHTML = "";
    if (!svg) {
      container.innerHTML = '<div class="ih-preview__empty"><span class="ih-preview__empty-icon">\u25C7</span><p>Nh\u1EADp n\u1ED9i dung v\u00E0 nh\u1EA5n <strong>T\u1EA1o</strong> \u0111\u1EC3 xem tr\u01B0\u1EDBc</p></div>';
      return;
    }
    var img = document.createElement("img");
    img.src = EXP.svgToDataURL(svg);
    img.alt = "Infographic preview";
    img.className = "ih-preview__img";
    container.appendChild(img);
    state.currentSVG = svg;
  }

  /* ---- Gallery rendering ---- */
  function renderGallery(results) {
    var gallery = $("ih-gallery");
    if (!gallery) return;
    gallery.innerHTML = "";

    var grid = document.createElement("div");
    grid.className = "ih-gallery__grid";

    results.forEach(function (r) {
      var card = document.createElement("div");
      card.className = "ih-gallery__card";

      var preview = document.createElement("div");
      preview.className = "ih-gallery__preview";
      var img = document.createElement("img");
      img.src = EXP.svgToDataURL(r.svg);
      img.alt = r.label + " infographic";
      img.loading = "lazy";
      preview.appendChild(img);

      var meta = document.createElement("div");
      meta.className = "ih-gallery__meta";
      meta.innerHTML = '<span class="ih-gallery__type">' + r.label + '</span><span class="ih-gallery__desc">' + r.desc + '</span>';

      var actions = document.createElement("div");
      actions.className = "ih-gallery__actions";
      var svgBtn = document.createElement("button");
      svgBtn.className = "ih-btn ih-btn--sm ih-btn--ghost";
      svgBtn.textContent = "SVG";
      svgBtn.addEventListener("click", function (svgCopy) {
        return function () { EXP.downloadSVG(svgCopy, "infographic-" + r.id + ".svg"); };
      }(r.svg));
      var pngBtn = document.createElement("button");
      pngBtn.className = "ih-btn ih-btn--sm ih-btn--primary";
      pngBtn.textContent = "PNG";
      pngBtn.addEventListener("click", function (svgCopy) {
        return function () {
          var sz = T.SIZES[state.currentSize] || T.SIZES.cover;
          pngBtn.disabled = true;
          pngBtn.textContent = "...";
          EXP.downloadPNG(svgCopy, "infographic-" + r.id + ".svg", sz.w, sz.h)
            .then(function () { pngBtn.disabled = false; pngBtn.textContent = "PNG"; })
            ["catch"](function () { pngBtn.disabled = false; pngBtn.textContent = "PNG"; });
        };
      }(r.svg));

      actions.appendChild(svgBtn);
      actions.appendChild(pngBtn);

      card.appendChild(preview);
      card.appendChild(meta);
      card.appendChild(actions);
      grid.appendChild(card);
    });

    gallery.appendChild(grid);
  }

  /* ---- Generate infographic from form data ---- */
  function generate() {
    if (state.isGenerating) return;
    state.isGenerating = true;

    var title = $("ih-title").value.trim();
    var subtitle = $("ih-subtitle").value.trim();
    var content = $("ih-content").value.trim();
    var customBullets = $("ih-bullets").value.trim();
    var kpiRaw = $("ih-kpis").value.trim();

    if (!title && !content && !subtitle && !customBullets) {
      $("ih-title").focus();
      state.isGenerating = false;
      return;
    }

    // Show progress
    var submitBtn = $("ih-generate-btn");
    var progress = $("ih-progress");
    submitBtn.disabled = true;
    submitBtn.textContent = "\u25B6 \u0110ang t\u1EA1o\u2026";
    progress.hidden = false;
    $("ih-progress-bar").style.width = "20%";
    $("ih-progress-text").textContent = "\u0110ang x\u1EED l\u00FD\u2026";

    // Defer to next tick for UI update
    setTimeout(function () {
      // Parse KPI values
      var kpis = [];
      if (kpiRaw) {
        var kpiLines = kpiRaw.split("\n").filter(Boolean);
        kpiLines.forEach(function (line) {
          var parts = line.split("|").map(function (s) { return s.trim(); });
          if (parts.length >= 1) {
            kpis.push({
              value: parts[0] || "\u2014",
              unit: parts[1] || "",
              label: parts[2] || "",
              icon: parts[3] || "chart"
            });
          }
        });
      }

      // Parse custom bullets
      var bullets = [];
      if (customBullets) {
        bullets = customBullets.split("\n").map(function (l) { return l.replace(/^[-*\u2022]\s*/, "").trim(); }).filter(Boolean);
      }

      // Build data
      var data = {
        title: title || "Infographic",
        subtitle: subtitle
      };
      if (bullets.length > 0) {
        data.bullets = bullets.slice(0, 5);
      }
      if (kpis.length > 0) {
        data.kpis = kpis.slice(0, 4);
      }
      // If no explicit bullets, extract from content
      if (!data.bullets && content) {
        var parsed = TMPL.parseInput(title, subtitle, content, kpis, "");
        data.bullets = parsed.bullets;
        data.summaryRows = parsed.summaryRows;
      }
      if (data.bullets && !data.summaryRows) {
        data.summaryRows = data.bullets.map(function (b) { return { label: b, value: "" }; });
      }

      // Determine template
      var templateMode = $("ih-template-select").value;
      var templateId;
      if (templateMode === "auto") {
        templateId = TMPL.autoSelectTemplate(data);
      } else {
        templateId = templateMode;
      }
      state.currentTemplate = templateId;

      // Determine size
      var sizeKey = $("ih-size-select").value;
      state.currentSize = sizeKey;
      var size = T.SIZES[sizeKey] || T.SIZES.cover;

      // Determine palette (use seed for deterministic random)
      var seed = parseInt($("ih-seed").value, 10) || Date.now();
      state.seed = seed;
      state.currentPalette = T.randomPalette(seed + templateId.length);

      $("ih-progress-bar").style.width = "60%";
      $("ih-progress-text").textContent = "\u0110ang d\u1EF1ng SVG\u2026";

      setTimeout(function () {
        // Generate
        var svg = TMPL.generate(templateId, data, state.currentPalette, size);

        // Validate
        var validResult = SDNA.Layout.validateLayout(svg, size.w, size.h);
        if (!validResult.valid) {
          $("ih-progress-text").textContent = "C\u1EA3nh b\u00E1o b\u1ED1 c\u1EE5c: " + validResult.issues.join("; ");
        }

        // Render preview + gallery
        renderPreview(svg);

        // Generate all templates for gallery
        var allResults = TMPL.generateAll(data, state.currentPalette, size);
        renderGallery(allResults);

        $("ih-result-panel").hidden = false;
        $("ih-progress-bar").style.width = "100%";
        $("ih-progress-text").textContent = "Ho\u00E0n t\u1EA5t!";

        submitBtn.disabled = false;
        submitBtn.textContent = "\u25C6 T\u1EA1o infographic";
        state.isGenerating = false;

        setTimeout(function () {
          progress.hidden = true;
          $("ih-progress-bar").style.width = "0%";
        }, 1500);
      }, 150);
    }, 50);
  }

  /* ---- Download current preview ---- */
  function downloadCurrentPNG() {
    if (!state.currentSVG) return;
    var sz = T.SIZES[state.currentSize] || T.SIZES.cover;
    var btn = $("ih-dl-png");
    btn.disabled = true;
    btn.textContent = "...";
    EXP.downloadPNG(state.currentSVG, "infographic-" + state.currentTemplate + ".png", sz.w, sz.h)
      .then(function () { btn.disabled = false; btn.textContent = "PNG"; })
      ["catch"](function () { btn.disabled = false; btn.textContent = "PNG"; });
  }

  function downloadCurrentSVG() {
    if (!state.currentSVG) return;
    EXP.downloadSVG(state.currentSVG, "infographic-" + state.currentTemplate + ".svg");
  }

  /* ---- Regenerate variant (new seed) ---- */
  function regenerateVariant() {
    var seedInput = $("ih-seed");
    var current = parseInt(seedInput.value, 10) || Date.now();
    seedInput.value = String(current + 1);
    generate();
  }

  /* ---- Initialize UI ---- */
  function init() {
    // Form submit
    var form = $("ih-form");
    if (form) form.addEventListener("submit", function (e) { e.preventDefault(); generate(); });

    // Generate button
    var genBtn = $("ih-generate-btn");
    if (genBtn) genBtn.addEventListener("click", function (e) { e.preventDefault(); generate(); });

    // Download buttons
    var dlPNG = $("ih-dl-png");
    if (dlPNG) dlPNG.addEventListener("click", downloadCurrentPNG);
    var dlSVG = $("ih-dl-svg");
    if (dlSVG) dlSVG.addEventListener("click", downloadCurrentSVG);

    // Regenerate variant
    var regenBtn = $("ih-regen");
    if (regenBtn) regenBtn.addEventListener("click", regenerateVariant);

    // Seed: set random initial
    var seedInput = $("ih-seed");
    if (seedInput && !seedInput.value) seedInput.value = String(Math.floor(Math.random() * 100000));

    // Size selector change → regenerate if preview exists
    var sizeSel = $("ih-size-select");
    if (sizeSel) sizeSel.addEventListener("change", function () {
      if (state.currentSVG) generate();
    });

    // Template selector change → regenerate if preview exists
    var tmplSel = $("ih-template-select");
    if (tmplSel) tmplSel.addEventListener("change", function () {
      if (state.currentSVG) generate();
    });

    // Initial empty preview
    renderPreview(null);
  }

  document.addEventListener("DOMContentLoaded", init);
})(window);
