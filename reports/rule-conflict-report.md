# Rule Conflict Report

**Updated:** 2026-06-17T19:34:37Z
**Found:** 1 conflicts

## Severity breakdown

- **HIGH:** 1

## 1. Auto-merge vs chặn merge thủ công

**Category:** AI Agents  
**Severity:** HIGH  
**Confidence:** 72%

### Rule A
```text
auto_merge: scripts/auto_merge_policy.py, scripts/try_auto_merge.py
```

### Rule B
```text
block_merge: .github/scripts/push_via_pr.sh
```

### Resolution
Làm rõ precedence trong CLAUDE.md; gắn no-auto-merge cho bot report-only.

