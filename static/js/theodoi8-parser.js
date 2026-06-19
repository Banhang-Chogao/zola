/**
 * THEODOI8 shared parser — format JSON report (build_theodoi8_report.py) thành
 * output terminal giống shortcut `theodoi8`. Dùng bởi theodoi8-banner.js + live-theodoi8.js.
 */
(function (global) {
  "use strict";

  var STATUS = {
    running: { cls: "is-running", icon: "🔄", label: "in_progress" },
    success: { cls: "is-success", icon: "✅", label: "success" },
    failure: { cls: "is-failure", icon: "❌", label: "failure" },
    cancelled: { cls: "is-cancelled", icon: "⊘", label: "cancelled" },
    idle: { cls: "is-idle", icon: "📡", label: "idle" }
  };

  var QUEUED = ["queued", "waiting", "pending", "requested"];

  function padEnd(str, len) {
    str = String(str == null ? "" : str);
    while (str.length < len) str += " ";
    return str.length > len ? str.slice(0, len - 1) + "…" : str;
  }

  function formatTimeVN(iso) {
    if (!iso) return "—";
    try {
      var d = new Date(iso);
      if (isNaN(d.getTime())) return "—";
      var p = function (n) {
        return n < 10 ? "0" + n : String(n);
      };
      var vn = new Date(d.toLocaleString("en-US", { timeZone: "Asia/Ho_Chi_Minh" }));
      return (
        p(vn.getHours()) +
        ":" +
        p(vn.getMinutes()) +
        ":" +
        p(vn.getSeconds()) +
        " " +
        p(vn.getDate()) +
        "/" +
        p(vn.getMonth() + 1) +
        "/" +
        vn.getFullYear() +
        " GMT+7"
      );
    } catch (e) {
      return "—";
    }
  }

  function rowBadge(row) {
    var rs = row && row.run_status;
    if (rs && QUEUED.indexOf(rs) >= 0) {
      return { icon: "⏳", label: "queued" };
    }
    if (row && (row.status === "running" || rs === "in_progress")) {
      return { icon: "🔄", label: "in_progress" };
    }
    if (row && row.status === "success") return { icon: "✅", label: "success" };
    if (row && row.status === "failure") return { icon: "❌", label: "failure" };
    if (row && row.status === "cancelled") return { icon: "⊘", label: "cancelled" };
    return { icon: "📡", label: "idle" };
  }

  function sortCommits(commits) {
    var list = (commits || []).slice();
    var rank = { running: 0, failure: 1, cancelled: 2, success: 3, idle: 4 };
    list.sort(function (a, b) {
      var ra = rank[a.status] != null ? rank[a.status] : 9;
      var rb = rank[b.status] != null ? rank[b.status] : 9;
      return ra - rb;
    });
    return list;
  }

  function changeLabel(prevMap, row) {
    if (!prevMap || !row || !row.sha) return "—";
    var prev = prevMap[row.sha];
    if (!prev || prev === row.status) return "—";
    var prevB = rowBadge({ status: prev, run_status: prev === "running" ? "in_progress" : "" });
    var nextB = rowBadge(row);
    return prevB.icon + "→" + nextB.icon;
  }

  function formatRoundSummary(data, roundNum) {
    if (!data || typeof data !== "object") return "";
    var summary = data.summary || "Theo dõi commit & CI/CD chạy trực tiếp trên GitHub Actions";
    var time = formatTimeVN(data.generated_at) || data.generated_at_display || "—";
    return "theodoi8 [vòng " + roundNum + "]: " + summary + " (" + time + ")";
  }

  function formatTerminalTable(commits, prevCommits) {
    var prevMap = {};
    (prevCommits || []).forEach(function (c) {
      if (c && c.sha) prevMap[c.sha] = c.status;
    });
    var rows = sortCommits(commits);
    if (!rows.length) {
      return (
        "┌────────┬──────────────────────────────┬─────────────────────────┬────────────────┬─────┐\n" +
        "│ Commit │ Message                      │ Workflow (run #)        │ Trạng thái     │ Đổi?│\n" +
        "├────────┼──────────────────────────────┼─────────────────────────┼────────────────┼─────┤\n" +
        "│ —      │ Chưa có commit đang theo dõi │ —                       │ 📡 idle        │ —   │\n" +
        "└────────┴──────────────────────────────┴─────────────────────────┴────────────────┴─────┘"
      );
    }

    var lines = [
      "┌────────┬──────────────────────────────┬─────────────────────────┬────────────────┬─────┐",
      "│ Commit │ Message                      │ Workflow (run #)        │ Trạng thái     │ Đổi?│",
      "├────────┼──────────────────────────────┼─────────────────────────┼────────────────┼─────┤"
    ];

    rows.forEach(function (r) {
      var badge = rowBadge(r);
      var wf = r.run_name || "—";
      if (r.run_number) wf += " #" + r.run_number;
      var statusCol = badge.icon + " " + badge.label;
      lines.push(
        "│ " +
          padEnd(r.sha || "—", 6) +
          " │ " +
          padEnd(r.message || "—", 28) +
          " │ " +
          padEnd(wf, 23) +
          " │ " +
          padEnd(statusCol, 14) +
          " │ " +
          padEnd(changeLabel(prevMap, r), 3) +
          " │"
      );
    });

    lines.push(
      "└────────┴──────────────────────────────┴─────────────────────────┴────────────────┴─────┘"
    );
    return lines.join("\n");
  }

  function formatTerminalRound(data, roundNum, prevCommits) {
    return formatRoundSummary(data, roundNum) + "\n\n" + formatTerminalTable(data.commits, prevCommits);
  }

  function hasActiveRuns(data) {
    if (!data) return false;
    if (data.status === "running") return true;
    var c = data.counts || {};
    return (c.running || 0) > 0;
  }

  function overallBadge(data) {
    if (!data) return STATUS.idle;
    if (hasActiveRuns(data)) {
      var commits = data.commits || [];
      for (var i = 0; i < commits.length; i++) {
        var b = rowBadge(commits[i]);
        if (b.label === "queued") return { cls: "is-queued", icon: "⏳", label: "queued" };
      }
      return STATUS.running;
    }
    return STATUS[data.status] || STATUS.idle;
  }

  function reportUrl(baseUrl) {
    var root = (baseUrl || "").replace(/\/$/, "");
    if (!root) {
      var m = document.querySelector('meta[name="zola-base-url"]');
      root = m ? m.content.replace(/\/$/, "") : "";
    }
    return root + "/data/theodoi8-report.json";
  }

  global.Theodoi8Parser = {
    STATUS: STATUS,
    rowBadge: rowBadge,
    sortCommits: sortCommits,
    formatTimeVN: formatTimeVN,
    formatRoundSummary: formatRoundSummary,
    formatTerminalTable: formatTerminalTable,
    formatTerminalRound: formatTerminalRound,
    hasActiveRuns: hasActiveRuns,
    overallBadge: overallBadge,
    reportUrl: reportUrl
  };
})(typeof window !== "undefined" ? window : this);