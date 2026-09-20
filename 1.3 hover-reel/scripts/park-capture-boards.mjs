// Fill review boards: Navigation, Components, and Buttons (legacy: Hover States).

import { importSibling } from "./skill-paths.mjs";
import {
  BUTTONS_BOARD,
  BUTTONS_BOARD_ALIASES,
  COMPONENTS_BOARD,
  NAVIGATION_BOARD,
  isHumanClickPair,
  objectTypeLabel,
} from "./component-state-utils.mjs";

/** Visual size — hug children. Never a fixed 1400 / 1800 board. */
export const REVIEW_BOARD_WIDTH = "fit-content";
export const NAVIGATION_BOARD_WIDTH = "fit-content";
/** Canvas slot reserved when parking an empty review frame. */
export const REVIEW_BOARD_PARK_WIDTH = 1400;
export const NAVIGATION_BOARD_PARK_WIDTH = 1800;
export const NAVIGATION_SPECIMEN_WIDTH = 1600;

export function reviewBoardFrameStyles({ left, top } = {}) {
  const styles = {
    display: "flex",
    flexDirection: "column",
    width: REVIEW_BOARD_WIDTH,
    height: "fit-content",
    overflow: "visible",
    backgroundColor: "#F2F2F2",
    padding: "48px",
    gap: "40px",
  };
  if (left != null) styles.left = `${left}px`;
  if (top != null) styles.top = `${top}px`;
  return styles;
}

function kidsOf(payload) {
  return payload?.children || [];
}

function nameOf(node) {
  return String(node?.name || "").trim();
}

export function sortBoardGroups(nodes = []) {
  return [...(nodes || [])].sort((a, b) => {
    const ay = Number(a.y ?? a.top ?? 0);
    const by = Number(b.y ?? b.top ?? 0);
    if (ay !== by) return ay - by;
    return Number(a.x ?? a.left ?? 0) - Number(b.x ?? b.left ?? 0);
  });
}

export function isNavigationChrome(name) {
  return /^(header|title)$/i.test(String(name || "").trim());
}

export function nextComponentIndex(nodes = [], prefix = "Object") {
  const re = new RegExp(`^${String(prefix).replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\s+(\\d+)$`, "i");
  return (nodes || []).reduce((max, node) => {
    const match = nameOf(node).match(re);
    return match ? Math.max(max, Number(match[1]) || 0) : max;
  }, 0) + 1;
}

export function isNavigationSpecimen(name) {
  return /^(placeholder|navbar|dropdown)/i.test(String(name || "").trim());
}

export function navigationSpecimens(nodes = []) {
  return sortBoardGroups((nodes || []).filter((n) => {
    if (isNavigationChrome(nameOf(n))) return false;
    if (isNavigationSpecimen(nameOf(n))) return true;
    return String(n.component || "") === "Frame";
  }));
}

export async function findBoard(call, name, aliases = []) {
  const { findArtboard, mcpPayload } = await importSibling(
    "url-to-paper",
    "scripts/write-paper-section.mjs",
  );
  const found = await findArtboard(call, name);
  if (found.board?.id) return found.board;
  for (const alias of aliases) {
    const next = await findArtboard(call, alias);
    if (next.board?.id) return next.board;
  }
  return null;
}

export function reviewBoardTitleHtml(name) {
  return `
    <div layer-name="Title" style="font-family: Inter, sans-serif; font-size: 26px; font-weight: 700; color: #111111;">
      ${name}
    </div>`;
}

function hasReviewTitle(nodes = []) {
  return (nodes || []).some((node) => isNavigationChrome(nameOf(node)));
}

export function navigationRowHtml() {
  return `
    <div layer-name="placeholder" style="display: flex; flex-direction: column; gap: 16px; width: 1600px; padding: 24px; background: #ffffff; border-radius: 16px; overflow: visible;">
      <div layer-name="title" style="font-family: Inter, sans-serif; font-size: 14px; font-weight: 600; color: #666666;">
        Navbar / dropdown
      </div>
      <div layer-name="states" style="display: flex; flex-direction: column; gap: 16px;">
        <div layer-name="closed" style="display: flex; width: 100%; min-height: 48px;">
          <div layer-name="slot" style="display: flex; width: 100%; min-height: 48px;"></div>
        </div>
        <div layer-name="open" style="display: flex; width: 100%; min-height: 48px;">
          <div layer-name="slot" style="display: flex; width: 100%; min-height: 48px;"></div>
        </div>
      </div>
    </div>
  `;
}

/** Seed HTML: title only. Capture rows are written on first park. */
export function navigationPlaceholderHtml({ includeTitle = true } = {}) {
  return includeTitle ? reviewBoardTitleHtml("Navigation") : "";
}

async function writeBoardChildren(call, boardId, fileId, html) {
  if (!html?.trim()) return;
  await call("write_html", {
    fileId,
    targetNodeId: boardId,
    mode: "insert-children",
    html,
  });
}

async function pinBoardInRow({
  call, fileId, board, name, parkWidth, log,
} = {}) {
  if (!call || !fileId || !board?.id) return null;
  const { mcpPayload } = await importSibling("url-to-paper", "scripts/write-paper-section.mjs");
  const { parkNextInRow } = await importSibling("url-to-paper", "scripts/rulers.mjs");
  const info = mcpPayload(await call("get_basic_info", { fileId }));
  const others = (info.artboards || []).filter((b) => b.id !== board.id);
  const park = parkNextInRow({ boards: others, name, newWidth: parkWidth });
  try {
    await call("update_styles", {
      fileId,
      updates: [{
        nodeIds: [board.id],
        styles: {
          left: `${park.left}px`,
          top: `${park.top}px`,
          width: REVIEW_BOARD_WIDTH,
        },
      }],
    });
  } catch { /* pin is best-effort */ }
  log?.(`${name} pinned ${park.left},${park.top} · ${REVIEW_BOARD_WIDTH}`);
  return park;
}

export async function alignCaptureReviewBoards({
  call, fileId, log = console.error,
} = {}) {
  if (!call || !fileId) return { aligned: 0 };
  const { mcpPayload } = await importSibling("url-to-paper", "scripts/write-paper-section.mjs");
  const { parkNextInRow } = await importSibling("url-to-paper", "scripts/rulers.mjs");
  const info = mcpPayload(await call("get_basic_info", { fileId }));
  const live = [...(info.artboards || [])];
  const row = [
    { name: BUTTONS_BOARD, aliases: BUTTONS_BOARD_ALIASES, parkWidth: REVIEW_BOARD_PARK_WIDTH },
    { name: COMPONENTS_BOARD, aliases: [], parkWidth: REVIEW_BOARD_PARK_WIDTH },
    { name: NAVIGATION_BOARD, aliases: [], parkWidth: NAVIGATION_BOARD_PARK_WIDTH },
  ];
  const updates = [];
  for (const spec of row) {
    const names = [spec.name, ...(spec.aliases || [])];
    const board = live.find((b) => names.includes(b.name));
    if (!board?.id) continue;
    const others = live.filter((b) => b.id !== board.id);
    const park = parkNextInRow({ boards: others, name: spec.name, newWidth: spec.parkWidth });
    updates.push({
      nodeIds: [board.id],
      styles: {
        left: `${park.left}px`,
        top: `${park.top}px`,
        width: REVIEW_BOARD_WIDTH,
      },
    });
    board.worldX = park.left;
    board.worldY = park.top;
    board.width = spec.parkWidth;
  }
  if (updates.length) {
    await call("update_styles", { fileId, updates });
  }
  log(`Capture frames aligned on one Y · ${updates.length} board(s)`);
  return { aligned: updates.length };
}

export async function ensureNavigationBoard({
  call, fileId, log = console.error,
} = {}) {
  if (!call || !fileId) return { ready: false, reason: "need call and file" };
  const { mcpPayload } = await importSibling("url-to-paper", "scripts/write-paper-section.mjs");
  let board = await findBoard(call, NAVIGATION_BOARD, ["Interactive components"]);
  if (!board?.id) {
    const { parkNextInRow } = await importSibling("url-to-paper", "scripts/rulers.mjs");
    const info = mcpPayload(await call("get_basic_info", { fileId }));
    const park = parkNextInRow({
      boards: info.artboards || [],
      name: NAVIGATION_BOARD,
      newWidth: NAVIGATION_BOARD_PARK_WIDTH,
    });
    const created = mcpPayload(await call("create_artboard", {
      fileId,
      name: NAVIGATION_BOARD,
      styles: reviewBoardFrameStyles({ left: park.left, top: park.top }),
    }));
    board = created?.id ? created : await findBoard(call, NAVIGATION_BOARD);
    if (!board?.id) {
      return { ready: false, reason: "Navigation frame creation failed" };
    }
    await pinBoardInRow({
      call, fileId, board, name: NAVIGATION_BOARD, parkWidth: NAVIGATION_BOARD_PARK_WIDTH, log,
    });
  } else {
    await pinBoardInRow({
      call, fileId, board, name: NAVIGATION_BOARD, parkWidth: NAVIGATION_BOARD_PARK_WIDTH, log,
    });
  }

  const boardKids = await children(call, board.id, fileId);
  if (!hasReviewTitle(boardKids)) {
    await writeBoardChildren(call, board.id, fileId, reviewBoardTitleHtml(NAVIGATION_BOARD));
  }
  await stripEmptyReviewRows(call, board.id, fileId);
  return { ready: true, board: NAVIGATION_BOARD };
}

/** Home-desktop `NN ·` section id for the red review-card badge — never dump order. */
export function reviewSectionSid(value = "") {
  const digits = String(value ?? "").replace(/\D/g, "");
  if (!digits) return "";
  return digits.slice(0, 2).padStart(2, "0");
}

export function reviewRowHtml({ name, label, pair, sid = "01" }) {
  const badge = reviewSectionSid(sid) || "01";
  const second = pair
    ? `<div layer-name="second" style="display:flex;width:100%;min-height:48px;"><div layer-name="slot" style="display:flex;width:100%;min-height:48px;"></div></div>`
    : "";
  return `<div layer-name="${name}" style="display:flex;flex-direction:column;gap:16px;width:1600px;padding:24px;background:#ffffff;border-radius:16px;overflow:visible;">
      <div layer-name="title" style="display:flex;align-items:center;gap:12px;">
        <div layer-name="section-number" style="display:flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:36px;background:#E11D2E;flex-shrink:0;">
          <p style="font-family:Inter,sans-serif;font-size:14px;font-weight:700;color:#ffffff;line-height:18px;">${badge}</p>
        </div>
        <p style="font-family:Inter,sans-serif;font-size:14px;font-weight:600;color:#666666;">${label}</p>
      </div>
      <div layer-name="states" style="display:flex;flex-direction:column;gap:16px;">
        <div layer-name="first" style="display:flex;width:100%;min-height:48px;"><div layer-name="slot" style="display:flex;width:100%;min-height:48px;"></div></div>
        ${second}
      </div>
    </div>`;
}

export function buttonsPlaceholderHtml() {
  return reviewBoardTitleHtml(BUTTONS_BOARD);
}

export const hoverStatesPlaceholderHtml = buttonsPlaceholderHtml;

export function componentsPlaceholderHtml() {
  return reviewBoardTitleHtml(COMPONENTS_BOARD);
}

async function ensureNamedReviewBoard({
  call, fileId, name, aliases = [], html, log = console.error,
} = {}) {
  if (!call || !fileId) return { ready: false, reason: "need call and file" };
  const { mcpPayload } = await importSibling("url-to-paper", "scripts/write-paper-section.mjs");
  let board = await findBoard(call, name, aliases);
  if (!board?.id) {
    const { parkNextInRow } = await importSibling("url-to-paper", "scripts/rulers.mjs");
    const info = mcpPayload(await call("get_basic_info", { fileId }));
    const park = parkNextInRow({
      boards: info.artboards || [],
      name,
      newWidth: REVIEW_BOARD_PARK_WIDTH,
    });
    const created = mcpPayload(await call("create_artboard", {
      fileId,
      name,
      styles: reviewBoardFrameStyles({ left: park.left, top: park.top }),
    }));
    board = created?.id ? created : await findBoard(call, name);
    if (!board?.id) return { ready: false, reason: `${name} frame creation failed` };
    try {
      await call("update_styles", {
        fileId,
        updates: [{
          nodeIds: [board.id],
          styles: {
            left: `${park.left}px`,
            top: `${park.top}px`,
            width: REVIEW_BOARD_WIDTH,
          },
        }],
      });
    } catch { /* pin is best-effort */ }
    log(`${name} frame created at ${park.left},${park.top}`);
  }
  const kids = await children(call, board.id, fileId);
  if (!hasReviewTitle(kids)) {
    await writeBoardChildren(call, board.id, fileId, html);
  }
  await stripEmptyReviewRows(call, board.id, fileId);
  return { ready: true, board: name };
}

async function stripEmptyReviewRows(call, boardId, fileId) {
  const kids = await children(call, boardId, fileId);
  const remove = [];
  for (const kid of kids) {
    const n = nameOf(kid);
    if (isNavigationChrome(n)) continue;
    if (!isHoverSpecimen(n) && !/^object\b/i.test(n) && !isNavigationSpecimen(n)) continue;
    if (await hoverGroupIsEmpty(call, kid.id, fileId)) remove.push(kid.id);
  }
  if (remove.length) {
    await call("delete_nodes", { fileId, nodeIds: remove });
  }
}

export async function renameLegacyHoverStatesBoard({ call, fileId } = {}) {
  if (!call || !fileId) return { renamed: false, board: null };
  const current = await findBoard(call, BUTTONS_BOARD);
  if (current?.id) return { renamed: false, board: current };
  const legacy = await findBoard(call, "Hover States");
  if (!legacy?.id) return { renamed: false, board: null };
  await call("rename_nodes", {
    fileId,
    updates: [{ nodeId: legacy.id, name: BUTTONS_BOARD }],
  });
  const title = await findNamed(call, legacy.id, fileId, ["title", "Title"]);
  if (title?.id) {
    const kids = title.component === "Text"
      ? [title]
      : await children(call, title.id, fileId);
    const text = kids.find((n) => n.component === "Text") || (title.component === "Text" ? title : null);
    if (text?.id) {
      try {
        await call("set_text_content", {
          fileId,
          updates: [{ nodeId: text.id, textContent: BUTTONS_BOARD }],
        });
      } catch { /* title restamp is best-effort */ }
    }
  }
  return { renamed: true, board: { ...legacy, name: BUTTONS_BOARD } };
}

export async function ensureButtonsBoard(opts = {}) {
  await renameLegacyHoverStatesBoard(opts);
  return ensureNamedReviewBoard({
    ...opts,
    name: BUTTONS_BOARD,
    aliases: BUTTONS_BOARD_ALIASES,
    html: buttonsPlaceholderHtml(),
  });
}

export const ensureHoverStatesBoard = ensureButtonsBoard;

export async function ensureComponentsBoard(opts = {}) {
  return ensureNamedReviewBoard({
    ...opts,
    name: COMPONENTS_BOARD,
    html: componentsPlaceholderHtml(),
  });
}

/** 1.2 seed: Buttons + Components + Navigation before the 1.3 pull. */
export async function ensureCaptureReviewBoards({ call, fileId, log = console.error } = {}) {
  const buttons = await ensureButtonsBoard({ call, fileId, log });
  if (!buttons.ready) return buttons;
  const components = await ensureComponentsBoard({ call, fileId, log });
  if (!components.ready) return components;
  const navigation = await ensureNavigationBoard({ call, fileId, log });
  if (!navigation.ready) return navigation;
  await alignCaptureReviewBoards({ call, fileId, log });
  return { ready: true, boards: [BUTTONS_BOARD, COMPONENTS_BOARD, NAVIGATION_BOARD] };
}

async function children(call, nodeId, fileId) {
  const { mcpPayload } = await importSibling("url-to-paper", "scripts/write-paper-section.mjs");
  return kidsOf(mcpPayload(await call("get_children", { nodeId, fileId })));
}

async function findChild(call, parentId, fileId, test) {
  const list = await children(call, parentId, fileId);
  return list.find((n) => test(n)) || null;
}

async function findNamed(call, parentId, fileId, names) {
  const want = names.map((n) => String(n).toLowerCase());
  return findChild(call, parentId, fileId, (n) => want.includes(nameOf(n).toLowerCase()));
}

async function deepestSlot(call, nodeId, fileId) {
  let id = nodeId;
  for (let i = 0; i < 8; i += 1) {
    const slot = await findNamed(call, id, fileId, ["slot", "donot-jsx-dump"]);
    if (!slot?.id) return id;
    const inner = await findNamed(call, slot.id, fileId, ["slot", "donot-jsx-dump"]);
    if (!inner?.id) return slot.id;
    id = slot.id;
  }
  return id;
}

async function fillSlot(call, slotId, html, {
  fileId, projectRoot, name = "capture", log, relative = false,
} = {}) {
  if (!slotId || !html) return { written: false };
  const { prepareSectionHtml, mcpPayload } = await importSibling(
    "url-to-paper",
    "scripts/write-paper-section.mjs",
  );
  let source = html;
  if (relative) {
    const { ensureRelativeFlow } = await importSibling("url-to-paper", "scripts/park-nav.mjs");
    source = ensureRelativeFlow(html);
  }
  const prepared = await prepareSectionHtml(source, { projectRoot });
  if (!prepared?.html) return { written: false };
  const kids = await children(call, slotId, fileId);
  if (kids.length) {
    await call("delete_nodes", { fileId, nodeIds: kids.map((n) => n.id) });
  }
  const res = mcpPayload(await call("write_html", {
    html: prepared.html,
    targetNodeId: slotId,
    mode: "insert-children",
    fileId,
  }));
  const nodeId = res.createdNodes?.[0]?.id || res.ids?.[0] || null;
  if (!nodeId) {
    log?.(`  ✗ ${name} → slot empty`);
    return { written: false };
  }
  await call("rename_nodes", { fileId, updates: [{ nodeId, name }] });
  try {
    const styles = { height: "min-content" };
    if (relative) {
      Object.assign(styles, {
        position: "relative",
        left: "auto",
        top: "auto",
        right: "auto",
        bottom: "auto",
      });
    }
    await call("update_styles", {
      fileId,
      updates: [{ nodeIds: [slotId, nodeId], styles }],
    });
  } catch { /* hug is best-effort */ }
  log?.(`  ✓ ${name} → slot`);
  return { written: true, nodeId };
}

async function setGroupLabel(call, groupId, fileId, text) {
  const title = await findNamed(call, groupId, fileId, ["object-name", "title", "Frame"]);
  if (!title?.id) return;
  const kids = await children(call, title.id, fileId);
  const label = kids.find((n) => n.component === "Text" && nameOf(n).toLowerCase() === "object-name")
    || kids.find((n) => n.component === "Text" && !/^\d{2}$/.test(nameOf(n)))
    || kids.find((n) => n.component === "Text")
    || kids[kids.length - 1];
  if (label?.id) {
    await call("set_text_content", { fileId, updates: [{ nodeId: label.id, textContent: text }] });
  }
}

async function stampReviewSectionBadge(call, groupId, fileId, sid) {
  const id = reviewSectionSid(sid);
  if (!id || !groupId) return false;
  const title = await findNamed(call, groupId, fileId, ["title", "Frame"]);
  if (!title?.id) return false;
  const badge = await findNamed(call, title.id, fileId, ["section-number"]);
  if (!badge?.id) return false;
  const num = await children(call, badge.id, fileId);
  const digit = num.find((n) => n.component === "Text") || num[0];
  if (!digit?.id) return false;
  await call("set_text_content", {
    fileId,
    updates: [{ nodeId: digit.id, textContent: id }],
  });
  return true;
}

export function parseDupId(res) {
  if (!res || typeof res !== "object") return null;
  const node = res.createdNodes?.[0] || res.newNodes?.[0] || res.nodes?.[0];
  if (node?.id) return node;
  const id = res.newNodeIds?.[0]
    || res.createdNodeIds?.[0]
    || res.nodeIds?.[0]
    || res.ids?.[0]
    || res.newId
    || (typeof res.id === "string" ? res.id : null);
  if (id) return { id };
  const map = res.descendantIdMap;
  if (map && typeof map === "object") {
    const root = map[res.sourceId] || map[res.sourceNodeId];
    if (typeof root === "string") return { id: root };
  }
  return null;
}

async function duplicateGroup(call, fileId, sourceId, parentId) {
  const { mcpPayload } = await importSibling("url-to-paper", "scripts/write-paper-section.mjs");
  const before = new Set((await children(call, parentId, fileId)).map((n) => n.id));
  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      const raw = mcpPayload(await call("duplicate_nodes", {
        fileId,
        nodes: [{ id: sourceId, parentId }],
      }));
      const copy = parseDupId(raw);
      if (copy?.id && copy.id !== sourceId && !before.has(copy.id)) return copy;
    } catch { /* try nodeIds */ }
    try {
      const copy = parseDupId(mcpPayload(await call("duplicate_nodes", { fileId, nodeIds: [sourceId] })));
      if (copy?.id && copy.id !== sourceId && !before.has(copy.id)) return copy;
    } catch { /* retry */ }
    const after = await children(call, parentId, fileId);
    const fresh = after.find((n) => n.id && !before.has(n.id));
    if (fresh?.id) return fresh;
    await new Promise((r) => setTimeout(r, 400));
  }
  const after = await children(call, parentId, fileId);
  return after.find((n) => n.id && !before.has(n.id)) || null;
}

export function isParkedNavigationName(name) {
  return /^(navbar|dropdown\b)/i.test(String(name || "").trim());
}

export function nextDropdownIndex(nodes = []) {
  const nums = navigationSpecimens(nodes)
    .map((n) => String(n?.name || "").match(/^dropdown\s+(\d+)/i)?.[1])
    .filter(Boolean)
    .map((n) => Number(n));
  return nums.length ? Math.max(...nums) + 1 : 1;
}

async function fillSpecimen(call, group, html, {
  fileId, projectRoot, name, log, pair = true,
} = {}) {
  if (!group?.id || !html) return { written: false };
  await setGroupLabel(call, group.id, fileId, name);
  const states = await findNamed(call, group.id, fileId, ["states", "donot-jsx-dump"]);
  const closedWell = await findNamed(call, states?.id || group.id, fileId, ["closed"]);
  const openWell = await findNamed(call, states?.id || group.id, fileId, ["open"]);
  if (closedWell?.id || openWell?.id) {
    let filled = false;
    if (closedWell?.id) {
      const wrote = await fillSlot(call, await deepestSlot(call, closedWell.id, fileId), html, {
        fileId, projectRoot, name: `${name} closed`, log, relative: true,
      });
      filled = filled || wrote.written;
    }
    if (pair && openWell?.id) {
      const wrote = await fillSlot(call, await deepestSlot(call, openWell.id, fileId), html, {
        fileId, projectRoot, name: `${name} open`, log, relative: true,
      });
      filled = filled || wrote.written;
    }
    return { written: filled };
  }
  const slot = await deepestSlot(call, states?.id || group.id, fileId);
  return fillSlot(call, slot, html, { fileId, projectRoot, name, log, relative: true });
}

async function removeNavbarOpenState(call, groupId, fileId) {
  const states = await findNamed(call, groupId, fileId, ["states", "donot-jsx-dump"]);
  const open = await findNamed(call, states?.id || groupId, fileId, ["open"]);
  if (open?.id) await call("delete_nodes", { fileId, nodeIds: [open.id] });
}

async function ensureSpecimens(call, boardId, fileId, count, log) {
  let groups = navigationSpecimens(await children(call, boardId, fileId));
  if (!groups.length) {
    await writeBoardChildren(call, boardId, fileId, navigationRowHtml());
    groups = navigationSpecimens(await children(call, boardId, fileId));
  }
  const template = groups[0];
  if (!template?.id) {
    log?.("Navigation has no Navbar / Dropdown group");
    return groups;
  }
  while (groups.length < count) {
    const copy = await duplicateGroup(call, fileId, template.id, boardId);
    if (!copy?.id) break;
    const n = groups.length + 1;
    await call("rename_nodes", {
      fileId,
      updates: [{ nodeId: copy.id, name: n === 1 ? "Navbar" : `Dropdown ${String(n - 1).padStart(2, "0")}` }],
    });
    groups.push(copy);
  }
  return groups;
}

export async function navigationHasNavbar(call, fileId) {
  if (!call || !fileId) return false;
  const board = await findBoard(call, NAVIGATION_BOARD, ["Interactive components"]);
  if (!board?.id) return false;
  return (await children(call, board.id, fileId)).some((n) => /^navbar$/i.test(nameOf(n)));
}

const LANDER_NAV_WIDTHS = [
  { suffix: "desktop", width: 1600 },
  { suffix: "768", width: 768 },
  { suffix: "390", width: 390 },
];

/** HUD pills: `done` only when that lander already has a Navbar overlay. */
export async function landerNavbarWidths({ call, fileId, pageSlug = "home" } = {}) {
  const widths = { 1600: "queue", 768: "queue", 390: "queue" };
  if (!call || !fileId) return widths;
  for (const spec of LANDER_NAV_WIDTHS) {
    const board = await findBoard(call, `${pageSlug}-${spec.suffix}`);
    if (!board?.id) continue;
    const kids = await children(call, board.id, fileId);
    if (kids.some((n) => /^navbar$/i.test(nameOf(n)))) widths[spec.width] = "done";
  }
  return widths;
}

export async function paperNavbarsReady({ call, fileId, pageSlug = "home" } = {}) {
  if (!call || !fileId) return false;
  if (!await navigationHasNavbar(call, fileId)) return false;
  const widths = await landerNavbarWidths({ call, fileId, pageSlug });
  return [1600, 768, 390].every((w) => widths[w] === "done");
}

/** Small Overlay nav — never the live Framer header dump. */
export function compactNavbarHtml({ width = 1600, links = width >= 1200 } = {}) {
  const w = Math.round(Number(width) || 1600);
  const brand = `<div style="display:flex;align-items:center;gap:10px;flex-shrink:0;"><div style="width:36px;height:36px;border:2px solid #111111;border-radius:50%;"></div><p style="font-family:system-ui;font-weight:700;font-size:18px;line-height:22px;color:#111111;letter-spacing:0.04em;">BRAND</p></div>`;
  const menu = links
    ? `<div style="display:flex;align-items:center;gap:28px;flex-shrink:0;"><p style="font-family:Satoshi;font-weight:500;font-size:15px;line-height:20px;color:#111111;">Home</p><p style="font-family:Satoshi;font-weight:500;font-size:15px;line-height:20px;color:#111111;">About Us</p><p style="font-family:Satoshi;font-weight:500;font-size:15px;line-height:20px;color:#111111;">Services</p><p style="font-family:Satoshi;font-weight:500;font-size:15px;line-height:20px;color:#111111;">Blog</p><p style="font-family:Satoshi;font-weight:500;font-size:15px;line-height:20px;color:#111111;">Contact Us</p></div>`
    : `<div style="display:flex;flex-direction:column;justify-content:space-between;width:22px;height:16px;flex-shrink:0;"><div style="width:22px;height:2px;background:#111111;"></div><div style="width:22px;height:2px;background:#111111;"></div><div style="width:22px;height:2px;background:#111111;"></div></div>`;
  return `<div layer-name="Navbar" style="display:flex;align-items:center;justify-content:space-between;position:absolute;left:0px;top:0px;width:${w}px;height:72px;padding:0 32px;background:#ffffff;">${brand}${menu}</div>`;
}

const LANDER_NAV_BOARDS = [
  { name: "home-desktop", width: 1600, links: true },
  { name: "home-768", width: 768, links: false },
  { name: "home-390", width: 390, links: false },
];

export async function parkNavbarOnLanders({
  call, fileId, projectRoot, log = console.error, htmlByWidth = {},
} = {}) {
  if (!call || !fileId) return { written: 0 };
  const { writePaperSection, findArtboard, mcpPayload } = await importSibling(
    "url-to-paper",
    "scripts/write-paper-section.mjs",
  );
  let written = 0;
  for (const spec of LANDER_NAV_BOARDS) {
    const found = await findArtboard(call, spec.name);
    if (!found.board?.id) {
      log(`Navbar ${spec.name} — artboard missing`);
      continue;
    }
    const kids = mcpPayload(await call("get_children", { nodeId: found.board.id, fileId }));
    const old = (kids.children || []).filter((n) => /^navbar$/i.test(n.name || ""));
    if (old.length) {
      await call("delete_nodes", { fileId, nodeIds: old.map((n) => n.id) });
    }
    const html = htmlByWidth[spec.width] || compactNavbarHtml(spec);
    if (html.length > 80_000) {
      log(`Navbar ${spec.name} — skipped oversized HTML (${Math.round(html.length / 1024)} KB)`);
      continue;
    }
    const wrote = await writePaperSection({
      call,
      targetId: found.board.id,
      name: "Navbar",
      html,
      projectRoot,
      log,
    });
    if (wrote?.nodeId) {
      try {
        await call("update_styles", {
          fileId,
          updates: [{
            nodeIds: [wrote.nodeId],
            styles: {
              position: "absolute",
              left: "0px",
              top: "0px",
              width: `${spec.width}px`,
              height: "72px",
            },
          }],
        });
      } catch { /* overlay pin is best-effort */ }
      written += 1;
      log(`Navbar overlay last on ${spec.name}`);
    }
  }
  return { written };
}

export async function parkNavbarOnNavigation({
  call, fileId, html, projectRoot, log = console.error, replace = false,
} = {}) {
  if (!html || !fileId) return { written: false, reason: "need html and file" };
  const board = await findBoard(call, NAVIGATION_BOARD, ["Interactive components"]);
  if (!board?.id) {
    log("Navigation board missing — navbar not copied there");
    return { written: false, reason: "no Navigation board" };
  }
  const kids = await children(call, board.id, fileId);
  const existing = kids.filter((n) => /^navbar$/i.test(nameOf(n)));
  const keep = existing[0];
  if (existing.length > 1) {
    try {
      await call("delete_nodes", { fileId, nodeIds: existing.slice(1).map((n) => n.id) });
    } catch { /* extras are best-effort */ }
  }
  if (keep?.id && !replace) {
    const empty = await hoverGroupIsEmpty(call, keep.id, fileId);
    if (!empty) {
      await removeNavbarOpenState(call, keep.id, fileId);
      log("Navbar already on Navigation — left in place");
      return { written: true, skipped: true, board: NAVIGATION_BOARD };
    }
    log("Navbar specimen empty — filling from 1.2 chrome");
  }
  const groups = await ensureSpecimens(call, board.id, fileId, 1, log);
  const group = keep || groups[0];
  if (!group?.id) {
    log("Navigation · Navbar group missing");
    return { written: false, reason: "no Navbar group" };
  }
  await call("rename_nodes", { fileId, updates: [{ nodeId: group.id, name: "Navbar" }] });
  const wrote = await fillSpecimen(call, group, html, {
    fileId, projectRoot, name: "Navbar", log, pair: false,
  });
  if (!wrote.written) {
    log("Navbar → Navigation slot empty");
    return { written: false, reason: "slot empty" };
  }
  await removeNavbarOpenState(call, group.id, fileId);
  log("Navbar → Navigation");
  return { written: true, board: NAVIGATION_BOARD };
}

export async function parkDropdownsOnNavigation({
  call, fileId, pairs = [], projectRoot, log = console.error,
} = {}) {
  if (!pairs.length || !fileId) return { written: 0 };
  const board = await findBoard(call, NAVIGATION_BOARD, ["Interactive components"]);
  if (!board?.id) {
    log("Navigation board missing — dropdowns not copied there");
    return { written: 0 };
  }
  let kids = await children(call, board.id, fileId);
  let groups = navigationSpecimens(kids);
  if (!groups.length) {
    await writeBoardChildren(call, board.id, fileId, navigationRowHtml());
    kids = await children(call, board.id, fileId);
    groups = navigationSpecimens(kids);
  }
  const template = groups[0];
  if (!template?.id) {
    log("Navigation has no Navbar / Dropdown group");
    return { written: 0 };
  }
  let next = nextDropdownIndex(kids);
  let made = 0;
  for (const [i, pair] of pairs.entries()) {
    kids = await children(call, board.id, fileId);
    const stack = navigationSpecimens(kids);
    const last = stack[stack.length - 1] || template;
    const group = await duplicateGroup(call, fileId, template.id, board.id);
    if (!group?.id || group.id === template.id || stack.some((n) => n.id === group.id)) {
      log(`dropdown ${pair.label || i} — duplicate failed`);
      continue;
    }
    const name = `Dropdown ${String(next).padStart(2, "0")}`;
    next += 1;
    await call("rename_nodes", { fileId, updates: [{ nodeId: group.id, name }] });
    const top = Number(last.y ?? last.top ?? 0) + 680;
    try {
      await call("update_styles", {
        fileId,
        updates: [{ nodeIds: [group.id], styles: { top: `${Math.round(top)}px` } }],
      });
    } catch { /* park below last row is best-effort */ }
    const html = pair.openHtml || pair.closedHtml;
    const wrote = await fillSpecimen(call, group, html, {
      fileId, projectRoot, name: pair.label || name, log,
    });
    if (wrote.written) made += 1;
  }
  log(`dropdowns ×${made} → Navigation (new row)`);
  return { written: made };
}

export function isHoverSpecimen(name) {
  return /^component\b/i.test(String(name || "").trim());
}

export function hoverSpecimens(nodes = []) {
  return sortBoardGroups((nodes || []).filter((n) => isHoverSpecimen(nameOf(n))));
}

async function hoverGroupIsEmpty(call, groupId, fileId) {
  if (!groupId) return true;
  const title = await findNamed(call, groupId, fileId, ["title", "Frame"]);
  const titleKids = title?.id ? await children(call, title.id, fileId) : [];
  if (titleKids.some((n) => /placeholder/i.test(String(n.name || n.textContent || "")))) return true;
  const states = await findNamed(call, groupId, fileId, ["states", "donot-jsx-dump"]);
  const first = await findNamed(call, states?.id || groupId, fileId, ["first", "slot"]);
  const slot = await deepestSlot(call, first?.id || states?.id || groupId, fileId);
  const kids = slot ? await children(call, slot, fileId) : [];
  return !kids.length || kids.some((n) => /placeholder/i.test(nameOf(n)));
}

export async function parkOneHoverOnBoard({
  call, fileId, sid, type, label, defaultHtml, hoverHtml = "",
  includeHover = true, captureMethod = "", kind = "buttons", projectRoot, log = console.error,
} = {}) {
  if (!call || !fileId || !defaultHtml) return { written: false };
  const board = await findBoard(call, BUTTONS_BOARD, BUTTONS_BOARD_ALIASES);
  if (!board?.id) {
    log("Buttons missing — hover take not parked");
    return { written: false, reason: "no Buttons" };
  }
  const id = String(sid || "").replace(/\D/g, "").padStart(2, "0").slice(0, 2) || "01";
  const name = label || objectTypeLabel({ type, captureMethod }, kind) || type || "Button";
  let kids = await children(call, board.id, fileId);
  let stack = hoverSpecimens(kids);
  let template = stack[0];
  if (!template?.id) {
    await writeBoardChildren(call, board.id, fileId, reviewRowHtml({
      name: "Component 01",
      label: name,
      pair: true,
      sid: id,
    }));
    kids = await children(call, board.id, fileId);
    stack = hoverSpecimens(kids);
    template = stack[0];
  }
  if (!template?.id) {
    log("Buttons could not create a Component row");
    return { written: false, reason: "no template" };
  }
  let group = template;
  const empty = await hoverGroupIsEmpty(call, template.id, fileId);
  if (!empty) {
    const last = stack[stack.length - 1] || template;
    group = await duplicateGroup(call, fileId, template.id, board.id);
    if (!group?.id || group.id === template.id || stack.some((n) => n.id === group.id)) {
      log(`  ✗ ${id} · ${name} — duplicate failed`);
      return { written: false };
    }
    const top = Number(last.y ?? last.top ?? 0) + Number(last.height || 487) + 24;
    try {
      await call("update_styles", {
        fileId,
        updates: [{ nodeIds: [group.id], styles: { top: `${Math.round(top)}px` } }],
      });
    } catch { /* stack below last is best-effort */ }
  }
  const index = empty ? 1 : stack.length + 1;
  const rowName = `Component ${String(index).padStart(2, "0")}`;
  await call("rename_nodes", { fileId, updates: [{ nodeId: group.id, name: rowName }] });
  await setGroupLabel(call, group.id, fileId, name);
  await stampReviewSectionBadge(call, group.id, fileId, id);
  const states = await findNamed(call, group.id, fileId, ["states", "donot-jsx-dump"]);
  const first = await findNamed(call, states?.id || group.id, fileId, ["first"]);
  const second = await findNamed(call, states?.id || group.id, fileId, ["second"]);
  let wrote = { written: false };
  if (first?.id) {
    wrote = await fillSlot(call, await deepestSlot(call, first.id, fileId), defaultHtml, {
      fileId, projectRoot, name: `${name} default`, log,
    });
  }
  if (includeHover && hoverHtml && second?.id) {
    await fillSlot(call, await deepestSlot(call, second.id, fileId), hoverHtml, {
      fileId, projectRoot, name: `${name} hover`, log,
    });
  }
  try {
    await call("update_styles", {
      fileId,
      updates: [{ nodeIds: [board.id], styles: { width: REVIEW_BOARD_WIDTH, height: "fit-content" } }],
    });
  } catch { /* hug board */ }
  if (!wrote.written) {
    log(`  ✗ ${id} · ${name} → Buttons`);
    return { written: false };
  }
  log(`  ✓ ${id} · ${name} → Buttons (${empty ? "placeholder" : "stacked"})`);
  return { written: true, board: BUTTONS_BOARD, nodeId: group.id };
}

export async function parkTakesOnComponents({
  call, fileId, items = [], projectRoot, log = console.error, append = false,
} = {}) {
  if (!items.length || !fileId) return { written: 0 };
  const board = await findBoard(call, COMPONENTS_BOARD);
  if (!board?.id) {
    log("Components board missing — component takes not parked");
    return { written: 0 };
  }
  let kids = await children(call, board.id, fileId);
  const pickTemplates = (list) => {
    const pairTemplates = sortBoardGroups(list.filter((n) => /^component/i.test(nameOf(n))));
    const soloTemplates = sortBoardGroups(list.filter((n) => /^object/i.test(nameOf(n))));
    return {
      pair: append ? pairTemplates.at(-1) : pairTemplates[0],
      solo: append ? soloTemplates.at(-1) : soloTemplates[0],
    };
  };
  const templates = pickTemplates(kids);
  let pairN = append ? nextComponentIndex(kids, "Component") - 1 : 0;
  let soloN = append ? nextComponentIndex(kids, "Object") - 1 : 0;
  let made = 0;
  for (const item of items) {
    const pair = isHumanClickPair(item);
    let template = pair ? templates.pair : templates.solo;
    if (!template?.id) {
      const rowName = `${pair ? "Component" : "Object"} 01`;
      await writeBoardChildren(call, board.id, fileId, reviewRowHtml({
        name: rowName,
        label: item.label || (pair ? "Multi-state" : "Single component"),
        pair,
        sid: item.sid || "01",
      }));
      kids = await children(call, board.id, fileId);
      Object.assign(templates, pickTemplates(kids));
      template = pair ? templates.pair : templates.solo;
    }
    if (!template?.id) {
      log(`Components row missing for ${item.label || item.kind}`);
      continue;
    }
    const index = pair ? ++pairN : ++soloN;
    let group = template;
    if ((append || index > 1) && (pair ? pairN > 1 : soloN > 1)) {
      group = await duplicateGroup(call, fileId, template.id, board.id);
      if (!group?.id) {
        log(`Components duplicate failed for ${item.label || item.kind}`);
        continue;
      }
    }
    const name = `${pair ? "Component" : "Object"} ${String(index).padStart(2, "0")}`;
    if (group?.id) {
      await call("rename_nodes", { fileId, updates: [{ nodeId: group.id, name }] });
      await setGroupLabel(call, group.id, fileId, item.label || name);
      await stampReviewSectionBadge(
        call, group.id, fileId,
        item.sid || item.sectionId || String(index).padStart(2, "0"),
      );
      const states = await findNamed(call, group.id, fileId, ["states", "donot-jsx-dump"]);
      if (pair) {
        const first = await findNamed(call, states?.id || group.id, fileId, ["first"]);
        const second = await findNamed(call, states?.id || group.id, fileId, ["second"]);
        if (item.defaultHtml && first?.id) {
          await fillSlot(call, await deepestSlot(call, first.id, fileId), item.defaultHtml, {
            fileId, projectRoot, name: `${item.label} 01`, log,
          });
        }
        if (item.hoverHtml && second?.id) {
          await fillSlot(call, await deepestSlot(call, second.id, fileId), item.hoverHtml, {
            fileId, projectRoot, name: `${item.label} 02`, log,
          });
        }
      } else if (item.defaultHtml) {
        const first = await findNamed(call, states?.id || group.id, fileId, ["first", "slot"]);
        await fillSlot(call, await deepestSlot(call, first?.id || states?.id || group.id, fileId), item.defaultHtml, {
          fileId, projectRoot, name: item.label || name, log,
        });
      }
      made += 1;
      if (append) templates[pair ? "pair" : "solo"] = group;
    }
  }
  try {
    await call("update_styles", {
      fileId,
      updates: [{ nodeIds: [board.id], styles: { width: REVIEW_BOARD_WIDTH, height: "fit-content" } }],
    });
  } catch { /* hug board */ }
  log(`takes ×${made} → Components`);
  return { written: made };
}

export async function parkDesktopNodeOnBoard({
  call, fileId, boardName, aliases = [], sourceNodeId, label, sid, kind = "button",
  log = console.error,
} = {}) {
  if (!call || !fileId || !sourceNodeId) return { written: false, reason: "need source node" };
  const board = await findBoard(call, boardName, aliases);
  if (!board?.id) return { written: false, reason: `no ${boardName}` };
  const prefix = kind === "component" ? "Object" : "Component";
  let kids = await children(call, board.id, fileId);
  let stack = sortBoardGroups(kids.filter((n) => new RegExp(`^${prefix}\\b`, "i").test(nameOf(n))));
  let template = stack[0];
  const id = reviewSectionSid(sid);
  if (!id) return { written: false, reason: "need section id" };
  const rowLabel = label || `${prefix} ${id}`;
  if (!template?.id) {
    await writeBoardChildren(call, board.id, fileId, reviewRowHtml({
      name: `${prefix} 01`,
      label: rowLabel,
      pair: false,
      sid: id,
    }));
    kids = await children(call, board.id, fileId);
    stack = sortBoardGroups(kids.filter((n) => new RegExp(`^${prefix}\\b`, "i").test(nameOf(n))));
    template = stack[0];
  }
  if (!template?.id) return { written: false, reason: "no template" };
  let group = template;
  const empty = await hoverGroupIsEmpty(call, template.id, fileId);
  if (!empty) {
    const last = stack[stack.length - 1] || template;
    group = await duplicateGroup(call, fileId, template.id, board.id);
    if (!group?.id || group.id === template.id) {
      log(`  ✗ ${id} · ${rowLabel} — duplicate row failed`);
      return { written: false };
    }
    const top = Number(last.y ?? last.top ?? 0) + Number(last.height || 280) + 24;
    try {
      await call("update_styles", {
        fileId,
        updates: [{ nodeIds: [group.id], styles: { top: `${Math.round(top)}px` } }],
      });
    } catch { /* stack below last is best-effort */ }
  }
  const index = empty ? 1 : stack.length + 1;
  const rowName = `${prefix} ${String(index).padStart(2, "0")}`;
  await call("rename_nodes", { fileId, updates: [{ nodeId: group.id, name: rowName }] });
  await setGroupLabel(call, group.id, fileId, rowLabel);
  await stampReviewSectionBadge(call, group.id, fileId, id);
  const states = await findNamed(call, group.id, fileId, ["states", "donot-jsx-dump"]);
  const first = await findNamed(call, states?.id || group.id, fileId, ["first", "slot"]);
  const slotId = await deepestSlot(call, first?.id || states?.id || group.id, fileId);
  const slotKids = slotId ? await children(call, slotId, fileId) : [];
  if (slotKids.length) {
    await call("delete_nodes", { fileId, nodeIds: slotKids.map((n) => n.id) });
  }
  const copy = await duplicateGroup(call, fileId, sourceNodeId, slotId);
  if (!copy?.id) {
    log(`  ✗ ${id} · ${rowLabel} → ${boardName} (duplicate node failed)`);
    return { written: false };
  }
  try {
    await call("update_styles", {
      fileId,
      updates: [
        {
          nodeIds: [copy.id],
          styles: {
            position: "relative",
            left: "auto",
            top: "auto",
            width: "fit-content",
            height: "fit-content",
          },
        },
        {
          nodeIds: [board.id],
          styles: { width: REVIEW_BOARD_WIDTH, height: "fit-content" },
        },
      ],
    });
  } catch { /* hug is best-effort */ }
  log(`  ✓ ${id} · ${rowLabel} → ${boardName}`);
  return { written: true, board: boardName, nodeId: group.id, parkedNodeId: copy.id };
}

/** Duplicate a parked default CTA into the Hover cell and apply source CSS paint. */
export async function parkCssHoverOnRow({
  call, fileId, groupId, parkedNodeId, styles = {}, label = "hover", log = console.error,
} = {}) {
  if (!call || !fileId || !groupId || !parkedNodeId) {
    return { written: false, reason: "need row and parked node" };
  }
  const states = await findNamed(call, groupId, fileId, ["states", "donot-jsx-dump"]);
  let second = await findNamed(call, states?.id || groupId, fileId, ["second"]);
  if (!second?.id && states?.id) {
    await writeBoardChildren(call, states.id, fileId, `
      <div layer-name="second" style="display:flex;width:100%;min-height:48px;">
        <div layer-name="slot" style="display:flex;width:100%;min-height:48px;"></div>
      </div>`);
    second = await findNamed(call, states.id, fileId, ["second"]);
  }
  if (!second?.id) return { written: false, reason: "no hover slot" };
  const slotId = await deepestSlot(call, second.id, fileId);
  const slotKids = slotId ? await children(call, slotId, fileId) : [];
  if (slotKids.length) {
    await call("delete_nodes", { fileId, nodeIds: slotKids.map((n) => n.id) });
  }
  const copy = await duplicateGroup(call, fileId, parkedNodeId, slotId);
  if (!copy?.id) return { written: false, reason: "hover duplicate failed" };
  const paint = {};
  for (const [key, value] of Object.entries(styles)) {
    if (value) paint[key] = value;
  }
  try {
    await call("update_styles", {
      fileId,
      updates: [{
        nodeIds: [copy.id],
        styles: {
          position: "relative",
          left: "auto",
          top: "auto",
          width: "fit-content",
          height: "fit-content",
          ...paint,
        },
      }],
    });
  } catch { /* paint is best-effort */ }
  try {
    await call("rename_nodes", { fileId, updates: [{ nodeId: copy.id, name: `${label} hover` }] });
  } catch { /* name is best-effort */ }
  log(`  ✓ hover · ${label}`);
  return { written: true, hoverNodeId: copy.id };
}

