// Component state capture — A/6, steps 4.0 – 4.4.
//
// Captures a live site's INTERACTIVE COMPONENTS as default/hover state pairs of
// Paper-ready inline-styled HTML. No GIFs: a state pair plus the measured style
// delta is smaller, readable by a vision model, and directly implementable.
//
// Two skills combine here:
//   • url-to-paper — scripts/serializer.js turns a live DOM subtree into
//     inline-styled HTML that Paper's write_html parses into real layers.
//   • hover-reel   — Playwright drives visible Chrome (same launch as Stage P).
//     Framer whileHover / variants do not fire under headless + reduced-motion
//     (prior-run white CTA stayed white instead of going black). --headless is
//     opt-in for CI only.
//
//   node capture-component-states.mjs --url <url> --kind nav|buttons|forms|faq|footer --out <dir>
//
// Output: <dir>/<page>/<kind>/NN-<component>-<state>.html  + manifest.json
//
// faq is the one kind whose defining state is not hover. An accordion's design
// information is collapsed vs EXPANDED — the answer copy, the row growth, the
// icon rotation — so it captures default / hover / open and measures the height
// delta that proves the row actually opened.

import fs from 'node:fs';
import path from 'node:path';
import { trim } from './trim-styles.mjs';
import { importSibling, siblingSkill } from './skill-paths.mjs';
import {
  assignDesignSystemTokens,
  DESKTOP_DROPDOWN_WIDTH,
  emptyKindManifest,
  htmlChanged,
  hamburgerKindHeight,
  interactiveRowMeta,
  isDesktopDropdownViewport,
  isDropdownKind,
  isHamburgerKind,
  kindCaptureWidth,
  looksLikeSectionId,
  normalizeCaptureKind,
  patternKey,
  slugify,
  styleDelta,
} from './component-state-utils.mjs';
import { installVisibleCursor, movePointer, showCursorLabel, showHud } from './visible-cursor.mjs';
import { prepareStateHtml } from './prepare-state-html.mjs';
import { captureFirstDropdownPair } from './dropdown-capture.mjs';
import { captureHamburgerPair } from './hamburger-capture.mjs';
import { writeDropdownPairFiles, writeFluidPairFiles } from './write-dropdown-pair.mjs';

const { launchOptions } = await importSibling('url-to-paper', 'scripts/chrome-path.mjs');

const SERIALIZER = siblingSkill('url-to-paper', 'scripts/serializer.js');
const arg = (n, d) => { const i = process.argv.indexOf(`--${n}`); return i > -1 ? process.argv[i + 1] : d; };
const has = (n) => process.argv.includes(`--${n}`);

const URL_ = arg('url');
const KIND = normalizeCaptureKind(arg('kind', 'nav'));
const OUT = path.resolve(arg('out', 'source-site/components'));
const PAGE = arg('page', '');
const SECTION_MANIFEST = arg('section-manifest', '');
const MAX = parseInt(arg('max', '40'), 10);
// Nav and footer links repeat one pattern — 2 representative states is the rule.
const MAX_STATES = parseInt(arg('max-states', '2'), 10);
const WIDTH = kindCaptureWidth(KIND, arg('width', isDropdownKind(KIND) ? String(DESKTOP_DROPDOWN_WIDTH) : isHamburgerKind(KIND) ? undefined : '1440'));
const HEIGHT = parseInt(arg('height', isDropdownKind(KIND) ? '1100' : isHamburgerKind(KIND) ? String(hamburgerKindHeight(KIND, WIDTH)) : '1000'), 10);
// Visible Chrome is the default. Headless + reduced-motion misses Framer
// whileHover (white pill → black fill became white-on-white).
const HEADLESS = has('headless');

if (!URL_) { console.error('need --url'); process.exit(1); }
if (!['nav', 'buttons', 'forms', 'faq', 'footer', 'dropdown', 'hamburger', 'nav-mobile', 'nav-mobile-768', 'nav-mobile-390'].includes(KIND)) {
  console.error(`--kind must be nav|buttons|forms|faq|footer|dropdown|nav-mobile[-768|-390], got ${KIND}`); process.exit(1);
}

const pageSlug = PAGE ? slugify(PAGE, 'page') : '';
const dir = path.join(OUT, ...(pageSlug ? [pageSlug] : []), KIND);
const ALLOW_FAQ = has('allow-faq');
const ALLOW_DROPDOWN = has('allow-dropdown');
const writeEmpty = (reason) => {
  fs.rmSync(dir, { recursive: true, force: true });
  fs.mkdirSync(dir, { recursive: true });
  const empty = emptyKindManifest({
    url: URL_, page: PAGE, pageSlug, kind: KIND, reason,
  });
  fs.writeFileSync(path.join(dir, 'manifest.json'), JSON.stringify(empty, null, 2));
  console.error(`${KIND}: skipped (${reason})`);
};
if (KIND === 'faq' && !ALLOW_FAQ) {
  writeEmpty('accordion capture is off — human decides if missing hover states belong on A/6');
  process.exit(0);
}
if (isDropdownKind(KIND) && !ALLOW_DROPDOWN) {
  writeEmpty('dropdown capture is off — do not hunt; pass --allow-dropdown when a hover-to-open panel exists');
  process.exit(0);
}

const { chromium } = await import('playwright');
fs.rmSync(dir, { recursive: true, force: true });
fs.mkdirSync(dir, { recursive: true });

let sectionManifest = [];
if (SECTION_MANIFEST) {
  try {
    const parsed = JSON.parse(fs.readFileSync(path.resolve(SECTION_MANIFEST), 'utf8'));
    sectionManifest = Array.isArray(parsed) ? parsed : (parsed.sections || []);
  } catch (error) {
    console.error(`section manifest ignored: ${error.message}`);
  }
}

const serializerSrc = fs.readFileSync(SERIALIZER, 'utf8');
const serialize = (page, sel) => page.evaluate(
  `(async () => { ${serializerSrc}\n return await fe(${JSON.stringify(sel)}); })()`);

const browser = await chromium.launch(launchOptions({ visible: !HEADLESS }));
const context = await browser.newContext({
  viewport: { width: WIDTH, height: HEIGHT },
  deviceScaleFactor: 2,
  // Settle entrance animations so the serializer does not drop opacity:0
  // nodes. Hover capture turns reduced-motion OFF below — Framer whileHover
  // is a no-op under prefers-reduced-motion (prior-run purple CTA).
  reducedMotion: 'reduce'
});
const page = await context.newPage();
if (!HEADLESS) await installVisibleCursor(page);
await page.goto(URL_, { waitUntil: 'domcontentloaded', timeout: 60000 });
try { await page.waitForLoadState('networkidle', { timeout: 15000 }); } catch { /* Framer rarely idles */ }
await page.waitForTimeout(3500);
await page.emulateMedia({ reducedMotion: 'no-preference' });
await page.waitForTimeout(400);
// Mount lazy below-fold content before target selection. Framer unmounts
// off-screen sections, so without a scroll pass the buttons/footer pools only
// see the hero (prior-run: Buy Now / section CTAs never mounted).
await page.evaluate(async () => {
  const h = document.documentElement.scrollHeight;
  const step = Math.max(400, Math.floor(innerHeight * 0.6));
  for (let y = 0; y <= h; y += step) {
    scrollTo(0, y);
    await new Promise((r) => setTimeout(r, 90));
  }
  scrollTo(0, 0);
});
await page.waitForTimeout(1200);
if (!HEADLESS) {
  await installVisibleCursor(page);
  await showHud(page, { phase: KIND, label: 'starting' });
}
console.error(`browser ${HEADLESS ? 'headless' : 'visible Chrome + cursor overlay'} · reduced-motion off for hover`);

// Real pointer over the painted box — locator.hover({ force: true }) can
// skip Framer's whileHover handlers. Measure the live pill fill (often an
// inner frame) so hover normalize does not restore the default white.
const livePaint = (sel) => page.evaluate((s) => {
  const el = document.querySelector(s);
  if (!el) return null;
  const opaque = (bg) => bg && bg !== 'transparent' && bg !== 'rgba(0, 0, 0, 0)';
  const rootR = el.getBoundingClientRect();
  let best = getComputedStyle(el).backgroundColor;
  let bestArea = opaque(best) ? rootR.width * rootR.height : 0;
  const walk = (n) => {
    const cs = getComputedStyle(n);
    const bg = cs.backgroundColor;
    if (opaque(bg)) {
      const r = n.getBoundingClientRect();
      const area = Math.min(r.width, rootR.width) * Math.min(r.height, rootR.height);
      if (area >= bestArea && r.width >= rootR.width * 0.55) {
        best = bg;
        bestArea = area;
      }
    }
    for (const c of n.children) walk(c);
  };
  walk(el);
  const text = [...el.querySelectorAll('p,h1,h2,h3,h4,h5,h6,span,div')]
    .find((n) => (n.textContent || '').trim()) || el;
  return {
    backgroundColor: best,
    color: getComputedStyle(text).color,
    hover: el.matches(':hover'),
  };
}, sel);

const pointerHover = async (sel, label = '', hud = null) => {
  if (hud && !HEADLESS) await showHud(page, hud);
  try { await page.locator(sel).scrollIntoViewIfNeeded({ timeout: 4000 }); } catch { /* fine */ }
  await page.waitForTimeout(200);
  const box = await page.locator(sel).boundingBox();
  if (box && box.width > 2 && box.height > 2) {
    await movePointer(page, box.x + box.width / 2, box.y + box.height / 2, {
      steps: 18,
      label,
    });
  } else {
    await showCursorLabel(page, label);
    await page.locator(sel).hover({ timeout: 5000 }).catch(() => {});
  }
};

const waitHoverPaint = async (sel, restBg, label = '') => {
  await pointerHover(sel, label);
  const start = Date.now();
  let last = await livePaint(sel);
  let prev = null;
  let stable = 0;
  while (Date.now() - start < 2000) {
    last = await livePaint(sel);
    const bg = last?.backgroundColor || null;
    if (bg && bg === prev) {
      stable += 1;
      if (stable >= 2 && bg !== restBg &&
          bg !== 'transparent' && bg !== 'rgba(0, 0, 0, 0)') {
        return last;
      }
    } else {
      stable = 0;
    }
    prev = bg;
    await page.waitForTimeout(150);
  }
  return last;
};

const hoverMeta = (it, paint) => ({
  ...it,
  backgroundColor: paint?.backgroundColor || it.backgroundColor,
  sourceBackground: paint?.backgroundColor || it.sourceBackground,
});

// Step 4.0 — the skip list, applied to every kind.
await page.evaluate(() => {
  // Floating fixed chrome ("Made in Framer", "Remix for free", template purchase
  // badges, cookie bars) is not part of the design being rebuilt. Marking it here
  // keeps it out of every selection below AND out of any container we serialize.
  const BADGE = /(made in framer|remix|buy template|purchase|get template|powered by|cookie|consent|accept)/i;
  let n = 0;
  for (const el of document.querySelectorAll('*')) {
    const cs = getComputedStyle(el);
    if (cs.position !== 'fixed' && cs.position !== 'sticky') continue;
    const r = el.getBoundingClientRect();
    if (r.width < 8 || r.height < 8) continue;
    const txt = (el.textContent || '').trim();
    const isBadge = BADGE.test(txt) && txt.length < 60;
    const floatsInCorner = r.width < 420 && r.height < 220 &&
      (r.bottom > innerHeight - 220 || r.top > innerHeight - 220);
    if (isBadge || (floatsInCorner && cs.position === 'fixed')) {
      el.setAttribute('data-hr-skip', '');
      n++;
    }
  }
  return n;
});
const skipped = await page.evaluate(() => [...document.querySelectorAll('[data-hr-skip]')]
  .map((e) => ((e.textContent || '').trim().slice(0, 40) || e.tagName.toLowerCase())));
console.error(`4.0 skip list: ${skipped.length} floating element(s)${skipped.length ? ' — ' + skipped.join(' | ') : ''}`);

const writeState = (name, html, meta = {}) => {
  const mode = meta.mode
    || (isDropdownKind(KIND) ? 'dropdown' : KIND === 'faq' ? 'accordion' : 'elements');
  const t = prepareStateHtml(trim(html), {
    kind: KIND,
    mode,
    rect: meta.rect || meta.captureRect,
    backgroundColor: meta.backgroundColor ?? meta.sourceBackground,
    ancestorBackground: meta.ancestorBackground,
    unlockOverflow: meta.unlockOverflow,
  });
  fs.writeFileSync(path.join(dir, `${name}.html`), t.html);
  return t.html;
};

if (isDropdownKind(KIND)) {
  if (!isDesktopDropdownViewport(WIDTH)) {
    await browser.close();
    writeEmpty('not a desktop viewport — hamburger stays 4.1-M');
    process.exit(0);
  }
  const pair = await captureFirstDropdownPair(page, {
    serialize,
    movePointer,
    viewportWidth: WIDTH,
  });
  if (!pair.found) {
    await browser.close();
    writeEmpty(pair.reason || 'no hover-to-open navbar panel');
    process.exit(0);
  }
  const sectionId = (sectionManifest.find((s) => looksLikeSectionId(s.id || s.name))?.id
    || sectionManifest[0]?.id
    || '01');
  writeDropdownPairFiles({
    dir,
    pair,
    url: URL_,
    page: PAGE || null,
    pageSlug: pageSlug || null,
    sectionId,
    skipped,
    viewportWidth: WIDTH,
    viewportHeight: HEIGHT,
  });
  await browser.close();
  console.error(`\nwrote ${dir} — closed | open (${pair.triggerLabel}) @ ${WIDTH}`);
  process.exit(0);
}

if (isHamburgerKind(KIND)) {
  const pair = await captureHamburgerPair(page, {
    serialize,
    movePointer,
    viewportWidth: WIDTH,
  });
  if (!pair.found) {
    await browser.close();
    writeEmpty(pair.reason || 'no hamburger at this width — do not invent');
    process.exit(0);
  }
  const row = interactiveRowMeta({ kind: KIND, viewportWidth: WIDTH });
  writeFluidPairFiles({
    dir,
    pair,
    url: URL_,
    page: PAGE || null,
    pageSlug: pageSlug || null,
    kind: KIND,
    mode: 'hamburger',
    sectionId: row.sid,
    skipped,
    viewportWidth: WIDTH,
    viewportHeight: HEIGHT,
  });
  await browser.close();
  console.error(`\nwrote ${dir} — closed | open (${row.sid} · ${row.token}) @ ${WIDTH}`);
  process.exit(0);
}

const isSkipped = (el) => el.closest('[data-hr-skip]');

// ---- target selection per kind -------------------------------------------
// Selection deliberately happens after Stage P has walked the full page. The
// browser is still the source of hover truth, but the page/section manifest is
// now available to prove which page and section each interaction belongs to.
const targets = await page.evaluate(({ kind, max, maxStates, sections }) => {
  const vh = innerHeight;
  const skip = (el) => !!el.closest('[data-hr-skip]');
  // Framer carousels keep a long strip of duplicate cards mounted off-canvas.
  // Their boxes have positive size, but they cannot be hovered by a user. Keep
  // off-viewport content vertically (we scroll each target into view later),
  // while excluding horizontal clones from every candidate pool.
  const visible = (el, r, cs) => r.width >= 16 && r.height >= 12 &&
    r.right > 0 && r.left < innerWidth &&
    parseFloat(cs.opacity) >= 0.05 && cs.visibility !== 'hidden' && cs.display !== 'none';
  const rect = (el) => { const r = el.getBoundingClientRect();
    return [Math.round(r.x), Math.round(r.y + scrollY), Math.round(r.width), Math.round(r.height)]; };
  const sectionFor = (r) => {
    if (Array.isArray(sections)) {
      let best = null; let overlap = 0;
      for (const s of sections) {
        const top = Number(s.top); const height = Number(s.height ?? s.h);
        if (!Number.isFinite(top) || !Number.isFinite(height)) continue;
        const amount = Math.max(0, Math.min(r[1] + r[3], top + height) - Math.max(r[1], top));
        if (amount > overlap) { overlap = amount; best = s.id || s.name || s.label || null; }
      }
      if (best) return best;
    }
    const owner = document.elementFromPoint(Math.max(1, r[0] + r[2] / 2),
      Math.max(1, Math.min(innerHeight - 1, r[1] - scrollY + r[3] / 2)));
    const container = owner?.closest('[data-section],section,main > *,header,footer');
    const heading = container?.querySelector('h1,h2,h3,h4,h5,h6');
    return container?.getAttribute('data-section') || container?.id ||
      heading?.textContent?.trim().replace(/\s+/g, ' ').slice(0, 64) || null;
  };
  const label = (el) => {
    const t = (el.getAttribute('aria-label') || el.textContent || '').trim().replace(/\s+/g, ' ');
    if (t) return t.slice(0, 64);
    const f = el.matches('input,textarea,select') ? el : el.querySelector('input,textarea,select');
    if (f) {
      const n = f.getAttribute('placeholder') || f.getAttribute('aria-label') ||
                f.getAttribute('name') || f.getAttribute('type') || f.tagName.toLowerCase();
      return String(n).trim().slice(0, 64);
    }
    const img = el.querySelector('img[alt]');
    if (img?.getAttribute('alt')) return img.getAttribute('alt').trim().slice(0, 64);
    return el.tagName.toLowerCase();
  };
  const paintedBg = (el) => {
    let n = el;
    while (n && n !== document.documentElement) {
      const bg = getComputedStyle(n).backgroundColor;
      if (bg && bg !== 'transparent' && bg !== 'rgba(0, 0, 0, 0)') return bg;
      n = n.parentElement;
    }
    return null;
  };
  // Framer pills often paint on an inner frame. The tagged wrapper is
  // transparent, so getComputedStyle(el) is not the fill we must restore.
  const ownPaint = (el) => {
    const opaque = (bg) => bg && bg !== 'transparent' && bg !== 'rgba(0, 0, 0, 0)';
    const rootR = el.getBoundingClientRect();
    let best = getComputedStyle(el).backgroundColor;
    let bestArea = opaque(best) ? rootR.width * rootR.height : 0;
    const walk = (n) => {
      const cs = getComputedStyle(n);
      const bg = cs.backgroundColor;
      if (opaque(bg)) {
        const r = n.getBoundingClientRect();
        const area = Math.min(r.width, rootR.width) * Math.min(r.height, rootR.height);
        if (area >= bestArea && r.width >= rootR.width * 0.55) {
          best = bg;
          bestArea = area;
        }
      }
      for (const c of n.children) walk(c);
    };
    walk(el);
    return best;
  };
  const paintRoot = (el) => {
    const fill = ownPaint(el);
    let best = el;
    let n = el;
    for (let i = 0; i < 6 && n.parentElement; i++) {
      const parent = n.parentElement;
      const pr = parent.getBoundingClientRect();
      const er = el.getBoundingClientRect();
      if (pr.width > Math.max(er.width * 1.85, 560) || pr.height > er.height * 2.4) break;
      const pf = ownPaint(parent);
      if (pf && fill && pf === fill && pr.width >= er.width * 0.92) {
        best = parent;
        n = parent;
      } else break;
    }
    return best;
  };
  // The element's own fill is not the band. A white pill on a purple
  // section recorded white and vanished on the review card (prior-run).
  // Prefer the nearest full-width painted ancestor.
  const bandBg = (el) => {
    let n = el?.parentElement;
    while (n && n !== document.documentElement) {
      const r = n.getBoundingClientRect();
      const bg = getComputedStyle(n).backgroundColor;
      if (r.width >= innerWidth * 0.72 && bg && bg !== 'transparent' && bg !== 'rgba(0, 0, 0, 0)') return bg;
      n = n.parentElement;
    }
    return paintedBg(el?.parentElement);
  };
  const outermost = (list) => list.filter((e) => !list.some((o) => o !== e && o.contains(e)));
  const compact = (el) => {
    const r = el.getBoundingClientRect();
    return r.width >= 180 && r.height >= 28 && r.height <= 260 && r.width <= innerWidth * 1.15;
  };
  const linkCount = (el) => [...el.querySelectorAll('a,button,[role=button]')].filter((a) => !skip(a)).length;

  // Rules are allowed to express hover without setting cursor:pointer. Keep a
  // cheap selector inventory so those controls enter the button pool as well.
  const hoverSelectors = [];
  const collectRules = (rules) => {
    for (const rule of rules || []) {
      if (rule.selectorText?.includes(':hover')) hoverSelectors.push(rule.selectorText);
      if (rule.cssRules) { try { collectRules(rule.cssRules); } catch { /* cross-origin sheet */ } }
    }
  };
  for (const sheet of document.styleSheets) { try { collectRules(sheet.cssRules); } catch { /* cross-origin sheet */ } }
  const hasHoverRule = (el) => hoverSelectors.some((selector) => {
    const candidates = [selector.replace(/:hover\b/g, ''), selector.replace(/:hover\b/g, ':not(*)')];
    return candidates.some((candidate) => { try { return candidate.trim() && el.matches(candidate); } catch { return false; } });
  });
  const interactive = (el) => {
    const cs = getComputedStyle(el);
    return cs.cursor === 'pointer' || el.tagName === 'A' || el.tagName === 'BUTTON' ||
      el.getAttribute('role') === 'button' || el.hasAttribute('onclick') ||
      (el.hasAttribute('tabindex') && el.getAttribute('tabindex') !== '-1') || hasHoverRule(el);
  };

  // A semantic header can contain an entire hero (prior-run does), so never
  // accept it merely because it is a <header>. Prefer the compact descendant
  // that actually holds the navigation controls; use the large semantic root
  // only as a last-resort diagnostic fallback.
  const findRoot = (which) => {
    const semantic = which === 'nav'
      ? [...document.querySelectorAll('nav,[role=navigation]')]
      : [...document.querySelectorAll('footer')];
    const pool = [...new Set([...semantic, ...document.querySelectorAll('header,footer,nav,div,section,ul')])]
      .filter((el) => !skip(el) && !el.closest('[data-hr-skip]'));
    const scored = pool.map((el) => {
      const r = el.getBoundingClientRect();
      const links = linkCount(el);
      const top = r.top + scrollY;
      const bottom = top + r.height;
      const nearTop = top < 260;
      const nearBottom = bottom > document.documentElement.scrollHeight - 260;
      const semanticBonus = semantic.includes(el) ? 18 : 0;
      const locationBonus = which === 'nav' ? (nearTop ? 22 : 0) : (nearBottom ? 22 : 0);
      const onExpectedEdge = which === 'nav' ? nearTop : nearBottom;
      return { el, links, onExpectedEdge, score: links * 4 + semanticBonus + locationBonus - (compact(el) ? 0 : 45) };
    }).filter((x) => x.onExpectedEdge && x.links >= (which === 'nav' ? 2 : 3) && (compact(x.el) || semantic.includes(x.el)))
      .sort((a, b) => b.score - a.score || a.el.getBoundingClientRect().height - b.el.getBoundingClientRect().height);
    const first = scored[0]?.el || null;
    if (!first) return null;
    if (compact(first)) return first;
    const descendants = [...first.querySelectorAll('nav,div,section,ul')]
      .filter((el) => !skip(el) && compact(el) && linkCount(el) >= (which === 'nav' ? 2 : 3))
      .sort((a, b) => linkCount(b) - linkCount(a) || a.getBoundingClientRect().height - b.getBoundingClientRect().height);
    return descendants[0] || first;
  };
  const navRoot = findRoot('nav');
  const footerRoot = findRoot('footer');
  const chromeRoots = [navRoot, footerRoot].filter(Boolean);
  chromeRoots.forEach((root) => root.setAttribute('data-hr-chrome-root', ''));
  const rootMeta = (root) => ({
    tag: root.tagName.toLowerCase(), rect: rect(root),
    backgroundColor: getComputedStyle(root).backgroundColor,
    ancestorBackground: paintedBg(root),
    sectionLabel: sectionFor(rect(root)),
  });

  const isSolid = (cs) => {
    const bg = cs.backgroundColor;
    return bg && bg !== 'transparent' && bg !== 'rgba(0, 0, 0, 0)';
  };
  const isPillCta = (el, r, cs) => {
    const radius = Math.max(parseFloat(cs.borderTopLeftRadius) || 0, parseFloat(cs.borderBottomLeftRadius) || 0);
    const border = Math.max(parseFloat(cs.borderTopWidth) || 0, parseFloat(cs.borderLeftWidth) || 0);
    const pill = radius >= 8 && r.height >= 32 && r.height <= 88 && r.width >= 72 && r.width <= 520;
    // Ghost pills (Hire An Expert) have a stroke and no fill. Solid-only
    // dropped them from the 1600 buttons pass.
    return pill && (isSolid(cs) || border >= 1);
  };

  // -- nav / footer: serialize the LINKS, not the bar or the whole footer.
  // Container mode imported a 1600×89 navbar and a 1320×182 footer block
  // (prior-run). 4.1 / 4.4 are link pairs. Pill CTAs in that chrome belong
  // in --kind buttons (header trial, footer-band yellow).
  if (kind === 'nav' || kind === 'footer') {
    const root = kind === 'nav' ? navRoot : footerRoot;
    if (!root) return { mode: 'empty', reason: `no ${kind} container found`, items: [] };
    const inner = [...root.querySelectorAll('*')].filter((el) => {
      if (skip(el)) return false;
      const r = el.getBoundingClientRect(); const cs = getComputedStyle(el);
      if (!visible(el, r, cs) || !interactive(el) || r.width > 700) return false;
      if (isPillCta(el, r, cs)) return false;
      return true;
    });
    const compactLinks = outermost(inner).filter((el) => el.getBoundingClientRect().height <= 48);
    const pool = compactLinks.length >= 2 ? compactLinks : outermost(inner);
    const patternOf = (el) => {
      const r = el.getBoundingClientRect(); const cs = getComputedStyle(el);
      const radius = Math.round(parseFloat(cs.borderTopLeftRadius) || 0);
      return [el.tagName, isSolid(cs) ? 'bg' : 'plain', radius > 8 ? 'pill' : 'flat', Math.round(r.height / 8)].join('|');
    };
    const byPattern = new Map();
    for (const el of pool) {
      const key = patternOf(el); if (!byPattern.has(key)) byPattern.set(key, []); byPattern.get(key).push(el);
    }
    const items = [...byPattern.values()].sort((a, b) => b.length - a.length).flat().slice(0, maxStates);
    items.forEach((el, i) => el.setAttribute('data-hr-item', String(i)));
    return { mode: 'elements', root: rootMeta(root), items: items.map((el, i) => ({
      i, label: label(el), rect: rect(el), sectionLabel: sectionFor(rect(el)),
      sourceBackground: ownPaint(el), ancestorBackground: bandBg(el),
    })), coverage: {
      // --max-states is the 4.1/4.4 rule, not a truncated pool. A/7 fails on
      // truncated:true, so the unused link patterns stay in patternPool only.
      candidateCount: items.length, selectedCount: items.length, truncated: false,
      patternPool: pool.length, maxStates,
      sections: [...new Set(items.map((el) => sectionFor(rect(el))).filter(Boolean))],
    } };
  }

  // -- accordion kind: rows that OPEN, captured collapsed + expanded
  if (kind === 'faq') {
    const semantic = [...document.querySelectorAll('details,[aria-expanded],[data-state]')]
      .filter((el) => !skip(el) && visible(el, el.getBoundingClientRect(), getComputedStyle(el)) && el.getBoundingClientRect().width > 200);
    let faqSection = null;
    const head = [...document.querySelectorAll('h1,h2,h3,h4,h5')]
      .find((e) => /faq|frequently asked|have any question|common question/i.test((e.textContent || '').trim()));
    if (head) {
      let s = head;
      for (let i = 0; i < 8 && s.parentElement; i++) { s = s.parentElement; if (s.getBoundingClientRect().height > 400) break; }
      faqSection = s;
    }
    const rowish = [...document.querySelectorAll('div,li,section,article,button')].filter((el) => {
      if (skip(el)) return false;
      const r = el.getBoundingClientRect(); const cs = getComputedStyle(el);
      if (!visible(el, r, cs) || cs.cursor !== 'pointer' || r.width < 240 || r.height < 28 || r.height > 800) return false;
      const t = (el.textContent || '').trim(); return t.length >= 8 && t.length <= 400;
    });
    const groups = new Map();
    for (const el of outermost(rowish)) { const r = el.getBoundingClientRect(); const key = `${Math.round(r.width)}`; if (!groups.has(key)) groups.set(key, []); groups.get(key).push(el); }
    const scored = [...groups.values()].map((g) => {
      const inSection = faqSection && g.every((e) => faqSection.contains(e));
      const questionish = g.filter((e) => /\?\s*$/.test((e.textContent || '').trim())).length;
      // FAQ rows repeat down the page. A carousel repeats across one horizontal
      // lane, so it must not be mistaken for an accordion just because its
      // cloned cards share a pointer cursor and dimensions.
      const verticalLanes = new Set(g.map((e) => Math.round(e.getBoundingClientRect().top / 8))).size;
      return { g, verticalLanes, score: g.length + (inSection ? 8 : 0) + questionish * 2 };
    }).filter((s) => (s.g.length >= 2 || s.score >= 8) && (faqSection || s.verticalLanes >= 2))
      .sort((a, b) => b.score - a.score);
    let rows = scored.length ? scored[0].g : [];
    if (semantic.length) rows = outermost([...new Set([...semantic, ...rows])]);
    if (!rows.length) return { mode: 'empty', reason: 'no accordion/FAQ rows found', items: [] };
    rows.sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);
    const candidateCount = rows.length;
    // Repeating accordion rows share one component. Capture the first
    // representative — A/7 must not treat this as a truncated pool.
    rows = rows.slice(0, 1);
    rows.forEach((el, i) => el.setAttribute('data-hr-item', String(i)));
    return { mode: 'accordion', section: faqSection ? rootMeta(faqSection) : null,
      coverage: {
        candidateCount, selectedCount: rows.length, truncated: false,
        repeatingPattern: candidateCount > 1, patternCount: candidateCount,
      },
      items: rows.map((el, i) => ({
        i, label: label(el), rect: rect(el), sectionLabel: sectionFor(rect(el)),
        sourceBackground: ownPaint(el), ancestorBackground: paintedBg(el),
      })) };
  }

  // -- element kinds: many components, two states each
  const toItem = (el, sectionLabel) => ({
    el, label: label(el), rect: rect(el),
    sectionLabel: sectionLabel || sectionFor(rect(el)),
    sourceBackground: ownPaint(el),
    ancestorBackground: bandBg(el),
  });

  // 4.2 walks Stage P sections one by one. Deduping "Get 14 Days Free Trial"
  // by label×size across the page kept only the hero and dropped the purple
  // mid-page CTA and the yellow footer-band CTA (prior-run). Same label in
  // different sections is a different component. Do not scrape accordion-like
  // rows — the human flags missing hover states instead.
  if (kind === 'buttons') {
    const raw = [...document.querySelectorAll('*')].filter((el) => {
      if (skip(el) || el.matches('input,textarea,select')) return false;
      const r = el.getBoundingClientRect(); const cs = getComputedStyle(el);
      // Keep pill CTAs that live in nav chrome (header trial). Drop nav/footer
      // text links — those are 4.1 / 4.4.
      if (chromeRoots.some((root) => root.contains(el)) && !isPillCta(el, r, cs)) return false;
      if (!visible(el, r, cs) || r.width < 28 || r.height < 18 || r.width > 720 || r.height > 260 || !interactive(el)) return false;
      // Wide non-pill pointer rows are list/card heads, not CTAs.
      if (!isPillCta(el, r, cs) && r.width > 400) return false;
      const t = (el.getAttribute('aria-label') || el.textContent || '').trim();
      return t.length > 0 && t.length < 80;
    });
    const candidates = [];
    const seenEl = new Set();
    const takeLocal = (els, sectionLabel) => {
      const seen = new Set();
      for (const el of outermost(els)) {
        if (seenEl.has(el)) continue;
        const r = el.getBoundingClientRect();
      const key = label(el).toLowerCase().replace(/\s+/g, ' ');
      if (seen.has(key)) continue;
      seen.add(key);
      const root = paintRoot(el);
      // Two nested interactive elements (an <a> and its cursor:pointer parent)
      // can promote to the SAME paint root. Dedup on the root, not just the
      // raw element — otherwise identical-rect duplicates reach `unique` and
      // mutually "contain" each other, wiping the whole pool (prior-run).
      if (seenEl.has(root)) continue;
      seenEl.add(el);
      seenEl.add(root);
      candidates.push(toItem(root, sectionLabel));
      }
    };
    const walked = [];
    if (Array.isArray(sections) && sections.length) {
      for (const section of sections) {
        const top = Number(section.top);
        const height = Number(section.height ?? section.h);
        if (!Number.isFinite(top) || !Number.isFinite(height)) continue;
        const name = section.id || section.name || section.label || null;
        walked.push(name);
        const bot = top + height;
        takeLocal(raw.filter((el) => {
          const box = rect(el);
          const cy = box[1] + box[3] / 2;
          return cy >= top && cy < bot;
        }), name);
      }
      takeLocal(raw.filter((el) => !seenEl.has(el)), null);
    } else {
      takeLocal(raw, null);
    }
    // Strict containment: identical rects must not "contain" each other —
    // with j !== i two duplicate entries would otherwise both be dropped.
    const inside = (a, b) => (a[0] !== b[0] || a[1] !== b[1] || a[2] !== b[2] || a[3] !== b[3]) &&
      a[0] >= b[0] && a[1] >= b[1] &&
      a[0] + a[2] <= b[0] + b[2] && a[1] + a[3] <= b[1] + b[3];
    const unique = candidates.filter((c, i) =>
      !candidates.some((o, j) => j !== i && inside(c.rect, o.rect)));
    const items = unique.slice(0, max).map((candidate, i) => {
      candidate.el.setAttribute('data-hr-item', String(i));
      return { i, label: candidate.label, rect: candidate.rect, sectionLabel: candidate.sectionLabel,
        captureSelector: `[data-hr-item="${i}"]`, sourceBackground: candidate.sourceBackground,
        ancestorBackground: candidate.ancestorBackground };
    });
    if (!items.length) return { mode: 'empty', reason: `no ${kind} targets found`, items: [] };
    return { mode: 'elements', items, coverage: {
      candidateCount: unique.length, selectedCount: items.length,
      truncated: unique.length > items.length,
      sections: [...new Set(items.map((i) => i.sectionLabel).filter(Boolean))],
      walkedSections: walked.filter(Boolean),
    } };
  }

  let pool = [];
  if (kind === 'forms') {
    const fields = [...document.querySelectorAll('input,textarea,select')].filter((el) => {
      if (skip(el)) return false; const r = el.getBoundingClientRect(); const cs = getComputedStyle(el);
      return visible(el, r, cs) && r.height >= 24;
    });
    const wrapSmall = (el) => {
      const base = el.getBoundingClientRect(); let w = el;
      while (w.parentElement && w.parentElement !== document.body) {
        const r = w.parentElement.getBoundingClientRect();
        if (r.width > Math.max(base.width * 2.6, 520) || r.height > base.height * 3.6) break;
        w = w.parentElement;
      }
      return w;
    };
    pool = outermost([...new Set(fields.map(wrapSmall))]);
  }

  const seen = new Set(); const candidates = [];
  for (const el of outermost(pool)) {
    const r = el.getBoundingClientRect();
    const key = (sectionFor(rect(el)) || 'page') + '|' + label(el) + '|' + Math.round(r.width) + 'x' + Math.round(r.height);
    if (seen.has(key)) continue;
    seen.add(key);
    candidates.push(toItem(el, null));
  }
  const items = candidates.slice(0, max).map((candidate, i) => {
    candidate.el.setAttribute('data-hr-item', String(i));
    return { i, label: candidate.label, rect: candidate.rect, sectionLabel: candidate.sectionLabel,
      captureSelector: `[data-hr-item="${i}"]`, sourceBackground: candidate.sourceBackground,
      ancestorBackground: candidate.ancestorBackground };
  });
  if (!items.length) return { mode: 'empty', reason: `no ${kind} targets found`, items: [] };
  return { mode: 'elements', items, coverage: { candidateCount: candidates.length, selectedCount: items.length, truncated: candidates.length > items.length } };
}, { kind: KIND, max: MAX, maxStates: MAX_STATES, sections: sectionManifest });

const stateSlug = (s, i) => `${String(i).padStart(2, '0')}-${String(s || 'item').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 32) || 'item'}`;

// "hover changed = true" is not evidence — a subtle tint reads as identical in
// the artboard. Diff the complete serialized declaration stream so a child
// color/pseudo-element change is carried into the implementation spec too.
const written = [];

if (targets.mode === 'container') {
  console.error(`${KIND}: ${targets.root.tag} ${targets.root.rect.join('x')} · ${targets.items.length} control(s)`);
  // Scroll the container into view BEFORE the default capture. Hovering a child
  // auto-scrolls, so without this the default is serialized while the component
  // is still off-screen with its reveal children at opacity:0 (which the
  // serializer drops) — producing a default far smaller than every hover state.
  await page.locator('[data-hr-root]').scrollIntoViewIfNeeded({ timeout: 8000 }).catch(() => {});
  await page.waitForTimeout(900);
  await movePointer(page, 5, 5, { steps: 10, label: '' });
  await page.waitForTimeout(700);
  const def = await serialize(page, '[data-hr-root]');
  if (def.status !== 'success') { console.error('default serialize failed'); await browser.close(); process.exit(3); }
  const n0 = writeState('00-default', def.html, targets.root);
  written.push({ component: KIND, state: 'default', file: '00-default.html', bytes: n0.length,
                 ancestorBackground: targets.root?.ancestorBackground || null });
  console.error(`  default${' '.repeat(18)}${n0.length} bytes`);

  for (const it of targets.items) {
    await movePointer(page, 5, 5, { steps: 10, label: '' });
    await page.waitForTimeout(300);
    await pointerHover(`[data-hr-item="${it.i}"]`, it.label, {
      phase: KIND, current: it.i + 1, total: targets.items.length, label: it.label,
    });
    await page.waitForTimeout(800);
    const ok = await page.evaluate((i) => {
      const el = document.querySelector(`[data-hr-item="${i}"]`);
      return !!el && el.matches(':hover');
    }, it.i);
    const s = await serialize(page, '[data-hr-root]');
    if (s.status !== 'success') { console.error(`  ${it.label}: FAILED`); continue; }
    const name = stateSlug(it.label, it.i + 1);
    const normalized = writeState(name, s.html, targets.root);
    const defaultNormalized = prepareStateHtml(trim(def.html), targets.root).html;
    const changed = htmlChanged(normalized, defaultNormalized);
    written.push({ component: KIND, state: 'hover', label: it.label, index: it.i,
                   file: `${name}.html`, bytes: normalized.length, hoverConfirmed: ok, changed,
                   ancestorBackground: it.ancestorBackground || targets.root?.ancestorBackground || null,
                   sectionLabel: it.sectionLabel, rect: it.rect,
                   styleDelta: changed ? styleDelta(defaultNormalized, normalized) : [] });
    console.error(`  hover ${it.label.padEnd(22).slice(0, 22)} ${String(normalized.length).padStart(6)} bytes  :hover=${ok}  changed=${changed}`);
  }
} else if (targets.mode === 'accordion') {
  console.error(`${KIND}: ${targets.items.length} accordion row(s)` +
    (targets.section ? ` in ${targets.section.tag} ${targets.section.rect.join('x')}` : ' (no FAQ heading — matched by repeated pointer rows)'));

  // Height before/after the click is the proof the row opened. Without it a
  // silently-inert click writes an "open" state identical to the default and
  // nothing downstream can tell.
  const heights = (i) => page.evaluate((idx) => {
    const el = document.querySelector(`[data-hr-item="${idx}"]`);
    if (!el) return null;
    const chain = [el, el.parentElement, el.parentElement?.parentElement].filter(Boolean);
    return chain.map((e) => Math.round(e.getBoundingClientRect().height));
  }, i);
  // Playwright clicks the box centre. On an already-open row that is the
  // answer body, which often is not the toggle. Hit the compact question head.
  const clickHead = async (sel) => {
    const box = await page.evaluate((s) => {
      const el = document.querySelector(s);
      if (!el) return null;
      const head = [...el.querySelectorAll('*')].find((n) => {
        const r = n.getBoundingClientRect();
        const cs = getComputedStyle(n);
        return (cs.cursor === 'pointer' || n.tagName === 'BUTTON') &&
          r.height >= 24 && r.height <= 80 && r.width > 160;
      });
      const r = (head || el).getBoundingClientRect();
      return { x: r.x + Math.min(36, r.width / 2), y: r.y + Math.min(18, r.height / 2) };
    }, sel);
    if (!box) {
      await page.locator(sel).click({ force: true, timeout: 5000 }).catch(() => {});
      return;
    }
    await page.mouse.click(box.x, box.y);
  };

  for (const it of targets.items) {
    const sel = `[data-hr-item="${it.i}"]`;
    const base = stateSlug(it.label, it.i);
    await movePointer(page, 5, 5, { steps: 10, label: '' });
    await page.waitForTimeout(250);
    try { await page.locator(sel).scrollIntoViewIfNeeded({ timeout: 4000 }); } catch { /* fine */ }
    await page.waitForTimeout(400);

    // An already-open first row (Cashless Payment) serializes as the answer
    // and then fails the 8px growth gate. Collapse it so default is closed.
    const alreadyOpen = await page.evaluate((s) => {
      const el = document.querySelector(s);
      if (!el) return false;
      return el.getBoundingClientRect().height > 100 ||
        el.hasAttribute('open') || el.getAttribute('aria-expanded') === 'true' ||
        !!el.querySelector('[aria-expanded="true"],[open]');
    }, sel);
    if (alreadyOpen) {
      await clickHead(sel);
      await page.waitForTimeout(800);
    }
    const stuckOpen = alreadyOpen && await page.evaluate((s) =>
      (document.querySelector(s)?.getBoundingClientRect().height || 0) > 100, sel);
    const headMeta = stuckOpen ? await page.evaluate((s) => {
      const el = document.querySelector(s);
      if (!el) return null;
      const head = [...el.querySelectorAll('*')].find((n) => {
        const r = n.getBoundingClientRect();
        return r.height >= 24 && r.height <= 80 && r.width > 200;
      });
      if (!head) return null;
      document.querySelectorAll('[data-hr-head]').forEach((n) => n.removeAttribute('data-hr-head'));
      head.setAttribute('data-hr-head', '');
      const r = head.getBoundingClientRect();
      return { h: Math.round(r.height), label: (head.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 64) };
    }, sel) : null;

    const d = await serialize(page, headMeta ? '[data-hr-head]' : sel);
    if (d.status !== 'success') { console.error(`  ${it.label}: default FAILED`); continue; }
    const hBefore = stuckOpen && headMeta ? [headMeta.h] : await heights(it.i);

    // hover — accordion rows often tint or shift their icon
    const hoverSel = headMeta ? '[data-hr-head]' : sel;
    await pointerHover(hoverSel, it.label, {
      phase: KIND, current: it.i + 1, total: targets.items.length, label: it.label,
    });
    await page.waitForTimeout(800);
    const hoverConfirmed = await page.evaluate((s) => {
      const el = document.querySelector(s);
      return !!el && el.matches(':hover');
    }, hoverSel);
    const h = await serialize(page, hoverSel);
    const hoverChanged = h.status === 'success' && trim(h.html) !== trim(d.html);
    const hoverDelta = hoverChanged ? styleDelta(d.html, h.html) : [];

    // open
    if (!stuckOpen) {
      await clickHead(sel);
      await page.waitForTimeout(900);
    }
    const hAfter = await heights(it.i);
    const deltas = (hAfter || []).map((v, k) => v - ((hBefore || [])[k] ?? v));
    const grewAt = deltas.findIndex((v) => v >= 8);
    const opened = grewAt > -1 || await page.evaluate((s) => {
      const el = document.querySelector(s);
      return !!el && (el.hasAttribute('open') || el.getAttribute('aria-expanded') === 'true' ||
                      el.querySelector('[aria-expanded="true"],[open]') !== null);
    }, sel);

    // Serialize the INNERMOST ancestor that grew ≥8px. The last/outermost
    // growing wrapper often includes sibling rows (prior-run Easy Loan).
    // The answer copy still usually lives one wrapper above the clicked row.
    const openHtml = grewAt > 0
      ? await page.evaluate((args) => {
          const el = document.querySelector(args.s);
          let t = el;
          for (let k = 0; k < args.up; k++) t = t.parentElement || t;
          t.setAttribute('data-hr-open', '');
          return true;
        }, { s: sel, up: grewAt }).then(() => serialize(page, '[data-hr-open]'))
      : await serialize(page, sel);

    if (openHtml.status === 'success') {
      const defaultHtml = writeState(`${base}-default`, d.html, it);
      const hoverHtml = h.status === 'success' ? writeState(`${base}-hover`, h.html, it) : null;
      const openRect = await page.evaluate(() => {
        const el = document.querySelector('[data-hr-open]');
        if (!el) return null;
        const r = el.getBoundingClientRect();
        return [Math.round(r.x), Math.round(r.y + scrollY), Math.round(r.width), Math.round(r.height)];
      });
      const measuredOpenH = Math.max(
        openRect?.[3] || 0,
        hAfter?.[0] || 0,
        (hBefore?.[0] || 0) + (deltas[0] || 0),
        it.rect?.[3] || 0,
      ) + 24;
      const openBox = [
        (openRect || it.rect)[0], (openRect || it.rect)[1],
        (openRect || it.rect)[2], measuredOpenH,
      ];
      const openHtmlNormalized = writeState(`${base}-open`, openHtml.html, {
        ...it, rect: openBox, unlockOverflow: true,
      });
      const bd = defaultHtml.length;
      const bo = openHtmlNormalized.length;
      const openChanged = htmlChanged(openHtmlNormalized, defaultHtml);
      const sectionId = /^\d{2}$/.test(String(it.sectionLabel || '')) ? it.sectionLabel : null;
      const rowLabel = (stuckOpen && headMeta?.label) ? headMeta.label : it.label;
      written.push({ component: sectionId ? `${sectionId} · ${rowLabel}` : rowLabel, index: it.i, rect: it.rect,
                     defaultFile: `${base}-default.html`,
                     hoverFile: h.status === 'success' ? `${base}-hover.html` : null,
                     openFile: `${base}-open.html`,
                     heightBefore: hBefore?.[0] ?? null, heightAfter: hAfter?.[0] ?? null,
                     heightDelta: deltas.length ? Math.max(...deltas) : null, openWrapperLevel: Math.max(grewAt, 0),
                     bytes: bd + bo, hoverConfirmed, hoverChanged, hoverDelta, opened, changed: openChanged,
                     ancestorBackground: it.ancestorBackground || targets.section?.ancestorBackground || null,
                     sectionId, sectionLabel: it.sectionLabel,
                     repeatingPattern: !!targets.coverage?.repeatingPattern,
                     patternCount: targets.coverage?.patternCount || 1,
                     styleDelta: openChanged ? styleDelta(defaultHtml, openHtmlNormalized) : [] });
      console.error(`  ${it.label.padEnd(34).slice(0, 34)} ${String(bd + bo).padStart(6)} bytes  ` +
        `h ${hBefore?.[0]}→${hAfter?.[0]}  opened=${opened}  hoverΔ=${hoverChanged}`);
    } else {
      console.error(`  ${it.label}: open serialize FAILED`);
    }

    // Collapse again so the next row starts from a clean default.
    await page.evaluate(() => document.querySelectorAll('[data-hr-open]')
      .forEach((e) => e.removeAttribute('data-hr-open')));
    if (opened) {
      await clickHead(sel);
      await page.waitForTimeout(700);
    }
  }
} else {
  console.error(`${KIND}: ${targets.items.length} component(s)`);
  for (const it of targets.items) {
    const sel = `[data-hr-item="${it.i}"]`;
    await movePointer(page, 5, 5, { steps: 10, label: '' });
    await page.waitForTimeout(250);
    try { await page.locator(sel).scrollIntoViewIfNeeded({ timeout: 4000 }); } catch { /* fine */ }
    await page.waitForTimeout(300);
    const d0 = await serialize(page, sel);
    if (d0.status !== 'success') { console.error(`  ${it.label}: default FAILED`); continue; }
    const restPaint = await livePaint(sel);
    const fillOk = (html, bg) => {
      if (!bg || !html) return true;
      const compact = (s) => String(s).replace(/\s+/g, '');
      return compact(html).includes(compact(bg));
    };
    let d = d0;
    if (!fillOk(d.html, restPaint?.backgroundColor || it.sourceBackground)) {
      const again = await serialize(page, sel);
      if (again.status === 'success') d = again;
    }
    if (!HEADLESS) {
      await showHud(page, {
        phase: KIND, current: it.i + 1, total: targets.items.length, label: it.label,
      });
    }
    const paint = await waitHoverPaint(sel, restPaint?.backgroundColor || it.sourceBackground, it.label);
    const ok = !!(paint?.hover);
    let h = await serialize(page, sel);
    if (h.status !== 'success') { console.error(`  ${it.label}: hover FAILED`); continue; }
    if (!fillOk(h.html, paint?.backgroundColor || restPaint?.backgroundColor)) {
      const again = await serialize(page, sel);
      if (again.status === 'success') h = again;
    }
    const base = stateSlug(it.label, it.i);
    const hm = hoverMeta(it, paint);
    const defaultHtml = writeState(`${base}-default`, d.html, it);
    const hoverHtml = writeState(`${base}-hover`, h.html, hm);
    const bd = defaultHtml.length;
    const bh = hoverHtml.length;
    const changed = htmlChanged(hoverHtml, defaultHtml);
    const sectionId = /^\d{2}$/.test(String(it.sectionLabel || '')) ? it.sectionLabel : null;
    const componentName = sectionId ? `${sectionId} · ${it.label}` : it.label;
    written.push({ component: componentName, index: it.i, rect: it.rect,
                   defaultFile: `${base}-default.html`, hoverFile: `${base}-hover.html`,
                   bytes: bd + bh, hoverConfirmed: ok, changed,
                   sourceBackground: it.sourceBackground || null,
                   hoverBackground: paint?.backgroundColor || null,
                   hoverColor: paint?.color || null,
                   ancestorBackground: it.ancestorBackground || null,
                   sectionId, sectionLabel: it.sectionLabel,
                   styleDelta: changed ? styleDelta(defaultHtml, hoverHtml) : [] });
    console.error(`  ${it.label.padEnd(26).slice(0, 26)} ${String(bd + bh).padStart(6)} bytes  :hover=${ok}  changed=${changed}` +
      (paint?.backgroundColor ? `  fill ${restPaint?.backgroundColor || it.sourceBackground}→${paint.backgroundColor}` : ''));
  }
}

await browser.close();
const tokens = assignDesignSystemTokens(written, { kind: KIND });
written.forEach((state, i) => {
  state.patternKey = patternKey(state, { kind: KIND });
  state.token = tokens[i];
});
const manifest = { url: URL_, page: PAGE || null, pageSlug: pageSlug || null,
                   kind: KIND, mode: targets.mode, status: targets.mode === 'empty' ? 'empty' : 'ok',
                   reason: targets.reason || null, capturedAt: new Date().toISOString(),
                   skipped, root: targets.root || null, coverage: targets.coverage || {
                     candidateCount: targets.items?.length || 0, selectedCount: targets.items?.length || 0,
                     truncated: false, sections: [...new Set((targets.items || []).map((i) => i.sectionLabel).filter(Boolean))],
                   }, states: written };
fs.writeFileSync(path.join(dir, 'manifest.json'), JSON.stringify(manifest, null, 2));

const noChange = written.filter((w) => w.changed === false).length;
console.error(targets.mode === 'empty' ? `\n${KIND}: no targets — recorded empty manifest (${targets.reason})` : `\nwrote ${dir} — ${written.length} state file(s)` +
  (noChange ? `; ${noChange} with NO hover delta (recorded, not dropped)` : ''));
