# Rule Conflict Report

**Updated:** 2026-06-17T17:25:12Z
**Found:** 5 conflicts

## Severity breakdown

- **HIGH:** 4
- **CRITICAL:** 1

## 1. Rule mâu thuẫn trong CLAUDE.md: claude_cancelled_classification

**Category:** CLAUDE.md  
**Severity:** HIGH  
**Confidence:** 92%

### Rule A
```text
ard.py` |
| **Prevention rule** | Không classify GitHub Actions `cancelled` là `failed`. Concurrency cancellation = non-critical trừ khi **mọi** deploy run mới nhất
```

### Rule B
```text
dashboard.py` |
| **Prevention rule** | Không classify GitHub Actions `cancelled` là `failed`. Concurrency cancellation = non-critical trừ khi **mọi** deploy run mới nhất
```

### Resolution
GitHub conclusion cancelled ≠ failure; dashboard dùng status_normalized.

## 2. Bot sửa link vs bot khôi phục link

**Category:** AI Agents  
**Severity:** HIGH  
**Confidence:** 72%

### Rule A
```text
fix_links: scripts/.venv-fd/lib/python3.14/site-packages/pip/_internal/locations/base.py, scripts/.venv-fd/lib/python3.14/site-packages/pip/_internal/metadata/importlib/_envs.py, scripts/autofix_conflicts.py, scripts/check_internal_links.py
```

### Rule B
```text
restore_links: scripts/qa-auto-rule-checker.py
```

### Resolution
Làm rõ precedence trong CLAUDE.md; gắn no-auto-merge cho bot report-only.

## 3. Auto-merge vs chặn merge thủ công

**Category:** AI Agents  
**Severity:** HIGH  
**Confidence:** 72%

### Rule A
```text
auto_merge: scripts/autofix_conflicts.py, scripts/fetch_merge_report.py, scripts/performance_qa_checker.py, scripts/qa-auto-rule-checker.py
```

### Rule B
```text
block_merge: scripts/autofix_conflicts.py, scripts/performance_qa_checker.py, scripts/qa-auto-rule-checker.py, scripts/try_auto_merge.py
```

### Resolution
Làm rõ precedence trong CLAUDE.md; gắn no-auto-merge cho bot report-only.

## 4. Nhiều workflow deploy trên push main

**Category:** GitHub Workflows  
**Severity:** HIGH  
**Confidence:** 70%

### Rule A
```text
deploy.yml (Build and deploy Zola site to GitHub Pages); qa.yml (QA Gatekeeper)
```

### Rule B
```text
Chỉ một workflow nên deploy production (deploy.yml)
```

### Resolution
Gộp deploy logic hoặc tắt deploy trùng trên các workflow phụ.

## 5. robots.txt Disallow / xung đột với meta index

**Category:** SEO Rules  
**Severity:** CRITICAL  
**Confidence:** 98%

### Rule A
```text
robots.txt: Disallow /
```

### Rule B
```text
base.html: index, follow
```

### Resolution
Sửa robots.txt Allow / và khai báo Sitemap.

