/**
 * Admin Zone Application
 * Orchestrates auth, search, PDF, and stats
 */

(function () {
  const adminZone = document.getElementById("admin-zone");
  if (!adminZone) return;

  // ===== INITIALIZATION =====
  async function init() {
    // Handle OAuth callback hash
    window.AdminZoneAuth.consumeUrlHashSid();

    // Check auth error
    const authError = window.AdminZoneAuth.consumeUrlAuthError();
    if (authError) {
      switchView("login");
      window.AdminZoneAuth.showLoginError(authError);
      return;
    }

    // Attempt to fetch current user
    const user = await window.AdminZoneAuth.fetchMe();

    if (!user) {
      // Not authenticated
      switchView("login");
      return;
    }

    // Authenticated
    window.AdminZoneAuth.currentUser = user;
    window.AdminZoneAuth.populateUserBar(user);
    window.AdminZoneStats.displayStats();
    switchView("dashboard");
  }

  function switchView(viewName) {
    const views = document.querySelectorAll("[data-view]");
    views.forEach(v => {
      v.hidden = v.dataset.view !== viewName;
    });
  }

  // ===== EVENT HANDLERS =====
  function handleAction(action) {
    switch (action) {
      case "github-login": {
        const returnTo = window.location.pathname;
        const loginUrl = `${window.AdminZoneAuth.AUTH_API}/auth/login?return_to=${encodeURIComponent(returnTo)}`;
        window.location.href = loginUrl;
        break;
      }
      case "logout": {
        window.AdminZoneAuth.logoutRemote();
        switchView("login");
        window.AdminZoneAuth.currentUser = null;
        break;
      }
      case "pdf-download": {
        window.AdminZonePDF.downloadPdf();
        window.AdminZoneStats.incrementRun(true);
        break;
      }
      case "pdf-webview": {
        window.AdminZonePDF.openPdfWebview();
        window.AdminZoneStats.incrementRun(true);
        break;
      }
      case "pdf-close": {
        window.AdminZonePDF.closePdfWebview();
        break;
      }
      case "search-clear": {
        window.AdminZoneSearch.clear();
        break;
      }
    }
  }

  // Attach event handlers
  document.addEventListener("click", (e) => {
    const actionBtn = e.target.closest("[data-action]");
    if (actionBtn) {
      const action = actionBtn.dataset.action;
      handleAction(action);
    }
  });

  // Initialize on DOM ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
