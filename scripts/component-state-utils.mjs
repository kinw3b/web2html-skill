// Shared, dependency-free helpers for component-state capture and QA.
//
// These functions deliberately work on the serializer's HTML rather than a
// browser DOM. A capture is often consumed by Paper from disk, and keeping the
// geometry lock here makes the same checks available to the capture runner,
// Paper builder, and offline validation command.

import path from 'node:path';

const OPENING_TAG = /^<([a-z][\w:-]*)(?:\s[^>]*)?>/i;
const STYLE_ATTR = /\sstyle="([^"]*)"/i;

export function slugify(value, fallback = 'page') {
  const slug = String(value || '')
    .trim()
    .replace(/^https?:\/\/[^/]+/i, '')
    .replace(/[?#].*$/, '')
    .replace(/(^|\/)index\.html?$/i, '$1')
    .replace(/[^a-z0-9]+/gi, '-')
    .replace(/^-+|-+$/g, '')
    .toLowerCase();
  return slug || fallback;
}

export function pageSlug(entry, index = 0) {
  if (typeof entry === 'string') return slugify(entry, `page-${index + 1}`);
  return slugify(entry?.slug || entry?.name || entry?.path || entry?.url, `page-${index + 1}`);
}

export function parseStyleDeclarations(style) {
  const out = new Map();
  for (const declaration of String(style || '').split(';')) {
    const i = declaration.indexOf(':');
    if (i < 1) continue;
    out.set(declaration.slice(0, i).trim(), declaration.slice(i + 1).trim());
  }
  return out;
}

export function fillStylesForFlexChild(parentStyle = {}, childStyle = {}) {
  const display = String(parentStyle.display || '').toLowerCase();
  const direction = String(parentStyle.flexDirection || 'row').toLowerCase();
  const width = String(childStyle.width || '').trim().toLowerCase();
  const intrinsicWidth = /^(auto|fit-content|min-content|max-content|intrinsic)$/.test(width);
  const rawFlexGrow = childStyle.flexGrow ?? childStyle['flex-grow'];
  const numericFlexGrow = Number.parseFloat(rawFlexGrow);
  const hasFlexGrow = Number.isFinite(numericFlexGrow)
    ? numericFlexGrow !== 0
    : rawFlexGrow != null && String(rawFlexGrow).trim() !== '';
  const alignSelf = String(childStyle.alignSelf || childStyle['align-self'] || '').toLowerCase();
  if (intrinsicWidth || hasFlexGrow || alignSelf === 'stretch') return {};
  if (display.includes('flex') && direction === 'row') return { flexGrow: '1' };
  if (display.includes('flex') && direction === 'column') return { alignSelf: 'stretch' };
  return { width: '100%' };
}

function serializeDeclarations(declarations) {
  return [...declarations].map(([prop, value]) => `${prop}: ${value}`).join('; ');
}

export const NAVIGATION_BOARD = 'Navigation';
export const COMPONENTS_BOARD = 'Components';
export const BUTTONS_BOARD = 'Buttons';
export const HOVER_STATES_BOARD = BUTTONS_BOARD;
export const BUTTONS_BOARD_ALIASES = ['Hover States'];

export function isButtonsBoard(name = '') {
  return name === BUTTONS_BOARD || name === 'Hover States';
}
export const SCREENSHOTS_BOARD = 'Screenshots';
/** Retired name. Dropdowns / navbar now park on Navigation. */
export const INTERACTIVE_COMPONENTS_BOARD = NAVIGATION_BOARD;
export const PAPER_SLOT_INSET = 24;
export const A6_PAIR_BOARD = 1240;
/** Stage P desktop lander. Dropdown capture uses this, not the A/6 1440 default. */
export const DESKTOP_DROPDOWN_WIDTH = 1600;
/** Historic A/6 default. Not the desktop lander — dropdowns remap it to 1600. */
export const LEGACY_A6_WIDTH = 1440;
/**
 * Yearning orchard `Interactive components` 6IW-0: 2800×684 @ 4418, 108,
 * right of A/6. Spec only — do not write that live file from this package.
 */
export const INTERACTIVE_COMPONENTS_WIDTH = 2800;

const DROPDOWN_KINDS = new Set(['dropdown', 'navbar-dropdown']);
const HAMBURGER_KINDS = new Set(['hamburger', 'nav-mobile', 'nav-mobile-768', 'nav-mobile-390']);
const FAQ_KINDS = new Set(['faq', 'accordion']);

export function normalizeCaptureKind(kind) {
  const k = String(kind || '').toLowerCase();
  if (k === 'navbar-dropdown') return 'dropdown';
  return k;
}

export function isDropdownKind(kind, mode) {
  return DROPDOWN_KINDS.has(String(kind || '').toLowerCase())
    || String(mode || '').toLowerCase() === 'dropdown';
}

export function isHamburgerKind(kind, mode) {
  const k = String(kind || '').toLowerCase();
  const m = String(mode || '').toLowerCase();
  return HAMBURGER_KINDS.has(k)
    || m === 'hamburger'
    || m === 'hamburger-click'
    || /^nav-mobile/.test(k);
}

/** Desktop dropdown + 768/390 burgers share FRAME `Navigation`. */
export function isInteractiveKind(kind, mode) {
  return isDropdownKind(kind, mode) || isHamburgerKind(kind, mode);
}

/**
 * Row labels on Interactive components:
 * `01 · navbar-dropdown` · `02 · nav-mobile-768` · `03 · nav-mobile-390`.
 */
export function interactiveRowMeta({ kind, mode, viewportWidth } = {}) {
  if (isDropdownKind(kind, mode)) {
    return { sid: '01', token: 'navbar-dropdown', section: 'Dropdown' };
  }
  if (isHamburgerKind(kind, mode)) {
    const w = Number(viewportWidth);
    if (w === 768 || /768/.test(String(kind || ''))) {
      return { sid: '02', token: 'nav-mobile-768', section: 'Nav mobile' };
    }
    return { sid: '03', token: 'nav-mobile-390', section: 'Nav mobile' };
  }
  return { sid: '', token: normalizeCaptureKind(kind), section: paperSectionName({ kind, mode }) };
}

export function isFaqKind(kind, mode) {
  return FAQ_KINDS.has(String(kind || '').toLowerCase())
    || String(mode || '').toLowerCase() === 'accordion';
}

/** Closed|open pairs that hug the parent — dropdowns + burgers. FAQ stays on A/6. */
export function isFluidPairKind(kind, mode) {
  return isInteractiveKind(kind, mode);
}

/** FAQ + desktop dropdown hug the parent. Burgers stay narrow (fit-content). */
export function isHugParentKind(kind, mode) {
  return isFaqKind(kind, mode) || isDropdownKind(kind, mode);
}

/** Token-pass still visits burgers; they are not 100% wide. */
export function isFluidInteractiveKind(kind, mode) {
  return isFluidPairKind(kind, mode) || isFaqKind(kind, mode);
}

export function a6StatesBoardName(pageSlug = 'home') {
  return `A/6 · ${pageSlug || 'home'} · states`;
}

export const SOURCE_PARK_KINDS = new Set(['buttons', 'footer', 'nav']);
export const NAVIGATION_PARK_KINDS = new Set([
  'dropdown', 'navbar-dropdown',
  'hamburger', 'nav-mobile', 'nav-mobile-768', 'nav-mobile-390',
]);
export const COMPONENTS_PARK_KINDS = new Set([
  'objects', 'component', 'forms', 'faq', 'accordion',
]);
export const INTERACTIVE_PARK_KINDS = NAVIGATION_PARK_KINDS;

export function isPressSolo(state = {}) {
  const method = String(state.captureMethod || '').toLowerCase();
  return method === 'click-solo'
    || method === 'press-solo'
    || String(state.type || '').toLowerCase() === 'component';
}

export function parksOnHoverStates(kind, state = {}) {
  if (isHumanClickPair(state) || isPressSolo(state)) return false;
  if (COMPONENTS_PARK_KINDS.has(normalizeCaptureKind(kind))) return false;
  return SOURCE_PARK_KINDS.has(normalizeCaptureKind(kind));
}

export function parksOnSource(kind, state = {}) {
  return parksOnHoverStates(kind, state);
}

export function parksOnNavigation(kind, mode) {
  return isInteractiveKind(kind, mode)
    || NAVIGATION_PARK_KINDS.has(normalizeCaptureKind(kind));
}

export function parksOnComponents(kind, state = {}) {
  if (isHumanClickPair(state) || isPressSolo(state)) return true;
  return COMPONENTS_PARK_KINDS.has(normalizeCaptureKind(kind));
}

export function parksOnInteractive(kind, mode) {
  return parksOnNavigation(kind, mode);
}

/** Navbar + dropdowns → Navigation.
 *  Objects / components → Components.
 *  Hover buttons + footer → FRAME Buttons. Never seed A/6. */
export function paperBoardName({ kind, mode, pageSlug, board, captureMethod, type } = {}) {
  if (board && !/^A\/6/.test(board) && board !== 'Interactive components') return board;
  const state = { captureMethod, type };
  if (parksOnComponents(kind, state)) return COMPONENTS_BOARD;
  if (parksOnHoverStates(kind, state)) return HOVER_STATES_BOARD;
  if (parksOnNavigation(kind, mode)) return NAVIGATION_BOARD;
  return COMPONENTS_BOARD;
}

export function paperSectionName({ kind, mode, section, viewportWidth } = {}) {
  if (section) return section;
  if (isInteractiveKind(kind, mode)) return interactiveRowMeta({ kind, mode, viewportWidth }).section;
  if (isFaqKind(kind, mode)) return 'Accordion';
  const map = { nav: 'Navbar', buttons: 'Buttons', forms: 'Forms', footer: 'Footer' };
  return map[normalizeCaptureKind(kind)] || kind || 'States';
}

/** Yearning orchard 6IW-0 is 2800 wide. FAQ / A/6 boards keep their own math. */
export function paperBoardWidth({ kind, mode } = {}) {
  if (isInteractiveKind(kind, mode)) return `${INTERACTIVE_COMPONENTS_WIDTH}px`;
  return null;
}

/**
 * Dropdowns capture at the desktop lander (1600), not A/6's 1440 default.
 * Explicit 1920 / 1280 stay. 1440 remaps. Phone widths stay so the runner
 * can write an empty "not a desktop viewport" manifest.
 */
export function dropdownCaptureWidth(requested) {
  const n = Number.parseInt(requested, 10);
  if (!Number.isFinite(n)) return DESKTOP_DROPDOWN_WIDTH;
  if (n === LEGACY_A6_WIDTH) return DESKTOP_DROPDOWN_WIDTH;
  return n;
}

export function hamburgerKindWidth(kind, requested) {
  const k = normalizeCaptureKind(kind);
  if (/768/.test(k)) return 768;
  if (/390/.test(k)) return 390;
  const n = Number.parseInt(requested, 10);
  if (Number.isFinite(n) && n > 0) return n;
  if (k === 'nav-mobile' || k === 'hamburger') return 390;
  return 390;
}

export function hamburgerKindHeight(kind, width) {
  const w = Number(width) || hamburgerKindWidth(kind);
  if (w === 768) return 1024;
  if (w === 390) return 844;
  return 844;
}

export function kindCaptureWidth(kind, requested) {
  if (isDropdownKind(kind)) return dropdownCaptureWidth(requested);
  if (isHamburgerKind(kind)) return hamburgerKindWidth(kind, requested);
  const n = Number.parseInt(requested, 10);
  return Number.isFinite(n) && n > 0 ? n : LEGACY_A6_WIDTH;
}

/**
 * `--out taro-menu.json` still writes JSON, but HTML lands in `taro-menu/`.
 * A directory named `dropdown` is used as-is. Anything else nests
 * `<out>/<page>/dropdown/`.
 */
export function resolveDropdownOutDir(out, pageSlug = 'home') {
  const resolved = path.resolve(out || 'source-site/components');
  if (/\.json$/i.test(resolved)) {
    return { dir: resolved.replace(/\.json$/i, ''), json: resolved };
  }
  const base = path.basename(resolved);
  if (base === 'dropdown' || base === 'navbar-dropdown') {
    return { dir: resolved, json: null };
  }
  return { dir: path.join(resolved, pageSlug || 'home', 'dropdown'), json: null };
}

/** `nav-mobile-768` / `nav-mobile-390` folders under `<out>/<page>/`. */
export function resolveHamburgerOutDir(out, { pageSlug = 'home', kind, width } = {}) {
  const resolved = path.resolve(out || 'source-site/components');
  const meta = interactiveRowMeta({ kind: kind || 'hamburger', viewportWidth: width });
  const folder = meta.token;
  if (/\.json$/i.test(resolved)) {
    return { dir: resolved.replace(/\.json$/i, ''), json: resolved };
  }
  const base = path.basename(resolved);
  if (HAMBURGER_KINDS.has(base) || /^nav-mobile/.test(base)) {
    return { dir: resolved, json: null };
  }
  return { dir: path.join(resolved, pageSlug || 'home', folder), json: null };
}

export function resolveCaptureKinds({
  kinds = [],
  allowFaq: _allowFaq = false,
  allowDropdown = false,
  allowHamburger = true,
} = {}) {
  const out = [];
  const seen = new Set();
  for (const raw of kinds) {
    const kind = normalizeCaptureKind(raw);
    if (!kind || seen.has(kind)) continue;
    seen.add(kind);
    out.push(kind);
  }
  if (allowDropdown && !seen.has('dropdown')) out.push('dropdown');
  // Burgers run when the icon is painted at that width — not gated on
  // --allow-dropdown (that flag stays for hover mega-menus). Do not invent
  // a desktop burger; capture writes empty if the icon is absent.
  if (allowHamburger !== false) {
    if (!seen.has('nav-mobile-768')) {
      seen.add('nav-mobile-768');
      out.push('nav-mobile-768');
    }
    if (!seen.has('nav-mobile-390') && !seen.has('hamburger') && !seen.has('nav-mobile')) {
      seen.add('nav-mobile-390');
      out.push('nav-mobile-390');
    }
  }
  return out;
}

export function shouldCaptureDropdown({ allowDropdown = false, kind } = {}) {
  return Boolean(allowDropdown) && (kind == null || isDropdownKind(kind));
}

export function emptyKindManifest({
  url = null, page = null, pageSlug = null, kind = 'dropdown', reason,
} = {}) {
  return {
    url,
    page: page || null,
    pageSlug: pageSlug || null,
    kind: normalizeCaptureKind(kind),
    mode: 'empty',
    status: 'empty',
    paperBoard: isInteractiveKind(kind) ? INTERACTIVE_COMPONENTS_BOARD : a6StatesBoardName(pageSlug),
    reason: reason || 'capture is off',
    capturedAt: new Date().toISOString(),
    skipped: [],
    root: null,
    coverage: { candidateCount: 0, selectedCount: 0, truncated: false },
    states: [],
  };
}

export function isDesktopDropdownViewport(width) {
  return Number(width) >= 1100;
}

export function looksLikeHamburger({
  width, height, label = '', aria = '', viewportWidth,
} = {}) {
  if (Number.isFinite(viewportWidth) && viewportWidth < 1100) return true;
  const hint = `${label} ${aria}`.toLowerCase();
  const named = /(hamburger|burger|menu-toggle|nav-toggle|open menu|toggle menu|^menu$)/i.test(hint);
  const box = Number(width) > 0 && Number(height) > 0
    && width <= 48 && height <= 48 && Math.abs(width - height) <= 8;
  return Boolean(named && box);
}

export function paperRootBox({ kind, mode, rect } = {}) {
  if (isHamburgerKind(kind, mode)) {
    const cap = hamburgerKindWidth(kind);
    const w = rect && Number.isFinite(rect[2]) && rect[2] > 0
      ? `${Math.round(rect[2])}px`
      : 'fit-content';
    return {
      width: w,
      maxWidth: `${cap}px`,
      height: 'fit-content',
      alignItems: 'flex-start',
      alignSelf: 'flex-start',
    };
  }
  if (isHugParentKind(kind, mode)) {
    return {
      width: '100%',
      maxWidth: '100%',
      height: 'fit-content',
      alignItems: 'flex-start',
      alignSelf: 'flex-start',
    };
  }
  const out = {};
  if (rect && Number.isFinite(rect[2]) && rect[2] > 0) out.width = `${Math.round(rect[2])}px`;
  if (rect && Number.isFinite(rect[3]) && rect[3] > 0) out.height = `${Math.round(rect[3])}px`;
  return out;
}

export function paperSlotBox({ kind, mode } = {}) {
  if (isHamburgerKind(kind, mode)) {
    return {
      width: 'fit-content',
      maxWidth: `${hamburgerKindWidth(kind)}px`,
      height: 'fit-content',
      alignItems: 'flex-start',
      alignSelf: 'flex-start',
      justifyContent: 'flex-start',
    };
  }
  if (isHugParentKind(kind, mode)) {
    return {
      width: '100%',
      maxWidth: '100%',
      height: 'fit-content',
      alignItems: 'flex-start',
      alignSelf: 'flex-start',
      justifyContent: 'flex-start',
    };
  }
  return {
    width: 'fit-content',
    height: 'fit-content',
    alignItems: 'center',
    justifyContent: 'center',
  };
}

export function fluidFitStyles(rect) {
  const out = {
    width: '100%',
    maxWidth: '100%',
    height: 'fit-content',
    overflow: 'visible',
    alignItems: 'flex-start',
    alignSelf: 'flex-start',
    justifyContent: 'flex-start',
  };
  const h = rect && Number(rect[3]);
  if (Number.isFinite(h) && h > 0) out.minHeight = `${Math.round(h)}px`;
  return out;
}

export function fluidInteractiveFitStyles() {
  return fluidFitStyles();
}

/** Framer chevron leftovers knock the glyph out of its box in Paper. */
export function stripChevronTransforms(html) {
  return String(html || '').replace(/\sstyle="([^"]*)"/gi, (full, css) => {
    const declarations = parseStyleDeclarations(css);
    let changed = false;
    for (const prop of ['transform', 'translate', 'rotate', 'transform-origin']) {
      if (declarations.has(prop)) {
        declarations.delete(prop);
        changed = true;
      }
    }
    return changed ? ` style="${serializeDeclarations(declarations)}"` : full;
  });
}

function topAlignFluidFlex(html) {
  return String(html || '').replace(/\sstyle="([^"]*)"/gi, (full, css) => {
    const declarations = parseStyleDeclarations(css);
    const display = String(declarations.get('display') || '');
    if (!display.includes('flex') && !declarations.has('align-items')) return full;
    declarations.set('align-items', 'flex-start');
    return ` style="${serializeDeclarations(declarations)}"`;
  });
}

function forceFluidRootFit(html, { kind, mode, rect } = {}) {
  const match = String(html || '').match(OPENING_TAG);
  if (!match) return String(html || '');
  const opening = match[0];
  const styleMatch = opening.match(STYLE_ATTR);
  const declarations = parseStyleDeclarations(styleMatch?.[1] || '');
  const box = paperRootBox({ kind: kind || 'dropdown', mode, rect });
  declarations.set('width', box.width);
  if (box.maxWidth) declarations.set('max-width', box.maxWidth);
  declarations.set('height', box.height);
  if (box.alignItems) declarations.set('align-items', box.alignItems);
  if (box.alignSelf) declarations.set('align-self', box.alignSelf);
  // Live hamburger/dropdown panels are position:absolute. That hangs the
  // open menu off Interactive components (prior-run 390). Review cells
  // must be in-flow so the board can hug them.
  declarations.set('position', 'relative');
  declarations.set('overflow', 'visible');
  for (const prop of ['top', 'left', 'right', 'bottom']) declarations.delete(prop);
  const replacement = ` style="${serializeDeclarations(declarations)}"`;
  const next = styleMatch
    ? opening.replace(STYLE_ATTR, replacement)
    : opening.endsWith('/>')
      ? `${opening.slice(0, -2)}${replacement} />`
      : opening.replace(/>$/, `${replacement}>`);
  return next + String(html || '').slice(opening.length);
}

export function prepareFluidPairHtml(html, { kind, mode, rect } = {}) {
  return topAlignFluidFlex(stripChevronTransforms(forceFluidRootFit(html, { kind, mode, rect })));
}

export function paperCellWidth({ kind, mode, fallback = 'fit-content' } = {}) {
  return isHugParentKind(kind, mode) ? '100%' : fallback;
}

export function htmlEscape(value) {
  return String(value ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

export function paperSectionBadgeHtml(sid) {
  if (!sid) return '';
  return `<div style="width: 36px; height: 36px; border-radius: 999px; background-color: #E11D2E; color: #FFFFFF; font-family: Inter, sans-serif; font-size: 13px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">${htmlEscape(sid)}</div>`;
}

export function paperStateCellShell({
  name, note = '', fill = '', card = '#FFFFFF', lab = '#999999', kind, mode, width,
} = {}) {
  const fluid = isHugParentKind(kind, mode) || width === '100%';
  const slot = paperSlotBox({ kind, mode });
  const widthRule = fluid
    ? ' width: 100%; max-width: 100%; flex: 1 1 0; min-width: 0; align-self: flex-start;'
    : (width ? ` width: ${width}; flex-shrink: 0;` : '');
  const cardAlign = fluid ? 'flex-start' : 'center';
  const slotAlign = slot.alignItems || 'center';
  const slotJustify = slot.justifyContent || 'center';
  const slotSelf = slot.alignSelf ? ` align-self: ${slot.alignSelf};` : '';
  const slotWidth = fluid
    ? `width: ${slot.width}; max-width: ${slot.maxWidth || '100%'};`
    : 'width: fit-content;';
  return `<div layer-name="${htmlEscape(name)}" style="display: flex; flex-direction: column; align-items: ${cardAlign}; gap: 8px; padding: 14px 16px 16px 16px; background-color: ${card}; border-radius: 10px; overflow: visible; height: fit-content;${widthRule}">
     <div style="display: flex; flex-direction: row; align-items: center; justify-content: center; gap: 8px;">
       <div style="font-family: Inter, ui-monospace, monospace; font-size: 12px; font-weight: 600; letter-spacing: 0; text-transform: none; color: ${lab};">${htmlEscape(name)}</div>
       ${note ? `<div style="font-family: Inter, sans-serif; font-size: 11px; font-weight: 500; color: #E9A23B;">${htmlEscape(note)}</div>` : ''}
     </div>
     <div layer-name="Slot" style="display: flex; align-items: ${slotAlign}; justify-content: ${slotJustify};${slotSelf} ${slotWidth} height: fit-content; min-height: 0; padding: ${PAPER_SLOT_INSET}px; flex-shrink: 0; overflow: visible; border-radius: 12px;${fill ? ` background-color: ${fill};` : ''}"></div>
   </div>`;
}

export function paperPairRowHtml({ sid, title, token, head = '#111111', note = '' } = {}) {
  const label = sid ? `${sid} · ${token}` : token;
  return `<div layer-name="${htmlEscape(label)}" style="display: flex; flex-direction: column; gap: 10px; padding-top: 6px; width: 100%;">
         <div style="display: flex; flex-direction: row; align-items: center; gap: 10px;">
           ${paperSectionBadgeHtml(sid)}
           <div style="font-family: Inter, sans-serif; font-size: 15px; font-weight: 600; color: ${head};">${htmlEscape(title)}${htmlEscape(note)}</div>
         </div>
         <div layer-name="States" style="display: flex; flex-direction: column; gap: 8px; align-items: flex-start; width: 100%; height: fit-content;"></div>
       </div>`;
}

export function isGeometryLockedRoot(html, { kind, mode } = {}) {
  const opening = String(html || '').match(OPENING_TAG)?.[0] || '';
  const style = opening.match(STYLE_ATTR)?.[1] || '';
  const declarations = parseStyleDeclarations(style);
  const px = (name) => {
    const match = String(declarations.get(name) || '').match(/^(\d+(?:\.\d+)?)px$/);
    return match ? Number(match[1]) : 0;
  };
  if (isHugParentKind(kind, mode)) {
    const width = String(declarations.get('width') || '');
    const maxWidth = String(declarations.get('max-width') || '');
    const height = String(declarations.get('height') || '');
    return (width === '100%' || maxWidth === '100%')
      && (height === 'fit-content' || px('height') > 0);
  }
  return px('width') > 0 && px('height') > 0;
}

function isStartAligned(value) {
  const v = String(value || '').trim().toLowerCase();
  return !v || v === 'flex-start' || v === 'start';
}

function flexRadius(declarations) {
  return Math.max(
    parseFloat(declarations.get('border-radius') || '') || 0,
    parseFloat(declarations.get('border-top-left-radius') || '') || 0,
    parseFloat(declarations.get('border-bottom-left-radius') || '') || 0,
  );
}

function isCompactFlexControl(declarations) {
  const display = String(declarations.get('display') || '');
  if (!display.includes('flex')) return false;
  const height = parseFloat(declarations.get('height') || '');
  const compact = Number.isFinite(height) && height >= 28 && height <= 88;
  const radius = flexRadius(declarations);
  const padded = ['padding', 'padding-top', 'padding-left', 'padding-bottom', 'padding-right']
    .some((key) => (parseFloat(declarations.get(key) || '') || 0) > 0);
  const painted = Boolean(
    declarations.get('background-image')
    || declarations.get('background-color')
    || declarations.get('border')
    || declarations.get('border-width'),
  );
  return (compact || radius >= 8) && (radius >= 8 || (padded && painted));
}

function centerStartFlex(declarations) {
  for (const prop of ['align-items', 'justify-content', 'align-content']) {
    if (isStartAligned(declarations.get(prop))) declarations.set(prop, 'center');
  }
}

/**
 * Desktop lander pills are Autoflex-center. Framer computed styles often
 * serialize `flex-start`, and Paper then shows top-left. Rewrite start
 * alignment on compact pill/button roots so A/6 matches the page. Leave
 * `flex-end` / `space-between` alone — those are real hover slides.
 */
export function centerDesktopFlex(html) {
  return String(html || '').replace(
    /<([a-z][\w:-]*)([^>]*?)\sstyle="([^"]*)"([^>]*)>/gi,
    (full, tag, pre, style, post) => {
      const declarations = parseStyleDeclarations(style);
      if (!isCompactFlexControl(declarations)) return full;
      centerStartFlex(declarations);
      return `<${tag}${pre} style="${serializeDeclarations(declarations)}"${post}>`;
    },
  );
}

function isTransparent(value) {
  return !value || value === 'transparent' || value === 'rgba(0, 0, 0, 0)';
}

function luminance(value) {
  const match = String(value || '').match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/i);
  if (!match) return null;
  const r = Number(match[1]), g = Number(match[2]), b = Number(match[3]);
  return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
}

export function hasLightText(html) {
  for (const match of String(html || '').matchAll(/(?:^|[;\s"])color:\s*([^;"]+)/gi)) {
    const lum = luminance(match[1]);
    if (lum != null && lum >= 0.72) return true;
  }
  return false;
}

/**
 * Serializer often omits the ancestor fill. A transparent root with white
 * type then lands on a white Paper cell (prior-run hero CTA / footer).
 * Only paint when the source root was transparent AND the copy is light —
 * otherwise we reintroduce the charityx black-card failure.
 */
export function applyAncestorFill(html, ancestorBackground) {
  if (!ancestorBackground || isTransparent(ancestorBackground) || !hasLightText(html)) {
    return String(html || '');
  }
  const match = String(html || '').match(OPENING_TAG);
  if (!match) return String(html || '');
  const opening = match[0];
  const styleMatch = opening.match(STYLE_ATTR);
  const declarations = parseStyleDeclarations(styleMatch?.[1] || '');
  if (!isTransparent(declarations.get('background-color'))) return String(html || '');
  declarations.set('background-color', ancestorBackground);
  const replacement = ` style="${serializeDeclarations(declarations)}"`;
  const next = styleMatch
    ? opening.replace(STYLE_ATTR, replacement)
    : opening.endsWith('/>')
      ? `${opening.slice(0, -2)}${replacement} />`
      : opening.replace(/>$/, `${replacement}>`);
  return next + String(html || '').slice(opening.length);
}

/** Post-write Slot / imported-root styles for accordion cells. */
export function faqFitStyles() {
  return fluidFitStyles();
}

/**
 * Plus→minus leftover motion knocks the glyph out of the 35×35 circle once
 * Paper rotates about the top-left. Drop translate / rotate / transform.
 */
export function stripAccordionIconTransforms(html) {
  return String(html || '').replace(/\sstyle="([^"]*)"/gi, (full, css) => {
    const declarations = parseStyleDeclarations(css);
    let changed = false;
    for (const prop of ['transform', 'translate', 'rotate', 'transform-origin']) {
      if (declarations.has(prop)) {
        declarations.delete(prop);
        changed = true;
      }
    }
    return changed ? ` style="${serializeDeclarations(declarations)}"` : full;
  });
}

function topAlignFaqFlex(html) {
  return String(html || '').replace(/\sstyle="([^"]*)"/gi, (full, css) => {
    const declarations = parseStyleDeclarations(css);
    const display = String(declarations.get('display') || '');
    if (!display.includes('flex') && !declarations.has('align-items')) return full;
    declarations.set('align-items', 'flex-start');
    return ` style="${serializeDeclarations(declarations)}"`;
  });
}

function forceFaqRootFit(html) {
  const match = String(html || '').match(OPENING_TAG);
  if (!match) return String(html || '');
  const opening = match[0];
  const styleMatch = opening.match(STYLE_ATTR);
  const declarations = parseStyleDeclarations(styleMatch?.[1] || '');
  const box = paperRootBox({ kind: 'faq' });
  declarations.set('width', box.width);
  declarations.set('max-width', box.maxWidth);
  declarations.set('height', box.height);
  declarations.set('align-items', box.alignItems);
  declarations.set('align-self', box.alignSelf);
  const replacement = ` style="${serializeDeclarations(declarations)}"`;
  const next = styleMatch
    ? opening.replace(STYLE_ATTR, replacement)
    : opening.endsWith('/>')
      ? `${opening.slice(0, -2)}${replacement} />`
      : opening.replace(/>$/, `${replacement}>`);
  return next + String(html || '').slice(opening.length);
}

/** FAQ capture HTML for the A/6 states board: fluid, top-aligned, no icon motion. */
export function prepareFaqStateHtml(html) {
  return topAlignFaqFlex(stripAccordionIconTransforms(forceFaqRootFit(html)));
}

export function shouldWidenBoardForKind(kind, mode) {
  return !isFaqKind(kind, mode);
}

/**
 * A/6 board width. FAQ / accordion hugs the same parent as Navbar / Buttons /
 * Footer (pair-grid 1240). Never `capturedRect × 3`.
 */
export function a6BoardWidthPx({ mode, kind, states = [], root, cols = 0 } = {}) {
  if (isFaqKind(kind, mode)) return A6_PAIR_BOARD;
  if (mode === 'elements') {
    const widest = Math.max(...states.map((s) => (s.rect && s.rect[2]) || 0), 520);
    return widest + PAPER_SLOT_INSET * 2 + 32 + widest + PAPER_SLOT_INSET * 2 + 32 + 18 + 96;
  }
  const containerWidth = Math.max(root?.rect?.[2] || 0, 1200) + 96;
  return cols ? Math.max(A6_PAIR_BOARD, containerWidth) : Math.max(1400, containerWidth);
}

/**
 * Make the serialized root safe for an isolated Paper state cell.
 *
 * The url-to-paper serializer intentionally paints a transparent root with
 * its ancestor background so a full page does not lose its backdrop. That is
 * the wrong default for an isolated button/link: prior-run's transparent
 * anchors inherited the page's black background and then arrived as black
 * cards in the state board. We only remove that fallback when the source root
 * was transparent, and always pin the measured root box in px so `min-content`
 * cannot clip it inside a Paper slot. FAQ / accordion is the exception: those
 * rows are full-width patterns and must stay `width: 100%` in the A/6 parent.
 */
export function normalizePaperRoot(html, {
  rect, backgroundColor, ancestorBackground, unlockOverflow, kind, mode,
} = {}) {
  const match = String(html || '').match(OPENING_TAG);
  if (!match) return String(html || '');
  const opening = match[0];
  const styleMatch = opening.match(STYLE_ATTR);
  const declarations = parseStyleDeclarations(styleMatch?.[1] || '');
  const box = paperRootBox({ kind, mode, rect });
  if (box.width) declarations.set('width', box.width);
  if (box.maxWidth) declarations.set('max-width', box.maxWidth);
  if (box.height) declarations.set('height', box.height);
  if (box.alignItems) declarations.set('align-items', box.alignItems);
  if (box.alignSelf) declarations.set('align-self', box.alignSelf);
  if (unlockOverflow) {
    declarations.set('overflow', 'visible');
    declarations.set('overflow-x', 'visible');
    declarations.set('overflow-y', 'visible');
  }
  // Serializer often drops a solid pill fill, then paints the ancestor
  // onto the transparent root. That makes a black header CTA inherit
  // white and vanish (prior-run). Prefer the measured source fill.
  const currentBg = declarations.get('background-color');
  if (!isTransparent(backgroundColor) &&
      (isTransparent(currentBg) || currentBg === ancestorBackground)) {
    declarations.set('background-color', backgroundColor);
  } else if (isTransparent(backgroundColor) && isTransparent(currentBg)) {
    declarations.delete('background-color');
  }

  const replacement = ` style="${serializeDeclarations(declarations)}"`;
  const normalizedOpening = styleMatch
    ? opening.replace(STYLE_ATTR, replacement)
    : opening.endsWith('/>')
      ? `${opening.slice(0, -2)}${replacement} />`
      : opening.replace(/>$/, `${replacement}>`);
  const locked = stripCaptureAttributes(normalizedOpening + String(html || '').slice(opening.length));
  const filled = applyAncestorFill(locked, ancestorBackground);
  if (isHugParentKind(kind, mode)) return filled;
  return centerDesktopFlex(filled);
}

export function stripCaptureAttributes(html) {
  return String(html || '')
    .replace(/\sdata-hr-[\w-]+(?:="[^"]*")?/g, '');
}

export function htmlChanged(a, b) {
  return String(a || '').trim() !== String(b || '').trim();
}

/** Click 01→02 is two declared states. Keep Hover even when CSS looks identical. */
export function isHumanClickPair(state = {}) {
  return String(state.captureMethod || '').toLowerCase() === 'click-pair'
    || String(state.type || '').toLowerCase() === 'objects';
}

function styleMaps(html) {
  return [...String(html || '').matchAll(/style="([^"]*)"/g)]
    .map((match) => parseStyleDeclarations(match[1]));
}

/** Compare computed inline declarations by serialized node position. */
export function styleDelta(a, b, limit = 24) {
  const before = styleMaps(a);
  const after = styleMaps(b);
  const result = [];
  const count = Math.max(before.length, after.length);
  for (let node = 0; node < count && result.length < limit; node++) {
    const A = before[node] || new Map();
    const B = after[node] || new Map();
    const props = new Set([...A.keys(), ...B.keys()]);
    for (const prop of props) {
      const from = A.get(prop) ?? null;
      const to = B.get(prop) ?? null;
      if (from !== to) result.push({ node, prop, from, to });
      if (result.length >= limit) break;
    }
  }
  return result;
}

export function sectionKey(section) {
  return section?.id || section?.name || section?.label || null;
}

export function looksLikeSectionId(value) {
  return /^\d{2}$/.test(String(value || ''));
}

export function sectionLabelForRect(rect, sections = []) {
  if (!rect || !Array.isArray(sections) || !sections.length) return null;
  const top = Number(rect[1]) || 0;
  const bottom = top + (Number(rect[3]) || 0);
  let best = null;
  let bestOverlap = 0;
  for (const section of sections) {
    const sTop = Number(section.top);
    const sHeight = Number(section.height ?? section.h);
    if (!Number.isFinite(sTop) || !Number.isFinite(sHeight)) continue;
    const overlap = Math.max(0, Math.min(bottom, sTop + sHeight) - Math.max(top, sTop));
    if (overlap > bestOverlap) {
      bestOverlap = overlap;
      best = sectionKey(section);
    }
  }
  return best;
}

function parseRgb(value) {
  const match = String(value || '').match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/i);
  if (!match) return null;
  return { r: Number(match[1]), g: Number(match[2]), b: Number(match[3]) };
}

function rgbLuminance(rgb) {
  return (0.2126 * rgb.r + 0.7152 * rgb.g + 0.0722 * rgb.b) / 255;
}

function isAccentYellow(rgb) {
  return rgb.r > 180 && rgb.g > 160 && rgb.b < 130;
}

function isBrandPurple(rgb) {
  return rgb.b > 180 && rgb.r < 140 && rgb.g < 140;
}

function isTransparentPaint(value) {
  if (!value || value === 'transparent') return true;
  const match = String(value).match(/rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+(?:\s*,\s*([.\d]+))?/i);
  return Boolean(match && match[1] !== undefined && Number(match[1]) === 0);
}

function heightBand(state = {}) {
  const height = Number(state.rect?.[3]);
  if (!Number.isFinite(height)) return 'cta';
  if (height <= 24) return 'text';
  if (height <= 42) return 'chip';
  if (height <= 72) return 'cta';
  return 'block';
}

function hoverKind(state = {}) {
  const props = (state.styleDelta || []).map((delta) => String(delta.prop || '').toLowerCase());
  if (props.some((prop) => prop === 'transform' || prop === 'rotate' || prop === 'translate')) return 'rotate';
  if (props.includes('background-image')) return 'gradient';
  if (props.includes('background-color')) return 'fill';
  if (props.some((prop) => prop === 'color' || prop === '-webkit-text-fill-color')) return 'color';
  if (state.changed === false) return 'none';
  return 'other';
}

function paintKind(state = {}) {
  if (hoverKind(state) === 'gradient' || (state.styleDelta || []).some((delta) => delta.prop === 'background-image')) {
    return 'gradient';
  }
  const raw = state.sourceBackground;
  if (isTransparentPaint(raw)) return 'transparent';
  const rgb = parseRgb(raw);
  if (!rgb) return 'transparent';
  if (isAccentYellow(rgb)) return 'accent';
  if (isBrandPurple(rgb)) return 'brand';
  if (rgbLuminance(rgb) > 0.8) return 'light';
  return 'dark';
}

/** Visual fingerprint. Same pattern → same name; a new scrape gets a new key. */
export function patternKey(state = {}, { kind } = {}) {
  const k = String(kind || state.kind || '').toLowerCase();
  return [k, heightBand(state), paintKind(state), hoverKind(state)].join('|');
}

function preferredToken(state = {}, { kind } = {}) {
  const k = String(kind || state.kind || '').toLowerCase();
  const height = heightBand(state);
  const paint = paintKind(state);
  const hover = hoverKind(state);
  if (k === 'nav') return hover === 'rotate' ? 'navbar-dropdown' : 'navbar-link';
  if (isDropdownKind(k)) return 'navbar-dropdown';
  if (isHamburgerKind(k)) return interactiveRowMeta({ kind: k, viewportWidth: state.viewportWidth }).token;
  if (k === 'footer') return 'footer-link';
  if (k === 'faq') return 'accordion-item';
  if (k === 'forms') {
    return /button|submit|trial|cta/i.test(String(state.component || ''))
      ? 'btn-primary'
      : 'form-control';
  }
  if (k === 'buttons') {
    if (height === 'text' && paint === 'transparent') return 'text-link';
    if (height === 'chip') return 'pill';
    if (paint === 'accent') return 'btn-accent';
    if (paint === 'brand') return 'btn-brand';
    if (paint === 'light') return 'btn-secondary';
    if (paint === 'gradient' || paint === 'dark') return 'btn-primary';
    return 'btn-ghost';
  }
  return slugify(state.component, 'component');
}

function nextUniqueToken(base, used) {
  if (!used.has(base)) return base;
  let n = 2;
  while (used.has(`${base}-${n}`)) n += 1;
  return `${base}-${n}`;
}

/**
 * Stable design-system token for an A/6 cell. Eyebrows hand to development
 * as `navbar-link` / `btn-primary` / `pill`, not "PRODUCT — DEFAULT".
 * Variants follow the visual pattern (size + paint + hover), not the
 * marketing label. Transparent gradient CTAs are not the same as date chips.
 */
export function designSystemToken(state = {}, { kind } = {}) {
  return preferredToken(state, { kind });
}

/**
 * Name a batch. Repeating patterns reuse one token; a newly scraped pattern
 * that would collide (`btn-primary` on a date chip) gets the next free name.
 */
export function assignDesignSystemTokens(states = [], { kind } = {}) {
  const used = new Set();
  const byKey = new Map();
  return states.map((state) => {
    const key = patternKey(state, { kind });
    if (byKey.has(key)) return byKey.get(key);
    const name = nextUniqueToken(preferredToken(state, { kind }), used);
    used.add(name);
    byKey.set(key, name);
    return name;
  });
}

/** Human type for Source · {page} state columns. Never a class or component name. */
export function objectTypeLabel(state = {}, kind = '') {
  const method = String(state.captureMethod || '').toLowerCase();
  if (method === 'hover-leave') return 'buttons';
  if (method === 'click-solo' || method === 'press-solo') return 'component';
  if (method === 'click-pair') return 'objects';
  const type = String(state.type || '').toLowerCase();
  if (type === 'buttons') return 'buttons';
  if (type === 'component') return 'component';
  if (type === 'objects') return 'objects';
  const token = String(state.token || '').toLowerCase();
  const key = String(state.patternKey || '').toLowerCase();
  const k = String(kind || state.kind || '').toLowerCase();
  const blob = `${token} ${key} ${k}`;
  if (
    token.includes('text-link')
    || token.includes('footer-link')
    || token.includes('navbar-link')
    || k === 'footer'
    || key.includes('|text|')
    || /\btext-link\b/.test(blob)
  ) {
    return 'Text link';
  }
  if (blob.includes('social')) return 'Social icon';
  if (blob.includes('pill')) return 'Pill';
  if (token === 'object' || String(state.type || '') === 'Object') return 'Object';
  if (/\bicon\b/.test(token) && !token.includes('button')) return 'Icon';
  return 'Button';
}


export const SOURCE_ITEM_RULE_COLOR = '#DDDDDD';
export const SOURCE_ITEM_RULE_HEIGHT = 2;
export const SOURCE_STACK_GAP = 16;
export const SOURCE_HOVER_WIDTH = 780;
/** Review ground for parked buttons — grey so a dark-mode wrong fill is visible. */
export const SOURCE_HOVER_PAD = 24;
export const SOURCE_HEADING_FILL = '#E8E8E8';

export function sourceHoverColumnCss() {
  return [
    'display: flex',
    'flex-direction: column',
    'align-items: flex-start',
    `gap: ${SOURCE_STACK_GAP}px`,
    `width: ${SOURCE_HOVER_WIDTH}px`,
    `min-width: ${SOURCE_HOVER_WIDTH}px`,
    `max-width: ${SOURCE_HOVER_WIDTH}px`,
    'flex-shrink: 0',
    'flex-grow: 0',
    'height: fit-content',
    'overflow: visible',
    `padding: ${SOURCE_HOVER_PAD}px`,
    `background-color: ${SOURCE_HEADING_FILL}`,
  ].join('; ') + ';';
}

export function sourceHoverColumnStyles() {
  return {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-start',
    gap: `${SOURCE_STACK_GAP}px`,
    width: `${SOURCE_HOVER_WIDTH}px`,
    minWidth: `${SOURCE_HOVER_WIDTH}px`,
    maxWidth: `${SOURCE_HOVER_WIDTH}px`,
    flexGrow: '0',
    flexShrink: '0',
    height: 'fit-content',
    overflow: 'visible',
    padding: `${SOURCE_HOVER_PAD}px`,
    backgroundColor: SOURCE_HEADING_FILL,
  };
}

/** Pill / primary / pattern `|cta|`. Process cards and blog titles are not CTAs. */
export function isSourceCta(state = {}, kind = '') {
  const key = String(state.patternKey || '').toLowerCase();
  if (key.includes('|cta|')) return true;
  const t = objectTypeLabel(state, kind);
  if (t === 'Pill' || t === 'Object' || t === 'objects') return true;
  if (isHumanClickPair(state)) return true;
  const token = String(state.token || '').toLowerCase();
  if (state.human && /button|buttons/i.test(String(kind || state.kind || ''))) return true;
  return /^btn-primary$|^btn-accent$|^btn-brand$|^btn-ghost$|^btn-secondary$/.test(token);
}

export function sourceSectionNumberHtml(sid) {
  const id = String(sid || '').padStart(2, '0').slice(0, 2);
  if (!id) return '';
  return `<div layer-name="section-number" style="width: 80px; height: 80px; border-radius: 999px; background-color: #E11D2E; color: #FFFFFF; font-family: Inter, sans-serif; font-size: 24px; font-weight: 700; line-height: 30px; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">${htmlEscape(id)}</div>`;
}

/**
 * url-to-paper `fe()` returns `{ status, html }`.
 * `String(that)` is `[object Object]` — that is not Paper HTML.
 */
export function unwrapSerializerHtml(result) {
  if (result == null) return '';
  if (typeof result === 'string') {
    const trimmed = result.trim();
    if (!trimmed || trimmed === '[object Object]') return '';
    return trimmed.startsWith('<') ? trimmed : '';
  }
  if (typeof result === 'object') {
    if (result.status && result.status !== 'success') return '';
    if (typeof result.html === 'string') return unwrapSerializerHtml(result.html);
  }
  return '';
}

/** Stamp layer-name="button" on the painted CTA root. Never wrap it in another Frame. */
export function asNamedButtonHtml(html) {
  const raw = unwrapSerializerHtml(html);
  if (!raw) return '';
  const m = raw.match(/^<([a-z][\w:-]*)((?:\s[^>]*)?)(\/?)>/i);
  if (!m) return `<div layer-name="button">${raw}</div>`;
  let attrs = m[2] || '';
  if (/layer-name\s*=/i.test(attrs)) {
    attrs = attrs.replace(/layer-name\s*=\s*("[^"]*"|'[^']*')/i, 'layer-name="button"');
  } else {
    attrs += ' layer-name="button"';
  }
  return `<${m[1]}${attrs}${m[3]}>${raw.slice(m[0].length)}`;
}

export function sourceStateCellHtml({
  label, inner = '', lab = '#999999', showLabel = true, layer,
} = {}) {
  const name = layer || (String(label || 'default').toLowerCase() === 'hover' ? 'hover' : 'default');
  const caption = showLabel
    ? `<div layer-name="label" style="font-family: Inter, sans-serif; font-size: 11px; font-weight: 600; letter-spacing: 0.02em; text-transform: uppercase; color: ${lab};">${htmlEscape(label)}</div>`
    : '';
  return `<div layer-name="${htmlEscape(name)}" style="display: flex; flex-direction: column; align-items: flex-start; height: fit-content; width: fit-content; flex-shrink: 0; gap: 8px;">
  ${caption}
  ${asNamedButtonHtml(inner)}
</div>`;
}

export function sourceHoverItemHtml({
  type = 'Button', defaultHtml = '', hoverHtml = '', includeHover = true,
  head = '#111111', lab = '#999999', captureMethod = '',
} = {}) {
  const objectPair = isHumanClickPair({ type, captureMethod });
  const cells = objectPair
    ? [
      sourceStateCellHtml({ label: '01', inner: defaultHtml, showLabel: false, layer: '01' }),
      ...(includeHover && hoverHtml
        ? [sourceStateCellHtml({ label: '02', inner: hoverHtml, showLabel: false, layer: '02' })]
        : []),
    ]
    : [
      sourceStateCellHtml({ label: 'Default', inner: defaultHtml, lab }),
      ...(includeHover && hoverHtml
        ? [sourceStateCellHtml({ label: 'Hover', inner: hoverHtml, lab })]
        : []),
    ];
  const states = objectPair
    ? 'display: flex; flex-direction: column; align-items: flex-start; width: 100%; gap: 16px;'
    : 'display: flex; flex-direction: row; align-items: flex-start; width: 100%; gap: 12px;';
  return `<div layer-name="object" style="display: flex; flex-direction: column; align-items: flex-start; align-self: stretch;">
  <div layer-name="${htmlEscape(type)}" style="display: flex; flex-direction: column; width: 100%; gap: 8px;">
    <div layer-name="type" style="font-family: Inter, sans-serif; font-size: 13px; font-weight: 600; line-height: 16px; color: ${head};">${htmlEscape(type)}</div>
    <div layer-name="States" style="${states}">
${cells.join('\n')}
    </div>
  </div>
</div>`;
}

export function sourceItemRuleHtml() {
  return `<div layer-name="Rule" style="height: ${SOURCE_ITEM_RULE_HEIGHT}px; align-self: stretch; flex-shrink: 0; background-color: ${SOURCE_ITEM_RULE_COLOR};"></div>`;
}

/** Inner children of Hover States: one section-number, then a list of objects. */
export function sourceHoverStackInnerHtml(items = []) {
  const sid = String(items[0]?.sid || '').padStart(2, '0').slice(0, 2);
  const objects = (items || []).map((item) => sourceHoverItemHtml(item)).join('\n');
  return `${sourceSectionNumberHtml(sid)}
<div layer-name="list" style="display: flex; flex-direction: column; align-items: flex-start; gap: ${SOURCE_STACK_GAP}px; width: 100%; height: fit-content;">
${objects}
</div>`;
}

export function sourceHoverStackHtml(items = []) {
  return `<div layer-name="Hover States" style="${sourceHoverColumnCss()}">
${sourceHoverStackInnerHtml(items)}
</div>`;
}

/**
 * Parent-row leftover: an old sibling 36px #E11D2E sid circle sitting
 * beside Hover States. The section number lives ONCE inside the column
 * (`section-number`). Keep the JPEG shot + red divider. Only delete a
 * sibling leftover when the column is about to grow the list.
 */
export function isLeftoverSourceSectionBadge(node, { keepIds = [] } = {}) {
  if (!node?.id || keepIds.includes(node.id)) return false;
  const name = String(node.name || '');
  if (/^(Hover States|Buttons|Divider|Rule|Screenshots|Headings|section-number|list|object)$/i.test(name)) return false;
  if (node.component && node.component !== 'Frame') return false;
  const kids = node.childCount ?? node.children?.length ?? 0;
  if (kids > 1) return false;
  return name === 'Frame' || /^\d{2}$/.test(name) || /badge/i.test(name);
}

export function leftoverSourceSectionBadgeIds(children = [], opts = {}) {
  return (children || [])
    .filter((c) => isLeftoverSourceSectionBadge(c, opts))
    .map((c) => c.id)
    .filter(Boolean);
}

const TRANSPARENT = /^(transparent|rgba?\(\s*0\s*,\s*0\s*,\s*0\s*,\s*0(?:\.0+)?\s*\))$/i;

function isOpaquePaint(value) {
  const v = String(value || '').trim();
  return Boolean(v) && !TRANSPARENT.test(v);
}

/** True only when default and hover would look different on Paper.
 *  Color-only / unchanged bg pairs stay off the board. Closed|open is not a hover pair. */
export function hasVisibleHoverDelta(state = {}) {
  if (isHumanClickPair(state) && (state.hoverFile || state.includeHover === true)) return true;
  if (state.openFile || state.opened || /\[open\]|accordion|hamburger|dropdown/i.test(String(state.mode || state.kind || ''))) {
    if (state.openFile || state.opened) return true;
  }
  const from = String(state.sourceBackground || '');
  const to = String(state.hoverBackground || '');
  if (from && to && from !== to && (isOpaquePaint(from) || isOpaquePaint(to))) return true;
  const deltas = state.styleDelta || state.hoverDelta || [];
  for (const d of deltas) {
    const prop = String(d.prop || d.property || '');
    if (!/background|border|box-shadow|filter|opacity/i.test(prop)) continue;
    if (String(d.from) !== String(d.to) && (isOpaquePaint(d.to) || isOpaquePaint(d.from))) return true;
  }
  // Text links (footer / nav) express hover as a color change only — that IS
  // the visible delta for a link, not an incidental tick (prior-run footer:
  // grey → indigo). Buttons keep the paint-only rule above.
  if (/link|text/i.test(String(state.token || state.patternKey || '')) || String(state.kind || '') === 'footer') {
    for (const d of deltas) {
      const prop = String(d.prop || d.property || '');
      if (!/^color$|text-fill/i.test(prop)) continue;
      if (String(d.from) !== String(d.to)) return true;
    }
  }
  return false;
}

/**
 * One representative per pattern on a section.
 * If more than two of the same type share a section, keep one.
 */
export function pickStatesForSection(states = [], kind = '') {
  const bySid = new Map();
  for (const s of states || []) {
    const sid = String(s.sectionId || '').padStart(2, '0');
    if (!bySid.has(sid)) bySid.set(sid, []);
    bySid.get(sid).push(s);
  }
  const out = [];
  for (const [sid, group] of bySid) {
    const picked = [];
    const seenToken = new Set();
    const seenLabel = new Set();
    for (const s of group) {
      const visible = hasVisibleHoverDelta(s);
      const cta = isSourceCta(s, kind);
      if (!visible && !cta) continue;
      const token = s.component || s.defaultFile || s.token || s.patternKey;
      const label = String(s.label || s.component || '')
        .toLowerCase()
        .replace(/^\d{2}\s*·\s*/, '')
        .replace(/\s+/g, ' ')
        .trim();
      if (seenToken.has(token)) continue;
      if (label && seenLabel.has(label)) continue;
      seenToken.add(token);
      if (label) seenLabel.add(label);
      picked.push({ ...s, includeHover: visible || Boolean(isHumanClickPair(s) && s.hoverFile) });
    }
    picked.sort((a, b) => {
      const ah = a.includeHover ? 0 : 1;
      const bh = b.includeHover ? 0 : 1;
      if (ah !== bh) return ah - bh;
      const ax = Array.isArray(a.rect) ? a.rect[0] : 0;
      const bx = Array.isArray(b.rect) ? b.rect[0] : 0;
      return ax - bx;
    });
    if (!picked.length) continue;
    out.push({
      sid,
      states: picked,
      types: [...new Set(picked.map((s) => objectTypeLabel(s, kind)))],
    });
  }
  return out;
}

/** Visible / layer eyebrow: `btn-primary`, `btn-primary:hover`, `accordion-item[open]`. */
export function designSystemEyebrow(token, stateKind = 'default') {
  const name = String(token || 'component');
  const kind = String(stateKind || 'default').toLowerCase();
  if (kind === 'hover') return `${name}:hover`;
  if (kind === 'open') return `${name}[open]`;
  if (kind === 'closed' || kind === 'collapsed' || kind === 'default') return name;
  return name;
}

export function uniquePageEntries(entries = []) {
  const seen = new Set();
  const out = [];
  for (const [index, entry] of entries.entries()) {
    const url = typeof entry === 'string' ? entry : entry?.url;
    if (!url || seen.has(url)) continue;
    seen.add(url);
    out.push({ ...(typeof entry === 'object' ? entry : { url }), slug: pageSlug(entry, index) });
  }
  return out;
}
