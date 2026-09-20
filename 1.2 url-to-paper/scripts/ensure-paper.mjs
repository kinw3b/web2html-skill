#!/usr/bin/env node
// Make sure Paper Desktop is running and its MCP server is reachable.
//
// The MCP server is bound to the Paper app process, not a background daemon:
//   lsof -nP -iTCP:29979 -sTCP:LISTEN
//   Paper  <pid>  /Applications/Paper.app/Contents/MacOS/Paper
// Quit Paper and the port closes. So autonomy means launching the app.
//
// Usage: node ensure-paper.mjs [--timeout 60] [--no-launch]
// Exports ensurePaper() for the other scripts.

import { spawn } from "node:child_process";

const ENDPOINT = process.env.PAPER_MCP || "http://127.0.0.1:29979/mcp";

export async function isUp() {
  try {
    const res = await fetch(ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json, text/event-stream",
      },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: 1,
        method: "initialize",
        params: {
          protocolVersion: "2025-06-18",
          capabilities: {},
          clientInfo: { name: "url-to-paper-probe", version: "1.0" },
        },
      }),
      signal: AbortSignal.timeout(4000),
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function ensurePaper({ timeoutSec = 60, launch = true, log = console.error } = {}) {
  if (await isUp()) {
    log("· Paper MCP already up");
    return { launched: false };
  }

  if (!launch) {
    throw new Error(
      "Paper MCP is not reachable and --no-launch was set. Open Paper Desktop with a file.",
    );
  }

  log("· Paper MCP not reachable — launching Paper…");
  spawn("open", ["-a", "Paper"], { stdio: "ignore", detached: true }).unref();

  const deadline = Date.now() + timeoutSec * 1000;
  let waited = 0;
  while (Date.now() < deadline) {
    await new Promise((r) => setTimeout(r, 2000));
    waited += 2;
    if (await isUp()) {
      log(`· Paper MCP up after ${waited}s`);
      return { launched: true, waitedSec: waited };
    }
    if (waited % 10 === 0) log(`  …waiting (${waited}s)`);
  }

  throw new Error(
    `Paper MCP still unreachable after ${timeoutSec}s.\n` +
    "The server only starts once Paper has a FILE OPEN — if Paper launched to an\n" +
    "empty state, open or create a document once and retry.",
  );
}

// CLI
if (import.meta.url === `file://${process.argv[1]}`) {
  const argv = process.argv.slice(2);
  const ti = argv.indexOf("--timeout");
  const timeoutSec = ti >= 0 ? parseInt(argv[ti + 1], 10) : 60;
  const result = await ensurePaper({
    timeoutSec,
    launch: !argv.includes("--no-launch"),
  });
  console.log(JSON.stringify(result, null, 1));
}
