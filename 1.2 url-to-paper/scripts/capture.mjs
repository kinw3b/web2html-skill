#!/usr/bin/env node
// Render a URL and serialize it to Paper-compatible inline-styled HTML, using
// the Paper Snapshot 0.3.12 serializer (plus 1.2 layer-name / sidecar).
//
// Usage:
//   node capture.mjs --url <url> [--selector <css>] [--out <file>] [--width 1600]
//   node capture.mjs --url <url> --list-sections

import { chromium } from "playwright-core";
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { resolveChrome } from "./chrome-path.mjs";
import { settlePageLoad } from "./settle-page.mjs";

const __dir = dirname(fileURLToPath(import.meta.url));

const argv = process.argv.slice(2);
const arg = (name, fallback) => {
  const i = argv.indexOf(`--${name}`);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : fallback;
};

const url = arg("url");
const selector = arg("selector", "body");
const outPath = resolve(arg("out", "capture.html"));
const width = parseInt(arg("width", "1600"), 10);
const listSections = argv.includes("--list-sections");

if (!url) {
  console.error("--url is required");
  process.exit(1);
}

const serializerSrc = readFileSync(resolve(__dir, "serializer.js"), "utf8");
const log = (...a) => console.error("·", ...a);

const browser = await chromium.launch({ executablePath: resolveChrome(), headless: true });

const context = await browser.newContext({
  viewport: { width, height: 1000 },
  deviceScaleFactor: 2,
  // CRITICAL: modern sites (Framer especially) start entrance animations at
  // opacity:0, and the serializer DROPS zero-opacity nodes. Under reduced
  // motion they render at their final state. Without this, captures come back
  // nearly empty. Do not remove.
  reducedMotion: "reduce",
  userAgent:
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
});

const page = await context.newPage();

log(`loading ${url}`);
// domcontentloaded first — Framer often never reaches true networkidle.
await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60_000 });
try {
  await page.waitForLoadState("networkidle", { timeout: 15_000 });
} catch {
  log("networkidle timed out — continuing (common on Framer)");
}
await page.waitForTimeout(1500);

// CRITICAL: scroll the full height to trigger IntersectionObserver reveals and
// lazy images, then return to top and let it settle. Do not remove.
// ALL settle waits are bounded (ora-portfolio 2026-08: unbounded image onload hung).
log("scrolling to trigger lazy content…");
await page.evaluate(async () => {
  const step = window.innerHeight * 0.8;
  const max = Math.min(document.body.scrollHeight || 0, 20_000);
  for (let y = 0; y < max; y += step) {
    window.scrollTo(0, y);
    await new Promise((r) => setTimeout(r, 180));
  }
  window.scrollTo(0, max);
  await new Promise((r) => setTimeout(r, 500));
  window.scrollTo(0, 0);
  await new Promise((r) => setTimeout(r, 500));
});

// Fonts and images must settle or computed styles won't be final — with timeouts.
await settlePageLoad(page);

if (listSections) {
  const sections = await page.evaluate(() => {
    const out = [];
    const seen = new Set();
    for (const el of document.querySelectorAll("body *")) {
      const r = el.getBoundingClientRect();
      if (r.width < 300 || r.height < 120) continue;
      if (el.children.length === 0) continue;
      let depth = 0;
      for (let p = el; (p = p.parentElement); ) depth++;
      if (depth > 6) continue;
      const sel = el.id
        ? `#${el.id}`
        : el.className && typeof el.className === "string"
          ? `${el.tagName.toLowerCase()}.${el.className.trim().split(/\s+/).slice(0, 2).join(".")}`
          : el.tagName.toLowerCase();
      if (seen.has(sel)) continue;
      seen.add(sel);
      out.push({
        sel,
        depth,
        w: Math.round(r.width),
        h: Math.round(r.height),
        text: (el.textContent || "").trim().replace(/\s+/g, " ").slice(0, 70),
      });
    }
    return out;
  });
  console.log(JSON.stringify(sections, null, 1));
  await browser.close();
  process.exit(0);
}

log(`serializing "${selector}" …`);
// Evaluated as a string expression via CDP, which is not subject to the page's
// CSP — some sites would otherwise block the injected function.
const expr = `(async () => {
  ${serializerSrc}
  return await fe(${JSON.stringify(selector)});
})()`;

const result = await page.evaluate(expr);

if (result.status !== "success") {
  console.error("FAILED:", JSON.stringify(result));
  await browser.close();
  process.exit(1);
}

const html = result.html;
writeFileSync(outPath, html, "utf8");

const imgs = [...html.matchAll(/<img[^>]*\ssrc="([^"]+)"/g)].map((m) => m[1]);
const stats = {
  outPath,
  bytes: html.length,
  elements: (html.match(/<[a-z]/g) || []).length,
  images: imgs.length,
  remoteImages: imgs.filter((s) => /^https?:/.test(s)).length,
  warning: result.warning ?? null,
};
console.log(JSON.stringify(stats, null, 1));

if (stats.bytes < 2000) {
  console.error(
    "· WARNING: capture is suspiciously small. Content may have been dropped —\n" +
    "  preview it with shot.mjs before writing to Paper.",
  );
}

await browser.close();
