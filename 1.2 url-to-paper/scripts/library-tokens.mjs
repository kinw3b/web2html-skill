// Build Stage L / 1.3 tokens from mined colors + fonts, plus Tailwind
// default scales for type sizes, spacing, radius, and elevation.
//
// extract-library.mjs walks Paper for colors / families / weights / styles
// plus desktop line-height (%) and letter-spacing (rem).
// This module does not need that walk to emit the default scales.

import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  defaultFontSizeTokens,
  defaultRadiusTokens,
  defaultShadowTokens,
  defaultSpacingTokens,
  extraFontSizeTokens,
  mergeFontSizeTokens,
  TAILWIND_SEMANTIC_COLORS,
} from "./tailwind-defaults.mjs";
export { TAILWIND_SEMANTIC_COLORS } from "./tailwind-defaults.mjs";
export { extraFontSizeTokens, mergeFontSizeTokens } from "./tailwind-defaults.mjs";
export { isTokenPassArtboard } from "./token-pass-targets.mjs";

export const WEIGHT_NAMES = {
  100: "thin", 200: "extralight", 300: "light", 400: "normal", 500: "medium",
  600: "semibold", 700: "bold", 800: "extrabold", 900: "black",
};

const SERIF = /(vollkorn|newsreader|playfair|georgia|garamond|merriweather|lora|times|serif\b)/i;
const MONO = /(mono|consolas|menlo|courier|ibm plex mono)/i;
const TRANSPARENT = /^(transparent|rgba\(0, ?0, ?0, ?0\))$/i;

export function tally() {
  return new Map();
}

export function bump(m, key, node) {
  if (key == null || key === "") return;
  const k = String(key).trim();
  if (!k || k === "none" || k === "normal" && m._skipNormal) return;
  if (!k || k === "auto") return;
  if (!m.has(k)) m.set(k, { value: k, count: 0, examples: [] });
  const e = m.get(k);
  e.count++;
  if (node && e.examples.length < 4) {
    e.examples.push(`${node.artboard || "?"}/${node.name || "?"}`);
  }
}

export function rank(m, minUses = 1) {
  return [...m.values()].filter((e) => e.count >= minUses).sort((a, b) => b.count - a.count);
}

export function parseColor(v) {
  if (!v) return null;
  const s = String(v).trim();
  let m = /^#([0-9a-f]{3,8})$/i.exec(s);
  if (m) {
    let h = m[1];
    if (h.length === 3 || h.length === 4) h = h.split("").map((c) => c + c).join("");
    if (h.length !== 6 && h.length !== 8) return null;
    const rgb = {
      r: parseInt(h.slice(0, 2), 16),
      g: parseInt(h.slice(2, 4), 16),
      b: parseInt(h.slice(4, 6), 16),
      a: h.length === 8 ? parseInt(h.slice(6, 8), 16) / 255 : 1,
    };
    return rgb;
  }
  m = /^rgba?\(\s*(\d+)[,\s]+(\d+)[,\s]+(\d+)(?:\s*[,/]\s*([\d.]+))?\s*\)/i.exec(s);
  if (m) return { r: +m[1], g: +m[2], b: +m[3], a: m[4] == null ? 1 : +m[4] };
  return null;
}

function hasAlpha(c) {
  return c && c.a != null && c.a < 0.999;
}

function alphaOf(c) {
  return c && c.a != null ? c.a : 1;
}

/** Manhattan RGB plus 0–255 alpha. Opaque #EF4B3C and wash #EF4B3C1A are not near. */
export function colorDist(a, b) {
  if (!a || !b) return Infinity;
  return Math.abs(a.r - b.r) + Math.abs(a.g - b.g) + Math.abs(a.b - b.b)
    + Math.round(Math.abs(alphaOf(a) - alphaOf(b)) * 255);
}

function formatRgbHex(c) {
  return `#${[c.r, c.g, c.b].map((n) => n.toString(16).padStart(2, "0")).join("")}`.toUpperCase();
}

function formatPaintedHex(value, { keepAlpha = false } = {}) {
  const c = parseColor(value);
  if (!c) return String(value || "");
  const rgb = formatRgbHex(c);
  if (keepAlpha && hasAlpha(c)) {
    return `${rgb}${Math.round(c.a * 255).toString(16).padStart(2, "0").toUpperCase()}`;
  }
  return rgb;
}

/** Hex with alpha when the paint is translucent (`#EF4B3C1A`), RGB otherwise. */
export function toPaintedHex(value) {
  const c = parseColor(value);
  if (!c) return null;
  return formatPaintedHex(value, { keepAlpha: hasAlpha(c) });
}

const lum = (c) => (0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b) / 255;
const sat = (c) => {
  const mx = Math.max(c.r, c.g, c.b), mn = Math.min(c.r, c.g, c.b);
  return mx === 0 ? 0 : (mx - mn) / mx;
};
const dist = (a, b) => Math.abs(a.r - b.r) + Math.abs(a.g - b.g) + Math.abs(a.b - b.b);

export function mergeColors(entries, threshold = 12) {
  const kept = [];
  for (const e of entries) {
    const c = parseColor(e.value);
    if (!c) continue;
    const near = kept.find((k) => k.rgb && colorDist(k.rgb, c) <= threshold);
    if (near) {
      near.count += e.count;
      near.merged = near.merged || [];
      near.merged.push(e.value);
    } else {
      kept.push({ ...e, rgb: c });
    }
  }
  return kept.sort((a, b) => b.count - a.count);
}

function colorRole(kind, l, s, { alpha = false } = {}) {
  if (kind === "text") {
    if (alpha) return s >= 0.30 ? "accent-soft" : "muted";
    if (l <= 0.28) return "default";
    if (l >= 0.85) return "inverse";
    if (s >= 0.30) return "accent";
    return "muted";
  }
  if (alpha) {
    if (s >= 0.35) return "accent-soft";
    if (l >= 0.75) return "subtle";
    return "wash";
  }
  if (l >= 0.93) return "surface";
  if (l <= 0.18) return "ink";
  if (s >= 0.35) return "accent";
  if (l >= 0.75) return "subtle";
  return "neutral";
}

export function nameColors(entries, prefix, kind = "surface") {
  const used = new Set();
  const take = (n) => {
    let name = n, i = 2;
    while (used.has(name)) name = `${n}-${i++}`;
    used.add(name);
    return name;
  };
  const paint = (list, alpha) => list.flatMap((e) => {
    const rgb = e.rgb || parseColor(e.value);
    if (!rgb) return [];
    const l = lum(rgb), s = sat(rgb);
    return [{
      type: "color",
      name: take(`${prefix}-${colorRole(kind, l, s, { alpha })}`),
      value: e.value,
      uses: e.count,
      merged: e.merged,
      luminance: +l.toFixed(3),
      saturation: +s.toFixed(3),
      source: "mined",
    }];
  });
  const opaque = [];
  const translucent = [];
  for (const e of entries || []) {
    const rgb = e.rgb || parseColor(e.value);
    if (!rgb) continue;
    (hasAlpha(rgb) ? translucent : opaque).push({ ...e, rgb });
  }
  // Opaque fills name --color-accent first. A more common 10% wash must not
  // steal that role (Pitfall #154).
  return [...paint(opaque, false), ...paint(translucent, true)];
}

// Fixed semantic *roles* for leftover hexes. Not a grey ramp.
// Only created when that hex (or a tiny delta) appears on homepage / A/6.
export const SEMANTIC_COLOR_ROLES = [
  { name: "--color-surface-alt", targets: ["#FBFBFB"], pool: "fill", skipIfNear: ["--color-surface"] },
  { name: "--color-surface-muted", targets: ["#F2F2F2"], pool: "fill" },
  { name: "--color-danger", targets: ["#E11D2E", "#EF4444", "#DC2626"], pool: "any" },
  { name: "--color-warning", targets: ["#F59E0B", "#FBBF24", "#D97706"], pool: "any" },
  { name: "--color-success", targets: ["#22C55E", "#16A34A", "#10B981"], pool: "any" },
  { name: "--color-info", targets: ["#3B82F6", "#2563EB", "#0EA5E9"], pool: "any" },
  { name: "--color-muted", targets: ["#6B7280", "#737373", "#9CA3AF"], pool: "any" },
  { name: "--color-text-subtle", targets: ["#999999"], pool: "text" },
  { name: "--color-text-secondary", targets: ["#666666"], pool: "text" },
  { name: "--color-overlay", targets: ["#1D2B19B3", "#1D2B1999", "#1D2B19"], pool: "fill", preferAlpha: true },
];

const INK_SOFT_TARGETS = ["#333333", "#111111"];
const CLAIMED_DIST = 4;
const ROLE_DIST = 12;

function leftoverEntries(entries, brandTokens) {
  return (entries || []).filter((e) => {
    const c = parseColor(e.value);
    if (!c) return false;
    if (hasAlpha(c)) {
      return !brandTokens.some((t) => {
        const tc = parseColor(t.value);
        return tc && colorDist(tc, c) <= CLAIMED_DIST;
      });
    }
    return !brandTokens.some((t) => {
      const tc = parseColor(t.value);
      return tc && !hasAlpha(tc) && dist(tc, c) <= CLAIMED_DIST;
    });
  });
}

function bestRoleHit(entries, targets, { preferAlpha = false, maxDist = ROLE_DIST } = {}) {
  let best = null, bestD = Infinity;
  for (const e of entries) {
    const c = parseColor(e.value);
    if (!c) continue;
    for (const target of targets) {
      const tc = parseColor(target);
      if (!tc) continue;
      const d = dist(c, tc);
      if (d > maxDist) continue;
      const alphaBoost = preferAlpha && hasAlpha(c) ? -0.5 : 0;
      const score = d + alphaBoost;
      if (!best || score < bestD) {
        best = e;
        bestD = score;
      }
    }
  }
  return best;
}

function semanticToken(name, entry, { keepAlpha = false } = {}) {
  const value = formatPaintedHex(entry.value, { keepAlpha });
  const c = parseColor(entry.value);
  const token = {
    type: "color",
    name,
    value,
    uses: entry.count,
    source: "semantic-role",
    luminance: c ? +lum(c).toFixed(3) : undefined,
    saturation: c ? +sat(c).toFixed(3) : undefined,
  };
  if (keepAlpha && hasAlpha(c)) token.paperValue = formatRgbHex(c);
  return token;
}

export function ensureTailwindSemanticColors(existing = []) {
  const used = new Set((existing || []).map((t) => t.name));
  const extra = [];
  for (const row of TAILWIND_SEMANTIC_COLORS) {
    if (used.has(row.name)) continue;
    extra.push({
      type: "color",
      name: row.name,
      value: row.value,
      uses: 0,
      source: "semantic-role",
      twClass: row.twClass,
      floor: "tailwind-default",
    });
    used.add(row.name);
  }
  return [...existing, ...extra];
}

export function assertFoundationsContract(proposed = []) {
  const names = new Set((proposed || []).map((t) => t.name));
  const missing = [];
  for (const row of TAILWIND_SEMANTIC_COLORS) {
    if (!names.has(row.name)) missing.push(row.name);
  }
  for (const step of ["10xl", "11xl", "12xl"]) {
    if (!names.has(`--text-${step}`)) missing.push(`--text-${step}`);
  }
  if (missing.length) {
    throw new Error(`1.4 foundations contract missing: ${missing.join(", ")}`);
  }
  return true;
}

export function assignSemanticColorRoles(mined, brandTokens = [], { maxDist = ROLE_DIST, floor = true } = {}) {
  const brand = (brandTokens || []).filter((t) => t.type === "color" || /^--color/.test(t.name || ""));
  const fills = leftoverEntries(mined.colors || mined.allColors || [], brand);
  const texts = leftoverEntries(mined.textColors || mined.allTextColors || [], brand);
  const any = leftoverEntries(
    [...(mined.colors || mined.allColors || []), ...(mined.textColors || mined.allTextColors || [])],
    brand,
  );
  const poolOf = (pool) => (pool === "fill" ? fills : pool === "text" ? texts : any);
  const out = [];
  const used = new Set(brand.map((t) => t.name));

  for (const role of SEMANTIC_COLOR_ROLES) {
    if (used.has(role.name)) continue;
    const hit = bestRoleHit(poolOf(role.pool), role.targets, { preferAlpha: role.preferAlpha, maxDist });
    if (!hit) continue;
    if (role.skipIfNear) {
      const c = parseColor(hit.value);
      const nearBrand = brand.find((t) => {
        if (!role.skipIfNear.includes(t.name)) return false;
        const tc = parseColor(t.value);
        return c && tc && dist(c, tc) <= CLAIMED_DIST;
      });
      if (nearBrand) continue;
    }
    out.push(semanticToken(role.name, hit, { keepAlpha: role.preferAlpha }));
    used.add(role.name);
  }

  const inkHits = INK_SOFT_TARGETS.map((hex) => {
    const hit = bestRoleHit(any, [hex], { maxDist });
    return hit ? { hex, hit, lum: lum(parseColor(hit.value)) } : null;
  }).filter(Boolean);
  const seen = new Set();
  const uniqueInk = inkHits.filter((h) => {
    const key = formatRgbHex(parseColor(h.hit.value));
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
  if (uniqueInk.length === 1 && !used.has("--color-ink-soft")) {
    out.push(semanticToken("--color-ink-soft", uniqueInk[0].hit));
  } else if (uniqueInk.length >= 2) {
    const sorted = [...uniqueInk].sort((a, b) => b.lum - a.lum);
    if (!used.has("--color-ink-soft")) out.push(semanticToken("--color-ink-soft", sorted[0].hit));
    if (!used.has("--color-ink-strong")) out.push(semanticToken("--color-ink-strong", sorted[1].hit));
  }

  return floor ? ensureTailwindSemanticColors(out) : out;
}

export function baseFamily(v) {
  const raw = String(v || "").trim();
  if (!raw || /^var\(--font-[^)]+\)$/i.test(raw)) return "";
  return (raw.split(",")[0] || "").replace(/["']/g, "")
    .replace(/-(thin|extralight|light|regular|book|medium|semibold|bold|extrabold|black|italic)+$/i, "")
    .trim();
}

export function resolveBoundTokenValue(value, tokens = [], seen = new Set()) {
  const raw = String(value || "").trim();
  const match = /^var\((--[^)]+)\)$/i.exec(raw);
  if (!match) return raw;
  if (seen.has(match[1])) return raw;
  seen.add(match[1]);
  const token = (tokens || []).find((item) => item?.name === match[1]);
  if (!token?.value) return raw;
  return resolveBoundTokenValue(String(token.value), tokens, seen);
}

export function resolveBoundFontFamily(value, tokens = []) {
  return resolveBoundTokenValue(value, tokens);
}

export function familyTokens(ranked) {
  const famRoles = new Map();
  for (const e of ranked) {
    const base = baseFamily(e.value);
    if (!base) continue;
    const role = MONO.test(e.value) ? "mono" : SERIF.test(base) ? "serif" : "sans";
    const key = `${role}:${base.toLowerCase()}`;
    if (!famRoles.has(key)) famRoles.set(key, { role, base, value: e.value, uses: 0 });
    famRoles.get(key).uses += e.count;
  }
  const generic = /^(system sans-serif|system serif|system-ui|ui-sans-serif|ui-serif|sans-serif|serif|monospace|cursive)$/i;
  const families = [...famRoles.values()];
  const concreteRoles = new Set(families.filter((f) => !generic.test(f.base)).map((f) => f.role));
  return families
    .filter((f) => !generic.test(f.base) || !concreteRoles.has(f.role))
    .sort((a, b) => b.uses - a.uses).slice(0, 4).map((f, _i, all) => {
    const sameRole = all.filter((x) => x.role === f.role);
    const suffix = sameRole.length > 1 ? `-${f.base.toLowerCase().replace(/\s+/g, "-")}` : "";
    return {
      type: "fontFamily",
      name: `--font-${f.role}${suffix}`,
      value: f.value,
      paperValue: f.base,
      uses: f.uses,
      family: f.base,
      source: "mined",
    };
  });
}

export function weightTokens(ranked) {
  return ranked.slice(0, 5).flatMap((e) => {
    const n = parseInt(e.value, 10);
    if (Number.isNaN(n)) return [];
    return [{
      type: "fontWeight",
      name: `--font-weight-${WEIGHT_NAMES[n] || n}`,
      value: n,
      uses: e.count,
      source: "mined",
    }];
  });
}

const STYLE_NAMES = {
  italic: "italic",
  oblique: "oblique",
  normal: "normal",
};

export function styleTokens(ranked) {
  return ranked.flatMap((e) => {
    const raw = String(e.value).toLowerCase();
    const slug = STYLE_NAMES[raw];
    if (!slug) return [];
    return [{
      type: "fontStyle",
      name: `--font-style-${slug}`,
      value: raw,
      uses: e.count,
      source: "mined",
      paperToken: false,
    }];
  });
}

function numericPx(value) {
  if (value == null || value === "") return null;
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  const s = String(value).trim();
  if (!s || /var\s*\(/i.test(s)) return null;
  const n = parseFloat(s);
  if (!Number.isFinite(n)) return null;
  if (/rem$/i.test(s)) return n * 16;
  if (/px$/i.test(s) || /^[-+]?\d*\.?\d+$/.test(s)) return n;
  return null;
}

function isDesktopMineNode(node) {
  const name = String(node?.artboard || "");
  if (!name) return true;
  return /-(desktop)$/i.test(name);
}

export function formatRem(n) {
  if (!Number.isFinite(n)) return null;
  const r = Math.round(n * 1000) / 1000;
  if (r === 0) return "0rem";
  let body = r.toFixed(3).replace(/\.?0+$/, "");
  if (body === "-0") body = "0";
  return `${body}rem`;
}

export function remTokenSlug(n) {
  if (!Number.isFinite(n) || n === 0) return "0";
  const sign = n < 0 ? "neg-" : "";
  const abs = formatRem(Math.abs(n)).replace(/rem$/i, "").replace(/\./g, "-");
  return `${sign}${abs}`;
}

export function lineHeightToPercent(value, fontSize) {
  if (value == null || value === "") return null;
  if (typeof value === "number") {
    if (value <= 4) return Number.isFinite(value) ? `${Math.round(value * 100)}%` : null;
    const fs = numericPx(fontSize);
    if (!Number.isFinite(value) || fs == null || fs <= 0) return null;
    return `${Math.round((value / fs) * 100)}%`;
  }
  const s = String(value).trim().toLowerCase();
  if (!s || s === "normal" || s === "auto" || s === "unset" || s === "inherit" || s === "initial") {
    return null;
  }
  if (/var\s*\(/i.test(s)) return null;
  if (/%$/.test(s)) {
    const n = parseFloat(s);
    return Number.isFinite(n) && n > 0 ? `${Math.round(n)}%` : null;
  }
  if (/^[-+]?\d*\.?\d+$/.test(s)) {
    const n = parseFloat(s);
    if (!Number.isFinite(n) || n <= 0) return null;
    if (n <= 4) return `${Math.round(n * 100)}%`;
    const fs = numericPx(fontSize);
    if (fs == null || fs <= 0) return null;
    return `${Math.round((n / fs) * 100)}%`;
  }
  if (/px$/i.test(s)) {
    const px = parseFloat(s);
    const fs = numericPx(fontSize);
    if (!Number.isFinite(px) || px <= 0 || fs == null || fs <= 0) return null;
    return `${Math.round((px / fs) * 100)}%`;
  }
  if (/rem$/i.test(s)) {
    const rem = parseFloat(s);
    const fs = numericPx(fontSize);
    if (!Number.isFinite(rem) || rem <= 0 || fs == null || fs <= 0) return null;
    return `${Math.round(((rem * 16) / fs) * 100)}%`;
  }
  if (/em$/i.test(s)) {
    const em = parseFloat(s);
    return Number.isFinite(em) && em > 0 ? `${Math.round(em * 100)}%` : null;
  }
  return null;
}

export function letterSpacingToRem(value, fontSize) {
  if (value == null || value === "") return null;
  if (typeof value === "number") {
    return Number.isFinite(value) ? formatRem(value / 16) : null;
  }
  const s = String(value).trim().toLowerCase();
  if (!s || s === "unset" || s === "inherit" || s === "initial") return null;
  if (/var\s*\(/i.test(s)) return null;
  if (s === "normal") return "0rem";
  if (/rem$/i.test(s)) {
    const n = parseFloat(s);
    return Number.isFinite(n) ? formatRem(n) : null;
  }
  if (/em$/i.test(s)) {
    const em = parseFloat(s);
    if (!Number.isFinite(em)) return null;
    const fs = numericPx(fontSize);
    if (fs != null && fs > 0) return formatRem((em * fs) / 16);
    return formatRem(em);
  }
  if (/px$/i.test(s) || /^[-+]?\d*\.?\d+$/.test(s)) {
    const px = parseFloat(s);
    return Number.isFinite(px) ? formatRem(px / 16) : null;
  }
  return null;
}

export function lineHeightTokens(ranked = []) {
  return (ranked || []).slice(0, 16).flatMap((e) => {
    const pct = lineHeightToPercent(e.value) || (/%$/.test(String(e.value || "")) ? String(e.value) : null);
    if (!pct) return [];
    const n = Math.round(parseFloat(pct));
    if (!Number.isFinite(n) || n <= 0) return [];
    return [{
      type: "lineHeight",
      name: `--line-height-${n}`,
      value: `${n}%`,
      uses: e.count,
      source: "mined",
    }];
  }).sort((a, b) => parseFloat(a.value) - parseFloat(b.value));
}

export function letterSpacingTokens(ranked = []) {
  return (ranked || []).slice(0, 16).flatMap((e) => {
    const rem = /rem$/i.test(String(e.value || ""))
      ? formatRem(parseFloat(e.value))
      : letterSpacingToRem(e.value);
    if (!rem) return [];
    const n = parseFloat(rem);
    if (!Number.isFinite(n)) return [];
    return [{
      type: "letterSpacing",
      name: `--letter-spacing-${remTokenSlug(n)}`,
      value: rem,
      uses: e.count,
      source: "mined",
    }];
  }).sort((a, b) => parseFloat(a.value) - parseFloat(b.value));
}

export function mineFromStyledNodes(nodes, { minUses = 3 } = {}) {
  const colors = tally();
  const textColors = tally();
  const fontFamilies = tally();
  const fontWeights = tally();
  const fontStyles = tally();
  const fontSizes = tally();
  const lineHeights = tally();
  const letterSpacings = tally();

  for (const n of nodes) {
    const s = n.style;
    if (!s) continue;
    if (s.backgroundColor && !TRANSPARENT.test(s.backgroundColor)) bump(colors, s.backgroundColor, n);
    if (s.color) bump(textColors, s.color, n);
    if (s.fontFamily) bump(fontFamilies, s.fontFamily, n);
    if (s.fontWeight) bump(fontWeights, s.fontWeight, n);
    if (s.fontStyle && !/^\s*normal\s*$/i.test(s.fontStyle)) bump(fontStyles, s.fontStyle, n);
    else if (s.fontStyle) bump(fontStyles, s.fontStyle, n);
    if (s.fontSize) bump(fontSizes, s.fontSize, n);
    if (isDesktopMineNode(n) && s.fontSize) {
      const leading = lineHeightToPercent(s.lineHeight ?? s["line-height"], s.fontSize);
      if (leading) bump(lineHeights, leading, n);
      const tracking = letterSpacingToRem(s.letterSpacing ?? s["letter-spacing"], s.fontSize);
      if (tracking) bump(letterSpacings, tracking, n);
    }
  }

  return {
    colors: rank(colors, minUses),
    textColors: rank(textColors, minUses),
    allColors: rank(colors, 1),
    allTextColors: rank(textColors, 1),
    fontFamilies: rank(fontFamilies, minUses),
    fontWeights: rank(fontWeights, minUses),
    fontStyles: rank(fontStyles, 1),
    fontSizes: rank(fontSizes, 1),
    lineHeights: rank(lineHeights, 1),
    letterSpacings: rank(letterSpacings, 1),
  };
}

export function proposeLibraryTokens(mined, { minUses = 3, leftoverMined } = {}) {
  const brandColors = [
    ...nameColors(mergeColors(mined.colors || []).slice(0, 8), "--color", "surface"),
    ...nameColors(mergeColors(mined.textColors || []).slice(0, 5), "--color-text", "text"),
  ];
  const leftover = leftoverMined || {
    colors: mined.allColors || mined.colors || [],
    textColors: mined.allTextColors || mined.textColors || [],
  };
  const semantic = assignSemanticColorRoles(leftover, brandColors);
  const proposed = [];
  proposed.push(...brandColors);
  proposed.push(...semantic);
  proposed.push(...familyTokens(mined.fontFamilies || []));
  proposed.push(...weightTokens(mined.fontWeights || []));
  proposed.push(...styleTokens(mined.fontStyles || []));
  proposed.push(...lineHeightTokens(mined.lineHeights || []));
  proposed.push(...letterSpacingTokens(mined.letterSpacings || []));
  proposed.push(...mergeFontSizeTokens(
    defaultFontSizeTokens(),
    extraFontSizeTokens(mined.fontSizes || mined.allFontSizes || []),
  ));
  proposed.push(...defaultSpacingTokens());
  proposed.push(...defaultRadiusTokens());
  proposed.push(...defaultShadowTokens());
  assertFoundationsContract(proposed);
  return proposed;
}

// Paper create_tokens: no shadow / fontStyle types; names cannot contain dots.
export function cssVar(name) {
  const n = String(name || "").trim();
  if (!n) return "";
  if (n.startsWith("var(")) return n;
  return n.startsWith("--") ? `var(${n})` : `var(--${n})`;
}

export function withCssVar(token) {
  return { ...token, cssVar: cssVar(token.name) };
}

export function bindThemeToTokens(hexTheme, tokens = []) {
  const colors = tokens.filter((t) => t.type === "color");
  const fonts = tokens.filter((t) => t.type === "fontFamily");
  const byName = (re) => colors.find((c) => re.test(c.name));
  const byValue = (hex) => colors.find((c) => String(c.value).toLowerCase() === String(hex || "").toLowerCase());
  const colorVar = (re, hex) => {
    const t = byName(re) || byValue(hex);
    return t ? cssVar(t.name) : hex;
  };
  const sans = fonts.find((f) => /sans/.test(f.name));
  const serif = fonts.find((f) => /serif/.test(f.name));
  const accentTok = byValue(hexTheme.accent);
  return {
    ...hexTheme,
    ink: colorVar(/--color-ink$/, hexTheme.ink),
    accent: accentTok ? cssVar(accentTok.name) : colorVar(/--color-accent/, hexTheme.accent),
    surface: colorVar(/--color-surface$/, hexTheme.surface),
    surfaceAlt: colorVar(/--color-surface-alt$/, hexTheme.surfaceAlt) === hexTheme.surfaceAlt
      ? colorVar(/--color-surface-2$/, hexTheme.surfaceAlt)
      : colorVar(/--color-surface-alt$/, hexTheme.surfaceAlt),
    border: colorVar(/--color-subtle$/, hexTheme.border),
    muted: colorVar(/--color-text-muted$/, hexTheme.muted),
    body: colorVar(/--color-text-accent$/, hexTheme.body),
    display: serif ? cssVar(serif.name) : (sans ? cssVar(sans.name) : hexTheme.display),
    sans: sans ? cssVar(sans.name) : hexTheme.sans,
  };
}

function pxNum(v) {
  const n = parseFloat(v);
  return Number.isFinite(n) ? n : null;
}

function colorKey(v) {
  const c = parseColor(v);
  if (!c) return String(v || "").toLowerCase().replace(/\s+/g, "");
  const rgb = `#${[c.r, c.g, c.b].map((n) => n.toString(16).padStart(2, "0")).join("")}`;
  if (hasAlpha(c)) {
    return `${rgb}${Math.round(c.a * 255).toString(16).padStart(2, "0")}`.toUpperCase();
  }
  return rgb.toUpperCase();
}

// After write_html, Paper may have resolved var(--text-6xl) to 60px.
// Rebuild update_styles payloads that put the token back.
export function tokenRebindUpdates(nodes, tokens = []) {
  const of = (type) => tokens.filter((t) => t.type === type);
  const already = (v) => String(v || "").includes("var(");
  const updates = [];
  for (const n of nodes) {
    const s = n.style || {};
    const styles = {};
    if (s.fontSize && !already(s.fontSize)) {
      const px = pxNum(s.fontSize);
      const tok = of("fontSize").find((t) => pxNum(t.value) === px);
      if (tok) styles.fontSize = cssVar(tok.name);
    }
    if (s.backgroundColor && !already(s.backgroundColor)) {
      const tok = of("color").find((t) => colorKey(t.value) === colorKey(s.backgroundColor));
      if (tok) styles.backgroundColor = cssVar(tok.name);
    }
    if (s.color && !already(s.color)) {
      const tok = of("color").find((t) => colorKey(t.value) === colorKey(s.color));
      if (tok) styles.color = cssVar(tok.name);
    }
    if (s.fontFamily && !already(s.fontFamily)) {
      const tok = of("fontFamily").find((t) => {
        const face = t.family || String(t.value).split(",")[0].replace(/["']/g, "").trim();
        return face && String(s.fontFamily).includes(face);
      });
      if (tok) styles.fontFamily = cssVar(tok.name);
    }
    if (s.fontWeight && !already(s.fontWeight)) {
      const tok = of("fontWeight").find((t) => String(t.value) === String(parseInt(s.fontWeight, 10)));
      if (tok) styles.fontWeight = cssVar(tok.name);
    }
    if (s.borderRadius && !already(s.borderRadius)) {
      const px = pxNum(s.borderRadius);
      const tok = of("radius").find((t) => pxNum(t.value) === px || t.value === s.borderRadius);
      if (tok) styles.borderRadius = cssVar(tok.name);
    }
    if (s.width && !already(s.width)) {
      const px = pxNum(s.width);
      const h = pxNum(s.height);
      const tok = of("spacing").find((t) => pxNum(t.value) === px);
      if (tok && h != null && h <= 24) styles.width = cssVar(tok.name);
    }
    if (s.boxShadow && !already(s.boxShadow)) {
      const tok = of("shadow").find((t) => t.value === s.boxShadow);
      if (tok) styles.boxShadow = cssVar(tok.name);
    }
    if ((s.lineHeight || s["line-height"]) && !already(s.lineHeight || s["line-height"])) {
      const tok = exactTokenForPaintedProp("lineHeight", s.lineHeight || s["line-height"], tokens, n);
      if (tok) styles.lineHeight = cssVar(tok.name);
    }
    if ((s.letterSpacing || s["letter-spacing"]) && !already(s.letterSpacing || s["letter-spacing"])) {
      const tok = exactTokenForPaintedProp("letterSpacing", s.letterSpacing || s["letter-spacing"], tokens, n);
      if (tok) styles.letterSpacing = cssVar(tok.name);
    }
    if (Object.keys(styles).length) updates.push({ nodeIds: [n.id], styles });
  }
  return updates;
}

const WEIGHT_NUM = {
  thin: 100, extralight: 200, light: 300, normal: 400, regular: 400,
  medium: 500, semibold: 600, bold: 700, extrabold: 800, black: 900,
};

export function isCssVar(v) {
  return typeof v === "string" && /var\s*\(\s*--/.test(v);
}

export function inferTokenType(name) {
  const n = String(name || "");
  if (/^--color/.test(n)) return "color";
  if (/^--text-/.test(n)) return "fontSize";
  if (/^--spacing/.test(n)) return "spacing";
  if (/^--radius/.test(n)) return "radius";
  if (/^--font-weight/.test(n)) return "fontWeight";
  if (/^--font-style/.test(n)) return "fontStyle";
  if (/^--font-/.test(n)) return "fontFamily";
  if (/^--shadow/.test(n)) return "shadow";
  return null;
}

export function normalizeTokens(input) {
  if (!input) return [];
  const one = (t, fallbackName) => {
    if (!t) return null;
    const name = t.name || t.id || fallbackName;
    if (!name) return null;
    const value = t.value ?? t.cssValue ?? t.css;
    if (value == null || value === "") return null;
    return {
      type: t.type || inferTokenType(name),
      name: String(name).startsWith("--") ? String(name) : `--${name}`,
      value,
      family: t.family,
      paperValue: t.paperValue,
    };
  };
  if (typeof input === "string") return parseCssCustomProps(input);
  if (Array.isArray(input)) return input.map((t) => one(t)).filter(Boolean);
  if (Array.isArray(input.tokens)) return input.tokens.map((t) => one(t)).filter(Boolean);
  if (Array.isArray(input.proposedTokens)) return input.proposedTokens.map((t) => one(t)).filter(Boolean);
  if (input.tokens && typeof input.tokens === "object") {
    return Object.entries(input.tokens).map(([name, v]) => one(typeof v === "object" ? v : { value: v }, name)).filter(Boolean);
  }
  if (input.css || input.text) return parseCssCustomProps(input.css || input.text);
  return [];
}

export function parseCssCustomProps(css) {
  const out = [];
  const re = /(--[A-Za-z0-9_-]+)\s*:\s*([^;}{]+)/g;
  let m;
  while ((m = re.exec(String(css || "")))) {
    out.push({
      type: inferTokenType(m[1]),
      name: m[1],
      value: m[2].trim(),
    });
  }
  return out;
}

export function closestPxToken(tokens, px) {
  const n = Number(px);
  if (!Number.isFinite(n) || !tokens?.length) return null;
  return tokens.reduce((best, t) => {
    const v = parseFloat(t.value);
    if (!Number.isFinite(v)) return best;
    if (!best) return t;
    const d = Math.abs(v - n);
    const bd = Math.abs(parseFloat(best.value) - n);
    return d < bd || (d === bd && v > parseFloat(best.value)) ? t : best;
  }, null);
}

export function closestColorToken(tokens, color, { maxDist = 48 } = {}) {
  const c = parseColor(color);
  if (!c || !tokens?.length) return null;
  let best = null, bestD = Infinity;
  for (const t of tokens) {
    const tc = parseColor(t.value);
    if (!tc) continue;
    const d = colorDist(tc, c);
    if (d < bestD) { bestD = d; best = t; }
  }
  if (!best || bestD > maxDist) return null;
  return best;
}

export function skipThemeTokenNode(node) {
  const comp = String(node.component || "");
  const name = String(node.name || "");
  const s = node.style || {};
  if (/^(Image|Img)$/i.test(comp)) return "skip-image";
  const abs = /absolute/i.test(s.position || "");
  if (/scribble|underline-deco|ornament/i.test(name)) return "skip-scribble";
  if (/^SVG$/i.test(comp) && abs) return "skip-scribble";
  if (abs && s.pointerEvents === "none" && /svg|vector|scribble/i.test(`${comp} ${name}`)) {
    return "skip-scribble";
  }
  return null;
}

function singlePx(v) {
  if (v == null || isCssVar(v)) return null;
  const s = String(v).trim();
  if (!/^-?\d+(\.\d+)?px$/.test(s)) return null;
  return parseFloat(s);
}

function weightNumber(v) {
  if (v == null || isCssVar(v)) return null;
  if (typeof v === "number") return Number.isInteger(v) ? v : null;
  const raw = String(v).trim();
  if (/^[+-]?\d+$/.test(raw)) {
    const n = Number(raw);
    return Number.isSafeInteger(n) ? n : null;
  }
  return WEIGHT_NUM[raw.toLowerCase()] ?? null;
}

function isSpacerWidth(node) {
  const s = node.style || {};
  const w = singlePx(s.width);
  const h = singlePx(s.height);
  if (w == null || w <= 0 || w > 384) return false;
  if (h != null && h <= 32) return true;
  return /spacer|gap|bar/i.test(String(node.name || ""));
}

const TRANSPARENT_FILL = /^(transparent|none|initial|unset|inherit|rgba\(\s*0\s*,\s*0\s*,\s*0\s*,\s*0(?:\.0+)?\s*\))$/i;
const NAMED_SECTION = /^\d{2}\s*·/;

/** Paper / CSS fills that paint nothing. Do not bind or restore onto these. */
export function isUnpaintedFill(value) {
  if (value == null || value === "") return true;
  const raw = String(value).trim();
  if (TRANSPARENT_FILL.test(raw)) return true;
  const c = parseColor(raw);
  return Boolean(c && c.a === 0);
}

/** Exact RGB + alpha. Near hues are leftovers, not assumed fills (Pitfall #157). */
export function exactColorToken(tokens, color) {
  if (isUnpaintedFill(color)) return null;
  const key = colorKey(color);
  if (!key) return null;
  return (tokens || []).find((t) => (!t.type || t.type === "color") && colorKey(t.value) === key) || null;
}

export function isNamedSectionNode(node) {
  return NAMED_SECTION.test(String(node?.name || ""));
}

/** A wrapper that already contains two+ lander bands must stay unpainted. */
export function isSectionStack(node, children = []) {
  if (isNamedSectionNode(node)) return false;
  const named = (children || []).filter(isNamedSectionNode);
  return named.length >= 2;
}

export function isInheritedFill(node, parent, prop = "backgroundColor") {
  if (!node || !parent) return false;
  const child = node.style?.[prop] ?? node.style?.backgroundColor;
  const fromParent = parent.style?.[prop] ?? parent.style?.backgroundColor;
  if (isUnpaintedFill(child) || isUnpaintedFill(fromParent)) return false;
  return colorKey(child) === colorKey(fromParent);
}

export function dropInventedFillChanges(pass, unpaintedIds) {
  const ids = unpaintedIds instanceof Set ? unpaintedIds : new Set(unpaintedIds || []);
  const next = {
    changes: [...(pass?.changes || [])],
    skipped: [...(pass?.skipped || [])],
    leftovers: [...(pass?.leftovers || [])],
    updates: (pass?.updates || []).map((update) => ({
      nodeIds: [...(update.nodeIds || [])],
      styles: { ...(update.styles || {}) },
    })),
  };
  const invented = next.changes.filter((change) => (
    (change.property === "backgroundColor" || change.property === "fill")
    && ids.has(change.nodeId)
  ));
  if (!invented.length) return { ...next, invented: [] };
  const drop = new Set(invented.map((change) => `${change.nodeId}:${change.property}`));
  next.changes = next.changes.filter((change) => !drop.has(`${change.nodeId}:${change.property}`));
  for (const update of next.updates) {
    if (!ids.has(update.nodeIds?.[0])) continue;
    delete update.styles.backgroundColor;
    delete update.styles.fill;
  }
  next.updates = next.updates.filter((update) => Object.keys(update.styles || {}).length);
  next.invented = invented;
  return next;
}

/** JPEG outline boards stay raw. Still listed as skipped-board in the QA file. */
export function isSkippedTokenPassBoard(name) {
  return /^(Source · |Screenshots(\s·|$))/i.test(String(name || ""));
}

// 1.4 heading rule: titles get text-wrap: pretty so orphans do not sit
// on the last line. Preferred over pixel-identical Framer/Paper wraps.
export const TEXT_WRAP_PRETTY = "pretty";
export const HEADING_MIN_PX = 28;
const TEXT_XL_UP = new Set(["xl", "2xl", "3xl", "4xl", "5xl", "6xl", "7xl", "8xl", "9xl", "display", "display-xl"]);

export function fontSizeTokenStep(value) {
  const m = /--text-(display-xl|display|[a-z0-9]+)/i.exec(String(value || ""));
  return m ? m[1].toLowerCase() : null;
}

function isChromeLabel(node) {
  const name = String(node.name || "");
  if (/heading|title/i.test(name)) return false;
  const blob = `${name} ${node.component || ""}`;
  return /\b(nav|navbar|footer|button|btn|cta|label)\b/i.test(blob);
}

function isTextishNode(node) {
  const comp = String(node.component || "");
  if (!comp) return true;
  if (/^(Text|RichText|Paragraph|Heading|H[1-6])$/i.test(comp)) return true;
  if (/^(Frame|Rectangle|Image|Img|SVG|Div|Link|Button|NavLink)$/i.test(comp)) return false;
  return Boolean(node.style?.fontSize);
}

/** Text nodes plus frames that already carry type (caption / label). */
export function isPaperTextNode(node) {
  const comp = String(node.component || "");
  if (/^(Text|RichText|Paragraph|Heading|H[1-6])$/i.test(comp)) return true;
  if (node.textContent && String(node.textContent).trim()) {
    if (/^(Image|Img|SVG|Rectangle)$/i.test(comp)) return false;
    return true;
  }
  return isTextishNode(node);
}

export function shouldSetPrettyTextWrap(node, tokens = []) {
  if (skipThemeTokenNode(node)) return false;
  if (!isTextishNode(node)) return false;
  if (isChromeLabel(node)) return false;
  const name = String(node.name || "");
  if (/heading|title/i.test(name)) return true;
  const s = node.style || {};
  const step = fontSizeTokenStep(s.fontSize);
  if (step && TEXT_XL_UP.has(step)) return true;
  let px = singlePx(s.fontSize);
  if (px == null && s.fontSize) {
    const list = normalizeTokens(tokens).filter((t) => t.type === "fontSize");
    const tok = list.find((t) => cssVar(t.name) === s.fontSize || t.name === s.fontSize);
    if (tok) {
      const tokStep = fontSizeTokenStep(tok.name);
      if (tokStep && TEXT_XL_UP.has(tokStep)) return true;
      px = singlePx(tok.value);
    }
  }
  return px != null && px >= HEADING_MIN_PX;
}

export function exactPxToken(tokens, px) {
  const n = Number(px);
  if (!Number.isFinite(n) || !tokens?.length) return null;
  return tokens.find((t) => parseFloat(t.value) === n) || null;
}

export const SPACING_LEFTOVER_MIN = 128;

export const PAINTABLE_PROP_MAP = [
  ["fontSize", "fontSize"],
  ["fontFamily", "fontFamily"],
  ["fontWeight", "fontWeight"],
  ["color", "color"],
  ["fill", "fill"],
  ["backgroundColor", "fill"],
  ["gap", "gap"],
  ["rowGap", "gap"],
  ["columnGap", "gap"],
  ["padding", "padding"],
  ["paddingTop", "padding"],
  ["paddingRight", "padding"],
  ["paddingBottom", "padding"],
  ["paddingLeft", "padding"],
  ["borderRadius", "radius"],
  ["radius", "radius"],
  ["width", "width"],
];

function leftoverForSpacing(node, prop, value, spacingTokens) {
  const px = singlePx(value);
  if (px == null) return null;
  if (prop === "width" && isSpacerWidth(node) && !exactPxToken(spacingTokens, px)) {
    return "spacer-width-no-exact-token";
  }
  if (px > SPACING_LEFTOVER_MIN && !exactPxToken(spacingTokens, px)) {
    return "spacing-over-128-no-token";
  }
  return null;
}

export function leftoverWhyForProp(node, prop, value, tokens = []) {
  if (value == null || isCssVar(value)) return null;
  const list = normalizeTokens(tokens);
  const token = exactTokenForPaintedProp(prop, value, list, node);
  if (token) return null;
  const spacing = list.filter((t) => t.type === "spacing");
  if (/^(gap|rowGap|columnGap|padding|paddingTop|paddingRight|paddingBottom|paddingLeft|width)$/.test(prop)) {
    return leftoverForSpacing(node, prop, value, spacing)
      || (prop !== "width" || isSpacerWidth(node) ? "measured-value-no-exact-token" : null);
  }
  if (/^(fontSize|fontWeight|borderRadius|radius|lineHeight|letterSpacing)$/.test(prop)) {
    return "measured-value-no-exact-token";
  }
  return null;
}

export function exactTokenForPaintedProp(prop, value, tokens = [], node = {}) {
  if (value == null || isCssVar(value)) return null;
  const list = normalizeTokens(tokens);
  const of = (type) => list.filter((t) => t.type === type);
  if (prop === "fontSize") {
    const px = singlePx(value);
    return px == null ? null : exactPxToken(of("fontSize"), px);
  }
  if (prop === "fontFamily") {
    const face = String(value).split(",")[0].replace(/["']/g, "").trim();
    return of("fontFamily").find((t) => {
      const fam = t.family || String(t.value).split(",")[0].replace(/["']/g, "").trim();
      return fam && (face.includes(fam) || fam.includes(face.replace(/-(Bold|Medium|Regular|Light|SemiBold|Black)$/i, "")));
    }) || null;
  }
  if (prop === "fontWeight") {
    const n = weightNumber(value);
    return n == null ? null : of("fontWeight").find((t) => weightNumber(t.value) === n) || null;
  }
  if (prop === "color" || prop === "fill" || prop === "backgroundColor") {
    if (isUnpaintedFill(value)) return null;
    return exactColorToken(of("color"), value);
  }
  if (prop === "borderRadius" || prop === "radius") {
    const px = singlePx(value);
    return px == null ? null : exactPxToken(of("radius"), px);
  }
  if (/^(gap|rowGap|columnGap|padding|paddingTop|paddingRight|paddingBottom|paddingLeft)$/.test(prop)) {
    const px = singlePx(value);
    if (px == null) return null;
    return exactPxToken(of("spacing"), px);
  }
  if (prop === "width") {
    const px = singlePx(value);
    if (px == null || !isSpacerWidth(node)) return null;
    return exactPxToken(of("spacing"), px);
  }
  if (prop === "lineHeight") {
    const fontSize = resolveBoundTokenValue(node?.style?.fontSize ?? node?.fontSize, list)
      || node?.style?.fontSize
      || node?.fontSize;
    const pct = lineHeightToPercent(value, fontSize);
    if (!pct) return null;
    return of("lineHeight").find((t) => String(t.value) === pct) || null;
  }
  if (prop === "letterSpacing") {
    const fontSize = resolveBoundTokenValue(node?.style?.fontSize ?? node?.fontSize, list)
      || node?.style?.fontSize
      || node?.fontSize;
    const rem = letterSpacingToRem(value, fontSize);
    if (!rem) return null;
    return of("letterSpacing").find((t) => String(t.value) === rem) || null;
  }
  return null;
}

export const tokenForPaintedProp = exactTokenForPaintedProp;

function pushLeftover(leftovers, node, prop, value, why) {
  leftovers.push({
    nodeId: node.id,
    artboard: node.artboard || "",
    name: node.name || "",
    prop,
    value: String(value),
    why,
  });
}

// Map painted styles on landers / A/6 / Interactive components / Design Library
// to exact registered tokens. Unmatched measured literals stay raw and listed.
function childrenOf(nodeId, byId) {
  return [...byId.values()].filter((n) => n.parentId === nodeId);
}

function refuseFillBind(node, byId, prop) {
  if (isUnpaintedFill(node.style?.[prop])) return "unpainted-fill";
  if (isSectionStack(node, childrenOf(node.id, byId))) return "section-stack-fill";
  if (isNamedSectionNode(node)) return null;
  const parent = node.parentId ? byId.get(node.parentId) : null;
  if (isInheritedFill(node, parent, prop)) return "inherited-fill";
  return null;
}

/**
 * A fill the binder refuses to rebind (section stack / inherited fill,
 * Pitfall #157) must still be LISTED when it has an exact token match,
 * so token-pass QA reports it as an intentional raw literal instead of
 * `tokenable-raw-unlisted`. The value stays raw — nothing is painted.
 */
export function refusedFillLeftover(node, byId, prop, tokens = []) {
  const raw = node.style?.[prop];
  if (raw == null || isCssVar(raw) || isUnpaintedFill(raw)) return null;
  const reason = refuseFillBind(node, byId, prop);
  if (!reason) return null;
  const tok = exactTokenForPaintedProp(prop, String(raw), tokens, node);
  if (!tok) return null;
  return {
    nodeId: node.id,
    artboard: node.artboard || "",
    name: node.name || "",
    prop,
    value: String(raw),
    why: `fill-preserved-${reason}`,
    token: tok.name,
  };
}

export function themeTokenPass(nodes, tokens = []) {
  const list = normalizeTokens(tokens);
  const of = (type) => list.filter((t) => t.type === type);
  const changes = [];
  const skipped = [];
  const leftovers = [];
  const byNode = new Map();
  const byId = new Map((nodes || []).filter((n) => n?.id).map((n) => [n.id, n]));

  const assign = (node, property, from, tok) => {
    if (!tok) return false;
    const to = cssVar(tok.name);
    if (String(from) === to) return false;
    changes.push({
      nodeId: node.id,
      name: node.name || "",
      property,
      from: String(from),
      to,
      token: tok.name,
    });
    if (!byNode.has(node.id)) byNode.set(node.id, {});
    byNode.get(node.id)[property] = to;
    return true;
  };

  for (const node of nodes) {
    const reason = skipThemeTokenNode(node);
    if (reason) {
      skipped.push({ nodeId: node.id, name: node.name || "", reason });
      continue;
    }
    const s = node.style || {};
    if (s.fontSize && !isCssVar(s.fontSize)) {
      const tok = exactTokenForPaintedProp("fontSize", s.fontSize, list, node);
      if (tok) assign(node, "fontSize", s.fontSize, tok);
      else pushLeftover(leftovers, node, "fontSize", s.fontSize, "measured-value-no-exact-token");
    }
    if (s.color && !isCssVar(s.color) && !isUnpaintedFill(s.color)) {
      assign(node, "color", s.color, exactColorToken(of("color"), s.color));
    }
    if (s.fill && !isCssVar(s.fill) && !isUnpaintedFill(s.fill)) {
      const refused = refusedFillLeftover(node, byId, "fill", list);
      if (refused) {
        leftovers.push(refused);
      } else if (!refuseFillBind(node, byId, "fill")) {
        assign(node, "fill", s.fill, exactColorToken(of("color"), s.fill));
      }
    }
    if (s.backgroundColor && !isCssVar(s.backgroundColor) && !isUnpaintedFill(s.backgroundColor)) {
      const refused = refusedFillLeftover(node, byId, "backgroundColor", list);
      if (refused) {
        leftovers.push(refused);
      } else if (!refuseFillBind(node, byId, "backgroundColor")) {
        assign(node, "backgroundColor", s.backgroundColor, exactColorToken(of("color"), s.backgroundColor));
      }
    }
    if (isPaperTextNode(node) && isUnboundFontFamily(s.fontFamily)) {
      const tok = tokenForPaintedProp("fontFamily", s.fontFamily || "", list, node)
        || tokenForUnboundFont(node, list);
      if (tok) assign(node, "fontFamily", s.fontFamily || "", tok);
    } else if (s.fontFamily && !isCssVar(s.fontFamily)) {
      assign(node, "fontFamily", s.fontFamily, tokenForPaintedProp("fontFamily", s.fontFamily, list, node));
    }
    if (s.fontWeight && !isCssVar(s.fontWeight)) {
      const tok = exactTokenForPaintedProp("fontWeight", s.fontWeight, list, node);
      if (tok) assign(node, "fontWeight", s.fontWeight, tok);
      else pushLeftover(leftovers, node, "fontWeight", s.fontWeight, "measured-value-no-exact-token");
    }
    if (s.fontStyle && !isCssVar(s.fontStyle)) {
      const raw = String(s.fontStyle).toLowerCase();
      const tok = of("fontStyle").find((t) => String(t.value).toLowerCase() === raw);
      if (tok) assign(node, "fontStyle", s.fontStyle, tok);
    }
    if (s.borderRadius && !isCssVar(s.borderRadius)) {
      const tok = exactTokenForPaintedProp("borderRadius", s.borderRadius, list, node);
      if (tok) assign(node, "borderRadius", s.borderRadius, tok);
      else pushLeftover(leftovers, node, "borderRadius", s.borderRadius, "measured-value-no-exact-token");
    }
    if (s.radius && !isCssVar(s.radius)) {
      const tok = exactTokenForPaintedProp("radius", s.radius, list, node);
      if (tok) assign(node, "radius", s.radius, tok);
      else pushLeftover(leftovers, node, "radius", s.radius, "measured-value-no-exact-token");
    }
    for (const prop of ["gap", "rowGap", "columnGap", "padding", "paddingTop", "paddingRight", "paddingBottom", "paddingLeft"]) {
      if (!s[prop] || isCssVar(s[prop])) continue;
      const why = leftoverWhyForProp(node, prop, s[prop], list);
      if (why) {
        pushLeftover(leftovers, node, prop, s[prop], why);
        continue;
      }
      const tok = exactTokenForPaintedProp(prop, s[prop], list, node);
      if (tok) assign(node, prop, s[prop], tok);
      else pushLeftover(leftovers, node, prop, s[prop], "measured-value-no-exact-token");
    }
    if (s.width && !isCssVar(s.width) && isSpacerWidth(node)) {
      const why = leftoverWhyForProp(node, "width", s.width, list) || "spacer-width-preserved";
      pushLeftover(leftovers, node, "width", s.width, why);
    }
    if (s.boxShadow && !isCssVar(s.boxShadow) && of("shadow").length) {
      const tok = of("shadow").find((t) => t.value === s.boxShadow);
      if (tok) assign(node, "boxShadow", s.boxShadow, tok);
    }
    const leading = s.lineHeight ?? s["line-height"];
    if (leading && !isCssVar(leading)) {
      const tok = exactTokenForPaintedProp("lineHeight", leading, list, node);
      if (tok) assign(node, "lineHeight", leading, tok);
      else pushLeftover(leftovers, node, "lineHeight", leading, "measured-value-no-exact-token");
    }
    const tracking = s.letterSpacing ?? s["letter-spacing"];
    if (tracking && !isCssVar(tracking)) {
      const tok = exactTokenForPaintedProp("letterSpacing", tracking, list, node);
      if (tok) assign(node, "letterSpacing", tracking, tok);
      else if (!/^(normal|0(?:px|rem|em)?)$/i.test(String(tracking).trim())) {
        pushLeftover(leftovers, node, "letterSpacing", tracking, "measured-value-no-exact-token");
      }
    }
  }

  const updates = [...byNode.entries()].map(([id, styles]) => ({ nodeIds: [id], styles }));
  return { changes, skipped, leftovers, updates };
}

export function applyPassStyles(node, pass) {
  const style = { ...(node.style || {}) };
  for (const c of pass?.changes || []) {
    if (c.nodeId === node.id) style[c.property] = c.to;
  }
  return style;
}

function skipStatus(reason) {
  if (reason === "skip-image" || reason === "image") return "skip-image";
  if (reason === "skip-scribble" || reason === "scribble" || reason === "decorative-abs-svg") {
    return "skip-scribble";
  }
  return null;
}

/**
 * Census every tree node. Each id must be rebound | leftover | skip-image |
 * skip-scribble. Tree minus the QA file is a fail. A still-raw tokenable
 * hex/px that is not listed in leftovers is a defect.
 */
export function buildTokenPassQa({
  treeNodes = [],
  pass = { changes: [], skipped: [], leftovers: [] },
  tokens = [],
  skippedBoards = [],
  accounts,
} = {}) {
  const list = normalizeTokens(tokens);
  const skipById = new Map((pass.skipped || []).map((s) => [s.nodeId, s.reason]));
  const listedLeftover = new Set(
    (pass.leftovers || []).map((L) => `${L.nodeId}:${L.prop}`),
  );
  const nodes = accounts ? { ...accounts } : {};
  const leftovers = [];
  const defects = [];

  for (const node of treeNodes) {
    const id = node.id;
    if (!id) continue;
    if (accounts && !Object.prototype.hasOwnProperty.call(accounts, id)) continue;

    const skip = skipStatus(skipById.get(id) || skipThemeTokenNode(node));
    if (skip) {
      nodes[id] = skip;
      continue;
    }

    const style = applyPassStyles(node, pass);
    const nodeLeftovers = (pass.leftovers || [])
      .filter((L) => L.nodeId === id)
      .map((L) => ({
        nodeId: id,
        artboard: L.artboard || node.artboard || "",
        prop: L.prop,
        value: String(L.value),
        why: L.why,
      }));
    for (const [cssProp, reportProp] of PAINTABLE_PROP_MAP) {
      const raw = style[cssProp];
      if (raw == null || raw === "" || isCssVar(raw)) continue;
      if (nodeLeftovers.some((L) => L.prop === reportProp || L.prop === cssProp)) continue;
      if (TRANSPARENT_FILL.test(String(raw)) && /color|fill|background/i.test(cssProp)) continue;
      const why = leftoverWhyForProp({ ...node, style }, cssProp, raw, list)
        || (pass.leftovers || []).find((L) => L.nodeId === id && L.prop === cssProp)?.why;
      if (why) {
        nodeLeftovers.push({
          nodeId: id,
          artboard: node.artboard || "",
          prop: reportProp,
          value: String(raw),
          why,
        });
        continue;
      }
      if (tokenForPaintedProp(cssProp, raw, list, { ...node, style })) {
        const listed = listedLeftover.has(`${id}:${cssProp}`) || listedLeftover.has(`${id}:${reportProp}`);
        if (!listed) {
          defects.push({
            nodeId: id,
            artboard: node.artboard || "",
            prop: reportProp,
            value: String(raw),
            why: "tokenable-raw-unlisted",
          });
        }
      }
    }

    if (nodeLeftovers.length) {
      nodes[id] = "leftover";
      leftovers.push(...nodeLeftovers);
      continue;
    }
    nodes[id] = "rebound";
  }

  const treeIds = treeNodes.map((n) => n.id).filter(Boolean);
  const missing = treeIds.filter((id) => !Object.prototype.hasOwnProperty.call(nodes, id));
  const coverage = {
    treeNodes: treeIds.length,
    accounted: Object.keys(nodes).length,
    missing,
  };

  return {
    nodesTouchedCount: Object.keys(nodes).length,
    propsReboundCount: (pass.changes || []).filter((c) => c.property !== "textWrap").length,
    leftovers,
    coverage,
    nodes,
    skippedBoards,
    defects,
    ok: missing.length === 0 && defects.length === 0,
  };
}

export function tokenPassQaFails(qa) {
  return !qa || (qa.coverage?.missing?.length || 0) > 0 || (qa.defects?.length || 0) > 0 || qa.ok === false;
}

const STYLE_ATTR = /\sstyle="([^"]*)"/gi;
const CSS_TOKEN_PROPS = {
  "font-size": "fontSize",
  "font-family": "fontFamily",
  "font-weight": "fontWeight",
  color: "color",
  fill: "fill",
  "background-color": "backgroundColor",
  gap: "gap",
  "row-gap": "rowGap",
  "column-gap": "columnGap",
  padding: "padding",
  "padding-top": "paddingTop",
  "padding-right": "paddingRight",
  "padding-bottom": "paddingBottom",
  "padding-left": "paddingLeft",
  "border-radius": "borderRadius",
  "line-height": "lineHeight",
  "letter-spacing": "letterSpacing",
};

function parseStyleMap(css) {
  const out = new Map();
  for (const declaration of String(css || "").split(";")) {
    const i = declaration.indexOf(":");
    if (i < 1) continue;
    out.set(declaration.slice(0, i).trim().toLowerCase(), declaration.slice(i + 1).trim());
  }
  return out;
}

function serializeStyleMap(map) {
  return [...map].map(([prop, value]) => `${prop}: ${value}`).join("; ");
}

/** Catch-at-write: replace paintable px/hex with var(--token). Never touch 100% / fit-content / flex-start. */
export function bindInlineThemeTokens(html, tokens = [], node = {}) {
  const list = normalizeTokens(tokens);
  if (!list.length) return String(html || "");
  return String(html || "").replace(STYLE_ATTR, (full, css) => {
    const map = parseStyleMap(css);
    const painted = { ...node, style: { ...(node.style || {}) } };
    for (const [cssProp, jsProp] of Object.entries(CSS_TOKEN_PROPS)) {
      if (map.has(cssProp)) painted.style[jsProp] = map.get(cssProp);
    }
    let changed = false;
    for (const [cssProp, jsProp] of Object.entries(CSS_TOKEN_PROPS)) {
      if (!map.has(cssProp)) continue;
      const value = map.get(cssProp);
      if (!value || isCssVar(value)) continue;
      if (leftoverWhyForProp(painted, jsProp, value, list)) continue;
      const tok = tokenForPaintedProp(jsProp, value, list, painted);
      if (!tok) continue;
      map.set(cssProp, cssVar(tok.name));
      changed = true;
    }
    return changed ? ` style="${serializeStyleMap(map)}"` : full;
  });
}

export function applyThemeTokensScriptPath(fromHref = import.meta.url) {
  return join(dirname(fileURLToPath(fromHref)), "apply-theme-tokens.mjs");
}

export function requireApplyThemeTokensScript(scriptPath) {
  const p = scriptPath || applyThemeTokensScriptPath();
  if (!p || !existsSync(p)) {
    throw new Error(
      "apply-theme-tokens.mjs is missing — refuse to update_styles a subset. Token bind is not best-effort.",
    );
  }
  return p;
}

// Paper fontFamily tokens must be a catalog/local/Google face ("Inter").
// The mined CSS stack stays on `value` for HTML / tokens.css / rebuild.
export const PAPER_FONT_FALLBACKS = ["Inter", "Satoshi"];

export function firstNamedFace(value) {
  return baseFamily(value);
}

export function paperFontFamilyValue(token) {
  if (token == null) return "";
  if (typeof token === "string") return firstNamedFace(token);
  if (token.paperValue) return String(token.paperValue).trim();
  if (token.family) return String(token.family).trim();
  return firstNamedFace(token.value);
}

export function buildFontFamilyValue(token) {
  if (token == null) return "";
  if (typeof token === "string") return token;
  return String(token.value ?? "");
}

export const GENERIC_FONT_FAMILIES = new Set([
  "system sans-serif",
  "system serif",
  "system-ui",
  "ui-sans-serif",
  "ui-serif",
  "sans-serif",
  "serif",
  "monospace",
  "cursive",
  "fantasy",
  "-apple-system",
  "blinkmacsystemfont",
]);

export const PAPER_MONO_FACES = ["SF Mono", "Menlo", "ui-monospace"];

export function isCssFontStack(value) {
  const s = String(value || "").trim();
  if (!s) return false;
  return /,(?![^(]*\))/.test(s);
}

export function isUnboundFontFamily(value) {
  const s = String(value || "").trim();
  if (!s) return true;
  if (isCssVar(s)) return false;
  if (isCssFontStack(s)) return true;
  const face = firstNamedFace(s).toLowerCase();
  if (!face) return true;
  return GENERIC_FONT_FAMILIES.has(face);
}

export function paperThemeFonts(tokens = [], catalog) {
  const fonts = normalizeTokens(tokens).filter((t) => t.type === "fontFamily");
  const sansTok = fonts.find((f) => /^--font-sans\b/.test(f.name))
    || fonts.find((f) => /sans/.test(f.name));
  const serifTok = fonts.find((f) => /serif|display/.test(f.name) && !/sans/.test(f.name));
  const monoTok = fonts.find((f) => /mono/.test(f.name));

  const faceOf = (tok, fallback) => {
    const resolved = resolvePaperFontFamily(tok || fallback, catalog);
    return resolved.paperValue || firstNamedFace(fallback) || "Inter";
  };

  const sans = faceOf(sansTok, "Inter");
  const display = serifTok ? faceOf(serifTok, sans) : sans;

  let mono = null;
  if (monoTok) {
    const resolved = resolvePaperFontFamily(monoTok, catalog);
    if (resolved.paperValue && !isUnboundFontFamily(resolved.paperValue)) {
      mono = resolved.paperValue;
    }
  }
  if (!mono && catalog != null) {
    for (const face of PAPER_MONO_FACES) {
      const hit = catalogHasFace(catalog, face);
      if (hit) { mono = hit; break; }
    }
    if (!mono) mono = sans;
  }
  if (!mono) {
    const named = monoTok ? paperFontFamilyValue(monoTok) : "";
    mono = named && !isUnboundFontFamily(named) && !isCssFontStack(named) ? named : "SF Mono";
  }
  return { sans, display, mono };
}

export function fontRoleForNode(node) {
  const blob = `${node?.name || ""} ${node?.component || ""}`;
  if (/\b(code|mono|pre|kbd)\b/i.test(blob)) return "mono";
  if (/\b(heading|title|display|hero|h[1-3])\b/i.test(blob)) return "display";
  return "sans";
}

export function tokenForUnboundFont(node, tokens = []) {
  const list = normalizeTokens(tokens).filter((t) => t.type === "fontFamily");
  if (!list.length) return null;
  const value = node?.style?.fontFamily || node?.fontFamily || "";
  if (value && (isCssFontStack(value) || !isUnboundFontFamily(value))) {
    const hit = tokenForPaintedProp("fontFamily", value, list, node);
    if (hit) return hit;
  }
  const role = fontRoleForNode(node);
  if (role === "mono") {
    return list.find((t) => /mono/.test(t.name)) || list.find((t) => /sans/.test(t.name)) || list[0];
  }
  if (role === "display") {
    return list.find((t) => /serif|display/.test(t.name) && !/sans/.test(t.name))
      || list.find((t) => /sans/.test(t.name))
      || list[0];
  }
  return list.find((t) => /sans/.test(t.name)) || list[0];
}

export function bindPaperFontUpdates(nodes = [], tokens = [], { preferVar = true, catalog } = {}) {
  const fonts = normalizeTokens(tokens).filter((t) => t.type === "fontFamily");
  const changes = [];
  const skipped = [];
  const byNode = new Map();
  if (!fonts.length) return { updates: [], changes, skipped };
  for (const node of nodes) {
    if (!isPaperTextNode(node)) continue;
    const family = node.style?.fontFamily ?? node.fontFamily;
    if (!isUnboundFontFamily(family)) continue;
    const tok = tokenForUnboundFont(node, fonts);
    if (!tok) {
      skipped.push({ nodeId: node.id, reason: "no-font-token" });
      continue;
    }
    const resolved = resolvePaperFontFamily(tok, catalog);
    if (resolved.status === "unavailable") {
      skipped.push({
        nodeId: node.id,
        reason: "unavailable-face",
        requested: resolved.requested,
      });
      continue;
    }
    const to = preferVar
      ? cssVar(tok.name)
      : (resolved.paperValue || paperFontFamilyValue(tok));
    if (!to || String(family) === to) continue;
    changes.push({
      nodeId: node.id,
      name: node.name || "",
      property: "fontFamily",
      from: String(family || ""),
      to,
      token: tok.name,
    });
    byNode.set(node.id, { fontFamily: to });
  }
  const updates = [...byNode.entries()].map(([id, styles]) => ({ nodeIds: [id], styles }));
  return { updates, changes, skipped };
}

export function findUnboundFonts(nodes = [], tokens = [], { artboard } = {}) {
  const fonts = normalizeTokens(tokens).filter((t) => t.type === "fontFamily");
  if (!fonts.length) return [];
  const findings = [];
  for (const node of nodes) {
    if (!isPaperTextNode(node)) continue;
    const family = node.style?.fontFamily ?? node.fontFamily;
    if (!isUnboundFontFamily(family)) continue;
    findings.push({
      type: "unbound-font",
      severity: "high",
      node: node.id,
      name: node.name || "",
      artboard: node.artboard || artboard || "",
      detail: `fontFamily=${family || "(empty)"} — System Sans-Serif / generic / CSS stack while font tokens exist`,
    });
  }
  return findings;
}

/** Collapse CSS stacks / generics in write_html styles to a catalog face. */
export function bindInlinePaperFonts(html, tokens = [], catalog) {
  const list = normalizeTokens(tokens);
  const fonts = list.filter((t) => t.type === "fontFamily");
  const paper = paperThemeFonts(fonts, catalog);
  return String(html || "").replace(STYLE_ATTR, (full, css) => {
    const map = parseStyleMap(css);
    if (!map.has("font-family")) return full;
    const value = map.get("font-family");
    if (!value || isCssVar(value)) return full;
    if (!isUnboundFontFamily(value) && !isCssFontStack(value)) return full;
    let face = firstNamedFace(value);
    const tok = tokenForPaintedProp("fontFamily", value, list, {})
      || (isUnboundFontFamily(face) ? fonts.find((t) => /sans/.test(t.name)) : null);
    if (tok) {
      const resolved = resolvePaperFontFamily(tok, catalog);
      if (resolved.status === "unavailable") return full;
      face = resolved.paperValue || paperFontFamilyValue(tok);
    } else if (!face || isUnboundFontFamily(face)) {
      face = paper.sans || "Inter";
    }
    if (!face || isCssFontStack(face) || isUnboundFontFamily(face)) face = "Inter";
    if (map.get("font-family") === face) return full;
    map.set("font-family", face);
    return ` style="${serializeStyleMap(map)}"`;
  });
}

function unwrapMcpJson(result) {
  if (!result || typeof result !== "object") return {};
  if (result.fontsPerFamily || Array.isArray(result.errors)) return result;
  const items = result.content;
  if (Array.isArray(items)) {
    for (const item of items) {
      if (item?.type === "text") {
        try { return JSON.parse(item.text); } catch { return { text: item.text }; }
      }
    }
  }
  if (typeof result.text === "string") {
    try { return JSON.parse(result.text); } catch { /* keep */ }
  }
  return result;
}

export function parseFontFamilyInfo(result) {
  const data = unwrapMcpJson(result);
  const available = new Map();
  const unavailable = new Set();
  for (const [name, faces] of Object.entries(data.fontsPerFamily || {})) {
    if (Array.isArray(faces) && faces.length) available.set(name.toLowerCase(), name);
  }
  for (const err of data.errors || []) {
    const m = /Font family ["“]([^"”]+)["”] is not available/i.exec(String(err));
    if (m) unavailable.add(m[1].toLowerCase());
  }
  return { available, unavailable, raw: data };
}

export function catalogHasFace(catalog, name) {
  if (!catalog || !name) return null;
  const key = String(name).toLowerCase();
  if (catalog.available instanceof Map) return catalog.available.get(key) || null;
  if (catalog instanceof Map) {
    const hit = catalog.get(key);
    if (typeof hit === "string") return hit;
    if (hit?.status === "available" && hit.name) return hit.name;
    return null;
  }
  if (catalog instanceof Set) {
    for (const n of catalog) if (String(n).toLowerCase() === key) return n;
    return null;
  }
  if (Array.isArray(catalog)) {
    const hit = catalog.find((n) => String(n).toLowerCase() === key);
    return hit || null;
  }
  return null;
}

export function resolvePaperFontFamily(nameOrToken, catalog, { fallbacks = PAPER_FONT_FALLBACKS } = {}) {
  const bare = paperFontFamilyValue(nameOrToken);
  if (!bare) return { status: "empty", paperValue: null };
  if (catalog == null) return { status: "unprobed", paperValue: bare };
  const exact = catalogHasFace(catalog, bare);
  if (exact) return { status: "catalog", paperValue: exact };
  for (const fb of fallbacks) {
    const hit = catalogHasFace(catalog, fb);
    if (hit) return { status: "fallback", paperValue: hit, requested: bare, fallback: hit };
  }
  return { status: "unavailable", paperValue: null, requested: bare };
}

export function applyPaperFontFamilies(tokens = [], catalog, opts) {
  return tokens.map((t) => {
    if (t.type !== "fontFamily") return t;
    const resolved = resolvePaperFontFamily(t, catalog, opts);
    if (resolved.status === "unavailable") {
      return {
        ...t,
        paperToken: false,
        paperSkip: "unavailable-face",
        paperRequested: resolved.requested,
      };
    }
    const next = { ...t, paperValue: resolved.paperValue };
    if (resolved.status === "fallback") {
      next.paperFallback = resolved.fallback;
      next.paperRequested = resolved.requested;
    }
    return next;
  });
}

export function paperCreateTokens(proposed) {
  return proposed
    .filter((t) => t.paperToken !== false && t.type !== "shadow" && t.type !== "fontStyle")
    .map((t) => ({
      type: t.type,
      name: t.name,
      value: t.type === "fontFamily" ? paperFontFamilyValue(t) : (t.paperValue || t.value),
    }))
    .filter((t) => t.value != null && t.value !== "");
}

export function tokenWritePlan(desired = [], existing = [], { replace = false } = {}) {
  if (replace) {
    return {
      deletes: existing.filter((t) => t?.name).map((t) => ({ name: t.name, delete: true })),
      updates: [],
      creates: desired,
    };
  }
  const names = new Set(existing.map((t) => t?.name).filter(Boolean));
  return {
    deletes: [],
    updates: desired.filter((t) => names.has(t.name)).map((t) => ({
      name: t.name,
      value: t.value,
    })),
    creates: desired.filter((t) => !names.has(t.name)),
  };
}

export function buildLibraryReport({
  file,
  artboards = [],
  nodes = 0,
  styledNodes = 0,
  minUses = 3,
  mined,
  leftoverMined,
  components,
}) {
  const proposed = proposeLibraryTokens(mined, { minUses, leftoverMined });
  return {
    file,
    artboards,
    nodes,
    styledNodes,
    minUses,
    scalePolicy: {
      mined: ["color", "fontFamily", "fontWeight", "fontStyle", "fontSize-extras", "lineHeight", "letterSpacing"],
      semanticColorRoles: SEMANTIC_COLOR_ROLES.map((r) => r.name).concat(
        ["--color-ink-soft", "--color-ink-strong"],
        TAILWIND_SEMANTIC_COLORS.map((r) => r.name),
      ),
      tailwindDefault: ["fontSize", "spacing", "radius", "shadow"],
      displayType: ["--text-7xl", "--text-8xl", "--text-9xl", "--text-10xl", "--text-11xl", "--text-12xl"],
      lineHeightUnit: "%",
      letterSpacingUnit: "rem",
      rebuild: "bind exact px to a token (Tailwind or mined extra); do not snap an off-scale size onto 7xl/8xl",
    },
    palette: {
      backgrounds: mined.colors || [],
      text: mined.textColors || [],
    },
    semanticRoles: proposed.filter((t) => t.source === "semantic-role"),
    typography: {
      families: mined.fontFamilies || [],
      weights: mined.fontWeights || [],
      styles: mined.fontStyles || [],
      sizes: proposed.filter((t) => t.type === "fontSize"),
      extraSizes: proposed.filter((t) => t.type === "fontSize" && t.source === "mined"),
      lineHeights: proposed.filter((t) => t.type === "lineHeight"),
      letterSpacings: proposed.filter((t) => t.type === "letterSpacing"),
    },
    spacing: proposed.filter((t) => t.type === "spacing"),
    radii: proposed.filter((t) => t.type === "radius"),
    shadows: proposed.filter((t) => t.type === "shadow"),
    proposedTokens: proposed,
    components: components || {
      total: 0,
      shared: [],
      inPage: [],
      byLevel: { atom: 0, molecule: 0, organism: 0 },
      atoms: [],
      molecules: [],
      organisms: [],
      top: [],
    },
  };
}
