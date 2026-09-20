#!/usr/bin/env node
// Seed `Screenshots` from capture/<page>-desktop/source-sections/.
//
// Reads per-section PNGs + sidecars and write_html's a vertical stack:
// red section-number + outlined shot. Parks first under Ruler · desktop. Never on the
// lander. Desktop 1600 only. Artboard opacity 50% so it recedes next to home-desktop.
// Never a full-page screenshot. Never a Hover States column.
//
// Default is disk → HTML. Paper MCP runs only with --file-id / PAPER_FILE_ID.
//
//   node seed-source-board.mjs --dir capture/home-desktop/source-sections \
//     --page home --html-out /tmp/source-home.html
//   PAPER_FILE_ID=$PAPER_FILE_ID node seed-source-board.mjs \
//     --dir capture/home-desktop/source-sections --page home

import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import {
  SOURCE_BOARD_PAD,
  SOURCE_SHOT_MAX_WIDTH,
  buildSourceBoardHtml,
  buildSourceRowHtml,
  hasSourceSectionShots,
  readSourceSectionsDir,
  isSourceBoardName,
  sourceBoardFrameStyles,
  sourceBoardName,
} from "./source-sections.mjs";
import { reviewSequenceSections, writeReviewSequence } from "./review-sequence.mjs";
import { contentOrigin, ensureRulers, mcpPayload, parkNextInRow } from "./rulers.mjs";

export async function seedSourceBoard({
  dir,
  page = "home",
  htmlOut,
  fileId,
  call,
  log = () => {},
} = {}) {
  const abs = resolve(dir);
  if (!hasSourceSectionShots(abs)) {
    throw new Error(`${abs} has no NN-*.png source shots`);
  }
  const captured = readSourceSectionsDir(abs);
  const sections = reviewSequenceSections(captured);
  writeReviewSequence(dirname(abs), captured, { page });
  const html = buildSourceBoardHtml(sections, { page });
  const name = sourceBoardName(page);
  if (htmlOut) {
    mkdirSync(dirname(resolve(htmlOut)), { recursive: true });
    writeFileSync(resolve(htmlOut), html);
    log(`html → ${htmlOut}`);
  }
  if (!fileId || !call) {
    return { html, name, written: false, sections: sections.length };
  }

  const info = mcpPayload(await call("get_basic_info", fileId ? { fileId } : {}));
  await ensureRulers({
    call,
    fileId,
    boards: info.artboards || [],
    init: true,
    log,
  });
  const ruled = mcpPayload(await call("get_basic_info", fileId ? { fileId } : {}));
  const boards = ruled.artboards || [];
  const existing = boards.find((b) => b.name === name)
    || boards.find((b) => isSourceBoardName(b.name));
  const replace = true; // never leave a badge-only blank board in place
  if (existing && !replace) {
    log(`${name} already exists — skip create`);
    return { html, name, written: false, skipped: true, id: existing.id, sections: sections.length };
  }

  const badge = 80 + 16;
  // Rows are capped at the desktop frame width, so the board is too — a wide
  // bbox must not pull the stack past `home-desktop`.
  let stackW = SOURCE_SHOT_MAX_WIDTH;
  for (const section of sections) {
    const w = Math.min(section.bbox?.w || SOURCE_SHOT_MAX_WIDTH, SOURCE_SHOT_MAX_WIDTH);
    stackW = Math.max(stackW, badge + w);
  }
  stackW += SOURCE_BOARD_PAD * 2;
  const park = parkNextInRow({
    boards: boards.filter((b) => b.id !== existing?.id),
    name,
    pageName: "home-desktop",
    newWidth: stackW,
  });
  const origin = contentOrigin(boards);
  const left = existing
    ? Math.round(existing.worldX ?? existing.left ?? park.left)
    : park.left;
  const top = existing
    ? Math.round(existing.worldY ?? existing.top ?? park.top)
    : Math.max(park.top, origin.top);
  const styles = sourceBoardFrameStyles({ stackW, left, top });
  let id = existing?.id;
  if (!id) {
    const made = mcpPayload(await call("create_artboard", {
      ...(fileId ? { fileId } : {}),
      name,
      styles,
    }));
    id = made.id || made.nodeId || made.createdNodes?.[0]?.id;
    if (!id) throw new Error(`create_artboard returned no id for ${name}`);
    await call("update_styles", {
      ...(fileId ? { fileId } : {}),
      updates: [{ nodeIds: [id], styles: { left: `${left}px`, top: `${top}px` } }],
    });
  } else {
    const kids = mcpPayload(await call("get_children", {
      ...(fileId ? { fileId } : {}),
      nodeId: id,
    })).children || [];
    const ids = kids.map((k) => k.id).filter(Boolean);
    if (ids.length) {
      await call("delete_nodes", { ...(fileId ? { fileId } : {}), nodeIds: ids });
      log(`${name}  cleared ${ids.length} blank/old row(s)`);
    }
    await call("update_styles", {
      ...(fileId ? { fileId } : {}),
      updates: [{ nodeIds: [id], styles }],
    });
  }
  // One row per write_html so a 1.3MB hero cannot blank the stack. No title
  // row — the artboard name already reads Screenshots.
  for (const section of sections) {
    const row = buildSourceRowHtml(section);
    await call("write_html", {
      ...(fileId ? { fileId } : {}),
      html: row,
      targetNodeId: id,
      mode: "insert-children",
    });
    log(`  row ${section.paperName || section.id}`);
  }
  log(`${name}  ${sections.length} section(s) @ ${left},${top}`);
  const painted = await verifySourceFills({ call, fileId, boardId: id, log });
  return { html, name, written: true, replaced: !!existing, id, left, top, sections: sections.length, painted };
}


async function verifySourceFills({ call, fileId, boardId, log }) {
  const kids = mcpPayload(await call("get_children", {
    ...(fileId ? { fileId } : {}),
    nodeId: boardId,
  })).children || [];
  const painted = [];
  for (const row of kids) {
    if (!/^\d{2} · /.test(row.name || "")) continue;
    const inner = mcpPayload(await call("get_children", {
      ...(fileId ? { fileId } : {}),
      nodeId: row.id,
    })).children || [];
    const file = inner.find((g) => g.component === "Rectangle" || /image|file|img/i.test(`${g.component || ""} ${g.name || ""}`))
      || inner.find((g) => !/badge|divider|hover/i.test(g.name || ""));
    if (!file?.id) {
      throw new Error(`${row.name || row.id} has no image child after seed`);
    }
    const fill = mcpPayload(await call("get_fill_image", {
      ...(fileId ? { fileId } : {}),
      nodeId: file.id,
    }));
    const url = fill.originalUrl || fill.url || "";
    if (!/^https:\/\//.test(url) && !/^https:\/\//.test(fill.mimeType || "")) {
      if (!fill.mimeType && !url) {
        throw new Error(`${row.name} image is still empty after seed (no fill)`);
      }
    }
    if (url.startsWith("paper-asset:") || url.startsWith("file:")) {
      throw new Error(`${row.name} still has ${url}`);
    }
    painted.push({ name: row.name, url: url || fill.mimeType });
    log(`  fill ${row.name}  ${url || fill.mimeType}`);
  }
  if (!painted.length) throw new Error("Source board has no painted rows after seed");
  return painted;
}

const isCli = process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1]);
if (isCli) {
  const argv = process.argv.slice(2);
  const arg = (name, fallback) => {
    const i = argv.indexOf(`--${name}`);
    return i >= 0 && argv[i + 1] ? argv[i + 1] : fallback;
  };
  const dir = arg("dir", "capture/home-desktop/source-sections");
  const page = arg("page", "home");
  const htmlOut = arg("html-out");
  const fileId = arg("file-id") || process.env.PAPER_FILE_ID || "";
  const log = (...a) => console.error("·", ...a);

  if (!htmlOut && !fileId) {
    log("no --html-out and no --file-id / PAPER_FILE_ID — nothing to write.");
    log("Pass --html-out for a local stack, or a file id to seed Paper.");
    process.exit(0);
  }

  let call;
  if (fileId) {
    const mcp = await import("./mcp-client.mjs");
    if (arg("file-id")) mcp.setFileId(arg("file-id"));
    const { ensurePaper } = await import("./ensure-paper.mjs");
    await ensurePaper({ launch: !argv.includes("--no-launch"), log });
    await mcp.call("open_file", { fileId });
    call = mcp.call;
  }

  const result = await seedSourceBoard({
    dir,
    page,
    htmlOut,
    fileId: fileId || undefined,
    call,
    log,
  });
  if (fileId && result.written) {
    await call("finish_working_on_nodes", { fileId });
  }
  console.log(JSON.stringify({
    name: result.name,
    written: result.written,
    skipped: !!result.skipped,
    htmlOut: htmlOut || null,
    sections: result.sections,
    id: result.id || null,
  }, null, 2));
}
