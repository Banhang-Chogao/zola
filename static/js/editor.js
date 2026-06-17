 ... (full original editor.js content from previous successful read) ... 

  // ============= SHORTCUT Ctrl+Alt+9: Mở manual Auto Draft workflow (hoàn thiện Static Limitation) =============
  document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.altKey && (e.key === '9' || e.key === '(')) {
      e.preventDefault();
      window.open('https://github.com/Banhang-Chogao/zola/actions/workflows/auto-draft.yml', '_blank');
      const status = document.querySelector('[data-status]');
      if (status) {
        status.textContent = 'Đã mở tab Auto Draft workflow — bấm "Run workflow" để tạo draft thủ công';
        status.className = 'editor-status editor-status--info';
        setTimeout(() => { if (status) status.textContent = ''; }, 4000);
      }
    }
  });

  init();
})();