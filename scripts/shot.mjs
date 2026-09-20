#!/usr/bin/env node
// Render a captured HTML fragment and screenshot it, so the capture can be
// eyeballed BEFORE it is written into Paper.
//
// Usage: node shot.mjs <fragment.html> <out.png> [--full] [--width 1600]

import { chromium } from "playwright-core";
import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { resolveChrome } from "./chrome-path.mjs";

const argv = process.argv.slice(2);
const [input, out] = argv.filter((a) => !a.startsWith("--"));
if (!input || !out) {
  console.error("usage: node shot.mjs <fragment.html> <out.png> [--full] [--width N]");
  process.exit(1);
}
const wi = argv.indexOf("--width");
const width = wi >= 0 ? parseInt(argv[wi + 1], 10) : 1600;
const fullPage = argv.includes("--full");

// The capture is a bare fragment; wrap it so it renders standalone.
const fragment = readFileSync(resolve(input), "utf8");
const previewPath = resolve(input).replace(/\.html$/, "") + ".preview.html";
writeFileSync(
  previewPath,
  `<!doctype html><meta charset="utf-8"><title>capture preview</title><body style="margin:0">${fragment}`,
  "utf8",
);

const browser = await chromium.launch({ executablePath: resolveChrome(), headless: true });
const page = await browser.newPage({
  viewport: { width, height: 1200 },
  deviceScaleFactor: fullPage ? 0.5 : 1,
});
await page.goto("file://" + previewPath, { waitUntil: "networkidle", timeout: 60_000 });
await page.waitForTimeout(2500);
await page.screenshot({ path: resolve(out), fullPage });

const height = await page.evaluate(() => document.body.scrollHeight);
console.log(JSON.stringify({ out: resolve(out), previewPath, renderedHeight: height }, null, 1));

await browser.close();
