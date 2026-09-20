#!/usr/bin/env node
// Serial page runner for Steps 4.0–4.4.
//
// Stage P has already selected the contract pages and written one section
// manifest per page. This runner reuses that exact page list, gives each page
// its own output directory, and runs the browser writer once per kind. Keeping
// writes serial prevents one page's hover DOM from leaking into another page's
// manifest; the read-only QA checks can run in parallel afterwards.

import { spawn } from 'node:child_process';
import { existsSync, readFileSync, mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { hamburgerKindHeight, isHamburgerKind, kindCaptureWidth, pageSlug, resolveCaptureKinds, slugify, uniquePageEntries } from './component-state-utils.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const RUNNER = path.join(HERE, 'capture-component-states.mjs');

const values = new Map();
const repeated = new Map();
for (let i = 2; i < process.argv.length; i++) {
  const token = process.argv[i];
  if (!token.startsWith('--')) continue;
  const key = token.slice(2);
  if (key === 'help' || key === 'h') {
    console.log('Usage: node capture-site-component-states.mjs --pages-json source-site/pages.json [--pages home,contact] [--out source-site/components] [--headless]');
    process.exit(0);
  }
  if (key === 'headless' || key === 'allow-faq' || key === 'allow-dropdown' || key === 'skip-hamburger' || key === 'auto' || key === 'human') { values.set(key, '1'); continue; }
  const next = process.argv[i + 1];
  if (!next || next.startsWith('--')) { console.error(`missing value for --${key}`); process.exit(2); }
  i++;
  if (key === 'url') {
    if (!repeated.has(key)) repeated.set(key, []);
    repeated.get(key).push(next);
  } else values.set(key, next);
}

const get = (key, fallback) => values.has(key) ? values.get(key) : fallback;
const pagesJson = get('pages-json', '');
const out = path.resolve(get('out', 'source-site/components'));
const captureDir = path.resolve(get('capture-dir', 'capture'));
const kinds = resolveCaptureKinds({
  kinds: get('kinds', 'nav,buttons,forms,footer').split(',').map((kind) => kind.trim()).filter(Boolean),
  allowFaq: values.has('allow-faq'),
  allowDropdown: values.has('allow-dropdown'),
  allowHamburger: !values.has('skip-hamburger'),
});
const max = get('max', '40');
const maxStates = get('max-states', '2');
const width = get('width', '1440');
const height = get('height', '1000');
const maxPages = Number.parseInt(get('max-pages', '1'), 10);
const requestedPages = get('pages', 'home').split(',').map((value) => value.trim()).filter(Boolean);
const headless = values.has('headless');
const allowMultiPage = values.has('allow-multi-page');

const pageFromUrl = (url, fallback = 'page') => {
  try {
    const pathname = new URL(url).pathname;
    return pathname === '/' || !pathname.replace(/\/+$/, '') ? 'home' : slugify(pathname, fallback);
  } catch {
    return fallback;
  }
};

const pageMatches = (entry, token) => {
  const candidates = [entry.slug, entry.path, entry.name, entry.url, pageFromUrl(entry.url)]
    .filter(Boolean).map((value) => String(value).replace(/^\/+|\/+$/g, '').toLowerCase());
  const wanted = String(token).replace(/^\/+|\/+$/g, '').toLowerCase();
  return candidates.includes(wanted) || candidates.some((value) => value.endsWith(`/${wanted}`));
};

let entries = [];
if (pagesJson) {
  try {
    const parsed = JSON.parse(readFileSync(path.resolve(pagesJson), 'utf8'));
    const raw = Array.isArray(parsed) ? parsed : (parsed.pages || []);
    entries = uniquePageEntries(raw).map((entry, index) => ({
      ...entry,
      slug: pageFromUrl(entry.url, pageSlug(entry, index)),
    }));
  } catch (error) {
    console.error(`could not read --pages-json ${pagesJson}: ${error.message}`);
    process.exit(2);
  }
}

for (const url of repeated.get('url') || []) {
  entries.push({ url, slug: pageFromUrl(url, `page-${entries.length + 1}`) });
}

const deduped = [];
const seenUrls = new Set();
for (const entry of entries) {
  if (!entry.url || seenUrls.has(entry.url)) continue;
  seenUrls.add(entry.url);
  if (!deduped.some((other) => other.slug === entry.slug)) deduped.push(entry);
}
entries = deduped;

if (requestedPages.length) entries = entries.filter((entry) => requestedPages.some((token) => pageMatches(entry, token)));
entries.sort((a, b) => (a.slug === 'home' ? -1 : 0) - (b.slug === 'home' ? -1 : 0));
if (Number.isFinite(maxPages) && maxPages > 0) entries = entries.slice(0, maxPages);

// Storm lock: A/6 default is homepage only. Extra routes need --allow-multi-page.
if (entries.length > 1 && !allowMultiPage) {
  console.error(`refusing ${entries.length} pages (${entries.map((e) => e.slug).join(', ')}).`);
  console.error('A/6 is homepage-only. Pass --pages home, or --allow-multi-page only when the user named extra routes.');
  process.exit(2);
}

if (!entries.length) {
  console.error('no pages — pass --pages-json source-site/pages.json or repeat --url <url>');
  process.exit(2);
}
const allowedKinds = new Set(['nav', 'buttons', 'forms', 'faq', 'footer', 'dropdown', 'navbar-dropdown', 'hamburger', 'nav-mobile', 'nav-mobile-768', 'nav-mobile-390']);
const invalidKind = kinds.find((kind) => !allowedKinds.has(kind));
if (invalidKind) {
  console.error(`invalid --kinds entry: ${invalidKind}`);
  process.exit(2);
}
mkdirSync(out, { recursive: true });

const spawnCaptureWith = (script, args) => new Promise((resolve) => {
  const child = spawn(process.execPath, [script, ...args], { stdio: 'inherit' });
  child.once('close', (code, signal) => resolve({ code: code ?? 1, signal }));
  child.once('error', (error) => resolve({ code: 1, error: error.message }));
});
const spawnCapture = (args) => spawnCaptureWith(RUNNER, args);

// Human-led capture is step 1.3 — the Chrome Capture Tool extension in
// `capture-extension/`. This script is the automated / CI hunter only, so refuse
// to run without an explicit --auto or --headless rather than silently hunting
// targets a person is meant to pick.
if (!values.has('auto') && !headless) {
  console.error('Human-led capture is 1.3: open the source URL in Chrome with');
  console.error('  ?paperFileId=<id>&projectRoot=<abs path>');
  console.error('and use the Paper Capture Tool side panel (Nav → Hover → Multi → Single → Done).');
  console.error('This script only runs automated discovery: pass --auto (CI) or --headless.');
  process.exit(2);
}

const run = {
  startedAt: new Date().toISOString(),
  pages: entries.map(({ url, slug }) => ({ url, slug })),
  kinds,
  output: out,
  captureDir,
  results: [],
};

for (const entry of entries) {
    const sectionManifest = [
      path.join(captureDir, entry.slug, 'manifest.json'),
      path.join(captureDir, `${entry.slug}-desktop`, 'manifest.json'),
    ].find((file) => existsSync(file));
    for (const kind of kinds) {
      const args = [
        '--url', entry.url,
        '--page', entry.slug,
        '--kind', kind,
        '--out', out,
        '--max', max,
        '--max-states', maxStates,
        '--width', String(kindCaptureWidth(kind, width)),
        '--height', isHamburgerKind(kind) ? String(hamburgerKindHeight(kind, kindCaptureWidth(kind, width))) : height,
      ];
      if (sectionManifest) args.push('--section-manifest', sectionManifest);
      else console.error(`warning: ${entry.slug} has no Stage P section manifest under ${captureDir}`);
      if (headless) args.push('--headless');
      if (values.has('allow-faq')) args.push('--allow-faq');
      if (values.has('allow-dropdown')) args.push('--allow-dropdown');
    console.error(`\n[component states] ${entry.slug} · ${kind}`);
    const result = await spawnCapture(args);
    run.results.push({ page: entry.slug, kind, sectionManifest: sectionManifest || null, ...result });
  }
}

run.finishedAt = new Date().toISOString();
run.failed = run.results.filter((result) => result.code !== 0).length;
writeFileSync(path.join(out, 'capture-run.json'), JSON.stringify(run, null, 2));
console.log(JSON.stringify({ pages: entries.length, kinds, failed: run.failed, output: out }, null, 2));
if (run.failed) process.exit(1);
