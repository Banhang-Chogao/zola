/**
 * H-Dashboard — purchase invoice / receipt parser (hóa đơn mua hàng).
 *
 * Source = retail invoices (e.g. Highlands Coffee, supermarket receipts), NOT a
 * bank statement. Each invoice line item becomes one "expense" transaction so
 * the shared dashboard (summary / health / charts / insights) can aggregate
 * spending across many uploaded invoices.
 *
 * Reading strategy (mirrors L/O-Dashboard architecture):
 *   1. pdf.js text extraction (digital e-invoices with a real text layer).
 *   2. if that yields too little text → Tesseract.js OCR fallback for scanned
 *      paper receipts (HDashboardOcr).
 *
 * Money is Vietnamese-formatted (15.000 = 15000). All items are expenses, so
 *   amount = -lineTotal, debit = lineTotal, credit = 0, balance = running spend.
 */
(function (global) {
  "use strict";

  const SOURCE = "invoice";

  // A price token: grouped thousands (15.000 / 1,296,314) or a bare 4+ digit run.
  // Deliberately excludes small bare numbers like quantity "1" or "510ml" → 510.
  const PRICE_RE = /\d{1,3}(?:[.,]\d{3})+|\d{4,}/g;

  const PAYMENT_KEYWORDS = [
    ["payoo", "Payoo"],
    ["bank card", "Thẻ ngân hàng"],
    ["the ", "Thẻ"],
    ["tien mat", "Tiền mặt"],
    ["cash", "Tiền mặt"],
    ["momo", "MoMo"],
    ["vnpay", "VNPay"],
    ["zalopay", "ZaloPay"],
    ["chuyen khoan", "Chuyển khoản"],
    ["qr", "QR code"],
    ["visa", "Visa"],
    ["master", "Mastercard"],
  ];

  // Lines that are document metadata, never an item row.
  const META_MARKERS = [
    "hoa don", "hóa đơn", "thanh toan", "thanh toán", "invoice", "receipt",
    "shopid", "shop id", "check#", "check #", "check:", "pos", "pager",
    "so hd", "số hđ", "so hoa don", "số hóa đơn", "hoa don so", "hóa đơn số",
    "thu ngan", "thu ngân", "cashier", "ngay", "ngày", "date", "in store",
    "sdt", "đt:", "tel", "hotline", "ma so thue", "mã số thuế", "mst",
    "customerservice", "@", "www.", ".com", ".vn", "cam on", "cảm ơn",
    "xin chao", "quy khach", "quý khách", "thank you",
  ];

  // Note: "thanh toan" alone is excluded — it appears in the document title
  // "Hóa Đơn Thanh Toán" and would prematurely cut off the item region.
  const TOTAL_MARKERS = [
    "tong tien", "tổng tiền", "tong cong", "tổng cộng", "thanh tien",
    "thành tiền", "tong thanh toan", "tổng thanh toán", "total",
    "tien thoi", "tien khach", "tien thua",
  ];

  function deaccent(s) {
    return String(s)
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/đ/g, "d")
      .replace(/Đ/g, "D")
      .toLowerCase();
  }

  function normLine(line) {
    return String(line).trim().replace(/\s+/g, " ");
  }

  function parseVndNumber(token) {
    if (token == null) return 0;
    const digits = String(token).replace(/[^\d]/g, "");
    return digits ? parseInt(digits, 10) : 0;
  }

  function priceTokens(line) {
    const matches = line.match(PRICE_RE) || [];
    // Reject leading-zero runs (e.g. invoice id "0099") — money never starts with 0.
    return matches
      .filter((tok) => !/^0\d/.test(tok))
      .map(parseVndNumber)
      .filter((n) => n > 0);
  }

  function lastPrice(line) {
    const t = priceTokens(line);
    return t.length ? t[t.length - 1] : 0;
  }

  function isMetaLine(line) {
    const low = deaccent(line);
    return META_MARKERS.some((m) => low.includes(deaccent(m)));
  }

  function isTotalLine(line) {
    const low = deaccent(line);
    return TOTAL_MARKERS.some((m) => low.includes(deaccent(m)));
  }

  function detectPayment(lines) {
    for (const line of lines) {
      const low = deaccent(line);
      for (const [kw, label] of PAYMENT_KEYWORDS) {
        if (low.includes(kw)) return label;
      }
    }
    return "";
  }

  function parseDateTime(text) {
    // DD-MM-YYYY [HH:MM[:SS]] or DD/MM/YYYY — pick the first plausible match.
    const m = text.match(
      /(\d{1,2})[-/](\d{1,2})[-/](\d{4})(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?/
    );
    if (!m) return { iso: "", date: "", time: "" };
    const dd = m[1].padStart(2, "0");
    const mm = m[2].padStart(2, "0");
    const yyyy = m[3];
    const hh = (m[4] || "00").padStart(2, "0");
    const min = m[5] || "00";
    const ss = m[6] || "00";
    return {
      iso: `${yyyy}-${mm}-${dd}T${hh}:${min}:${ss}`,
      date: `${yyyy}-${mm}-${dd}`,
      time: m[4] ? `${hh}:${min}` : "",
    };
  }

  function captureAfter(text, label) {
    // Match "<label> : value" tolerant of diacritics / OCR spacing.
    const lines = text.split(/\r?\n/);
    const needle = deaccent(label);
    for (const raw of lines) {
      const low = deaccent(raw);
      const idx = low.indexOf(needle);
      if (idx >= 0) {
        let val = normLine(raw.slice(idx + label.length));
        val = val.replace(/^[\s:#.\-]+/, "").trim();
        if (val) return val;
      }
    }
    return "";
  }

  function parseMetadata(text, lines, stmt) {
    // Merchant: first non-empty line that isn't obvious metadata noise.
    for (const line of lines) {
      if (!line) continue;
      const low = deaccent(line);
      if (low.includes("hoa don") || low.includes("invoice") || low.includes("receipt")) continue;
      if (/^[\d\s.,:#/-]+$/.test(line)) continue;
      stmt.merchant = line;
      break;
    }

    const dt = parseDateTime(text);
    stmt.date_iso = dt.iso;
    stmt.invoice_date = dt.date;
    stmt.invoice_time = dt.time;

    let m = text.match(/Check\s*#?\s*[:#]?\s*(\w+)/i);
    if (!m) m = text.match(/(?:So HD|Số HĐ|So hoa don|Số hóa đơn|Hoa don so|Hóa đơn số|Invoice\s*(?:no|number|#))\s*[:#]?\s*([A-Za-z0-9]+)/i);
    if (m) stmt.invoice_no = m[1].trim();

    m = text.match(/Shop\s*ID\s*[:#]?\s*(\w+)/i);
    if (m) stmt.shop_id = m[1].trim();

    m = text.match(/\b(POS\d+)\b/i);
    if (m) stmt.pos = m[1].toUpperCase();

    m = text.match(/Pager\s*[:#]?\s*(\w+)/i);
    if (m) stmt.pager = m[1].trim();

    m = text.match(/(?:SDT|ĐT|Tel|Hotline)\s*[:#]?\s*([\d.\s\-()]{6,})/i);
    if (m) stmt.phone = normLine(m[1]).replace(/\s+/g, "");

    stmt.cashier = captureAfter(text, "Thu ngan") || captureAfter(text, "Thu ngân") || captureAfter(text, "Cashier");

    // Service type: In Store / Mang về / Tại chỗ / Take away.
    for (const line of lines) {
      const low = deaccent(line);
      if (low.includes("in store")) { stmt.service_type = "In Store"; break; }
      if (low.includes("mang ve") || low.includes("take away") || low.includes("takeaway")) { stmt.service_type = "Mang về"; break; }
      if (low.includes("tai cho") || low.includes("dine in")) { stmt.service_type = "Tại chỗ"; break; }
    }

    stmt.payment_method = detectPayment(lines);
  }

  function parseItems(lines, stmt) {
    // Items live between the header block and the first totals line. We scan all
    // lines, flag the totals region, and treat priced non-meta rows as items.
    let totalsIdx = lines.findIndex((l) => isTotalLine(l));
    if (totalsIdx < 0) totalsIdx = lines.length;

    const items = [];
    let current = null;

    const flush = () => {
      if (current && current.name) items.push(current);
      current = null;
    };

    for (let i = 0; i < totalsIdx; i++) {
      const line = lines[i];
      if (!line) continue;
      if (isMetaLine(line)) { flush(); continue; }

      const prices = priceTokens(line);
      if (prices.length) {
        // New item row: leading qty (small bare int), trailing price = line total.
        flush();
        const qtyMatch = line.match(/^(\d{1,3})\s+/);
        const qty = qtyMatch ? parseInt(qtyMatch[1], 10) : 1;
        const lineTotal = prices[prices.length - 1];
        const unitPrice = prices.length >= 2 ? prices[prices.length - 2] : (qty > 0 ? Math.round(lineTotal / qty) : lineTotal);

        let name = line;
        if (qtyMatch) name = name.slice(qtyMatch[0].length);
        name = name.replace(PRICE_RE, "").replace(/\bx\b/gi, " ").replace(/\s+/g, " ").trim();
        name = name.replace(/[.\-:]+$/, "").trim();

        current = { qty: qty || 1, unit_price: unitPrice, amount: lineTotal, name };
      } else if (current) {
        // Continuation line (e.g. size "510ml") → append to current item name.
        current.name = normLine(current.name + " " + line);
      }
    }
    flush();

    // Totals + payment from the totals region.
    let total = 0;
    let subtotal = 0;
    for (let i = totalsIdx; i < lines.length; i++) {
      const line = lines[i];
      const low = deaccent(line);
      const price = lastPrice(line);
      if (!price) continue;
      if ((low.includes("tong tien") || low.includes("tong cong") || low.includes("tong thanh toan") || low.includes("total")) && price > total) {
        total = price;
      } else if ((low.includes("thanh tien") || low.includes("thành tiền")) && !subtotal) {
        subtotal = price;
      }
    }

    const itemsSum = items.reduce((s, it) => s + it.amount, 0);
    stmt.subtotal = subtotal || itemsSum;
    stmt.total = total || subtotal || itemsSum;
    stmt.item_count = items.length;
    return items;
  }

  function parseInvoiceText(text) {
    const stmt = {
      source: SOURCE,
      merchant: "",
      address: "",
      phone: "",
      shop_id: "",
      invoice_no: "",
      pos: "",
      pager: "",
      cashier: "",
      service_type: "",
      payment_method: "",
      currency: "VND",
      date_iso: "",
      invoice_date: "",
      invoice_time: "",
      subtotal: 0,
      total: 0,
      item_count: 0,
      items: [],
      // Compatibility fields reused by the shared dashboard/insights code.
      from_date: "",
      to_date: "",
      opening_balance: 0,
      ending_balance: 0,
      total_debit: 0,
      total_credit: 0,
    };

    const lines = text.split(/\r?\n/).map(normLine).filter(Boolean);
    parseMetadata(text, lines, stmt);
    const items = parseItems(lines, stmt);
    stmt.items = items;

    stmt.from_date = stmt.invoice_date;
    stmt.to_date = stmt.invoice_date;
    stmt.ending_balance = stmt.total;
    stmt.total_debit = stmt.subtotal || stmt.total;
    return stmt;
  }

  async function sha256Hex(text) {
    const buf = new TextEncoder().encode(text);
    const hash = await crypto.subtle.digest("SHA-256", buf);
    return Array.from(new Uint8Array(hash))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
  }

  async function transactionsForDashboard(stmt) {
    const rows = [];
    const dateIso = stmt.date_iso || (stmt.invoice_date ? stmt.invoice_date + "T00:00:00" : "");
    const invNo = stmt.invoice_no || "HD";
    let running = 0;
    for (let i = 0; i < stmt.items.length; i++) {
      const it = stmt.items[i];
      running += it.amount;
      const txnNo = `${invNo}-${i + 1}`;
      // transaction_id keyed on stable invoice + item identity → re-upload dedupes.
      const id = await sha256Hex(
        `${stmt.merchant}|${dateIso}|${invNo}|${i + 1}|${it.name}|${it.amount}`
      );
      rows.push({
        source: SOURCE,
        date: dateIso || new Date().toISOString().slice(0, 19),
        value_date: stmt.invoice_date,
        merchant: stmt.merchant,
        description: it.name || "(không tên)",
        txn_no: txnNo,
        qty: it.qty,
        unit_price: it.unit_price,
        debit: it.amount,
        credit: 0,
        fee: 0,
        balance: running,
        amount: -it.amount,
        type: "expense",
        transaction_id: id,
      });
    }
    return rows;
  }

  function reconcile(stmt, transactions) {
    const sum = transactions.reduce((s, t) => s + t.debit, 0);
    const expected = stmt.total || stmt.subtotal || sum;
    const ok = !expected || Math.abs(sum - expected) <= Math.max(1, expected * 0.01);
    return {
      ok,
      sum_debit: sum,
      sum_credit: 0,
      expected_debit: expected,
      expected_credit: 0,
      expected_ending: expected,
      message: ok
        ? ""
        : "Tổng mặt hàng không khớp tổng hóa đơn — OCR có thể đọc thiếu/sai, hãy đối chiếu bảng bên dưới",
    };
  }

  function looksLikeText(text) {
    if (!text) return false;
    const letters = (text.match(/[A-Za-zÀ-ỹ]/g) || []).length;
    const digits = (text.match(/\d/g) || []).length;
    return letters >= 12 && letters + digits >= 20;
  }

  async function extractPdfText(arrayBuffer) {
    if (global.HDashboardPdf && typeof global.HDashboardPdf.ensureReady === "function") {
      await global.HDashboardPdf.ensureReady();
    }
    const pdfjs = global.pdfjsLib;
    if (!pdfjs) {
      const hint = global.HDashboardPdf && global.HDashboardPdf.getLastError ? global.HDashboardPdf.getLastError() : null;
      throw new Error(hint && hint.message ? hint.message : "pdf.js chưa tải — không thể đọc PDF hóa đơn");
    }

    let pdf;
    try {
      pdf = await pdfjs.getDocument({ data: arrayBuffer }).promise;
    } catch (firstErr) {
      if (global.HDashboardPdf && typeof global.HDashboardPdf.retryWithCdnWorker === "function") {
        await global.HDashboardPdf.retryWithCdnWorker();
        pdf = await pdfjs.getDocument({ data: arrayBuffer }).promise;
      } else {
        throw firstErr;
      }
    }

    const chunks = [];
    for (let i = 1; i <= pdf.numPages; i++) {
      const page = await pdf.getPage(i);
      const content = await page.getTextContent();
      chunks.push(groupTextItemsToLines(content.items).join("\n"));
    }
    return chunks.join("\n\n");
  }

  function groupTextItemsToLines(items) {
    const rows = [];
    for (const item of items) {
      const y = Math.round(item.transform[5]);
      const x = item.transform[4];
      let row = rows.find((r) => Math.abs(r.y - y) <= 2);
      if (!row) {
        row = { y, parts: [] };
        rows.push(row);
      }
      row.parts.push({ x, str: item.str });
    }
    rows.sort((a, b) => b.y - a.y);
    return rows.map((row) => {
      row.parts.sort((a, b) => a.x - b.x);
      return row.parts.map((p) => p.str).join(" ").replace(/\s+/g, " ").trim();
    });
  }

  /**
   * Read an invoice PDF: try the text layer first, OCR scanned images as fallback.
   * @param {ArrayBuffer} arrayBuffer
   * @param {{onStatus?:(msg:string)=>void}} [opts]
   */
  async function parseInvoicePdfArrayBuffer(arrayBuffer, opts) {
    const onStatus = opts && typeof opts.onStatus === "function" ? opts.onStatus : function () {};

    // pdf.js detaches the buffer it consumes → hand each reader its own copy.
    let text = "";
    try {
      onStatus("Đang đọc lớp text của PDF…");
      text = await extractPdfText(arrayBuffer.slice(0));
    } catch (err) {
      text = "";
    }

    let usedOcr = false;
    if (!looksLikeText(text)) {
      if (!global.HDashboardOcr || !global.HDashboardOcr.isAvailable()) {
        throw new Error("PDF là ảnh scan và OCR không khả dụng trên trình duyệt này.");
      }
      try {
        text = await global.HDashboardOcr.ocrPdf(arrayBuffer.slice(0), onStatus);
      } catch (ocrErr) {
        const prev = global.HDashboardOcr.getLastError && global.HDashboardOcr.getLastError();
        const detail = (ocrErr && ocrErr.message) || (prev && prev.message) || "OCR thất bại";
        throw new Error(detail);
      }
      usedOcr = true;
    }

    const stmt = parseInvoiceText(text);
    stmt.via_ocr = usedOcr;
    const transactions = await transactionsForDashboard(stmt);
    const reconciliation = reconcile(stmt, transactions);
    return { statement: stmt, transactions, reconciliation, via_ocr: usedOcr, raw_text: text };
  }

  global.HDashboardInvoiceParser = {
    SOURCE,
    parseInvoiceText,
    parseInvoicePdfArrayBuffer,
    transactionsForDashboard,
    reconcile,
  };
})(typeof window !== "undefined" ? window : globalThis);
