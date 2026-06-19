/**
 * H-Dashboard — Import & merge previous reports (JSON preferred, PDF fallback).
 */
(function (global) {
  "use strict";

  function isJsonFile(file) {
    return /\.json$/i.test(file.name) || file.type === "application/json";
  }

  function isPdfFile(file) {
    return /\.pdf$/i.test(file.name) || file.type === "application/pdf";
  }

  function normalizeImportedPayload(raw) {
    if (!raw || typeof raw !== "object") {
      throw new Error("JSON không hợp lệ — thiếu object gốc.");
    }
    if (raw.source && raw.source !== "h-dashboard") {
      console.warn("[H-Dashboard Import] source:", raw.source);
    }
    const txs = Array.isArray(raw.transactions) ? raw.transactions : [];
    if (!txs.length) {
      throw new Error("JSON không chứa transactions — không thể merge.");
    }
    return {
      transactions: txs,
      summary: raw.summary || null,
      coffee: raw.coffee || null,
      exported_at: raw.exported_at || null,
      series_id: raw.series_id || null,
      receipts_catalog: raw.receipts_catalog || null,
    };
  }

  async function importJsonFile(file) {
    const text = await file.text();
    let parsed;
    try {
      parsed = JSON.parse(text);
    } catch (e) {
      throw new Error("Không parse được JSON: " + file.name);
    }
    return normalizeImportedPayload(parsed);
  }

  async function importPdfFile(file, onStatus) {
    const notify = typeof onStatus === "function" ? onStatus : function () {};
    if (!global.HDashboardInvoiceParser || !global.HDashboardInvoiceParser.parseInvoicePdfArrayBuffer) {
      throw new Error("Invoice parser chưa tải.");
    }
    notify("Đang thử đọc PDF như hóa đơn: " + file.name + "…");
    const buffer = await file.arrayBuffer();
    try {
      const parsed = await global.HDashboardInvoiceParser.parseInvoicePdfArrayBuffer(buffer, {
        onStatus: notify,
      });
      if (parsed && parsed.transactions && parsed.transactions.length) {
        return {
          transactions: parsed.transactions,
          summary: null,
          coffee: null,
          via_pdf_receipt: true,
          statement: parsed.statement,
        };
      }
    } catch (e) {
      console.warn("[H-Dashboard Import] PDF receipt parse failed:", e);
    }
    throw new Error(
      "This PDF lacks machine-readable data. Please import the JSON file for better accuracy."
    );
  }

  /**
   * Merge imported reports into session (dedupe by transaction_id + receipt fingerprint).
   * @returns {{ merged: number, skipped: number, duplicates: number, warnings: string[] }}
   */
  async function mergeImportedFiles(fileList, hooks) {
    const files = Array.from(fileList || []);
    if (!files.length) throw new Error("Chọn ít nhất một file JSON hoặc PDF.");

    const onStatus = hooks && hooks.onStatus ? hooks.onStatus : function () {};
    const getCatalog = hooks && hooks.getCatalog ? hooks.getCatalog : async () => ({ fingerprints: [], statements: [] });
    const saveCatalog = hooks && hooks.saveCatalog ? hooks.saveCatalog : async () => {};
    const getExistingIds = hooks && hooks.getExistingIds ? hooks.getExistingIds : async () => new Set();
    const insertTx = hooks && hooks.insertTx ? hooks.insertTx : async () => 0;
    const buildFingerprint =
      hooks && hooks.buildFingerprint
        ? hooks.buildFingerprint
        : async () => "";

    const catalog = await getCatalog();
    const fpSet = new Set(catalog.fingerprints || []);
    const existingIds = await getExistingIds();

    const result = { merged: 0, skipped: 0, duplicates: 0, warnings: [] };

    for (const file of files) {
      onStatus("Đang import " + file.name + "…");
      let imported;
      try {
        if (isJsonFile(file)) {
          imported = await importJsonFile(file);
        } else if (isPdfFile(file)) {
          imported = await importPdfFile(file, onStatus);
        } else {
          result.warnings.push("Bỏ qua " + file.name + " — chỉ hỗ trợ .json / .pdf");
          continue;
        }
      } catch (err) {
        result.warnings.push(err.message || String(err));
        continue;
      }

      if (imported.receipts_catalog && Array.isArray(imported.receipts_catalog.fingerprints)) {
        imported.receipts_catalog.fingerprints.forEach((fp) => fpSet.add(fp));
        if (Array.isArray(imported.receipts_catalog.statements)) {
          if (!catalog.statements) catalog.statements = [];
          catalog.statements.push(...imported.receipts_catalog.statements);
        }
      }

      if (imported.statement && buildFingerprint) {
        const fp = await buildFingerprint(imported.statement);
        if (fpSet.has(fp)) {
          result.duplicates++;
          const inv = imported.statement.invoice_no || "?";
          result.warnings.push("Skipped duplicate receipt #" + inv);
          continue;
        }
        fpSet.add(fp);
        if (!catalog.statements) catalog.statements = [];
        catalog.statements.push({
          invoice_no: imported.statement.invoice_no,
          merchant: imported.statement.merchant,
          invoice_date: imported.statement.invoice_date,
          total: imported.statement.total,
          item_count: imported.statement.item_count,
        });
      }

      catalog.fingerprints = Array.from(fpSet);

      const toInsert = [];
      for (const tx of imported.transactions) {
        if (!tx.transaction_id) continue;
        if (existingIds.has(tx.transaction_id)) {
          result.skipped++;
        } else {
          toInsert.push(tx);
          existingIds.add(tx.transaction_id);
        }
      }

      if (toInsert.length) {
        await insertTx(toInsert);
        result.merged += toInsert.length;
      }
    }

    await saveCatalog(catalog);
    return result;
  }

  global.HDashboardImport = {
    importJsonFile,
    importPdfFile,
    mergeImportedFiles,
    normalizeImportedPayload,
  };
})(typeof window !== "undefined" ? window : globalThis);