function payload(result) {
  for (const item of result?.content || []) {
    if (item.type !== "text") continue;
    try { return JSON.parse(item.text); } catch { return { text: item.text }; }
  }
  return result || {};
}

function childrenOf(raw) {
  if (Array.isArray(raw)) return raw;
  if (Array.isArray(raw?.children)) return raw.children;
  if (Array.isArray(raw?.nodes)) return raw.nodes;
  return [];
}

function norm(value) {
  return String(value || "").replace(/\s+/g, " ").trim().toLowerCase();
}

function semanticName(node) {
  const tag = String(node.tag || "div").toLowerCase();
  const label = String(node.text || node.alt || tag).replace(/\s+/g, " ").trim().slice(0, 48) || tag;
  return `${tag} · ${label}`;
}

export function isSemanticLayerName(name) {
  return /^(h[1-6]|p|ul|ol|img|a|button|form)\s*·/i.test(String(name || ""));
}

export function canRenamePaperNode(hit, semantic) {
  if (!hit) return false;
  const name = String(hit.name || "");
  const want = semantic?.paperName || semanticName(semantic || {});
  if (name === want) return false;
  if (/^\d{2}\s*·/.test(name)) return false;
  if (/^pc-/.test(name)) {
    const pcId = String(semantic?.pcId || "").trim();
    return Boolean(pcId) && (name === pcId || hit.pcId === pcId);
  }
  return true;
}

function paperIdMap(paperLayerIds) {
  if (!paperLayerIds) return {};
  if (paperLayerIds.ids && typeof paperLayerIds.ids === "object") return paperLayerIds.ids;
  return paperLayerIds;
}

export function matchPaperNode(nodes, census) {
  const list = nodes || [];
  const pcId = String(census.pcId || "").trim();
  if (pcId) {
    const exact = list.find((node) => node.name === pcId || node.pcId === pcId);
    if (exact) return exact;
  }
  const want = norm(census.text || census.alt);
  const tag = String(census.tag || "").toLowerCase();
  const targetName = census.paperName || semanticName({ tag, text: census.text, alt: census.alt });
  // Deepest exact name wins. A second Scan used to return the outermost
  // stolen `a · …` ancestor and then climb again (Pitfall #155).
  let already = null;
  for (const node of list) {
    if (node.name === targetName) already = node;
  }
  if (already) return already;
  const scored = [];
  for (const node of list) {
    if (/^\d{2}\s*·/.test(node.name || "")) continue;
    const text = norm(node.textContent || node.name || "");
    const image = /image|img/i.test(node.component || "") || /image|img/i.test(node.name || "");
    if (tag === "img") {
      if (!image && !/photo|shot|media/i.test(node.name || "")) continue;
      if (!want) scored.push({ node, score: Number(node.childCount || 0) === 0 ? 2 : 1 });
      continue;
    }
    if (!text || !want) continue;
    if (text === want) scored.push({ node, score: Number(node.childCount || 0) === 0 ? 4 : 3 });
    else if (text.includes(want) || want.includes(text)) scored.push({ node, score: 1 });
  }
  scored.sort((a, b) => b.score - a.score);
  return scored[0]?.score >= 1 ? scored[0].node : null;
}

async function walkPaperTree(call, rootId, depth = 0) {
  if (!rootId || depth > 10) return [];
  const list = childrenOf(payload(await call("get_children", { nodeId: rootId })));
  const out = [];
  for (const node of list) {
    node.parentId = rootId;
    out.push(node);
    if (Number(node.childCount || node.children?.length || 0) > 0) {
      out.push(...await walkPaperTree(call, node.id, depth + 1));
    }
  }
  return out;
}

function interactiveContainer(hit, nodes, tag, { pcId } = {}) {
  if (!hit || !["a", "button"].includes(tag)) return hit;
  if (isSemanticLayerName(hit.name)) return hit;
  const byId = new Map(nodes.map((node) => [node.id, node]));
  const blocked = (node) => {
    if (!node) return true;
    if (/^\d{2}\s*·/.test(node.name || "")) return true;
    if (isSemanticLayerName(node.name)) return true;
    return /^pc-/.test(node.name || "") && node.name !== pcId;
  };
  let current = hit;
  let component = hit;
  while (current?.parentId) {
    const parent = byId.get(current.parentId);
    if (!parent || blocked(parent)) break;
    const textLayer = /text|richtext/i.test(parent.component || "");
    if (!textLayer && Number(parent.childCount || parent.children?.length || 0) > 0) {
      component = parent;
      break;
    }
    current = parent;
  }
  current = component;
  while (current?.parentId) {
    const parent = byId.get(current.parentId);
    if (!parent || blocked(parent)) break;
    if (Number(parent.childCount || parent.children?.length || 0) !== 1) break;
    current = parent;
  }
  return current;
}

async function hydratePaperTexts(call, nodes) {
  const leaves = nodes.filter((node) => !node.textContent
    && !/^\d{2}\s*·/.test(node.name || "")
    && (/text|image|img/i.test(node.component || "") || Number(node.childCount || 0) === 0));
  for (let index = 0; index < leaves.length; index += 8) {
    await Promise.all(leaves.slice(index, index + 8).map(async (node) => {
      try {
        const info = payload(await call("get_node_info", { nodeId: node.id }));
        node.textContent = info.textContent || node.textContent;
        node.component = info.component || node.component;
      } catch { /* Paper node changed during the scan */ }
    }));
  }
}

export async function applySemanticsToPaper({ call, doc, artboard = "home-desktop", paperLayerIds } = {}) {
  const info = payload(await call("get_basic_info", {}));
  const board = (info.artboards || []).find((item) => item.name === artboard)
    || (info.artboards || []).find((item) => String(item.name || "").includes(artboard));
  if (!board?.id) throw new Error(`No ${artboard} artboard exists in Paper`);
  const children = childrenOf(payload(await call("get_children", { nodeId: board.id })));
  const sections = children.filter((node) => /^\d{2}\s*·/.test(node.name || ""));
  const updates = [];
  const used = new Set();
  const scanned = (doc.sections || []).reduce((count, section) => count + (section.nodes || []).length, 0);
  const missingSections = [];
  const paperByPc = paperIdMap(paperLayerIds);
  let matchedByLayerId = 0;
  const queueRename = (nodeId, semantic) => {
    if (!nodeId || used.has(nodeId)) return false;
    used.add(nodeId);
    const name = semantic.paperName || semanticName(semantic);
    updates.push({ nodeId, name });
    return true;
  };
  for (const section of doc.sections || []) {
    const frame = sections.find((node) => String(node.name || "").startsWith(`${section.id} ·`));
    const leftovers = [];
    for (const semantic of section.nodes || []) {
      const mapped = semantic.pcId ? paperByPc[semantic.pcId] : null;
      const nodeId = typeof mapped === "string" ? mapped : mapped?.id;
      if (nodeId && queueRename(nodeId, semantic)) {
        matchedByLayerId += 1;
        continue;
      }
      leftovers.push(semantic);
    }
    if (!leftovers.length) continue;
    if (!frame) {
      missingSections.push(section.id);
      continue;
    }
    const tree = await walkPaperTree(call, frame.id);
    await hydratePaperTexts(call, tree);
    for (const semantic of leftovers) {
      const name = semantic.paperName || semanticName(semantic);
      let hit = matchPaperNode(tree.filter((node) => !used.has(node.id)), semantic);
      if (!hit) continue;
      if (semantic.pcId && (hit.name === semantic.pcId || hit.pcId === semantic.pcId)) {
        matchedByLayerId += 1;
      } else if (hit.name !== name && !isSemanticLayerName(hit.name)) {
        const promoted = interactiveContainer(hit, tree, String(semantic.tag || "").toLowerCase(), {
          pcId: semantic.pcId,
        });
        hit = canRenamePaperNode(promoted, semantic) ? promoted
          : canRenamePaperNode(hit, semantic) ? hit
          : null;
      }
      if (!hit || used.has(hit.id)) continue;
      used.add(hit.id);
      if (hit.name !== name && canRenamePaperNode(hit, semantic)) {
        updates.push({ nodeId: hit.id, name });
      }
    }
  }
  if (updates.length) {
    await call("rename_nodes", { updates });
    try { await call("finish_working_on_nodes", {}); } catch { /* optional Paper cleanup */ }
  }
  return {
    artboard,
    scanned,
    sourceSections: (doc.sections || []).length,
    missingSections,
    matched: used.size,
    matchedByLayerId,
    renamed: updates.length,
    updates,
  };
}
