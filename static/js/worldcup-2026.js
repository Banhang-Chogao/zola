/**
 * WorldCup 2026 News Hub
 * Client-side filtering, stats calculation, and interactivity.
 * Static-first: all data loaded from HTML (data attributes).
 */

(function () {
  'use strict';

  const DOM = {
    filterTabs: document.querySelectorAll('[data-filter]'),
    newsCards: document.querySelectorAll('[data-category]'),
    statElements: {
      news: document.querySelector('[data-stat="news-count"]'),
      match: document.querySelector('[data-stat="match-count"]'),
      team: document.querySelector('[data-stat="team-count"]'),
      editorial: document.querySelector('[data-stat="editorial-count"]'),
    },
  };

  /**
   * Calculate and display stats
   */
  function updateStats() {
    const newsCount = DOM.newsCards.length;
    const matchCount = document.querySelectorAll('.worldcup-2026__match-card').length;
    const teamCount = document.querySelectorAll('.worldcup-2026__team-chip').length;
    const editorialCount = document.querySelectorAll('.worldcup-2026__editorial-card').length;

    if (DOM.statElements.news) DOM.statElements.news.textContent = newsCount || '—';
    if (DOM.statElements.match) DOM.statElements.match.textContent = matchCount || '—';
    if (DOM.statElements.team) DOM.statElements.team.textContent = teamCount || '—';
    if (DOM.statElements.editorial) DOM.statElements.editorial.textContent = editorialCount || '—';
  }

  /**
   * Filter news cards by category
   */
  function filterByCategory(category) {
    DOM.newsCards.forEach(card => {
      const cardCategory = card.getAttribute('data-category');
      const shouldShow = category === 'all' || cardCategory === category;

      if (shouldShow) {
        card.style.display = '';
        requestAnimationFrame(() => {
          card.classList.add('visible');
        });
      } else {
        card.style.display = 'none';
        card.classList.remove('visible');
      }
    });
  }

  /**
   * Update active filter tab
   */
  function setActiveTab(activeTab) {
    DOM.filterTabs.forEach(tab => {
      const isActive = tab === activeTab;
      tab.classList.toggle('worldcup-2026__filter-tab--active', isActive);
      tab.setAttribute('aria-selected', isActive);
    });
  }

  /**
   * Initialize filter event listeners
   */
  function initFilters() {
    DOM.filterTabs.forEach(tab => {
      tab.addEventListener('click', () => {
        const category = tab.getAttribute('data-filter');
        filterByCategory(category);
        setActiveTab(tab);

        // Scroll to news section smoothly
        const newsPanel = document.getElementById('news-panel');
        if (newsPanel) {
          newsPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      });
    });
  }

  /**
   * Smooth scroll for anchor links
   */
  function initAnchorLinks() {
    document.querySelectorAll('a[href^="#"]').forEach(link => {
      link.addEventListener('click', e => {
        const target = document.querySelector(link.getAttribute('href'));
        if (target) {
          e.preventDefault();
          target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      });
    });
  }

  /**
   * Initialize dark mode support
   */
  function initDarkMode() {
    // CSS handles dark mode via prefers-color-scheme media query
    // and semantic tokens var(--c-*) from _themes.scss
    // No JS needed unless user theme toggle is added later.
  }

  /**
   * Main initialization
   */
  function init() {
    updateStats();
    initFilters();
    initAnchorLinks();
    initDarkMode();

    // Log initialization (dev only)
    if (process.env.NODE_ENV === 'development' || false) {
      console.log('WorldCup 2026 Hub initialized', {
        newsCards: DOM.newsCards.length,
        filterTabs: DOM.filterTabs.length,
      });
    }
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
