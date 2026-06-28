+++
title = "Kinh nghiệm refactor homepage Zola: khi code đúng nhưng chưa nên push"
description = "Một case study thực tế khi refactor homepage blog SEOMONEY theo layout editorial: QA pass, scope sạch, nhưng build chưa có exit code 0 nên vẫn phải dừng đúng lúc."
date = 2026-06-28T23:10:00+07:00
aliases = ["/kinh-nghiem-refactor-homepage-zola-khi-code-dung-nhung-chua-nen-push/"]
updated = 2026-06-28T23:10:00+07:00
[taxonomies]
categories = ["Công nghệ"]
tags = ["ci/cd", "homepage", "qa", "refactor", "seo", "webops", "zola"]
[extra]
author = "Duy Nguyen"
featured = true
+++

# Kinh nghiệm refactor homepage Zola: khi code đúng nhưng chưa nên push

Có những buổi làm web không kết thúc bằng câu “đã merge”, mà kết thúc bằng một câu nghe rất kỷ luật:

**Code đang đúng hướng, nhưng chưa đủ điều kiện để push.**

Case này xảy ra khi tôi refactor homepage của SEOMONEY theo hướng editorial, giống một front page của báo hơn là một dashboard nhiều card. Mục tiêu ban đầu khá rõ: chỉ thay layout trang chủ, giữ nguyên trang đọc bài, giữ nguyên Editor cũ, không đụng CMS-V2, không mở rộng scope.

Nghe thì đơn giản. Nhưng khi đi vào thực tế, bài học lớn nhất không nằm ở CSS hay template. Nó nằm ở cách quyết định: **khi nào nên dừng lại dù code có vẻ đã ổn.**

## Bối cảnh: chỉ đổi homepage, không đụng trang đọc bài

Task lần này có scope rất hẹp:

* chỉ đổi homepage `seomoney.org`;
* áp dụng cho desktop và mobile;
* giữ nguyên trang đọc bài viết;
* không đổi article body;
* không đổi TOC;
* không đổi right rail;
* không đổi schema;
* không đổi ad placement trong bài viết;
* không đụng Editor cũ;
* không đụng CMS-V2.

Tôi muốn homepage có cảm giác giống một trang báo editorial hơn: có masthead, nav chuyên mục, bài sticky/editor pick, latest main story, feed chính, right rail, topic sections và các vị trí AdSense được chừa chỗ rõ ràng.

Nói cách khác, đây không phải là redesign toàn site. Đây là **refactor homepage có kiểm soát**.

## Thứ đã làm đúng: scope được giữ sạch

Một điểm đáng mừng là working tree cuối cùng chỉ còn các file homepage:

```text
templates/index.html
sass/site.scss
sass/_homepage-main.scss
```

Đây là dấu hiệu tốt. Với các task UI lớn, nguy hiểm nhất là “tiện tay” sửa lan sang article template, shared layout hoặc CSS toàn cục. Khi scope bắt đầu lan, task nhỏ biến thành PR khó review.

Ở case này, các vùng quan trọng đều được xác nhận không bị chạm:

* article templates không bị redesign;
* `/editor/` cũ không bị đụng;
* CMS-V2 không bị đụng;
* logic trang đọc bài vẫn giữ nguyên.

Đó là tiêu chuẩn đầu tiên của một refactor an toàn: **đổi đúng nơi cần đổi, không đổi nơi không cần đổi.**

## Vấn đề Tera/Zola: đừng quá tin vào `{% break %}`

Một lỗi nhỏ nhưng đáng nhớ là logic chọn bài mới nhất không nên dựa vào `{% break %}` trong template.

Khi cần tránh trùng giữa sticky, featured và latest story, cách an toàn hơn là dùng một biến trạng thái như:

```text
latest_story_found
```

Ý tưởng là:

* nếu sticky và latest trùng nhau, chọn bài tiếp theo;
* nếu featured và latest trùng nhau, chọn bài tiếp theo;
* không để cùng một bài xuất hiện lặp lại trong top fold;
* fallback vẫn đi qua danh sách `all_pages` để tìm bài hợp lệ kế tiếp.

Bài học ở đây rất thực tế: trong static site generator, đặc biệt khi dùng template engine như Tera, logic nên **rõ ràng và dễ đoán**, hơn là thông minh nhưng phụ thuộc vào control flow dễ gây lỗi.

## QA pass không có nghĩa là được push

Sau khi refactor, `qa_check.py` không báo lỗi nghiêm trọng. Kết quả là:

```text
0 errors
warnings only
```

Đây là tín hiệu tốt, nhưng chưa đủ.

Internal link validator lại fail vì một số link cũ trong article pages đã publish từ trước. Điểm quan trọng là: lỗi này **nằm ngoài scope homepage task**. Nếu mở rộng task để sửa luôn link cũ, PR sẽ bắt đầu phình ra và khó review.

Cách xử lý đúng là ghi rõ:

* QA chính không có error;
* internal-link check fail do pre-existing article-page links;
* không sửa link cũ trong task homepage;
* report blocker thay vì âm thầm mở scope.

Đây là một nguyên tắc WebOps quan trọng: **không biến một PR layout thành PR dọn nợ kỹ thuật toàn site.**

## Build timeout: lý do cuối cùng để không push

Điểm quyết định nằm ở `zola build`.

Fresh build không trả về exit code `0` trong bounded window. Không phải build báo fail rõ ràng, nhưng cũng không có kết quả pass thật. Đây là vùng dễ mắc lỗi nhất: thấy log chạy một lúc, thấy có output, rồi tự kết luận “chắc pass”.

Nhưng trong CI/CD, “chắc pass” không tồn tại.

Một build chỉ được tính là pass khi có:

```text
exit code 0
```

Không có exit code thì phải xem là:

```text
build unresolved / timeout
```

Vì vậy quyết định cuối cùng là:

```text
No push
```

Không phải vì code sai. Mà vì **bằng chứng chưa đủ**.

## Vì sao quyết định “không push” lại là quyết định đúng?

Trong vận hành blog tĩnh, nhất là blog đã có production traffic, không push đôi khi là hành động chuyên nghiệp nhất.

Nếu push khi build chưa được xác nhận:

* có thể làm queue CI kẹt;
* có thể tạo PR xanh giả;
* có thể làm deploy fail sau merge;
* có thể lẫn với task khác đang chạy;
* có thể gây conflict khó debug hơn.

Trong case này, còn có một task khác đang xử lý PR World Cup 2026. Nếu homepage WIP bị commit nhầm chung với PR đó, hậu quả sẽ rất mệt: một PR SEO content bỗng chứa cả layout homepage.

Vì vậy, homepage task được dừng lại ở trạng thái:

```text
Code scoped OK
QA acceptable
Build unresolved
No push
```

Đó là trạng thái không hào nhoáng, nhưng sạch.

## Bài học 1: Luôn tách task theo terminal, branch và staged files

Khi có nhiều terminal cùng chạy, điều quan trọng nhất là không để chúng trộn file.

Với case này:

* Terminal homepage chỉ được giữ homepage WIP;
* Terminal World Cup chỉ được stage file SEO/content/generated liên quan;
* không dùng `git add .`;
* không stage untracked directories;
* không commit file layout vào PR content.

Một câu lệnh rất đáng nhớ:

```text
git diff --cached --name-only
```

Trước khi commit, luôn kiểm tra staged set. Không nhìn working tree chung chung. Chỉ staged files mới là thứ sẽ đi vào commit.

## Bài học 2: Generated output không nên được xử lý như source code

Trong quá trình build, có những thư mục như:

```text
public/
.zola-build/
```

Đây là output build, không phải source. Nếu chúng bị lock hoặc stale, không nên vội kết luận code lỗi.

Nhưng cũng không nên đưa chúng vào git.

Nguyên tắc tốt:

* source code thì review kỹ;
* generated JSON thì regenerate bằng script;
* build output thì loại khỏi commit;
* thư mục build bị lock thì dùng output dir khác để verify.

Đây là khác biệt giữa sửa code và xử lý môi trường.

## Bài học 3: Warning không đáng sợ bằng scope creep

Trong một hệ thống blog sống lâu, warning là chuyện bình thường. Điều nguy hiểm hơn là thấy warning rồi sửa lan.

Ví dụ internal-link check báo lỗi từ bài viết cũ. Nếu task hiện tại là homepage layout, ta không nên biến nó thành task sửa toàn bộ internal links.

Cách đúng là:

```text
Report clearly.
Keep scope.
Open separate task if needed.
```

Scope sạch giúp PR dễ review. PR dễ review thì dễ merge. Dễ merge thì production an toàn hơn.

## Bài học 4: UI refactor cần guardrail SEO và AdSense từ đầu

Homepage không chỉ là đẹp. Với một blog kiếm tiền từ SEO và AdSense, homepage còn phải:

* crawlable;
* có internal links thật;
* không mock data;
* không nhồi ad lên đầu trang;
* không tạo layout shift;
* không làm headline bị chìm;
* không làm mobile feed khó đọc.

Layout editorial tốt không phải là nhiều hiệu ứng. Nó là hệ thống phân cấp thông tin rõ:

```text
Masthead
Navigation
Sticky / Editor Pick
Latest Main Story
Main Feed
Right Rail
Topic Sections
Footer
```

Mobile cũng cần thứ tự riêng:

```text
Header
Search
Sticky
Ad
Latest Feed
In-feed Ad
Topic Chips
Featured Blocks
Footer
```

Khi wireframe rõ từ đầu, code ít bị lạc.

## Checklist tôi sẽ dùng lại cho các task homepage sau

Trước khi push một homepage refactor, tôi sẽ kiểm tra:

```text
Scope:
- chỉ homepage files
- không article templates
- không Editor
- không CMS-V2

Logic:
- không duplicate sticky / featured / latest
- không dùng control flow template thiếu ổn định
- fallback chọn bài kế tiếp hợp lệ

SEO:
- link chuyên mục crawlable
- internal links thật
- title/H1 strategy giữ nguyên
- timestamp đầy đủ nếu template có hiển thị

AdSense:
- không đặt ad làm content đầu tiên
- reserve min-height
- không sticky mobile overlay
- không gây CLS

QA:
- qa_check.py không error
- internal link lỗi cũ phải report riêng
- zola build phải có exit code 0

Git:
- không git add .
- kiểm tra git diff --cached --name-only
- không stage output build
- không trộn task khác
```

## Kết luận: làm web nhanh không bằng dừng đúng lúc

Điều tôi thích nhất ở case này không phải là layout đã đẹp hơn. Điều đáng giá hơn là cả quy trình đã dừng đúng chỗ.

Homepage logic đã ổn. Scope đã sạch. Article pages không bị phá. Nhưng build chưa có exit code `0`, nên chưa push.

Đây là kiểu kỷ luật nhỏ nhưng cứu production rất nhiều lần.

Làm WebOps không chỉ là biết sửa. Đôi khi là biết nói:

**“Chưa đủ bằng chứng để merge.”**

Và đó là một kỹ năng rất đáng học.

## Liên kết bên ngoài được sử dụng trong bài viết

Không sử dụng liên kết bên ngoài trong bài viết này. Nội dung được viết lại từ trải nghiệm vận hành nội bộ và log terminal đã được biên tập, không trích dẫn tài liệu bên ngoài.

## Liên kết nội bộ liên quan

* [SEOMONEY](https://seomoney.org/)
* [Branding Guideline](https://seomoney.org/branding-guideline/)
* [S-DNA](https://seomoney.org/tools/s-dna/)
* [Font](https://seomoney.org/font/)

## Tuyên bố bản quyền

Bài viết này là nội dung gốc của SEOMONEY, được biên tập lại từ trải nghiệm vận hành blog thực tế. Không sao chép nguyên văn log terminal, không công khai thông tin nhạy cảm, không chia sẻ token, secret, đường dẫn riêng tư hoặc dữ liệu nội bộ không cần thiết.

## Ghi chú biên tập

Case study này nên được publish sau khi task homepage chính thức hoàn tất hoặc được ghi rõ là “bài học từ một phiên refactor chưa merge”. Nếu sau này build pass và PR homepage được merge, có thể cập nhật thêm phần hậu kiểm production.
