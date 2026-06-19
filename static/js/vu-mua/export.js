/**
 * Vụ Mùa — export / import helpers.
 *
 * Export JSON or CSV of the current records; import a previously exported JSON
 * back into local storage. All client-side — files never touch a server.
 */
(function (global) {
  "use strict";

  const FIELDS = ["product", "quantity", "type", "unitPrice", "total", "buyer", "date"];
  const HEADERS = [
    "TÊN HÀNG HOÁ",
    "SỐ LƯỢNG",
    "LOẠI",
    "ĐƠN GIÁ",
    "THÀNH TIỀN",
    "NGƯỜI MUA",
    "NGÀY MUA",
  ];

  function stamp() {
    const d = new Date();
    const p = (n) => String(n).padStart(2, "0");
    return d.getFullYear() + p(d.getMonth() + 1) + p(d.getDate()) + "-" + p(d.getHours()) + p(d.getMinutes());
  }

  function triggerDownload(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function exportJson(records) {
    const payload = {
      app: "vu-mua",
      version: 1,
      exported_at: new Date().toISOString(),
      count: records.length,
      records,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    triggerDownload(blob, "vu-mua-" + stamp() + ".json");
  }

  function csvCell(value) {
    const s = String(value == null ? "" : value);
    if (/[",\n;]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
    return s;
  }

  function exportCsv(records) {
    const lines = [HEADERS.join(",")];
    records.forEach((r) => {
      lines.push(FIELDS.map((f) => csvCell(r[f])).join(","));
    });
    // BOM so Excel reads UTF-8 (Vietnamese) correctly.
    const blob = new Blob(["﻿" + lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
    triggerDownload(blob, "vu-mua-" + stamp() + ".csv");
  }

  /** Parse an imported JSON file → array of records (Promise). Rejects on bad input. */
  function importJson(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        try {
          const data = JSON.parse(reader.result);
          const records = Array.isArray(data) ? data : data && data.records;
          if (!Array.isArray(records)) {
            reject(new Error("File không đúng định dạng Vụ Mùa."));
            return;
          }
          resolve(records);
        } catch (e) {
          reject(new Error("Không đọc được file JSON."));
        }
      };
      reader.onerror = () => reject(new Error("Lỗi khi đọc file."));
      reader.readAsText(file);
    });
  }

  global.VuMuaExport = { exportJson, exportCsv, importJson, FIELDS, HEADERS };
})(typeof window !== "undefined" ? window : globalThis);
