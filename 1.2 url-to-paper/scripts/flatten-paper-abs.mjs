#!/usr/bin/env node
// Paper-side flatten for decorative abs overlays already on the canvas.
//
//   PAPER_FILE_ID=… node flatten-paper-abs.mjs [--artboard <id>] [--dry-run]
//
// Walks page landers and A/6 · {page} · states (not source shots / rulers).
// Hoists 1px strokes / CSS gradients onto the parent and deletes the
// Rectangle / empty Frame.

import { call, setFileId, getFileId } from "./mcp-client.mjs";
import { mcpPayload } from "./rulers.mjs";
import { isDecorativeAbs, parentHoistCamel } from "./flatten-decorative-abs.mjs";

const argv = process.argv.slice(2);
const arg = (name, fallback) => {
  const i = argv.indexOf(`--${name}`);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : fallback;
};
if (arg("file-id")) setFileId(arg("file-id"));
const fileId = arg("file-id") || process.env.PAPER_FILE_ID || getFileId();
if (fileId) setFileId(fileId);
const only = arg("artboard");
const dry = argv.includes("--dry-run");
const log = (...a) => console.error("·", ...a);

const PAGE = /^(home-desktop|home-768|home-390)$/;
const STATES = /^A\/6 · .+ · states$/;
const skipName = (name = "") =>
  name.startsWith("Ruler · ") ||
  name.endsWith(" — source screenshot") ||
  name === "Desktop section IDs";

const info = mcpPayload(await call("get_basic_info", {}));
let boards = info.artboards || [];
if (only) boards = boards.filter((b) => b.id === only);
else boards = boards.filter((b) => (PAGE.test(b.name) || STATES.test(b.name)) && !skipName(b.name));

const findings = [];
const deletes = [];
const updates = [];

for (const ab of boards) {
  log(`scan ${ab.name}`);
  const found = mcpPayload(await call("find_nodes", {
    nodeId: ab.id,
    filters: [{ styleName: "position", styleValue: "absolute" }],
  }));
  const nodes = (found.nodes || []).filter((n) => n.id !== ab.id);
  const ids = nodes.map((n) => n.id);
  const metas = new Map();
  for (let i = 0; i < ids.length; i += 8) {
    const chunk = ids.slice(i, i + 8);
    await Promise.all(chunk.map(async (id) => {
      try {
        metas.set(id, mcpPayload(await call("get_node_info", { nodeId: id })));
      } catch {}
    }));
  }
  const parentIds = [...new Set([...metas.values()].map((m) => m.parentId).filter(Boolean))];
  const styleIds = [...new Set([...ids, ...parentIds])];
  const styles = {};
  for (let i = 0; i < styleIds.length; i += 40) {
    Object.assign(
      styles,
      mcpPayload(await call("get_computed_styles", { nodeIds: styleIds.slice(i, i + 40) })).styles || {},
    );
  }

  for (const n of nodes) {
    const meta = metas.get(n.id);
    if (!meta) continue;
    const childStyle = kebabize(styles[n.id] || {});
    const parentStyle = kebabize(styles[meta.parentId] || {});
    const hit = isDecorativeAbs({
      childStyle,
      parentStyle,
      childCount: meta.childCount || 0,
      text: meta.textContent || "",
      hasMedia: n.component === "Image" || n.component === "SVG",
      width: meta.width,
      height: meta.height,
    });
    if (!hit) continue;
    const hoist = parentHoistCamel(childStyle, hit.paint);
    if (hit.paint.box) hoist.overflow = "visible";
    findings.push({
      artboard: ab.name,
      name: n.name,
      parent: meta.parentId,
      hoist,
    });
    if (meta.parentId) {
      updates.push({ nodeIds: [meta.parentId], styles: hoist });
    }
    deletes.push(n.id);
  }
}

function kebabize(obj) {
  const out = {};
  for (const [k, v] of Object.entries(obj || {})) {
    out[k.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`)] = v;
  }
  return out;
}

const merged = new Map();
for (const u of updates) {
  const id = u.nodeIds[0];
  merged.set(id, { ...(merged.get(id) || {}), ...u.styles });
}
const mergedUpdates = [...merged.entries()].map(([id, styles]) => ({ nodeIds: [id], styles }));

log(`${findings.length} decorative overlay(s)`);
if (!dry && mergedUpdates.length) {
  for (let i = 0; i < mergedUpdates.length; i += 20) {
    await call("update_styles", { updates: mergedUpdates.slice(i, i + 20) });
  }
}
if (!dry && deletes.length) {
  for (let i = 0; i < deletes.length; i += 40) {
    await call("delete_nodes", { nodeIds: deletes.slice(i, i + 40) });
  }
}
if (!dry) await call("finish_working_on_nodes", {});

console.log(JSON.stringify({
  file: info.fileName,
  dry,
  flattened: findings.length,
  findings: findings.map((f) => ({ artboard: f.artboard, name: f.name, hoist: f.hoist })),
}, null, 2));
