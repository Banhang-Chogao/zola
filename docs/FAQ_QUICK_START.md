# Quick Start: FAQ, Related Posts & Copyright

## TL;DR

### Add FAQ to a Post

Add this to your post's frontmatter:

```toml
[[extra.faq]]
q = "Your question?"
a = "Your answer"

[[extra.faq]]
q = "Another question?"
a = "Another answer"

[[extra.faq]]
q = "Third question?"
a = "Third answer"
```

✅ FAQ section shows automatically when ≥3 items exist

---

### Customize Copyright

In `config.toml`:

```toml
[extra]
author = "Your Name"
email = "your-email@example.com"
```

Or override per-post:

```toml
[extra]
author = "Guest Author"
```

---

### Related Posts

**Automatic** - Shows 6 newest posts from same section.

No configuration needed!

---

## What Gets Displayed

Every blog post now has these sections at the end:

```
📝 Post Content
└─ Post Categories/Tags
└─ 💡 FAQ Section (if ≥3 items)
└─ 📚 Related Posts (from same section)
└─ © Copyright Notice
└─ ← → Post Navigation (prev/next)
└─ 💬 Comments
```

---

## SEO Benefits

✅ **FAQ Schema** - Google shows FAQ in rich results + People Also Ask
✅ **Structured Data** - FAQPage schema.org JSON-LD auto-generated
✅ **Internal Links** - Related posts improve site structure
✅ **Copyright** - Clear usage rights = lower duplicate content risk

---

## Real Example

See `/content/posting/vietinbank-v-plus-v-advance-la-gi.md`:

```toml
[[extra.faq]]
q = "V-Plus và V-Advance VietinBank là gì?"
a = "V-Plus và V-Advance là hai gói tiện ích tài chính dạng membership..."

[[extra.faq]]
q = "V-Plus VietinBank giá bao nhiêu?"
a = "V-Plus có phí hội viên 20.000 VND/tháng..."

[[extra.faq]]
q = "Đăng ký V-Plus hoặc V-Advance ở đâu?"
a = "Khách hàng có thể đăng ký trực tiếp trên ứng dụng VietinBank iPay..."
```

---

## Mobile Preview

### FAQ
```
💡 Câu hỏi thường gặp

❓ Question 1? ▼
   Answer text shows here

❓ Question 2? ▼
   Answer text shows here
```

### Related Posts
```
📚 Bài viết liên quan

[Image] Title 1        [Image] Title 2
Excerpt... Date        Excerpt... Date

[Image] Title 3
Excerpt... Date
```

### Copyright
```
© Tuyên bố bản quyền

© 2026 Author | Site Name
Post shared for education...
📧 Contact: email@example.com
License: CC BY-SA 4.0
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| FAQ not showing | ✓ Need ≥3 items; ✓ Use `q` and `a` keys; ✓ Check TOML brackets `[[extra.faq]]` |
| Related posts empty | Post needs to be in a section with other posts |
| Copyright email not showing | Set `[extra] email = "..."` in config.toml |
| Styling looks off | Rebuild CSS (Zola build should do this) |

---

## Full Documentation

See `docs/FAQ_RELATED_POSTS_IMPLEMENTATION.md` for:
- Detailed usage guide
- CSS customization
- Accessibility features
- Performance tips
- Future enhancements

---

## Support

For questions or issues:
1. Check the full documentation first
2. Review existing posts with FAQ (e.g., vietinbank posts)
3. Look at the macro source code in `templates/macros/`
