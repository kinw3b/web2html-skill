#!/usr/bin/env node
// Hover-triggered dropdown nav — desktop lander width (1600), HTML pair.
//
// Three things this gets right that the naive version did not:
//
// 1. PANEL DETECTION BY DIFF. The panel is found by comparing the set of visible
//    interactive labels while closed vs while open. Only genuinely new labels are
//    menu items, which excludes page content and the Framer badge.
// 2. SCOPED CONTAINER. The serialized root is the smallest ancestor holding the
//    trigger and the panel, rejected if it grows page-sized. Without the cap it
//    climbs to a 1600×6409 wrapper and serializes the entire document.
// 3. HOVER THAT STICKS. Jumping the pointer from trigger to item drops the hover
//    chain and the panel closes. The pointer is walked in steps from the trigger
//    to the item so the wrapper stays hovered the whole way, and :hover is asserted.
//
// Kind `dropdown` / `--allow-dropdown` reuses this detection and writes
// closed | open onto FRAME `Interactive components` (not A/6). This CLI
// writes the same HTML pair. `--out foo.json` still dumps JSON, plus HTML
// in `foo/`. Default capture width is the Stage P desktop lander (1600),
// not the historic A/6 1440. Hamburgers stay 4.1-M on this same frame.
//
//   node capture-menu-states.mjs --url <url> [--width 1600] \
//        [--out source-site/components] [--page home]

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { siblingSkill, importSibling } from './skill-paths.mjs';
import { installVisibleCursor, movePointer, showHud } from './visible-cursor.mjs';
import {
  captureDropdownPair,
  captureFirstDropdownPair,
} from './dropdown-capture.mjs';
import { writeDropdownPairFiles } from './write-dropdown-pair.mjs';
import {
  DESKTOP_DROPDOWN_WIDTH,
  dropdownCaptureWidth,
  emptyKindManifest,
  INTERACTIVE_COMPONENTS_BOARD,
  looksLikeSectionId,
  resolveDropdownOutDir,
  slugify,
} from './component-state-utils.mjs';

const SERIALIZER = siblingSkill('url-to-paper', 'scripts/serializer.js');
const arg = (n, d) => { const i = process.argv.indexOf(`--${n}`); return i > -1 ? process.argv[i + 1] : d; };
const has = (n) => process.argv.includes(`--${n}`);

export function parseMenuCaptureArgs(argv = process.argv) {
  const get = (n, d) => { const i = argv.indexOf(`--${n}`); return i > -1 ? argv[i + 1] : d; };
  const flag = (n) => argv.includes(`--${n}`);
  const triggerRaw = get('trigger', '');
  const page = get('page', 'home');
  const out = get('out', 'source-site/components');
  const paths = resolveDropdownOutDir(out, slugify(page, 'home'));
  return {
    url: get('url', ''),
    width: dropdownCaptureWidth(get('width', String(DESKTOP_DROPDOWN_WIDTH))),
    height: parseInt(get('height', '1100'), 10) || 1100,
    page,
    pageSlug: slugify(page, 'home'),
    trigger: triggerRaw === '' ? null : parseInt(triggerRaw, 10),
    headless: flag('headless'),
    json: get('json', paths.json),
    dir: paths.dir,
    paperBoard: INTERACTIVE_COMPONENTS_BOARD,
  };
}

async function runMenuCapture(opts) {
  const {
    url, width, height, page, pageSlug, trigger, headless, json, dir,
  } = opts;
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
  await pageHandle.waitForTimeout(3500);
  await pageHandle.emulateMedia({ reducedMotion: 'no-preference' });
  await pageHandle.waitForTimeout(400);
  if (!headless) {
    await installVisibleCursor(pageHandle);
    await showHud(pageHandle, { phase: 'dropdown', current: 1, total: 1, label: 'menu' });
  }

  const pairOpts = { serialize, movePointer, viewportWidth: width };
  const pair = Number.isInteger(trigger)
    ? await captureDropdownPair(pageHandle, { ...pairOpts, trigger })
    : await captureFirstDropdownPair(pageHandle, pairOpts);

  if (!pair.found) {
    fs.mkdirSync(dir, { recursive: true });
    const empty = emptyKindManifest({
      url, page, pageSlug, kind: 'dropdown',
      reason: pair.reason || 'no hover-to-open navbar panel',
    });
    empty.paperBoard = INTERACTIVE_COMPONENTS_BOARD;
    empty.viewport = { width, height };
    fs.writeFileSync(path.join(dir, 'manifest.json'), JSON.stringify(empty, null, 2));
    if (json) fs.writeFileSync(json, JSON.stringify(empty, null, 2));
    console.error(pair.reason || 'nothing new appeared on hover');
    await browser.close();
    return 0;
  }

  const sectionId = looksLikeSectionId(pair.sectionId) ? pair.sectionId : '01';
  const manifest = writeDropdownPairFiles({
    dir,
    pair,
    url,
    page,
    pageSlug,
    sectionId,
    viewportWidth: width,
    viewportHeight: height,
  });
  if (json) {
    fs.mkdirSync(path.dirname(json), { recursive: true });
    fs.writeFileSync(json, JSON.stringify({
      url,
      paperBoard: INTERACTIVE_COMPONENTS_BOARD,
      viewport: { width, height },
      root: pair.rootSel,
      navBox: pair.navBox,
      items: pair.items,
      states: [
        { label: 'closed', kind: 'closed', file: '00-closed.html' },
        { label: 'open', kind: 'open', file: '00-open.html' },
      ],
      manifest,
    }, null, 2));
  }
  await browser.close();
  console.error(`root ${pair.rootSel} · ${pair.items?.length || 0} item(s): ${(pair.items || []).map((i) => i.label).join(', ')}`);
  console.error(`wrote ${dir} — closed | open (${pair.triggerLabel}) → ${INTERACTIVE_COMPONENTS_BOARD} @ ${width}`);
  return 0;
}

const invoked = process.argv[1]
  && fileURLToPath(import.meta.url) === path.resolve(process.argv[1]);
if (invoked) {
  const code = await runMenuCapture(parseMenuCaptureArgs());
  process.exit(code);
}
