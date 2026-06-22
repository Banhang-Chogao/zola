/**
 * LPBank PDF statement parser — mirrors scripts/lpbank_parser.py
 * Uses pdf.js for text extraction, then shared line-based parser.
 */
(function (global) {
  "use strict";

  const SOURCE = "lpbank";
  const DATE_PATTERN = /^\d{2}\/\d{2}\/\d{4}$/;
  const ANCHOR_PATTERN = /(\d{2}\/\d{2}\/\d{4})\s+(\d{2}\/\d{2}\/\d{4}).*?(FT\d{14,})(.*)$/;
  const AMOUNT_PATTERN = /\d{1,3}(?:,\d{3})+|\d+/g;
  const FT_PATTERN = /FT\d{14,}/;

  const SKIP_LINE_MARKERS = [
    "sao kê tài khoản",
    "bank statement",
    "txn.date",
    "value date",
    "description",
    "txn.no",
    "debit",
    "credit",
    "balance",
    "ngày giao dịch",
    "ngày hiệu lực",
    "nội dung giao dịch",
    "số giao dịch",
    "ghi nợ",
    "ghi có",
    "số dư",
    "đề nghị quý khách",
    "please examine",
    "người ký",
    "ngân hàng thương mại",
    "printing branch",
    "printing time",
    "đơn vị in",
  ];

  function normLine(line) {
    return String(line).trim().replace(/\s+/g, " ");
  }

  function parseNumber(value) {
    if (value == null || value === "") return 0;
    const s = String(value).replace(/,/g, "").trim();
    return /^\d+$/.test(s) ? parseInt(s, 10) : 0;
  }

  function parseDateToIso(value) {
    const m = String(value).trim().match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
    if (!m) return value;
    return `${m[3]}-${m[2]}-${m[1]}`;
  }

  function shouldSkipLine(line) {
    const low = line.toLowerCase();
    return SKIP_LINE_MARKERS.some((m) => low.includes(m));
  }

  function isFooterLine(line) {
    const low = line.toLowerCase();
    return (
      low.includes("cộng doanh số") ||
      low.includes("total") ||
      low.includes("số dư cuối kỳ") ||
      low.includes("ending balance") ||
      low.includes("opening balance") ||
      low.includes("số dư đầu kỳ")
    );
  }

  function interpretAmounts(amounts, prevBalance) {
    if (!amounts.length) return { debit: 0, credit: 0, balance: prevBalance };

    if (amounts.length >= 3) {
      const balance = amounts[amounts.length - 1];
      const credit = amounts[amounts.length - 2];
      const debit = amounts[amounts.length - 3];
      return { debit, credit, balance };
    }

    const balance = amounts[amounts.length - 1];
    const txnAmount = amounts.length >= 2 ? amounts[amounts.length - 2] : 0;

    if (balance > prevBalance) return { debit: 0, credit: txnAmount, balance };
    if (balance < prevBalance) return { debit: txnAmount, credit: 0, balance };
    if (txnAmount && prevBalance > 0) return { debit: txnAmount, credit: 0, balance };
    if (txnAmount) return { debit: 0, credit: txnAmount, balance };
    return { debit: 0, credit: 0, balance };
  }

  function parseMetadata(text, stmt) {
    const flat = text.replace(/\s+/g, " ");

    let m = flat.match(/Tên tài khoản\s*\/\s*Account name:\s*([^/]+?)(?:Mã khách hàng|CIF)/i);
    if (m) stmt.account_name = m[1].trim();

    m = flat.match(/Số tài khoản\s*\/\s*Account number:\s*(\d+)/i);
    if (m) stmt.account_number = m[1].trim();

    m = flat.match(/Tên khách hàng\s*\/\s*Customer name:\s*([^/]+?)(?:Địa chỉ|Address)/i);
    if (m) stmt.customer_name = m[1].trim();

    m = flat.match(/CIF No:\s*(\d+)/i);
    if (m) stmt.cif_no = m[1].trim();

    m = flat.match(/Currency:\s*([A-Z]{3})/i);
    if (m) stmt.currency = m[1].trim();

    m = flat.match(/From Date\):\s*(\d{2}\/\d{2}\/\d{4})/i);
    if (m) stmt.from_date = parseDateToIso(m[1]);

    m = flat.match(/To Date\):\s*(\d{2}\/\d{2}\/\d{4})/i);
    if (m) stmt.to_date = parseDateToIso(m[1]);

    m = flat.match(/Printing date:\s*(\d{2}\/\d{2}\/\d{4})/i);
    if (m) stmt.printing_date = parseDateToIso(m[1]);

    m = flat.match(/Printing time:\s*(\d{2}:\d{2})/i);
    if (m) stmt.printing_time = m[1].trim();

    const lines = text.split(/\r?\n/);
    for (let i = 0; i < lines.length; i++) {
      const low = lines[i].toLowerCase();
      if (low.includes("opening balance") || low.includes("số dư đầu kỳ")) {
        for (let j = i; j < Math.min(i + 6, lines.length); j++) {
          const lone = normLine(lines[j]);
          if (/^\d[\d,]*$/.test(lone)) {
            stmt.opening_balance = parseNumber(lone);
            break;
          }
        }
        break;
      }
    }

    m = text.match(/Cộng doanh số[\s\S]*?(\d[\d,]*)\s+(\d[\d,]*)[\s\S]*?Total/i);
    if (m) {
      stmt.total_debit = parseNumber(m[1]);
      stmt.total_credit = parseNumber(m[2]);
    }

    m = text.match(/Ending Balance\s*(\d[\d,]*)/i);
    if (!m) m = text.match(/Số dư cuối kỳ\s*(\d[\d,]*)/i);
    if (m) stmt.ending_balance = parseNumber(m[1]);
  }

  function parseAnchorLine(line, prevBalance) {
    const m = line.match(ANCHOR_PATTERN);
    if (!m) return null;

    const txnDate = parseDateToIso(m[1]);
    const valueDate = parseDateToIso(m[2]);
    const txnNo = m[3];
    const tail = m[4] || "";
    const amounts = (tail.match(AMOUNT_PATTERN) || []).map(parseNumber);
    const { debit, credit, balance } = interpretAmounts(amounts, prevBalance);

    const inline = line.slice(0, m.index + m[0].indexOf(txnNo)).replace(/^\d{2}\/\d{2}\/\d{4}\s+\d{2}\/\d{2}\/\d{4}\s*/, "").trim();

    return {
      txn_date: txnDate,
      value_date: valueDate,
      description: inline,
      txn_no: txnNo,
      debit,
      credit,
      balance,
    };
  }

  function parseLpbankText(text) {
    const stmt = {
      source: SOURCE,
      account_name: "",
      account_number: "",
      customer_name: "",
      cif_no: "",
      currency: "VND",
      from_date: "",
      to_date: "",
      printing_date: "",
      printing_time: "",
      opening_balance: 0,
      ending_balance: 0,
      total_debit: 0,
      total_credit: 0,
      transactions: [],
    };

    parseMetadata(text, stmt);

    const lines = text.split(/\r?\n/).map(normLine).filter(Boolean);
    let prevBalance = stmt.opening_balance;
    let pendingDesc = [];
    let current = null;

    for (const line of lines) {
      if (shouldSkipLine(line)) continue;
      if (/^\d{1,2}$/.test(line)) continue;

      if (line.toLowerCase().includes("cộng doanh số")) {
        if (current) {
          stmt.transactions.push(current);
          current = null;
        }
        break;
      }

      if (isFooterLine(line)) continue;

      if (ANCHOR_PATTERN.test(line)) {
        if (current) {
          const extra = pendingDesc.join(" ").trim();
          if (extra) current.description = (current.description + " " + extra).trim();
          stmt.transactions.push(current);
          prevBalance = current.balance;
        }

        current = parseAnchorLine(line, prevBalance);
        const descParts = pendingDesc.slice();
        pendingDesc = [];
        if (current.description) descParts.push(current.description);
        current.description = descParts.join(" ").trim();
        continue;
      }

      if (FT_PATTERN.test(line) && !ANCHOR_PATTERN.test(line)) continue;

      if (DATE_PATTERN.test((line.split(" ")[0] || ""))) continue;

      if (current) {
        pendingDesc.push(line);
      } else if (!line.toLowerCase().includes("opening balance") && !line.toLowerCase().includes("số dư đầu kỳ")) {
        pendingDesc.push(line);
      }
    }

    if (current) {
      const extra = pendingDesc.join(" ").trim();
      if (extra) current.description = (current.description + " " + extra).trim();
      stmt.transactions.push(current);
    }

    return stmt;
  }

  async function sha256Hex(text) {
    const buf = new TextEncoder().encode(text);
    const hash = await crypto.subtle.digest("SHA-256", buf);
    return Array.from(new Uint8Array(hash))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
  }

  async function transactionId(txn) {
    const payload = `${txn.txn_date}|${txn.description}|${txn.debit}|${txn.credit}|${txn.balance}|${txn.txn_no}`;
    return sha256Hex(payload);
  }

  async function transactionsForDashboard(stmt) {
    const rows = [];
    for (const t of stmt.transactions) {
      const amount = t.credit > 0 ? t.credit : -t.debit;
      rows.push({
        source: SOURCE,
        date: `${t.txn_date}T00:00:00`,
        value_date: t.value_date,
        description: t.description,
        txn_no: t.txn_no,
        debit: t.debit,
        credit: t.credit,
        balance: t.balance,
        amount,
        type: t.credit > 0 ? "income" : "expense",
        transaction_id: await transactionId(t),
      });
    }
    return rows;
  }

  function reconcile(stmt) {
    const sumDebit = stmt.transactions.reduce((s, t) => s + t.debit, 0);
    const sumCredit = stmt.transactions.reduce((s, t) => s + t.credit, 0);
    const okDebit = !stmt.total_debit || sumDebit === stmt.total_debit;
    const okCredit = !stmt.total_credit || sumCredit === stmt.total_credit;
    const okEnding =
      !stmt.transactions.length ||
      stmt.transactions[stmt.transactions.length - 1].balance === stmt.ending_balance;
    const ok = okDebit && okCredit && okEnding;
    return {
      ok,
      sum_debit: sumDebit,
      sum_credit: sumCredit,
      expected_debit: stmt.total_debit,
      expected_credit: stmt.total_credit,
      expected_ending: stmt.ending_balance,
      message: ok ? "" : "Có thể parser chưa đọc đúng định dạng sao kê",
    };
  }

  async function extractPdfText(arrayBuffer) {
    if (global.LDashboardPdf && typeof global.LDashboardPdf.ensureReady === "function") {
      await global.LDashboardPdf.ensureReady();
    }
    const pdfjs = global.pdfjsLib;
    if (!pdfjs) {
      const hint =
        global.LDashboardPdf && global.LDashboardPdf.getLastError
          ? global.LDashboardPdf.getLastError()
          : null;
      throw new Error(
        hint && hint.message
          ? hint.message
          : "pdf.js chưa tải — không thể đọc PDF LPBank"
      );
    }

    let pdf;
    try {
      const loadingTask = pdfjs.getDocument({ data: arrayBuffer });
      pdf = await loadingTask.promise;
    } catch (firstErr) {
      if (global.LDashboardPdf && typeof global.LDashboardPdf.retryWithCdnWorker === "function") {
        await global.LDashboardPdf.retryWithCdnWorker();
        const retryTask = pdfjs.getDocument({ data: arrayBuffer });
        pdf = await retryTask.promise;
      } else {
        throw firstErr;
      }
    }
    const chunks = [];

    for (let i = 1; i <= pdf.numPages; i++) {
      const page = await pdf.getPage(i);
      const content = await page.getTextContent();
      const lines = groupTextItemsToLines(content.items);
      chunks.push(lines.join("\n"));
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

  async function parseLpbankPdfArrayBuffer(arrayBuffer) {
    const text = await extractPdfText(arrayBuffer);
    const stmt = parseLpbankText(text);
    const transactions = await transactionsForDashboard(stmt);
    const reconciliation = reconcile(stmt);
    return { statement: stmt, transactions, reconciliation };
  }

  global.LDashboardLpbankParser = {
    SOURCE,
    parseLpbankText,
    parseLpbankPdfArrayBuffer,
    reconcile,
    transactionsForDashboard,
  };
})(typeof window !== "undefined" ? window : globalThis);