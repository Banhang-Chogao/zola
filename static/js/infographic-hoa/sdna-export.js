/* ============================================================================
   sdna-export.js — SVG / PNG export helpers
   PNG export uses Image + Canvas rasterization (browser-native, no deps).
   SVG export uses Blob URL download.
   ============================================================================ */

var SDNA = SDNA || {};

SDNA.Export = (function () {
  "use strict";

  /* ---- SVG to Blob URL ---- */
  function svgToBlobURL(svg) {
    var blob = new Blob([svg], { type: "image/svg+xml;charset=utf-8" });
    return URL.createObjectURL(blob);
  }

  /* ---- SVG to Data URL ---- */
  function svgToDataURL(svg) {
    return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
  }

  /* ---- Trigger download via anchor element ---- */
  function downloadURL(url, filename) {
    var a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }

  /* ---- Download SVG as .svg file ---- */
  function downloadSVG(svg, filename) {
    var url = svgToBlobURL(svg);
    downloadURL(url, filename.replace(/\.\w+$/, ".svg"));
    setTimeout(function () { URL.revokeObjectURL(url); }, 5000);
  }

  /* ---- Download PNG by rendering SVG on canvas ---- */
  function downloadPNG(svg, filename, width, height) {
    return new Promise(function (resolve, reject) {
      var img = new Image();
      var canvas = document.createElement("canvas");
      var ctx = canvas.getContext("2d");

      var w = width || 1200;
      var h = height || 630;

      // Set canvas to a multiple for crisp output (2x)
      var scale = 2;
      canvas.width = w * scale;
      canvas.height = h * scale;

      // White background (in case SVG has transparent areas)
      img.onload = function () {
        ctx.scale(scale, scale);
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, w, h);
        ctx.drawImage(img, 0, 0, w, h);
        canvas.toBlob(function (blob) {
          if (blob) {
            var blobUrl = URL.createObjectURL(blob);
            downloadURL(blobUrl, filename.replace(/\.\w+$/, ".png"));
            URL.revokeObjectURL(blobUrl);
            resolve();
          } else {
            reject(new Error("Canvas toBlob failed"));
          }
        }, "image/png");
        URL.revokeObjectURL(img.src);
      };

      img.onerror = function () {
        reject(new Error("Image load failed for PNG export"));
      };

      img.src = svgToBlobURL(svg);
    });
  }

  /* ---- High-level export: returns Blob URL for preview ---- */
  function getPreviewURL(svg) {
    return svgToBlobURL(svg);
  }

  return {
    svgToBlobURL:  svgToBlobURL,
    svgToDataURL:  svgToDataURL,
    downloadURL:   downloadURL,
    downloadSVG:   downloadSVG,
    downloadPNG:   downloadPNG,
    getPreviewURL: getPreviewURL
  };
})();
