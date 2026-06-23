# CI speed + retired paywall cleanup — 2026-06-23

## Context

LC8 is live:

https://seomoney.org/posting/lc8-blog-20260623-215111/

PR #789 exposed two issues:

- Normal QA/deploy still executed legacy paywall strip logic.
- Deploy build took about 23m46s before Pages publish.

## Changes in this PR

- Removed the default QA/deploy step: `Strip premium content before build`.
- Removed default `scripts.test_paywall` from QA unit tests.
- Kept legacy paywall scripts and tests in the repository for archive/manual use.
- Kept full Zola build, 404 checker, OG validation, and public security audit intact for safety.

## Not changed

- LC8 article content.
- Public routes.
- `/tools/blog-heart-beat/`.
- Deploy Monitor route.
- Existing paywall source files.

## Expected impact

The normal pipeline no longer mutates premium content before every QA/deploy run and avoids one retired paywall test group in default QA. Full site build may still be slow and should be optimized in a later Quick Gate / Heavy Gate split.

## Follow-up

- Split PR checks into Quick Gate and Heavy Gate.
- Move full 404/OG/public security checks to main/nightly where safe.
- Audit Deploy Monitor freshness warning.
