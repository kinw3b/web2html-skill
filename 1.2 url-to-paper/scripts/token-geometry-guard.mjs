import { lineHeightToPercent } from "./library-tokens.mjs";

const NUMERIC_PROPERTIES = [
  "x",
  "y",
  "width",
  "height",
  "fontSize",
  "lineHeight",
  "flexGrow",
];

const STRING_PROPERTIES = ["textWrap", "alignSelf"];

function geometryValue(value) {
  if (value == null || value === "") return null;
  return typeof value === "string" ? value.trim() : value;
}

function strictPixelNumber(value) {
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  const raw = String(value).trim();
  if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:px)?$/i.test(raw)) return null;
  const parsed = Number(raw.replace(/px$/i, ""));
  return Number.isFinite(parsed) ? parsed : null;
}

function normalizedGeometryString(value) {
  if (value == null) return "";
  return String(value).trim().toLowerCase();
}

function tokenValueMap(tokens) {
  return new Map((tokens || [])
    .filter((token) => token?.name)
    .map((token) => [String(token.name).trim(), token.value]));
}

function resolveGeometryToken(value, values, seen = new Set()) {
  if (typeof value !== "string") return value;
  const match = /^var\(\s*(--[^)\s]+)\s*\)$/i.exec(value.trim());
  if (!match || seen.has(match[1]) || !values.has(match[1])) return value;
  seen.add(match[1]);
  return resolveGeometryToken(values.get(match[1]), values, seen);
}

function stringValue(value) {
  return value == null ? "" : String(value);
}

export function snapshotTokenGeometry(nodes = []) {
  return nodes.map((node) => {
    const style = node.style || {};
    return {
      nodeId: node.id || node.nodeId,
      artboard: node.artboard || "",
      x: geometryValue(style.x ?? node.x),
      y: geometryValue(style.y ?? node.y),
      width: geometryValue(style.width ?? node.width),
      height: geometryValue(style.height ?? node.height),
      fontSize: geometryValue(style.fontSize ?? style["font-size"]),
      lineHeight: geometryValue(style.lineHeight ?? style["line-height"]),
      textWrap: stringValue(style.textWrap ?? style["text-wrap"]),
      flexGrow: geometryValue(style.flexGrow ?? style["flex-grow"]),
      alignSelf: stringValue(style.alignSelf ?? style["align-self"]),
    };
  });
}

export function compareTokenGeometry(
  before = [],
  after = [],
  { ignoredArtboards = ["Design Library"], tokens = [] } = {},
) {
  const ignored = new Set(ignoredArtboards);
  const tokenValues = tokenValueMap(tokens);
  const include = (item) => !ignored.has(item.artboard);
  const beforeById = new Map(before.filter(include).map((item) => [item.nodeId, item]));
  const afterById = new Map(after.filter(include).map((item) => [item.nodeId, item]));
  const differences = [];

  for (const [nodeId, earlier] of beforeById) {
    const later = afterById.get(nodeId);
    if (!later) {
      differences.push({ nodeId, artboard: earlier.artboard, reason: "missing-after" });
      continue;
    }
    for (const property of NUMERIC_PROPERTIES) {
      const from = earlier[property];
      const to = later[property];
      const resolvedFrom = resolveGeometryToken(from, tokenValues);
      const resolvedTo = resolveGeometryToken(to, tokenValues);
      if (property === "lineHeight") {
        const fontFrom = resolveGeometryToken(earlier.fontSize, tokenValues);
        const fontTo = resolveGeometryToken(later.fontSize, tokenValues);
        const fromPct = lineHeightToPercent(resolvedFrom, fontFrom);
        const toPct = lineHeightToPercent(resolvedTo, fontTo);
        if (fromPct && toPct) {
          if (fromPct !== toPct) {
            differences.push({ nodeId, artboard: earlier.artboard, property, from, to });
          }
          continue;
        }
      }
      const fromNumber = strictPixelNumber(resolvedFrom);
      const toNumber = strictPixelNumber(resolvedTo);
      const changed = fromNumber != null && toNumber != null
        ? Math.abs(fromNumber - toNumber) > 0.5
        : normalizedGeometryString(resolvedFrom) !== normalizedGeometryString(resolvedTo);
      if (changed) {
        differences.push({ nodeId, artboard: earlier.artboard, property, from, to });
      }
    }
    for (const property of STRING_PROPERTIES) {
      if (earlier[property] !== later[property]) {
        differences.push({
          nodeId,
          artboard: earlier.artboard,
          property,
          from: earlier[property],
          to: later[property],
        });
      }
    }
  }

  for (const [nodeId, later] of afterById) {
    if (!beforeById.has(nodeId)) {
      differences.push({ nodeId, artboard: later.artboard, reason: "missing-before" });
    }
  }

  return {
    ok: differences.length === 0,
    checkedNodes: beforeById.size,
    differences,
  };
}
