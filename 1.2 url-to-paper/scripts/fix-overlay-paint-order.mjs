#!/usr/bin/env node
// Paper-side repair for Pitfall #84 (overlay behind type).
//
//   PAPER_FILE_ID=… node fix-overlay-paint-order.mjs [--artboard <id>] [--dry-run]
//
// Census full-bleed abs overlays vs later text siblings on home-desktop /
// home-768 / home-390. Reorder with move_nodes: overlay after the image,
// before type. Do NOT clone the overlay on top. Fallback: z-index -1.
//
// Optional safety blocklist: PAPER_PROTECTED_FILE_IDS / PAPER_PROTECTED_FILE_NAMES.

import { call, setFileId, getFileId } from "./mcp-client.mjs";
import { findOverlayPaintOrderIssues, planOverlayPaintOrder } from "./overlay-paint-order.mjs";

const PAGE = /^(home-desktop|home-768|home-390)$/;

const argv = process.argv.slice(2);
const arg = (name, fallback) => {
  const i = argv.indexOf(`--${name}`);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : fallback;
};
if (arg("file-id")) setFileId(arg("file-id"));
const fileId = arg("file-id") || process.env.PAPER_FILE_ID || getFileId();
if (fileId) setFileId(fileId);
const only = arg("artboard");
const dry = argv.includes("--dry-run") || argv.includes("--scan");
const apply = argv.includes("--apply");
const log = (...a) => console.error("·", ...a);

function payload(result) {
  for (const item of result.content ?? []) {
    if (item.type === "text") {
      try { return JSON.parse(item.text); } catch { return { text: item.text }; }
    }
  }
  return {};
}

const protectedIds = String(process.env.PAPER_PROTECTED_FILE_IDS || "").split(",").map((v) => v.trim()).filter(Boolean);
const protectedNames = String(process.env.PAPER_PROTECTED_FILE_NAMES || "").split(",").map((v) => v.trim()).filter(Boolean);
if (protectedIds.includes(fileId) && apply) {
  console.error("refusing to write protected Paper file. Use --dry-run.");
  process.exit(2);
}

const info = payload(await call("get_basic_info", {}));
if (protectedNames.some((value) => String(info.fileName || "").toLowerCase().includes(value.toLowerCase())) && apply) {
  console.error(`refusing to write "${info.fileName}" (Pitfall #84). Use --dry-run.`);
  process.exit(2);
}

let boards = info.artboards || [];
if (only) boards = boards.filter((b) => b.id === only || b.name === only);
else boards = boards.filter((b) => PAGE.test(b.name));

const findings = [];
const moves = [];

async function collect(rootId, rootMeta, depth = 6) {
  const nodes = new Map();
  nodes.set(rootId, { id: rootId, ...rootMeta, parentId: null });
  let frontier = [rootId];
  for (let d = 0; d < depth; d++) {
    const next = [];
    for (const pid of frontier) {
      let kids;
      try {
        kids = payload(await call("get_children", { nodeId: pid })).children || [];
      } catch {
        continue;
      }
      const parent = nodes.get(pid);
      parent.childIds = kids.map((k) => k.id);
      for (const k of kids) {
        nodes.set(k.id, {
          id: k.id,
          name: k.name,
          component: k.component,
          childCount: k.childCount,
          parentId: pid,
        });
        if (k.childCount > 0) next.push(k.id);
      }
    }
    if (!next.length) break;
    frontier = next;
  }
  const ids = [...nodes.keys()];
  for (let i = 0; i < ids.length; i += 60) {
    try {
      const styles = payload(await call("get_computed_styles", { nodeIds: ids.slice(i, i + 60) })).styles || {};
      for (const [id, s] of Object.entries(styles)) {
        const n = nodes.get(id);
        if (!n) continue;
        n.bg = s.backgroundColor;
        n.position = s.position;
        n.opacity = s.opacity;
        n.top = s.top;
        n.right = s.right;
        n.bottom = s.bottom;
        n.left = s.left;
        n.inset = s.inset;
        n.widthStyle = s.width;
      }
    } catch {}
  }
  for (let i = 0; i < ids.length; i += 8) {
    const chunk = ids.slice(i, i + 8);
    await Promise.all(chunk.map(async (id) => {
      if (id === rootId) return;
      try {
        const d = payload(await call("get_node_info", { nodeId: id }));
        const n = nodes.get(id);
        if (!n) return;
        n.w = typeof d.width === "number" ? d.width : parseFloat(d.width);
        n.h = typeof d.height === "number" ? d.height : parseFloat(d.height);
        n.textContent = d.textContent;
      } catch {}
    }));
  }
  return nodes;
}

async function moveOverlay(nodeId, parentId, index, beforeId) {
  const attempts = [
    ["move_nodes", { nodeIds: [nodeId], parentId, index }],
    ["move_nodes", { nodeIds: [nodeId], parentId, beforeNodeId: beforeId }],
    ["move_nodes", { nodeIds: [nodeId], parentId, beforeId }],
    ["reparent_nodes", { nodeIds: [nodeId], parentId, index }],
  ];
  for (const [name, args] of attempts) {
    if (args.index == null && !args.beforeNodeId && !args.beforeId) continue;
    try {
      await call(name, args);
      return name;
    } catch {}
  }
  try {
    await call("update_styles", {
      updates: [{ nodeIds: [nodeId], styles: { zIndex: "-1" } }],
    });
    return "z-index-fallback";
  } catch {
    return null;
  }
}

for (const ab of boards) {
  log(`scan ${ab.name}`);
  const nodes = await collect(ab.id, {
    name: ab.name,
    component: "Artboard",
    w: ab.width,
    h: ab.height,
  });
  const hits = findOverlayPaintOrderIssues(nodes, { artboard: ab.name });
  findings.push(...hits);
  if (dry || !apply) continue;

  for (const n of nodes.values()) {
    if (!n.childIds || n.childIds.length < 2) continue;
    const sibs = n.childIds.map((id) => {
      const k = nodes.get(id);
      if (!k) return null;
      return {
        id: k.id,
        name: k.name,
        style: {
          position: k.position,
          width: k.widthStyle || (k.w != null ? `${k.w}px` : ""),
          height: k.h != null ? `${k.h}px` : "",
          top: k.top,
          right: k.right,
          bottom: k.bottom,
          left: k.left,
          inset: k.inset,
          "background-color": k.bg,
          opacity: k.opacity,
        },
        backgroundColor: k.bg,
        opacity: k.opacity,
        text: k.textContent,
        hasMedia: k.component === "Image" || k.component === "SVG",
        childCount: k.childCount || 0,
        component: k.component,
        width: k.w,
        height: k.h,
        parentWidth: n.w,
        parentHeight: n.h,
      };
    }).filter(Boolean);
    const plan = planOverlayPaintOrder(sibs);
    if (plan.alreadyGold) continue;
    for (const item of plan.ordered) {
      const dest = plan.ordered.indexOf(item);
      const src = n.childIds.indexOf(item.id);
      if (item.kind !== "overlay" && dest === src) continue;
    }
    for (let i = 0; i < plan.ordered.length; i++) {
      const item = plan.ordered[i];
      if (item.kind !== "overlay") continue;
      const before = plan.ordered.slice(i + 1).find((s) => s.kind === "type");
      const how = await moveOverlay(item.id, n.id, i, before?.id);
      moves.push({
        artboard: ab.name,
        node: item.id,
        name: item.name,
        how,
        index: i,
      });
      log(`  ${how || "failed"} ${item.name || item.id} → index ${i} in ${ab.name}`);
    }
  }
}

const summary = {
  fileId,
  file: info.fileName,
  dry: dry || !apply,
  findings,
  moves,
};
console.log(JSON.stringify(summary, null, 2));
if (findings.length && (dry || !apply)) process.exitCode = 1;
