#!/usr/bin/env node
// 1.2 always starts a brand-new Paper file.
//
// Never list_files. Never open_file a similarly-named existing document.
// A leftover "Thrive" / "kp-thrive" file from last week is not this run.
//
//   node create-paper-file.mjs --project /path/to/kp-thrive [--url https://…]
//                             [--name "optional override"]
//
// Writes qa/paper-file.json and prints { fileId, fileName, created: true }.
// A retry of this same run reopens that receipt. It does not create_file again.
// Never list_files. Never open a similarly-named file from another project.

import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import os from "node:os";
import { basename, dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { call, setFileId } from "./mcp-client.mjs";
import { ensurePaper } from "./ensure-paper.mjs";

export function paperFileName({ projectRoot, url, now = new Date() } = {}) {
  const slug = slugOf(projectRoot, url);
  const pad = (n) => String(n).padStart(2, "0");
  const stamp = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}${pad(now.getMinutes())}`;
  return `${slug} ${stamp}`;
}

export const PAPER_FILE_GENERATOR = "url-to-paper/create-paper-file";

/** fileId this run already wrote. Empty when the receipt is missing or not ours. */
export function runPaperFileId(receipt) {
  if (!receipt || typeof receipt !== "object") return "";
  if (receipt.generatedFrom !== PAPER_FILE_GENERATOR) return "";
  return String(receipt.fileId || receipt.paperFileId || "").trim();
}

export function readRunPaperReceipt(projectRoot) {
  const file = join(resolve(projectRoot || process.cwd()), "qa", "paper-file.json");
  if (!existsSync(file)) return null;
  try {
    const data = JSON.parse(readFileSync(file, "utf8"));
    const fileId = runPaperFileId(data);
    return fileId ? { ...data, fileId } : null;
  } catch {
    return null;
  }
}

function slugOf(projectRoot, url) {
  if (projectRoot) {
    const base = basename(resolve(projectRoot)).replace(/[^a-zA-Z0-9._-]+/g, "-").replace(/^-|-$/g, "");
    if (base) return base;
  }
  if (url) {
    try {
      const host = new URL(url).hostname.replace(/^www\./, "");
      if (host) return host;
    } catch { /* ignore */ }
  }
  return "web2html";
}

function pipelineProgressScript() {
  const here = dirname(fileURLToPath(import.meta.url));
  const candidates = [
    join(here, "..", "..", "1.0 - web2html", "scripts", "pipeline-progress.py"),
    process.env.SKILLS && join(process.env.SKILLS, "web2html", "scripts", "pipeline-progress.py"),
    join(os.homedir(), ".claude", "skills", "web2html", "scripts", "pipeline-progress.py"),
    join(os.homedir(), ".config", "opencode", "skills", "web2html", "scripts", "pipeline-progress.py"),
  ].filter(Boolean);
  try {
    for (const entry of readdirSync(join(here, "..", ".."))) {
      if (entry === "web2html" || entry.endsWith("web2html")) {
        candidates.unshift(join(here, "..", "..", entry, "scripts", "pipeline-progress.py"));
      }
    }
  } catch { /* missing checkout */ }
  return candidates.find((p) => existsSync(p)) || null;
}

export function restampLiveBoard(projectRoot, log = console.error) {
  const script = pipelineProgressScript();
  if (!script) {
    log("  board restamp skipped: pipeline-progress.py not found");
    return;
  }
  const result = spawnSync("python3", [script, "restamp", projectRoot], { encoding: "utf8" });
  if (result.status !== 0) {
    log(`  board restamp failed: ${(result.stderr || result.stdout || "").trim()}`);
    return;
  }
  const line = (result.stdout || "").split("\n").map((s) => s.trim()).find((s) => s.includes("paperFileId="));
  if (line) log(`  capture ${line}`);
}

function payload(result) {
  for (const item of result.content ?? []) {
    if (item.type === "text") {
      try { return JSON.parse(item.text); } catch { return { text: item.text }; }
    }
  }
  return result && typeof result === "object" ? result : {};
}

async function openRunPaperFile({ projectRoot, launch, log }) {
  const receipt = readRunPaperReceipt(projectRoot);
  if (!receipt) return null;
  setFileId(null);
  await ensurePaper({ launch, log });
  try {
    await call("open_file", { fileId: receipt.fileId });
    const info = payload(await call("get_basic_info", { fileId: receipt.fileId }));
    setFileId(receipt.fileId);
    log(
      `1.2 reusing this run's Paper file ${receipt.fileId} ("${info.fileName || receipt.fileName || ""}") — a retry does not create a second document`,
    );
    return {
      ...receipt,
      fileName: info.fileName || receipt.fileName,
      created: false,
      reused: true,
    };
  } catch (err) {
    log(`  receipt ${receipt.fileId} did not open (${err.message}). Creating a new Paper file.`);
    setFileId(null);
    return null;
  }
}

export async function createPaperFile({
  projectRoot,
  url = "",
  name = "",
  launch = true,
  reuse = false,
  log = console.error,
} = {}) {
  const root = resolve(projectRoot || process.cwd());
  if (reuse) {
    const existing = await openRunPaperFile({ projectRoot: root, launch, log });
    if (existing) return existing;
  }
  const fileName = name || paperFileName({ projectRoot: root, url });
  log(`1.2 creating new Paper file "${fileName}" — never reuse a similarly-named existing file`);
  setFileId(null);
  await ensurePaper({ launch, log });
  const created = payload(await call("create_file", { name: fileName }, { pinFile: false }));
  const fileId = created.fileId || created.id || created.file?.id;
  if (!fileId) {
    throw new Error(`create_file returned no id: ${JSON.stringify(created).slice(0, 400)}`);
  }
  setFileId(fileId);
  await call("open_file", { fileId });
  const info = payload(await call("get_basic_info", { fileId }));
  const receipt = {
    fileId,
    fileName: info.fileName || fileName,
    url: created.url || created.fileUrl || info.fileUrl || info.url || null,
    sourceUrl: url || null,
    created: true,
    createdAt: new Date().toISOString(),
    generatedFrom: PAPER_FILE_GENERATOR,
  };
  const qaDir = join(root, "qa");
  mkdirSync(qaDir, { recursive: true });
  writeFileSync(join(qaDir, "paper-file.json"), `${JSON.stringify(receipt, null, 2)}\n`);
  log(`  file ${fileId} (created)`);
  restampLiveBoard(root, log);
  return receipt;
}

if (process.argv[1]?.endsWith("create-paper-file.mjs")) {
  const argv = process.argv.slice(2);
  const arg = (flag, fallback) => {
    const i = argv.indexOf(`--${flag}`);
    return i >= 0 && argv[i + 1] ? argv[i + 1] : fallback;
  };
  const projectRoot = arg("project", process.cwd());
  const receipt = await createPaperFile({
    projectRoot,
    url: arg("url", ""),
    name: arg("name", ""),
    reuse: !argv.includes("--new-file"),
  });
  console.log(JSON.stringify(receipt, null, 2));
}
