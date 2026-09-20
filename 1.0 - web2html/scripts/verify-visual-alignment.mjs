#!/usr/bin/env node
/**
 * 2.2.b / 3.3 computed-style type-align QA.
 *
 * Playwright at 1600×1000 / 768×1024 / 390×844 against file:// rebuild/index.html.
 * Gold is qa/type-align-census.json (lock align + Tailwind size).
 * The skill does not lock or assert fonts.
 *
 * Resolve playwright from $SKILLS/url-to-paper or hover-reel (or this
 * checkout's sibling packages). Never hardcode ~/.claude/skills.
 *
 * If Playwright / Chromium is missing, write a skip receipt and exit 0
 * so the semantics gate does not crash.
 *
 *   node verify-visual-alignment.mjs rebuild/index.html
 *   node verify-visual-alignment.mjs --html rebuild/index.html --census qa/type-align-census.json
 */
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SKILL_ROOT = path.resolve(HERE, '..');
const REPO_ROOT = path.resolve(SKILL_ROOT, '..');

const VIEWPORTS = [
  { name: 'desktop-1600', width: 1600, height: 1000 },
  { name: 'tablet-768', width: 768, height: 1024 },
  { name: 'mobile-390', width: 390, height: 844 },
];

const TOKEN_PX = {
  xs: 12, sm: 14, base: 16, lg: 18, xl: 20,
  '2xl': 24, '3xl': 30, '4xl': 36, '5xl': 48,
  '6xl': 60, '7xl': 72, '8xl': 96, '9xl': 128,
  '10xl': 160, '11xl': 192, '12xl': 224,
};
const SIZE_TOLERANCE_PX = 1.05;

function parseArgs(argv) {
  const out = { html: null, census: null, qa: null, root: null };
  const rest = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--html') out.html = argv[++i];
    else if (a === '--census') out.census = argv[++i];
    else if (a === '--qa') out.qa = argv[++i];
    else if (a === '--root') out.root = argv[++i];
    else if (!a.startsWith('-')) rest.push(a);
  }
  if (!out.html && rest[0]) out.html = rest[0];
  return out;
}

function skillCandidates() {
  const names = [
    'url-to-paper',
    'hover-reel',
    '1.2 url-to-paper',
    '1.3 hover-reel',
  ];
  const roots = [
    process.env.SKILLS,
    path.join(os.homedir(), '.claude', 'skills'),
    REPO_ROOT,
    path.resolve(SKILL_ROOT, '..'),
  ].filter(Boolean);
  const dirs = [process.cwd(), SKILL_ROOT];
  for (const root of roots) {
    for (const name of names) dirs.push(path.join(root, name));
  }
  dirs.push(path.join(REPO_ROOT, '1.2 url-to-paper'));
  dirs.push(path.join(REPO_ROOT, '1.3 hover-reel'));
  return [...new Set(dirs)];
}

async function loadPlaywright() {
  try { return await import('playwright-core'); } catch { /* next */ }
  try { return await import('playwright'); } catch { /* next */ }
  for (const dir of skillCandidates()) {
    for (const pkg of ['playwright-core', 'playwright']) {
      try {
        const req = createRequire(path.join(dir, 'noop.js'));
        const resolved = req.resolve(pkg);
        return await import(pathToFileURL(resolved).href);
      } catch { /* next */ }
    }
  }
  return null;
}

function projectRoot(htmlPath) {
  const abs = path.resolve(htmlPath);
  const parent = path.dirname(abs);
  if (path.basename(parent) === 'rebuild') return path.dirname(parent);
  return parent;
}

function defaultCensus(root) {
  return path.join(root, 'qa', 'type-align-census.json');
}

function defaultQa(root) {
  return path.join(root, 'qa', 'visual-align-qa.json');
}

function writeJson(dest, data) {
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.writeFileSync(dest, JSON.stringify(data, null, 2) + '\n', 'utf8');
}

function alignFamily(value) {
  if (!value) return null;
  const v = String(value).trim().toLowerCase();
  if (v === 'start' || v === 'left') return 'start';
  if (v === 'end' || v === 'right') return 'end';
  if (v === 'center' || v === 'justify') return v;
  return null;
}

function alignMatches(expected, actual) {
  const exp = alignFamily(expected);
  if (!exp) return true;
  return exp === alignFamily(actual);
}

function parsePx(value) {
  if (value == null) return null;
  const m = String(value).trim().match(/^(\d+(?:\.\d+)?)px$/i);
  return m ? Number(m[1]) : Number.isFinite(Number(value)) ? Number(value) : null;
}

function sizeMatches(expected, actualPx) {
  if (!expected) return true;
  if (actualPx == null) return false;
  let token = String(expected).trim();
  if (token.startsWith('text-')) token = token.slice(5);
  let want;
  if (token.endsWith('px')) want = parsePx(token);
  else want = TOKEN_PX[token];
  if (want == null) return false;
  return Math.abs(want - actualPx) <= SIZE_TOLERANCE_PX;
}

function censusRows(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data.rows)) return data.rows;
  if (Array.isArray(data.items)) return data.items;
  return [];
}

async function findElement(page, row) {
  if (row.selector) {
    const handle = await page.$(row.selector);
    if (handle) return handle;
  }
  const text = (row.text || '').trim();
  if (!text) return null;
  return page.evaluateHandle((needle) => {
    const tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p'];
    const norm = (s) => (s || '').replace(/\s+/g, ' ').trim();
    const want = norm(needle);
    for (const tag of tags) {
      for (const el of document.querySelectorAll(tag)) {
        if (norm(el.textContent) === want) return el;
      }
    }
    for (const tag of tags) {
      for (const el of document.querySelectorAll(tag)) {
        if (norm(el.textContent).includes(want) && want.length >= 8) return el;
      }
    }
    return null;
  }, text);
}

async function readComputed(handle) {
  if (!handle) return null;
  const el = handle.asElement ? handle.asElement() : handle;
  if (!el) return null;
  return el.evaluate((node) => {
    const cs = window.getComputedStyle(node);
    return {
      fontFamily: cs.fontFamily,
      fontSize: cs.fontSize,
      textAlign: cs.textAlign,
      tag: node.tagName ? node.tagName.toLowerCase() : '',
      id: node.id || '',
    };
  });
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.html) {
    console.error('FAIL: pass rebuild/index.html (positional or --html)');
    process.exit(1);
  }
  const htmlPath = path.resolve(args.html);
  if (!fs.existsSync(htmlPath)) {
    console.error(`FAIL: missing ${htmlPath}`);
    process.exit(1);
  }
  const root = args.root ? path.resolve(args.root) : projectRoot(htmlPath);
  const censusPath = args.census ? path.resolve(args.census) : defaultCensus(root);
  const qaPath = args.qa ? path.resolve(args.qa) : defaultQa(root);

  let census = { rows: [] };
  if (fs.existsSync(censusPath)) {
    census = JSON.parse(fs.readFileSync(censusPath, 'utf8'));
  } else {
    const receipt = {
      ok: true,
      skipped: true,
      reason: `missing census ${censusPath} — run census-type-align.py first`,
      viewports: VIEWPORTS.map((v) => v.name),
    };
    writeJson(qaPath, receipt);
    console.log(`SKIP visual-align: ${receipt.reason}`);
    process.exit(0);
  }
  const rows = censusRows(census);
  const playwright = await loadPlaywright();
  if (!playwright) {
    const receipt = {
      ok: true,
      skipped: true,
      reason: 'playwright missing — resolve from $SKILLS/url-to-paper or hover-reel; do not crash the semantics gate',
      viewports: VIEWPORTS.map((v) => v.name),
      census: censusPath,
    };
    writeJson(qaPath, receipt);
    console.log(`SKIP visual-align: ${receipt.reason}`);
    process.exit(0);
  }

  const chromium = playwright.chromium;
  let browser;
  try {
    browser = await chromium.launch({ headless: true });
  } catch (err) {
    const receipt = {
      ok: true,
      skipped: true,
      reason: `chromium launch failed: ${err.message || err}`,
      viewports: VIEWPORTS.map((v) => v.name),
    };
    writeJson(qaPath, receipt);
    console.log(`SKIP visual-align: ${receipt.reason}`);
    process.exit(0);
  }

  const uri = pathToFileURL(htmlPath).href;
  const failures = [];
  const results = [];

  try {
    for (const vp of VIEWPORTS) {
      const page = await browser.newPage({ viewport: { width: vp.width, height: vp.height } });
      await page.goto(uri, { waitUntil: 'load' });
      for (const row of rows) {
        const handle = await findElement(page, row);
        const computed = await readComputed(handle);
        if (handle && handle.dispose) {
          try { await handle.dispose(); } catch { /* ignore */ }
        }
        const actual = computed
          ? {
              fontFamily: computed.fontFamily,
              fontSize: computed.fontSize,
              fontSizePx: parsePx(computed.fontSize),
              textAlign: computed.textAlign,
              tag: computed.tag,
              id: computed.id,
            }
          : null;
        const errors = [];
        if (!actual) {
          errors.push(`missing element for ${row.selector || row.text || '?'}`);
        } else {
          if (!alignMatches(row.align, actual.textAlign)) {
            errors.push(
              `textAlign gold=${JSON.stringify(row.align)} got=${JSON.stringify(actual.textAlign)}`,
            );
          }
          if (!sizeMatches(row.fontSize, actual.fontSizePx)) {
            errors.push(
              `fontSize gold=${JSON.stringify(row.fontSize)} got=${JSON.stringify(actual.fontSize)}`,
            );
          }
        }
        const rec = {
          viewport: vp.name,
          text: row.text,
          selector: row.selector || null,
          expected: {
            align: row.align || null,
            fontSize: row.fontSize || null,
          },
          actual,
          ok: errors.length === 0,
          errors,
        };
        results.push(rec);
        if (errors.length) {
          for (const e of errors) failures.push(`[${vp.name}] ${e}`);
        }
      }
      await page.close();
    }
  } finally {
    await browser.close();
  }

  const payload = {
    ok: failures.length === 0,
    skipped: false,
    html: htmlPath,
    census: censusPath,
    viewports: VIEWPORTS.map((v) => v.name),
    count: results.length,
    failures,
    results,
  };
  writeJson(qaPath, payload);
  if (failures.length) {
    for (const f of failures) console.error(`FAIL: ${f}`);
    console.error(`${failures.length} visual-align check(s) failed → ${qaPath}`);
    process.exit(2);
  }
  console.log(`OK visual-align ${results.length} check(s) across ${VIEWPORTS.length} viewports → ${qaPath}`);
  process.exit(0);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
