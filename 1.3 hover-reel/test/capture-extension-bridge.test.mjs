import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { applySemanticsToPaper } from "../capture-extension/bridge/semantics.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const hostPath = path.resolve(here, "..", "capture-extension", "bridge", "host.mjs");

function installMockFetch(projectRoot) {
  const loader = path.join(projectRoot, "mock-paper-fetch.mjs");
  const callsFile = path.join(projectRoot, "mock-paper-calls.jsonl");
  fs.writeFileSync(loader, `
    import fs from "node:fs";
    const artboards = [];
    let nodeSequence = 0;
    const mcpResult = (value) => ({ content: [{ type: "text", text: JSON.stringify(value) }] });
    globalThis.fetch = async (_url, options = {}) => {
      const message = JSON.parse(String(options.body || "{}"));
      const headers = { "content-type": "application/json", "mcp-session-id": "capture-extension-test" };
      if (!Object.hasOwn(message, "id")) return new Response("", { status: 202, headers });
      let result = {};
      if (message.method === "initialize") {
        result = { protocolVersion: "2025-06-18", capabilities: {}, serverInfo: { name: "mock-paper", version: "1" } };
      } else if (message.method === "tools/call") {
        const name = message.params.name;
        const args = message.params.arguments || {};
        fs.appendFileSync(process.env.HC_MOCK_CALLS, JSON.stringify({ name, args }) + "\\n");
        if (name === "get_basic_info") result = mcpResult({ artboards });
        else if (name === "create_artboard") {
          const board = { id: "board-" + (++nodeSequence), name: args.name, width: 1400, worldX: nodeSequence * 1500, worldY: 300 };
          artboards.push(board);
          result = mcpResult({ createdNodes: [board] });
        } else if (name === "write_html") {
          result = mcpResult({ createdNodes: [{ id: "node-" + (++nodeSequence) }] });
        } else result = mcpResult({});
      }
      return new Response(JSON.stringify({ jsonrpc: "2.0", id: message.id, result }), { status: 200, headers });
    };
  `, "utf8");
  return { loader, callsFile };
}

function nativeClient(process) {
  let input = Buffer.alloc(0);
  const waiters = new Map();
  process.stdout.on("data", (chunk) => {
    input = Buffer.concat([input, chunk]);
    while (input.length >= 4) {
      const length = input.readUInt32LE(0);
      if (input.length < length + 4) return;
      const message = JSON.parse(input.subarray(4, length + 4).toString("utf8"));
      input = input.subarray(length + 4);
      const waiter = waiters.get(message.requestId);
      if (waiter) {
        waiters.delete(message.requestId);
        waiter.resolve(message);
      }
    }
  });
  let sequence = 0;
  return (type, payload = {}) => {
    const requestId = `test-${++sequence}`;
    const body = Buffer.from(JSON.stringify({ requestId, type, ...payload }));
    const header = Buffer.alloc(4);
    header.writeUInt32LE(body.length);
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        waiters.delete(requestId);
        reject(new Error(`native host timeout: ${type}`));
      }, 5000);
      waiters.set(requestId, {
        resolve(message) { clearTimeout(timer); resolve(message); },
      });
      process.stdin.write(Buffer.concat([header, body]));
    });
  };
}

test("native bridge waits for a Paper node before returning a green-check receipt", async (t) => {
  const projectRoot = fs.mkdtempSync(path.join(os.tmpdir(), "paper-capture-bridge-test-"));
  const paper = installMockFetch(projectRoot);
  const host = spawn(process.execPath, [hostPath], {
    stdio: ["pipe", "pipe", "pipe"],
    env: {
      ...process.env,
      NODE_OPTIONS: `${process.env.NODE_OPTIONS || ""} --import=${paper.loader}`.trim(),
      HC_MOCK_CALLS: paper.callsFile,
    },
  });
  let stderr = "";
  host.stderr.setEncoding("utf8");
  host.stderr.on("data", (chunk) => { stderr += chunk; });
  t.after(async () => {
    host.stdin.end();
    host.kill();
    fs.rmSync(projectRoot, { recursive: true, force: true });
  });
  const request = nativeClient(host);

  const sessionFile = path.join(projectRoot, "active-session.json");
  fs.mkdirSync(path.join(projectRoot, "qa"), { recursive: true });
  fs.writeFileSync(path.join(projectRoot, "qa", "paper-file.json"), JSON.stringify({
    fileId: "paper-from-qa",
    url: "https://example.test/",
  }));
  fs.writeFileSync(sessionFile, JSON.stringify({ projectRoot }));
  const pingHost = spawn(process.execPath, [hostPath], {
    stdio: ["pipe", "pipe", "pipe"],
    env: { ...process.env, PAPER_CAPTURE_SESSION: sessionFile },
  });
  t.after(() => { pingHost.stdin.end(); pingHost.kill(); });
  const ping = await nativeClient(pingHost)("PING");
  assert.equal(ping.ok, true);
  assert.equal(ping.session.paperFileId, "paper-from-qa");
  assert.equal(ping.session.projectRoot, projectRoot);

  const started = await request("START_SESSION", {
    config: {
      paperFileId: "paper-file-test",
      projectRoot,
      paperEndpoint: "http://127.0.0.1:29979/mcp",
      sourceUrl: "https://example.test/",
    },
  });
  assert.equal(started.ok, true, stderr);
  assert.deepEqual(started.boards, ["Navigation", "Buttons", "Components"]);

  const committed = await request("COMMIT_TAKE", {
    take: {
      id: "navbar-test-1",
      mode: "nav",
      kind: "navbar",
      label: "Primary navigation",
      sectionId: "NAV",
      url: "https://example.test/",
      html: '<nav style="display:flex"><a href="https://example.test/">Home</a></nav>',
    },
  });
  assert.equal(committed.ok, true, stderr);
  assert.equal(committed.receipt.board, "Navigation");
  assert.match(committed.receipt.paperNodeId, /^node-/);
  const calls = fs.readFileSync(paper.callsFile, "utf8").trim().split("\n").map((line) => JSON.parse(line));
  assert.ok(calls.some((call) => call.name === "write_html" && call.args.targetNodeId === "board-1"));
  const takeWrite = calls.find((call) => call.name === "write_html"
    && call.args.targetNodeId === "board-1"
    && call.args.html.includes("Capture Extension · Primary navigation"));
  assert.ok(takeWrite, "expected the capture row HTML to be written to Navigation");
  assert.match(takeWrite.args.html, /layer-name="Capture Extension[^>]+width:fit-content/);
  assert.match(takeWrite.args.html, /background:#6F6F6F/);
  assert.doesNotMatch(takeWrite.args.html, /confirmed take/);
  assert.doesNotMatch(takeWrite.args.html, /width:1304px/);
  assert.doesNotMatch(takeWrite.args.html, /width:1600px/);

  const done = await request("COMPLETE_SESSION", {
    summary: { sourceUrl: "https://example.test/", takeCount: 1, boards: ["Navigation"] },
  });
  assert.equal(done.ok, true, stderr);
  const doneFile = path.join(projectRoot, "source-site", "components", "human-hover-done.json");
  assert.equal(fs.existsSync(doneFile), true);
  const receipt = JSON.parse(fs.readFileSync(doneFile, "utf8"));
  assert.deepEqual(receipt.boards, ["Navigation"]);
  assert.equal(receipt.takeCount, 1);
  const legacyWakeFile = path.join(projectRoot, "qa", "agent-pings", "1.3-continue.json");
  assert.equal(fs.existsSync(legacyWakeFile), false);
});

test("Tags Scan does not write enrich or rename home-desktop", () => {
  const host = fs.readFileSync(hostPath, "utf8");
  const panel = fs.readFileSync(path.resolve(here, "..", "capture-extension", "sidepanel", "panel.js"), "utf8");
  assert.match(host, /Tags Scan is removed; 1\.2 layer-ids\.json is the census/);
  assert.doesNotMatch(host, /applySemanticsToPaper/);
  assert.doesNotMatch(host, /layer-ids-enrich\.json/);
  assert.doesNotMatch(host, /function tagsHtml\(/);
  assert.doesNotMatch(panel, /nativeRequest\("APPLY_SEMANTICS"/);
  assert.doesNotMatch(panel, /HC_AUTO_TAGS/);
});

test("pc-id semantics rename the Paper node from paper-layer-ids, not leftover geometry", async () => {
  const renamed = [];
  const call = async (name, args) => {
    const result = (value) => ({ content: [{ type: "text", text: JSON.stringify(value) }] });
    if (name === "get_basic_info") return result({ artboards: [{ id: "desktop", name: "home-desktop" }] });
    if (name === "get_children") return result({ children: [{ id: "section", name: "01 · hero", childCount: 0 }] });
    if (name === "rename_nodes") { renamed.push(...args.updates); return result({}); }
    return result({});
  };
  const applied = await applySemanticsToPaper({
    call,
    doc: { sections: [{ id: "01", nodes: [{ tag: "h1", text: "Your Pet's Happy Place", pcId: "pc-01-0.2" }] }] },
    paperLayerIds: { ids: { "pc-01-0.2": "hero-h1" } },
  });
  assert.equal(applied.renamed, 1);
  assert.equal(applied.matchedByLayerId, 1);
  assert.deepEqual(renamed, [{ nodeId: "hero-h1", name: "h1 · Your Pet's Happy Place" }]);
});

test("interactive semantics rename the CTA container rather than its text leaf", async () => {
  const renamed = [];
  const call = async (name, args) => {
    const result = (value) => ({ content: [{ type: "text", text: JSON.stringify(value) }] });
    if (name === "get_basic_info") return result({ artboards: [{ id: "desktop", name: "home-desktop" }] });
    if (name === "get_children" && args.nodeId === "desktop") {
      return result({ children: [{ id: "section", name: "01 · hero", childCount: 1 }] });
    }
    if (name === "get_children" && args.nodeId === "section") {
      return result({ children: [{ id: "cta-outer", name: "Frame", component: "Frame", childCount: 1 }] });
    }
    if (name === "get_children" && args.nodeId === "cta-outer") {
      return result({ children: [{ id: "cta-layout", name: "Frame", component: "Frame", childCount: 1 }] });
    }
    if (name === "get_children" && args.nodeId === "cta-layout") {
      return result({ children: [{ id: "cta-frame", name: "Frame", component: "Frame", childCount: 1 }] });
    }
    if (name === "get_children" && args.nodeId === "cta-frame") {
      return result({ children: [{ id: "cta-label", name: "Free Consultation", component: "Text", childCount: 0 }] });
    }
    if (name === "get_node_info") return result({ textContent: "Free Consultation", component: "Text" });
    if (name === "rename_nodes") { renamed.push(...args.updates); return result({}); }
    return result({});
  };
  const applied = await applySemanticsToPaper({
    call,
    doc: { sections: [{ id: "01", nodes: [{ tag: "a", text: "Free Consultation" }] }] },
  });
  assert.equal(applied.renamed, 1);
  assert.deepEqual(renamed, [{ nodeId: "cta-outer", name: "a · Free Consultation" }]);
});

function paperTreeCall(tree, renamed) {
  return async (name, args) => {
    const result = (value) => ({ content: [{ type: "text", text: JSON.stringify(value) }] });
    if (name === "get_basic_info") return result({ artboards: [{ id: "desktop", name: "home-desktop" }] });
    if (name === "get_children") return result({ children: tree[args.nodeId] || [] });
    if (name === "get_node_info") {
      const node = Object.values(tree).flat().find((item) => item.id === args.nodeId);
      return result({ textContent: node?.textContent || node?.name || "", component: node?.component || "" });
    }
    if (name === "rename_nodes") { renamed.push(...args.updates); return result({}); }
    return result({});
  };
}

test("a second Tags scan does not climb from an already-named CTA onto pc-id parents", async () => {
  const renamed = [];
  const tree = {
    desktop: [{ id: "section", name: "01 · hero", childCount: 1 }],
    section: [{ id: "column", name: "a · Book A Schedule", component: "Frame", childCount: 2 }],
    column: [
      { id: "heading", name: "h1 · Your Pet's Happy Place on Earth.", component: "Text", childCount: 0, textContent: "Your Pet's Happy Place on Earth." },
      { id: "cta", name: "a · Book A Schedule", component: "Frame", childCount: 1 },
    ],
    cta: [{ id: "label", name: "Book A Schedule", component: "Text", childCount: 0, textContent: "Book A Schedule" }],
  };
  const applied = await applySemanticsToPaper({
    call: paperTreeCall(tree, renamed),
    doc: { sections: [{ id: "01", nodes: [{ tag: "a", text: "Book A Schedule", paperName: "a · Book A Schedule" }] }] },
  });
  assert.equal(applied.renamed, 0);
  assert.deepEqual(renamed, []);
});

test("leftover interactive climb must not rename a foreign pc-id parent", async () => {
  const renamed = [];
  const tree = {
    desktop: [{ id: "section", name: "01 · hero", childCount: 1 }],
    section: [{ id: "column", name: "pc-0.0.1.0", component: "Frame", childCount: 2 }],
    column: [
      { id: "heading", name: "pc-0.0.1.0.0", component: "Text", childCount: 0, textContent: "Your Pet's Happy Place on Earth." },
      { id: "cta", name: "Frame", component: "Frame", childCount: 1 },
    ],
    cta: [{ id: "label", name: "Book A Schedule", component: "Text", childCount: 0, textContent: "Book A Schedule" }],
  };
  const applied = await applySemanticsToPaper({
    call: paperTreeCall(tree, renamed),
    doc: { sections: [{ id: "01", nodes: [{ tag: "a", text: "Book A Schedule" }] }] },
  });
  assert.equal(applied.renamed, 1);
  assert.deepEqual(renamed, [{ nodeId: "cta", name: "a · Book A Schedule" }]);
});
