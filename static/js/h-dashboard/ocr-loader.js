/**
 * H-Dashboard — OCR fallback for scanned invoices (CamScanner / photo receipts).
 *
 * Invoice PDFs come in two shapes:
 *   1. e-invoices / digital receipts → have a real text layer (pdf.js reads them).
 *   2. scanned paper receipts (the common case) → are flat images with NO text.
 *
 * For case 2 the parser falls back here: each PDF page is rendered to a canvas
 * via pdf.js, then Tesseract.js (lang vie+eng) recognises the text. Everything
 * runs in the browser — the invoice never leaves the device. Tesseract loads
 * lazily from jsDelivr (CSP script-src allowlists it) only when OCR is needed.
 */
(function (global) {
  "use strict";

  const TESS_VERSION = "5.1.1";
  const TESS_SRC =
    "https://cdn.jsdelivr.net/npm/tesseract.js@" + TESS_VERSION + "/dist/tesseract.min.js";
  const TESS_WORKER =
    "https://cdn.jsdelivr.net/npm/tesseract.js@" + TESS_VERSION + "/dist/worker.min.js";
  const TESS_CORE = "https://cdn.jsdelivr.net/npm/tesseract.js-core@5.1.0";
  const TESS_LANG = "https://tessdata.projectnaptha.com/4.0.0";
  const OCR_LANGS = "vie+eng";
  const RENDER_SCALE = 2.4; // upscale for sharper glyphs on thermal receipts

  let scriptPromise = null;
  let lastError = null;

  function loadScript(src) {
    return new Promise(function (resolve, reject) {
      const existing = document.querySelector('script[data-hd-ocr-src="' + src + '"]');
      if (existing) {
        if (global.Tesseract) return resolve();
        existing.addEventListener("load", function () {
          return global.Tesseract ? resolve() : reject(new Error("Tesseract load xong nhưng undefined"));
        });
        existing.addEventListener("error", function () {
          return reject(new Error("Không tải được Tesseract.js: " + src));
        });
        return;
      }
      const s = document.createElement("script");
      s.src = src;
      s.async = true;
      s.dataset.hdOcrSrc = src;
      s.onload = function () {
        global.Tesseract ? resolve() : reject(new Error("Tesseract.js load xong nhưng undefined"));
      };
      s.onerror = function () {
        reject(new Error("Không tải được Tesseract.js: " + src));
      };
      document.head.appendChild(s);
    });
  }

  async function ensureReady() {
    if (global.Tesseract) return global.Tesseract;
    if (!scriptPromise) {
      scriptPromise = loadScript(TESS_SRC).catch(function (err) {
        scriptPromise = null;
        lastError = err;
        throw err;
      });
    }
    await scriptPromise;
    return global.Tesseract;
  }

  function isAvailable() {
    return typeof document !== "undefined" && typeof crypto !== "undefined";
  }

  function getLastError() {
    return lastError;
  }

  async function renderPageToCanvas(page) {
    const viewport = page.getViewport({ scale: RENDER_SCALE });
    const canvas = document.createElement("canvas");
    canvas.width = Math.ceil(viewport.width);
    canvas.height = Math.ceil(viewport.height);
    const ctx = canvas.getContext("2d");
    // White backdrop so transparent PDF regions don't OCR as noise.
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    await page.render({ canvasContext: ctx, viewport }).promise;
    return canvas;
  }

  /**
   * OCR every page of the invoice PDF and return the concatenated text.
   * @param {ArrayBuffer} arrayBuffer fresh copy (pdf.js detaches the buffer)
   * @param {(msg:string)=>void} onStatus progress callback
   */
  async function ocrPdf(arrayBuffer, onStatus) {
    const notify = typeof onStatus === "function" ? onStatus : function () {};

    if (global.HDashboardPdf && typeof global.HDashboardPdf.ensureReady === "function") {
      await global.HDashboardPdf.ensureReady();
    }
    const pdfjs = global.pdfjsLib;
    if (!pdfjs) throw new Error("pdf.js chưa tải — không thể render trang hóa đơn để OCR.");

    notify("Đang tải bộ nhận dạng chữ (OCR)…");
    const Tesseract = await ensureReady();

    const pdf = await pdfjs.getDocument({ data: arrayBuffer }).promise;
    const worker = await Tesseract.createWorker(OCR_LANGS, 1, {
      workerPath: TESS_WORKER,
      corePath: TESS_CORE,
      langPath: TESS_LANG,
    });

    const chunks = [];
    try {
      for (let i = 1; i <= pdf.numPages; i++) {
        notify("Đang OCR trang " + i + "/" + pdf.numPages + " (ảnh scan)…");
        const page = await pdf.getPage(i);
        const canvas = await renderPageToCanvas(page);
        const { data } = await worker.recognize(canvas);
        chunks.push(data && data.text ? data.text : "");
        canvas.width = canvas.height = 0; // release pixels
      }
    } finally {
      await worker.terminate();
    }
    return chunks.join("\n\n");
  }

  global.HDashboardOcr = {
    ensureReady: ensureReady,
    isAvailable: isAvailable,
    getLastError: getLastError,
    ocrPdf: ocrPdf,
  };
})(typeof window !== "undefined" ? window : globalThis);
