#!/usr/bin/env node
// Place the canvas row under a single ruler, left to right, shared Y:
// Design Library → Screenshots → home-desktop → home-768 → home-390
// → Buttons → Components → Navigation.
//
// create_artboard ignores left/top — this is the tidy-up pass.
//
// Usage:
//   node arrange-artboards.mjs [--gap 120] [--order "home-desktop,home-768,home-390"]

import { call } from "./mcp-client.mjs";
import {
  contentOrigin,
  ensureRulers,
  isRulerName,
  LANDER_NAMES,
  planLanderRow,
} from "./rulers.mjs";

const argv = process.argv.slice(2);
const arg = (name, fallback) => {
  const i = argv.indexOf(`--${name}`);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : fallback;
};

const gap = parseInt(arg("gap", "120"), 10);
const explicitOrder = arg("order")?.split(",").map((s) => s.trim()).filter(Boolean);
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
const boards = info.artboards || [];
const fileId = info.fileId || info.id || process.env.PAPER_FILE_ID;
if (!boards.length) {
  console.error("no artboards on the active page");
  process.exit(1);
}

await ensureRulers({
  call,
  fileId,
  boards,
  init: true,
  log,
});
const afterRulers = payload(await call("get_basic_info", { ...(fileId ? { fileId } : {}) }));
const origin = contentOrigin(afterRulers.artboards || []);

const orderHint = explicitOrder?.length ? explicitOrder : LANDER_NAMES;
log(`horizontal landers: ${orderHint.join(" → ")}`);

const planned = planLanderRow(afterRulers.artboards || [], {
  gap,
  originX: origin.left,
  originY: origin.top,
});
const updates = planned.map((p) => ({
  nodeIds: [p.id],
  styles: { left: `${p.x}px`, top: `${p.y}px` },
}));

if (updates.length) await call("update_styles", { updates });
log(`arranged ${updates.length} artboard(s) in 1 row under Ruler · desktop, ${gap}px gaps`);

await new Promise((r) => setTimeout(r, 2500));

const after = payload(await call("get_basic_info", {}));
const placed = after.artboards || [];

let overlaps = 0;
for (let i = 0; i < placed.length; i++) {
  for (let j = i + 1; j < placed.length; j++) {
    const a = placed[i], b = placed[j];
    if (isRulerName(a.name) || isRulerName(b.name)) continue;
    const ox = a.worldX < b.worldX + b.width && b.worldX < a.worldX + a.width;
    const oy = a.worldY < b.worldY + b.height && b.worldY < a.worldY + a.height;
    if (ox && oy) overlaps++;
  }
}

const landers = LANDER_NAMES
  .map((n) => placed.find((b) => b.name === n))
  .filter(Boolean);
const landerOk = landers.length < 2 || landers.every((b, i) => {
  if (i === 0) return true;
  const prev = landers[i - 1];
  const sameY = Math.abs((b.worldY || 0) - (landers[0].worldY || 0)) <= 2;
  const toRight = (b.worldX || 0) + 2 >= (prev.worldX || 0) + (prev.width || 0);
  return sameY && toRight;
});
const extraRulers = placed.filter((b) => isRulerName(b.name) && b.name !== "Ruler · desktop");

await call("finish_working_on_nodes", {});

console.log(JSON.stringify({
  arranged: updates.length,
  rows: 1,
  overlaps,
  landerOk,
  extraRulers: extraRulers.map((b) => b.name),
  order: planned.map((r) => r.name),
  layout: planned,
}, null, 1));
