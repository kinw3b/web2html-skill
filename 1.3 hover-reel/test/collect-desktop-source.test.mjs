import test from "node:test";
import assert from "node:assert/strict";
import {
  diskShotWidths,
  paperAssembleWidths,
  paperScreenshotBoardWidth,
} from "../scripts/run-paper-phase.mjs";

test("1.2 serializes every required viewport to Paper", () => {
  assert.deepEqual(paperAssembleWidths(), [1600, 768, 390]);
});

test("1.2 still shots every breakpoint unless desktop-only", () => {
  assert.deepEqual(diskShotWidths(), [1600, 768, 390]);
  assert.deepEqual(diskShotWidths({ desktopOnly: true }), [1600]);
});

test("Paper Screenshots board is always the 1600 clips", () => {
  assert.equal(paperScreenshotBoardWidth(), 1600);
});
