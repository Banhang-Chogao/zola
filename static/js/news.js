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

  function parseFeed(xmlText) {
    const xml = new DOMParser().parseFromString(xmlText, "text/xml");
    if (xml.querySelector("parsererror")) throw new Error("invalid xml");
    const items = Array.from(xml.querySelectorAll("item")).slice(0, 6);
    return items.map((item) => {
      const title = (item.querySelector("title")?.textContent || "").trim();
      const link = (item.querySelector("link")?.textContent || "#").trim();
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
      li.innerHTML =
        '<span class="news-item__num">' + pad(i + 1) + "</span>" +
        '<div class="news-item__body">' +
        '<a class="news-item__title" href="' + it.link + '" target="_blank" rel="noopener"></a>' +
        '<span class="news-item__time"></span>' +
        "</div>";
      li.querySelector(".news-item__title").textContent = it.title;
      li.querySelector(".news-item__time").textContent = timeAgo(it.date);
      list.appendChild(li);
    });
    const count = card.querySelector(".count");
    if (count) count.textContent = items.length + " tin mới nhất";
  }

  function renderError(card, msg) {
    const list = card.querySelector(".news-card__list");
    list.innerHTML =
      '<li class="news-item news-item--error">' +
      '<div class="news-error">' +
      '<div class="news-error__title">Không tải được tin</div>' +
      '<div class="news-error__msg">' + (msg || "fetch failed") + "</div>" +
      "</div></li>";
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
