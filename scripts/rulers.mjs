// Canvas rulers. Paper has no native guides — a thin red artboard is the lintel.
// HARD GATE: the first artboard in a Paper file is `Ruler · desktop`.
// One ruler only. One horizontal row under that bar, in this drop order:
//   1. Design Library
//   2. Screenshots (or Source · {page})
//   3. home-desktop (live assemble)
//   4. home-768 (authored from desktop)
//   5. home-390 (authored from desktop)
//   6. Buttons (legacy alias: Hover States)
//   7. Components
//   8. Navigation
//   then leftover A/6
// Never a Ruler · 768 / Ruler · 390 stack.
//
//   node draw-rulers.mjs --file <id> [--init]
//
// create_artboard ignores left/top. Always pin with update_styles.

export const RULER_PREFIX = "Ruler · ";
export const PARK_BUFFER = 100;
export const RULER_THICK = 8;
export const RULER_ABOVE = 100;
export const RULER_COLOR = "#E11D2E";
export const RULER_WIDTH = 20000;
export const COLUMN_GAP = 160;
export const LANDER_NAMES = ["home-desktop", "home-768", "home-390"];
export const INTERACTIVE_COMPONENTS = "Interactive components";
export const BUTTONS_BOARD = "Buttons";
export const HOVER_STATES_BOARD = BUTTONS_BOARD;
export const BUTTONS_BOARD_ALIASES = ["Hover States"];
export const COMPONENTS_BOARD = "Components";

export function isButtonsBoard(name = "") {
  return name === BUTTONS_BOARD || name === "Hover States";
}
export const NAVIGATION_BOARD = "Navigation";
export const SCREENSHOTS_BOARD = "Screenshots";
export const DESIGN_LIBRARY_NAME = "Design Library";
export const DESIGN_LIBRARY = DESIGN_LIBRARY_NAME;
export const LIBRARY_WIDTH = 1200;
export const LIBRARY_GAP = 160;

export const isRulerName = (name) =>
  typeof name === "string" && name.startsWith(RULER_PREFIX);

export const isLibraryName = (name = "") =>
  name === DESIGN_LIBRARY_NAME || /^(LIBRARY\b|Design Library)/.test(name);

export const contentArtboards = (boards = []) =>
  boards.filter((b) => !isRulerName(b.name));

/** Boards that sit in the main row (includes Design Library). */
export const landerRowArtboards = (boards = []) => contentArtboards(boards);

export function rowKeyFromPageName(name = "") {
  if (/-390\b/.test(name) || /\bphone\b/i.test(name)) return "390";
  if (/-768\b/.test(name) || /\btablet\b/i.test(name)) return "768";
  return "desktop";
}

export const rulerNameForRow = (key) => `${RULER_PREFIX}${key}`;
export const DESKTOP_RULER = rulerNameForRow("desktop");

export const rulerTopForRowY = (rowY, thick = RULER_THICK, above = RULER_ABOVE) =>
  (rowY || 0) - thick - above;

export function isReviewBoard(name = "") {
  if (isRulerName(name)) return false;
  if (name.endsWith(" — source screenshot")) return false;
  if (/^home-(desktop|768|390)$/.test(name)) return false;
  if (name === INTERACTIVE_COMPONENTS || isButtonsBoard(name)) return true;
  if (name === COMPONENTS_BOARD || name === NAVIGATION_BOARD) return true;
  if (name === SCREENSHOTS_BOARD) return true;
  if (typeof name === "string" && name.startsWith("Source · ")) return true;
  return /^A\/\d/.test(name);
}

export const isSourceBoardName = (name = "") =>
  typeof name === "string"
  && (name === SCREENSHOTS_BOARD || name.startsWith("Source · "));

/** Left-to-right drop order under the ruler. */
export const CANVAS_SLOTS = [
  { id: "library", test: isLibraryName },
  { id: "source", test: isSourceBoardName },
  { id: "desktop", test: (n) => n === "home-desktop" },
  { id: "tablet", test: (n) => n === "home-768" },
  { id: "mobile", test: (n) => n === "home-390" },
  { id: "hover", test: isButtonsBoard },
  { id: "components", test: (n) => n === COMPONENTS_BOARD },
  { id: "navigation", test: (n) => n === NAVIGATION_BOARD || n === INTERACTIVE_COMPONENTS },
  { id: "states", test: (n) => /^A\/\d/.test(n) || /^LIBRARY — Components/.test(n) },
];

export function canvasSlot(name = "") {
  const i = CANVAS_SLOTS.findIndex((s) => s.test(name));
  return i < 0 ? CANVAS_SLOTS.length : i;
}

/** Review / library frames must not shove the next lander past the lintel. */
export function ignoresLanderRightEdge(name = "") {
  if (!name) return false;
  if (isRulerName(name)) return true;
  if (name === DESIGN_LIBRARY) return true;
  if (name === INTERACTIVE_COMPONENTS) return true;
  if (isButtonsBoard(name) || name === COMPONENTS_BOARD || name === NAVIGATION_BOARD) return true;
  if (/^A\/\d/.test(name)) return true;
  if (name.endsWith(" — source screenshot")) return true;
  if (name === "Desktop section IDs") return true;
  return false;
}

export function landerPlacementBoards(boards = []) {
  return contentArtboards(boards).filter((b) => !ignoresLanderRightEdge(b.name));
}

export function landerRightEdge(boards = [], originLeft = 0) {
  return landerPlacementBoards(boards).reduce(
    (max, a) => Math.max(max, (a.worldX || 0) + (a.width || 0)),
    originLeft,
  );
}

export function mcpPayload(result) {
  for (const item of result.content ?? []) {
    if (item.type === "text") {
      try { return JSON.parse(item.text); } catch { return { text: item.text }; }
    }
  }
  return {};
}

function pageNamed(boards, name) {
  return (boards || []).find((b) => b.name === name);
}

export function contentOrigin(boards = []) {
  const ruler = pageNamed(boards, DESKTOP_RULER);
  const top = ruler
    ? Math.round((ruler.worldY || 0) + (ruler.height || RULER_THICK) + PARK_BUFFER)
    : PARK_BUFFER;
  return { left: 0, top };
}

/** Park Design Library first in the row — left of screenshots + landers (slot 1). */
export function libraryPark({
  boards = [],
  originX = 0,
  originY = PARK_BUFFER,
  width = LIBRARY_WIDTH,
  gap = LIBRARY_GAP,
  lintel = RULER_WIDTH,
  side = "row",
} = {}) {
  const y = originY;
  if (side === "right") return { x: lintel + gap, y, width };
  if (side === "left") return { x: originX - width - gap, y, width };
  // Library is slot 1: nothing legitimately precedes it, so park it left of the
  // row that 1.0–1.3 already dropped. arrange-artboards.mjs re-packs from x=0.
  const later = contentArtboards(boards).filter(
    (b) => !isLibraryName(b.name) && canvasSlot(b.name) > canvasSlot(DESIGN_LIBRARY_NAME),
  );
  if (!later.length) return { x: originX, y, width };
  const left = later.reduce((min, b) => Math.min(min, b.worldX || 0), Infinity);
  return { x: Math.round(left - width - gap), y, width };
}

/** Library → source → desktop → tablet → mobile → hover → components → nav. */
export function planLanderRow(boards = [], {
  gap = 120,
  originX = 0,
  originY = PARK_BUFFER,
  wrapAt = RULER_WIDTH,
} = {}) {
  const content = landerRowArtboards(boards);
  const ranked = [...content].sort((a, b) => {
    const d = canvasSlot(a.name) - canvasSlot(b.name);
    return d || String(a.name).localeCompare(String(b.name));
  });
  const planned = [];
  let x = originX;
  let y = originY;
  let rowH = 0;

  for (const b of ranked) {
    const w = b.width || 0;
    if (wrapAt && x > originX && x + w > wrapAt) {
      y += rowH + gap;
      x = originX;
      rowH = 0;
    }
    planned.push({
      name: b.name,
      id: b.id,
      x,
      y,
      width: b.width,
      height: b.height,
    });
    x += w + gap;
    rowH = Math.max(rowH, b.height || 0);
  }
  return planned;
}

export async function retireBreakpointRulers({
  call,
  fileId,
  boards = [],
  log = () => {},
} = {}) {
  const extra = (boards || []).filter(
    (b) => isRulerName(b.name) && b.name !== DESKTOP_RULER,
  );
  if (!extra.length || !call) return extra;
  await call("delete_nodes", {
    ...(fileId ? { fileId } : {}),
    nodeIds: extra.map((b) => b.id),
  });
  log(`retired ${extra.map((b) => b.name).join(", ")}`);
  return extra;
}

export async function ensureRulers({
  call,
  fileId,
  boards = [],
  init = false,
  width = RULER_WIDTH,
  left = 0,
  thick = RULER_THICK,
  log = () => {},
} = {}) {
  if (!call) throw new Error("ensureRulers needs call()");
  await retireBreakpointRulers({ call, fileId, boards, log });
  const live = (boards || []).filter(
    (b) => !(isRulerName(b.name) && b.name !== DESKTOP_RULER),
  );
  const byName = new Map(live.map((b) => [b.name, b]));
  const noRulers = !live.some((b) => b.name === DESKTOP_RULER);
  if (!init && !noRulers && !byName.get(DESKTOP_RULER)) {
    return [];
  }

  const name = DESKTOP_RULER;
  let board = byName.get(name);
  if (!board) {
    const made = mcpPayload(await call("create_artboard", {
      ...(fileId ? { fileId } : {}),
      name,
      styles: {
        width: `${width}px`,
        height: `${thick}px`,
        backgroundColor: RULER_COLOR,
        padding: "0px",
        display: "flex",
      },
    }));
    const id = made.id || made.nodeId || made.createdNodes?.[0]?.id;
    if (!id) throw new Error(`create_artboard returned no id for ${name}`);
    board = { id, name };
    log(`ruler ${name} created`);
  }
  await call("update_styles", {
    ...(fileId ? { fileId } : {}),
    updates: [{
      nodeIds: [board.id],
      styles: {
        left: `${left}px`,
        top: "0px",
        width: `${width}px`,
        height: `${thick}px`,
        backgroundColor: RULER_COLOR,
      },
    }],
  });
  log(`ruler ${name}  y=0`);
  return [{ name, id: board.id, y: 0, rowY: PARK_BUFFER }];
}

export function parkNextInRow({
  boards = [],
  name = "",
  pageName = "home-desktop",
  buffer = PARK_BUFFER,
  columnGap = COLUMN_GAP,
  newWidth = 1400,
  wrapAt = RULER_WIDTH,
} = {}) {
  const origin = contentOrigin(boards);
  const slot = canvasSlot(name || pageName);
  const earlier = contentArtboards(boards).filter((b) => canvasSlot(b.name) < slot);
  const same = contentArtboards(boards).filter((b) => canvasSlot(b.name) === slot);
  const pack = same.length ? same : earlier;
  if (!pack.length) return { left: origin.left, top: origin.top, buffer };
  const right = Math.max(...pack.map((b) => (b.worldX || 0) + (b.width || 0)));
  const top = origin.top;
  if (wrapAt && right + buffer + newWidth > wrapAt) {
    const bottom = Math.max(...pack.map((b) => (b.worldY || 0) + (b.height || 0)));
    return { left: origin.left, top: Math.round(bottom + buffer), buffer };
  }
  return { left: Math.round(right + columnGap), top, buffer };
}

/** @deprecated use parkNextInRow — review boards stack horizontally under the ruler */
export function parkNextInColumn(opts) {
  return parkNextInRow(opts);
}

export function hasDesktopRuler(boards = []) {
  return boards.some((b) => b.name === DESKTOP_RULER);
}
