# AI Diagnose Migration Plan

## Executive summary

**Current CI does not consume Claude credits.** The paid `ai-diagnose.yml` workflow was removed in PR #205 (2026-06-16). Deploy failures are handled by `build-failure-handler.yml` → `qa-failed.py`, which uses regex vaccines only.

Issue **#195** (`AI Diagnose: deploy fail @ bcef229`) is a **legacy artifact** from the deleted workflow. Close it manually; no ongoing token burn.

## Historical vs current architecture

| Era | Trigger | Diagnosis | Cost |
|-----|---------|-----------|------|
| **Before PR #205** | `deploy.yml` failure | `ff.py` + `ANTHROPIC_API_KEY` + `claude-opus-4-7` | **Paid** — every deploy fail |
| **After PR #205** | Same failures | `qa-failed.py` + `vaccine_rules.py` | **Free** |
| **This PR** | Same | `ai_diagnose.py` Tier 1 + vaccines | **Free** (Claude opt-in only) |

### Old workflow (deleted)

```yaml
# .github/workflows/ai-diagnose.yml (removed)
env:
  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  FF_AI_MODEL: claude-opus-4-7
run: python3 scripts/ff.py  # always called Claude on failure
```

## New hybrid tiers

```
Tier 1 (default, CI + local)
  scripts/ai_diagnose.py — regex + heuristics
  Confidence often ≥ 70% for known Zola/CI patterns
        ↓ confidence < 70%
Tier 2 (optional, local dev)
  Ollama — AI_DIAGNOSE_USE_OLLAMA=1
        ↓ still < 70% + explicit opt-in
Tier 3 (last resort, manual)
  Claude — AI_DIAGNOSE_USE_CLAUDE=1 + ANTHROPIC_API_KEY
  Used by ff.py locally only; NEVER enabled in CI by default
```

## Files changed

| File | Role |
|------|------|
| `scripts/ai_diagnose.py` | Free-first log parser + optional Tier 2/3 |
| `qa-failed.py` | Embeds Tier-1 diagnosis in GitHub issue bodies |
| `scripts/ff.py` | Runs heuristics first; Claude only with opt-in |
| `.github/workflows/build-failure-handler.yml` | `AI_DIAGNOSE_USE_CLAUDE=0` explicit |
| `scripts/test_ai_diagnose.py` | Unit tests |

## What we do **not** do

- **Do not** restore `ai-diagnose.yml` with `ANTHROPIC_API_KEY` on every failure.
- **Do not** add `ANTHROPIC_API_KEY` to CI workflows unless explicitly approved.
- **Do not** auto-call `claude-opus-4-7` from GitHub Actions.

## Local usage

```bash
# Free diagnosis from failed run
gh run view RUN_ID --log-failed | python3 scripts/ai_diagnose.py

# Zola build + free diagnose
python3 scripts/ff.py --dry-run

# Paid fallback (explicit)
export AI_DIAGNOSE_USE_CLAUDE=1
export ANTHROPIC_API_KEY=sk-ant-...
python3 scripts/ff.py
```

## Free alternatives already in repo

| Tool | Used for |
|------|----------|
| `vaccine_rules.py` / `qa-failed.py` | Auto-fix safe patterns |
| `qa_check.py --fix safe` | Frontmatter / content |
| `qa.yml` | Ruff, link checks, Zola build |
| `scripts/ff.py --dry-run` | Heuristics only |

## Rollout checklist

- [x] Implement `ai_diagnose.py` Tier 1 patterns (Zola, SCSS, Tera, deps, deploy, YAML, links)
- [x] Wire into `qa-failed.py` issue bodies
- [x] Gate `ff.py` Claude behind `AI_DIAGNOSE_USE_CLAUDE=1`
- [x] Set `AI_DIAGNOSE_USE_CLAUDE=0` in `build-failure-handler.yml`
- [ ] Merge PR → verify next build failure issue includes "AI Diagnose (free-first)" section
- [ ] Close legacy issues #195 and others labeled `auto-diagnose`
- [ ] Optional: remove unused `ANTHROPIC_API_KEY` repo secret if nothing else needs it

## Adding new patterns

1. Add a `DiagnosticRule` in `scripts/ai_diagnose.py`.
2. If auto-fixable, mirror in `scripts/vaccine_rules.py` + `qa-failed.py` fixer.
3. Add a fixture to `scripts/test_ai_diagnose.py`.

Target: **near-zero Claude token use** for automated deploy-failure auditing while preserving actionable root-cause summaries.