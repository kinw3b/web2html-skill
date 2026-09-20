// Shared hover-to-open navbar dropdown detection.
//
// Reused by capture-menu-states.mjs (desktop hover-to-open at 1600) and
// capture-component-states.mjs --kind dropdown. Do not hunt: a site with no
// panel of new labels on hover is not a dropdown. Hamburgers stay 4.1-M
// (capture-hamburger-states.mjs) on the same Interactive components frame.

import { DESKTOP_DROPDOWN_WIDTH, isDesktopDropdownViewport, looksLikeHamburger } from './component-state-utils.mjs';

export function tagNavTriggersInPage() {
  const inter = [];
  for (const el of document.querySelectorAll('*')) {
    const r = el.getBoundingClientRect();
    if (r.width < 18 || r.height < 14 || r.width > 700 || r.top > 160 || r.top < -10) continue;
    const cs = getComputedStyle(el);
    if (cs.cursor !== 'pointer' && el.tagName !== 'A' && el.tagName !== 'BUTTON') continue;
    if (parseFloat(cs.opacity) < 0.05) continue;
    inter.push(el);
  }
  const outer = inter.filter((e) => !inter.some((o) => o !== e && o.contains(e)));
  outer.sort((a, b) => a.getBoundingClientRect().x - b.getBoundingClientRect().x);
  outer.forEach((e, i) => e.setAttribute('data-hr-ctl', String(i)));
  return outer.length;
}

export function visibleInteractiveLabels() {
  const out = [];
  for (const el of document.querySelectorAll('a,button,div,li,p,span')) {
    const r = el.getBoundingClientRect();
    if (r.width < 30 || r.height < 14 || r.height > 90) continue;
    if (r.bottom < 0 || r.top > innerHeight) continue;
    const cs = getComputedStyle(el);
    if (cs.cursor !== 'pointer' && el.tagName !== 'A') continue;
    if (parseFloat(cs.opacity) < 0.05 || cs.visibility === 'hidden') continue;
    const txt = (el.textContent || '').trim();
    if (!txt || txt.length > 26) continue;
    out.push(txt + '@' + Math.round(r.x) + ',' + Math.round(r.y));
  }
  return out;
}

export function resolveOpenPanel({ trigger, newLabels }) {
  const want = new Set(newLabels);
  const hits = [];
  for (const el of document.querySelectorAll('a,button,div,li,p,span')) {
    const r = el.getBoundingClientRect();
    if (r.width < 30 || r.height < 14 || r.height > 90) continue;
    const cs = getComputedStyle(el);
    if (cs.cursor !== 'pointer' && el.tagName !== 'A') continue;
    if (parseFloat(cs.opacity) < 0.05) continue;
    const txt = (el.textContent || '').trim();
    if (!txt || txt.length > 26) continue;
    if (!want.has(txt + '@' + Math.round(r.x) + ',' + Math.round(r.y))) continue;
    hits.push({ el, txt, r });
  }
  const outer = hits.filter((c) => !hits.some((o) => o.el !== c.el && o.el.contains(c.el)));
  const seen = new Set();
  const items = [];
  for (const c of outer.sort((a, b) => a.r.top - b.r.top)) {
    if (seen.has(c.txt)) continue;
    seen.add(c.txt);
    c.el.setAttribute('data-hr-mi', String(items.length));
    items.push({
      i: items.length,
      label: c.txt,
      box: [Math.round(c.r.x), Math.round(c.r.y), Math.round(c.r.width), Math.round(c.r.height)],
    });
  }
  if (!items.length) return { err: 'no panel items resolved' };

  const trgEl = document.querySelector(`[data-hr-ctl="${trigger}"]`);
  if (!trgEl) return { err: 'trigger gone', items };
  const nodes = [trgEl, ...items.map((it) => document.querySelector(`[data-hr-mi="${it.i}"]`))];
  let nav = trgEl;
  while (nav.parentElement && !nodes.every((n) => nav.contains(n))) nav = nav.parentElement;
  const nr0 = nav.getBoundingClientRect();
  if (nr0.height > 1200 || nr0.width > innerWidth * 0.95) {
    return {
      err: `container escaped to ${Math.round(nr0.width)}x${Math.round(nr0.height)}`,
      items,
      tooBig: true,
    };
  }
  nav.setAttribute('data-hr-nav', '');
  const nr = nav.getBoundingClientRect();
  return {
    items,
    triggerLabel: (trgEl.getAttribute('aria-label') || trgEl.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 64),
    triggerBox: [Math.round(trgEl.getBoundingClientRect().x), Math.round(trgEl.getBoundingClientRect().y),
      Math.round(trgEl.getBoundingClientRect().width), Math.round(trgEl.getBoundingClientRect().height)],
    nav: {
      tag: nav.tagName.toLowerCase(),
      cls: (nav.className || '').toString().slice(0, 50),
      box: [Math.round(nr.x), Math.round(nr.y), Math.round(nr.width), Math.round(nr.height)],
    },
  };
}

export function markPanelRoot(itemCount) {
  const els = [];
  for (let i = 0; i < itemCount; i++) els.push(document.querySelector(`[data-hr-mi="${i}"]`));
  let p = els[0];
  if (!p) return null;
  while (p.parentElement && !els.every((e) => p.contains(e))) p = p.parentElement;
  if (p.parentElement && p.parentElement.getBoundingClientRect().height < 900) p = p.parentElement;
  p.setAttribute('data-hr-panel', '');
  const r = p.getBoundingClientRect();
  return {
    tag: p.tagName.toLowerCase(),
    box: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)],
  };
}

export function triggerMeta(index) {
  const el = document.querySelector(`[data-hr-ctl="${index}"]`);
  if (!el) return null;
  const r = el.getBoundingClientRect();
  return {
    label: (el.getAttribute('aria-label') || el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 64),
    aria: el.getAttribute('aria-label') || '',
    width: Math.round(r.width),
    height: Math.round(r.height),
    box: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)],
  };
}

const centre = (b) => ({ x: b.x + b.width / 2, y: b.y + b.height / 2 });

/**
 * Hover a nav control. If a panel of new link labels appears, return the
 * scoped root selector. Otherwise { found: false, reason }.
 */
export async function discoverHoverDropdown(page, {
  trigger = 0,
  movePointer,
  viewportWidth = DESKTOP_DROPDOWN_WIDTH,
} = {}) {
  if (!isDesktopDropdownViewport(viewportWidth)) {
    return { found: false, reason: 'not a desktop viewport — hamburger stays 4.1-M' };
  }
  const count = await page.evaluate(tagNavTriggersInPage);
  if (!count) return { found: false, reason: 'no nav controls in the header band' };

  const meta = await page.evaluate(triggerMeta, trigger);
  if (!meta) return { found: false, reason: `trigger ${trigger} not found` };
  if (looksLikeHamburger({ ...meta, viewportWidth })) {
    return { found: false, reason: 'hamburger / click-toggle — use capture-hamburger-states.mjs (4.1-M)' };
  }

  const trg = page.locator(`[data-hr-ctl="${trigger}"]`);
  const trgBox = await trg.boundingBox();
  if (!trgBox) return { found: false, reason: 'trigger has no box' };
  const tc = centre(trgBox);

  await movePointer(page, 5, 5, { steps: 10, label: '' });
  await page.waitForTimeout(700);
  const closedSet = new Set(await page.evaluate(visibleInteractiveLabels));

  await movePointer(page, tc.x, tc.y, { steps: 12, label: meta.label || 'menu' });
  await page.waitForTimeout(750);
  const openList = await page.evaluate(visibleInteractiveLabels);
  const newLabels = openList.filter((l) => !closedSet.has(l));
  if (!newLabels.length) {
    return { found: false, reason: 'nothing new appeared on hover — not a dropdown' };
  }

  const info = await page.evaluate(resolveOpenPanel, { trigger, newLabels });
  if (info.err && !info.tooBig) return { found: false, reason: info.err, items: info.items };

  let rootSel = '[data-hr-nav]';
  let navBox = info.nav && info.nav.box;
  if (info.tooBig) {
    const panel = await page.evaluate(markPanelRoot, info.items.length);
    if (!panel) return { found: false, reason: 'panel root missing after page-sized ancestor' };
    rootSel = '[data-hr-panel]';
    navBox = panel.box;
  }

  return {
    found: true,
    trigger,
    triggerLabel: info.triggerLabel || meta.label || 'Menu',
    triggerBox: info.triggerBox || meta.box,
    items: info.items,
    rootSel,
    navBox,
    triggerCentre: tc,
  };
}

/**
 * Closed | open pair. One pattern. Does not capture per-item hovers.
 */
export async function captureDropdownPair(page, {
  serialize,
  movePointer,
  trigger = 0,
  viewportWidth = DESKTOP_DROPDOWN_WIDTH,
} = {}) {
  const found = await discoverHoverDropdown(page, { trigger, movePointer, viewportWidth });
  if (!found.found) return found;

  await movePointer(page, 5, 5, { steps: 10, label: '' });
  await page.waitForTimeout(500);
  let closed = await serialize(page, found.rootSel);
  if (closed.status !== 'success') {
    closed = await serialize(page, `[data-hr-ctl="${found.trigger}"]`);
  }
  if (closed.status !== 'success') {
    return { found: false, reason: 'closed serialize failed' };
  }
  found.closed = closed;

  await movePointer(page, found.triggerCentre.x, found.triggerCentre.y, {
    steps: 12,
    label: found.triggerLabel || 'menu',
  });
  await page.waitForTimeout(750);
  const open = await serialize(page, found.rootSel);
  if (open.status !== 'success') return { found: false, reason: 'open serialize failed' };
  found.open = open;
  found.hoverConfirmed = await page.evaluate((i) => {
    const el = document.querySelector(`[data-hr-ctl="${i}"]`);
    return !!el && el.matches(':hover');
  }, found.trigger);
  return found;
}

/**
 * Walk header triggers until one hover-opens a panel. One of a pattern.
 */
export async function captureFirstDropdownPair(page, opts = {}) {
  const count = await page.evaluate(tagNavTriggersInPage);
  if (!count) return { found: false, reason: 'no nav controls in the header band' };
  let last = { found: false, reason: 'no hover-to-open panel' };
  for (let i = 0; i < count; i++) {
    const hit = await captureDropdownPair(page, { ...opts, trigger: i });
    if (hit.found) return hit;
    last = hit;
  }
  return last;
}

async function htmlFromSelector(page, serialize, sel) {
  if (!sel) return { status: "error", html: "", error: "no selector" };
  try {
    const via = await serialize(page, sel);
    if (via?.status === "success" && via.html) return via;
  } catch { /* fall through to outerHTML */ }
  const html = await page.evaluate((s) => {
    const el = document.querySelector(s);
    return el ? el.outerHTML : "";
  }, sel);
  return html
    ? { status: "success", html }
    : { status: "error", html: "", error: "wrapper serialize failed" };
}

/**
 * Human click: HUD stamped [data-hr-dd-keep]. Serialize the open wrapper first
 * so a later click cannot steal the pick. Then try closed | hover-open.
 */
export async function capturePickedDropdown(page, {
  serialize,
  movePointer,
  keep = "",
  label = "",
  pickSelector = "[data-hr-dd-pick]",
  viewportWidth = DESKTOP_DROPDOWN_WIDTH,
} = {}) {
  const keepId = String(keep || "").replace(/"/g, "");
  const sel = keepId ? `[data-hr-dd-keep="${keepId}"]` : pickSelector;
  const bag = await page.evaluate(({ s, k }) => {
    const el = document.querySelector(s);
    const snap = (window.__hrDdHtml && k && window.__hrDdHtml[k]) || (el ? el.outerHTML : "") || "";
    if (!el) {
      return { tagged: null, snap };
    }
    document.querySelectorAll("[data-hr-ctl]").forEach((n) => n.removeAttribute("data-hr-ctl"));
    el.setAttribute("data-hr-ctl", "picked");
    const r = el.getBoundingClientRect();
    return {
      tagged: {
        label: (el.getAttribute("aria-label") || el.getAttribute("data-framer-name") || el.textContent || "")
          .trim().replace(/\s+/g, " ").slice(0, 64),
        box: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)],
        x: r.x + r.width / 2,
        y: r.y + r.height / 2,
      },
      snap,
    };
  }, { s: sel, k: keepId });
  const snapHtml = String(bag?.snap || "");
  const snapPair = snapHtml
    ? { status: "success", html: snapHtml }
    : null;
  if (!bag?.tagged) {
    if (!snapPair) return { found: false, reason: "no picked trigger" };
    return {
      found: true,
      triggerLabel: label || "Dropdown",
      triggerBox: [0, 0, 0, 0],
      items: [],
      rootSel: sel,
      navBox: [0, 0, 0, 0],
      closed: snapPair,
      open: snapPair,
      hoverConfirmed: false,
    };
  }
  const tagged = bag.tagged;
  if (!isDesktopDropdownViewport(viewportWidth)) {
    return { found: false, reason: "not a desktop viewport — hamburger stays 4.1-M" };
  }

  let snapped = await htmlFromSelector(page, serialize, sel);
  if (snapped.status !== "success" && snapPair) snapped = snapPair;
  if (snapped.status !== "success") {
    return { found: false, reason: snapped.error || "wrapper serialize failed" };
  }

  await movePointer(page, 5, 5, { steps: 10, label: "" });
  await page.waitForTimeout(500);
  const closedSet = new Set(await page.evaluate(visibleInteractiveLabels));

  await movePointer(page, tagged.x, tagged.y, { steps: 12, label: tagged.label || "menu" });
  await page.waitForTimeout(750);
  const openList = await page.evaluate(visibleInteractiveLabels);
  const newLabels = openList.filter((l) => !closedSet.has(l));

  if (!newLabels.length) {
    const closed = await htmlFromSelector(page, serialize, sel);
    return {
      found: true,
      triggerLabel: tagged.label || "Dropdown",
      triggerBox: tagged.box,
      items: [],
      rootSel: sel,
      navBox: tagged.box,
      closed: closed.status === "success" ? closed : snapped,
      open: snapped,
      hoverConfirmed: false,
    };
  }

  const info = await page.evaluate(resolveOpenPanel, { trigger: "picked", newLabels });
  let rootSel = sel;
  let navBox = tagged.box;
  if (info.err && !info.tooBig) {
    const closed = await htmlFromSelector(page, serialize, sel);
    return {
      found: true,
      triggerLabel: tagged.label || "Dropdown",
      triggerBox: tagged.box,
      items: info.items || [],
      rootSel: sel,
      navBox,
      closed: closed.status === "success" ? closed : snapped,
      open: snapped,
      hoverConfirmed: false,
    };
  }
  if (!info.err) {
    rootSel = "[data-hr-nav]";
    navBox = info.nav && info.nav.box;
  }
  if (info.tooBig) {
    const panel = await page.evaluate(markPanelRoot, info.items.length);
    if (panel) {
      rootSel = "[data-hr-panel]";
      navBox = panel.box;
    }
  }

  await movePointer(page, 5, 5, { steps: 10, label: "" });
  await page.waitForTimeout(500);
  let closed = await htmlFromSelector(page, serialize, rootSel);
  if (closed.status !== "success") closed = await htmlFromSelector(page, serialize, sel);
  if (closed.status !== "success") closed = snapped;

  await movePointer(page, tagged.x, tagged.y, { steps: 12, label: tagged.label || "menu" });
  await page.waitForTimeout(750);
  let open = await htmlFromSelector(page, serialize, rootSel);
  if (open.status !== "success") open = snapped;

  return {
    found: true,
    triggerLabel: info.triggerLabel || tagged.label || "Menu",
    triggerBox: info.triggerBox || tagged.box,
    items: info.items,
    rootSel,
    navBox,
    closed,
    open,
    hoverConfirmed: true,
  };
}
