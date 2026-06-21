/**
 * IndexedDB + AES-GCM encrypted local storage for H-Dashboard.
 * Data never leaves the browser; not written to /static or /public.
 * Separate DB name from F/L dashboards so transaction data never mixes.
 */
(function (global) {
  "use strict";

  const DB_NAME = "h-dashboard-db";
  const DB_VERSION = 1;
  const STORE_TX = "transactions";
  const STORE_META = "meta";
  const CRYPTO_KEY_META = "crypto_key";
  const RECEIPTS_CATALOG_KEY = "receipts_catalog";

  function openDb() {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains(STORE_TX)) {
          const store = db.createObjectStore(STORE_TX, { keyPath: "transaction_id" });
          store.createIndex("date", "date", { unique: false });
          store.createIndex("type", "type", { unique: false });
        }
        if (!db.objectStoreNames.contains(STORE_META)) {
          db.createObjectStore(STORE_META, { keyPath: "key" });
        }
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }

  async function getOrCreateCryptoKey(db) {
    const existing = await getMeta(db, CRYPTO_KEY_META);
    if (existing) {
      const raw = Uint8Array.from(atob(existing), (c) => c.charCodeAt(0));
      return crypto.subtle.importKey("raw", raw, "AES-GCM", false, ["encrypt", "decrypt"]);
    }

    const key = await crypto.subtle.generateKey({ name: "AES-GCM", length: 256 }, true, [
      "encrypt",
      "decrypt",
    ]);
    const exported = await crypto.subtle.exportKey("raw", key);
    const b64 = btoa(String.fromCharCode(...new Uint8Array(exported)));
    await setMeta(db, CRYPTO_KEY_META, b64);
    return key;
  }

  function getMeta(db, key) {
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_META, "readonly");
      const req = tx.objectStore(STORE_META).get(key);
      req.onsuccess = () => resolve(req.result ? req.result.value : null);
      req.onerror = () => reject(req.error);
    });
  }

  function setMeta(db, key, value) {
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_META, "readwrite");
      tx.objectStore(STORE_META).put({ key, value });
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  }

  async function encryptPayload(key, obj) {
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const encoded = new TextEncoder().encode(JSON.stringify(obj));
    const cipher = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, encoded);
    return {
      iv: btoa(String.fromCharCode(...iv)),
      data: btoa(String.fromCharCode(...new Uint8Array(cipher))),
    };
  }

  async function decryptPayload(key, record) {
    const iv = Uint8Array.from(atob(record.iv), (c) => c.charCodeAt(0));
    const data = Uint8Array.from(atob(record.data), (c) => c.charCodeAt(0));
    const plain = await crypto.subtle.decrypt({ name: "AES-GCM", iv }, key, data);
    return JSON.parse(new TextDecoder().decode(plain));
  }

  async function getAllTransactionIds() {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_TX, "readonly");
      // Return a Set: callers dedupe via existingIds.has(id) (O(1) lookup).
      const ids = new Set();
      const req = tx.objectStore(STORE_TX).openKeyCursor();
      req.onsuccess = () => {
        const cursor = req.result;
        if (cursor) {
          ids.add(cursor.key);
          cursor.continue();
        } else {
          db.close();
          resolve(ids);
        }
      };
      req.onerror = () => reject(req.error);
    });
  }

  async function insertTransactions(newTxs) {
    const db = await openDb();
    const cryptoKey = await getOrCreateCryptoKey(db);

    const encryptedItems = await Promise.all(
      newTxs.map(async (item) => {
        const encrypted = await encryptPayload(cryptoKey, item);
        return { transaction_id: item.transaction_id, ...encrypted };
      })
    );

    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_TX, "readwrite");
      const store = tx.objectStore(STORE_TX);
      encryptedItems.forEach((item) => store.put(item));
      tx.oncomplete = () => {
        db.close();
        resolve(encryptedItems.length);
      };
      tx.onerror = () => reject(tx.error);
    });
  }

  async function getAllTransactions() {
    const db = await openDb();
    const cryptoKey = await getOrCreateCryptoKey(db);

    const records = await new Promise((resolve, reject) => {
      const results = [];
      const tx = db.transaction(STORE_TX, "readonly");
      const req = tx.objectStore(STORE_TX).openCursor();
      req.onsuccess = () => {
        const cursor = req.result;
        if (cursor) {
          results.push(cursor.value);
          cursor.continue();
        } else {
          resolve(results);
        }
      };
      req.onerror = () => reject(req.error);
      tx.oncomplete = () => db.close();
    });

    const decrypted = await Promise.all(records.map((r) => decryptPayload(cryptoKey, r)));
    decrypted.sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));
    return decrypted;
  }

  async function clearAll() {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction([STORE_TX, STORE_META], "readwrite");
      tx.objectStore(STORE_TX).clear();
      tx.objectStore(STORE_META).clear();
      tx.oncomplete = () => {
        db.close();
        resolve();
      };
      tx.onerror = () => reject(tx.error);
    });
  }

  async function getReceiptsCatalog() {
    const db = await openDb();
    const raw = await getMeta(db, RECEIPTS_CATALOG_KEY);
    db.close();
    if (!raw) return { fingerprints: [], statements: [] };
    try {
      const parsed = JSON.parse(raw);
      return {
        fingerprints: Array.isArray(parsed.fingerprints) ? parsed.fingerprints : [],
        statements: Array.isArray(parsed.statements) ? parsed.statements : [],
      };
    } catch (e) {
      return { fingerprints: [], statements: [] };
    }
  }

  async function setReceiptsCatalog(catalog) {
    const db = await openDb();
    await setMeta(db, RECEIPTS_CATALOG_KEY, JSON.stringify(catalog || { fingerprints: [], statements: [] }));
    db.close();
  }

  global.HDashboardStorage = {
    getAllTransactionIds,
    insertTransactions,
    getAllTransactions,
    clearAll,
    getReceiptsCatalog,
    setReceiptsCatalog,
  };
})(typeof window !== "undefined" ? window : globalThis);
