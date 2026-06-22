/**
 * H-Dashboard — OCR fallback for scanned invoices (CamScanner / photo receipts).
 *
 * Invoice PDFs come in two shapes:
 *   1. e-invoices / digital receipts → have a real text layer (pdf.js reads them).
 *   2. scanned paper receipts (the common case) → are flat images with NO text.
 *
 * For case 2 the parser falls back here: each PDF page is rendered to a canvas
 * via pdf.js, then Tesseract.js (lang vie+eng) recognises the text. Everything
 * runs in the browser — the invoice never leaves the device.
 */
(function (global) {
  "use strict";

  const TESS_VERSION = "5.1.1";
  const CDN_BASE = "https://cdn.jsdelivr.net/npm/tesseract.js@" + TESS_VERSION + "/dist/";
  const CDN_TESS = CDN_BASE + "tesseract.min.js";
  const CDN_WORKER = CDN_BASE + "worker.min.js";
  const CDN_CORE = "https://cdn.jsdelivr.net/npm/tesseract.js-core@" + TESS_VERSION;
  const TESS_LANG = "https://tessdata.projectnaptha.com/4.0.0";
  const OCR_LANGS_PRIMARY = "vie+eng";
  const OCR_LANGS_FALLBACK = "eng";
  const RENDER_SCALE = 2.4;
  const WORKER_TIMEOUT_MS = 120000;

  let scriptPromise = null;
  let lastError = null;

  function metaContent(name) {
    const el = document.querySelector('meta[name="' + name + '"]');
    return el && el.getAttribute("content") ? el.getAttribute("content").trim() : "";
  }

  function tessSources() {
    return {
      script: metaContent("hd-tesseract-src") || CDN_TESS,
      worker: metaContent("hd-tesseract-worker") || CDN_WORKER,
      core: metaContent("hd-tesseract-core") || CDN_CORE,
    };
  }

  function loadScript(src) {
    return new Promise(function (resolve, reject) {
      if (!src) {
        reject(new Error("OCR: thiếu URL Tesseract.js"));
        return;
      }
      if (global.Tesseract) {
        resolve();
        return;
      }

      const existing = document.querySelector('script[data-hd-ocr-src="' + src + '"]');
      if (existing) {
        if (existing.dataset.hdOcrState === "error") {
          reject(new Error("Không tải được Tesseract.js: " + src));
          return;
        }
        if (existing.dataset.hdOcrState === "loaded" || global.Tesseract) {
          return global.Tesseract ? resolve() : reject(new Error("Tesseract.js load xong nhưng undefined"));
        }
        existing.addEventListener("load", function onLoad() {
          existing.removeEventListener("load", onLoad);
          existing.dataset.hdOcrState = global.Tesseract ? "loaded" : "error";
          return global.Tesseract ? resolve() : reject(new Error("Tesseract.js load xong nhưng undefined"));
        });
        existing.addEventListener("error", function onErr() {
          existing.removeEventListener("error", onErr);
          existing.dataset.hdOcrState = "error";
          reject(new Error("Không tải được Tesseract.js: " + src));
        });
        return;
      }

      const s = document.createElement("script");
      s.src = src;
      s.async = true;
      s.dataset.hdOcrSrc = src;
      s.onload = function () {
        s.dataset.hdOcrState = global.Tesseract ? "loaded" : "error";
        global.Tesseract ? resolve() : reject(new Error("Tesseract.js load xong nhưng undefined"));
      };
      s.onerror = function () {
        s.dataset.hdOcrState = "error";
        reject(new Error("Không tải được Tesseract.js: " + src));
      };
      document.head.appendChild(s);
    });
  }

  async function ensureReady() {
    if (global.Tesseract) return global.Tesseract;

    if (!scriptPromise) {
      const sources = tessSources();
      const candidates = [sources.script, CDN_TESS].filter(Boolean);
      scriptPromise = (async function () {
        let loadErr = null;
        for (let i = 0; i < candidates.length; i++) {
          try {
            await loadScript(candidates[i]);
            if (global.Tesseract) break;
          } catch (err) {
            loadErr = err;
            console.warn("[H-Dashboard OCR] Tesseract source failed:", candidates[i], err);
          }
        }
        if (!global.Tesseract) {
          lastError = loadErr || new Error("Không tải được Tesseract.js — kiểm tra mạng hoặc tải lại trang.");
          throw lastError;
        }
        return global.Tesseract;
      })().catch(function (err) {
        scriptPromise = null;
        lastError = err;
        throw err;
      });
    }
    return scriptPromise;
  }

  function isAvailable() {
    return typeof document !== "undefined" && typeof crypto !== "undefined";
  }

  function getLastError() {
    return lastError;
  }

  function mapProgress(status, langs) {
    if (!status) return "";
    if (status.status === "loading tesseract core") return "Đang tải engine OCR (WASM)…";
    if (status.status === "initializing tesseract") return "Đang khởi tạo OCR…";
    if (status.status === "loading language traineddata") {
      return "Đang tải dữ liệu ngôn ngữ (" + (langs || "vie+eng") + ")… " +
        (status.progress != null ? Math.round(status.progress * 100) + "%" : "");
    }
    if (status.status === "initializing api") return "Đang khởi tạo API OCR…";
    if (status.status === "recognizing text") {
      return "Đang nhận dạng chữ… " +
        (status.progress != null ? Math.round(status.progress * 100) + "%" : "");
    }
    return status.status || "";
  }

  function withTimeout(promise, ms, label) {
    return new Promise(function (resolve, reject) {
      const timer = setTimeout(function () {
        reject(new Error(label + " (quá " + Math.round(ms / 1000) + "s — kiểm tra mạng hoặc thử lại)"));
      }, ms);
      promise.then(
        function (val) {
          clearTimeout(timer);
          resolve(val);
        },
        function (err) {
          clearTimeout(timer);
          reject(err);
        }
      );
    });
  }

  async function createOcrWorker(Tesseract, langs, onStatus) {
    const notify = typeof onStatus === "function" ? onStatus : function () {};
    const sources = tessSources();
    const workerPath = sources.worker || CDN_WORKER;
    const corePath = sources.core || CDN_CORE;

    const options = {
      workerPath: workerPath,
      corePath: corePath,
      langPath: TESS_LANG,
      workerBlobURL: false,
      gzip: true,
      logger: function (m) {
        const msg = mapProgress(m, langs);
        if (msg) notify(msg);
      },
      errorHandler: function (err) {
        console.error("[H-Dashboard OCR] worker error:", err);
        lastError = err instanceof Error ? err : new Error(String(err));
      },
    };

    notify("Đang tải bộ nhận dạng chữ (OCR)…");
    return withTimeout(
      Tesseract.createWorker(langs, 1, options),
      WORKER_TIMEOUT_MS,
      "Không khởi tạo được OCR"
    );
  }

  async function renderPageToCanvas(page) {
    const viewport = page.getViewport({ scale: RENDER_SCALE });
    const canvas = document.createElement("canvas");
    canvas.width = Math.ceil(viewport.width);
    canvas.height = Math.ceil(viewport.height);
    const ctx = canvas.getContext("2d");
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

    const Tesseract = await ensureReady();
    const pdf = await pdfjs.getDocument({ data: arrayBuffer }).promise;

    let worker;
    let usedLangs = OCR_LANGS_PRIMARY;
    try {
      try {
        worker = await createOcrWorker(Tesseract, OCR_LANGS_PRIMARY, notify);
      } catch (primaryErr) {
        console.warn("[H-Dashboard OCR] vie+eng failed, fallback eng:", primaryErr);
        notify("OCR vie+eng thất bại — thử lại chỉ tiếng Anh (eng)…");
        usedLangs = OCR_LANGS_FALLBACK;
        worker = await createOcrWorker(Tesseract, OCR_LANGS_FALLBACK, notify);
      }

      const chunks = [];
      for (let i = 1; i <= pdf.numPages; i++) {
        notify("Đang OCR trang " + i + "/" + pdf.numPages + " (" + usedLangs + ")…");
        const page = await pdf.getPage(i);
        const canvas = await renderPageToCanvas(page);
        const { data } = await worker.recognize(canvas);
        chunks.push(data && data.text ? data.text : "");
        canvas.width = canvas.height = 0;
      }
      return chunks.join("\n\n");
    } catch (err) {
      lastError = err;
      const hint = err && err.message ? err.message : "OCR thất bại";
      throw new Error(
        hint +
          ". Gợi ý: kiểm tra mạng, tải lại trang, hoặc dùng PDF có lớp text (không phải ảnh scan mờ)."
      );
    } finally {
      if (worker) {
        try {
          await worker.terminate();
        } catch (e) {
          /* ignore */
        }
      }
    }
  }

  global.HDashboardOcr = {
    ensureReady: ensureReady,
    isAvailable: isAvailable,
    getLastError: getLastError,
    ocrPdf: ocrPdf,
  };
})(typeof window !== "undefined" ? window : globalThis);