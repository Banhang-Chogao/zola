 ... full original JS content ... 

  // ============= SHORTCUT Ctrl+Alt+9: Mở manual Auto Draft workflow (giải quyết Static Limitation trên GitHub Pages) =============
  document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.altKey && (e.key === '9' || e.key === '(')) {
      e.preventDefault();
      // Mở tab GitHub Actions workflow để user bấm "Run workflow" thủ công
      window.open('https://github.com/Banhang-Chogao/zola/actions/workflows/auto-draft.yml', '_blank');
      // Optional: show toast
      const status = document.querySelector('[data-status]');
      if (status) {
        status.textContent = 'Đã mở tab Auto Draft workflow (Ctrl+Alt+9) — bấm Run workflow để tạo draft thủ công';
        status.className = 'editor-status editor-status--info';
        setTimeout(() => { if (status) status.textContent = ''; }, 4000);
      }
    }
  });

  init();
})();