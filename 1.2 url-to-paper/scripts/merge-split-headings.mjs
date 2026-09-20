#!/usr/bin/env node
// Detect + repair Framer line-box headings that landed as stacked line rows.
//
// Serializer / Paper import often splits one title into row Frames that each
// hold one Text ("Take" / "control" / "of your personal spending today."),
// or into sibling Text nodes, and leaves a scribble SVG in flow. That is
// Pitfall #69 — not a design system. Default is merge into one Text node.
//
// Library (no Paper):
//   findSplitHeadings(nodes, { artboard })
//   planSplitHeadingMerges(nodes, { artboard })
//   applySplitHeadingPlans(nodes, plans)
//   headingMergeHtml(plan)
//
// Repair (Paper MCP, same client as flatten-paper-abs / assemble-lander):
//   PAPER_FILE_ID=… node merge-split-headings.mjs [--artboard <id>] [--dry-run]
//
// Whole-file default walks home-desktop / home-768 / home-390.

import { fileURLToPath } from "node:url";
import { resolve } from "node:path";

const HEADING_NAME = /\b(heading|headline|title|display|h1)\b/i;
const SECTION_NAME = /^\d+\s*·\s*/;
const DECOR_NAME = /scribble|underline|oval|highlight|decoration|swirl|stroke|squiggle/i;
const SVG_PART = /^(svg|path|svgvisualelement|circle|rect|ellipse|line|polygon|polyline|g|use)$/i;
const SKIP_BOARD = /^(Ruler · |A\/6 · )|source screenshot|Design Library|Desktop section IDs/;
const PAGE = /^(home-desktop|home-768|home-390)$/;
const DISPLAY_PX = 28;
const TYPE_SIZE_SLACK = 4;
const DEFAULT_WALK_DEPTH = 16;

export function joinHeadingText(parts) {
  return parts.reduce((acc, part) => {
    const p = String(part || "").replace(/\s+/g, " ").trim();
    if (!p) return acc;
    if (!acc) return p;
    if (/^[,.;:!?)]/.test(p)) return acc + p;
    return `${acc} ${p}`;
  }, "");
}

export function isSvgPart(n) {
  if (!n) return false;
  return SVG_PART.test(String(n.component || "")) || SVG_PART.test(String(n.name || ""));
}

export function isTextNode(n) {
  if (!n) return false;
  const c = String(n.component || "").toLowerCase();
  if (c === "svg" || c === "image" || c === "artboard" || isSvgPart(n)) return false;
  if (/button|link|nav|input/.test(c)) return false;
  if (/\b(button|cta|navlink|footerlink)\b/i.test(n.name || "")) return false;
  if (c === "text" || /^h[1-6]$/.test(c) || c === "p") return true;
  const text = String(n.textContent || "").trim();
  return Boolean(text) && (n.childCount || 0) === 0;
}

export function isHeadingDecoration(n) {
  if (!n) return false;
  const c = String(n.component || "").toLowerCase();
  if (c === "svg") return true;
  if (isSvgPart(n)) return false;
  if ((n.childCount || n.childIds?.length || 0) > 0) return false;
  return DECOR_NAME.test(String(n.name || ""));
}

function fontPx(n) {
  const v = parseFloat(n?.fontSize);
  return Number.isFinite(v) ? v : 0;
}

function typeSignature(n) {
  return {
    size: fontPx(n),
    family: String(n.fontFamily || "").split(",")[0].trim().toLowerCase(),
    weight: String(n.fontWeight || "").trim(),
    color: String(n.color || "").replace(/\s+/g, "").toLowerCase(),
  };
}

export function sameTypeStyle(a, b) {
  const ta = typeSignature(a);
  const tb = typeSignature(b);
  if (ta.size && tb.size && Math.abs(ta.size - tb.size) > TYPE_SIZE_SLACK) return false;
  if (ta.family && tb.family && ta.family !== tb.family) return false;
  if (ta.weight && tb.weight && ta.weight !== tb.weight) return false;
  return true;
}

function ancestorNames(node, nodes, depth = 6) {
  const names = [];
  let cur = node;
  for (let i = 0; i < depth && cur; i++) {
    names.push(String(cur.name || ""));
    cur = cur.parentId ? nodes.get(cur.parentId) : null;
  }
  return names;
}

export function isHeadingContext(parent, texts, nodes) {
  if (ancestorNames(parent, nodes).some((n) => HEADING_NAME.test(n))) return true;
  const sizes = texts.map(fontPx);
  if (Math.max(0, ...sizes) >= DISPLAY_PX) return true;
  return false;
}

export function stackedAsRows(texts) {
  if (texts.length < 2) return false;
  const col = [...texts].sort((a, b) => (a.worldY ?? 0) - (b.worldY ?? 0));
  for (let i = 1; i < col.length; i++) {
    const prev = col[i - 1];
    const cur = col[i];
    if (prev.worldY == null || cur.worldY == null || prev.h == null || cur.h == null) {
      continue;
    }
    const gap = cur.worldY - (prev.worldY + prev.h);
    const overlapX =
      Math.min((prev.worldX ?? 0) + (prev.w ?? 0), (cur.worldX ?? 0) + (cur.w ?? 0)) -
      Math.max(prev.worldX ?? 0, cur.worldX ?? 0);
    const sideBySide =
      overlapX > 8 &&
      Math.abs(cur.worldY - prev.worldY) < Math.min(prev.h, cur.h) * 0.4;
    if (sideBySide) return false;
    if (gap > 48) return false;
  }
  return true;
}

export function hasExplicitWrapConstraint(texts, parent, extras = []) {
  const pw = parent?.w;
  if (!pw) return false;
  return [...texts, ...extras].some((n) => {
    const mw = parseFloat(n.maxWidth);
    if (!Number.isFinite(mw) || mw <= 0) return false;
    return mw < pw * 0.7 && (n.w ?? 0) >= mw - 4;
  });
}

function isDuplicateStack(texts) {
  const norms = texts.map((t) => String(t.textContent || "").trim().toLowerCase()).filter(Boolean);
  return norms.length >= 2 && norms.every((t) => t === norms[0]);
}

export function inferTextAlign(texts, parent) {
  const authored = [parent, ...texts]
    .map((n) => String(n?.textAlign || n?.alignItems || "").toLowerCase());
  if (authored.some((v) => v === "center" || v === "centre")) return "center";
  if (parent?.w && parent.worldX != null) {
    const mid = parent.worldX + parent.w / 2;
    const centered = texts.filter((t) => {
      if (t.worldX == null || t.w == null) return false;
      return Math.abs(t.worldX + t.w / 2 - mid) <= Math.max(24, parent.w * 0.12);
    });
    if (centered.length >= Math.ceil(texts.length * 0.6)) return "center";
  }
  return "left";
}

function collectRuns(kids) {
  const runs = [];
  let cur = [];
  const flush = () => {
    if (cur.filter(isTextNode).length >= 2) runs.push(cur);
    cur = [];
  };
  for (const k of kids) {
    if (isTextNode(k) || isHeadingDecoration(k)) cur.push(k);
    else flush();
  }
  flush();
  return runs;
}

function descendants(node, nodes, acc = []) {
  for (const id of node.childIds || []) {
    const child = nodes.get(id);
    if (!child) continue;
    acc.push(child);
    descendants(child, nodes, acc);
  }
  return acc;
}

function isFrameLike(n) {
  if (!n || isTextNode(n) || isHeadingDecoration(n)) return false;
  const c = String(n.component || "").toLowerCase();
  if (/button|link|nav|input|image|svg|artboard|text/.test(c)) return false;
  if (/\b(button|cta|navlink|footerlink)\b/i.test(n.name || "")) return false;
  return c === "frame" || c === "div" || c === "group" || c === "";
}

export function lineRowFromFrame(frame, nodes) {
  if (!isFrameLike(frame)) return null;
  const desc = descendants(frame, nodes);
  const texts = desc.filter(isTextNode);
  if (texts.length !== 1) return null;
  const extras = desc.filter((n) => {
    if (isTextNode(n) || isHeadingDecoration(n) || isFrameLike(n) || isSvgPart(n)) return false;
    return n.component === "Image" || Boolean(String(n.textContent || "").trim());
  });
  if (extras.length) return null;
  return {
    frame,
    text: texts[0],
    decorations: desc.filter(isHeadingDecoration),
  };
}

function collectLineRowRuns(kids, nodes) {
  const runs = [];
  let cur = [];
  const flush = () => {
    if (cur.length >= 2) runs.push(cur);
    cur = [];
  };
  for (const k of kids) {
    const row = lineRowFromFrame(k, nodes);
    if (row) cur.push(row);
    else flush();
  }
  flush();
  return runs;
}

function typeGroups(rows) {
  const groups = [];
  let cur = [];
  for (const row of rows) {
    if (!cur.length || sameTypeStyle(row.text, cur[0].text)) cur.push(row);
    else {
      if (cur.length >= 2) groups.push(cur);
      cur = [row];
    }
  }
  if (cur.length >= 2) groups.push(cur);
  return groups;
}

function shouldMergeRun(texts, parent, nodes, frames = []) {
  if (texts.length < 2) return false;
  if (isDuplicateStack(texts)) return false;
  if (!isHeadingContext(parent, texts, nodes)) return false;
  if (!texts.every((t) => sameTypeStyle(t, texts[0]))) return false;
  if (!stackedAsRows(frames.length ? frames : texts)) return false;
  if (hasExplicitWrapConstraint(texts, parent, frames)) return false;
  return true;
}

function decorationPlan(node, parent) {
  const left =
    node.worldX != null && parent?.worldX != null
      ? Math.round(node.worldX - parent.worldX)
      : parseFloat(node.left) || 0;
  const top =
    node.worldY != null && parent?.worldY != null
      ? Math.round(node.worldY - parent.worldY)
      : parseFloat(node.top) || 0;
  return {
    id: node.id,
    name: node.name,
    position: "absolute",
    pointerEvents: "none",
    decorative: true,
    parentId: parent?.id,
    left,
    top,
    html: node.html || "",
  };
}

function buildPlan(parent, texts, decorations, { artboard, deleteIds = [] }) {
  const keep = texts[0];
  const text = joinHeadingText(texts.map((t) => t.textContent));
  return {
    artboard,
    parentId: parent.id,
    parentName: parent.name,
    keepId: keep.id,
    text,
    textAlign: inferTextAlign(texts, parent),
    deleteIds: [...new Set(deleteIds)],
    decorations: decorations.map((n) => decorationPlan(n, parent)),
    nodeIds: texts.map((t) => t.id),
  };
}

export function planSplitHeadingMerges(nodes, { artboard = "" } = {}) {
  if (SKIP_BOARD.test(String(artboard || ""))) return [];
  const plans = [];
  const seen = new Set();
  for (const parent of nodes.values()) {
    if (!parent.childIds || parent.childIds.length < 2) continue;
    const kids = parent.childIds.map((id) => nodes.get(id)).filter(Boolean);

    for (const group of collectLineRowRuns(kids, nodes).flatMap(typeGroups)) {
      const texts = group.map((row) => row.text);
      const frames = group.map((row) => row.frame);
      if (!shouldMergeRun(texts, parent, nodes, frames)) continue;
      const decorations = group.flatMap((row) => row.decorations);
      const deleteIds = [
        ...texts.slice(1).map((t) => t.id),
        ...frames.slice(1).map((f) => f.id),
      ];
      const plan = buildPlan(parent, texts, decorations, { artboard, deleteIds });
      plans.push(plan);
      for (const id of plan.nodeIds) seen.add(id);
    }

    for (const run of collectRuns(kids)) {
      const texts = run.filter(isTextNode);
      if (texts.some((t) => seen.has(t.id))) continue;
      if (!shouldMergeRun(texts, parent, nodes)) continue;
      plans.push(buildPlan(parent, texts, run.filter(isHeadingDecoration), {
        artboard,
        deleteIds: texts.slice(1).map((t) => t.id),
      }));
    }
  }
  return plans;
}

export function findSplitHeadings(nodes, { artboard = "" } = {}) {
  return planSplitHeadingMerges(nodes, { artboard }).map((plan) => ({
    artboard,
    type: "split-heading",
    severity: "high",
    node: plan.keepId,
    name: plan.parentName,
    parent: plan.parentName,
    detail:
      `heading is ${plan.nodeIds.length} stacked line rows ("${plan.text}"). ` +
      `Merge into one Text node (text-align: ${plan.textAlign}) and pin decorations ` +
      `absolute + data-decorative. Run merge-split-headings.mjs (Pitfall #69).`,
  }));
}

function detachChild(next, childId) {
  const child = next.get(childId);
  if (!child?.parentId) return;
  const old = next.get(child.parentId);
  if (old?.childIds) {
    old.childIds = old.childIds.filter((id) => id !== childId);
    old.childCount = old.childIds.length;
  }
}

function deleteSubtree(next, id, keep) {
  const n = next.get(id);
  if (!n || keep.has(id)) return;
  for (const cid of [...(n.childIds || [])]) deleteSubtree(next, cid, keep);
  detachChild(next, id);
  next.delete(id);
}

export function applySplitHeadingPlans(nodes, plans) {
  const next = new Map();
  for (const [id, n] of nodes) next.set(id, { ...n, childIds: n.childIds ? [...n.childIds] : n.childIds });
  for (const plan of plans) {
    const keep = next.get(plan.keepId);
    if (keep) {
      keep.textContent = plan.text;
      keep.textAlign = plan.textAlign;
      keep.name = plan.text;
    }
    const parent = next.get(plan.parentId);
    if (parent && !/absolute|relative|fixed/.test(String(parent.position || ""))) {
      parent.position = "relative";
    }
    const keepSet = new Set([plan.keepId, ...plan.decorations.map((d) => d.id)]);
    for (const dec of plan.decorations) {
      const n = next.get(dec.id);
      if (!n) continue;
      detachChild(next, dec.id);
      n.position = "absolute";
      n.pointerEvents = "none";
      n.decorative = true;
      n.parentId = plan.parentId;
      n.left = `${dec.left}px`;
      n.top = `${dec.top}px`;
      if (parent?.childIds && !parent.childIds.includes(dec.id)) {
        parent.childIds.push(dec.id);
        parent.childCount = parent.childIds.length;
      }
    }
    for (const id of plan.deleteIds) deleteSubtree(next, id, keepSet);
    if (parent?.childIds) {
      parent.childIds = parent.childIds.filter((id) => next.has(id));
      parent.childCount = parent.childIds.length;
    }
  }
  return next;
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function headingMergeHtml(plan) {
  const decorations = (plan.decorations || []).map((d) => {
    const style =
      `position: absolute; pointer-events: none; left: ${d.left}px; top: ${d.top}px`;
    if (d.html && /<svg[\s>]/i.test(d.html)) {
      return d.html.replace(
        /<svg\b/i,
        `<svg data-decorative style="${style}"`,
      );
    }
    return `<svg data-decorative style="${style}" aria-hidden="true"></svg>`;
  }).join("");
  return (
    `<div style="position: relative; text-align: ${plan.textAlign}">` +
    `<p style="text-align: ${plan.textAlign}">${escapeHtml(plan.text)}</p>` +
    decorations +
    `</div>`
  );
}

function payload(result) {
  for (const item of result.content ?? []) {
    if (item.type === "text") {
      try { return JSON.parse(item.text); } catch { return { text: item.text }; }
    }
  }
  return {};
}

const num = (v) => {
  if (typeof v === "number") return v;
  if (typeof v === "string") {
    const n = parseFloat(v);
    return Number.isNaN(n) ? null : n;
  }
  return null;
};

export function childrenFromPayload(raw) {
  if (!raw) return [];
  if (Array.isArray(raw.children)) return raw.children;
  if (Array.isArray(raw.nodes)) return raw.nodes;
  if (Array.isArray(raw)) return raw;
  return [];
}

export function shouldDescend(kid) {
  if (!kid) return false;
  if (kid.childCount == null) return true;
  if (Number(kid.childCount) > 0) return true;
  return SECTION_NAME.test(kid.name || "");
}

async function walkFrom(call, nodes, rootId, maxDepth) {
  let frontier = [rootId];
  for (let d = 0; d < maxDepth; d++) {
    const next = [];
    for (const pid of frontier) {
      let kids = [];
      try {
        kids = childrenFromPayload(payload(await call("get_children", { nodeId: pid })));
      } catch (err) {
        console.error("· get_children failed", pid, String(err.message || err).split("\n")[0]);
        continue;
      }
      const parent = nodes.get(pid);
      if (parent) {
        parent.childIds = kids.map((k) => k.id);
        parent.childCount = kids.length;
      }
      for (const k of kids) {
        if (!nodes.has(k.id)) {
          nodes.set(k.id, {
            id: k.id,
            name: k.name,
            component: k.component,
            childCount: k.childCount,
            worldX: k.worldX,
            worldY: k.worldY,
            depth: (parent?.depth ?? 0) + 1,
            parentId: pid,
          });
        }
        if (shouldDescend(k)) next.push(k.id);
      }
    }
    if (!next.length) break;
    frontier = next;
  }
}

export async function collectNodes(call, rootId, rootMeta = {}, maxDepth = DEFAULT_WALK_DEPTH) {
  const nodes = new Map();
  nodes.set(rootId, { id: rootId, ...rootMeta, depth: 0, parentId: null });
  await walkFrom(call, nodes, rootId, maxDepth);
  const sections = [...nodes.values()].filter((n) => n.id !== rootId && SECTION_NAME.test(n.name || ""));
  for (const sec of sections) {
    await walkFrom(call, nodes, sec.id, maxDepth);
  }

  const ids = [...nodes.keys()];
  for (let i = 0; i < ids.length; i += 8) {
    const chunk = ids.slice(i, i + 8);
    await Promise.all(chunk.map(async (id) => {
      if (id === rootId) return;
      try {
        const d = payload(await call("get_node_info", { nodeId: id }));
        const n = nodes.get(id);
        if (!n) return;
        n.w = num(d.width);
        n.h = num(d.height);
        if (d.worldX != null) n.worldX = d.worldX;
        if (d.worldY != null) n.worldY = d.worldY;
        n.textContent = d.textContent;
      } catch {}
    }));
  }

  for (let i = 0; i < ids.length; i += 60) {
    try {
      const styles = payload(await call("get_computed_styles", { nodeIds: ids.slice(i, i + 60) })).styles || {};
      for (const [id, s] of Object.entries(styles)) {
        const n = nodes.get(id);
        if (!n) continue;
        n.position = s.position;
        n.display = s.display;
        n.fontSize = s.fontSize;
        n.fontFamily = s.fontFamily;
        n.fontWeight = s.fontWeight;
        n.color = s.color;
        n.textAlign = s.textAlign;
        n.maxWidth = s.maxWidth;
        n.alignItems = s.alignItems;
        n.justifyContent = s.justifyContent;
        n.left = s.left;
        n.top = s.top;
        n.pointerEvents = s.pointerEvents;
      }
    } catch {}
  }
  return nodes;
}

export async function setHeadingText(call, nodeId, text) {
  try {
    await call("set_text_content", { updates: [{ nodeId, textContent: text }] });
    return "set_text_content";
  } catch {
    await call("write_html", {
      html: `<p style="text-align: center">${escapeHtml(text)}</p>`,
      targetNodeId: nodeId,
      mode: "replace",
    });
    return "write_html";
  }
}

async function reparentNode(call, nodeId, parentId) {
  for (const [name, args] of [
    ["move_nodes", { nodeIds: [nodeId], parentId }],
    ["reparent_nodes", { nodeIds: [nodeId], parentId }],
  ]) {
    try {
      await call(name, args);
      return name;
    } catch {}
  }
  return null;
}

export async function applyPlansToPaper(call, plans, { dry = false } = {}) {
  const applied = [];
  for (const plan of plans) {
    if (dry) {
      applied.push({ ...plan, dry: true });
      continue;
    }
    for (const dec of plan.decorations) {
      if (plan.parentId) await reparentNode(call, dec.id, plan.parentId);
    }
    const textHow = await setHeadingText(call, plan.keepId, plan.text);
    const updates = [
      { nodeIds: [plan.keepId], styles: { textAlign: plan.textAlign } },
    ];
    if (plan.parentId) {
      updates.push({ nodeIds: [plan.parentId], styles: { position: "relative" } });
    }
    for (const dec of plan.decorations) {
      updates.push({
        nodeIds: [dec.id],
        styles: {
          position: "absolute",
          pointerEvents: "none",
          left: `${dec.left}px`,
          top: `${dec.top}px`,
        },
      });
    }
    if (updates.length) await call("update_styles", { updates });
    if (plan.deleteIds.length) {
      await call("delete_nodes", { nodeIds: plan.deleteIds });
    }
    applied.push({ ...plan, textHow });
  }
  return applied;
}

async function main() {
  const { call, setFileId, getFileId } = await import("./mcp-client.mjs");
  const { mcpPayload } = await import("./rulers.mjs");

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

  const info = mcpPayload(await call("get_basic_info", {}));
  let boards = info.artboards || [];
  if (only) boards = boards.filter((b) => b.id === only || b.name === only);
  else boards = boards.filter((b) => PAGE.test(b.name) && !SKIP_BOARD.test(b.name));
  if (!boards.length) {
    console.error("no lander artboards found (home-desktop / home-768 / home-390)");
    process.exit(1);
  }

  const allPlans = [];
  for (const ab of boards) {
    log(`scan ${ab.name}`);
    const nodes = await collectNodes(call, ab.id, {
      name: ab.name,
      component: "Artboard",
      worldX: ab.worldX,
      worldY: ab.worldY,
      childCount: ab.childCount,
      w: ab.width,
      h: ab.height,
    });
    const plans = planSplitHeadingMerges(nodes, { artboard: ab.name });
    log(`  walked ${nodes.size} node(s), ${plans.length} split heading(s)`);
    allPlans.push(...plans);
  }

  const applied = await applyPlansToPaper(call, allPlans, { dry });
  if (!dry && applied.length) await call("finish_working_on_nodes", {});

  console.log(JSON.stringify({
    file: info.fileName,
    dry,
    merged: applied.length,
    plans: applied.map((p) => ({
      artboard: p.artboard,
      text: p.text,
      textAlign: p.textAlign,
      keepId: p.keepId,
      deleteIds: p.deleteIds,
      decorations: p.decorations.map((d) => d.id),
    })),
  }, null, 2));
}

const isCli = process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1]);
if (isCli) await main();
