# GSC Deploy Preflight

`scripts/gsc_preflight.py` is a **hard deploy gate** that protects the production
deploy from a misconfigured Google Search Console property. It runs in
`deploy.yml` right after the DNS Vaccine gate.

## What it enforces

1. **Property gate (offline, always runs).** The environment variable
   `GSC_PROPERTY_URL` **must** resolve to the canonical *domain* property
   `sc-domain:seomoney.org`. A URL-prefix property (`https://seomoney.org/`), a
   different host, or an unset value **FAILS the deploy** (exit code `2`). This
   check needs no network and no Python wheels, so it never flakes.

   A domain property is required because it covers `http`/`https` and every
   subdomain/path in a single entry — the URL-prefix property does not.

2. **Live verify (only when OAuth creds are present).** If
   `GSC_REFRESH_TOKEN`, `GSC_CLIENT_ID` and `GSC_CLIENT_SECRET` are all set, the
   script also:
   - `sites.list` → confirms `sc-domain:seomoney.org` is in the account's
     verified properties and the permission level is **not** `siteUnverifiedUser`.
   - `sitemaps.list` → confirms `https://seomoney.org/sitemap.xml` is registered.
   - `searchanalytics.query` → a **7-day** smoke fetch to confirm the analytics
     endpoint answers for the property.

   Any failure here also fails the deploy (exit code `2`).

## Security

The script **never logs credentials**. Output is limited to booleans, the
property string, the sitemap URL, and aggregate impression/click counts. OAuth
secrets are read from the environment and handed straight to the Google client;
on error only the exception *type* is printed (no message that could echo a
token).

## Required GitHub secrets

| Secret | Value |
| --- | --- |
| `GSC_PROPERTY_URL` | `sc-domain:seomoney.org` |
| `GSC_REFRESH_TOKEN` | OAuth refresh token (live verify) |
| `GSC_CLIENT_ID` | OAuth client id (live verify) |
| `GSC_CLIENT_SECRET` | OAuth client secret (live verify) |

If the OAuth secrets are absent, the live verify is **skipped** (with a `SKIP`
line) but the offline property gate still runs — so the deploy is never blocked
just because metrics secrets are not wired, yet a wrong property value always
blocks it.

## Usage

```bash
# Offline property gate only (no network / no google wheels)
python3 scripts/gsc_preflight.py --gate-only

# Gate + live verify when creds are in the environment
python3 scripts/gsc_preflight.py

# Make live verification mandatory (fail if creds missing)
python3 scripts/gsc_preflight.py --require-live
```

## Tests

```bash
python3 -m unittest scripts.test_gsc_preflight scripts.test_gsc_client -v
```

The test suite covers property normalization, the gate decision matrix, the CLI
exit codes, and a guard that keeps the inlined constants in sync with
`services/visitor-counter/gsc_client.py` (`EXPECTED_GSC_PROPERTY`,
`EXPECTED_SITEMAP_URL`).
