#!/usr/bin/env node
// 4.3 — serial token bind onto Phase 4 Paper pages.
// Never create_tokens. Never a second Design Library. One writer.

import { spawn } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { call, setFileId } from "./mcp-client.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const arg = (name, fallback) => {
  const i = process.argv.indexOf(`--${name}`);
  return i > -1 ? process.argv[i + 1] : fallback;
};

const PROJECT = resolve(arg("project", process.cwd()));
const pagesPath = resolve(PROJECT, arg("pages", "qa/phase-4-pages.json"));
const libraryPath = resolve(PROJECT, arg("library", "design-library/library.json"));
const apply = resolve(here, "apply-theme-tokens.mjs");

function readJson(file) {
  return JSON.parse(readFileSync(file, "utf8"));
}

function spawnNode(script, args) {
  return new Promise((resolvePromise) => {
    const child = spawn(process.execPath, [script, ...args], {
      cwd: PROJECT,
      stdio: ["ignore", "pipe", "inherit"],
    });
    let out = "";
    child.stdout.on("data", (d) => { out += d; });
    child.on("close", (code) => resolvePromise({ code: code ?? 1, out }));
  });
}

if (!existsSync(pagesPath)) {
  console.error("need qa/phase-4-pages.json from 4.2");
  process.exit(2);
}
if (!existsSync(libraryPath)) {
  console.error("need design-library/library.json — 4.3 binds existing tokens only");
  process.exit(2);
}

const library = readJson(libraryPath);
const tokens = library.tokens || {};
const hasTokens = Boolean(
  (tokens.color && Object.keys(tokens.color).length)
  || (tokens.font && Object.keys(tokens.font).length)
  || (Array.isArray(library.tokens) && library.tokens.length),
);
if (!hasTokens && !library.css) {
  console.error("FAIL: library tokens are empty — refuse to seed interior pages");
  process.exit(2);
}

const receipt = readJson(pagesPath);
const fileId = receipt.fileId;
if (!fileId) {
  console.error("qa/phase-4-pages.json is missing fileId");
  process.exit(2);
}
setFileId(fileId);

const results = [];
for (const row of receipt.pages || []) {
  await call("open_file", { fileId, pageId: row.pageId });
  const only = row.artboard || `${row.slug}-desktop`;
  const applied = await spawnNode(apply, [
    "--file-id", fileId,
    "--project", PROJECT,
    "--library", libraryPath,
    "--only", only,
    "--exact-only",
    "--json", `qa/phase-4-token-pass-${row.slug}.json`,
    "--qa", `qa/phase-4-token-pass-${row.slug}-qa.json`,
  ]);
  if (applied.code !== 0) {
    console.error(`token seed failed for ${row.slug}`);
    process.exit(applied.code);
  }
  results.push({ slug: row.slug, pageId: row.pageId, only, ok: true });
}

const out = resolve(PROJECT, "qa/phase-4-token-seed.json");
mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, `${JSON.stringify({
  ok: true,
  serial: true,
  createdTokens: false,
  secondLibrary: false,
  pages: results,
}, null, 2)}\n`);
console.log(JSON.stringify({ ok: true, pages: results.length, out }, null, 2));
