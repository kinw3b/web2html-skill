#!/usr/bin/env node
// Rename home-desktop inner layers to `h1 · …` / `p · …` from source-semantics.json
// so 2.2.b wrap matches the live tag census.

import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { importSibling } from "./skill-paths.mjs";
import { normalizeSemText, paperSemanticsName } from "./source-semantics.mjs";

const arg = (n, d) => {
  const i = process.argv.indexOf(`--${n}`);
  return i > -1 ? process.argv[i + 1] : d;
};

export function payload(result) {
  for (const item of result?.content ?? []) {
    if (item.type === "text") {
      try { return JSON.parse(item.text); } catch { return { text: item.text }; }
    }
  }
  return result || {};
}

export function childrenOf(raw) {
  if (Array.isArray(raw)) return raw;
  if (Array.isArray(raw?.children)) return raw.children;
  if (Array.isArray(raw?.nodes)) return raw.nodes;
  return [];
}

function norm(value) {
  return normalizeSemText(value).toLowerCase();
}

export function matchPaperNode(nodes, census) {
  const want = norm(census.text || census.alt);
  const tag = String(census.tag || "").toLowerCase();
  const scored = [];
  for (const node of nodes) {
    if (/^\d{2}\s*·/.test(node.name || "")) continue;
    if (new RegExp(`^${tag}\\s*·`, "i").test(node.name || "") && (!want || norm(node.name).includes(want.slice(0, 24)))) {
      return node;
    }
    const text = norm(node.textContent || node.name || "");
    const image = /image|img/i.test(node.component || "") || /image|img/i.test(node.name || "");
    if (tag === "img") {
      if (!image && !/photo|shot|media/i.test(node.name || "")) continue;
      if (!want) {
        scored.push({ node, score: Number(node.childCount || 0) === 0 ? 2 : 1 });
        continue;
      }
    }
    if (!text || !want) continue;
    if (text === want) scored.push({ node, score: Number(node.childCount || 0) === 0 ? 4 : 3 });
    else if (text.includes(want) || want.includes(text)) scored.push({ node, score: 1 });
  }
  scored.sort((a, b) => b.score - a.score);
  return scored[0]?.score >= 1 ? scored[0].node : null;
}

export async function walkPaperTree(call, rootId, { depth = 0, maxDepth = 10 } = {}) {
  if (!rootId || depth > maxDepth) return [];
  const raw = payload(await call("get_children", { nodeId: rootId }));
  const list = childrenOf(raw);
  const out = [];
  for (const node of list) {
    out.push(node);
    const count = Number(node.childCount || node.children?.length || 0);
    if (count > 0) out.push(...await walkPaperTree(call, node.id, { depth: depth + 1, maxDepth }));
  }
  return out;
}

export async function hydratePaperTexts(call, nodes) {
  const leaves = (nodes || []).filter((n) => {
    if (/^\d{2}\s*·/.test(n.name || "")) return false;
    if (n.textContent) return false;
    const textish = /text|image|img/i.test(n.component || "");
    return textish || Number(n.childCount || 0) === 0;
  });
  for (let i = 0; i < leaves.length; i += 8) {
    await Promise.all(leaves.slice(i, i + 8).map(async (n) => {
      try {
        const d = payload(await call("get_node_info", { nodeId: n.id }));
        n.textContent = d.textContent || n.textContent;
        n.component = d.component || n.component;
      } catch { /* Paper node vanished */ }
    }));
  }
  return nodes;
}

export async function applySemanticsToPaper({
  call,
  doc,
  artboard = "home-desktop",
  hydrate = true,
} = {}) {
  const info = payload(await call("get_basic_info", {}));
  const board = (info.artboards || []).find((a) => a.name === artboard)
    || (info.artboards || []).find((a) => String(a.name || "").includes(artboard));
  if (!board?.id) throw new Error(`no ${artboard} artboard`);
  const kids = childrenOf(payload(await call("get_children", { nodeId: board.id })));
  const sections = kids.filter((n) => /^\d{2}\s*·/.test(n.name || ""));
  const updates = [];
  const used = new Set();
  for (const section of doc.sections || []) {
    const frame = sections.find((n) => String(n.name).startsWith(`${section.id} ·`));
    if (!frame) continue;
    const tree = await walkPaperTree(call, frame.id);
    if (hydrate) await hydratePaperTexts(call, tree);
    for (const node of section.nodes || []) {
      const hit = matchPaperNode(tree.filter((n) => !used.has(n.id)), node);
      if (!hit) continue;
      const name = node.paperName || paperSemanticsName(node.tag, node.text || node.alt);
      used.add(hit.id);
      if (hit.name === name) continue;
      updates.push({ nodeId: hit.id, name });
    }
  }
  if (updates.length) {
    await call("rename_nodes", { updates });
    try { await call("finish_working_on_nodes", {}); } catch { /* optional */ }
  }
  return { artboard, renamed: updates.length, updates };
}

const isMain = process.argv[1]
  && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url;
if (isMain) {
  const FILE = arg("file", process.env.PAPER_FILE_ID || "");
  const JSON_PATH = path.resolve(arg("json", "capture/home-desktop/source-semantics.json"));
  const ARTBOARD = arg("artboard", "home-desktop");
  if (!FILE) {
    console.error("need --file <paperFileId>");
    process.exit(1);
  }
  if (!fs.existsSync(JSON_PATH)) {
    console.error(`missing ${JSON_PATH}`);
    process.exit(1);
  }
  const doc = JSON.parse(fs.readFileSync(JSON_PATH, "utf8"));
  const { call, setFileId } = await importSibling("url-to-paper", "scripts/mcp-client.mjs");
  setFileId(FILE);
  const result = await applySemanticsToPaper({ call, doc, artboard: ARTBOARD });
  console.error(`source-semantics → Paper ${result.artboard} · ${result.renamed} layer(s)`);
  console.log(JSON.stringify({ artboard: result.artboard, renamed: result.renamed }, null, 2));
}
