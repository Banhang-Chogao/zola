+++
title = "Fix PR conflict Zola blog: auto-healing an toàn vs recreate"
description = "Bài học từ PR #1148: generated JSON conflicts có thể auto-heal an toàn, nhưng content migration phải recreate từ main để tránh mất dữ liệu."
date = 2026-06-28T18:30:00+07:00

[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["GitHub Actions", "Zola", "blog cá nhân", "auto-healing", "merge conflict", "content migration", "QA", "DevOps"]

[extra]
seo_keyword = "fix PR conflict Zola auto-healing"
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
+++

Hôm nay mình gặp một PR đầy conflict: **PR #1148** với hàng loạt file `content/**/*.md` bị conflict. Lúc đầu mình tưởng auto-healing bot sẽ tự xử lý (như nó từng làm với `data/*.json`). Nhưng không — và đó là lý do đúng.

Bài viết này là một postmortem thực tế: tại sao không phải mọi PR conflict đều nên auto-heal, và bài học cho những người làm blog cá nhân chạy trên Zola + GitHub Actions. Đây cũng là lý do hệ thống auto-healing của SEOMONEY phải học cách phân biệt: cái gì có thể tự fix, cái gì phải dừng lại.

## Câu chuyện PR conflict: khi nào auto-healing nên tự sửa?

PR này chứa một content migration lớn — di chuyển bài viết từ nguồn báo chí sang thật sự publish dưới các chuyên mục như [Công nghệ](/categories/cong-nghe/), [Ngân hàng](/categories/ngan-hang/), Khoa học… 

Khoảng hai tuần branch này đợi review. Trong thời gian chờ đó, `main` không đơn giản im lặng. Hệ thống blog chạy liên tục:
- Workflow QA mỗi giờ regenerate `data/seo-qa-scores.json`
- Cron hàng ngày chạy compliance audit
- Editor CMS publish bài mới
- Auto-healing bot update từng section

Kết quả: branch cũ **dần trở nên stale**. `main` đã có những thay đổi mới ở:

```
content/cong-nghe/_index.md  (metadata chuyên mục)
content/ngan-hang/_index.md
content/baochi/...           (bài gốc từ nguồn)
content/khoa-hoc/bang-ma-codon-dna-rna.md  (bài mới publish)
...và nhiều file khác
```

Khi PR cố merge lên `main`, git báo conflict ở **mỗi file này**. Mình nhìn vào log tự hỏi: "Sao auto-healing bot không tự merge cái này giống như nó làm với generated JSON?"

## Vì sao auto-healing bot KHÔNG nên merge bừa?

Đây là câu hỏi then chốt. Hệ thống mình có một vaccine (auto-healing rule) cho **generated JSON conflicts**:

```
data/compliance-score.json
data/qa-404-report.json
data/seo-qa-scores.json
```

Với những file này, rule rất đơn giản: **lấy bản từ `main` rồi regenerate bằng script**.

Lý do nó an toàn: **source of truth là code + content, không phải JSON file**. Nếu conflict ở `seo-qa-scores.json`, mình chỉ cần chạy `python3 scripts/seo_qa_checker.py --all` và dữ liệu tự cập nhật đúng.

Nhưng **content conflict thì khác hẳn**. Source of truth là chính file `.md` đó:

```markdown
# content/cong-nghe/bai-moi.md

+++
title = "Bài mới"
categories = ["Tất cả", "Công nghệ"]
tags = ["GitHub", "WebOps"]
+++

Nội dung bài viết...
```

Khi merge conflict, mình không thể "lấy `main` rồi regenerate" được — không có script nào tạo ra prose của bài viết hay SEO metadata của nó. Nếu auto-fix bừa, mình có thể:

- **Mất nội dung mới:** main đã publish bài mới nhưng branch cũ chưa biết → auto-fix "lấy main" = mất thay đổi của branch.
- **Mất metadata:** frontmatter update (SEO keyword, category, FAQ schema) bị ghi đè.
- **Gây index lỗi:** bài bị mất canonical link, alias, hoặc routing sai.
- **Break homepage:** nếu `_index.md` conflict, trang chuyên mục có thể disappear.

Đó là lý do: **content migration conflict phải resolve thủ công hoặc recreate branch từ main**.

## Generated JSON conflict vs Content conflict

Hãy nhìn sự khác biệt rõ ràng:

### Generated JSON Conflict

```json
// data/qa-404-report.json
{
  "timestamp": "2026-06-28T15:00:00Z",  // <- conflict ở đây (thay đổi mỗi lần chạy)
  "broken_links": [...]
}
```

**Cách xử lý:** take `origin/main` → chạy `qa-404-checker.py` → commit lại.

**Tại sao an toàn:** file này là **output**, KHÔNG phải input. Nó được sinh từ code + content. Merge conflict ở timestamp hoặc entry order không ảnh hưởng.

### Content Conflict

```markdown
// content/cong-nghe/bai-moi.md
# conflict ở đây
+++
title = "Bài mới"
categories = ["Tất cả", "Công nghệ"]
date = 2026-06-27T10:00:00+07:00
+++

Nội dung bài viết...
```

**Cách xử lý:** **KHÔNG auto-fix**. Phải:
1. Kiểm tra PR còn cần không
2. Nếu stale → đóng PR
3. Nếu còn cần → recreate branch từ `main` mới nhất
4. Reapply migration bằng script idempotent
5. Chạy QA + verify production

## Phân biệt: PR conflict Zola auto-healing hay rebuild từ đầu?

Đây là quyết định then chốt. Khi PR conflict, không phải lúc nào cũng nên áp dụng auto-healing. Hãy hỏi 3 câu này trước tiên:

1. **PR này có phải content migration không?** Nếu có → không auto-heal.
2. **Conflict ở generated files hay authored files?** Generated → auto-heal OK; Authored → cần rebuild.
3. **Branch này còn cần không?** Nếu features đã implement khác cách trên main → đóng PR (duplicate).

Với PR #1148, câu trả lời cho 3 câu trên là: Yes (migration) → authored files → still needed. Vậy cách duy nhất là **recreate branch từ main mới nhất**.

## Cách xử lý đúng khi PR conflict nhiều content file

Dưới đây là quy trình mình áp dụng cho PR #1148:

### Bước 1: Kiểm tra PR còn cần không

```bash
git log origin/main --oneline -20 | grep -i "content\|migration"
```

Nếu chức năng đã được implement khác cách trên `main` → đóng PR (duplicate).

### Bước 2: Nếu PR còn cần — Recreate branch từ main

```bash
git fetch origin main
git checkout main
git pull --ff-only origin main
git checkout -b <branch>-recreated

# Reapply migration bằng script hoặc CLI
python3 scripts/migrate_content_to_categories.py --source baochi --dest cong-nghe
```

### Bước 3: Chạy QA đầy đủ

```bash
python3 qa_check.py
python3 scripts/build_references.py
zola build
python3 scripts/check_internal_links.py
python3 qa-404-checker.py
```

### Bước 4: Commit và push (PR mới)

```bash
git add content/
git commit -m "feat(content): migrate posts to proper categories"
git push -u origin <branch>-recreated
```

**Tuyệt đối KHÔNG push -f vào branch cũ.**

## Vaccine mới cần thêm cho hệ thống

Dựa vào kinh nghiệm PR #1148, vaccine tiếp theo trong bộ auto-healing rules cần là:

> **V25 — Content Migration Conflict:** Khi PR chứa nhiều `content/**/*.md` conflicts từ migration, **không auto-merge**. Thay vào đó, script `qa-auto-rule-checker.py` phát hiện pattern:
> - `content/` file conflict ≥ 5 → thêm label `manual-resolve`, comment tới PR: "Đây là content migration. Vui lòng recreate branch từ main mới nhất để tránh mất dữ liệu."
> - Để user quyết định recreate hay đóng PR.

## Bài học cho người làm blog cá nhân

Nếu bạn cũng đang chạy blog trên **Zola + GitHub Actions**, đây là những lesson rút được:

### 1. **Phân biệt "generated" vs "authored"**

- **Generated files** (JSON, report, build output): được sinh từ code → an toàn auto-regenerate.
- **Authored files** (markdown, template, config): được viết tay → cần thận trọng khi merge.

Auto-healing bot phải biết cái nào có thể tự fix, cái nào phải dừng lại.

### 2. **Stale branch là vấn đề thực**

Với blog lớn, feature branch có thể mất relevance nhanh chóng. Luôn check:

```bash
git log main...HEAD --oneline | wc -l
```

Nếu quá 20 commit chênh lệch → branch đang stale, nên recreate từ `main`.

### 3. **Script idempotent là bác sĩ**

Khi migration không thể auto-merge, cách tốt nhất là **dùng script idempotent** (chạy lại N lần cũng ra kết quả như nhau) để reapply.

```python
def migrate_posts(source_dir, dest_dir):
    # Vừa move file, vừa update frontmatter
    # Chạy lại nhiều lần vẫn OK
    ...
```

### 4. **Luôn verify production sau deploy**

Ngay cả PR auto-merge, bạn vẫn cần:

```bash
curl -I https://yourblog.com/new-post/
# HTTP 200 = live
# HTTP 404 = có vấn đề (content không được render)
```

## Checklist xử lý conflict trong Zola blog + GitHub Actions

Dán checklist này vào máy khi gặp conflict lớn:

- [ ] **Kiểm tra loại conflict:**
  - Nếu chỉ `data/*.json` (generated) → lấy `main` rồi regenerate
  - Nếu `content/**/*.md` (authored) → STOP, không merge tay

- [ ] **Cho content conflict:**
  - Kiểm tra PR branch còn cần không (check commit log trên `main`)
  - Nếu stale/duplicate → đóng PR
  - Nếu còn cần → recreate từ `git checkout main && git pull origin main`

- [ ] **Recreate migration:**
  - Tạo branch mới
  - Chạy script migration idempotent
  - Commit kết quả

- [ ] **Chạy QA đầy đủ:**
  ```bash
  python3 qa_check.py
  python3 scripts/build_references.py
  zola build
  python3 scripts/check_internal_links.py
  python3 qa-404-checker.py
  ```

- [ ] **Tạo PR mới (từ branch recreate):**
  - Không force-push vào branch cũ
  - Để CI tự chạy, tự merge (auto-merge policy)

- [ ] **Verify production sau deploy:**
  - Kiểm tra route mới lên HTTP 200
  - Kiểm tra homepage không bị break
  - Kiểm tra internal link không hỏng

## Làm sao để fix PR conflict Zola auto-healing lần tới?

Dưới đây là hướng dẫn cụ thể để phòng tránh tình cảnh PR #1148 lặp lại. Nó không chỉ áp dụng cho SEOMONEY, mà còn cho bất kỳ blog Zola nào chạy trên GitHub Actions:

### Ngăn chặn branch stale

```bash
# Định kỳ (weekly) rebase PR vào main mới nhất
git fetch origin main
git rebase origin/main
git push origin <branch> --force-with-lease

# Hoặc: merge main vào branch (thay vì rebase)
git fetch origin main
git merge origin/main
```

Chiến lược rebase tốt hơn vì nó giữ history sạch, nhưng cần `--force-with-lease` để tránh đè lên remote.

### Script tự động kiểm tra stale

```bash
#!/bin/bash
# Chạy CI trigger nếu branch >20 commit đằng sau main
behind=$(git rev-list --count origin/main..HEAD)
if [ "$behind" -gt 20 ]; then
  echo "⚠️ Branch này $behind commits đằng sau main"
  echo "Vui lòng rebase trước merge"
  exit 1
fi
```

### Thiết lập `auto-merge` đúng cách

Không phải mọi PR đều nên auto-merge ngay. Thay vào đó:
- Auto-merge chỉ cho generated/config PRs (data, workflow, policy)
- Content PRs cần review thủ công (ít nhất xem qua diff)
- Large migration PRs phải wait for maintainer approval

Tham khảo [GitHub auto-merge documentation](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/incorporating-changes-from-a-pull-request/automatically-merging-a-pull-request) để setup đúng.

## Tài liệu tham khảo & đọc thêm

Nếu bạn muốn hiểu sâu hơn về conflict resolution với Zola + GitHub Actions, tôi gợi ý:

- [Zola Documentation — Markdown & Content](https://www.getzola.org/documentation/content/overview/) — hiểu cấu trúc content
- [Git Conflict Resolution Guide](https://git-scm.com/book/en/v2/Git-Branching-Branch-Management) — learn branching strategy
- [GitHub Actions Troubleshooting](https://docs.github.com/en/actions/learn-github-actions/workflow-syntax-for-github-actions) — when CI decisions matter

## Kết luận

Auto-healing bot là công cụ tuyệt vời, nhưng **nó phải biết giới hạn của mình**. Không phải mọi conflict đều xứng đáng được auto-fix.

Bài học từ PR #1148:
- **Generated data** (JSON, reports) → auto-heal an toàn ✅
- **Content migration** (markdown files) → recreate từ main ⚠️
- **Large conflicts** → stop, review, recreate nếu cần
- **Luôn verify production** → không tin CI mà thôi

Nếu bạn là người chạy blog cá nhân với Zola + GitHub Actions, vaccine này sẽ giúp bạn tránh được một số bug tinh quái khi scale content. Và nếu bạn đang xây dựng auto-healing system của riêng mình, hãy nhớ:

> **Sự khác biệt giữa "có thể auto-fix" và "nên auto-fix" là rất lớn.**

Không phải vì bạn CÓ THỂ auto-merge content migration, không có nghĩa bạn NÊN làm vậy. Một chút patience ở lúc merge có thể tiết kiệm hàng giờ debug sau này.

Happy merging! 🚀
