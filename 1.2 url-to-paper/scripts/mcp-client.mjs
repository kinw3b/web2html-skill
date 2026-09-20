// Minimal Paper MCP (streamable HTTP) client, shared by the other scripts.
// Exists so the skill works even when the session was started before the MCP
// was registered and `mcp__paper__*` tools aren't in the tool registry.

const ENDPOINT = process.env.PAPER_MCP || "http://127.0.0.1:29979/mcp";
/** Hard ceiling so a wedged Paper write_html cannot lock Capture Tool forever. */
const DEFAULT_TIMEOUT_MS = Number(process.env.PAPER_MCP_TIMEOUT_MS || 90_000);
let sessionId = null;

function parseSSE(text) {
  const out = [];
  for (const line of text.split(/\r?\n/)) {
    if (!line.startsWith("data:")) continue;
    const raw = line.slice(5).trim();
    if (!raw || raw === "[DONE]") continue;
    try { out.push(JSON.parse(raw)); } catch {}
  }
  if (!out.length && text.trim().startsWith("{")) {
    try { out.push(JSON.parse(text)); } catch {}
  }
  return out;
}

export async function rpc(method, params, { notify = false, timeoutMs = DEFAULT_TIMEOUT_MS } = {}) {
  const headers = {
    "Content-Type": "application/json",
    Accept: "application/json, text/event-stream",
  };
  if (sessionId) headers["mcp-session-id"] = sessionId;

  const body = notify
    ? { jsonrpc: "2.0", method, params }
    : { jsonrpc: "2.0", id: Math.floor(Math.random() * 1e6) + 1, method, params };

  const ms = Number.isFinite(timeoutMs) && timeoutMs > 0 ? timeoutMs : DEFAULT_TIMEOUT_MS;
  const ac = new AbortController();
  const timer = setTimeout(() => ac.abort(), ms);
  let res;
  let text = "";
  try {
    res = await fetch(ENDPOINT, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      signal: ac.signal,
    });
    const sid = res.headers.get("mcp-session-id");
    if (sid) sessionId = sid;
    if (notify) return null;
    text = await res.text();
  } catch (err) {
    if (err?.name === "AbortError") {
      throw new Error(
        `Paper MCP timed out after ${ms}ms (${method}). Paper may be wedged on a large write_html — retry or skip.`,
      );
    }
    throw new Error(
      `Cannot reach Paper MCP at ${ENDPOINT}. Is Paper Desktop running with a file open? (${err.message})`,
    );
  } finally {
    clearTimeout(timer);
  }

  const reply = parseSSE(text).find((m) => m.result || m.error);
  if (!reply) throw new Error(`No JSON-RPC reply. Raw:\n${text.slice(0, 500)}`);
  if (reply.error) throw new Error(`MCP error: ${JSON.stringify(reply.error)}`);
  return reply.result;
}

let connected = false;
export async function connect() {
  if (connected) return;
  await rpc("initialize", {
    protocolVersion: "2025-06-18",
    capabilities: {},
    clientInfo: { name: "url-to-paper", version: "1.0" },
  });
  await rpc("notifications/initialized", {}, { notify: true });
  connected = true;
}

// Paper routes tool calls to a "sticky" active file. That is racy: if the user
// clicks another file in the Paper UI mid-run, subsequent calls silently target
// the WRONG document. Observed: an extraction run mined "Welcome to Paper"
// instead of the site file. Pin a fileId and every call carries it explicitly.
let pinnedFileId = process.env.PAPER_FILE_ID || null;

export function setFileId(id) {
  pinnedFileId = id || null;
}

export function getFileId() {
  return pinnedFileId;
}

export async function call(name, args = {}, { pinFile = true, timeoutMs } = {}) {
  await connect();
  const withFile =
    pinFile && pinnedFileId && args.fileId === undefined ? { ...args, fileId: pinnedFileId } : args;
  // Heavy HTML inserts need more headroom; still fail closed so the HUD unlocks.
  const toolTimeout = timeoutMs
    ?? (name === "write_html" ? Math.max(DEFAULT_TIMEOUT_MS, 120_000) : DEFAULT_TIMEOUT_MS);
  return rpc("tools/call", { name, arguments: withFile }, { timeoutMs: toolTimeout });
}

export async function listTools() {
  await connect();
  const { tools } = await rpc("tools/list", {});
  return tools;
}
