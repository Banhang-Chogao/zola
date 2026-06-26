+++
title = "PR Knowledge Base: Pattern Recognition & Auto-Logging"
description = "Building institutional memory: how auto-logging turns every incident into data, and data into predictive rules."
date = 2026-06-26
slug = "pr-management-part-4-knowledge-base"

[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["git", "devops", "knowledge-management", "pattern-recognition", "machine-learning"]

[extra]
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
seo_keyword = "PR knowledge base"
featured = false
series = "The Art of PR Management"
series_part = 4

[[extra.faq]]
q = "How do you turn incidents into lessons?"
a = "Auto-log every failure: timestamp, error message, PR metadata, attempted fix, result. Query patterns monthly. When 2+ incidents match, create a vaccine."

[[extra.faq]]
q = "What should a PR knowledge base contain?"
a = "Classification rules (tiers), detector patterns (symptoms), fixer code (solutions), test cases (verification), and prevention rules (future prevention)."

[[extra.faq]]
q = "Can you predict PR failures before merge?"
a = "Partially. You can detect high-risk patterns (large diffs + shared files + low test coverage). Prevention is better than cure."
+++

By Part 3, we had automation. But automation alone is reactive—it fixes known problems.

What we needed was something that gets *smarter* with every crisis. That's the **PR knowledge base** — the system that learns from every incident and prevents repeats.

<!-- more -->

<!-- more -->

## Building Your PR Knowledge Base: Three Layers

### Layer 1: Raw Incident Logs

Every failed PR, every build error, every deployment issue—logged.

```json
{
  "timestamp": "2026-06-26T11:47:00Z",
  "pr_number": 735,
  "branch": "feat/template-refactor",
  "author": "alice",
  "failure_type": "merge_conflict",
  "failure_file": "templates/base.html",
  "failure_message": "<<<<<<< HEAD",
  "attempted_fix": "manual_merge",
  "fix_result": "success",
  "time_to_fix_minutes": 2,
  "vaccine_applied": "V12_semantic_conflict_fixer"
}
```

We collect these automatically from GitHub Actions logs, git output, and QA checks.

**Storage**: `data/incident-log.jsonl` (append-only, never delete).

### Layer 2: Pattern Aggregation

Raw logs are noise. Aggregation finds the signal.

```python
# Count failures by type over 30 days
failure_counts = aggregate_incidents(days=30)
# Result:
# {
#   "merge_conflict": 14,
#   "build_error": 23,
#   "rate_limit": 7,
#   "stale_base": 9,
#   ...
# }
```

From this, we identify:
- Most common failure (build errors: 23 in 30 days)
- Rarest failures (worth documenting but not automating)
- Trends (are conflicts increasing? Why?)

**Storage**: `data/failure-dashboard.json` (refreshed daily).

### Layer 3: Actionable Vaccines

When a pattern emerges (same error 2+ times), we document it as a **Vaccine**.

```
#### V32 — Series Sort Crash

Symptom:
  zola build fails with:
  "Failed to render 'section.html'"
  "Filter call 'sort' failed: attribute 'extra.series_part' does not reference a field"

Root Cause:
  Macro sorts posts by series_part, but 1 article in series lacks series_part field.
  Tera sort() requires ALL items to have the attribute or it crashes the whole build.

Detector:
  Scan templates for `sort(attribute=...)` patterns.
  Verify ALL articles in that series have that field defined.
  Flag if missing.

Fixer (Python):
  1. Find template using broken sort()
  2. Wrap in filter: `filter(attribute="field_name")`
  3. Test zola build locally
  4. Commit template fix + set series_part=0 on intro articles

Prevention:
  Pre-commit hook: before push, scan all series articles for missing series_part.
  Fail push if found.

Cost:
  Manual diagnosis: 15 minutes
  Automated fix + test: 3 minutes
  First detection: 10 minutes
  Next 10 detections: 20 seconds each (lookup + apply fixer)
```

This vaccine is now **deterministic**. When we see the error, we don't think. We look it up and apply V32.

## Why Knowledge Bases Win

Compare two scenarios:

**Scenario A (No Knowledge Base)**
- Hit error X
- Spend 20 minutes diagnosing
- Apply random fix
- Hope it works
- Error X happens again (6 months later)
- Repeat diagnosis from scratch

**Scenario B (With Knowledge Base)**
- Hit error X
- Database knows it's V8
- Look up V8 fixer (3 second search)
- Apply known-good solution (2 minutes)
- Error X happens again (6 months later)
- Same 2-minute fix

Over a year with 10 similar errors:
- Scenario A: 20 min × 10 = **200 minutes**
- Scenario B: (20 min first time) + (2 min × 9) = **38 minutes**

**Savings: 162 minutes per error type per year.**

Scale to 20 error types? That's 52+ hours per year of saved debugging.

## Building Your Knowledge Base

**Step 1: Standardize Logging**

Every PR failure must capture:
- What failed (file, error message, stack trace)
- When it failed (timestamp, which commit)
- How long to recover (time-to-fix)
- What was the fix (if known)
- Did the fix work? (verification)

**Step 2: Monthly Pattern Review**

Once a month (e.g., first Friday):
- Query logs for patterns (same error 2+ times)
- Classify by severity (critical, important, informational)
- Check if already in vaccine library
- If new pattern → create vaccine

**Step 3: Automate Detection**

Don't wait for monthly review. Build detectors that run on every failure:

```python
def detect_and_log(error_message):
    for vaccine in VACCINE_LIBRARY:
        if vaccine.detector(error_message):
            return vaccine.id  # V8, V12, etc.
    return "UNKNOWN"  # No match; add to escalation queue
```

**Step 4: Close the Loop**

If `detect_and_log()` returns UNKNOWN repeatedly, create a new vaccine:

```python
# After 3 UNKNOWN errors matching same pattern:
new_vaccine = Vaccine(
    id="V33",
    name="<descriptive name>",
    detector=pattern_you_observed,
    fixer=solution_that_worked,
    test_case=error_message_you_saw
)
```

## The Dashboard

A knowledge base is only useful if people can query it.

We built a simple dashboard at `/tools/pr-knowledge/`:

```
Vaccine Library (32 registered)
├─ V1–V7: Workflow/CI issues
├─ V8–V15: Build/Syntax errors
├─ V16–V22: Merge/Conflict issues
├─ V23–V28: Deployment issues
├─ V29–V32: Runtime issues

Incident Trends (30 days)
├─ Total incidents: 143
├─ Auto-resolved: 94 (66%)
├─ Manual escalation: 49 (34%)
├─ Avg time-to-fix: 12 min (was 45 min 6 months ago)

Top Recurring Patterns
├─ Build errors (23) — V8, V14
├─ Merge conflicts (14) — V12, V18
├─ Rate limits (7) — V5, V16
```

This dashboard makes three things visible:
1. **What's our biggest problem?** (Build errors)
2. **Are we improving?** (Avg time-to-fix down 62%)
3. **What's not in the knowledge base yet?** (High escalation rate = gaps)

## The Prediction Frontier

Right now, our PR knowledge base is **reactive**: We fix known issues faster.

But what if we could **predict** which PRs would fail before they merge?

Signals we could watch:
- Diff size (>500 lines = riskier)
- Files touched (touching shared infra = riskier)
- Branch age (>1 week stale = riskier)
- Test coverage (diff not covered = riskier)
- Author history (first-timer = riskier)

Combine these into a **risk score** on every PR:

```
PR #742: MEDIUM risk (65/100)
├─ Diff size: 180 lines (low)
├─ Shared files: base.html (high)
├─ Branch age: 3 days (low)
├─ Test coverage: 40% (high)
└─ Recommendation: Run extra QA before merge
```

This is the frontier of PR management—not just fixing failures, but **preventing them before they happen**.

Read [Part 5 - Rules & Metrics](@/content/posting/pr-management-series-part-5.md) for the actionable framework.

Learn more: [OWASP's risk rating methodology](https://owasp.org/www-community/OWASP_Risk_Rating_Methodology) and [Code review best practices](https://google.github.io/eng-practices/review/) provide additional context for risk assessment.
