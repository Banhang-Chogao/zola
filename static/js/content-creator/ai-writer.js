/**
 * AI Blog Writer — "Viết blog" button for /tools/content-creator/.
 *
 * Reads the prompt from the existing #cc-prompt textarea (filled by app.js),
 * calls the backend POST /api/content-creator/write-blog, and shows the
 * result (PR link, slug, preview URL) without disturbing the prompt text.
 *
 * Requires a CMS admin session (same OAuth as the editor). When the AI API
 * is not configured on the backend, the button shows a friendly fallback
 * message and the user can still copy the prompt manually.
 */
(function () {
  "use strict";

  // ── Auth helpers (reuse same pattern as app.js) ──────────────
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

  function baseUrl() {
    var m = document.querySelector('meta[name="zola-base-url"]');
    return m ? m.getAttribute("content").replace(/\/$/, "") : "";
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

    // Enable/disable based on prompt presence.
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

    var html = "";
    if (data.pr_url) {
      html +=
        '<div class="cc-write-result__meta">' +
        '<span class="cc-write-result__title">' +
        escapeHtml(data.title || "") +
        "</span>" +
        '<span class="cc-write-result__slug">/' +
        escapeHtml(data.slug || "") +
        "/</span>" +
        "</div>" +
        '<div class="cc-write-result__actions">' +
        '<a href="' +
        escapeAttr(data.pr_url) +
        '" target="_blank" rel="noopener" class="cc-btn cc-btn--primary cc-btn--sm">' +
        "🔍 Xem PR #" +
        escapeHtml(String(data.pr_number || "")) +
        "</a>" +
        '<a href="' +
        escapeAttr(data.public_url || "") +
        '" target="_blank" rel="noopener" class="cc-btn cc-btn--ghost cc-btn--sm"' +
        ' id="cc-preview-link">' +
        "🔗 Xem preview" +
        "</a>" +
        '<button type="button" class="cc-btn cc-btn--ghost cc-btn--sm" id="cc-copy-blog-link">' +
        "📋 Copy link" +
        "</button>" +
        "</div>";
    }
    resultPanel.innerHTML = html;

    // Wire copy link button.
    var copyLinkBtn = document.getElementById("cc-copy-blog-link");
    if (copyLinkBtn && data.public_url) {
      copyLinkBtn.addEventListener("click", function () {
        copyToClipboard(data.public_url)
          .then(function () {
            copyLinkBtn.textContent = "✓ Copied!";
            setTimeout(function () {
              copyLinkBtn.textContent = "📋 Copy link";
            }, 2200);
          })
          .catch(function () {
            copyLinkBtn.textContent = "✗ Copy failed";
          });
      });
    }
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

  function copyToClipboard(text) {
    if (!text) return Promise.reject(new Error("empty"));
    if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
      return navigator.clipboard.writeText(text).catch(function () {
        return fallbackCopy(text);
      });
    }
    return fallbackCopy(text);
  }

  function fallbackCopy(text) {
    return new Promise(function (resolve, reject) {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      ta.style.top = "0";
      ta.opacity = "0";
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      try {
        if (ta.setSelectionRange) ta.setSelectionRange(0, text.length);
      } catch (e) {}
      var ok = false;
      try {
        ok = document.execCommand("copy");
      } catch (err) {
        ok = false;
      }
      document.body.removeChild(ta);
      if (ok) resolve();
      else reject(new Error("execCommand_failed"));
    });
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

    // Hide previous result.
    if (resultPanel) resultPanel.hidden = true;
    setLoading(true);
    setStatus("⏳ AI đang viết bài…", "info");

    var form = getFormData();
    var api = authApi();
    var s = sid();

    if (!api || !s) {
      setLoading(false);
      setStatus(
        "🔒 Cần đăng nhập CMS để dùng AI Writer. " +
          'Hãy copy prompt thủ công hoặc <a href="' +
          escapeAttr(api ? api + "/auth/login?return_to=/tools/content-creator/" : "#") +
          '" class="cc-write-status__link">đăng nhập</a> trước.',
        "error"
      );
      return;
    }

    try {
      var res = await fetch(api + "/api/content-creator/write-blog", {
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
          watermark: "",
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
        setStatus("✅ " + data.message, "success");
        showResult(data);
      } else if (res.status === 401) {
        setStatus(
          "🔒 Phiên đăng nhập hết hạn. Hãy refresh trang và đăng nhập lại.",
          "error"
        );
      } else if (res.status === 429) {
        setStatus(
          "⚠️ " +
            (data.detail ||
              "AI provider quota exceeded. Giữ prompt và thử lại sau, hoặc copy thủ công."),
          "warn"
        );
      } else if (res.status === 501) {
        setStatus(
          "ℹ️ " +
            (data.detail ||
              "AI chưa được cấu hình. Copy prompt và dùng AI ngoài để viết bài."),
          "warn"
        );
      } else {
        var errMsg =
          data.detail || data.message || "Lỗi không xác định — thử lại sau.";
        setStatus("❌ Chưa thể publish: " + escapeHtml(errMsg), "error");
      }
    } catch (err) {
      setLoading(false);
      setStatus(
        "❌ Không thể kết nối server — hãy thử lại hoặc copy prompt thủ công.",
        "error"
      );
    }
  }

  // ── Boot ─────────────────────────────────────────────────────
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
