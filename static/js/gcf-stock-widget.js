(function () {
  "use strict";

  var widget = document.querySelector("[data-gcf-stock]");
  if (!widget) return;
  if (!window.matchMedia("(min-width: 768px)").matches) return;

  var SOURCE_URL = "https://simplize.vn/co-phieu/GCF/lich-su-gia";
  var API_URL = "https://api.allorigins.win/get?url=" + encodeURIComponent(SOURCE_URL);
  var REFRESH_INTERVAL = 60000;
  var fallback = {
    name: "CTCP Thực phẩm G.C",
    price: "18,500",
    change: "+400",
    percent: "+2.21%",
    high: "18,500",
    low: "18,400",
    volume: "30,410"
  };

  var fields = {
    name: widget.querySelector("[data-gcf-name]"),
    price: widget.querySelector("[data-gcf-price]"),
    change: widget.querySelector("[data-gcf-change]"),
    high: widget.querySelector("[data-gcf-high]"),
    low: widget.querySelector("[data-gcf-low]"),
    volume: widget.querySelector("[data-gcf-volume]"),
    updated: widget.querySelector("[data-gcf-updated]"),
    notice: widget.querySelector("[data-gcf-notice]"),
    refresh: widget.querySelector("[data-gcf-refresh]")
  };

  function cleanText(value) {
    return (value || "").replace(/\u00a0/g, " ").replace(/\s+/g, " ").trim();
  }

  function valueAfter(text, label) {
    var start = text.toLowerCase().indexOf(label.toLowerCase());
    if (start < 0) return "";
    var tail = text.slice(start + label.length, start + label.length + 160);
    var match = tail.match(/[-+]?\d[\d.,]*/);
    return match ? match[0] : "";
  }

  function parseStockHtml(html) {
    var doc = new DOMParser().parseFromString(html, "text/html");
    var text = cleanText(doc.body ? doc.body.textContent : "");
    var price = valueAfter(text, "Giá hiện tại:");
    var high = valueAfter(text, "Giá cao nhất");
    var low = valueAfter(text, "Giá thấp nhất");
    var volume = valueAfter(text, "Khối lượng giao dịch TB 10 phiên");
    var priceIndex = text.toLowerCase().indexOf("giá hiện tại:");
    var quoteText = priceIndex >= 0 ? text.slice(priceIndex, priceIndex + 220) : text;
    var changeMatch = quoteText.match(/[+-]\s*\d[\d.,]*/);
    var percentMatch = quoteText.match(/[+-]?\s*\d+(?:[.,]\d+)?\s*%/);
    var heading = doc.querySelector("h1");
    var nameMatch = text.match(/(?:Công ty|CTCP)\s+(?:Cổ phần\s+)?Thực phẩm\s+G\.?C/i);
    var name = cleanText(heading && heading.textContent);

    if (!name || !/G\.?C|GCF/i.test(name)) {
      name = nameMatch ? cleanText(nameMatch[0]) : fallback.name;
    }
    if (!price || !high || !low || !volume || !changeMatch || !percentMatch) {
      throw new Error("Simplize response does not contain the expected GCF quote");
    }

    return {
      name: name,
      price: price,
      change: cleanText(changeMatch[0]),
      percent: cleanText(percentMatch[0]).replace(/\s/g, ""),
      high: high,
      low: low,
      volume: volume
    };
  }

  function render(data, isFallback) {
    var changeValue = parseFloat(data.change.replace(/\s/g, "").replace(",", "."));
    var direction = changeValue < 0 ? "is-negative" : "is-positive";

    fields.name.textContent = data.name;
    fields.price.textContent = data.price;
    fields.change.textContent = data.change + " (" + data.percent + ")";
    fields.change.classList.remove("is-positive", "is-negative");
    fields.change.classList.add(direction);
    fields.high.textContent = data.high;
    fields.low.textContent = data.low;
    fields.volume.textContent = data.volume;
    fields.updated.textContent = "Cập nhật: " + new Intl.DateTimeFormat("vi-VN", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
      timeZone: "Asia/Ho_Chi_Minh"
    }).format(new Date());
    fields.notice.hidden = !isFallback;
  }

  function update() {
    fields.refresh.disabled = true;
    fields.refresh.setAttribute("aria-busy", "true");

    fetch(API_URL, { headers: { Accept: "application/json" } })
      .then(function (response) {
        if (!response.ok) throw new Error("AllOrigins returned " + response.status);
        return response.json();
      })
      .then(function (payload) {
        if (!payload || typeof payload.contents !== "string") {
          throw new Error("AllOrigins response is invalid");
        }
        render(parseStockHtml(payload.contents), false);
      })
      .catch(function () {
        render(fallback, true);
      })
      .finally(function () {
        fields.refresh.disabled = false;
        fields.refresh.removeAttribute("aria-busy");
      });
  }

  fields.refresh.addEventListener("click", update);
  update();
  window.setInterval(update, REFRESH_INTERVAL);
})();
