import test from "node:test";
import assert from "node:assert/strict";
import {
  breakpointShotQaDone,
  requiredAuthoredFrames,
  summarizeShotQa,
} from "../scripts/breakpoint-shot-qa.mjs";

test("authored frames must exist before screenshot QA", () => {
  const missing = requiredAuthoredFrames([{ name: "home-desktop" }]);
  assert.equal(missing.ok, false);
  assert.deepEqual(missing.missing, ["home-768", "home-390"]);
  const ready = requiredAuthoredFrames([
    { name: "home-desktop" },
    { name: "home-768" },
    { name: "home-390" },
  ]);
  assert.equal(ready.ok, true);
});

test("shot QA fails a blank Paper band against a contentful clip", () => {
  const summary = summarizeShotQa([
    { shot: "01-hero.png", verdict: { kind: "shot-mismatch", symptom: "white" } },
    { shot: "02-menu.png", verdict: null },
  ]);
  assert.equal(summary.ok, false);
  assert.equal(summary.failures.length, 1);
});

test("receipt needs two authored frames and ok:true", () => {
  assert.equal(breakpointShotQaDone({ ok: true, frames: [{}, {}] }), true);
  assert.equal(breakpointShotQaDone({ ok: true, frames: [{}] }), false);
  assert.equal(breakpointShotQaDone({ ok: false, frames: [{}, {}] }), false);
  assert.equal(breakpointShotQaDone({
    ok: true, frames: [{}, {}], missingFrames: ["home-768"],
  }), false);
});
