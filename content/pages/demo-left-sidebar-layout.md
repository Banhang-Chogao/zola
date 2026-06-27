+++
title = "Demo: Left Sidebar Layout"
description = "Documentation for the new 30/70 responsive left-sidebar blog layout with fixed ad spots"
date = 2026-06-27
slug = "demo-left-sidebar-layout"

[taxonomies]
categories = ["Tất cả"]
tags = ["layout", "demo", "design"]
+++

# New Left Sidebar Layout Demo

This page demonstrates the new **30/70 responsive layout** with:

- **Left Sidebar (30%):** Sticky post widget, categories, date widget, ad spot
- **Main Content (70%):** Sticky post, featured post, normal posts, pagination
- **Ad Spots:** 3 fixed-height placeholders (728×90, 300×250, 728×90)
- **Responsive:** 2-column desktop → 1-column mobile

## Design Features

✅ **Anti-Layout-Shift Protection** — Fixed min-height and aspect-ratio on all ad placeholders  
✅ **Mobile-First Responsive** — Flexbox with order property for sidebar reflow at 768px  
✅ **Semantic HTML5** — Proper accessibility attributes and structure  
✅ **Zero Breaking Changes** — Can coexist with existing blog layout  

## Implementation

The template extends `base.html` and integrates with:
- Existing Zola macros (img, pagination, series-nav)
- Current blog taxonomies and categories
- Real post data from the posting section
- All existing styling and configuration

## Next Steps

This layout can be:
1. **Applied per-section** — Add `template = "posting-left-sidebar.html"` to specific sections
2. **Made site-wide** — Update `config.toml` default template
3. **Added as theme option** — Create a theme selector for users to choose layouts
4. **Further customized** — Adjust sidebar width, ad spots, widgets per needs

---

*Scroll down to see the layout in action with real blog posts and navigation.*
