#!/usr/bin/env node
// 1.3 — after Design Library + token seed, park unique buttons and
// components from token-seeded home-desktop onto FRAME Buttons / Components.
// The agent identifies the nodes. This script duplicates them and writes
// qa/buttons-components-pull.json.

import { mkdirSync, readFileSync, realpathSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { importSibling } from "./skill-paths.mjs";
import {
  BUTTONS_BOARD,
  BUTTONS_BOARD_ALIASES,
  COMPONENTS_BOARD,
} from "./component-state-utils.mjs";
import {
  ensureButtonsBoard,
  ensureComponentsBoard,
  boardsClear,
  clearReviewBoardOverlap,
  parkDesktopNodeOnBoard,
  renameLegacyHoverStatesBoard,
  restackReviewBoard,
  reviewSectionSid,
  sectionOrderOk,
} from "./park-capture-boards.mjs";

const WRITER = "pull-desktop-specimens.mjs";
export { reviewSectionSid };

export function sectionNameFromScan(scannedSections = [], sid = "") {
  const needle = reviewSectionSid(sid);
  if (!needle) return "";
  for (const row of scannedSections) {
    if (reviewSectionSid(row) === needle) {
      return String(row).replace(/^\s*\d{1,2}\s*·\s*/, "").trim();
    }
  }
  return "";
}

function rowSectionSid(row = {}) {
  return reviewSectionSid(row.sectionId || row.sid);
}

function rowOk(row, allowed) {
  return Boolean(row?.sourceNodeId) && allowed.has(rowSectionSid(row));
}

export function specimenPlanOk(plan = {}) {
  if (!plan || typeof plan !== "object") return false;
  if (!Array.isArray(plan.scannedSections) || plan.scannedSections.length < 1) return false;
  if (!plan.scannedSections.every((row) => reviewSectionSid(row))) return false;
  if (!Array.isArray(plan.buttons) || !Array.isArray(plan.components)) return false;
  const allowed = new Set(plan.scannedSections.map(reviewSectionSid));
  return plan.buttons.every((row) => rowOk(row, allowed))
    && plan.components.every((row) => rowOk(row, allowed));
}

export function sortPlanRows(rows = []) {
  return [...rows].sort((a, b) => {
    const as = Number(reviewSectionSid(a?.sectionId || a?.sid)) || 999;
    const bs = Number(reviewSectionSid(b?.sectionId || b?.sid)) || 999;
    if (as !== bs) return as - bs;
    return String(a?.label || "").localeCompare(String(b?.label || ""));
  });
}

export function pullReceiptOk(receipt = {}) {
  return receipt?.ok === true
    && receipt.writer === WRITER
    && receipt.geometry?.ok === true
    && Array.isArray(receipt.scannedSections)
    && receipt.scannedSections.length >= 1
    && Array.isArray(receipt.buttons)
    && Array.isArray(receipt.components);
}

function requiredArg(argv, name) {
  const i = argv.indexOf(`--${name}`);
  const value = i >= 0 ? argv[i + 1] : "";
  if (!value || value.startsWith("--")) {
    throw new Error(`pull-desktop-specimens.mjs requires --${name}`);
  }
  return value;
}

function loadPlan(path) {
  const plan = JSON.parse(readFileSync(path, "utf8"));
  if (!specimenPlanOk(plan)) {
    throw new Error(
      "qa/buttons-components-plan.json needs scannedSections (NN ·) plus buttons[] / components[] with sourceNodeId and sectionId matching a scanned section",
    );
  }
  return plan;
}

function sidOf(row) {
  const sid = rowSectionSid(row);
  if (!sid) {
    throw new Error(`1.3 pull row needs sectionId (home-desktop NN): ${row?.label || row?.sourceNodeId || "unknown"}`);
  }
  return sid;
}

function parkedRow(row, parked, scannedSections) {
  const sid = sidOf(row);
  return {
    id: sid,
    label: row.label || "",
    sectionId: sid,
    sectionName: row.sectionName || sectionNameFromScan(scannedSections, sid),
    sourceNodeId: row.sourceNodeId,
    parkedNodeId: parked.parkedNodeId,
    rowNodeId: parked.nodeId,
  };
}

export async function pullDesktopSpecimens({
  call, fileId, projectRoot, plan, now = () => new Date().toISOString(),
  log = console.error,
} = {}) {
  if (!specimenPlanOk(plan)) {
    throw new Error("1.3 pull needs scanned NN · sections and sectionId on every specimen");
  }
  const renamed = await renameLegacyHoverStatesBoard({ call, fileId });
  const buttonsBoard = await ensureButtonsBoard({ call, fileId, log });
  if (!buttonsBoard.ready) throw new Error("1.3 pull needs FRAME Buttons");
  const componentsBoard = await ensureComponentsBoard({ call, fileId, log });
  if (!componentsBoard.ready) throw new Error("1.3 pull needs FRAME Components");

  const buttons = [];
  for (const row of sortPlanRows(plan.buttons)) {
    const parked = await parkDesktopNodeOnBoard({
      call, fileId,
      boardName: BUTTONS_BOARD,
      aliases: BUTTONS_BOARD_ALIASES,
      sourceNodeId: row.sourceNodeId,
      label: row.label,
      sid: sidOf(row),
      kind: "button",
      log,
    });
    if (!parked.written) {
      throw new Error(`Buttons park failed: ${row.label || row.sourceNodeId} (${parked.reason || "unknown"})`);
    }
    buttons.push(parkedRow(row, parked, plan.scannedSections));
  }

  const components = [];
  for (const row of sortPlanRows(plan.components)) {
    const parked = await parkDesktopNodeOnBoard({
      call, fileId,
      boardName: COMPONENTS_BOARD,
      aliases: [],
      sourceNodeId: row.sourceNodeId,
      label: row.label,
      sid: sidOf(row),
      kind: "component",
      log,
    });
    if (!parked.written) {
      throw new Error(`Components park failed: ${row.label || row.sourceNodeId} (${parked.reason || "unknown"})`);
    }
    components.push(parkedRow(row, parked, plan.scannedSections));
  }

  const stackedButtons = await restackReviewBoard(call, fileId, BUTTONS_BOARD, BUTTONS_BOARD_ALIASES);
  const stackedComponents = await restackReviewBoard(call, fileId, COMPONENTS_BOARD);
  if (stackedButtons.reason || stackedComponents.reason) {
    throw new Error(`1.3 restack failed: ${stackedButtons.reason || stackedComponents.reason}`);
  }
  if (!sectionOrderOk(stackedButtons.order) || !sectionOrderOk(stackedComponents.order)) {
    throw new Error("1.3 rows are not in section NN order");
  }
  await clearReviewBoardOverlap({ call, fileId, log });
  const { mcpPayload } = await importSibling("url-to-paper", "scripts/write-paper-section.mjs");
  const info = mcpPayload(await call("get_basic_info", { fileId }));
  const boards = info.artboards || [];
  const clearance = boardsClear(
    boards.find((board) => board.name === BUTTONS_BOARD || board.name === "Hover States"),
    boards.find((board) => board.name === COMPONENTS_BOARD),
  );
  if (!clearance.ok) {
    throw new Error(`1.3 board clearance failed: ${clearance.reason}`);
  }

  const receipt = {
    ok: true,
    writer: WRITER,
    geometry: {
      ok: true,
      sourceWidth: true,
      hugged: true,
      sectionOrder: true,
      clearance: clearance.left,
    },
    completedAt: now(),
    fileId,
    boardButtons: BUTTONS_BOARD,
    boardComponents: COMPONENTS_BOARD,
    renamedFrom: renamed.renamed ? "Hover States" : null,
    scannedSections: plan.scannedSections,
    buttons,
    components,
  };
  const root = resolve(projectRoot);
  const dest = join(root, "qa", "buttons-components-pull.json");
  mkdirSync(dirname(dest), { recursive: true });
  writeFileSync(dest, `${JSON.stringify(receipt, null, 2)}\n`, "utf8");
  const { authorButtonHover } = await import("./author-button-hover.mjs");
  await authorButtonHover({ call, fileId, projectRoot, pull: receipt, now, log });
  return receipt;
}

const invoked = process.argv[1]
  && realpathSync(fileURLToPath(import.meta.url)) === realpathSync(resolve(process.argv[1]));

if (invoked) {
  try {
    const argv = process.argv.slice(2);
    const projectRoot = requiredArg(argv, "project");
    const fileId = requiredArg(argv, "file-id");
    const planPath = argv.includes("--plan")
      ? requiredArg(argv, "plan")
      : join(resolve(projectRoot), "qa", "buttons-components-plan.json");
    const plan = loadPlan(planPath);
    const { call, setFileId } = await importSibling("url-to-paper", "scripts/mcp-client.mjs");
    setFileId(fileId);
    const receipt = await pullDesktopSpecimens({
      call, fileId, projectRoot, plan,
    });
    console.log(JSON.stringify(receipt, null, 2));
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
