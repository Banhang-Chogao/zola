# Zulma Theme

A minimalist Zola theme with dark mode support, search functionality, and responsive design.

## Features

- 🌗 Dark/Light theme toggle with system preference detection
- 🔍 Built-in search functionality
- 📱 Fully responsive design
- ♿ Accessibility-first approach
- 🎨 Clean and modern UI
- ⚡ Fast and lightweight

## Configuration

### Enable in config.toml

```toml
theme = "zulma"

[extra]
# Zulma theme settings
show_menu = true
enable_search = true
theme_mode = "darkly"
allow_theme_toggle = true
```

### Menu Navigation

Configure the menu in `[extra.menus]`:

```toml
[extra.menus]
menu = [
    { name = "Home", url = "$BASE_URL/" },
    { name = "Blog", url = "$BASE_URL/posting" },
    { name = "About", url = "$BASE_URL/about" },
]
```

### Search

The theme supports Zola's built-in search. Make sure to enable it:

```toml
build_search_index = true
```

Press `Ctrl+K` (or `Cmd+K` on Mac) to open the search modal.

### Theme Colors

The theme comes with a "darkly" color scheme by default. To switch to light mode, users can toggle the theme button in the navigation bar.

### Author Information

```toml
[extra.profiles.duynguyenlog]
avatar_url = "https://example.com/avatar.png"
avatar_alt = "Your Name"
name = "Your Name"
bio = "Your bio here"
```

## Directory Structure

```
zulma/
├── sass/
│   ├── zulma.scss      # Main theme styles
│   └── search.scss     # Search modal styles
├── static/
│   └── js/
│       ├── theme.js    # Theme toggle functionality
│       └── search.js   # Search functionality
├── templates/
│   ├── base.html       # Base template
│   ├── index.html      # Home page
│   ├── section.html    # Section/archive pages
│   └── page.html       # Single page/post
└── theme.toml          # Theme metadata
```

## Keyboard Shortcuts

- `Ctrl+K` / `Cmd+K` - Open search
- `Esc` - Close search/modal

## Customization

### Colors

To customize colors, modify the CSS variables in `sass/zulma.scss`:

```scss
:root {
    --color-bg: #1e1e2e;
    --color-accent: #50fa7b;
    /* ... other variables ... */
}
```

### Fonts

Change the default fonts by modifying:

```scss
--font-sans: /* your font family */;
--font-mono: /* your monospace font */;
```

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

## License

MIT
