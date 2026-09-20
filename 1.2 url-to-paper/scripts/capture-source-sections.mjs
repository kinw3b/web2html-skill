#!/usr/bin/env node
// Per-section SOURCE shots at 1600 / 768 / 390 with capture overlays hidden.
//
// Prefer pre-pesticide.mjs (inventory + shots in one Chrome session).
// This CLI re-clips when the inventory already exists or you only want shots.
//
//   node capture-source-sections.mjs --url <live> \
//     --out capture/home-desktop/source-sections --width 1600
//   node capture-source-sections.mjs --url <live> --width 768 \
//     --out capture/home-768/source-sections
//
// Visible Chrome (same launch as Stage P). --headless is CI-only.
// Never writes full-page.png into --out. Never seeds a 768/390 Screenshots board.

import { mkdirSync, readFileSync, existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import {
  captureSourceSectionsOnPage,
  isSourceShotViewport,
  landerFolderForWidth,
  sourceSectionsDirFor,
} from "./source-sections.mjs";

const __dir = dirname(fileURLToPath(import.meta.url));

const argv = process.argv.slice(2);
const arg = (name, fallback) => {
  const i = argv.indexOf(`--${name}`);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : fallback;
};

const url = arg("url");
const width = parseInt(arg("width", "1600"), 10);
const visible = !argv.includes("--headless");
const defaultOut = join("capture", landerFolderForWidth("home", width), "source-sections");
const outDir = resolve(arg("out", defaultOut));
const inventoryPath = arg("inventory");

if (!url) {
  console.error("Usage: node scripts/capture-source-sections.mjs --url <live> [--width 1600|768|390]");
  process.exit(1);
}
if (!isSourceShotViewport(width)) {
  console.error("source-section shots are 1600 / 768 / 390 only");
  process.exit(1);
}

const dest = sourceSectionsDirFor(outDir);
mkdirSync(dest, { recursive: true });

const hudSrc = readFileSync(join(__dir, "pre-pesticide.js"), "utf8");
const detectSrc = readFileSync(join(__dir, "detect-sections.js"), "utf8");
const log = (...a) => console.error("·", ...a);

const { chromium } = await import("playwright-core");
const { launchOptions } = await import("./chrome-path.mjs");

const browser = await chromium.launch(launchOptions({ visible }));
const context = await browser.newContext({
  viewport: { width, height: 1000 },
  deviceScaleFactor: 1,
  reducedMotion: "reduce",
});
const page = await context.newPage();

log(`loading ${url} @ ${width}`);
await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60_000 });
try {
  await page.waitForLoadState("networkidle", { timeout: 15_000 });
} catch {
  log("networkidle timed out — continuing (common on Framer)");
}
await page.waitForTimeout(800);
await page.evaluate(async () => {
  const step = window.innerHeight * 0.8;
  const max = Math.min(document.body.scrollHeight || 0, 20_000);
  for (let y = 0; y < max; y += step) {
    window.scrollTo(0, y);
    await new Promise((r) => setTimeout(r, 120));
  }
  window.scrollTo(0, 0);
  await new Promise((r) => setTimeout(r, 300));
});

await page.addScriptTag({ content: detectSrc });
await page.addScriptTag({ content: hudSrc });
await page.evaluate(() => window.__xPaperPrePesticide.init());

let sections = [];
if (inventoryPath && existsSync(inventoryPath)) {
  try {
    sections = JSON.parse(readFileSync(inventoryPath, "utf8")).sections || [];
  } catch {
    sections = [];
  }
}
if (!sections.length) {
  const live = await page.evaluate(() => window.__xPaperPrePesticide.inventory());
  sections = live.sections || [];
}

log(`source-section shots (pesticide on) — ${sections.length} section(s)`);
const written = await captureSourceSectionsOnPage(page, {
  sections,
  outDir: dest,
  log,
  viewportWidth: width,
});
await page.evaluate(() => window.__xPaperPrePesticide?.destroy?.());
await browser.close();

console.log(JSON.stringify({
  out: dest,
  url,
  width,
  sections: written.length,
  pngs: written.filter((w) => w.png).map((w) => w.stem),
}, null, 2));
