/**
 * Content Creator — sinh prompt thủ công từ input người dùng, kích hoạt workflow
 * "Content Creator" (viết series bài liên tục) rồi tự build/deploy production.
 *
 * Static site → không có token GitHub trong browser. Việc dispatch workflow đi
 * qua backend CMS (cùng OAuth session với editor). Nếu backend không có endpoint
 * dispatch → fallback: tải brief JSON + mở trang Actions để chạy workflow thủ công.
 */
(function () {
  "use strict";

  var SESSION_KEY = "zola-cms-session-id";

  function authApi() {
    var m = document.querySelector('meta[name="zola-cms-auth-api"]');
    return m && m.getAttribute("content") ? m.getAttribute("content").trim().replace(/\/$/, "") : "";
  }
  function actionsUrl() {
    var m = document.querySelector('meta[name="cc-actions-url"]');
    return m ? m.getAttribute("content") : "";
  }
  function sid() {
    try { return sessionStorage.getItem(SESSION_KEY) || ""; } catch (e) { return ""; }
  }

  /** 16 hex (8 byte) random — trùng định dạng trace-code các dashboard (export.js). */
  function id16() {
    var bytes = new Uint8Array(8);
    crypto.getRandomValues(bytes);
    return Array.from(bytes, function (b) { return b.toString(16).padStart(2, "0"); }).join("");
  }

  function slugify(s) {
    return String(s || "")
      .normalize("NFD").replace(/[̀-ͯ]/g, "")
      .replace(/đ/gi, "d")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/(^-|-$)/g, "")
      .slice(0, 60) || "content-series";
  }

  /** Sinh prompt thủ công đầy đủ từ toàn bộ input. */
  function buildPrompt(data) {
    var isPaid = data.pricing === "paid";
    var category = isPaid ? "premium (thu phí)" : "mặc định (Tất cả) — miễn phí";
    var lines = [
      "# PROMPT VIẾT SERIES — " + data.topic,
      "",
      "Bạn là cây viết SEO tiếng Việt. Viết LẦN LƯỢT " + data.count + " bài cho series về chủ đề:",
      "«" + data.topic + "».",
      "",
      "## Hình thức",
      "- Thu phí: " + (isPaid ? "CÓ — đặt category = premium, frontmatter premium=true." : "KHÔNG — category mặc định \"Tất cả\"."),
      "- Category: " + category,
      "",
      "## Diễn giải chi tiết của người tạo",
      (data.brief && data.brief.trim()) ? data.brief.trim() : "(không có — tự bám sát chủ đề)",
      "",
      "## UI/UX mong muốn",
      (data.ux && data.ux.trim()) ? data.ux.trim() : "(không có yêu cầu riêng)",
      "",
      "## Yêu cầu BẮT BUỘC mỗi bài (theo SEO CONTENT SYSTEM RULE của blog)",
      "1. Xác định search intent, thoả mãn trong 150 từ đầu.",
      "2. title < 60 ký tự chứa từ khoá chính; description < 155 ký tự.",
      "3. ≥ 1500 từ (bài chuẩn); ≥ 2 heading H2; đoạn ngắn, mobile-first.",
      "4. ≥ 5 internal link (gồm 1 link hub chuyên mục) + ≥ 1 external link uy tín.",
      "5. 3–8 FAQ ([[extra.faq]]) + CTA/next-step cuối bài, không để trang cụt.",
      "6. categories đặt \"Tất cả\" đầu mảng" + (isPaid ? " + premium." : ".") ,
      "7. Mỗi bài là 1 part: series_part / series_total = " + data.count + ".",
      "",
      "## Đầu ra",
      "- Mỗi bài = 1 file content/posting/<slug>.md với frontmatter hợp lệ.",
      "- series id = \"" + data.series_id + "\".",
      "- Sau khi viết đủ " + data.count + " bài → push PR → auto-merge khi QA xanh → deploy production.",
    ];
    return lines.join("\n");
  }

  function buildJob(data) {
    return {
      series_id: data.series_id,
      topic: data.topic,
      count: data.count,
      pricing: data.pricing,
      category: data.pricing === "paid" ? "premium" : "default",
      brief: data.brief || "",
      ux_brief: data.ux || "",
      watermark: data.watermark,
      prompt: data.prompt,
      created_at: new Date().toISOString(),
    };
  }

  function setStatus(el, msg, kind) {
    if (!el) return;
    el.textContent = msg;
    el.className = "cc-status" + (kind ? " cc-status--" + kind : "");
  }

  /** Clipboard with execCommand fallback (mobile / denied permission). */
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
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      try {
        if (ta.setSelectionRange) ta.setSelectionRange(0, text.length);
      } catch (e) { /* iOS */ }
      var ok = false;
      try { ok = document.execCommand("copy"); } catch (err) { ok = false; }
      document.body.removeChild(ta);
      if (ok) resolve();
      else reject(new Error("execCommand_failed"));
    });
  }

  var copyFeedbackTimer = null;

  function setCopyFeedback(feedbackEl, copyBtn, msg, kind) {
    if (feedbackEl) {
      feedbackEl.textContent = msg;
      feedbackEl.className = "cc-copy-feedback" + (kind ? " cc-copy-feedback--" + kind : "");
    }
    if (copyBtn) {
      if (kind === "success") {
        var copied = copyBtn.getAttribute("data-label-copied") || "✓ Copied!";
        copyBtn.textContent = copied;
        copyBtn.classList.add("cc-btn--copied");
        if (copyFeedbackTimer) clearTimeout(copyFeedbackTimer);
        copyFeedbackTimer = setTimeout(function () {
          copyBtn.textContent = copyBtn.getAttribute("data-label-default") || "📋 Copy prompt";
          copyBtn.classList.remove("cc-btn--copied");
          if (feedbackEl) {
            feedbackEl.textContent = "";
            feedbackEl.className = "cc-copy-feedback";
          }
        }, 2200);
      } else if (kind === "error") {
        copyBtn.classList.remove("cc-btn--copied");
      }
    }
    if (window.getSelection && window.getSelection().removeAllRanges) {
      window.getSelection().removeAllRanges();
    }
    if (copyBtn && typeof copyBtn.blur === "function") copyBtn.blur();
  }

  function download(filename, text) {
    var blob = new Blob([text], { type: "application/json" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url; a.download = filename;
    document.body.appendChild(a); a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1500);
  }

  /** Thử dispatch workflow qua backend CMS. Trả về true nếu thành công. */
  async function dispatchViaBackend(job) {
    var api = authApi();
    var s = sid();
    if (!api || !s) return false;
    try {
      var res = await fetch(api + "/cms/content-creator", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer " + s,
        },
        body: JSON.stringify(job),
      });
      return res.ok;
    } catch (e) {
      return false;
    }
  }

  function init() {
    var form = document.getElementById("cc-form");
    if (!form) return;
    var statusEl = document.getElementById("cc-status");
    var promptEl = document.getElementById("cc-prompt");
    var copyBtn = document.getElementById("cc-copy");
    var copyFeedbackEl = document.getElementById("cc-copy-feedback");
    var dlBtn = document.getElementById("cc-download");
    var openBtn = document.getElementById("cc-open-actions");
    var lastJob = null;

    form.addEventListener("submit", async function (e) {
      e.preventDefault();
      var topic = document.getElementById("cc-topic").value.trim();
      var count = parseInt(document.getElementById("cc-count").value, 10);
      var pricing = document.getElementById("cc-pricing").value;
      var brief = document.getElementById("cc-brief").value;
      var ux = document.getElementById("cc-ux").value;

      if (!topic) { setStatus(statusEl, "Vui lòng nhập chủ đề.", "error"); return; }
      if (!count || count < 1) { setStatus(statusEl, "Số lượng bài phải ≥ 1.", "error"); return; }
      if (count > 30) { setStatus(statusEl, "Tối đa 30 bài / series.", "error"); return; }

      var data = {
        topic: topic, count: count, pricing: pricing, brief: brief, ux: ux,
        series_id: slugify(topic) + "-" + id16().slice(0, 6),
        watermark: id16(),
      };
      data.prompt = buildPrompt(data);
      promptEl.value = data.prompt;
      copyBtn.disabled = false;
      dlBtn.disabled = false;
      lastJob = buildJob(data);

      setStatus(statusEl, "Đang kích hoạt workflow viết bài…", "info");
      var ok = await dispatchViaBackend(lastJob);
      if (ok) {
        setStatus(statusEl,
          "✓ Đã kích hoạt workflow Content Creator — sẽ viết " + count +
          " bài rồi tự build & deploy production (không cần phê duyệt).", "success");
        if (openBtn) openBtn.hidden = true;
      } else {
        setStatus(statusEl,
          "Đã sinh prompt + brief. Backend dispatch chưa khả dụng — tải brief JSON và chạy " +
          "workflow “Content Creator” thủ công trên GitHub Actions.", "warn");
        if (openBtn && actionsUrl()) { openBtn.href = actionsUrl(); openBtn.hidden = false; }
      }
    });

    if (copyBtn) {
      copyBtn.addEventListener("click", function () {
        var text = promptEl && promptEl.value ? promptEl.value.trim() : "";
        if (!text) {
          setCopyFeedback(copyFeedbackEl, copyBtn, "Chưa có prompt — bấm Lưu trước.", "error");
          setStatus(statusEl, "Chưa có prompt để copy.", "error");
          return;
        }
        copyToClipboard(text).then(function () {
          setCopyFeedback(copyFeedbackEl, copyBtn, "Copied!", "success");
          setStatus(statusEl, "✓ Đã copy prompt.", "success");
        }).catch(function () {
          setCopyFeedback(copyFeedbackEl, copyBtn, "Không copy được — chọn thủ công trong ô prompt.", "error");
          setStatus(statusEl, "✗ Không copy được. Thử chọn toàn bộ ô prompt và copy thủ công.", "error");
          if (promptEl) {
            promptEl.focus();
            promptEl.select();
          }
        });
      });
    }

    dlBtn.addEventListener("click", function () {
      if (!lastJob) return;
      download("content-creator-" + lastJob.series_id + ".json", JSON.stringify(lastJob, null, 2));
    });

    document.getElementById("cc-reset").addEventListener("click", function () {
      form.reset();
      promptEl.value = "";
      if (copyBtn) copyBtn.disabled = true;
      if (dlBtn) dlBtn.disabled = true;
      if (openBtn) openBtn.hidden = true;
      setStatus(statusEl, "", "");
      setCopyFeedback(copyFeedbackEl, copyBtn, "", "");
      if (copyBtn) {
        copyBtn.textContent = copyBtn.getAttribute("data-label-default") || "📋 Copy prompt";
        copyBtn.classList.remove("cc-btn--copied");
      }
      lastJob = null;
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
