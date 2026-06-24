# Release Pipeline Audit

## Current known components

- Zola build
- qa_check.py
- scripts/check_internal_links.py if available
- GitHub Actions workflows
- auto-merge workflow
- deploy workflow
- production monitoring / verification scripts

## Target state

qa_check.py should eventually become severity-based:

QA RESULT: PASS / PASS_WITH_WARNINGS / FAIL
Errors: N
Warnings: N
Info: N

Exit behavior:

- exit 1 only when ERROR exists
- exit 0 when only WARN/INFO exists
- write warning-only issues to reports/qa-warnings.md

## Follow-up required

This PR adds the release policy and local helper scripts first.

A later bounded PR should refactor qa_check.py after inspecting current checks, so we do not accidentally weaken production safety.
