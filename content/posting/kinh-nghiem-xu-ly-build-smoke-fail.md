+++
title = "Cách Fix Build-Smoke Fail: 3 Bài Học Từ Kinh Nghiệm Zola"
date = 2026-06-26
description = "3 bài học từ việc fix build-smoke fail hàng chục lần: log không nói dối, frontmatter là thủ phạm, và quy trình chuẩn để tự fix."
slug = "kinh-nghiem-xu-ly-build-smoke-fail"

[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["zola", "build", "ci-cd", "debug"]

[extra]
seo_keyword = "build-smoke fail zola fix"
featured = false
+++

## Mở đầu

Hôm nay vừa rồi, tôi gặp một tình huống quen thuộc: một PR mới với 5 bài viết tuyệt vời, tất cả các check đều xanh, nhưng Zola build fail — **build-smoke lại xuất hiện lỗi** — chỉ sau đúng 1 phút. Và đây không phải lần đầu.

Có những lúc như vậy khiến bạn muốn quỳ gối. Nhưng nếu đã trải qua hàng chục lần (và tôi đã trải qua), bạn sẽ nhận ra: **không có gì là random ở đây**. Mỗi **build-smoke fail** đều có nguyên nhân cụ thể, và nó thường nằm trong 3 chỗ mà bạn có thể check trong 10 phút.

Bài viết này chia sẻ 3 bài học từ kinh nghiệm fix Zola build-smoke fail, cộng với một **quy trình chuẩn** để bạn có thể tự fix mà không cần chờ đợi hay nhờ giúp đỡ.

---

## Bài Học #1: Cách Fix Build-Smoke Fail — Log Là Chìa Khóa

Nhiều developer khi nhìn thấy **build-smoke fail** thường nghĩ: *"Chỉ là smoke test, chắc lỗi nhỏ xíu, merge đi rồi tính. Lỡ gì thì sửa sau."*

Đó là **sai lầm lớn**.

Build-smoke không phải một test nhỏ hay vui. Nó chạy **`zola build`** — tức là **xây dựng toàn bộ site từ đầu đến cuối**. Khi nó fail sau 1 phút, điều đó có nghĩa là có **lỗi syntax nghiêm trọng** ở đâu đó, không phải warning hay deprecation.

Nếu bạn merge PR này:
- Site sẽ crash tràn lan
- Khách hàng sẽ thấy **500 error** thay vì nội dung
- Bạn sẽ phải rollback gấp
- Mọi người sẽ tức giận

Không đáng đổi chút tiện lợi lúc merge để sau này đối mặt với hỗn loạn. **Luôn luôn fix build-smoke trước khi merge.**

---

## Bài Học #2: Fix Build-Smoke Fail — 3 Điểm Kiểm Tra Bắt Buộc

Từ kinh nghiệm fix **hàng chục build-smoke fail**, tôi nhận ra pattern: 95% lỗi nằm trong 3 danh mục này.

### 1. **Frontmatter** (80% cases)

Đây là thủ phạm chính. Zola yêu cầu frontmatter **chính xác** — thứ tự, định dạng, kiểu dữ liệu đều quan trọng.

Những lỗi thường gặp:
- **Thiếu trường bắt buộc**: `date`, `title`, `description` không có → FAIL
- **Định dạng date sai**: Zola chỉ chấp nhận `YYYY-MM-DD`, không cho phép quote trong một số config:
  ```yaml
  date: 2026-06-26          # ✅ Đúng
  date: "2026-06-26"        # ❌ Có thể sai (tuỳ config)
  ```
- **Kiểu dữ liệu sai**: `draft: "true"` thay vì `draft: true`

**Cách check**: Mở 5 bài mới trong PR, copy-paste frontmatter so sánh với bài cũ đã hoạt động tốt.

### 2. **Taxonomy** (15% cases)

Category và tag phải được **định nghĩa sẵn** trong `config.toml`, hoặc có thể bị reject.

Vấn đề thường gặp:
- **Category không tồn tại** trong config → FAIL
- **Tag có ký tự đặc biệt** không được escape, ví dụ `tag: "C++"` thay vì `tag: "C++"` (nếu cần)
- **Taxonomies bị typo**: `categor` thay vì `category`

**Cách check**: Mở `config.toml`, tìm section `[taxonomy]` và xác nhận mọi category/tag trong PR đều có mặt.

### 3. **Assets** (5% cases)

Đôi khi bài viết tham chiếu tới image hoặc file không tồn tại.

Vấn đề thường gặp:
- **Image path sai**: `/static/images/missing.png` nhưng file lại ở `/static/images/missing-2026.png`
- **Relative path nhầm**: `images/photo.jpg` thay vì `/images/photo.jpg`

**Cách check**: Grep tìm `![` hoặc `](` trong bài mới, xác nhận mỗi file tồn tại.

---

## Bài Học #3: Log Là Thánh Kinh, Đừng Đoán Mò

Tôi từng gặp developers ngồi đoán lỗi build-smoke 30 phút, trong khi **log đã nói rõ lỗi ở dòng nào**.

Build-smoke log thường rất cụ thể:
```
Error: Failed to render page 'content/posting/pr-management-series-part-3.md'
Caused by: Missing field 'description' in frontmatter
```

Dòng này **nói hết tất cả**: file nào, lỗi gì, cần thêm gì.

**Cách tiếp cận đúng:**
1. Copy log lỗi đầu tiên (thường là lỗi root cause)
2. Đọc kỹ 3-5 dòng xung quanh nó
3. Trực tiếp fix file được chỉ ra
4. Rebuild và confirm

Đừng tốn thời gian vào trò đoán. Máy tính không nói dối.

---

## Quy Trình Fix Build-Smoke Fail: Hướng Dẫn Zola Chi Tiết

Nếu bạn gặp tình huống tương tự, hãy làm đúng thứ tự này (tham khảo thêm [hướng dẫn Zola build](https://www.getzola.org/documentation/getting-started/installation/)):

```bash
# Step 1: Checkout PR và build local
git checkout pr-969
zola build 2>&1 | tee build.log

# Step 2: Parse lỗi đầu tiên
cat build.log | grep -A 5 "Error"

# Step 3: Kiểm tra frontmatter của tất cả bài mới
for file in content/posting/pr-management-series-*.md; do
    echo "=== $file ==="
    head -20 $file  # In 20 dòng đầu (frontmatter)
done

# Step 4: So sánh với bài hoạt động tốt
diff content/posting/existing-post.md content/posting/new-post.md

# Step 5: Fix file và rebuild
# Chỉnh sửa file → zola build → lặp lại nếu còn lỗi

# Step 6: Commit fix (nếu lỗi do nội dung PR)
git add content/posting/
git commit -m "fix: correct frontmatter for PR #969 blog posts"
git push -u origin <branch-name>
```

**Mẹo quan trọng**: Khi fix, **chỉ sửa lỗi build**, đừng cải tiến content hoặc cosmetic. Giữ PR sạch.

---

## Kết Luận

3 nguyên tắc vàng mà tôi sử dụng mỗi lần gặp build-smoke fail:

1. **Build-smoke không bao giờ fail vô cớ** — luôn có nguyên nhân cụ thể (frontmatter, taxonomy, hoặc assets)
2. **Log chứa câu trả lời** — đọc kỹ trước khi hỏi AI hoặc đồng nghiệp
3. **Tự tin check 3 thứ đầu tiên** — frontmatter → taxonomy → assets — sẽ giải quyết 95% vấn đề

Sự khác biệt giữa developer mất 2 giờ debug với developer mất 10 phút fix không phải do bổng lộc — mà do **quy trình**. Một quy trình rõ ràng, kiểm tra theo thứ tự, và tin tưởng log.

**Đừng merge khi build-smoke đỏ.** Tôi đã học được điều này theo cách khó khăn. Bạn không cần phải thế.

---

*Liên quan: Tìm hiểu thêm về [Pull Request và quy trình cộng tác GitHub](/pull-request-quy-trinh-cong-tac-github/) và [Deploy Zola tự động với GitHub Actions](/tu-dong-deploy-zola-github-actions/) để tránh các lỗi này từ lần đầu tiên.*
