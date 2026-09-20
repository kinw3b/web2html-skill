import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  applyCapturePaintWitness,
  isCaptureFillWitness,
  loadCapturePaintIndex,
  parseCaptureHtmlPaints,
  parseInlineStyle,
} from "../scripts/capture-paints.mjs";
import {
  closestColorToken,
  dropInventedFillChanges,
  exactColorToken,
  isSectionStack,
  isUnpaintedFill,
  mineFromStyledNodes,
  proposeLibraryTokens,
  themeTokenPass,
  toPaintedHex,
} from "../scripts/library-tokens.mjs";

test("parseInlineStyle keeps background-color distinct from border-*-color", () => {
  const style = parseInlineStyle(
    "border-bottom-color: rgb(0, 0, 0); background-color: rgb(239, 75, 60); color: rgb(255, 255, 255)",
  );
  assert.equal(style["background-color"], "rgb(239, 75, 60)");
  assert.equal(style.color, "rgb(255, 255, 255)");
});

test("toPaintedHex keeps 10% wash alpha", () => {
  assert.equal(toPaintedHex("rgb(239, 75, 60)"), "#EF4B3C");
  assert.equal(toPaintedHex("rgba(239, 75, 60, 0.1)"), "#EF4B3C1A");
});

test("capture fill witness is brand paint, not cream or white", () => {
  assert.equal(isCaptureFillWitness("rgb(239, 75, 60)"), true);
  assert.equal(isCaptureFillWitness("rgba(239, 75, 60, 0.1)"), true);
  assert.equal(isCaptureFillWitness("rgb(247, 243, 237)"), false);
  assert.equal(isCaptureFillWitness("rgb(255, 255, 255)"), false);
  assert.equal(isCaptureFillWitness("transparent"), false);
});

test("parseCaptureHtmlPaints still reads rgb vs rgba on legacy named layers", () => {
  const html = [
    `<div layer-name="pc-0.cta" style="background-color: rgb(239, 75, 60); color: rgb(255, 255, 255)"></div>`,
    `<div layer-name="pc-0.well" style="background-color: rgba(239, 75, 60, 0.1)"></div>`,
    `<div layer-name="pc-0.cream" style="background-color: rgb(247, 243, 237)"></div>`,
  ].join("");
  const paints = parseCaptureHtmlPaints(html);
  assert.deepEqual(
    paints.map((p) => [p.pcId, p.backgroundColor]),
    [["pc-0.cta", "#EF4B3C"], ["pc-0.well", "#EF4B3C1A"]],
  );
});

function fixtureProject() {
  const root = mkdtempSync(join(tmpdir(), "capture-paints-"));
  const dir = join(root, "capture", "home-desktop");
  mkdirSync(dir, { recursive: true });
  writeFileSync(join(dir, "paper-layer-ids.json"), JSON.stringify({
    ids: {
      "pc-0.cta": "cta-node",
      "pc-0.well": "well-node",
      "pc-0.footer": "footer-node",
    },
  }));
  writeFileSync(join(dir, "01-hero-sections.html"), [
    `<div layer-name="pc-0.cta" style="background-color: rgb(239, 75, 60)"></div>`,
    `<div layer-name="pc-0.well" style="background-color: rgba(239, 75, 60, 0.1)"></div>`,
    `<div layer-name="pc-0.footer" style="background-color: rgb(239, 75, 60)"></div>`,
  ].join(""));
  return root;
}

test("collapsed Paper fills restore from capture HTML before bind", () => {
  const root = fixtureProject();
  const index = loadCapturePaintIndex(root);
  assert.equal(index.paints.length, 3);
  assert.equal(index.byNodeId.get("cta-node").backgroundColor, "#EF4B3C");
  assert.equal(index.byNodeId.get("well-node").backgroundColor, "#EF4B3C1A");

  const nodes = [
    { id: "cta-node", name: "a · Book A Schedule", style: { backgroundColor: "var(--color-accent)" } },
    { id: "well-node", name: "card well", style: { backgroundColor: "var(--color-accent)" } },
    { id: "footer-node", name: "10 · footer", style: { backgroundColor: "transparent" } },
    { id: "other", name: "cream", style: { backgroundColor: "#F7F3ED" } },
  ];
  const { restored, inventedSkipped, mineNodes } = applyCapturePaintWitness(nodes, root);
  assert.equal(restored, 2);
  assert.equal(inventedSkipped, 1);
  assert.equal(nodes[0].style.backgroundColor, "#EF4B3C");
  assert.equal(nodes[1].style.backgroundColor, "#EF4B3C1A");
  assert.equal(nodes[2].style.backgroundColor, "transparent");

  const washedPaper = [
    ...Array.from({ length: 24 }, () => ({ style: { backgroundColor: "#EF4B3C1A" } })),
    { style: { backgroundColor: "#F7F3ED" } },
  ];
  const mined = mineFromStyledNodes([...washedPaper, ...mineNodes], { minUses: 1 });
  const proposed = proposeLibraryTokens(mined);
  const accent = proposed.find((t) => t.name === "--color-accent");
  const soft = proposed.find((t) => t.name === "--color-accent-soft");
  assert.equal(String(accent?.value || "").toUpperCase(), "#EF4B3C");
  assert.equal(String(soft?.value || "").toUpperCase(), "#EF4B3C1A");
  assert.equal(closestColorToken([accent, soft], "#EF4B3C")?.name, "--color-accent");
  assert.equal(closestColorToken([accent, soft], "#EF4B3C1A")?.name, "--color-accent-soft");

  const pass = themeTokenPass(nodes, proposed);
  const byId = Object.fromEntries(pass.changes.map((c) => [`${c.nodeId}:${c.property}`, c]));
  assert.equal(byId["cta-node:backgroundColor"].to, "var(--color-accent)");
  assert.equal(byId["well-node:backgroundColor"].to, "var(--color-accent-soft)");
  assert.equal(byId["footer-node:backgroundColor"], undefined);
});

test("1.4 does not invent fills on unpainted frames or near-color snaps", () => {
  assert.equal(isUnpaintedFill("transparent"), true);
  assert.equal(isUnpaintedFill("rgba(0, 0, 0, 0)"), true);
  assert.equal(isUnpaintedFill("#EF4B3C"), false);
  const tokens = [
    { type: "color", name: "--color-accent", value: "#EF4B3C" },
    { type: "color", name: "--color-surface", value: "#F7F3ED" },
  ];
  assert.equal(exactColorToken(tokens, "#EF4B3C")?.name, "--color-accent");
  assert.equal(exactColorToken(tokens, "#E14A3A"), null);
  assert.equal(closestColorToken(tokens, "#E14A3A")?.name, "--color-accent");

  const stack = { id: "page", name: "home-desktop", style: { backgroundColor: "#EF4B3C" } };
  const cta = {
    id: "cta",
    name: "09 · cta",
    parentId: "page",
    style: { backgroundColor: "#EF4B3C" },
  };
  const footer = {
    id: "footer",
    name: "10 · footer",
    parentId: "page",
    style: { backgroundColor: "transparent" },
  };
  assert.equal(isSectionStack(stack, [cta, footer]), true);

  const pass = themeTokenPass([stack, cta, footer], tokens);
  const bound = pass.changes.map((c) => `${c.nodeId}:${c.property}`);
  assert.deepEqual(bound, ["cta:backgroundColor"]);
  assert.equal(pass.updates.some((u) => u.nodeIds.includes("page")), false);
  assert.equal(pass.updates.some((u) => u.nodeIds.includes("footer")), false);
});

test("dropInventedFillChanges strips fills that 1.2 left unpainted", () => {
  const pass = dropInventedFillChanges({
    changes: [
      { nodeId: "footer", property: "backgroundColor", to: "var(--color-accent)" },
      { nodeId: "cta", property: "backgroundColor", to: "var(--color-accent)" },
    ],
    skipped: [],
    leftovers: [],
    updates: [
      { nodeIds: ["footer"], styles: { backgroundColor: "var(--color-accent)" } },
      { nodeIds: ["cta"], styles: { backgroundColor: "var(--color-accent)", color: "#fff" } },
    ],
  }, ["footer"]);
  assert.equal(pass.invented.length, 1);
  assert.equal(pass.changes.length, 1);
  assert.equal(pass.changes[0].nodeId, "cta");
  assert.equal(pass.updates.length, 1);
  assert.deepEqual(pass.updates[0].nodeIds, ["cta"]);
});
