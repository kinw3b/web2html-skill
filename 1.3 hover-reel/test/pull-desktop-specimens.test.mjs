import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  pullDesktopSpecimens,
  pullReceiptOk,
  sectionNameFromScan,
  specimenPlanOk,
} from "../scripts/pull-desktop-specimens.mjs";
import {
  BUTTONS_BOARD,
  isButtonsBoard,
} from "../scripts/component-state-utils.mjs";
import {
  REVIEW_ROW_FILL,
  REVIEW_ROW_LABEL,
  reviewRowHtml,
  reviewSectionSid,
} from "../scripts/park-capture-boards.mjs";

test("Buttons is the canonical review board; Hover States is a legacy alias", () => {
  assert.equal(BUTTONS_BOARD, "Buttons");
  assert.equal(isButtonsBoard("Buttons"), true);
  assert.equal(isButtonsBoard("Hover States"), true);
  assert.equal(isButtonsBoard("Components"), false);
});

test("review card badge is the home-desktop section NN, title is the specimen name", () => {
  assert.equal(reviewSectionSid("02 · features"), "02");
  assert.equal(reviewSectionSid("2"), "02");
  assert.equal(sectionNameFromScan(["02 · features"], "02"), "features");
  const row = reviewRowHtml({
    name: "Object 01",
    label: "Content Widget",
    pair: false,
    sid: "02",
  });
  assert.match(row, /layer-name="section-number"/);
  assert.match(row, />02</);
  assert.match(row, />Content Widget</);
  assert.doesNotMatch(row, />01</);
  assert.match(row, new RegExp(`background:${REVIEW_ROW_FILL}`, "i"));
  assert.doesNotMatch(row, /background:#ffffff/i);
  assert.match(row, new RegExp(`color:${REVIEW_ROW_LABEL}`, "i"));
});

test("1.3 pull plan requires scanned NN sections and matching sectionId on every row", () => {
  assert.equal(specimenPlanOk({}), false);
  assert.equal(specimenPlanOk({
    scannedSections: ["01 · hero"],
    buttons: [{ sourceNodeId: "btn-1", label: "Primary" }],
    components: [],
  }), false);
  assert.equal(specimenPlanOk({
    scannedSections: ["01 · hero"],
    buttons: [{ sourceNodeId: "btn-1", label: "Primary", sectionId: "01" }],
    components: [],
  }), true);
  assert.equal(specimenPlanOk({
    scannedSections: ["01 · hero", "02 · features"],
    buttons: [],
    components: [{ sourceNodeId: "card-1", label: "Content Widget", sectionId: "99" }],
  }), false);
  assert.equal(specimenPlanOk({
    scannedSections: ["01 · hero"],
    buttons: [{ label: "Primary", sectionId: "01" }],
    components: [],
  }), false);
  assert.equal(specimenPlanOk({
    scannedSections: [],
    buttons: [],
    components: [],
  }), false);
});

test("1.3 pull receipt is the 1.3 done artifact", () => {
  assert.equal(pullReceiptOk({}), false);
  assert.equal(pullReceiptOk({
    ok: true,
    writer: "pull-desktop-specimens.mjs",
    scannedSections: ["01 · hero"],
    buttons: [],
    components: [],
  }), true);
});

function paperCall({ artboards, children, texts = [], htmlWrites = [] }) {
  const reply = (payload) => ({ content: [{ type: "text", text: JSON.stringify(payload) }] });
  let rows = 0;
  let dups = 0;

  function seedRow(rowId) {
    children.set(rowId, [
      { id: `${rowId}-title`, name: "title", component: "Frame" },
      { id: `${rowId}-states`, name: "states", component: "Frame" },
    ]);
    children.set(`${rowId}-title`, [
      { id: `${rowId}-badge`, name: "section-number", component: "Frame" },
      { id: `${rowId}-label`, name: "object-name", component: "Text" },
    ]);
    children.set(`${rowId}-badge`, [
      { id: `${rowId}-digit`, name: "01", component: "Text", textContent: "01" },
    ]);
    children.set(`${rowId}-states`, [
      { id: `${rowId}-first`, name: "first", component: "Frame" },
    ]);
    children.set(`${rowId}-first`, [
      { id: `${rowId}-slot`, name: "slot", component: "Frame" },
    ]);
    children.set(`${rowId}-slot`, []);
  }

  function cloneTree(sourceId, copyId) {
    const srcKids = children.get(sourceId);
    if (!srcKids) return;
    children.set(copyId, srcKids.map((kid) => {
      const nextId = `${copyId}/${kid.id}`;
      cloneTree(kid.id, nextId);
      return { ...kid, id: nextId };
    }));
  }

  return async (method, args = {}) => {
    if (method === "get_basic_info") return reply({ artboards });
    if (method === "get_children") return reply({ children: children.get(args.nodeId) || [] });
    if (method === "rename_nodes") {
      for (const update of args.updates || []) {
        const board = artboards.find((b) => b.id === update.nodeId);
        if (board && update.name) board.name = update.name;
      }
      return reply({});
    }
    if (method === "write_html") {
      htmlWrites.push(args.html || "");
      const rowId = `${args.targetNodeId}-row-${++rows}`;
      seedRow(rowId);
      const rowName = /layer-name="Object /i.test(args.html || "") ? "Object 01" : "Component 01";
      children.set(args.targetNodeId, [
        ...(children.get(args.targetNodeId) || []),
        { id: rowId, name: rowName, component: "Frame" },
      ]);
      return reply({ createdNodes: [{ id: rowId }] });
    }
    if (method === "duplicate_nodes") {
      const sourceId = args.nodes?.[0]?.id || args.nodeIds?.[0];
      const parentId = args.nodes?.[0]?.parentId;
      const copy = { id: `${sourceId}-copy-${++dups}`, name: "specimen" };
      if (parentId) {
        children.set(parentId, [...(children.get(parentId) || []), copy]);
      }
      cloneTree(sourceId, copy.id);
      return reply({ createdNodes: [copy] });
    }
    if (method === "set_text_content") {
      texts.push(...(args.updates || []));
      return reply({});
    }
    if (method === "delete_nodes") {
      for (const id of args.nodeIds || []) children.set(id, []);
      return reply({});
    }
    return reply({});
  };
}

test("pullDesktopSpecimens parks plan nodes and writes the receipt", async () => {
  const root = mkdtempSync(join(tmpdir(), "pull-specimens-"));
  const artboards = [
    { id: "buttons", name: "Hover States" },
    { id: "components", name: "Components" },
    { id: "desktop", name: "home-desktop" },
  ];
  const children = new Map([
    ["buttons", [{ id: "b-title", name: "Title", component: "Text" }]],
    ["components", [{ id: "c-title", name: "Title", component: "Text" }]],
    ["desktop", [{ id: "btn-1", name: "Get Started Now" }]],
  ]);
  const receipt = await pullDesktopSpecimens({
    call: paperCall({ artboards, children }),
    fileId: "paper",
    projectRoot: root,
    plan: {
      scannedSections: ["01 · hero"],
      buttons: [{ sourceNodeId: "btn-1", label: "Primary - Get Started Now", sectionId: "01" }],
      components: [],
    },
    now: () => "2026-09-07T00:00:00.000Z",
  });

  assert.equal(receipt.ok, true);
  assert.equal(receipt.boardButtons, "Buttons");
  assert.equal(receipt.renamedFrom, "Hover States");
  assert.equal(receipt.buttons.length, 1);
  assert.equal(receipt.buttons[0].label, "Primary - Get Started Now");
  assert.equal(receipt.buttons[0].sectionId, "01");
  assert.ok(receipt.buttons[0].parkedNodeId);
  assert.ok(receipt.buttons[0].rowNodeId);
  assert.equal(artboards.find((b) => b.id === "buttons").name, "Buttons");
  const disk = JSON.parse(readFileSync(join(root, "qa", "buttons-components-pull.json"), "utf8"));
  assert.equal(pullReceiptOk(disk), true);
  const hover = JSON.parse(readFileSync(join(root, "qa", "button-hover.json"), "utf8"));
  assert.equal(hover.writer, "author-button-hover.mjs");
  assert.equal(hover.ok, true);
});

test("two Components from the same lander section keep that section badge", async () => {
  const root = mkdtempSync(join(tmpdir(), "pull-section-badge-"));
  const artboards = [
    { id: "buttons", name: "Buttons" },
    { id: "components", name: "Components" },
  ];
  const children = new Map([
    ["buttons", [{ id: "b-title", name: "Title", component: "Text" }]],
    ["components", [{ id: "c-title", name: "Title", component: "Text" }]],
    ["card-a", []],
    ["card-b", []],
  ]);
  const texts = [];
  const htmlWrites = [];
  const receipt = await pullDesktopSpecimens({
    call: paperCall({ artboards, children, texts, htmlWrites }),
    fileId: "paper",
    projectRoot: root,
    plan: {
      scannedSections: ["01 · hero", "02 · features"],
      buttons: [],
      components: [
        { sourceNodeId: "card-a", label: "Content Widget", sectionId: "02" },
        { sourceNodeId: "card-b", label: "Integrate Card Medium", sectionId: "02 · features" },
      ],
    },
  });

  assert.equal(receipt.components.length, 2);
  assert.deepEqual(receipt.components.map((row) => row.sectionId), ["02", "02"]);
  assert.deepEqual(receipt.components.map((row) => row.sectionName), ["features", "features"]);
  assert.match(htmlWrites[0], />02</);
  assert.match(htmlWrites[0], />Content Widget</);
  const badgeStamps = texts.filter((row) => /^\d{2}$/.test(String(row.textContent || "")));
  assert.ok(badgeStamps.length >= 2);
  assert.ok(badgeStamps.every((row) => row.textContent === "02"));
  assert.ok(texts.some((row) => row.textContent === "Content Widget"));
  assert.ok(texts.some((row) => row.textContent === "Integrate Card Medium"));
});
