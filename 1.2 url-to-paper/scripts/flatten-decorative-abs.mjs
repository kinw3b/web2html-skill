#!/usr/bin/env node
// Flatten paint-only position:absolute overlays into parent CSS.
//
// Framer / Paper often emit a sibling Rectangle (inset 0, 1px border,
// frozen capture width/height) instead of `border` on the card. That
// overlay shears on mobile and shifts layout. Import must hoist the
// stroke/fill onto the parent and drop the floater before write_html.
//
//   node flatten-decorative-abs.mjs --scan capture/home-desktop
//   node flatten-decorative-abs.mjs --in card.html --out card.flat.html
//
// Library: flattenDecorativeAbs(html) / scanDecorativeAbs(html) /
// collapseAnimatedLabelStacks(html) / isDecorativeAbs(meta).
// Also hoists CSS gradients. A/6 hover HTML uses the same helpers.

import { readFileSync, writeFileSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";

const VOID = new Set(["img", "br", "hr", "input", "meta", "link", "source", "area", "col", "embed", "wbr"]);
const MEDIA = new Set(["img", "svg", "video", "canvas", "iframe", "picture", "source"]);
const INTERACTIVE = new Set(["a", "button", "input", "select", "textarea", "label"]);
const MAX_STROKE = 2;
const MIN_EDGE = 8;

export function parseStyle(s = "") {
  const out = {};
  for (const part of String(s).split(";")) {
    const i = part.indexOf(":");
    if (i < 0) continue;
    const k = part.slice(0, i).trim().toLowerCase();
    const v = part.slice(i + 1).trim();
    if (k) out[k] = v;
  }
  return out;
}

export function serializeStyle(dict) {
  return Object.entries(dict)
    .filter(([, v]) => v != null && v !== "")
    .map(([k, v]) => `${k}: ${v}`)
    .join("; ");
}

export function px(v) {
  if (v == null || v === "" || v === "auto") return null;
  const n = parseFloat(String(v));
  return Number.isNaN(n) ? null : n;
}

export function isTransparent(v) {
  if (!v) return true;
  const s = String(v).toLowerCase();
  return s === "transparent" || s === "none" || /rgba\(\s*0\s*,\s*0\s*,\s*0\s*,\s*0/.test(s);
}

function sideWidth(st, side) {
  const long = px(st[`border-${side}-width`]);
  if (long != null) return long;
  const all = px(st["border-width"]);
  if (all != null) return all;
  if (st.border) {
    const m = String(st.border).match(/(\d+(?:\.\d+)?)px/);
    if (m) return parseFloat(m[1]);
  }
  return 0;
}

export function strokeSides(st = {}) {
  return {
    top: sideWidth(st, "top"),
    right: sideWidth(st, "right"),
    bottom: sideWidth(st, "bottom"),
    left: sideWidth(st, "left"),
  };
}

export function maxStroke(st = {}) {
  return Math.max(...Object.values(strokeSides(st)));
}

export function looksInset(st = {}) {
  if (st.inset && st.inset !== "auto" && st.inset !== "unset") return true;
  const zeros = ["top", "right", "bottom", "left"].filter((k) => px(st[k]) === 0).length;
  return zeros >= 3;
}

export function coversParent(childStyle = {}, parentStyle = {}) {
  if (looksInset(childStyle)) return true;
  const cw = px(childStyle.width) ?? px(childStyle["inline-size"]);
  const ch = px(childStyle.height) ?? px(childStyle["block-size"]);
  const pw = px(parentStyle.width) ?? px(parentStyle["inline-size"]);
  const ph = px(parentStyle.height) ?? px(parentStyle["block-size"]);
  if (cw != null && ch != null && pw != null && ph != null) {
    return Math.abs(cw - pw) <= 2 && Math.abs(ch - ph) <= 2;
  }
  return false;
}

function sideColor(st, side) {
  return st[`border-${side}-color`] || st["border-color"] || st["border-top-color"] || "";
}

function sideStyle(st, side) {
  return st[`border-${side}-style`] || st["border-style"] || "solid";
}

export function isCssGradient(value) {
  return /^(?:repeating-)?(?:linear|radial|conic)-gradient\(/i.test(String(value || "").trim());
}

export function decorationPaint(st = {}) {
  const sides = strokeSides(st);
  const max = Math.max(...Object.values(sides));
  const fill = !isTransparent(st["background-color"]) ? st["background-color"] : "";
  const gradient = isCssGradient(st["background-image"]) ? st["background-image"] : "";
  const radius = st["border-radius"] || "";
  const shadow = st["box-shadow"] && st["box-shadow"] !== "none" ? st["box-shadow"] : "";
  if (max <= 0 && !fill && !shadow && !gradient) return null;
  if (max > MAX_STROKE && !fill && !shadow && !gradient) return null;
  const painted = Object.entries(sides).filter(([, w]) => w > 0 && w <= MAX_STROKE);
  const box = painted.length === 4 && painted.every(([, w]) => w === painted[0][1]);
  return { sides, max, fill, gradient, radius, shadow, box, painted };
}

/** Build CSS declarations to copy onto the parent. */
export function parentHoist(childStyle, paint) {
  const styles = {};
  if (!paint) return styles;
  if (paint.box) {
    const w = paint.painted[0][1];
    const color =
      childStyle["border-color"] ||
      childStyle["border-top-color"] ||
      childStyle["border-bottom-color"] ||
      "#EAEDF0";
    const line = childStyle["border-style"] || childStyle["border-top-style"] || "solid";
    styles.border = `${w}px ${line} ${toHex(color)}`;
  } else {
    for (const [side, w] of paint.painted) {
      const color = childStyle[`border-${side}-color`] || childStyle["border-color"] || "#EAEDF0";
      const line = childStyle[`border-${side}-style`] || childStyle["border-style"] || "solid";
      const key = `border-${side}`;
      styles[key] = `${w}px ${line} ${toHex(color)}`;
    }
  }
  if (paint.radius) styles["border-radius"] = paint.radius;
  if (paint.fill) styles["background-color"] = paint.fill;
  if (paint.gradient) styles["background-image"] = paint.gradient;
  if (paint.shadow) styles["box-shadow"] = paint.shadow;
  return styles;
}

export function parentHoistCamel(childStyle, paint) {
  const kebab = parentHoist(childStyle, paint);
  const camel = {};
  for (const [k, v] of Object.entries(kebab)) {
    camel[k.replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = v;
  }
  return camel;
}

function toHex(color) {
  const s = String(color || "").trim();
  if (s.startsWith("#")) return s.toUpperCase();
  const m = s.match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*([0-9.]+))?\s*\)/i);
  if (!m) return s;
  const alpha = m[4] == null ? 1 : Number(m[4]);
  if (Number.isFinite(alpha) && alpha < 1) return s;
  const hex = [m[1], m[2], m[3]]
    .map((n) => Number(n).toString(16).padStart(2, "0"))
    .join("");
  return `#${hex.toUpperCase()}`;
}

export function isDecorativeAbs({
  childStyle = {},
  parentStyle = {},
  childCount = 0,
  text = "",
  hasMedia = false,
  hasInteractive = false,
  width = null,
  height = null,
  paintOnlyChildren = false,
  treePaint = null,
} = {}) {
  const pos = childStyle.position;
  if (pos !== "absolute" && pos !== "fixed") return false;
  if (hasMedia || hasInteractive) return false;
  if (String(text || "").trim()) return false;
  // A Frame whose only child is a paint Rectangle is still a floater.
  // Hoist that fill onto the parent (Pitfall #95). Empty leaf still required
  // unless the whole subtree is paint-only.
  if (childCount > 0 && !paintOnlyChildren) return false;
  const bgImg = childStyle["background-image"];
  if (bgImg && bgImg !== "none" && !isCssGradient(bgImg)) return false;
  const w = width ?? px(childStyle.width) ?? px(childStyle["inline-size"]);
  const h = height ?? px(childStyle.height) ?? px(childStyle["block-size"]);
  if ((w != null && w <= MIN_EDGE) || (h != null && h <= MIN_EDGE)) return false;
  const paint = treePaint || decorationPaint(childStyle);
  if (!paint) return false;
  if (paint.max > MAX_STROKE && !paint.fill && !paint.gradient) return false;
  if (!coversParent(childStyle, parentStyle) && !looksInset(childStyle)) return false;
  return { paint };
}

// ---- HTML tree (serializer fragments: quoted attrs, no scripts) ----

function parseAttrs(raw) {
  const attrs = [];
  const re = /([^\s=]+)(?:="([^"]*)")?/g;
  let m;
  while ((m = re.exec(raw))) attrs.push({ name: m[1], value: m[2] ?? "" });
  return attrs;
}

function attr(node, name) {
  return node.attrs?.find((a) => a.name.toLowerCase() === name)?.value ?? "";
}

function setAttr(node, name, value) {
  const i = node.attrs.findIndex((a) => a.name.toLowerCase() === name);
  if (i >= 0) node.attrs[i].value = value;
  else node.attrs.push({ name, value });
}

function parseFragment(html) {
  const nodes = [];
  let i = 0;
  const s = String(html);
  while (i < s.length) {
    if (s.startsWith("</", i)) break;
    if (s[i] !== "<") {
      const next = s.indexOf("<", i);
      const end = next < 0 ? s.length : next;
      const value = s.slice(i, end);
      if (value) nodes.push({ type: "text", value });
      i = end;
      continue;
    }
    if (s.startsWith("<!--", i)) {
      const end = s.indexOf("-->", i + 4);
      const close = end < 0 ? s.length : end + 3;
      nodes.push({ type: "comment", value: s.slice(i, close) });
      i = close;
      continue;
    }
    const tagEnd = s.indexOf(">", i);
    if (tagEnd < 0) break;
    const body = s.slice(i + 1, tagEnd);
    const selfClose = body.endsWith("/");
    const parts = body.replace(/\/$/, "").match(/^([^\s]+)([\s\S]*)$/);
    if (!parts) {
      i = tagEnd + 1;
      continue;
    }
    const tag = parts[1].toLowerCase();
    const attrs = parseAttrs(parts[2] || "");
    const node = { type: "el", tag, attrs, children: [] };
    i = tagEnd + 1;
    if (tag === "svg") {
      const close = s.toLowerCase().indexOf("</svg>", i);
      node.rawInner = close < 0 ? s.slice(i) : s.slice(i, close);
      node.children = [{ type: "raw", value: node.rawInner }];
      i = close < 0 ? s.length : close + 6;
      nodes.push(node);
      continue;
    }
    if (VOID.has(tag) || selfClose) {
      nodes.push(node);
      continue;
    }
    const inner = parseFragment(s.slice(i));
    node.children = inner.nodes;
    i += inner.consumed;
    const close = s.slice(i).match(new RegExp(`^</${tag}\\s*>`, "i"));
    if (close) i += close[0].length;
    nodes.push(node);
  }
  return { nodes, consumed: i };
}

function serializeNodes(nodes) {
  return nodes.map(serializeNode).join("");
}

function serializeNode(node) {
  if (node.type === "text" || node.type === "comment" || node.type === "raw") return node.value;
  const attrs = (node.attrs || [])
    .map((a) => (a.value === "" && !a.name.startsWith("data-") ? a.name : `${a.name}="${a.value}"`))
    .join(" ");
  const open = attrs ? `<${node.tag} ${attrs}>` : `<${node.tag}>`;
  if (VOID.has(node.tag)) return attrs ? `<${node.tag} ${attrs}>` : `<${node.tag}>`;
  return `${open}${serializeNodes(node.children || [])}</${node.tag}>`;
}

function nodeText(node) {
  if (node.type === "text") return node.value;
  if (node.type === "raw" || node.type === "comment") return "";
  return (node.children || []).map(nodeText).join("");
}

function nodeHas(node, tags) {
  if (node.type !== "el") return false;
  if (tags.has(node.tag)) return true;
  return (node.children || []).some((c) => nodeHas(c, tags));
}


function isPaintOnlyNode(node) {
  if (!node || node.type !== "el") return false;
  if (nodeHas(node, MEDIA) || nodeHas(node, INTERACTIVE)) return false;
  if (String(nodeText(node) || "").trim()) return false;
  const kids = (node.children || []).filter((c) => c.type === "el" || (c.type === "text" && String(c.value).trim()));
  if (!kids.length) return !!decorationPaint(parseStyle(attr(node, "style")));
  return kids.every((c) => c.type === "el" && isPaintOnlyNode(c));
}

function collectTreePaint(node) {
  if (!node || node.type !== "el") return null;
  let paint = decorationPaint(parseStyle(attr(node, "style")));
  for (const c of node.children || []) {
    if (c.type !== "el") continue;
    const inner = collectTreePaint(c);
    if (!inner) continue;
    if (!paint) {
      paint = { ...inner };
      continue;
    }
    if (!paint.fill && inner.fill) paint.fill = inner.fill;
    if (!paint.gradient && inner.gradient) paint.gradient = inner.gradient;
    if (!paint.radius && inner.radius) paint.radius = inner.radius;
    if (!paint.shadow && inner.shadow) paint.shadow = inner.shadow;
    if (!paint.box && inner.box) {
      paint.box = inner.box;
      paint.painted = inner.painted;
      paint.sides = inner.sides;
      paint.max = inner.max;
    }
  }
  return paint;
}

function walkFlatten(node, findings, parentStyle = {}) {
  if (node.type !== "el") return;
  const style = parseStyle(attr(node, "style"));
  const kept = [];
  for (const child of node.children || []) {
    if (child.type !== "el") {
      kept.push(child);
      continue;
    }
    walkFlatten(child, findings, style);
    const childStyle = parseStyle(attr(child, "style"));
    const paintOnly = isPaintOnlyNode(child);
    const hit = isDecorativeAbs({
      childStyle,
      parentStyle: style,
      childCount: (child.children || []).filter((c) => c.type === "el" || (c.type === "text" && c.value.trim())).length,
      text: nodeText(child),
      hasMedia: nodeHas(child, MEDIA),
      hasInteractive: nodeHas(child, INTERACTIVE),
      paintOnlyChildren: paintOnly,
      treePaint: paintOnly ? collectTreePaint(child) : null,
    });
    if (!hit) {
      kept.push(child);
      continue;
    }
    const hoist = parentHoist(childStyle, hit.paint);
    const next = { ...style };
    for (const [k, v] of Object.entries(hoist)) {
      if (k === "background-color" && !isTransparent(next[k])) continue;
      if (k === "background-image" && next[k] && next[k] !== "none") continue;
      if (k === "border-radius" && next[k]) continue;
      next[k] = v;
    }
    if (hit.paint.box && /^(hidden|clip)$/.test(next.overflow || "")) next.overflow = "visible";
    setAttr(node, "style", serializeStyle(next));
    Object.assign(style, next);
    findings.push({
      tag: child.tag,
      paint: hit.paint.fill && !hit.paint.box && !hit.paint.painted?.length ? "fill" : hit.paint.box ? "box-border" : "side-border",
      hoist,
    });
  }
  node.children = kept;
}

export function flattenDecorativeAbs(html) {
  const parsed = parseFragment(html);
  const findings = [];
  for (const node of parsed.nodes) walkFlatten(node, findings, {});
  return { html: serializeNodes(parsed.nodes) + html.slice(parsed.consumed), removed: findings };
}

function walkStripAbsFill(node, findings) {
  if (node.type !== "el") return;
  for (const child of node.children || []) walkStripAbsFill(child, findings);
  if (MEDIA.has(node.tag)) return;
  const hasMedia = (node.children || []).some((c) => c.type === "el" && MEDIA.has(c.tag));
  if (hasMedia) return;
  const st = parseStyle(attr(node, "style"));
  if (String(st.position || "").toLowerCase() !== "absolute") return;
  const fill = st["background-color"] || st.background || st["background-image"];
  if (isTransparent(fill) && !st.border && !st["border-color"] && !st["border-width"]) return;
  delete st.position;
  delete st.top;
  delete st.left;
  delete st.right;
  delete st.bottom;
  delete st.inset;
  setAttr(node, "style", serializeStyle(st));
  findings.push({ tag: node.tag, paint: "css-fill" });
}

/** Button / link fills are background-color on the pill — never an abs overlay. */
export function stripAbsolutePaintFill(html) {
  const parsed = parseFragment(html);
  const findings = [];
  for (const node of parsed.nodes) walkStripAbsFill(node, findings);
  return { html: serializeNodes(parsed.nodes) + html.slice(parsed.consumed), removed: findings };
}

export function scanDecorativeAbs(html) {
  return flattenDecorativeAbs(html).removed;
}

const MIN_LABEL = 4;

function normLabel(node) {
  return nodeText(node).replace(/\s+/g, " ").trim();
}

function walkCollapseLabels(node, findings) {
  if (node.type !== "el") return;
  for (const child of node.children || []) walkCollapseLabels(child, findings);
  const kids = node.children || [];
  const kept = [];
  for (let i = 0; i < kids.length; i++) {
    const child = kids[i];
    const text = child.type === "el" ? normLabel(child) : "";
    if (child.type === "el" && text.length >= MIN_LABEL) {
      let j = i + 1;
      let dropped = 0;
      while (j < kids.length && kids[j].type === "el" && normLabel(kids[j]) === text) {
        findings.push({ text, tag: kids[j].tag });
        dropped++;
        j++;
      }
      if (dropped) {
        kept.push(child);
        const st = parseStyle(attr(node, "style"));
        if (st["flex-direction"] === "column") {
          delete st.height;
          delete st["min-height"];
          st["justify-content"] = "center";
          setAttr(node, "style", serializeStyle(st));
        }
        i = j - 1;
        continue;
      }
    }
    kept.push(child);
  }
  node.children = kept;
}

/**
 * Framer text-swap / slide labels serialize both copies (default + hover
 * glyph) as consecutive siblings. Paper then paints a vertical stack.
 * Keep the first, drop the rest.
 */
export function collapseAnimatedLabelStacks(html) {
  const parsed = parseFragment(html);
  const collapsed = [];
  for (const node of parsed.nodes) walkCollapseLabels(node, collapsed);
  return { html: serializeNodes(parsed.nodes) + html.slice(parsed.consumed), collapsed };
}

function walkFiles(dir, acc = []) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) walkFiles(p, acc);
    else if (name.endsWith(".html")) acc.push(p);
  }
  return acc;
}

if (process.argv.includes("--scan") || process.argv.includes("--in")) {
  const argv = process.argv.slice(2);
  const arg = (name) => {
    const i = argv.indexOf(`--${name}`);
    return i >= 0 && argv[i + 1] ? argv[i + 1] : null;
  };
  const scanDir = arg("scan");
  const inFile = arg("in");
  const outFile = arg("out");
  if (scanDir) {
    const files = walkFiles(resolve(scanDir));
    const report = [];
    for (const file of files) {
      const removed = scanDecorativeAbs(readFileSync(file, "utf8"));
      if (removed.length) report.push({ file, count: removed.length, kinds: removed.map((r) => r.paint) });
    }
    console.log(JSON.stringify({ files: files.length, hits: report.reduce((n, r) => n + r.count, 0), report }, null, 2));
  } else if (inFile) {
    const src = readFileSync(resolve(inFile), "utf8");
    const out = flattenDecorativeAbs(src);
    if (outFile) writeFileSync(resolve(outFile), out.html);
    console.log(JSON.stringify({ removed: out.removed.length, findings: out.removed }, null, 2));
  } else {
    console.error("Usage: flatten-decorative-abs.mjs --scan <dir> | --in <html> [--out <html>]");
    process.exit(1);
  }
}
