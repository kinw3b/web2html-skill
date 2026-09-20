#!/usr/bin/env node
// Thin wrapper — the dump lives in url-to-paper next to Paper MCP.

import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const candidates = [
  resolve(here, "../../1.2 url-to-paper/scripts/dump-interior-raw.mjs"),
  resolve(here, "../../url-to-paper/scripts/dump-interior-raw.mjs"),
];
const dest = candidates.find((p) => existsSync(p));
if (!dest) {
  console.error("dump-interior-raw.mjs not found next to url-to-paper");
  process.exit(2);
}
const child = spawn(process.execPath, [dest, ...process.argv.slice(2)], { stdio: "inherit" });
child.on("exit", (code) => process.exit(code ?? 2));
