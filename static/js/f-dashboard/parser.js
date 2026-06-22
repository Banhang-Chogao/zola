/**
 * VietinBank Excel parser — mirrors scripts/f_dashboard_parse_excel.py
 * Uses SheetJS (XLSX) loaded from CDN.
 */
(function (global) {
  "use strict";

  const SOURCE = "vietinbank";
  const HEADER_MARKERS = {
    stt: ["stt"],
    date: ["ngày", "ngay"],
    description: ["nội dung", "noi dung"],
    amount: ["số tiền gd", "so tien gd"],
    balance: ["số dư", "so du"],
  };

  function norm(text) {
    if (text == null) return "";
    return String(text).trim().toLowerCase().replace(/\s+/g, " ");
  }

  function parseNumber(value) {
    if (value == null || value === "") return null;
    if (typeof value === "number") return Math.round(value);

    let s = String(value).trim().replace(/,/g, "").replace(/\s/g, "");
    if (!s) return null;

    let sign = 1;
    if (s.startsWith("+")) s = s.slice(1);
    else if (s.startsWith("-")) {
      sign = -1;
      s = s.slice(1);
    }

    if (!/^\d+(\.\d+)?$/.test(s)) return null;
    return sign * Math.round(parseFloat(s));
  }

  function excelSerialToISO(serial) {
    if (typeof serial !== "number") return null;
    const utc = (serial - 25569) * 86400 * 1000;
    const d = new Date(utc);
    const pad = (n) => String(n).padStart(2, "0");
    return (
      d.getUTCFullYear() +
      "-" +
      pad(d.getUTCMonth() + 1) +
      "-" +
      pad(d.getUTCDate()) +
      "T" +
      pad(d.getUTCHours()) +
      ":" +
      pad(d.getUTCMinutes()) +
      ":" +
      pad(d.getUTCSeconds())
    );
  }

  function parseDate(value) {
    if (value == null || value === "") return null;
    if (typeof value === "number") return excelSerialToISO(value);
    if (value instanceof Date) {
      const pad = (n) => String(n).padStart(2, "0");
      return (
        value.getFullYear() +
        "-" +
        pad(value.getMonth() + 1) +
        "-" +
        pad(value.getDate()) +
        "T" +
        pad(value.getHours()) +
        ":" +
        pad(value.getMinutes()) +
        ":" +
        pad(value.getSeconds())
      );
    }

    const s = String(value).trim();
    const patterns = [
      /^(\d{2})\/(\d{2})\/(\d{4})\s+(\d{2}):(\d{2}):(\d{2})$/,
      /^(\d{2})\/(\d{2})\/(\d{4})\s+(\d{2}):(\d{2})$/,
      /^(\d{2})\/(\d{2})\/(\d{4})$/,
    ];
    for (const re of patterns) {
      const m = s.match(re);
      if (m) {
        const [, dd, mm, yyyy, hh = "00", mi = "00", ss = "00"] = m;
        return `${yyyy}-${mm}-${dd}T${hh}:${mi}:${ss}`;
      }
    }
    return null;
  }

  function amountType(amount, colorHint) {
    if (amount < 0) return "expense";
    if (amount > 0) return "income";
    if (colorHint === "expense" || colorHint === "income") return colorHint;
    return "expense";
  }

  async function sha256Hex(text) {
    const buf = new TextEncoder().encode(text);
    const hash = await crypto.subtle.digest("SHA-256", buf);
    return Array.from(new Uint8Array(hash))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
  }

  async function transactionId(date, description, amount, balance) {
    const payload = `${date}|${description}|${amount}|${balance}`;
    return sha256Hex(payload);
  }

  function findHeaderRow(rows) {
    for (let i = 0; i < rows.length; i++) {
      const cells = rows[i] || [];
      const norms = cells.map(norm);
      const cols = {};

      norms.forEach((text, colIdx) => {
        if (!text) return;
        Object.entries(HEADER_MARKERS).forEach(([key, markers]) => {
          if (cols[key] != null) return;
          if (markers.some((m) => text.includes(m))) cols[key] = colIdx;
        });
      });

      if (Object.keys(HEADER_MARKERS).every((k) => cols[k] != null)) {
        return { headerRow: i, cols };
      }
    }
    return null;
  }

  async function parseVietinbankArrayBuffer(buffer) {
    if (!global.XLSX) throw new Error("SheetJS (XLSX) chưa được tải");

    const wb = XLSX.read(buffer, { type: "array", cellStyles: true });
    const sheet = wb.Sheets[wb.SheetNames[0]];
    const rows = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: null, raw: true });

    const found = findHeaderRow(rows);
    if (!found) {
      throw new Error(
        "Không tìm thấy dòng tiêu đề bảng (STT / Ngày / Nội dung / Số tiền GD / Số dư)"
      );
    }

    const { headerRow, cols } = found;
    const transactions = [];

    for (let r = headerRow + 1; r < rows.length; r++) {
      const row = rows[r];
      if (!row) continue;

      const stt = row[cols.stt];
      if (stt == null || String(stt).trim() === "") continue;

      const dateIso = parseDate(row[cols.date]);
      const desc = row[cols.description] != null ? String(row[cols.description]).trim() : "";
      const amount = parseNumber(row[cols.amount]);
      const balance = parseNumber(row[cols.balance]);

      if (!dateIso || amount == null || balance == null) continue;

      const txType = amountType(amount, null);
      const txId = await transactionId(dateIso, desc, amount, balance);

      transactions.push({
        transaction_id: txId,
        date: dateIso,
        description: desc,
        amount,
        type: txType,
        balance,
        source: SOURCE,
      });
    }

    return transactions;
  }

  function mergeTransactions(parsed, existingIds) {
    const seen = new Set(existingIds || []);
    const inserted = [];
    const skipped = [];

    parsed.forEach((tx) => {
      if (seen.has(tx.transaction_id)) {
        skipped.push(tx);
      } else {
        inserted.push(tx);
        seen.add(tx.transaction_id);
      }
    });

    return { inserted, skipped };
  }

  global.FDashboardParser = {
    parseVietinbankArrayBuffer,
    mergeTransactions,
    transactionId,
    parseNumber,
    parseDate,
    amountType,
  };
})(typeof window !== "undefined" ? window : globalThis);