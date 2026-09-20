// One section → Paper. Shared by the Capture Tool walk and assemble-lander.
// Never put paper-asset:// in write_html. Hug height: min-content after insert.

import { localizeHtml } from "./localize-html-images.mjs";
import { flattenDecorativeAbs } from "./flatten-decorative-abs.mjs";
import { trimPaperStyles } from "./trim-paper-styles.mjs";
import { reorderOverlayPaintOrder } from "./overlay-paint-order.mjs";
import { bindInlinePaperFonts } from "./library-tokens.mjs";
import { isDesktopCapture, paperSectionName, SECTION_ID_LEGEND } from "./section-ids.mjs";
import { canvasSlot, contentOrigin, landerRowArtboards } from "./rulers.mjs";

export function mcpPayload(result) {
  for (const item of result.content ?? []) {
    if (item.type === "text") {
      try { return JSON.parse(item.text); } catch { return { text: item.text }; }
    }
  }
  return {};
}

export async function prepareSectionHtml(html, { projectRoot } = {}) {
  let next = String(html || "");
  if (projectRoot) {
    const localized = await localizeHtml(next, { projectRoot });
    next = localized.html;
  }
  const flat = flattenDecorativeAbs(next);
  next = trimPaperStyles(flat.html);
  const stacked = reorderOverlayPaintOrder(next);
  next = bindInlinePaperFonts(stacked.html);
  return { html: next, flattened: flat.removed?.length || 0, restacked: stacked.moved?.length || 0 };
}

export async function writePaperSection({
  call,
  targetId,
  name,
  html,
  projectRoot,
  log = () => {},
} = {}) {
  if (!call || !targetId) throw new Error("writePaperSection needs call() and targetId");
  const prepared = await prepareSectionHtml(html, { projectRoot });
  const res = mcpPayload(await call("write_html", {
    html: prepared.html,
    targetNodeId: targetId,
    mode: "insert-children",
  }));
  const nodeId = res.createdNodes?.[0]?.id || null;
  if (nodeId) {
    await call("rename_nodes", { updates: [{ nodeId, name }] });
    try {
      await call("update_styles", {
        updates: [{ nodeIds: [nodeId], styles: { height: "min-content" } }],
      });
    } catch (error) {
      log(`  ! ${name}: could not hug height (${String(error.message || error).split("\n")[0]})`);
    }
  }
  log(`  ✓ ${name}${nodeId ? ` → ${nodeId}` : ""}`);
  return { nodeId, name, bytes: prepared.html.length };
}

export async function findArtboard(call, name) {
  const info = mcpPayload(await call("get_basic_info", {}));
  const board = (info.artboards || []).find((a) => a.name === name) || null;
  return { info, board };
}

export async function ensureLanderArtboard({
  call,
  fileId,
  name = "home-desktop",
  width = 1600,
  log = () => {},
} = {}) {
  const found = await findArtboard(call, name);
  if (found.board) {
    log(`artboard ${name} exists`);
    return { id: found.board.id, name, created: false };
  }
  const origin = contentOrigin(found.info.artboards || []);
  const desktop = isDesktopCapture({ width, name });
  const content = landerRowArtboards(found.info.artboards || [])
    .filter((a) => a.name !== SECTION_ID_LEGEND && canvasSlot(a.name) < canvasSlot(name));
  const rightEdge = content.reduce(
    (max, a) => Math.max(max, (a.worldX || 0) + (a.width || 0)),
    origin.left,
  );
  const x = content.length ? Math.round(rightEdge + 80) : origin.left;
  const y = origin.top;
  const made = mcpPayload(await call("create_artboard", {
    fileId,
    name,
    styles: {
      width: `${width}px`,
      height: "2000px",
      display: "flex",
      flexDirection: "column",
      backgroundColor: "#ffffff",
    },
  }));
  const id = made.createdNodes?.[0]?.id || made.id || made.nodeId;
  if (!id) throw new Error(`create_artboard returned no id for ${name}`);
  await call("update_styles", {
    updates: [{ nodeIds: [id], styles: { left: `${x}px`, top: `${y}px` } }],
  });
  log(`artboard ${name} created (${width}px, desktop=${desktop})`);
  return { id, name, created: true, x, y };
}

export async function hugArtboard(call, id) {
  if (!id) return;
  try {
    await call("update_styles", {
      updates: [{ nodeIds: [id], styles: { height: "fit-content" } }],
    });
  } catch { /* Paper may already be fit-content */ }
}

export { paperSectionName, isDesktopCapture };
