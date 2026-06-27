# Manual Broken Links Healing Bot

The Broken Links Healing Bot helps fix broken internal links in the SEOMONEY blog. It scans the built Zola site, identifies 404 links, and applies safe automated fixes.

## How to Run

### Via GitHub Actions (Recommended)

1. Go to **Actions** → **Manual Broken Links Healing Bot**
2. Click **Run workflow**
3. Select mode:
   - **scan-only** — Report broken links without fixing
   - **fix** — Scan and auto-fix safe broken links
4. Click **Run workflow**

### Via CLI (Local)

Requires: `zola build` to be run first.

```bash
# Scan only (no changes to files)
python3 scripts/heal_broken_links.py --scan --stdout

# Scan and apply safe fixes
python3 scripts/heal_broken_links.py --fix --stdout
```

## Scan-Only Mode

When running in **scan-only** mode:

- ✅ Builds the Zola site (`zola build`)
- ✅ Scans all internal links for 404s
- ✅ Generates detailed report
- ✅ Uploads report as artifact
- ❌ Does NOT modify any files
- ❌ Does NOT open a PR

**Use when:** You want to inspect broken links before deciding to fix them.

**Reports saved to:**
- `data/broken-links-report.json` (JSON format, machine-readable)
- `reports/broken-links/report-YYYYMMDD-HHMMSS.md` (Markdown format, human-readable)

## Fix Mode

When running in **fix** mode:

- ✅ Builds the Zola site
- ✅ Scans all internal links
- ✅ Applies safe automated fixes
- ✅ Regenerates references
- ✅ Runs full QA suite (qa_check, check_internal_links, qa-404-checker)
- ✅ Verifies `zola build` passes with fixes
- ✅ Opens a PR with fixes (if changes exist)
- ❌ Never pushes directly to `main`

**Use when:** You want to automatically fix known, safe broken link patterns.

**PR created if:**
- Safe fixes were found and applied
- All QA checks passed
- Build succeeded

**PR details:**
- Branch: `bot/heal-broken-links-{run-number}`
- Title: `fix(links): heal broken internal links`
- Labels: `auto-healing`, `links`
- Contains: before/after analysis, detailed report

## What Gets Auto-Fixed

The bot applies only **high-confidence** fixes:

### 1. `/zola/` Prefix Normalization

Links with legacy `/zola` prefix (from GitHub Pages subpath migration).

```
/zola/some-page/  →  /some-page/
```

**Safe because:** This is a known migration pattern; the target must already exist for the link to be auto-fixed.

### 2. Trailing Slash Correction

Missing trailing slashes on directory-style URLs.

```
/categories/ngan-hang  →  /categories/ngan-hang/
```

**Safe because:** Zola directory URLs always end with `/`; if the slash version exists, it's the correct target.

### 3. Case/Slug Normalization

URL case mismatches when exactly one normalized version exists.

```
/Categories/Ngan-Hang/  →  /categories/ngan-hang/
```

**Safe because:** Filenames are case-sensitive on production; if exactly one match exists, it's unambiguous.

### 4. Known Alias Mapping

Pre-defined explicit route aliases (verified safe).

```
/categories/bao-chi/  →  /categories/tat-ca/
/categories/ngan-hang-so/  →  /categories/ngan-hang/
```

**Safe because:** Only known, manually-verified mappings are used; prevents guess-based fixes.

### 5. Anchor Fragment Cleanup

Removes broken anchor fragments when the base page exists.

```
/some-page/#broken-anchor  →  /some-page/
```

**Safe because:** The user can still reach the page; fragment navigation is graceful degradation.

## What Does NOT Get Auto-Fixed

The bot **refuses** to auto-fix:

- ❌ External URLs (`https://...`)
- ❌ Payment links (`momo.vn`, payment gateways)
- ❌ Backend URLs (`/auth/`, `/api/`, `/admin/`)
- ❌ Affiliate links
- ❌ MoMo links
- ❌ Protocol-relative URLs (`//host/path`)
- ❌ URLs inside code blocks or historical quotes
- ❌ Links with unclear/ambiguous targets

**These are reported as "Manual Review Required"** and include a suggested action for manual inspection.

## Report Format

### JSON Report

**File:** `data/broken-links-report.json`

```json
{
  "generated_at": "2026-06-27T14:30:00+07:00",
  "mode": "fix",
  "summary": {
    "total_checked": 487,
    "broken_count": 12,
    "safe_fixes_available": 8,
    "safe_fixes_applied": 8,
    "manual_review_required": 4,
    "status": "has_broken_links"
  },
  "safe_fixes": [
    {
      "source_file": "content/posting/some-article.md",
      "old_url": "/zola/categories/ngan-hang/",
      "normalized": "/categories/ngan-hang/",
      "new_url": "/categories/ngan-hang/",
      "reason": "zola_prefix_removed",
      "applied": true
    }
  ],
  "manual_review": [
    {
      "source_file": "content/posting/another-article.md",
      "broken_url": "https://external-site.com/old-page",
      "normalized": "https://external-site.com/old-page",
      "reason": "unsafe_pattern_detected"
    }
  ]
}
```

### Markdown Report

**File:** `reports/broken-links/report-YYYYMMDD-HHMMSS.md`

Human-readable markdown table format with:
- Summary statistics
- Fixed links (with applied status)
- Links requiring manual review (with reason)

## Quality Assurance

When fixes are applied, the workflow automatically runs:

1. ✅ `zola build` — Ensure site still builds
2. ✅ `qa_check.py` — Run QA lint checks
3. ✅ `check_internal_links.py` — Verify all internal links
4. ✅ `qa-404-checker.py` — Re-scan for remaining 404s
5. ✅ `build_references.py` — Regenerate reference data

**If any check fails,** the workflow stops and does not open a PR. No broken fixes reach production.

## PR Auto-Merge

Once the PR is created:

1. GitHub Actions runs CI (`qa.yml`)
2. If CI passes, the PR **auto-merges** to `main` (ZERO_BARRIER policy)
3. Fixes deploy automatically via `deploy.yml`

**Monitoring:** Watch the PR for CI results; green checks mean safe to merge.

## Examples

### Example 1: `/zola/` Prefix (Most Common)

**Before:**
```markdown
See [our banking guide](/zola/categories/ngan-hang/)
```

**After:**
```markdown
See [our banking guide](/categories/ngan-hang/)
```

**Report:**
```
| source_file | old_url | new_url | reason | status |
|---|---|---|---|---|
| content/.../banking.md | /zola/categories/ngan-hang/ | /categories/ngan-hang/ | zola_prefix_removed | ✓ |
```

### Example 2: Trailing Slash

**Before:**
```markdown
Read [this post](/posting/my-article)
```

**After:**
```markdown
Read [this post](/posting/my-article/)
```

**Report:**
```
| ... | /posting/my-article | /posting/my-article/ | trailing_slash_added | ✓ |
```

### Example 3: Manual Review (External URL)

**Not fixed** (external):
```markdown
Check [this external site](https://example.com/old-page)
```

**Report (Manual Review):**
```
| source_file | broken_url | reason |
|---|---|---|
| content/.../article.md | https://example.com/old-page | unsafe_pattern_detected |
```

→ Reported for manual inspection; you decide if the link should be removed or updated.

## Troubleshooting

### Q: I ran the bot but my PR didn't open. Why?

**A:** Check the workflow run logs:
- If no changes were found, no PR is needed (all links OK or no safe fixes available)
- If QA failed, the workflow stops before opening a PR
- Check `data/broken-links-report.json` in the artifact to see what was found

### Q: Can I schedule this to run automatically?

**A:** No — this is **workflow_dispatch only** (manual-trigger). This ensures the owner reviews broken links before auto-fixing. If you need periodic scans, run the workflow on a schedule by visiting **Actions** → **Manual Broken Links Healing Bot** → **Run workflow** regularly.

### Q: What if a "safe fix" actually breaks something?

**A:** This should never happen because:
1. The script only fixes links to **existing pages** (verified offline)
2. All fixes pass full QA + `zola build` before opening a PR
3. The PR is reviewed before auto-merge

If a link fix causes an issue, the PR can be reverted immediately.

### Q: Can I manually edit the safe fixes before the PR merges?

**A:** Yes:
1. The PR is opened as a regular pull request
2. You can push additional commits to the branch
3. Run QA again to verify changes
4. PR auto-merges when CI passes

## Adding New Safe Fix Rules

To add a new auto-fix pattern:

1. Edit `scripts/heal_broken_links.py`
2. Add your rule to the `_try_fix()` function
3. Include logic to verify the fix target exists
4. Add a new reason code (e.g., `"custom_rule_applied"`)
5. Test: `python3 scripts/heal_broken_links.py --scan`
6. Document the rule above in this file

**Rules must be:**
- ✅ Deterministic (same input → same output every time)
- ✅ Safe (fix target must exist in `public/`)
- ✅ Verifiable (offline check, no network)
- ✅ Low-risk (won't break redirects or create cycles)

## Related

- **QA 404 Checker:** `qa-404-checker.py` — Deeper offline link scanning
- **Internal Links Checker:** `scripts/check_internal_links.py` — Link validation in source
- **Zola Link Prefix Fixer:** `scripts/fix_stale_zola_links.py` — Batch `/zola/` prefix removal
- **Auto-Healing Workflows:** See CLAUDE.md §Auto Build Failed Healing for automated remediation

## Support

For issues or questions:
1. Check workflow run logs: **Actions** → **Manual Broken Links Healing Bot** → select run
2. Review the JSON/markdown reports in artifacts
3. See `data/broken-links-report.json` for structured details
4. File an issue with the report attached
