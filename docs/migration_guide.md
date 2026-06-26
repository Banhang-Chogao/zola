# Merge Conflict Preflight — Migration Guide

## Overview

The Merge Conflict Preflight system automates merge conflict detection and resolution using a protocol-based approach. It catches conflicts **before merge**, auto-resolves common patterns, and blocks merges until conflicts are resolved.

## For Developers

### One-Command Fix

When a PR has merge conflicts, add the `auto-resolve` label and the system handles it:

```bash
# In GitHub UI: Add label "auto-resolve" to the PR
# Or via CLI:
gh pr edit <PR_NUMBER> --add-label auto-resolve
```

The workflow will:
1. Detect conflicts with `main`
2. Auto-resolve safe conflicts (data files, registry files)
3. Regenerate any generated data
4. Run QA checks
5. Push fixes and remove the label

### Manual Resolution

If you need to fix conflicts locally:

```bash
# Fetch and merge main
git fetch origin main
git merge origin/main

# Auto-resolve conflicts
python3 scripts/autofix_conflicts.py --auto-resolve

# Run QA checks
python3 qa_check.py --strict

# Push the fixed branch
git push origin HEAD:$(git rev-parse --abbrev-ref HEAD)
```

### Understanding Conflict Resolution Strategy

The system uses **CLAUDE.md V10/V12 protocol**:

| File Type | Strategy | Example |
|-----------|----------|---------|
| Generated data | Take main's version | `data/seo-qa-scores.json`, `data/reports-*.json` |
| Registry files | Merge both sides | `registry.json`, configuration merges |
| Changelog | Combine versions | `CHANGELOG.md` entries from both sides |
| Templates/CSS | Preserve intent | Manual review needed |
| Content | Do not modify | Content files kept from original PR |

### Conflict Detection

Every PR is checked automatically:
- **Every 15 minutes** (scheduled check)
- **On push** (immediate check)
- **Manual trigger** with `workflow_dispatch`

The Preflight check:
1. Tests merge with latest `main`
2. Reports conflicts in PR comment
3. Blocks merge if conflicts exist (unless `auto-resolve` label)
4. Runs QA checks on clean merge

## System Architecture

### Files

```
.github/workflows/
├── preflight.yml              # Main preflight detection workflow
└── auto-resolve.yml           # Label-triggered auto-resolution

scripts/
├── autofix_conflicts.py       # Intelligent conflict resolver
├── push_with_retry.py         # Push with exponential backoff
└── qa_check.py               # Comprehensive QA validation
```

### Workflow: Manual Resolution

```
Developer Push
    ↓
Preflight Check (15min, on-push)
    ↓
    Conflict? → Yes → Preflight Comment
                      ↓
                   "Add auto-resolve label"
                      ↓
                   Auto-Resolve Workflow
                      ↓
                      autofix_conflicts.py
                      ↓
                      qa_check.py
                      ↓
                      push_with_retry.py
                      ↓
                   Remove Label
                      ↓
                   Re-run Preflight
                      ↓
                   ✅ Merge Ready
    ↓
    Conflict? → No → Run QA Checks
                     ↓
                     ✅ Merge Ready
```

## GitHub Actions Setup

### Permissions Required

The workflows need these GitHub permissions:

```yaml
permissions:
  contents: write        # Git push access
  pull-requests: write   # Update PR comments
  issues: write          # Close/comment on issues
```

### Branch Protection Rules

Recommended branch protection for `main`:

```
Require status checks to pass before merging:
- preflight-check (required)
- qa-check (required)
- zola build (required)

Require branches to be up to date before merging: Yes
Require code review before merging: 1+ approvers
```

## Team Adoption Steps

### Phase 1: Deployment (Week 1)

1. **Copy workflows** to `.github/workflows/`
2. **Copy scripts** to `scripts/`
3. **Update branch protection** rules for `main`
4. **Test on development branch** (don't merge to main yet)

```bash
git checkout -b test/preflight-integration
git push origin test/preflight-integration
# Create PR and test
```

### Phase 2: Documentation (Week 1-2)

1. Add to team wiki: **When conflicts happen → add `auto-resolve` label**
2. Create Slack message explaining preflight
3. Link to CHEATSHEET.md in PR template

### Phase 3: Enforcement (Week 2-3)

1. Enable required status checks in branch protection
2. Merge preflight branch to `main`
3. Monitor first 5-10 PRs with preflight active

### Phase 4: Optimization (Ongoing)

1. Review conflict patterns weekly
2. Update `autofix_conflicts.py` classification for new file types
3. Document new vaccine patterns in CLAUDE.md

## Troubleshooting

### "Auto-resolve failed" message

**Cause:** Conflict involves file types that can't be auto-resolved (templates, content)

**Solution:**
```bash
git fetch origin main
git merge origin/main
# Manually resolve conflicts marked as "manual"
git add <resolved-files>
git commit -m "Resolve conflicts with main"
git push origin HEAD
```

### Push fails after auto-resolve

**Cause:** Network error or rate limit during push

**Solution:** The workflow retries automatically (up to 5 times). If it continues to fail:

```bash
# Manual push with retry
python3 scripts/push_with_retry.py --branch <BRANCH_NAME> --max-retries 5
```

### QA check fails after auto-resolve

**Cause:** Auto-resolved conflicts introduced validation error

**Solution:**
```bash
# Check what failed
python3 qa_check.py --verbose

# Fix the issue locally
# Then push again - preflight will retry
git push origin HEAD
```

### Preflight check never completes

**Cause:** Stuck workflow or webhook lag

**Solution:**
1. Check workflow logs: GitHub Actions → preflight-check
2. Manually trigger: `gh workflow run preflight.yml -f pr_number=<N>`
3. Force sync: `git fetch origin && git push origin HEAD:$(git rev-parse --abbrev-ref HEAD)`

## Performance Impact

### CI Time

- **Preflight check:** ~30 seconds (per 15-min poll)
- **Auto-resolve workflow:** ~2-3 minutes (if triggered)
- **QA checks:** ~3-5 minutes
- **Total:** Conflicts resolved in 5-10 minutes vs. 45+ minutes manual

### Cost

- **Workflows:** ~0.1 minutes/PR (negligible GitHub Actions cost)
- **Storage:** <1MB for workflow logs and data
- **API calls:** ~2-3 calls per PR check

## Customization

### Add New Conflict Resolution Rules

Edit `scripts/autofix_conflicts.py`:

```python
# Add to conflict classification
if 'my-file' in filepath:
    return 'custom_type'

# Add resolver method
def resolve_custom_type(self, filepath: str) -> bool:
    # Custom logic here
    return True
```

### Change Check Frequency

Edit `.github/workflows/preflight.yml`:

```yaml
schedule:
  - cron: '*/5 * * * *'  # Every 5 minutes instead of 15
```

### Add Custom QA Checks

Edit `scripts/qa_check.py`:

```python
def check_my_validation(self) -> bool:
    """Check something specific."""
    return self.run_check('My Check', ['python3', 'my_check.py'])
```

Then call it in `run_all_checks()`:

```python
def run_all_checks(self) -> bool:
    # ... existing checks ...
    self.check_my_validation()
```

## See Also

- **CHEATSHEET.md** — Quick reference for commands
- **CLAUDE.md** — Full system rules and vaccine library (V10, V12)
- **Workflow logs** — GitHub Actions → preflight-check
