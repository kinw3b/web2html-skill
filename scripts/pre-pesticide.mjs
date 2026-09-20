#!/usr/bin/env node
// Live-site pre-pesticide: pesticide outlines + DOM inventory *before* Stage P.
//
// Smart sibling of rebuild qa-overlay (end-of-build Outlines). This run is
// pre-scrape, on the live URL. The HUD is x-paper- prefixed so the serializer
// skips it. Homepage only by default.
//
// Usage:
//   node scripts/pre-pesticide.mjs --url <live> --width 1600 \
//     [--out capture/home-desktop/pre-pesticide.json]
//   node scripts/pre-pesticide.mjs --url <live> --inspect
//   node scripts/pre-pesticide.mjs --bookmarklet
//
// Desktop 1600, tablet 768, and phone 390 write source-sections/01-slug.png.
// The Paper Screenshots board still uses the 1600 clips only.
// --no-source-sections skips those clips. --headless is CI-only.
// Visible Chrome (same launch as Stage P).

import { mkdirSync, readFileSync, writeFileSync, writeSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { HUD_ID, HUD_TAG } from "./pre-pesticide-core.mjs";
import { captureSourceSectionsOnPage, sourceSectionsDirFor } from "./source-sections.mjs";

const __dir = dirname(fileURLToPath(import.meta.url));

const argv = process.argv.slice(2);
const arg = (name, fallback) => {
  const i = argv.indexOf(`--${name}`);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : fallback;
};

if (argv.includes("--bookmarklet")) {
  const src = readFileSync(join(__dir, "pre-pesticide.js"), "utf8");
  const detect = readFileSync(join(__dir, "detect-sections.js"), "utf8");
  const packed = `${detect}\n${src}\nwindow.__xPaperPrePesticide.init();`;
  const href = `javascript:${encodeURIComponent(packed)}`;
  // Pipes are async in Node: process.exit() right after write() truncates the
  // ~60 KB URL at the first 8 KB chunk. Use a synchronous fd write instead.
  writeSync(1, `${href}\n`);
  process.exit(0);
}

const url = arg("url");
const outPath = resolve(arg("out", "capture/home-desktop/pre-pesticide.json"));
const width = parseInt(arg("width", "1600"), 10);
const visible = !argv.includes("--headless");
const inspect = argv.includes("--inspect");
const twPrefix = arg("tw-prefix", "");
const wantSource = !argv.includes("--no-source-sections");
const sourceDir = resolve(arg("source-dir", sourceSectionsDirFor(outPath)));

if (!url) {
  console.error("Usage: node scripts/pre-pesticide.mjs --url <live> [--width 1600] [--out capture/home-desktop/pre-pesticide.json]");
  console.error("       --headless is CI-only. --inspect keeps the HUD open. --bookmarklet prints a javascript: URL.");
  process.exit(1);
}

const hudSrc = readFileSync(join(__dir, "pre-pesticide.js"), "utf8");
const detectSrc = readFileSync(join(__dir, "detect-sections.js"), "utf8");
const log = (...a) => console.error("·", ...a);

mkdirSync(dirname(outPath), { recursive: true });

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

log("settling page (scroll pass)…");
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
await page.evaluate((prefix) => {
  window.__xPaperPrePesticide.init({ prefix });
}, twPrefix);

const live = await page.evaluate(() => window.__xPaperPrePesticide.inventory());

const inventory = {
  sections: live.sections || [],
  images: live.images || [],
  forms: live.forms || [],
  landmarks: live.landmarks || [],
  totals: {
    sections: (live.sections || []).length,
    images: (live.images || []).length,
    forms: (live.forms || []).length,
    landmarks: (live.landmarks || []).length,
  },
  twPrefix,
};

const payload = {
  url,
  width,
  capturedAt: new Date().toISOString(),
  hud: { tag: live.hudTag || HUD_TAG, id: live.hudId || HUD_ID },
  ...inventory,
};

writeFileSync(outPath, JSON.stringify(payload, null, 2));
log(`wrote ${outPath}`);
log(`  sections=${payload.totals.sections}  images=${payload.totals.images}  forms=${payload.totals.forms}  landmarks=${payload.totals.landmarks}`);
if (live.hudTag && !live.hudTag.startsWith("x-paper-")) {
  log("  ! HUD tag is not x-paper- prefixed — serializer will leak it");
}

let sourceShots = [];
if (wantSource) {
  log(`source-section shots (pesticide on) → ${sourceDir}`);
  sourceShots = await captureSourceSectionsOnPage(page, {
    sections: live.sections || [],
    outDir: sourceDir,
    log,
    viewportWidth: width,
  });
}

if (inspect && visible) {
  await page.evaluate(() => window.__xPaperPrePesticide?.show?.());
  log("inspect mode — HUD stays up. Close the Chrome window to finish.");
  await new Promise((resolveDone) => {
    browser.on("disconnected", resolveDone);
    page.on("close", resolveDone);
  });
} else {
  await page.evaluate(() => window.__xPaperPrePesticide?.destroy?.());
}

await browser.close();
console.log(JSON.stringify({
  out: outPath,
  url,
  width,
  totals: payload.totals,
  hud: payload.hud,
  sourceSections: sourceDir,
  sourceShots: sourceShots.map((s) => s.stem),
}, null, 2));
