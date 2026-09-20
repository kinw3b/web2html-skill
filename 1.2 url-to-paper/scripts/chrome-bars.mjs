// Compact live chrome (top bar + nav) for Framer pages that have no
// <header>/<nav>. detect-sections drops those bars from the content walk,
// so official 1.2 would otherwise omit them from layer-ids.json.
//
// Serialize each bar only — never climb to the page shell (max height 220 /
// 28% viewport, top ≤ 160). Prefixes 00- / 0a- keep content ids at 01+.
// Write the HTML onto FRAME Navigation (relative). Prepend the same compact
// stack onto home-desktop only when that lander has no navbar. Never dump
// the live Framer page/hero shell onto a lander (Pitfall #110 / #168).

import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { serializeSelector } from "./paper-walk.mjs";
import { ensureRelativeFlow } from "./park-nav.mjs";

export const CHROME_SLUGS = ["header", "nav"];
export const CHROME_PREFIXES = ["00-", "0a-"];
export const MAX_CHROME_HEIGHT = 220;
export const MAX_CHROME_TOP = 160;
export const NAVBAR_NAME_RE =
  /^(header|nav|navbar|site-chrome|chrome)\b|^(00|0a)[- ·]|pc-0[0a]([-.]|$)/i;

export function isCompactBar({
  width,
  height,
  top,
  viewportWidth = 1600,
  viewportHeight = 900,
} = {}) {
  const maxH = Math.min(MAX_CHROME_HEIGHT, Math.round(Number(viewportHeight) * 0.28));
  return Number(width) >= Number(viewportWidth) * 0.8
    && Number(height) >= 32
    && Number(height) <= maxH
    && Number(top) <= MAX_CHROME_TOP;
}

export function isPhoneLeafText(text) {
  const t = String(text || "").replace(/\s+/g, " ").trim();
  return /^\(?\d{3}\)?[\s.-]*\d{3}/.test(t) && t.length <= 24;
}

/** Playwright `page.evaluate` body — stamps selectors, never climbs to body. */
export function findChromeBarsInPage() {
  const maxH = Math.min(220, Math.round(window.innerHeight * 0.28));
  const compact = (el) => {
    if (!el) return false;
    const r = el.getBoundingClientRect();
    const top = r.top + window.scrollY;
    return r.width >= window.innerWidth * 0.8 && r.height >= 32 && r.height <= maxH && top <= 160;
  };
  const climb = (start) => {
    let el = start;
    let best = null;
    for (let i = 0; i < 16 && el?.parentElement && el.parentElement !== document.body; i += 1) {
      el = el.parentElement;
      if (compact(el)) best = el;
    }
    return best;
  };
  const bars = [];
  const seen = new Set();
  const add = (el, name) => {
    if (!el || seen.has(el)) return;
    seen.add(el);
    const attr = `data-x-paper-chrome-${bars.length}`;
    el.setAttribute(attr, "1");
    const r = el.getBoundingClientRect();
    bars.push({
      selector: `[${attr}='1']`,
      name,
      w: Math.round(r.width),
      h: Math.round(r.height),
      top: Math.round(r.top + window.scrollY),
      chrome: true,
    });
  };
  // Framer variants: desktop Header/Desktop, compact Tablet/Phone/Mobile.
  // "Top Bar" is the older template name. Pick the first compact named bar
  // so 768/390 logo+hamburger still serialize when nav links are hidden.
  const namedChrome = ["Top Bar", "Header", "Tablet", "Phone", "Mobile", "Desktop"];
  for (const name of namedChrome) {
    const el = document.querySelector(`[data-framer-name="${name}"]`);
    if (compact(el)) {
      add(el, "header");
      break;
    }
  }
  if (!bars.length) {
    const phone = [...document.querySelectorAll("p, span, a")].find((el) => {
      const t = (el.textContent || "").replace(/\s+/g, " ").trim();
      return /^\(?\d{3}\)?[\s.-]*\d{3}/.test(t) && t.length <= 24;
    });
    add(climb(phone), "header");
  }
  if (!bars.length) {
    const navLabel = /^(home|about|services|pricing|work|contact|trabajos|servicios|precios|nosotros|hablemos)$/i;
    const navSeed = [...document.querySelectorAll("a, button")].find((el) =>
      navLabel.test((el.textContent || "").replace(/\s+/g, " ").trim()),
    );
    add(climb(navSeed), "nav");
  }
  if (!bars.length) {
    const burger = document.querySelector(
      '[data-framer-name="Humburger"], [data-framer-name="Hamburger"], [data-framer-name="Button & Burger"]',
    );
    add(climb(burger), "nav");
  }
  if (!bars.length) {
    const logo = [...document.querySelectorAll('[data-framer-name="Logo"]')].find((el) => climb(el));
    add(climb(logo), "nav");
  }
  if (!bars.length) {
    const semantic = document.querySelector("header, nav, [role='navigation']");
    if (compact(semantic)) add(semantic, "nav");
    else add(climb(semantic), "nav");
  }
  return bars.filter((b) => b.selector);
}

export function chromeFragmentPath(outDir, slug) {
  return join(outDir, `00-${slug}.html`);
}

export function readChromeFragments(outDir) {
  const headerPath = chromeFragmentPath(outDir, "header");
  const navPath = chromeFragmentPath(outDir, "nav");
  return {
    header: existsSync(headerPath) ? readFileSync(headerPath, "utf8") : "",
    nav: existsSync(navPath) ? readFileSync(navPath, "utf8") : "",
  };
}

export function nodeLooksLikeNavbar(node = {}) {
  const name = String(node?.name || node?.textContent || "");
  if (NAVBAR_NAME_RE.test(name)) return true;
  const tag = String(node?.tag || node?.htmlTag || "").toLowerCase();
  if (tag === "header" || tag === "nav") return true;
  const compact = Number(node?.height) > 0 && Number(node.height) <= MAX_CHROME_HEIGHT;
  if (compact && /\b(logo|menu|burger|hamburger)\b/i.test(name) && !/\b(hero|section)\b/i.test(name)) {
    return true;
  }
  return false;
}

/** True when home-desktop already has compact chrome / header / nav. */
export function desktopLanderHasNavbar(nodes = []) {
  return (nodes || []).some((n) => nodeLooksLikeNavbar(n));
}

/** Stack 00-header + 00-nav for FRAME Navigation (relative, never Absolute). */
export function combineChromeHtml(headerHtml = "", navHtml = "") {
  const parts = [headerHtml, navHtml].map((h) => String(h || "").trim()).filter(Boolean);
  if (!parts.length) return "";
  const stacked = parts.map((html) => ensureRelativeFlow(html));
  if (stacked.length === 1) return stacked[0];
  return `<div layer-name="Navbar" style="display:flex;flex-direction:column;align-items:stretch;width:100%;position:relative;left:auto;top:auto;right:auto;bottom:auto;">${stacked.join("")}</div>`;
}

export async function serializeChromeBars(page, serializerSrc, {
  outDir,
  log = console.error,
  skip = false,
} = {}) {
  if (skip) return { bars: [], layerIds: [], files: [] };
  const bars = await page.evaluate(findChromeBarsInPage);
  if (!bars.length) {
    log("! no chrome/header found");
    return { bars, layerIds: [], files: [] };
  }
  const layerIds = [];
  const files = [];
  for (let c = 0; c < bars.length; c += 1) {
    const chrome = bars[c];
    const prefix = CHROME_PREFIXES[c] || `0${c}-`;
    const id = prefix.replace(/-$/, "");
    const slug = CHROME_SLUGS[c] || chrome.name;
    log(`chrome ${slug} ${chrome.w}×${chrome.h} → ${id} (content bands stay 01+)`);
    await page.evaluate((sel) => {
      document.querySelector(sel)?.scrollIntoView({ behavior: "instant", block: "start" });
    }, chrome.selector);
    try { await page.waitForTimeout(200); } catch { /* evaluate-only contexts */ }
    const result = await serializeSelector(page, serializerSrc, chrome.selector, {
      idPrefix: prefix,
    });
    if (result.status === "success" && result.html) {
      const file = chromeFragmentPath(outDir, slug);
      writeFileSync(file, result.html, "utf8");
      layerIds.push({ section: { id, slug }, ids: result.ids || [] });
      files.push(file);
      log(`  ✓ 00-${slug}  ${(result.html.length / 1024).toFixed(0)} KB`);
    } else {
      log(`  ! chrome ${slug}: ${result.error || "empty"}`);
    }
  }
  return { bars, layerIds, files };
}
