# Healing Patterns — auto-build-failed-healing bot

> Public-safe documentation for the SEOMONEY auto maintainer bot
> `auto-build-failed-healing`. Anyone (user, contributor, agent) may read this.
> NO secrets, tokens, or private tactics live here.

The bot runs the SEOMONEY deployment culture as code:

```text
Bug found → Fix it → Learn from it → Auto-healing
Detect → Classify → Heal → Build → Learn → PR
```

It scans build/deploy/qa runs that **FAILED in the last 48h**, classifies each
failure, applies a **safe deterministic fix** when one is matched, runs a
targeted build, and opens a **hotfix PR**. It **never pushes `main` directly**.

## Files

| Component | Path |
|-----------|------|
| Workflow | `.github/workflows/auto-build-failed-healing.yml` |
| Engine | `scripts/auto_build_failed_healing.py` |
| Tests | `scripts/test_auto_build_failed_healing.py` |
| Public registry | `data/healing-patterns.json` |
| Dedup state | `data/auto-healing-state.json` |
| Report | `data/auto-healing-report.json` |

## Triggers

- `workflow_run` (completed) on `deploy`, `qa`, `Build`, `Zola Deploy`,
  `GitHub Pages`, plus the long-named build/QA/related workflows. Only acts when
  the upstream `conclusion == failure`.
- `schedule` hourly — scans failed runs from the last 48h.
- `workflow_dispatch` — optional `dry_run` input.

## 48h rule (hard)

- Failures **older than 48h are ignored** and reported as `stale_ignored`.
- Old broken feature branches are **not revived**.
- No hotfix PR is created for stale builds.

## Severity model

| Tier | Meaning | Bot behaviour |
|------|---------|---------------|
| **P0** | Hard blocker (zola/Tera/SCSS/frontmatter/conflict markers/YAML/secret/route) | Heal if a safe fixer exists, else open a manual-review PR/report |
| **P1** | Auto-heal candidate (generated JSON conflict, stale report, missing data, known template/route, internal link, known auth UI) | Apply safe fix → build → hotfix PR |
| **P2** | Advisory (SEO/thin content/missing FAQ/weak links/external timeout/quota/PageSpeed/compliance) | **Report only — never blocks, never PRs** |
| **P3** | Informational | Log only |

## Public-safe healing sources

The bot reads only committed, public-safe sources:

1. `CLAUDE.md`
2. `CULTURE_OF_DEPLOYMENT.md`
3. `docs/HEALING_PATTERNS.md` (this file, optional)
4. `data/healing-patterns.json` (optional)

`CLAUDE_PRIVATE.md` is **gitignored local-only memory**. CI must not require it,
must not depend on it, and its content is never printed or committed. A local
Claude/OpenCode agent **may** read it when present.

## Registry schema (`data/healing-patterns.json`)

```jsonc
{
  "version": 1,
  "patterns": [
    {
      "id": "tera-items-method-not-supported",
      "match": ["expected +, -, *, /", ".items()", "failed to parse"],
      "severity": "P1",
      "safe_fix": "Replace Python-style .items() with Tera-compatible iteration.",
      "fixer": null,            // id of a deterministic safe fixer, or null
      "commands": ["zola build"],
      "requires_pr": true        // bot never pushes main
    }
  ]
}
```

`match` tokens are lowercase substrings searched in the failure log. A pattern
matches when all (or, for long lists, most) tokens appear. The most-specific and
most-severe pattern wins.

## Safe fixers (deterministic, reuse existing scripts)

| Fixer id | What it does |
|----------|--------------|
| `regenerate-references` | `python3 scripts/build_references.py` |
| `clean-public` | remove the gitignored `public/` artifact (clean rebuild) |
| `internal-link-fix` | `python3 qa-404-checker.py --fix` (source `.md` only) |
| `faq-field-rename` | rename FAQ frontmatter `question=`/`answer=` → `q=`/`a=` (line-anchored) |

Patterns with `fixer: null` are **not** auto-edited — the bot reports them for
manual review (auth, payment, backend, deploy creds, large template rewrites,
mass content rewrites). Secrets/tokens/credentials are **never** auto-fixed.

## Branch / PR behaviour

1. Branch: `auto-build-failed-healing/<pattern-id>-<run-id>`
2. Apply safe fix → targeted build/QA → commit.
3. PR title: `fix(auto-healing): <pattern-id>`
4. Labels: `auto-healing`, `build-fix` (created if missing, skipped on error).
5. **Dedup:** before opening a PR the bot checks for an existing open PR for the
   same `run-id`/`pattern`/branch and skips/updates instead of duplicating.

## Usage

```bash
# Dry-run (list failed runs, classify, show proposed fix — no mutation, no PR)
python3 scripts/auto_build_failed_healing.py --dry-run --hours 48

# Real run (apply safe matched fixes, open hotfix PR, never push main)
python3 scripts/auto_build_failed_healing.py --hours 48 --apply
```

The `--hours` value is hard-capped at 48. Offline / no `gh` token → the live run
scan is skipped and the bot exits 0 (never self-red).

## QA

```bash
python3 scripts/auto_build_failed_healing.py --dry-run --hours 48
python3 -m py_compile scripts/auto_build_failed_healing.py
python3 -m unittest scripts.test_auto_build_failed_healing -v
zola build
```

## Permanent prevention

Every healed failure should leave a reusable lesson:

- Add/extend a pattern in `data/healing-patterns.json` (the bot auto-parses it).
- Add a public-safe note to `CLAUDE.md` / `CULTURE_OF_DEPLOYMENT.md` when broadly
  reusable.
- For private/tactical lessons: keep a **local** note in `CLAUDE_PRIVATE.md`
  (never committed).
