// Artboards that 1.4 token-pass must bind to registered tokens.
// Landers + Design Library + Capture Tool boards (Navigation, Components).

export const INTERACTIVE_COMPONENTS = 'Interactive components';
export const NAVIGATION_BOARD = 'Navigation';
export const COMPONENTS_BOARD = 'Components';
export const BUTTONS_BOARD = 'Buttons';
export const HOVER_STATES_BOARD = BUTTONS_BOARD;

export function isInteractiveComponentsBoard(name = '') {
  const n = String(name || '');
  return n === INTERACTIVE_COMPONENTS || n === NAVIGATION_BOARD
    || n === COMPONENTS_BOARD || n === BUTTONS_BOARD || n === 'Hover States';
}

/** Frames eligible for authoritative 1.4 mining. Generated boards stay out. */
export function isLibraryMineArtboard(name = '') {
  const n = String(name || '');
  return /^[\w][\w-]*-(desktop|768|390)$/i.test(n)
    || /^(Buttons|Hover States|Components|Navigation|Interactive components)$/.test(n)
    || /^A\/6 · .+ · states$/.test(n);
}

/** `{page}-(desktop|768|390)`, Design Library, Navigation, Components. */
export function isTokenPassArtboard(name = '') {
  const n = String(name || '');
  if (isLibraryMineArtboard(n)) return true;
  if (/^Design Library$/i.test(n)) return true;
  return false;
}

export function selectTokenPassArtboards(artboards = [], { only } = {}) {
  return (artboards || []).filter((a) => {
    const name = typeof a === 'string' ? a : a?.name;
    if (only && !String(name).includes(only)) return false;
    return isTokenPassArtboard(name);
  });
}
