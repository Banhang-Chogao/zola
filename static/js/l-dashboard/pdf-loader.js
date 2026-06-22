/**
 * L-Dashboard — load pdf.js with local-first + jsDelivr fallback (CSP-safe).
 * cdnjs.cloudflare.com is blocked by site CSP; assets live under / via get_url().
 */
(function (global) {
  "use strict";

  const PDFJS_VERSION = "3.11.174";
  const CDN_PDF =
    "https://cdn.jsdelivr.net/npm/pdfjs-dist@" + PDFJS_VERSION + "/build/pdf.min.js";
  const CDN_WORKER =
    "https://cdn.jsdelivr.net/npm/pdfjs-dist@" + PDFJS_VERSION + "/build/pdf.worker.min.js";

  let readyPromise = null;
  let lastError = null;

  function metaContent(name) {
    const el = document.querySelector('meta[name="' + name + '"]');
    return el && el.getAttribute("content") ? el.getAttribute("content").trim() : "";
  }

  function loadScript(src) {
    return new Promise(function (resolve, reject) {
      if (!src) {
        reject(new Error("PDF.js: thiếu URL script"));
        return;
      }
      const existing = document.querySelector('script[data-ld-pdfjs-src="' + src + '"]');
      if (existing) {
        if (global.pdfjsLib) {
          resolve();
          return;
        }
        existing.addEventListener("load", function () {
          return global.pdfjsLib ? resolve() : reject(new Error("PDF.js load xong nhưng pdfjsLib undefined"));
        });
        existing.addEventListener("error", function () {
          return reject(new Error("Không tải được PDF.js: " + src));
        });
        return;
      }
      const script = document.createElement("script");
      script.src = src;
      script.async = false;
      script.dataset.ldPdfjsSrc = src;
      script.onload = function () {
        if (global.pdfjsLib) resolve();
        else reject(new Error("PDF.js load xong nhưng pdfjsLib undefined: " + src));
      };
      script.onerror = function () {
        reject(new Error("Không tải được PDF.js: " + src));
      };
      document.head.appendChild(script);
    });
  }

  function configureWorker(workerCandidates) {
    const pdfjs = global.pdfjsLib;
    if (!pdfjs) return false;
    for (let i = 0; i < workerCandidates.length; i++) {
      const workerSrc = workerCandidates[i];
      if (!workerSrc) continue;
      try {
        pdfjs.GlobalWorkerOptions.workerSrc = workerSrc;
        return true;
      } catch (err) {
        lastError = err;
      }
    }
    return false;
  }

  async function ensureReady() {
    if (global.pdfjsLib && global.pdfjsLib.GlobalWorkerOptions.workerSrc) {
      return global.pdfjsLib;
    }
    if (readyPromise) return readyPromise;

    const pdfCandidates = [metaContent("ld-pdfjs-src"), CDN_PDF].filter(Boolean);
    const workerCandidates = [metaContent("ld-pdfjs-worker"), CDN_WORKER].filter(Boolean);

    readyPromise = (async function () {
      let loadErr = null;
      for (let i = 0; i < pdfCandidates.length; i++) {
        try {
          if (!global.pdfjsLib) await loadScript(pdfCandidates[i]);
          if (global.pdfjsLib) break;
        } catch (err) {
          loadErr = err;
          console.warn("[L-Dashboard] PDF.js source failed:", pdfCandidates[i], err);
        }
      }

      if (!global.pdfjsLib) {
        const msg =
          "pdf.js chưa tải — không thể đọc PDF LPBank. Kiểm tra mạng hoặc tải lại trang.";
        lastError = loadErr || new Error(msg);
        throw lastError;
      }

      if (!configureWorker(workerCandidates)) {
        const msg = "pdf.js worker chưa cấu hình được — thử tải lại trang.";
        lastError = new Error(msg);
        throw lastError;
      }

      return global.pdfjsLib;
    })();

    return readyPromise;
  }

  function isReady() {
    return !!(global.pdfjsLib && global.pdfjsLib.GlobalWorkerOptions.workerSrc);
  }

  function getLastError() {
    return lastError;
  }

  async function retryWithCdnWorker() {
    await ensureReady();
    if (!global.pdfjsLib) return;
    const localWorker = metaContent("ld-pdfjs-worker");
    const current = global.pdfjsLib.GlobalWorkerOptions.workerSrc || "";
    if (current && current !== CDN_WORKER && current === localWorker) {
      console.warn("[L-Dashboard] Retrying PDF.js with CDN worker fallback");
      global.pdfjsLib.GlobalWorkerOptions.workerSrc = CDN_WORKER;
    }
  }

  global.LDashboardPdf = {
    ensureReady: ensureReady,
    isReady: isReady,
    getLastError: getLastError,
    retryWithCdnWorker: retryWithCdnWorker,
  };
})(typeof window !== "undefined" ? window : globalThis);