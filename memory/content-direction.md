# Content Direction — Content Intelligence engine

Detailed memory for the content-intelligence feature. CLAUDE.md stays an index.

## Purpose

Analyze the whole blog corpus and emit one static report powering the S-DNA
dashboard at **`/tools/content-direction/`**. Surfaces what to write/fix next:
topics, clusters, internal-link gaps, orphan content, SEO weakness, AdSense-safe
direction, Google Helpful-Content actions, keyword/content opportunities, next
article ideas by category, and which old posts need a refresh.

## Files

| Part | Path |
|------|------|
| Analyzer | `scripts/content_direction.py` |
| Report (output) | `static/data/content-direction/report.json` |
| Page | `content/tools/content-direction.md` |
| Template | `templates/content-direction.html` (reads report via `load_data`) |
| Styles | `sass/_content-direction.scss` (import after `s-dna` in `site.scss`) |

## Reuse, don't duplicate

- Post loading / frontmatter / cluster inference / `strip_markdown` →
  `scripts/related_engine.py` (its top-level `numpy` import was made **lazy** so
  these helpers load without numpy in a minimal env).
- Semantic neighbors / scores → `data/related.json`, `data/scores.json`.
- SEO scores → `data/seo-qa-scores.json` (`seo_qa_checker.py`).

No model download at report-build time: it consumes already-computed semantic
data. Optional `textstat` / `rank-bm25` refine signals when present (guarded).

## Signals & thresholds

- **Internal link gap**: post body has `< 5` internal links (SEO §3). Suggestions
  come from the post's semantic neighbors in `related.json`.
- **Orphan**: 0 inbound (no other post lists it as a neighbor).
- **SEO weakness**: `seo_qa` score `< 70`, thin content `< 800` words, link gap, or
  missing external link.
- **Refresh**: posts older than 150 days.
- **AdSense status**: `review` if any title/keyword/tag hits a policy-risk term,
  else `safe`.

## Run

```bash
python3 scripts/content_direction.py            # build report.json
python3 scripts/content_direction.py --print     # + summary to stdout
```

CI-safe: any failure is caught, prints a WARN, keeps the cached report, exit 0.
Regenerated in `deploy.yml` before `zola build` (alongside `build_references.py`).

## Notes

- Post references render as **text** (title + cluster/age badge), not anchors, so
  the page never trips the `qa-404-checker` internal-link gate.
- Page alias kept to `/content-direction/` only (the `/tools/content-direction/`
  canonical needs no self-alias).
