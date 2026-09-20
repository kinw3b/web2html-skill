#!/usr/bin/env node
// Build gate: dump open Paper comment threads. Exit 2 while any remain.
// Humans pin comments. Agents cannot create_comment. Apply every open thread
// even if the user never mentioned comments, then re-run until exit 0.
//
//   PAPER_FILE_ID=<id> node scripts/list-paper-comments.mjs [--file <id>] [--out qa/paper-comments.json]

import { mkdirSync, writeFileSync, realpathSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { call, setFileId } from "./mcp-client.mjs";

/** Exit 2 while open comments remain so 2.1 cannot start on an unfixed canvas. */
export function openCommentExitCode(openCount) {
  return Number(openCount) > 0 ? 2 : 0;
}

const arg = (n, d) => {
  const i = process.argv.indexOf(`--${n}`);
  return i > -1 ? process.argv[i + 1] : d;
};

export async function listOpenPaperComments({
  fileId,
  out = "qa/paper-comments.json",
  paperCall = call,
} = {}) {
  if (!fileId) throw new Error("list-paper-comments.mjs requires --file <paperFileId>");
  setFileId(fileId);
  await paperCall("open_file", { fileId });

  const text = (r) => (r.content || []).filter((c) => c.type === "text").map((c) => c.text).join("\n");
  const parse = (r) => {
    try { return JSON.parse(text(r)); } catch { return r; }
  };

  const listed = parse(await paperCall("list_comment_threads", { fileId, status: "open" }));
  const threads = listed.threads || listed.commentThreads || listed.items || (Array.isArray(listed) ? listed : []);
  const full = [];
  for (const t of threads) {
    const id = t.id || t.commentThreadId;
    if (!id) {
      full.push(t);
      continue;
    }
    const detail = parse(await paperCall("get_comment_thread", { fileId, commentThreadId: id }));
    full.push(detail);
  }

  const dest = resolve(out);
  const report = {
    fileId,
    generatedAt: new Date().toISOString(),
    openCount: full.length,
    threads: full,
  };
  mkdirSync(dirname(dest), { recursive: true });
  writeFileSync(dest, JSON.stringify(report, null, 2));
  return { ...report, out: dest };
}

const invoked = process.argv[1]
  && realpathSync(fileURLToPath(import.meta.url)) === realpathSync(resolve(process.argv[1]));

if (invoked) {
  const FILE = arg("file", process.env.PAPER_FILE_ID || "");
  const OUT = arg("out", "qa/paper-comments.json");
  try {
    const report = await listOpenPaperComments({ fileId: FILE, out: OUT });
    console.error(`${report.openCount} open Paper comment thread(s) → ${report.out}`);
    if (report.openCount) {
      console.error("Build remediation required. Apply every open thread on the canvas and matching ship output, resolve it, then re-run this gate.");
    } else {
      console.error("No open comments. Safe to enter 2.1 if the human signed off.");
    }
    console.log(JSON.stringify({ fileId: FILE, out: report.out, openCount: report.openCount }));
    process.exitCode = openCommentExitCode(report.openCount);
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
