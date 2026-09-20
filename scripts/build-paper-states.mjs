// Build a Paper artboard from a page-aware A/6 capture-component-states manifest.
//
// Reads the trimmed HTML off disk and writes it through the Paper MCP, so the
// payload never passes through the agent's context. One command per pipeline
// step (4.1 nav, 4.2 buttons, 4.3 forms, 4.4 footer).
//
//   node build-paper-states.mjs --dir source-site/components/home/nav \
//        --file <paperFileId> [--board "A/6 · home · states"] [--section Navbar]
//
// fileId is REQUIRED: this script opens its own MCP session, whose "sticky" file
// is not necessarily the one the agent is working in. Passing it explicitly is
// the difference between landing in the right file and silently writing to
// whichever file was last opened.

import fs from 'node:fs';
import path from 'node:path';
import {
  a6BoardWidthPx,
  applyAncestorFill,
  assignDesignSystemTokens,
  designSystemEyebrow,
  faqFitStyles,
  fluidFitStyles,
  isHugParentKind,
  isInteractiveKind,
  interactiveRowMeta,
  paperBoardName,
  paperBoardWidth,
  paperCellWidth,
  paperPairRowHtml,
  paperSectionName,
  paperSlotBox,
  paperStateCellShell,
  parksOnHoverStates,
  parksOnComponents,
  parksOnNavigation,
  objectTypeLabel,
  hasVisibleHoverDelta,
  unwrapSerializerHtml,
  shouldWidenBoardForKind,
} from './component-state-utils.mjs';
import { prepareStateHtml } from './prepare-state-html.mjs';
import { importSibling, siblingSkill } from './skill-paths.mjs';
import { parkDropdownsOnNavigation, parkOneHoverOnBoard, parkTakesOnComponents } from './park-capture-boards.mjs';

const { call } = await importSibling('url-to-paper', 'scripts/mcp-client.mjs');
const {
  normalizeTokens,
  requireApplyThemeTokensScript,
  themeTokenPass,
} = await importSibling('url-to-paper', 'scripts/library-tokens.mjs');
const { ensureRulers, hasDesktopRuler, parkNextInRow } = await importSibling(
  'url-to-paper',
  'scripts/rulers.mjs',
);

requireApplyThemeTokensScript(siblingSkill('url-to-paper', 'scripts/apply-theme-tokens.mjs'));

const KIND_SECTION = {
  nav: 'Navbar',
  buttons: 'Buttons',
  faq: 'Accordion',
  forms: 'Forms',
  footer: 'Footer',
  dropdown: 'Dropdown',
  'navbar-dropdown': 'Dropdown',
  hamburger: 'Nav mobile',
  'nav-mobile': 'Nav mobile',
  'nav-mobile-768': 'Nav mobile',
  'nav-mobile-390': 'Nav mobile',
};

const arg = (n, d) => { const i = process.argv.indexOf(`--${n}`); return i > -1 ? process.argv[i + 1] : d; };
const has = (n) => process.argv.includes(`--${n}`);

const DIR = path.resolve(arg('dir', ''));
const FILE = arg('file', '');
const TITLE = arg('title', 'Component states');
const DARK = has('dark');
const COLS = parseInt(arg('cols', '0'), 10);
const LEFT = arg('left', '');
const TOP = arg('top', '');

if (!DIR || !FILE) { console.error('usage: --dir <captureDir> --file <paperFileId> [--title] [--dark] [--cols N] [--left] [--top]'); process.exit(1); }

function loadLibraryTokens() {
  const candidates = [
    arg('library', ''),
    path.resolve('design-library/library.json'),
    path.resolve(DIR, '../../../design-library/library.json'),
    path.resolve(DIR, '../../../../design-library/library.json'),
  ].filter(Boolean);
  for (const p of candidates) {
    const abs = path.resolve(p);
    if (!fs.existsSync(abs)) continue;
    try {
      return normalizeTokens(JSON.parse(fs.readFileSync(abs, 'utf8')));
    } catch {
      /* next */
    }
  }
  return [];
}
const libraryTokens = loadLibraryTokens();
if (!libraryTokens.length) {
  console.error('· no design-library/library.json — catch-at-write will skip var() bind; 1.4 token-pass still required');
}

const manifest = JSON.parse(fs.readFileSync(path.join(DIR, 'manifest.json'), 'utf8'));
if (!manifest.states?.length || manifest.status === 'empty') {
  console.error('no captured ' + (manifest.kind || 'component') + ' states in ' + DIR + ' — Paper artboard skipped');
  process.exit(0);
}
const bg = DARK ? '#0B0B0B' : '#F2F2F2';
const card = DARK ? '#141414' : '#FFFFFF';
const head = DARK ? '#FFFFFF' : '#111111';
const sub = DARK ? '#8A8A8A' : '#666666';
const lab = DARK ? '#7A7A7A' : '#999999';

const text = (r) => (r.content || []).filter((c) => c.type === 'text').map((c) => c.text).join('\n');
const parse = (r) => { try { return JSON.parse(text(r)); } catch { return {}; } };

// Element mode always lays out as default | hover pairs, so its width is fixed
// to the pair grid; --cols only applies to container mode (a tall dropdown panel
// benefits from wrapping, a nav bar does not).
// FAQ / accordion cards are full-width patterns: they hug the same A/6 parent
// as Navbar / Buttons / Footer. Never size the board from the captured rect
// (prior-run Yearning orchard imported a 99px FAQ pair). Label wrap is fine.
// Even inset around the control inside the ancestor-color Slot (prior-run).
// Slot hugs the pill — do not stretch width 100% or the band leaves a
// flush top-left button and a empty trail on the right. FAQ is the exception.
const SLOT_INSET = 24;
const containerWidth = manifest.mode === 'container'
  ? Math.max(manifest.root?.rect?.[2] || 0, 1200) + 96
  : 0;
const dropdownBoard = paperBoardWidth({ kind: manifest.kind, mode: manifest.mode });
const boardWidth = dropdownBoard
  ? dropdownBoard
  : `${a6BoardWidthPx({
    mode: manifest.mode,
    kind: manifest.kind,
    states: manifest.states,
    root: manifest.root,
    cols: COLS,
  })}px`;
const pageSlug = manifest.pageSlug || manifest.page || 'home';
const BOARD_NAME = arg('board', paperBoardName({
  kind: manifest.kind,
  mode: manifest.mode,
  pageSlug,
}));
const SECTION_NAME = arg('section', paperSectionName({
  kind: manifest.kind,
  mode: manifest.mode,
  section: KIND_SECTION[manifest.kind],
}));
if (/^A\/6/.test(BOARD_NAME)) {
  console.error(BOARD_NAME + ' is retired — nav/forms/FAQ park on Interactive components, buttons/footer on Source');
  process.exit(1);
}
const artboardStyles = { display: 'flex', flexDirection: 'column', width: boardWidth,
            height: 'fit-content', overflow: 'visible', backgroundColor: bg, padding: '48px', gap: '40px' };
const before = parse(await call('get_basic_info', { fileId: FILE }));
await ensureRulers({
  call,
  fileId: FILE,
  boards: before.artboards || [],
  init: true,
  rowKeys: ['desktop'],
  log: (...a) => console.error('·', ...a),
});
const info = parse(await call('get_basic_info', { fileId: FILE }));
if (!hasDesktopRuler(info.artboards || [])) {
  console.error('P-0: Ruler · desktop missing — refuse to drop an A/6 frame');
  process.exit(1);
}

const projectRoot = path.resolve(DIR, '../../..');
const hoverStates = (manifest.states || []).filter((s) => parksOnHoverStates(manifest.kind, s));
const componentTakes = (manifest.states || []).filter((s) => parksOnComponents(manifest.kind, s));
const parkHoverBoard = parksOnHoverStates(manifest.kind)
  && !arg('board')
  && hoverStates.length > 0;
if (parkHoverBoard) {
  let made = 0;
  for (const st of hoverStates) {
    const defRaw = st.defaultFile
      ? unwrapSerializerHtml(fs.readFileSync(path.join(DIR, st.defaultFile), 'utf8'))
      : '';
    if (!defRaw) continue;
    const def = prepareStateHtml(defRaw, { kind: manifest.kind, mode: manifest.mode }).html;
    let includeHover = st.includeHover !== false && hasVisibleHoverDelta(st) && st.hoverFile;
    let hov = '';
    if (includeHover) {
      const hovRaw = unwrapSerializerHtml(fs.readFileSync(path.join(DIR, st.hoverFile), 'utf8'));
      if (hovRaw) hov = prepareStateHtml(hovRaw, { kind: manifest.kind, mode: manifest.mode }).html;
      else includeHover = false;
    }
    const parked = await parkOneHoverOnBoard({
      call,
      fileId: FILE,
      sid: st.sectionId,
      type: objectTypeLabel(st, manifest.kind),
      label: String(st.component || '').replace(/^\d{2}\s*·\s*/, ''),
      defaultHtml: def,
      hoverHtml: hov,
      includeHover,
      captureMethod: st.captureMethod || '',
      kind: manifest.kind,
      projectRoot,
      log: console.error,
    });
    if (parked.written) made += 1;
  }
  const staleA6 = (info.artboards || []).filter((b) => /^A\/6/.test(b.name || ''));
  if (staleA6.length) {
    try { await call('delete_nodes', { fileId: FILE, nodeIds: staleA6.map((b) => b.id) }); } catch { /* ok */ }
    console.error(`  removed ${staleA6.map((b) => b.name).join(', ')}`);
  }
  await call('finish_working_on_nodes', { fileId: FILE });
  console.error(`\nparked ${made} hover row(s) on Buttons`);
  console.log(JSON.stringify({ board: 'Buttons', cells: made }));
}

if (componentTakes.length && !arg('board')) {
  const items = componentTakes.map((st) => ({
    ...st,
    sid: st.sectionId,
    label: String(st.component || st.label || '').replace(/^\d{2}\s*·\s*/, ''),
    defaultHtml: st.defaultFile
      ? unwrapSerializerHtml(fs.readFileSync(path.join(DIR, st.defaultFile), 'utf8'))
      : '',
    hoverHtml: st.hoverFile
      ? unwrapSerializerHtml(fs.readFileSync(path.join(DIR, st.hoverFile), 'utf8'))
      : '',
  }));
  await parkTakesOnComponents({
    call, fileId: FILE, items, projectRoot, log: console.error,
  });
  await call('finish_working_on_nodes', { fileId: FILE });
}

if (parkHoverBoard || (componentTakes.length && !arg('board'))) {
  process.exit(0);
}

if ((isInteractiveKind(manifest.kind, manifest.mode) || parksOnNavigation(manifest.kind, manifest.mode))
    && !arg('board')) {
  const pairs = [];
  for (const s of manifest.states || []) {
    const closedFile = s.closedFile || s.defaultFile;
    const openFile = s.openFile;
    if (!closedFile || !openFile) continue;
    pairs.push({
      label: String(s.component || '').replace(/^\d{2}\s*·\s*/, '') || 'Dropdown',
      closedHtml: unwrapSerializerHtml(fs.readFileSync(path.join(DIR, closedFile), 'utf8')),
      openHtml: unwrapSerializerHtml(fs.readFileSync(path.join(DIR, openFile), 'utf8')),
    });
  }
  const parked = await parkDropdownsOnNavigation({
    call, fileId: FILE, pairs, projectRoot, log: console.error,
  });
  await call('finish_working_on_nodes', { fileId: FILE });
  console.error(`\nparked ${parked.written} dropdown(s) on Navigation`);
  console.log(JSON.stringify({ board: 'Navigation', cells: parked.written }));
  process.exit(0);
}

const writeHtml = (html, target, mode = 'insert-children') =>
  call('write_html', { fileId: FILE, html, targetNodeId: target, mode });

const existing = (info.artboards || []).find((b) => b.name === BOARD_NAME);
let abId;
if (existing) {
  abId = existing.id;
  const kids = parse(await call('get_children', { fileId: FILE, nodeId: abId })).children || [];
  const prior = kids.find((c) => c.name === SECTION_NAME);
  if (prior?.id) await call('delete_nodes', { fileId: FILE, nodeIds: [prior.id] });
  await call('update_styles', {
    fileId: FILE,
    updates: [{ nodeIds: [abId], styles: {
      height: 'fit-content',
      overflow: 'visible',
      display: 'flex',
      flexDirection: 'column',
    } }],
  });
  const needW = parseInt(boardWidth, 10);
  if (shouldWidenBoardForKind(manifest.kind, manifest.mode)
      && Number.isFinite(needW) && (existing.width || 0) < needW) {
    await call('update_styles', {
      fileId: FILE,
      updates: [{ nodeIds: [abId], styles: { width: `${needW}px` } }],
    });
  }
  console.error(`artboard ${abId} — ${BOARD_NAME} (append ${SECTION_NAME})`);
} else {
  const park = (LEFT === '' && TOP === '')
    ? parkNextInRow({ boards: info.artboards || [], name: BOARD_NAME || "A/6 · home · states", newWidth: parseInt(boardWidth, 10) || 1400 })
    : null;
  if (LEFT !== '') artboardStyles.left = /^\d+$/.test(LEFT) ? `${LEFT}px` : LEFT;
  else if (park) artboardStyles.left = `${park.left}px`;
  if (TOP !== '') artboardStyles.top = /^\d+$/.test(TOP) ? `${TOP}px` : TOP;
  else if (park) artboardStyles.top = `${park.top}px`;
  const artboard = parse(await call('create_artboard', {
    fileId: FILE, name: BOARD_NAME, styles: artboardStyles
  }));
  abId = artboard.id;
  console.error(`artboard ${abId} — ${BOARD_NAME}`);
  const pin = {};
  if (LEFT !== '') pin.left = /^\d+$/.test(LEFT) ? `${LEFT}px` : LEFT;
  else if (park) pin.left = `${park.left}px`;
  if (TOP !== '') pin.top = /^\d+$/.test(TOP) ? `${TOP}px` : TOP;
  else if (park) pin.top = `${park.top}px`;
  if (Object.keys(pin).length) {
    await call('update_styles', { fileId: FILE, updates: [{ nodeIds: [abId], styles: pin }] });
    if (park) console.error(`  parked ${park.left},${park.top} (horizontal row under desktop ruler)`);
  }
  await writeHtml(
    `<div layer-name="Title" style="display: flex; flex-direction: column; gap: 6px; padding-bottom: 6px;">
       <div style="font-family: Inter, sans-serif; font-size: 26px; font-weight: 700; letter-spacing: -0.02em; color: ${head};">${BOARD_NAME}</div>
       <div style="font-family: Inter, sans-serif; font-size: 14px; line-height: 20px; color: ${sub};">Serialized live from ${manifest.url} · IDs match home-desktop layers</div>
     </div>`, abId);
}

const sectionWrap = parse(await writeHtml(
  `<div layer-name="${SECTION_NAME}" style="display: flex; flex-direction: column; gap: 22px; width: 100%; height: fit-content;">
     <div style="font-family: Inter, sans-serif; font-size: 20px; font-weight: 700; letter-spacing: -0.02em; color: ${head};">${SECTION_NAME}</div>
   </div>`, abId));
const sectionId = (sectionWrap.createdNodes || []).find((n) => n.name === SECTION_NAME)?.id || abId;

const cellFill = (state) => state?.ancestorBackground || manifest.root?.ancestorBackground || '';
// Paper clips children to a fixed-px Slot even with overflow:visible
// (prior-run buttons/accordions). Slot is min-height + height:fit-content;
// a second pass after write_html re-asserts fit-content on Slot + artboard.
const fluidPair = isHugParentKind(manifest.kind, manifest.mode);
const cellShell = (name, note, minH, width, fill) =>
  paperStateCellShell({
    name, note, fill, card, lab,
    kind: manifest.kind, mode: manifest.mode, width,
  });
const tokenPassCreated = async (created, extra = {}) => {
  const nodes = (created || []).filter((n) => n?.id);
  if (!nodes.length) return;
  if (fluidPair) {
    await call('update_styles', {
      fileId: FILE,
      updates: [{ nodeIds: nodes.map((n) => n.id), styles: { ...fluidFitStyles(), ...extra } }],
    });
  }
  if (!libraryTokens.length) return;
  const ids = nodes.map((n) => n.id);
  let styles = {};
  try {
    styles = parse(await call('get_computed_styles', { fileId: FILE, nodeIds: ids })).styles || {};
  } catch {
    return;
  }
  const pass = themeTokenPass(ids.map((id) => ({
    id,
    name: nodes.find((n) => n.id === id)?.name,
    component: nodes.find((n) => n.id === id)?.component,
    artboard: BOARD_NAME,
    style: styles[id] || {},
  })), libraryTokens);
  if (pass.updates.length) {
    await call('update_styles', { fileId: FILE, updates: pass.updates });
  }
};
const writeStateHtml = async (file, slotId, fill, extra = {}) => {
  const raw = applyAncestorFill(fs.readFileSync(path.join(DIR, file), 'utf8'), fill);
  const html = prepareStateHtml(raw, {
    ancestorBackground: fill,
    kind: manifest.kind,
    mode: manifest.mode,
    unlockOverflow: extra.unlockOverflow,
    rect: extra.rect,
  }).html;
  const written = parse(await writeHtml(html, slotId));
  const created = (written.createdNodes || []).filter((n) => n.id && n.name !== 'Slot');
  if (fluidPair) {
    const root = created[0];
    if (root?.id) {
      await call('update_styles', {
        fileId: FILE,
        updates: [{ nodeIds: [root.id], styles: fluidPair ? fluidFitStyles() : faqFitStyles() }],
      });
    }
  }
  await tokenPassCreated(created);
  return written;
};
const fitNodes = (nodeIds, extra = {}) => {
  const ids = [...new Set(nodeIds.filter(Boolean))];
  if (!ids.length) return Promise.resolve(null);
  return call('update_styles', {
    fileId: FILE,
    updates: [{ nodeIds: ids, styles: { height: 'fit-content', overflow: 'visible', ...extra } }],
  });
};
const slotBox = paperSlotBox({ kind: manifest.kind, mode: manifest.mode });
const fitSlots = (nodeIds) => fitNodes(nodeIds, {
  ...(fluidPair ? fluidFitStyles() : {
    width: slotBox.width,
    height: slotBox.height || 'fit-content',
    alignItems: slotBox.alignItems || 'center',
    justifyContent: slotBox.justifyContent || 'center',
  }),
  padding: `${SLOT_INSET}px`,
  borderRadius: '12px',
});
const slotIds = [];
const rememberSlot = (slot) => { if (slot?.id) slotIds.push(slot.id); return slot; };

const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const tokens = assignDesignSystemTokens(manifest.states, { kind: manifest.kind });
const tokenOf = (state, i) => state.token || tokens[i];

let parent = sectionId;
if (COLS) {
  const grid = parse(await writeHtml(
    `<div layer-name="Grid" style="display: flex; flex-direction: row; flex-wrap: wrap; gap: 18px; align-items: flex-start;"></div>`, sectionId));
  parent = (grid.createdNodes || [])[0].id;
}

const cellWidth = COLS ? `${Math.floor((Math.max(1240, containerWidth || 0) - 96 - (COLS - 1) * 18) / COLS)}px` : '';
// Height is driven by the component, not the layout: a grid of small buttons in
// panel-sized cells is mostly empty space. Only container mode (a nav bar or a
// dropdown panel) needs a tall slot.
const maxStateHeight = Math.max(...manifest.states.map((s) => (s.rect && s.rect[3]) || 0), 0);
const minH = manifest.mode === 'container'
  ? Math.max(COLS ? 300 : 60, manifest.root?.rect?.[3] || 0)
  : Math.max(48, maxStateHeight + 8);

let made = 0;
if (manifest.mode === 'dropdown' || manifest.mode === 'hamburger'
    || isInteractiveKind(manifest.kind, manifest.mode)) {
  for (const [i, s] of manifest.states.entries()) {
    const row = interactiveRowMeta({
      kind: manifest.kind,
      mode: manifest.mode,
      viewportWidth: s.viewportWidth || manifest.viewport?.width,
    });
    const sid = s.sectionId || row.sid || (s.component || '').match(/^(\d{2})\b/)?.[1] || '';
    const title = String(s.component || '').replace(/^\d{2}\s*·\s*/, '') || row.token;
    const ds = s.token || row.token || tokenOf(s, i);
    const repeatNote = s.repeatingPattern && s.patternCount > 1
      ? ` · 1 of ${s.patternCount} identical menus` : '';
    const rowWrap = parse(await writeHtml(
      paperPairRowHtml({ sid, title, token: ds, head, note: repeatNote }), parent));
    const rowId = (rowWrap.createdNodes || []).find((n) => n.name === 'States').id;
    const cells = [
      ['closed', s.closedFile || s.defaultFile, '', designSystemEyebrow(ds, 'closed')],
      ['open', s.openFile, s.opened === false ? 'DID NOT OPEN' : 'open', designSystemEyebrow(ds, 'open')],
    ];
    for (const [kind, file, note, eyebrow] of cells) {
      if (!file) continue;
      const fill = cellFill(s);
      const shell = parse(await writeHtml(
        cellShell(eyebrow, note, 0, paperCellWidth({ kind: manifest.kind, mode: manifest.mode }), fill), rowId));
      const slot = rememberSlot((shell.createdNodes || []).find((n) => n.name === 'Slot'));
      if (!slot?.id) { console.error(`  missing Slot for ${s.component} ${kind}`); continue; }
      await writeStateHtml(file, slot.id, fill, {
        unlockOverflow: kind === 'open',
        rect: kind === 'open' ? (s.openRect || s.rect) : s.rect,
      });
      await fitSlots([slot.id]);
      if (kind === 'open') {
        await fitNodes([slot.id, rowId, sectionId, abId], fluidFitStyles(s.openRect || s.rect));
      }
      made++;
    }
    console.error(`  + ${s.component} (closed | open)`);
  }
} else if (manifest.mode === 'accordion') {
  // Three cells per row: collapsed | hover | open. The open cell carries the
  // answer copy and the measured growth, which is the whole reason this kind
  // exists — a hover pair alone says nothing about an accordion.
  for (const [i, s] of manifest.states.entries()) {
    // The question heads the row once. Repeating it in all three cell labels
    // wrapped the longer ones onto a second line, which pushed that cell down
    // and broke the vertical lane the comparison depends on.
    const sid = s.sectionId || (s.component || '').match(/^(\d{2})\b/)?.[1] || '';
    const title = String(s.component || '').replace(/^\d{2}\s*·\s*/, '');
    const ds = tokenOf(s, i);
    const repeatNote = s.repeatingPattern && s.patternCount > 1
      ? ` · 1 of ${s.patternCount} identical rows` : '';
    const rowWrap = parse(await writeHtml(
      `<div layer-name="${sid ? `${esc(sid)} · ` : ''}${esc(ds)}" style="display: flex; flex-direction: column; gap: 10px; padding-top: 6px; width: 100%;">
         <div style="display: flex; flex-direction: row; align-items: center; gap: 10px;">
           ${sid ? `<div style="width: 36px; height: 36px; border-radius: 999px; background-color: #E11D2E; color: #FFFFFF; font-family: Inter, sans-serif; font-size: 13px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">${esc(sid)}</div>` : ''}
           <div style="font-family: Inter, sans-serif; font-size: 15px; font-weight: 600; color: ${head};">${esc(title)}${esc(repeatNote)}</div>
         </div>
         <div layer-name="States" style="display: flex; flex-direction: row; gap: 18px; align-items: flex-start; width: 100%;"></div>
       </div>`, parent));
    const rowId = (rowWrap.createdNodes || []).find((n) => n.name === 'States').id;
    // A tint of 10 RGB units is invisible side by side, so the note carries the
    // measured value. Without it the hover cell reads as a duplicate.
    const hv = (s.hoverDelta || [])
      .filter((d) => /color|background|border|transform|opacity|shadow/i.test(d.prop))
      .slice(0, 2).map((d) => `${d.prop}: ${d.from} → ${d.to}`).join(' · ');
    const cells = [
      ['collapsed', s.defaultFile, '', designSystemEyebrow(ds, 'default')],
      ['hover', s.hoverFile, hv || (s.hoverChanged ? 'changed' : 'no hover delta'), designSystemEyebrow(ds, 'hover')],
      ['open', s.openFile, s.opened ? `+${s.heightDelta}px · ${s.heightBefore}→${s.heightAfter}` : 'DID NOT OPEN', designSystemEyebrow(ds, 'open')],
    ];
    for (const [kind, file, note, eyebrow] of cells) {
      if (!file) continue;
      const fill = cellFill(s);
      const shell = parse(await writeHtml(
        cellShell(eyebrow, note, 0, paperCellWidth({ kind: manifest.kind, mode: manifest.mode }), fill), rowId));
      const slot = rememberSlot((shell.createdNodes || []).find((n) => n.name === 'Slot'));
      if (!slot?.id) { console.error(`  missing Slot for ${s.component} ${kind}`); continue; }
      await writeStateHtml(file, slot.id, fill);
      await fitSlots([slot.id]);
      made++;
    }
    console.error(`  + ${s.component} (collapsed | hover | open +${s.heightDelta}px)`);
  }
} else if (manifest.mode === 'container') {
  for (const [i, s] of manifest.states.entries()) {
    const ds = tokenOf({ ...s, kind: manifest.kind }, i);
    const name = designSystemEyebrow(ds, s.state === 'hover' ? 'hover' : 'default');
    const note = s.state === 'hover' && s.changed === false ? 'no hover delta' : '';
    const fill = cellFill(s);
    const shell = parse(await writeHtml(cellShell(name, note, minH, cellWidth, fill), parent));
    const slot = rememberSlot((shell.createdNodes || []).find((n) => n.name === 'Slot'));
    if (!slot?.id) { console.error(`  missing Slot for ${name}`); continue; }
    await writeStateHtml(s.file, slot.id, fill);
    await fitSlots([slot.id]);
    made++;
    console.error(`  + ${name}`);
  }
} else {
  // A component has exactly TWO states, so it gets its own row holding both.
  // Laying the cells out in an N-column grid instead lets a component's default
  // land at the end of one row and its hover at the start of the next, which is
  // precisely the comparison the artboard exists to make.
  for (const [i, s] of manifest.states.entries()) {
    const note = s.changed === false ? 'no hover delta' : '';
    const sid = s.sectionId || (s.component || '').match(/^(\d{2})\b/)?.[1] || '';
    const ds = tokenOf(s, i);
    const row = parse(await writeHtml(
      `<div layer-name="${sid ? `${esc(sid)} · ` : ''}${esc(ds)}" style="display: flex; flex-direction: row; gap: 12px; align-items: flex-start;">
         ${sid ? `<div style="width: 36px; height: 36px; border-radius: 999px; background-color: #E11D2E; color: #FFFFFF; font-family: Inter, sans-serif; font-size: 13px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0; margin-top: 18px;">${esc(sid)}</div>` : ''}
       </div>`,
      parent));
    const rowId = (row.createdNodes || [])[0].id;
    const pairs = [['default', s.defaultFile]];
    if (hasVisibleHoverDelta(s) && s.hoverFile) pairs.push(['hover', s.hoverFile]);
    for (const [kind, file] of pairs) {
      const name = designSystemEyebrow(ds, kind);
      const fill = cellFill(s);
      const slotH = Math.max(48, Math.round((s.rect && s.rect[3]) || 48) + 12);
      const shell = parse(await writeHtml(
        cellShell(name, kind === 'hover' ? note : '', slotH, 'fit-content', fill), rowId));
      const slot = rememberSlot((shell.createdNodes || []).find((n) => n.name === 'Slot'));
      if (!slot?.id) { console.error(`  missing Slot for ${name}`); continue; }
      await writeStateHtml(file, slot.id, fill);
      await fitSlots([slot.id]);
      made++;
    }
    console.error(`  + ${s.component} (${pairs.map(p => p[0]).join(' | ')})`);
  }
}

await fitNodes([abId, sectionId], { overflow: 'visible', height: 'fit-content' });
await fitSlots(slotIds);
const qa = parse(await call('get_computed_styles', { fileId: FILE, nodeIds: [abId, ...slotIds] }));
const clipped = [];
const stylesOf = (id) => (qa && (qa[id] || qa.styles?.[id] || qa.nodes?.[id])) || {};
for (const id of slotIds) {
  const st = stylesOf(id);
  const h = parseFloat(st.height);
  const minHpx = parseFloat(st.minHeight);
  if (Number.isFinite(h) && Number.isFinite(minHpx) && h + 1 < minHpx) clipped.push(id);
}
if (clipped.length) {
  await fitSlots(clipped);
  await fitNodes([abId]);
  console.error(`  QA refit ${clipped.length} clipped slot(s)`);
}
await call('finish_working_on_nodes', { fileId: FILE });
if (isInteractiveKind(manifest.kind, manifest.mode) && !has('skip-token-pass')) {
  const { spawnSync } = await import('node:child_process');
  const { siblingSkill } = await import('./skill-paths.mjs');
  const script = siblingSkill('url-to-paper', 'scripts/apply-theme-tokens.mjs');
  const run = spawnSync(process.execPath, [
    script,
    '--file-id', FILE,
    '--only', 'Interactive components',
  ], { encoding: 'utf8' });
  if (run.status !== 0) {
    console.error('token-pass on Interactive components failed — generate → token-pass is required');
    if (run.stderr) console.error(run.stderr);
  } else {
    console.error('token-pass visited Interactive components');
  }
}
console.error(`\nbuilt ${made} cell(s) in ${BOARD_NAME} / ${SECTION_NAME}`);
console.log(JSON.stringify({ artboardId: abId, board: BOARD_NAME, section: SECTION_NAME, cells: made, slots: slotIds.length }));
