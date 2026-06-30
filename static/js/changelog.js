(function () {
  "use strict";

  const list = document.querySelector("[data-changelog-list]");
  const pagination = document.querySelector("[data-changelog-pagination]");
  if (!list || !pagination) return;

  const pageSize = Number(list.dataset.pageSize) || 50;
  const source = list.dataset.source;
  const previous = pagination.querySelector("[data-page-prev]");
  const next = pagination.querySelector("[data-page-next]");
  const status = pagination.querySelector("[data-page-status]");
  const numbers = pagination.querySelector("[data-page-numbers]");
  let items = [];
  let currentPage = 1;

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function entryNode(item, index) {
    const repository = item.repository || "Banhang-Chogao/zola";
    const statusName = normaliseStatus(item.status);
    const prNumber = Number(item.pr) || 0;
    const runNumber = item.run_number || (prNumber || "—");
    const sha = String(item.commit || item.commit_sha || "");
    const li = element("li", "changelog__item changelog__item--" + statusName);

    const icon = element("div", "changelog__status-icon changelog__status-icon--" + statusName, statusIcon(statusName));
    icon.setAttribute("aria-label", statusLabel(statusName));

    const content = element("article", "changelog__content");
    const head = element("div", "changelog__head");
    const title = "Build #" + runNumber + " — " + (item.title || "Không có tiêu đề") +
      (prNumber ? " (#" + prNumber + ")" : "");
    head.appendChild(element("h3", "changelog__item-title", title));
    head.appendChild(element("span", "changelog__status changelog__status--" + statusName, statusLabel(statusName)));
    content.appendChild(head);

    const technical = element("div", "changelog__technical");
    if (sha) technical.appendChild(element("code", "changelog__sha", sha.slice(0, 12)));
    if (item.tag) {
      technical.appendChild(element("span", "changelog__tag changelog__tag--" + String(item.tag).toLowerCase(), item.tag));
    }
    if (technical.childNodes.length) content.appendChild(technical);

    const summary = item.summary ||
      (Array.isArray(item.highlights) && item.highlights.length ? item.highlights[0] : item.title);
    if (summary) content.appendChild(element("p", "changelog__summary", summary));

    const links = element("div", "changelog__links");
    if (prNumber) {
      appendLink(links, "Xem PR", "https://github.com/" + repository + "/pull/" + encodeURIComponent(prNumber));
    }
    if (sha) appendLink(links, "Xem Commit", "https://github.com/" + repository + "/commit/" + encodeURIComponent(sha));
    if (item.run_url) appendLink(links, "Xem GitHub Action Run", item.run_url);
    if (links.childNodes.length) content.appendChild(links);

    const footer = element("footer", "changelog__card-footer");
    footer.appendChild(element("span", "", repository));
    const mergedAt = item.merged_at || item.date || "";
    const date = element("time", "", formatDate(mergedAt));
    date.dateTime = mergedAt;
    footer.appendChild(date);
    footer.appendChild(element("span", "", item.author ? "@" + String(item.author).replace(/^@/, "") : "Không rõ tác giả"));
    content.appendChild(footer);

    li.appendChild(icon);
    li.appendChild(content);
    li.dataset.order = String(index);
    return li;
  }

  function appendLink(parent, label, href) {
    const link = element("a", "changelog__action-link", label);
    link.href = href;
    link.target = "_blank";
    link.rel = "noopener";
    parent.appendChild(link);
  }

  function normaliseStatus(value) {
    const statusName = String(value || "success").toLowerCase();
    if (statusName === "failure" || statusName === "failed") return "failure";
    if (statusName === "cancelled" || statusName === "canceled") return "cancelled";
    if (statusName === "in_progress" || statusName === "queued") return "pending";
    return "success";
  }

  function statusIcon(statusName) {
    return { success: "✓", failure: "×", cancelled: "−", pending: "●" }[statusName];
  }

  function statusLabel(statusName) {
    return { success: "success", failure: "failure", cancelled: "cancelled", pending: "pending" }[statusName];
  }

  function formatDate(value) {
    if (!value) return "Không rõ thời gian";
    const parsed = new Date(value);
    if (!Number.isNaN(parsed.getTime())) {
      return new Intl.DateTimeFormat("vi-VN", {
        dateStyle: "medium",
        timeStyle: String(value).includes("T") ? "short" : undefined,
      }).format(parsed);
    }
    return value;
  }

  function pageFromUrl() {
    const value = Number(new URL(window.location.href).searchParams.get("page"));
    return Number.isInteger(value) && value > 0 ? value : 1;
  }

  function setUrl(page) {
    const url = new URL(window.location.href);
    if (page === 1) url.searchParams.delete("page");
    else url.searchParams.set("page", String(page));
    history.replaceState(null, "", url);
  }

  function renderNumbers(totalPages) {
    numbers.replaceChildren();
    const start = Math.max(1, currentPage - 2);
    const end = Math.min(totalPages, currentPage + 2);
    for (let page = start; page <= end; page += 1) {
      const button = element("button", "changelog__page-number", String(page));
      button.type = "button";
      button.setAttribute("aria-label", "Trang " + page);
      if (page === currentPage) {
        button.classList.add("is-current");
        button.setAttribute("aria-current", "page");
      }
      button.addEventListener("click", function () { showPage(page, true); });
      numbers.appendChild(button);
    }
  }

  function showPage(requestedPage, scroll) {
    const totalPages = Math.max(1, Math.ceil(items.length / pageSize));
    currentPage = Math.min(Math.max(1, requestedPage), totalPages);
    const start = (currentPage - 1) * pageSize;
    const fragment = document.createDocumentFragment();
    if (!items.length) {
      fragment.appendChild(element("li", "changelog__empty", "Chưa có bản build nào trong lịch sử."));
    }
    items.slice(start, start + pageSize).forEach(function (item, index) {
      fragment.appendChild(entryNode(item, start + index));
    });
    list.replaceChildren(fragment);
    previous.disabled = currentPage === 1;
    next.disabled = currentPage === totalPages;
    status.textContent = "Trang " + currentPage + " / " + totalPages + " · " + items.length + " cập nhật";
    renderNumbers(totalPages);
    pagination.hidden = totalPages <= 1;
    setUrl(currentPage);
    if (scroll) list.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function sortNewestFirst(entries) {
    return entries.map(function (item, index) {
      return { item: item, index: index };
    }).sort(function (a, b) {
      const dateOrder = String(b.item.date || "").localeCompare(String(a.item.date || ""));
      return dateOrder || a.index - b.index;
    }).map(function (entry) { return entry.item; });
  }

  previous.addEventListener("click", function () { showPage(currentPage - 1, true); });
  next.addEventListener("click", function () { showPage(currentPage + 1, true); });
  window.addEventListener("popstate", function () { showPage(pageFromUrl(), false); });

  fetch(source, { cache: "no-store", headers: { Accept: "application/json" } })
    .then(function (response) {
      if (!response.ok) throw new Error("HTTP " + response.status);
      return response.json();
    })
    .then(function (data) {
      if (!data || !Array.isArray(data.items)) throw new Error("Invalid changelog data");
      items = sortNewestFirst(data.items);
      showPage(pageFromUrl(), false);
    })
    .catch(function (error) {
      console.warn("[Changelog] Live data unavailable; keeping build-time first page.", error);
      pagination.hidden = true;
    });
}());
