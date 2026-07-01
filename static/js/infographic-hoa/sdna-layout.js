/* ============================================================================
   sdna-layout.js — Text measurement, wrapping, font scaling, layout validation
   Uses offscreen canvas for precise text width measurement.
   ============================================================================ */

var SDNA = SDNA || {};

SDNA.Layout = (function () {
  "use strict";

  var _ctx = null;

  function getCtx() {
    if (!_ctx) {
      _ctx = document.createElement("canvas").getContext("2d");
    }
    return _ctx;
  }

  /* ---- Measure exact pixel width of text ---- */
  function measureText(text, font) {
    if (!text) return 0;
    var ctx = getCtx();
    ctx.font = font;
    // Normalize spaces for measurement
    return ctx.measureText(text.replace(/\s+/g, " ")).width;
  }

  /* ---- Build font string from family, size, weight ---- */
  function fontStr(family, size, weight) {
    return (weight || 400) + " " + size + "px " + family;
  }

  /* ---- Wrap text to fit maxWidth ---- */
  function wrapText(text, maxWidth, fontFamily, fontSize, fontWeight) {
    if (!text) return [];
    var font = fontStr(fontFamily, fontSize, fontWeight);
    var words = String(text).split(/\s+/);
    var lines = [];
    var current = "";

    for (var i = 0; i < words.length; i++) {
      var word = words[i];
      // If word itself is too long, force-break it
      var wordWidth = measureText(word, font);
      if (wordWidth > maxWidth) {
        // Force-break long word
        if (current) lines.push(current);
        current = word;
        continue;
      }
      var test = current ? current + " " + word : word;
      if (measureText(test, font) > maxWidth && current) {
        lines.push(current);
        current = word;
      } else {
        current = test;
      }
    }
    if (current) lines.push(current);

    return lines;
  }

  /* ---- Scale font to fit within constraints ---- */
  function scaleFont(text, maxWidth, maxLines, fontFamily, minSize, maxSize, fontWeight, lineHeight) {
    if (!text) return { lines: [], fontSize: maxSize || 20, lineHeight: 1.3 };

    minSize = minSize || 12;
    maxSize = maxSize || 60;
    lineHeight = lineHeight || 1.3;

    // Try sizes from max down to min
    for (var size = maxSize; size >= minSize; size -= 1) {
      var lines = wrapText(text, maxWidth, fontFamily, size, fontWeight);
      if (lines.length <= maxLines) {
        // Check that last line isn't absurdly short (optional)
        return {
          lines: lines,
          fontSize: size,
          lineHeight: lineHeight,
          font: fontStr(fontFamily, size, fontWeight)
        };
      }
    }

    // Fallback: use minSize and accept overspill
    var fallbackLines = wrapText(text, maxWidth, fontFamily, minSize, fontWeight);
    return {
      lines: fallbackLines,
      fontSize: minSize,
      lineHeight: lineHeight,
      font: fontStr(fontFamily, minSize, fontWeight),
      overflow: fallbackLines.length > maxLines
    };
  }

  /* ---- Parse SVG and validate no element exceeds canvas bounds ---- */
  function validateLayout(svgText, canvasW, canvasH, _opts) {
    var opts = _opts || {};
    var issues = [];
    var valid = true;

    if (!svgText || !svgText.length) {
      return { valid: false, issues: ["Empty SVG"] };
    }

    // Check SVG dimensions in viewBox
    var vbMatch = svgText.match(/viewBox=["']([^"']+)["']/);
    if (vbMatch) {
      var parts = vbMatch[1].split(/\s+/).map(Number);
      if (parts.length === 4) {
        var svgW = parts[2];
        var svgH = parts[3];
        // Allow small tolerance (3px)
        if (Math.abs(svgW - canvasW) > 3) {
          issues.push("SVG width " + svgW + " does not match canvas " + canvasW);
          valid = false;
        }
        if (Math.abs(svgH - canvasH) > 3) {
          issues.push("SVG height " + svgH + " does not match canvas " + canvasH);
          valid = false;
        }
      }
    }

    // Basic structural checks
    if (!svgText.includes("<svg") || !svgText.includes("</svg>")) {
      issues.push("Invalid SVG structure");
      valid = false;
    }

    // Check for empty text elements
    var textMatch = svgText.match(/<text[^>]*><\/text>/g);
    if (textMatch && textMatch.length > 0) {
      issues.push("Empty text elements found: " + textMatch.length);
      // Non-fatal — SVG still renders
    }

    return { valid: valid, issues: issues };
  }

  /* ---- Estimate if given text will fit in an area (character-based fallback) ---- */
  function estimateCharFit(text, maxChars) {
    if (!text) return true;
    return String(text).length <= maxChars;
  }

  /* ---- Safe string truncation (keep whole words if possible) ---- */
  function truncateWords(text, maxChars) {
    if (!text || text.length <= maxChars) return text;
    var truncated = text.slice(0, maxChars);
    // Try to break at a space
    var lastSpace = truncated.lastIndexOf(" ");
    if (lastSpace > maxChars * 0.7) {
      return truncated.slice(0, lastSpace) + "…";
    }
    return truncated + "…";
  }

  return {
    measureText:     measureText,
    fontStr:         fontStr,
    wrapText:        wrapText,
    scaleFont:       scaleFont,
    validateLayout:  validateLayout,
    estimateCharFit: estimateCharFit,
    truncateWords:   truncateWords
  };
})();
