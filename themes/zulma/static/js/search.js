// Search Functionality

let searchIndex = null;
let searchData = [];

async function initSearch() {
    const searchToggleBtn = document.getElementById('search-toggle');
    const searchModal = document.getElementById('search-modal');
    const searchCloseBtn = document.getElementById('search-close');
    const searchInput = document.getElementById('search-input');

    if (!searchToggleBtn) return;

    // Load search index
    await loadSearchIndex();

    // Toggle search modal
    searchToggleBtn.addEventListener('click', () => {
        searchModal.style.display = 'flex';
        searchInput.focus();
    });

    searchCloseBtn.addEventListener('click', () => {
        searchModal.style.display = 'none';
    });

    // Close on background click
    searchModal.addEventListener('click', (e) => {
        if (e.target === searchModal) {
            searchModal.style.display = 'none';
        }
    });

    // Search on input
    searchInput.addEventListener('input', (e) => {
        performSearch(e.target.value);
    });

    // Close on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            searchModal.style.display = 'none';
        }
        // Open search on Ctrl+K or Cmd+K
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            searchModal.style.display = 'flex';
            searchInput.focus();
        }
    });
}

async function loadSearchIndex() {
    try {
        const response = await fetch(document.location.origin + '/search_index.en.json');
        const data = await response.json();
        searchIndex = data;
        searchData = data.docs || [];
    } catch (error) {
        console.warn('Could not load search index:', error);
        searchData = [];
    }
}

function performSearch(query) {
    const searchResults = document.getElementById('search-results');

    if (!query.trim()) {
        searchResults.innerHTML = '';
        return;
    }

    const results = searchData.filter(doc => {
        const text = (doc.title + ' ' + (doc.body || '')).toLowerCase();
        return text.includes(query.toLowerCase());
    }).slice(0, 10);

    if (results.length === 0) {
        searchResults.innerHTML = '<div class="search-empty">No results found</div>';
        return;
    }

    const html = results.map(result => `
        <div class="search-result">
            <h4><a href="${result.url}">${highlightQuery(result.title, query)}</a></h4>
            <p>${highlightQuery((result.body || '').substring(0, 150), query)}</p>
        </div>
    `).join('');

    searchResults.innerHTML = html;

    // Add click handlers to results
    searchResults.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => {
            searchModal.style.display = 'none';
        });
    });
}

function highlightQuery(text, query) {
    const regex = new RegExp(`(${query})`, 'gi');
    return text.replace(regex, '<strong>$1</strong>');
}

// Initialize search when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSearch);
} else {
    initSearch();
}
