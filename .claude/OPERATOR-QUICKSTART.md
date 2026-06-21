# Vaccine Shortcut Operator Quick Start — Bilingual Guide

**Language:** English + Tiếng Việt (side-by-side)

---

## 1. Decision Flow: "What's Wrong? → Which Shortcut?"

### Flow Chart (Text)

```
START: What's broken?

├─ PR won't merge? Conflict? Branch stale?
│  └─→ **fix-merge** (ff9, prn, gg)
│
├─ Deploy failed? Build red? Backend not synced?
│  └─→ **fix-deploy** (ff, backend8, deploysafe29)
│
├─ Article score low? Links broken? SEO bad?
│  └─→ **fix-seo** (seo11, check_404, build_ref)
│
├─ UI looks wrong? CSS broken? Layout fail?
│  └─→ **fix-ui** (search11, editor11)
│
└─ GA/GSC disconnected? Analytics missing?
   └─→ **fix-gsc-ga** (theodoi8, ga_vacxin)
```

---

## 2. When-to-Use Reference Tables

### TOP-LEVEL 1: fix-merge (Merge / Conflict Resolution)

| English | Tiếng Việt | Symptom | Shortcut | Action |
|---------|-----------|---------|----------|--------|
| **Merge Conflict** | **Xung đột Merge** | PR shows `mergeable_state: dirty` with conflict markers in files | `ff9` | Auto-fix semantic conflicts; rebase onto main; re-merge |
| **Auto-Merge Stuck** | **Auto-Merge Kẹt** | PR passed qa-check but auto-merge blocked or timed out | `prn` | Check merge blocker, re-trigger auto-merge, or diagnose CI delay |
| **Create/Open PR** | **Mở PR** | Branch pushed but no PR exists; need to open/reuse one | `gg` | Create PR, enable auto-merge, trigger CI pipeline |

**When fix-merge applies:**
- 🔴 Conflict markers in `.md`, template, SCSS, data JSON
- 🟡 Stale branch (content already merged, rebasing needed)
- 🟡 Dirty state (auto-generated files diverged)

---

### TOP-LEVEL 2: fix-deploy (Deploy / Production Verification)

| English | Tiếng Việt | Symptom | Shortcut | Action |
|---------|-----------|---------|----------|--------|
| **Diagnose CI** | **Chẩn đoán CI** | `zola build` or `qa-check` failed; need log + vaccine match | `ff` | Identify root cause from failure pattern; match vaccine signature |
| **Backend Sync** | **Kiểm tra Backend** | Frontend calls `/cms/…` or `/gsc/…` but gets 404; Pages green but backend lag | `backend8` | Verify backend routes are deployed (not 404); suggest Render Manual Sync if needed |
| **Smoke Test Prod** | **Kiểm tra Production** | Pages deploy green; verify backend routes actually serve (not 404) | `deploysafe29` | Post-deploy validation; confirm critical routes non-404 |

**When fix-deploy applies:**
- 🔴 `zola build` fail (Tera/YAML/SCSS syntax error)
- 🔴 `configure-pages` rate limit (V5)
- 🟡 Backend route 404 (Pages ≠ Render lag, V16/V25)
- 🟡 Deploy cancelled (concurrency, harmless if latest is success, V5)

---

### TOP-LEVEL 3: fix-seo (SEO / Content Optimization)

| English | Tiếng Việt | Symptom | Shortcut | Action |
|---------|-----------|---------|----------|--------|
| **Check Internal Links** | **Kiểm tra Internal Links** | `qa-404-checker.py` report: "N internal broken"; links to posts 404 | `check_404` | Scan internal links; auto-fix with `--fix` for safe rewrites |
| **Build References** | **Tính lại References** | Article references block missing or stale; `data/references.json` out of sync | `build_ref` | Regenerate reference blocks; ensure all articles tracked |
| **SEO Health Check** | **Chấm điểm SEO** | Article score <70; missing FAQ, internal links, keyword placement | `seo11` (auto) | Auto-score via PostToolUse hook; `--all` to re-score all articles |

**When fix-seo applies:**
- 🔴 `qa-404-checker` exit 2 (internal link broken, V14 fabricated links)
- 🟡 Compliance score <70 on new article
- 🟡 Each article: ≥5 internal links, FAQs, keyword placement (E-E-A-T)

---

### TOP-LEVEL 4: fix-ui (UI / Layout Compliance)

| English | Tiếng Việt | Symptom | Shortcut | Action |
|---------|-----------|---------|----------|--------|
| **Search UI Style** | **Sửa Search Dialog** | Internal search dialog renders raw/unstyled (BEM markup, no structure CSS) | `search11` | Check if CSS partial `_site-search.scss` imported; add structure CSS |
| **Editor S-DNA Layer** | **Editor Visual Fix** | CMS `/editor/` loses calm S-DNA look; emoji icons appear; handlers broken | `editor11` | Verify `_editor-sdna.scss` imported; restore publish/SEO logic |

**When fix-ui applies:**
- 🟡 Component renders but looks broken (no CSS partial, V20 Search UI)
- 🟡 `zola build` passes (structure/data fine, just visuals)
- 🟡 Mobile responsive not applied (V21 floating nav)

---

### TOP-LEVEL 5: fix-gsc-ga (GSC / Analytics Health)

| English | Tiếng Việt | Symptom | Shortcut | Action |
|---------|-----------|---------|----------|--------|
| **Monitor Dashboard** | **Theo dõi Dashboard** | Build dashboard, merge report, CI feeds need live poll; diagnostic dashboard check | `theodoi8` (merged as `wip8`) | Live poll of CI/deploy/merge status; real-time feed |
| **GA Vaccine Daily** | **GA Health Check** | GA metrics stale; property mismatch; health status pending or disconnected | `ga_vacxin` | Detect GA auth failure; property drift; verify data flow hourly |

**When fix-gsc-ga applies:**
- 🟡 GA property changed; backend not re-authed (V19/V27)
- 🟡 GSC property mismatch (URL-prefix vs domain, V19)
- 🟡 Dashboard metrics pending (no recent run)

---

## 3. Vaccine Mapping Reference

When a symptom matches, map to the correct vaccine + fixer:

| Symptom | Vaccine | Fix Tool | Shortcut | Phase |
|---------|---------|----------|----------|-------|
| Merge conflict in shared infrastructure | V10/V12 | `autofix_conflicts.py` + semantic resolve | `ff9` | Auto |
| Data JSON conflict (seo-scores, references) | V6/V18 | Take `main` + regenerate | `ff9` | Auto |
| Tera `replace(old=/new=)` syntax error | V8 | Search/replace; revert to `from=/to=` | `ff` | Manual |
| HuggingFace 401 on snapshot_download | V1 | Update `MODEL_NAME` to full org/model | `ff` | Manual |
| `configure-pages` API rate limit | V5 | Deploy concurrency + backoff; wait quota | `ff` | Wait |
| Draft link (publish_at future) | V13 | Skip as scheduled forward-ref; don't gate | `check_404` | Auto-skip |
| Fabricated `/bai-N-…/` cluster links | V14 | Repoint to real `/zola/posting/slug/` | `check_404` + `ff` | Manual |
| Backend route 404 (frontend calls it) | V16/V22b/V25 | Mount route on deployed `services/vipzone` | `backend8` | Manual |
| GSC domain property mismatch | V19/V27 | Use `sc-domain:seomoney.org`; not URL-prefix | `ga_vacxin` | Manual |

---

## 4. Escalation & Manual Cases

When automated shortcut doesn't resolve (or no matching vaccine):

### Escalation Path

1. **Read log from `ff` output** → match V<N> signature in CLAUDE.md §4
2. **If no vaccine match:**
   - Use `ff9` (semantic diagnostic tool, not auto-fixer)
   - Append findings to CLAUDE.md "Autofixer Conflict Learning Log"
   - Open GitHub issue with log + context
3. **If vaccine match + fixer fails:**
   - Check fixer pre-conditions (files exist? config valid?)
   - Run fixer with `--dry-run` to diagnose
   - If confidence < 90%, escalate to manual/user review

### Manual Review Checklist

- [ ] Read complete vaccine definition (CLAUDE.md §4 `#### V<N>`)
- [ ] Verify symptom matches (not false positive)
- [ ] Check prerequisites (files/config/permissions)
- [ ] Run fixer with `--dry-run` first
- [ ] Test locally before commit
- [ ] Document learning if new pattern discovered

---

## 5. Common Aliases & Backward Compat

Old shortcut names (maintained for workflow automation):

| Old Name | New Group | Maps to | Status | Notes |
|----------|-----------|---------|--------|-------|
| `theodoi8` | fix-gsc-ga | `wip8` (merged with WIP tracker) | Active | Still callable as alias |
| `ff` | fix-deploy | Diagnose CI; reuse vaccine FIXER | Core | No alias needed |
| `ff9` | fix-merge | Semantic conflict resolver | Core | No alias needed |
| `prn` | fix-merge | Create/update PR + auto-merge | Core | No alias needed |
| `gg` | fix-merge | Open PR on GitHub | Core | No alias needed |

---

## 6. Files for Phase 1 Implementation

✅ **Created/Updated:**
1. `shortcuts.md` — grouping sections + constraint comment (no logic change)
2. `.claude/OPERATOR-QUICKSTART.md` — this guide (new file)
3. `.claude/ui-layout.md` — ASCII sketches (new file)

❌ **NOT modified (Phase 2 only):**
- `CLAUDE.md §4` (vaccine definitions locked)
- `qa_vaccines.py` (detector code locked)
- `.claude/settings.json` (runtime config locked)
- Manifest / Phase 2 tooling (deferred)

---

## 7. Next Steps: Phase 2 (Future)

When Phase 2 is approved:
- [ ] Create `.claude/vaccine-manifest.json` (registry + metadata)
- [ ] Wire up alias support in `.claude/settings.json` (if needed)
- [ ] Build operator UI dashboard with top-5 buttons
- [ ] Add search/filter for shortcut discovery
- [ ] Integrate vaccine matching engine into UI

---

**End of OPERATOR-QUICKSTART.md**
