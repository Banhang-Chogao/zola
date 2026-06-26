+++
title = "Thiết Kế Framework Giải Quyết Merge Conflict Tự Động"
description = "Từ chaos sang order: Tôi thiết kế framework dựa trên CLAUDE.md protocol V10/V12 để auto-resolve 70% conflicts."
date = 2026-06-26
updated = 2026-06-26
slug = "thiet-ke-framework-giai-quyet-merge-conflict"
category = "Công nghệ"
tags = ["CI/CD", "merge-conflict", "automation", "framework", "git"]
series = "merge-conflict-preflight"
extra.series_part = 2
extra.seo_keyword = "merge conflict resolution framework"
extra.thumbnail = "/images/blog/conflict-framework.jpg"
+++

## Từ Chaos Sang Order

Ngày 19 tháng 6, sáng sớm — 06:30 GMT+7. Tôi ngồi xuống với cà phê và một mục tiêu: **không bao giờ babysit PR resolve conflict nữa**.

Điều đầu tiên tôi làm là **không viết code**. Tôi viết **protocol**.

---

## Protocol Giải Quyết Conflict Chuẩn Hóa

Căn cứ vào 7 conflict từ hôm qua, tôi thấy pattern rõ ràng:

**Pattern #1: Generated Data Files**
```json
// data/seo-qa-scores.json
// data/build-dashboard.json
// data/ga-stats.json
```

Những file này được tạo bởi workflow/cron. Chúng không phải manual edits. Khi conflict xảy ra, **luôn lấy version từ `main`** (mới nhất, freshest).

**Pattern #2: Registry/Config Merge**
```json
// registry.json — cần merge cả hai phía
// Không loại bỏ entries từ PR
// Thêm entries từ main
```

**Pattern #3: Changelog Combine**
```
// CHANGELOG.md
// Gộp lại, không throw away entries
```

**Pattern #4: Templates Need Review**
```html
// templates/base.html
// scripts/config.yaml
// Cần inspect cả hai phía manually
```

**Pattern #5: Content Preservation**
```markdown
// content/posting/*.md
// Luôn giữ version từ PR (authorial intent)
```

Tôi ghi vào CLAUDE.md — ra đời **V10 "Dirty PR / merge race protocol"** và **V12 "Semantic Conflict Auto-Fix"**.

---

## Python Engine: ConflictResolver

Dựa vào protocol, tôi code `autofix_conflicts.py`:

```python
class ConflictResolver:
    """
    Phân loại file → apply chiến lược giải quyết
    """
    
    def classify_file(self, filepath: str) -> str:
        """
        Returns: 'generated', 'registry', 'changelog', 
                 'template', 'content', 'unknown'
        """
        if filepath.startswith('data/'):
            return 'generated'  # data/*.json luôn từ main
        
        if 'registry.json' in filepath:
            return 'registry'   # merge cả hai
        
        if 'CHANGELOG' in filepath:
            return 'changelog'  # combine entries
        
        if filepath.startswith('templates/') or \
           filepath.endswith('.html') or \
           filepath.endswith('.css'):
            return 'template'   # manual review
        
        if filepath.startswith('content/'):
            return 'content'    # keep PR version
        
        return 'unknown'
    
    def resolve_generated(self, filepath):
        """Lấy main's version"""
        subprocess.run(['git', 'checkout', '--theirs', filepath])
        subprocess.run(['git', 'add', filepath])
        return True
    
    def resolve_registry(self, filepath):
        """Merge cả hai JSON entries"""
        main_data = load_json_from_main(filepath)
        pr_data = load_json_from_pr(filepath)
        merged = {**main_data, **pr_data}  # union merge
        save_json(filepath, merged)
        subprocess.run(['git', 'add', filepath])
        return True
    
    def resolve_changelog(self, filepath):
        """Combine entries từ cả hai phía"""
        # Extract entries từ <<<<<<, =====, >>>>>>
        # Combine lại, sort by date
        return True
    
    def resolve_manual(self, filepath):
        """Report để manual review"""
        return False
```

---

## Workflow Integration

Nhưng code Python không chạy tự động. Cần CI/CD trigger nó.

Tôi tạo hai GitHub Actions workflow:

**Workflow #1: `preflight.yml` — Kiểm tra mỗi 15 phút**
```yaml
schedule:
  - cron: '*/15 * * * *'  # Mỗi 15 phút

jobs:
  preflight-check:
    steps:
      - name: Test merge with main
        run: |
          git merge --no-commit --no-ff origin/main || true
          # Kiểm tra có conflict không
          if git status | grep -q "both modified"; then
            echo "CONFLICTS_DETECTED=true"
      
      - name: Comment PR with status
        # Báo dev trong PR comment
```

**Workflow #2: `auto-resolve.yml` — Trigger bởi label**
```yaml
on:
  pull_request:
    types: [labeled]

jobs:
  auto-resolve:
    if: github.event.label.name == 'auto-resolve'
    steps:
      - name: Auto-resolve conflicts
        run: |
          python3 scripts/autofix_conflicts.py \
            --auto-resolve --branch ${{ PR_BRANCH }}
      
      - name: Run QA checks
        run: python3 qa_check.py --strict
      
      - name: Push with retry
        run: |
          python3 scripts/push_with_retry.py \
            --branch ${{ PR_BRANCH }} \
            --max-retries 5
```

---

## Push Retry: Vì Network Không Hoàn Hảo

Khi push changes lên GitHub, có thể fail:
- Rate limit exceeded
- Temporary network glitch
- GitHub API overloaded

**Giải pháp:** Exponential backoff retry

```python
class PushRetry:
    def push(self, branch):
        for attempt in range(1, 6):  # 5 attempts
            result = subprocess.run(
                ['git', 'push', 'origin', f'HEAD:{branch}']
            )
            
            if result.returncode == 0:
                return True  # Success!
            
            # Check if error is transient
            if is_transient_error(result.stderr):
                backoff = 2 ** (attempt - 1)  # 2s, 4s, 8s, 16s, 32s
                time.sleep(backoff)
                continue
            else:
                return False  # Permanent error
        
        return False
```

---

## QA Check After Resolution

Giải quyết conflict không đủ. Phải đảm bảo code vẫn build.

`qa_check.py` chạy:
1. ✅ Zola build
2. ✅ Check conflict markers (không thể miss)
3. ✅ Run SEO checks
4. ✅ Run link validation
5. ✅ Check secrets leak

Nếu QA fail, thì push không được. Developer phải fix.

---

## Architecture Diagram

```
Push to PR branch
    ↓
Preflight Workflow (15 min polling)
    ├─ git merge --no-commit origin/main
    ├─ Check conflict markers
    └─ Post comment: "✅ Ready" OR "⚠️ Conflicts"
    
    IF Conflicts Detected:
        Developer adds "auto-resolve" label
            ↓
        Auto-Resolve Workflow triggers
            ├─ autofix_conflicts.py
            │   ├─ Classify each conflicted file
            │   ├─ Apply resolution strategy
            │   └─ Regenerate data files
            ├─ qa_check.py
            │   ├─ Verify no conflicts remain
            │   ├─ Run zola build
            │   └─ Run QA suite
            └─ push_with_retry.py
                ├─ Push with 5 retry attempts
                ├─ Exponential backoff
                └─ Report result
    
    Preflight re-checks → ✅ Ready for merge
```

---

## Benefits of This Framework

✅ **Standardized:** Mỗi conflict giải quyết theo cùng protocol  
✅ **Predictable:** Dev biết exactly sẽ xảy ra gì  
✅ **Reversible:** Mỗi commit có thể revert nếu cần  
✅ **Testable:** Từng step được test trước deploy  
✅ **Observable:** Workflow logs rõ ràng  

---

## Phần Tiếp Theo

[Part 3: The Automation That Saved Us](../automation-that-saved-us) — Hệ thống chạy trên production. Những gì xảy ra?

---

## Tài Liệu Tham Khảo

- [Git Merge Strategies](https://git-scm.com/book/en/v2/Git-Branching-Basic-Branching-and-Merging)
- [GitHub Actions Workflows](https://docs.github.com/en/actions/using-workflows)
- [Exponential Backoff Pattern](https://en.wikipedia.org/wiki/Exponential_backoff)
