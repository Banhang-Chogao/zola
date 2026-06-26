+++
title = "PR Management Best Practices: The Day 7 PRs Failed at Once"
description = "When 7 PRs fail simultaneously: how systematic classification turns chaos into fixes."
date = 2026-06-30
updated = 2026-06-30
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["ci cd", "github actions", "merge conflict", "devops", "monorepo", "pull request", "pr management"]
[extra]
toc = true
series = "The Art of PR Management"
series_part = 1
seo_keyword = "PR management best practices"
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
featured = false
+++

## Executive Summary (For Managers)

Following **PR management best practices**, I resolved a crisis of 7 concurrent PR failures by applying systematic classification instead of reactive fixes.

**Problem**: 7 concurrent PRs failed simultaneously with different root causes.
**Time to resolve**: 45 minutes with systematic classification (vs. 2+ hours with reactive fixes).
**Key lesson**: Categorizing failures takes 10 minutes and saves hours of blind debugging.
**ROI**: Prevented 3+ hours of wasted engineering time on this incident alone.

---

## The Moment Everything Went Red

It was 3:47 PM on a Wednesday. I'd been reviewing a routine content update when my GitHub notifications exploded. Not one PR. Seven of them. All failing CI/CD. All with different error messages.

My first instinct: **panic**. My second: **coffee**. My third: **read the logs**.

This is the story of what happened when parallel development collided head-on with our shared infrastructure, how I stayed calm, and the systematic approach that turned a chaotic situation into actionable insights.

## The Monorepo Reality

Let me set the scene. This isn't a microservices setup with cleanly separated repositories. This is a single Zola blog serving ~40 content categories, ~12 template macros, a complex taxonomy system, dynamic series registration, and a nested asset pipeline. One `.toml` configuration file controls everything. One set of templates touches every page.

When multiple PRs land on overlapping infrastructure, merge conflicts aren't just likely — they're inevitable.

**The Setup:**
- **7 PRs** in flight: #934–#943 (a few merged already, but these seven were stuck)
- **Team size:** Solo engineer responsible for triage and merge strategy
- **Services touched:** content/categories, templates/base.html, sass/layout.scss, data/auto-index.json
- **Build system:** Zola 0.18 + GitHub Actions

**The immediate problem:** Not a single error message. Not a single root cause. Seven different failure modes, each one silent and opaque until I dug into the logs.

## Initial Classification: Bucket Before Fixing

Here's what I learned the hard way: when multiple PRs fail, **the instinct to "fix" them quickly is wrong**. The instinct to **categorize them first** is right.

I spent the first 10 minutes reading logs, not editing code. Not committing. Just categorizing.

### The Seven PRs and Their Failure Types

| PR | Status | Error Message (shortened) | Bucket |
|----|---------|-----------------------|--------|
| #934 | Cancelled | `build-smoke` timed out after 45 min | Infrastructure failure |
| #935 | ❌ Failed | `Failed to render 'faq.html'` — Tera syntax error | Build/syntax failure |
| #936 | ❌ Failed | Merge conflict in `base.html` | Merge conflict |
| #938 | ❌ Failed | `static-checks` — vaccine detector flag | Stale base (not code) |
| #939 | ⏳ Waiting | No checks started | CI trigger issue |
| #942 | ✅ Merged | Already merged 2h ago | No action needed |
| #943 | ✅ Passing | All checks green | Ready to merge |

Four buckets emerged:

1. **Infrastructure failure** (#934): A stuck runner, nothing to code-fix
2. **Real syntax error** (#935): Zola build actually broken
3. **Merge conflicts** (#936, #938): Stale branches, not bad code
4. **CI trigger issues** (#939, #942, #943): Already done or skipped

**This classification took 8 minutes and saved 3 hours of blind debugging.**

## Why This Happened (Root Cause Preview)

The underlying reason all seven PRs landed at the same time:

1. **Feature freeze ended**: 5 simultaneous content/template updates
2. **Base drift**: Some PRs had been open for 3 days while `main` received 12 commits
3. **Shared file contention**: Four PRs touched `base.html` (the foundation of every page)
4. **CI timing**: One workflow ran on a slow runner, triggering a cascade of timeouts

None of this was obvious without looking at logs. The PR titles gave no hint.

## The Panic vs. The Process

Here's what separates a crisis from a controllable situation:

**The panic version:**
- Open the first red PR
- Read the error message
- Make a guess at what's wrong
- Commit a fix
- Push
- Wait 5 minutes for CI
- Still broken
- Repeat across 7 PRs
- *~2 hours later:* PRs still red, base drifting further, new conflicts spawning

**The process version:**
- List all red PRs
- Read logs for each one
- Classify into buckets
- Fix highest priority bucket first
- Rebase downstream PRs
- Merge in safe order
- Monitor once
- *~45 minutes later:* all merged, deployed, done

The difference isn't intelligence. It's methodology.

## Merge Dependency Graph

This is where it got tricky. These PRs weren't independent. Some depended on others being merged first.

```
#943 (fully green, clean)
  ↓ [MERGE FIRST — establish clean baseline]
#936 (touches base.html)
  ↓ [MERGE SECOND — other PRs rebase here]
#934, #935, #938, #939 (all depend on ↑)
  ↓ [REBASE all, then MERGE sequentially]
```

If I merged #935 before #936, the new `base.html` from #936 would conflict with #935's syntax fix. If I rebased too early, I'd have to rebase again after #936 lands. **The order mattered.**

## What I Didn't Do (And Why It Matters)

- ❌ **Force-push** to override conflicts
- ❌ **Merge to a branch and test there** (adds extra commits)
- ❌ **Touch code I didn't understand** (just to make CI pass)
- ❌ **Blame contributors** (it was parallelism, not negligence)
- ❌ **Auto-merge without reading logs** (the dashboard would hide real issues)

Each of these shortcuts would have cost 2–4 hours of cleanup later.

## The Turning Point

At about the 25-minute mark, after I'd classified all seven PRs and understood the dependency graph, something shifted. The situation went from "7 crises" to "4 sequential tasks + 1 decision."

That shift happened because I'd stopped trying to fix and started trying to understand.

---

## PR Management Best Practices: Key Takeaways From Part 1

1. **Bucket before fixing**: When multiple PRs fail, categorize them first. Is it infrastructure, syntax, merge, or state?
2. **Read logs, don't guess**: Each error message tells a story. The error message is the diagnosis.
3. **Merge order matters**: In a monorepo with shared files, the order you merge affects all downstream PRs.
4. **Don't panic—process**: Panic = reactive. Process = intentional.

See also: [GitHub PR best practices](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request) · [Zola documentation](https://www.getzola.org/documentation/)

## What to Read Next

👉 **[Part 2: Building the Conflict Resolution Framework](/pr-crisis-part-2-framework/)**

In Part 2, I dive into the CLAUDE.md protocol that prevents this crisis from happening again: how to classify conflicts into three categories and resolve each one safely using automation.

---

## Appendix: Tools I Used

- **GitHub UI**: Cancel/re-run workflow
- **Git CLI**: `git rebase`, `git merge`, `git diff`
- **Python**: QA checker scripts for validation
- **Bash**: Retry loops for flaky push operations

None of these are exotic. The magic wasn't in the tools—it was in the order and the understanding.
