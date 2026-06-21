+++
title = "Viết blog bằng local terminal khi AI hết credit"
date = 2026-06-22
description = "Quy trình viết và publish một bài blog từ local terminal khi Claude hoặc trợ lý AI hết credit, có QA, Git và PR an toàn."
slug = "viet-blog-bang-local-terminal-khi-ai-het-credit"

[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["terminal", "blog", "zola", "github", "git", "ai", "workflow", "production"]

[extra]
thumbnail = "https://picsum.photos/seed/local-terminal-blog/600/400"
seo_keyword = "viết blog bằng local terminal"
featured = false
+++

Có những ngày trợ lý AI của bạn báo hết credit, hết lượt, hoặc đơn giản là đang bảo trì. Nếu cả quy trình xuất bản của bạn phụ thuộc vào AI, bạn sẽ kẹt. Bài này hướng dẫn cách **viết blog bằng local terminal** một cách trọn vẹn — từ tạo nhánh, soạn bài, kiểm tra QA, build sạch, tới mở Pull Request và chờ auto-merge — mà không cần một dòng trợ giúp nào từ AI.

Đây là phần ba của cụm bài. Nếu muốn hiểu vì sao quy trình kỷ luật lại quan trọng, hãy đọc [case study fix QA Gatekeeper GitHub Actions](/posting/fix-qa-gatekeeper-github-actions-merge-conflict-zola/). Còn nếu muốn tra cứu ý nghĩa từng câu lệnh, [bài giải thích các lệnh Git đưa blog lên production](/posting/cac-lenh-git-dua-blog-len-production/) là cẩm nang đi kèm.

<!-- more -->

## AI là trợ thủ, terminal mới là xương sống

Trước hết, hãy nói thẳng: AI rất hữu ích. Nó giúp brainstorm tiêu đề, gợi ý dàn ý, soát lỗi diễn đạt. Nhưng AI **không phải** là hệ thống xuất bản của bạn. Khi đưa nội dung lên production, thứ thực sự làm việc là: trình soạn thảo, Git, trình tạo site tĩnh (Zola), bộ QA, và CI/CD trên GitHub.

Nói cách khác, AI nằm ở tầng ý tưởng; còn terminal, Git và QA nằm ở tầng vận hành. Khi AI hết credit, tầng vận hành vẫn phải chạy được. Đó là lý do mỗi người viết blog kỹ thuật nên thành thạo quy trình thủ công ít nhất một lần.

## Bước 1 — Luôn bắt đầu từ main mới nhất

Mở terminal và đồng bộ với nhánh chính:

```bash
git fetch origin
git checkout main
git pull origin main
```

Việc này đảm bảo bạn xuất phát từ trạng thái production gần nhất, tránh "stale base" — một trong những nguyên nhân conflict phổ biến nhất.

## Bước 2 — Tạo một nhánh riêng cho bài viết

```bash
git checkout -b feat/bai-viet-moi-cua-toi
```

Mỗi bài viết (hoặc cụm bài) nên có nhánh riêng. Điều này giữ `main` sạch và giúp Pull Request về sau dễ review.

## Bước 3 — Tạo file Markdown đúng chỗ

Blog Zola lưu bài trong thư mục `content/`. Với blog này, bài viết nằm ở `content/posting/`:

```bash
touch content/posting/bai-viet-moi-cua-toi.md
```

Tên file thường chính là slug — hãy đặt không dấu, dùng gạch nối, ngắn gọn và mô tả đúng nội dung.

## Bước 4 — Viết frontmatter chuẩn

Frontmatter là khối cấu hình đầu file, đặt giữa hai dấu `+++`. Đây là phần QA sẽ kiểm tra nghiêm ngặt:

```toml
+++
title = "Tiêu đề bài viết của bạn"
date = 2026-06-22
description = "Mô tả ngắn 1-2 câu cho SEO."
slug = "bai-viet-moi-cua-toi"

[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["terminal", "blog", "zola"]

[extra]
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
seo_keyword = "từ khóa chính"
featured = false
+++
```

Hãy chắc chắn có `title`, `date` đúng định dạng `YYYY-MM-DD`, một `description`, và ít nhất một `category` hoặc `tag`. Thiếu những trường này, QA sẽ báo lỗi ngay.

## Bước 5 — Thêm ảnh một cách an toàn

Ảnh đặt trong `static/`. Khi build, Zola sao chép `static/` thành đường dẫn gốc của site, nên ảnh ở `static/img/abc.webp` sẽ truy cập qua `/img/abc.webp`.

Một lưu ý quan trọng và rất thực tế: nhiều blog tĩnh có pipeline tự động chuyển ảnh raster (`.jpg`, `.png`) sang `.webp` và **xóa bản gốc**. Vì vậy, nếu bạn nhúng ảnh trong body bằng đường dẫn `.jpg`, link có thể chết sau khi pipeline chạy. An toàn nhất là tham chiếu ảnh ở dạng `.webp` trong nội dung:

```markdown
![Mô tả ảnh](/img/posting/bai-viet-moi-cua-toi/cover.webp)
```

## Bước 6 — Kiểm tra đường dẫn trước khi nghĩ tới push

Trước khi tốn thời gian build, hãy soi nhanh đường dẫn ảnh và link:

```bash
grep -RIn "](/img/" content/posting/bai-viet-moi-cua-toi.md
ls static/img/posting/bai-viet-moi-cua-toi/
```

Nếu file ảnh không tồn tại đúng tên, sửa ngay. Đây là loại lỗi nhỏ nhưng hay gặp nhất.

## Bước 7 — Chạy QA ngay trên máy

```bash
python3 qa_check.py
```

Bộ QA của repo sẽ quét conflict marker, secret, frontmatter SEO và nhiều rule production-safe khác. Sửa hết những gì nó báo trước khi đi tiếp.

## Bước 8 — Build sạch và kiểm 404 trước khi push

Đây là bước bảo hiểm quan trọng nhất cho blog tĩnh:

```bash
git status -sb
rm -rf public
zola build
python3 qa-404-checker.py
echo "qa_404_exit=$?"
```

* `rm -rf public` xóa build cũ để tránh báo cáo 404 bị nhiễu.
* `zola build` dựng lại toàn bộ site.
* `qa-404-checker.py` quét link/ảnh hỏng trong `public/`.

Nếu checker báo broken link **thật** trong bài mới, đừng push — hãy sửa. Nếu nó bỗng báo hỏng cả các route lõi như `/` hay `/site.css`, gần như chắc chắn `public/` đang cũ; hãy build lại rồi chạy lại checker. Tuyệt đối không commit một báo cáo 404 đang fail.

## Bước 9 — Chỉ commit đúng file mình muốn

Đừng `git add .` một cách máy móc. Hãy liệt kê chính xác:

```bash
git add content/posting/bai-viet-moi-cua-toi.md
git add static/img/posting/bai-viet-moi-cua-toi/cover.webp
git diff --cached --stat
git commit -m "feat(blog): them bai viet moi"
```

`git diff --cached --stat` cho bạn xem lại đúng những gì sắp commit. Cách này giúp commit gọn, tránh lỡ tay đưa `public/` hay file report tự sinh vào lịch sử.

## Bước 10 — Push nhánh và mở Pull Request

```bash
git push -u origin feat/bai-viet-moi-cua-toi
gh pr create --base main --head feat/bai-viet-moi-cua-toi \
  --title "feat(blog): them bai viet moi" \
  --body "Bai viet moi tu local terminal."
```

Nếu chưa quen [GitHub CLI](https://cli.github.com/), bạn hoàn toàn có thể mở PR thủ công trên giao diện web của GitHub. Cả hai cách đều đưa bạn vào cùng một pipeline.

## Bước 11 — Theo dõi check và chờ auto-merge

```bash
gh pr checks --watch
```

Lệnh này cho bạn xem QA Gatekeeper và các check khác chạy theo thời gian thực. Khi mọi check xanh, hệ thống auto-merge sẽ gộp PR vào `main`, và deploy sẽ đưa bài lên production. Việc của bạn lúc này chỉ là kiên nhẫn — đừng push linh tinh khi CI đang chạy.

## Vì sao nên thành thạo viết blog bằng local terminal

Khi bạn biết **viết blog bằng local terminal**, bạn không còn bị phụ thuộc vào bất kỳ công cụ nào — kể cả AI. Bạn hiểu nội dung của mình đi qua những cổng kiểm tra nào, vì sao chúng tồn tại, và phải làm gì khi một cổng báo đỏ.

Theo [tài liệu chính thức của Zola](https://www.getzola.org/documentation/getting-started/cli-usage/), toàn bộ vòng đời của một site tĩnh chỉ xoay quanh vài lệnh đơn giản: `build`, `serve`, `check`. Phần còn lại là kỷ luật Git và QA. Khi đã nắm chắc, bạn có thể xuất bản từ bất kỳ máy nào có terminal, kể cả lúc 2 giờ sáng ở một quán cà phê.

## Kết luận

AI hết credit không phải là cái cớ để dừng xuất bản. Quy trình cốt lõi vẫn nằm trong tay bạn: bắt đầu từ `main` mới, tạo nhánh, viết frontmatter chuẩn, thêm ảnh an toàn, chạy QA, build sạch, kiểm 404, commit có chủ đích, push, mở PR và chờ auto-merge.

Hãy xem AI như một người cộng sự sáng tạo, còn terminal và Git như dây chuyền sản xuất. Khi bạn vững phần vận hành, mọi thứ khác chỉ là gia vị. Để ôn lại từng câu lệnh, hãy ghé [các lệnh Git đưa blog lên production](/posting/cac-lenh-git-dua-blog-len-production/); và để thấy quy trình này cứu bạn thế nào trong một sự cố thật, [case study fix QA Gatekeeper GitHub Actions](/posting/fix-qa-gatekeeper-github-actions-merge-conflict-zola/) là minh chứng rõ nhất.
