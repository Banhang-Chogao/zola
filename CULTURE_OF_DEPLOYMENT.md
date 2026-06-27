# Culture of Deployment — SEOMONEY

> Public-safe runbook. Anyone (user, contributor, agent) may read this file.
> It defines **how SEOMONEY ships**: deploy philosophy, QA culture, severity model,
> auto-healing, and where agent memory lives (public vs private).
>
> SEOMONEY is a Zola static-first blog deployed to GitHub Pages at `seomoney.org`.
> Companion docs: [`CLAUDE.md`](CLAUDE.md) (agent runbook + experience library),
> [`docs/OPERATIONS.md`](docs/OPERATIONS.md) (ZERO_BARRIER auto-merge workflow).

---

## 1. Deployment Philosophy

```text
Bug found → Fix it → Learn from it → Auto-healing
```

Every meaningful build/deploy bug becomes a permanent improvement to the system.
We do not "fix and forget". We fix, we learn, and we teach the pipeline to heal
itself next time.

The QA pipeline runs as:

```text
Detect → Classify → Heal → Build → Learn → Deploy
```

- **Detect** — find the problem early (preflight, fast checks).
- **Classify** — assign a severity (P0/P1/P2/P3). Not every failure is equal.
- **Heal** — try known safe auto-fixes before failing anyone.
- **Build** — `zola build` is the source of truth for "does the site compile".
- **Learn** — record the lesson (public-safe → `CLAUDE.md`; tactical → private memory).
- **Deploy** — ship to production when it is safe.

---

## 2. Important Deployment Culture Rule

For **every meaningful build/deploy bug**:

1. **Bug found.**
2. **Fix it properly** (root cause, not a band-aid).
3. **Learn from it.**
4. Save a **public-safe, reusable lesson** into [`CLAUDE.md`](CLAUDE.md).
5. Save **private/tactical/sensitive** detail into `CLAUDE_PRIVATE.md` (local, gitignored).
6. Convert the lesson into an **auto-healing hint** when it is safe to automate.
7. On future deploy/build failures, the system should:
   - check **public rules** in `CLAUDE.md` first,
   - then **private local memory** (`CLAUDE_PRIVATE.md`) if it exists,
   - **match** known failure patterns,
   - **apply** safe auto-fixes if available,
   - **rerun** QA / `zola build` **before** failing CI.

This is **mandatory SEOMONEY deployment culture**, not optional documentation.

**Important guardrails:**

- `CLAUDE_PRIVATE.md` is **optional in CI** — it must never be committed.
- **CI must not depend on private local files.** A clean checkout must pass.
- Public auto-healing may only use **committed, safe, public** rules/scripts.
- Local Claude/OpenCode agents **may** use `CLAUDE_PRIVATE.md` when available.
- **Never print private memory contents in CI logs.**

---

## 3. QA Culture

> QA is **not** here to prove a build is wrong. QA exists to make **deploy safer**.

QA is the **deployment immune system**, not the deploy police. Its job is to:

- **Block** only what would actually break production.
- **Report** everything else.
- **Auto-heal** known, safe problems.
- **Backlog** quality/SEO improvements for the Editor/Insights tooling.

A QA checker that turns a small SEO warning into a hard deploy block is a bug in
QA, not a win. ~90% of historical "failed builds" came from over-strict QA, not
from production-breaking errors. We fix that by **classifying** instead of
**blocking**.

---

## 4. Severity Model

Every QA finding maps to exactly one tier.

### P0 — Hard blocker (MUST fail CI)

Only genuinely dangerous, production-breaking failures:

- `zola build` fails.
- Tera template syntax error.
- Missing template partial / include.
- SCSS compile failure.
- Frontmatter TOML invalid (Zola cannot parse the page).
- Conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`) left in source.
- Workflow YAML invalid.
- A secret / token committed to the repo.
- Broken internal route in a **critical** area: homepage, nav, sitemap, canonical,
  editor/admin tool route.
- Auth / VIPZone backend change that risks breaking Editor/Admin login.

### P1 — Should fix (auto-heal or hotfix PR)

Do not block immediately if a **safe auto-fix** exists:

- Generated JSON conflict in `data/`.
- Stale report: merge-report, build-dashboard, compliance, pagespeed.
- Missing generated data **that a script can regenerate**.
- Category/tag format that can be normalized.
- Broken internal link **outside** a critical route.
- Old / stale artifact in `public/`.
- A **known failure pattern** already documented in `CLAUDE.md` (or local `CLAUDE_PRIVATE.md`).

Logic:

- If auto-fixable → fix → rerun QA / build.
- If not auto-fixable → create a report + hotfix PR.
- **Only fail after** auto-healing was attempted and still failed.

### P2 — Warning / advisory (MUST NOT block deploy)

Content/SEO quality issues never kill a build:

- Missing / weak SEO description.
- Title too long / too short.
- Thin content.
- Missing FAQ.
- Too few internal links.
- Unpolished tags / categories.
- Low compliance score.
- Readability warnings.
- Low PageSpeed score, poor mobile LCP.
- External link timeout / 404.
- GSC / GA / PageSpeed API fetch failure (quota / network).

These are written to a **report** for the Editor / Insights to handle later.

### P3 — Informational (log only)

- UX suggestions.
- Taxonomy suggestions.
- Internal-linking suggestions.
- Non-critical dashboard freshness.
- Optional image / OG improvements.

### QA Decision Rule

```text
PASS       if P0 == 0 and the build succeeds.
AUTO_HEAL  if P1 > 0 and a known safe fix exists.
FAIL       only if P0 > 0, OR auto-healing was attempted and still failed.
P2 / P3    never block deploy.
```

---

## 5. Auto-healing Policy

Before failing CI, the system must:

1. Read public rules in `CLAUDE.md`.
2. If running locally and `CLAUDE_PRIVATE.md` exists, read private local memory too.
3. Match the current failure against a known vaccine / experience pattern.
4. If a safe fix exists:
   - apply the fix,
   - rerun the affected checker,
   - rerun `zola build`,
   - write a summary of exactly **what was auto-healed**.
5. Only fail CI **after** auto-healing was attempted and the P0/P1 error remains.

**Safe to auto-heal:**

- regenerate generated JSON,
- remove stale `public/`,
- normalize a data report,
- restore a missing generated file via an existing script,
- fix a known Tera include path (pattern already documented),
- take `origin/main` for a generated-report conflict,
- rerun `scripts/build_references.py`,
- rerun `scripts/compliance_audit.py` in report-only mode.

**Do NOT auto-heal (no clear vaccine):**

- auth,
- payment,
- backend secrets,
- deploy credentials,
- bulk content rewrites,
- large template/layout changes,
- domain / canonical config.

These require a human or an explicit, reviewed vaccine.

---

## 6. Public vs Private Agent Memory

SEOMONEY agent memory is split in two:

| File | Visibility | Holds |
|------|-----------|-------|
| `CLAUDE.md` | **Public** (committed) | Runbook, deployment culture, high-level QA policy, public-safe vaccine summaries, non-sensitive command patterns, general coding rules, links to public docs. |
| `CLAUDE_PRIVATE.md` | **Private** (gitignored, local-only) | Private code/deploy strategy, tactical auto-healing notes, fragile-area warnings, backend/auth/VIPZone caveats, private QA exceptions, risky heuristics not safe for a public repo. |

**Never put in `CLAUDE.md`:** private strategy, sensitive deploy tactics, internal
security/auth notes, secret names *or* values, backend private assumptions, risky
auto-fix heuristics, or anything that should not be public in a GitHub repo.

`CLAUDE_PRIVATE.md` is gitignored and **must not be committed**. CI must work
without it.

---

## 7. CLAUDE.md Experience Library

`CLAUDE.md` is the **public-safe** experience library. It keeps:

- the operational runbook (auto-merge, deploy, PR workflow),
- high-level QA / severity policy,
- the **vaccine library** (`#### V<N> — …` blocks) of known build failures and
  their public-safe fixers — these are also parsed by `scripts/vaccine_autofixer.py`,
  so the heading format must stay stable,
- general Zola / Tera / SCSS / GitHub Actions lessons,
- non-sensitive command patterns and coding rules.

When a vaccine entry contains tactical/fragile detail, keep a **short sanitized
summary** in `CLAUDE.md` and move the detailed version to private memory.

---

## 8. CLAUDE_PRIVATE.md Local Memory

`CLAUDE_PRIVATE.md` is **local-only** memory for agents (Claude / OpenCode) and the
maintainer. It is gitignored. Suggested structure:

```md
# SEOMONEY Private Agent Memory

This file is private/local only.
Do not commit this file.
Do not expose this content in public docs.

## Private Deployment Lessons
## Private QA / Auto-healing Heuristics
## Fragile Areas
## Backend / Auth / VIPZone Notes
## Generated Data Handling Notes
## PR / Deploy Strategy Notes
## Retired or Risky Fix Patterns
```

To bootstrap one locally, copy `CLAUDE_PRIVATE.example.md` → `CLAUDE_PRIVATE.md`
and fill in. Confirm it stays untracked (`git status` should not list it).

---

## 9. Existing Vaccine / Rule Migration Policy

When auditing existing `CLAUDE.md` entries, classify each into one bucket:

- **A — Public-safe → keep in `CLAUDE.md`.** General Zola/Tera/SCSS or GitHub
  Actions lessons, QA severity policy, deployment culture, non-sensitive commands,
  public-safe vaccine summaries. Rewrite to be short and clean.
- **B — Private/tactical → move to `CLAUDE_PRIVATE.md`.** Internal agent strategy,
  fragile repo-specific heuristics, backend/auth/VIPZone caveats, risky
  auto-healing logic, private operational assumptions. Leave only a sanitized
  summary in `CLAUDE.md` if a public trace is needed.
- **C — Deprecated/retired → mark, do not migrate as an active rule.** Use the
  format below.
- **D — Sensitive/security → stop and report.** If an entry contains real secrets,
  tokens, keys, or credentials: remove from public docs, do **not** copy the secret
  anywhere, report that **rotation may be needed**, leave only a sanitized note,
  and never print the secret in PR summaries or CI logs.

Retired-rule format:

```md
### Retired Rule: <name>

- Old behavior:
- Why retired:
- Replacement:
- Date:
```

---

## 10. Generated Data Policy

Audit files in `data/` and classify:

- **Source-of-truth data** (e.g. curated series manifests, `categories.json`,
  `auto-merge-policy.json`) — review carefully; never auto-overwrite.
- **Generated reports** (merge-report, build-dashboard, compliance, references,
  related, seo-qa-scores) — must **never** cause a conflict or block deploy.
  Conflicts here are a merge race, not a code bug: take `origin/main`, then
  regenerate.
- **Runtime snapshots** — rebuild or treat as report-only.
- **Stale dashboard data** — warning (P2), not a blocker.

If a checker fails because a generated report is stale/divergent, convert it to a
warning or auto-regenerate it.

---

## 11. What Should Block Deploy

Only **P0**:

- `zola build` failure,
- Tera syntax error / missing include,
- SCSS compile failure,
- invalid frontmatter TOML,
- conflict markers in source,
- invalid workflow YAML,
- a committed secret/token,
- a broken critical route (homepage, nav, sitemap, canonical, editor/admin),
- an auth/VIPZone change that risks breaking Editor/Admin login.

---

## 12. What Should NOT Block Deploy

**P2 / P3** never block:

- SEO description / title length / focus-keyword warnings,
- thin content, missing FAQ, too few internal links,
- unpolished tags/categories, low compliance score, readability,
- low PageSpeed / poor mobile LCP,
- external link 404/timeout,
- GSC/GA/PageSpeed API fetch failures (quota/network),
- non-critical dashboard staleness,
- optional image/OG/UX/taxonomy suggestions.

And **P1** does not block **until auto-healing has been attempted and failed**.

---

## 13. Bugfix PR Summary Standard

Every bugfix PR summary must state where the lesson was recorded **and** the QA
outcome:

```text
P0 blockers:
P1 healed/candidates:
P2 warnings:
P3 info:
Build result:
Experience added:
- Public CLAUDE.md: Yes/No
- Private CLAUDE_PRIVATE.md: Yes/No/Local-only
Reason:
```

- `Public CLAUDE.md: Yes` — only when the lesson is safe and publicly reusable.
- `Private CLAUDE_PRIVATE.md: Yes/Local-only` — for sensitive/tactical lessons.
- `No` — when the bug is trivial or not reusable.

Never leak secrets or sensitive backend/auth detail into a PR summary.

---

## 14. Definition of Done

A deployment-culture change is done when:

- `CULTURE_OF_DEPLOYMENT.md` exists and covers: the `Bug found → … → Auto-healing`
  loop, the `Detect → … → Deploy` pipeline, the Important Deployment Culture Rule,
  the public/private memory strategy, the P0/P1/P2/P3 severity model, the
  auto-healing policy, and the vaccine/rule migration policy.
- `.gitignore` protects private memory files.
- `CLAUDE.md` is sanitized as public-safe guidance and links here.
- Existing vaccines/rules are audited and classified (A/B/C/D).
- Private/tactical content is out of public `CLAUDE.md`.
- The real `CLAUDE_PRIVATE.md` is **not** committed.
- `CLAUDE_PRIVATE.example.md` (if present) contains only safe placeholders.
- P0 remains a hard blocker; P2/P3 are documented as non-blocking advisory checks.
- The bugfix PR summary standard is updated.
- A migration summary is included in the final report.
