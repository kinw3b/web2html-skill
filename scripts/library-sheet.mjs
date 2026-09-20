// Design Library sheet — step 1.4 create/update.
//
// Step 1.4 writes templates/library/foundations/*.html into an
// artboard named exactly `Design Library`. The layout shell ships locally in
// templates/library/foundations. Never clone it from another Paper file.
//
// Creation paints greyscale MINED slots + Tailwind scales before the
// authoritative update rebinds mined colors / families / weights / styles,
// desktop line-height / letter-spacing, and SEMANTIC roles.
// It does not census spacing, type sizes, radius, or elevation.

import { readdirSync, readFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  DESIGN_LIBRARY_NAME,
  LIBRARY_WIDTH,
  PARK_BUFFER,
  contentOrigin,
  isLibraryName,
  libraryPark,
  mcpPayload,
} from "./rulers.mjs";
import {
  defaultFontSizeTokens,
  defaultRadiusTokens,
  defaultShadowTokens,
  defaultSpacingTokens,
  mergeFontSizeTokens,
  TAILWIND_SEMANTIC_COLORS,
} from "./tailwind-defaults.mjs";
import { cssVar, paperFontFamilyValue, paperThemeFonts, bindThemeToTokens, withCssVar, ensureTailwindSemanticColors, assertFoundationsContract } from "./library-tokens.mjs";

const __dir = dirname(fileURLToPath(import.meta.url));
export const FOUNDATIONS_DIR = join(__dir, "..", "templates", "library", "foundations");
export const DESIGN_LIBRARY_REFERENCE_HTML = join(
  __dir,
  "..",
  "templates",
  "library",
  "reference",
  "design-library.html",
);

export const NEUTRAL_THEME = {
  ink: "#1A1A1A",
  accent: "#1A1A1A",
  surface: "#FFFFFF",
  surfaceAlt: "#F5F5F5",
  border: "#E3E3E3",
  borderStrong: "#BDBDBD",
  muted: "#8A8A8A",
  body: "#5C5C5C",
  display: "Inter",
  sans: "Inter",
  mono: "SF Mono",
};

// Greyscale placeholders — not Yearning Outfit / #6052FF.
const SEED_MINED_SURFACE = [
  { name: "--color-surface", value: "#FFFFFF" },
  { name: "--color-surface-2", value: "#F5F5F5" },
  { name: "--color-accent", value: "#1A1A1A" },
  { name: "--color-border", value: "#E3E3E3" },
];
const SEED_MINED_TEXT = [
  { name: "--color-ink", value: "#1A1A1A" },
  { name: "--color-text-primary", value: "#1A1A1A" },
  { name: "--color-text-muted", value: "#8A8A8A" },
];
const SEED_SEMANTIC_SURFACE = [
  ...TAILWIND_SEMANTIC_COLORS,
  { name: "--color-surface-alt", value: "#FBFBFB" },
  { name: "--color-surface-muted", value: "#F2F2F2" },
  { name: "--color-overlay", value: "#1A1A1A99" },
];
const SEED_SEMANTIC_TEXT = [
  { name: "--color-text-subtle", value: "#999999" },
  { name: "--color-text-secondary", value: "#666666" },
  { name: "--color-ink-soft", value: "#333333" },
  { name: "--color-ink-strong", value: "#111111" },
];

const MINED_PILL_FILL = "#E11D2E";
const MINED_TYPES = new Set(["color", "fontFamily", "fontWeight", "fontStyle", "lineHeight", "letterSpacing"]);

export function minedPillHtml(theme = NEUTRAL_THEME, label = "MINED") {
  const sans = theme.sans || "Inter";
  return `<div style="font-family:${sans}; font-size:var(--text-xs); font-weight:700; letter-spacing:0.12em; color:#FFFFFF; background:${MINED_PILL_FILL}; padding:2px 6px; border-radius:999px;">${label}</div>`;
}

export function semanticPillHtml(theme = NEUTRAL_THEME, label = "SEMANTIC") {
  const sans = theme.sans || "Inter";
  const muted = theme.muted || "#8A8A8A";
  const border = theme.border || "#E3E3E3";
  return `<div style="font-family:${sans}; font-size:var(--text-xs); font-weight:700; letter-spacing:0.12em; color:${muted}; border:1px solid ${border}; padding:2px 6px;">${label}</div>`;
}

export function requireFileId(fileId, who = "library-sheet") {
  if (!fileId) throw new Error(`${who} needs fileId — sticky-file otherwise hits the project ruler`);
  return fileId;
}

export function findDesignLibrary(boards = []) {
  return (boards || []).find((b) => b.name === DESIGN_LIBRARY_NAME) || null;
}

export function renderTemplate(tpl, ctx) {
  let out = tpl;

  out = out.replace(/\{\{#each\s+([\w.]+)\}\}([\s\S]*?)\{\{\/each\}\}/g, (_, path, body) => {
    const list = path.split(".").reduce((o, k) => (o == null ? undefined : o[k]), ctx);
    if (!Array.isArray(list)) return "";
    return list.map((item, i) =>
      body
        .replace(/\{\{\.index1\}\}/g, String(i + 1))
        .replace(/\{\{\.([\w.]+)\}\}/g, (__, f) => {
          const v = f.split(".").reduce((o, k) => (o == null ? undefined : o[k]), item);
          return v == null ? "" : String(v);
        })
        .replace(/\{\{([\w.]+)\}\}/g, (__, p) => {
          const v = p.split(".").reduce((o, k) => (o == null ? undefined : o[k]), ctx);
          return v == null ? "" : String(v);
        }),
    ).join("");
  });

  out = out.replace(/\{\{#if\s+([\w.]+)\}\}([\s\S]*?)\{\{\/if\}\}/g, (_, path, body) => {
    const v = path.split(".").reduce((o, k) => (o == null ? undefined : o[k]), ctx);
    return v && (!Array.isArray(v) || v.length) ? body : "";
  });

  out = out.replace(/\{\{([\w.]+)\}\}/g, (_, path) => {
    const v = path.split(".").reduce((o, k) => (o == null ? undefined : o[k]), ctx);
    return v == null ? "" : String(v);
  });

  return out;
}

function colorToken(name, value, { source, uses = 0 } = {}) {
  return { type: "color", name, value, uses, source };
}

export function seedTokens() {
  const mined = [
    ...SEED_MINED_SURFACE.map((t) => colorToken(t.name, t.value, { source: "seed-mined" })),
    ...SEED_MINED_TEXT.map((t) => colorToken(t.name, t.value, { source: "seed-mined" })),
  ];
  const semantic = [
    ...SEED_SEMANTIC_SURFACE.map((t) => colorToken(t.name, t.value, { source: "semantic-role" })),
    ...SEED_SEMANTIC_TEXT.map((t) => colorToken(t.name, t.value, { source: "semantic-role" })),
  ];
  const out = [
    ...mined,
    ...semantic,
    {
      type: "fontFamily",
      name: "--font-sans",
      value: "Inter, system-ui, sans-serif",
      paperValue: "Inter",
      family: "Inter",
      source: "seed",
    },
    { type: "fontWeight", name: "--font-weight-normal", value: "400", source: "seed" },
    { type: "fontWeight", name: "--font-weight-medium", value: "500", source: "seed" },
    ...defaultFontSizeTokens(),
    ...defaultSpacingTokens(),
    ...defaultRadiusTokens(),
    ...defaultShadowTokens(),
  ];
  assertFoundationsContract(out);
  return out;
}

function minedPlusDefaults(proposed = []) {
  const mined = (proposed || []).filter((t) => MINED_TYPES.has(t.type));
  const colors = ensureTailwindSemanticColors(mined.filter((t) => t.type === "color"));
  const rest = mined.filter((t) => t.type !== "color");
  const extraSizes = (proposed || []).filter((t) => t.type === "fontSize" && t.source === "mined");
  const tokens = [
    ...colors,
    ...rest,
    ...mergeFontSizeTokens(defaultFontSizeTokens(), extraSizes),
    ...defaultSpacingTokens(),
    ...defaultRadiusTokens(),
    ...defaultShadowTokens(),
  ];
  assertFoundationsContract(tokens);
  return tokens;
}

function isTextColorName(name = "") {
  return /text|ink/i.test(name);
}

function isSemanticColor(t) {
  return t?.source === "semantic-role";
}

function paint(token, { useVar }) {
  return {
    ...token,
    cssVar: useVar ? cssVar(token.name) : token.value,
  };
}

const SIZE_WRAP = /^(xl|2xl|3xl|4xl|5xl|6xl|7xl|8xl|9xl|10xl|11xl|12xl)$/;

export function paintSheetSizes(tokens = [], theme = NEUTRAL_THEME, { useVar = true } = {}) {
  return (tokens || [])
    .filter((t) => t.onSheet !== false)
    .slice()
    .sort((a, b) => parseFloat(b.value) - parseFloat(a.value))
    .map((t) => paint({
      ...t,
      wrap: SIZE_WRAP.test(t.step) ? "text-wrap:pretty;" : "",
      specimen: "Aa",
      displayBadge: t.sheetGroup === "display" && t.source !== "mined"
        ? `<div style="font-family:${theme.sans}; font-size:var(--text-xs); font-weight:700; letter-spacing:0.12em; color:${theme.muted}; border:1px solid ${theme.border}; padding:2px 6px;">DISPLAY</div>`
        : "",
      minedBadge: t.source === "mined" ? minedPillHtml(theme) : "",
    }, { useVar }));
}

function colorSwatch(token, badge, { useVar, theme = NEUTRAL_THEME }) {
  return {
    ...paint(token, { useVar }),
    badge,
    badgeHtml: badge === "MINED" ? minedPillHtml(theme) : semanticPillHtml(theme, badge),
    mergedNote: token.merged?.length ? `merged ${token.merged.join(", ")}` : "",
  };
}

export function foundationsSheetContext(lib = {}, { seed = false, useVar } = {}) {
  const tokens = seed ? seedTokens() : minedPlusDefaults(lib.proposedTokens || []);
  const paintVar = useVar ?? !seed;
  const T = (type) => tokens.filter((t) => t.type === type);
  const paperFonts = paperThemeFonts(tokens);
  const hexTheme = { ...NEUTRAL_THEME, ...paperFonts };
  // Colors → var(--token) so 2.1 design-system.html consumes tokens.css.
  // Faces stay catalog names so Paper write_html can paint (Pitfall #88).
  const theme = paintVar
    ? { ...bindThemeToTokens(hexTheme, tokens), ...paperFonts }
    : hexTheme;

  return {
    theme,
    site: lib.file || "site",
    pages: (lib.artboards || []).length,
    nodes: lib.nodes || 0,
    colorsSurfaceMined: T("color")
      .filter((t) => !isTextColorName(t.name) && !isSemanticColor(t))
      .map((t) => colorSwatch(t, "MINED", { useVar: paintVar, theme })),
    colorsSurfaceSemantic: T("color")
      .filter((t) => !isTextColorName(t.name) && isSemanticColor(t))
      .map((t) => colorSwatch(t, "SEMANTIC", { useVar: paintVar, theme })),
    colorsTextMined: T("color")
      .filter((t) => isTextColorName(t.name) && !isSemanticColor(t))
      .map((t) => colorSwatch(t, "MINED", { useVar: paintVar, theme })),
    colorsTextSemantic: T("color")
      .filter((t) => isTextColorName(t.name) && isSemanticColor(t))
      .map((t) => colorSwatch(t, "SEMANTIC", { useVar: paintVar, theme })),
    families: T("fontFamily").map((t) => paint({
      ...t,
      label: t.family || String(t.value).split(",")[0].replace(/["']/g, ""),
      paperValue: paperFontFamilyValue(t) || t.family || "Inter",
    }, { useVar: paintVar })),
    sizesScale: paintSheetSizes(T("fontSize"), theme, { useVar: paintVar }),
    sizesDisplay: paintSheetSizes(
      T("fontSize").filter((t) => t.sheetGroup === "display"),
      theme,
      { useVar: paintVar },
    ),
    weights: T("fontWeight").map((t) => paint(t, { useVar: paintVar })),
    styles: T("fontStyle").map((t) => paint(t, { useVar: paintVar })),
    lineHeights: T("lineHeight").map((t) => paint({
      ...t,
      minedBadge: t.source === "mined" ? minedPillHtml(theme) : "",
    }, { useVar: paintVar })),
    letterSpacings: T("letterSpacing").map((t) => paint({
      ...t,
      minedBadge: t.source === "mined" ? minedPillHtml(theme) : "",
    }, { useVar: paintVar })),
    spacing: T("spacing").filter((t) => t.onSheet !== false).map((t) => paint(t, { useVar: paintVar })),
    radii: T("radius").filter((t) => t.onSheet !== false).map((t) => paint(t, { useVar: paintVar })),
    shadows: T("shadow").filter((t) => t.onSheet !== false).map((t) => paint(t, { useVar: paintVar })),
    counts: {
      colors: T("color").length,
      sizes: T("fontSize").filter((t) => t.onSheet !== false).length,
      families: T("fontFamily").length,
      weights: T("fontWeight").length,
      lineHeights: T("lineHeight").length,
      letterSpacings: T("letterSpacing").length,
      spacing: T("spacing").filter((t) => t.onSheet !== false).length,
      shadows: T("shadow").filter((t) => t.onSheet !== false).length,
      radii: T("radius").filter((t) => t.onSheet !== false).length,
    },
    tokens,
  };
}

export function listFoundationTemplates(dir = FOUNDATIONS_DIR) {
  if (!existsSync(dir)) return [];
  return readdirSync(dir).filter((f) => f.endsWith(".html")).sort();
}

export function renderFoundationsChunks(lib = {}, opts = {}) {
  const ctx = foundationsSheetContext(lib, opts);
  const files = listFoundationTemplates(opts.dir);
  return {
    ctx,
    chunks: files.map((f) => ({
      name: f.replace(/^\d+-|\.html$/g, ""),
      file: f,
      html: renderTemplate(readFileSync(join(opts.dir || FOUNDATIONS_DIR, f), "utf8"), ctx).trim(),
    })),
  };
}

async function pinLibrary({ call, fileId, board, x, y, log = () => {} }) {
  requireFileId(fileId, "pinLibrary");
  await call("update_styles", {
    fileId,
    updates: [{
      nodeIds: [board.id],
      styles: {
        left: `${x}px`,
        top: `${y}px`,
        width: `${LIBRARY_WIDTH}px`,
      },
    }],
  });
  log(`library ${DESIGN_LIBRARY_NAME}  x=${x} y=${y}`);
}

export async function writeFoundationSections({
  call,
  fileId,
  targetId,
  lib = {},
  seed = false,
  replace = false,
  pace = 0,
  log = () => {},
} = {}) {
  requireFileId(fileId, "writeFoundationSections");
  if (!targetId) throw new Error("writeFoundationSections needs targetId");
  const kids = mcpPayload(await call("get_children", { fileId, nodeId: targetId })).children || [];
  // prior-run: a Stage L pull appended a second colour/type scale instead of
  // replacing the P-0 seed. Always drop same-named foundation sections
  // (colour, typography, …) before insert. `replace: true` still wipes all.
  if (replace && kids.length) {
    await call("delete_nodes", { fileId, nodeIds: kids.map((k) => k.id).filter(Boolean) });
    log(`cleared ${kids.length} Design Library child(ren)`);
  }
  const leftover = replace
    ? []
    : (mcpPayload(await call("get_children", { fileId, nodeId: targetId })).children || []);
  const byName = new Map();
  for (const k of leftover) {
    const arr = byName.get(k.name) || [];
    arr.push(k);
    byName.set(k.name, arr);
  }
  const { chunks } = renderFoundationsChunks(lib, { seed, useVar: !seed });
  const written = [];
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  for (let i = 0; i < chunks.length; i++) {
    const c = chunks[i];
    const existing = byName.get(c.name) || [];
    const existingIds = existing.map((k) => k.id).filter(Boolean);
    if (existingIds.length) {
      await call("delete_nodes", { fileId, nodeIds: existingIds });
      log(`replaced ${existingIds.length} existing ${c.name} section(s)`);
      byName.delete(c.name);
    }
    const res = mcpPayload(await call("write_html", {
      fileId,
      html: c.html,
      targetNodeId: targetId,
      mode: "insert-children",
    }));
    const id = res.createdNodes?.[0]?.id || res.id || res.nodeId;
    if (id) {
      await call("rename_nodes", { fileId, updates: [{ nodeId: id, name: c.name }] });
    }
    written.push({ name: c.name, id });
    log(`  ✓ ${c.name}${id ? ` → ${id}` : ""}`);
    if (pace && i < chunks.length - 1) await sleep(pace);
  }
  try {
    await call("update_styles", {
      fileId,
      updates: [{ nodeIds: [targetId], styles: { height: "fit-content" } }],
    });
  } catch {}
  return written;
}

export async function ensureDesignLibrary({
  call,
  fileId,
  boards = [],
  log = () => {},
} = {}) {
  if (!call) throw new Error("ensureDesignLibrary needs call()");
  requireFileId(fileId, "ensureDesignLibrary");
  const board = findDesignLibrary(boards);
  if (!board) return null;
  const origin = contentOrigin(boards);
  const park = libraryPark({ boards, originX: origin.left, originY: origin.top });
  const y = Math.max(origin.top, PARK_BUFFER);
  const pin = { x: park.x, y };
  await pinLibrary({ call, fileId, board, x: pin.x, y: pin.y, log });
  return { id: board.id, name: DESIGN_LIBRARY_NAME, x: pin.x, y: pin.y, created: false };
}

async function createDesignLibrary({
  call,
  fileId,
  boards = [],
  pace = 0,
  log = () => {},
} = {}) {
  const origin = contentOrigin(boards);
  const park = libraryPark({ boards, originX: origin.left, originY: origin.top });
  const made = mcpPayload(await call("create_artboard", {
    fileId,
    name: DESIGN_LIBRARY_NAME,
    styles: {
      width: `${LIBRARY_WIDTH}px`,
      height: "4000px",
      backgroundColor: NEUTRAL_THEME.surface,
      display: "flex",
      flexDirection: "column",
      gap: "64px",
      padding: "64px",
    },
  }));
  const id = made.id || made.nodeId || made.createdNodes?.[0]?.id;
  if (!id) throw new Error(`create_artboard returned no id for ${DESIGN_LIBRARY_NAME}`);
  const board = { id, name: DESIGN_LIBRARY_NAME };
  log(`library ${DESIGN_LIBRARY_NAME} created`);
  await pinLibrary({ call, fileId, board, x: park.x, y: park.y, log });
  const written = await writeFoundationSections({
    call, fileId, targetId: id, seed: true, pace, log,
  });
  return { ...board, x: park.x, y: park.y, created: true, written };
}

export async function updateDesignLibrary({
  call,
  fileId,
  boards = [],
  lib = {},
  pace = 1500,
  log = () => {},
} = {}) {
  if (!call) throw new Error("updateDesignLibrary needs call()");
  requireFileId(fileId, "updateDesignLibrary");
  let board = findDesignLibrary(boards);
  if (!board) {
    const seeded = await createDesignLibrary({ call, fileId, boards, log, pace });
    board = { id: seeded.id, name: DESIGN_LIBRARY_NAME };
  }
  const written = await writeFoundationSections({
    call,
    fileId,
    targetId: board.id,
    lib,
    seed: false,
    replace: true,
    pace,
    log,
  });
  return { id: board.id, name: DESIGN_LIBRARY_NAME, written, updated: true };
}

export { DESIGN_LIBRARY_NAME, isLibraryName, libraryPark, withCssVar };
