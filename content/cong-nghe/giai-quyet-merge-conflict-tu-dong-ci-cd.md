+++
title = "Giải Quyết Merge Conflict Tự Động: Case Study CI/CD Thực Tế"
description = "Hướng dẫn giải quyết merge conflict tự động cho file auto-generated trong CI/CD. Case study thực tế: resolve data JSON, broken link và lỗi template Tera."
date = 2026-06-27
aliases = ["/giai-quyet-merge-conflict-tu-dong-ci-cd/",
  "/posting/giai-quyet-merge-conflict-tu-dong-ci-cd/"
]
slug = "giai-quyet-merge-conflict-tu-dong-ci-cd"

[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["automation", "ci-cd", "devops", "git", "merge-conflict"]
[extra]
seo_keyword = "giải quyết merge conflict"
thumbnail = "/img/placeholder/placeholder.svg"
toc = true

[[extra.faq]]
q = "Merge conflict ở file auto-generated nên lấy bản nào?"
a = "Với file do script/CI tự sinh (ví dụ data/*.json, references, scores), gần như luôn lấy bản trên nhánh main. Lý do: main đã chạy lại script và có state mới nhất, còn nhánh feature giữ bản cũ. Sau khi lấy main, có thể chạy lại script sinh data để khớp hoàn toàn."

[[extra.faq]]
q = "Khi resolve conflict ở file nội dung thì giữ bản nào?"
a = "Mặc định giữ bản trên nhánh feature (vì đó là thay đổi bạn muốn đưa lên). Nhưng phải kiểm tra hai trường hợp: bài viết đã tồn tại trên main (trùng lặp) hoặc bản nhánh có link nội bộ trỏ tới trang chưa tồn tại. Cả hai đều nên lấy bản main hoặc sửa lại trước khi merge."

[[extra.faq]]
q = "Có nên dùng git checkout --theirs cho file template không?"
a = "Không nên lấy nguyên cả file một cách mù quáng. Với template hoặc mã nguồn, hãy resolve từng vùng conflict cụ thể để giữ phần logic mới của nhánh, đồng thời nhận các bản vá đã có trên main. Lấy nguyên một bên có thể xóa mất công sức của nhánh kia."

[[extra.faq]]
q = "Cú pháp ternary kiểu Python có chạy trong template Tera không?"
a = "Không. Tera (engine của Zola) không hỗ trợ cú pháp 'X if Y else Z' trong câu lệnh set. Bạn phải dùng khối if-elif-else nhiều dòng. Nếu để cú pháp Python, zola build sẽ báo lỗi parse kiểu 'expected or, and, not...' và chặn deploy."

[[extra.faq]]
q = "Làm sao tự động hóa việc giải quyết merge conflict?"
a = "Xây một bộ quy tắc phân loại theo loại file: data tự sinh lấy main, nội dung giữ feature, template resolve từng vùng. Sau đó viết script đọc danh sách file unmerged và áp đúng chiến lược cho từng nhóm, rồi luôn chạy bộ kiểm tra (QA, build, link) trước khi push."

[[extra.faq]]
q = "Vì sao phải verify lại sau khi resolve conflict?"
a = "Vì một PR không có conflict marker vẫn có thể vỡ build. Resolve sai có thể để lại link hỏng, cú pháp template lỗi, hoặc trùng bài. Luôn chạy QA check, build site và kiểm tra internal link trước khi đẩy lên để bắt lỗi sớm thay vì để CI đỏ."
+++

Trong vài tháng vận hành một blog tĩnh chạy trên GitHub Actions, mình nhận ra phần lớn thời gian "chữa cháy" CI/CD không nằm ở code chính, mà ở khâu **giải quyết merge conflict**. Đặc biệt là khi nhiều pull request mở song song và cùng chạm vào các file do hệ thống tự sinh.

Bài viết này tổng kết một case study thực tế: mình xử lý cùng lúc **4 pull request bị conflict** bằng một chiến lược mình gọi là "auto-healing" — tự động chữa lành theo quy tắc cố định, thay vì ngồi đoán mò từng file. Nếu bạn đang vận hành CI/CD cho blog, tài liệu, hay bất kỳ static site nào, cách tiếp cận này sẽ giúp bạn merge nhanh và an toàn hơn rất nhiều.

## Vì sao merge conflict cứ lặp lại ở file tự sinh

Trước khi nói cách giải quyết merge conflict, cần hiểu vì sao nó cứ tái diễn. Trên blog của mình, có một loạt file dữ liệu được sinh tự động bởi script và hook CI:

- `data/seo-qa-scores.json` — điểm SEO chấm sau mỗi lần sửa bài
- `data/references.json` — danh sách nguồn tham khảo build từ nội dung
- `data/related.json` — bài viết liên quan tính theo ngữ nghĩa
- Các báo cáo dashboard, compliance, merge-report…

Vấn đề nằm ở vòng đời: một nhánh feature được tạo ra từ `main` ở thời điểm A. Trong lúc nhánh đó chờ review, `main` tiếp tục merge các PR khác, và mỗi lần merge lại **chạy lại hook sinh data** — ghi đè cùng những dòng đầu file (thường là timestamp). Đến khi nhánh feature muốn merge, hai bên đụng nhau ở đúng các file tự sinh đó.

Điểm mấu chốt: đây **không phải xung đột logic**. Nội dung thật (file `.md` của bài viết) thường không hề conflict. Chỉ có metadata tự sinh là đụng. Hiểu được điều này, ta có thể xử lý nó một cách máy móc, deterministic.

## Chiến lược giải quyết merge conflict tự động bằng cách phân loại file

Bí quyết để giải quyết merge conflict nhanh là **đừng coi mọi conflict như nhau**. Mình chia file thành ba nhóm, mỗi nhóm một chiến lược cố định.

### File data tự sinh → luôn lấy bản main

Với mọi file trong `data/*.json` do script/hook sinh ra, mình luôn lấy bản trên `main`:

```bash
git checkout --theirs data/seo-qa-scores.json data/references.json
git add data/seo-qa-scores.json data/references.json
```

Lý do: `main` đã chạy lại toàn bộ pipeline và mang state mới nhất. Bản trên nhánh feature là ảnh chụp cũ, giữ lại chỉ gây sai lệch. Nếu cần khớp tuyệt đối, sau khi lấy main mình chạy lại `build_references.py` để regenerate.

### File nội dung → giữ bản PR, trừ khi trùng hoặc link hỏng

Với `content/posting/*.md`, mặc định giữ bản trên nhánh feature vì đó chính là thay đổi muốn đưa lên. Nhưng có hai ngoại lệ quan trọng phải kiểm tra:

1. **Bài đã tồn tại trên main** — tức là một PR khác đã merge đúng bài đó rồi. Khi này nhánh feature chỉ là bản trùng, nên lấy bản main để tránh phân nhánh nội dung.
2. **Bản nhánh chứa internal link hỏng** — trỏ tới bài chưa được publish. Đây là cái bẫy mình sẽ nói kỹ ở dưới.

### Template và code → resolve từng vùng, không lấy mù

Đây là nhóm nguy hiểm nhất. Tuyệt đối **không** dùng `git checkout --theirs` hay `--ours` cho cả file template. Lý do: template thường chứa cả phần logic mới của nhánh (ví dụ một layout mới) lẫn bản vá đã có trên main. Lấy nguyên một bên sẽ xóa mất công sức của bên kia.

Cách đúng là mở file, tìm đúng vùng nằm giữa các marker `<<<<<<<` và `>>>>>>>`, rồi tự quyết định giữ gì cho từng vùng — giữ phần layout mới của nhánh, đồng thời nhận bản vá đúng từ main.

## Case study: giải quyết 4 pull request một lúc

Đây là bảng tổng kết bốn PR mình xử lý trong một phiên, mỗi PR một kiểu conflict khác nhau:

| PR | File conflict | Cách resolve | Phát hiện đặc biệt |
|----|---------------|--------------|--------------------|
| #1 | content + 2 data file | Content giữ PR, data lấy main | Sạch, đúng pattern |
| #2 | seo-scores | Data lấy main + sửa `[taxonomies]` | Category để sai cấp, Zola bỏ qua |
| #3 | content + 2 data file | Content **lấy main**, data lấy main | Bản nhánh thêm 3 link hỏng |
| #4 | template + seo-scores | Template **resolve từng vùng**, data lấy main | Bản nhánh có ternary kiểu Python làm vỡ build |

Mỗi dòng là một bài học. PR #1 là trường hợp lý tưởng, áp pattern là xong. Nhưng ba PR còn lại đều có "bẫy" mà nếu resolve mù quáng thì sẽ đẩy lỗi lên production.

## Hai cái bẫy dễ bỏ sót khi resolve

### Internal link hỏng trỏ tới bài chưa tồn tại

Ở PR #3, bản trên nhánh feature "cải tiến" phần kết bài bằng cách thêm vài link nội bộ tới các bài liên quan. Nghe thì tốt, nhưng ba bài đó **chưa hề tồn tại** trong repo. Bộ kiểm tra internal link sẽ resolve mỗi href thành một file trong thư mục build; không thấy file là báo hỏng, exit code khác 0, và CI đỏ ngay.

Bài học: trước khi thêm bất kỳ link nội bộ nào, hãy xác minh trang đích thật sự tồn tại. Một link đẹp trỏ tới hư không còn tệ hơn là không có link. Đây cũng là lý do mình luôn kiểm tra danh sách file trước khi viết phần "bài viết liên quan".

### Cú pháp ternary kiểu Python trong template Tera

Ở PR #4, file template chứa dòng này:

```tera
{% set display_title = section.title if is_section else (page.title if is_page else "Not Found") %}
```

Trông rất tự nhiên với người quen Python. Nhưng Tera — template engine của Zola — **không hỗ trợ** cú pháp `X if Y else Z` trong câu lệnh `set`. Kết quả là build vỡ với thông báo khó hiểu:

```
expected `or`, `and`, `not`, `<=`, `>=`, `<`, `>`, `==`, `!=`, ...
```

Cách viết đúng trong Tera là khối điều kiện nhiều dòng:

```tera
{% if is_section %}
  {% set display_title = section.title %}
{% elif is_page %}
  {% set display_title = page.title %}
{% else %}
  {% set display_title = "Not Found" %}
{% endif %}
```

May mắn là `main` đã có sẵn bản vá đúng. Mình chỉ cần resolve vùng conflict đó theo hướng giữ khối if-elif-else của main, đồng thời vẫn bảo toàn phần layout mới mà nhánh đóng góp.

## Quy trình verify bắt buộc trước khi push

Đây là nguyên tắc mình rút ra: **một PR không có conflict marker vẫn có thể vỡ build**. Vì vậy sau mỗi lần resolve, mình luôn chạy đủ bộ kiểm tra trước khi đẩy lên:

1. **QA check** — quét toàn bộ file, bắt lỗi SEO, category, cấu trúc.
2. **Build site** — xác nhận template parse được, không lỗi cú pháp.
3. **Kiểm tra internal link** — đảm bảo mọi link nội bộ trỏ tới trang có thật.
4. **Quét lại marker** — chắc chắn không còn `<<<<<<<` hay `>>>>>>>` sót lại.

Chỉ khi cả bốn bước xanh, mình mới commit và push. Cách này tốn vài phút nhưng tiết kiệm hàng giờ debug CI đỏ về sau. Bạn có thể tham khảo thêm cách xử lý lỗi pipeline trong bài [troubleshooting GitHub Actions build failure](/posting/github-actions-ci-cd-build-failure-vipzone-token/) và cách chống rate limit khi quét bảo mật trong [CodeQL API rate limit](/posting/codeql-api-rate-limit-giai-phap/).

## Kết luận

Giải quyết merge conflict không phải là việc đoán mò. Khi bạn phân loại file theo nguồn gốc — data tự sinh, nội dung, hay code — và áp một chiến lược cố định cho từng nhóm, việc resolve trở nên deterministic và có thể tự động hóa. Quan trọng nhất là luôn cảnh giác với hai cái bẫy: link nội bộ hỏng và cú pháp template sai, vì cả hai đều lọt qua kiểm tra conflict marker nhưng vẫn làm vỡ build.

**Bước tiếp theo:** nếu bạn muốn hiểu sâu hơn về phân tích code tự động và bảo mật, hãy đọc bài [CodeQL — công cụ phân tích code tự động](/posting/codeql-phan-tich-code-tu-dong-cho-lap-trinh-vien/). Hoặc xem thêm các bài cùng chủ đề tại chuyên mục [Công nghệ](/categories/cong-nghe/) và [tất cả bài viết](/categories/tat-ca/) của blog.

## Tham khảo

- [Git — Basic Branching and Merging](https://git-scm.com/book/en/v2/Git-Branching-Basic-Branching-and-Merging)
- [GitHub Docs — Resolving a merge conflict](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/addressing-merge-conflicts/resolving-a-merge-conflict-on-github)
- [Tera Documentation — Templates](https://keats.github.io/tera/docs/)
