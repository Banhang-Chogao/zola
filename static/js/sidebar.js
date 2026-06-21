/**
 * Sidebar picker — Featured Posts + Random Posts với personalization qua localStorage.
 *
 * KIẾN TRÚC:
 *   - posts-data: JSON inline trong base.html, chứa metadata tất cả bài viết
 *   - localStorage["zola-events"]: array các sự kiện {url, ts, type}
 *       type = "view"  (load trang bài)
 *           | "click" (click vào link bài từ trang khác)
 *           | "full"  (cuộn >= 90% nội dung — đọc trọn vẹn)
 *
 * CÔNG THỨC PICK:
 *   FEATURED = bài có score cao nhất:
 *       score = views_7d + 0.6 * clicks_7d - 0.5 * full_reads_total
 *       (bài view nhiều trong 7 ngày, nhưng phạt nếu đọc trọn → ưu tiên bài còn dở dang)
 *       Override nếu có bài extra.featured = true: chọn featured_at mới nhất
 *       Fallback nếu chưa có override: analytics → bài mới nhất
 *
 *   RANDOM = weighted-random pick 5 bài, weight = exp(-age_days / 30)
 *       → bài mới có xác suất cao gấp e^(age/30) lần bài cũ
 *       → bài mới publish hôm nay weight = 1, bài 30 ngày trước weight = 0.37
 *       → bài mới luôn được xem xét tự động, không cần config thủ công
 *
 *   RANDOM SCORE = điểm chất lượng ngẫu nhiên 0–10 (badge cạnh "RANDOM POSTS"):
 *       computeRandomScore() chấm theo 5 tín hiệu (category/date/unique/topic/
 *       seed-freshness). Tính lại mỗi lần renderRandom() → đổi động khi reshuffle.
 *       Bấm badge (🎲) → reshuffle bài + điểm mới. Màu: <5 đỏ · 5–7 hổ phách · ≥8 xanh.
 *
 * TẮT/BẬT TÍNH NĂNG:
 *   - Tắt rotation random: gỡ tag <section data-widget="random"> hoặc bỏ script này
 *   - Tắt analytics: thêm sessionStorage.setItem("zola-no-track", "1") trong DevTools
 *   - Reset data:    localStorage.removeItem("zola-events")
 */
(function () {
  const STORAGE_KEY = "zola-events";
  const SEVEN_DAYS_MS = 7 * 24 * 60 * 60 * 1000;
  const RANDOM_COUNT = 5;
  const PREMIUM_COUNT = 10;
  const HALF_LIFE_DAYS = 30;
  const NO_TRACK = sessionStorage.getItem("zola-no-track") === "1";

  // Trọng số chấm điểm chất lượng ngẫu nhiên (tổng = 1.0) → score 0–10.
  const SCORE_WEIGHTS = {
    category: 0.25, // đa dạng chuyên mục
    date: 0.2, // đa dạng thời điểm đăng
    unique: 0.2, // không trùng bài
    topic: 0.2, // đa dạng chủ đề (tag)
    freshness: 0.15, // độ "tươi" của seed ngẫu nhiên
  };
  // Seed gần nhất — so bit khác biệt giữa 2 lần reshuffle để đo freshness.
  let lastSeed = (Math.random() * 0xffffffff) >>> 0;

  // ---------- Storage helpers ----------
  function loadEvents() {
    try {
      const arr = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
      if (!Array.isArray(arr)) return [];
      // Auto prune events older than 30 days to keep storage small
      const cutoff = Date.now() - 30 * 24 * 60 * 60 * 1000;
      return arr.filter((e) => e.ts >= cutoff);
    } catch {
      return [];
    }
  }

  function pushEvent(url, type) {
    if (NO_TRACK) return;
    const events = loadEvents();
    events.push({ url, ts: Date.now(), type });
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(events));
    } catch {
      // localStorage full or disabled — silently ignore
    }
  }

  // ---------- Load posts data ----------
  const dataEl = document.getElementById("posts-data");
  if (!dataEl) return;
  let posts;
  try {
    posts = JSON.parse(dataEl.textContent);
  } catch (e) {
    console.warn("[sidebar] posts-data parse failed", e);
    return;
  }
  if (!Array.isArray(posts) || posts.length === 0) return;

  // ---------- Scoring ----------
  function countEvents(events, url, type, since) {
    return events.filter(
      (e) => e.url === url && e.type === type && (since == null || e.ts >= since)
    ).length;
  }

  function pickFeatured(events) {
    // ƯU TIÊN 1: Bài user TỰ TICK featured = true → luôn thắng (override analytics).
    // Nếu nhiều bài cùng featured, bài được CMS stamp featured_at mới nhất thắng.
    const manualFeatured = posts
      .map((post, index) => ({ post, index }))
      .filter((item) => item.post.featured)
      .sort((a, b) => {
        const bStamp = b.post.featured_at || "";
        const aStamp = a.post.featured_at || "";
        if (aStamp !== bStamp) return bStamp.localeCompare(aStamp);
        return a.index - b.index; // posts đã sort date desc, giữ bài mới hơn khi không có stamp
      });
    if (manualFeatured.length > 0) {
      console.log("[featured] manual pick:", manualFeatured[0].post.title);
      return manualFeatured[0].post;
    }

    // ƯU TIÊN 2: Không có bài nào tick featured → dùng analytics
    const since7d = Date.now() - SEVEN_DAYS_MS;
    let scored = posts.map((p) => {
      const views7d = countEvents(events, p.permalink, "view", since7d);
      const clicks7d = countEvents(events, p.permalink, "click", since7d);
      const fullReads = countEvents(events, p.permalink, "full", null);
      const score = views7d + 0.6 * clicks7d - 0.5 * fullReads;
      return { post: p, score: score };
    });

    const hasAnyAnalytics = scored.some((s) => s.score > 0);
    if (!hasAnyAnalytics) {
      console.log("[featured] fallback: newest post");
      return posts[0]; // bài mới nhất
    }
    scored.sort((a, b) => b.score - a.score);
    console.log("[featured] analytics pick:", scored[0].post.title, "score:", scored[0].score);
    return scored[0].post;
  }

  function ageInDays(dateStr) {
    const ms = Date.now() - new Date(dateStr).getTime();
    return Math.max(0, ms / (1000 * 60 * 60 * 24));
  }

  function pickRandom(n) {
    const pool = posts.map((p) => ({
      post: p,
      weight: Math.exp(-ageInDays(p.date) / HALF_LIFE_DAYS),
    }));

    const picked = [];
    for (let i = 0; i < n && pool.length > 0; i++) {
      const total = pool.reduce((s, x) => s + x.weight, 0);
      let r = Math.random() * total;
      let idx = 0;
      for (; idx < pool.length; idx++) {
        r -= pool[idx].weight;
        if (r <= 0) break;
      }
      if (idx >= pool.length) idx = pool.length - 1;
      picked.push(pool[idx].post);
      pool.splice(idx, 1);
    }
    return picked;
  }

  // PREMIUM = pick tối đa n bài premium NGẪU NHIÊN mỗi lần load, KHÔNG trùng lặp.
  // Fisher-Yates shuffle trên pool premium rồi cắt n đầu → uniform random, no-dup.
  function pickPremium(n) {
    const pool = posts.filter((p) => p.premium);
    for (let i = pool.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      const tmp = pool[i];
      pool[i] = pool[j];
      pool[j] = tmp;
    }
    return pool.slice(0, n);
  }

  // ---------- Randomization quality score ----------
  // Chấm điểm 0–10 cho một set bài random dựa trên 5 tín hiệu đa dạng.
  // Tính lại mỗi lần reshuffle → điểm thay đổi động theo set mới + seed mới.
  function clamp01(x) {
    return x < 0 ? 0 : x > 1 ? 1 : x;
  }

  // Đếm số bit 1 của một số 32-bit (Hamming weight) — đo khác biệt 2 seed.
  function popcount32(x) {
    x = x - ((x >> 1) & 0x55555555);
    x = (x & 0x33333333) + ((x >> 2) & 0x33333333);
    x = (x + (x >> 4)) & 0x0f0f0f0f;
    return ((x * 0x01010101) >>> 24) & 0x3f;
  }

  // Quy về mốc NGÀY để đo đa dạng thời điểm đăng. Ngày (thay vì tháng) hợp với
  // picker thiên về bài mới: bài cùng ngày (blog hay đăng theo lô) mới bị trừ điểm.
  function dayBucket(dateStr) {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return String(dateStr || "");
    return d.getFullYear() + "-" + d.getMonth() + "-" + d.getDate();
  }

  function computeRandomScore(list) {
    const n = list.length;
    if (n === 0) return { score: 0, tier: "low" };

    // 1) Category diversity — số chuyên mục khác nhau / tối đa có thể đạt.
    const corpusTopics = new Set(posts.map((p) => p.topic || p.category || ""));
    const pickedTopics = new Set(list.map((p) => p.topic || p.category || ""));
    const catCap = Math.max(1, Math.min(n, corpusTopics.size));
    const categoryDiv = clamp01(pickedTopics.size / catCap);

    // 2) Publication date diversity — số ngày đăng khác nhau / n.
    const days = new Set(list.map((p) => dayBucket(p.date)));
    const dateDiv = clamp01(days.size / n);

    // 3) No duplicate posts — tỉ lệ permalink duy nhất.
    const uniq = new Set(list.map((p) => p.permalink));
    const uniqueScore = clamp01(uniq.size / n);

    // 4) Topic diversity — tag riêng biệt / tổng số tag (bài cùng series → thấp).
    let totalTags = 0;
    const tagSet = new Set();
    list.forEach((p) => {
      (p.tags || []).forEach((t) => {
        totalTags++;
        tagSet.add(String(t).toLowerCase());
      });
    });
    const topicDiv = totalTags > 0 ? clamp01(tagSet.size / totalTags) : 0.6;

    // 5) Seed freshness — seed mới mỗi lần, đo khác biệt bit so với seed trước.
    const seed = ((Date.now() & 0xffff) ^ ((Math.random() * 0xffffffff) >>> 0)) >>> 0;
    const freshness = 0.7 + 0.3 * (popcount32(seed ^ lastSeed) / 32);
    lastSeed = seed;

    const weighted =
      SCORE_WEIGHTS.category * categoryDiv +
      SCORE_WEIGHTS.date * dateDiv +
      SCORE_WEIGHTS.unique * uniqueScore +
      SCORE_WEIGHTS.topic * topicDiv +
      SCORE_WEIGHTS.freshness * freshness;

    // 0..1 → 0..10, làm tròn 1 chữ số thập phân.
    const score = Math.round(clamp01(weighted) * 100) / 10;
    const tier = score >= 8 ? "high" : score >= 5 ? "mid" : "low";
    return { score, tier };
  }

  function renderScore(result) {
    const badge = document.querySelector('[data-target="random-score"]');
    if (!badge) return;
    const valEl = badge.querySelector('[data-target="random-score-value"]');
    if (valEl) valEl.textContent = result.score.toFixed(1);
    badge.classList.remove("is-loading", "is-low", "is-mid", "is-high");
    badge.classList.add("is-" + result.tier);
    // Retrigger animation "pop" mỗi lần điểm đổi.
    badge.classList.remove("is-pop");
    void badge.offsetWidth; // force reflow
    badge.classList.add("is-pop");
  }

  // ---------- Rendering ----------
  function fmtDate(iso) {
    return (window.ZolaDateTime && window.ZolaDateTime.formatDisplayDate(iso)) || "";
  }

  function escapeHtml(s) {
    return String(s || "").replace(/[&<>"']/g, (c) => ({
      "&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"
    })[c]);
  }

  function renderFeatured(p) {
    const target = document.querySelector('[data-target="featured"]');
    if (!target) return;
    const author = "duynguyenlog";
    const cat = p.category ? `<span class="cat-tag">${escapeHtml(p.category.toUpperCase())}</span>` : "";
    const thumb = p.thumbnail ? `
      <a class="featured-card__image" href="${escapeHtml(p.permalink)}">
        ${cat}
        <img src="${escapeHtml(p.thumbnail)}" alt="${escapeHtml(p.title)}" loading="lazy">
        <span class="rank-overlay rank-overlay--lg" aria-hidden="true">1</span>
      </a>` : "";
    target.innerHTML = `
      ${thumb}
      <h4 class="featured-card__title">
        <a href="${escapeHtml(p.permalink)}">${escapeHtml(p.title)}</a>
      </h4>
      <div class="post-meta">
        <span class="post-meta__author">${author}</span>
        <span class="post-meta__date">${fmtDate(p.date)}</span>
      </div>
    `;
  }

  function renderRandom(list) {
    // Điểm chất lượng cập nhật kể cả khi list rỗng → badge luôn phản ánh set hiện tại.
    renderScore(computeRandomScore(list));
    const target = document.querySelector('[data-target="random"]');
    if (!target) return;
    target.innerHTML = list.map((p, i) => `
      <li class="random-item">
        ${p.thumbnail ? `
          <a class="random-item__image" href="${escapeHtml(p.permalink)}">
            <img src="${escapeHtml(p.thumbnail)}" alt="" loading="lazy">
            <span class="rank-overlay" aria-hidden="true">${i + 1}</span>
          </a>` : ""}
        <div class="random-item__body">
          <h5 class="random-item__title">
            <a href="${escapeHtml(p.permalink)}">${escapeHtml(p.title)}</a>
          </h5>
          <time class="random-item__date">${fmtDate(p.date)}</time>
        </div>
      </li>
    `).join("");
  }

  function renderPremium(list) {
    const target = document.querySelector('[data-target="premium"]');
    if (!target) return; // section chỉ render khi CÓ bài premium → guard an toàn
    target.innerHTML = list.map((p) => {
      return `
      <li class="premium-item">
        <a class="premium-item__link" href="${escapeHtml(p.permalink)}">
          <span class="premium-item__icon" aria-hidden="true">💎</span>
          <span class="premium-item__main">
            <span class="premium-item__title">${escapeHtml(p.title)}</span>
            <span class="premium-item__badges">
              <span class="premium-item__badge premium-item__badge--premium">💎 Chuyên sâu</span>
            </span>
          </span>
        </a>
      </li>`;
    }).join("");
  }

  // ---------- Event tracking ----------

  // Click on any link to a post → "click" event
  document.addEventListener("click", (e) => {
    const link = e.target.closest("a[href]");
    if (!link) return;
    const href = link.href;
    if (posts.some((p) => p.permalink === href)) {
      pushEvent(href, "click");
    }
  });

  // Current page is a post → "view" event
  const currentUrl = window.location.href.replace(/#.*$/, "").replace(/\?.*$/, "");
  const normalized = currentUrl.endsWith("/") ? currentUrl : currentUrl + "/";
  const currentPost = posts.find((p) => {
    const pp = p.permalink.endsWith("/") ? p.permalink : p.permalink + "/";
    return pp === normalized;
  });
  if (currentPost) {
    pushEvent(currentPost.permalink, "view");

    // Track 90% scroll → "full" event (only once per page load)
    let fullSent = false;
    const onScroll = () => {
      if (fullSent) return;
      const docH = document.documentElement.scrollHeight - window.innerHeight;
      if (docH <= 0) return;
      const pct = window.scrollY / docH;
      if (pct >= 0.9) {
        pushEvent(currentPost.permalink, "full");
        fullSent = true;
        window.removeEventListener("scroll", onScroll);
      }
    };
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  // ---------- Reshuffle (badge bấm để xáo lại) ----------
  // Mỗi lần reshuffle → pick mới + điểm mới (computeRandomScore). Đây là cơ chế
  // làm điểm "thay đổi động whenever the random posts are regenerated".
  function reshuffle() {
    const badge = document.querySelector('[data-target="random-score"]');
    if (badge) {
      badge.classList.remove("is-rolling");
      void badge.offsetWidth; // force reflow để chạy lại animation xúc xắc
      badge.classList.add("is-rolling");
    }
    renderRandom(pickRandom(RANDOM_COUNT));
  }

  const scoreBadge = document.querySelector('[data-target="random-score"]');
  if (scoreBadge) {
    // <button> tự xử lý Enter/Space → chỉ cần lắng nghe click.
    scoreBadge.addEventListener("click", reshuffle);
  }

  // ---------- Initial render ----------
  const events = loadEvents();
  renderFeatured(pickFeatured(events));
  renderRandom(pickRandom(RANDOM_COUNT));
  renderPremium(pickPremium(PREMIUM_COUNT));
})();
