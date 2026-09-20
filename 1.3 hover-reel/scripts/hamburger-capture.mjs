// Click-to-open hamburger at every width that paints the icon (typically
// 768 and 390). Do not invent a burger on desktop when the icon is absent.
// Closed | open HTML lands on FRAME `Interactive components`.

import { isDesktopDropdownViewport, looksLikeHamburger } from './component-state-utils.mjs';

export function findHamburgerCandidate() {
  const cands = [];
  for (const el of document.querySelectorAll('div,button,a')) {
    const r = el.getBoundingClientRect();
    if (r.top > 90 || r.top < 0) continue;
    if (r.width < 20 || r.width > 56 || r.height < 20 || r.height > 56) continue;
    if (r.x < innerWidth * 0.55) continue;
    const cs = getComputedStyle(el);
    if (parseFloat(cs.opacity) < 0.05) continue;
    cands.push({
      el,
      x: r.x + r.width / 2,
      y: r.y + r.height / 2,
      w: r.width,
      h: r.height,
      tag: el.tagName,
      label: (el.getAttribute('aria-label') || el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 64),
      aria: el.getAttribute('aria-label') || '',
    });
  }
  cands.sort((a, b) => a.w * a.h - b.w * b.h);
  const hit = cands[0];
  if (!hit) return null;
  hit.el.setAttribute('data-hr-burger', '');
  return {
    x: hit.x,
    y: hit.y,
    w: hit.w,
    h: hit.h,
    tag: hit.tag,
    label: hit.label,
    aria: hit.aria,
    box: [Math.round(hit.x - hit.w / 2), Math.round(hit.y - hit.h / 2), Math.round(hit.w), Math.round(hit.h)],
  };
}

export function visibleNavish() {
  const out = [];
  for (const el of document.querySelectorAll('a,button')) {
    const r = el.getBoundingClientRect();
    if (r.width < 12 || r.height < 12) continue;
    if (r.bottom < 0 || r.top > innerHeight) continue;
    const cs = getComputedStyle(el);
    if (parseFloat(cs.opacity) < 0.05 || cs.visibility === 'hidden') continue;
    const txt = (el.textContent || '').trim().replace(/\s+/g, ' ');
    if (!txt || txt.length > 48) continue;
    out.push({
      t: txt.slice(0, 48),
      tag: el.tagName,
      x: Math.round(r.x),
      y: Math.round(r.y),
      w: Math.round(r.width),
      h: Math.round(r.height),
    });
  }
  return out;
}

export function markOpenOverlay() {
  const first = [...document.querySelectorAll('a')].find((a) => {
    const t = (a.textContent || '').trim();
    const r = a.getBoundingClientRect();
    return r.y > 70 && r.y < 220 && t.length > 1 && t.length < 24;
  });
  if (!first) return null;
  let el = first.parentElement;
  let best = null;
  while (el && el !== document.body) {
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    if (
      (cs.position === 'absolute' || cs.position === 'fixed')
      && r.height >= 80
      && r.width >= innerWidth * 0.5
      && r.y < 200
    ) {
      el.setAttribute('data-hr-panel', '');
      best = {
        tag: el.tagName,
        pos: cs.position,
        box: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)],
      };
      break;
    }
    el = el.parentElement;
  }
  return best;
}

/**
 * Click the burger if one is painted. Desktop without a hamburger-shaped
 * icon is not a burger — do not invent one.
 */
export async function captureHamburgerPair(page, {
  serialize,
  movePointer,
  viewportWidth = 390,
} = {}) {
  const clicked = await page.evaluate(findHamburgerCandidate);
  if (!clicked) {
    return { found: false, reason: 'no hamburger candidate in the top-right 56px bucket' };
  }
  if (isDesktopDropdownViewport(viewportWidth)
      && !looksLikeHamburger({
        width: clicked.w,
        height: clicked.h,
        label: clicked.label,
        aria: clicked.aria,
        viewportWidth,
      })) {
    return { found: false, reason: 'no hamburger on desktop — do not invent' };
  }

  const closedSel = '[data-hr-burger]';
  const closedLabels = await page.evaluate(visibleNavish);
  let closed = await serialize(page, closedSel);
  if (closed.status !== 'success') {
    return { found: false, reason: 'closed serialize failed' };
  }

  await movePointer(page, clicked.x, clicked.y, { steps: 16, label: 'hamburger' });
  await page.mouse.click(clicked.x, clicked.y);
  await page.waitForTimeout(700);

  const overlay = await page.evaluate(markOpenOverlay);
  const openLabels = await page.evaluate(visibleNavish);
  const closedSet = new Set(closedLabels.map((x) => x.t));
  const appeared = openLabels.filter((x) => !closedSet.has(x.t));
  const opened = Boolean(overlay || appeared.length);

  let openSel = overlay ? '[data-hr-panel]' : closedSel;
  let open = await serialize(page, openSel);
  if (open.status !== 'success') open = await serialize(page, closedSel);
  if (open.status !== 'success') {
    return { found: false, reason: 'open serialize failed' };
  }

  return {
    found: true,
    triggerLabel: clicked.label || 'Menu',
    triggerBox: clicked.box,
    navBox: overlay?.box || clicked.box,
    rootSel: openSel,
    hoverConfirmed: true,
    items: appeared,
    overlay,
    opened,
    closed,
    open,
  };
}
