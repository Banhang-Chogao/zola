# FAQ, Related Posts & Copyright Implementation

## Overview

This implementation adds three new sections to each blog post:
1. **FAQ Section** (Câu hỏi thường gặp) - FAQ items with accordion UI
2. **Related Posts Section** (Bài viết liên quan) - Display related blog posts from the same section
3. **Copyright Notice** (Tuyên bố bản quyền) - Copyright and usage rights statement

These sections are rendered at the end of each blog post article, before the comments section.

## File Structure

### New Files Added

```
templates/
├── macros/
│   ├── faq.html              # FAQ display macro
│   ├── related-posts.html    # Related posts display macro
│   └── copyright.html        # Copyright notice macro

sass/
├── _faq.scss                 # FAQ styling (existing, reused)
├── _related-posts.scss       # Related posts grid styling
└── _copyright-notice.scss    # Copyright notice styling
```

### Modified Files

- `templates/page.html` - Added macro imports and display calls
- `sass/site.scss` - Added imports for new SCSS files

## Usage Guide

### 1. FAQ Section

#### Frontmatter Configuration

Add FAQ items to your post's frontmatter using the `[extra]` section with `[[extra.faq]]` arrays:

```toml
[extra]
# ... other extra fields ...

[[extra.faq]]
q = "Câu hỏi 1?"
a = "Câu trả lời 1 - có thể chứa HTML hoặc text thuần"

[[extra.faq]]
q = "Câu hỏi 2?"
a = "Câu trả lời 2"

[[extra.faq]]
q = "Câu hỏi 3?"
a = "Câu trả lời 3"
```

#### How It Works

- The FAQ macro (`templates/macros/faq.html`) checks for `page.extra.faq`
- If FAQ items exist and there are ≥3 items, the section is displayed
- Maximum 6 FAQ items are shown (via `slice(6)` filter)
- Each FAQ item uses HTML `<details>/<summary>` elements (native accordion, no JS)
- Styling uses existing `.faq` CSS classes from `sass/_faq.scss`

#### Schema.org JSON-LD

The FAQ schema is automatically generated in `templates/base.html` (lines 431-451):
- Uses `page.extra.faq` with `q` (question) and `a` (answer) keys
- Generates `FAQPage` schema.org structured data
- Helps Google display FAQ rich results in search

#### Styling

Classes used: `.faq`, `.faq__title`, `.faq__item`, `.faq__q`, `.faq__a`

These are already defined in `sass/_faq.scss` with:
- Responsive design (mobile-first)
- Reduced motion support
- Accessibility (focus-visible)
- Color tokens from B-DNA design system

---

### 2. Related Posts Section

#### How It Works

The related posts macro (`templates/macros/related-posts.html`):
- Gets posts from the same section as current post
- Sorts them by date (newest first)
- Excludes the current post
- Displays up to 6 related posts

#### Display Format

Each related post shows:
- Thumbnail image (if available from `post.extra.thumbnail`)
- Title (linked to post)
- Description/excerpt (truncated to 100 chars)
- Publication date

#### Styling

Grid-based layout with responsive columns:
- Desktop: up to 3-4 columns
- Tablet: 2 columns
- Mobile: 1 column

Classes: `.related-posts-section`, `.related-posts-grid`, `.related-post-card`

Defined in `sass/_related-posts.scss` with:
- Card hover effects (shadow + elevation)
- Image hover zoom effect
- Responsive grid with `auto-fit`
- Mobile-first design
- Reduced motion support

#### Image Fallback

If a post doesn't have a thumbnail:
- The image container is not displayed
- Card content is still shown
- No placeholder image is forced

---

### 3. Copyright Notice

#### How It Works

The copyright macro (`templates/macros/copyright.html`):
- Reads author name from `config.extra.author`
- Gets site title from `config.title`
- Gets current year via `now() | date(format="%Y")`
- Displays a styled copyright notice box

#### Frontmatter Override

You can override the author on a per-post basis:

```toml
[extra]
author = "Custom Author Name"
```

If not specified, uses the site-wide author from config.

#### Email Configuration

The notice includes a contact email (displayed as a link):
- Uses `config.extra.email` if defined
- Falls back to `tamsudev.com@gmail.com` 
- To customize, add to `config.toml`:
  ```toml
  [extra]
  email = "your-email@example.com"
  ```

#### Styling

Classes: `.copyright-notice`, `.copyright-notice__content`, `.copyright-notice__title`, etc.

Defined in `sass/_copyright-notice.scss` with:
- Left border accent (cyan) matching B-DNA
- Light background
- Responsive padding
- Mobile-friendly layout
- Reduced motion support

---

## Rendering Order

In the blog post, sections appear in this order:

1. **Post Content**
2. **Post Taxonomies** (categories/tags)
3. **FAQ Section** (if `page.extra.faq` exists with ≥3 items)
4. **Related Posts Section** (if posts exist in same section)
5. **Copyright Notice** (always displayed)
6. **Post Navigation** (previous/next posts, if available)
7. **Comments Section** (if enabled)

---

## Example Post with All Sections

Here's a complete example:

```toml
+++
title = "Example Blog Post"
description = "A sample post showing FAQ, related posts, and copyright notice"
date = 2026-06-25

[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["blog", "seo", "implementation"]

[extra]
thumbnail = "https://example.com/image.jpg"
author = "Duy Nguyen"

[[extra.faq]]
q = "What is this post about?"
a = "This post demonstrates the new FAQ, related posts, and copyright features."

[[extra.faq]]
q = "How do I add FAQ to my posts?"
a = "Add FAQ items to the frontmatter using [[extra.faq]] arrays with 'q' (question) and 'a' (answer) fields."

[[extra.faq]]
q = "Can I customize the copyright notice?"
a = "Yes, you can override the author field per-post or set the email in config.toml."
+++

# Post content here...
```

---

## CSS Custom Properties (Color Tokens)

Both new CSS files use the B-DNA design system color tokens:

- `--c-spacing-*` - Spacing scale
- `--c-text-heading` - Heading text color
- `--c-text-body` - Body text color
- `--c-text-muted` - Muted/secondary text
- `--c-bg-surface` - Card background
- `--c-bg-soft` - Soft background
- `--c-bg-page` - Page background
- `--c-border` - Border color
- `--c-accent` - Primary accent color (cyan)
- `--c-shadow-*` - Shadow utilities
- `--c-focus-ring` - Focus indicator color

These are defined in `sass/_themes.scss` and dynamically updated based on the active theme.

---

## Responsive Design

All sections are mobile-first responsive:

### Breakpoints Used

- **Mobile**: ≤640px
  - Single column layouts
  - Reduced padding/margins
  - Smaller fonts
  - Simplified spacing

- **Tablet**: 640px - 768px
  - 2-column grids
  - Medium padding
  - Balanced spacing

- **Desktop**: ≥768px
  - 3-4 column grids
  - Full padding/margins
  - Hover effects enabled

---

## Accessibility Features

All components include:

- **Focus Indicators**: Visible outlines for keyboard navigation
- **Reduced Motion**: Media queries respect `prefers-reduced-motion`
- **ARIA Labels**: Proper semantic HTML with `aria-labelledby`
- **Semantic HTML**: Using `<details>/<summary>` for FAQ, `<section>`, `<article>`, `<time>`, etc.
- **Color Contrast**: All text meets WCAG AA standards
- **Image Alt Text**: Required for all images
- **Link Focus**: Clear focus rings on all interactive elements

---

## Performance Considerations

- **No JavaScript Required**: FAQ accordion uses native `<details>` element
- **Lazy Loading**: Related post images use `loading="lazy"` and `decoding="async"`
- **CSS Optimization**: Scoped classes avoid global namespace pollution
- **Reduced Bundle**: Reuses existing `_faq.scss` instead of creating new styles

---

## Troubleshooting

### FAQ Section Not Showing

**Problem**: FAQ items defined in frontmatter but section not rendering

**Solutions**:
1. Ensure at least 3 FAQ items are defined
2. Check TOML syntax - use `[[extra.faq]]` arrays (double brackets)
3. Verify `q` and `a` fields are present in each item
4. Build and check console for Zola template errors

### Related Posts Section Not Showing

**Problem**: No related posts appearing

**Solutions**:
1. Ensure post is in a section with other posts
2. Check that `section.pages` is available in template context
3. Verify at least one other post exists in the same section
4. Exclude drafts/hidden posts from visibility

### Copyright Notice Not Showing

**Problem**: Copyright notice is missing

**Solutions**:
1. Ensure `config.extra.author` is set in `config.toml`
2. Check that page context is available
3. The macro should always render - if not, check Zola build errors

---

## Future Enhancements

Possible improvements for future versions:

1. **Automatic FAQ Extraction** - Parse headings + paragraphs to auto-generate FAQ (requires server-side logic)
2. **Tag-Based Related Posts** - Filter related posts by shared tags (requires taxonomy API)
3. **Category-Based Related Posts** - Smart category matching
4. **FAQ Collapsible Animation** - Add smooth expand/collapse animation
5. **Related Posts Filtering** - UI to filter by category/date
6. **Custom Templates** - Allow per-post layout overrides

---

## Testing Checklist

- [x] FAQ section displays when ≥3 items defined
- [x] FAQ section hidden when <3 items or undefined
- [x] Related posts show recent posts from same section
- [x] Current post excluded from related posts
- [x] Copyright notice displays with correct year and author
- [x] All sections responsive on mobile/tablet/desktop
- [x] Links have proper focus indicators
- [x] Images lazy load correctly
- [x] Markdown in copyright notice renders properly
- [x] JSON-LD schema valid for FAQ

---

## Author

Implementation: Claude (AI Assistant)
Date: 2026-06-25
Branch: claude/faq-ui-related-articles-15oxtr
