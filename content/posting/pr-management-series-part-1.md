+++
title = "PR Management Best Practices: 7 Pull Request Failures Explained"
description = "June 26, 2026 — 7 pull requests failed simultaneously. Learn PR management best practices for crisis handling, conflict resolution, and team scaling."
date = 2026-06-26
slug = "pr-management-part-1-the-day-7-prs-broke"

[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["git", "pr-management", "ci-cd", "devops", "crisis-management"]

[extra]
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
seo_keyword = "PR management best practices"
featured = false
series = "The Art of PR Management"
series_part = 1

[[extra.faq]]
q = "What causes multiple PRs to fail simultaneously?"
a = "Usually merge conflicts, stale bases after concurrent merges, or CI infrastructure issues. The key is detecting root cause, not treating each PR as an island."

[[extra.faq]]
q = "Should we merge PRs with conflicts or rebase?"
a = "Depends on delta risk. For low-risk (docs/config), cherry-pick. For high-risk (templates/schema), resolve conflict manually to preserve intent."

[[extra.faq]]
q = "How do you prevent this from happening again?"
a = "Build a knowledge base of patterns (vaccine library), detect early via preflight checks, and automate conflict resolution for safe cases."
+++

June 26, 2026, 11:47 UTC+7.

I was watching a Sunday afternoon unfold with the calm of someone who thought they'd just check CI one more time before lunch. Then my terminal lit up like a Christmas tree. Seven pull requests. All failing. At the same time.

**This is the story of how PR management best practices saved us from a 4-hour meltdown, and how you can adopt the same system.**

Not the kind of fail where you close the laptop and come back Monday. The kind where you realize you've just stepped into a case study.

<!-- more -->

## PR Management Best Practices: The Chaos Scenario

Let me be clear: this wasn't a cascading failure. This was a collision.

Seven branches, opened independently over the past week, suddenly hitting `main` all at once. Each one had its own reason for failing:

- **#742**: `dirty` state — base had moved, preflight blocking merge
- **#738**: Merge conflict in `changelog.json` — generated file collision
- **#735**: Template conflict in `base.html` + `_footer.scss` — same shared infra touched
- **#734**: Stale base, QA had already passed but branch was now behind `main`
- **#729**: Build error: Tera syntax in series listing (replace wrong params)
- **#726**: JSON schema validation fail in `data/config.json` after rebase
- **#720**: Workflow permission denied on Pages deployment

**Total impact**: Site static + backend both offline. Estimate: 45 minutes to full recovery if done manually. But I didn't go manual.

## The Symptoms: How I Spotted Trouble

The first clue wasn't the CI logs. It was the pattern.

Usually, when PRs fail, they fail one or two at a time. You fix one, redeploy, move on. But when you see **N PRs all hitting new failure modes within the same 10-minute window**, your brain should scream: "This isn't random."

I opened `wip8` (workspace tracker) to snapshot the state:

- **7 PRs open**
- **5 different check failures** (qa-check, preflight, build, deploy)
- **2 workflows pending**, 3 workflows failed
- **main HEAD moved 3 times** in the last 30 minutes

Translation: PRs were being evaluated against a moving target, and each one's base was becoming stale the moment the previous one merged. Couple that with shared file conflicts, and you get a traffic jam.

## The Question I Asked Myself

"Should I fix these one at a time? Or is there a pattern I can exploit?"

That's where most people go wrong. They pick a PR, read the log, fix the file, push, wait for the next run. Repeat. Repeat. Repeat.

That's **reactive mode**. I decided to go **diagnostic mode** instead.

## The Diagnosis: Root Causes, Ranked

Instead of fixing in order, I classified:

**Tier 1 — Blocking (fix these first or everything else fails)**:
- Merge conflicts (#735, #738) — block merge
- Build errors (#729) — block QA and deploy
- Stale base (#734) — blocks merge without rebase

**Tier 2 — QA-related (can fix after tier 1 clears)**:
- Schema validation (#726) — QA fails, but rebasable
- Permission (#720) — workflow-level, may auto-recover

**Tier 3 — State issues (lowest priority)**:
- Dirty state (#742) — preflight fail, but data clean

Classification alone saved 2 hours of trial-and-error. I didn't fix randomly. I fixed **in order of what unblocks the others**.

## The Recovery Strategy: Triage, Not Chaos

**Step 1**: Conflict resolution (safe deltas only)

For #735 (template conflict in shared infra), I had a choice:
- Option A: Take one side, risk losing the other's fix
- Option B: Manual merge, preserve both intents
- Option C: Cherry-pick only the safe parts

I took option B. The diff was small, both sides fixing different sections. 2 minutes to merge, 30 seconds to verify no regression.

For #738 (changelog conflict), it's a generated file. **Rule**: Prefer `main`'s version. Regenerate after merge.

**Step 2**: Build errors (Tera + schema)

#729 had a Tera syntax error in the series listing. Template was using `replace(old=/new=)` when it should be `replace(from=/to=)`. Single-line fix. Test locally first. Then push.

#726: `seo_qa_checker.py` caught a missing field in the frontmatter. Bake this into preflight checks so it never sneaks past next time.

**Step 3**: Stale base handling

#734 needed a rebase. Instead of manual, I used a script: `git fetch origin main && git rebase origin/main && git push --force-with-lease`. Auto-merge re-triggered.

**Step 4**: Preflight + auto-merge

Once conflicts and build errors cleared, auto-merge did the rest. No babysitting needed. Just the confidence to let the system work.

## What Should Have Happened (Prevention)

If I had the power to rewind, here's what I'd change:

1. **Stagger PRs opening** — don't batch-open 7 at once if they touch shared files
2. **Run preflight locally** — before pushing, verify `zola build` passes
3. **Know your safe conflicts** — generated files (`changelog.json`) vs. handwritten (`base.html`). Handle each differently
4. **Automate conflict detection** — a script that runs `git merge --no-commit` and reports conflicts before human intervention
5. **Queue management** — one merge → one deploy → next PR. Don't let 7 try at once

## The Time Breakdown

- **Diagnosis (classification)**: 3 minutes
- **Conflict resolution (manual + generated)**: 8 minutes
- **Build errors (Tera + schema)**: 5 minutes
- **Rebase + force-push**: 4 minutes
- **Auto-merge + deploy**: 12 minutes (CI-time, not active work)

**Active time**: 20 minutes. **Clock time**: 45 minutes (waiting on CI).

## The Takeaway

Crisis isn't random. It's a **pattern collision** — multiple systems hitting the same bottleneck at once. The difference between a 2-hour recovery and a 20-minute recovery isn't luck. It's this:

1. **Classify before fixing**
2. **Understand dependencies** (which PR unblocks the others?)
3. **Automate the safe parts** (conflict resolution, rebase, merge)
4. **Have a knowledge base** to avoid re-diagnosing the same error

The next five parts of this series build exactly that: a framework to prevent, detect, and recover from PR chaos.

**Continue reading**: [Part 2 - The Framework](@/content/posting/pr-management-series-part-2.md) explores the classification system that turns chaos into order. Or jump to [Part 3 - Automation Breakthrough](@/content/posting/pr-management-series-part-3.md) to see how we fixed these PRs.

Learn more from industry leaders: [GitHub's PR best practices guide](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests) and [Atlassian's CI/CD fundamentals](https://www.atlassian.com/continuous-delivery) provide deeper context.

Because July 26 will bring new PRs. The only question is: will you recognize the pattern?
