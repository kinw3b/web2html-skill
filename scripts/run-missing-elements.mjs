#!/usr/bin/env node
// Optional diagnostic: inventory → apply → rewrite the checklist → open Chrome.
// Not a pipeline step. 1.5 is the human walk with Paper comments.

import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const argv = process.argv.slice(2);
const arg = (name, fallback) => {
  const i = argv.indexOf(`--${name}`);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : fallback;
};

const capture = resolve(arg("capture", "capture/home-desktop"));
const outDir = resolve(arg("out-dir", "qa"));

function extra() {
  const out = [];
  for (const key of ["project", "live", "paper", "file-id", "artboard"]) {
    if (arg(key)) out.push(`--${key}`, arg(key));
  }
  return out;
}

function run(file, args) {
  return new Promise((resolveP, reject) => {
    const child = spawn(process.execPath, [file, ...args], { stdio: "inherit" });
    child.on("exit", (code) => (code === 0 ? resolveP() : reject(new Error(`${file} exited ${code}`))));
  });
}

await run(resolve(here, "missing-elements-qa.mjs"), ["--capture", capture, "--out-dir", outDir, ...extra()]);
if (!argv.includes("--report-only")) {
  const applyArgs = [
    "--from", resolve(outDir, "missing-elements-fix.json"),
    "--capture", capture,
    "--out-dir", outDir,
  ];
  if (arg("file-id")) applyArgs.push("--file-id", arg("file-id"));
  if (argv.includes("--dry-run")) applyArgs.push("--dry-run");
  await run(resolve(here, "apply-from-source-shots.mjs"), applyArgs);
}

const html = resolve(outDir, "missing-elements-fix.html");
if (existsSync(html) && !argv.includes("--no-open")) {
  spawn("open", ["-a", "Google Chrome", html], { stdio: "ignore", detached: true }).unref();
  console.error(`· opened ${html}`);
}
console.log(html);
