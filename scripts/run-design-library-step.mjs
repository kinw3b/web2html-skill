#!/usr/bin/env node

import { existsSync, mkdirSync, readFileSync, realpathSync, writeFileSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { isLibraryMineArtboard } from "./token-pass-targets.mjs";

const __dir = dirname(fileURLToPath(import.meta.url));
const CAPTURE_TOOL_FRAME = /^(Buttons|Hover States|Components|Navigation|Interactive components)$/;
const LANDER = /-(desktop|768|390)$/i;
export const STALL_SILENCE_MS = 20_000;
export const COMMAND_HARD_CAP_MS = 240_000;
export const HEARTBEAT_MS = 10_000;

export function stallReason({
  startedAt,
  lastByteAt,
  now,
  silenceMs = STALL_SILENCE_MS,
  hardCapMs = COMMAND_HARD_CAP_MS,
}) {
  if (now - startedAt >= hardCapMs) {
    return `hard cap ${hardCapMs}ms`;
  }
  if (now - lastByteAt >= silenceMs) {
    return `silent ${silenceMs}ms`;
  }
  return null;
}

export function runCommandWithStallWatch(script, args, {
  cwd,
  execPath = process.execPath,
  scriptDir = __dir,
  silenceMs = STALL_SILENCE_MS,
  hardCapMs = COMMAND_HARD_CAP_MS,
  heartbeatMs = HEARTBEAT_MS,
  now = Date.now,
  log = console.error,
  spawnFn = spawn,
} = {}) {
  log(`[1.3] starting ${script} …`);
  const startedAt = now();
  let lastByteAt = startedAt;
  const child = spawnFn(execPath, [join(scriptDir, script), ...args], {
    cwd,
    stdio: ["ignore", "pipe", "pipe"],
  });
  const onChunk = (chunk, write) => {
    lastByteAt = now();
    write(chunk);
  };
  child.stdout?.on("data", (chunk) => onChunk(chunk, (b) => process.stdout.write(b)));
  child.stderr?.on("data", (chunk) => onChunk(chunk, (b) => process.stderr.write(b)));

  return new Promise((resolve) => {
    const tick = () => {
      const reason = stallReason({
        startedAt,
        lastByteAt,
        now: now(),
        silenceMs,
        hardCapMs,
      });
      if (!reason) {
        return;
      }
      log(`[1.3] stalled: ${script} ${reason} — killing`);
      try { child.kill("SIGTERM"); } catch {}
      setTimeout(() => {
        try { child.kill("SIGKILL"); } catch {}
      }, 400);
    };
    const beat = setInterval(tick, heartbeatMs);
    child.on("close", (status, signal) => {
      clearInterval(beat);
      if (signal) {
        resolve({ status: 1, error: `${script} killed (${signal})` });
        return;
      }
      resolve({ status: status ?? 1 });
    });
    child.on("error", (error) => {
      clearInterval(beat);
      resolve({ status: 1, error: error.message });
    });
  });
}

function uniqueNames(artboards) {
  return [...new Set((artboards || [])
    .map((board) => typeof board === "string" ? board : board?.name)
    .filter(Boolean))];
}

export function assertDesignLibrarySources(artboards = []) {
  const sources = uniqueNames(artboards).filter(isLibraryMineArtboard);
  const landers = sources.filter((name) => LANDER.test(name));
  const viewports = new Set(landers.map((name) => LANDER.exec(name)?.[1].toLowerCase()));
  if (!["desktop", "768", "390"].every((viewport) => viewports.has(viewport))) {
    throw new Error("1.3 requires desktop, 768, and 390 landers");
  }

  const captureFrames = sources.filter((name) => CAPTURE_TOOL_FRAME.test(name));
  if (!captureFrames.includes("Navigation")) {
    throw new Error("1.3 requires the Navigation frame captured by 1.2");
  }
  return { sources, landers, captureFrames };
}


export function foundationsLibraryReceiptOk(receipt = {}) {
  const commands = receipt.commands || [];
  return receipt.status === "done"
    && receipt.writer === "render-library.mjs"
    && receipt.kind === "foundations"
    && commands.includes("extract-library.mjs")
    && commands.includes("render-library.mjs");
}

export function designLibraryStepCommands({ projectRoot, fileId, expectFile }) {
  const root = resolve(projectRoot);
  const library = join(root, "design-library", "library.json");
  const common = ["--file-id", fileId, "--expect-file", expectFile, "--project", root];
  return [
    [
      "extract-library.mjs",
      "--replace-tokens",
      "--write-tokens",
      ...common,
      "--json",
      library,
    ],
    [
      "render-library.mjs",
      "--kind",
      "foundations",
      ...common,
      "--library",
      library,
    ],
    [
      "apply-theme-tokens.mjs",
      "--exact-only",
      ...common,
      "--library",
      library,
      "--json",
      join(root, "qa", "token-pass.json"),
      "--qa",
      join(root, "qa", "token-pass-qa.json"),
    ],
  ];
}

function payload(result) {
  for (const item of result?.content || []) {
    if (item.type !== "text") continue;
    try { return JSON.parse(item.text); } catch { return { text: item.text }; }
  }
  return {};
}

function requiredArg(argv, name) {
  const i = argv.indexOf(`--${name}`);
  const value = i >= 0 ? argv[i + 1] : "";
  if (!value || value.startsWith("--")) {
    throw new Error(`run-design-library-step.mjs requires --${name}`);
  }
  return value;
}

export function libraryMineRefusal(projectRoot) {
  const path = join(resolve(projectRoot), "qa", "run-config.json");
  if (!existsSync(path)) return null;
  try {
    const cfg = JSON.parse(readFileSync(path, "utf8"));
    if (cfg && cfg.adopt === true) {
      return "clean HTML source is adopted — do not mine a Design Library or bind tokens onto frames (Pitfall #224).";
    }
    if (cfg && cfg.designLibrary === false) {
      return "run-config designLibrary is false — 1.3 is skipped.";
    }
  } catch {
    return null;
  }
  return null;
}

export async function runDesignLibraryStep({
  projectRoot,
  fileId,
  expectFile,
  paperCall,
  runCommand = (script, args) => runCommandWithStallWatch(script, args, {
    cwd: projectRoot,
    silenceMs: STALL_SILENCE_MS,
  }),
  now = () => new Date().toISOString(),
}) {
  const root = resolve(projectRoot);
  const refused = libraryMineRefusal(root);
  if (refused) {
    throw new Error(refused);
  }
  const info = payload(await paperCall("get_basic_info", { fileId }));
  if (!info.fileName || !String(info.fileName).includes(expectFile)) {
    throw new Error(
      `Active file is "${info.fileName || "(none)"}" but --expect-file "${expectFile}" was required. Refusing to run.`,
    );
  }
  const inventory = assertDesignLibrarySources(info.artboards || []);
  const commands = designLibraryStepCommands({ projectRoot: root, fileId, expectFile });

  for (const [script, ...args] of commands) {
    const result = await runCommand(script, args);
    if (result?.status !== 0) {
      throw new Error(
        `1.3 stopped: ${script} failed with status ${result?.status ?? "unknown"}`
        + (result?.error ? ` (${result.error})` : ""),
      );
    }
  }

  const finalInfo = payload(await paperCall("get_basic_info", { fileId }));
  const libraries = (finalInfo.artboards || [])
    .filter((board) => board?.name === "Design Library");
  if (libraries.length !== 1) {
    throw new Error(`1.3 requires exactly one Design Library; found ${libraries.length}`);
  }

  const artifacts = {
    library: join(root, "design-library", "library.json"),
    tokenPass: join(root, "qa", "token-pass.json"),
    tokenPassQa: join(root, "qa", "token-pass-qa.json"),
    geometryBefore: join(root, "qa", "token-geometry-before.json"),
    geometryAfter: join(root, "qa", "token-geometry-after.json"),
  };
  const commandNames = commands.map(([script]) => script);
  if (!foundationsLibraryReceiptOk({
    status: "done",
    writer: "render-library.mjs",
    kind: "foundations",
    commands: commandNames,
  })) {
    throw new Error(
      "1.3 stopped: Design Library must be painted by render-library.mjs --kind foundations "
      + "(templates/library/foundations). Do not write_html a hand-built sheet. Pitfall #158",
    );
  }
  const receipt = {
    status: "done",
    completedAt: now(),
    file: finalInfo.fileName || info.fileName,
    fileId,
    writer: "render-library.mjs",
    kind: "foundations",
    templates: "templates/library/foundations",
    ...inventory,
    commands: commandNames,
    artifacts,
  };
  const receiptPath = join(root, "qa", "design-library-step.json");
  mkdirSync(dirname(receiptPath), { recursive: true });
  writeFileSync(receiptPath, JSON.stringify(receipt, null, 2), "utf8");
  return receipt;
}

const invoked = process.argv[1]
  && realpathSync(fileURLToPath(import.meta.url)) === realpathSync(resolve(process.argv[1]));

if (invoked) {
  try {
    const argv = process.argv.slice(2);
    const projectRoot = requiredArg(argv, "project");
    const fileId = requiredArg(argv, "file-id");
    const expectFile = requiredArg(argv, "expect-file");
    const { call, setFileId } = await import("./mcp-client.mjs");
    setFileId(fileId);
    const receipt = await runDesignLibraryStep({
      projectRoot,
      fileId,
      expectFile,
      paperCall: call,
    });
    console.log(JSON.stringify(receipt, null, 2));
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
