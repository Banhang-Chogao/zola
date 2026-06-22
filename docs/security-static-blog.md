# Static Blog Security — what is and isn't real

> TL;DR **Static-site security = do not publish secrets or private docs.**
> Hidden menu entries, client-side "auth", and `robots.txt` are **not** access
> control. A static host (Zola → GitHub Pages) serves every published byte to
> anyone who knows the URL.

This is the operating doctrine behind `scripts/security_public_audit.py`, the
public-surface security gate that runs with QA.

## The one rule that matters

Everything under these paths is **public the moment it deploys**:

- `content/` — every page, draft, and asset Zola renders
- `static/` — copied verbatim to the site root (`static/x.html` → `/x.html`)
- `public/` — the built output that is uploaded to GitHub Pages
- `sitemap.xml` + the `config.toml` menu — links that advertise URLs

So the only real control is **don't put the secret/private file there.**

## What is NOT real security (common traps)

| Looks protective | Reality on a static host |
|---|---|
| Removing a link from the menu | File still served at its URL; just unlinked |
| `robots.txt` `Disallow:` | A crawl *hint*. Humans/bad bots ignore it; the file is still public |
| Client-side / JS "login" gate | All JS + gated content already shipped to the browser |
| "Hidden" `static/…` admin page | Public URL; discoverable via sitemap, history, guessing |
| Obfuscated/minified secret in JS | Still readable; minification ≠ encryption |

Real protection lives **server-side** (the FastAPI backends on Render gate
premium content, CMS auth, GSC, etc.) or **at the edge** (Cloudflare WAF/rate
limiting). The static layer's job is simply: ship nothing private.

## Safe convention for private/internal docs

Keep operator/ops material **outside the build paths** (`content/`, `static/`):

- `ops/` — operator runbooks, cheat-sheets (e.g. `ops/vaccine-cheat-sheet.html`)
- `docs/`, `docs/private/` — engineering + private notes (`docs/private/` is git-ignored)
- `_private/`, `shortcuts/private/` — anything else internal
- root docs (`CLAUDE.md`, `shortcuts.md`, `MANU9.md`, `SECURITY-GUIDE.md`) are
  fine **only** because Zola never builds the repo root — never copy them into
  `content/` or `static/`.

**Downloadables:** only files that are explicitly public-safe may be offered for
download — name them `*-public.md` or mark frontmatter `public_safe = true`.
Anything else stays out of `static/` / `content/`.

## The gate — `scripts/security_public_audit.py`

Fails the build (exit 1) when the public surface exposes:

- **Private/internal files by name/type:** `CLAUDE.md`, `operation-guide.md`,
  `shortcut(s).md`, `admin-rules.md`, `.env*`, `.key`, `.pem`, `.sqlite`, `.db`,
  `.bak`, `.zip`, …
- **Internal ops/operator docs** in `static/`/`public/` (cheat-sheet, runbook, …)
- **Real secret values** anywhere (`ghp_…`, `github_pat_…`, `AKIA…`, `sk-…`,
  Slack `xox…`, `GOCSPX-…`, `-----BEGIN … PRIVATE KEY-----`)
- **Secret-looking assignments** in infra files (`api_key = "…"`, `password: "…"`)
- **Local machine paths** in infra files (`/Users/<name>/`, `/home/<name>/`, `~/…`)
- **Sitemap / menu links** that point at any of the above

### Calibration (why it doesn't cry wolf)

This is a real tech/SEO blog: articles legitimately *mention* `API_KEY`,
`PASSWORD`, `TOKEN`, etc. in tutorials. The gate therefore **never flags bare
keywords**. It only flags real secret *formats* (everywhere) and secret
*assignments* / local paths in **infra files** (`static/`, built `public/`) —
not in `content/*.md` prose. Documented placeholders (`YOUR_API_KEY`, `xxx`,
`<token>`) and generic paths (`/home/user/`, `/home/runner/`) are allowed.

### Run it

```bash
python3 scripts/security_public_audit.py            # full: + built public/ + sitemap
python3 scripts/security_public_audit.py --no-public # source-only (content/ + static/)
python3 scripts/security_public_audit.py --json      # machine-readable
python3 -m unittest scripts.test_security_public_audit -v
```

It also runs automatically:

- inside `python3 qa_check.py` (source-surface, early local signal), and
- as a dedicated **QA Gatekeeper** step in `.github/workflows/qa.yml` after the
  Zola build (full scan incl. `public/` + `sitemap.xml`) → blocks merge/deploy.

## HTTP security headers

GitHub Pages cannot set custom response headers, so the **active** layer is the
`<meta http-equiv>` set in `templates/base.html` (CSP, `X-Content-Type-Options:
nosniff`, `X-Frame-Options: DENY`, referrer policy). `static/_headers`
additionally declares `Permissions-Policy` and re-states the safe headers using
the Netlify/Cloudflare-Pages `_headers` convention — inert on GitHub Pages, and
applied automatically if the site is ever fronted by an edge that reads it. None
of these change any visible UI.

## If the gate fails

1. **A real secret leaked** → rotate it, remove it from the public surface, and
   purge it from git history if it was ever committed (`git filter-repo`).
2. **A private/ops doc is public** → move it to `ops/` / `docs/` / `_private/`.
3. **A false positive** → tighten the pattern or add a documented allowlist
   entry in `scripts/security_public_audit.py` and a test asserting it stays
   green. Never weaken the gate just to pass.
