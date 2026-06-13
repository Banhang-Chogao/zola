/**
 * Posts loader — fetch JSON từ GitHub Gist (CORS native, không cần proxy)
 * ============================================================
 *
 * CÁCH SETUP:
 * 1. Vào https://gist.github.com → New gist
 * 2. Filename: posts.json
 * 3. Paste JSON theo schema bên dưới
 * 4. Click "Create public gist"
 * 5. Copy gist URL, lấy GIST_ID (đoạn hex dài cuối URL)
 * 6. Paste vào GIST_ID dưới
 *
 * EDIT BÀI VIẾT:
 *   Vào lại gist URL → click "Edit" → sửa → "Update public gist"
 *   → Reload blog → bài mới hiện ra trong vài giây (no rebuild)
 *
 * JSON SCHEMA:
 * {
 *   "posts": [
 *     {
 *       "title": "Tiêu đề bài",
 *       "slug": "tieu-de-bai",                    // optional
 *       "date": "2026-06-14",                     // YYYY-MM-DD
 *       "category": "Posting",
 *       "tags": ["zola", "drive"],
 *       "thumbnail": "https://...",
 *       "summary": "Tóm tắt 1-2 câu",
 *       "content": "**Markdown** body..."
 *     }
 *   ]
 * }
 */
(function () {
  // ============= CẤU HÌNH =============
  const GIST_USER = "Banhang-Chogao";
  const GIST_ID = "9e75490dacb5333bec86f8e175b7b4d0";
  // ====================================

  // Dùng GitHub Gist API thay vì raw URL — API CORS native + trả về file list
  // → tự tìm file JSON đầu tiên, không cần biết filename chính xác
  // Cache 5 phút (ts giảm tần suất gọi API)
  const API_URL =
    "https://api.github.com/gists/" + GIST_ID +
    "?ts=" + Math.floor(Date.now() / 300000);

  const statusEl = document.querySelector("[data-status]");
  const listEl = document.querySelector("[data-drive-posts]");
  if (!listEl) return;

  function setStatus(text, type) {
    if (!statusEl) return;
    statusEl.className = "drive-status drive-status--" + (type || "loading");
    statusEl.querySelector(".drive-status__msg").textContent = text;
  }

  function escapeHtml(s) {
    return String(s || "").replace(/[&<>"']/g, (c) =>
      ({ "&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;" }[c])
    );
  }

  function slugify(s) {
    return String(s).toLowerCase()
      .normalize("NFD").replace(/[̀-ͯ]/g, "")
      .replace(/đ/g, "d")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "");
  }

  function fmtDate(iso) {
    const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return months[d.getMonth()] + " " + String(d.getDate()).padStart(2, "0") + ", " + d.getFullYear();
  }

  function renderPost(p) {
    const slug = p.slug || slugify(p.title || "untitled");
    const safeId = "drive-" + slug;
    const cat = p.category ? `<span class="cat-tag">${escapeHtml(p.category.toUpperCase())}</span>` : "";
    const thumb = p.thumbnail ? `
      <a class="post-card__image" href="#${escapeHtml(safeId)}">
        ${cat}
        <img src="${escapeHtml(p.thumbnail)}" alt="${escapeHtml(p.title)}" loading="lazy">
      </a>` : "";

    let bodyHtml = "";
    if (p.content && window.marked && window.DOMPurify) {
      bodyHtml = window.DOMPurify.sanitize(window.marked.parse(p.content));
    } else if (p.content) {
      bodyHtml = "<pre>" + escapeHtml(p.content) + "</pre>";
    }

    const summary = p.summary || (p.content ? escapeHtml(p.content.replace(/[#*`>\[\]]/g, "").slice(0, 200)) + "…" : "");

    return `
      <article class="post-card drive-post" id="${escapeHtml(safeId)}">
        ${thumb}
        <div class="post-card__body">
          <h3 class="post-card__title">${escapeHtml(p.title || "Untitled")}</h3>
          <div class="post-meta">
            <span class="post-meta__author">gist</span>
            <span class="post-meta__date">${fmtDate(p.date || "")}</span>
          </div>
          <p class="post-card__summary">${summary}</p>
          <details class="drive-post__body">
            <summary class="read-more">ĐỌC BÀI <span class="read-more__arrow">»</span></summary>
            <div class="drive-post__content">${bodyHtml}</div>
          </details>
        </div>
      </article>
    `;
  }

  async function load() {
    if (!GIST_ID || GIST_ID.startsWith("PASTE")) {
      setStatus("⚙ Chưa cấu hình GIST_ID trong static/js/drive-posts.js", "error");
      listEl.innerHTML = `
        <div class="drive-setup-notice">
          <h3>Cần cấu hình GitHub Gist trước khi dùng</h3>
          <ol>
            <li>Vào <a href="https://gist.github.com">gist.github.com</a> → New gist</li>
            <li>Filename: <code>posts.json</code></li>
            <li>Paste content theo schema</li>
            <li>Click <strong>Create public gist</strong></li>
            <li>Copy URL → extract GIST_ID → paste vào file <code>static/js/drive-posts.js</code></li>
          </ol>
        </div>
      `;
      return;
    }

    try {
      // Đợi marked + DOMPurify load (defer)
      await new Promise((r) => setTimeout(r, 400));

      setStatus("Đang tải từ Gist…", "loading");
      const res = await fetch(API_URL, {
        cache: "no-store",
        headers: { Accept: "application/vnd.github+json" },
      });
      if (!res.ok) {
        if (res.status === 404) throw new Error("Gist không tồn tại (404). Kiểm tra GIST_ID + gist phải public.");
        if (res.status === 403) throw new Error("GitHub API rate limit (60 req/h/IP). Đợi 1 giờ.");
        throw new Error("HTTP " + res.status);
      }

      const gist = await res.json();
      const files = gist.files || {};
      const fileNames = Object.keys(files);
      if (!fileNames.length) throw new Error("Gist không có file nào");

      // Tìm file JSON đầu tiên, hoặc file đầu tiên nếu không có .json
      let target = fileNames.find((n) => n.toLowerCase().endsWith(".json")) || fileNames[0];
      const file = files[target];
      let raw = file.content;

      // Nếu content bị truncate (file > 1MB), fetch raw URL bổ sung
      if (file.truncated && file.raw_url) {
        console.log("[posts] gist file truncated, fetching raw");
        const rawRes = await fetch(file.raw_url, { cache: "no-store" });
        if (!rawRes.ok) throw new Error("Raw fetch HTTP " + rawRes.status);
        raw = await rawRes.text();
      }

      if (!raw || !raw.trim()) throw new Error("File '" + target + "' rỗng");

      console.log("[posts] using gist file:", target);
      const data = JSON.parse(raw);
      const posts = Array.isArray(data.posts) ? data.posts : (Array.isArray(data) ? data : []);
      if (!posts.length) {
        setStatus("Không có bài viết nào trong gist", "empty");
        return;
      }

      posts.sort((a, b) => new Date(b.date || 0) - new Date(a.date || 0));

      listEl.innerHTML = posts.map(renderPost).join("");
      setStatus("✓ Đã tải " + posts.length + " bài từ Gist", "success");

      console.log("[posts] loaded from gist:", { count: posts.length, gistId: GIST_ID });
    } catch (err) {
      console.error("[posts]", err);
      setStatus("✗ Không tải được Gist: " + err.message, "error");
      listEl.innerHTML = `
        <div class="drive-setup-notice">
          <h3>Lỗi: ${escapeHtml(err.message)}</h3>
          <p>Kiểm tra:</p>
          <ol>
            <li>Gist <strong>public</strong>? Vào <a href="https://gist.github.com/${escapeHtml(GIST_USER)}/${escapeHtml(GIST_ID)}" target="_blank">gist URL</a> ở tab incognito (không login), thấy file không?</li>
            <li>Trong gist có ít nhất 1 file <code>.json</code>?</li>
            <li>Nội dung JSON đúng cú pháp? Kiểm tra ở <a href="https://jsonlint.com" target="_blank">jsonlint.com</a></li>
          </ol>
        </div>
      `;
    }
  }

  load();
})();
