# SEOMONEY Private Agent Memory — Example

> Copy this file to `CLAUDE_PRIVATE.md` for local-only notes.
>
> **Do not commit `CLAUDE_PRIVATE.md`** — it is gitignored on purpose (see
> `.gitignore` and `CULTURE_OF_DEPLOYMENT.md` §6, §8).
> CI must never depend on this file. Never paste real secrets, tokens, keys, or
> credentials here — keep only tactical notes. If a secret leaks anywhere,
> rotate it and remove it; do not record the value.

This file contains only **safe placeholder section headings**. Fill them in
locally with private/tactical detail that is useful but not clean/safe enough for
the public `CLAUDE.md`.

## Private Deployment Lessons

<!-- e.g. "Deploy X tends to fail right after batch merges because <reason>; do Y first." -->

## Private QA / Auto-healing Heuristics

<!-- e.g. fragile auto-fix order, when to take origin/main vs regenerate, retry timings. -->

## Fragile Areas

<!-- e.g. templates/scripts that break in non-obvious ways; what to check before touching them. -->

## Backend / Auth / VIPZone Notes

<!-- e.g. Editor/Admin login assumptions, OAuth return_to quirks. Names only, never values. -->

## Generated Data Handling Notes

<!-- e.g. which data/*.json to regenerate vs take-from-main on conflict. -->

## PR / Deploy Strategy Notes

<!-- e.g. ordering when several PRs collide; what to rebase first. -->

## Retired or Risky Fix Patterns

<!-- e.g. fixes that looked right but caused regressions; do not repeat. -->
