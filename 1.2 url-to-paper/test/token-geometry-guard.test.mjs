import test from "node:test";
import assert from "node:assert/strict";
import {
  compareTokenGeometry,
  snapshotTokenGeometry,
} from "../scripts/token-geometry-guard.mjs";

function fixture() {
  return [
    {
      id: "hero",
      artboard: "home-desktop",
      style: {
        x: "12px",
        y: 24,
        width: "640px",
        height: "180px",
        fontSize: "30px",
        lineHeight: "36px",
        textWrap: "wrap",
        flexGrow: 0,
        alignSelf: "stretch",
      },
    },
    {
      id: "body",
      artboard: "home-desktop",
      style: { x: 12, y: 220, width: 640, height: 80 },
    },
    {
      id: "swatch",
      artboard: "Design Library",
      style: { x: 0, y: 0, width: 100, height: 100 },
    },
  ];
}

test("snapshotTokenGeometry records the geometry contract", () => {
  assert.deepEqual(snapshotTokenGeometry(fixture()), [
    {
      nodeId: "hero",
      artboard: "home-desktop",
      x: "12px",
      y: 24,
      width: "640px",
      height: "180px",
      fontSize: "30px",
      lineHeight: "36px",
      textWrap: "wrap",
      flexGrow: 0,
      alignSelf: "stretch",
    },
    {
      nodeId: "body",
      artboard: "home-desktop",
      x: 12,
      y: 220,
      width: 640,
      height: 80,
      fontSize: null,
      lineHeight: null,
      textWrap: "",
      flexGrow: null,
      alignSelf: "",
    },
    {
      nodeId: "swatch",
      artboard: "Design Library",
      x: 0,
      y: 0,
      width: 100,
      height: 100,
      fontSize: null,
      lineHeight: null,
      textWrap: "",
      flexGrow: null,
      alignSelf: "",
    },
  ]);
});

test("compareTokenGeometry tolerates half a pixel and ignores Design Library", () => {
  const before = snapshotTokenGeometry(fixture());
  const changed = fixture();
  changed[0].style.x = "12.5px";
  changed[2].style.width = 400;
  const after = snapshotTokenGeometry(changed);
  const result = compareTokenGeometry(before, after, {
    ignoredArtboards: ["Design Library"],
  });
  assert.equal(result.ok, true);
  assert.deepEqual(result.differences, []);
});

test("compareTokenGeometry fails numeric, string, and node census drift", () => {
  const before = snapshotTokenGeometry(fixture());
  const changed = [fixture()[0], fixture()[2]];
  changed[0].style.width = "641px";
  changed[0].style.textWrap = "pretty";
  const after = snapshotTokenGeometry(changed);
  const result = compareTokenGeometry(before, after, {
    ignoredArtboards: ["Design Library"],
  });
  assert.equal(result.ok, false);
  assert.ok(result.differences.some((item) => item.nodeId === "hero" && item.property === "width"));
  assert.ok(result.differences.some((item) => item.nodeId === "hero" && item.property === "textWrap"));
  assert.ok(result.differences.some((item) => item.nodeId === "body" && item.reason === "missing-after"));
  assert.ok(!result.differences.some((item) => item.nodeId === "swatch"));
});

test("compareTokenGeometry preserves units and non-numeric sizing keywords", () => {
  const before = snapshotTokenGeometry([
    {
      id: "percent",
      artboard: "home-desktop",
      style: { width: "100%", height: "fit-content" },
    },
  ]);
  const after = snapshotTokenGeometry([
    {
      id: "percent",
      artboard: "home-desktop",
      style: { width: "100px", height: "auto" },
    },
  ]);
  const result = compareTokenGeometry(before, after);
  assert.equal(result.ok, false);
  assert.ok(result.differences.some((item) => (
    item.nodeId === "percent"
    && item.property === "width"
    && item.from === "100%"
    && item.to === "100px"
  )));
  assert.ok(result.differences.some((item) => (
    item.nodeId === "percent"
    && item.property === "height"
    && item.from === "fit-content"
    && item.to === "auto"
  )));
});

test("compareTokenGeometry resolves active CSS tokens before comparison", () => {
  const tokens = [
    { type: "fontSize", name: "--text-8xl", value: "96px" },
  ];
  const after = snapshotTokenGeometry([
    {
      id: "hero",
      artboard: "home-desktop",
      style: { fontSize: "var(--text-8xl)" },
    },
  ]);

  const equivalent = compareTokenGeometry(
    snapshotTokenGeometry([{
      id: "hero",
      artboard: "home-desktop",
      style: { fontSize: "96px" },
    }]),
    after,
    { tokens },
  );
  assert.equal(equivalent.ok, true);

  const drift = compareTokenGeometry(
    snapshotTokenGeometry([{
      id: "hero",
      artboard: "home-desktop",
      style: { fontSize: "95px" },
    }]),
    after,
    { tokens },
  );
  assert.equal(drift.ok, false);
  assert.ok(drift.differences.some((item) => (
    item.nodeId === "hero"
    && item.property === "fontSize"
    && item.from === "95px"
    && item.to === "var(--text-8xl)"
  )));
});

test("compareTokenGeometry treats equivalent line-height px and percent tokens as the same", () => {
  const tokens = [
    { type: "fontSize", name: "--text-base", value: "16px" },
    { type: "lineHeight", name: "--line-height-170", value: "170%" },
  ];
  const equivalent = compareTokenGeometry(
    snapshotTokenGeometry([{
      id: "body",
      artboard: "home-desktop",
      style: { fontSize: "var(--text-base)", lineHeight: "27.2px" },
    }]),
    snapshotTokenGeometry([{
      id: "body",
      artboard: "home-desktop",
      style: { fontSize: "var(--text-base)", lineHeight: "var(--line-height-170)" },
    }]),
    { tokens },
  );
  assert.equal(equivalent.ok, true);

  const drifted = compareTokenGeometry(
    snapshotTokenGeometry([{
      id: "body",
      artboard: "home-desktop",
      style: { fontSize: "16px", lineHeight: "24px" },
    }]),
    snapshotTokenGeometry([{
      id: "body",
      artboard: "home-desktop",
      style: { fontSize: "16px", lineHeight: "var(--line-height-170)" },
    }]),
    { tokens },
  );
  assert.equal(drifted.ok, false);
});
