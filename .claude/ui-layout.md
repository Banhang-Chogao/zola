# Operator UI Layout Sketches — Bilingual

---

## 1. Top-Level Operator Dashboard

### English Layout

```
┌──────────────────────────────────────────────────────┐
│  ZOLA VACCINE OPERATOR DASHBOARD                     │
│                                                      │
│  Quick Access (5 Top-Level Functions)                │
│  ┌────────────────────────────────────────────────┐  │
│  │ [fix-merge]  [fix-deploy]  [fix-seo]           │  │
│  │ [fix-ui]     [fix-gsc-ga]                      │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  System Status                                       │
│  ├─ CI/Deploy: ⚫ Green (latest: 2m ago)            │
│  ├─ QA Gate: ⚫ Pass (vaccines: 0 FAIL)             │
│  ├─ SEO Health: 97/100 (A+)                        │
│  ├─ Build Dashboard: 🟡 2 cancelled (OK, V5)       │
│  └─ Latest Deploy: ✓ Success (#529)                │
│                                                      │
│  [More Tools ▼]  [Settings]  [Help]               │
└──────────────────────────────────────────────────────┘
```

### Tiếng Việt Layout

```
┌──────────────────────────────────────────────────────┐
│  BẢNG ĐIỀU KHIỂN VACCINE ZOLA                        │
│                                                      │
│  Truy cập nhanh (5 Chức năng chính)                 │
│  ┌────────────────────────────────────────────────┐  │
│  │ [fix-merge]  [fix-deploy]  [fix-seo]           │  │
│  │ [fix-ui]     [fix-gsc-ga]                      │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  Trạng thái hệ thống                                │
│  ├─ CI/Deploy: ⚫ Xanh (vừa: 2m trước)             │
│  ├─ QA Gate: ⚫ Pass (vaccine: 0 FAIL)             │
│  ├─ SEO Health: 97/100 (A+)                        │
│  ├─ Build Dashboard: 🟡 2 cancelled (OK, V5)      │
│  └─ Deploy mới nhất: ✓ Success (#529)             │
│                                                      │
│  [Công cụ khác ▼]  [Cài đặt]  [Trợ giúp]         │
└──────────────────────────────────────────────────────┘
```

---

## 2. Submenu Example: fix-merge Expansion

When user clicks `[fix-merge]` button, expandable menu shows grouped shortcuts:

### English

```
fix-merge ▼
├─ [ff9] Resolve Merge Conflict
│   Description: Auto-fix semantic conflicts; rebase onto main; re-merge
│   When: PR dirty, multiple conflicts, shared infrastructure files
│
├─ [prn] Create/Update PR  
│   Description: Ensure PR exists; enable auto-merge; gate to CI
│   When: Branch pushed; need to trigger pipeline
│
└─ [gg] Open PR on GitHub
    Description: Shorthand navigate; create PR on GitHub web
    When: Quick PR link; manual PR creation
```

### Tiếng Việt

```
fix-merge ▼
├─ [ff9] Giải quyết Merge Conflict
│   Mô tả: Auto-fix semantic; rebase lên main; re-merge
│   Khi nào: PR dirty, xung đột nhiều, file shared
│
├─ [prn] Tạo/Cập nhật PR  
│   Mô tả: Ensure PR exists; enable auto-merge; CI gate
│   Khi nào: Branch đã push; cần trigger pipeline
│
└─ [gg] Mở PR trên GitHub
    Mô tả: Shorthand navigate; tạo PR trên GitHub web
    Khi nào: Cần link PR nhanh; tạo PR thủ công
```

---

## 3. Vaccine Library Archive (Reference Structure)

Full vaccine library remains in CLAUDE.md §4 — not exposed as top-level buttons. Operator uses guide to map symptom → vaccine, then `ff` loads the FIXER:

```
VACCINE LIBRARY (CLAUDE.md §4)
├─ V1–V7: Build Errors
│  ├─ V1: HF model ID fix
│  ├─ V2: Slack notify action bump
│  ├─ V3: GitHub Actions PR permissions
│  ├─ V4: Perf audit image attributes
│  ├─ V5: configure-pages rate limit  ⚠️ (wait, concurrency)
│  ├─ V6: Bot data refresh conflict
│  └─ V7: Build failure handler self-loop
│
├─ V8–V9: Syntax & Stale Base
│  ├─ V8: Tera syntax (replace filter)
│  └─ V9: Docs stale base rebase
│
├─ V10–V12: Shared Infrastructure
│  ├─ V10: Dirty PR / merge race
│  ├─ V11: Daily Vaccine Autofixer
│  └─ V12: Semantic Conflict (base.html/footer)
│
├─ V13–V14: Content Safety
│  ├─ V13: Scheduled forward-ref (draft links)
│  └─ V14: Fabricated topic-cluster links
│
├─ V15: [EMPTY — reserved]
│
├─ V16–V17: Backend Split-Brain
│  ├─ V16: Static ↔ backend deploy mismatch
│  └─ V17: VIPZone OAuth loop + Edge/Safari
│
├─ V18–V20: Artifacts & Domain
│  ├─ V18: Runtime artifact conflict
│  ├─ V19: Domain migration drift
│  ├─ V19b: Domain selector (candidate generation)
│  └─ V20: Search UI raw/unstyled
│
├─ V21–V23: UI & Editor
│  ├─ V21: No floating bar (stable nav)
│  ├─ V22: Editor save→GitHub (publish, SEO rail)
│  ├─ V22b: Split-brain (routes 404 undeployed)
│  └─ V23: SEO Identity / homepage migration
│
├─ V24–V25: Analytics & Backend Routes
│  ├─ V24: GSC OAuth refresh token export
│  ├─ V25: Split-backend 404 (frontend route parity)
│  └─ V27: GA stats module (build-time analytics)
│
└─ V26–V29: Advanced Topics
   ├─ V26: "On This Page" TOC rail
   ├─ V28: Vaccine registry merge (conflict-safe)
   ├─ V29: External Prod Verification
   └─ Future: [V30+] to be discovered
```

### How It Works

1. Operator reports: *"PR won't merge, getting conflict in base.html"*
2. Guide maps: Symptom → **V12 (Semantic Conflict)**
3. Operator runs: `ff` → engine reads CLAUDE.md §4, loads **V12 FIXER**
4. FIXER executes: semantic merge (keep both footer blocks, merge base.html safely)
5. Result: ✓ PR merged

User **never** types "V12" as command — the vaccine number is hidden; guide + `ff` handle routing.

---

## 4. Mobile Responsive Constraint

Top-level buttons **stack vertically** on mobile ≤720px:

### Mobile (≤720px)

```
┌─────────────────────┐
│ VACCINE OPERATOR    │
│                     │
│ [fix-merge]        │
│ [fix-deploy]       │
│ [fix-seo]          │
│ [fix-ui]           │
│ [fix-gsc-ga]       │
│                     │
│ [Công cụ khác ▼]  │
│                     │
│ System Status       │
│ ⚫ QA: Pass         │
│ ⚫ Deploy: Green    │
│ 🟡 Build: 2 skip   │
└─────────────────────┘
```

---

## 5. Decision Flow Diagram

```
User reports: "PR won't merge"
    ↓
System: Load OPERATOR-QUICKSTART.md decision flow
    ↓
Match: "Merge conflict" → try [fix-merge] group
    ↓
[fix-merge] menu expands: [ff9] [prn] [gg]
    ↓
Operator picks [ff9] (conflict resolver)
    ↓
ff9 runs conflict detector:
  "Detected conflicts in base.html, sass/_footer.scss"
    ↓
ff9 matches pattern:
  "Matches V10/V12; shared infrastructure files"
    ↓
V12 FIXER executes:
  1. Merge origin/main
  2. Classify hunks: additive (keep both sections)
  3. Resolve: `.footer-categories` + `.footer-tags` both in footer
  4. Remove stale sidebar blocks
  5. QA: PASS
    ↓
Output:
  "V12 FIXER complete. PR merged ✓"
    ↓
PR merged to main ✓
Deploy triggered ✓
```

---

## 6. Escalation Path (When Shortcut Fails)

```
Shortcut [fix-seo] → check_404 reports:
  "20 internal broken links"

Check OPERATOR-QUICKSTART.md:
  "If vaccine match + fixer fails → run with --dry-run"

Run locally:
  python3 qa-404-checker.py --dry-run

Still failing? 
  Read CLAUDE.md §4 V14 (Fabricated topic-cluster links)
  
Matches V14? 
  → Manual intent-based repoint (cannot auto-fix mangled slugs)
  → Operator reviews each link + rewrites by hand
  → Commit + push → re-check

No match?
  → Open GitHub issue + log
  → Append to CLAUDE.md "Autofixer Conflict Learning Log"
  → Wait for Phase 2 (new vaccine creation)
```

---

## 7. Configuration (No Phase 1 Changes)

### `.claude/settings.json` (Inspect Only)

Current state: contains only PostToolUse hooks (SEO QA validation).

Phase 1 finding: **No shortcut alias infrastructure exists.**

Decision: Document aliases in OPERATOR-QUICKSTART.md (backward compat table) instead of modifying runtime config.

### Future Phase 2

If operator UI is built:
- Aliases may be wired via `.claude/vaccine-manifest.json` (if created)
- Settings.json may gain a `[shortcuts]` section for mapping
- Dashboard search may index V1–V29 symptoms + shortcuts

---

## 8. File Organization

```
.claude/
├─ OPERATOR-QUICKSTART.md    (this guide — decision flows)
├─ ui-layout.md               (this file — visual sketches)
└─ settings.json              (existing — NO CHANGE phase 1)

CLAUDE.md
└─ §4 Vaccine Library         (V1–V29 definitions, LOCKED)

shortcuts.md
├─ §0 Bootstrap              (read first each session)
├─ §1 Intro                  (why shortcuts exist)
├─ §2 Shortcuts (GROUPED)    (✅ Added in Phase 1)
│  ├─ Constraint comment
│  ├─ Quick-ref mapping table
│  ├─ 2.1 FIX-MERGE
│  ├─ 2.2 FIX-DEPLOY         (to be added: section headers)
│  ├─ 2.3 FIX-SEO
│  ├─ 2.4 FIX-UI
│  ├─ 2.5 FIX-GSC-GA
│  └─ 2.6 OPERATIONAL TOOLS
├─ §5 Learning Log
└─ §6 Metadata
```

---

**End of ui-layout.md**
