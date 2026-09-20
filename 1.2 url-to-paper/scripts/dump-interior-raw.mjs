#!/usr/bin/env node
// 5.2 — serial get_jsx dumps of Phase 4 Paper pages → rebuild/{slug}-raw.html (structure reference for the .astro bodies).
// Never create_file / list_files. Controller owns Paper. One page at a time.

import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { call as defaultCall, setFileId } from "./mcp-client.mjs";

export const FORBIDDEN_TOOLS = ["create_file", "list_files"];

const here = dirname(fileURLToPath(import.meta.url));
const CONVERTER_CANDIDATES = [
  resolve(here, "../../1.0 - web2html/scripts/jsx_to_static_html.py"),
  resolve(here, "../../web2html/scripts/jsx_to_static_html.py"),
];
const CONVERTER = CONVERTER_CANDIDATES.find((p) => existsSync(p)) || CONVERTER_CANDIDATES[0];

const arg = (name, fallback) => {
  const i = process.argv.indexOf(`--${name}`);
  return i > -1 ? process.argv[i + 1] : fallback;
};

function readJson(file) {
  return JSON.parse(readFileSync(file, "utf8"));
}

function jsxPayload(result) {
  for (const item of result?.content || []) {
    if (item.type !== "text") continue;
    try {
      return JSON.parse(item.text);
    } catch {
      /* continue */
    }
  }
  return result && typeof result === "object" ? result : {};
}

export function assertSafeTool(name) {
  if (FORBIDDEN_TOOLS.includes(name)) {
    throw new Error(`5.1 refuses ${name} — same Paper file as 1.2 only`);
  }
}

export async function dumpInteriorPages({
  project,
  pages,
  fileId,
  call = defaultCall,
} = {}) {
  if (!fileId) throw new Error("qa/paper-file.json is missing fileId");
  if (!Array.isArray(pages) || !pages.length) throw new Error("no Phase 4 pages to dump");
  setFileId(fileId);
  const results = [];
  for (const row of pages) {
    const slug = row.slug;
    if (!slug || slug === "home") throw new Error("5.1 refuses the homepage slug");
    const pageId = row.pageId;
    const artboard = row.artboard || `${slug}-desktop`;
    const nodeId = row.artboardId || row.nodeId;
    await call("open_file", { fileId, pageId });
    const params = { fileId, format: "inline-styles" };
    if (nodeId) params.nodeId = nodeId;
    else params.nodeName = artboard;
    const exported = jsxPayload(await call("get_jsx", params));
    const jsx = exported.jsx || exported.html || "";
    if (!jsx) throw new Error(`get_jsx returned no markup for ${slug}`);
    const qaDir = resolve(project, "qa");
    mkdirSync(qaDir, { recursive: true });
    const jsonPath = resolve(qaDir, `${slug}-raw.jsx.json`);
    writeFileSync(jsonPath, `${JSON.stringify({ jsx }, null, 2)}\n`);
    const dest = resolve(project, "rebuild", `${slug}-raw.html`);
    mkdirSync(dirname(dest), { recursive: true });
    const converted = spawnSync("python3", [CONVERTER, jsonPath, "-o", dest], {
      encoding: "utf8",
    });
    if (converted.status !== 0) {
      throw new Error(`HTML conversion failed for ${slug}: ${converted.stderr || converted.stdout}`);
    }
    results.push({
      slug,
      pageId,
      artboard,
      raw: `rebuild/${slug}-raw.html`,
      serial: true,
    });
  }
  return results;
}

async function main() {
  const PROJECT = resolve(arg("project", process.cwd()));
  const paperPath = resolve(PROJECT, "qa/paper-file.json");
  const pagesPath = resolve(PROJECT, "qa/phase-4-pages.json");
  if (!existsSync(paperPath)) {
    console.error("need qa/paper-file.json from 1.2");
    process.exit(2);
  }
  if (!existsSync(pagesPath)) {
    console.error("need qa/phase-4-pages.json from 4.2");
    process.exit(2);
  }
  const paper = readJson(paperPath);
  const receipt = readJson(pagesPath);
  const fileId = paper.fileId || receipt.fileId;
  const pages = receipt.pages || [];
  const dumped = await dumpInteriorPages({
    project: PROJECT,
    pages,
    fileId,
    call: async (name, params) => {
      assertSafeTool(name);
      return defaultCall(name, params);
    },
  });
  const out = resolve(PROJECT, "qa/phase-5-raw.json");
  mkdirSync(dirname(out), { recursive: true });
  writeFileSync(out, `${JSON.stringify({
    ok: true,
    serial: true,
    createdFile: false,
    fileId,
    pages: dumped,
  }, null, 2)}\n`);
  console.log(JSON.stringify({ ok: true, pages: dumped.length, out }, null, 2));
}

const invoked = process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (invoked) {
  main().catch((err) => {
    console.error(err.message || err);
    process.exit(2);
  });
}
