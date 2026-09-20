#!/usr/bin/env node
// Import a captured section manifest into Paper, progressively.
//
// One artboard, sections stacked as NAMED children — the naming is the point:
// a whole-page write produces layers all called "Frame", which makes the
// Paper -> rebuild/ round trip semantically useless.
//
// Usage:
//   node import-sections.mjs <sections/manifest.json> [--new-file] [--name "…"]
//                            [--target <nodeId>] [--source-target <nodeId>]
//                            [--screenshots-only]
//                            [--new-source-artboard] [--no-launch]

import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { call } from "./mcp-client.mjs";
import { ensurePaper } from "./ensure-paper.mjs";
import { scaledImageDimensions } from "./paper-image-geometry.mjs";
import { localizeHtml } from "./localize-html-images.mjs";
import { flattenDecorativeAbs } from "./flatten-decorative-abs.mjs";
import { trimPaperStyles } from "./trim-paper-styles.mjs";
import { reorderOverlayPaintOrder } from "./overlay-paint-order.mjs";
import { bindInlinePaperFonts } from "./library-tokens.mjs";
import { isDesktopCapture, paperSectionName, retireSectionIdLegend, stampSectionIds, SECTION_ID_LEGEND } from "./section-ids.mjs";
import { contentOrigin, ensureRulers, isReviewBoard, landerRowArtboards } from "./rulers.mjs";

const argv = process.argv.slice(2);
const arg = (name, fallback) => {
  const i = argv.indexOf(`--${name}`);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : fallback;
};

const manifestPath = resolve(argv.find((a) => !a.startsWith("--")) || "sections/manifest.json");
const newFile = argv.includes("--new-file");
const newSourceArtboard = argv.includes("--new-source-artboard");
const screenshotsOnly = argv.includes("--screenshots-only");
const explicitTarget = arg("target");
const explicitSourceTarget = arg("source-target");
// Pause between writes. NOT cosmetic: Paper fetches every remote image while
// parsing, and back-to-back writes outrun that fetcher — images silently land
// as broken placeholders. Verified: the same section HTML that failed inside a
// 10-write burst imported perfectly when written alone.
const pace = parseInt(arg("pace", "2500"), 10);
const log = (...a) => console.error("·", ...a);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
const desktopSections = isDesktopCapture({ width: manifest.width, name: arg("name", "") });
function dropNestedChrome(list) {
  // Framer one-menu tree: header > header > nav. Nested chrome at the same
  // visual top must not become sibling Paper frames (triple navbar).
  const chrome = list.filter((s) => s.chrome || /^(header|nav|site-chrome)/i.test(s.name || s.slug || ""));
  const drop = new Set();
  for (const inner of chrome) {
    const sel = inner.selector || "";
    if (!sel) continue;
    const nested = chrome.some((outer) => {
      if (outer === inner) return false;
      const os = outer.selector || "";
      return os && sel.startsWith(`${os} > `);
    });
    if (nested) drop.add(inner);
  }
  if (drop.size) log(`dropped ${drop.size} nested chrome section(s) (keep outermost header only)`);
  return list.filter((s) => !drop.has(s));
}
const sections = stampSectionIds(
  dropNestedChrome((manifest.sections || []).filter((s) => s.status === "ok")),
  { desktop: desktopSections },
);
if (!sections.length && !screenshotsOnly) {
  console.error("manifest has no successfully captured sections");
  process.exit(1);
}
if (screenshotsOnly && !explicitTarget) {
  console.error("--screenshots-only requires --target <existing page artboard id>");
  process.exit(1);
}

const hostname = (() => {
  try { return new URL(manifest.url).hostname; } catch { return "capture"; }
})();
const artboardName = arg("name", hostname);

await ensurePaper({ launch: !argv.includes("--no-launch"), log });

// Helper: pull the first JSON payload out of an MCP tool result.
function payload(result) {
  for (const item of result.content ?? []) {
    if (item.type === "text") {
      try { return JSON.parse(item.text); } catch { return { text: item.text }; }
    }
  }
  return {};
}

// ---- 1. target file ----
if (newFile) {
  log("creating new Paper file…");
  const fileName = arg("file-name", `${artboardName} — url-to-paper`);
  const created = payload(await call("create_file", { name: fileName }));
  const fileId = created.fileId || created.id;
  if (!fileId) throw new Error(`create_file returned no id: ${JSON.stringify(created)}`);
  log(`  file ${fileId}`);
  await call("open_file", { fileId });
}

const info = payload(await call("get_basic_info", {}));
log(`file "${info.fileName}" / ${info.pageName} — ${info.artboardCount} existing artboard(s)`);

// ---- 1b. P-0 ruler BEFORE any lander ----
const fileId = info.fileId || info.id || process.env.PAPER_FILE_ID;
await ensureRulers({
  call,
  fileId,
  boards: info.artboards || [],
  init: true,
  log,
});
const ruled = payload(await call("get_basic_info", { ...(fileId ? { fileId } : {}) }));
await retireSectionIdLegend({ call, boards: ruled.artboards || [], log });

// ---- 2. container artboard ----
const totalHeight = sections.reduce((n, s) => n + (s.h || 0), 0) || 2000;
const width = manifest.width || 1600;

// Park it clear of anything already on the page. Ignore rulers, any existing
// Design Library, and review boards — none may sit between desktop and tablet.
const origin = contentOrigin(ruled.artboards || []);
const content = landerRowArtboards(ruled.artboards || [])
  .filter((a) => a.name !== SECTION_ID_LEGEND && !isReviewBoard(a.name));
const rightEdge = content.reduce(
  (max, a) => Math.max(max, (a.worldX || 0) + (a.width || 0)),
  origin.left,
);
const targetArtboard = explicitTarget
  ? (info.artboards || []).find((artboard) => artboard.id === explicitTarget)
  : null;
if (screenshotsOnly && !targetArtboard) {
  throw new Error(`--screenshots-only target ${explicitTarget} is not an artboard in the active Paper file`);
}
const sourceArtboard = explicitSourceTarget
  ? (info.artboards || []).find((artboard) => artboard.id === explicitSourceTarget)
  : null;
if (explicitSourceTarget && !sourceArtboard) {
  throw new Error(`--source-target ${explicitSourceTarget} is not an artboard in the active Paper file`);
}
const x = targetArtboard
  ? Math.round(targetArtboard.worldX || 0)
  : (content.length ? Math.round(rightEdge + 80) : origin.left);
const y = targetArtboard ? Math.round(targetArtboard.worldY || 0) : origin.top;

let containerId = explicitTarget || null;

if (!containerId) {
  const styles = {
    width: `${width}px`,
    height: `${totalHeight}px`,
      display: "flex",
      flexDirection: "column",
      backgroundColor: "#ffffff",
      left: x,
      top: y,
  };
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
    log("falling back: first section written to page root will become the container");
  }
}

// ---- 2b. SOURCE SCREENSHOT artboard (left of page) — MANDATORY when capture has shots ----
// Serializer often omits fixed/sticky nav & menus. The one full-page image is
// the ground-truth QA reference for rebuilding both chrome and content.
let refArtboardId = null;
const shotPath =
  (manifest.fullpagePaperScreenshot && existsSync(manifest.fullpagePaperScreenshot) && manifest.fullpagePaperScreenshot) ||
  (manifest.fullpageScreenshot && existsSync(manifest.fullpageScreenshot) && manifest.fullpageScreenshot) ||
  (manifest.screenshots?.fullpagePaper && existsSync(manifest.screenshots.fullpagePaper) && manifest.screenshots.fullpagePaper) ||
  (manifest.screenshots?.fullpage && existsSync(manifest.screenshots.fullpage) && manifest.screenshots.fullpage) ||
  null;
if (shotPath) {
  try {
    const buf = readFileSync(shotPath);
    const isJpeg = /\.jpe?g$/i.test(shotPath);
    const mime = isJpeg ? "image/jpeg" : "image/png";
    const b64 = buf.toString("base64");
    // Cap: if payload is enormous, skip Paper embed but keep disk path in summary
    const maxBytes = 12 * 1024 * 1024; // 12MB base64 ~9MB raw
    if (buf.length > maxBytes) {
      log(`  ! fullpage shot too large for Paper embed (${(buf.length / 1024 / 1024).toFixed(1)} MB) — disk only: ${shotPath}`);
    } else {
      const fullImage = scaledImageDimensions(buf, width);
      if (!fullImage) throw new Error("could not read fullpage image dimensions; refusing a collapsible Paper image layer");
      const refName = `${artboardName} — source screenshot`;
      // Prefer immediately left of the target. If that slot overlaps another
      // board (two landers on one row → 390 source lands on the 1600 lander),
      // walk left until the rect is clear. arrange-artboards.mjs then pairs
      // source + page on a shared Y. Do not set x/y — those do not move artboards.
      const sourceW = fullImage.displayWidth;
      const sourceH = fullImage.displayHeight;
      const existingRef = !newSourceArtboard
        ? sourceArtboard || (info.artboards || []).find((artboard) => artboard.name === refName)
        : null;
      const others = (info.artboards || []).filter(
        (a) => a.id !== existingRef?.id && a.id !== explicitTarget,
      );
      let refX = Math.round(x - sourceW - 100);
      for (let guard = 0; guard < 50; guard++) {
        const hit = others.find((b) => {
          const bx = b.worldX || 0, by = b.worldY || 0;
          const bw = b.width || 0, bh = b.height || 0;
          return refX < bx + bw && bx < refX + sourceW && y < by + bh && by < y + sourceH;
        });
        if (!hit) break;
        refX = Math.round((hit.worldX || 0) - sourceW - 100);
      }
      // Keep the reference image at the board origin. In-frame labels shift
      // hero/card landmarks even when both artboards share the same worldY.
      const refHeight = fullImage.displayHeight;
      const refStyles = {
        width: `${fullImage.displayWidth}px`,
        height: `${refHeight}px`,
        flexShrink: 0,
        overflow: "hidden",
        backgroundColor: "#ffffff",
        left: refX,
        top: y,
      };
      if (existingRef?.id) {
        refArtboardId = existingRef.id;
        try {
          const children = payload(await call("get_children", { nodeId: refArtboardId })).children || [];
          const childIds = children.map((child) => child.id).filter(Boolean);
          if (childIds.length) await call("delete_nodes", { nodeIds: childIds });
          await call("update_styles", { updates: [{ nodeIds: [refArtboardId], styles: refStyles }] });
          log(`reusing source screenshot artboard ${refArtboardId} and clearing ${childIds.length} stale child tree(s)`);
        } catch (err) {
          throw new Error(`could not repair existing source screenshot artboard ${refArtboardId}: ${err.message.split("\n")[0]}`);
        }
      }
      if (!refArtboardId) {
        const res = payload(await call("create_artboard", { name: refName, styles: refStyles }));
        refArtboardId = res.createdNodes?.[0]?.id || res.id || res.nodeId;
      }
      // The artboard name identifies the reference; the image is its only
      // child and starts at (0, 0), so its Y landmarks align with the page.
      const html = `<img src="data:${mime};base64,${b64}" style="width:${fullImage.displayWidth}px;height:${fullImage.displayHeight}px;min-width:${fullImage.displayWidth}px;min-height:${fullImage.displayHeight}px;max-width:none;display:block;object-fit:fill;flex:none" alt="source full page" />`;
      if (refArtboardId) {
        await call("write_html", { html, targetNodeId: refArtboardId, mode: "insert-children" });
        log(`  ✓ source screenshot artboard ${refArtboardId} @ x=${refX} · fullpage ${fullImage.displayWidth}×${fullImage.displayHeight}px ← ${shotPath}`);
        // The geometry is already explicit; this wait only gives Paper time to
        // decode the data URI before a QA screenshot is requested.
        await sleep(Math.min(12000, Math.max(pace, 2500) + Math.ceil(buf.length / 500000) * 250));
      }
    }
  } catch (err) {
    log(`  ! source screenshot artboard failed: ${err.message.split("\n")[0]}`);
  }
} else {
  log("  ! no fullpage screenshot in manifest — re-run capture-sections (v1.2+)");
}

// ---- 3. progressive writes ----
const written = [];
let failed = 0;

for (let i = 0; !screenshotsOnly && i < sections.length; i++) {
  const s = sections[i];
  const raw = readFileSync(s.file, "utf8");
  const localized = await localizeHtml(raw, { projectRoot: resolve(s.file, "../..") });
  const flat = flattenDecorativeAbs(localized.html);
  if (flat.removed.length) {
    log(`  flattened ${flat.removed.length} abs decoration(s) in ${s.name || s.slug}`);
  }
  const stacked = reorderOverlayPaintOrder(trimPaperStyles(flat.html));
  if (stacked.moved.length) {
    log(`  restacked ${stacked.moved.length} overlay(s) in ${s.name || s.slug} (Pitfall #84)`);
  }
  const html = bindInlinePaperFonts(stacked.html);

  const target = containerId || info.rootNodeId;
  const mode = "insert-children";

  try {
    const res = payload(await call("write_html", { html, targetNodeId: target, mode }));
    const created = res.createdNodes || [];
    const nodeId = created[0]?.id;

    // Fallback path: the very first write landed on the page root and Paper
    // wrapped it in an artboard — adopt that as the container.
    if (!containerId && nodeId) {
      containerId = nodeId;
      log(`adopted ${containerId} as container`);
    }

    if (nodeId) {
      const layerName = paperSectionName(s, { desktop: desktopSections });
      await call("rename_nodes", { updates: [{ nodeId, name: layerName }] });
      try {
        await call("update_styles", {
          updates: [{ nodeIds: [nodeId], styles: { width: "100%", flexShrink: "0" } }],
        });
      } catch {}
      written.push({
        name: layerName,
        slug: s.slug || s.name,
        id: s.id,
        nodeId,
        bytes: html.length,
        top: s.top,
        h: s.h,
        chrome: s.chrome,
      });
      log(`  ✓ ${s.id || i + 1}/${sections.length}  ${layerName} → ${nodeId}`);
    } else {
      written.push({ name: s.name, nodeId: null, bytes: html.length });
      log(`  ✓ ${s.id || i + 1}/${sections.length}  ${s.name} (no node id returned)`);
    }
  } catch (err) {
    failed++;
    const msg = err.message.split("\n")[0];
    log(`  ✗ ${i + 1}/${sections.length}  ${s.name}: ${msg}`);
    if (/weekly mcp limit/i.test(msg)) {
      log("    quota error — this has been seen as non-terminal; continuing");
    }
  }

  // Give Paper's image fetcher room before the next write. Scale the wait with
  // how image-heavy the section was.
  if (i < sections.length - 1 && pace > 0) {
    const imgCount = (html.match(/<img/g) || []).length;
    await sleep(pace + imgCount * 250);
  }
}

// Let the last section's images finish downloading before we screenshot.
if (!screenshotsOnly && pace > 0) await sleep(pace * 2);

// ---- 4. let the artboard fit its content ----
if (containerId && !screenshotsOnly) {
  try {
    // `nodeIds` is an ARRAY — the singular `nodeId` is silently ineffective.
    await call("update_styles", {
      updates: [{ nodeIds: [containerId], styles: { height: "fit-content" } }],
    });
    log("artboard height → fit-content");
  } catch (err) {
    log(`could not set fit-content: ${err.message.split("\n")[0]}`);
  }

  // Restore source vertical rhythm. Framer chrome is overlay; Paper stacks
  // in-flow. padding-top = this.top − (prev.top + prev.h) from the manifest.
  const flow = written.filter((w) => w.nodeId && !/hero-bg/i.test(w.slug || w.name || ""));
  const gapUpdates = [];
  for (let i = 1; i < flow.length; i++) {
    const prev = flow[i - 1];
    const cur = flow[i];
    if (cur.top == null || prev.top == null || prev.h == null) continue;
    const gap = Math.max(0, cur.top - (prev.top + prev.h));
    if (gap <= 8) continue;
    gapUpdates.push({
      nodeIds: [cur.nodeId],
      styles: { paddingTop: `${gap}px`, height: "fit-content" },
    });
  }
  if (gapUpdates.length) {
    try {
      await call("update_styles", { updates: gapUpdates });
      log(`applied ${gapUpdates.length} source gap(s) from capture tops`);
    } catch (err) {
      log(`could not apply source gaps: ${err.message.split("\n")[0]}`);
    }
  }
}

await call("finish_working_on_nodes", {});

const summary = {
  file: info.fileName,
  page: info.pageName,
  containerId,
  refArtboardId,
  sourceScreenshot: shotPath,
  sourceTarget: explicitSourceTarget || null,
  screenshotsOnly,
  written: written.length,
  failed,
  names: written.map((w) => w.name),
};
writeFileSync(join(dirname(manifestPath), "import-result.json"), JSON.stringify(summary, null, 2));
console.log(JSON.stringify(summary, null, 1));
