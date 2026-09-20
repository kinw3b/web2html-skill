// 1.3 light pass — mine source CSS :hover paint for pulled FRAME Buttons.
// No Playwright. Inline <style> plus linked stylesheets. Bare a:hover / button:hover
// is not a CTA recipe (Pitfall #33). Buttons still need paint, not a color tick.

import { readFileSync } from "node:fs";
import { join } from "node:path";

const WRITER = "author-button-hover.mjs";
const PAINT_PROPS = new Set([
  "background",
  "background-color",
  "background-image",
  "color",
  "-webkit-text-fill-color",
  "border",
  "border-color",
  "border-width",
  "border-style",
  "outline",
  "outline-color",
  "box-shadow",
  "opacity",
  "filter",
  "transition",
  "transition-duration",
  "transition-property",
  "transition-timing-function",
]);
const BUTTON_PAINT = /background|border|box-shadow|filter|opacity/i;

export { WRITER };

export function stripCssComments(css = "") {
  return String(css || "").replace(/\/\*[\s\S]*?\*\//g, "");
}

export function parseDeclarations(block = "") {
  const out = {};
  for (const part of String(block || "").split(";")) {
    const i = part.indexOf(":");
    if (i < 0) continue;
    const prop = part.slice(0, i).trim().toLowerCase();
    const value = part.slice(i + 1).trim();
    if (prop && value) out[prop] = value;
  }
  return out;
}

export function pickPaintDeclarations(decls = {}) {
  const keep = {};
  for (const [prop, value] of Object.entries(decls)) {
    if (PAINT_PROPS.has(prop) && value) keep[prop] = value;
  }
  return keep;
}

function sliceBlock(css, braceIndex) {
  let depth = 0;
  for (let i = braceIndex; i < css.length; i += 1) {
    if (css[i] === "{") depth += 1;
    else if (css[i] === "}") {
      depth -= 1;
      if (depth === 0) return [css.slice(braceIndex + 1, i), i + 1];
    }
  }
  return [css.slice(braceIndex + 1), css.length];
}

export function walkCssRules(css, visit) {
  const text = stripCssComments(css);
  let i = 0;
  while (i < text.length) {
    while (i < text.length && /\s/.test(text[i])) i += 1;
    if (i >= text.length) break;
    if (text.startsWith("@", i)) {
      const brace = text.indexOf("{", i);
      if (brace < 0) break;
      const header = text.slice(i, brace).trim();
      const [inner, end] = sliceBlock(text, brace);
      if (/^@(media|supports|layer)\b/i.test(header)) walkCssRules(inner, visit);
      i = end;
      continue;
    }
    const brace = text.indexOf("{", i);
    if (brace < 0) break;
    const selector = text.slice(i, brace).trim();
    const [inner, end] = sliceBlock(text, brace);
    if (inner.includes("{")) walkCssRules(inner, visit);
    else visit(selector, inner);
    i = end;
  }
}

export function stripHover(selector = "") {
  return String(selector || "")
    .replace(/:hover\b/gi, "")
    .replace(/::?[a-z-]+(\([^)]*\))?/gi, "")
    .replace(/\s+/g, " ")
    .trim();
}

export function isBareTagHover(selector = "") {
  const stripped = stripHover(selector);
  return /^(a|button|input|textarea|select|\*|html|body)$/i.test(stripped);
}

export function isSimpleSelector(selector = "") {
  return !/[\s>+~]/.test(stripHover(selector));
}

export function parseHoverRules(css = "") {
  const rules = [];
  walkCssRules(css, (selector, body) => {
    if (!/:hover\b/i.test(selector)) return;
    const decls = pickPaintDeclarations(parseDeclarations(body));
    if (!Object.keys(decls).length) return;
    for (const raw of selector.split(",")) {
      const sel = raw.trim();
      if (!/:hover\b/i.test(sel)) continue;
      if (isBareTagHover(sel)) continue;
      if (!isSimpleSelector(sel)) continue;
      rules.push({
        selector: sel,
        matchSelector: stripHover(sel),
        declarations: { ...decls },
      });
    }
  });
  return rules;
}

export function extractStyleBlocks(html = "") {
  return [...String(html || "").matchAll(/<style\b[^>]*>([\s\S]*?)<\/style>/gi)].map((m) => m[1]);
}

export function extractStylesheetHrefs(html = "", pageUrl = "") {
  const hrefs = [];
  const tags = String(html || "").match(/<link\b[^>]*>/gi) || [];
  for (const tag of tags) {
    if (!/rel=["'][^"']*stylesheet/i.test(tag)) continue;
    const href = tag.match(/href=["']([^"']+)/i)?.[1];
    if (!href || href.startsWith("data:")) continue;
    if (/fonts\.google|typekit|use\.typekit/i.test(href)) continue;
    try {
      hrefs.push(pageUrl ? new URL(href, pageUrl).href : href);
    } catch {
      hrefs.push(href);
    }
  }
  return hrefs;
}

function attr(attrs, name) {
  return attrs.match(new RegExp(`\\b${name}=["']([^"']*)`, "i"))?.[1] || "";
}

function textOf(inner = "") {
  return String(inner || "")
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/\s+/g, " ")
    .trim();
}

export function extractControls(html = "") {
  const out = [];
  const re = /<(a|button)\b([^>]*)>([\s\S]*?)<\/\1>/gi;
  let match;
  while ((match = re.exec(html))) {
    const tag = match[1].toLowerCase();
    const attrs = match[2] || "";
    const classes = attr(attrs, "class").split(/\s+/).filter(Boolean);
    out.push({
      tag,
      classes,
      id: attr(attrs, "id"),
      text: textOf(match[3]),
      attrs,
    });
  }
  return out;
}

export function controlMatchesSelector(control, matchSelector = "") {
  if (!control || !isSimpleSelector(matchSelector)) return false;
  const sel = stripHover(matchSelector);
  const tag = (sel.match(/^[a-z][a-z0-9-]*/i) || [""])[0].toLowerCase();
  if (tag && tag !== control.tag) return false;
  const id = (sel.match(/#([a-zA-Z0-9_-]+)/) || [])[1];
  if (id && id !== control.id) return false;
  const classes = [...sel.matchAll(/\.([a-zA-Z0-9_-]+)/g)].map((row) => row[1]);
  if (!classes.length && !id) return false;
  return classes.every((cls) => control.classes.includes(cls));
}

export function labelKey(label = "") {
  return String(label || "")
    .replace(/^(primary|secondary|ghost|outline|button|cta|pill|nav|link)\s*[-–—:]\s*/i, "")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();
}

export function findControlForLabel(controls = [], label = "") {
  const key = labelKey(label);
  if (!key) return null;
  const exact = controls.find((row) => labelKey(row.text) === key);
  if (exact) return exact;
  return controls.find((row) => {
    const text = labelKey(row.text);
    return text && (text.includes(key) || key.includes(text));
  }) || null;
}

export function isButtonPaintHover(decls = {}) {
  return Object.keys(decls).some((prop) => BUTTON_PAINT.test(prop));
}

export function hoverPaintForControl(control, rules = []) {
  if (!control) return null;
  const merged = {};
  let selector = "";
  for (const rule of rules) {
    if (!controlMatchesSelector(control, rule.matchSelector)) continue;
    Object.assign(merged, rule.declarations);
    selector = rule.selector;
  }
  if (!Object.keys(merged).length || !isButtonPaintHover(merged)) return null;
  return { selector, declarations: merged };
}

export function suggestedLibraryClass(control, declarations = {}) {
  const named = (control?.classes || []).find((cls) => /^(btn-[a-z0-9-]+|pill|text-link)$/i.test(cls));
  if (named) return named.toLowerCase();
  if ((control?.classes || []).some((cls) => /ghost/i.test(cls))) return "btn-ghost";
  const bg = String(declarations["background-color"] || declarations.background || "");
  if (/transparent|rgba\(\s*0\s*,\s*0\s*,\s*0\s*,\s*0/i.test(bg)) return "btn-ghost";
  return "btn-primary";
}

export function paperStylesFromHover(decls = {}) {
  const styles = {};
  if (decls["background-color"]) styles.backgroundColor = decls["background-color"];
  else if (decls.background && !/url\(/i.test(decls.background)) styles.backgroundColor = decls.background;
  if (decls.color) styles.color = decls.color;
  if (decls["-webkit-text-fill-color"]) styles.webkitTextFillColor = decls["-webkit-text-fill-color"];
  if (decls["box-shadow"]) styles.boxShadow = decls["box-shadow"];
  if (decls.opacity) styles.opacity = decls.opacity;
  if (decls.border) styles.border = decls.border;
  if (decls["border-color"]) styles.borderColor = decls["border-color"];
  if (decls.filter) styles.filter = decls.filter;
  return styles;
}

export function cssHoverRecipes({ html = "", css = "", buttons = [] } = {}) {
  const controls = extractControls(html);
  const rules = parseHoverRules(css);
  const applied = [];
  const skipped = [];
  for (const row of buttons) {
    const label = row.label || row.sourceNodeId || "button";
    const control = findControlForLabel(controls, label);
    if (!control) {
      skipped.push({ label, sectionId: row.sectionId || "", reason: "no matching source control" });
      continue;
    }
    const paint = hoverPaintForControl(control, rules);
    if (!paint) {
      skipped.push({
        label,
        sectionId: row.sectionId || "",
        reason: "no source CSS :hover paint",
      });
      continue;
    }
    applied.push({
      label,
      sectionId: row.sectionId || "",
      sectionName: row.sectionName || "",
      sourceNodeId: row.sourceNodeId || "",
      parkedNodeId: row.parkedNodeId || "",
      rowNodeId: row.rowNodeId || "",
      sourceSelector: paint.selector,
      className: suggestedLibraryClass(control, paint.declarations),
      declarations: paint.declarations,
      paperStyles: paperStylesFromHover(paint.declarations),
    });
  }
  return { applied, skipped, controlCount: controls.length, ruleCount: rules.length };
}

export function buttonHoverReceiptOk(receipt = {}) {
  return receipt?.ok === true
    && receipt.writer === WRITER
    && Array.isArray(receipt.applied)
    && Array.isArray(receipt.skipped);
}

export function localSheetCandidates(root, href, pageUrl = "") {
  const out = [];
  if (!root || !href) return out;
  try {
    const url = pageUrl ? new URL(href, pageUrl) : new URL(href, "https://local.invalid/");
    const path = url.pathname.replace(/^\/+/, "");
    if (path) out.push(join(root, "source-site", path));
  } catch { /* keep relative fallback */ }
  if (!/^https?:/i.test(href) && !href.startsWith("data:")) {
    out.push(join(root, "source-site", href.replace(/^\/+/, "")));
  }
  return [...new Set(out)];
}

export async function loadSourceCss(html, pageUrl, { fetchImpl = globalThis.fetch, log, root } = {}) {
  const sheets = [...extractStyleBlocks(html)];
  const hrefs = extractStylesheetHrefs(html, pageUrl).slice(0, 20);
  for (const href of hrefs) {
    let loaded = false;
    for (const candidate of localSheetCandidates(root, href, pageUrl)) {
      try {
        const text = readFileSync(candidate, "utf8");
        if (text && text.length < 800_000) {
          sheets.push(text);
          loaded = true;
          break;
        }
      } catch { /* try the live href */ }
    }
    if (loaded) continue;
    if (typeof fetchImpl !== "function") continue;
    try {
      const res = await fetchImpl(href, { signal: AbortSignal.timeout(8000) });
      if (!res?.ok) continue;
      const text = await res.text();
      if (text && text.length < 800_000) sheets.push(text);
    } catch (error) {
      log?.(`source CSS skip ${href}: ${error.message || error}`);
    }
  }
  return sheets.join("\n");
}
