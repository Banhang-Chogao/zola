+++
title = "Cách xoá sạch ứng dụng khỏi Mac bằng Terminal: ví dụ gỡ 84Key"
description = "Hướng dẫn chi tiết xoá ứng dụng trên Mac bằng Terminal, bao gồm cache và preference files. Sử dụng 84Key (bộ gõ tiếng Việt) làm ví dụ thực tế."
date = 2026-06-21
aliases = ["/cach-xoa-sach-ung-dung-khoi-mac-bang-terminal-84key/"]

[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["Mac", "macOS", "Terminal", "gỡ ứng dụng", "xoá app trên Mac", "84Key", "bộ gõ tiếng Việt"]

[extra]
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
seo_keyword = "xoá app trên Mac bằng Terminal"
featured = true

[[extra.faq]]
q = "Tại sao không xoá app bằng cách kéo vào Trash bình thường?"
a = "Kéo vào Trash chỉ xoá file ứng dụng chính (.app), nhưng để lại cache, preferences, và các file cấu hình trong Library — làm Mac lâu dần. Terminal cho phép xoá sạch tất cả liên quan."

[[extra.faq]]
q = "Xoá app bằng Terminal có nguy hiểm không?"
a = "Nếu bạn biết cú pháp lệnh, thì rất an toàn. Chỉ cần nhớ: dùng đúng tên app, kiểm tra kỹ trước khi chạy `rm -rf`, và tránh xoá file hệ thống Apple. Bài này có ví dụ an toàn với 84Key."

[[extra.faq]]
q = "84Key là gì? Có phải là malware không?"
a = "84Key là bộ gõ tiếng Việt hợp pháp cho macOS, phát triển bởi Nghĩa Lương. Không phải malware — chúng tôi chỉ dùng nó làm ví dụ vì nó dễ phát hiện và có cây thư mục chuẩn."

[[extra.faq]]
q = "Sau khi xoá, nên làm gì tiếp?"
a = "Chạy lệnh kiểm tra để đảm bảo app không còn. Sau đó, xóa file .dmg cài đặt (nếu có) từ Downloads. Cuối cùng, restart Mac hoặc đăng xuất rồi đăng nhập lại nếu app có service tự khởi động."

[[extra.faq]]
q = "Tôi quên lại tên Bundle ID của app. Làm sao tìm?"
a = "Dùng lệnh `mdinfo -name com.example.app` hoặc xem trong `/Applications/AppName.app/Contents/Info.plist` (macOS đã cài `plistutil` hoặc dùng `cat` để xem text)."
+++

> 💡 **Mẹo từ Mac người dùng lâu năm:** Khi cài một ứng dụng Mac, đặc biệt là input method (bộ gõ) như 84Key, hệ thống không chỉ lưu file `.app` chính. Các tệp cấu hình, cache, và preference sẽ nằm rải rác trong thư mục `Library`. Xoá không sạch = còn "rác" làm máy chậm. Bài này hướng dẫn cách xoá **từ A tới Z** mà không bỏ sót.

Mac ngày nay có SSD nhanh nhưng dung lượng hạn chế, và tích tích những app cũ + cache → máy sẽ cảm thấy nặng. Thay vì xoá app bằng cách kéo vào Trash (để lại rác), bạn có thể dùng Terminal — công cụ dòng lệnh mạnh mẽ trên mọi Mac — để xoá **hoàn toàn**, kể cả những file ẩn.

Bài này dùng **84Key** (bộ gõ tiếng Việt) làm ví dụ thực tế — nó có cây thư mục tiêu chuẩn và dễ kiểm chứng, nhưng quy trình cũng áp dụng cho hầu hết ứng dụng Mac khác.

## Bước 1: Kiểm tra ứng dụng có đang chạy không

Trước khi xoá, hãy dừng process của app (nếu đang chạy). Mở Terminal (`⌘ + Space`, gõ "Terminal", Enter) và chạy:

```bash
ps aux | grep -iE "84[ -]?key|84key" | grep -v grep
```

Lệnh này tìm kiếm process có tên chứa "84key" (không phân biệt hoa/thường) và hiển thị nếu có. Nếu thấy một dòng kết quả → app đang chạy.

**Nếu đang chạy, cách dừng:** Bấm icon app trên menu bar (nếu có) → Quit, hoặc:

```bash
killall -9 "84Key" 2>/dev/null || true
```

Lưu ý: `2>/dev/null` bỏ đi lỗi nếu process không tồn tại; `|| true` đảm bảo lệnh luôn thành công.

## Bước 2: Tìm tất cả file liên quan tới 84Key trên Mac

Ứng dụng Mac không chỉ nằm ở `/Applications/`. Cache, preference, support file có thể nằm ở `/Library`, `~/Library` (thư mục nhà), hoặc `/var/`. Dùng `mdfind` (Spotlight search qua dòng lệnh) để quét:

```bash
mdfind "84Key OR '84 Key' OR 84key" 2>/dev/null | head -20
```

Ngoài ra, quét trực tiếp các thư mục thường:

```bash
find /Applications "$HOME/Applications" "$HOME/Downloads" "$HOME/Library" /Library -iname "*84*key*" 2>/dev/null
```

Lệnh này tìm mọi file/thư mục có tên chứa "84" và "key" (case-insensitive). `2>/dev/null` ẩn cảnh báo "Permission denied" để output sạch hơn.

**Kết quả sẽ gồm:**
- Ứng dụng chính: `/Applications/84Key.app`
- File cài đặt: `$HOME/Downloads/84Key-v0.1.0.dmg`
- Cache: `$HOME/Library/Caches/com.nghialuong.key84`
- Preferences: `$HOME/Library/Preferences/com.nghialuong.key84.plist`
- Support folder: `$HOME/Library/Application Support/com.nghialuong.key84`

Ghi chú những đường dẫn này lại — bạn sẽ cần chúng ở bước kế tiếp.

## Bước 3: Xoá ứng dụng chính trong /Applications

Đây là phần dễ nhất. Ứng dụng chính thường nằm ở `/Applications/`:

```bash
sudo rm -rf "/Applications/84Key.app"
```

**Giải thích:**
- `sudo` = chạy lệnh với quyền admin (MacOS yêu cầu để xoá trong `/Applications`)
- `rm` = remove (xoá)
- `-rf` = recursive (xoá thư mục + nội dung), force (không hỏi xác nhận)
- `"/Applications/84Key.app"` = đường dẫn đúng (lưu ý dấu nháy nếu tên có space)

Khi gõ `sudo`, bạn sẽ được hỏi mật khẩu Mac. **Khi nhập mật khẩu, ký tự sẽ KHÔNG hiển thị** (đó là bình thường) — chỉ cần gõ đúng rồi nhấn Enter.

Nếu muốn hủy lệnh khi đang gõ, nhấn `Ctrl + C`.

## Bước 4: Xoá file cài đặt (.dmg) nếu có

Nếu file cài đặt vẫn còn trong `Downloads`:

```bash
rm -f "$HOME/Downloads/84Key-v0.1.0.dmg"
```

Hoặc tổng quát hơn (tất cả file `.dmg` có "84Key"):

```bash
rm -f "$HOME/Downloads"/*84Key*.dmg
```

## Bước 5: Xoá cache, preferences, và Application Support

Đây là phần quan trọng — những folder ẩn này chứa setting, cache, và dữ liệu:

**Xoá cache:**
```bash
rm -rf "$HOME/Library/Caches/com.nghialuong.key84"
```

**Xoá preferences (.plist file):**
```bash
rm -f "$HOME/Library/Preferences/com.nghialuong.key84.plist"
```

**Xoá Application Support folder:**
```bash
rm -rf "$HOME/Library/Application Support/com.nghialuong.key84"
```

**Xoá Cookies (nếu app có web component):**
```bash
rm -f "$HOME/Library/Cookies/com.nghialuong.key84.binarycookies"
```

Ghi chú: Bundle ID (`com.nghialuong.key84`) không phải lúc nào cũng dễ đoán. Bạn có thể tìm trong `/Applications/AppName.app/Contents/Info.plist`:

```bash
cat "/Applications/84Key.app/Contents/Info.plist" | grep -i "bundle"
```

Nếu đã xoá app, hãy dùng kết quả từ Bước 2 (tìm mdfind) để biết Bundle ID chính xác.

## Bước 6: Kiểm tra xoá thành công

Chạy lại lệnh kiểm tra từ Bước 1:

```bash
ps aux | grep -iE "84key" | grep -v grep
```

Nếu **không có output** (hoặc chỉ có "grep" trong kết quả) → process xoá thành công.

Kiểm tra ứng dụng không còn trong `/Applications`:

```bash
ls -la "/Applications/" | grep -i "84key"
```

Nếu **không có output** → ứng dụng xoá thành công.

Kiểm tra cache/preferences:

```bash
ls -la "$HOME/Library/Caches/" | grep -i "84key"
ls -la "$HOME/Library/Preferences/" | grep -i "84key"
```

Cả hai không có output = xoá sạch.

## Bước 7: Làm sạch thêm (Tùy chọn)

Nếu muốn tuyệt đối chắc chắn:

**Kiểm tra Input Sources (nếu là input method):**
```bash
defaults read com.apple.HIToolbox AppleEnabledInputSources | grep -i "84"
```

Nếu 84Key được đăng ký làm input source, bạn có thể xoá nó qua **System Settings → Keyboard → Input Sources** (GUI). Hoặc dùng Terminal tùy chỉnh nâng cao nếu biết rõ.

**Restart hoặc Logout/Login:**
Nếu app từng tự khởi động khi Mac boot, hãy restart để làm sạch hết:

```bash
sudo reboot  # Để restart ngay
```

Hoặc đơn giản hơn: Menu Apple → Restart.

## Những điều nên tránh

- ❌ **Xoá file hệ thống Apple:** Tránh xoá bất cứ file nào dụng tên "Apple" hoặc trong `/System/Library` trừ khi chắc chắn.
- ❌ **Xoá toàn bộ ~/Library:** Đây là folder chứa setting của toàn bộ ứng dụng, xoá cả folder làm mất hết cấu hình Mac.
- ❌ **Quên `sudo`:** Một số folder trong `/Library` yêu cầu quyền admin; nhầm xoá không được sẽ không hỏi lại.

## Tóm lại

Xoá sạch app trên Mac bằng Terminal rất đơn giản nếu biết các bước:

1. ✅ Kiểm tra app có chạy (ps aux)
2. ✅ Tìm tất cả file liên quan (mdfind, find)
3. ✅ Xoá `/Applications/AppName.app`
4. ✅ Xoá file .dmg cài đặt
5. ✅ Xoá cache, preferences, Application Support
6. ✅ Kiểm tra lại không còn process/file
7. ✅ Restart nếu cần

Với ví dụ 84Key, bạn cũng đã hiểu cơ chế Bundle ID và tên thư mục — áp dụng quy trình này cho **bất kỳ app Mac nào**.

Mac của bạn sẽ nhẹ nhàng hơn — đó là lý do bạn nên làm sạch định kỳ!

---

**Bạn đã thử Terminal xoá app trên Mac chưa?** Bình luận bên dưới nếu có câu hỏi hoặc muốn hỏi thêm về app khác.

**Đọc thêm:** 
- [Git là gì? Version Control dành cho người mới](/posting/git-la-gi-version-control-cho-nguoi-moi/)
- [Cài đặt Git và cấu hình lần đầu](/posting/cai-dat-git-cau-hinh-lan-dau/)
- [Bảo mật Best Practices cho Git & GitHub](/posting/bao-mat-best-practices-git-github/)
