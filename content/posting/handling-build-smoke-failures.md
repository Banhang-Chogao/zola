+++
title = "Cách Fix Build-Smoke Fail: 3 Bài Học Từ Kinh Nghiệm Zola"
date = 2026-06-26
description = "3 bài học từ việc fix build-smoke fail hàng chục lần: log không nói dối, frontmatter là thủ phạm, và quy trình chuẩn để tự fix."
slug = "handling-build-smoke-failures"

[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["zola", "build", "ci-cd", "debug"]
+++

## Mở đầu

Hôm nay vừa rồi, tôi gặp một tình huống quen thuộc: một PR mới với 5 bài viết tuyệt vời, tất cả các check đều xanh, nhưng Zola build fail. Build-smoke lại xuất hiện lỗi, chỉ sau đúng 1 phút. Và đây không phải lần đầu.

Có những lúc như vậy khiến bạn muốn quỳ gối. Nhưng nếu đã trải qua hàng chục lần, bạn sẽ nhận ra: không có gì là random ở đây. Mỗi build-smoke fail đều có nguyên nhân cụ thể, và nó thường nằm trong 3 chỗ mà bạn có thể check trong 10 phút.

Bài viết này chia sẻ 3 bài học từ kinh nghiệm fix build-smoke, cộng với một quy trình chuẩn để bạn có thể tự fix mà không cần chờ đợi.

## Bài Học 1: Đừng Bao Giờ Bỏ Qua Build-Smoke

Nhiều developer khi thấy build-smoke fail thường nghĩ: "Chỉ là smoke test, chắc lỗi nhỏ xíu, merge đi rồi tính."

Đó là sai lầm lớn.

Build-smoke chạy zola build toàn bộ site. Khi nó fail sau 1 phút, có nghĩa là có lỗi syntax nghiêm trọng, không phải warning hay deprecation.

Nếu bạn merge: Site sẽ crash, khách hàng thấy 500 error, phải rollback gấp. Không đáng đổi tiện lợi lúc merge để sau đối mặt hỗn loạn.

## Bài Học 2: Mặc Định Kiểm Tra 3 Thứ Đầu Tiên

95% lỗi build-smoke nằm trong 3 danh mục này:

**Frontmatter (80% cases)**: Thiếu date, title, description. Định dạng date sai. Kiểu dữ liệu sai (ví dụ draft: "true" thay vì draft: true).

**Taxonomy (15% cases)**: Category không tồn tại trong config.toml. Tag có ký tự đặc biệt không được escape. Typo trong category/tag names.

**Assets (5% cases)**: Image path sai. Relative path nhầm lẫn.

Cách check: Mở 5 bài mới, so sánh frontmatter với bài cũ đã hoạt động. Mở config.toml, xác nhận mọi category/tag đều có mặt. Grep tìm tất cả image references.

## Bài Học 3: Log Là Thánh Kinh

Build-smoke log thường rất cụ thể:

```
Error: Failed to render page 'content/posting/example.md'
Caused by: Missing field 'description' in frontmatter
```

Dòng này nói hết tất cả: file nào, lỗi gì, cần thêm gì.

Cách tiếp cận đúng: Copy log lỗi đầu tiên. Đọc kỹ 3-5 dòng xung quanh. Fix trực tiếp file được chỉ ra. Rebuild và confirm.

Đừng đoán mò. Máy tính không nói dối.

## Quy Trình Chuẩn

Nếu gặp tình huống tương tự:

```bash
git checkout pr-branch
zola build 2>&1 | tee build.log
cat build.log | grep -A 5 "Error"
for file in content/posting/*.md; do head -15 $file; done
diff content/posting/working-post.md content/posting/broken-post.md
```

Khi fix: chỉ sửa lỗi build, đừng cải tiến content. Giữ PR sạch.

## Kết Luận

3 nguyên tắc vàng:

1. Build-smoke không fail vô cớ. Luôn có nguyên nhân cụ thể.
2. Log chứa câu trả lời. Đọc kỹ trước hỏi AI.
3. Check 3 thứ đầu tiên sẽ giải quyết 95% vấn đề.

Sự khác biệt giữa developer mất 2 giờ debug và mất 10 phút fix không phải do bổng lộc, mà do quy trình.

Đừng merge khi build-smoke đỏ. Tôi đã học được điều này theo cách khó khăn. Bạn không cần phải thế.
