(function () {
  const PROXY = "https://api.allorigins.win/get?url=";

  function timeAgo(date) {
    const diff = Math.floor((Date.now() - date.getTime()) / 1000);
    if (diff < 60) return diff + " giây trước";
    if (diff < 3600) return Math.floor(diff / 60) + " phút trước";
    if (diff < 86400) return Math.floor(diff / 3600) + " giờ trước";
    return Math.floor(diff / 86400) + " ngày trước";
  }

  function pad(n) {
    return n < 10 ? "0" + n : "" + n;
  }

  function formatClock(d) {
    return pad(d.getHours()) + ":" + pad(d.getMinutes());
  }

  function formatDate(d) {
    return pad(d.getDate()) + "/" + pad(d.getMonth() + 1) + "/" + d.getFullYear();
  }

  // Security: chỉ accept http/https URLs từ RSS link. Block javascript:, data:,
  // file:, vbscript:, … — RSS từ external feed (VnExpress, Tuổi Trẻ, …) không
  // được trust 100%, nếu feed bị compromise thì link bẩn không thành XSS sink.
  function safeUrl(url) {
    if (typeof url !== "string") return "#";
    const trimmed = url.trim();
    if (/^https?:\/\//i.test(trimmed)) return trimmed;
    return "#";
  }

  function parseFeed(xmlText) {
    const xml = new DOMParser().parseFromString(xmlText, "text/xml");
    if (xml.querySelector("parsererror")) throw new Error("invalid xml");
    const items = Array.from(xml.querySelectorAll("item")).slice(0, 6);
    return items.map((item) => {
      const title = (item.querySelector("title")?.textContent || "").trim();
      const link = safeUrl(item.querySelector("link")?.textContent || "#");
      const pubDate = item.querySelector("pubDate")?.textContent;
      const date = pubDate ? new Date(pubDate) : new Date();
      return { title, link, date };
    });
  }

  function renderItems(card, items) {
    const list = card.querySelector(".news-card__list");
    list.innerHTML = "";
    items.forEach((it, i) => {
      const li = document.createElement("li");
      li.className = "news-item";
      // Tạo DOM elements thay vì concat innerHTML — title/link bypass HTML parser
      // hoàn toàn, không có vector XSS dù RSS feed có chứa chuỗi độc hại.
      const num = document.createElement("span");
      num.className = "news-item__num";
      num.textContent = pad(i + 1);
      const body = document.createElement("div");
      body.className = "news-item__body";
      const a = document.createElement("a");
      a.className = "news-item__title";
      a.href = it.link;            // safeUrl đã validate
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.textContent = it.title;    // textContent → không parse HTML
      const time = document.createElement("span");
      time.className = "news-item__time";
      time.textContent = timeAgo(it.date);
      body.appendChild(a);
      body.appendChild(time);
      li.appendChild(num);
      li.appendChild(body);
      list.appendChild(li);
    });
    const count = card.querySelector(".count");
    if (count) count.textContent = items.length + " tin mới nhất";
  }

  function renderError(card, msg) {
    const list = card.querySelector(".news-card__list");
    list.innerHTML = ""; // clear safely
    const li = document.createElement("li");
    li.className = "news-item news-item--error";
    const errDiv = document.createElement("div");
    errDiv.className = "news-error";
    const title = document.createElement("div");
    title.className = "news-error__title";
    title.textContent = "Không tải được tin";
    const msgDiv = document.createElement("div");
    msgDiv.className = "news-error__msg";
    msgDiv.textContent = msg || "fetch failed"; // textContent — escape mọi HTML
    errDiv.appendChild(title);
    errDiv.appendChild(msgDiv);
    li.appendChild(errDiv);
    list.appendChild(li);
    const tags = card.querySelector(".news-card__tags");
    const updateTag = tags.querySelector("[data-update]");
    if (updateTag) {
      updateTag.textContent = "KHÔNG TẢI ĐƯỢC";
      updateTag.classList.remove("tag--update");
      updateTag.classList.add("tag--error");
    }
    const count = card.querySelector(".count");
    if (count) count.textContent = "0 tin mới nhất";
  }

  function updateClock(card) {
    const now = new Date();
    const c = card.querySelector(".news-card__clock");
    const d = card.querySelector(".news-card__date");
    if (c) c.textContent = formatClock(now);
    if (d) d.textContent = formatDate(now);
  }

  async function loadCard(card) {
    const feed = card.dataset.feed;
    updateClock(card);
    try {
      const res = await fetch(PROXY + encodeURIComponent(feed), { cache: "no-store" });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      const items = parseFeed(data.contents);
      if (!items.length) throw new Error("empty feed");
      renderItems(card, items);
    } catch (err) {
      renderError(card, err.message);
    }
  }

  document.querySelectorAll(".news-card").forEach(loadCard);

  setInterval(() => {
    document.querySelectorAll(".news-card").forEach(updateClock);
  }, 30000);
})();
