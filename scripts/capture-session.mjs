#!/usr/bin/env node
// Step 1.2 runner — headless only.
//
// Always create_file a brand-new Paper document. Never list_files / never
// open a similarly-named existing file. Omit --file and PAPER_FILE_ID.
//
// Collect the real 1600 / 768 / 390 DOM onto Paper, clip source shots, write
// the Paper Screenshots board from the 1600 clips, park Navigation at every
// width, run the desktop geometry postflight, and write the Paper receipt.
// 1.2 never authors breakpoint frames from desktop.
//
// This script never opens a visible browser window and never mounts an in-page
// HUD. Navbar, dropdown, hover, component and tag capture all belong to the
// Chrome Capture Tool extension in `capture-extension/`, which is optional 1.4.

import fs from "node:fs";
import path from "node:path";
import { importSibling } from "./skill-paths.mjs";

const arg = (name, fallback) => {
  const i = process.argv.indexOf(`--${name}`);
  return i > -1 ? process.argv[i + 1] : fallback;
};

const URL_ = arg("url");
const PAGE = arg("page", "home");
const CAPTURE = path.resolve(arg("capture", "capture"));
const OUT = path.resolve(arg("out", "source-site/components"));
const ENDPOINT = arg("paper-endpoint", process.env.PAPER_MCP_ENDPOINT || "");
const FORCE = process.argv.includes("--force");
const DESKTOP_ONLY = process.argv.includes("--desktop-only");
const PASSED_FILE = arg("file", "");

if (!URL_) {
  console.error("need --url");
  process.exit(1);
}
if (PASSED_FILE) {
  console.error(
    "1.2 always creates a new Paper file. Omit --file — do not list_files / open a similarly-named existing document (Pitfall #187).",
  );
  process.exit(2);
}
if (process.env.PAPER_FILE_ID) {
  console.error("ignoring PAPER_FILE_ID — 1.2 creates a new Paper file (Pitfall #187)");
}

const pageSlug = String(PAGE || "home").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "home";
const projectRoot = path.dirname(CAPTURE);
fs.mkdirSync(OUT, { recursive: true });

const { createPaperFile, restampLiveBoard } = await importSibling("url-to-paper", "scripts/create-paper-file.mjs");
const paperFile = await createPaperFile({
  projectRoot,
  url: URL_,
  log: (...a) => console.error(...a),
});
const FILE = paperFile.fileId;

const { collectHomepageToPaper } = await import("./run-paper-phase.mjs");
const collected = await collectHomepageToPaper({
  url: URL_,
  fileId: FILE,
  captureRoot: CAPTURE,
  pageSlug,
  force: FORCE,
  desktopOnly: DESKTOP_ONLY,
  log: (...a) => console.error(...a),
});

const activeRoot = collected?.projectRoot || projectRoot;

console.error("Running automatic geometry postflight…");
const { runGeometryPostflight } = await importSibling(
  "url-to-paper",
  "scripts/run-geometry-postflight.mjs",
);
const postflight = await runGeometryPostflight({
  projectRoot: activeRoot,
  fileId: FILE,
  artboard: `${pageSlug}-desktop`,
  log: (...a) => console.error(...a),
});
if (!postflight.ok) {
  console.error(`Geometry postflight failed: ${postflight.reason}. Fix Paper, then rerun 1.2.`);
  process.exit(2);
}

// 1.3 handoff — the Capture Tool extension prefills from this file (and from
// `active-session.json`, which pipeline-progress.py writes).
const qaDir = path.join(activeRoot, "qa");
fs.mkdirSync(qaDir, { recursive: true });
const receipt = {
  ...paperFile,
  fileId: FILE,
  url: URL_,
  page: pageSlug,
  updatedAt: new Date().toISOString(),
};
if (ENDPOINT) receipt.paperEndpoint = ENDPOINT;
fs.writeFileSync(path.join(qaDir, "paper-file.json"), `${JSON.stringify(receipt, null, 2)}\n`);
restampLiveBoard(activeRoot, (...a) => console.error(...a));

console.error("1.2 collect done: home-desktop + home-768 + home-390 + Navigation takes + Screenshots board.");
console.error("Run the single 1.3 Design Library mine next; no breakpoint authoring or retry loop is required.");
console.log(JSON.stringify({
  step: "1.2",
  mode: "collect",
  output: OUT,
  capture: CAPTURE,
  projectRoot: activeRoot,
  sections: (collected?.walk || []).map((s) => s.paperName || s.slug || s.id),
  gates: collected?.gates || {},
  postflight: true,
  capturedViewports: [1600, 768, 390],
  screenshotsBoard: "Screenshots",
  next: "1.3-design-library",
}, null, 2));
