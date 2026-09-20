// 1.4 color witness from capture HTML.
//
// After a bad token pass, Paper CTAs and washes can share one var and the
// computed fill is the wash. Capture section HTML still has rgb() vs rgba().
// Mine those paints so --color-accent stays the solid, then restore the
// matching Paper nodes via an optional paper-layer-ids.json before bind
// when that sidecar exists (Pitfall #154). The sidecar is not required.
// Never paint a frame 1.2 left unpainted — serializer F() may have copied an
// ancestor fill into capture HTML (Pitfall #157).

import { existsSync, readdirSync, readFileSync } from "node:fs";
import { basename, dirname, join, resolve } from "node:path";
import { isUnpaintedFill, parseColor, toPaintedHex } from "./library-tokens.mjs";

const LANDER_DIR = /-(desktop|768|390)$/i;
const SECTION_HTML = /^\d{2}-.*\.html$/i;

function saturation(c) {
  const mx = Math.max(c.r, c.g, c.b);
  const mn = Math.min(c.r, c.g, c.b);
  return mx === 0 ? 0 : (mx - mn) / mx;
}

export function parseInlineStyle(style) {
  const map = {};
  for (const part of String(style || "").split(";")) {
    const i = part.indexOf(":");
    if (i < 0) continue;
    const key = part.slice(0, i).trim().toLowerCase();
    const value = part.slice(i + 1).trim();
    if (key) map[key] = value;
  }
  return map;
}

/** Saturated opaque fills and saturated alpha washes. Not cream / white / ink. */
export function isCaptureFillWitness(value) {
  const c = parseColor(value);
  if (!c || c.a === 0) return false;
  const s = saturation(c);
  if (c.a < 0.999) return s >= 0.20;
  return s >= 0.35;
}

export function parseCaptureHtmlPaints(html) {
  const paints = [];
  const layer = /layer-name="([^"]+)"\s+style="([^"]*)"/g;
  let m;
  while ((m = layer.exec(html))) {
    const bg = parseInlineStyle(m[2])["background-color"];
    const hex = toPaintedHex(bg);
    if (!hex || !isCaptureFillWitness(hex)) continue;
    paints.push({ pcId: m[1], backgroundColor: hex });
  }
  return paints;
}

export function resolveCaptureProjectRoot({
  project,
  cwd = process.cwd(),
  jsonOut,
} = {}) {
  if (project) return resolve(project);
  if (existsSync(join(cwd, "capture"))) return resolve(cwd);
  if (jsonOut) {
    const dir = dirname(resolve(jsonOut));
    const root = basename(dir) === "design-library" ? dirname(dir) : dir;
    if (existsSync(join(root, "capture"))) return root;
  }
  return resolve(cwd);
}

function listLanderDirs(projectRoot) {
  const cap = join(projectRoot, "capture");
  if (!existsSync(cap)) return [];
  return readdirSync(cap, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && LANDER_DIR.test(entry.name))
    .map((entry) => ({ name: entry.name, dir: join(cap, entry.name) }));
}

function loadPaperLayerIds(landerDir) {
  const file = join(landerDir, "paper-layer-ids.json");
  if (!existsSync(file)) return {};
  try {
    return JSON.parse(readFileSync(file, "utf8")).ids || {};
  } catch {
    return {};
  }
}

function sectionHtmlFiles(landerDir) {
  return readdirSync(landerDir)
    .filter((name) => SECTION_HTML.test(name))
    .sort()
    .map((name) => join(landerDir, name));
}

function uniqueHex(values) {
  const set = new Set(values.filter(Boolean));
  return set.size === 1 ? [...set][0] : null;
}

export function loadCapturePaintIndex(projectRoot) {
  const root = resolve(projectRoot);
  const paints = [];
  const byNodeId = new Map();
  const byPcId = new Map();
  let mapped = 0;
  let conflicts = 0;

  for (const lander of listLanderDirs(root)) {
    const ids = loadPaperLayerIds(lander.dir);
    const found = new Map();
    for (const file of sectionHtmlFiles(lander.dir)) {
      const html = readFileSync(file, "utf8");
      for (const paint of parseCaptureHtmlPaints(html)) {
        paints.push({ ...paint, lander: lander.name, file: basename(file) });
        if (!found.has(paint.pcId)) found.set(paint.pcId, []);
        found.get(paint.pcId).push(paint.backgroundColor);
      }
    }
    for (const [pcId, hexes] of found) {
      const hex = uniqueHex(hexes);
      byPcId.set(`${lander.name}:${pcId}`, hex);
      const nodeId = ids[pcId];
      if (!nodeId) continue;
      if (!hex) {
        conflicts++;
        continue;
      }
      byNodeId.set(nodeId, { backgroundColor: hex, pcId, lander: lander.name });
      mapped++;
    }
  }

  return { paints, byNodeId, byPcId, mapped, conflicts };
}

export function overlayCapturePaints(nodes, index) {
  const list = Array.isArray(nodes) ? nodes : [...(nodes || [])];
  let restored = 0;
  let inventedSkipped = 0;
  for (const node of list) {
    const paint = index?.byNodeId?.get(node.id);
    if (!paint?.backgroundColor) continue;
    // Capture HTML may carry an ancestor fill from serializer F(). That is
    // not a license to paint a Paper frame 1.2 left unpainted (Pitfall #157).
    if (isUnpaintedFill(node.style?.backgroundColor)) {
      inventedSkipped++;
      continue;
    }
    node.style = { ...(node.style || {}), backgroundColor: paint.backgroundColor };
    restored++;
  }
  return { restored, inventedSkipped };
}

export function captureMineNodes(index) {
  return (index?.paints || []).map((paint, i) => ({
    id: `capture:${paint.lander || "x"}:${paint.pcId}:${i}`,
    name: paint.pcId,
    artboard: `${paint.lander || "capture"}-witness`,
    style: { backgroundColor: paint.backgroundColor },
  }));
}

export function applyCapturePaintWitness(nodes, projectRoot, { log } = {}) {
  const index = loadCapturePaintIndex(projectRoot);
  const { restored, inventedSkipped } = overlayCapturePaints(nodes, index);
  if (log) {
    log(
      `capture fills: ${index.paints.length} witness(es), `
      + `mapped ${index.mapped}, restored ${restored}`
      + (inventedSkipped ? `, skipped ${inventedSkipped} unpainted frame(s)` : "")
      + (index.conflicts ? `, skipped ${index.conflicts} pc-id conflict(s)` : ""),
    );
  }
  return { index, restored, inventedSkipped, mineNodes: captureMineNodes(index) };
}
