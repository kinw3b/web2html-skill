#!/usr/bin/env node
// Mine imported artboards for site-specific colors and fonts, then attach
// the default Tailwind scales for type sizes, spacing, radius, and elevation.
//
// Colors, families, weights, and font styles come from the file.
// Desktop lander also mines line-height (%) and letter-spacing (rem).
// After brand colors, leftover homepage / A/6 hexes fill a small semantic
// role set, then a Tailwind floor of five SEMANTIC colors so token-pass can bind
// them. Do not invent a grey ramp. Type sizes start as the Tailwind set;
// off-scale painted sizes (80px between 72 and 96) inject as `--text-{px}`
// with source mined. Do not census gap / padding / radius / boxShadow.
// Opaque fills and alpha tints of the same RGB stay separate tokens
// (--color-accent vs --color-accent-soft). Capture HTML restores those
// paints when Paper already collapsed them onto one var. Pitfall #154.
//
// Read-only by default. Pass --write-tokens to create them in Paper.
//
// Usage:
//   node extract-library.mjs [--depth 10] [--json library.json]
//                            [--min-uses 3] [--write-tokens]
//                            [--replace-tokens] [--prefix ""]

import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { applyCapturePaintWitness, resolveCaptureProjectRoot } from "./capture-paints.mjs";
import { call, setFileId } from "./mcp-client.mjs";
import {
  applyPaperFontFamilies,
  bindPaperFontUpdates,
  buildLibraryReport,
  mineFromStyledNodes,
  paperCreateTokens,
  paperFontFamilyValue,
  parseFontFamilyInfo,
  resolveBoundFontFamily,
  resolveBoundTokenValue,
  tokenWritePlan,
} from "./library-tokens.mjs";
import { refusesPaperFile } from "./bind-paper-fonts.mjs";
import { applyPaperTokenWritePlan } from "./paper-token-writer.mjs";
import { isLibraryMineArtboard } from "./token-pass-targets.mjs";

const argv = process.argv.slice(2);
const arg = (name, fallback) => {
  const i = argv.indexOf(`--${name}`);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : fallback;
};

const depth = Math.min(parseInt(arg("depth", "10"), 10), 10);
const minUses = parseInt(arg("min-uses", "3"), 10);
const jsonOut = arg("json", "library.json");
const writeTokens = argv.includes("--write-tokens");
const replaceTokens = argv.includes("--replace-tokens");
const log = (...a) => console.error("·", ...a);

function payload(result) {
  for (const item of result.content ?? []) {
    if (item.type === "text") {
      try { return JSON.parse(item.text); } catch { return { text: item.text }; }
    }
  }
  return {};
}

// `Frame "about-us" (2-0) 1600×482` → structure without a call per node.
const LINE = /^(\s*)(\w+)\s+"([^"]*)"\s+\(([^)]+)\)\s+(\d+(?:\.\d+)?)×(\d+(?:\.\d+)?)/;

function parseTree(summary) {
  const out = [];
  const stack = [];
  for (const raw of summary.split("\n")) {
    const m = LINE.exec(raw);
    if (!m) continue;
    const [, indent, component, name, id, w, h] = m;
    const level = Math.floor(indent.length / 2);
    const node = {
      id, name, component,
      w: parseFloat(w), h: parseFloat(h),
      level,
      childIds: [],
    };
    while (stack.length > level) stack.pop();
    const parent = stack[level - 1];
    node.parentId = parent ? parent.id : null;
    if (parent) parent.childIds.push(id);
    stack[level] = node;
    out.push(node);
  }
  return out;
}

if (arg("file-id")) setFileId(arg("file-id"));

const info = payload(await call("get_basic_info", {}));
if (!info.fileName) {
  console.error("No Paper file open. Pass --file-id <id>, or open one in Paper.");
  process.exit(1);
}
const expect = arg("expect-file");
if (expect && !info.fileName.includes(expect)) {
  console.error(`Active file is "${info.fileName}" but --expect-file "${expect}" was required. Refusing to run.`);
  process.exit(1);
}
const only = arg("only");
const artboards = (info.artboards || []).filter((a) => {
  if (!isLibraryMineArtboard(a.name)) return false;
  if (only && !String(a.name).includes(only)) return false;
  return true;
});
if (!artboards.length) {
  console.error("no source artboards (all were excluded as generated output)");
  process.exit(1);
}
log(`mining ${artboards.length} artboard(s) in "${info.fileName}"`);

const nodes = new Map();
const existingTokens = info.tokens?.items || [];
for (const ab of artboards) {
  try {
    const res = payload(await call("get_tree_summary", { nodeId: ab.id, depth }));
    const parsed = parseTree(res.summary || "");
    for (const n of parsed) nodes.set(n.id, { ...n, artboard: ab.name });
    log(`  ${ab.name}: ${parsed.length} node(s)`);
  } catch (err) {
    log(`  ${ab.name}: tree failed — ${err.message.split("\n")[0]}`);
  }
}
log(`total ${nodes.size} node(s)`);

// Styles are required for colors + fonts + desktop line-height / letter-spacing.
// Spacing / type-size / radius / elevation tokens do not read these values.
const ids = [...nodes.keys()];
let styled = 0;
for (let i = 0; i < ids.length; i += 60) {
  try {
    const styles = payload(await call("get_computed_styles", { nodeIds: ids.slice(i, i + 60) })).styles || {};
    for (const [id, s] of Object.entries(styles)) {
      const n = nodes.get(id);
      if (!n) continue;
      n.style = {
        ...s,
        backgroundColor: resolveBoundTokenValue(s.backgroundColor, existingTokens),
        color: resolveBoundTokenValue(s.color, existingTokens),
        fontFamily: resolveBoundFontFamily(s.fontFamily, existingTokens),
        fontWeight: resolveBoundTokenValue(s.fontWeight, existingTokens),
        fontStyle: resolveBoundTokenValue(s.fontStyle, existingTokens),
        fontSize: resolveBoundTokenValue(s.fontSize, existingTokens),
        lineHeight: resolveBoundTokenValue(s.lineHeight, existingTokens),
        letterSpacing: resolveBoundTokenValue(s.letterSpacing, existingTokens),
      };
      styled++;
    }
  } catch (err) {
    log(`  styles batch ${i} failed: ${err.message.split("\n")[0]}`);
  }
}
log(`styles resolved for ${styled}/${ids.length} node(s)`);

const projectRoot = resolveCaptureProjectRoot({
  project: arg("project"),
  jsonOut,
});
const captureWitness = applyCapturePaintWitness(nodes.values(), projectRoot, { log });

// Brand roles come from the source landers. Capture Tool frames still enter
// leftoverMined below so every newly parked color/font can receive a semantic
// token without turning tool chrome (red badges, pale review wells) into the
// site's primary accent.
const landerNodes = [...nodes.values()].filter((n) => /-(desktop|768|390)$/i.test(n.artboard || ""));
const mined = mineFromStyledNodes(
  [...landerNodes, ...captureWitness.mineNodes],
  { minUses },
);
const leftoverMined = mineFromStyledNodes(
  [...nodes.values(), ...captureWitness.mineNodes],
  { minUses: 1 },
);

const bucket = (v, step) => Math.round(v / step) * step;

const styleFingerprint = (n) => {
  const s = n.style || {};
  return [
    s.fontSize, s.fontWeight, s.fontFamily, s.color, s.backgroundColor,
    s.borderRadius, s.boxShadow ? "shadow" : "", s.flexDirection,
    s.borderWidth, s.textTransform,
  ].map((v) => (v == null ? "" : String(v))).join("/");
};

const roleSig = (n) => {
  const kids = n.childIds.map((id) => nodes.get(id)).filter(Boolean);
  const kidShape = kids.map((k) => `${k.component}:h${bucket(k.h, 8)}`).join("|");
  return `${n.component}|h${bucket(n.h, 8)}|k${kids.length}|${styleFingerprint(n)}|{${kidShape}}`;
};

const bySig = new Map();
for (const n of nodes.values()) {
  if (/^A\/6/.test(n.artboard || "")) continue;
  if (n.w < 24 || n.h < 12) continue;
  const key = roleSig(n);
  if (!bySig.has(key)) bySig.set(key, []);
  bySig.get(key).push(n);
}

function classify(n, instances) {
  const kids = n.childIds.length;
  const spansPage = n.w >= 1400;
  const pageCount = new Set(instances.map((i) => i.artboard)).size;
  if (spansPage && pageCount >= 2) return "organism";
  if (kids === 0) return "atom";
  if (kids <= 4 && n.h < 400) return "molecule";
  return "organism";
}

const components = [...bySig.entries()]
  .filter(([, list]) => list.length >= Math.max(2, minUses - 1))
  .map(([signature, list]) => {
    const pages = [...new Set(list.map((i) => i.artboard))];
    const sorted = [...list].sort((a, b) => a.w - b.w);
    const exemplar = sorted[Math.floor(sorted.length / 2)];
    const widths = [...new Set(list.map((i) => Math.round(i.w)))].sort((a, b) => a - b);
    return {
      signature,
      atomicLevel: classify(exemplar, list),
      instances: list.length,
      pages: pages.length,
      pageNames: pages.slice(0, 6),
      width: Math.round(exemplar.w),
      height: Math.round(exemplar.h),
      widthVariants: widths.length,
      widths: widths.slice(0, 8),
      childCount: exemplar.childIds.length,
      exampleNodeId: exemplar.id,
      exampleName: exemplar.name,
      variantNodeIds: [...new Map(list.map((i) => [Math.round(i.w), i.id])).values()].slice(0, 8),
    };
  })
  .sort((a, b) => b.instances - a.instances || b.pages - a.pages);

const shared = components.filter((c) => c.atomicLevel === "organism" && c.pages >= 3);
const inPage = components.filter((c) => c.pages <= 2 && c.instances >= 2);
const byLevel = (lvl, n) => components.filter((c) => c.atomicLevel === lvl).slice(0, n);

const report = buildLibraryReport({
  file: info.fileName,
  artboards: artboards.map((a) => a.name),
  nodes: nodes.size,
  styledNodes: styled,
  minUses,
  mined,
  leftoverMined,
  components: {
    total: components.length,
    shared,
    inPage: inPage.slice(0, 24),
    byLevel: {
      atom: components.filter((c) => c.atomicLevel === "atom").length,
      molecule: components.filter((c) => c.atomicLevel === "molecule").length,
      organism: components.filter((c) => c.atomicLevel === "organism").length,
    },
    atoms: byLevel("atom", 16),
    molecules: byLevel("molecule", 16),
    organisms: byLevel("organism", 10),
    top: components.slice(0, 60),
  },
});

const jsonPath = resolve(jsonOut);
mkdirSync(dirname(jsonPath), { recursive: true });
writeFileSync(jsonPath, JSON.stringify(report, null, 2), "utf8");
log(`wrote ${resolve(jsonOut)}`);

async function probePaperFontCatalog(names) {
  const unique = [...new Set(names.map((n) => String(n || "").trim()).filter(Boolean))];
  if (!unique.length) return null;
  try {
    const raw = payload(await call("get_font_family_info", { familyNames: unique }, { pinFile: false }));
    const catalog = parseFontFamilyInfo(raw);
    const hits = [...catalog.available.values()];
    if (hits.length) log(`font catalog: ${hits.join(", ")}`);
    if (catalog.unavailable.size) log(`font catalog unavailable: ${[...catalog.unavailable].join(", ")}`);
    return catalog;
  } catch (err) {
    log(`get_font_family_info skipped — ${err.message.split("\n")[0]}`);
    return null;
  }
}

const familyNames = report.proposedTokens
  .filter((t) => t.type === "fontFamily")
  .map((t) => paperFontFamilyValue(t));
const catalog = writeTokens ? await probePaperFontCatalog(familyNames) : null;
const shaped = applyPaperFontFamilies(report.proposedTokens, catalog);
for (const t of shaped.filter((x) => x.type === "fontFamily")) {
  if (t.paperSkip) log(`skip Paper font ${t.name} (${t.paperRequested}) — unavailable`);
  else if (t.paperFallback) log(`Paper font ${t.name}: ${t.paperRequested} → ${t.paperFallback}`);
}
const paperTokens = paperCreateTokens(shaped);
if (writeTokens && paperTokens.length) {
  const plan = tokenWritePlan(paperTokens, existingTokens, { replace: replaceTokens });
  await applyPaperTokenWritePlan({ call, plan });
  log(`tokens: ${plan.creates.length} created, ${plan.updates.length} updated, ${plan.deletes.length} removed`);
  const blocked = refusesPaperFile({ fileName: info.fileName });
  if (blocked) {
    log(`skip font bind on ${blocked} (Pitfall #89)`);
  } else {
    const pass = bindPaperFontUpdates([...nodes.values()], shaped, { preferVar: true, catalog });
    if (pass.updates.length) {
      for (let i = 0; i < pass.updates.length; i += 40) {
        try {
          await call("update_styles", { updates: pass.updates.slice(i, i + 40) });
        } catch (err) {
          log(`  font bind batch ${i} failed: ${err.message.split("\n")[0]}`);
        }
      }
      log(`bound ${pass.changes.length} unbound font(s) after create_tokens`);
    }
  }
}

console.log(JSON.stringify({
  nodes: nodes.size,
  styledNodes: styled,
  proposedTokens: report.proposedTokens.length,
  paperTokens: paperTokens.length,
  components: report.components.byLevel,
  sharedOrganisms: shared.length,
  report: resolve(jsonOut),
}, null, 1));
