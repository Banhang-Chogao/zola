(() => {
  const roots = document.querySelectorAll(".post-single__content");
  if (!roots.length) return;

  roots.forEach((root) => {
    root.querySelectorAll("pre > code").forEach((code) => {
      const pre = code.parentElement;
      if (!pre || pre.dataset.copyReady) return;

      pre.dataset.copyReady = "true";
      pre.classList.add("code-copy");

      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "code-copy__btn";
      btn.textContent = "Copy";
      btn.setAttribute("aria-label", "Copy code");

      btn.addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText(code.innerText);
          btn.textContent = "Đã copy";
          btn.classList.add("is-copied");

          window.setTimeout(() => {
            btn.textContent = "Copy";
            btn.classList.remove("is-copied");
          }, 1600);
        } catch (_) {
          btn.textContent = "Không copy được";
          window.setTimeout(() => {
            btn.textContent = "Copy";
          }, 1600);
        }
      });

      pre.appendChild(btn);
    });
  });
})();
