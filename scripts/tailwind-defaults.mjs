// Tailwind default scales for Stage L / 1.4.
//
// Colors, families, weights, and font styles stay site-mined.
// Type *sizes* start as this Tailwind set. Off-scale painted sizes (80px
// between 72 and 96) are injected as extra `--text-{px}` tokens (source:
// mined) and shown with a red MINED pill. Spacing, radius, and elevation
// stay this file — never a per-node census.
//
// Values match Tailwind v3/v4 defaults at a 16px root.
// Paper `create_tokens` rejects dots in names (`--spacing-0.5` fails).
// Use `paperName` (`--spacing-0-5`) when writing tokens; keep `step` as
// the Tailwind key (`0.5`).

export const TAILWIND_SPACING = [
  { step: "0", px: 0, rem: "0" },
  { step: "px", px: 1, rem: "1px" },
  { step: "0.5", px: 2, rem: "0.125rem" },
  { step: "1", px: 4, rem: "0.25rem" },
  { step: "1.5", px: 6, rem: "0.375rem" },
  { step: "2", px: 8, rem: "0.5rem" },
  { step: "2.5", px: 10, rem: "0.625rem" },
  { step: "3", px: 12, rem: "0.75rem" },
  { step: "3.5", px: 14, rem: "0.875rem" },
  { step: "4", px: 16, rem: "1rem" },
  { step: "5", px: 20, rem: "1.25rem" },
  { step: "6", px: 24, rem: "1.5rem" },
  { step: "7", px: 28, rem: "1.75rem" },
  { step: "8", px: 32, rem: "2rem" },
  { step: "9", px: 36, rem: "2.25rem" },
  { step: "10", px: 40, rem: "2.5rem" },
  { step: "11", px: 44, rem: "2.75rem" },
  { step: "12", px: 48, rem: "3rem" },
  { step: "14", px: 56, rem: "3.5rem" },
  { step: "16", px: 64, rem: "4rem" },
  { step: "20", px: 80, rem: "5rem" },
  { step: "24", px: 96, rem: "6rem" },
  { step: "28", px: 112, rem: "7rem" },
  { step: "32", px: 128, rem: "8rem" },
  { step: "36", px: 144, rem: "9rem" },
  { step: "40", px: 160, rem: "10rem" },
  { step: "44", px: 176, rem: "11rem" },
  { step: "48", px: 192, rem: "12rem" },
  { step: "52", px: 208, rem: "13rem" },
  { step: "56", px: 224, rem: "14rem" },
  { step: "60", px: 240, rem: "15rem" },
  { step: "64", px: 256, rem: "16rem" },
  { step: "72", px: 288, rem: "18rem" },
  { step: "80", px: 320, rem: "20rem" },
  { step: "96", px: 384, rem: "24rem" },
];

// Readable specimen — not every half-step. The token set above is complete.
export const SPACING_SHEET_STEPS = new Set([
  "0", "0.5", "1", "2", "3", "4", "5", "6", "8", "10", "12",
  "16", "20", "24", "32", "40", "48", "64", "80", "96",
]);

// Tailwind fontSize defaults plus display 10xl–12xl (160 / 192 / 224).
// Do not add --text-display / --text-display-xl names.
export const TAILWIND_FONT_SIZES = [
  { step: "xs", px: 12, rem: "0.75rem", lineHeight: "1rem" },
  { step: "sm", px: 14, rem: "0.875rem", lineHeight: "1.25rem" },
  { step: "base", px: 16, rem: "1rem", lineHeight: "1.5rem" },
  { step: "lg", px: 18, rem: "1.125rem", lineHeight: "1.75rem" },
  { step: "xl", px: 20, rem: "1.25rem", lineHeight: "1.75rem" },
  { step: "2xl", px: 24, rem: "1.5rem", lineHeight: "2rem" },
  { step: "3xl", px: 30, rem: "1.875rem", lineHeight: "2.25rem" },
  { step: "4xl", px: 36, rem: "2.25rem", lineHeight: "2.5rem" },
  { step: "5xl", px: 48, rem: "3rem", lineHeight: "1" },
  { step: "6xl", px: 60, rem: "3.75rem", lineHeight: "1" },
  { step: "7xl", px: 72, rem: "4.5rem", lineHeight: "1" },
  { step: "8xl", px: 96, rem: "6rem", lineHeight: "1" },
  { step: "9xl", px: 128, rem: "8rem", lineHeight: "1" },
  { step: "10xl", px: 160, rem: "10rem", lineHeight: "1" },
  { step: "11xl", px: 192, rem: "12rem", lineHeight: "1" },
  { step: "12xl", px: 224, rem: "14rem", lineHeight: "1" },
];

export const FONT_SIZE_SHEET_STEPS = new Set([
  "xs", "sm", "base", "lg", "xl", "2xl", "3xl", "4xl", "5xl", "6xl",
  "7xl", "8xl", "9xl", "10xl", "11xl", "12xl",
]);

// Big-title set: 7xl–12xl. Specimens stay named --text-Nxl, never --text-display.
export const FONT_SIZE_DISPLAY_STEPS = new Set([
  "7xl", "8xl", "9xl", "10xl", "11xl", "12xl",
]);

// Always-on SEMANTIC swatches (Tailwind 500s). Leftover site hexes override
// a role when they match; otherwise every run still ships these five.
export const TAILWIND_SEMANTIC_COLORS = [
  { name: "--color-danger", value: "#EF4444", twClass: "red-500" },
  { name: "--color-warning", value: "#F59E0B", twClass: "amber-500" },
  { name: "--color-success", value: "#22C55E", twClass: "green-500" },
  { name: "--color-info", value: "#3B82F6", twClass: "blue-500" },
  { name: "--color-muted", value: "#6B7280", twClass: "gray-500" },
];

export const DISPLAY_FONT_SIZES = [];

export const TAILWIND_RADII = [
  { step: "none", px: 0, rem: "0px", css: "0px" },
  { step: "sm", px: 2, rem: "0.125rem", css: "2px" },
  { step: "DEFAULT", px: 4, rem: "0.25rem", css: "4px" },
  { step: "md", px: 6, rem: "0.375rem", css: "6px" },
  { step: "lg", px: 8, rem: "0.5rem", css: "8px" },
  { step: "xl", px: 12, rem: "0.75rem", css: "12px" },
  { step: "2xl", px: 16, rem: "1rem", css: "16px" },
  { step: "3xl", px: 24, rem: "1.5rem", css: "24px" },
  { step: "full", px: 9999, rem: "9999px", css: "9999px" },
];

// Paper create_tokens has no shadow type — CSS / library.json only.
export const TAILWIND_SHADOWS = [
  { step: "sm", css: "0 1px 2px 0 rgb(0 0 0 / 0.05)" },
  { step: "DEFAULT", css: "0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)" },
  { step: "md", css: "0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)" },
  { step: "lg", css: "0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)" },
  { step: "xl", css: "0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)" },
  { step: "2xl", css: "0 25px 50px -12px rgb(0 0 0 / 0.25)" },
];

export function paperTokenName(prefix, step) {
  const slug = String(step).replace(/\./g, "-");
  if (step === "DEFAULT") return prefix;
  return `${prefix}-${slug}`;
}

function closestByPx(table, px) {
  const n = Number(px);
  if (!Number.isFinite(n)) return null;
  return table.reduce((best, row) => {
    const d = Math.abs(row.px - n);
    const bd = Math.abs(best.px - n);
    return d < bd || (d === bd && row.px > best.px) ? row : best;
  }, table[0]);
}

export function closestSpacing(px) {
  const row = closestByPx(TAILWIND_SPACING, px);
  if (!row) return null;
  return {
    ...row,
    name: paperTokenName("--spacing", row.step),
    value: `${row.px}px`,
    twClass: row.step === "DEFAULT" ? "" : row.step,
  };
}

export function closestFontSize(px) {
  const row = closestByPx(TAILWIND_FONT_SIZES, px);
  if (!row) return null;
  return {
    ...row,
    name: `--text-${row.step}`,
    value: `${row.px}px`,
    twClass: `text-${row.step}`,
  };
}

export function closestRadius(px) {
  const row = closestByPx(TAILWIND_RADII, px);
  if (!row) return null;
  const twClass = row.step === "DEFAULT" ? "rounded" : `rounded-${row.step}`;
  return {
    ...row,
    name: paperTokenName("--radius", row.step),
    value: row.css,
    twClass,
  };
}

export function defaultSpacingTokens() {
  return TAILWIND_SPACING.map((row) => ({
    type: "spacing",
    name: paperTokenName("--spacing", row.step),
    value: `${row.px}px`,
    step: row.step,
    rem: row.rem,
    source: "tailwind-default",
    onSheet: SPACING_SHEET_STEPS.has(row.step),
  }));
}

export function defaultFontSizeTokens() {
  const tw = TAILWIND_FONT_SIZES.map((row) => ({
    type: "fontSize",
    name: `--text-${row.step}`,
    value: `${row.px}px`,
    step: row.step,
    rem: row.rem,
    lineHeight: row.lineHeight,
    source: "tailwind-default",
    sheetGroup: FONT_SIZE_DISPLAY_STEPS.has(row.step) ? "display" : "scale",
    onSheet: FONT_SIZE_SHEET_STEPS.has(row.step),
  }));
  return tw;
}

export function fontSizePx(value) {
  const s = String(value || "").trim();
  if (!s || /var\s*\(/i.test(s)) return null;
  const n = parseFloat(s);
  if (!Number.isFinite(n)) return null;
  if (/rem$/i.test(s)) return Math.round(n * 16);
  if (/%$/.test(s) || /em$/i.test(s)) return null;
  return Math.round(n);
}

const PRESET_FONT_PX = new Set(TAILWIND_FONT_SIZES.map((row) => row.px));

/** Off-scale painted sizes (80 between 72 and 96) become extra tokens. */
export function extraFontSizeTokens(ranked = [], { minPx = 10, maxPx = 240 } = {}) {
  const extras = [];
  const seen = new Set();
  for (const entry of ranked || []) {
    const px = fontSizePx(entry.value);
    if (px == null || px < minPx || px > maxPx) continue;
    if (PRESET_FONT_PX.has(px) || seen.has(px)) continue;
    seen.add(px);
    extras.push({
      type: "fontSize",
      name: `--text-${px}`,
      value: `${px}px`,
      step: String(px),
      rem: `${px / 16}rem`,
      lineHeight: px >= 48 ? "1" : undefined,
      source: "mined",
      sheetGroup: px >= 72 ? "display" : "scale",
      onSheet: true,
      uses: entry.count,
    });
  }
  return extras;
}

export function mergeFontSizeTokens(defaults = [], extras = []) {
  const byPx = new Map();
  for (const token of defaults || []) {
    const px = fontSizePx(token.value);
    if (px == null) continue;
    byPx.set(px, token);
  }
  for (const token of extras || []) {
    const px = fontSizePx(token.value);
    if (px == null || byPx.has(px)) continue;
    byPx.set(px, token);
  }
  return [...byPx.values()].sort((a, b) => parseFloat(b.value) - parseFloat(a.value));
}

export function defaultRadiusTokens() {
  return TAILWIND_RADII.map((row) => ({
    type: "radius",
    name: paperTokenName("--radius", row.step),
    value: row.css,
    step: row.step,
    rem: row.rem,
    source: "tailwind-default",
    onSheet: true,
  }));
}

export function defaultShadowTokens() {
  return TAILWIND_SHADOWS.map((row) => ({
    type: "shadow",
    name: paperTokenName("--shadow", row.step),
    value: row.css,
    step: row.step,
    source: "tailwind-default",
    onSheet: true,
    paperToken: false,
  }));
}
