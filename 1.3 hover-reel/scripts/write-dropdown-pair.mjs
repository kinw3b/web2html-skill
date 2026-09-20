// Write a closed | open dropdown pair as Paper-ready HTML + manifest.
// Shared by --kind dropdown and capture-menu-states.mjs (no longer JSON-only).

import fs from 'node:fs';
import path from 'node:path';
import { trim } from './trim-styles.mjs';
import { prepareStateHtml } from './prepare-state-html.mjs';
import {
  assignDesignSystemTokens,
  DESKTOP_DROPDOWN_WIDTH,
  htmlChanged,
  INTERACTIVE_COMPONENTS_BOARD,
  interactiveRowMeta,
  isHamburgerKind,
  patternKey,
  slugify,
  styleDelta,
} from './component-state-utils.mjs';

export function writeDropdownStateHtml(dir, name, html, meta = {}) {
  const kind = meta.kind || 'dropdown';
  const mode = meta.mode || (isHamburgerKind(kind) ? 'hamburger' : 'dropdown');
  const t = prepareStateHtml(trim(html), {
    kind,
    mode,
    rect: meta.rect,
    backgroundColor: meta.backgroundColor ?? meta.sourceBackground,
    ancestorBackground: meta.ancestorBackground,
    unlockOverflow: meta.unlockOverflow,
  });
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, `${name}.html`), t.html);
  return t.html;
}

export function writeFluidPairFiles({
  dir,
  pair,
  url = null,
  page = 'home',
  pageSlug = 'home',
  kind = 'dropdown',
  mode,
  sectionId,
  skipped = [],
  viewportWidth = DESKTOP_DROPDOWN_WIDTH,
  viewportHeight = 1100,
} = {}) {
  if (!dir) throw new Error('writeFluidPairFiles needs dir');
  if (!pair?.closed?.html || !pair?.open?.html) {
    throw new Error('writeFluidPairFiles needs pair.closed.html and pair.open.html');
  }
  const resolvedMode = mode || (isHamburgerKind(kind) ? 'hamburger' : 'dropdown');
  const row = interactiveRowMeta({ kind, mode: resolvedMode, viewportWidth });
  const sid = sectionId || row.sid;
  fs.mkdirSync(dir, { recursive: true });
  const closedHtml = writeDropdownStateHtml(dir, '00-closed', pair.closed.html, {
    kind,
    mode: resolvedMode,
    rect: pair.triggerBox,
    ancestorBackground: pair.closed.ancestorBackground || null,
  });
  const openHtml = writeDropdownStateHtml(dir, '00-open', pair.open.html, {
    kind,
    mode: resolvedMode,
    rect: pair.navBox,
    unlockOverflow: true,
    ancestorBackground: pair.open.ancestorBackground || null,
  });
  const changed = htmlChanged(openHtml, closedHtml);
  const written = [{
    component: sid ? `${sid} · ${row.token}` : row.token,
    index: 0,
    rect: pair.navBox || pair.triggerBox,
    defaultFile: '00-closed.html',
    closedFile: '00-closed.html',
    openFile: '00-open.html',
    bytes: closedHtml.length + openHtml.length,
    hoverConfirmed: pair.hoverConfirmed === true,
    opened: pair.opened !== false,
    changed,
    ancestorBackground: null,
    sectionId: sid,
    sectionLabel: sid,
    viewportWidth,
    repeatingPattern: true,
    patternCount: 1,
    styleDelta: changed ? styleDelta(closedHtml, openHtml) : [],
    items: pair.items || [],
    token: row.token,
  }];
  const tokens = assignDesignSystemTokens(written, { kind });
  written.forEach((state, i) => {
    state.patternKey = patternKey(state, { kind });
    state.token = state.token || tokens[i];
  });
  const manifest = {
    url,
    page: page || null,
    pageSlug: pageSlug || null,
    kind,
    mode: resolvedMode,
    status: 'ok',
    reason: null,
    capturedAt: new Date().toISOString(),
    skipped,
    paperBoard: INTERACTIVE_COMPONENTS_BOARD,
    viewport: { width: viewportWidth, height: viewportHeight },
    root: { rect: pair.navBox, selector: pair.rootSel },
    coverage: {
      candidateCount: 1, selectedCount: 1, truncated: false,
      repeatingPattern: true, patternCount: 1,
    },
    states: written,
  };
  fs.writeFileSync(path.join(dir, 'manifest.json'), JSON.stringify(manifest, null, 2));
  return manifest;
}

export function writeDropdownPairFiles(opts = {}) {
  return writeFluidPairFiles({ ...opts, kind: opts.kind || 'dropdown', mode: opts.mode || 'dropdown' });
}

/** One or more human-picked navbar dropdowns → Interactive components. */
export function writeDropdownPairs({
  dir,
  pairs = [],
  url = null,
  page = 'home',
  pageSlug = 'home',
  skipped = [],
  viewportWidth = DESKTOP_DROPDOWN_WIDTH,
  viewportHeight = 1100,
} = {}) {
  if (!dir) throw new Error('writeDropdownPairs needs dir');
  const list = (Array.isArray(pairs) ? pairs : []).filter((pair) => pair?.closed?.html && pair?.open?.html);
  if (!list.length) throw new Error('writeDropdownPairs needs closed|open pairs');
  fs.mkdirSync(dir, { recursive: true });
  const row = interactiveRowMeta({ kind: 'dropdown', mode: 'dropdown' });
  const written = list.map((pair, i) => {
    const slug = slugify(pair.triggerLabel || pair.label || `menu-${i}`, `menu-${i}`);
    const base = `${String(i).padStart(2, '0')}-${slug}`;
    const closedHtml = writeDropdownStateHtml(dir, `${base}-closed`, pair.closed.html, {
      kind: 'dropdown',
      mode: 'dropdown',
      rect: pair.triggerBox,
      ancestorBackground: pair.closed.ancestorBackground || null,
    });
    const openHtml = writeDropdownStateHtml(dir, `${base}-open`, pair.open.html, {
      kind: 'dropdown',
      mode: 'dropdown',
      rect: pair.navBox,
      unlockOverflow: true,
      ancestorBackground: pair.open.ancestorBackground || null,
    });
    const changed = htmlChanged(openHtml, closedHtml);
    return {
      component: `${row.sid} · ${slug}`,
      index: i,
      rect: pair.navBox || pair.triggerBox,
      defaultFile: `${base}-closed.html`,
      closedFile: `${base}-closed.html`,
      openFile: `${base}-open.html`,
      bytes: closedHtml.length + openHtml.length,
      hoverConfirmed: pair.hoverConfirmed === true,
      opened: pair.opened !== false,
      changed,
      ancestorBackground: null,
      sectionId: row.sid,
      sectionLabel: row.sid,
      viewportWidth,
      repeatingPattern: true,
      patternCount: 1,
      styleDelta: changed ? styleDelta(closedHtml, openHtml) : [],
      items: pair.items || [],
      token: row.token,
      patternKey: patternKey({ token: row.token, sectionId: row.sid }, { kind: 'dropdown' }),
    };
  });
  assignDesignSystemTokens(written, { kind: 'dropdown' });
  const first = list[0];
  const manifest = {
    url,
    page: page || null,
    pageSlug: pageSlug || null,
    kind: 'dropdown',
    mode: 'dropdown',
    status: 'ok',
    reason: null,
    capturedAt: new Date().toISOString(),
    skipped,
    paperBoard: INTERACTIVE_COMPONENTS_BOARD,
    viewport: { width: viewportWidth, height: viewportHeight },
    root: { rect: first.navBox, selector: first.rootSel },
    coverage: {
      candidateCount: written.length, selectedCount: written.length, truncated: false,
      repeatingPattern: true, patternCount: written.length, human: true,
    },
    states: written,
  };
  fs.writeFileSync(path.join(dir, 'manifest.json'), JSON.stringify(manifest, null, 2));
  return manifest;
}
