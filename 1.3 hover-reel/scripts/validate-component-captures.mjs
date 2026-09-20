#!/usr/bin/env node
// Read-only QA gate for page-aware component state captures.
//
// This is intentionally independent of Playwright and Paper. It catches the
// failures that a successful browser run can still leave behind: a truncated
// target pool, a missing state file, a root that can collapse in a Paper cell,
// or an FAQ "open" state without measured growth.

import { existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { isDropdownKind, isHugParentKind, isGeometryLockedRoot, parseStyleDeclarations } from './component-state-utils.mjs';
import { importSibling } from './skill-paths.mjs';

const { collapseAnimatedLabelStacks, flattenDecorativeAbs } = await importSibling(
  'url-to-paper',
  'scripts/flatten-decorative-abs.mjs',
);

const value = (name, fallback) => {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 && process.argv[i + 1] && !process.argv[i + 1].startsWith('--') ? process.argv[i + 1] : fallback;
};
const root = path.resolve(value('dir', 'source-site/components'));
const output = path.resolve(value('json', 'qa/component-state-coverage.json'));
const expectedPages = value('expected-pages', '').split(',').map((page) => page.trim()).filter(Boolean);

const result = {
  checkedAt: new Date().toISOString(),
  directory: root,
  expectedPages,
  manifests: [],
  errors: [],
  warnings: [],
};

const addError = (message, manifest = null) => result.errors.push({ message, manifest });
const addWarning = (message, manifest = null) => result.warnings.push({ message, manifest });

const walk = (dir) => {
  if (!existsSync(dir)) return [];
  const found = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const file = path.join(dir, entry.name);
    if (entry.isDirectory()) found.push(...walk(file));
    else if (entry.name === 'manifest.json') found.push(file);
  }
  return found;
};

const readRootGeometry = (file) => {
  const html = readFileSync(file, 'utf8');
  const opening = html.match(/^<([a-z][\w:-]*)(?:\s[^>]*)?>/i)?.[0] || '';
  const style = opening.match(/\sstyle="([^"]*)"/i)?.[1] || '';
  const declarations = parseStyleDeclarations(style);
  const px = (name) => {
    const match = String(declarations.get(name) || '').match(/^(\d+(?:\.\d+)?)px$/);
    return match ? Number(match[1]) : 0;
  };
  return { bytes: html.length, tag: opening.match(/^<([a-z][\w:-]*)/i)?.[1] || null, width: px('width'), height: px('height') };
};

const checkFile = (manifestPath, relative, { kind, mode } = {}) => {
  if (!relative) {
    addError('state has no file reference', manifestPath);
    return null;
  }
  const file = path.join(path.dirname(manifestPath), relative);
  if (!existsSync(file)) {
    addError(`missing state file: ${relative}`, manifestPath);
    return null;
  }
  const geometry = readRootGeometry(file);
  if (!geometry.bytes) addError(`empty state file: ${relative}`, manifestPath);
  const html = readFileSync(file, 'utf8');
  if (!isGeometryLockedRoot(html, { kind, mode })) {
    const locked = isHugParentKind(kind, mode)
      ? (kind === 'faq' || mode === 'accordion'
        ? 'FAQ root must be width/max-width 100% and height fit-content'
        : 'dropdown root must be width/max-width 100% and height fit-content')
      : `state root is not geometry-locked (${geometry.tag || 'unknown'} ${geometry.width}×${geometry.height})`;
    addError(`${locked}: ${relative}`, manifestPath);
  }
  const abs = flattenDecorativeAbs(html).removed;
  if (abs.length) {
    addError(`state still has floating abs decoration (use background-color / border on the pill, not a Frame+Rectangle): ${relative}`, manifestPath);
  }
  const stacked = collapseAnimatedLabelStacks(html).collapsed;
  if (stacked.length) {
    addError(`state still has stacked duplicate labels: ${relative}`, manifestPath);
  }
  return { file: relative, ...geometry };
};

const pageOf = (manifestPath) => path.basename(path.dirname(path.dirname(manifestPath)));
const allManifests = walk(root);
if (expectedPages.length && existsSync(root)) {
  const leftover = readdirSync(root, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && !expectedPages.includes(entry.name))
    .map((entry) => entry.name)
    .filter((name) => walk(path.join(root, name)).length);
  if (leftover.length) {
    addWarning(`leftover page folders ignored (not in --expected-pages): ${leftover.join(', ')}`);
  }
}
const manifests = expectedPages.length
  ? allManifests.filter((file) => expectedPages.includes(pageOf(file)))
  : allManifests;
if (!manifests.length) addError(`no component manifests found under ${root}`);

for (const manifestPath of manifests) {
  let manifest;
  try {
    manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
  } catch (error) {
    addError(`invalid JSON: ${error.message}`, manifestPath);
    continue;
  }
  const page = manifest.pageSlug || manifest.page || path.basename(path.dirname(path.dirname(manifestPath)));
  const kind = manifest.kind || path.basename(path.dirname(manifestPath));
  const checked = {
    page,
    kind,
    path: manifestPath,
    status: manifest.status || 'ok',
    mode: manifest.mode || null,
    candidateCount: manifest.coverage?.candidateCount ?? null,
    selectedCount: manifest.coverage?.selectedCount ?? null,
    truncated: Boolean(manifest.coverage?.truncated),
    states: [],
  };
  result.manifests.push(checked);

  if (manifest.coverage?.truncated) {
    addError(`target pool truncated at ${manifest.coverage.selectedCount}; rerun with a larger --max`, manifestPath);
  }
  if (manifest.status === 'empty' || manifest.mode === 'empty') {
    if (!manifest.reason) addWarning('empty manifest has no reason', manifestPath);
    continue;
  }
  if (!Array.isArray(manifest.states) || !manifest.states.length) {
    addError('non-empty manifest has no states', manifestPath);
    continue;
  }
  if (manifest.root?.rect && (!manifest.root.rect[2] || !manifest.root.rect[3])) {
    addError('container root has zero geometry', manifestPath);
  }

  for (const state of manifest.states) {
    const stateFiles = [];
    if (state.file) stateFiles.push(checkFile(manifestPath, state.file, { kind, mode: manifest.mode }));
    if (state.defaultFile) stateFiles.push(checkFile(manifestPath, state.defaultFile, { kind, mode: manifest.mode }));
    if (state.closedFile && state.closedFile !== state.defaultFile) {
      stateFiles.push(checkFile(manifestPath, state.closedFile, { kind, mode: manifest.mode }));
    }
    if (state.hoverFile) stateFiles.push(checkFile(manifestPath, state.hoverFile, { kind, mode: manifest.mode }));
    if (state.openFile) stateFiles.push(checkFile(manifestPath, state.openFile, { kind, mode: manifest.mode }));
    checked.states.push({
      component: state.component || state.label || null,
      changed: state.changed ?? state.hoverChanged ?? null,
      hoverConfirmed: state.hoverConfirmed ?? null,
      opened: state.opened ?? null,
      heightDelta: state.heightDelta ?? null,
      files: stateFiles.filter(Boolean),
    });

    if (manifest.mode === 'elements' && (!state.defaultFile || !state.hoverFile)) {
      addError(`element is missing its default|hover pair for ${state.component || state.label || 'component'}`, manifestPath);
    }
    if (manifest.mode === 'accordion' && (!state.defaultFile || !state.hoverFile || !state.openFile)) {
      addError(`FAQ row is missing its collapsed|hover|open states for ${state.component || state.label || 'row'}`, manifestPath);
    }
    if ((manifest.mode === 'dropdown' || manifest.mode === 'hamburger' || isDropdownKind(kind, manifest.mode))
        && (!(state.closedFile || state.defaultFile) || !state.openFile)) {
      addError(`${manifest.mode || 'dropdown'} is missing its closed|open pair for ${state.component || state.label || 'menu'}`, manifestPath);
    }
    if ((manifest.mode === 'dropdown' || isDropdownKind(kind, manifest.mode))
        && manifest.status !== 'empty') {
      const vw = manifest.viewport?.width ?? manifest.viewportWidth;
      if (vw === 1440) {
        addError('dropdown captured at 1440; desktop lander is 1600', manifestPath);
      }
    }
    const isHoverState = Boolean(state.hoverFile || state.state === 'hover');
    if (isHoverState && state.hoverConfirmed !== true) {
      addError(`hover was not confirmed for ${state.component || state.label || 'component'}`, manifestPath);
    }
    // A confirmed pointer can legitimately have no visual delta (for example,
    // an already-active link). It remains useful parity evidence and is
    // explicitly consumed as `n-a` in Step 8a, so do not turn it into a gate
    // failure. Unconfirmed hover states above still block the run.
    if (manifest.mode === 'accordion' && state.openFile &&
        (state.opened !== true || !Number.isFinite(Number(state.heightDelta)) || Number(state.heightDelta) < 8)) {
      addError(`FAQ open state lacks an 8px measured height delta for ${state.component || state.label || 'row'}`, manifestPath);
    }
  }
}

const byPage = new Map();
for (const manifest of result.manifests) {
  if (!byPage.has(manifest.page)) byPage.set(manifest.page, new Set());
  byPage.get(manifest.page).add(manifest.kind);
}
for (const page of expectedPages) {
  const found = byPage.get(page);
  if (!found) addError(`expected page has no component manifests: ${page}`);
  else for (const kind of ['nav', 'buttons', 'forms', 'footer']) {
    if (!found.has(kind)) addError(`expected page is missing ${kind} manifest: ${page}`);
  }
}

result.summary = {
  manifests: result.manifests.length,
  pages: byPage.size,
  empty: result.manifests.filter((manifest) => manifest.status === 'empty').length,
  errors: result.errors.length,
  warnings: result.warnings.length,
  ok: result.errors.length === 0,
};
mkdirSync(path.dirname(output), { recursive: true });
writeFileSync(output, JSON.stringify(result, null, 2));
console.log(JSON.stringify(result.summary, null, 2));
if (result.errors.length) process.exit(1);
