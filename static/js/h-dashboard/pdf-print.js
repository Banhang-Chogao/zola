/**
 * H-Dashboard — Print-to-PDF export (browser Save as PDF).
 * Preserves online layout: cards, charts, heatmaps, maps, tables.
 */
(function (global) {
  "use strict";

  const CHART_IDS = [
    "hd-chart-timeline",
    "hd-chart-categories",
    "hd-chart-season",
    "hd-chart-monthly",
  ];

  let printState = null;

  function sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
  }

  async function waitForFonts() {
    if (document.fonts && document.fonts.ready) {
      try {
        await document.fonts.ready;
      } catch (e) {
        /* ignore */
      }
    }
    await sleep(200);
  }

  async function waitForCharts() {
    const Chart = global.Chart;
    if (!Chart || !Chart.instances) {
      await sleep(400);
      return;
    }
    const instances = Object.values(Chart.instances);
    instances.forEach((ch) => {
      try {
        ch.update("none");
      } catch (e) {
        /* ignore */
      }
    });
    await sleep(350);
  }

  function freezeChartsForPrint() {
    const frozen = [];
    CHART_IDS.forEach((id) => {
      const canvas = document.getElementById(id);
      if (!canvas || !canvas.getContext) return;
      const wrap = canvas.parentElement;
      if (!wrap) return;
      try {
        const w = canvas.width || canvas.clientWidth;
        const h = canvas.height || canvas.clientHeight;
        if (!w || !h) return;
        const off = document.createElement("canvas");
        off.width = w;
        off.height = h;
        const ctx = off.getContext("2d");
        if (!ctx) return;
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, w, h);
        ctx.drawImage(canvas, 0, 0, w, h);
        const img = document.createElement("img");
        img.src = off.toDataURL("image/png");
        img.className = "hd-print-chart-img";
        img.alt = canvas.getAttribute("aria-label") || "Chart";
        img.setAttribute("data-hd-print-frozen", "1");
        wrap.insertBefore(img, canvas);
        canvas.setAttribute("data-hd-print-hidden", "1");
        canvas.style.display = "none";
        frozen.push({ canvas, img });
      } catch (e) {
        console.warn("[H-Dashboard Print] chart freeze failed:", id, e);
      }
    });
    return frozen;
  }

  function unfreezeCharts(frozen) {
    (frozen || []).forEach(({ canvas, img }) => {
      if (img && img.parentNode) img.parentNode.removeChild(img);
      if (canvas) {
        canvas.style.display = "";
        canvas.removeAttribute("data-hd-print-hidden");
      }
    });
  }

  function ensurePrintBanner(title, subtitle) {
    let banner = document.getElementById("hd-print-banner");
    if (!banner) {
      banner = document.createElement("div");
      banner.id = "hd-print-banner";
      banner.className = "hd-print-banner";
      const dash = document.querySelector(".h-dashboard[data-hd-view='dashboard']");
      if (dash) dash.insertBefore(banner, dash.firstChild);
    }
    banner.innerHTML =
      "<h1 class='hd-print-banner__title'>" +
      escapeHtml(title || "H-Dashboard — Coffee Life Analytics") +
      "</h1>" +
      (subtitle
        ? "<p class='hd-print-banner__sub'>" + escapeHtml(subtitle) + "</p>"
        : "");
    return banner;
  }

  function removePrintBanner() {
    const banner = document.getElementById("hd-print-banner");
    if (banner) banner.remove();
  }

  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function buildSubtitle(payload, mode) {
    const summary = payload && payload.summary;
    if (!summary) return "";
    const range =
      summary.date_from && summary.date_to
        ? summary.date_from + " → " + summary.date_to
        : "";
    if (mode === "monthly") {
      return "Monthly Combined Report" + (range ? " · " + range : "");
    }
    return range ? "Khoảng thời gian: " + range : "";
  }

  /**
   * Wait until OCR, charts, maps, fonts, heatmaps are rendered.
   */
  async function waitForRender() {
    await waitForFonts();
    await waitForCharts();
    await sleep(150);
  }

  /**
   * Export dashboard via window.print() — user chooses Save as PDF.
   * @param {{ payload?: object, mode?: 'full'|'monthly', title?: string }} opts
   */
  async function exportViaPrint(opts) {
    opts = opts || {};
    const payload = opts.payload || {};
    const mode = opts.mode || "full";

    await waitForRender();

    const frozen = freezeChartsForPrint();
    const title =
      opts.title ||
      (mode === "monthly"
        ? "H-Dashboard — Monthly Combined Report"
        : "H-Dashboard — Coffee Life Analytics");
    const subtitle = buildSubtitle(payload, mode);

    document.dispatchEvent(new CustomEvent("hd-before-print"));

    document.body.classList.add("hd-print-export");
    if (mode === "monthly") document.body.classList.add("hd-print-export--monthly");
    ensurePrintBanner(title, subtitle);

    return new Promise((resolve, reject) => {
      printState = { frozen, resolve, reject };

      function cleanup() {
        document.body.classList.remove("hd-print-export");
        document.body.classList.remove("hd-print-export--monthly");
        removePrintBanner();
        unfreezeCharts(frozen);
        document.dispatchEvent(new CustomEvent("hd-after-print"));
        printState = null;
      }

      function onAfterPrint() {
        window.removeEventListener("afterprint", onAfterPrint);
        cleanup();
        resolve({ printed: true });
      }

      window.addEventListener("afterprint", onAfterPrint);

      try {
        window.print();
      } catch (err) {
        window.removeEventListener("afterprint", onAfterPrint);
        cleanup();
        reject(err);
      }

      setTimeout(() => {
        if (printState) {
          window.removeEventListener("afterprint", onAfterPrint);
          cleanup();
          resolve({ printed: true, fallback: true });
        }
      }, 60000);
    });
  }

  global.HDashboardPrint = {
    exportViaPrint,
    waitForRender,
    freezeChartsForPrint,
    unfreezeCharts,
  };
})(typeof window !== "undefined" ? window : globalThis);