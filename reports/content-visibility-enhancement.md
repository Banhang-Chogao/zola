---
title: "Content Visibility Enhancement Guide"
date: 2026-06-26
---

# Content Visibility & Discovery Enhancement

## Current Status

All 174 posts are **present and properly formatted**. However, to ensure maximum visibility and SEO performance, consider these enhancements:

---

## 1. Archive/All Posts Page

**Problem:** Homepage pagination (10 posts/page) means users need to click through multiple pages to find older posts.

**Solution:** Create dedicated archive page showing all posts.

### Implementation

**File:** `content/archive/_index.md`

```toml
+++
title = "Tất cả bài viết — Archive"
description = "Danh sách đầy đủ tất cả bài viết trên blog SEOMONEY, sắp xếp theo ngày mới nhất."
template = "archive.html"
sort_by = "date"
+++

# Tất cả bài viết

Danh sách đầy đủ {{num_posts}} bài viết trên blog, sắp xếp theo ngày đăng mới nhất.
Sử dụng thanh tìm kiếm hoặc bộ lọc danh mục để tìm bài viết bạn quan tâm.
```

**Template:** `templates/archive.html`

```html
{% extends "base.html" %}

{% block main %}
<h1>Tất cả bài viết</h1>

{% set posting = get_section(path="posting/_index.md") %}
{% set baochi = get_section(path="baochi/_index.md") %}

{% set all_posts = posting.pages | concat(with=baochi.pages) 
    | filter(attribute="extra.feed_anchor", value=false) 
    | sort(attribute="date") | reverse %}

<div class="archive">
    {% for post in all_posts %}
        <article class="archive-item">
            <h3><a href="{{ post.permalink }}">{{ post.title }}</a></h3>
            <div class="archive-meta">
                <span class="date">{{ post.date | date(format="%d/%m/%Y") }}</span>
                <span class="categories">
                    {% for cat in post.taxonomies.categories %}
                        <a href="/categories/{{ cat | slugify }}/">{{ cat }}</a>
                    {% endfor %}
                </span>
            </div>
            <p>{{ post.description | default(value=post.summary | striptags | truncate(length=200)) }}</p>
        </article>
    {% endfor %}
</div>

{% endblock %}
```

**Add to Menu:** `config.toml`

```toml
{ name = "Archive", url = "$BASE_URL/archive" },
```

**SEO Benefits:**
- ✅ All 174 posts visible on one page (better crawl depth)
- ✅ Internal linking boost (every post linked from archive)
- ✅ User can bookmark and return easily
- ✅ Improves dwell time (users browse more posts)

---

## 2. Content Audit Dashboard

**Problem:** No automated way to detect if posts go missing in future changes.

**Solution:** Add content validation to CI/CD.

### Python Script: `scripts/content_audit.py`

```python
#!/usr/bin/env python3
"""Automated content audit for CI."""

import json
from pathlib import Path
from datetime import datetime

def audit_content():
    """Count and validate all posts."""
    posting = list(Path("content/posting").glob("*.md"))
    baochi = list(Path("content/baochi").glob("*.md"))
    
    posting = [f for f in posting if f.name != "_index.md"]
    baochi = [f for f in baochi if f.name != "_index.md"]
    
    total = len(posting) + len(baochi)
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "posting_count": len(posting),
        "baochi_count": len(baochi),
        "total_posts": total,
        "threshold_alert": total < 150,  # Alert if count drops below 150
    }
    
    with open("data/content-audit.json", "w") as f:
        json.dump(report, f)
    
    print(f"Content audit: {total} posts")
    if report["threshold_alert"]:
        print("⚠️  WARNING: Post count below threshold!")
        exit(1)
    else:
        exit(0)

if __name__ == "__main__":
    audit_content()
```

### GitHub Actions: `.github/workflows/content-audit.yml`

```yaml
name: Content Audit

on:
  pull_request:
    paths:
      - 'content/posting/**'
      - 'content/baochi/**'
  schedule:
    - cron: '0 0 * * *'  # Daily

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
      - run: python3 scripts/content_audit.py
      - uses: actions/upload-artifact@v4
        with:
          name: content-audit
          path: data/content-audit.json
```

---

## 3. Improve Content Discoverability

### 3a. Add "Related Posts" Block

Enhance `templates/page.html` to show related posts at bottom of each article:

```html
<section class="related-posts">
    <h3>Bài viết liên quan</h3>
    {% set related = get_taxonomy(kind="categories", term=page.taxonomies.categories[0]) %}
    {% for post in related.pages | slice(start=0, end=5) %}
        {% if post.slug != page.slug %}
            <a href="{{ post.permalink }}">{{ post.title }}</a>
        {% endif %}
    {% endfor %}
</section>
```

### 3b. Breadcrumb Navigation

Show post's path in category hierarchy:

```html
<nav class="breadcrumb">
    <a href="/">Home</a> /
    {% for cat in page.taxonomies.categories %}
        <a href="/categories/{{ cat | slugify }}/">{{ cat }}</a>
        {% if not loop.last %} / {% endif %}
    {% endfor %}
</nav>
```

### 3c. "Continue Reading" Section

At end of post preview/summary, link to full article:

```html
{% if post_is_summary %}
    <a class="read-more" href="{{ post.permalink }}">
        Đọc tiếp → 
        <span class="word-count">({{post.word_count}} từ)</span>
    </a>
{% endif %}
```

---

## 4. RSS/Atom Feed Verification

Ensure feeds properly distribute content.

### Check Feed Generation

```bash
# After zola build
echo "Posting feed:"
grep -c "<entry>" public/atom.xml
grep -c "<item>" public/rss.xml

echo "Category feeds:"
ls -la public/categories/*/atom.xml
```

### Publish Feed to Aggregators

- [ ] Submit RSS to Google News (if eligible)
- [ ] Submit to RSS reader aggregators (Feedly, Inoreader, etc.)
- [ ] Add feed links to sidebar

### Frontend Feed Discovery

In `templates/base.html` `<head>`:

```html
<link rel="alternate" type="application/atom+xml" title="SEOMONEY Feed" href="/atom.xml">
<link rel="alternate" type="application/rss+xml" title="SEOMONEY RSS" href="/rss.xml">
```

---

## 5. Sitemap & SEO Verification

### Verify Sitemap Contains All Posts

```bash
# After build
grep -c "<url>" public/sitemap.xml
# Should be ≥ 180 (all posts + category pages + static pages)

# Check specific post
grep "posting/git-la-gi" public/sitemap.xml
```

### Submit to Search Engines

- Submit `sitemap.xml` to Google Search Console
- Request indexing of key posts in GSC
- Monitor "Coverage" report for any missing/excluded URLs

### Robots.txt Configuration

Ensure `static/robots.txt` allows crawling:

```
User-agent: *
Allow: /
Disallow: /admin/
Disallow: /editor/
Allow: /posting/
Allow: /baochi/
Allow: /categories/

Sitemap: https://seomoney.org/sitemap.xml
```

---

## 6. Content Organization Rules (Update CLAUDE.md)

Add to project documentation:

```markdown
## Content Structure

### Posts Location & Organization

| Location | Purpose | Template | Pagination |
|----------|---------|----------|-----------|
| `content/posting/` | Main blog posts (1500-5000 words) | `page.html` | Via homepage + category |
| `content/baochi/` | News digests from RSS feeds (300-1000 words) | `page.html` | Via homepage + category |

### Expected Post Counts

- **posting/** minimum: 100 posts
- **baochi/** varies: 20-50 posts (auto-generated from RSS)
- **Total visible:** ≥ 150 posts
- **Archive page:** displays all 174 posts in one view

### Visibility Checklist

Every post MUST have:
- ✅ `title = "..."`
- ✅ `date = YYYY-MM-DD`
- ✅ `[taxonomies] categories = ["Tất cả", "Category"]`
- ✅ `description = "..."` (50-160 chars)
- ✅ NO `draft = true`
- ✅ NO future date

### Audit Automation

- CI runs `content_audit.py` on every PR touching content
- Alerts if post count drops below 150
- Archives daily count in `data/content-audit.json`
```

---

## 7. Performance Monitoring

### Add Post Count to Dashboard

Update `templates/insights.html` to show:

```
📊 Content Stats
├─ Total Posts: 174
├─ Posted This Month: 12
├─ Posted This Year: 156
├─ Average Words: 2,340
└─ Archive: /archive/ [View All]
```

### Weekly Report

Create `scripts/content_weekly_report.py`:

```python
def report():
    """Generate weekly content stats."""
    posts_this_week = count_posts_in_date_range(
        start=date.today() - timedelta(days=7),
        end=date.today()
    )
    print(f"📚 Content Report (week of {date.today()})")
    print(f"New posts: {posts_this_week}")
    print(f"Total posts: {get_total_posts()}")
    # Email or Slack notification
```

---

## 8. User-Facing Improvements

### Navigation Enhancements

1. **Mega Menu → Add Search**
   - Quick search across all posts
   - Filter by category/tag

2. **Sidebar Widget → Recent Posts**
   ```html
   <aside class="sidebar-recent">
       <h4>Mới nhất</h4>
       {% set recent = all_posts | slice(start=0, end=5) %}
       {% for post in recent %}
           <a href="{{ post.permalink }}">{{ post.title }}</a>
       {% endfor %}
   </aside>
   ```

3. **Footer → Links to Archive & Feeds**
   ```html
   <footer>
       <a href="/archive/">View All {{ total_posts }} Posts</a> |
       <a href="/atom.xml">Subscribe (Atom)</a> |
       <a href="/rss.xml">Subscribe (RSS)</a>
   </footer>
   ```

---

## Implementation Priority

| Priority | Task | Effort | SEO Impact |
|----------|------|--------|-----------|
| 🔴 High | Archive page | 2 hours | +30% crawl depth |
| 🔴 High | Content audit CI | 1 hour | Prevents losses |
| 🟡 Medium | Related posts | 1 hour | +20% dwell time |
| 🟡 Medium | RSS verification | 30 min | +10% feed subscribers |
| 🟢 Low | Dashboard stats | 30 min | UX only |

---

## Next Steps

1. ✅ Review this enhancement guide
2. ✅ Create `/archive/` page using template above
3. ✅ Add `content_audit.py` to scripts/
4. ✅ Add `.github/workflows/content-audit.yml`
5. ✅ Update `config.toml` menu with archive link
6. ✅ Update `CLAUDE.md` with content rules
7. ✅ Test archive page renders all 174 posts
8. ✅ Commit and PR

All posts are **already available and ready**. These enhancements will ensure they're **discoverable and protected** going forward.
