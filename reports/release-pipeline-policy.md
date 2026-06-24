# SEOMONEY Release Pipeline Policy

## Goal

SEOMONEY uses a severity-based release pipeline from commit to production.

## Flow

Local change → Quickcheck → Commit → Push branch → Pull Request → CI hard gate → Auto-merge → Deploy GitHub Pages → Production verification.

Done only when the real site is confirmed.

## ERROR — blocks PR/deploy

Only production-breaking issues may fail CI:

- Zola build failure
- Tera/template syntax error
- conflict markers
- invalid TOML/YAML/JSON
- leaked secrets/tokens/keys
- required internal links broken
- required assets missing
- private/admin/auth/editor pages exposed as indexable
- sitemap contains forbidden private/admin/auth/editor URLs

## WARN — does not block

SEO/content/dashboard issues must not block shipping:

- SEO score below target
- orphan posts
- weak internal links
- thin clusters
- empty categories
- missing FAQ/TLDR
- GSC low/no data
- non-indexed pages
- GA/GSC API empty
- old generated reports
- dashboard data unavailable
- content opportunity suggestions

## INFO

- generated stats
- recommendations
- trend notes

## Local commands

- bash scripts/quickcheck.sh
- bash scripts/preflight.sh
- python3 scripts/verify_production.py

## Final report format

Every release task should report:

- Files changed
- Checks reclassified
- New commands
- QA result
- Production verification behavior
- Remaining true blockers, if any
