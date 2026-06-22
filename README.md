<section class="seo-github-insights">
  <h2>GitHub Pulse</h2>

  <div class="insight-grid">
    <article class="insight-card">
      <h3>Commit Activity</h3>
      <canvas id="commitChart" height="120"></canvas>
      <a href="https://github.com/tetdinhmui/tetdinhmui/graphs/commit-activity" target="_blank">Xem GitHub</a>
    </article>

    <article class="insight-card">
      <h3>Deploy / Actions</h3>
      <div class="action-buttons">
        <button class="ok">Thành công: <span id="successCount">0</span></button>
        <button class="fail">Thất bại: <span id="failCount">0</span></button>
      </div>
      <canvas id="actionsChart" height="120"></canvas>
      <a href="https://github.com/Banhang-Chogao/zola/actions" target="_blank">Xem Actions</a>
    </article>
  </div>
</section>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
(async () => {
  const headers = { Accept: "application/vnd.github+json" };

  const commitRes = await fetch(
    "https://api.github.com/repos/tetdinhmui/tetdinhmui/stats/commit_activity",
    { headers }
  );
  const commitData = await commitRes.json();

  const weeks = commitData.slice(-12).map(w =>
    new Date(w.week * 1000).toLocaleDateString("vi-VN", { month: "2-digit", day: "2-digit" })
  );
  const commits = commitData.slice(-12).map(w => w.total);

  new Chart(document.getElementById("commitChart"), {
    type: "line",
    data: {
      labels: weeks,
      datasets: [{ label: "Commits / tuần", data: commits, tension: 0.35 }]
    }
  });

  const actionsRes = await fetch(
    "https://api.github.com/repos/Banhang-Chogao/zola/actions/runs?per_page=30",
    { headers }
  );
  const actionsData = await actionsRes.json();

  const runs = actionsData.workflow_runs || [];
  const success = runs.filter(r => r.conclusion === "success").length;
  const fail = runs.filter(r => ["failure", "cancelled", "timed_out"].includes(r.conclusion)).length;

  document.getElementById("successCount").textContent = success;
  document.getElementById("failCount").textContent = fail;

  new Chart(document.getElementById("actionsChart"), {
    type: "doughnut",
    data: {
      labels: ["Thành công", "Thất bại"],
      datasets: [{ data: [success, fail] }]
    }
  });
})();
</script>

<style>
.seo-github-insights{padding:24px;border:1px solid #eee;border-radius:20px;background:#fff}
.insight-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}
.insight-card{padding:18px;border:1px solid #eee;border-radius:16px;box-shadow:0 8px 30px rgba(0,0,0,.04)}
.action-buttons{display:flex;gap:8px;margin:12px 0}
.action-buttons button{border:0;border-radius:999px;padding:8px 12px;font-weight:700}
.ok{background:#e8fff0}
.fail{background:#fff0f0}
.insight-card a{display:inline-block;margin-top:10px;font-size:14px}
</style>
