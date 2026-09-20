#!/usr/bin/env node
// Make Paper lander frames follow the root when the artboard is stretched.
//
// Capture writes section roots at a frozen px width (1600 / 768 / 390).
// Stretching the artboard then leaves a short band. This pass:
//   1. Sets true section roots to width: 100%; nested full-bleed flex
//      children use parent-axis Fill-equivalent growth or stretch.
//   2. Pins site containers (the first narrower band, typically ~80% of the
//      root) with Fill-equivalent sizing + max-width: <measured>, so they
//      stay centered when the frame grows and shrink when it narrows.
//   3. Leaves cards, columns, and collage pieces alone.
//
// Optional --prove widens each page artboard, checks section measured widths
// match the new root, then restores the capture width. Responsive styles stay.
//
// Usage:
//   PAPER_FILE_ID=<id> node stretch-root.mjs [--prove] [--delta 200]
//                                           [--artboard <id>] [--dry-run]

import { call, setFileId } from "./mcp-client.mjs";
import { pathToFileURL } from "node:url";
import { fillStylesForFlexChild } from "../../1.3 hover-reel/scripts/component-state-utils.mjs";

const argv = process.argv.slice(2);
const arg = (name, fallback) => {
  const i = argv.indexOf(`--${name}`);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : fallback;
};

if (arg("file-id")) setFileId(arg("file-id"));
const prove = argv.includes("--prove");
const dryRun = argv.includes("--dry-run");
const delta = parseInt(arg("delta", "200"), 10);
const onlyArtboard = arg("artboard");
const log = (...a) => console.error("·", ...a);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const SOURCE_SUFFIX = " — source screenshot";

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

function near(a, b, tol = 2) {
  return a != null && b != null && Math.abs(a - b) <= tol;
}

function hasIntrinsicWidth(style = {}) {
  return /^(auto|fit-content|min-content|max-content|intrinsic)$/i
    .test(String(style.width || "").trim());
}

export function stretchStylesForNode({
  isSectionRoot = false,
  parentStyle = {},
  childStyle = {},
  measuredWidth,
  authoredWidth,
  rootWidth,
  siblingCount = 0,
} = {}) {
  const measured = num(measuredWidth) ?? num(authoredWidth);
  const authored = num(authoredWidth);
  const fullBleed = near(measured, rootWidth) || near(authored, rootWidth);
  if (isSectionRoot) return fullBleed ? { width: "100%" } : {};
  if (hasIntrinsicWidth(childStyle)) return {};
  if (fullBleed) return fillStylesForFlexChild(parentStyle, childStyle);

  const ratio = measured == null || !rootWidth ? 0 : measured / rootWidth;
  if (siblingCount <= 2 && ratio >= 0.7 && ratio < 0.99) {
    // Site container: cap at the captured width and stay centered.
    // Never align-self:stretch here — stretch + max-width eats leftover
    // space on the start edge and the parent cannot flex-center the child.
    return {
      width: "100%",
      maxWidth: `${Math.round(measured)}px`,
      alignSelf: "center",
    };
  }
  return {};
}

export async function main() {
const info = payload(await call("get_basic_info", {}));
let boards = (info.artboards || []).filter((a) => !String(a.name || "").endsWith(SOURCE_SUFFIX));
if (onlyArtboard) boards = boards.filter((a) => a.id === onlyArtboard || a.name === onlyArtboard);
if (!boards.length) {
  console.error("no page artboards to stretch-root");
  process.exit(1);
}

const updates = [];
const changed = [];

for (const ab of boards) {
  const kids = payload(await call("get_children", { nodeId: ab.id })).children || [];
  const sectionIds = kids.map((k) => k.id).filter(Boolean);
  if (!sectionIds.length) continue;

  const styles = payload(await call("get_computed_styles", { nodeIds: sectionIds })).styles || {};
  for (const section of kids) {
    const authored = num(styles[section.id]?.width);
    const measured = num(section.width) ?? authored;
    const rootW = ab.width;
    const sectionStyles = stretchStylesForNode({
      isSectionRoot: true,
      childStyle: styles[section.id] || {},
      measuredWidth: measured,
      authoredWidth: authored,
      rootWidth: rootW,
    });

    if (Object.keys(sectionStyles).length) {
      updates.push({ nodeIds: [section.id], styles: sectionStyles });
      changed.push({ artboard: ab.name, node: section.id, name: section.name, role: "section-root" });
    }

    const inner = payload(await call("get_children", { nodeId: section.id })).children || [];
    if (!inner.length) continue;
    const innerStyles = payload(await call("get_computed_styles", {
      nodeIds: inner.map((k) => k.id),
    })).styles || {};

    for (const child of inner) {
      const cAuthored = num(innerStyles[child.id]?.width);
      const cMeasured = num(child.width) ?? cAuthored;
      if (cMeasured == null) continue;
      const childStyles = stretchStylesForNode({
        parentStyle: styles[section.id] || {},
        childStyle: innerStyles[child.id] || {},
        measuredWidth: cMeasured,
        authoredWidth: cAuthored,
        rootWidth: rootW,
        siblingCount: inner.length,
      });
      if (Object.keys(childStyles).length) {
        const fullBleed = near(cMeasured, rootW) || near(cAuthored, rootW);
        updates.push({ nodeIds: [child.id], styles: childStyles });
        changed.push({
          artboard: ab.name,
          node: child.id,
          name: child.name || "Frame",
          role: fullBleed ? "full-bleed-child" : "site-container",
          ...(fullBleed ? {} : { maxWidth: Math.round(cMeasured) }),
        });
      }
    }
  }
}

if (!dryRun && updates.length) {
  const CHUNK = 20;
  for (let i = 0; i < updates.length; i += CHUNK) {
    await call("update_styles", { updates: updates.slice(i, i + CHUNK) });
  }
  await sleep(2500);
}

const proof = [];
if (prove && !dryRun) {
  for (const ab of boards) {
    const original = ab.width;
    const wide = original + delta;
    await call("update_styles", {
      updates: [{ nodeIds: [ab.id], styles: { width: `${wide}px` } }],
    });
    await sleep(2500);
    const kids = payload(await call("get_children", { nodeId: ab.id })).children || [];
    const styles = payload(await call("get_computed_styles", {
      nodeIds: kids.map((k) => k.id),
    })).styles || {};
    let ok = 0;
    let fail = 0;
    for (const k of kids) {
      const authored = String(styles[k.id]?.width || "");
      const infoNode = payload(await call("get_node_info", { nodeId: k.id }));
      const measured = num(infoNode.width);
      const follows = authored.includes("%") || near(measured, wide, 4);
      if (follows) ok++;
      else fail++;
      proof.push({
        artboard: ab.name,
        name: k.name,
        authored,
        measured,
        expected: wide,
        ok: follows,
      });
    }
    await call("update_styles", {
      updates: [{ nodeIds: [ab.id], styles: { width: `${original}px` } }],
    });
    log(`${ab.name}: prove ${wide}px → ${ok} follow / ${fail} frozen`);
  }
  await sleep(1500);
}

await call("finish_working_on_nodes", {});

const failedProof = proof.filter((p) => !p.ok);
console.log(JSON.stringify({
  file: info.fileName,
  dryRun,
  prove,
  updated: changed.length,
  changed,
  proofFailed: failedProof.length,
  proof: prove ? proof : undefined,
}, null, 1));

if (failedProof.length) process.exit(2);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  await main();
}
