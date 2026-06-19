# V17 — VIPZone Edge/Safari Auth + Content Picker

**Date:** 2026-06-20  
**Scope:** `services/vipzone/`, `static/js/vip-admin.js`, `static/js/vipzone.js`

## Symptom

- VIPZone Admin (`/tools/vipzone-admin/`) stuck in OAuth redirect loop on Edge/Safari.
- `GET /auth/me` or `/api/vipzone/me` returns `401 missing_token` after successful GitHub login.
- Content Picker panel hidden or never rendered when role detection fails.
- SUPER_ADMIN button on `/tools/vipzone/` disappears for authenticated non-super users.

## Root cause

1. **Fragment-only session** — OAuth callback set `#sid=` but `vip-admin.js` read only `sessionStorage`, which Edge/Safari/ITP clears aggressively.
2. **No cross-site cookie** — Static site (GitHub Pages) and API (Render) are different origins; Bearer-only auth with `credentials:omit` cannot use HttpOnly cookies.
3. **Over-restrictive callback** — `auth_callback` rejected non-repo-admin users (`access_denied`), causing retry loops for valid VIP users.
4. **UI gated on role** — `vip-admin.js` called `showView("denied")` / hid app shell when `isSuperuser()` failed, hiding Content Picker entirely.

## Fix (minimal)

### Backend (`services/vipzone/cms_auth.py`)

- Set session cookie on callback: `zola_cms_sid`, `HttpOnly`, `Secure`, `SameSite=None`, `path=/`.
- Redirect with `?auth=success` + `#sid=` (backward compatible).
- Accept session from **Bearer OR cookie** via `resolve_sid()` / `session_dep`.
- Allow all verified GitHub users to create session; assign role by VIP row + superadmin rules.
- Clear cookie on `/auth/logout`.

### Roles (`services/vipzone/roles.py`)

- `SUPERADMIN_EMAIL = tamsudev.com@gmail.com` (env override `SUPERADMIN_EMAIL`).
- `email_is_superadmin()` checked in `is_superadmin()` and at OAuth callback.

### Frontend (`static/js/vip-admin.js`)

- `getSid()`: `sessionStorage` + `localStorage` mirror (same as `base.html` bootstrap).
- All API fetches: `credentials: "include"`.
- Always `showView("app")`; Content Picker always loads.
- Disable admin actions (save picker, create code, resolve payments) when `role !== superadmin` and not `is_admin`.
- Guest fallback object — never throw on auth failure.
- `fetchMe()` uses `/api/vipzone/me` (not `/auth/login` loop).

### Frontend (`static/js/vipzone.js`)

- `credentials: "include"` on auth/API fetches.
- SUPER_ADMIN shortcut stays visible for superadmin; shortcut (not hidden) for others.

### CORS (`services/vipzone/main.py`)

- `allow_credentials=True` (required for cookie auth).

## Prevention / detector

- QA Vaccine Gate: `check_v17_vipzone_edge_safari_auth` in `scripts/qa_vaccines.py`.
- CLAUDE.md index: `#### V17 — …` (short); this file holds full detail.

## Validation

```bash
python3 -m unittest services.vipzone.test_main scripts.test_vipzone_roles -v
python3 scripts/qa_vaccines.py | grep V17
node --check static/js/vip-admin.js
node --check static/js/vipzone.js
```

## Deploy note

Backend changes require Render Manual Sync (`blog-vipzone-api`) before cookie auth works in production (V16 family).