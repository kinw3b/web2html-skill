import test from "node:test";
import assert from "node:assert/strict";
import {
  boardShotVerdict,
  leftoverTopPx,
  namedIndex,
  placementVerdict,
  shotVerdict,
} from "../scripts/source-shot-compare.mjs";

test("shotVerdict does not hard-pass on childCount > 0", () => {
  const emptyKids = shotVerdict({ sourceWhite: 0.29, paperWhite: 0.28, paperChildCount: 2 });
  assert.equal(emptyKids, null, "content-on-content is still a match");

  const holeWithKids = shotVerdict({ sourceWhite: 0.29, paperWhite: 0.91, paperChildCount: 2 });
  assert.equal(holeWithKids?.kind, "shot-mismatch");

  const emptyFrame = shotVerdict({ sourceWhite: 0.29, paperWhite: 0.95, paperChildCount: 0 });
  assert.equal(emptyFrame?.kind, "empty-named-section");
});

test("leftover top 3252px is a displaced-section even with children", () => {
  const sections = [
    { id: "a", name: "04 · content-section-1", worldY: 2400, h: 800, childCount: 3, position: "relative", top: 0 },
    { id: "b", name: "05 · content-section-2", worldY: 6452, h: 700, childCount: 2, position: "relative", top: "3252px" },
    { id: "c", name: "06 · footer", worldY: 3200, h: 400, childCount: 4, position: "relative", top: 0 },
  ];
  const hits = placementVerdict(sections);
  assert.ok(hits.some((f) => f.kind === "displaced-section" && f.section.startsWith("05")));
  assert.ok(hits.some((f) => /leftover top 3252/.test(f.symptom) || /hole after/.test(f.symptom) || /y order/.test(f.symptom)));
  assert.equal(leftoverTopPx(sections[1]), 3252);
});

test("monotonic named stack with small gaps is clean", () => {
  const sections = [
    { id: "1", name: "01 · hero", worldY: 0, h: 800, childCount: 4, position: "relative", top: 0 },
    { id: "2", name: "02 · logos", worldY: 800, h: 200, childCount: 2, position: "relative", top: 0 },
    { id: "3", name: "03 · footer", worldY: 1000, h: 300, childCount: 3, position: "relative", top: 0 },
  ];
  assert.deepEqual(placementVerdict(sections), []);
});

test("namedIndex reads NN · labels", () => {
  assert.equal(namedIndex("05 · content-section-2"), 5);
  assert.equal(namedIndex("Source · home"), null);
});

test("boardShotVerdict flags a white stack vs a dark fullpage", () => {
  const hit = boardShotVerdict({ sourceWhite: 0.22, paperWhite: 0.81 });
  assert.equal(hit?.kind, "displaced-section");
  assert.equal(boardShotVerdict({ sourceWhite: 0.22, paperWhite: 0.30 }), null);
});
