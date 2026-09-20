#!/usr/bin/env node
// Render the library frames from templates + a library.json, with no agent
// authoring involved.
//
// The first build of these frames cost two agents ~75k tokens and ~105 tool
// calls each to author HTML that is fundamentally the same layout every time.
// Only the DATA changes per site. This renders the same sheet deterministically
// from `templates/library/**` and writes it in a handful of paced calls.
//
// Usage:
//   node render-library.mjs --library library.json --file-id <id>
//                           [--target <artboardId>] [--kind foundations|components]
//                           [--dry-run --out-dir rendered/]
//                           [--name "Design Library"] [--pace 1500]
//
// Step 1.4 foundations may create/update `Design Library`.
// Every other kind requires an explicit existing target.

import { mkdirSync, readFileSync, readdirSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { call, getFileId, setFileId } from "./mcp-client.mjs";
import {
  DESIGN_LIBRARY_NAME,
  findDesignLibrary,
  foundationsSheetContext,
  paintSheetSizes,
  updateDesignLibrary,
  writeFoundationSections,
} from "./library-sheet.mjs";
import {
  bindThemeToTokens,
  paperFontFamilyValue,
  paperThemeFonts,
  tokenRebindUpdates,
  withCssVar,
} from "./library-tokens.mjs";
import { seedPaperLibraryTokens } from "./paper-token-writer.mjs";

const __dir = dirname(fileURLToPath(import.meta.url));
const TEMPLATES = join(__dir, "..", "templates", "library");

const argv = process.argv.slice(2);
const arg = (name, fallback) => {
  const i = argv.indexOf(`--${name}`);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : fallback;
};

const libraryPath = resolve(arg("library", "library.json"));
const kind = arg("kind", "foundations");
// kit-* renders the neutral starting base: placeholders and names only, no site
// data and no palette. Everything else renders a real site's mined library.
const isKit = kind.startsWith("kit");
const dryRun = argv.includes("--dry-run");
const outDir = arg("out-dir", "rendered");
const pace = parseInt(arg("pace", "1500"), 10);
const log = (...a) => console.error("·", ...a);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

if (arg("file-id")) setFileId(arg("file-id"));
const fileId = arg("file-id") || process.env.PAPER_FILE_ID || getFileId();

if (!isKit && !existsSync(libraryPath)) {
  console.error(`render-library.mjs requires an existing --library JSON file: ${libraryPath}`);
  process.exit(1);
}

// A kit with an explicit target needs no mined data.
const lib = isKit && !existsSync(libraryPath)
  ? { proposedTokens: [], artboards: [], components: {} }
  : JSON.parse(readFileSync(libraryPath, "utf8"));

// Deliberately greyscale. The kit is a starting base dropped into any project,
// so it must not carry the palette of whichever site it was first built from.
const NEUTRAL = {
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

// Placeholder inventory. Edit here to change what a fresh library starts with.
const n = (name) => ({ name });
const KIT = {
  atoms: ["text label", "heading", "eyebrow / kicker", "logo mark", "icon", "image", "divider", "list item"].map(n),
  buttons: ["primary", "secondary", "tertiary / text", "icon button", "form submit", "link + arrow"].map(n),
  molecules: ["nav link list", "social row", "stat block", "rating row", "form field", "card meta", "breadcrumb", "pagination"].map(n),
  cards: ["blog card", "team member card", "service / feature card", "testimonial card", "pricing card", "media block"].map(n),
  regions: [
    { name: "announcement bar", h: 64 },
    { name: "nav bar", h: 96 },
    { name: "hero", h: 320 },
    { name: "stats band", h: 220 },
    { name: "CTA band", h: 180 },
    { name: "footer", h: 300 },
  ],
  colour: ["surface", "surface alt", "ink", "accent", "border", "muted text"].map(n),
  typography: ["display family", "body family", "type scale", "weights", "line height", "letter spacing"].map(n),
  spacing: ["spacing scale", "container widths", "grid / gutters", "breakpoints"].map(n),
  elevation: ["shadow", "radius"].map(n),
};

// ---------- tiny template engine ----------
// {{path.to.value}}                     — substitution
// {{#each list}} … {{/each}}            — repeat, with {{.field}} inside
// {{#if path}} … {{/if}}                — conditional block
const get = (ctx, path) =>
  path.split(".").reduce((o, k) => (o == null ? undefined : o[k]), ctx);

function render(tpl, ctx) {
  let out = tpl;

  out = out.replace(/\{\{#each\s+([\w.]+)\}\}([\s\S]*?)\{\{\/each\}\}/g, (_, path, body) => {
    const list = get(ctx, path);
    if (!Array.isArray(list)) return "";
    return list.map((item, i) =>
      body
        .replace(/\{\{\.index1\}\}/g, String(i + 1))
        .replace(/\{\{\.([\w.]+)\}\}/g, (__, f) => {
          const v = get(item, f);
          return v == null ? "" : String(v);
        })
        // theme/global refs still resolve inside a repeat
        .replace(/\{\{([\w.]+)\}\}/g, (__, p) => {
          const v = get(ctx, p);
          return v == null ? "" : String(v);
        }),
    ).join("");
  });

  out = out.replace(/\{\{#if\s+([\w.]+)\}\}([\s\S]*?)\{\{\/if\}\}/g, (_, path, body) => {
    const v = get(ctx, path);
    return v && (!Array.isArray(v) || v.length) ? body : "";
  });

  out = out.replace(/\{\{([\w.]+)\}\}/g, (_, path) => {
    const v = get(ctx, path);
    return v == null ? "" : String(v);
  });

  return out;
}

// ---------- theme, derived from the mined palette ----------
// Without this the kit stays hard-coded to the first site it was built from.
function deriveTheme(l) {
  const colors = (l.proposedTokens || []).filter((t) => t.type === "color");
  const pick = (re, fallback) => colors.find((c) => re.test(c.name))?.value || fallback;
  const paperFonts = paperThemeFonts(l.proposedTokens || []);
  const namedAccent = pick(/^--color-accent$/, null);

  // An accent is the colour that CONTRASTS with the dominant one, not simply
  // the most saturated. Picking by saturation chose a dark teal (0.76) over the
  // site's gold (0.51) — but that teal is the same hue as the ink, so it reads
  // as the brand base, not an accent. Score = chroma × hue-distance from ink.
  const rgb = (hex) => {
    const m = /^#([0-9a-f]{6})$/i.exec((hex || "").trim());
    if (!m) return null;
    return {
      r: parseInt(m[1].slice(0, 2), 16),
      g: parseInt(m[1].slice(2, 4), 16),
      b: parseInt(m[1].slice(4, 6), 16),
    };
  };
  const hueOf = (c) => {
    const mx = Math.max(c.r, c.g, c.b), mn = Math.min(c.r, c.g, c.b), d = mx - mn;
    if (d === 0) return 0;
    let h;
    if (mx === c.r) h = ((c.g - c.b) / d) % 6;
    else if (mx === c.g) h = (c.b - c.r) / d + 2;
    else h = (c.r - c.g) / d + 4;
    return ((h * 60) + 360) % 360;
  };
  const chromaOf = (c) => {
    const mx = Math.max(c.r, c.g, c.b), mn = Math.min(c.r, c.g, c.b);
    return mx === 0 ? 0 : (mx - mn) / mx;
  };
  const lumOf = (c) => (0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b) / 255;

  const inkRgb = rgb(pick(/--color-ink$/, "#0D2C35"));
  const inkHue = inkRgb ? hueOf(inkRgb) : 0;

  let accent = null, bestScore = 0;
  for (const c of colors) {
    const v = rgb(c.value);
    if (!v) continue;
    const l = lumOf(v);
    if (l < 0.12 || l > 0.95) continue; // near-black / near-white are not accents
    const ch = chromaOf(v);
    if (ch < 0.2) continue;
    let dh = Math.abs(hueOf(v) - inkHue);
    if (dh > 180) dh = 360 - dh;
    const score = ch * (dh / 180);
    if (score > bestScore) { bestScore = score; accent = c.value; }
  }

  return {
    ink: pick(/--color-ink$/, "#0D2C35"),
    accent: namedAccent || accent || pick(/--color-accent/, "#B99E5A"),
    surface: pick(/--color-surface$/, "#FFFFFF"),
    surfaceAlt: pick(/--color-surface-2$/, "#F3F8F9"),
    border: pick(/--color-subtle$/, "#DDE4E5"),
    muted: pick(/--color-text-muted$/, "#647275"),
    body: pick(/--color-text-accent$/, "#395963"),
    // Paper write: catalog faces only. Build stacks stay on token.value.
    display: paperFonts.display,
    sans: paperFonts.sans,
    mono: paperFonts.mono,
  };
}

// ---------- build the context the templates consume ----------
const T = (type) => (lib.proposedTokens || []).filter((t) => t.type === type);
const SEMANTIC_COLOR_NAME = /--color-(surface-alt|surface-muted|overlay|danger|warning|success|info|muted|text-subtle|text-secondary|ink-soft|ink-strong)$/;
const isTextColorName = (name) => /text/.test(String(name || ""));
const isSemanticColor = (t) => t.source === "semantic-role" || SEMANTIC_COLOR_NAME.test(t.name);
const colorSwatch = (t, badge) => withCssVar({
  ...t,
  badge,
  mergedNote: t.merged?.length ? `merged ${t.merged.join(", ")}` : "",
});
// site-* sheets show REAL components but keep neutral chrome, so the labels read
// as a spec sheet rather than competing with the components themselves.
const inventoryPath = arg("inventory");
const isSite = kind.startsWith("site");
const hexTheme = isKit || isSite ? NEUTRAL : { ...deriveTheme(lib), borderStrong: "#BDBDBD" };
const bound = isKit || isSite
  ? hexTheme
  : { ...bindThemeToTokens(hexTheme, lib.proposedTokens || []), borderStrong: hexTheme.borderStrong };
const theme = { ...bound, ...paperThemeFonts(isKit || isSite ? [] : (lib.proposedTokens || [])) };

// Resolve real node geometry so clones don't stretch to fill their flex parent.
let inventoryCtx = {};
if (inventoryPath) {
  const inv = JSON.parse(readFileSync(resolve(inventoryPath), "utf8"));
  const DARK = "#0D2C35";
  const groups = ["atoms", "buttons", "molecules", "cards", "regions"];
  const all = groups.flatMap((g) => (inv[g] || []).map((it) => ({ ...it, _group: g })));

  const sized = [];
  for (let i = 0; i < all.length; i += 8) {
    const chunk = all.slice(i, i + 8);
    await Promise.all(chunk.map(async (it) => {
      try {
        const res = await call("get_node_info", { nodeId: it.id });
        let d = {};
        for (const item of res.content ?? []) {
          if (item.type === "text") { try { d = JSON.parse(item.text); } catch {} }
        }
        const w = Math.round(d.width || 200);
        const h = Math.round(d.height || 100);
        // Container FITS the component. Fixed cells cropped anything bigger —
        // a 627x252 testimonial card lost its right third inside a 400x480 box.
        // Minimums stop tiny atoms from collapsing to a sliver; the max keeps a
        // full-width region inside the artboard's 1472px content box.
        const pad = it._group === "regions" ? 16 : 24;
        const isRegion = it._group === "regions";
        const cw = Math.min(Math.max(w + pad * 2, isRegion ? 0 : it._group === "atoms" ? 220 : 260), 1472);
        // Regions get no minimum height — a 46px announcement bar should not be
        // padded out to the same box as a 614px footer.
        const ch = isRegion ? h + pad * 2 : Math.max(h + pad * 2, it._group === "atoms" ? 120 : 140);
        sized.push({
          ...it,
          w, h, cw, ch, pad,
          // A default+hover pair plus the 12px gutter between them.
          bw: cw * 2 + 12,
          bg: it.dark ? DARK : NEUTRAL.surfaceAlt,
          missing: !d.width,
        });
      } catch {
        sized.push({ ...it, w: 200, h: 100, bg: NEUTRAL.surfaceAlt, missing: true });
      }
    }));
  }
  const missing = sized.filter((s) => s.missing);
  if (missing.length) log(`WARNING: ${missing.length} node(s) not resolvable: ${missing.map((m) => m.id).join(", ")}`);

  for (const g of groups) inventoryCtx[g] = sized.filter((s) => s._group === g);
  inventoryCtx.site = inv.site || "";
  log(`inventory: ${sized.length - missing.length}/${sized.length} node(s) resolved`);
}

const foundations = (kind === "foundations" || kind === "kit-foundations")
  && (isKit || !existsSync(libraryPath))
  ? foundationsSheetContext(lib, { seed: true })
  : null;

const ctx = foundations || {
  theme,
  ...(isKit ? KIT : {}),
  ...inventoryCtx,
  site: lib.file || "site",
  pages: (lib.artboards || []).length,
  nodes: lib.nodes || 0,
  colorsSurface: T("color").filter((t) => !/text/.test(t.name) && t.source !== "semantic-role")
    .map((t) => withCssVar({ ...t, mergedNote: t.merged?.length ? `merged ${t.merged.join(", ")}` : "" })),
  colorsText: T("color").filter((t) => /text/.test(t.name) && t.source !== "semantic-role").map(withCssVar),
  colorsSemantic: T("color").filter((t) => t.source === "semantic-role").map(withCssVar),
  colorsSurfaceMined: T("color").filter((t) => !isTextColorName(t.name) && !isSemanticColor(t))
    .map((t) => colorSwatch(t, "MINED")),
  colorsSurfaceSemantic: T("color").filter((t) => !isTextColorName(t.name) && isSemanticColor(t))
    .map((t) => colorSwatch(t, "SEMANTIC")),
  colorsTextMined: T("color").filter((t) => isTextColorName(t.name) && !isSemanticColor(t))
    .map((t) => colorSwatch(t, "MINED")),
  colorsTextSemantic: T("color").filter((t) => isTextColorName(t.name) && isSemanticColor(t))
    .map((t) => colorSwatch(t, "SEMANTIC")),
  families: T("fontFamily").map((t) => withCssVar({
    ...t,
    label: t.family || t.value.split(",")[0].replace(/["']/g, ""),
    paperValue: paperFontFamilyValue(t) || t.family || "Inter",
  })),
  sizes: paintSheetSizes(T("fontSize"), theme, { useVar: true }),
  sizesScale: paintSheetSizes(T("fontSize"), theme, { useVar: true }),
  sizesDisplay: paintSheetSizes(
    T("fontSize").filter((t) => t.sheetGroup === "display"),
    theme,
    { useVar: true },
  ),
  weights: T("fontWeight").map(withCssVar),
  styles: T("fontStyle").map(withCssVar),
  spacing: T("spacing").filter((t) => t.onSheet !== false).map((t) => withCssVar({
    ...t,
    barW: Math.min(Math.max(parseFloat(t.value) || 0, 0) * 4, 240),
  })),
  radii: T("radius").filter((t) => t.onSheet !== false).map(withCssVar),
  shadows: T("shadow").filter((t) => t.onSheet !== false).map(withCssVar),
  counts: {
    colors: T("color").length,
    sizes: T("fontSize").filter((t) => t.onSheet !== false).length,
    families: T("fontFamily").length,
    weights: T("fontWeight").length,
    spacing: T("spacing").filter((t) => t.onSheet !== false).length,
    shadows: T("shadow").filter((t) => t.onSheet !== false).length,
    radii: T("radius").filter((t) => t.onSheet !== false).length,
  },
  components: lib.components || { atoms: [], molecules: [], organisms: [] },
};

// ---------- render ----------
const dir = join(TEMPLATES, kind);
if (!existsSync(dir)) {
  console.error(`no templates at ${dir}`);
  process.exit(1);
}
const files = readdirSync(dir).filter((f) => f.endsWith(".html")).sort();
if (!files.length) {
  console.error(`no .html templates in ${dir}`);
  process.exit(1);
}

const chunks = files.map((f) => ({
  name: f.replace(/^\d+-|\.html$/g, ""),
  html: render(readFileSync(join(dir, f), "utf8"), ctx).trim(),
}));

if (dryRun) {
  mkdirSync(resolve(outDir), { recursive: true });
  for (const c of chunks) {
    const p = join(resolve(outDir), `${c.name}.html`);
    writeFileSync(p, c.html, "utf8");
  }
  console.log(JSON.stringify({
    kind, templates: files.length, outDir: resolve(outDir),
    chunks: chunks.map((c) => ({ name: c.name, bytes: c.html.length })),
    theme,
  }, null, 1));
  process.exit(0);
}

// ---------- write into Paper ----------
function payload(result) {
  for (const item of result.content ?? []) {
    if (item.type === "text") {
      try { return JSON.parse(item.text); } catch { return { text: item.text }; }
    }
  }
  return {};
}

const TREE_LINE = /^(\s*)(\w+)\s+"([^"]*)"\s+\(([^)]+)\)\s+(\d+(?:\.\d+)?)×(\d+(?:\.\d+)?)/;

function parseTree(summary) {
  const out = [];
  for (const raw of String(summary || "").split("\n")) {
    const m = TREE_LINE.exec(raw);
    if (!m) continue;
    out.push({ id: m[4], name: m[3], component: m[2] });
  }
  return out;
}

async function rebindWrittenTokens(rootId) {
  if (!rootId || isKit || isSite) return 0;
  try {
    const tree = parseTree(payload(await call("get_tree_summary", { nodeId: rootId, depth: 8 })).summary);
    const ids = [rootId, ...tree.map((n) => n.id)];
    const styles = payload(await call("get_computed_styles", { nodeIds: ids })).styles || {};
    const nodes = ids.map((id) => {
      const meta = tree.find((n) => n.id === id) || { id, name: "" };
      return { ...meta, style: styles[id] || {} };
    });
    const updates = tokenRebindUpdates(nodes, lib.proposedTokens || []);
    if (!updates.length) return 0;
    for (let i = 0; i < updates.length; i += 40) {
      await call("update_styles", { updates: updates.slice(i, i + 40) });
    }
    log(`  rebound ${updates.length} token style(s) on ${rootId}`);
    return updates.length;
  } catch (err) {
    log(`  token rebind skipped: ${err.message.split("\n")[0]}`);
    return 0;
  }
}

let target = arg("target");
const requestedName = arg("name", kind === "components" ? "LIBRARY — Components" : DESIGN_LIBRARY_NAME);
let foundationInfo = null;
let tokenSeed = null;
if (kind === "foundations") {
  foundationInfo = payload(await call("get_basic_info", { ...(fileId ? { fileId } : {}) }));
  tokenSeed = await seedPaperLibraryTokens({
    call,
    proposed: lib.proposedTokens || [],
    existing: foundationInfo.tokens?.items || [],
  });
  log(`Paper tokens synchronized: ${tokenSeed.desired} desired, ${tokenSeed.created} created, ${tokenSeed.updated} updated`);
}
if (kind === "foundations" && !target) {
  const info = foundationInfo;
  const existing = findDesignLibrary(info.artboards || []);
  const updated = await updateDesignLibrary({
    call,
    fileId,
    boards: info.artboards || [],
    lib,
    pace,
    log,
  });
  target = updated.id;
  if (existing && updated.id !== existing.id) {
    throw new Error("1.4 created a second Design Library — refuse");
  }
  log(`1.4 update ${DESIGN_LIBRARY_NAME} → ${target}`);
  await call("finish_working_on_nodes", { ...(fileId ? { fileId } : {}) });
  console.log(JSON.stringify({ kind, target, mode: "update", sections: updated.written.length, written: updated.written, tokenSeed, theme }, null, 1));
  process.exit(0);
}
if (!target) {
  console.error(
    `render-library.mjs --kind ${kind} requires an existing --target artboard (${requestedName}). `
      + "Only step 1.4 foundations may create Design Library through updateDesignLibrary.",
  );
  process.exit(1);
}

const written = (kind === "foundations" || kind === "kit-foundations")
  ? await writeFoundationSections({
      call,
      fileId,
      targetId: target,
      lib,
      seed: false,
      replace: false, // same-name replace is now the default inside the writer
      pace,
      log,
    })
  : [];
if (!(kind === "foundations" || kind === "kit-foundations")) {
  for (let i = 0; i < chunks.length; i++) {
    const c = chunks[i];
    const tmp = join(process.cwd(), `.render-${kind}-${i}.html`);
    writeFileSync(tmp, c.html, "utf8");
    try {
      const res = payload(await call("write_html", {
        html: c.html, targetNodeId: target, mode: "insert-children",
      }));
      const id = res.createdNodes?.[0]?.id;
      if (id) await call("rename_nodes", { updates: [{ nodeId: id, name: c.name }] });
      written.push({ name: c.name, id });
      log(`  ✓ ${c.name}${id ? ` → ${id}` : ""}`);
    } catch (err) {
      log(`  ✗ ${c.name}: ${err.message.split("\n")[0]}`);
    }
    if (i < chunks.length - 1) await sleep(pace);
  }
}

// Content height is data-dependent — never guess a pixel height.
try {
  await call("update_styles", { updates: [{ nodeIds: [target], styles: { height: "fit-content" } }] });
} catch {}
await call("finish_working_on_nodes", {});

console.log(JSON.stringify({ kind, target, sections: written.length, written, tokenSeed, theme }, null, 1));
