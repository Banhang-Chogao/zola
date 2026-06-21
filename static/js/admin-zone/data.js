/**
 * Operation Guideline data
 * Extracted from CLAUDE.md vaccines, rules, and procedures
 */

(function () {
  window.AdminZoneData = window.AdminZoneData || {};

  const guidelines = [
    {
      id: "v1",
      code: "V1",
      name: "HuggingFace Model ID",
      purpose: "Tự động sửa 401 lỗi khi fetch HF model không có org prefix",
      template: 'Thêm `"sentence-transformers/"` vào model ID khi gọi `snapshot_download`',
    },
    {
      id: "v5",
      code: "V5",
      name: "GitHub Pages Rate Limit",
      purpose: "Tự động xử lý khi configure-pages bị rate limit",
      template: "Thêm `concurrency.cancel-in-progress: true` vào deploy.yml và retry exponential backoff",
    },
    {
      id: "v8",
      code: "V8",
      name: "Tera Syntax — replace Filter",
      purpose: "Phát hiện lỗi replace(old=) thay vì replace(from=) trong Tera templates",
      template: "Đổi `replace(old=X, new=Y)` thành `replace(from=X, to=Y)` trong Tera templates",
    },
    {
      id: "v9",
      code: "V9",
      name: "Stale Branch Base",
      purpose: "Xử lý PR docs-only vẫn fail do base branch cũ và build bugs trên main đã fix",
      template: "Rebase PR lên origin/main, chạy lại QA và zola build",
    },
    {
      id: "v10",
      code: "V10",
      name: "Dirty PR / Merge Race",
      purpose: "Xử lý conflict khi branch bị stale so với main do generated data",
      template: "Merge main, resolve conflict (giữ both sides cho registry), regenerate data, chạy QA",
    },
    {
      id: "zero-barrier",
      code: "ZERO_BARRIER",
      name: "Zero Barrier Auto-Merge",
      purpose: "Tự động merge PR khi QA xanh — không cần manual approval",
      template: "auto-merge.yml sử dụng try_auto_merge.py → merge SQUASH khi qa-check pass",
    },
    {
      id: "v21",
      code: "V21",
      name: "No Floating Bar",
      purpose: "Chặn desktop nav từ sticky/fixed — phải giữ trong normal flow",
      template: ".side-nav { position: static } — KHÔNG dùng sticky/fixed trên desktop",
    },
    {
      id: "v27",
      code: "V27",
      name: "GA Stats Module",
      purpose: "GA4 property mới (542421812) sau migrate sang seomoney.org",
      template: "Cập nhật config.toml: ga_property_id=542421812, ga_measurement_id=G-SMTFZVC0XN",
    },
  ];

  function getAllGuidelines() {
    return guidelines;
  }

  function searchGuidelines(query) {
    if (!query || query.length === 0) return [];
    const q = query.toLowerCase().trim();
    return guidelines.filter(g => {
      return (
        g.code.toLowerCase().includes(q) ||
        g.name.toLowerCase().includes(q) ||
        g.purpose.toLowerCase().includes(q)
      );
    });
  }

  function getGuidelineById(id) {
    return guidelines.find(g => g.id === id);
  }

  Object.assign(window.AdminZoneData, {
    getAllGuidelines,
    searchGuidelines,
    getGuidelineById,
  });
})();
