+++
title = "Top 10 công cụ terminal cho Mac 2026: dev toolkit"
description = "Tổng hợp 10 công cụ terminal cho Mac 2026 mình dùng hằng ngày: Homebrew, iTerm2, Starship, fzf, ripgrep, bat, eza, zoxide, tmux, lazygit, kèm cách cài nhanh."
date = 2026-06-27
slug = "top-10-cong-cu-terminal-cho-mac-2026"
aliases = ["/top-10-cong-cu-terminal-cho-mac-2026/"]

[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["command line", "công cụ dev", "lập trình", "macos", "terminal"]
[extra]
seo_keyword = "công cụ terminal cho Mac"
thumbnail = "/img/placeholder/placeholder.svg"
toc = true
featured = false

[[extra.faq]]
q = "Mới dùng Mac thì nên cài công cụ terminal nào trước?"
a = "Cài Homebrew trước tiên, vì gần như mọi công cụ khác đều cài qua nó chỉ bằng một dòng brew install. Sau đó mình gợi ý iTerm2 (hoặc Warp) làm terminal, rồi Starship cho prompt đẹp và fzf để tìm kiếm nhanh. Bốn thứ này đã đủ thay đổi trải nghiệm dòng lệnh của bạn."

[[extra.faq]]
q = "Warp và iTerm2 nên chọn cái nào?"
a = "Tùy gu. iTerm2 là lựa chọn kinh điển, nhẹ, ổn định, cấu hình sâu và miễn phí hoàn toàn. Warp hiện đại hơn với block command, autocomplete kiểu AI và editor đa dòng, nhưng nặng hơn và một số tính năng cần đăng nhập. Mình để cả hai trên máy: iTerm2 cho việc thường ngày, Warp khi muốn gõ lệnh dài."

[[extra.faq]]
q = "Cài nhiều công cụ thay thế lệnh gốc (ls, cat, cd) có làm Mac chậm không?"
a = "Không đáng kể. eza, bat, zoxide đều là binary nhỏ viết bằng Rust hoặc Go, khởi động gần như tức thì. Cái bạn cần lưu ý là alias trong file cấu hình zsh: nếu alias quá nhiều thứ chạy lúc khởi động shell thì terminal có thể mở chậm vài trăm mili-giây, nhưng bản thân các công cụ này không phải nguyên nhân."

[[extra.faq]]
q = "Làm sao đồng bộ bộ công cụ terminal sang máy Mac mới?"
a = "Mình lưu danh sách package vào một Brewfile (brew bundle dump), rồi commit cùng dotfiles lên Git. Trên máy mới chỉ cần cài Homebrew, clone dotfiles và chạy brew bundle là khôi phục lại toàn bộ. Cách này tiết kiệm hàng giờ so với cài tay từng cái."
+++

Nếu bạn dùng Mac để code, cái terminal mặc định của macOS thật ra mới chỉ là điểm khởi đầu. Sau nhiều năm vọc vạch, mình nhận ra phần lớn thời gian tăng tốc không đến từ một editor xịn, mà đến từ một bộ **công cụ terminal cho Mac** được chọn lọc kỹ. Bài này mình tổng hợp 10 công cụ đang nằm trong dev toolkit 2026 của mình — thứ mình thật sự mở ra mỗi ngày, kèm cách cài nhanh để bạn áp dụng ngay.

<!-- more -->

## Vì sao công cụ terminal cho Mac lại đáng đầu tư

Terminal mặc định (Terminal.app) chạy được, nhưng nó dừng ở mức "đủ xài". Khi khối lượng việc tăng lên — nhảy giữa hàng chục thư mục, tìm một chuỗi trong nghìn file, xem diff Git, quản lý nhiều session — thì sự khác biệt giữa công cụ thô và công cụ tốt được tính bằng giờ mỗi tuần.

Điểm hay của hệ sinh thái **công cụ terminal cho Mac** là gần như tất cả đều cài qua một trình quản lý gói duy nhất, cấu hình bằng vài dòng text, và đồng bộ dễ dàng sang máy mới. Bạn bỏ ra một buổi chiều cài đặt, rồi hưởng lợi trong nhiều năm.

Mình chia 10 công cụ dưới đây thành ba nhóm: **nền tảng** (Homebrew, iTerm2), **trải nghiệm shell** (Oh My Zsh, Starship, zoxide) và **năng suất** (fzf, ripgrep, bat, eza, tmux, lazygit). Bạn không cần cài hết một lúc — cứ thêm dần theo nhu cầu.

## Cài đặt nền tảng: Homebrew đứng đầu danh sách

Trước khi nói tới công cụ nào khác, hãy cài [Homebrew](https://brew.sh) — trình quản lý gói cho macOS. Đây là thứ giúp mọi công cụ phía sau chỉ còn là một dòng `brew install`.

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Cài xong, bạn có thể gom cả bộ toolkit này bằng một lệnh duy nhất:

```bash
brew install starship fzf ripgrep bat eza zoxide tmux lazygit
brew install --cask iterm2
```

Mẹo của mình: chạy `brew bundle dump` để xuất một `Brewfile`, commit nó cùng dotfiles. Khi đổi máy, chỉ cần `brew bundle` là khôi phục nguyên trạng.

## Top 10 công cụ terminal cho Mac 2026

### 1. Homebrew — gốc rễ của mọi thứ

Như đã nói, Homebrew là package manager mình cài đầu tiên trên bất kỳ Mac nào. Nó không chỉ cài CLI tool mà còn quản lý cả ứng dụng GUI qua `--cask`. Lệnh `brew upgrade` cập nhật toàn bộ cùng lúc, còn `brew leaves` cho biết bạn đã cài chủ động những gì. Một công cụ nền, nhưng thiếu nó thì cả danh sách này sụp đổ.

### 2. iTerm2 — terminal thay cho Terminal.app

[iTerm2](https://iterm2.com) là terminal emulator mình gắn bó lâu nhất. Split pane linh hoạt, search trong buffer, hotkey window kéo xuống từ trên cùng, profile theo từng dự án — những tính năng này biến cửa sổ dòng lệnh thành không gian làm việc thực thụ. Nó miễn phí và cấu hình rất sâu.

Nếu thích thứ hiện đại hơn, [Warp](https://www.warp.dev) là ứng viên đáng thử với giao diện block và autocomplete thông minh. Mình để cả hai trên máy và chọn theo tâm trạng.

### 3. Oh My Zsh — khung cho shell zsh

macOS dùng zsh làm shell mặc định, và [Oh My Zsh](https://ohmyz.sh) là framework giúp bạn quản lý plugin, theme, alias gọn gàng. Mình bật vài plugin yêu thích như `git`, `zsh-autosuggestions` (gợi ý lệnh từ lịch sử) và `zsh-syntax-highlighting` (tô màu lệnh đúng/sai khi gõ). Chỉ riêng hai plugin gợi ý và highlight đã giảm hẳn số lần gõ sai.

### 4. Starship — prompt nhanh, đẹp, đa ngôn ngữ

[Starship](https://starship.rs) là prompt viết bằng Rust, hiện đúng thông tin bạn cần ngay tại dòng lệnh: nhánh Git, trạng thái thay đổi, phiên bản Node/Python/Rust của thư mục hiện tại, thời gian chạy lệnh vừa rồi. Nó nhanh tới mức bạn không cảm nhận được độ trễ. Bật bằng một dòng trong `~/.zshrc`:

```bash
eval "$(starship init zsh)"
```

Tùy biến qua `~/.config/starship.toml` — mình để prompt tối giản, chỉ hiện thư mục và Git.

### 5. fzf — fuzzy finder gõ đâu cũng thấy

[fzf](https://github.com/junegunn/fzf) là công cụ mình dùng nhiều nhất trong ngày. Nó cho phép tìm mờ (fuzzy) bất cứ danh sách nào: lịch sử lệnh (`Ctrl-R`), file trong thư mục (`Ctrl-T`), nhánh Git, process để kill... Một khi quen `Ctrl-R` của fzf, bạn sẽ không bao giờ muốn quay lại tìm lịch sử lệnh kiểu cũ.

### 6. ripgrep — tìm trong code siêu nhanh

[ripgrep](https://github.com/BurntSushi/ripgrep) (lệnh `rg`) tìm chuỗi trong cả cây thư mục nhanh hơn `grep` nhiều lần, lại tự động bỏ qua những gì có trong `.gitignore`. Khi cần tìm xem một hàm được gọi ở đâu trong dự án vài nghìn file, `rg tên_hàm` trả kết quả gần như tức thì. Đây là công cụ mình thay cho `grep` hoàn toàn.

### 7. bat — `cat` có tô màu và số dòng

[bat](https://github.com/sharkdp/bat) là phiên bản nâng cấp của `cat`: tô màu cú pháp, hiện số dòng, tích hợp với Git để đánh dấu dòng thay đổi. Đọc một file cấu hình hay đoạn code ngay trên terminal trở nên dễ chịu hơn nhiều. Mình thường alias `cat` thành `bat` cho tiện tay.

### 8. eza — `ls` của thời hiện đại

[eza](https://github.com/eza-community/eza) thay thế `ls` với màu sắc rõ ràng, icon, cây thư mục (`eza --tree`) và cột trạng thái Git. Nhìn cấu trúc thư mục bằng eza dễ quét mắt hơn hẳn `ls` trắng đen. Alias quen thuộc của mình:

```bash
alias ls="eza --icons --group-directories-first"
alias ll="eza -lah --icons --git"
```

### 9. zoxide — `cd` biết bạn muốn đi đâu

[zoxide](https://github.com/ajeetdsouza/zoxide) học thói quen di chuyển thư mục của bạn. Thay vì gõ đường dẫn dài, bạn chỉ cần `z ten-thu-muc` và nó nhảy tới thư mục bạn hay ghé nhất khớp tên đó. Sau vài ngày dùng, mình gần như không còn gõ `cd` với đường dẫn đầy đủ nữa.

### 10. tmux — chia session, giữ phiên không mất

[tmux](https://github.com/tmux/tmux) là terminal multiplexer: chia một cửa sổ thành nhiều pane, nhiều window, và quan trọng nhất là **giữ session sống** kể cả khi bạn đóng terminal hay mất kết nối SSH. Khi làm việc với server từ xa hoặc chạy tiến trình dài, tmux là cứu cánh. Học vài phím tắt cơ bản (`prefix + |` để split, `prefix + d` để detach) là đủ dùng.

> **Bonus — lazygit:** [lazygit](https://github.com/jesseduffield/lazygit) là giao diện TUI cho Git ngay trong terminal. Stage từng dòng, xem diff, rebase tương tác, quản lý nhánh — tất cả bằng phím tắt trực quan. Nếu bạn còn ngại các lệnh Git phức tạp, lazygit là cầu nối tuyệt vời. Mình xem nó như công cụ thứ 11 không thể thiếu.

## Bảng so sánh nhanh 10 công cụ

| Công cụ | Thay cho | Cài bằng | Ngôn ngữ |
|---|---|---|---|
| Homebrew | — (nền tảng) | script chính chủ | Ruby |
| iTerm2 | Terminal.app | `brew install --cask iterm2` | Objective-C |
| Oh My Zsh | cấu hình zsh thô | script chính chủ | Shell |
| Starship | prompt mặc định | `brew install starship` | Rust |
| fzf | tìm lịch sử/file | `brew install fzf` | Go |
| ripgrep | `grep` | `brew install ripgrep` | Rust |
| bat | `cat` | `brew install bat` | Rust |
| eza | `ls` | `brew install eza` | Rust |
| zoxide | `cd` | `brew install zoxide` | Rust |
| tmux | nhiều cửa sổ rời | `brew install tmux` | C |

Điểm chung thú vị: phần lớn công cụ mới đều viết bằng **Rust** hoặc **Go** — nhanh, gọn, an toàn bộ nhớ. Đó cũng là lý do chúng nhẹ và khởi động tức thì dù thay thế các lệnh hệ thống.

## Ghép thành một bộ toolkit mạch lạc

Cài rời từng cái thì tốt, nhưng sức mạnh thật sự đến khi chúng phối hợp. Đây là phần `~/.zshrc` rút gọn mình hay dùng — bốn dòng đầu khởi tạo prompt Starship, zoxide và fzf, phần còn lại alias lại các lệnh gốc:

```bash
eval "$(starship init zsh)"
eval "$(zoxide init zsh)"
source <(fzf --zsh)
alias cat="bat"
alias ls="eza --icons --group-directories-first"
alias ll="eza -lah --icons --git"
```

Khi viết code, mình thường mở một session tmux, chia làm hai pane: một pane chạy editor, một pane để gõ lệnh với `rg`, `fzf` và `lazygit`. Toàn bộ vòng lặp viết — tìm — commit gói gọn trong terminal mà không phải rời tay khỏi bàn phím.

Nếu bạn đang dựng môi trường dev từ đầu, mình khuyên bắt đầu từ Git trước. Mình có hướng dẫn riêng về [cài đặt và cấu hình Git lần đầu](/posting/cai-dat-git-cau-hinh-lan-dau/) cùng [bộ lệnh Git cơ bản init, add, commit, status](/posting/lenh-git-co-ban-init-add-commit-status/) — hai bài này ghép rất ăn ý với lazygit ở trên.

## Vài lưu ý để không "vỡ mồm" khi cấu hình

- **Backup file `~/.zshrc` trước khi sửa.** Một dòng sai cú pháp có thể khiến shell không khởi động được. Cứ `cp ~/.zshrc ~/.zshrc.bak` cho chắc.
- **Thêm dần, đừng dán cả nghìn dòng dotfiles của người khác.** Mỗi alias nên là thứ bạn hiểu, nếu không lúc lỗi sẽ rất khó dò.
- **Quan tâm tới bảo mật.** Đừng commit token hay key vào dotfiles công khai — mình đã viết kỹ về chuyện này trong bài [bảo mật và best practices với Git/GitHub](/posting/bao-mat-best-practices-git-github/).
- **Tự động hóa khi có thể.** Nếu bạn dựng pipeline build/test, hãy xem qua [GitHub Actions cho người mới](/posting/github-actions-ci-cd-cho-nguoi-moi/) và công cụ phân tích code như [CodeQL](/posting/codeql-phan-tich-code-tu-dong-cho-lap-trinh-vien/) để bổ trợ cho terminal toolkit của bạn.

Toàn bộ blog này thật ra cũng được dựng và deploy từ terminal — nếu tò mò quy trình, mình có chia sẻ cách [tạo blog với Zola](/posting/tao-blog-voi-zola/). Muốn xem thêm các bài cùng mảng, ghé chuyên mục [Công nghệ](/categories/cong-nghe/).

## Kết luận

Một bộ **công cụ terminal cho Mac** được chọn lọc không phải để khoe màn hình cho ngầu, mà để bạn làm việc nhanh hơn, ít ma sát hơn mỗi ngày. Mười công cụ ở trên — từ Homebrew làm nền, iTerm2 và Starship lo trải nghiệm, tới fzf, ripgrep, bat, eza, zoxide, tmux và lazygit lo năng suất — là dev toolkit 2026 mình thật sự dùng và tin tưởng.

Lời khuyên cuối: đừng cài hết trong một buổi rồi choáng. Hãy bắt đầu từ Homebrew, thêm fzf và Starship trong tuần đầu, rồi mỗi tuần làm quen thêm một công cụ. Sau một tháng, bạn sẽ ngạc nhiên vì mình từng sống thế nào mà không có chúng. Bạn đang dùng công cụ terminal nào tâm đắc? Để lại bình luận để mình bổ sung vào danh sách năm sau nhé!
