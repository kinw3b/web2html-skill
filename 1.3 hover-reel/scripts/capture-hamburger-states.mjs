#!/usr/bin/env node
/**
 * Click-toggle hamburger / overlay nav at every width that paints the icon.
 *
 * capture-menu-states.mjs is hover-dropdown at 1600. This is click + --width.
 * Closed | open HTML lands on FRAME `Interactive components` (not A/6).
 * Do not invent a burger on desktop when the icon is absent.
 *
 *   node capture-hamburger-states.mjs \
 *     --url https://example.com/ --width 390 --height 844 \
 *     --out source-site/components --page home
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { importSibling, siblingSkill } from './skill-paths.mjs';
import { installVisibleCursor, movePointer, showHud } from './visible-cursor.mjs';
import { captureHamburgerPair } from './hamburger-capture.mjs';
import { writeFluidPairFiles } from './write-dropdown-pair.mjs';
import {
  emptyKindManifest,
  hamburgerKindHeight,
  hamburgerKindWidth,
  INTERACTIVE_COMPONENTS_BOARD,
  interactiveRowMeta,
  resolveHamburgerOutDir,
  slugify,
} from './component-state-utils.mjs';

const SERIALIZER = siblingSkill('url-to-paper', 'scripts/serializer.js');
const arg = (n, d) => { const i = process.argv.indexOf(`--${n}`); return i > -1 ? process.argv[i + 1] : d; };
const has = (n) => process.argv.includes(`--${n}`);

export function parseHamburgerCaptureArgs(argv = process.argv) {
  const get = (n, d) => { const i = argv.indexOf(`--${n}`); return i > -1 ? argv[i + 1] : d; };
  const flag = (n) => argv.includes(`--${n}`);
  const page = get('page', 'home');
  const kind = get('kind', '');
  const width = hamburgerKindWidth(kind, get('width', '390'));
  const height = parseInt(get('height', String(hamburgerKindHeight(kind, width))), 10) || hamburgerKindHeight(kind, width);
  const out = get('out', 'source-site/components');
  const paths = resolveHamburgerOutDir(out, { pageSlug: slugify(page, 'home'), kind: kind || `nav-mobile-${width}`, width });
  const row = interactiveRowMeta({ kind: kind || `nav-mobile-${width}`, viewportWidth: width });
  return {
    url: get('url', ''),
    width,
    height,
    page,
    pageSlug: slugify(page, 'home'),
    kind: kind || row.token,
    headless: flag('headless'),
    json: get('json', paths.json),
    dir: paths.dir,
    paperBoard: INTERACTIVE_COMPONENTS_BOARD,
    row,
  };
}

async function runHamburgerCapture(opts) {
  const { url, width, height, page, pageSlug, kind, headless, json, dir, row } = opts;
  if (!url) {
    console.error('need --url');
    return 1;
  }

  const { launchOptions } = await importSibling('url-to-paper', 'scripts/chrome-path.mjs');
  const { chromium } = await import('playwright');
  const serializerSrc = fs.readFileSync(SERIALIZER, 'utf8');
  const serialize = (pageHandle, sel) => pageHandle.evaluate(
    `(async () => { ${serializerSrc}\n return await fe(${JSON.stringify(sel)}); })()`);

  const browser = await chromium.launch(launchOptions({ visible: !headless }));
  const context = await browser.newContext({
    viewport: { width, height },
    deviceScaleFactor: 2,
    reducedMotion: 'reduce',
  });
  const pageHandle = await context.newPage();
  if (!headless) await installVisibleCursor(pageHandle);
  await pageHandle.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  try { await pageHandle.waitForLoadState('networkidle', { timeout: 15000 }); } catch { /* Framer */ }
  await pageHandle.waitForTimeout(2500);
  await pageHandle.emulateMedia({ reducedMotion: 'no-preference' });
  if (!headless) {
    await installVisibleCursor(pageHandle);
    await showHud(pageHandle, { phase: kind || 'hamburger', current: 1, total: 1, label: 'menu' });
  }

  const pair = await captureHamburgerPair(pageHandle, {
    serialize,
    movePointer,
    viewportWidth: width,
  });

  if (!pair.found) {
    fs.mkdirSync(dir, { recursive: true });
    const empty = emptyKindManifest({
      url, page, pageSlug, kind,
      reason: pair.reason || 'no hamburger at this width — do not invent',
    });
    empty.paperBoard = INTERACTIVE_COMPONENTS_BOARD;
    empty.viewport = { width, height };
    fs.writeFileSync(path.join(dir, 'manifest.json'), JSON.stringify(empty, null, 2));
    if (json) fs.writeFileSync(json, JSON.stringify(empty, null, 2));
    console.error(pair.reason || 'no hamburger candidate');
    await browser.close();
    return 0;
  }

  const manifest = writeFluidPairFiles({
    dir,
    pair,
    url,
    page,
    pageSlug,
    kind,
    mode: 'hamburger',
    sectionId: row.sid,
    viewportWidth: width,
    viewportHeight: height,
  });
  if (json) {
    fs.mkdirSync(path.dirname(json), { recursive: true });
    fs.writeFileSync(json, JSON.stringify({
      url,
      paperBoard: INTERACTIVE_COMPONENTS_BOARD,
      viewport: { width, height },
      trigger: pair.triggerBox,
      overlay: pair.overlay,
      appeared: pair.items,
      manifest,
    }, null, 2));
  }
  await browser.close();
  console.error(`wrote ${dir} — closed | open (${row.sid} · ${row.token}) → ${INTERACTIVE_COMPONENTS_BOARD} @ ${width}`);
  return 0;
}

const invoked = process.argv[1]
  && fileURLToPath(import.meta.url) === path.resolve(process.argv[1]);
if (invoked) {
  const code = await runHamburgerCapture(parseHamburgerCaptureArgs());
  process.exit(code);
}
