+++
title = "Syntax highlighting trong Zola: từ cơ bản đến custom theme"
description = "Hướng dẫn đầy đủ syntax highlighting trong Zola qua Syntect: built-in themes, custom theme tmTheme, extra syntaxes, line numbers, performance vs client-side highlighter."
date = 2026-06-15

[taxonomies]
categories = ["Posting"]
tags = ["zola", "syntax highlighting", "syntect", "tutorial", "rust", "ssg", "code block", "tutorial nâng cao"]

[extra]
thumbnail = "https://picsum.photos/seed/syntax-highlighting-zola/600/400"
featured = false
+++

![Syntax highlighting Zola]

Code block đẹp là đặc tính quan trọng của blog kỹ thuật. Zola không
yêu cầu thêm bất kỳ JS runtime nào — syntax highlighting được build
ngay tại compile time qua **Syntect**, một thư viện Rust port từ
TextMate grammar. Bài này deep dive tất cả mọi thứ về syntax
highlighting trong Zola: từ bật cơ bản, chọn theme, custom theme
tmTheme, thêm syntax mới, hiển thị line number, đến so sánh với
client-side highlighter (Prism, Highlight.js, Shiki).

<!-- more -->

## 1. Syntect — cốt lõi xử lý syntax

Zola dùng [**Syntect**](https://github.com/trishume/syntect) làm
engine highlight. Syntect parse code dựa trên **TextMate grammar
files (.sublime-syntax)** — chuẩn được Sublime Text, TextMate,
VSCode dùng từ lâu.

Ưu điểm so với client-side highlighter:

- **Build-time**: HTML đã có sẵn span colored, browser KHÔNG cần
  chạy JS để colorize
- **No FOUC**: không có hiện tượng "code không màu loé chốc" trước
  khi JS xử lý
- **No JS bundle**: tiết kiệm 30-100KB JS so với Prism/Highlight.js
- **SEO friendly**: crawler đọc được color → hiểu cấu trúc code
- **Cache-friendly**: HTML tĩnh cache hoàn hảo trên CDN

Nhược điểm:

- **Build time tăng** (~5-10% nếu nhiều code block)
- **CSS payload to hơn**: theme inline trong từng `<span>` (~ 1-3KB
  thêm per page)
- **Không update động**: copy/paste code mới phải rebuild
- **Khó animate** highlight diff (cần JS bổ sung)

## 2. Bật syntax highlighting cơ bản

Thêm vào `config.toml`:

```toml
[markdown]
highlight_code = true
highlight_theme = "base16-ocean-dark"
```

Sau đó dùng markdown code fence bình thường:

````markdown
```python
def hello(name):
    return f"Hello, {name}!"

print(hello("World"))
```
````

Output sẽ là `<pre><code>` với span màu cho keyword, string, function
name, comment, v.v.

## 3. Built-in themes — chọn theme phù hợp

Zola ship với **20+ themes** từ Syntect. Phân loại:

### Light themes
- `inspired-github` — sạch như GitHub light
- `solarized-light` — palette Solarized phổ biến
- `Visual Studio Dark+` — light version
- `base16-ocean-light`

### Dark themes
- `base16-ocean-dark` ⭐ default suggestion
- `Solarized (dark)`
- `Monokai`
- `Dracula`
- `OneHalfDark`
- `gruvbox-dark`
- `Nord`

### Đặc biệt
- `ayu-dark` / `ayu-light` — palette pastel mềm mại
- `kronuz` — bold contrast cho theatre presentation

**Mẹo**: chuyển theme test nhanh bằng `zola serve` — file watch sẽ
re-build instant.

## 4. Custom theme — viết tmTheme riêng

Nếu 20+ themes built-in không vừa ý, viết theme custom dạng tmTheme
(XML plist format).

### Bước 1: tạo file `.tmTheme`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "...">
<plist version="1.0">
<dict>
    <key>name</key>
    <string>My Dark Theme</string>
    <key>settings</key>
    <array>
        <dict>
            <key>settings</key>
            <dict>
                <key>background</key>
                <string>#1a1a1a</string>
                <key>foreground</key>
                <string>#d4d4d4</string>
            </dict>
        </dict>
        <!-- Keyword scope -->
        <dict>
            <key>scope</key>
            <string>keyword</string>
            <key>settings</key>
            <dict>
                <key>foreground</key>
                <string>#c586c0</string>
                <key>fontStyle</key>
                <string>bold</string>
            </dict>
        </dict>
        <!-- String scope -->
        <dict>
            <key>scope</key>
            <string>string</string>
            <key>settings</key>
            <dict>
                <key>foreground</key>
                <string>#ce9178</string>
            </dict>
        </dict>
    </array>
</dict>
</plist>
```

### Bước 2: place theme + config

Lưu file vào `theme/my-dark.tmTheme` rồi config:

```toml
[markdown]
highlight_code = true
highlight_theme = "my-dark"
extra_syntaxes_and_themes = ["theme"]
```

Zola sẽ scan thư mục `theme/` tìm `.tmTheme` và `.sublime-syntax`.

**Mẹo lười**: download tmTheme có sẵn từ
[colorsublime.github.io](https://colorsublime.github.io) hoặc convert
VSCode theme JSON sang tmTheme qua tool
[vscode-tmTheme](https://github.com/aziz/tmTheme-Editor).

## 5. Extra syntaxes — hỗ trợ ngôn ngữ mới

Syntect ship với ~100 ngôn ngữ phổ biến nhưng thiếu một số như:

- **Solidity** (smart contract)
- **Move** (Aptos/Sui)
- **Cairo** (Starknet)
- **Vue** (single-file component)
- **Svelte**

Để thêm:

1. Tìm `.sublime-syntax` file (Sublime Text Package Control hoặc
   GitHub `*-sublime-syntax`)
2. Place vào `syntaxes/<lang>.sublime-syntax`
3. Config:

```toml
[markdown]
highlight_code = true
extra_syntaxes_and_themes = ["syntaxes", "theme"]
```

Test code block với language tag mới:

````markdown
```solidity
pragma solidity ^0.8.0;
contract Hello {
    string public greeting = "Hello, World!";
}
```
````

## 6. Line numbers + line highlighting

Zola 0.17+ hỗ trợ inline annotation cho code block:

````markdown
```rust,linenos,hl_lines=2-3
fn main() {
    let x = 5;
    let y = 10;
    println!("{}", x + y);
}
```
````

- `linenos`: hiển thị số dòng bên trái
- `hl_lines=2-3`: highlight dòng 2-3 với background khác
- `linenostart=10`: bắt đầu số dòng từ 10

CSS để custom:

```css
pre {
  position: relative;
  padding: 1rem;
  border-radius: 6px;
  overflow-x: auto;
}

pre table {
  border-collapse: collapse;
}

pre td.linenos {
  color: #6b7280;
  padding-right: 1rem;
  border-right: 1px solid #374151;
  text-align: right;
  user-select: none; /* tránh copy số dòng */
}

pre .line-highlighted {
  background: rgba(255, 235, 59, 0.15);
  display: block;
  margin: 0 -1rem;
  padding: 0 1rem;
}
```

## 7. Inline code vs block code

**Inline code** (single backtick) KHÔNG được Zola highlight — chỉ
wrap trong `<code>`:

```markdown
Dùng hàm `printf` để in.
```

→ `<code>printf</code>` không có syntax color.

Nếu muốn inline cũng có màu, dùng plugin client-side như Prism với
`inline-color` plugin. Nhưng đa số blog kỹ thuật chỉ cần block highlight.

## 8. Copy-to-clipboard button

Zola không tự thêm copy button. Cần JS vanilla:

```js
// static/js/code-copy.js
document.querySelectorAll('pre').forEach(block => {
    const btn = document.createElement('button');
    btn.className = 'copy-btn';
    btn.textContent = 'Copy';
    btn.addEventListener('click', async () => {
        const code = block.querySelector('code').textContent;
        await navigator.clipboard.writeText(code);
        btn.textContent = 'Copied!';
        setTimeout(() => btn.textContent = 'Copy', 1500);
    });
    block.appendChild(btn);
});
```

```css
pre {
  position: relative;
}
.copy-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  padding: 4px 8px;
  background: #2d2d2d;
  color: #fff;
  border: none;
  border-radius: 4px;
  font-size: 11px;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.15s;
}
pre:hover .copy-btn {
  opacity: 1;
}
```

Load script ở base.html: `<script src="/js/code-copy.js" defer></script>`.

## 9. Performance: build-time vs runtime

| Approach | Build time +/- | Page size +/- | LCP impact |
|---|---|---|---|
| **Syntect (Zola default)** | +5-10% | +1-3KB/page | None |
| **Prism (client JS)** | 0 | +14KB JS + 8KB CSS | +50-100ms |
| **Highlight.js** | 0 | +30KB JS | +80-150ms |
| **Shiki (build-time)** | +15-20% | +0KB | None |

**Khuyên**: dùng Syntect built-in cho blog tĩnh. Shiki tốt hơn về
quality nhưng cần Node.js trong build pipeline (Zola không có).

## 10. Best practices

1. **Chọn 1 theme + giữ nguyên** xuyên suốt blog. Đừng đổi theme
   giữa các bài → người đọc rối.
2. **Background contrast đủ 4.5:1** với text color → WCAG AA.
3. **Code block luôn có language tag** dù chỉ là `text` → giúp screen
   reader + future syntax engine.
4. **Tránh code block dài >100 lines** trong bài. Tách section riêng
   hoặc link tới Gist.
5. **Test với DevTools "Disable JavaScript"** → đảm bảo code block
   vẫn render đẹp khi JS tắt.
6. **Mobile-first**: code block thường overflow ngang → đảm bảo
   `overflow-x: auto` và padding đủ cho ngón tay scroll.

## 11. Debug khi syntax không highlight

Checklist khi gặp lỗi:

- ✅ `highlight_code = true` trong `[markdown]` section
- ✅ Language tag chính xác (ví dụ `python` không phải `py`)
- ✅ Theme tồn tại trong list built-in hoặc đường dẫn `theme/` đúng
- ✅ `zola check` không báo warning
- ✅ Browser DevTools → Network: file CSS có color rules cho `.z-keyword`, `.z-string`, v.v.
- ✅ Cache cleared: `rm -rf public/` rồi `zola build` lại

## Kết: tránh client-side highlighter khi có thể

Syntect tích hợp sẵn trong Zola là giải pháp **tốt nhất 95% trường
hợp** cho blog tĩnh. Đẹp, nhanh, miễn JS, miễn FOUC. Chỉ khi cần tính
năng advanced (animation, live editor, theme switcher real-time) mới
xem xét client-side library.

Nếu bạn quan tâm hơn về cấu trúc tổng thể blog Zola này, đọc thêm
[hành trình công nghệ blog cá nhân](/posting/cong-nghe-blog-duy-nguyen/)
hoặc xem cách hệ thống [related posts dựa trên semantic similarity](/posting/sentence-transformers-sbert-deep-dive/)
được build qua workflow GitHub Actions.

Reference: [Syntect repo](https://github.com/trishume/syntect),
[Zola syntax highlighting docs](https://www.getzola.org/documentation/content/syntax-highlighting/),
[TextMate grammar specification](https://macromates.com/manual/en/language_grammars).
