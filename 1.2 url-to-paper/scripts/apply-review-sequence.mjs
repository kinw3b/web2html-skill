#!/usr/bin/env node
// After source-section shots exist, number Paper 01, 02, 03… for the
// review sequence. Chrome-only layers stay unnumbered (nav stays
// `01 · nav` beside `01 · hero-section`). Writes review-sequence.json.
// Hover reads that file.
//
//   PAPER_FILE_ID=$PAPER_FILE_ID node apply-review-sequence.mjs \
//     --dir capture/home-desktop/source-sections --page home

import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { readSourceSectionsDir } from "./source-sections.mjs";
import {
  matchReviewRow,
  parsePaperSectionName,
  reviewSequenceSections,
  writeReviewSequence,
} from "./review-sequence.mjs";
import { call, setFileId } from "./mcp-client.mjs";

const arg = (n, d) => {
  const i = process.argv.indexOf(`--${n}`);
  return i > -1 ? process.argv[i + 1] : d;
};

const payload = (raw) => {
  const text = raw?.content?.[0]?.text;
  if (typeof text === "string") {
    try { return JSON.parse(text); } catch { /* fall through */ }
  }
  return raw;
};

export function overlayRename(layerName, sequence) {
  const parsed = parsePaperSectionName(layerName);
  if (!parsed.id) return null;
  if (matchReviewRow(layerName, sequence)) return null;
  if (parsed.slug.toLowerCase() === "nav" || /^(nav|header)$/i.test(parsed.slug)) {
    return parsed.id === "01" ? null : `01 · ${parsed.slug}`;
  }
  return parsed.slug;
}

export function sortRenamePlan(plan = []) {
  const overlays = plan.filter((p) => p.kind === "overlay");
  const review = plan.filter((p) => p.kind === "review")
    .sort((a, b) => Number(b.fromId || 0) - Number(a.fromId || 0));
  return [...overlays, ...review];
}

export async function runReviewSequence({
  dir,
  page = "home",
  fileId,
  call: mcpCall,
  log = console.error,
} = {}) {
  const abs = resolve(dir);
  const captured = readSourceSectionsDir(abs);
  const sequence = reviewSequenceSections(captured);
  if (!sequence.length) throw new Error(`${abs} has no review sections`);
  const written = writeReviewSequence(dirname(abs), captured, { page });
  log(`review sequence ${sequence.map((s) => s.paperName).join(" → ")}`);
  log(`wrote ${written.file}`);
  if (!fileId || !mcpCall) return { sequence, file: written.file, paper: false };

  const info = payload(await mcpCall("get_basic_info", { fileId }));
  const boards = info.artboards || [];
  const source = boards.find((b) => b.name === `Screenshots` || b.name === `Screenshots · ${page}` || b.name === `Source · ${page}`);
  const desktop = boards.find((b) => b.name === `${page}-desktop` || b.name === "home-desktop");
  const plan = [];
  const texts = [];

  const walkBoard = async (board, { dropOverlay = false } = {}) => {
    if (!board?.id) return;
    const kids = payload(await mcpCall("get_children", { fileId, nodeId: board.id })).children || [];
    for (const kid of kids) {
      const parsed = parsePaperSectionName(kid.name);
      const overlay = dropOverlay ? overlayRename(kid.name, sequence) : null;
      const row = matchReviewRow(kid.name, sequence);
      if (overlay && overlay !== kid.name) {
        plan.push({
          kind: "overlay", nodeId: kid.id, name: overlay, fromId: parsed.id,
        });
      } else if (row && row.paperName !== kid.name) {
        plan.push({
          kind: "review", nodeId: kid.id, name: row.paperName, fromId: parsed.id,
        });
      }
      if (!row) continue;
      const inner = payload(await mcpCall("get_children", { fileId, nodeId: kid.id })).children || [];
      const hover = inner.find((c) => c.name === "Hover States");
      const number = inner.find((c) => c.name === "section-number")
        || (hover
          ? (payload(await mcpCall("get_children", { fileId, nodeId: hover.id })).children || [])
            .find((c) => c.name === "section-number")
          : null);
      if (!number) continue;
      const labelKids = payload(await mcpCall("get_children", { fileId, nodeId: number.id })).children || [];
      const text = labelKids.find((c) => c.component === "Text" || /^\d{2}$/.test(c.name || ""));
      if (text?.id) {
        texts.push({ nodeId: text.id, textContent: row.id });
        if (text.name !== row.id) {
          plan.push({ kind: "review", nodeId: text.id, name: row.id, fromId: text.name });
        }
      }
    }
  };

  await walkBoard(source);
  await walkBoard(desktop, { dropOverlay: true });
  const renames = sortRenamePlan(plan).map(({ nodeId, name }) => ({ nodeId, name }));

  if (renames.length) {
    await mcpCall("rename_nodes", { fileId, updates: renames });
    log(`renamed ${renames.length} layer(s)`);
  }
  if (texts.length) {
    await mcpCall("set_text_content", { fileId, updates: texts });
    log(`stamped ${texts.length} section-number(s)`);
  }
  return { sequence, file: written.file, paper: true, renamed: renames.length, stamped: texts.length };
}

const here = fileURLToPath(import.meta.url);
if (process.argv[1] && resolve(process.argv[1]) === here) {
  const DIR = arg("dir", "capture/home-desktop/source-sections");
  const PAGE = arg("page", "home");
  const FILE = arg("file", process.env.PAPER_FILE_ID || "");
  if (FILE) setFileId(FILE);
  const out = await runReviewSequence({
    dir: DIR,
    page: PAGE,
    fileId: FILE,
    call: FILE ? call : null,
  });
  console.log(JSON.stringify({
    file: out.file,
    paper: out.paper,
    sections: out.sequence.map((s) => s.paperName),
  }));
}
