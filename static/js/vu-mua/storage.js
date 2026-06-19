/**
 * Vụ Mùa — local storage for agricultural sales records.
 *
 * 100% client-side. Records persist in localStorage (this browser only);
 * nothing is uploaded to any server (same security posture as F/H/L-Dashboard).
 * Use Export JSON/CSV to back up or move data between devices.
 */
(function (global) {
  "use strict";

  const LS_KEY = "vumua_records_v1";

  function safeParse(raw) {
    try {
      const data = JSON.parse(raw || "[]");
      return Array.isArray(data) ? data : [];
    } catch (_) {
      return [];
    }
  }

  function getAll() {
    try {
      return safeParse(localStorage.getItem(LS_KEY));
    } catch (_) {
      return [];
    }
  }

  function persist(records) {
    try {
      localStorage.setItem(LS_KEY, JSON.stringify(records || []));
      return true;
    } catch (_) {
      // Quota exceeded or private-mode storage disabled.
      return false;
    }
  }

  function makeId() {
    if (global.crypto && typeof global.crypto.randomUUID === "function") {
      return global.crypto.randomUUID();
    }
    return "vm-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 8);
  }

  function insert(record) {
    const records = getAll();
    const row = Object.assign(
      { id: makeId(), createdAt: new Date().toISOString() },
      record
    );
    records.push(row);
    persist(records);
    return row;
  }

  function remove(id) {
    const records = getAll().filter((r) => r.id !== id);
    persist(records);
    return records;
  }

  /** Replace the whole dataset (used by JSON import). Returns the saved array. */
  function replaceAll(records) {
    const clean = Array.isArray(records) ? records : [];
    persist(clean);
    return clean;
  }

  /** Merge imported records, skipping ids that already exist. Returns count added. */
  function merge(records) {
    if (!Array.isArray(records) || !records.length) return 0;
    const current = getAll();
    const seen = new Set(current.map((r) => r.id));
    let added = 0;
    records.forEach((r) => {
      if (!r || typeof r !== "object") return;
      const row = Object.assign({}, r);
      if (!row.id || seen.has(row.id)) row.id = makeId();
      seen.add(row.id);
      current.push(row);
      added += 1;
    });
    persist(current);
    return added;
  }

  function clearAll() {
    try {
      localStorage.removeItem(LS_KEY);
    } catch (_) {
      /* ignore */
    }
  }

  global.VuMuaStorage = { getAll, insert, remove, replaceAll, merge, clearAll, makeId };
})(typeof window !== "undefined" ? window : globalThis);
