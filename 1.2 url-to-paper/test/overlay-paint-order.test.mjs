import test from "node:test";
import assert from "node:assert/strict";
import {
  findOverlayPaintOrderIssues,
  isFullBleedAbsOverlay,
  planOverlayPaintOrder,
  reorderOverlayPaintOrder,
} from "../scripts/overlay-paint-order.mjs";

const overlay = `<div style="position: absolute; top: 0; right: 0; bottom: 0; left: 0; width: 100%; height: 100%; background-color: rgba(0, 0, 0, 0.5)"></div>`;
const img = `<img src="hero.jpg" alt="" style="width: 1600px; height: 900px" />`;
const type = `<div style="display: flex; flex-direction: column"><h1>Stay a little longer</h1><p>Copy</p></div>`;

test("gold is image → overlay → type last", () => {
  const html = `<section style="position: relative">${img}${type}${overlay}</section>`;
  const out = reorderOverlayPaintOrder(html);
  assert.equal(out.moved.length, 1);
  const overlayAt = out.html.indexOf("rgba(0, 0, 0, 0.5)");
  const typeAt = out.html.indexOf("Stay a little longer");
  const imgAt = out.html.indexOf("hero.jpg");
  assert.ok(imgAt < overlayAt && overlayAt < typeAt);
  assert.equal((out.html.match(/rgba\(0, 0, 0, 0\.5\)/g) || []).length, 1);
});

test("already-gold JA-0 order is a no-op", () => {
  const html = `<section style="position: relative">${img}${overlay}${type}</section>`;
  const out = reorderOverlayPaintOrder(html);
  assert.equal(out.moved.length, 0);
  assert.match(out.html, /hero\.jpg[\s\S]*rgba\(0, 0, 0, 0\.5\)[\s\S]*Stay a little longer/);
});

test("does not clone the overlay on top", () => {
  const html = `<section>${img}${type}${overlay}</section>`;
  const out = reorderOverlayPaintOrder(html);
  assert.equal((out.html.match(/position: absolute/g) || []).length, 1);
});

test("no image: overlay still sits before type", () => {
  const html = `<section>${type}${overlay}</section>`;
  const out = reorderOverlayPaintOrder(html);
  assert.equal(out.moved.length, 1);
  assert.ok(out.html.indexOf("rgba(0, 0, 0, 0.5)") < out.html.indexOf("Stay a little longer"));
});

test("nav with links is not a dim overlay", () => {
  const nav = `<nav style="position: absolute; top: 0; left: 0; width: 100%; height: 80px; background-color: rgba(0,0,0,0.2)"><a href="/">Home</a></nav>`;
  const html = `<section>${img}${nav}${type}</section>`;
  const out = reorderOverlayPaintOrder(html);
  assert.equal(out.moved.length, 0);
});

test("1px stroke decoration is not a dim overlay", () => {
  const stroke = `<div style="position: absolute; inset: 0; border-width: 1px; border-style: solid; border-color: #eee"></div>`;
  const html = `<section>${img}${type}${stroke}</section>`;
  const out = reorderOverlayPaintOrder(html);
  assert.equal(out.moved.length, 0);
});

test("isFullBleedAbsOverlay accepts ink 0.5 + 100%", () => {
  assert.equal(
    isFullBleedAbsOverlay({
      position: "absolute",
      width: "100%",
      height: "100%",
      "background-color": "rgba(0,0,0,0.5)",
    }, { childCount: 0, text: "" }),
    true,
  );
});

test("planOverlayPaintOrder matches 768/390 gold (overlay after image, before type)", () => {
  const plan = planOverlayPaintOrder([
    { id: "29I-0", name: "image", hasMedia: true, style: {} },
    { id: "29K-0", name: "type", text: "Headline", style: {} },
    { id: "2A0-0", name: "overlay", style: { position: "absolute", width: "100%", height: "100%", "background-color": "rgba(0,0,0,0.5)" }, childCount: 0 },
  ]);
  assert.equal(plan.alreadyGold, false);
  assert.deepEqual(plan.ordered.map((s) => s.id), ["29I-0", "2A0-0", "29K-0"]);
});

test("qa census flags overlay after type", () => {
  const nodes = new Map([
    ["sec", { id: "sec", name: "01 · hero", childIds: ["img", "type", "ov"], w: 1600, h: 900 }],
    ["img", { id: "img", name: "photo", parentId: "sec", component: "Image", w: 1600, h: 900, position: "relative" }],
    ["type", { id: "type", name: "JD-0", parentId: "sec", component: "Text", textContent: "Stay", w: 400, h: 80, position: "relative" }],
    ["ov", { id: "ov", name: "JT-0", parentId: "sec", component: "Frame", childCount: 0, w: 1600, h: 900, position: "absolute", bg: "rgba(0,0,0,0.5)", top: "0", right: "0", bottom: "0", left: "0" }],
  ]);
  const hits = findOverlayPaintOrderIssues(nodes, { artboard: "home-desktop" });
  assert.equal(hits.length, 1);
  assert.equal(hits[0].type, "overlay-covers-type");
  assert.equal(hits[0].node, "ov");
});
