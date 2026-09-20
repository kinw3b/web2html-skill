#!/usr/bin/env node
// Bind Paper Text nodes to catalog font tokens (Pitfall #89).
//
// After create_tokens and after write_html of the Design Library / landers,
// census Text (and text-like frames). System Sans-Serif, generics, and CSS
// stacks become var(--font-xxx) or the catalog face.
//
//   node bind-paper-fonts.mjs --file-id <id> [--library library.json]
//                             [--dry-run] [--json qa/font-bind.json]
//
// Optional safety blocklist: PAPER_PROTECTED_FILE_IDS / PAPER_PROTECTED_FILE_NAMES
// are comma-separated values. --dry-run is always allowed.

import { mkdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import {
  bindPaperFontUpdates,
  findUnboundFonts,
  normalizeTokens,
} from "./library-tokens.mjs";
import { isTokenPassArtboard } from "./token-pass-targets.mjs";

export function refusesPaperFile({
  fileId,
  fileName,
  protectedIds = process.env.PAPER_PROTECTED_FILE_IDS || "",
  protectedNames = process.env.PAPER_PROTECTED_FILE_NAMES || "",
} = {}) {
  const name = String(fileName || "");
  const id = String(fileId || "");
  const ids = String(protectedIds).split(",").map((v) => v.trim()).filter(Boolean);
  const names = String(protectedNames).split(",").map((v) => v.trim()).filter(Boolean);
  if (ids.includes(id)) return `protected id ${id}`;
  const match = names.find((value) => name.toLowerCase().includes(value.toLowerCase()));
  if (match) return `protected name ${match}`;
  return null;
}

const invoked = process.argv[1]
  && fileURLToPath(import.meta.url) === resolve(process.argv[1]);

if (!invoked) {
  // imported for refusesPaperFile / tests
} else {
const { call, setFileId, getFileId } = await import("./mcp-client.mjs");

const argv = process.argv.slice(2);
const arg = (name, fallback) => {
  const i = argv.indexOf(`--${name}`);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : fallback;
};

if (arg("file-id")) setFileId(arg("file-id"));
const fileId = arg("file-id") || process.env.PAPER_FILE_ID || getFileId();
if (fileId) setFileId(fileId);
const dryRun = argv.includes("--dry-run") || argv.includes("--scan");
const jsonOut = resolve(arg("json", "qa/font-bind.json"));
const log = (...a) => console.error("·", ...a);

function payload(result) {
  for (const item of result.content ?? []) {
    if (item.type === "text") {
      try { return JSON.parse(item.text); } catch { return { text: item.text }; }
    }
  }
  return {};
}

const info = payload(await call("get_basic_info", {}));
const blocked = refusesPaperFile({ fileId, fileName: info.fileName });
if (blocked && !dryRun) {
  console.error(`refusing to write ${blocked} Paper (Pitfall #89). Use --dry-run.`);
  process.exit(2);
}

const expect = arg("expect-file");
if (expect && !String(info.fileName || "").includes(expect)) {
  console.error(`Active file is "${info.fileName}" but --expect-file "${expect}" was required.`);
  process.exit(1);
}

let tokens = [];
try {
  tokens = normalizeTokens(payload(await call("get_tokens", {})));
} catch (err) {
  log(`get_tokens failed: ${err.message.split("\n")[0]}`);
}
const libraryPath = arg("library");
if (libraryPath && existsSync(resolve(libraryPath))) {
  const extra = normalizeTokens(JSON.parse(readFileSync(resolve(libraryPath), "utf8")));
  const have = new Set(tokens.map((t) => t.name));
  for (const t of extra) if (!have.has(t.name)) tokens.push(t);
}
if (!tokens.filter((t) => t.type === "fontFamily").length) {
  console.error("no fontFamily tokens — finish extract-library --write-tokens first.");
  process.exit(1);
}

const only = arg("artboard") || arg("only");
let boards = info.artboards || [];
if (only) boards = boards.filter((b) => b.id === only || String(b.name).includes(only));
else boards = boards.filter((b) => isTokenPassArtboard(b.name));

const depth = Math.min(Math.max(parseInt(arg("depth", "16"), 10) || 16, 1), 32);
const nodes = [];
for (const ab of boards) {
  const seen = new Map();
  seen.set(ab.id, { id: ab.id, name: ab.name, component: "Artboard", artboard: ab.name });
  let frontier = [ab.id];
  for (let d = 0; d < depth; d++) {
    const next = [];
    for (const pid of frontier) {
      let kids = [];
      try {
        kids = payload(await call("get_children", { nodeId: pid })).children || [];
      } catch {
        continue;
      }
      for (const k of kids) {
        if (!seen.has(k.id)) {
          seen.set(k.id, {
            id: k.id,
            name: k.name,
            component: k.component,
            artboard: ab.name,
          });
        }
        if (k.childCount > 0) next.push(k.id);
      }
    }
    if (!next.length) break;
    frontier = next;
  }
  nodes.push(...seen.values());
  log(`${ab.name}: ${seen.size} node(s)`);
}

const ids = [...new Set(nodes.map((n) => n.id))];
for (let i = 0; i < ids.length; i += 60) {
  try {
    const styles = payload(await call("get_computed_styles", { nodeIds: ids.slice(i, i + 60) })).styles || {};
    for (const [id, s] of Object.entries(styles)) {
      const n = nodes.find((x) => x.id === id);
      if (n) n.style = s;
    }
  } catch (err) {
    log(`styles batch ${i} failed: ${err.message.split("\n")[0]}`);
  }
}

const pass = bindPaperFontUpdates(nodes, tokens, { preferVar: true });
const findings = findUnboundFonts(nodes, tokens);

if (!dryRun && pass.updates.length) {
  for (let i = 0; i < pass.updates.length; i += 40) {
    await call("update_styles", { updates: pass.updates.slice(i, i + 40) });
  }
  try { await call("finish_working_on_nodes", {}); } catch {}
}

const report = {
  file: info.fileName,
  dryRun,
  refused: blocked || null,
  artboards: boards.map((b) => b.name),
  tokens: tokens.filter((t) => t.type === "fontFamily").map((t) => t.name),
  changes: pass.changes,
  skipped: pass.skipped,
  unboundBefore: findings.length,
};

mkdirSync(dirname(jsonOut), { recursive: true });
writeFileSync(jsonOut, JSON.stringify(report, null, 2), "utf8");
log(`wrote ${jsonOut} (${pass.changes.length} bind(s), ${findings.length} unbound before)`);
console.log(JSON.stringify({
  file: info.fileName,
  dryRun,
  changes: pass.changes.length,
  skipped: pass.skipped.length,
  unboundBefore: findings.length,
  report: jsonOut,
}, null, 1));
}
