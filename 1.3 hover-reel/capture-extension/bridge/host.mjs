#!/usr/bin/env node

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
const HOST_VERSION = "1.2.34";
const BOARD_NAMES = ["Navigation", "Buttons", "Components"];
const BOARD_ALIASES = { Buttons: ["Hover States"] };
const MAX_MESSAGE_BYTES = 8 * 1024 * 1024;
const MAX_HTML_BYTES = 220_000;

let input = Buffer.alloc(0);
let config = null;
let mcpSessionId = null;
let mcpConnected = false;

function send(message) {
  const payload = Buffer.from(JSON.stringify(message));
  const header = Buffer.alloc(4);
  header.writeUInt32LE(payload.length, 0);
  process.stdout.write(Buffer.concat([header, payload]));
}

function cleanError(error) {
  return String(error?.message || error || "Unknown bridge error").split("\n")[0];
}

function parseSse(text) {
  const messages = [];
  for (const line of text.split(/\r?\n/)) {
    if (!line.startsWith("data:")) continue;
    const raw = line.slice(5).trim();
    if (!raw || raw === "[DONE]") continue;
    try { messages.push(JSON.parse(raw)); } catch { /* malformed event */ }
  }
  if (!messages.length && text.trim().startsWith("{")) {
    try { messages.push(JSON.parse(text)); } catch { /* malformed response */ }
  }
  return messages;
}

async function rpc(method, params, { notify = false, timeoutMs = 90000 } = {}) {
  if (!config?.paperEndpoint) throw new Error("Paper endpoint is not configured");
  const headers = {
    "Content-Type": "application/json",
    Accept: "application/json, text/event-stream",
  };
  if (mcpSessionId) headers["mcp-session-id"] = mcpSessionId;
  const body = notify
    ? { jsonrpc: "2.0", method, params }
    : { jsonrpc: "2.0", id: Math.floor(Math.random() * 1e8), method, params };
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let response;
  try {
    response = await fetch(config.paperEndpoint, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      signal: controller.signal,
    });
  } catch (error) {
    if (error.name === "AbortError") throw new Error(`Paper timed out during ${method}`);
    throw new Error(`Cannot reach Paper Desktop at ${config.paperEndpoint}`);
  } finally {
    clearTimeout(timer);
  }
  const nextSessionId = response.headers.get("mcp-session-id");
  if (nextSessionId) mcpSessionId = nextSessionId;
  if (notify) return null;
  const text = await response.text();
  const reply = parseSse(text).find((item) => item.result || item.error);
  if (!reply) throw new Error(`Paper returned no JSON-RPC result for ${method}`);
  if (reply.error) throw new Error(`Paper MCP error: ${JSON.stringify(reply.error)}`);
  return reply.result;
}

async function connectPaper() {
  if (mcpConnected) return;
  await rpc("initialize", {
    protocolVersion: "2025-06-18",
    capabilities: {},
    clientInfo: { name: "paper-capture-extension", version: HOST_VERSION },
  });
  await rpc("notifications/initialized", {}, { notify: true });
  mcpConnected = true;
}

async function paperCall(name, args = {}) {
  await connectPaper();
  const withFile = config.paperFileId && args.fileId === undefined
    ? { ...args, fileId: config.paperFileId }
    : args;
  return rpc("tools/call", { name, arguments: withFile }, {
    timeoutMs: name === "write_html" ? 120000 : 90000,
  });
}

function mcpPayload(result) {
  for (const item of result?.content || []) {
    if (item.type !== "text") continue;
    try { return JSON.parse(item.text); } catch { return { text: item.text }; }
  }
  return {};
}

function nodeId(payload) {
  return payload?.createdNodes?.[0]?.id || payload?.ids?.[0] || payload?.nodeId || payload?.id || null;
}

function captureToolHome() {
  const override = String(process.env.PAPER_CAPTURE_HOME || "").trim();
  if (override) return override;
  if (process.platform === "darwin") {
    return path.join(os.homedir(), "Library", "Application Support", "Paper Capture Tool");
  }
  return path.join(os.homedir(), ".paper-capture-tool");
}

function readJsonFile(file) {
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch {
    return null;
  }
}

function loadPaperSections(projectRoot) {
  const capture = path.join(projectRoot, "capture", "home-desktop");
  for (const name of ["review-sequence.json", "section-ids.json"]) {
    const rows = readJsonFile(path.join(capture, name))?.sections || [];
    const sections = rows.map((section, index) => ({
      id: String(section.id || String(index + 1).padStart(2, "0")).padStart(2, "0"),
      slug: section.slug || section.name || "",
      top: Number(section.top ?? section.bbox?.y ?? section.y),
      h: Number(section.height ?? section.h ?? section.bbox?.h ?? 0),
    })).filter((section) => Number.isFinite(section.top));
    if (sections.length) return sections;
  }
  return [];
}

export function readActiveSession() {
  const explicit = String(process.env.PAPER_CAPTURE_SESSION || "").trim();
  const candidates = [
    explicit,
    path.join(captureToolHome(), "active-session.json"),
  ].filter(Boolean);
  let session = null;
  for (const file of candidates) {
    const parsed = readJsonFile(file);
    if (!parsed || typeof parsed !== "object") continue;
    session = parsed;
    break;
  }
  const projectRoot = String(session?.projectRoot || "").trim();
  if (projectRoot) {
    const paper = readJsonFile(path.join(projectRoot, "qa", "paper-file.json")) || {};
    session = {
      ...session,
      paperFileId: session.paperFileId || paper.fileId || paper.paperFileId || "",
      projectRoot,
      paperEndpoint: session.paperEndpoint || paper.paperEndpoint || "",
      url: session.url || paper.url || "",
    };
  }
  const paperFileId = String(session?.paperFileId || "").trim();
  const root = String(session?.projectRoot || "").trim();
  if (!paperFileId && !root) return null;
  return {
    paperFileId,
    projectRoot: root,
    paperEndpoint: String(session?.paperEndpoint || "").trim(),
    url: String(session?.url || "").trim(),
  };
}

function assertConfig(next) {
  const projectRoot = String(next?.projectRoot || "").trim();
  const paperFileId = String(next?.paperFileId || "").trim();
  const paperEndpoint = String(next?.paperEndpoint || "http://127.0.0.1:29979/mcp").trim();
  if (!path.isAbsolute(projectRoot)) throw new Error("Project folder must be an absolute path");
  const stat = fs.statSync(projectRoot, { throwIfNoEntry: false });
  if (!stat?.isDirectory()) throw new Error("Project folder does not exist or is not a directory");
  if (!paperFileId) throw new Error("Paper file ID is required");
  let endpoint;
  try { endpoint = new URL(paperEndpoint); } catch { throw new Error("Paper endpoint is not a valid URL"); }
  if (!(["127.0.0.1", "localhost", "::1"].includes(endpoint.hostname))) {
    throw new Error("Paper endpoint must stay on localhost");
  }
  if (endpoint.protocol !== "http:" && endpoint.protocol !== "https:") {
    throw new Error("Paper endpoint must use http or https");
  }
  return {
    projectRoot: fs.realpathSync(projectRoot),
    paperFileId,
    paperEndpoint: endpoint.href,
    sourceUrl: String(next?.sourceUrl || ""),
  };
}

function boardPosition(artboards, index) {
  const right = artboards.reduce((max, board) => {
    const x = Number(board.worldX ?? board.x ?? board.left ?? 0);
    return Math.max(max, x + Number(board.width || 0));
  }, 0);
  const top = artboards.reduce((min, board) => {
    const y = Number(board.worldY ?? board.y ?? board.top ?? 300);
    return Math.min(min, y);
  }, 300);
  return { left: Math.round(right + 100 + index * 1500), top: Math.round(top) };
}

function escapeHtml(value) {
  return String(value || "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);
}

function titleHtml(name) {
  return `<div layer-name="Title" style="font-family:Inter,sans-serif;font-size:26px;font-weight:700;color:#111827;line-height:120%;">${escapeHtml(name)}</div>`;
}

async function getBoards() {
  const info = mcpPayload(await paperCall("get_basic_info", {}));
  return { info, artboards: info.artboards || [] };
}

async function ensureBoard(name, index) {
  const current = await getBoards();
  const aliases = BOARD_ALIASES[name] || [];
  let board = current.artboards.find((item) => item.name === name)
    || current.artboards.find((item) => aliases.includes(item.name));
  if (board?.id) {
    if (board.name !== name) {
      try {
        await paperCall("rename_nodes", { updates: [{ nodeId: board.id, name }] });
        board = { ...board, name };
      } catch { /* alias frame is still writable under the old name */ }
    }
    return board;
  }
  const position = boardPosition(current.artboards, index);
  const created = mcpPayload(await paperCall("create_artboard", {
    name,
    styles: {
      display: "flex",
      flexDirection: "column",
      width: "fit-content",
      height: "fit-content",
      overflow: "visible",
      backgroundColor: "#F2F2F2",
      padding: "48px",
      gap: "28px",
      left: `${position.left}px`,
      top: `${position.top}px`,
    },
  }));
  const id = nodeId(created);
  if (!id) throw new Error(`Paper did not create the ${name} frame`);
  try {
    await paperCall("update_styles", {
      updates: [{ nodeIds: [id], styles: { width: "fit-content", height: "fit-content" } }],
    });
  } catch { /* Paper may already be fit-content */ }
  await paperCall("write_html", {
    targetNodeId: id,
    mode: "insert-children",
    html: titleHtml(name),
  });
  return { id, name };
}

async function ensureBoards() {
  const ready = {};
  for (const [index, name] of BOARD_NAMES.entries()) {
    ready[name] = await ensureBoard(name, index);
  }
  return ready;
}

function artifactRoot() {
  return path.join(config.projectRoot, "source-site", "components");
}

function sessionPath() {
  return path.join(artifactRoot(), "capture-extension-session.json");
}

function readJson(file, fallback) {
  try { return JSON.parse(fs.readFileSync(file, "utf8")); } catch { return fallback; }
}

function writeJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function sessionState() {
  return readJson(sessionPath(), {
    version: HOST_VERSION,
    sourceUrl: config.sourceUrl,
    startedAt: new Date().toISOString(),
    receipts: {},
    takes: [],
  });
}

function saveSession(value) {
  writeJson(sessionPath(), value);
}

function slug(value, fallback = "take") {
  const result = String(value || "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 52);
  return result || fallback;
}

function takeFolder(take) {
  const kind = take.kind === "multi-state" ? "multi-state"
    : take.kind === "single" ? "single"
      : take.kind === "dropdown" ? "dropdown"
        : take.kind === "navbar" ? "navbar" : "hover";
  return path.join(artifactRoot(), "home", kind);
}

function safeTakeHtml(value) {
  const html = typeof value === "string" ? value.trim() : "";
  if (!html || html === "[object Object]") throw new Error("Capture HTML is empty");
  if (Buffer.byteLength(html) > MAX_HTML_BYTES) throw new Error("Capture HTML is too large for a reliable Paper write");
  return html;
}

function paperBoardFor(take) {
  if (take.kind === "navbar" || take.kind === "dropdown") return "Navigation";
  if (take.mode === "hover") return "Buttons";
  return "Components";
}

function takeRowHtml(take) {
  const label = escapeHtml(take.label || take.kind || take.mode || "Capture");
  const section = escapeHtml(take.sectionId || "—");
  let first = "";
  let second = "";
  if (take.defaultHtml || take.hoverHtml) {
    first = safeTakeHtml(take.defaultHtml || take.html);
    second = take.hoverHtml ? safeTakeHtml(take.hoverHtml) : "";
  } else {
    first = safeTakeHtml(take.html);
  }
  const state = (name, html) => html ? `<div layer-name="${name}" style="display:flex;align-items:flex-start;width:fit-content;height:fit-content;overflow:visible;">${html}</div>` : "";
  return `<div layer-name="Capture Extension · ${label}" style="display:flex;flex-direction:column;align-items:flex-start;gap:16px;width:fit-content;height:fit-content;flex-shrink:0;padding:24px;background:#6F6F6F;border-radius:16px;overflow:visible;box-sizing:border-box;">
    <div layer-name="title" style="display:flex;align-items:center;gap:12px;width:fit-content;height:fit-content;">
      <div layer-name="section-number" style="display:flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:36px;background:#E11D2E;flex-shrink:0;"><p style="font-family:Inter,sans-serif;font-size:12px;font-weight:700;color:#FFFFFF;line-height:120%;">${section}</p></div>
      <p style="font-family:Inter,sans-serif;font-size:14px;font-weight:600;color:#F2F2F2;line-height:120%;">${label}</p>
    </div>
    <div layer-name="states" style="display:flex;flex-direction:column;align-items:flex-start;gap:12px;width:fit-content;height:fit-content;overflow:visible;">
      ${state("first", first)}${state("second", second)}
    </div>
  </div>`;
}

function persistTakeArtifacts(take) {
  const folder = takeFolder(take);
  fs.mkdirSync(folder, { recursive: true });
  // Labels are archetype names now, so two takes in one section can share one.
  // The take id keeps their files apart.
  const suffix = String(take.id || "").slice(-6).replace(/[^a-z0-9]/gi, "") || "take";
  const base = `${String(take.sectionId || "00").padStart(2, "0")}-${slug(take.label, take.kind)}-${suffix}`;
  if (take.mode === "tags") {
    throw new Error("Tags Scan is removed; 1.2 layer-ids.json is the census");
  } else if (take.defaultHtml || take.hoverHtml) {
    fs.writeFileSync(path.join(folder, `${base}--default.html`), `${safeTakeHtml(take.defaultHtml || take.html)}\n`, "utf8");
    if (take.hoverHtml) fs.writeFileSync(path.join(folder, `${base}--state-2.html`), `${safeTakeHtml(take.hoverHtml)}\n`, "utf8");
  } else {
    fs.writeFileSync(path.join(folder, `${base}.html`), `${safeTakeHtml(take.html)}\n`, "utf8");
  }
  const manifestFile = path.join(folder, "manifest.json");
  const manifest = readJson(manifestFile, { version: 1, takes: [] });
  const metadata = { ...take };
  delete metadata.html;
  delete metadata.defaultHtml;
  delete metadata.hoverHtml;
  const oldIndex = manifest.takes.findIndex((item) => item.id === take.id);
  if (oldIndex >= 0) manifest.takes[oldIndex] = metadata;
  else manifest.takes.push(metadata);
  writeJson(manifestFile, manifest);
}

async function commitTake(take) {
  if (!take?.id) throw new Error("Take ID is missing");
  if (take.mode === "tags") throw new Error("Tags Scan is removed; no Tags board is created");
  const session = sessionState();
  if (session.receipts[take.id]?.paperNodeId) return session.receipts[take.id];
  persistTakeArtifacts(take);
  const boardName = paperBoardFor(take);
  const boards = await ensureBoards();
  const board = boards[boardName];
  if (!board?.id) throw new Error(`${boardName} is not writable`);
  const result = mcpPayload(await paperCall("write_html", {
    targetNodeId: board.id,
    mode: "insert-children",
    html: takeRowHtml(take),
  }));
  const paperNodeId = nodeId(result);
  if (!paperNodeId) throw new Error(`Paper returned no node receipt for ${take.label || take.kind}`);
  try {
    await paperCall("rename_nodes", {
      updates: [{ nodeId: paperNodeId, name: take.label || take.kind || take.mode || "Capture" }],
    });
    await paperCall("update_styles", {
      updates: [{ nodeIds: [board.id], styles: { width: "fit-content", height: "fit-content", overflow: "visible" } }],
    });
  } catch { /* write receipt is authoritative; naming/hug is best effort */ }
  const receipt = {
    takeId: take.id,
    board: boardName,
    paperNodeId,
    addedAt: new Date().toISOString(),
  };
  session.receipts[take.id] = receipt;
  const metadata = { ...take };
  delete metadata.html;
  delete metadata.defaultHtml;
  delete metadata.hoverHtml;
  const old = session.takes.findIndex((item) => item.id === take.id);
  if (old >= 0) session.takes[old] = metadata;
  else session.takes.push(metadata);
  saveSession(session);
  return receipt;
}

async function startSession(nextConfig) {
  const normalized = assertConfig(nextConfig);
  const endpointChanged = config?.paperEndpoint !== normalized.paperEndpoint;
  config = normalized;
  if (endpointChanged) {
    mcpSessionId = null;
    mcpConnected = false;
  }
  fs.mkdirSync(artifactRoot(), { recursive: true });
  const boards = await ensureBoards();
  const session = sessionState();
  session.sourceUrl = config.sourceUrl;
  session.paperFileId = config.paperFileId;
  session.status = "active";
  saveSession(session);
  return {
    boards: Object.keys(boards),
    projectRoot: config.projectRoot,
    paperSections: loadPaperSections(config.projectRoot),
  };
}

function completeSession(summary) {
  if (!config) throw new Error("No capture session is active");
  const session = sessionState();
  const done = {
    status: "done",
    generatedFrom: "paper-capture-extension",
    completedAt: new Date().toISOString(),
    sourceUrl: summary?.sourceUrl || config.sourceUrl,
    paperFileId: config.paperFileId,
    takeCount: Number(summary?.takeCount || Object.keys(session.receipts || {}).length),
    boards: summary?.boards || [...new Set(Object.values(session.receipts || {}).map((item) => item.board))],
    receiptNodeIds: Object.values(session.receipts || {}).map((item) => item.paperNodeId).filter(Boolean),
  };
  writeJson(path.join(artifactRoot(), "human-hover-done.json"), done);
  session.status = "complete";
  session.completedAt = done.completedAt;
  saveSession(session);
  return done;
}

async function handle(message) {
  if (message.type === "PING") {
    return {
      version: HOST_VERSION,
      host: "paper-capture-extension",
      session: readActiveSession(),
    };
  }
  if (message.type === "START_SESSION") return startSession(message.config);
  if (message.type === "COMMIT_TAKE") {
    if (!config) throw new Error("Start the capture session first");
    return { receipt: await commitTake(message.take) };
  }
  if (message.type === "APPLY_SEMANTICS") {
    throw new Error("Tags Scan is removed; 1.2 layer-ids.json is the census");
  }
  if (message.type === "COMPLETE_SESSION") return { done: completeSession(message.summary) };
  throw new Error(`Unknown bridge message: ${message.type}`);
}

async function dispatch(message) {
  const requestId = message?.requestId || null;
  try {
    const result = await handle(message || {});
    send({ requestId, ok: true, ...result });
  } catch (error) {
    send({ requestId, ok: false, error: cleanError(error) });
  }
}

process.stdin.on("data", (chunk) => {
  input = Buffer.concat([input, chunk]);
  while (input.length >= 4) {
    const length = input.readUInt32LE(0);
    if (length > MAX_MESSAGE_BYTES) {
      send({ requestId: null, ok: false, error: "Native message exceeded the 8 MB safety limit" });
      process.exit(1);
    }
    if (input.length < length + 4) break;
    const body = input.subarray(4, length + 4);
    input = input.subarray(length + 4);
    try {
      dispatch(JSON.parse(body.toString("utf8")));
    } catch {
      send({ requestId: null, ok: false, error: "Native message was not valid JSON" });
    }
  }
});

process.stdin.on("end", () => process.exit(0));
