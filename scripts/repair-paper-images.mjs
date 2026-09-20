#!/usr/bin/env node
// Re-write image-bearing Paper sections from localized capture HTML.
//
// Usage:
//   PAPER_FILE_ID=<id> node repair-paper-images.mjs \
//     --manifest capture/home-desktop/manifest.json \
//     --artboard <page-artboard-id> [--pace 2500]

import { readFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";
import { call, setFileId } from "./mcp-client.mjs";
import { localizeHtml } from "./localize-html-images.mjs";

const argv = process.argv.slice(2);
const arg = (name, fallback) => {
  const i = argv.indexOf(`--${name}`);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : fallback;
};
if (arg("file-id")) setFileId(arg("file-id"));

const manifestPath = resolve(arg("manifest") || "");
const artboardId = arg("artboard");
const pace = parseInt(arg("pace", "2500"), 10);
const only = new Set(
  (arg("only") || "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean),
);
if (!manifestPath || !existsSync(manifestPath) || !artboardId) {
  console.error("--manifest and --artboard are required");
  process.exit(1);
}

function payload(result) {
  for (const item of result.content ?? []) {
    if (item.type === "text") {
      try { return JSON.parse(item.text); } catch { return { text: item.text }; }
    }
  }
  return {};
}

const log = (...a) => console.error("·", ...a);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
const sections = (manifest.sections || []).filter((s) => s.status === "ok");
const kids = payload(await call("get_children", { nodeId: artboardId })).children || [];
const byName = new Map(kids.map((k) => [k.name, k]));

const repaired = [];
const skipped = [];

for (const s of sections) {
  if (only.size && !only.has(s.name) && !only.has(s.id) && !only.has(s.slug)) {
    skipped.push({ name: s.name, reason: "not --only" });
    continue;
  }
  const raw = readFileSync(s.file, "utf8");
  if (!/<img\b/i.test(raw) && !/url\(/i.test(raw) && !/data:image\//i.test(raw)) {
    skipped.push({ name: s.name, reason: "no images" });
    continue;
  }
  const node = byName.get(s.id) || byName.get(s.name) || byName.get(s.slug);
  if (!node) {
    skipped.push({ name: s.name, reason: "no Paper section" });
    continue;
  }
  const { html, mapped, missing } = await localizeHtml(raw, {
    projectRoot: resolve(s.file, "../.."),
  });
  const inner = payload(await call("get_children", { nodeId: node.id })).children || [];
  const ids = inner.map((c) => c.id).filter(Boolean);
  if (ids.length) await call("delete_nodes", { nodeIds: ids });
  await call("write_html", { html, targetNodeId: node.id, mode: "insert-children" });
  repaired.push({ name: s.name, nodeId: node.id, mapped: mapped.length, missing: missing.length });
  log(`  ✓ ${s.name}  ${mapped.length} local image(s)`);
  await sleep(pace + mapped.length * 200);
}

await call("finish_working_on_nodes", {});
console.log(JSON.stringify({ artboard: artboardId, repaired, skipped }, null, 1));
