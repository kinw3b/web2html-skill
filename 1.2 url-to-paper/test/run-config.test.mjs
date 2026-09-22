import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { loadRunConfig, runWidths, isFastRun, normalizeWidths, GENERATED_FROM } from "../scripts/run-config.mjs";
import { breakpointWidthsFor, requiredAuthoredFrames, breakpointShotQaDone } from "../scripts/breakpoint-shot-qa.mjs";
import { missingSourceSectionDirs } from "../scripts/source-sections.mjs";

function project(config) {
  const root = mkdtempSync(join(tmpdir(), "w2h-runcfg-"));
  if (config) {
    mkdirSync(join(root, "qa"), { recursive: true });
    writeFileSync(join(root, "qa", "run-config.json"), JSON.stringify(config));
  }
  return root;
}

test("no run-config → full widths, human checkpoints", () => {
  const root = project(null);
  assert.deepEqual(runWidths(root), [1600, 768, 390]);
  assert.equal(isFastRun(root), false);
  assert.equal(loadRunConfig(root).checkpoints, "human");
});

test("fast run-config → 1600 + 390, checkpoints forced auto", () => {
  const root = project({ generatedFrom: GENERATED_FROM, speed: "fast", checkpoints: "human", widths: [1600, 390] });
  assert.deepEqual(runWidths(root), [1600, 390]);
  assert.equal(isFastRun(root), true);
  assert.equal(loadRunConfig(root).checkpoints, "auto");
  assert.deepEqual(breakpointWidthsFor(root), [390]);
});

test("malformed or foreign run-config reads as the default", () => {
  const root = project({ generatedFrom: "someone-else", widths: [1024] });
  assert.deepEqual(runWidths(root), [1600, 768, 390]);
  const broken = mkdtempSync(join(tmpdir(), "w2h-runcfg-"));
  mkdirSync(join(broken, "qa"));
  writeFileSync(join(broken, "qa", "run-config.json"), "{not json");
  assert.deepEqual(runWidths(broken), [1600, 768, 390]);
});

test("normalizeWidths dedupes, drops junk, sorts wide → narrow", () => {
  assert.deepEqual(normalizeWidths(["390", 1600, "x", 390, -1]), [1600, 390]);
  assert.deepEqual(normalizeWidths([]), [1600, 768, 390]);
});

test("breakpoint frames + done-gate follow the configured widths", () => {
  const boards = [{ name: "home-desktop" }, { name: "home-390" }];
  assert.equal(requiredAuthoredFrames(boards, "home", [390]).ok, true);
  assert.deepEqual(requiredAuthoredFrames(boards, "home").missing, ["home-768"]);
  const report = { ok: true, frames: [{ width: 390 }], missingFrames: [] };
  assert.equal(breakpointShotQaDone(report, [390]), true);
  assert.equal(breakpointShotQaDone(report), false);
});

test("missingSourceSectionDirs only asks for the configured widths", () => {
  const root = project(null);
  const capture = join(root, "capture");
  for (const folder of ["home-desktop", "home-390"]) {
    const dir = join(capture, folder, "source-sections");
    mkdirSync(dir, { recursive: true });
    writeFileSync(join(dir, "01-hero.png"), Buffer.from([0x89, 0x50, 0x4e, 0x47]));
    writeFileSync(join(dir, "01-hero.json"), JSON.stringify({ id: "01", slug: "hero", png: "01-hero.png" }));
  }
  assert.deepEqual(missingSourceSectionDirs(capture, "home", [1600, 390]), []);
  assert.equal(missingSourceSectionDirs(capture, "home").length, 1);
});
