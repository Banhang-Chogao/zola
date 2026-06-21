# QA Tiered Gate

## Goal

Reduce false-blocking PRs by separating hard blockers from repo hygiene and content-quality warnings.

## Tier 1 — Merge Blockers

Always fail PR:

- conflict markers
- real secret leaks
- syntax errors
- unit test failures
- Zola build failures
- broken internal links
- invalid YAML/TOML/JSON

## Tier 2 — Repo Hygiene

Fail only when related files are modified. Otherwise warn.

Examples:

- duplicate vaccine IDs
- vaccine registry drift
- detector/test mismatch
- workflow wiring drift

Related files:

- CLAUDE.md
- scripts/qa_vaccines.py
- scripts/test_qa_vaccines.py
- .github/workflows/*
- docs/ci/*

## Tier 3 — Content Warnings

Never block merge:

- SEO title length
- category ordering
- report freshness
- non-critical UX hints

## Diff Awareness

Primary:

```bash
git diff --name-only origin/main...HEAD
EOf
