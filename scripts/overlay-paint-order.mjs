#!/usr/bin/env node
// Pitfall #84 — full-bleed abs overlay vs later text siblings.
//
// Serializer emits absolute full-bleed dim overlays AFTER in-flow content.
// Paper last-sibling paints on top, so type loses to the rectangle.
// Gold (JA-0): image → dim overlay → type last.
// Do NOT clone the overlay on top. Clone-on-top is for *content* (CTA forms)
// when the overlay already covers them. Fallback: overlay z-index: -1.
//
// Library (no Paper):
//   isFullBleedAbsOverlay(style, meta)
//   planOverlayPaintOrder(siblings)
//   reorderOverlayPaintOrder(html)
//   findOverlayPaintOrderIssues(nodes, { artboard })
//
// Catch-at-write: assemble-lander / import-sections call
// reorderOverlayPaintOrder after flatten+trim, before write_html.
// Already-written landers: fix-overlay-paint-order.mjs (supports an optional blocklist).

import {
  coversParent,
  looksInset,
  maxStroke,
  parseStyle,
} from "./flatten-decorative-abs.mjs";

const VOID = new Set(["img", "br", "hr", "input", "meta", "link", "source", "area", "col", "embed", "wbr"]);
const MEDIA = new Set(["img", "svg", "video", "canvas", "iframe", "picture", "source"]);
const INTERACTIVE = new Set(["a", "button", "input", "select", "textarea", "label"]);
const TYPE_TAGS = new Set(["p", "h1", "h2", "h3", "h4", "h5", "h6", "span", "em", "strong", "small", "li"]);

function alphaOf(color) {
  const s = String(color || "").trim().toLowerCase();
  if (!s || s === "transparent" || s === "none") return 0;
  const rgba = s.match(/rgba\(\s*[\d.]+\s*,\s*[\d.]+\s*,\s*[\d.]+\s*,\s*([\d.]+)/);
  if (rgba) return Number(rgba[1]);
  const hex = s.match(/^#([0-9a-f]{8})$/i);
  if (hex) return parseInt(hex[1].slice(6, 8), 16) / 255;
  return 1;
}

export function hasDimFill(style = {}) {
  const bg = style["background-color"] || "";
  if (bg && alphaOf(bg) > 0) return true;
  const short = style.background || "";
  if (short && !/url\(/i.test(short) && alphaOf(short) > 0) return true;
  const op = parseFloat(style.opacity);
  return Number.isFinite(op) && op > 0 && op < 1;
}

export function isPctCover(style = {}) {
  const w = String(style.width || style["inline-size"] || "");
  const h = String(style.height || style["block-size"] || "");
  return /100%/.test(w) && /100%/.test(h);
}

export function isFullBleedAbsOverlay(style = {}, meta = {}) {
  const pos = style.position || meta.position;
  if (pos !== "absolute" && pos !== "fixed") return false;
  if (meta.hasMedia) return false;
  if (String(meta.text || "").trim()) return false;
  if ((meta.childCount || 0) > 0) return false;
  if (meta.hasInteractive) return false;
  if (!hasDimFill(style) && !hasDimFill({
    "background-color": meta.backgroundColor,
    opacity: meta.opacity,
  })) return false;
  const stroke = maxStroke(style);
  if (stroke > 0 && stroke <= 2 && !hasDimFill(style) && !meta.backgroundColor) return false;
  if (looksInset(style) || isPctCover(style) || coversParent(style, meta.parentStyle || {})) {
    return true;
  }
  const w = meta.width;
  const h = meta.height;
  const pw = meta.parentWidth;
  const ph = meta.parentHeight;
  if (w != null && h != null && pw != null && ph != null) {
    return Math.abs(w - pw) <= 4 && Math.abs(h - ph) <= 4;
  }
  return false;
}

export function isImageSibling(sib) {
  if (!sib) return false;
  if (sib.hasMedia) return true;
  if (sib.tag && MEDIA.has(sib.tag)) return true;
  const c = String(sib.component || "").toLowerCase();
  if (c === "image" || c === "svg") return true;
  const bg = sib.style?.["background-image"] || "";
  if (bg && bg !== "none" && /url\(/i.test(bg)) return true;
  return false;
}

export function isTypeSibling(sib) {
  if (!sib) return false;
  if (String(sib.text || "").trim()) return true;
  if (sib.tag && TYPE_TAGS.has(sib.tag)) return true;
  const c = String(sib.component || "").toLowerCase();
  if (c === "text" || /^h[1-6]$/.test(c) || c === "p") return true;
  return false;
}

function classify(sib) {
  if (sib.overlay) return "overlay";
  if (isImageSibling(sib)) return "image";
  if (isTypeSibling(sib)) return "type";
  return "other";
}

/**
 * Gold: image → dim overlay → type last.
 * Only the overlay moves. Images / type / other keep relative order.
 */
export function planOverlayPaintOrder(siblings = []) {
  const items = siblings.map((sib, index) => ({
    ...sib,
    index,
    kind: sib.overlay || isFullBleedAbsOverlay(sib.style || {}, sib)
      ? "overlay"
      : classify(sib),
  }));
  const overlays = items.filter((s) => s.kind === "overlay");
  const types = items.filter((s) => s.kind === "type");
  if (!overlays.length || !types.length) {
    return { alreadyGold: true, moved: [], ordered: items };
  }
  const firstType = types[0].index;
  const coversType = overlays.some((o) => o.index > firstType);
  if (!coversType) {
    return { alreadyGold: true, moved: [], ordered: items };
  }
  const rest = items.filter((s) => s.kind !== "overlay");
  let insertAt = 0;
  for (let i = rest.length - 1; i >= 0; i--) {
    if (rest[i].kind === "image") {
      insertAt = i + 1;
      break;
    }
  }
  const ordered = [...rest.slice(0, insertAt), ...overlays, ...rest.slice(insertAt)];
  const moved = overlays.map((o) => ({
    id: o.id,
    name: o.name,
    from: o.index,
    reason: "abs overlay after type — Paper last-sibling paints on top",
  }));
  return { alreadyGold: false, moved, ordered };
}

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
    continue;
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

function elSiblings(children, parentStyle = {}) {
  return (children || []).map((child) => {
    if (child.type !== "el") {
      return {
        node: child,
        style: {},
        text: child.type === "text" ? child.value : "",
        tag: "",
        childCount: 0,
        hasMedia: false,
        hasInteractive: false,
        parentStyle,
      };
    }
    const style = parseStyle(attr(child, "style"));
    const kids = (child.children || []).filter((c) => c.type === "el" || (c.type === "text" && c.value.trim()));
    return {
      node: child,
      style,
      text: nodeText(child),
      tag: child.tag,
      childCount: kids.length,
      hasMedia: nodeHas(child, MEDIA),
      hasInteractive: nodeHas(child, INTERACTIVE),
      parentStyle,
    };
  });
}

function walkReorder(node, moved, parentStyle = {}) {
  if (node.type !== "el") return;
  const style = parseStyle(attr(node, "style"));
  const sibs = elSiblings(node.children, style);
  for (const sib of sibs) walkReorder(sib.node, moved, style);
  const plan = planOverlayPaintOrder(sibs);
  if (plan.alreadyGold) return;
  node.children = plan.ordered.map((s) => s.node);
  moved.push(...plan.moved);
}

export function reorderOverlayPaintOrder(html) {
  const parsed = parseFragment(html);
  const moved = [];
  for (const node of parsed.nodes) walkReorder(node, moved, {});
  return {
    html: serializeNodes(parsed.nodes) + html.slice(parsed.consumed),
    moved,
  };
}

export function findOverlayPaintOrderIssues(nodes, { artboard } = {}) {
  const list = nodes instanceof Map ? [...nodes.values()] : [...(nodes || [])];
  const byId = new Map(list.map((n) => [n.id, n]));
  const findings = [];
  const parents = new Set();
  for (const n of list) {
    if (n.childIds?.length) parents.add(n.id);
    else if (n.parentId) parents.add(n.parentId);
  }
  for (const pid of parents) {
    const parent = byId.get(pid);
    const childIds = parent?.childIds || list.filter((n) => n.parentId === pid).map((n) => n.id);
    if (!childIds.length) continue;
    const sibs = childIds.map((id) => {
      const n = byId.get(id);
      if (!n) return null;
      return {
        id: n.id,
        name: n.name,
        style: {
          position: n.position,
          width: n.widthStyle || (n.w != null ? `${n.w}px` : ""),
          height: n.h != null ? `${n.h}px` : "",
          top: n.top,
          right: n.right,
          bottom: n.bottom,
          left: n.left,
          inset: n.inset,
          "background-color": n.bg || n.backgroundColor,
          opacity: n.opacity,
        },
        position: n.position,
        backgroundColor: n.bg || n.backgroundColor,
        opacity: n.opacity,
        text: n.textContent,
        hasMedia: n.component === "Image" || n.component === "SVG",
        childCount: n.childCount || n.childIds?.length || 0,
        component: n.component,
        width: n.w,
        height: n.h,
        parentWidth: parent?.w,
        parentHeight: parent?.h,
      };
    }).filter(Boolean);
    const plan = planOverlayPaintOrder(sibs);
    if (plan.alreadyGold) continue;
    for (const m of plan.moved) {
      findings.push({
        artboard,
        type: "overlay-covers-type",
        severity: "high",
        node: m.id,
        name: m.name,
        parent: parent?.name,
        detail: "full-bleed abs overlay after type — move after image, before type (Pitfall #84). Do not clone the overlay on top.",
      });
    }
  }
  return findings;
}
