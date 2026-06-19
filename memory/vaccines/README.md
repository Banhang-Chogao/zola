# memory/vaccines/ — AI Learning Engine for the Vaccine AutoFixer

Detailed memory for the **learning layer** on top of the hand-curated QA Vaccine
library (CLAUDE.md §4 / `docs/VACCINES.md`). CLAUDE.md stays an index; the engine
details live here.

## What it does

Every time a failed **CI / build / deploy** is fixed, the fix is captured as a
reusable *vaccine candidate*. On a future failure the new log is compared against
the learned cases and the best-matching fix is suggested — auto-applied only when
it is **low-risk** and **confidence is high**, otherwise **suggest-only**.

- Engine: `scripts/vaccine_learner.py`
- Store: `memory/vaccines/learned_failures.jsonl` (one candidate per line)
- Tests: `scripts/test_vaccine_learner.py`

## Matching pipeline (failure → vaccine)

1. **Normalize** the log: strip ANSI, digits, hashes, timestamps → identifier
   tokens (so the same failure under different run-ids/SHAs share a signature).
2. **Score** each learned case:
   - Default: stdlib **TF-IDF + cosine** (no install, never breaks CI).
   - Optional upgrade when `VACCINE_LEARNER_EMBED=1` and `sentence-transformers`
     is installed: **embed** the failure logs and **search similar failures with
     FAISS** (`IndexFlatIP` over L2-normalized case vectors). Falls back to a
     numpy dot product, then to TF-IDF, on any error.
3. **Confidence** = similarity × the case's base confidence + small occurrence
   bonus (0–100).
4. **Auto-apply gate**: `risk == low` AND `confidence ≥ 80` AND `fix_tool` is in
   the `SAFE_FIX_TOOLS` allowlist. Anything else is suggest-only.

## On a successful fix → `learn`

Captures: failure **signature** (tokens), **root cause**, **files changed**, **fix
summary**, **proof command**, **vaccine candidate** (code `VL<N>`, risk, base
confidence). Near-duplicates (same `pattern_id` + cosine ≥ 0.65) are **merged**
(occurrences++), not appended — the store stays small. `dedup` re-runs the merge.

## Safety (never bypasses QA)

- Auto-apply only routes through EXISTING safe fixers (`internal-link-fix`,
  `build-references`, `qa-safe-fix`) — never a re-implemented fixer, never an
  arbitrary stored shell string. Proof commands must start with an allowlisted
  prefix (`python3`/`pytest`/`zola`/`node`).
- Content edits are forced to `high` risk → never auto-applied.
- The daily autofixer + CI still gate every change; this only suggests/queues.
- No secrets, no network by default, no model committed.

## CLI

```bash
python3 scripts/vaccine_learner.py learn  --log-file fail.log \
    --root-cause "HF 401" --files scripts/build_related.py \
    --fix-summary "org-qualify MODEL_NAME" --fix-tool hf-model-id \
    --proof "python3 scripts/qa_vaccines.py" --risk low
python3 scripts/vaccine_learner.py match  --log-file new.log [--json] [--apply]
python3 scripts/vaccine_learner.py list
python3 scripts/vaccine_learner.py dedup

# Enable embedding + FAISS search (opt-in)
VACCINE_LEARNER_EMBED=1 python3 scripts/vaccine_learner.py match --log-file new.log
```

> Vaccine = AutoFixer. ZERO_BARRIER preserved: this layer never gates merges, it
> only makes the autofixer faster at recognizing a known failure.
