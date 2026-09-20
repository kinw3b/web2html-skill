import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";


const HERE = path.dirname(fileURLToPath(import.meta.url));


function runNode(script, args, { cwd, env, log }) {
  return new Promise((resolve) => {
    const child = spawn(process.execPath, [script, ...args], {
      cwd,
      env,
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (data) => {
      stdout += data;
      log?.(String(data).trimEnd());
    });
    child.stderr.on("data", (data) => {
      stderr += data;
      log?.(String(data).trimEnd());
    });
    child.on("close", (code) => resolve({ code: code ?? 1, stdout, stderr }));
    child.on("error", (error) => resolve({
      code: 1,
      stdout,
      stderr: `${stderr}\n${error.message}`.trim(),
    }));
  });
}


function evidenceBlock(label, result) {
  const output = `${result.stdout}\n${result.stderr}`.trim();
  return [
    `## ${label}`,
    "",
    `Exit: ${result.code}`,
    "",
    "```text",
    output || "(no output)",
    "```",
  ].join("\n");
}


export async function runGeometryPostflight({
  projectRoot,
  fileId,
  artboard = "home-desktop",
  log = console.error,
}) {
  if (!fileId) return { ok: false, reason: "Paper file is missing" };
  const root = path.resolve(projectRoot);
  const qaDir = path.join(root, "qa");
  const evidence = path.join(qaDir, "stretch-root-evidence.md");
  fs.mkdirSync(qaDir, { recursive: true });
  const env = { ...process.env, PAPER_FILE_ID: fileId };

  log("1.2 postflight · proving stretch-root");
  const stretch = await runNode(
    path.join(HERE, "stretch-root.mjs"),
    ["--prove", "--artboard", artboard],
    { cwd: root, env, log },
  );
  const ok = stretch.code === 0;
  fs.writeFileSync(evidence, [
    "# 1.2 geometry postflight",
    "",
    `Generated: ${new Date().toISOString()}`,
    `Artboard: ${artboard}`,
    "",
    evidenceBlock("Stretch-root proof", stretch),
    "",
    `Result: ${ok ? "PASS" : "FAIL"}`,
    "",
  ].join("\n"));
  if (!ok) {
    return { ok: false, reason: "stretch-root proof failed", evidence };
  }
  return { ok: true, reason: "", evidence };
}


if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  const arg = (name, fallback = "") => {
    const index = process.argv.indexOf(`--${name}`);
    return index >= 0 ? process.argv[index + 1] : fallback;
  };
  const result = await runGeometryPostflight({
    projectRoot: arg("project", process.cwd()),
    fileId: arg("file", process.env.PAPER_FILE_ID || ""),
    artboard: arg("artboard", "home-desktop"),
  });
  console.log(JSON.stringify(result, null, 2));
  if (!result.ok) process.exitCode = 2;
}
