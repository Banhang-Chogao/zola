+++
title = "Bảo mật và best practices với Git/GitHub"
description = "Bảo mật Git GitHub: tránh lộ secret, .gitignore, 2FA, SSH, signed commit, branch protection và thói quen tốt. Series Git & GitHub — Bài 15/15."
date = 2026-06-18
aliases = ["/bao-mat-best-practices-git-github/"]
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["git", "github", "bảo mật git", "git github series", "lập trình"]
[extra]
thumbnail = "https://banhang-chogao.github.io/zola/img/placeholder/placeholder.svg"
seo_keyword = "bảo mật git"
featured = false
series = "git-github"
series_part = 15
series_total = 15

[[extra.faq]]
q = "Lỡ commit file chứa mật khẩu lên GitHub thì sao?"
a = "Coi như mật khẩu đó đã lộ — hãy thu hồi/đổi nó ngay lập tức, vì nó còn trong lịch sử Git dù bạn xóa file. Sau đó dùng công cụ như git filter-repo hoặc BFG để gột khỏi lịch sử, rồi force-push (cẩn trọng)."

[[extra.faq]]
q = ".gitignore quan trọng thế nào với bảo mật?"
a = "Rất quan trọng. .gitignore ngăn các file nhạy cảm như .env, key, token bị vô tình commit. Đây là tuyến phòng thủ đầu tiên chống lộ secret. Hãy thêm .env và thư mục build vào .gitignore ngay từ đầu dự án."

[[extra.faq]]
q = "Có nên ký (sign) commit không?"
a = "Nên, nhất là với dự án quan trọng. Signed commit dùng GPG/SSH chứng minh commit thật sự do bạn tạo, hiển thị nhãn Verified trên GitHub, chống mạo danh tác giả."
+++

> 📚 **Git & GitHub Series (Bài 15/15)** — Bài cuối cùng. Sau khi tự động hóa với [GitHub Actions ở Bài 14](/zola/posting/github-actions-ci-cd-cho-nguoi-moi/), ta khép lại series bằng chủ đề sống còn: **bảo mật Git**.

**Bảo mật Git** và GitHub là phần nhiều người mới bỏ qua — cho tới khi vô tình đẩy mật khẩu lên một repo công khai. Vì Git lưu **toàn bộ lịch sử**, một secret bị lộ không biến mất chỉ vì bạn xóa file ở commit sau. Bài cuối này tổng hợp các best practice quan trọng nhất để giữ an toàn cho code, tài khoản và cả nhóm của bạn.

<!-- more -->

## Bảo mật Git: đừng bao giờ commit secret

Quy tắc số một: **không commit thông tin nhạy cảm** — mật khẩu, API key, token, file `.env`, private key. Theo [hướng dẫn bảo mật của GitHub](https://docs.github.com/en/code-security), một khi secret lên repo (nhất là public), hãy coi như nó đã bị lộ vĩnh viễn.

Tuyến phòng thủ đầu tiên là `.gitignore` (nhắc lại [Bài 3](/zola/posting/lenh-git-co-ban-init-add-commit-status/)):

```
.env
*.key
*.pem
secrets.json
config/local.*
```

Blog này cũng tuân thủ nghiêm: không hardcode secret trong repo hay workflow, mọi token đều qua GitHub Secrets như đã thấy ở Bài 14.

## Khi lỡ tay đẩy secret lên — xử lý ngay

Nếu đã push một secret, hãy hành động theo thứ tự:

1. **Thu hồi/đổi ngay** secret đó (đổi mật khẩu, revoke token). Đây là việc khẩn cấp nhất.
2. **Gột khỏi lịch sử** bằng `git filter-repo` hoặc công cụ BFG Repo-Cleaner.
3. Force-push lịch sử đã làm sạch (cẩn trọng, phối hợp với cả nhóm).
4. Bật **secret scanning** của GitHub để được cảnh báo tự động lần sau.

Nhớ rằng chỉ xóa file ở commit mới là **không đủ** — secret vẫn nằm trong các commit cũ.

## Bảo vệ tài khoản GitHub

| Biện pháp | Vì sao |
|---|---|
| Bật **2FA** | Chặn truy cập trái phép dù lộ mật khẩu |
| Dùng **SSH key** hoặc PAT phạm vi hẹp | Tránh dùng mật khẩu thô; giới hạn quyền |
| Đặt **token hết hạn** | Giảm rủi ro nếu token rò rỉ |
| Rà soát **OAuth apps** định kỳ | Thu hồi ứng dụng không còn dùng |

Personal Access Token nên cấp **quyền tối thiểu** cần thiết và đặt thời hạn — đừng tạo token "toàn quyền, không hết hạn".

## Signed commit — chứng minh bạn là tác giả

Mặc định, ai cũng có thể đặt `user.name`/`user.email` trùng bạn và mạo danh. Ký commit bằng GPG hoặc SSH giải quyết điều này:

```bash
git config --global commit.gpgsign true
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519.pub
```

Commit đã ký hiển thị nhãn **Verified** trên GitHub, tăng độ tin cậy cho dự án.

## Branch protection — chốt chặn ở cấp repo

Với nhánh quan trọng như `main`, bật **branch protection** trong Settings để:

- Bắt buộc Pull Request trước khi merge (nối tiếp [Bài 9](/zola/posting/pull-request-quy-trinh-cong-tac-github/)).
- Yêu cầu CI xanh trước khi gộp.
- Cấm force-push và xóa nhánh.

Đây là cách biến quy ước workflow thành luật được hệ thống cưỡng chế, tránh tai nạn ghi đè lịch sử.

## Checklist best practices

- ✅ Thêm `.gitignore` ngay khi tạo dự án.
- ✅ Không bao giờ commit `.env`, key, token.
- ✅ Bật 2FA và dùng SSH/PAT phạm vi hẹp.
- ✅ Viết commit message rõ ràng, commit nhỏ và thường xuyên.
- ✅ Mọi thay đổi qua nhánh + Pull Request, không push thẳng `main`.
- ✅ Bật branch protection và secret scanning cho repo quan trọng.
- ✅ Cấp token theo nguyên tắc quyền tối thiểu và đặt thời hạn hết hạn.
- ✅ Ký commit để có nhãn Verified với dự án cần độ tin cậy cao.

## Tổng kết series Git & GitHub

Vậy là khép lại 15 bài: từ [Git là gì](/zola/posting/git-la-gi-version-control-cho-nguoi-moi/), [lệnh cơ bản](/zola/posting/lenh-git-co-ban-init-add-commit-status/), [branch](/zola/posting/git-branch-lam-viec-voi-nhanh/), [merge](/zola/posting/git-merge-va-xu-ly-conflict/), tới [Pull Request](/zola/posting/pull-request-quy-trinh-cong-tac-github/), [rebase](/zola/posting/git-rebase-lam-sach-lich-su-commit/) và [GitHub Actions](/zola/posting/github-actions-ci-cd-cho-nguoi-moi/). **Bảo mật Git** là mảnh ghép cuối, biến bạn từ người biết dùng Git thành người dùng Git **an toàn và chuyên nghiệp**. Chúc bạn commit vui và đừng quên: push thường xuyên, và đừng bao giờ commit mật khẩu!
