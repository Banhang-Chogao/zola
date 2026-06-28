/**
 * AI Blog Writer — "Viết blog" button for /tools/content-creator/.
 *
 * Reads the prompt from the existing #cc-prompt textarea (filled by app.js),
 * dispatches the write request to the backend via POST /cms/ai-writer-dispatch,
 * which proxies to GitHub repository_dispatch. The actual AI work runs in
 * a GitHub Actions workflow, which creates a branch + PR.
 *
 * We show "Đã gửi yêu cầu viết bài, PR sẽ được tạo sau vài phút." on success
 * and a link to the Actions page so the user can track progress.
 *
 * Requires a CMS admin session (same OAuth as the editor). When the backend is
 * unreachable or unconfigured, we fall back to showing the Actions URL.
 */
(function () {
  "use strict";

  // ── DOM helpers ────────────────────────────────────────────────
  function authApi() {
    var m = document.querySelector('meta[name="zola-cms-auth-api"]');
    return m && m.getAttribute("content")
      ? m.getAttribute("content").trim().replace(/\/$/, "")
      : "";
  }

  function sid() {
    try {
      return sessionStorage.getItem("zola-cms-session-id") || "";
    } catch (e) {
      return "";
    }
  }

  function actionsUrl() {
    var m = document.querySelector('meta[name="cc-actions-url"]');
    if (m) return m.getAttribute("content");
    var base = document.querySelector('meta[name="zola-base-url"]');
    if (!base) return "https://github.com/Banhang-Chogao/zola/actions";
    return "https://github.com/Banhang-Chogao/zola/actions";
  }

  function aiWriterActionsUrl() {
    return "https://github.com/Banhang-Chogao/zola/actions/workflows/ai-writer-dispatch.yml";
  }

  // ── DOM refs ─────────────────────────────────────────────────
  var writeBtn, promptEl, statusEl, resultPanel, loadingPanel;

  function init() {
    writeBtn = document.getElementById("cc-write-blog");
    if (!writeBtn) return;

    promptEl = document.getElementById("cc-prompt");
    statusEl = document.getElementById("cc-write-status");
    loadingPanel = document.getElementById("cc-write-loading");
    resultPanel = document.getElementById("cc-write-result");

    function updateButtonState() {
      var hasPrompt =
        promptEl && promptEl.value && promptEl.value.trim().length > 0;
      writeBtn.disabled = !hasPrompt;
    }

    updateButtonState();
    if (promptEl) {
      promptEl.addEventListener("input", updateButtonState);
    }

    writeBtn.addEventListener("click", handleWrite);
  }

  // ── UI helpers ───────────────────────────────────────────────
  function setStatus(msg, kind) {
    if (!statusEl) return;
    statusEl.textContent = msg;
    statusEl.className = "cc-write-status" + (kind ? " cc-write-status--" + kind : "");
  }

  function setLoading(loading) {
    if (!loadingPanel) return;
    loadingPanel.hidden = !loading;
    if (writeBtn) writeBtn.disabled = loading;
  }

  function showResult(data) {
    if (!resultPanel) return;
    resultPanel.hidden = false;

    var actionsHref = aiWriterActionsUrl();
    var html =
      '<div class="cc-write-result__meta">' +
      '<span class="cc-write-result__icon">✅</span>' +
      '<span class="cc-write-result__msg">' +
      escapeHtml(data && data.message ? data.message : "Đã gửi yêu cầu viết bài.") +
      "</span>" +
      "</div>" +
      '<div class="cc-write-result__actions">' +
      '<a href="' +
      escapeAttr(actionsHref) +
      '" target="_blank" rel="noopener" class="cc-btn cc-btn--primary cc-btn--sm">' +
      "⚙ Theo dõi tiến độ trên Actions" +
      "</a>" +
      '<button type="button" class="cc-btn cc-btn--ghost cc-btn--sm" id="cc-write-again">' +
      "✍ Viết bài khác" +
      "</button>" +
      "</div>" +
      '<p class="cc-write-result__note">' +
      "PR sẽ được tạo tự động sau khi workflow hoàn tất. " +
      'Theo dõi tại <a href="' +
      escapeAttr(actionsHref) +
      '" target="_blank" rel="noopener">GitHub Actions</a> ' +
      "hoặc mục <strong>Changelog</strong> trên site." +
      "</p>";

    resultPanel.innerHTML = html;

    var againBtn = document.getElementById("cc-write-again");
    if (againBtn) {
      againBtn.addEventListener("click", function () {
        resultPanel.hidden = true;
        if (promptEl) promptEl.focus();
      });
    }
  }

  function showFallback(msg) {
    if (!resultPanel) return;
    resultPanel.hidden = false;

    var actionsHref = aiWriterActionsUrl();
    var html =
      '<div class="cc-write-result__meta">' +
      '<span class="cc-write-result__icon">ℹ️</span>' +
      '<span class="cc-write-result__msg">' +
      escapeHtml(msg || "Không thể gửi yêu cầu qua backend.") +
      "</span>" +
      "</div>" +
      '<div class="cc-write-result__actions">' +
      '<a href="' +
      escapeAttr(actionsHref) +
      '" target="_blank" rel="noopener" class="cc-btn cc-btn--ghost cc-btn--sm">' +
      "⚙ Mở workflow thủ công" +
      "</a>" +
      "</div>" +
      '<p class="cc-write-result__note">' +
      "Bạn có thể copy prompt và chạy workflow <strong>AI Writer Dispatch</strong> " +
      "thủ công trên GitHub Actions, hoặc dùng prompt trong ô phía trên với AI ngoài." +
      "</p>";

    resultPanel.innerHTML = html;
  }

  function escapeHtml(s) {
    if (!s) return "";
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function escapeAttr(s) {
    if (!s) return "";
    return String(s).replace(/"/g, "&quot;").replace(/&/g, "&amp;");
  }

  // ── Main handler ─────────────────────────────────────────────
  function getFormData() {
    var topicEl = document.getElementById("cc-topic");
    var pricingEl = document.getElementById("cc-pricing");
    var briefEl = document.getElementById("cc-brief");
    var uxEl = document.getElementById("cc-ux");
    return {
      topic: topicEl ? topicEl.value.trim() : "",
      pricing: pricingEl ? pricingEl.value : "free",
      brief: briefEl ? briefEl.value : "",
      ux: uxEl ? uxEl.value : "",
    };
  }

  async function handleWrite() {
    var prompt = promptEl ? promptEl.value.trim() : "";
    if (!prompt) {
      setStatus("Chưa có prompt — bấm Lưu trước.", "error");
      return;
    }

    if (resultPanel) resultPanel.hidden = true;
    setLoading(true);
    setStatus("⏳ Đang gửi yêu cầu…", "info");

    var form = getFormData();
    var api = authApi();
    var s = sid();

    if (!api || !s) {
      setLoading(false);
      setStatus(
        "🔒 Cần đăng nhập CMS để dùng AI Writer. " +
          'Hãy <a href="' +
          escapeAttr(api ? api + "/auth/login?return_to=/tools/content-creator/" : "#") +
          '" class="cc-write-status__link">đăng nhập</a> trước.',
        "error"
      );
      showFallback("Cần đăng nhập CMS để gửi yêu cầu viết bài.");
      return;
    }

    try {
      var res = await fetch(api + "/cms/ai-writer-dispatch", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer " + s,
        },
        body: JSON.stringify({
          prompt: prompt,
          topic: form.topic,
          category: "Tất cả",
          pricing: form.pricing,
          brief: form.brief,
          ux_brief: form.ux,
        }),
      });

      var data;
      try {
        data = await res.json();
      } catch (e) {
        data = { ok: false, detail: "Phản hồi từ server không hợp lệ." };
      }

      setLoading(false);

      if (res.ok && data.ok) {
        setStatus("✅ " + (data.message || "Đã gửi yêu cầu."), "success");
        showResult(data);
      } else if (res.status === 401) {
        setStatus(
          "🔒 Phiên đăng nhập hết hạn. Hãy refresh trang và đăng nhập lại.",
          "error"
        );
        showFallback("Phiên đăng nhập hết hạn.");
      } else {
        var errMsg =
          data.detail || data.message || "Lỗi không xác định — thử lại sau.";
        setStatus("❌ Chưa thể gửi yêu cầu: " + escapeHtml(errMsg), "error");
        showFallback(errMsg);
      }
    } catch (err) {
      setLoading(false);
      setStatus(
        "❌ Không thể kết nối server — hãy thử lại hoặc copy prompt thủ công.",
        "error"
      );
      showFallback("Không thể kết nối server AI Writer.");
    }
  }

  // ── Boot ─────────────────────────────────────────────────────
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
