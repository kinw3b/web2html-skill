#!/usr/bin/env node
// 1.4 token-pass: bind landers + A/6 + Design Library + Interactive components
// to registered tokens. Brand colors plus leftover semantic roles
// (--color-danger, --color-surface-alt, …). Geometry-affecting values bind
// only when an exact token exists; unmatched measurements remain literals.
//
// Census every node. Token bind is not best-effort (Pitfall #76).
// Design Library is the source of tokens. After render-library, walk
// `{page}-desktop` / `{page}-768` / `{page}-390`, `A/6 · {page} · states`,
// Design Library, and FRAME `Interactive components`, and update_styles
// each painted property to an exact token where allowed. Not 2.0 / get_jsx.
//
// Usage:
//   node apply-theme-tokens.mjs --file-id <id> [--json qa/token-pass.json]
//                               [--qa qa/token-pass-qa.json]
//                               [--library design-library/library.json]
//                               [--only "Interactive components"]
//                               [--list-targets] [--depth 16] [--dry-run]

import { mkdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { applyCapturePaintWitness, resolveCaptureProjectRoot } from "./capture-paints.mjs";
import { childrenFromPayload, shouldDescend } from "./merge-split-headings.mjs";
import {
  buildTokenPassQa,
  isSkippedTokenPassBoard,
  isTokenPassArtboard,
  dropInventedFillChanges,
  isUnpaintedFill,
  normalizeTokens,
  requireApplyThemeTokensScript,
  themeTokenPass,
  tokenPassQaFails,
} from "./library-tokens.mjs";
import {
  INTERACTIVE_COMPONENTS,
  selectTokenPassArtboards,
} from "./token-pass-targets.mjs";
import {
  compareTokenGeometry,
  snapshotTokenGeometry,
} from "./token-geometry-guard.mjs";

export { INTERACTIVE_COMPONENTS, isTokenPassArtboard, selectTokenPassArtboards };

export function tokenPassVisitsInteractiveComponents(artboards, { only } = {}) {
  return selectTokenPassArtboards(artboards, { only })
    .some((a) => (typeof a === "string" ? a : a.name) === INTERACTIVE_COMPONENTS);
}

requireApplyThemeTokensScript(fileURLToPath(import.meta.url));

const argv = process.argv.slice(2);
const arg = (name, fallback) => {
  const i = argv.indexOf(`--${name}`);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : fallback;
};

const depth = Math.min(Math.max(parseInt(arg("depth", "16"), 10) || 16, 1), 32);
const outRoot = arg("project") ? resolve(arg("project")) : process.cwd();
const resolveOut = (value) => resolve(outRoot, value);
const jsonOut = resolveOut(arg("json", "qa/token-pass.json"));
const qaOut = resolveOut(arg("qa", "qa/token-pass-qa.json"));
const geometryBeforeOut = resolveOut(arg("geometry-before", "qa/token-geometry-before.json"));
const geometryAfterOut = resolveOut(arg("geometry-after", "qa/token-geometry-after.json"));
const dryRun = argv.includes("--dry-run");
const exactOnly = argv.includes("--exact-only");
const log = (...a) => console.error("·", ...a);

function payload(result) {
  for (const item of result.content ?? []) {
    if (item.type === "text") {
      try { return JSON.parse(item.text); } catch { return { text: item.text }; }
    }
  }
  return {};
}

const invoked = process.argv[1]
  && fileURLToPath(import.meta.url) === resolve(process.argv[1]);

if (invoked && argv.includes("--list-targets")) {
  const names = [
    "home-desktop", "home-768", "home-390",
    "Design Library",
    "A/6 · home · states",
    INTERACTIVE_COMPONENTS,
    "Source · home",
    "Screenshots",
  ];
  const selected = selectTokenPassArtboards(names.map((name) => ({ name })), {
    only: arg("only"),
  }).map((a) => a.name);
  const skippedBoards = names.filter((name) => isSkippedTokenPassBoard(name));
  console.log(JSON.stringify({
    artboards: selected,
    targets: selected,
    skippedBoards,
    visitsInteractiveComponents: selected.includes(INTERACTIVE_COMPONENTS),
  }, null, 2));
  process.exit(0);
}

if (invoked) {
  const bindRefusal = (() => {
    const path = resolve(outRoot, "qa", "run-config.json");
    if (!existsSync(path)) return null;
    try {
      const cfg = JSON.parse(readFileSync(path, "utf8"));
      if (cfg && (cfg.adopt === true || cfg.bindTokens === false)) {
        return "adopted clean HTML — do not seed variables onto Paper frames (Pitfall #224).";
      }
    } catch {
      return null;
    }
    return null;
  })();
  if (bindRefusal) {
    console.error(bindRefusal);
    process.exit(1);
  }
if (!exactOnly) {
  console.error("Paper step 1.4 requires --exact-only; nearest token snapping is forbidden.");
  process.exit(1);
}
const { call, setFileId } = await import("./mcp-client.mjs");
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
const allBoards = info.artboards || [];
const skippedBoards = allBoards.filter((a) => isSkippedTokenPassBoard(a.name)).map((a) => a.name);
const artboards = selectTokenPassArtboards(allBoards, { only });
if (!artboards.length) {
  console.error("no lander / A/6 / Design Library / Interactive components artboards to token-pass");
  process.exit(1);
}
log(`token-pass ${artboards.length} artboard(s) in "${info.fileName}" (census, depth ${depth})`);
if (tokenPassVisitsInteractiveComponents(artboards, { only })) {
  log(`includes ${INTERACTIVE_COMPONENTS}`);
}
if (skippedBoards.length) log(`skipped-board ${skippedBoards.join(", ")}`);

let tokens = [];
try {
  const raw = payload(await call("get_tokens", {}));
  tokens = normalizeTokens(raw);
  if (!tokens.length && (raw.css || raw.text || typeof raw === "string")) {
    tokens = normalizeTokens(raw);
  }
} catch (err) {
  log(`get_tokens failed: ${err.message.split("\n")[0]}`);
}
if (!tokens.length) {
  try {
    const css = payload(await call("get_tokens", { format: "css" }));
    tokens = normalizeTokens(css);
  } catch (err) {
    log(`get_tokens(css) failed: ${err.message.split("\n")[0]}`);
  }
}
const libraryPath = arg("library");
if (libraryPath && existsSync(resolve(libraryPath))) {
  const lib = JSON.parse(readFileSync(resolve(libraryPath), "utf8"));
  const extra = normalizeTokens(lib);
  const have = new Set(tokens.map((t) => t.name));
  for (const t of extra) if (!have.has(t.name)) tokens.push(t);
}
if (!tokens.length) {
  console.error("no registered tokens (get_tokens empty and no --library). Finish extract-library --write-tokens first.");
  process.exit(1);
}
log(`${tokens.length} token(s) in play`);

async function collectArtboardNodes(ab) {
  const nodes = new Map();
  nodes.set(ab.id, {
    id: ab.id,
    name: ab.name,
    component: "Artboard",
    artboard: ab.name,
    parentId: null,
  });
  let frontier = [ab.id];
  for (let d = 0; d < depth; d++) {
    const next = [];
    for (const pid of frontier) {
      let kids = [];
      try {
        kids = childrenFromPayload(payload(await call("get_children", { nodeId: pid })));
      } catch (err) {
        log(`  ${ab.name}: get_children ${pid} failed — ${err.message.split("\n")[0]}`);
        continue;
      }
      for (const k of kids) {
        if (!nodes.has(k.id)) {
          nodes.set(k.id, {
            id: k.id,
            name: k.name,
            component: k.component,
            artboard: ab.name,
            parentId: pid,
          });
        }
        if (shouldDescend(k)) next.push(k.id);
      }
    }
    if (!next.length) break;
    frontier = next;
  }
  return [...nodes.values()];
}

const nodes = [];
for (const ab of artboards) {
  const parsed = await collectArtboardNodes(ab);
  nodes.push(...parsed);
  log(`  ${ab.name}: ${parsed.length} node(s)`);
}

const ids = [...new Set(nodes.map((n) => n.id))];
let styled = 0;
for (let i = 0; i < ids.length; i += 60) {
  try {
    const styles = payload(await call("get_computed_styles", { nodeIds: ids.slice(i, i + 60) })).styles || {};
    for (const [id, s] of Object.entries(styles)) {
      const n = nodes.find((x) => x.id === id);
      if (!n) continue;
      n.style = s;
      styled++;
    }
  } catch (err) {
    log(`  styles batch ${i} failed: ${err.message.split("\n")[0]}`);
  }
}
log(`styles resolved for ${styled}/${ids.length} node(s)`);

const projectRoot = resolveCaptureProjectRoot({
  project: arg("project"),
  jsonOut: arg("library") || jsonOut,
});
const unpaintedIds = new Set(
  nodes
    .filter((node) => isUnpaintedFill(node.style?.backgroundColor) && isUnpaintedFill(node.style?.fill))
    .map((node) => node.id),
);
applyCapturePaintWitness(nodes, projectRoot, { log });

const geometryBefore = snapshotTokenGeometry(nodes);
mkdirSync(dirname(geometryBeforeOut), { recursive: true });
writeFileSync(geometryBeforeOut, JSON.stringify(geometryBefore, null, 2), "utf8");

const pass = dropInventedFillChanges(themeTokenPass(nodes, tokens), unpaintedIds);
if (pass.invented?.length) {
  log(`refused ${pass.invented.length} invented fill(s) on unpainted 1.2 frames`);
}

const postStyleErrors = [];
if (!dryRun && pass.updates.length) {
  for (let i = 0; i < pass.updates.length; i += 40) {
    try {
      await call("update_styles", { updates: pass.updates.slice(i, i + 40) });
    } catch (err) {
      log(`  update_styles batch ${i} failed: ${err.message.split("\n")[0]}`);
    }
  }
  try { await call("finish_working_on_nodes", {}); } catch {}
}

if (!dryRun && pass.updates.length) {
  await new Promise((resolveWait) => setTimeout(resolveWait, 200));
  for (let i = 0; i < ids.length; i += 60) {
    try {
      const styles = payload(await call("get_computed_styles", { nodeIds: ids.slice(i, i + 60) })).styles || {};
      for (const [id, style] of Object.entries(styles)) {
        const node = nodes.find((item) => item.id === id);
        if (node) node.style = style;
      }
    } catch (err) {
      postStyleErrors.push({ batch: i, error: err.message.split("\n")[0] });
      log(`  post-bind styles batch ${i} failed: ${err.message.split("\n")[0]}`);
    }
  }
}
const geometryAfter = snapshotTokenGeometry(nodes);
const geometry = compareTokenGeometry(geometryBefore, geometryAfter, {
  ignoredArtboards: ["Design Library"],
  tokens,
});
for (const error of postStyleErrors) {
  geometry.differences.push({
    reason: "post-bind-style-read-failed",
    batch: error.batch,
    error: error.error,
  });
}
geometry.ok = geometry.differences.length === 0;
mkdirSync(dirname(geometryAfterOut), { recursive: true });
writeFileSync(geometryAfterOut, JSON.stringify({
  snapshot: geometryAfter,
  comparison: geometry,
}, null, 2), "utf8");

const qa = buildTokenPassQa({
  treeNodes: nodes,
  pass,
  tokens,
  skippedBoards,
});

const report = {
  file: info.fileName,
  artboards: artboards.map((a) => a.name),
  visitsInteractiveComponents: tokenPassVisitsInteractiveComponents(artboards, { only }),
  skippedBoards,
  tokens: tokens.length,
  nodes: nodes.length,
  styledNodes: styled,
  dryRun,
  changes: pass.changes,
  skipped: pass.skipped,
  leftovers: pass.leftovers,
  geometry,
  coverage: qa.coverage,
};

mkdirSync(dirname(jsonOut), { recursive: true });
writeFileSync(jsonOut, JSON.stringify(report, null, 2), "utf8");
mkdirSync(dirname(qaOut), { recursive: true });
writeFileSync(qaOut, JSON.stringify(qa, null, 2), "utf8");
log(`wrote ${jsonOut} (${pass.changes.length} bind(s), ${pass.skipped.length} skip(s), ${pass.leftovers.length} leftover(s))`);
log(`wrote ${qaOut} (tree ${qa.coverage.treeNodes}, accounted ${qa.coverage.accounted}, missing ${qa.coverage.missing.length})`);

const summary = {
  file: info.fileName,
  artboards: report.artboards,
  visitsInteractiveComponents: report.visitsInteractiveComponents,
  skippedBoards,
  changes: pass.changes.length,
  skipped: pass.skipped.length,
  leftovers: pass.leftovers.length,
  nodesTouchedCount: qa.nodesTouchedCount,
  propsReboundCount: qa.propsReboundCount,
  coverage: qa.coverage,
  report: jsonOut,
  qa: qaOut,
  dryRun,
  exactOnly,
  geometry,
  geometryBefore: geometryBeforeOut,
  geometryAfter: geometryAfterOut,
  ok: qa.ok && geometry.ok,
};

if (tokenPassQaFails(qa) || !geometry.ok) {
  if (!geometry.ok) {
    console.error(`token geometry FAIL: ${geometry.differences.length} difference(s)`);
    for (const difference of geometry.differences.slice(0, 12)) {
      console.error(`  ${difference.nodeId} ${difference.property || difference.reason}`);
    }
  }
  console.error(`token-pass QA FAIL: ${qa.coverage.missing.length} missing node(s), ${(qa.defects || []).length} unlisted raw`);
  if (qa.coverage.missing.length) {
    console.error(`  missing: ${qa.coverage.missing.slice(0, 20).join(", ")}${qa.coverage.missing.length > 20 ? "…" : ""}`);
  }
  for (const d of (qa.defects || []).slice(0, 12)) {
    console.error(`  defect ${d.nodeId} ${d.prop}=${d.value} (${d.why})`);
  }
  console.log(JSON.stringify(summary, null, 1));
  process.exit(1);
}

console.log(JSON.stringify(summary, null, 1));
}
