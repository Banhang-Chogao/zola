+++
title = "Theme log rollback: an toàn cho blog tĩnh"
description = "Kinh nghiệm xây trang Theme log để lưu mốc rollback theo commit thật, và refactor menu Công cụ thành mega menu gọn gàng, dễ dùng trên desktop và mobile."
date = 2026-06-26
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["Zola", "GitHub Pages", "Rollback", "UX", "Theme Log", "Static Site", "Blog"]
[extra]
thumbnail = "https://picsum.photos/seed/lam-theme-log-sua-menu-cong-cu/600/400"
seo_keyword = "theme log rollback"
featured = false
+++

Có những lúc làm blog tĩnh, vấn đề không nằm ở việc "có build được không", mà nằm ở câu hỏi rất đời thường: **Nếu giao diện mới bị xấu, tôi rollback về bản nào?** Đây là lý do tôi xây dựng một **theme log rollback** — bảng mốc lịch sử giao diện để có thể quay lại phiên bản cũ khi cần. Cùng lúc đó, tôi cũng phát hiện menu Công cụ đang quá dài, khó dùng, nên cần refactor thành mega menu nhóm.

<!-- more -->

Trong lần chỉnh blog này, tôi gom hai việc tưởng nhỏ nhưng rất quan trọng vào một nhánh cải tiến để cải thiện vận hành blog:

Trong lần chỉnh blog này, tôi gom hai việc tưởng nhỏ nhưng rất quan trọng vào một nhánh cải tiến:

1. Tạo một trang **Theme log** để lưu các mốc theme/blog UI theo commit thật.
2. Refactor menu **Công cụ** từ một dropdown dài thành menu có nhóm, dễ đọc hơn.

Bài này ghi lại kinh nghiệm triển khai theo hướng thực chiến cho blog tĩnh dùng Zola và GitHub Pages.

---

## Tại sao cần theme log rollback khi làm blog tĩnh?

Khi blog còn đơn giản, mỗi lần đổi giao diện chỉ cần nhớ đại khái: "bản này đẹp", "bản kia lỗi", "bản trước ổn hơn".

Nhưng khi site đã có nhiều thứ như bài viết, footer, FAQ, related posts, dashboard, công cụ SEO (giống bảng SEO mình từng làm), guideline, font, brand system… thì nhớ bằng đầu không còn đủ nữa. Đó là khi một **theme log rollback** trở thành công cụ thiết yếu để quản lý lịch sử giao diện.

Vấn đề lớn nhất khi rollback theme là:

* Không biết commit nào là mốc giao diện ổn.
* Không phân biệt được commit đổi theme, đổi tính năng, đổi content hay đổi workflow (một bài học từ kinh nghiệm quản lý Git).
* Có khi PR đã merge nhưng production chưa deploy trên GitHub Pages.
* Có khi commit tồn tại trong chat/log nhưng không tồn tại trong repo hiện tại.
* Có khi copy nhầm "dòng ví dụ" trong prompt thành dữ liệu thật — lỗi thường gặp khi xây hệ thống tự động.

Vì vậy Theme log không nên là một trang ghi chú thủ công. Nó nên là một **rollback ledger**: bảng mốc kỹ thuật có thể kiểm chứng bằng git.

---

## Nguyên tắc quan trọng: chỉ dùng dữ liệu thật

Một bài học lớn là: không được hardcode dữ liệu ví dụ vào Theme log.

Ví dụ trong prompt có thể có các commit như:

```txt
cec222fd
06ab2462
a2fddc9d
e317a14b
f0c1c3e5
```

Nhưng commit chỉ được đưa vào bảng chính nếu repo hiện tại verify được bằng git.

Cách kiểm tra (theo [Git documentation](https://git-scm.com/book/en/v2/Git-Basics-Undoing-Things)):

```bash
git cat-file -e <commit>^{commit}
```

hoặc:

```bash
git rev-parse --verify <commit>
```

Điều này giống với cách [GitHub Pages quản lý deployment history](https://docs.github.com/en/pages) — mọi build đều ghi log lại, cho phép rollback nếu cần.

Nếu commit không tồn tại, không đưa vào bảng chính. Có thể đưa vào mục riêng như "Excluded / unverified", nhưng mặc định nên loại khỏi bảng chính.

Theme log phải là dữ liệu thật, không phải bảng minh họa.

---

## Format bảng Theme log nên như thế nào?

Tôi chọn format 9 cột:

| Theme ID | Commit hash | Date/time | Theme name | Layout/style | Color system | Font system | Status | Notes |
| -------- | ----------- | --------- | ---------- | ------------ | ------------ | ----------- | ------ | ----- |

Trong đó:

* **Theme ID**: mã dễ nhớ để rollback, ví dụ `theme-20260626-f0c1c3e`.
* **Commit hash**: commit thật đã verify.
* **Date/time**: thời điểm commit.
* **Theme name**: tên theme hoặc tên mốc thay đổi.
* **Layout/style**: kiểu layout chính.
* **Color system**: hệ màu đang dùng.
* **Font system**: font stack hoặc font thực tế.
* **Status**: live, rollback target, reference, archived, pending.
* **Notes**: ghi chú ngắn để sau này nhìn lại hiểu ngay.

Cách đặt Theme ID nên đơn giản:

```txt
theme-<YYYYMMDD>-<short7hash>
```

Ví dụ:

```txt
theme-20260626-f0c1c3e
```

Commit hash là mốc kỹ thuật. Theme ID là mốc vận hành, dễ đọc hơn.

---

## Theme log nên nằm ở đâu?

Vì đây là công cụ vận hành, tôi không đặt nó ở trang About.

Tôi đặt nó là một trang con của khu vực Công cụ:

```txt
/tools/theme-log/
```

Trang này có nhiệm vụ rõ ràng:

> Use this table as rollback milestones.

Nó không phải trang giới thiệu thương hiệu. Nó là bảng điều khiển nhỏ để sau này nhìn lại: theme nào từng live, theme nào là rollback target, mốc nào liên quan footer, mốc nào liên quan font, mốc nào chỉ là reference.

---

## Cách triển khai trong static site

Với [Zola](https://www.getzola.org/documentation/) + GitHub Pages, không có backend runtime để trang tự chạy lệnh git trực tiếp khi người dùng mở web.

Vì vậy "thời gian thực" ở đây nên hiểu là **near-real-time theo build/deploy**:

1. Chạy script audit trước build.
2. Script đọc git history thật.
3. Script sinh file JSON.
4. Zola render trang Theme log từ JSON.
5. Mỗi lần deploy, dữ liệu được cập nhật theo build mới nhất.

Cấu trúc đề xuất:

```txt
scripts/theme_audit.py
data/theme-log.json
content/tools/theme-log.md
templates/theme-log.html
```

Script `theme_audit.py` nên làm các việc sau:

* Đọc git history.
* Tìm commit liên quan UI/theme qua message và file changed.
* Ưu tiên các file như `templates/`, `sass/`, `static/css`, `static/js`, `config.toml`, các trang guideline, S-DNA, B-DNA.
* Verify từng commit.
* Lấy commit date và commit subject thật.
* Sinh Theme ID.
* Ghi `data/theme-log.json`.
* In bảng 9 cột ra terminal.
* Không fail hard nếu thiếu metadata phụ.

JSON có thể theo schema:

```json
{
  "generated_at": "...",
  "repo": "Banhang-Chogao/zola",
  "production_url": "https://seomoney.org",
  "current_head": "...",
  "themes": [
    {
      "theme_id": "theme-20260626-f0c1c3e",
      "commit_hash": "f0c1c3e...",
      "datetime": "...",
      "theme_name": "...",
      "layout_style": "...",
      "color_system": "...",
      "font_system": "...",
      "status": "live",
      "notes": "..."
    }
  ],
  "excluded": [
    {
      "commit_hash": "...",
      "reason": "not verified"
    }
  ]
}
```

Điểm quan trọng: file JSON được sinh bởi script, không phải gõ tay bảng minh họa.

---

## Vì sao cần làm Theme log trước khi sửa UX menu?

Vì sửa menu cũng là một thay đổi UI.

Nếu menu mới lỗi, dropdown vỡ mobile, hoặc làm mất link công cụ, tôi cần biết rollback về đâu. Theme log giúp ghi lại mốc trước khi sửa menu.

Nói cách khác:

> Trước khi thay đổi giao diện, hãy tạo bản đồ rollback.

Đây là cách làm an toàn hơn so với việc sửa liên tục rồi chỉ nhớ bằng cảm giác. Tương tự như cách quản lý version khi phát triển tính năng blog, mỗi thay đổi giao diện cũng cần có checkpoint rõ ràng.

---

## Vấn đề UX của menu Công cụ

Menu Công cụ trong blog có quá nhiều link:

* Viết bài
* Content Creator
* Bảng Vàng SEO
* Korean Converter
* Changelog
* Insights
* Scoring
* F-Dashboard
* L-Dashboard
* O-Dashboard
* H-Dashboard
* Prompt Support
* Branding Guideline
* S-DNA
* Font Guideline
* Theme log

Khi gom tất cả vào một dropdown một cột, menu sẽ rất dài. Trên desktop nó chiếm gần hết chiều cao màn hình. Trên mobile thì càng tệ hơn.

Vấn đề không phải là có nhiều công cụ. Vấn đề là thiếu phân nhóm.

---

## Cách xử lý: grouped mega menu

Thay vì một danh sách dài, tôi chia menu Công cụ thành các nhóm:

```txt
Công cụ
├─ Viết & biên tập
│  ├─ Viết bài
│  ├─ Content Creator
│  └─ Prompt Support
├─ SEO & phân tích
│  ├─ Bảng Vàng SEO
│  ├─ Insights
│  ├─ Scoring
│  └─ Theme log
├─ Dashboard
│  ├─ F-Dashboard
│  ├─ L-Dashboard
│  ├─ O-Dashboard
│  └─ H-Dashboard
├─ Hệ thống & guideline
│  ├─ Branding Guideline
│  ├─ S-DNA
│  └─ Font Guideline
└─ Công cụ phụ
   ├─ Korean Converter
   └─ Changelog
```

Desktop dùng mega menu 2–3 cột. Mobile dùng accordion hoặc drawer.

Nguyên tắc UX:

* Không xóa link.
* Không đổi URL.
* Không đổi logic tool.
* Chỉ đổi presentation.
* Có max-height khoảng 70vh.
* Nếu vẫn dài thì cho scroll bên trong dropdown.
* Nhóm có heading nhỏ, muted.
* Link đủ lớn để dễ bấm.
* Mobile tap target tối thiểu khoảng 44px.
* Không dùng thư viện ngoài.
* Không redesign toàn header nếu không cần.

---

## Desktop và mobile nên khác nhau

Một lỗi hay gặp là cố dùng cùng dropdown cho desktop và mobile.

Desktop có không gian ngang, nên mega menu nhiều cột hợp lý.

Mobile thì không nên bung một mega menu lớn. Trên mobile, accordion tốt hơn:

```txt
Công cụ
[+] Viết & biên tập
[+] SEO & phân tích
[+] Dashboard
[+] Hệ thống & guideline
[+] Công cụ phụ
```

Người dùng muốn nhóm nào thì mở nhóm đó. Menu không còn "đổ xuống" chiếm toàn màn hình một cách bất ngờ.

---

## Cấu trúc commit nên tách rõ

Dù làm trong cùng một PR, tôi vẫn thích tách thành hai commit:

```txt
feat(tools): add Theme log rollback milestones
fix(nav): group Tools menu into compact mega menu
```

Vì sao?

Vì sau này nếu menu UX lỗi nhưng Theme log ổn, tôi có thể rollback riêng commit menu. Nếu Theme log có lỗi build, cũng dễ tìm.

Một PR có thể chứa hai việc liên quan, nhưng commit nên tách theo trách nhiệm.

---

## QA tối thiểu

Sau khi làm xong, tôi muốn chạy ít nhất:

```bash
python3 scripts/theme_audit.py
zola build
python3 qa_check.py
```

Nếu `qa_check.py` có cảnh báo cũ không liên quan, cần ghi rõ là warning pre-existing. Nhưng `zola build` phải pass.

Ngoài build, nên kiểm tra bằng mắt:

* `/tools/theme-log/` desktop.
* `/tools/theme-log/` mobile.
* Menu Công cụ desktop.
* Menu Công cụ mobile.
* Một bài blog bất kỳ để chắc chắn article UI không bị ảnh hưởng.
* Footer, FAQ, related posts nếu site có các block này.

---

## Bài học rút ra

### 1. Rollback không nên dựa vào trí nhớ

Muốn rollback tốt, cần có mốc rõ ràng. Commit hash là mốc kỹ thuật, nhưng Theme ID là mốc dễ vận hành hơn.

### 2. Dữ liệu log phải kiểm chứng được

Không đưa dữ liệu ví dụ vào bảng production. Nếu một commit không verify được bằng git, không được coi là mốc thật.

### 3. Static site vẫn có thể có audit log

Không cần backend phức tạp. Chỉ cần script build-time sinh JSON, rồi Zola render thành trang.

### 4. Menu dài không phải lỗi nội dung, mà là lỗi tổ chức

Nhiều công cụ là tốt. Nhưng menu phải có phân nhóm, layout phù hợp desktop/mobile.

### 5. Đừng sửa UI lớn khi chưa có mốc rollback

Theme log nên làm trước. Menu, font, header, layout làm sau. Như vậy mỗi thay đổi đều có đường lui.

---

## Kết luận

Hai tính năng này nhìn nhỏ nhưng giúp blog vận hành trưởng thành hơn.

**Theme log** giúp biết rõ: theme nào đang live, commit nào có thể rollback, mốc nào chỉ là reference, mốc nào bị loại vì không verify được.

**Tools mega menu** giúp khu vực Công cụ dễ dùng hơn, không còn cảm giác một dropdown dài che kín màn hình.

Một bên là an toàn kỹ thuật. Một bên là trải nghiệm người dùng.

Khi làm blog lâu dài, cả hai đều quan trọng. Giao diện đẹp là tốt, nhưng giao diện có thể rollback an toàn và dễ dùng trên mọi thiết bị mới là thứ giúp site sống bền.
