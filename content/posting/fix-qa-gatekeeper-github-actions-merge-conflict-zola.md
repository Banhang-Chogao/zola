+++
title = "Fix QA Gatekeeper trong GitHub Actions: bài học từ một nút Countdown bị mất ở footer"
date = 2026-06-22
aliases = ["/fix-qa-gatekeeper-github-actions-merge-conflict-zola/"]
description = "Case study debug GitHub Actions: từ merge conflict, stale branch đến QA Gatekeeper xanh và auto-merge sau 12 phút."
slug = "fix-qa-gatekeeper-github-actions-merge-conflict-zola"

[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["ci cd", "debug", "github actions", "merge conflict", "qa gatekeeper", "regression test", "zola"]
[extra]
thumbnail = "/img/posting/fix-qa-gatekeeper-github-actions-merge-conflict-zola/cover.webp"
seo_keyword = "fix QA Gatekeeper GitHub Actions"
featured = false
+++

Khoảng 2:02 sáng ngày 22/06/2026, tôi ngồi ở The Coffee Bean & Tea Leaf, trước mặt là chiếc MacBook, một ly nước đã vơi dần và một pull request tưởng như chỉ còn “xử lý conflict cho xong”. Nhưng càng đi sâu, tôi càng nhận ra đây không chỉ là một lần sửa lỗi bình thường. Đó là lần đầu tôi tự xử lý một PR bị vướng nhiều lớp: merge conflict, stale branch, conflict marker còn sót, QA Gatekeeper fail, rồi cuối cùng nhìn GitHub Actions chạy hơn 10 phút và tự auto-merge vào `main`.

Cảm giác lúc đó rất khó tả. Không phải vì bug quá lớn, mà vì lần đầu tiên tôi đi trọn một vòng debug bằng local terminal: đọc log, hiểu test đang la gì, sửa đúng nguyên nhân, chạy QA local, push lại và chờ hệ thống xác nhận. Một nút Countdown nhỏ ở footer đã dạy tôi nhiều hơn vài giờ đọc tài liệu CI/CD khô khan.

![MacBook trên bàn cà phê trong buổi debug QA Gatekeeper GitHub Actions lúc khuya](/img/posting/fix-qa-gatekeeper-github-actions-merge-conflict-zola/cover.webp)

*Khoảnh khắc 2:02 sáng: một PR đỏ, một ly nước, và bài học thực tế về CI/CD.*

## Bối cảnh: khi PR không chỉ đơn giản là conflict

Case này bắt đầu từ một PR trên blog tĩnh Zola. Ban đầu, PR có nhiều thay đổi liên quan đến SEO/AdSense cleanup, một số chỉnh sửa nội dung, `.gitignore` cho file Zola binary bị extract, cùng vài thay đổi nhỏ ở footer và contact. Nhìn qua thì đây là dạng PR “dọn dẹp” quen thuộc, nhưng nó đụng vào nhiều file đã thay đổi trên `main`.

GitHub báo trạng thái kiểu `mergeable_state=dirty`, nghĩa là branch không thể merge sạch vào `main`. Auto-merge bị hoãn. Preflight conflict cũng báo branch đang xung đột với base branch. Đây là tín hiệu rõ ràng: không nên cố bấm merge, không nên push linh tinh, mà phải đưa branch về trạng thái cập nhật với `main`.

Quy trình đúng lúc đó là:

```bash
git fetch origin
git checkout <branch-dang-lam>
git merge origin/main
```

Sau đó resolve conflict, kiểm tra marker, chạy QA local rồi mới push. Nghe thì đơn giản, nhưng khi `main` đang chạy nhanh, tình huống stale-base race rất dễ xảy ra: mình vừa resolve xong, `main` lại có commit mới; mình vừa push lại, bot lại báo branch tiếp tục lệch. Nếu không bình tĩnh, rất dễ tưởng hệ thống bị lỗi.

## Preflight xanh không có nghĩa QA đã xanh

Một trong những bài học lớn nhất của lần này là: “No conflicts with base branch” chỉ nói rằng Git có thể merge branch vào `main` ở cấp độ file. Nó không đảm bảo code chạy đúng, test đúng, UI không mất chức năng, hay production an toàn.

Trong case này, sau vài vòng merge/rebase, preflight conflict đã xanh. GitHub không còn báo conflict với base branch. Về mặt Git, branch đã sạch. Nhưng QA Gatekeeper vẫn fail.

Đây là điểm nhiều người dễ nhầm: thấy QA đỏ sau khi resolve conflict thì nghĩ conflict vẫn chưa hết. Thực tế, lỗi lúc này đã chuyển tầng. Nó không còn là lỗi Git nữa, mà là lỗi regression test.

CI/CD có nhiều cổng. Preflight conflict chỉ là một cổng. QA Gatekeeper là cổng khác. Một PR muốn đi vào production an toàn phải qua cả hai.

## Cách đọc log: đừng nhìn cả biển output

Khi GitHub Actions đỏ, log thường rất dài. Nếu nhìn toàn bộ output, mình sẽ thấy hàng trăm dòng chạy test, build, warning, status. Người mới rất dễ bị ngợp và sửa lung tung.

Cách tôi rút ra là: hãy tìm test fail đầu tiên. Đừng đọc từ trên xuống như đọc truyện. Hãy tìm các từ khóa:

```text
FAIL
ERROR
AssertionError
FAILED
```

Trong case này, test quan trọng là test liên quan đến footer Countdown. Nội dung fail nói rõ hệ thống kỳ vọng trong `templates/base.html` phải có đủ ba thứ:

```text
/admin-countdown/
⏱ Countdown
site-footer__author-mgmt
```

Ban đầu, nhìn lỗi có thể tưởng chỉ thiếu link `/admin-countdown/`. Nhưng nếu chỉ thêm link mà thiếu class `site-footer__author-mgmt`, test vẫn fail. Đây là chỗ nhỏ nhưng rất đáng nhớ: regression test không chỉ kiểm tra route, nó kiểm tra đúng entrypoint quản trị trong footer.

## Một nút Countdown nhỏ nhưng là guard cho production

Fix cuối cùng rất nhỏ:

```html
<a class="site-footer__author-mgmt" href="/admin-countdown/">⏱ Countdown</a>
```

Chỉ một dòng HTML, nhưng dòng này có ý nghĩa lớn. Nó là admin entrypoint cho công cụ Countdown. Tính năng Countdown vẫn hoạt động, nhưng nếu nút quản trị ở footer biến mất sau một lần refactor menu/footer, người vận hành sẽ không còn đường vào nhanh để chỉnh. Với blog tĩnh, nhiều công cụ nhỏ kiểu này không có dashboard phức tạp, nên một link quản trị đúng chỗ là rất quan trọng.

Đó cũng là lý do regression test tồn tại. Test không làm khó mình. Test giữ lại những thứ dễ bị con người xóa nhầm.

Sau khi thêm đúng link, bước tiếp theo không phải push ngay, mà là chạy test nhỏ trước:

```bash
python3 -m unittest scripts.test_footer_countdown -v
```

Khi test nhỏ xanh, mới chạy full QA:

```bash
python3 qa_check.py
```

Cách này tiết kiệm thời gian hơn nhiều so với chạy full QA liên tục. Nếu lỗi nằm ở một module nhỏ, hãy chạy đúng test nhỏ trước. Khi test nhỏ xanh, full QA xanh sẽ có xác suất cao hơn.

![Ly matcha ở The Coffee Bean trong lúc chờ GitHub Actions auto merge PR](/img/posting/fix-qa-gatekeeper-github-actions-merge-conflict-zola/coffee-debug.webp)

*Ly nước trên bàn trong lúc chờ GitHub Actions chạy QA và auto-merge PR.*

## Empty commit không sửa được lỗi gốc

Trong quá trình debug CI/CD, đôi khi mình dùng empty commit để retrigger workflow:

```bash
git commit --allow-empty -m "chore: retrigger qa"
```

Lệnh này có ích khi CI bị kẹt, job bị flaky, hoặc cần kích hoạt lại workflow sau khi local đã pass. Nhưng empty commit không phải thuốc chữa bug. Nếu test đang fail vì thiếu class, thiếu link, sai frontmatter hoặc broken link, empty commit chỉ làm hệ thống fail lại thêm một lần.

Trong case này, retrigger QA chỉ có ý nghĩa sau khi lỗi thật đã được sửa. Trước đó, việc quan trọng hơn là đọc log và hiểu test muốn gì.

## Stale-base race: khi main chạy nhanh hơn mình nghĩ

Một khó chịu khác là `main` liên tục có commit mới. Khi mình đang resolve PR, các PR khác hoặc workflow tự động có thể merge vào `main`. Điều đó làm branch của mình lại lệch. Đây là stale-base race.

Dấu hiệu thường gặp là bot báo branch conflict với `main`, auto-merge bị hoãn, hoặc `mergeable_state=dirty`. Cách xử lý không phải đoán, mà là quay về quy trình:

```bash
git fetch origin
git merge origin/main
```

Nếu có conflict, resolve đúng file. Nếu là generated data thì thường nên ưu tiên `main` rồi regenerate theo rule của repo. Nếu là nội dung hoặc template thì phải đọc kỹ, không chọn bừa.

Với blog tĩnh, đặc biệt là repo có nhiều data JSON, template, nội dung Markdown và QA checker, stale-base race rất thường gặp. Mình càng giữ scope nhỏ, khả năng conflict càng thấp.

## Checklist debug CI/CD cho static blog

Sau lần này, tôi rút ra một checklist ngắn:

### 1. Xác định lỗi thuộc tầng nào

Đầu tiên, hãy phân biệt:

* Git conflict
* Build fail
* Unit test fail
* QA content fail
* Broken link
* SEO/frontmatter fail
* Deploy fail

Mỗi tầng có cách sửa khác nhau. Đừng dùng một cách cho mọi lỗi.

### 2. Luôn fetch trước khi xử lý PR

Trước khi sửa branch, nên chạy:

```bash
git fetch origin
git status -sb
```

Việc này giúp mình biết branch có đang lệch `main` không.

### 3. Tìm conflict marker còn sót

Sau khi resolve conflict, chạy:

```bash
grep -RIn -e '^<<<<<<<' -e '^=======$' -e '^>>>>>>>' .
```

Một marker còn sót trong Markdown, HTML hoặc JSON cũng có thể làm QA đỏ.

### 4. Chạy test nhỏ trước

Nếu log chỉ rõ test fail thuộc module nào, chạy test đó trước. Ví dụ:

```bash
python3 -m unittest scripts.test_footer_countdown -v
```

Đừng full QA liên tục nếu lỗi đang nằm trong một test cụ thể.

### 5. Sau cùng mới chạy full QA

Khi test nhỏ xanh:

```bash
python3 qa_check.py
```

Full QA là cổng cuối trước khi push. Với blog tĩnh, QA không chỉ là code, mà còn là link, SEO, frontmatter, static assets và rule production-safe.

### 6. Không sửa lan man

Một PR đang fix bài viết thì đừng sửa template. Một PR đang fix footer thì đừng dọn data. Một PR đang thêm ảnh thì đừng động workflow. Scope càng rộng, conflict càng dễ xảy ra.

## Vì sao một test nhỏ lại đáng giá

Nhiều người nghĩ test chỉ cần cho backend hoặc app lớn. Nhưng với static blog, test còn quan trọng hơn ở những điểm rất đời thường: link quản trị, menu, footer, robots.txt, sitemap, frontmatter, ảnh thumbnail, internal link.

Một nút quản trị Countdown bị mất không làm site sập. Người đọc có thể không thấy lỗi. Nhưng người vận hành sẽ bị mất lối vào tính năng. Nếu không có test, lỗi này có thể nằm im rất lâu.

Regression test giống như một tờ giấy ghi chú cho tương lai: “Đừng xóa cái này nữa, lần trước xóa là đau rồi.”

## Khoảnh khắc auto-merge sau 12 phút

Sau khi local QA xanh, tôi push branch lên GitHub. QA Gatekeeper bắt đầu chạy. Lần này không còn làm gì thêm, không empty commit, không sửa vội. Chỉ chờ.

Khoảng 12 phút sau, PR được auto-merge vào `main`.

Đó là một khoảnh khắc nhỏ nhưng rất đã. Không phải vì tôi vừa làm điều gì quá lớn, mà vì lần đầu tôi thật sự hiểu pipeline đang nói gì. Từ một PR conflict nhiều lớp, tôi đã đi qua từng lớp: Git, preflight, QA, regression test, local terminal, push, auto-merge.

Cảm giác vui mừng khôn siết lúc đó đến từ việc mình không còn chỉ “nhờ tool sửa hộ”, mà đã tự đọc, tự hiểu và tự đưa production về trạng thái xanh.

## Bài học cho solo maker và blogger kỹ thuật

Nếu bạn đang vận hành một blog tĩnh, đừng xem CI/CD là thứ xa xỉ. Một blog nhỏ vẫn có thể có nhiều rule production-safe: không broken link, không lộ file riêng tư, không sai robots.txt, không mất menu, không mất footer admin entrypoint, không sai category, không ảnh chết.

Điều quan trọng không phải là có pipeline phức tạp, mà là pipeline nói rõ điều gì đang sai. Khi test fail, nó nên chỉ ra đúng chỗ. Khi bot hoãn auto-merge, nó nên nói vì sao. Khi QA đỏ, log phải giúp người vận hành sửa đúng nguyên nhân.

Và quan trọng hơn: người vận hành phải học cách đọc log.

## Kết luận

Case “fix QA Gatekeeper GitHub Actions” lần này cho tôi một bài học rất thực tế: conflict chỉ là lớp đầu tiên. Sau khi conflict sạch, QA mới là nơi kiểm tra xem thay đổi có thật sự an toàn cho production không.

Một dòng link Countdown ở footer tưởng nhỏ, nhưng nó là biểu tượng cho cách một hệ thống tốt bảo vệ những chi tiết dễ bị quên. Preflight giúp branch merge được. QA Gatekeeper giúp production sống khỏe. Auto-merge chỉ nên xảy ra khi cả hai cùng xanh.

Nếu có một câu tôi muốn ghi lại sau đêm 2:02 sáng đó, thì đó là: đừng sợ QA đỏ. Hãy đọc đúng test fail đầu tiên, sửa đúng nguyên nhân, chạy local trước, rồi để automation làm phần còn lại.
