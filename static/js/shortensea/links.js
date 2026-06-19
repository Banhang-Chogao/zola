(function () {
  "use strict";

  var toast = window.ShortenSEAToast;
  var api = window.ShortenSEAApi;
  var auth = window.ShortenSEAAuth;

  function formatDate(iso) {
    if (!iso) return "—";
    try {
      return new Date(iso).toLocaleString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
    } catch (e) { return iso; }
  }

  function truncate(url, n) {
    n = n || 40;
    return url.length > n ? url.slice(0, n) + "…" : url;
  }

  async function copyText(text) {
    if (navigator.clipboard) {
      await navigator.clipboard.writeText(text);
      toast.show("Đã copy!", "success");
      return;
    }
    toast.show("Copy thủ công: " + text, "success");
  }

  function renderLinks(links) {
    var tbody = document.querySelector("[data-sse-links-body]");
    if (!tbody) return;
    if (!links.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="shortensea__empty">Chưa có link nào. <a href="' +
        api.getBaseUrl() + '/shortensea/">Tạo link đầu tiên</a></td></tr>';
      return;
    }
    tbody.innerHTML = links.map(function (link) {
      var statusClass = link.status === "active" ? "shortensea__status--active" : "shortensea__status--disabled";
      return '<tr data-link-id="' + link.link_id + '">' +
        '<td><span class="shortensea__short-url">' + link.short_url + '</span></td>' +
        '<td title="' + link.destination_url + '">' + truncate(link.destination_url) + '</td>' +
        '<td>' + (link.title || "—") + '</td>' +
        '<td>' + formatDate(link.created_at) + '</td>' +
        '<td>' + (link.click_count || 0) + '</td>' +
        '<td><span class="shortensea__status ' + statusClass + '">' + (link.status || "active") + '</span></td>' +
        '<td><div class="shortensea__actions">' +
        '<button type="button" class="shortensea__btn shortensea__btn--ghost shortensea__btn--sm" data-action="copy" data-url="' + link.short_url + '">Copy</button>' +
        '<button type="button" class="shortensea__btn shortensea__btn--ghost shortensea__btn--sm" data-action="edit" data-id="' + link.link_id + '">Sửa</button>' +
        '<button type="button" class="shortensea__btn shortensea__btn--ghost shortensea__btn--sm shortensea__btn--danger" data-action="delete" data-id="' + link.link_id + '">Xóa</button>' +
        '</div></td></tr>';
    }).join("");

    tbody.querySelectorAll("[data-action=copy]").forEach(function (btn) {
      btn.addEventListener("click", function () { copyText(btn.getAttribute("data-url")); });
    });
    tbody.querySelectorAll("[data-action=edit]").forEach(function (btn) {
      btn.addEventListener("click", async function () {
        var id = btn.getAttribute("data-id");
        var row = links.find(function (l) { return l.link_id === id; });
        if (!row) return;
        var title = prompt("Title mới:", row.title || "");
        if (title === null) return;
        var dest = prompt("Destination URL:", row.destination_url);
        if (dest === null) return;
        try {
          await api.updateLink(id, { title: title, destination_url: dest });
          toast.show("Đã cập nhật link.", "success");
          loadLinks();
        } catch (e) {
          toast.show(e.message || "Cập nhật thất bại.", "error");
        }
      });
    });
    tbody.querySelectorAll("[data-action=delete]").forEach(function (btn) {
      btn.addEventListener("click", async function () {
        var id = btn.getAttribute("data-id");
        if (!confirm("Xóa link này?")) return;
        try {
          await api.deleteLink(id);
          toast.show("Đã xóa link.", "success");
          loadLinks();
        } catch (e) {
          toast.show(e.message || "Xóa thất bại.", "error");
        }
      });
    });
  }

  async function loadLinks() {
    try {
      var links = await api.listLinks();
      renderLinks(links);
    } catch (e) {
      toast.show(e.message || "Không tải được danh sách.", "error");
    }
  }

  document.addEventListener("DOMContentLoaded", async function () {
    if (!document.querySelector('[data-sse-page="links"]')) return;
    document.querySelectorAll('[data-sse-action="login"]').forEach(function (btn) {
      btn.addEventListener("click", function () { auth.login(); });
    });
    var user = await auth.init();
    if (!user) return;
    await loadLinks();
  });
})();