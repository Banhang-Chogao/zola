+++
title = "PR Management Framework: Triage & Conflict Resolution Strategy"
description = "How a living document becomes the blueprint for PR triage, conflict classification, and automated recovery when things break."
date = 2026-06-26
slug = "pr-management-part-2-framework-claude-doctrine"

[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["git", "pr-management", "framework", "documentation", "devops"]

[extra]
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
seo_keyword = "PR management framework"
featured = false
series = "The Art of PR Management"
series_part = 2

[[extra.faq]]
q = "What's the difference between merge conflict and semantic conflict?"
a = "Merge conflict: Git can't auto-combine lines. Semantic: logic is wrong even if Git merges cleanly. Both need handling, but tools only catch the first."

[[extra.faq]]
q = "Why classify PRs before fixing?"
a = "Because fixing tier-1 blockers unblocks tier-2 and tier-3. Fix randomly and you'll fix tier-3 items twice while tier-1 still blocks deployment."

[[extra.faq]]
q = "Should every conflict resolution go in a framework?"
a = "No. Only patterns that repeat 2+ times. Single incident → learning log. Recurring pattern → vaccine library. This prevents over-documentation."
+++

After the chaos of Part 1, I realized something: **A good PR management framework isn't built after the crisis. It's built because of the crisis.**

The document that saved Part 1 from turning into a 4-hour meltdown exists in our codebase. It's called `CLAUDE.md`. It's not a tutorial. It's a **living doctrine** — a rulebook that evolves every time we hit a new edge case. This PR management framework is what separates reactive teams from proactive ones.

<!-- more -->

## What Is a PR Management Framework?

A framework is the bridge between "what should happen" and "what actually happens when everything breaks."

Most teams don't have this. They have:
- A PR template (5 fields, usually ignored)
- A GitHub ruleset (branch protection, require approvals)
- Prayers

We have something different: a classified system that says: *Here's what PR failure looks like. Here's how to detect it. Here's how to fix it. Here's how to prevent it next time.*

## The Doctrine: Five Tiers of PR Problems

When Part 1 hit, I wasn't improvising. I was executing tiers I'd already documented:

**Tier 1: Blocking conflicts**
- Merge conflict markers in files that can't auto-resolve
- Non-fast-forward (branch is behind main)
- Secret leaks or security violations

**Tier 2: Build failures**
- Syntax errors (Tera templates, YAML config, Python)
- Missing dependencies or imports
- Schema validation failures

**Tier 3: QA failures**
- Internal link checks fail (404 in content)
- SEO metrics below threshold
- Vaccine detectors (recurring issue patterns)

**Tier 4: State issues**
- Preflight checks fail (dirty working tree, untracked files)
- Auto-merge blocked by labels or branch rules
- Deploy pending or queued

**Tier 5: Deployment issues**
- Infrastructure rate limits (GitHub Pages API quota)
- Environment variable misconfigs
- Backend ↔ static site sync issues

The moment I saw 7 failed PRs, **I didn't panic. I sorted them into tiers.** Tier 1 gets fixed first, or nothing else moves.

## Classification in Action

From Part 1, here's how it looked:

```
#742 (dirty state) — Tier 4
  └─ Action: preflight re-check or rebase
  └─ Blocks: auto-merge
  └─ Wait for: tier 1-3 clear

#738 (changelog conflict) — Tier 1
  └─ Action: prefer main's version, regenerate
  └─ Blocks: merge → deploy
  └─ Fix: NOW

#735 (template conflict) — Tier 1
  └─ Action: manual merge (both sides safe)
  └─ Blocks: merge → build → deploy
  └─ Fix: NOW

#734 (stale base) — Tier 1
  └─ Action: rebase on main
  └─ Blocks: merge
  └─ Fix: NOW after #735-#738

#729 (Tera syntax) — Tier 2
  └─ Action: fix template, test build locally
  └─ Blocks: build → deploy
  └─ Fix: AFTER tier 1 resolves

#726 (schema validation) — Tier 2
  └─ Action: add missing field or fix schema
  └─ Blocks: QA → auto-merge
  └─ Fix: AFTER tier 1

#720 (workflow permission) — Tier 4
  └─ Action: escalate or wait for retry
  └─ Blocks: deploy
  └─ Wait for: others clear
```

The fix priority: `#738 → #735 → #734 → #729 → #726 → #742 → #720`

**That's the framework: detect, classify, sequence.**

## The Vaccine Library: Patterns We've Seen Before

Here's where it gets powerful. Every pattern we've recovered from is documented as a **Vaccine** — a numbered rule in `CLAUDE.md` §4.

**V1**: HuggingFace API 401 on semantic scoring
**V2**: Slack webhook input validation failure
**V3**: GitHub Actions can't create PRs (permissions)
**V4**: Auto-fixer inserts `loading="lazy"` into PR comments (wrong scope)
**V5**: Pages API rate limit on concurrent deploy retries
**V6**: Bot data refresh conflicts on regenerated JSON
**V7**: Workflow remediation tries to fix unknown issues (creates loop)

...and so on, up to V32.

When I hit #729 (Tera syntax), it matched **V8** (Series registration + Tera syntax edge case). Did I re-diagnose? No. Did I re-debug? No. I grabbed the **known fixer** for V8 and applied it.

**Cost: 2 minutes instead of 20.**

## Why This Matters for PR Management

Without this framework, Part 1 would have looked like:
1. See #742 fail → fix it → wait for CI
2. See #738 fail → fix it → wait for CI
3. ... repeat 7 times in sequence
4. **Total time: 2–3 hours**

With the framework:
1. Classify all 7 into tiers
2. Fix tier 1 in **dependency order** (conflicts first, then stale bases, then rebuilds)
3. Tier 2 in parallel with tier 1 (non-blocking)
4. Tier 3+ on auto-merge
5. **Total time: 45 minutes (20 min active work + 25 min CI)**

The framework doesn't prevent crises. It **compresses the recovery window by 75%**.

## How to Build Your Own Framework

If you don't have a `CLAUDE.md` equivalent yet, start here:

**Step 1: Document your last 5 crises**
- What failed? When? Why?
- How long to recover? What did you actually do?
- Could it happen again?

**Step 2: Classify the patterns**
- Single incident → Learning log
- Recurring (2+ times) → Vaccine library
- System-wide rule → Doctrine

**Step 3: Automate detection**
- Preflight check: Can I even merge?
- Schema validator: Will the build pass?
- Pattern detector: Is this a known issue?

**Step 4: Document the fixer**
- If detected, apply this fix
- Test it locally first
- Include verification steps

**Step 5: Iterate**
- Each crisis becomes a new vaccine or refinement to tiers
- Each vaccine prevents the next incident
- The framework becomes predictive, not just reactive

## The Cost of Not Having a Framework

Teams without a classified system treat every PR failure as a mystery. They:
- Spend 2–3x longer on recovery
- Fix the same issue 3+ times before realizing it's a pattern
- Have no institutional memory (new team member = starting over)
- Can't scale (10 PRs = chaos; 100 PRs = broken pipeline)

Teams with a framework:
- Scale linearly (add automation, not complexity)
- Recover predictably (not heroically)
- Build knowledge (vaccines prevent future issues)
- Sleep at night (because the system self-heals)

## The Next Step

The PR management framework alone isn't enough. You also need **automation** to execute it. That's where [Part 3 - Automation Breakthrough](@/content/posting/pr-management-series-part-3.md) comes in: how we actually *implement* this doctrine in code, turning classification into action.

Learn more: [Kubernetes merge strategies](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/declarative-config/merge-patch/) and [GitHub Flow guide](https://guides.github.com/introduction/flow/) provide additional context for pull request workflows.

Because a rulebook in a README does nothing. A rulebook that **runs automatically** changes everything.
