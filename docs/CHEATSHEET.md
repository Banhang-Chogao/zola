# Merge Conflict Preflight — Quick Reference

## When You See "⚠️ Merge conflicts detected"

### Option A: Auto-Resolve (Recommended)

```bash
# In GitHub UI:
# 1. Go to PR
# 2. Click "Labels" → add "auto-resolve"
# 3. Wait 1-3 min
# 4. ✅ Done

# Or via CLI:
gh pr edit <PR_NUMBER> --add-label auto-resolve
```

### Option B: Manual Fix (Local)

```bash
git fetch origin main
git merge origin/main

# Auto-resolve safe conflicts
python3 scripts/autofix_conflicts.py --auto-resolve

# Check QA
python3 qa_check.py --strict

# Push
git push

# 👆 Preflight runs automatically and confirms fix
```

### Option C: Resolve Manually (Complex Conflicts)

```bash
git fetch origin main
git merge origin/main

# Find conflicts
git status  # Shows UU files

# Edit each file
vim path/to/conflicted/file.md
# Find <<<<<, =====, >>>>>
# Choose which version to keep
# Remove conflict markers

git add path/to/conflicted/file.md
git commit -m "Resolve conflicts with main"
git push
```

---

## Commands Cheat Sheet

| Task | Command |
|------|---------|
| **Check conflicts locally** | `git merge --no-commit --no-ff origin/main` then `git merge --abort` |
| **View conflicted files** | `git status \| grep UU` |
| **See conflict details** | `git diff --name-only --diff-filter=U` |
| **Auto-resolve** | `python3 scripts/autofix_conflicts.py --auto-resolve` |
| **Test QA locally** | `python3 qa_check.py --strict` |
| **Push with retry** | `python3 scripts/push_with_retry.py --branch <NAME> --max-retries 5` |
| **Abort merge** | `git merge --abort` |
| **Check preflight status** | `gh pr checks <PR_NUMBER>` |
| **View workflow logs** | `gh run view <RUN_ID> --log` |
| **Re-trigger check** | `gh workflow run preflight.yml` |

---

## File Resolution Strategy

### Take Main's Version (Generated Data)
```bash
git checkout --theirs data/seo-qa-scores.json
git add data/seo-qa-scores.json
```

**Files:** `data/*.json`, dashboards, reports, generated content

### Keep PR's Version (Content)
```bash
git checkout --ours content/blog/my-post.md
git add content/blog/my-post.md
```

**Files:** `content/**/*.md`, original PR changes

### Merge Both (Registry)
```bash
# Edit file to keep both versions
vim registry.json
git add registry.json
```

**Files:** `registry.json`, configuration merges

### Manual Review (Templates)
```bash
# Open in editor
vim templates/base.html
# Inspect both <<<<<, =====, >>>>> sections
# Keep the version that makes sense
# Delete conflict markers
git add templates/base.html
```

**Files:** HTML, CSS, templates, code

---

## Preflight Status Codes

| Status | Meaning | Action |
|--------|---------|--------|
| ✅ All checks passed | No conflicts | Ready for review & merge |
| ⚠️ Merge conflicts detected | Conflicts with main | Add `auto-resolve` label or fix manually |
| 🔄 Attempting auto-resolution | Running auto-fix | Wait 1-3 minutes |
| ❌ Auto-resolve failed | Can't fix automatically | Resolve manually (see above) |
| ⚠️ QA checks failed | Tests failed | Fix issue and re-push |

---

## Common Scenarios

### Scenario: "data/seo-qa-scores.json conflicts"

```bash
# Auto-resolve handles this
python3 scripts/autofix_conflicts.py --auto-resolve
# Takes main's version + regenerates
git push
```

### Scenario: "templates/base.html conflicts"

```bash
# Needs manual review
git fetch origin main
git merge origin/main
vim templates/base.html
# Inspect both versions, choose which one to keep
git add templates/base.html
git commit -m "Resolve template conflict"
git push
```

### Scenario: "Package.json lock conflicts"

```bash
# Usually: take main's version
git checkout --theirs package-lock.json
python3 scripts/autofix_conflicts.py --auto-resolve
python3 qa_check.py --strict
git push
```

---

## GitHub Actions Troubleshooting

| Problem | Solution |
|---------|----------|
| Workflow never completes | Check logs: Actions tab → preflight-check |
| Label doesn't trigger auto-resolve | Re-add label after 30 seconds |
| Push still fails after auto-resolve | Workflow retries automatically, check logs |
| QA check fails | Run `python3 qa_check.py --verbose` locally |
| Need to re-run manually | `gh workflow run preflight.yml` |

---

## Tips & Tricks

### ✨ Avoid conflicts in the first place
```bash
# Before starting work
git fetch origin main
git rebase origin/main  # Or merge if rebase not preferred

# During work
git push frequently (don't work 3+ days without sync)
```

### 🚀 Quick PR setup
```bash
git checkout main
git pull origin main
git checkout -b feature/my-feature
# Make changes
git push -u origin feature/my-feature
gh pr create  # Auto-opens PR
```

### 🔍 Inspect conflicts before fixing
```bash
git diff HEAD  # See all changes
git diff --ours   # See only your changes
git diff --theirs # See only main changes
```

### 📊 Monitor PR health
```bash
gh pr checks <PR_NUMBER>  # See all checks
gh pr view <PR_NUMBER>    # Full PR details with comments
```

---

## Full Documentation

See **docs/migration_guide.md** for:
- System architecture
- GitHub Actions setup
- Custom rules & customization
- Performance metrics

See **CLAUDE.md §4** for:
- Vaccine library (V10, V12 conflict resolution)
- Full protocol rules
- Team standards
