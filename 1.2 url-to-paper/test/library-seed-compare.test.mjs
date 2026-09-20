import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  captureFontFaces,
  captureHtmlPath,
  colorSeedVerdict,
  fontSeedVerdict,
  layoutSeedVerdict,
  saturatedPalette,
  sectionSeedVerdict,
  seedExitCode,
  seedReportOk,
} from "../scripts/library-seed-compare.mjs";

function writeRgbPng(path, rgb, w = 48, h = 48) {
  execFileSync("python3", ["-c", `
from PIL import Image
Image.new("RGB", (${w}, ${h}), (${rgb[0]}, ${rgb[1]}, ${rgb[2]})).save(${JSON.stringify(path)})
`]);
}

test("captureFontFaces drops generic stacks and keeps the live face", () => {
  const html = `
    <div style="font-family: GeneralSans-Medium, sans-serif">A</div>
    <p style="font-family: Inter, system-ui, sans-serif">B</p>
    <span style="font-family: sans-serif">C</span>
  `;
  assert.deepEqual(captureFontFaces(html).sort(), ["GeneralSans", "Inter"]);
});

test("fontSeedVerdict fails only when Paper is all system after a concrete capture", () => {
  assert.equal(fontSeedVerdict({
    captureFaces: ["GeneralSans"],
    paperFaces: ["Inter"],
  }), null);
  assert.equal(fontSeedVerdict({
    captureFaces: ["GeneralSans"],
    paperFaces: ["var(--font-sans)"],
  }), null);
  assert.equal(fontSeedVerdict({
    captureFaces: ["GeneralSans"],
    paperFaces: ["System Sans-Serif"],
  })?.kind, "font-shift");
  assert.equal(fontSeedVerdict({
    captureFaces: ["GeneralSans"],
    paperFaces: [],
  }), null);
});

test("colorSeedVerdict flags a washed CTA band against a saturated source clip", () => {
  const source = { meanSat: 0.72, coverage: 0.4, saturatedMean: { r: 239, g: 75, b: 60 } };
  const wash = { meanSat: 0.11, coverage: 0.05, saturatedMean: { r: 246, g: 226, b: 219 } };
  assert.equal(colorSeedVerdict(source, wash)?.kind, "color-wash");
  assert.equal(colorSeedVerdict(source, source), null);
  assert.equal(colorSeedVerdict(
    { meanSat: 0.08, coverage: 0, saturatedMean: null },
    { meanSat: 0.07, coverage: 0, saturatedMean: null },
  ), null);
});

test("colorSeedVerdict flags a red spill onto a quiet footer band", () => {
  const source = { meanSat: 0.06, coverage: 0.01, saturatedMean: null };
  const spilled = { meanSat: 0.74, coverage: 0.62, saturatedMean: { r: 239, g: 75, b: 60 } };
  assert.equal(colorSeedVerdict(source, spilled)?.kind, "color-spill");
  assert.equal(colorSeedVerdict(source, source), null);
});

test("layoutSeedVerdict keeps content matches and flags collapse", () => {
  assert.equal(layoutSeedVerdict({
    sourceWhite: 0.29,
    paperWhite: 0.28,
    paperChildCount: 4,
    sourceH: 800,
    paperH: 790,
  }), null);
  assert.equal(layoutSeedVerdict({
    sourceWhite: 0.29,
    paperWhite: 0.91,
    paperChildCount: 2,
    sourceH: 800,
    paperH: 800,
  })?.kind, "layout-shift");
  assert.equal(layoutSeedVerdict({
    sourceWhite: 0.29,
    paperWhite: 0.28,
    paperChildCount: 4,
    sourceH: 800,
    paperH: 200,
  })?.kind, "layout-shift");
});

test("saturatedPalette distinguishes solid orange from a cream wash", () => {
  const dir = mkdtempSync(join(tmpdir(), "library-seed-palette-"));
  const orange = join(dir, "orange.png");
  const cream = join(dir, "cream.png");
  writeRgbPng(orange, [239, 75, 60]);
  writeRgbPng(cream, [247, 243, 237]);
  const hot = saturatedPalette(orange);
  const cool = saturatedPalette(cream);
  assert.ok(hot.meanSat >= 0.6);
  assert.ok(cool.meanSat < 0.12);
  assert.equal(sectionSeedVerdict({
    sourcePalette: hot,
    paperPalette: cool,
    captureFaces: ["Inter"],
    paperFaces: ["Inter"],
    sourceWhite: 0.0,
    paperWhite: 0.0,
    paperChildCount: 3,
    sourceH: 48,
    paperH: 48,
  })?.kind, "color-wash");
});

test("seedExitCode is 2 when the check cannot retry", () => {
  assert.equal(seedExitCode({ ok: true, failures: [] }), 0);
  assert.equal(seedExitCode({ ok: false, retryable: true, failures: [{ kind: "color-wash" }] }), 1);
  assert.equal(seedExitCode({ ok: false, retryable: false, failures: [{ kind: "missing-source-sections" }] }), 2);
  assert.equal(seedReportOk({ ok: true, failures: [] }), true);
});

test("captureHtmlPath pairs NN-*.html with the matching shot", () => {
  const dir = mkdtempSync(join(tmpdir(), "library-seed-html-"));
  writeFileSync(join(dir, "01-hero-sections.html"), "<div></div>");
  writeFileSync(join(dir, "02-pricing.html"), "<div></div>");
  assert.equal(
    captureHtmlPath(dir, { id: "01", slug: "hero-sections" }),
    join(dir, "01-hero-sections.html"),
  );
  assert.equal(captureHtmlPath(dir, { id: "09", slug: "missing" }), null);
});
