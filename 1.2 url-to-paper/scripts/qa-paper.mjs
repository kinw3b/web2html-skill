#!/usr/bin/env node
// Mechanical QA pass over imported Paper artboards.
//
// Catches the failure modes an import actually produces — clipped content,
// zero-size nodes, overlapping siblings, dead gaps, empty frames, split
// Framer line-box headings (Pitfall #69), full-bleed overlays covering type
// (Pitfall #84) — using node geometry from the MCP.
// This is the part a design-critique skill CANNOT do: it needs real
// coordinates, not a screenshot. Repair split titles with
// merge-split-headings.mjs (detect + auto-fix). `split-heading` is high
// and fails Stage P / A/5.
//
// Pair it with a visual pass (screenshots + Paper's Review Checkpoints).
//
// Usage:
//   node qa-paper.mjs [--depth 2] [--artboard <id>] [--gap 240]
//                     [--shots out/] [--json qa-report.json]

import { mkdirSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { call } from "./mcp-client.mjs";
import {
  emptyImageDetail,
  emptyImageKind,
  findBreakpointImageGaps,
  isEmptyImageSlot,
  sectionSlug,
} from "./qa-breakpoint-images.mjs";
import { collectNodes, findSplitHeadings } from "./merge-split-headings.mjs";
import { findOverlayPaintOrderIssues } from "./overlay-paint-order.mjs";
import {
  isPaperTextNode,
  isUnboundFontFamily,
  normalizeTokens,
} from "./library-tokens.mjs";

const argv = process.argv.slice(2);
const arg = (name, fallback) => {
  const i = argv.indexOf(`--${name}`);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : fallback;
};

const maxDepth = parseInt(arg("depth", "4"), 10);
const gapLimit = parseInt(arg("gap", "240"), 10);
const onlyArtboard = arg("artboard");
const shotsDir = arg("shots");
const jsonOut = arg("json", "qa-report.json");
const log = (...a) => console.error("·", ...a);

// Artboard names are user-facing labels and may contain `/` (for example the
// pipeline's `A/6 · home · Navbar states`). Keep the label legible in the QA
// evidence directory without allowing it to become a nested path.
function screenshotFileName(name) {
  const safe = String(name)
    .normalize("NFKC")
    .replace(/[\\/]/g, "∕")
    .replace(/[\u0000-\u001F<>:"|?*]/g, "-")
    .replace(/\.+$/g, "")
    .trim();
  return `${safe || "artboard"}.jpg`;
}

function payload(result) {
  for (const item of result.content ?? []) {
    if (item.type === "text") {
      try { return JSON.parse(item.text); } catch { return { text: item.text }; }
    }
  }
  return {};
}

const num = (v) => {
  if (typeof v === "number") return v;
  if (typeof v === "string") { const n = parseFloat(v); return Number.isNaN(n) ? null : n; }
  return null;
};

const info = payload(await call("get_basic_info", {}));
let artboards = info.artboards || [];
if (onlyArtboard) artboards = artboards.filter((a) => a.id === onlyArtboard || a.name === onlyArtboard);
if (!artboards.length) {
  console.error("no artboards found on the active page");
  process.exit(1);
}
log(`QA over ${artboards.length} artboard(s) in "${info.fileName}" / ${info.pageName}`);

let fontTokens = [];
try {
  fontTokens = normalizeTokens(payload(await call("get_tokens", {})))
    .filter((t) => t.type === "fontFamily");
  if (fontTokens.length) log(`${fontTokens.length} fontFamily token(s)`);
} catch (err) {
  log(`get_tokens skipped: ${String(err.message || err).split("\n")[0]}`);
}

// ---- collect geometry, one get_children per node, one styles batch per level ----
async function collectLevels(rootId, rootMeta) {
  const nodes = new Map();
  nodes.set(rootId, { id: rootId, ...rootMeta, depth: 0, parentId: null });

  let frontier = [rootId];
  for (let d = 0; d < maxDepth; d++) {
    const next = [];
    for (const pid of frontier) {
      let kids;
      try {
        kids = payload(await call("get_children", { nodeId: pid })).children || [];
      } catch {
        continue;
      }
      const parent = nodes.get(pid);
      parent.childIds = kids.map((k) => k.id);
      for (const k of kids) {
        nodes.set(k.id, {
          id: k.id,
          name: k.name,
          component: k.component,
          childCount: k.childCount,
          worldX: k.worldX,
          worldY: k.worldY,
          depth: d + 1,
          parentId: pid,
        });
        if (k.childCount > 0) next.push(k.id);
      }
    }
    if (!next.length) break;
    frontier = next;
  }

  const ids = [...nodes.keys()];

  // Geometry MUST come from get_node_info. get_computed_styles returns only
  // AUTHORED styles — an auto-sized frame comes back as {flexShrink:"0"} with
  // no width/height at all, which silently skips every geometric check.
  // Measured: styles-only resolved 12 of 50 nodes.
  const CONCURRENCY = 8;
  for (let i = 0; i < ids.length; i += CONCURRENCY) {
    const chunk = ids.slice(i, i + CONCURRENCY);
    await Promise.all(chunk.map(async (id) => {
      if (id === rootId) return; // artboard geometry already known
      try {
        const d = payload(await call("get_node_info", { nodeId: id }));
        const n = nodes.get(id);
        if (!n) return;
        n.w = num(d.width);
        n.h = num(d.height);
        if (d.worldX != null) n.worldX = d.worldX;
        if (d.worldY != null) n.worldY = d.worldY;
        n.isVisible = d.isVisible;
        n.textContent = d.textContent;
      } catch {}
    }));
  }

  // Styles are still useful for paint/clip decisions — best effort only.
  for (let i = 0; i < ids.length; i += 60) {
    try {
      const styles = payload(await call("get_computed_styles", { nodeIds: ids.slice(i, i + 60) })).styles || {};
      for (const [id, s] of Object.entries(styles)) {
        const n = nodes.get(id);
        if (!n) continue;
        n.bg = s.backgroundColor;
        n.overflow = s.overflow;
        n.position = s.position;
        n.display = s.display;
        n.fontSize = s.fontSize;
        n.fontFamily = s.fontFamily;
        n.fontWeight = s.fontWeight;
        n.color = s.color;
        n.textAlign = s.textAlign;
        n.maxWidth = s.maxWidth;
        n.alignItems = s.alignItems;
        n.widthStyle = s.width;
        n.borderWidth = s.borderWidth;
        n.borderTopWidth = s.borderTopWidth;
        n.borderRightWidth = s.borderRightWidth;
        n.borderBottomWidth = s.borderBottomWidth;
        n.borderLeftWidth = s.borderLeftWidth;
        n.top = s.top;
        n.right = s.right;
        n.bottom = s.bottom;
        n.left = s.left;
        n.inset = s.inset;
        n.opacity = s.opacity;
        n.borderRadius = s.borderRadius;
      }
    } catch {}
  }
  return nodes;
}

const findings = [];
const add = (f) => findings.push(f);
const boardStats = [];
// Coverage counters — a QA pass reporting "clean" is only meaningful if it
// actually resolved geometry for the nodes it walked.
const coverage = { scanned: 0, withGeometry: 0 };

for (const ab of artboards) {
  log(`  scanning ${ab.name} …`);
  const nodes = await collectLevels(ab.id, {
    name: ab.name,
    component: "Artboard",
    worldX: ab.worldX,
    worldY: ab.worldY,
    childCount: ab.childCount,
    w: ab.width,
    h: ab.height,
  });

  const box = (n) =>
    n.w != null && n.h != null && n.worldX != null && n.worldY != null
      ? { x: n.worldX, y: n.worldY, w: n.w, h: n.h, r: n.worldX + n.w, b: n.worldY + n.h }
      : null;

  for (const n of nodes.values()) {
    const b = box(n);
    coverage.scanned++;
    if (b) coverage.withGeometry++;

    const parentEarly = n.parentId ? nodes.get(n.parentId) : null;

    // 0. unbound font — System Sans-Serif / generic / CSS stack (Pitfall #89)
    const onLibrary = /^Design Library$/i.test(ab.name);
    if ((fontTokens.length || onLibrary) && isPaperTextNode(n) && isUnboundFontFamily(n.fontFamily)) {
      add({
        artboard: ab.name,
        type: "unbound-font",
        severity: "high",
        node: n.id,
        name: n.name,
        detail: `fontFamily=${n.fontFamily || "(empty)"} — System Sans-Serif / generic / CSS stack while font tokens exist`,
      });
    }

    // 1. zero-size — SVG/path text at 0×0 is a named miss (prior-run badge)
    if (b && (b.w === 0 || b.h === 0) && n.component !== "Artboard") {
      const parentSvg = parentEarly && /svg/i.test(`${parentEarly.component || ""} ${parentEarly.name || ""}`);
      const looksText = /text/i.test(`${n.component || ""} ${n.name || ""}`);
      add({
        artboard: ab.name,
        type: parentSvg && looksText ? "dead-svg-text" : "zero-size",
        severity: "high",
        node: n.id,
        name: n.name,
        detail: `${b.w}×${b.h}${parentSvg && looksText ? " SVG text — replace with scrape PNG (1.5 comment)" : ""}`,
      });
      continue;
    }

    // 1b. hidden Framer variant towers (prior-run 768)
    if (b && b.w <= 2 && b.h > 800) {
      add({
        artboard: ab.name,
        type: "hidden-variant-stack",
        severity: "high",
        node: n.id,
        name: n.name,
        detail: `${Math.round(b.w)}×${Math.round(b.h)} — collapse before 1.5`,
      });
    }

    // 2. empty frame — takes space, holds nothing, paints nothing
    if (b && n.childCount === 0 && n.component === "Frame" && b.w > 40 && b.h > 40) {
      const painted = n.bg && n.bg !== "transparent" && !/rgba\(0, ?0, ?0, ?0\)/.test(n.bg);
      const named = /^\d{2}\s*·/.test(String(n.name || ""));
      if (!painted) {
        add({
          artboard: ab.name,
          type: named ? "empty-named-section" : "empty-frame",
          severity: named ? "high" : "low",
          node: n.id,
          name: n.name,
          detail: `${Math.round(b.w)}×${Math.round(b.h)} with no children and no fill${named ? " — restore capture HTML, do not delete (1.5)" : ""}`,
        });
      }
    }

    const parent = n.parentId ? nodes.get(n.parentId) : null;
    const pb = parent ? box(parent) : null;

    // 2a. empty photo slot — hollow Rectangle, deferred-image, avatar overlay
    const imageKind = b ? emptyImageKind({ ...n, w: b.w, h: b.h }, parent) : null;
    if (imageKind) {
      add({
        artboard: ab.name,
        type: "empty-image",
        severity: "high",
        node: n.id,
        name: n.name,
        parent: parent?.name,
        detail: emptyImageDetail({ ...n, w: b.w, h: b.h }, imageKind),
      });
    }

    // 2b. decorative abs overlay — frozen 1px stroke / fill that should be parent CSS
    if (b && (n.position === "absolute" || n.position === "fixed") && (n.childCount || 0) === 0 && !n.textContent) {
      const stroke = Math.max(
        parseFloat(n.borderWidth) || 0,
        parseFloat(n.borderTopWidth) || 0,
        parseFloat(n.borderRightWidth) || 0,
        parseFloat(n.borderBottomWidth) || 0,
        parseFloat(n.borderLeftWidth) || 0,
      );
      const insetZeros = [n.top, n.right, n.bottom, n.left].filter((v) => parseFloat(v) === 0).length;
      const covers = pb && Math.abs(b.w - pb.w) <= 4 && Math.abs(b.h - pb.h) <= 4;
      if (stroke > 0 && stroke <= 2 && b.w > 8 && b.h > 8 && (insetZeros >= 3 || covers)) {
        add({
          artboard: ab.name,
          type: "abs-decoration",
          severity: "high",
          node: n.id,
          name: n.name,
          parent: parent?.name,
          detail: `empty ${Math.round(b.w)}×${Math.round(b.h)} abs ${stroke}px stroke — hoist onto parent CSS (border) and delete`,
        });
      }
    }

    // 3. overflow past parent — the clipped-content case
    if (b && pb && parent.overflow !== "visible") {
      const overRight = Math.round(b.r - pb.r);
      const overBottom = Math.round(b.b - pb.b);
      if (overRight > 2 || overBottom > 2) {
        const dirs = [];
        if (overRight > 2) dirs.push(`${overRight}px past the right edge`);
        if (overBottom > 2) dirs.push(`${overBottom}px past the bottom`);
        add({ artboard: ab.name, type: "overflow", severity: parent.component === "Artboard" ? "high" : "medium",
              node: n.id, name: n.name, parent: parent.name,
              detail: `extends ${dirs.join(" and ")} of parent "${parent.name}" (clipped)` });
      }
    }
  }

  // 4. sibling overlap + 5. dead gaps, per parent
  for (const n of nodes.values()) {
    if (!n.childIds || n.childIds.length < 2) continue;
    const kids = n.childIds.map((id) => nodes.get(id)).filter((k) => k && k.w != null && k.h != null);
    const flow = kids.filter((k) => k.position !== "absolute" && k.position !== "fixed");

    for (let i = 0; i < flow.length; i++) {
      for (let j = i + 1; j < flow.length; j++) {
        const a = flow[i], c = flow[j];
        const ox = Math.min(a.worldX + a.w, c.worldX + c.w) - Math.max(a.worldX, c.worldX);
        const oy = Math.min(a.worldY + a.h, c.worldY + c.h) - Math.max(a.worldY, c.worldY);
        if (ox > 2 && oy > 2) {
          add({ artboard: ab.name, type: "overlap", severity: "medium",
                node: a.id, name: a.name, other: c.name,
                detail: `overlaps sibling "${c.name}" by ${Math.round(ox)}×${Math.round(oy)}px` });
        }
      }
    }

    // Vertical stacks only — a big gap between consecutive rows reads as a hole.
    const col = [...flow].sort((a, c) => a.worldY - c.worldY);
    for (let i = 1; i < col.length; i++) {
      const prev = col[i - 1], cur = col[i];
      const gap = Math.round(cur.worldY - (prev.worldY + prev.h));
      if (gap > gapLimit) {
        add({ artboard: ab.name, type: "gap", severity: "low",
              node: cur.id, name: cur.name,
              detail: `${gap}px empty space above (after "${prev.name}")` });
      }
    }
  }

  // 5b. full-bleed abs overlay after type (Pitfall #84)
  if (!String(ab.name || "").endsWith(" — source screenshot")) {
    for (const hit of findOverlayPaintOrderIssues(nodes, { artboard: ab.name })) add(hit);
  }

  // Per-section image counts for cross-breakpoint compare (Pitfall #58)
  if (!String(ab.name || "").endsWith(" — source screenshot")) {
    const rootNode = nodes.get(ab.id);
    const sectionIds = rootNode?.childIds || [];
    const sections = [];
    for (const id of sectionIds) {
      const sec = nodes.get(id);
      if (!sec) continue;
      let filledImages = 0;
      let emptyImageSlots = 0;
      for (const n of nodes.values()) {
        if (n.id === ab.id) continue;
        let cur = n;
        let owned = n.id === sec.id;
        while (!owned && cur?.parentId) {
          if (cur.parentId === sec.id) { owned = true; break; }
          if (cur.parentId === ab.id) break;
          cur = nodes.get(cur.parentId);
        }
        if (!owned) continue;
        if (n.component === "Image") filledImages++;
        if (isEmptyImageSlot(n)) emptyImageSlots++;
      }
      sections.push({ slug: sectionSlug(sec.name), filledImages, emptyImageSlots });
    }
    boardStats.push({ name: ab.name, width: ab.width, sections });
  }

  // 6. frozen section roots — capture px that will not follow a stretched frame
  if (!String(ab.name || "").endsWith(" — source screenshot")) {
    const rootNode = nodes.get(ab.id);
    const sectionIds = rootNode?.childIds || [];
    for (const id of sectionIds) {
      const n = nodes.get(id);
      if (!n) continue;
      const authored = String(n.widthStyle || "");
      const px = num(authored);
      if (authored.includes("%")) continue;
      if (px != null && Math.abs(px - ab.width) <= 2) {
        add({
          artboard: ab.name,
          type: "frozen-root",
          severity: "high",
          node: n.id,
          name: n.name,
          detail: `section width is ${authored}; stretching the artboard will leave a short band. Run stretch-root.mjs (A/5-R).`,
        });
      }
    }
  }

  // 6b. nested chrome — Framer header>header>nav imported as sibling navbars
  if (!String(ab.name || "").endsWith(" — source screenshot")) {
    const rootNode = nodes.get(ab.id);
    const kids = (rootNode?.childIds || []).map((id) => nodes.get(id)).filter(Boolean);
    const chromeKids = kids.filter((k) => {
      const n = String(k.name || "").toLowerCase();
      return /(^|\s|·\s)(header|nav|site-chrome)(-\d+)?$/.test(n) || n === "nav";
    });
    if (chromeKids.length > 1) {
      add({
        artboard: ab.name,
        type: "nested-chrome",
        severity: "high",
        node: chromeKids[1].id,
        name: chromeKids.map((k) => k.name).join(", "),
        detail: `${chromeKids.length} chrome siblings in one frame (keep outermost header only). Pitfall #51.`,
      });
    }
    for (const k of kids) {
      if (k.position === "absolute" || k.position === "fixed") continue;
      if (k.w == null || !ab.width) continue;
      if (k.w < ab.width * 0.9) {
        add({
          artboard: ab.name,
          type: "narrow-section",
          severity: "high",
          node: k.id,
          name: k.name,
          detail: `section is ${Math.round(k.w)}px on a ${Math.round(ab.width)}px artboard — set width: 100% (Pitfall #51).`,
        });
      }
    }
  }

  // 6c. section Clip content / Height Fit that still shears children (Pitfall #55)
  if (!String(ab.name || "").endsWith(" — source screenshot")) {
    const rootNode = nodes.get(ab.id);
    const sectionIds = new Set(rootNode?.childIds || []);
    const enclosingSection = (node) => {
      let cur = node;
      while (cur?.parentId) {
        const p = nodes.get(cur.parentId);
        if (!p) return null;
        if (p.id === ab.id || p.component === "Artboard") return cur;
        cur = p;
      }
      return null;
    };
    for (const id of sectionIds) {
      const n = nodes.get(id);
      if (!n) continue;
      const ov = String(n.overflow || "").toLowerCase().trim();
      if (ov && ov !== "visible") {
        add({
          artboard: ab.name,
          type: "clip-content",
          severity: "high",
          node: n.id,
          name: n.name,
          detail: `section overflow is ${ov}. Uncheck Clip content. Height Fit is not a waiver if a photo or dashboard is sheared at the frame edge.`,
        });
      }
    }
    for (const n of nodes.values()) {
      if (sectionIds.has(n.id) || n.id === ab.id) continue;
      const section = enclosingSection(n);
      if (!section || !sectionIds.has(section.id)) continue;
      const sectionOverflow = String(section.overflow || "").toLowerCase().trim();
      if (!sectionOverflow || sectionOverflow === "visible") continue;
      const b = box(n);
      const sb = box(section);
      if (!b || !sb) continue;
      const overRight = Math.round(b.r - sb.r);
      const overBottom = Math.round(b.b - sb.b);
      const isAbs = n.position === "absolute" || n.position === "fixed";
      const thresh = isAbs ? 24 : 2;
      if (overRight > thresh || overBottom > thresh) {
        const dirs = [];
        if (overRight > thresh) dirs.push(`${overRight}px past the right`);
        if (overBottom > thresh) dirs.push(`${overBottom}px past the bottom`);
        add({
          artboard: ab.name,
          type: "clipped-section",
          severity: "high",
          node: n.id,
          name: n.name,
          parent: section.name,
          detail: `"${n.name}" extends ${dirs.join(" and ")} of section "${section.name}". Grow Fit height and uncheck Clip content until the full asset paints.`,
        });
      }
    }
  }

  // 6d. Framer line-box titles split into stacked Text siblings (Pitfall #69)
  if (!String(ab.name || "").endsWith(" — source screenshot")) {
    let headingNodes = nodes;
    try {
      headingNodes = await collectNodes(call, ab.id, {
        name: ab.name,
        component: "Artboard",
        worldX: ab.worldX,
        worldY: ab.worldY,
        childCount: ab.childCount,
        w: ab.width,
        h: ab.height,
      });
    } catch (err) {
      log(`  split-heading walk failed: ${String(err.message || err).split("\n")[0]}`);
    }
    for (const f of findSplitHeadings(headingNodes, { artboard: ab.name })) add(f);
  }

  // 7. artboard fit — Paper's own Review Checkpoint
  const root = nodes.get(ab.id);
  if (root?.childIds?.length) {
    const kids = root.childIds.map((id) => nodes.get(id)).filter((k) => k && k.h != null);
    const bottom = Math.max(...kids.map((k) => k.worldY + k.h));
    const over = Math.round(bottom - (ab.worldY + ab.height));
    if (over > 2) {
      add({ artboard: ab.name, type: "artboard-fit", severity: "high", node: ab.id, name: ab.name,
            detail: `content extends ${over}px past the artboard — set height: fit-content` });
    }
  }
}

// ---- optional screenshots of the worst artboards ----
if (shotsDir) {
  mkdirSync(resolve(shotsDir), { recursive: true });
  const byBoard = new Map();
  for (const f of findings) byBoard.set(f.artboard, (byBoard.get(f.artboard) || 0) + 1);
  for (const ab of artboards) {
    try {
      const res = await call("get_screenshot", { nodeId: ab.id });
      for (const item of res.content ?? []) {
        if (item.type === "image") {
          const p = join(resolve(shotsDir), screenshotFileName(ab.name));
          writeFileSync(p, Buffer.from(item.data, "base64"));
          log(`  shot ${p}`);
        }
      }
    } catch (err) {
      log(`  screenshot failed for ${ab.name}: ${err.message.split("\n")[0]}`);
    }
  }
}

for (const f of findBreakpointImageGaps(boardStats)) add(f);

const bySeverity = { high: 0, medium: 0, low: 0 };
for (const f of findings) bySeverity[f.severity]++;
const byType = {};
for (const f of findings) byType[f.type] = (byType[f.type] || 0) + 1;

const report = {
  file: info.fileName,
  page: info.pageName,
  artboards: artboards.map((a) => a.name),
  depth: maxDepth,
  coverage,
  totals: { findings: findings.length, ...bySeverity },
  byType,
  findings: findings.sort((a, b) => {
    const rank = { high: 0, medium: 1, low: 2 };
    return rank[a.severity] - rank[b.severity];
  }),
};

writeFileSync(resolve(jsonOut), JSON.stringify(report, null, 2), "utf8");
console.log(JSON.stringify({ ...report, findings: report.findings.slice(0, 25) }, null, 1));
