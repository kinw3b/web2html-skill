#!/usr/bin/env node
// P-0 · One canvas ruler.
// First Paper setup.
//
//   node draw-rulers.mjs --file <paperFileId> [--init]
//
// --init draws Ruler · desktop at y=0.
// Never draws 768 / 390 bars.

import { call, setFileId } from "./mcp-client.mjs";
import {
  ensureRulers,
  mcpPayload,
  PARK_BUFFER,
} from "./rulers.mjs";

const argv = process.argv.slice(2);
const arg = (name, fallback) => {
  const i = argv.indexOf(`--${name}`);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : fallback;
};

const FILE = arg("file", process.env.PAPER_FILE_ID || "");
const INIT = argv.includes("--init");
if (!FILE) {
  console.error("need --file <paperFileId>");
  process.exit(1);
}
setFileId(FILE);

const info = mcpPayload(await call("get_basic_info", { fileId: FILE }));
const boards = info.artboards || [];
const shouldInit = INIT || boards.length === 0;

const rulers = await ensureRulers({
  call,
  fileId: FILE,
  boards,
  init: shouldInit,
  log: (...a) => console.error("·", ...a),
});

await call("finish_working_on_nodes", { fileId: FILE });
console.log(JSON.stringify({ file: FILE, buffer: PARK_BUFFER, rulers }, null, 2));
