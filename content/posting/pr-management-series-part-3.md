+++
title = "PR Automation & Conflict Resolution: Cherry-Pick & Retry"
description = "How automated conflict resolution, cherry-pick strategies, and exponential backoff turned manual PR fixes into a self-healing system."
date = 2026-06-26
slug = "pr-management-part-3-automation-cherry-pick"

[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["git", "automation", "ci-cd", "conflict-resolution", "devops"]

[extra]
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
seo_keyword = "PR automation conflict resolution"
featured = false
series = "The Art of PR Management"
series_part = 3

[[extra.faq]]
q = "When should I cherry-pick vs. merge a PR?"
a = "Cherry-pick when: low-risk delta (docs/config), need specific commits, branch is toxic. Merge when: feature-complete, clean history, safe to rebase."

[[extra.faq]]
q = "How do you handle rate limits on retries?"
a = "Exponential backoff: 2s → 4s → 8s → 16s. Jitter (random offset) prevents thundering herd. Max 3-5 retries before escalate."

[[extra.faq]]
q = "Can you really auto-merge without human review?"
a = "Yes, if: CI passes all required checks, no merge conflicts, no secrets detected, branch matches approved whitelist. Otherwise, escalate to review queue."
+++

Part 1 showed the crisis. Part 2 showed the classification system. Part 3 is where we stop calling it "recovery" and start calling it **"self-healing."**

The difference between manual recovery and PR automation is the difference between firefighting and fire prevention. That's what this article explores: practical PR automation and conflict resolution techniques.

<!-- more -->

## PR Automation & Conflict Resolution: Three Core Strategies

When #735 hit (template conflict in shared infra), my first instinct was to manually merge and push. But I stopped myself and thought: *Can I teach the system to do this?*

That's when I implemented three parallel strategies:

### Strategy 1: Safe Conflict Resolution (Deterministic)

Some conflicts are 100% safe to auto-resolve. Generated files are the primary example.

```python
# Example: changelog.json conflict
if file_path.endswith('changelog.json'):
    git_checkout('main', file_path)  # Prefer main's version
    regenerate(file_path)            # Rebuild from source
    verify(file_path)                # Validate JSON schema
    return "auto-resolved"
```

**Files that are always safe to auto-resolve**:
- `changelog.json` — always regenerate from git log
- `data/related.json` — always rebuild via semantic scoring
- `data/seo-qa-scores.json` — always recalculate per-article
- `.lock` files — always prefer main's pinned versions

**Cost**: 30 seconds to auto-resolve + regenerate.

**Manual cost**: 10–15 minutes of thinking + testing.

### Strategy 2: Rebase on Stale Base (Automated with Verification)

When #734 had a stale base, the fix was mechanical:

```bash
git fetch origin main
git rebase origin/main
git push --force-with-lease
```

Risks:
- Force-push can overwrite in-flight merges
- Rebase can fail if there are real conflicts (not just base staleness)

How to minimize:
- Use `--force-with-lease` (safer than `--force`)
- Only rebase if: branch has no merge conflicts already
- Re-run QA after rebase
- If rebase fails → manual review

**Cost**: 2–3 minutes automated + CI re-run.

### Strategy 3: Build Failure Auto-Fix (Pattern-Matched)

When #729 failed on Tera syntax, the fix was in our Vaccine library:

```python
# V8: Series registration + Tera syntax error detection
if error_message.contains('Failed to render') and error_message.contains("Filter call 'sort' failed"):
    # Known issue: sort() on field missing from some articles in series
    apply_vaccine_v8_fixer()  # Known good fix for this pattern
    verify_build()
    return "vaccine_applied"
```

The key: We'd seen this exact error 3 times before. This was our 4th. By the 4th occurrence, we'd documented the fixer and automated it.

**Cost**: 20 seconds to detect + apply + verify.

**Cost of re-diagnosing**: 15 minutes every time.

## The Exponential Backoff Pattern

Not every auto-fix works on the first try. Network issues, race conditions, API timeouts—these happen.

The answer isn't to retry immediately (which can cause thundering herd). It's exponential backoff:

```python
max_retries = 5
delay = 1  # start with 1 second

for attempt in range(max_retries):
    try:
        result = attempt_merge_or_fix()
        if result.success:
            return result
    except TemporaryError as e:
        if attempt < max_retries - 1:
            sleep(delay + random(0, 1))  # Add jitter
            delay *= 2  # Exponential: 1 → 2 → 4 → 8 → 16
        else:
            escalate_to_human(e)
```

This handles:
- Network hiccups (retried automatically)
- Rate limits (backed off gracefully)
- Transient API failures (eventual consistency)

But **not**: Logic errors, permission issues, or intentional failures.

## The Auto-Merge Gate (Gatekeeper Pattern)

The scariest part of automation is: **when do you trust it enough to merge?**

Our answer: Never blindly. Always gate.

```python
def can_auto_merge(pr):
    # Required checks must ALL pass
    if not pr.qa_check == "pass":
        return False  # User review required
    
    # No merge conflicts
    if pr.mergeable == False:
        return False
    
    # Secret scanning passed
    if pr.secrets_detected > 0:
        return False
    
    # Branch is from approved list
    if pr.branch not in APPROVED_BRANCH_PATTERNS:
        return False
    
    # Author is automation, not human
    if pr.author not in ["github-actions[bot]", "claude-bot"]:
        return False
    
    # If all checks pass: auto-merge
    return True
```

The gatekeeper is **permissive for automation, conservative for humans**. Automation PRs auto-merge when CI passes. Human PRs wait for explicit approval.

Why? Because if automation is wrong, we catch it in QA. If a human is wrong, it's in production before we notice.

## Real Numbers from Part 1

Let's quantify what automation saved us:

| Task | Manual | Automated |
|------|--------|-----------|
| Detect conflict pattern | 3 min | Instant |
| Resolve generated file | 10 min | 30 sec |
| Rebase stale PR | 5 min | 3 min |
| Apply vaccine (build fix) | 15 min | 20 sec |
| Run QA verification | 5 min | 2 min |
| **Total per PR** | **38 min** | **5.8 min** |
| **7 PRs sequentially** | **4h 26m** | **40m** |

The automation didn't cut 1 hour. It cut **3 hours 46 minutes**.

## The Dark Side: When Automation Breaks

Automation is only good when it's **correct**. When it's wrong, it's **catastrophically wrong**.

Examples of autofix failure:
- **V7 incident**: Bot tried to fix unknown error, misdiagnosed, created worse problem
- **V5 incident**: Exponential backoff didn't account for GitHub Pages rate limits; retry storm made it worse
- **V12 incident**: Semantic conflict auto-fixer didn't account for hidden CSS dependencies; UI broke silently

How we handle this:

1. **Logging**: Every auto-fix logs decisions, not just results
2. **Rollback**: If auto-fix fails after retry, it reverts and escalates
3. **Monitoring**: Dashboard shows auto-fix success rate per vaccine
4. **Escalation**: Unknown errors go to human review, never auto-fix blind

## The Setup We Use

This automation lives in three places:

**1. GitHub Actions** (`autofix-conflicts.yml`, `vaccine-autofixer.yml`)
- Runs on PR events or scheduled
- Detects safe conflicts, regenerates generated files
- Creates PR if fix needed, escalates if unsafe

**2. Python Scripts** (`autofix_conflicts.py`, `vaccine_autofixer.py`)
- Core logic for conflict detection
- Vaccine library matching
- Logging and state tracking

**3. Pre-commit Hooks** (local, before push)
- Catch obvious errors before they hit CI
- Save network round-trips
- Fail fast locally, not in production

## The Next Frontier

Automation handles the patterns we've seen. But what about the patterns we *haven't* seen yet?

Read [Part 4 - The Knowledge Base](@/content/posting/pr-management-series-part-4.md): How we build a **machine learning foundation** to predict PR failures before they happen.

Further learning: [Git cherry-pick documentation](https://git-scm.com/docs/git-cherry-pick) and [Exponential backoff strategy](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/) provide additional technical depth for retry logic.
