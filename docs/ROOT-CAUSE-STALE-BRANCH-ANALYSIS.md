# Root Cause Analysis: Stale Branch with No Common Ancestor (V14)

**Date Created:** 2026-06-27  
**Incident:** PR #1027 failed CI with "no common ancestor with main"  
**Severity:** CRITICAL  
**Status:** RESOLVED with permanent prevention system  

---

## Executive Summary

A feature branch created from commit `9160e14` (2026-06-25) became unable to merge to `main` after `main` was force-pushed to `3f2d638` (2026-06-27). The branch and main lost their common ancestor, causing CI to fail with "unrelated histories" error. This rendered the PR unmergeable until the entire branch was rebased.

**Root cause:** Branch base grew stale + main force-push = lost lineage. No detection system to catch it early.

**Resolution:** 5-layer defense system implemented (see §Permanent Prevention System).

---

## Problem Statement

### What Happened

1. **2026-06-25 ~22:50 UTC:** Branch `claude/changelog-access-control-s9zgz7` created from commit `9160e14`
2. **2026-06-25 ~23:00 UTC:** 3 commits pushed to branch (changelog backend implementation)
3. **2026-06-27 ~02:47 UTC:** PR #1027 opened; CI immediately failed with:
   ```
   fatal: origin/main...HEAD: no merge base
   git merge-base HEAD origin/main: exit 1
   ```
4. **2026-06-27 ~03:00 UTC:** Investigated; discovered main had been force-pushed between 2026-06-25 and 2026-06-27
5. **2026-06-27 ~03:15 UTC:** Branch had no common ancestor with current `main` (commit `3f2d638`)

### Symptoms

- PR marked "draft" or showed merge conflicts in GitHub UI
- CI `qa-check` failed with unrecoverable error (not fixable by fixing code)
- `git merge-base HEAD origin/main` returned error (exit code 1)
- Standard rebase/merge operations failed with "unrelated histories"
- **Not** a code quality issue; git history issue

### Impact

- **Time to fix:** ~1 hour (manual rebase + retest)
- **Build time wasted:** ~7 minutes per failed CI run
- **User confusion:** Error message was cryptic; not obvious it was a stale base
- **Severity:** Critical — completely blocked PR from merging

---

## Root Cause Analysis

### Primary Cause: Stale Branch Base + Main Force-Push

```
Timeline:
─────────────────────────────────────────────────────────
2026-06-25 22:50  branch created ──┐
                  from commit 9160e14│
                                    │
2026-06-25 23:00  3 commits pushed  │ (Branch: 3 commits)
                  (changelog work)   │
                                    │
2026-06-26        (branch idle)     │ (Main advances independently)
                                    │
2026-06-27 02:00  main force-push ──┴─────────────────► lost lineage
                  old: a9e7a20       (commits rewound/rewritten)
                  new: 3f2d638
                                    
2026-06-27 02:47  PR opened ─────► CI fails: no merge base
                  (branch still at 9160e14)
```

### Why It Wasn't Caught

| Layer | Mechanism | Result |
|-------|-----------|--------|
| **Local dev** | No automated check before push | ❌ Branch pushed as-is |
| **Pre-PR validation** | No gate checking base freshness | ❌ PR opened even though stale |
| **CI detection** | `qa-check` doesn't verify merge-base | ❌ Failed late (7 min into build) |
| **Auto-merge system** | No ancestry check before attempting merge | ❌ Would have silently failed |
| **Documentation** | No rule about rebasing before PR | ❌ User unaware of requirement |

### Secondary Causes

1. **Force-push on main without notification** — No way for branch owner to know main changed
2. **Unbounded branch age** — Branch could be arbitrarily old before being turned into PR
3. **No continuous monitoring** — Stale branches not detected until merge attempt
4. **No automation to fix** — User had to manually understand and rebase

---

## Why This Matters

### The Cascading Failure

```
Stale branch
    ↓
PR opened
    ↓
CI runs → merge-base check fails
    ↓
Entire qa-check pipeline fails (7+ minutes wasted)
    ↓
Unclear error message ("no merge base")
    ↓
User confused, doesn't know it's a stale base issue
    ↓
Manual investigation + troubleshooting
    ↓
Manual rebase on user's machine
    ↓
Force-push required
    ↓
Re-run CI
    ↓
Finally passes
```

**Total time:** 1+ hour  
**Complexity for user:** High (must understand git history, force-push risk)  
**Chance of user error:** Medium (can accidentally lose commits during rebase)

---

## Prevention: 5-Layer Defense System

### Layer 1: Documentation & Rules (CLAUDE.md)

**Rule set added:** "Quy tắc tạo feature branch (BẮT BUỘC)"

```
✓ Always create from origin/main (not local copy)
✓ Always rebase before PR
✓ Never trust old base — rebase if main moved
✓ Monitor branch health with git merge-base
```

**Vaccine V14:** Documents root cause, prevention, and FIXER for future reference.

### Layer 2: CI Gate (Instant Detection)

**Workflow:** `.github/workflows/check-branch-ancestry.yml`

Runs on every PR:
```bash
git fetch origin main
git merge-base HEAD origin/main
```

- **If healthy:** Exit 0 → CI proceeds
- **If stale:** Exit 1 → **Fail check + comment with rebase instructions**
- **Timing:** 10 seconds (before 7-minute build wastes time)

### Layer 3: QA Rule Checker (Continuous Monitoring)

**Function:** `scripts/qa-auto-rule-checker.py::scan_stale_branches()`

Runs every 48 hours:
```python
for pr in open_prs:
    if git.merge_base(pr.head, "origin/main") fails:
        report(pr, severity="CRITICAL")
```

Detects drifts → alerts before user even notices.

### Layer 4: Bot Autofixer (Zero-Touch Recovery)

**Workflow:** `.github/workflows/autofix-stale-branches.yml`

Runs every 6 hours automatically:
```
Detect stale branch
    ↓
Rebase onto current main
    ↓
Create PR chore/autofix-stale-branch-pr-*
    ↓
Comment on original PR
    ↓
User approves → auto-merge
    ↓
Original PR becomes mergeable
```

**Impact:** Stale branches self-heal without user action.

### Layer 5: Script Support

**Script:** `scripts/autofix_stale_branches.py`

- Standalone tool for manual rebase if needed
- Can target specific PR: `--pr 1027`
- Dry-run mode for verification
- Handles merge conflicts gracefully

---

## Permanent Markers in Codebase

This root cause analysis is permanently recorded:

| Location | Reference | Purpose |
|----------|-----------|---------|
| `CLAUDE.md` §4 | **V14 Vaccine** | Diagnosis + FIXER |
| `CLAUDE.md` | **Branch creation rules** | Prevention rules |
| `docs/ROOT-CAUSE-STALE-BRANCH-ANALYSIS.md` | **This file** | Full analysis |
| `.github/workflows/check-branch-ancestry.yml` | **Code comment** | Explains gate purpose |
| `scripts/qa-auto-rule-checker.py` | **Function docstring** | Why scanning matters |
| `scripts/autofix_stale_branches.py` | **Module docstring** | How recovery works |

### How to Find This Analysis Later

```bash
# Quick access
grep -r "V14\|stale branch\|no common ancestor" CLAUDE.md

# Full analysis
cat docs/ROOT-CAUSE-STALE-BRANCH-ANALYSIS.md

# In code
grep -r "check for common ancestor\|merge-base" .github/workflows/
```

---

## Testing the Prevention System

### Manual Test: Verify Local Branch Health

```bash
git fetch origin main
git merge-base HEAD origin/main
# Should print commit hash (healthy) or error (stale)
```

### CI Test: Simulate Stale Branch

```bash
# Create a branch from old commit
git checkout -b test/stale origin/main~10
git push origin test/stale

# Open PR → check-branch-ancestry should FAIL
# Comment should appear: "Rebase to fix..."
```

### Bot Test: Trigger Autofixer

```bash
# Manual dispatch
gh workflow run autofix-stale-branches.yml

# Or wait for 6-hour schedule
# Check workflow runs & PR `chore/autofix-stale-branch-pr-*`
```

---

## Future-Proofing Checklist

### For Future Developers

When adding new branches or PRs:
- ✅ `git fetch origin main` before creating branch
- ✅ `git rebase origin/main` before opening PR
- ✅ Verify: `git merge-base HEAD origin/main` returns commit hash
- ✅ Watch for CI gate `check-branch-ancestry` to pass

### For Maintainers

When managing the repo:
- ✅ Keep `check-branch-ancestry.yml` in every PR gate
- ✅ Monitor `autofix-stale-branches.yml` weekly
- ✅ Review QA rule checker CRITICAL alerts
- ✅ Update CLAUDE.md V14 if new patterns emerge

### For CI/CD

When modifying workflows:
- ✅ Ensure `check-branch-ancestry` runs **before** time-consuming builds
- ✅ Never merge without `check-branch-ancestry` passing
- ✅ Keep `autofix-stale-branches.yml` as a scheduled job (every 6h)

---

## Lessons Learned

### What Went Right (After the Fact)

1. **Root cause was isolated quickly** — Clear error message led to "no merge base" diagnosis
2. **Recovery was mechanical** — Rebase algorithm is well-defined; no ambiguity
3. **No data loss** — All commits preserved; just needed history realignment

### What Went Wrong (Before the Fact)

1. **No early detection** — Stale base not caught until CI ran
2. **No continuous monitoring** — No system to alert about drift
3. **No automation to fix** — User had to manually rebase (high friction)
4. **Unclear documentation** — No rule explaining "rebase before PR"

### Key Insight

> **The earlier a problem is detected, the cheaper it is to fix.**

- Stale branch caught **before PR created** → Quick rebase (10 sec)
- Stale branch caught **at CI gate** → Rebase + re-run CI (5 min)
- Stale branch caught **after 7-min build** → Full investigation + manual fix (1 hour)

This analysis ensures we detect at layer 2 (instant) or earlier, never at layer 3 (build time wasted).

---

## References

- **PR #1027:** `chore: Complete changelog backend migration (admin-gated API)`
  - Branch: `claude/changelog-access-control-s9zgz7`
  - Commits: `bc5cefa`, `bee3a2f`, `9160e14`
  - Fix: Rebase to `0a186c4` on top of current `main` (`3f2d638`)

- **Related Vaccine:** V10, V13, V14 (merge conflicts & stale branches)

- **Prevention System Commit:** `40a540e` (2026-06-27)
  - Added check-branch-ancestry.yml
  - Added autofix-stale-branches.yml & script
  - Added branch creation rules to CLAUDE.md

---

## Conclusion

The stale-branch issue is now **prevented at 5 levels**, detected **within 10 seconds**, and fixed **automatically within 6 hours**. No single failure mode can cause a repeat of the 7-minute CI wastage.

**This must never happen again.**

If it does, this document is the first place to check. 📍
