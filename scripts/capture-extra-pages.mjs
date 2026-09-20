#!/usr/bin/env node
// 4.2 — capture each extra sitemap URL onto the HOME canvas (the 1.2 page),
// in one horizontal row under a single `Ruler · pages` below the existing
// frames. Same file as 1.2. Never create_file. NEVER create_page — one Paper
// page total, not a page per URL. Desktop only. Serial writes.

import fs from "node:fs";
import path from "node:path";
import { collectInteriorPageToPaper } from "./run-paper-phase.mjs";
import { importSibling } from "./skill-paths.mjs";

const arg = (name, fallback) => {
  const i = process.argv.indexOf(`--${name}`);
  return i > -1 ? process.argv[i + 1] : fallback;
};

const PROJECT = path.resolve(arg("project", process.cwd()));
const CAPTURE = path.resolve(arg("capture", path.join(PROJECT, "capture")));
const FORCE = process.argv.includes("--force");

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

const paperPath = path.join(PROJECT, "qa", "paper-file.json");
const sitemapPath = path.join(PROJECT, "qa", "phase-4-sitemap.json");
if (!fs.existsSync(paperPath)) {
  console.error("need qa/paper-file.json from 1.2");
  process.exit(2);
}
if (!fs.existsSync(sitemapPath)) {
  console.error("need qa/phase-4-sitemap.json from 4.1");
  process.exit(2);
}

const paper = readJson(paperPath);
const sitemap = readJson(sitemapPath);
const fileId = paper.fileId;
if (!fileId) {
  console.error("qa/paper-file.json is missing fileId — never list_files / create_file here");
  process.exit(2);
}

const { call, setFileId } = await importSibling("url-to-paper", "scripts/mcp-client.mjs");
const { mcpPayload } = await importSibling("url-to-paper", "scripts/write-paper-section.mjs");
const {
  COLUMN_GAP,
  PARK_BUFFER,
  RULER_COLOR,
  RULER_THICK,
  RULER_WIDTH,
  contentOrigin,
  mcpPayload: rulerPayload,
} = await importSibling("url-to-paper", "scripts/rulers.mjs");
setFileId(fileId);
await call("open_file", { fileId });

const PAGES_RULER = "Ruler · pages";
const RULER_DROP = 400; // gap between the lowest home frame and the new ruler

const pages = [];
for (const row of sitemap.pages || []) {
  const collected = await collectInteriorPageToPaper({
    url: row.url,
    fileId,
    captureRoot: CAPTURE,
    pageSlug: row.slug,
    force: FORCE,
    log: (...a) => console.error(...a),
  });
  pages.push({
    url: row.url,
    path: row.path,
    slug: row.slug,
    paperName: row.paperName,
    template: row.template || null,
    artboardId: collected.lander?.id || null,
    artboard: `${row.slug}-desktop`,
  });
}

// Arrange: one `Ruler · pages` below every existing frame, interior landers
// in a single horizontal row under it. Never touch the home row above.
const info = mcpPayload(await call("get_basic_info", { fileId }));
const boards = info.artboards || [];
const interiorNames = new Set(pages.map((p) => p.artboard));
const homeBoards = boards.filter(
  (b) => !interiorNames.has(b.name) && b.name !== PAGES_RULER,
);
const bottom = homeBoards.reduce(
  (max, b) => Math.max(max, (b.worldY || 0) + (b.height || 0)),
  0,
);
const origin = contentOrigin(homeBoards);
const rulerTop = bottom + RULER_DROP;

let ruler = boards.find((b) => b.name === PAGES_RULER) || null;
if (!ruler) {
  const made = (rulerPayload || mcpPayload)(await call("create_artboard", {
    fileId,
    name: PAGES_RULER,
    styles: {
      width: `${RULER_WIDTH}px`,
      height: `${RULER_THICK}px`,
      backgroundColor: RULER_COLOR,
      padding: "0px",
      display: "flex",
    },
  }));
  const rulerId = made.id || made.nodeId || made.createdNodes?.[0]?.id;
  if (!rulerId) throw new Error(`create_artboard returned no id for ${PAGES_RULER}`);
  ruler = { id: rulerId, name: PAGES_RULER };
}
const updates = [{
  nodeIds: [ruler.id],
  styles: {
    left: `${origin.left || 0}px`,
    top: `${rulerTop}px`,
    width: `${RULER_WIDTH}px`,
    height: `${RULER_THICK}px`,
    backgroundColor: RULER_COLOR,
  },
}];
let x = origin.left || 0;
const rowY = rulerTop + RULER_THICK + PARK_BUFFER;
for (const page of pages) {
  const board = boards.find((b) => b.name === page.artboard);
  if (!board) continue;
  updates.push({
    nodeIds: [board.id],
    styles: { left: `${x}px`, top: `${rowY}px` },
  });
  x += (board.width || 1600) + COLUMN_GAP;
}
await call("update_styles", { fileId, updates });
console.error(`· parked ${pages.length} interior lander(s) under ${PAGES_RULER} at y=${rowY}`);

const receipt = {
  ok: true,
  fileId,
  serial: true,
  createdFile: false,
  createdPages: false,
  pagesRuler: { name: PAGES_RULER, id: ruler.id, top: rulerTop },
  pages,
};
const out = path.join(PROJECT, "qa", "phase-4-pages.json");
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, `${JSON.stringify(receipt, null, 2)}\n`);
console.log(JSON.stringify({ ok: true, pages: pages.length, out }, null, 2));
