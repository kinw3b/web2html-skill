#!/usr/bin/env node
// Assemble a captured homepage (or lander) into a Paper artboard.
//
// Unlike import-sections.mjs, this writes **layers only** — no source
// screenshot artboard. Drop order under Ruler · desktop:
// Source · {page} → landers → A/6 → Interactive components.
// After all width assembles (1600 / 768 / 390), run
// arrange-artboards.mjs so that row is the source of truth.
// Section QA is done against on-disk JPEGs from experiment-capture-home.mjs.
// After each section insert, hug that layer with height: min-content
// (Pitfall #67) so a captured px box cannot clip titles.
// Before write_html, reorderOverlayPaintOrder stacks image → dim overlay →
// type last (Pitfall #84). Do not clone the overlay on top.
// Each --width assemble writes that capture's HTML as-is. There is no
// wrap-copy helper: do not lift flex-wrap / round(N%) / 2+1 from 768
// onto 1600/1440. Match icon size + container box + gap from the
// live/pre-pesticide inventory at this width (Pitfall #75).
//
// Default: reuse PAPER_FILE_ID / --file-id (required) and create an artboard
// inside that file. Pass --new-file only when you explicitly want a fresh
// Paper document (optional --file-name).
//
// Usage:
//   node assemble-lander.mjs --manifest capture/home/manifest.json \
//     [--file-id <id>] [--new-file] [--file-name "…"] \
//     [--prepend nav.html] [--width 1600] [--name "home-desktop"] \
//     [--out assemble-result.json] [--pace 2500] [--no-launch]
//
// Prints a JSON summary with fileId + url on stdout.

import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { call, getFileId, setFileId } from "./mcp-client.mjs";
import { ensurePaper } from "./ensure-paper.mjs";
import { localizeHtml } from "./localize-html-images.mjs";
import { flattenDecorativeAbs } from "./flatten-decorative-abs.mjs";
import { trimPaperStyles } from "./trim-paper-styles.mjs";
import { reorderOverlayPaintOrder } from "./overlay-paint-order.mjs";
import { bindInlinePaperFonts } from "./library-tokens.mjs";
import { isDesktopCapture, paperSectionName, retireSectionIdLegend, stampSectionIds, SECTION_ID_LEGEND } from "./section-ids.mjs";
import { canvasSlot, contentOrigin, ensureRulers, isReviewBoard, landerRowArtboards } from "./rulers.mjs";

function canvasSlotBeforeLander(name, artboardName) {
  return canvasSlot(name) < canvasSlot(artboardName || "home-desktop");
}
import { hasSourceSectionShots, sourcePageFromArtboard } from "./source-sections.mjs";
import { seedSourceBoard } from "./seed-source-board.mjs";

const argv = process.argv.slice(2);
const arg = (name, fallback) => {
  const i = argv.indexOf(`--${name}`);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : fallback;
};

const manifestPath = resolve(arg("manifest") || argv.find((a) => !a.startsWith("--")) || "");
if (!manifestPath || !existsSync(manifestPath)) {
  console.error("--manifest <path> is required");
  process.exit(1);
}

const prependPath = arg("prepend");
const newFile = argv.includes("--new-file");
if (arg("file-id")) setFileId(arg("file-id"));
const pinnedId = arg("file-id") || process.env.PAPER_FILE_ID || getFileId();
if (!newFile && !pinnedId) {
  console.error(
    "PAPER_FILE_ID or --file-id is required. Pass --new-file only when you want a fresh Paper file.",
  );
  process.exit(1);
}
const pace = parseInt(arg("pace", "2500"), 10);
const outPath = arg("out");
const log = (...a) => console.error("·", ...a);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
const hostname = (() => {
  try { return new URL(manifest.url).hostname; } catch { return "lander"; }
})();
const artboardName = arg("name", hostname);
const width = parseInt(arg("width", String(manifest.width || 1600)), 10);
const desktopSections = isDesktopCapture({ width, name: artboardName });
const sections = stampSectionIds(
  (manifest.sections || []).filter((s) => s.status === "ok"),
  { desktop: desktopSections },
);
if (!sections.length && !prependPath) {
  console.error("manifest has no successfully captured sections");
  process.exit(1);
}

await ensurePaper({ launch: !argv.includes("--no-launch"), log });

function payload(result) {
  for (const item of result.content ?? []) {
    if (item.type === "text") {
      try { return JSON.parse(item.text); } catch { return { text: item.text }; }
    }
  }
  return {};
}

// ---- 1. target file (reuse pinned project file unless --new-file) ----
let fileId;
let fileName;
let created = {};
let fileMode;

if (newFile) {
  fileName = arg("file-name", `${artboardName} — assemble-lander`);
  log(`creating new Paper file "${fileName}"…`);
  created = payload(await call("create_file", { name: fileName }));
  fileId = created.fileId || created.id;
  if (!fileId) throw new Error(`create_file returned no id: ${JSON.stringify(created)}`);
  setFileId(fileId);
  fileMode = "created";
  log(`  file ${fileId} (created)`);
  await call("open_file", { fileId });
} else {
  fileId = pinnedId;
  setFileId(fileId);
  fileMode = "reuse";
  log(`opening Paper file ${fileId}…`);
  await call("open_file", { fileId });
  log(`  file ${fileId} (reuse)`);
}

const info = payload(await call("get_basic_info", {}));
const fileUrl = created.url || created.fileUrl || info.fileUrl || info.url || null;
fileName = info.fileName || fileName;
log(`file "${info.fileName}" / ${info.pageName}`);

// ---- 1b. P-0 ruler, then Source · home (screenshots first) ----
await ensureRulers({
  call,
  fileId,
  boards: info.artboards || [],
  init: true,
  log,
});
const ruled = payload(await call("get_basic_info", { fileId }));
await retireSectionIdLegend({ call, boards: ruled.artboards || [], log });

if (desktopSections && !argv.includes("--no-source-board")) {
  const srcDir = join(dirname(manifestPath), "source-sections");
  if (hasSourceSectionShots(srcDir)) {
    await seedSourceBoard({
      dir: srcDir,
      page: arg("page", sourcePageFromArtboard(artboardName)),
      fileId,
      call,
      log,
    });
  }
}
const afterSource = payload(await call("get_basic_info", {}));

// ---- 2. one flex-column artboard ----
const totalHeight = sections.reduce((n, s) => n + (s.h || 0), 0) || 2000;
const origin = contentOrigin(afterSource.artboards || ruled.artboards || []);
const content = landerRowArtboards(afterSource.artboards || ruled.artboards || [])
  .filter((a) => a.name !== SECTION_ID_LEGEND && canvasSlotBeforeLander(a.name, artboardName));
const rightEdge = content.reduce(
  (max, a) => Math.max(max, (a.worldX || 0) + (a.width || 0)),
  origin.left,
);
const x = content.length ? Math.round(rightEdge + 80) : origin.left;
const y = origin.top;
const styles = {
  width: `${width}px`,
  height: `${totalHeight}px`,
  display: "flex",
  flexDirection: "column",
  backgroundColor: "#ffffff",
  left: x,
  top: y,
};

let containerId = null;
try {
  const res = payload(await call("create_artboard", { name: artboardName, styles }));
  containerId = res.createdNodes?.[0]?.id || res.id || res.nodeId;
  log(`artboard ${containerId} (${width}×${totalHeight} @ ${x},${y})`);
  if (containerId) {
    await call("update_styles", {
      updates: [{ nodeIds: [containerId], styles: { left: `${x}px`, top: `${y}px` } }],
    });
  }
} catch (err) {
  log(`create_artboard failed (${err.message.split("\n")[0]})`);
  log("falling back: first write to page root becomes the container");
}

// ---- 3. optional prepend (e.g. a separately captured nav.html) ----
const written = [];
let failed = 0;
// Lean 1.2: do not collect or write paper-layer-ids.json. Paper names stay
// the scrape name (or Paper's own). Sidecars are optional and invisible.

const projectRoot = resolve(manifestPath, "../..");

async function writeLayer(name, html, indexLabel) {
  const localized = await localizeHtml(html, { projectRoot });
  if (localized.missing.length) {
    log(`  ! ${name}: ${localized.missing.length} image(s) still remote`);
  }
  const flat = flattenDecorativeAbs(localized.html);
  if (flat.removed.length) log(`  flattened ${flat.removed.length} abs decoration(s) in ${name}`);
  html = trimPaperStyles(flat.html);
  const stacked = reorderOverlayPaintOrder(html);
  if (stacked.moved.length) log(`  restacked ${stacked.moved.length} overlay(s) in ${name} (Pitfall #84)`);
  html = bindInlinePaperFonts(stacked.html);
  const target = containerId || info.rootNodeId;
  try {
    const res = payload(await call("write_html", {
      html,
      targetNodeId: target,
      mode: "insert-children",
    }));
    const createdNodes = res.createdNodes || [];
    const nodeId = createdNodes[0]?.id;

    if (!containerId && nodeId) {
      containerId = nodeId;
      log(`adopted ${containerId} as container`);
    }

    if (nodeId) {
      await call("rename_nodes", { updates: [{ nodeId, name }] });
      try {
        await call("update_styles", {
          updates: [{ nodeIds: [nodeId], styles: { height: "min-content" } }],
        });
      } catch (err) {
        log(`  ! ${name}: could not hug height (${String(err.message || err).split("\n")[0]})`);
      }
      written.push({ name, nodeId, bytes: html.length });
      log(`  ✓ ${indexLabel}  ${name} → ${nodeId}`);
    } else {
      written.push({ name, nodeId: null, bytes: html.length });
      log(`  ✓ ${indexLabel}  ${name} (no node id returned)`);
    }
  } catch (err) {
    failed++;
    const msg = err.message.split("\n")[0];
    log(`  ✗ ${indexLabel}  ${name}: ${msg}`);
  }
}

if (prependPath) {
  const abs = resolve(prependPath);
  if (!existsSync(abs)) {
    console.error(`--prepend not found: ${abs}`);
    process.exit(1);
  }
  const html = readFileSync(abs, "utf8");
  await writeLayer("nav", html, "prepend");
  if (pace > 0) await sleep(pace);
}

// ---- 4. stack section HTML (layers only — not screenshots) ----
for (let i = 0; i < sections.length; i++) {
  const s = sections[i];
  const raw = readFileSync(s.file, "utf8");
  await writeLayer(paperSectionName(s, { desktop: desktopSections }), raw, `${s.id || i + 1}/${sections.length}`);

  if (i < sections.length - 1 && pace > 0) {
    const imgCount = (raw.match(/<img/g) || []).length;
    await sleep(pace + imgCount * 250);
  }
}

if (pace > 0) await sleep(pace * 2);

// ---- 5. height fit-content ----
if (containerId) {
  try {
    await call("update_styles", {
      updates: [{ nodeIds: [containerId], styles: { height: "fit-content" } }],
    });
    log("artboard height → fit-content");
  } catch (err) {
    log(`could not set fit-content: ${err.message.split("\n")[0]}`);
  }
}

await call("finish_working_on_nodes", {});

const summary = {
  fileId,
  url: fileUrl,
  file: info.fileName || fileName,
  fileMode,
  page: info.pageName,
  containerId,
  artboardName,
  width,
  written: written.length,
  failed,
  names: written.map((w) => w.name),
  manifest: manifestPath,
};

if (outPath) {
  writeFileSync(resolve(outPath), JSON.stringify(summary, null, 2));
  log(`wrote ${outPath}`);
}

console.log(JSON.stringify(summary, null, 1));
