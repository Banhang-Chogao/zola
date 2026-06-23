#!/usr/bin/env node
/**
 * seo_engine.js — SEO scorer for Zola markdown content
 *
 * Usage:
 *   node seo_engine.js                      # scan ./content recursively
 *   node seo_engine.js content/post.md      # score single file
 *   node seo_engine.js --dir ./content      # scan custom directory
 *   node seo_engine.js --json               # also write seo-report.json
 *   node seo_engine.js --min 70             # only show posts scoring below 70
 *   node seo_engine.js --help
 *
 * Scoring (total 100 pts):
 *   title present (8) · title length (6) · description (10) · slug (6)
 *   keyword in title (8) · keyword in intro (6) · keyword in h2 (6)
 *   heading structure (8) · word count (10) · og image (6)
 *   img alt coverage (6) · internal links (6) · external links (4)
 *   tags (4) · date present (3) · readability (3)
 *
 * Front matter: Zola TOML (+++ ... +++) or YAML (--- ... ---) supported.
 */

import { readFileSync, readdirSync, statSync, writeFileSync, existsSync } from 'fs';
import { join, basename, extname, relative } from 'path';
import { fileURLToPath } from 'url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));

// ─── Weights (total = 100) ────────────────────────────────────────────────────
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

const TITLE_MIN = 20, TITLE_MAX = 65;
const DESC_MIN  = 50, DESC_MAX  = 160;
const SLUG_MAX  = 60;
const WORDS_GOOD = 600, WORDS_OK = 300;

// ─── ANSI colours ─────────────────────────────────────────────────────────────
const C = {
  reset:  '\x1b[0m',
  bold:   '\x1b[1m',
  red:    '\x1b[31m',
  yellow: '\x1b[33m',
  green:  '\x1b[32m',
  cyan:   '\x1b[36m',
  grey:   '\x1b[90m',
  white:  '\x1b[97m',
};

function colour(score) {
  if (score >= 80) return C.green;
  if (score >= 60) return C.yellow;
  return C.red;
}

function bar(score, width = 20) {
  const filled = Math.round((score / 100) * width);
  return `[${'█'.repeat(filled)}${'░'.repeat(width - filled)}]`;
}

// ─── Front matter parser ──────────────────────────────────────────────────────
function parseFrontMatter(src) {
  // TOML: +++ ... +++
  const toml = src.match(/^\+\+\+\r?\n([\s\S]*?)\r?\n\+\+\+\r?\n?([\s\S]*)$/);
  if (toml) {
    return { fm: parseToml(toml[1]), body: toml[2] };
  }
  // YAML: --- ... ---
  const yaml = src.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/);
  if (yaml) {
    return { fm: parseYaml(yaml[1]), body: yaml[2] };
  }
  return { fm: {}, body: src };
}

/** Minimal TOML parser — handles string, bool, array, inline table values */
function parseToml(raw) {
  const result = {};
  let section = result;
  for (const line of raw.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;

    // [section]
    const sec = trimmed.match(/^\[(\w+)\]$/);
    if (sec) { result[sec[1]] = result[sec[1]] || {}; section = result[sec[1]]; continue; }

    const eq = trimmed.indexOf('=');
    if (eq === -1) continue;
    const key = trimmed.slice(0, eq).trim();
    const val = trimmed.slice(eq + 1).trim();
    section[key] = parseTomlValue(val);
  }
  return result;
}

function parseTomlValue(v) {
  if (v === 'true')  return true;
  if (v === 'false') return false;
  if (v.startsWith('"') || v.startsWith("'")) return v.slice(1, -1);
  if (v.startsWith('[')) {
    return v.slice(1, -1).split(',').map(s => s.trim().replace(/^["']|["']$/g, '')).filter(Boolean);
  }
  const n = Number(v);
  return isNaN(n) ? v.replace(/^["']|["']$/g, '') : n;
}

/** Minimal YAML parser — handles string, bool, list values */
function parseYaml(raw) {
  const result = {};
  const lines  = raw.split('\n');
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const m = line.match(/^(\w[\w-]*):\s*(.*)/);
    if (!m) { i++; continue; }
    const key = m[1];
    const rest = m[2].trim();
    if (rest === '' || rest === '|' || rest === '>') {
      // collect list items on next lines
      const items = [];
      i++;
      while (i < lines.length && lines[i].match(/^\s+-\s/)) {
        items.push(lines[i].replace(/^\s+-\s+/, '').trim().replace(/^["']|["']$/g, ''));
        i++;
      }
      result[key] = items.length ? items : '';
    } else if (rest.startsWith('[')) {
      result[key] = rest.slice(1, -1).split(',').map(s => s.trim().replace(/^["']|["']$/g, '')).filter(Boolean);
      i++;
    } else {
      result[key] = rest.replace(/^["']|["']$/g, '');
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

function wordCount(text) {
  return stripMarkdown(text).trim().split(/\s+/).filter(Boolean).length;
}

function avgSentenceLength(text) {
  const plain = stripMarkdown(text);
  const sentences = plain.split(/[.!?]+/).filter(s => s.trim().length > 0);
  if (!sentences.length) return 0;
  const words = sentences.map(s => s.trim().split(/\s+/).filter(Boolean).length);
  return words.reduce((a, b) => a + b, 0) / sentences.length;
}

// ─── Scorer ───────────────────────────────────────────────────────────────────
function scoreFile(filepath) {
  const src  = readFileSync(filepath, 'utf-8');
  const { fm, body } = parseFrontMatter(src);
  const slug = basename(filepath, extname(filepath));

  const extra   = fm.extra || {};
  const title   = String(fm.title   || '').trim();
  const desc    = String(fm.description || extra.description || '').trim();
  const keyword = String(extra.seo_keyword || extra.keyword || '').trim().toLowerCase();
  const ogImage = fm.extra?.thumbnail || fm.extra?.og_image || fm.cover_image || '';
  const tags    = Array.isArray(fm.taxonomies?.tags) ? fm.taxonomies.tags :
                  Array.isArray(fm.tags) ? fm.tags : [];
  const date    = fm.date || fm.published || '';

  const bodyLower = body.toLowerCase();
  const intro     = body.split('\n').filter(l => l.trim() && !l.startsWith('#')).slice(0, 5).join(' ');
  const h2s       = (body.match(/^##\s+.+$/gm) || []).map(h => h.replace(/^#+\s+/, '').toLowerCase());
  const allHeadings = body.match(/^#{1,6}\s+.+$/gm) || [];
  const images    = [...body.matchAll(/!\[([^\]]*)\]\([^)]+\)/g)];
  const links     = [...body.matchAll(/\[([^\]]+)\]\(([^)]+)\)/g)];
  const internalLinks = links.filter(m => !m[2].startsWith('http') || m[2].includes(fm.base_url || 'localhost'));
  const externalLinks = links.filter(m => m[2].startsWith('http') && !m[2].includes('localhost'));
  const imagesWithAlt = images.filter(m => m[1].trim().length > 0);
  const wc        = wordCount(body);
  const avgSL     = avgSentenceLength(body);

  const scores = {};
  const notes  = [];

  // title present
  if (title) {
    scores.title_present = W.title_present;
  } else {
    scores.title_present = 0;
    notes.push('✗ Missing title');
  }

  // title length
  if (title.length >= TITLE_MIN && title.length <= TITLE_MAX) {
    scores.title_length = W.title_length;
  } else if (title.length > 0) {
    scores.title_length = Math.round(W.title_length * 0.5);
    notes.push(`△ Title length ${title.length} chars (ideal ${TITLE_MIN}–${TITLE_MAX})`);
  } else {
    scores.title_length = 0;
  }

  // description
  if (desc.length >= DESC_MIN && desc.length <= DESC_MAX) {
    scores.description = W.description;
  } else if (desc.length > 0) {
    scores.description = Math.round(W.description * 0.5);
    notes.push(`△ Description length ${desc.length} chars (ideal ${DESC_MIN}–${DESC_MAX})`);
  } else {
    scores.description = 0;
    notes.push('✗ Missing meta description');
  }

  // slug
  if (slug.length <= SLUG_MAX && /^[a-z0-9-]+$/.test(slug)) {
    scores.slug = W.slug;
  } else if (slug.length <= SLUG_MAX) {
    scores.slug = Math.round(W.slug * 0.7);
    notes.push(`△ Slug "${slug}" has non-ascii characters`);
  } else {
    scores.slug = Math.round(W.slug * 0.5);
    notes.push(`△ Slug too long (${slug.length} chars, max ${SLUG_MAX})`);
  }

  // keyword in title
  if (!keyword) {
    scores.kw_title = W.kw_title * 0.5; // neutral — no keyword declared
  } else if (title.toLowerCase().includes(keyword)) {
    scores.kw_title = W.kw_title;
  } else {
    scores.kw_title = 0;
    notes.push(`✗ Keyword "${keyword}" not found in title`);
  }

  // keyword in intro
  if (!keyword) {
    scores.kw_intro = W.kw_intro * 0.5;
  } else if (intro.toLowerCase().includes(keyword)) {
    scores.kw_intro = W.kw_intro;
  } else {
    scores.kw_intro = 0;
    notes.push(`✗ Keyword "${keyword}" not in first paragraphs`);
  }

  // keyword in h2
  if (!keyword) {
    scores.kw_heading = W.kw_heading * 0.5;
  } else if (h2s.some(h => h.includes(keyword))) {
    scores.kw_heading = W.kw_heading;
  } else {
    scores.kw_heading = 0;
    notes.push(`△ Keyword "${keyword}" not in any H2`);
  }

  // heading structure (has h2+, hierarchical)
  const h1count = (body.match(/^#\s+.+$/gm) || []).length;
  const h2count = (body.match(/^##\s+.+$/gm) || []).length;
  if (h2count >= 2 && h1count <= 1) {
    scores.headings = W.headings;
  } else if (h2count >= 1) {
    scores.headings = Math.round(W.headings * 0.6);
    notes.push(`△ Headings: H1=${h1count} H2=${h2count} (recommend ≥2 H2, ≤1 H1)`);
  } else {
    scores.headings = 0;
    notes.push('✗ No H2 headings found — add section structure');
  }

  // word count
  if (wc >= WORDS_GOOD) {
    scores.word_count = W.word_count;
  } else if (wc >= WORDS_OK) {
    scores.word_count = Math.round(W.word_count * 0.6);
    notes.push(`△ Word count ${wc} (good ≥${WORDS_GOOD}, ok ≥${WORDS_OK})`);
  } else {
    scores.word_count = 0;
    notes.push(`✗ Too short: ${wc} words (min ${WORDS_OK})`);
  }

  // og image
  if (ogImage) {
    scores.og_image = W.og_image;
  } else {
    scores.og_image = 0;
    notes.push('✗ Missing OG / thumbnail image');
  }

  // img alt coverage
  if (images.length === 0) {
    scores.img_alt = Math.round(W.img_alt * 0.5); // no images — neutral
  } else {
    const ratio = imagesWithAlt.length / images.length;
    scores.img_alt = Math.round(W.img_alt * ratio);
    if (ratio < 1) notes.push(`△ ${images.length - imagesWithAlt.length}/${images.length} images missing alt text`);
  }

  // internal links
  if (internalLinks.length >= 3) {
    scores.internal_link = W.internal_link;
  } else if (internalLinks.length >= 1) {
    scores.internal_link = Math.round(W.internal_link * 0.6);
    notes.push(`△ Only ${internalLinks.length} internal link(s) (recommend ≥3)`);
  } else {
    scores.internal_link = 0;
    notes.push('✗ No internal links');
  }

  // external links
  if (externalLinks.length >= 1) {
    scores.external_link = W.external_link;
  } else {
    scores.external_link = Math.round(W.external_link * 0.5);
    notes.push('△ No external links (outbound authority signals)');
  }

  // tags
  if (tags.length >= 3) {
    scores.tags = W.tags;
  } else if (tags.length >= 1) {
    scores.tags = Math.round(W.tags * 0.6);
    notes.push(`△ Only ${tags.length} tag(s) (recommend 3–7)`);
  } else {
    scores.tags = 0;
    notes.push('✗ No tags defined');
  }

  // date
  scores.date = date ? W.date : 0;
  if (!date) notes.push('✗ No publication date');

  // readability (avg sentence length)
  if (avgSL > 0 && avgSL <= 20) {
    scores.readability = W.readability;
  } else if (avgSL <= 30) {
    scores.readability = Math.round(W.readability * 0.6);
    notes.push(`△ Avg sentence length ${avgSL.toFixed(1)} words (aim ≤20)`);
  } else {
    scores.readability = 0;
    notes.push(`✗ Sentences too long on avg (${avgSL.toFixed(1)} words)`);
  }

  const total = Object.values(scores).reduce((a, b) => a + b, 0);

  return {
    file: filepath,
    slug,
    title: title || '(no title)',
    keyword: keyword || null,
    total: Math.min(100, Math.round(total)),
    scores,
    notes,
    meta: { words: wc, tags: tags.length, images: images.length, internalLinks: internalLinks.length, externalLinks: externalLinks.length },
  };
}

// ─── File collection ──────────────────────────────────────────────────────────
function collectMarkdown(dir) {
  const files = [];
  if (!existsSync(dir)) return files;
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const stat = statSync(full);
    if (stat.isDirectory()) {
      files.push(...collectMarkdown(full));
    } else if (['.md', '.markdown'].includes(extname(entry).toLowerCase())) {
      files.push(full);
    }
  }
  return files;
}

// ─── Main ─────────────────────────────────────────────────────────────────────
function main() {
  const args = process.argv.slice(2);
  if (args.includes('--help') || args.includes('-h')) {
    console.log(`
${C.bold}seo_engine.js${C.reset} — SEO scorer for Zola markdown content

Usage:
  node seo_engine.js                       scan ./content directory
  node seo_engine.js path/to/post.md       score a single file
  node seo_engine.js --dir ./my-content    scan custom directory
  node seo_engine.js --json                write seo-report.json
  node seo_engine.js --min 70              show only posts scoring below 70
  node seo_engine.js --sort score          sort by score (default: filename)
`);
    process.exit(0);
  }

  const writeJson  = args.includes('--json');
  const minScore   = Number(args[args.indexOf('--min') + 1] ?? 0) || 0;
  const dirIdx     = args.indexOf('--dir');
  const sortBy     = args[args.indexOf('--sort') + 1] ?? 'file';

  let files = [];
  const positional = args.filter(a => !a.startsWith('--') && !/^\d+$/.test(a));

  if (positional.length > 0) {
    for (const p of positional) {
      const stat = statSync(p);
      if (stat.isDirectory()) files.push(...collectMarkdown(p));
      else files.push(p);
    }
  } else if (dirIdx !== -1) {
    files = collectMarkdown(args[dirIdx + 1]);
  } else {
    // auto-detect content directory
    for (const candidate of ['content', 'posts', 'blog', 'src/content']) {
      if (existsSync(candidate)) { files = collectMarkdown(candidate); break; }
    }
    if (!files.length) {
      console.error(`${C.red}No content directory found. Use --dir <path> or pass files directly.${C.reset}`);
      process.exit(1);
    }
  }

  if (!files.length) {
    console.log(`${C.yellow}No markdown files found.${C.reset}`);
    process.exit(0);
  }

  // Score all files
  const results = [];
  let errors = 0;
  for (const f of files) {
    try {
      results.push(scoreFile(f));
    } catch (e) {
      console.error(`${C.red}Error scoring ${f}: ${e.message}${C.reset}`);
      errors++;
    }
  }

  // Sort
  if (sortBy === 'score') results.sort((a, b) => a.total - b.total);
  else results.sort((a, b) => a.file.localeCompare(b.file));

  // Filter
  const shown = minScore > 0 ? results.filter(r => r.total < minScore) : results;

  // ── Report header ──
  console.log(`\n${C.bold}${C.cyan}╔══════════════════════════════════════════════════════════╗${C.reset}`);
  console.log(`${C.bold}${C.cyan}║          SEO ENGINE — Zola Content Audit                 ║${C.reset}`);
  console.log(`${C.bold}${C.cyan}╚══════════════════════════════════════════════════════════╝${C.reset}\n`);
  console.log(`${C.grey}Scanned: ${files.length} files   Shown: ${shown.length}   Errors: ${errors}${C.reset}\n`);

  for (const r of shown) {
    const col = colour(r.total);
    const rel = relative(process.cwd(), r.file);
    console.log(`${C.bold}${rel}${C.reset}`);
    console.log(`  ${col}${bar(r.total)} ${r.total}/100${C.reset}  ${C.grey}${r.title}${C.reset}`);
    if (r.keyword) console.log(`  ${C.grey}keyword: ${r.keyword}${C.reset}`);
    console.log(`  ${C.grey}words:${r.meta.words}  tags:${r.meta.tags}  imgs:${r.meta.images}  int-links:${r.meta.internalLinks}  ext-links:${r.meta.externalLinks}${C.reset}`);
    for (const note of r.notes) {
      const nc = note.startsWith('✗') ? C.red : C.yellow;
      console.log(`  ${nc}${note}${C.reset}`);
    }
    console.log();
  }

  // ── Summary table ──
  const avg   = results.reduce((a, b) => a + b.total, 0) / results.length;
  const green = results.filter(r => r.total >= 80).length;
  const amber = results.filter(r => r.total >= 60 && r.total < 80).length;
  const red   = results.filter(r => r.total < 60).length;

  console.log(`${C.bold}─────────────────────────────────────────────${C.reset}`);
  console.log(`${C.bold}SITE SCORE: ${colour(avg)}${avg.toFixed(1)}/100${C.reset}`);
  console.log(`  ${C.green}● Good  (≥80): ${green}${C.reset}   ${C.yellow}● OK (60–79): ${amber}${C.reset}   ${C.red}● Poor (<60): ${red}${C.reset}`);
  console.log();

  // Worst 5
  const worst = [...results].sort((a, b) => a.total - b.total).slice(0, 5);
  if (worst.length && worst[0].total < 80) {
    console.log(`${C.bold}Top priorities to fix:${C.reset}`);
    for (const r of worst) {
      if (r.total >= 80) break;
      const rel = relative(process.cwd(), r.file);
      console.log(`  ${colour(r.total)}${r.total.toString().padStart(3)}/100${C.reset}  ${rel}`);
      for (const n of r.notes.filter(n => n.startsWith('✗')).slice(0, 2)) {
        console.log(`        ${C.red}${n}${C.reset}`);
      }
    }
    console.log();
  }

  // JSON output
  if (writeJson) {
    const out = {
      generated_at: new Date().toISOString(),
      site_score: Math.round(avg * 10) / 10,
      totals: { good: green, ok: amber, poor: red, files: results.length },
      posts: results.map(r => ({
        file: relative(process.cwd(), r.file),
        slug: r.slug,
        title: r.title,
        score: r.total,
        keyword: r.keyword,
        meta: r.meta,
        issues: r.notes,
        breakdown: r.scores,
      })),
    };
    writeFileSync('seo-report.json', JSON.stringify(out, null, 2));
    console.log(`${C.green}✓ Written: seo-report.json${C.reset}\n`);
  }
}

main();
