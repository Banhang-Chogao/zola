/**
 * Stats tracking and display for Admin Zone
 * Data persisted in localStorage with fallback to zero defaults
 */

(function () {
  window.AdminZoneStats = window.AdminZoneStats || {};

  const STATS_KEY = "admin-zone-stats";
  const STATS_START_DATE = new Date("2026-06-14").getTime();

  function getStats() {
    try {
      const data = localStorage.getItem(STATS_KEY);
      if (!data) return getDefaultStats();
      const parsed = JSON.parse(data);
      // Validate structure
      if (typeof parsed.totalRuns !== "number" || typeof parsed.successCount !== "number" || typeof parsed.failureCount !== "number") {
        return getDefaultStats();
      }
      return parsed;
    } catch (e) {
      return getDefaultStats();
    }
  }

  function getDefaultStats() {
    return {
      totalRuns: 0,
      successCount: 0,
      failureCount: 0,
      lastUpdated: new Date().toISOString(),
    };
  }

  function saveStats(stats) {
    try {
      stats.lastUpdated = new Date().toISOString();
      localStorage.setItem(STATS_KEY, JSON.stringify(stats));
    } catch (e) {
      // Silent fail — localStorage might be full or disabled
    }
  }

  function incrementRun(success = true) {
    const stats = getStats();
    stats.totalRuns++;
    if (success) {
      stats.successCount++;
    } else {
      stats.failureCount++;
    }
    saveStats(stats);
    displayStats();
  }

  function displayStats() {
    const stats = getStats();

    // Update display
    const totalRunsEl = document.querySelector('[data-stat="total-runs"]');
    const successEl = document.querySelector('[data-stat="success-count"]');
    const failureEl = document.querySelector('[data-stat="failure-count"]');
    const updatedAtEl = document.querySelector('[data-stat="updated-at"]');

    if (totalRunsEl) totalRunsEl.textContent = stats.totalRuns;
    if (successEl) successEl.textContent = stats.successCount;
    if (failureEl) failureEl.textContent = stats.failureCount;

    if (updatedAtEl) {
      const dt = new Date(stats.lastUpdated);
      const formatted = dt.toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" });
      updatedAtEl.textContent = formatted;
    }
  }

  Object.assign(window.AdminZoneStats, {
    getStats,
    saveStats,
    incrementRun,
    displayStats,
    STATS_START_DATE,
  });
})();
