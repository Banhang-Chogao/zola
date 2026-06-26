/**
 * GA Stats Smart Refresh — production-standard dashboard updates.
 *
 * Features:
 * - Partial card updates every 60 seconds (no full page rerender)
 * - Debounce: prevents overlapping GA API calls
 * - Single-flight request lock: only 1 request in-flight at a time
 * - Cache responses for 50–60 seconds
 * - Graceful error handling: shows error state, doesn't silent-fail
 */

(function () {
  const GA_REFRESH_INTERVAL = 60 * 1000; // 60 seconds
  const GA_CACHE_TTL = 55 * 1000; // 55 seconds (5s buffer)
  const GA_REQUEST_TIMEOUT = 8000; // 8 second timeout

  let lastFetchTime = 0;
  let cachedData = null;
  let requestInFlight = false;

  /**
   * Fetch GA stats from /static/data/ga-stats.json (pre-rendered by build).
   * Returns cached data if fresh enough, otherwise fetches live.
   */
  async function fetchGAStats() {
    const now = Date.now();

    // Return cached data if still fresh
    if (cachedData && now - lastFetchTime < GA_CACHE_TTL) {
      return cachedData;
    }

    // Prevent concurrent requests (single-flight pattern)
    if (requestInFlight) {
      return cachedData || null;
    }

    requestInFlight = true;
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), GA_REQUEST_TIMEOUT);

      const response = await fetch("/static/data/ga-stats.json", {
        signal: controller.signal,
        headers: { Accept: "application/json" },
      });
      clearTimeout(timeoutId);

      if (!response.ok) {
        console.error(`GA fetch failed: ${response.status}`);
        return cachedData || null;
      }

      cachedData = await response.json();
      lastFetchTime = now;
      return cachedData;
    } catch (err) {
      console.error("GA stats refresh error:", err.message);
      return cachedData || null;
    } finally {
      requestInFlight = false;
    }
  }

  /**
   * Update a single metric card DOM element with new value.
   */
  function updateMetricCard(selector, value, emptyClass = "ga-stats__num--empty") {
    const el = document.querySelector(selector);
    if (!el) return;

    if (value === null || value === undefined || value === "—") {
      el.classList.add(emptyClass);
      el.textContent = "—";
    } else {
      el.classList.remove(emptyClass);
      el.textContent = value;
    }
  }

  /**
   * Channel emoji mapping for visual consistency.
   */
  const CHANNEL_EMOJIS = {
    "Direct": "🔗",
    "Organic Search": "🔍",
    "Organic Social": "📱",
    "Paid Social": "📣",
    "Paid Search": "💰",
    "Social": "📱",
    "Email": "📧",
    "Referral": "🔄",
    "Unassigned": "❓",
    "Display": "📺",
    "Affiliate": "💼",
    "Video": "🎥",
  };

  /**
   * Get emoji for a channel name.
   */
  function getChannelEmoji(channelName) {
    for (const [key, emoji] of Object.entries(CHANNEL_EMOJIS)) {
      if (channelName.includes(key)) {
        return emoji;
      }
    }
    return "📊";
  }

  /**
   * Update channel breakdown widget (if present).
   */
  function updateChannelBreakdown(channels) {
    const widget = document.querySelector("[data-ga-channels]");
    if (!widget || !channels || Object.keys(channels).length === 0) return;

    const list = widget.querySelector("[data-ga-channels-list]");
    if (!list) return;

    list.innerHTML = "";
    const maxUsers = Math.max(
      0,
      ...Object.values(channels).map((c) => c.users || 0)
    );

    for (const [channel, data] of Object.entries(channels).slice(0, 5)) {
      const pct = maxUsers > 0 ? Math.round((data.users / maxUsers) * 100) : 0;
      const emoji = getChannelEmoji(channel);
      const item = document.createElement("div");
      item.className = "ga-channels__item";
      item.innerHTML = `
        <span class="ga-channels__name">${emoji} ${escapeHtml(channel)}</span>
        <div class="ga-channels__bar-wrapper">
          <div class="ga-channels__bar" style="width: ${pct}%"></div>
        </div>
        <span class="ga-channels__metric">${data.users || 0}</span>
      `;
      list.appendChild(item);
    }
  }

  /**
   * Refresh all GA stat cards with latest data.
   */
  async function refreshMetrics() {
    const data = await fetchGAStats();
    if (!data) {
      console.warn("GA stats unavailable for refresh");
      return;
    }

    // Update main metric cards
    updateMetricCard('[data-ga-num="today_users"]', data.today_users);
    updateMetricCard('[data-ga-num="today_pageviews"]', data.today_pageviews);
    updateMetricCard('[data-ga-num="week_users"]', data.week_users);
    updateMetricCard('[data-ga-num="week_pageviews"]', data.week_pageviews);
    updateMetricCard('[data-ga-num="month_users"]', data.month_users);
    updateMetricCard('[data-ga-num="month_pageviews"]', data.month_pageviews);

    // Update extended metrics
    updateMetricCard('[data-ga-extended="sessions"]', data.month_sessions);
    updateMetricCard('[data-ga-extended="new_users"]', data.month_new_users);
    updateMetricCard(
      '[data-ga-extended="bounce_rate"]',
      data.month_bounce_rate_pct !== null
        ? `${data.month_bounce_rate_pct}%`
        : null
    );
    updateMetricCard(
      '[data-ga-extended="avg_duration"]',
      data.month_avg_session_duration_str
    );
    updateMetricCard(
      '[data-ga-extended="engagement"]',
      data.month_engagement_rate_pct !== null
        ? `${data.month_engagement_rate_pct}%`
        : null
    );

    // Update organic search metrics
    updateMetricCard('[data-ga-organic="users"]', data.organic_users);
    updateMetricCard(
      '[data-ga-organic="pct"]',
      data.organic_pct_traffic !== null
        ? `${data.organic_pct_traffic}%`
        : null
    );
    updateMetricCard('[data-ga-organic="sessions"]', data.organic_sessions);
    updateMetricCard('[data-ga-organic="pageviews"]', data.organic_pageviews);

    // Update channel breakdown
    updateChannelBreakdown(data.channel_breakdown);

    // Update last-checked time
    updateLastCheckedTime(data.updated_at);
  }

  /**
   * Update the "last refreshed" timestamp.
   */
  function updateLastCheckedTime(timestamp) {
    const el = document.querySelector("[data-ga-updated-time]");
    if (!el || !timestamp) return;
    try {
      const dt = new Date(timestamp);
      el.textContent = dt.toLocaleString("vi-VN", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
      el.setAttribute("datetime", timestamp);
    } catch (err) {
      console.error("Failed to format GA timestamp:", err);
    }
  }

  /**
   * Simple HTML escape to prevent XSS.
   */
  function escapeHtml(text) {
    const map = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;",
    };
    return text.replace(/[&<>"']/g, (m) => map[m]);
  }

  /**
   * Start the refresh loop.
   */
  function startRefreshLoop() {
    // Refresh immediately on page load
    refreshMetrics().catch(console.error);

    // Then refresh every 60 seconds
    setInterval(() => {
      refreshMetrics().catch(console.error);
    }, GA_REFRESH_INTERVAL);
  }

  // Start when DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", startRefreshLoop);
  } else {
    startRefreshLoop();
  }

  // Expose refresh function for manual trigger (e.g. from DevTools)
  window.gaRefreshMetrics = refreshMetrics;
})();
