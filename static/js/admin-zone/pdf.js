/**
 * PDF generation with watermark for Operation Guideline
 */

(function () {
  window.AdminZonePDF = window.AdminZonePDF || {};

  const { jsPDF } = window.jspdf;

  function generateContentHash() {
    // Deterministic 16-char hashcode based on content + timestamp
    const seed = "OPERATION_GUIDELINE_2026_06_21";
    let hash = 0;
    for (let i = 0; i < seed.length; i++) {
      const char = seed.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32bit integer
    }
    const hex = Math.abs(hash).toString(16).padStart(16, "0").substring(0, 16);
    return hex.toUpperCase();
  }

  function getBlogName() {
    // Try to get from config meta tag, fallback to page title
    const meta = document.querySelector('meta[name="og:site_name"]');
    if (meta) return meta.getAttribute("content") || "SEOMONEY";
    const titleEl = document.querySelector("title");
    if (titleEl) {
      const parts = titleEl.textContent.split(" | ");
      return (parts[parts.length - 1] || "SEOMONEY").trim();
    }
    return "SEOMONEY";
  }

  function buildPdfContent() {
    // Build Operation Guideline content for PDF
    const guidelines = window.AdminZoneData.getAllGuidelines();
    const pages = [];

    // Title page
    pages.push({
      type: "title",
      title: "Operation Guideline",
      subtitle: "Admin Zone Documentation",
      date: new Date().toLocaleDateString("vi-VN"),
    });

    // TOC
    pages.push({
      type: "toc",
      items: guidelines.map(g => ({
        code: g.code,
        name: g.name,
        page: 3 + guidelines.indexOf(g),
      })),
    });

    // Content pages
    guidelines.forEach((g, idx) => {
      pages.push({
        type: "guideline",
        number: idx + 1,
        code: g.code,
        name: g.name,
        purpose: g.purpose,
        template: g.template,
      });
    });

    return pages;
  }

  function generatePdf() {
    if (!jsPDF) {
      console.error("jsPDF not loaded");
      return null;
    }

    const pages = buildPdfContent();
    const pdf = new jsPDF({
      orientation: "portrait",
      unit: "mm",
      format: "a4",
    });

    const blogName = getBlogName();
    const hashcode = generateContentHash();
    const watermark = `${hashcode}_${blogName.toLowerCase()}`;

    // Helper: Draw watermark on page
    const drawWatermark = () => {
      pdf.setFontSize(10);
      pdf.setTextColor(255, 0, 0); // Red
      pdf.setAlpha(0.5); // 50% opacity
      pdf.text(watermark, pdf.internal.pageSize.getWidth() / 2, pdf.internal.pageSize.getHeight() / 2, {
        align: "center",
        angle: 45,
      });
      pdf.setAlpha(1); // Reset opacity
      pdf.setTextColor(0, 0, 0); // Black
    };

    // Build outline (bookmarks)
    const outline = [];

    let pageNum = 1;
    pages.forEach((page, idx) => {
      if (idx > 0) pdf.addPage();
      pageNum++;

      pdf.setFontSize(12);
      pdf.setFont(undefined, "normal");

      // Page number at bottom
      pdf.setFontSize(9);
      pdf.setTextColor(128, 128, 128);
      pdf.text(`Page ${pageNum}`, pdf.internal.pageSize.getWidth() / 2, pdf.internal.pageSize.getHeight() - 10, {
        align: "center",
      });
      pdf.setTextColor(0, 0, 0);
      pdf.setFontSize(12);

      // Render page content
      if (page.type === "title") {
        pdf.setFontSize(28);
        pdf.setFont(undefined, "bold");
        pdf.text(page.title, 20, 100);
        pdf.setFontSize(14);
        pdf.setFont(undefined, "normal");
        pdf.text(page.subtitle, 20, 120);
        pdf.setFontSize(10);
        pdf.setTextColor(128, 128, 128);
        pdf.text(`Generated: ${page.date}`, 20, 200);
        pdf.setTextColor(0, 0, 0);

        outline.push({
          title: page.title,
          pageNum,
        });
      } else if (page.type === "toc") {
        pdf.setFontSize(16);
        pdf.setFont(undefined, "bold");
        pdf.text("Table of Contents", 20, 20);
        pdf.setFontSize(11);
        pdf.setFont(undefined, "normal");

        let yPos = 35;
        page.items.forEach(item => {
          pdf.text(`${item.code} — ${item.name}`, 25, yPos);
          yPos += 8;
        });

        outline.push({
          title: "Table of Contents",
          pageNum,
        });
      } else if (page.type === "guideline") {
        pdf.setFontSize(14);
        pdf.setFont(undefined, "bold");
        pdf.text(`${page.code} — ${page.name}`, 20, 20);

        pdf.setFontSize(10);
        pdf.setFont(undefined, "normal");

        let yPos = 35;
        pdf.text("Tác dụng:", 20, yPos);
        yPos += 6;
        const purposeLines = pdf.splitTextToSize(page.purpose, 170);
        purposeLines.forEach(line => {
          pdf.text(line, 25, yPos);
          yPos += 5;
        });

        yPos += 3;
        pdf.setFont(undefined, "bold");
        pdf.text("Template tiêu biểu:", 20, yPos);
        yPos += 6;
        pdf.setFont(undefined, "normal");
        const templateLines = pdf.splitTextToSize(page.template, 170);
        templateLines.forEach(line => {
          pdf.text(line, 25, yPos);
          yPos += 5;
        });

        outline.push({
          title: `${page.code} — ${page.name}`,
          pageNum,
        });
      }

      // Draw watermark on every page
      drawWatermark();
    });

    // Set outline/bookmarks (if supported)
    try {
      if (pdf.setOutlines) {
        pdf.setOutlines(outline.map(o => ({
          title: o.title,
          pageNumber: o.pageNum,
        })));
      }
    } catch (e) {
      // Bookmarks not supported in this jsPDF version
    }

    return {
      pdf,
      filename: `Operation_Guideline_${hashcode}.pdf`,
      watermark,
    };
  }

  function downloadPdf() {
    const result = generatePdf();
    if (!result) {
      alert("Không thể tạo PDF. Vui lòng thử lại.");
      return;
    }

    result.pdf.save(result.filename);
  }

  function openPdfWebview() {
    const result = generatePdf();
    if (!result) {
      alert("Không thể tạo PDF. Vui lòng thử lại.");
      return;
    }

    const blob = result.pdf.output("blob");
    const url = URL.createObjectURL(blob);

    const viewer = document.getElementById("pdf-viewer");
    const iframe = document.getElementById("pdf-iframe");
    if (viewer && iframe) {
      iframe.src = url;
      viewer.hidden = false;
      // Store URL for cleanup
      viewer.dataset.blobUrl = url;
    }
  }

  function closePdfWebview() {
    const viewer = document.getElementById("pdf-viewer");
    const iframe = document.getElementById("pdf-iframe");
    if (viewer && iframe) {
      if (viewer.dataset.blobUrl) {
        URL.revokeObjectURL(viewer.dataset.blobUrl);
        delete viewer.dataset.blobUrl;
      }
      iframe.src = "";
      viewer.hidden = true;
    }
  }

  Object.assign(window.AdminZonePDF, {
    downloadPdf,
    openPdfWebview,
    closePdfWebview,
  });
})();
