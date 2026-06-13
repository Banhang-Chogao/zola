(function () {
  const card = document.querySelector(".github-card");
  if (!card) return;

  const repo = card.dataset.repo;
  const msgEl = card.querySelector(".commit-box__msg");
  const hashEl = card.querySelector(".commit-box__hash");
  const noteEl = card.querySelector(".commit-box__note");
  const clockEl = card.querySelector(".github-card__clock");

  function pad(n) {
    return n < 10 ? "0" + n : "" + n;
  }

  function formatTime(d) {
    return pad(d.getHours()) + ":" + pad(d.getMinutes()) + " " +
           pad(d.getDate()) + "/" + pad(d.getMonth() + 1) + "/" + d.getFullYear();
  }

  function tick() {
    clockEl.textContent = formatTime(new Date());
  }
  tick();
  setInterval(tick, 30000);

  async function loadCommit() {
    try {
      const res = await fetch("https://api.github.com/repos/" + repo + "/commits?per_page=1", {
        headers: { "Accept": "application/vnd.github+json" }
      });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      if (!Array.isArray(data) || !data.length) throw new Error("empty");

      const c = data[0];
      const sha = c.sha.substring(0, 7);
      const title = c.commit.message.split("\n")[0];

      msgEl.textContent = title;
      hashEl.textContent = sha;
      noteEl.textContent = "Code mới nhất đã được GitHub ghi nhận.";
    } catch (err) {
      msgEl.textContent = "Không tải được commit";
      hashEl.textContent = "ERROR";
      noteEl.textContent = err.message;
      const tags = card.querySelector(".github-card__tags");
      const active = tags.querySelector(".tag--active");
      if (active) {
        active.textContent = "KHÔNG TẢI ĐƯỢC";
        active.classList.remove("tag--active");
        active.classList.add("tag--error");
      }
    }
  }

  loadCommit();
})();
