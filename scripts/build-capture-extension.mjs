#!/usr/bin/env node

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const packageRoot = path.resolve(here, "..", "capture-extension");
const manifest = JSON.parse(fs.readFileSync(path.join(packageRoot, "manifest.json"), "utf8"));
const folderName = `Paper-Capture-Extension-${manifest.version}`;
const dist = path.resolve(here, "..", "dist");
const output = path.join(dist, `${folderName}.zip`);
const temp = fs.mkdtempSync(path.join(os.tmpdir(), "paper-capture-extension-"));
const staged = path.join(temp, folderName);

fs.mkdirSync(dist, { recursive: true });
fs.rmSync(output, { force: true });
fs.cpSync(packageRoot, staged, {
  recursive: true,
  filter(source) {
    return !source.endsWith(".DS_Store") && !source.includes(`${path.sep}__pycache__${path.sep}`);
  },
});
fs.chmodSync(path.join(staged, "install-native-host.command"), 0o755);
fs.chmodSync(path.join(staged, "uninstall-native-host.command"), 0o755);
fs.chmodSync(path.join(staged, "bridge", "host.mjs"), 0o755);

const zipped = spawnSync("zip", ["-qry", output, folderName], {
  cwd: temp,
  encoding: "utf8",
});
fs.rmSync(temp, { recursive: true, force: true });
if (zipped.status !== 0) {
  process.stderr.write(zipped.stderr || "zip failed\n");
  process.exit(zipped.status || 1);
}

const size = fs.statSync(output).size;
process.stdout.write(`${output}\n${size} bytes\n`);
