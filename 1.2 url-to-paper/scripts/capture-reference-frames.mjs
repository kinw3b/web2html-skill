#!/usr/bin/env node
// Snapshot the canonical Web2HTML Paper reference frames to local HTML.
// Runtime capture/library steps consume local templates; this command is only
// for intentionally refreshing the checked-in visual reference.

import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { call, setFileId } from "./mcp-client.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const PACKAGE_ROOT = resolve(HERE, "..");
const REPO_ROOT = resolve(PACKAGE_ROOT, "..");
const TMP_ROOT = join(PACKAGE_ROOT, ".reference-export");
const CONVERTER = join(REPO_ROOT, "1.0 - web2html", "scripts", "jsx_to_static_html.py");
const FILE_ID = "01M04TZDSPQDTXS5YCRKQD66WQ";

const FRAMES = [
  {
    nodeId: "BY-0",
    slug: "button-states",
    output: join(REPO_ROOT, "1.3 hover-reel", "templates", "capture-tool", "reference", "button-states.html"),
  },
  {
    nodeId: "16T-0",
    slug: "components",
    output: join(REPO_ROOT, "1.3 hover-reel", "templates", "capture-tool", "reference", "components.html"),
  },
  {
    nodeId: "CV-0",
    slug: "navigation",
    output: join(REPO_ROOT, "1.3 hover-reel", "templates", "capture-tool", "reference", "navigation.html"),
  },
  {
    nodeId: "SD-0",
    slug: "design-library",
    output: join(PACKAGE_ROOT, "templates", "library", "reference", "design-library.html"),
  },
];

function payload(result) {
  for (const item of result?.content || []) {
    if (item.type !== "text") continue;
    try { return JSON.parse(item.text); } catch { /* continue */ }
  }
  return {};
}

setFileId(FILE_ID);
mkdirSync(TMP_ROOT, { recursive: true });

for (const frame of FRAMES) {
  const exported = payload(await call("get_jsx", {
    fileId: FILE_ID,
    nodeId: frame.nodeId,
    format: "inline-styles",
  }));
  if (!exported.jsx) throw new Error(`No JSX returned for ${frame.slug}`);

  const jsonPath = join(TMP_ROOT, `${frame.slug}.json`);
  mkdirSync(dirname(frame.output), { recursive: true });
  writeFileSync(jsonPath, `${JSON.stringify({ jsx: exported.jsx }, null, 2)}\n`, "utf8");

  const converted = spawnSync("python3", [CONVERTER, jsonPath, "--check", "-o", frame.output], {
    cwd: REPO_ROOT,
    encoding: "utf8",
  });
  if (converted.status !== 0) {
    throw new Error(`HTML conversion failed for ${frame.slug}: ${converted.stderr || converted.stdout}`);
  }
  console.error(`captured ${frame.slug} -> ${frame.output}`);
}

rmSync(TMP_ROOT, { recursive: true, force: true });
console.log(JSON.stringify({ fileId: FILE_ID, frames: FRAMES.map(({ slug, output }) => ({ slug, output })) }, null, 2));
