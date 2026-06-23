#!/usr/bin/env node
/**
 * seo_engine.js — SEO Priority Engine for Zola blogs
 *
 * AUDIT (default — on-page scoring of markdown source):
 *   node seo_engine.js                        scan ./content
 *   node seo_engine.js content/post.md        score one file
 *   node seo_engine.js --dir ./content        custom directory
 *   node seo_engine.js --json                 write seo-report.json
 *   node seo_engine.js --min 70               show posts below 70
 *   node seo_engine.js --sort score           sort worst-first
 *
 * FIX (dry-run unless --write is explicitly passed):
 *   node seo_engine.js --fix                          propose fixes (dry-run)
 *   node seo_engine.js --fix --target content/x.md   one file only
 *   node seo_engine.js --fix --report                 before/after diff
 *   node seo_engine.js --fix --write --target x.md   APPLY to one file
 *   node seo_engine.js --fix --write                  APPLY to all
 *
 * PRIORITY (GSC-powered ranking — reads GSC_CREDENTIALS + GSC_SITE_URL env vars):
 *   node seo_engine.js --priority             score = 40%imp+25%click+15%CTR+10%fresh+10%links
 *   node seo_engine.js --priority --json      also write data/tiers.json
 *   Fallback (no GSC creds): freshness 50% + internal-links 50% only.
 *
 * QA GATEKEEPER (exits 1 on any failure — run before or after zola build):
 *   node seo_engine.js --qa                   full QA gate
 *   node seo_engine.js --qa --public ./public target a custom build dir
 *   FAIL conditions:
 *     • Any /tags/* page is indexable (missing noindex) in built HTML or sitemap
 *     • Any article is missing title, H1-equivalent heading, or meta description
 *     • Any article has a broken internal link (path not resolvable in content/ or public/)
 *     • Any built HTML page is missing <link rel="canonical">
 *
 * Env vars:
 *   GSC_CREDENTIALS   JSON string of a Google service-account key (webmasters.readonly scope)
 *   GSC_SITE_URL      verified property URL, e.g. "https://seomoney.org/"
 *
 * Guards:
 *   • --fix alone     = dry-run, nothing written
 *   • --write requires --fix
 *   • applyPatches()  only touches description field + img alt — never body prose
 *   • H2 suggestions  = report-only, never auto-inserted
 *   • No external API calls except explicit --priority (GSC)
 *   • No fake/hardcoded data — all signals derived from real content or live GSC
 */

import { readFileSync, readdirSync, statSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { join, basename, extname, relative, resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { createSign } from 'crypto';
import { request as httpsReq } from 'https';

const __dirname = fileURLToPath(new URL('.', import.meta.url));

// ─── On-page scoring weights (total = 100) ────────────────────────────────────
const W = {
  title_present:  8,
  title_length:   6,
  description:   10,
  slug:           6,
  kw_title:       8,
  kw_intro:       6,
  kw_heading:     6,
  headings:       8,
  word_count:    10,
  og_image:       6,
  img_alt:        6,
  internal_link:  6,
  external_link:  4,
  tags:           4,
  date:           3,
  readability:    3,
};

// ─── Priority score weights (must sum to 1.0) ─────────────────────────────────
const PW = {
  impressions:    0.40,
  clicks:         0.25,
  ctr:            0.15,
  freshness:      0.10,
  internal_links: 0.10,
};

// ─── Thresholds ───────────────────────────────────────────────────────────────
const TITLE_MIN  = 20,  TITLE_MAX  = 65;
const DESC_MIN   = 50,  DESC_MAX   = 160;
const DESC_TARGET = 145;
const SLUG_MAX   = 60;
const WORDS_GOOD = 600, WORDS_OK   = 300;
const TIER1_SIZE = 20,  TIER2_SIZE = 50;
const FRESH_MAX_DAYS = 730; // posts older than 2 years get freshness = 0

// ─── ANSI colours ─────────────────────────────────────────────────────────────
const C = {
  reset:  '\x1b[0m',  bold:  '\x1b[1m',   dim:  '\x1b[2m',
  red:    '\x1b[31m', yellow:'\x1b[33m',  green:'\x1b[32m',
  cyan:   '\x1b[36m', blue:  '\x1b[34m',  grey: '\x1b[90m',
  white:  '\x1b[97m', magenta:'\x1b[35m',
};
const colour  = s => s >= 80 ? C.green : s >= 60 ? C.yellow : C.red;
const tierCol = t => t === 1 ? C.green : t === 2 ? C.yellow : C.grey;
const bar = (score, w = 20) => {
  const f = Math.round((score / 100) * w);
  return `[${'█'.repeat(f)}${'░'.repeat(w - f)}]`;
};

// ─── HTTPS helpers (no npm, stdlib only) ──────────────────────────────────────
function httpsPost(url, data, extraHeaders = {}) {
  return new Promise((res, rej) => {
    const body   = typeof data === 'string' ? data : new URLSearchParams(data).toString();
    const parsed = new URL(url);
    const opts   = {
      hostname: parsed.hostname,
      path:     parsed.pathname + parsed.search,
      method:   'POST',
      headers:  {
        'Content-Type':   'application/x-www-form-urlencoded',
        'Content-Length': Buffer.byteLength(body),
        ...extraHeaders,
      },
    };
    const req = httpsReq(opts, r => {
      let d = '';
      r.on('data', c => d += c);
      r.on('end',  () => { try { res(JSON.parse(d)); } catch { res(d); } });
    });
    req.on('error', rej);
    req.write(body);
    req.end();
  });
}

function httpsGet(url, headers = {}) {
  return new Promise((res, rej) => {
    const parsed = new URL(url);
    const opts   = { hostname: parsed.hostname, path: parsed.pathname + parsed.search, headers };
    httpsReq(opts, r => {
      let d = '';
      r.on('data', c => d += c);
      r.on('end',  () => { try { res(JSON.parse(d)); } catch { res(d); } });
    }).on('error', rej).end();
  });
}

function httpsPostJson(url, payload, headers = {}) {
  return new Promise((res, rej) => {
    const body   = JSON.stringify(payload);
    const parsed = new URL(url);
    const opts   = {
      hostname: parsed.hostname,
      path:     parsed.pathname + parsed.search,
      method:   'POST',
      headers:  { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body), ...headers },
    };
    const req = httpsReq(opts, r => {
      let d = '';
      r.on('data', c => d += c);
      r.on('end',  () => { try { res(JSON.parse(d)); } catch { res(d); } });
    });
    req.on('error', rej);
    req.write(body);
    req.end();
  });
}

// ─── GSC API client (service-account JWT, no external packages) ───────────────
/**
 * Build and sign a Google service-account JWT, then exchange for an access token.
 * credentials = parsed JSON of a GCP service-account key file.
 */
async function getGscToken(credentials) {
  const now = Math.floor(Date.now() / 1000);
  const header  = Buffer.from(JSON.stringify({ alg: 'RS256', typ: 'JWT' })).toString('base64url');
  const payload = Buffer.from(JSON.stringify({
    iss:   credentials.client_email,
    scope: 'https://www.googleapis.com/auth/webmasters.readonly',
    aud:   'https://oauth2.googleapis.com/token',
    exp:   now + 3600,
    iat:   now,
  })).toString('base64url');

  const sign = createSign('RSA-SHA256');
  sign.update(`${header}.${payload}`);
  const sig = sign.sign(credentials.private_key, 'base64url');
  const jwt = `${header}.${payload}.${sig}`;

  const resp = await httpsPost('https://oauth2.googleapis.com/token', {
    grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer',
    assertion:  jwt,
  });

  if (!resp.access_token) {
    throw new Error(`GSC token error: ${JSON.stringify(resp)}`);
  }
  return resp.access_token;
}

/**
 * Fetch last `days` days of Search Analytics data from GSC.
 * Returns an array of { page, clicks, impressions, ctr, position }.
 * All page URLs are returned as-is from GSC (absolute URLs).
 */
async function fetchGscData(siteUrl, token, days = 90) {
  const endDate   = new Date();
  const startDate = new Date(endDate - days * 86400_000);
  const fmt = d => d.toISOString().split('T')[0];

  const data = await httpsPostJson(
    `https://searchconsole.googleapis.com/v1/sites/${encodeURIComponent(siteUrl)}/searchAnalytics/query`,
    {
      startDate:   fmt(startDate),
      endDate:     fmt(endDate),
      dimensions:  ['page'],
      rowLimit:    5000,
      dataState:   'all',
    },
    { Authorization: `Bearer ${token}` },
  );

  if (!data.rows) return [];
  return data.rows.map(r => ({
    page:        r.keys[0],
    clicks:      r.clicks      ?? 0,
    impressions: r.impressions ?? 0,
    ctr:         r.ctr         ?? 0,
    position:    r.position    ?? 100,
  }));
}

/**
 * Load GSC credentials from env. Returns null + prints warning if missing.
 */
function loadGscCredentials() {
  const raw     = process.env.GSC_CREDENTIALS || '';
  const siteUrl = (process.env.GSC_SITE_URL || '').replace(/\/$/, '') + '/';
  if (!raw) return null;
  try {
    const creds = JSON.parse(raw);
    if (!creds.private_key || !creds.client_email) throw new Error('missing fields');
    return { creds, siteUrl };
  } catch (e) {
    console.warn(`${C.yellow}⚠ GSC_CREDENTIALS parse error: ${e.message} — falling back to offline scoring${C.reset}`);
    return null;
  }
}

// ─── Priority score calculator ────────────────────────────────────────────────
/** Min-max normalize an array of numbers to [0, 1]. */
function minMax(values) {
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (max === min) return values.map(() => 0.5);
  return values.map(v => (v - min) / (max - min));
}

/** Days since a date string (YYYY-MM-DD). Returns FRESH_MAX_DAYS if unparseable. */
function daysSince(dateStr) {
  if (!dateStr) return FRESH_MAX_DAYS;
  const d = new Date(dateStr);
  if (isNaN(d)) return FRESH_MAX_DAYS;
  return Math.max(0, Math.floor((Date.now() - d.getTime()) / 86400_000));
}

/**
 * Compute priority scores for all scored results.
 * gscMap: Map<string pageUrl, {clicks, impressions, ctr}> or null (fallback mode).
 * siteUrl: base URL for matching GSC page URLs to local slugs.
 */
function calcPriorityScores(results, gscMap, siteUrl) {
  const hasGsc = gscMap && gscMap.size > 0;

  // Attach raw signal values to each result
  const enriched = results.map(r => {
    const slug     = r.slug;
    const freshDays = daysSince(r.meta.date || '');

    let clicks = 0, impressions = 0, ctr = 0;
    if (hasGsc) {
      // Try to match by slug — GSC page URLs may be absolute
      for (const [url, row] of gscMap) {
        if (url.includes(slug) || url.endsWith(`/${slug}/`) || url.endsWith(`/${slug}`)) {
          clicks      = row.clicks;
          impressions = row.impressions;
          ctr         = row.ctr;
          break;
        }
      }
    }

    return {
      ...r,
      _signals: {
        impressions,
        clicks,
        ctr,
        freshDays,
        internalLinks: r.meta.internalLinks,
      },
    };
  });

  // Normalise each signal across all posts
  const imps   = minMax(enriched.map(r => r._signals.impressions));
  const clicks = minMax(enriched.map(r => r._signals.clicks));
  const ctrs   = minMax(enriched.map(r => r._signals.ctr));
  // Fresher = higher score → invert days
  const freshs  = minMax(enriched.map(r => Math.max(0, FRESH_MAX_DAYS - r._signals.freshDays)));
  const intLinks = minMax(enriched.map(r => r._signals.internalLinks));

  enriched.forEach((r, i) => {
    let priority;
    if (hasGsc) {
      priority =
        PW.impressions    * imps[i]     +
        PW.clicks         * clicks[i]   +
        PW.ctr            * ctrs[i]     +
        PW.freshness      * freshs[i]   +
        PW.internal_links * intLinks[i];
    } else {
      // Offline fallback: freshness + internal links only (sum weights = 0.20, rescale to 1.0)
      priority = 0.5 * freshs[i] + 0.5 * intLinks[i];
      r._gscFallback = true;
    }
    r.priority = Math.round(priority * 1000) / 10; // 0–100 scale
  });

  // Sort by priority desc and assign tiers
  enriched.sort((a, b) => b.priority - a.priority);
  enriched.forEach((r, i) => {
    r.tier = i < TIER1_SIZE ? 1 : i < TIER2_SIZE ? 2 : 3;
    r.rank = i + 1;
  });

  return enriched;
}

// ─── Front matter parser ──────────────────────────────────────────────────────
function parseFrontMatter(src) {
  const toml = src.match(/^\+\+\+\r?\n([\s\S]*?)\r?\n\+\+\+\r?\n?([\s\S]*)$/);
  if (toml) return { fm: parseToml(toml[1]), body: toml[2], type: 'toml', rawFm: toml[1] };
  const yaml = src.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/);
  if (yaml) return { fm: parseYaml(yaml[1]), body: yaml[2], type: 'yaml', rawFm: yaml[1] };
  return { fm: {}, body: src, type: null, rawFm: '' };
}

function parseToml(raw) {
  const result = {};
  let section = result;
  for (const line of raw.split('\n')) {
    const t = line.trim();
    if (!t || t.startsWith('#')) continue;
    const sec = t.match(/^\[(\w[\w.]*)\]$/);
    if (sec) {
      const parts = sec[1].split('.');
      let cur = result;
      for (const p of parts) { cur[p] = cur[p] || {}; cur = cur[p]; }
      section = cur;
      continue;
    }
    const eq = t.indexOf('=');
    if (eq === -1) continue;
    section[t.slice(0, eq).trim()] = parseTomlValue(t.slice(eq + 1).trim());
  }
  return result;
}

function parseTomlValue(v) {
  if (v === 'true')  return true;
  if (v === 'false') return false;
  if (v.startsWith('"') || v.startsWith("'")) return v.slice(1, -1);
  if (v.startsWith('['))
    return v.slice(1, -1).split(',').map(s => s.trim().replace(/^["']|["']$/g, '')).filter(Boolean);
  const n = Number(v);
  return isNaN(n) ? v.replace(/^["']|["']$/g, '') : n;
}

function parseYaml(raw) {
  const result = {};
  const lines  = raw.split('\n');
  let i = 0;
  while (i < lines.length) {
    const m = lines[i].match(/^(\w[\w-]*):\s*(.*)/);
    if (!m) { i++; continue; }
    const [, key, rest] = m;
    const r = rest.trim();
    if (r === '' || r === '|' || r === '>') {
      const items = [];
      i++;
      while (i < lines.length && /^\s+-\s/.test(lines[i]))
        items.push(lines[i++].replace(/^\s+-\s+/, '').trim().replace(/^["']|["']$/g, ''));
      result[key] = items.length ? items : '';
    } else if (r.startsWith('[')) {
      result[key] = r.slice(1, -1).split(',').map(s => s.trim().replace(/^["']|["']$/g, '')).filter(Boolean);
      i++;
    } else {
      result[key] = r.replace(/^["']|["']$/g, '');
      i++;
    }
  }
  return result;
}

// ─── Text helpers ─────────────────────────────────────────────────────────────
function stripMarkdown(text) {
  return text
    .replace(/```[\s\S]*?```/g, '')
    .replace(/`[^`]+`/g, ' ')
    .replace(/!\[[^\]]*\]\([^)]+\)/g, '')
    .replace(/\[[^\]]+\]\([^)]+\)/g, ' ')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/[*_~>|]/g, '')
    .replace(/<!--[\s\S]*?-->/g, '');
}

const wordCount      = t => stripMarkdown(t).trim().split(/\s+/).filter(Boolean).length;
const avgSentenceLen = t => {
  const s = stripMarkdown(t).split(/[.!?]+/).filter(s => s.trim());
  if (!s.length) return 0;
  return s.map(x => x.trim().split(/\s+/).filter(Boolean).length).reduce((a, b) => a + b, 0) / s.length;
};

function firstParagraph(body) {
  const paras = []; let cur = [];
  for (const line of body.split('\n')) {
    const t = line.trim();
    if (!t) { if (cur.length) { paras.push(cur.join(' ')); cur = []; } }
    else if (/^#{1,6}\s/.test(t) || /^[>|-]/.test(t) || /^```/.test(t))
      { if (cur.length) { paras.push(cur.join(' ')); cur = []; } }
    else cur.push(t);
  }
  if (cur.length) paras.push(cur.join(' '));
  for (const p of paras) { const pl = stripMarkdown(p).trim(); if (pl.length >= 40) return pl; }
  return '';
}

function deriveAltFromPath(p) {
  return p.split('/').pop().split('?')[0].replace(/\.[^.]+$/, '').replace(/[-_]+/g, ' ').trim();
}

// ─── On-page scorer ───────────────────────────────────────────────────────────
function scoreFile(filepath) {
  const src  = readFileSync(filepath, 'utf-8');
  const { fm, body } = parseFrontMatter(src);
  const slug = basename(filepath, extname(filepath));

  const extra = fm.extra || {};
  const title = String(fm.title || '').trim();
  const desc  = String(fm.description || extra.description || '').trim();
  const kw    = String(extra.seo_keyword || extra.keyword || '').trim().toLowerCase();
  const ogImg = extra.thumbnail || extra.og_image || fm.cover_image || '';
  const tags  = Array.isArray(fm.taxonomies?.tags) ? fm.taxonomies.tags
              : Array.isArray(fm.tags) ? fm.tags : [];
  const date  = fm.date || fm.published || '';

  const intro  = body.split('\n').filter(l => l.trim() && !l.startsWith('#')).slice(0, 5).join(' ');
  const h2s    = (body.match(/^##\s+.+$/gm) || []).map(h => h.replace(/^#+\s+/, '').toLowerCase());
  const imgs   = [...body.matchAll(/!\[([^\]]*)\]\([^)]+\)/g)];
  const links  = [...body.matchAll(/\[([^\]]+)\]\(([^)]+)\)/g)];
  const intL   = links.filter(m => !m[2].startsWith('http'));
  const extL   = links.filter(m => m[2].startsWith('http'));
  const altOk  = imgs.filter(m => m[1].trim().length > 0);
  const wc     = wordCount(body);
  const avgSL  = avgSentenceLen(body);
  const h1c    = (body.match(/^#\s+.+$/gm) || []).length;
  const h2c    = (body.match(/^##\s+.+$/gm) || []).length;

  const scores = {};
  const notes  = [];

  // title
  if (title)                                 { scores.title_present = W.title_present; }
  else                                       { scores.title_present = 0; notes.push('✗ Missing title'); }
  if      (title.length >= TITLE_MIN && title.length <= TITLE_MAX) scores.title_length = W.title_length;
  else if (title.length > 0)                 { scores.title_length = Math.round(W.title_length * 0.5); notes.push(`△ Title ${title.length} chars (ideal ${TITLE_MIN}–${TITLE_MAX})`); }
  else                                         scores.title_length = 0;

  // description
  if      (desc.length >= DESC_MIN && desc.length <= DESC_MAX) scores.description = W.description;
  else if (desc.length > 0)                  { scores.description = Math.round(W.description * 0.5); notes.push(`△ Description ${desc.length} chars (ideal ${DESC_MIN}–${DESC_MAX})`); }
  else                                       { scores.description = 0; notes.push('✗ Missing meta description'); }

  // slug
  if      (slug.length <= SLUG_MAX && /^[a-z0-9-]+$/.test(slug)) scores.slug = W.slug;
  else if (slug.length <= SLUG_MAX)          { scores.slug = Math.round(W.slug * 0.7); notes.push(`△ Slug has non-ascii chars`); }
  else                                       { scores.slug = Math.round(W.slug * 0.5); notes.push(`△ Slug too long (${slug.length})`); }

  // keyword signals
  if (!kw)                                      { scores.kw_title = W.kw_title * 0.5; scores.kw_intro = W.kw_intro * 0.5; scores.kw_heading = W.kw_heading * 0.5; }
  else {
    scores.kw_title   = title.toLowerCase().includes(kw) ? W.kw_title   : (notes.push(`✗ Keyword "${kw}" not in title`),   0);
    scores.kw_intro   = intro.toLowerCase().includes(kw) ? W.kw_intro   : (notes.push(`✗ Keyword "${kw}" not in intro`),   0);
    scores.kw_heading = h2s.some(h => h.includes(kw))   ? W.kw_heading : (notes.push(`△ Keyword "${kw}" not in any H2`),  0);
  }

  // headings
  if      (h2c >= 2 && h1c <= 1) scores.headings = W.headings;
  else if (h2c >= 1)              { scores.headings = Math.round(W.headings * 0.6); notes.push(`△ H1=${h1c} H2=${h2c} (recommend ≥2 H2, ≤1 H1)`); }
  else                            { scores.headings = 0; notes.push('✗ No H2 headings'); }

  // word count
  if      (wc >= WORDS_GOOD) scores.word_count = W.word_count;
  else if (wc >= WORDS_OK)   { scores.word_count = Math.round(W.word_count * 0.6); notes.push(`△ ${wc} words (good ≥${WORDS_GOOD})`); }
  else                       { scores.word_count = 0; notes.push(`✗ Too short: ${wc} words`); }

  // og image
  if (ogImg) scores.og_image = W.og_image;
  else       { scores.og_image = 0; notes.push('✗ Missing OG/thumbnail image'); }

  // img alt
  if      (imgs.length === 0)                scores.img_alt = Math.round(W.img_alt * 0.5);
  else                                       { const r = altOk.length / imgs.length; scores.img_alt = Math.round(W.img_alt * r); if (r < 1) notes.push(`△ ${imgs.length - altOk.length}/${imgs.length} images missing alt`); }

  // links
  if      (intL.length >= 3) scores.internal_link = W.internal_link;
  else if (intL.length >= 1) { scores.internal_link = Math.round(W.internal_link * 0.6); notes.push(`△ Only ${intL.length} internal link(s)`); }
  else                       { scores.internal_link = 0; notes.push('✗ No internal links'); }

  if (extL.length >= 1) scores.external_link = W.external_link;
  else                  { scores.external_link = Math.round(W.external_link * 0.5); notes.push('△ No external links'); }

  // tags
  if      (tags.length >= 3) scores.tags = W.tags;
  else if (tags.length >= 1) { scores.tags = Math.round(W.tags * 0.6); notes.push(`△ Only ${tags.length} tag(s)`); }
  else                       { scores.tags = 0; notes.push('✗ No tags defined'); }

  // date
  scores.date = date ? W.date : (notes.push('✗ No publication date'), 0);

  // readability
  if      (avgSL > 0 && avgSL <= 20) scores.readability = W.readability;
  else if (avgSL <= 30)               { scores.readability = Math.round(W.readability * 0.6); notes.push(`△ Avg sentence ${avgSL.toFixed(1)} words`); }
  else                                { scores.readability = 0; notes.push(`✗ Sentences too long (${avgSL.toFixed(1)} words avg)`); }

  return {
    file: filepath, slug,
    title: title || '(no title)',
    keyword: kw || null,
    total: Math.min(100, Math.round(Object.values(scores).reduce((a, b) => a + b, 0))),
    scores, notes,
    meta: { words: wc, tags: tags.length, images: imgs.length, internalLinks: intL.length, externalLinks: extL.length, desc, title, h2count: h2c, h1count: h1c, imagesWithAlt: altOk.length, date },
  };
}

// ─── Fix engine ───────────────────────────────────────────────────────────────
function generateFixes(filepath, result) {
  const src  = readFileSync(filepath, 'utf-8');
  const { fm, body, type: fmType, rawFm } = parseFrontMatter(src);

  const patches = [], h2suggestions = [], titleNote = [];
  const desc    = result.meta.desc;
  const title   = result.meta.title === '(no title)' ? '' : result.meta.title;
  const keyword = result.keyword || '';

  // 1. Description
  if (!desc || desc.length < DESC_MIN) {
    const para = firstParagraph(body);
    if (para.length >= DESC_MIN) {
      let proposed = para.length > DESC_TARGET
        ? para.slice(0, DESC_TARGET).replace(/\s+\S+$/, '').trim()
        : para;
      if (!proposed.endsWith('.')) proposed += '.';
      proposed = proposed.replace(/[,;:]$/, '.').trim();
      if (proposed.length >= DESC_MIN && proposed.length <= DESC_MAX)
        patches.push({ type: 'description', was: desc || '(empty)', proposed,
          reason: !desc ? 'Missing description — extracted from first paragraph.'
                        : `Description too short (${desc.length} chars) — extended.` });
    }
  }

  // 2. Image alt text
  const bodyLines = body.split('\n');
  let lastH = title, charPos = 0;
  const lineStarts = bodyLines.map(l => { const s = charPos; charPos += l.length + 1; return s; });
  const lineH = bodyLines.map(l => { const m = l.match(/^#{1,3}\s+(.+)$/); if (m) lastH = m[1].replace(/[*_`]/g, '').trim(); return lastH; });

  const imgRx = /!\[([^\]]*)\]\(([^)]+)\)/g;
  let m; const imgPatches = [];
  while ((m = imgRx.exec(body)) !== null) {
    if (m[1].trim()) continue;
    const imgPath = m[2].split(' ')[0];
    let imgLine   = 0;
    for (let i = 0; i < lineStarts.length; i++) { if (lineStarts[i] > m.index) break; imgLine = i; }
    const nearH   = lineH[imgLine] || title;
    let alt       = deriveAltFromPath(imgPath);
    if (alt.length < 10 && nearH)                                     alt = nearH;
    else if (alt.length > 0 && nearH && alt.toLowerCase() !== nearH.toLowerCase()) {
      const c = `${alt} — ${nearH}`; if (c.length <= 120) alt = c;
    }
    alt = alt.replace(/\s{2,}/g, ' ').trim().slice(0, 120);
    if (alt.length >= 3) imgPatches.push({ original: m[0], replacement: `![${alt}](${m[2]})`, alt, path: imgPath });
  }
  if (imgPatches.length)
    patches.push({ type: 'img_alt', patches: imgPatches, reason: `${imgPatches.length} image(s) missing alt text.` });

  // 3. H2 suggestions (report-only)
  if (result.meta.h2count < 2) {
    let inCode = false, buf = [], sugg = [];
    for (const line of bodyLines) {
      if (line.startsWith('```')) { inCode = !inCode; continue; }
      if (inCode) continue;
      if (/^#{1,6}\s/.test(line)) { buf = []; continue; }
      if (!line.trim()) {
        if (buf.length) {
          const text = stripMarkdown(buf.join(' ')).trim();
          if (text.split(/\s+/).length >= 40 && sugg.length < 3) {
            const s = text.split(/[.!?]/)[0].trim();
            if (s.length >= 15 && s.length <= 80) sugg.push(`## ${s}`);
          }
          buf = [];
        }
        continue;
      }
      buf.push(line.trim());
    }
    h2suggestions.push(...sugg);
  }

  // 4. Title notes
  if      (title.length > TITLE_MAX)  titleNote.push(`Title ${title.length} chars (max ${TITLE_MAX})`);
  else if (title.length && title.length < TITLE_MIN) titleNote.push(`Title only ${title.length} chars (min ${TITLE_MIN})`);

  return { patches, h2suggestions, titleNote, fmType, rawFm, src, body };
}

function applyPatches(filepath, fixes) {
  const { patches, fmType, rawFm } = fixes;
  let newFm = rawFm, newBody = fixes.body, changed = false;

  for (const p of patches) {
    if (p.type === 'description') {
      const esc = p.proposed.replace(/"/g, '\\"');
      if (fmType === 'toml') {
        newFm = /^description\s*=/m.test(newFm)
          ? newFm.replace(/^(description\s*=\s*).*$/m, `description = "${esc}"`)
          : newFm.replace(/^(title\s*=.*$)/m, `$1\ndescription = "${esc}"`);
      } else if (fmType === 'yaml') {
        newFm = /^description:/m.test(newFm)
          ? newFm.replace(/^(description:\s*).*$/m, `description: "${esc}"`)
          : newFm.replace(/^(title:.*$)/m, `$1\ndescription: "${esc}"`);
      }
      changed = true;
    }
    if (p.type === 'img_alt') {
      for (const ip of p.patches) { newBody = newBody.replace(ip.original, ip.replacement); changed = true; }
    }
  }
  if (!changed) return null;
  if (fmType === 'toml') return `+++\n${newFm}\n+++\n${newBody}`;
  if (fmType === 'yaml') return `---\n${newFm}\n---\n${newBody}`;
  return newBody;
}

function printDiff(filepath, fixes) {
  const { patches, h2suggestions, titleNote } = fixes;
  if (!patches.length && !h2suggestions.length && !titleNote.length)
    return console.log(`${C.green}  ✓ Nothing to fix${C.reset}`);
  for (const p of patches) {
    if (p.type === 'description') {
      console.log(`\n  ${C.cyan}[DESCRIPTION]${C.reset} ${C.grey}${p.reason}${C.reset}`);
      console.log(`  ${C.red}− ${p.was.slice(0, 120)}${C.reset}`);
      console.log(`  ${C.green}+ ${p.proposed}${C.reset}`);
    }
    if (p.type === 'img_alt') {
      console.log(`\n  ${C.cyan}[IMG ALT]${C.reset} ${C.grey}${p.reason}${C.reset}`);
      for (const ip of p.patches) {
        console.log(`  ${C.red}− ![][${ip.path}]${C.reset}`);
        console.log(`  ${C.green}+ ![${ip.alt}](${ip.path})${C.reset}`);
      }
    }
  }
  if (titleNote.length) { console.log(`\n  ${C.yellow}[TITLE NOTE]${C.reset}`); titleNote.forEach(n => console.log(`  ${C.yellow}△ ${n}${C.reset}`)); }
  if (h2suggestions.length) { console.log(`\n  ${C.blue}[H2 SUGGESTIONS — insert manually]${C.reset}`); h2suggestions.forEach(s => console.log(`  ${C.blue}  ${s}${C.reset}`)); }
}

// ─── QA Gatekeeper ────────────────────────────────────────────────────────────
/**
 * Scan an HTML file for a pattern. Returns true if found.
 */
function htmlContains(filepath, pattern) {
  try { return pattern.test(readFileSync(filepath, 'utf-8')); } catch { return false; }
}

/**
 * Check all built tag pages for noindex. Returns array of violation objects.
 * publicDir: path to zola build output (e.g. ./public).
 */
function qaCheckTagPages(publicDir) {
  const failures = [];
  const tagDir   = join(publicDir, 'tags');
  if (!existsSync(tagDir)) return failures; // tags dir not built — nothing to check

  const noindexRx  = /<meta\s[^>]*name=["']robots["'][^>]*content=["'][^"']*noindex[^"']*["']/i;
  const canonicalRx = /<link\s[^>]*rel=["']canonical["'][^>]*/i;

  function scanDir(dir) {
    for (const entry of readdirSync(dir)) {
      const full = join(dir, entry);
      if (statSync(full).isDirectory()) { scanDir(full); continue; }
      if (!entry.endsWith('.html'))     continue;

      const relPath = '/' + relative(publicDir, full).replace(/\\/g, '/');
      if (!relPath.startsWith('/tags/')) continue;

      const hasNoindex  = htmlContains(full, noindexRx);
      const hasCanon    = htmlContains(full, canonicalRx);

      if (!hasNoindex)
        failures.push({ file: relPath, type: 'noindex_missing', message: `Tag page is indexable (missing noindex): ${relPath}` });
      if (!hasCanon)
        failures.push({ file: relPath, type: 'canonical_missing', message: `Tag page missing <link rel="canonical">: ${relPath}` });
    }
  }
  scanDir(tagDir);
  return failures;
}

/**
 * Check sitemap.xml for any /tags/ URLs. Returns violations.
 */
function qaCheckSitemap(publicDir) {
  const sitemapPath = join(publicDir, 'sitemap.xml');
  if (!existsSync(sitemapPath)) return [];
  const xml      = readFileSync(sitemapPath, 'utf-8');
  const tagUrls  = [...xml.matchAll(/<loc>([^<]*\/tags\/[^<]*)<\/loc>/gi)].map(m => m[1]);
  return tagUrls.map(url => ({
    type: 'sitemap_tag_url',
    message: `Tag URL found in sitemap (must be excluded): ${url}`,
  }));
}

/**
 * Check all built HTML pages (except tags/) for missing canonical tags.
 */
function qaCheckCanonicals(publicDir) {
  const failures   = [];
  const canonRx    = /<link\s[^>]*rel=["']canonical["'][^>]*/i;

  function scanDir(dir) {
    for (const entry of readdirSync(dir)) {
      const full = join(dir, entry);
      const stat = statSync(full);
      if (stat.isDirectory()) { scanDir(full); continue; }
      if (!entry.endsWith('.html')) continue;
      const relPath = '/' + relative(publicDir, full).replace(/\\/g, '/');
      if (relPath.startsWith('/tags/')) continue; // handled separately
      if (!htmlContains(full, canonRx))
        failures.push({ type: 'canonical_missing', message: `Missing canonical: ${relPath}` });
    }
  }
  if (existsSync(publicDir)) scanDir(publicDir);
  return failures;
}

/**
 * Check markdown source for missing title / description / H1-equivalent.
 * Uses the already-computed scoreFile results.
 */
function qaCheckArticles(results) {
  const failures = [];
  for (const r of results) {
    const rel = relative(process.cwd(), r.file);
    if (!r.meta.title || r.meta.title === '(no title)')
      failures.push({ type: 'missing_title',       message: `Missing title: ${rel}` });
    if (!r.meta.desc)
      failures.push({ type: 'missing_description', message: `Missing description: ${rel}` });
    // Zola uses the front matter title as the page H1 in most themes;
    // if the body also has an explicit H1 count > 1 that is a problem.
    if (r.meta.h1count > 1)
      failures.push({ type: 'multiple_h1',         message: `Multiple H1 tags (${r.meta.h1count}): ${rel}` });
  }
  return failures;
}

/**
 * Check internal links in markdown for broken paths.
 * A link is broken if:
 *  - It's a relative path (starts with /) and
 *  - Neither public/{path}/index.html nor content/{path}.md exists.
 */
function qaCheckBrokenLinks(files, publicDir, contentDir) {
  const failures = [];

  for (const filepath of files) {
    const src    = readFileSync(filepath, 'utf-8');
    const { body } = parseFrontMatter(src);
    const rel    = relative(process.cwd(), filepath);
    const links  = [...body.matchAll(/\[([^\]]+)\]\(([^)#?]+)[^)]*\)/g)];

    for (const [, , href] of links) {
      // Only check root-relative internal links
      if (!href.startsWith('/') || href.startsWith('//')) continue;
      const cleanPath = href.replace(/\/$/, '').replace(/^\//, '');

      // Acceptable resolutions
      const inPublic   = publicDir  && existsSync(join(publicDir, cleanPath, 'index.html'));
      const inContent1 = contentDir && existsSync(join(contentDir, cleanPath + '.md'));
      const inContent2 = contentDir && existsSync(join(contentDir, cleanPath, 'index.md'));
      const inContent3 = contentDir && existsSync(join(contentDir, cleanPath, '_index.md'));

      if (!inPublic && !inContent1 && !inContent2 && !inContent3)
        failures.push({ type: 'broken_link', message: `Broken internal link [${href}] in ${rel}` });
    }
  }
  return failures;
}

// ─── Automation Layer — Template / Hub / Related ─────────────────────────────
const HUB_MIN_POSTS = 3;    // min posts per tag before a hub page is generated
const RELATED_COUNT = 4;    // related posts written per article
const PARTIALS_DIR  = join('templates', 'partials');
const HUB_DIR       = join('content',   'hubs');
const TIERS_PATH    = join('data', 'tiers.json');
const FEATURED_PATH = join('data', 'featured.json');

/** Load data/tiers.json (written by --priority --json). Returns null if absent. */
function loadTiers() {
  if (!existsSync(TIERS_PATH)) return null;
  try { return JSON.parse(readFileSync(TIERS_PATH, 'utf-8')); }
  catch { return null; }
}

/**
 * ASCII slug from any string. Strips Vietnamese diacritics,
 * lowercases, replaces spaces with hyphens.
 */
function slugify(text) {
  const MAP = {
    à:'a',á:'a',â:'a',ã:'a',ä:'a',å:'a',
    è:'e',é:'e',ê:'e',ë:'e',
    ì:'i',í:'i',î:'i',ï:'i',
    ò:'o',ó:'o',ô:'o',õ:'o',ö:'o',
    ù:'u',ú:'u',û:'u',ü:'u',
    ý:'y',ÿ:'y',ñ:'n',ç:'c',ß:'ss',
    // Vietnamese
    ắ:'a',ặ:'a',ầ:'a',ấ:'a',ẩ:'a',ẫ:'a',ậ:'a',
    ằ:'a',ă:'a',ā:'a',
    ẻ:'e',ẽ:'e',ẹ:'e',ề:'e',ế:'e',ể:'e',ễ:'e',ệ:'e',
    ỉ:'i',ĩ:'i',ị:'i',
    ỏ:'o',ọ:'o',ồ:'o',ố:'o',ổ:'o',ỗ:'o',ộ:'o',ờ:'o',ớ:'o',ở:'o',ỡ:'o',ợ:'o',ơ:'o',
    ủ:'u',ũ:'u',ụ:'u',ừ:'u',ứ:'u',ử:'u',ữ:'u',ự:'u',ư:'u',
    ỳ:'y',ỵ:'y',ỷ:'y',ỹ:'y',
    đ:'d',
  };
  return text
    .toLowerCase()
    .split('').map(c => MAP[c] || c).join('')
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9\s-]/g, '')
    .trim().replace(/\s+/g, '-').replace(/-+/g, '-')
    .replace(/^-|-$/g, '');
}

/**
 * Given a scored result, compute its Zola content-relative path for get_page().
 * e.g.  /abs/path/content/blog/post.md  →  blog/post.md
 */
function zolaPath(filepath, contentDir) {
  const cd  = resolve(contentDir || resolveContentDir() || 'content');
  const abs = resolve(filepath);
  if (abs.startsWith(cd + '/') || abs.startsWith(cd + '\\'))
    return abs.slice(cd.length + 1).replace(/\\/g, '/');
  return relative(process.cwd(), abs).replace(/\\/g, '/');
}

// ── 1. TEMPLATE PARTIALS ──────────────────────────────────────────────────────

/** Tera source for templates/partials/featured_posts.html */
function featuredPartialSrc() {
  return `{#- ─────────────────────────────────────────────────────────────────────────
    featured_posts.html — Tier 1 featured posts (auto-generated)
    Source of truth : data/featured.json  (written by: node seo_engine.js --priority --json)
    Usage           : {%- include "partials/featured_posts.html" -%} in your index.html
    DO NOT EDIT MANUALLY — re-run --priority --json to refresh the data file.
─────────────────────────────────────────────────────────────────────────── -#}
{%- set featured = load_data(path="data/featured.json") -%}
{%- if featured and featured.tier1 -%}
<section class="featured-posts" aria-label="Bài Viết Nổi Bật">
  <h2 class="featured-title">Bài Viết Nổi Bật</h2>
  <div class="featured-grid">
    {%- for item in featured.tier1 | slice(end=6) -%}
      {%- set p = get_page(path=item.path) -%}
      <article class="featured-card rank-{{ loop.index }}">
        {%- if p.extra.thumbnail -%}
          <a href="{{ p.permalink }}" class="featured-thumb" tabindex="-1" aria-hidden="true">
            <img src="{{ p.extra.thumbnail }}" alt="{{ p.title }}" loading="lazy" width="400" height="250">
          </a>
        {%- endif -%}
        <div class="featured-body">
          <h3 class="featured-post-title">
            <a href="{{ p.permalink }}">{{ p.title }}</a>
          </h3>
          {%- if p.description -%}
            <p class="featured-desc">{{ p.description | truncate(length=120) }}</p>
          {%- endif -%}
          <div class="featured-meta">
            {%- if p.date -%}
              <time datetime="{{ p.date | date(format='%Y-%m-%d') }}">
                {{ p.date | date(format="%d/%m/%Y") }}
              </time>
            {%- endif -%}
            <span class="tier-badge t1" aria-label="Bài viết ưu tiên cao">⭐ Ưu tiên</span>
          </div>
        </div>
      </article>
    {%- endfor -%}
  </div>
</section>
{%- endif -%}
`;
}

/** Tera source for templates/partials/related_posts.html */
function relatedPartialSrc() {
  return `{#- ─────────────────────────────────────────────────────────────────────────
    related_posts.html — Score-weighted related posts (auto-generated)
    Reads  : page.extra.related = ["section/post.md", ...]  set by:
             node seo_engine.js --fix --related --write
    Usage  : {%- include "partials/related_posts.html" -%} in page.html
    DO NOT EDIT MANUALLY — re-run --fix --related --write to refresh assignments.
─────────────────────────────────────────────────────────────────────────── -#}
{%- if page.extra.related -%}
<aside class="related-posts" aria-label="Bài Viết Liên Quan">
  <h3 class="related-title">Bài Viết Liên Quan</h3>
  <div class="related-grid">
    {%- for rel_path in page.extra.related -%}
      {%- set rp = get_page(path=rel_path) -%}
      <article class="related-card">
        {%- if rp.extra.thumbnail -%}
          <a href="{{ rp.permalink }}" tabindex="-1" aria-hidden="true">
            <img src="{{ rp.extra.thumbnail }}" alt="{{ rp.title }}" loading="lazy" width="300" height="180">
          </a>
        {%- endif -%}
        <div class="related-body">
          <h4><a href="{{ rp.permalink }}">{{ rp.title }}</a></h4>
          {%- if rp.description -%}
            <p>{{ rp.description | truncate(length=100) }}</p>
          {%- endif -%}
        </div>
      </article>
    {%- endfor -%}
  </div>
</aside>
{%- endif -%}
`;
}

/**
 * Returns an array of template patch proposals.
 * Each proposal: { type, path, action, content, reason }
 */
function buildTemplatePatches() {
  const patches = [];

  // Partial: featured_posts.html
  const featPath = join(PARTIALS_DIR, 'featured_posts.html');
  const featSrc  = featuredPartialSrc();
  if (!existsSync(featPath)) {
    patches.push({ type: 'create', path: featPath, content: featSrc,
      reason: 'Create Tier-1 featured posts partial (uses data/featured.json + get_page())' });
  } else {
    const cur = readFileSync(featPath, 'utf-8');
    if (cur !== featSrc)
      patches.push({ type: 'update', path: featPath, content: featSrc,
        reason: 'Update featured_posts.html to latest template' });
    else
      patches.push({ type: 'noop', path: featPath, reason: 'featured_posts.html already up-to-date' });
  }

  // Partial: related_posts.html
  const relPath = join(PARTIALS_DIR, 'related_posts.html');
  const relSrc  = relatedPartialSrc();
  if (!existsSync(relPath)) {
    patches.push({ type: 'create', path: relPath, content: relSrc,
      reason: 'Create related posts partial (reads page.extra.related array via get_page())' });
  } else {
    const cur = readFileSync(relPath, 'utf-8');
    if (cur !== relSrc)
      patches.push({ type: 'update', path: relPath, content: relSrc,
        reason: 'Update related_posts.html to latest template' });
    else
      patches.push({ type: 'noop', path: relPath, reason: 'related_posts.html already up-to-date' });
  }

  // Patch templates/index.html — inject include if not already present
  const idxPath = join('templates', 'index.html');
  if (existsSync(idxPath)) {
    const idxSrc = readFileSync(idxPath, 'utf-8');
    const includeTag = `{%- include "partials/featured_posts.html" -%}`;
    if (!idxSrc.includes('featured_posts.html')) {
      // Insert after <body> or after the first {% block content %} / {% block body %}
      const insertRx = /(^\s*{%-?\s*block\s+(?:content|body)[^%]*%}|<body[^>]*>)/m;
      const m = idxSrc.match(insertRx);
      let patched;
      if (m) {
        patched = idxSrc.slice(0, m.index + m[0].length) + '\n' + includeTag + '\n' + idxSrc.slice(m.index + m[0].length);
      } else {
        patched = includeTag + '\n' + idxSrc; // prepend as last resort
      }
      patches.push({ type: 'patch', path: idxPath, content: patched,
        reason: `Inject {% include "partials/featured_posts.html" %} into templates/index.html` });
    } else {
      patches.push({ type: 'noop', path: idxPath, reason: 'templates/index.html already includes featured_posts partial' });
    }
  } else {
    patches.push({ type: 'info', path: idxPath,
      reason: 'templates/index.html not found — add {%- include "partials/featured_posts.html" -%} manually' });
  }

  return patches;
}

/** Apply template patches. Returns count of files written. */
function applyTemplatePatches(patches, doWrite) {
  let written = 0;
  for (const p of patches) {
    if (p.type === 'noop' || p.type === 'info') continue;
    if (doWrite) {
      mkdirSync(dirname(p.path), { recursive: true });
      writeFileSync(p.path, p.content, 'utf-8');
      written++;
    }
  }
  return written;
}

// ── 2. HUB PAGES ─────────────────────────────────────────────────────────────

/**
 * Group scored results by tag. Returns Map<tag, result[]>.
 * Only uses posts that have a minimum on-page score or appear in tiers.json.
 */
function groupByTag(results, tiersData) {
  const tierSlugs = new Set(
    tiersData ? [...tiersData.tiers.tier1, ...tiersData.tiers.tier2].map(r => r.slug) : []
  );
  const map = new Map();

  for (const r of results) {
    const src  = readFileSync(r.file, 'utf-8');
    const { fm } = parseFrontMatter(src);
    const tags = Array.isArray(fm.taxonomies?.tags) ? fm.taxonomies.tags
               : Array.isArray(fm.tags) ? fm.tags : [];

    // Include if: in tier1/2, or on-page score >= 60
    const qualified = tierSlugs.has(r.slug) || r.total >= 60;
    if (!qualified) continue;

    for (const tag of tags) {
      if (!map.has(tag)) map.set(tag, []);
      map.get(tag).push(r);
    }
  }

  // Sort each group by priority (from tiers) then on-page score
  const tierPri = new Map(
    tiersData ? tiersData.all.map(r => [r.slug, r.priority]) : []
  );
  for (const [, posts] of map)
    posts.sort((a, b) => (tierPri.get(b.slug) ?? b.total) - (tierPri.get(a.slug) ?? a.total));

  return map;
}

/** Generate _index.md markdown content for a hub page. */
function buildHubMarkdown(tag, posts, tiersData) {
  const tierPri = new Map(
    tiersData ? tiersData.all.map(r => [r.slug, r.priority]) : []
  );
  const now       = new Date().toISOString().split('T')[0];
  const topPosts  = posts.slice(0, 8);
  const kws       = [...new Set(topPosts.map(r => r.keyword).filter(Boolean))].slice(0, 3);
  const kwStr     = kws.length ? kws.join(', ') : tag;
  const titleTag  = tag.charAt(0).toUpperCase() + tag.slice(1);
  const descSnip  = topPosts.slice(0, 3).map(r => r.title).join(', ');

  const linksBlock = topPosts.map((r, i) => {
    const pri = tierPri.get(r.slug);
    const badge = pri !== undefined
      ? ` *(${i < TIER1_SIZE ? 'Tier 1' : 'Tier 2'}, điểm ưu tiên: ${pri.toFixed(1)})*`
      : '';
    return `${i + 1}. [${r.title}](/${r.slug}/)${badge}  \n   ${r.meta.desc ? r.meta.desc.slice(0, 110) : ''}`;
  }).join('\n\n');

  return `+++
title = "Hub: ${titleTag} — Tổng Hợp Bài Viết Chuyên Sâu"
description = "Tổng hợp các bài viết chuyên sâu về ${tag}: ${descSnip.slice(0, 100)}."
date = ${now}
updated = ${now}

[taxonomies]
tags = ["${tag}"]

[extra]
is_hub = true
hub_tag = "${tag}"
seo_keyword = "${kwStr}"
robots = "index, follow"
+++

<!-- AUTO-GENERATED by seo_engine.js --fix --hubs -->
<!-- Re-run: node seo_engine.js --fix --hubs --write  to refresh -->

Trang hub này tổng hợp những bài viết chuyên sâu và uy tín nhất về chủ đề **${tag}** — được xếp hạng theo điểm SEO ưu tiên, độ mới, và mức độ liên quan nội dung.

## Bài Viết Nổi Bật Về ${titleTag}

${linksBlock}

---

*Nội dung được cập nhật tự động bởi SEO Priority Engine. Xem thêm tất cả bài viết trong chuyên mục [${titleTag}](/tags/${slugify(tag)}/).*
`;
}

/**
 * Returns hub page fix proposals.
 * Each: { type, path, content, tag, postCount, reason }
 */
function buildHubPatches(results, tiersData) {
  const tagMap  = groupByTag(results, tiersData);
  const patches = [];

  for (const [tag, posts] of tagMap) {
    if (posts.length < HUB_MIN_POSTS) continue;
    const hubSlug = slugify(tag);
    if (!hubSlug) continue;

    const hubPath    = join(HUB_DIR, `${hubSlug}.md`);
    const newContent = buildHubMarkdown(tag, posts, tiersData);

    if (!existsSync(hubPath)) {
      patches.push({ type: 'create', path: hubPath, content: newContent, tag, postCount: posts.length,
        reason: `Create hub page for "${tag}" (${posts.length} qualified posts)` });
    } else {
      // Re-generate if stale (older than 7 days or post count changed)
      try {
        const cur = readFileSync(hubPath, 'utf-8');
        const dateMatch = cur.match(/^updated = (\S+)/m);
        const lastUp = dateMatch ? new Date(dateMatch[1]) : new Date(0);
        const stale  = (Date.now() - lastUp.getTime()) > 7 * 86400_000;
        if (stale)
          patches.push({ type: 'update', path: hubPath, content: newContent, tag, postCount: posts.length,
            reason: `Refresh hub page for "${tag}" (${posts.length} posts, last updated ${dateMatch?.[1] ?? 'unknown'})` });
        else
          patches.push({ type: 'noop', path: hubPath, tag, postCount: posts.length,
            reason: `Hub for "${tag}" is fresh (updated ${dateMatch?.[1]})` });
      } catch {
        patches.push({ type: 'update', path: hubPath, content: newContent, tag, postCount: posts.length,
          reason: `Re-create hub page for "${tag}" (read error on existing file)` });
      }
    }
  }

  return patches;
}

/** Apply hub patches. Returns count of files written. */
function applyHubPatches(patches, doWrite) {
  let written = 0;
  for (const p of patches) {
    if (p.type === 'noop') continue;
    if (doWrite) {
      mkdirSync(dirname(p.path), { recursive: true });
      writeFileSync(p.path, p.content, 'utf-8');
      written++;
    }
  }
  return written;
}

// ── 3. RELATED POSTS ─────────────────────────────────────────────────────────

/** Jaccard similarity between two arrays of strings. */
function jaccard(a, b) {
  if (!a.length && !b.length) return 0;
  const sa   = new Set(a.map(x => x.toLowerCase()));
  const sb   = new Set(b.map(x => x.toLowerCase()));
  const inter = [...sa].filter(x => sb.has(x)).length;
  const union  = new Set([...sa, ...sb]).size;
  return union ? inter / union : 0;
}

/** Keyword overlap score (0, 0.5, or 1.0). */
function kwOverlap(a, b) {
  if (!a || !b) return 0;
  if (a === b)  return 1;
  const wa = a.split(/\s+/), wb = b.split(/\s+/);
  return wa.some(w => wb.includes(w)) ? 0.5 : 0;
}

/**
 * Relatedness score between result A and B:
 *   55% tag Jaccard + 30% priority proximity + 15% keyword overlap
 * Returns 0–1.
 */
function relatedness(a, b, tierPriMap) {
  // Tags
  const srcA = readFileSync(a.file, 'utf-8');
  const srcB = readFileSync(b.file, 'utf-8');
  const fmA  = parseFrontMatter(srcA).fm;
  const fmB  = parseFrontMatter(srcB).fm;
  const tagsA = Array.isArray(fmA.taxonomies?.tags) ? fmA.taxonomies.tags : Array.isArray(fmA.tags) ? fmA.tags : [];
  const tagsB = Array.isArray(fmB.taxonomies?.tags) ? fmB.taxonomies.tags : Array.isArray(fmB.tags) ? fmB.tags : [];

  const tagSim  = jaccard(tagsA, tagsB);

  // Priority proximity (use tiers priority if available, else on-page score)
  const priA = tierPriMap?.get(a.slug) ?? a.total;
  const priB = tierPriMap?.get(b.slug) ?? b.total;
  const priSim = 1 - Math.abs(priA - priB) / 100;

  // Keyword overlap
  const kwSim   = kwOverlap(a.keyword, b.keyword);

  return 0.55 * tagSim + 0.30 * priSim + 0.15 * kwSim;
}

/**
 * Returns up to RELATED_COUNT related post paths (Zola content-relative) for `result`.
 * Excludes itself. Returns array of { slug, path, score }.
 */
function computeRelated(result, allResults, tierPriMap, contentDir) {
  return allResults
    .filter(r => r.file !== result.file)
    .map(r => ({ r, score: relatedness(result, r, tierPriMap) }))
    .filter(({ score }) => score > 0.05)
    .sort((a, b) => b.score - a.score)
    .slice(0, RELATED_COUNT)
    .map(({ r, score }) => ({
      slug: r.slug,
      path: zolaPath(r.file, contentDir),
      score: Math.round(score * 100) / 100,
    }));
}

/**
 * Returns related-posts patch proposals for all results.
 * Each: { filepath, slug, related: [{slug, path, score}], reason }
 */
function buildRelatedPatches(results, tiersData, contentDir) {
  const tierPriMap = tiersData
    ? new Map(tiersData.all.map(r => [r.slug, r.priority]))
    : null;

  return results.map(result => {
    const related = computeRelated(result, results, tierPriMap, contentDir);
    return { filepath: result.file, slug: result.slug, related,
      reason: `Top ${related.length} related posts (tag Jaccard + priority similarity)` };
  }).filter(p => p.related.length > 0);
}

/**
 * Patch `related = [...]` into the [extra] section of a TOML/YAML front matter file.
 * Never touches body content. Returns new full file source string, or null if no change.
 */
function applyRelatedPatch(filepath, relatedPaths) {
  const src = readFileSync(filepath, 'utf-8');
  const { type: fmType, rawFm, body } = parseFrontMatter(src);
  if (!fmType) return null;

  const arr    = JSON.stringify(relatedPaths);     // ["path1", "path2"]
  let newFm    = rawFm;
  let changed  = false;

  if (fmType === 'toml') {
    if (/^related\s*=/m.test(newFm)) {
      // Replace existing related line(s) — handle multi-line arrays too
      newFm = newFm.replace(/^related\s*=\s*\[[\s\S]*?\](\s*$)/m, `related = ${arr}`);
    } else if (/^\[extra\]/m.test(newFm)) {
      // Append inside [extra]
      newFm = newFm.replace(/(\[extra\][^\[]*)/s, `$1related = ${arr}\n`);
    } else {
      // No [extra] section — create it
      newFm = newFm.trimEnd() + `\n\n[extra]\nrelated = ${arr}\n`;
    }
    changed = true;
  } else if (fmType === 'yaml') {
    if (/^related:/m.test(newFm)) {
      newFm = newFm.replace(/^related:.*$/m, `related: ${arr}`);
    } else {
      newFm = newFm.trimEnd() + `\nrelated: ${arr}\n`;
    }
    changed = true;
  }

  if (!changed) return null;
  if (fmType === 'toml') return `+++\n${newFm}\n+++\n${body}`;
  return `---\n${newFm}\n---\n${body}`;
}

/** Apply related-posts patches. Returns count of files written. */
function applyRelatedPatches(patches, doWrite, contentDir) {
  let written = 0;
  for (const p of patches) {
    if (doWrite) {
      const paths = p.related.map(r => r.path);
      const newSrc = applyRelatedPatch(p.filepath, paths);
      if (newSrc) { writeFileSync(p.filepath, newSrc, 'utf-8'); written++; }
    }
  }
  return written;
}

// ─── File collection ──────────────────────────────────────────────────────────
function collectMarkdown(dir) {
  const files = [];
  if (!existsSync(dir)) return files;
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory())                                        files.push(...collectMarkdown(full));
    else if (['.md', '.markdown'].includes(extname(entry).toLowerCase())) files.push(full);
  }
  return files;
}

function resolveTarget(target) {
  if (existsSync(target)) return resolve(target);
  for (const base of ['content', 'posts', 'blog', 'src/content']) {
    if (!existsSync(base)) continue;
    const m = collectMarkdown(base).find(f => basename(f, extname(f)) === target || f.includes(target));
    if (m) return resolve(m);
  }
  return null;
}

function resolveContentDir() {
  for (const c of ['content', 'posts', 'blog', 'src/content']) if (existsSync(c)) return c;
  return null;
}

function resolveFiles(args, targetArg, dirIdx) {
  const positional = args.filter(a => !a.startsWith('--') && !/^\d+$/.test(a) && a !== targetArg);
  let files = [];
  if (targetArg) {
    const r = resolveTarget(targetArg);
    if (!r) { console.error(`${C.red}✗ Cannot find target: "${targetArg}"${C.reset}`); process.exit(1); }
    return [r];
  }
  if (positional.length) {
    for (const p of positional) {
      if (!existsSync(p)) { console.error(`${C.red}✗ Not found: ${p}${C.reset}`); continue; }
      statSync(p).isDirectory() ? files.push(...collectMarkdown(p)) : files.push(p);
    }
    return files;
  }
  if (dirIdx !== -1) return collectMarkdown(args[dirIdx + 1]);
  const cd = resolveContentDir();
  if (!cd) { console.error(`${C.red}No content directory found.${C.reset}`); process.exit(1); }
  return collectMarkdown(cd);
}

// ─── Main ─────────────────────────────────────────────────────────────────────
async function main() {
  const args = process.argv.slice(2);

  if (args.includes('--help') || args.includes('-h')) {
    console.log(`
${C.bold}seo_engine.js${C.reset} — SEO Priority Engine for Zola blogs

${C.bold}AUDIT${C.reset} (default, read-only on-page scoring):
  node seo_engine.js                   scan ./content
  node seo_engine.js --json            write seo-report.json
  node seo_engine.js --min 70          show posts below score 70
  node seo_engine.js --sort score      sort worst-first

${C.bold}FIX${C.reset} (dry-run unless --write):
  node seo_engine.js --fix                         propose fixes
  node seo_engine.js --fix --target path/post.md   one file
  node seo_engine.js --fix --report                diff view
  node seo_engine.js --fix --write --target x.md   ${C.red}apply to one file${C.reset}
  node seo_engine.js --fix --write                 ${C.red}apply to all${C.reset}

${C.bold}PRIORITY${C.reset} (GSC-powered ranking):
  node seo_engine.js --priority         compute priority scores + tiers
  node seo_engine.js --priority --json  also write data/tiers.json
  Env vars: GSC_CREDENTIALS (service-account JSON), GSC_SITE_URL
  Fallback: freshness + internal links if GSC not configured.

${C.bold}QA GATEKEEPER${C.reset} (exits 1 on any failure):
  node seo_engine.js --qa                    full quality gate
  node seo_engine.js --qa --public ./public  custom build dir
  Fail conditions:
    • /tags/* pages indexable or in sitemap
    • Articles missing title, description
    • Built HTML pages missing <link rel="canonical">
    • Broken internal links in markdown

${C.bold}AUTOMATION — Template / Hub / Related${C.reset} (dry-run unless --write):
  node seo_engine.js --fix --templates         propose Tera partial file changes
  node seo_engine.js --fix --hubs              propose hub page markdown generation
  node seo_engine.js --fix --related           propose related-post assignments
  node seo_engine.js --fix --write --templates ${C.red}write templates/partials/*.html${C.reset}
  node seo_engine.js --fix --write --hubs      ${C.red}write content/hubs/*.md${C.reset}
  node seo_engine.js --fix --write --related   ${C.red}patch related=[...] in all front matters${C.reset}
  node seo_engine.js --fix --write             ${C.red}run ALL three automation steps${C.reset}
  Prerequisites:
    • Run --priority --json first to build data/tiers.json + data/featured.json
    • --templates requires a templates/ directory (Zola repo)
    • --related patches [extra] related = [...] into TOML/YAML front matter
`);
    process.exit(0);
  }

  const doFix       = args.includes('--fix');
  const doWrite     = args.includes('--write');
  const doReport    = args.includes('--report');
  const doPriority  = args.includes('--priority');
  const doQa        = args.includes('--qa');
  const writeJson   = args.includes('--json');
  // Automation sub-modes (all live under --fix / --fix --write)
  const doTemplates = args.includes('--templates');
  const doHubs      = args.includes('--hubs');
  const doRelated   = args.includes('--related');
  // isAutoMode: any automation flag is set; original content fix runs when none are set
  const isAutoMode  = doFix && (doTemplates || doHubs || doRelated);
  const minScore   = Number(args[args.indexOf('--min')  + 1] ?? 0) || 0;
  const dirIdx     = args.indexOf('--dir');
  const sortBy     = args[args.indexOf('--sort')   + 1] ?? 'file';
  const targetArg  = args.indexOf('--target') !== -1  ? args[args.indexOf('--target')  + 1] : null;
  const publicArg  = args.indexOf('--public') !== -1  ? args[args.indexOf('--public')  + 1] : 'public';

  // Safety guards
  if (doWrite && !doFix) {
    console.log(`${C.yellow}⚠  --write has no effect without --fix.${C.reset}`);
    process.exit(0);
  }

  // --templates never needs markdown files; --hubs and --related do.
  const needsMarkdown = !isAutoMode || doHubs || doRelated;

  let files = [];
  if (needsMarkdown) {
    files = resolveFiles(args, targetArg, dirIdx);
    if (!files.length) { console.log(`${C.yellow}No markdown files found.${C.reset}`); process.exit(0); }
  }

  // Score all files (needed by every mode that scans markdown)
  const results = [];
  let errors = 0;
  for (const f of files) {
    try { results.push(scoreFile(f)); }
    catch (e) { console.error(`${C.red}Error scoring ${f}: ${e.message}${C.reset}`); errors++; }
  }
  if (sortBy === 'score') results.sort((a, b) => a.total - b.total);
  else                    results.sort((a, b) => a.file.localeCompare(b.file));

  // ════════════════════════════════════════════════════════════════════════════
  // QA GATEKEEPER MODE
  // ════════════════════════════════════════════════════════════════════════════
  if (doQa) {
    console.log(`\n${C.bold}${C.cyan}╔══════════════════════════════════════════════════════════╗${C.reset}`);
    console.log(`${C.bold}${C.cyan}║          SEO ENGINE — QA Gatekeeper                      ║${C.reset}`);
    console.log(`${C.bold}${C.cyan}╚══════════════════════════════════════════════════════════╝${C.reset}\n`);

    const allFailures = [];
    const contentDir  = resolveContentDir();

    // 1. Tag pages: noindex + sitemap
    console.log(`${C.bold}Checking tag page indexability…${C.reset}`);
    if (existsSync(publicArg)) {
      const tagF = qaCheckTagPages(publicArg);
      const mapF = qaCheckSitemap(publicArg);
      allFailures.push(...tagF, ...mapF);
      if (tagF.length + mapF.length === 0) console.log(`  ${C.green}✓ No indexable tag pages found${C.reset}`);
      else [...tagF, ...mapF].forEach(f => console.log(`  ${C.red}✗ FAIL: ${f.message}${C.reset}`));
    } else {
      console.log(`  ${C.yellow}△ public/ dir not found — skipping HTML/sitemap checks (run zola build first)${C.reset}`);
    }

    // 2. Canonical tags in built HTML
    console.log(`\n${C.bold}Checking canonical tags…${C.reset}`);
    if (existsSync(publicArg)) {
      const canonF = qaCheckCanonicals(publicArg);
      allFailures.push(...canonF);
      if (canonF.length === 0) console.log(`  ${C.green}✓ All pages have canonical tags${C.reset}`);
      else canonF.forEach(f => console.log(`  ${C.red}✗ FAIL: ${f.message}${C.reset}`));
    } else {
      console.log(`  ${C.yellow}△ Skipped (no public/ dir)${C.reset}`);
    }

    // 3. Article quality: title, description
    console.log(`\n${C.bold}Checking article metadata…${C.reset}`);
    const artF = qaCheckArticles(results);
    allFailures.push(...artF);
    if (artF.length === 0) console.log(`  ${C.green}✓ All articles have title + description${C.reset}`);
    else artF.forEach(f => console.log(`  ${C.red}✗ FAIL: ${f.message}${C.reset}`));

    // 4. Broken internal links
    console.log(`\n${C.bold}Checking internal links…${C.reset}`);
    const linkF = qaCheckBrokenLinks(files, existsSync(publicArg) ? publicArg : null, contentDir);
    allFailures.push(...linkF);
    if (linkF.length === 0) console.log(`  ${C.green}✓ No broken internal links${C.reset}`);
    else linkF.forEach(f => console.log(`  ${C.red}✗ FAIL: ${f.message}${C.reset}`));

    // Summary
    console.log(`\n${C.bold}──────────────────────────────────────────────${C.reset}`);
    if (allFailures.length === 0) {
      console.log(`${C.bold}${C.green}✓ QA PASSED — ${files.length} files checked, 0 failures${C.reset}\n`);
      process.exit(0);
    } else {
      console.log(`${C.bold}${C.red}✗ QA FAILED — ${allFailures.length} issue(s) must be resolved${C.reset}`);
      console.log(`${C.grey}  Run \`node seo_engine.js --fix\` for auto-fixable items.${C.reset}\n`);
      process.exit(1);
    }
  }

  // ════════════════════════════════════════════════════════════════════════════
  // PRIORITY MODE
  // ════════════════════════════════════════════════════════════════════════════
  if (doPriority) {
    console.log(`\n${C.bold}${C.cyan}╔══════════════════════════════════════════════════════════╗${C.reset}`);
    console.log(`${C.bold}${C.cyan}║          SEO ENGINE — Priority Scorer                    ║${C.reset}`);
    console.log(`${C.bold}${C.cyan}╚══════════════════════════════════════════════════════════╝${C.reset}\n`);

    let gscMap   = null;
    let gscMode  = 'offline';
    const gscCfg = loadGscCredentials();

    if (gscCfg) {
      try {
        console.log(`${C.grey}Authenticating with Google Search Console…${C.reset}`);
        const token = await getGscToken(gscCfg.creds);
        const rows  = await fetchGscData(gscCfg.siteUrl, token, 90);
        gscMap      = new Map(rows.map(r => [r.page, r]));
        gscMode     = `GSC live (${rows.length} URLs, site: ${gscCfg.siteUrl})`;
        console.log(`${C.green}✓ GSC data loaded: ${rows.length} page URLs${C.reset}\n`);
      } catch (e) {
        console.warn(`${C.yellow}⚠ GSC API error: ${e.message} — using offline fallback${C.reset}\n`);
      }
    } else {
      console.log(`${C.yellow}△ GSC_CREDENTIALS not set — using offline fallback (freshness + links only)${C.reset}`);
      console.log(`${C.grey}  Set GSC_CREDENTIALS (service-account JSON) and GSC_SITE_URL to enable full scoring.${C.reset}\n`);
    }

    const ranked = calcPriorityScores(results, gscMap, gscCfg?.siteUrl || '');

    console.log(`${C.bold}Ranked posts  [mode: ${gscMode}]${C.reset}\n`);
    console.log(`${'Rank'.padEnd(5)} ${'Tier'.padEnd(7)} ${'Priority'.padEnd(10)} ${'On-page'.padEnd(9)} ${'File'}`)
    console.log('─'.repeat(80));

    for (const r of ranked) {
      const tc   = tierCol(r.tier);
      const rel  = relative(process.cwd(), r.file);
      const pri  = r.priority.toFixed(1).padStart(5);
      const onp  = String(r.total).padStart(3);
      console.log(
        `${String(r.rank).padEnd(5)} ` +
        `${tc}T${r.tier}${C.reset}     ` +
        `${colour(r.priority)}${pri}/100${C.reset}  ` +
        `${colour(r.total)}${onp}/100${C.reset}   ` +
        `${C.grey}${rel}${C.reset}`
      );
    }

    // Tier summary
    const t1 = ranked.filter(r => r.tier === 1);
    const t2 = ranked.filter(r => r.tier === 2);
    const t3 = ranked.filter(r => r.tier === 3);
    console.log(`\n${C.bold}Tier summary:${C.reset}`);
    console.log(`  ${C.green}Tier 1 (Top ${TIER1_SIZE}): ${t1.length} posts${C.reset}  — highest-priority for homepage/hub links`);
    console.log(`  ${C.yellow}Tier 2 (Top ${TIER2_SIZE}): ${t2.length} posts${C.reset}  — featured in category pages`);
    console.log(`  ${C.grey}Tier 3 (Rest):  ${t3.length} posts${C.reset}  — standard listing`);

    if (writeJson) {
      const contentDir = resolveContentDir() || 'content';

      const toTierEntry = r => ({
        rank:      r.rank,
        slug:      r.slug,
        priority:  r.priority,
        on_page:   r.total,
        title:     r.title,
        // Zola content-relative path for get_page() in Tera templates
        path:      zolaPath(r.file, contentDir),
      });

      // ── data/tiers.json — full priority data for the daily bot ──────────────
      const tiersOut = {
        generated_at: new Date().toISOString(),
        mode:         gscMode,
        formula:      gscMap ? '40% impressions + 25% clicks + 15% CTR + 10% freshness + 10% internal_links'
                              : 'offline: 50% freshness + 50% internal_links',
        tiers: {
          tier1: t1.map(toTierEntry),
          tier2: t2.map(toTierEntry),
          tier3: t3.map(toTierEntry),
        },
        all: ranked.map(r => ({
          ...toTierEntry(r),
          tier:    r.tier,
          file:    relative(process.cwd(), r.file),
          signals: r._signals,
        })),
      };

      // ── data/featured.json — Zola template data for load_data() + get_page() ─
      // Used by templates/partials/featured_posts.html via:
      //   {% set featured = load_data(path="data/featured.json") %}
      //   {% set page = get_page(path=item.path) %}
      const featuredOut = {
        generated_at:  new Date().toISOString(),
        generated_by:  'seo_engine.js --priority --json',
        tier1:         t1.map(toTierEntry),
        tier2:         t2.map(toTierEntry),
        // Top 6 for direct homepage rendering (no loop needed in template)
        homepage_featured: t1.slice(0, 6).map(toTierEntry),
      };

      const outDir = 'data';
      if (!existsSync(outDir)) mkdirSync(outDir, { recursive: true });
      writeFileSync(TIERS_PATH,    JSON.stringify(tiersOut,    null, 2));
      writeFileSync(FEATURED_PATH, JSON.stringify(featuredOut, null, 2));
      console.log(`\n${C.green}✓ Written: data/tiers.json${C.reset}`);
      console.log(`${C.green}✓ Written: data/featured.json${C.reset}  ${C.grey}(for Tera load_data + get_page)${C.reset}`);
    }
    console.log();
    return;
  }

  // ════════════════════════════════════════════════════════════════════════════
  // AUTOMATION MODE — Template / Hub / Related  (--fix --templates/--hubs/--related)
  // ════════════════════════════════════════════════════════════════════════════
  if (isAutoMode) {
    const modeLabel = doWrite
      ? `${C.red}WRITE MODE — files will be created/mutated${C.reset}`
      : `${C.green}DRY-RUN — no files will be changed${C.reset}`;
    console.log(`\n${C.bold}${C.cyan}╔══════════════════════════════════════════════════════════╗${C.reset}`);
    console.log(`${C.bold}${C.cyan}║          SEO ENGINE — Automation Layer                   ║${C.reset}`);
    console.log(`${C.bold}${C.cyan}╚══════════════════════════════════════════════════════════╝${C.reset}`);
    console.log(`  ${modeLabel}\n`);

    const tiersData  = loadTiers();
    const contentDir = resolveContentDir() || 'content';
    if (!tiersData && (doTemplates || doHubs)) {
      console.log(`${C.yellow}△ data/tiers.json not found — run --priority --json first for full scoring.${C.reset}`);
      console.log(`${C.grey}  Continuing with on-page scores as fallback…${C.reset}\n`);
    }

    let totalWritten = 0;

    // ── 1. TEMPLATE PARTIALS ────────────────────────────────────────────────
    if (doTemplates) {
      console.log(`${C.bold}── Template Partials ──────────────────────────────────────${C.reset}`);
      const patches = buildTemplatePatches();
      for (const p of patches) {
        const rel = relative(process.cwd(), p.path);
        if (p.type === 'noop') {
          console.log(`  ${C.green}✓ up-to-date:${C.reset} ${rel}`);
        } else if (p.type === 'info') {
          console.log(`  ${C.yellow}△ manual step:${C.reset} ${p.reason}`);
        } else {
          const action = p.type === 'create' ? C.cyan + 'CREATE' : C.yellow + 'UPDATE';
          console.log(`  ${action}${C.reset}  ${rel}`);
          console.log(`    ${C.grey}${p.reason}${C.reset}`);
          if (p.type === 'patch') {
            console.log(`    ${C.grey}Line injected: {%- include "partials/featured_posts.html" -%}${C.reset}`);
          }
        }
      }
      const n = applyTemplatePatches(patches, doWrite);
      if (doWrite && n > 0) {
        console.log(`\n  ${C.green}✓ Written ${n} template file(s)${C.reset}`);
        totalWritten += n;
      } else if (!doWrite) {
        const actionable = patches.filter(p => p.type !== 'noop' && p.type !== 'info').length;
        console.log(`\n  ${C.grey}→ Run with --write to apply ${actionable} template change(s)${C.reset}`);
      }
      console.log();
    }

    // ── 2. HUB PAGES ────────────────────────────────────────────────────────
    if (doHubs) {
      console.log(`${C.bold}── Hub Pages ──────────────────────────────────────────────${C.reset}`);
      const patches = buildHubPatches(results, tiersData);
      if (patches.length === 0) {
        console.log(`  ${C.yellow}△ No tags have ≥${HUB_MIN_POSTS} qualified posts (score ≥60 or in Tier 1/2)${C.reset}`);
      }
      for (const p of patches) {
        const rel = relative(process.cwd(), p.path);
        if (p.type === 'noop') {
          console.log(`  ${C.green}✓ fresh:${C.reset}   "${p.tag}" hub (${p.postCount} posts)  ${C.grey}${rel}${C.reset}`);
        } else {
          const action = p.type === 'create' ? C.cyan + 'CREATE' : C.yellow + 'UPDATE';
          console.log(`  ${action}${C.reset}  "${p.tag}" (${p.postCount} posts)  ${C.grey}${rel}${C.reset}`);
          console.log(`    ${C.grey}${p.reason}${C.reset}`);
        }
      }
      const n = applyHubPatches(patches, doWrite);
      if (doWrite && n > 0) {
        console.log(`\n  ${C.green}✓ Written ${n} hub page(s) to content/hubs/${C.reset}`);
        totalWritten += n;
      } else if (!doWrite) {
        const actionable = patches.filter(p => p.type !== 'noop').length;
        console.log(`\n  ${C.grey}→ Run with --write to generate ${actionable} hub page(s)${C.reset}`);
      }
      console.log();
    }

    // ── 3. RELATED POSTS ────────────────────────────────────────────────────
    if (doRelated) {
      console.log(`${C.bold}── Related Posts ──────────────────────────────────────────${C.reset}`);
      const patches = buildRelatedPatches(results, tiersData, contentDir);
      for (const p of patches) {
        const rel = relative(process.cwd(), p.filepath);
        console.log(`  ${C.bold}${rel}${C.reset}  ${colour(results.find(r => r.slug === p.slug)?.total ?? 0)}${results.find(r => r.slug === p.slug)?.total ?? '?'}/100${C.reset}`);
        p.related.forEach(r => {
          console.log(`    ${C.grey}→ ${r.path}  (score: ${r.score})${C.reset}`);
        });
        if (!doWrite) console.log(`    ${C.grey}→ Run with --write to patch related=[...] in front matter${C.reset}`);
      }
      const n = applyRelatedPatches(patches, doWrite, contentDir);
      if (doWrite && n > 0) {
        console.log(`\n  ${C.green}✓ Patched related posts in ${n} file(s)${C.reset}`);
        totalWritten += n;
      } else if (!doWrite) {
        console.log(`\n  ${C.grey}→ Run with --write to patch ${patches.length} file(s)${C.reset}`);
      }
      console.log();
    }

    // Summary
    console.log(`${C.bold}──────────────────────────────────────────────${C.reset}`);
    if (doWrite) {
      console.log(`${C.bold}${C.green}Automation complete. ${totalWritten} file(s) written.${C.reset}\n`);
    } else {
      console.log(`${C.bold}Dry-run complete.${C.reset} Use ${C.bold}--write${C.reset} to apply changes.\n`);
    }
    return;
  }

  // ════════════════════════════════════════════════════════════════════════════
  // FIX MODE — content fixes (description, alt text)
  // ════════════════════════════════════════════════════════════════════════════
  if (doFix) {
    const modeLabel = doWrite
      ? `${C.red}WRITE MODE — files will be mutated${C.reset}`
      : `${C.green}DRY-RUN — no files will be changed${C.reset}`;
    console.log(`\n${C.bold}${C.cyan}╔══════════════════════════════════════════════════════════╗${C.reset}`);
    console.log(`${C.bold}${C.cyan}║          SEO ENGINE — Fix Mode                           ║${C.reset}`);
    console.log(`${C.bold}${C.cyan}╚══════════════════════════════════════════════════════════╝${C.reset}`);
    console.log(`  ${modeLabel}\n`);

    let fixedCount = 0, patchCount = 0;
    const fixReport = [];

    for (const result of results) {
      const rel       = relative(process.cwd(), result.file);
      const fixes     = generateFixes(result.file, result);
      const hasPatch  = fixes.patches.length > 0;
      const hasSugg   = fixes.h2suggestions.length > 0 || fixes.titleNote.length > 0;
      if (!hasPatch && !hasSugg) continue;

      console.log(`${C.bold}${rel}${C.reset}  ${colour(result.total)}${result.total}/100${C.reset}`);
      if (doReport || !doWrite) printDiff(result.file, fixes);

      if (doWrite && hasPatch) {
        const newSrc = applyPatches(result.file, fixes);
        if (newSrc) {
          writeFileSync(result.file, newSrc, 'utf-8');
          const nr    = scoreFile(result.file);
          const delta = nr.total - result.total;
          console.log(`  ${C.green}✓ Written.${C.reset} Score: ${result.total} → ${C.green}${nr.total}${C.reset} (${delta >= 0 ? '+' : ''}${delta} pts)`);
          fixedCount++;
          patchCount += fixes.patches.length;
          fixReport.push({ file: rel, before: result.total, after: nr.total, patches: fixes.patches.map(p => p.type) });
        }
      } else if (!doWrite && hasPatch) {
        console.log(`  ${C.grey}→ Run with --write to apply: ${fixes.patches.map(p => p.type).join(', ')}${C.reset}`);
      }
      console.log();
    }

    console.log(`${C.bold}─────────────────────────────────────────────${C.reset}`);
    if (doWrite) {
      console.log(`${C.bold}${C.green}Fixed ${fixedCount} file(s), ${patchCount} patch(es) applied.${C.reset}`);
      fixReport.forEach(r => {
        const d = r.after - r.before;
        console.log(`  ${r.file}  ${r.before} → ${C.green}${r.after}${C.reset} (${d >= 0 ? '+' : ''}${d}) [${r.patches.join(', ')}]`);
      });
    } else {
      const fixable = results.filter(r => { try { return generateFixes(r.file, r).patches.length > 0; } catch { return false; } }).length;
      console.log(`${C.bold}Dry-run complete.${C.reset} ${fixable} file(s) have auto-fixable issues.`);
      console.log(`${C.grey}Run with --write --target <file> to apply to a single file.${C.reset}`);
    }
    console.log();
    return;
  }

  // ════════════════════════════════════════════════════════════════════════════
  // AUDIT MODE (default)
  // ════════════════════════════════════════════════════════════════════════════
  const shown = minScore > 0 ? results.filter(r => r.total < minScore) : results;

  console.log(`\n${C.bold}${C.cyan}╔══════════════════════════════════════════════════════════╗${C.reset}`);
  console.log(`${C.bold}${C.cyan}║          SEO ENGINE — Content Audit                      ║${C.reset}`);
  console.log(`${C.bold}${C.cyan}╚══════════════════════════════════════════════════════════╝${C.reset}\n`);
  console.log(`${C.grey}Scanned: ${files.length}   Shown: ${shown.length}   Errors: ${errors}${C.reset}\n`);

  for (const r of shown) {
    const rel = relative(process.cwd(), r.file);
    console.log(`${C.bold}${rel}${C.reset}`);
    console.log(`  ${colour(r.total)}${bar(r.total)} ${r.total}/100${C.reset}  ${C.grey}${r.title}${C.reset}`);
    if (r.keyword) console.log(`  ${C.grey}keyword: ${r.keyword}${C.reset}`);
    console.log(`  ${C.grey}words:${r.meta.words}  tags:${r.meta.tags}  imgs:${r.meta.images}  int:${r.meta.internalLinks}  ext:${r.meta.externalLinks}${C.reset}`);
    r.notes.forEach(n => console.log(`  ${n.startsWith('✗') ? C.red : C.yellow}${n}${C.reset}`));
    console.log();
  }

  const avg   = results.reduce((a, b) => a + b.total, 0) / results.length;
  const green = results.filter(r => r.total >= 80).length;
  const amber = results.filter(r => r.total >= 60 && r.total < 80).length;
  const red   = results.filter(r => r.total < 60).length;

  console.log(`${C.bold}─────────────────────────────────────────────${C.reset}`);
  console.log(`${C.bold}SITE SCORE: ${colour(avg)}${avg.toFixed(1)}/100${C.reset}`);
  console.log(`  ${C.green}● Good (≥80): ${green}${C.reset}   ${C.yellow}● OK (60–79): ${amber}${C.reset}   ${C.red}● Poor (<60): ${red}${C.reset}\n`);

  const worst = [...results].sort((a, b) => a.total - b.total).slice(0, 5);
  if (worst.length && worst[0].total < 80) {
    console.log(`${C.bold}Top priorities:${C.reset}`);
    worst.filter(r => r.total < 80).forEach(r => {
      console.log(`  ${colour(r.total)}${r.total.toString().padStart(3)}/100${C.reset}  ${relative(process.cwd(), r.file)}`);
      r.notes.filter(n => n.startsWith('✗')).slice(0, 2).forEach(n => console.log(`        ${C.red}${n}${C.reset}`));
    });
    console.log();
  }

  if (writeJson) {
    const out = {
      generated_at: new Date().toISOString(),
      site_score:   Math.round(avg * 10) / 10,
      totals:       { good: green, ok: amber, poor: red, files: results.length },
      posts:        results.map(r => ({
        file:      relative(process.cwd(), r.file),
        slug:      r.slug, title: r.title, score: r.total,
        keyword:   r.keyword, meta: r.meta, issues: r.notes, breakdown: r.scores,
      })),
    };
    writeFileSync('seo-report.json', JSON.stringify(out, null, 2));
    console.log(`${C.green}✓ Written: seo-report.json${C.reset}\n`);
  }
}

main().catch(e => { console.error(`${C.red}Fatal: ${e.message}${C.reset}`); process.exit(1); });
