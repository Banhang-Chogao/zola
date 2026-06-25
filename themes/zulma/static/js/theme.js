// Theme Toggle Functionality

const THEME_KEY = 'zulma-theme';
const DARK_THEME = 'darkly';
const LIGHT_THEME = 'light';

function initTheme() {
    const html = document.documentElement;
    const themeToggleBtn = document.getElementById('theme-toggle');

    // Get saved theme or system preference
    let savedTheme = localStorage.getItem(THEME_KEY);
    if (!savedTheme) {
        // Check system preference
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            savedTheme = DARK_THEME;
        } else {
            savedTheme = LIGHT_THEME;
        }
    }

    // Set initial theme
    setTheme(savedTheme);

    // Theme toggle button listener
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            const currentTheme = html.getAttribute('data-theme') || DARK_THEME;
            const newTheme = currentTheme === DARK_THEME ? LIGHT_THEME : DARK_THEME;
            setTheme(newTheme);
        });
    }

    // Listen for system theme changes
    if (window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: dark)').addListener((e) => {
            if (!localStorage.getItem(THEME_KEY)) {
                setTheme(e.matches ? DARK_THEME : LIGHT_THEME);
            }
        });
    }
}

function setTheme(theme) {
    const html = document.documentElement;
    const themeToggleBtn = document.getElementById('theme-toggle');

    html.setAttribute('data-theme', theme);
    localStorage.setItem(THEME_KEY, theme);

    // Update icon visibility
    if (themeToggleBtn) {
        const sunIcon = themeToggleBtn.querySelector('.sun-icon');
        const moonIcon = themeToggleBtn.querySelector('.moon-icon');

        if (theme === DARK_THEME) {
            sunIcon.style.display = 'block';
            moonIcon.style.display = 'none';
        } else {
            sunIcon.style.display = 'none';
            moonIcon.style.display = 'block';
        }
    }
}

// Initialize theme when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTheme);
} else {
    initTheme();
}
