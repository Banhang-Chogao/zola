/**
 * Liobank by OCB PDF statement parser.
 * Adapted from the LPBank parser, but for the Liobank-by-OCB statement layout.
 *
 * Main table columns:
 *   Ngày GD | Nội dung | Số tiền ghi có | Số tiền ghi nợ | Phí | Số dư
 *
 * Uses pdf.js for text extraction (ODashboardPdf loader), then a line-based
 * parser. Emits the SAME transaction schema the insights/charts/export expect:
 *   { transaction_id, date (ISO), description, credit, debit, fee, balance,
 *     amount, type }  where amount = credit - debit - fee (signed).
 */
(function (global) {
  "use strict";

  const SOURCE = "liobank";

  // Liobank dates are DD-MM-YYYY. Time HH:MM:SS may follow on the same line OR
  // arrive as a separate text token/line (PDF column splitting).
  const ROW_DATE_RE = /^(\d{2})-(\d{2})-(\d{4})\b/;
  const TIME_RE = /\b(\d{2}:\d{2}:\d{2})\b/;
  // Vietnamese integer with "." thousands separators (e.g. 1.296.314) or bare digits.
  const AMOUNT_TOKEN_RE = /\d{1,3}(?:\.\d{3})+|\d+/g;
  // A standalone numeric/dash cell token (used to peel trailing columns).
  const DASH_RE = /^[-–—]$/;

  // Lines belonging to the issuer header / metadata block — skipped as rows.
  const SKIP_LINE_MARKERS = [
    "liobank by ocb",
    "ngân hàng tmcp phương đông",
    "the hallmark",
    "sao kê tài khoản",
    "account statement",
    "ngày gd",
    "nội dung",
    "số tiền ghi có",
    "số tiền ghi nợ",
    "số dư",
    "trang ",
    "page ",
    "loại tiền",
    "số tài khoản",
    "số cccd",
    "tên khách hàng",
    "địa chỉ",
  ];

  // Secondary "auto-savings (TKTG)" table on the last page — must NOT corrupt
  // the main table. Detect its header and stop parsing main rows there.
  const TKTG_MARKERS = [
    "tiết kiệm tự động",
    "tktg",
    "số tiền gửi vào",
    "số tiền rút ra",
    "lãi tktg",
    "số dư tktg",
  ];

  function normLine(line) {
    return String(line).trim().replace(/\s+/g, " ");
  }

  function parseNumber(value) {
    if (value == null) return 0;
    const raw = String(value).trim();
    if (raw === "" || DASH_RE.test(raw)) return 0;
    // Strip "." thousands separators (and stray spaces); keep digits only.
    const s = raw.replace(/[.\s]/g, "");
    return /^\d+$/.test(s) ? parseInt(s, 10) : 0;
  }

  function parseDateToIso(dd, mm, yyyy, time) {
    const t = time && /^\d{2}:\d{2}:\d{2}$/.test(time) ? time : "00:00:00";
    return `${yyyy}-${mm}-${dd}T${t}`;
  }

  function lineHasAny(line, markers) {
    const low = line.toLowerCase();
    return markers.some((m) => low.includes(m));
  }

  function isTktgHeader(line) {
    return lineHasAny(line, TKTG_MARKERS);
  }

  function isFooterLine(line) {
    const low = line.toLowerCase();
    return (
      low.includes("tổng phát sinh") ||
      low.includes("số dư cuối kỳ") ||
      low.includes("số dư đầu kỳ") ||
      low.includes("cộng phát sinh") ||
      low.includes("tổng cộng")
    );
  }

  function isMainTableHeader(line) {
    const low = line.toLowerCase();
    // Header row has at least the credit + debit + balance column captions.
    return (
      low.includes("ngày gd") &&
      (low.includes("ghi có") || low.includes("ghi nợ")) &&
      low.includes("số dư")
    );
  }

  /**
   * Reconstruct {credit, debit, fee, balance} from the trailing numeric cells
   * of a row. PDF extraction may keep dashes "-" for empty cells OR drop them
   * entirely, so we combine positional reading with a balance-delta fallback.
   *
   * @param cells  array of trailing cell tokens (strings: numbers or dashes)
   * @param prevBalance  running balance before this row
   */
  function interpretCells(cells, prevBalance) {
    // Map each trailing cell to a number; remember which were present (incl. dash).
    const nums = cells.map(parseNumber);

    // Balance is the last numeric cell on the row.
    const balance = nums.length ? nums[nums.length - 1] : prevBalance;

    if (cells.length >= 4) {
      // Full positional row: credit, debit, fee, balance.
      const credit = nums[nums.length - 4];
      const debit = nums[nums.length - 3];
      const fee = nums[nums.length - 2];
      return { credit, debit, fee, balance };
    }

    // Fewer cells survived extraction → infer direction from balance delta.
    // The non-balance numbers are the transaction amount (+ optional fee).
    const others = nums.slice(0, Math.max(0, nums.length - 1)).filter((n) => n > 0);
    const delta = balance - prevBalance;

    if (others.length === 0) {
      return { credit: 0, debit: 0, fee: 0, balance };
    }

    // Largest "other" number is the principal; any remainder is treated as fee.
    others.sort((a, b) => b - a);
    const principal = others[0];
    const fee = others.length > 1 ? others.slice(1).reduce((s, v) => s + v, 0) : 0;

    if (delta > 0) {
      return { credit: principal, debit: 0, fee, balance };
    }
    if (delta < 0) {
      return { credit: 0, debit: principal, fee, balance };
    }
    // delta == 0 (or unknown prevBalance): default to debit (outflow) unless
    // prevBalance is unset.
    if (prevBalance > 0) return { credit: 0, debit: principal, fee, balance };
    return { credit: principal, debit: 0, fee, balance };
  }

  /**
   * Parse one transaction row from its combined text. The row begins with a
   * DD-MM-YYYY date; the time (HH:MM:SS), the description and the trailing money
   * cells (credit, debit, fee, balance) may all have arrived on the SAME line
   * or across several lines — the caller joins them before calling this so split
   * columns are handled uniformly.
   */
  function parseRow(rowText, prevBalance) {
    const dm = rowText.match(ROW_DATE_RE);
    if (!dm) return null;
    const [, dd, mm, yyyy] = dm;

    let rest = rowText.slice(dm[0].length).trim();

    // Time may be inline right after the date, or anywhere in the joined row.
    let time = "";
    const tm = rest.match(/^(\d{2}:\d{2}:\d{2})\b/);
    if (tm) {
      time = tm[1];
      rest = rest.slice(tm[0].length).trim();
    } else {
      const anyTime = rest.match(TIME_RE);
      if (anyTime) {
        time = anyTime[1];
        // Remove that time token from the description stream.
        rest = (rest.slice(0, anyTime.index) + rest.slice(anyTime.index + anyTime[1].length)).trim();
      }
    }

    // Locate the money columns (credit, debit, fee, balance). They form the LAST
    // contiguous run of numeric/dash tokens in the row. Scanning for the last
    // run (rather than only the very end) tolerates a description fragment that
    // the PDF placed AFTER the amounts. Tokens outside the run are description.
    const tokens = rest.split(/\s+/).filter(Boolean);
    const isCell = (tok) =>
      DASH_RE.test(tok) || /^\d{1,3}(?:\.\d{3})+$|^\d+$/.test(tok);

    let runEnd = -1;
    for (let i = tokens.length - 1; i >= 0; i--) {
      if (isCell(tokens[i])) {
        runEnd = i;
        break;
      }
    }
    let trailing = [];
    let descParts = tokens;
    if (runEnd >= 0) {
      let runStart = runEnd;
      while (runStart - 1 >= 0 && isCell(tokens[runStart - 1])) runStart--;
      trailing = tokens.slice(runStart, runEnd + 1);
      descParts = tokens.slice(0, runStart).concat(tokens.slice(runEnd + 1));
    }

    const description = descParts.join(" ").trim();
    const { credit, debit, fee, balance } = interpretCells(trailing, prevBalance);

    return {
      date: parseDateToIso(dd, mm, yyyy, time),
      description,
      credit,
      debit,
      fee,
      balance,
    };
  }

  function parseMetadata(text, stmt) {
    const flat = text.replace(/\s+/g, " ");
    let m;

    m = flat.match(/Số tài khoản:?\s*([0-9]+)/i);
    if (m) stmt.account_number = m[1].trim();

    m = flat.match(/Tên khách hàng:?\s*([^:]+?)(?:Số CCCD|Loại tiền|Địa chỉ|$)/i);
    if (m) stmt.customer_name = m[1].trim();

    m = flat.match(/Số CCCD:?\s*([0-9]+)/i);
    if (m) stmt.cccd = m[1].trim();

    m = flat.match(/Loại tiền:?\s*([A-Z]{3})/i);
    if (m) stmt.currency = m[1].trim();

    // Từ/đến: DD-MM-YYYY - DD-MM-YYYY
    m = flat.match(/(?:Từ\/đến|Từ ngày)\s*:?\s*(\d{2})-(\d{2})-(\d{4})\s*[-–]\s*(\d{2})-(\d{2})-(\d{4})/i);
    if (m) {
      stmt.from_date = `${m[3]}-${m[2]}-${m[1]}`;
      stmt.to_date = `${m[6]}-${m[5]}-${m[4]}`;
    }

    m = flat.match(/Số dư đầu kỳ:?\s*([\d.]+)/i);
    if (m) stmt.opening_balance = parseNumber(m[1]);

    m = flat.match(/Số dư cuối kỳ:?\s*([\d.]+)/i);
    if (m) stmt.ending_balance = parseNumber(m[1]);

    m = flat.match(/Tổng phát sinh có(?:\s*trong kỳ)?:?\s*([\d.]+)/i);
    if (m) stmt.total_credit = parseNumber(m[1]);

    m = flat.match(/Tổng phát sinh nợ(?:\s*trong kỳ)?:?\s*([\d.]+)/i);
    if (m) stmt.total_debit = parseNumber(m[1]);
  }

  function parseLiobankText(text) {
    const stmt = {
      source: SOURCE,
      bank: "Liobank by OCB",
      account_number: "",
      customer_name: "",
      cccd: "",
      currency: "VND",
      from_date: "",
      to_date: "",
      opening_balance: 0,
      ending_balance: 0,
      total_debit: 0,
      total_credit: 0,
      transactions: [],
    };

    parseMetadata(text, stmt);

    const lines = text.split(/\r?\n/).map(normLine).filter(Boolean);
    let prevBalance = stmt.opening_balance;
    let inMainTable = false;
    let stop = false;

    // Buffer all text lines belonging to the current row (the date line plus any
    // continuation lines that carry a split time / description / money cells).
    // The row is parsed only once the NEXT date / footer / TKTG arrives, so
    // columns the PDF split across lines are reassembled before parsing.
    let rowLines = [];

    function flushRow() {
      if (!rowLines.length) return;
      const row = parseRow(rowLines.join(" "), prevBalance);
      rowLines = [];
      if (row) {
        stmt.transactions.push(row);
        prevBalance = row.balance;
      }
    }

    for (const line of lines) {
      if (stop) break;

      // Enter main-table mode at its header row; ignore everything before it.
      if (!inMainTable) {
        if (isMainTableHeader(line)) inMainTable = true;
        continue;
      }

      // Stop the MAIN table when the TKTG (auto-savings) section starts.
      if (isTktgHeader(line)) {
        flushRow();
        stop = true;
        break;
      }

      if (isFooterLine(line)) {
        flushRow();
        continue;
      }

      if (lineHasAny(line, SKIP_LINE_MARKERS)) continue;

      if (ROW_DATE_RE.test(line)) {
        // New row begins → finalize the previous one, start buffering this one.
        flushRow();
        rowLines.push(line);
        continue;
      }

      // Continuation line (split time / description / money cells) for the row
      // currently being buffered. Lines before the first row are ignored.
      if (rowLines.length) {
        rowLines.push(line);
      }
    }

    flushRow();
    return stmt;
  }

  async function sha256Hex(text) {
    const buf = new TextEncoder().encode(text);
    const hash = await crypto.subtle.digest("SHA-256", buf);
    return Array.from(new Uint8Array(hash))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
  }

  async function transactionId(txn, amount) {
    // SHA256 of date + "|" + description + "|" + amount + "|" + balance
    const payload = `${txn.date}|${txn.description}|${amount}|${txn.balance}`;
    return sha256Hex(payload);
  }

  async function transactionsForDashboard(stmt) {
    const rows = [];
    for (const t of stmt.transactions) {
      // Signed amount: + income, - expense. Fee always reduces the amount.
      const amount = t.credit - t.debit - t.fee;
      rows.push({
        source: SOURCE,
        date: t.date,
        description: t.description,
        credit: t.credit,
        debit: t.debit,
        fee: t.fee,
        balance: t.balance,
        amount,
        type: amount >= 0 ? "income" : "expense",
        transaction_id: await transactionId(t, amount),
      });
    }
    return rows;
  }

  function reconcile(stmt) {
    const sumCredit = stmt.transactions.reduce((s, t) => s + t.credit, 0);
    const sumDebit = stmt.transactions.reduce((s, t) => s + t.debit, 0);
    const sumFee = stmt.transactions.reduce((s, t) => s + t.fee, 0);
    const okCredit = !stmt.total_credit || sumCredit === stmt.total_credit;
    const okDebit = !stmt.total_debit || sumDebit + sumFee === stmt.total_debit || sumDebit === stmt.total_debit;
    const okEnding =
      !stmt.transactions.length ||
      !stmt.ending_balance ||
      stmt.transactions[stmt.transactions.length - 1].balance === stmt.ending_balance;
    const ok = okCredit && okDebit && okEnding;
    return {
      ok,
      sum_credit: sumCredit,
      sum_debit: sumDebit,
      sum_fee: sumFee,
      expected_credit: stmt.total_credit,
      expected_debit: stmt.total_debit,
      expected_ending: stmt.ending_balance,
      message: ok ? "" : "Có thể parser chưa đọc đúng định dạng sao kê Liobank",
    };
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

  async function extractPdfText(arrayBuffer) {
    if (global.ODashboardPdf && typeof global.ODashboardPdf.ensureReady === "function") {
      await global.ODashboardPdf.ensureReady();
    }
    const pdfjs = global.pdfjsLib;
    if (!pdfjs) {
      const hint =
        global.ODashboardPdf && global.ODashboardPdf.getLastError
          ? global.ODashboardPdf.getLastError()
          : null;
      throw new Error(
        hint && hint.message
          ? hint.message
          : "pdf.js chưa tải — không thể đọc PDF Liobank (OCB)"
      );
    }

    let pdf;
    try {
      const loadingTask = pdfjs.getDocument({ data: arrayBuffer });
      pdf = await loadingTask.promise;
    } catch (firstErr) {
      if (global.ODashboardPdf && typeof global.ODashboardPdf.retryWithCdnWorker === "function") {
        await global.ODashboardPdf.retryWithCdnWorker();
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

  async function parseLiobankPdfArrayBuffer(arrayBuffer) {
    const text = await extractPdfText(arrayBuffer);
    const stmt = parseLiobankText(text);
    const transactions = await transactionsForDashboard(stmt);
    const reconciliation = reconcile(stmt);
    return { statement: stmt, transactions, reconciliation };
  }

  global.ODashboardLiobankParser = {
    SOURCE,
    parseLiobankText,
    parseLiobankPdfArrayBuffer,
    reconcile,
    transactionsForDashboard,
  };
})(typeof window !== "undefined" ? window : globalThis);
