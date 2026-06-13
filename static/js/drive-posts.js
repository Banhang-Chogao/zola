/**
 * Drive Posts loader
 * ============================================================
 * Fetch file JSON public trên Google Drive → parse → render
 * thành các bài viết HTML hiển thị ngay trên blog.
 *
 * CÁCH SETUP:
 * 1. Tạo file posts.json đúng schema bên dưới
 * 2. Upload lên Google Drive
 * 3. Right click file → Share → "Anyone with the link" → Viewer
 * 4. Copy share URL — dạng: https://drive.google.com/file/d/FILE_ID/view?usp=sharing
 * 5. Lấy FILE_ID (đoạn giữa /d/ và /view) → paste vào DRIVE_FILE_ID dưới
 *
 * JSON SCHEMA (file posts.json trên Drive):
 * {
 *   "posts": [
 *     {
 *       "title": "Tiêu đề bài",
 *       "slug": "tieu-de-bai",                    // optional, tự sinh nếu thiếu
 *       "date": "2026-06-14",                     // YYYY-MM-DD
 *       "category": "Posting",
 *       "tags": ["zola", "drive"],
 *       "thumbnail": "https://...",               // URL ảnh, optional
 *       "summary": "Tóm tắt 1-2 câu",            // hiển thị ngắn
 *       "content": "**Markdown** nội dung đầy đủ..."
 *     },
 *     { ... }
 *   ]
 * }
 */
(function () {
  // ============= CẤU HÌNH =============
  const DRIVE_FILE_ID = "1mHlqPXvQyZuPqAeJV9OOxwo5mAp2otk8"; // 👈 FILE_ID file posts.json trên Drive

  // Drive không có CORS header → cần proxy. Có nhiều backup nếu 1 cái die.
  const DRIVE_URL = "https://drive.google.com/uc?export=download&id=" + DRIVE_FILE_ID;
  const PROXIES = [
    { url: "https://corsproxy.io/?", direct: true },
    { url: "https://api.codetabs.com/v1/proxy?quest=", direct: true },
    { url: "https://api.allorigins.win/raw?url=", direct: true },
    { url: "https://api.allorigins.win/get?url=", direct: false }, // trả JSON wrap {contents}
  ];
  // ====================================

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

    // Markdown body → HTML (sanitized)
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
            <span class="post-meta__author">drive</span>
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
    if (DRIVE_FILE_ID === "PASTE_FILE_ID_HERE" || !DRIVE_FILE_ID) {
      setStatus("⚙ Chưa cấu hình DRIVE_FILE_ID trong static/js/drive-posts.js", "error");
      listEl.innerHTML = `
        <div class="drive-setup-notice">
          <h3>Cần cấu hình trước khi dùng</h3>
          <ol>
            <li>Tạo file <code>posts.json</code> theo schema (xem comment đầu file <code>static/js/drive-posts.js</code>)</li>
            <li>Upload lên Google Drive</li>
            <li>Right-click → <strong>Share</strong> → <strong>Anyone with the link</strong> → Viewer</li>
            <li>Copy link, lấy phần ID giữa <code>/d/</code> và <code>/view</code></li>
            <li>Mở file <code>static/js/drive-posts.js</code>, sửa dòng <code>DRIVE_FILE_ID = "..."</code></li>
            <li>Commit + push</li>
          </ol>
        </div>
      `;
      return;
    }

    try {
      // Đợi marked + DOMPurify load (defer)
      await new Promise((r) => setTimeout(r, 400));

      // Thử lần lượt từng proxy, dừng khi 1 cái thành công
      let raw = null;
      let lastErr = null;
      for (let i = 0; i < PROXIES.length; i++) {
        const p = PROXIES[i];
        setStatus("Đang tải từ Drive… (proxy " + (i + 1) + "/" + PROXIES.length + ")", "loading");
        try {
          const fetchUrl = p.url + encodeURIComponent(DRIVE_URL);
          const res = await fetch(fetchUrl, { cache: "no-store" });
          if (!res.ok) throw new Error("HTTP " + res.status);
          if (p.direct) {
            raw = await res.text();
          } else {
            const wrapped = await res.json();
            raw = wrapped.contents;
          }
          if (raw && typeof raw === "string" && raw.trim().length > 0) {
            console.log("[drive-posts] proxy OK:", p.url);
            break;
          }
        } catch (err) {
          console.warn("[drive-posts] proxy fail:", p.url, err.message);
          lastErr = err;
        }
      }

      if (!raw) {
        throw lastErr || new Error("Tất cả proxy đều fail");
      }

      // Drive đôi khi wrap trong HTML (file > 25MB hoặc virus scan)
      if (typeof raw === "string" && raw.trim().startsWith("<")) {
        throw new Error("Drive trả HTML interstitial — file quá lớn hoặc chưa public");
      }

      const data = JSON.parse(raw);
      const posts = Array.isArray(data.posts) ? data.posts : (Array.isArray(data) ? data : []);
      if (!posts.length) {
        setStatus("Không có bài viết nào trong file JSON", "empty");
        return;
      }

      // Sort bài mới nhất lên đầu
      posts.sort((a, b) => new Date(b.date || 0) - new Date(a.date || 0));

      listEl.innerHTML = posts.map(renderPost).join("");
      setStatus(`✓ Đã tải ${posts.length} bài từ Drive`, "success");
    } catch (err) {
      console.error("[drive-posts]", err);
      setStatus("✗ Không tải được Drive: " + err.message, "error");
    }
  }

  load();
})();
