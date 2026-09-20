#!/usr/bin/env node
// Minimal homepage capture for section-level QA experiments.
//
// Loads one URL at a viewport width, detects sections, serializes each to
// HTML, takes a per-section JPEG with the capture HUD hidden, and writes
// manifest.json.
//
// Usage:
//   node experiment-capture-home.mjs --url <url> [--out-dir capture/home]
//                                    [--width 1600] [--headless]
//
// Overlay hide/show: the serializer skips x-paper-* nodes, but Playwright
// element screenshots still composite the fixed HUD. Always hide()+clearHighlight()
// before a section shot and show() in finally.

import { chromium } from "playwright-core";
import { mkdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { launchOptions } from "./chrome-path.mjs";
import { isDesktopCapture, sectionId, stampSectionIds, writeSectionIndex } from "./section-ids.mjs";
import { idPrefixFor, writeLayerIds } from "./layer-ids.mjs";
import { censusLivePage } from "./layer-ids-census.mjs";
import { serializeChromeBars } from "./chrome-bars.mjs";
import { captureSourceSectionsOnPage, hasSourceSectionShots, sourceSectionsDirFor } from "./source-sections.mjs";
import { settlePageLoad, settlePainted } from "./settle-page.mjs";

const __dir = dirname(fileURLToPath(import.meta.url));

const argv = process.argv.slice(2);
const arg = (name, fallback) => {
  const i = argv.indexOf(`--${name}`);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : fallback;
};

const url = arg("url");
const outDir = resolve(arg("out-dir", "capture/home"));
const width = parseInt(arg("width", "1600"), 10);
const visible = !argv.includes("--headless");

if (!url) {
  console.error("--url is required");
  process.exit(1);
}

const serializerSrc = readFileSync(join(__dir, "serializer.js"), "utf8");
const overlaySrc = readFileSync(join(__dir, "overlay.js"), "utf8");
const detectSrc = readFileSync(join(__dir, "detect-sections.js"), "utf8");

const log = (...a) => console.error("·", ...a);

mkdirSync(outDir, { recursive: true });
mkdirSync(join(outDir, "shots"), { recursive: true });

const browser = await chromium.launch(launchOptions({ visible }));
const context = await browser.newContext({
  viewport: { width, height: 1000 },
  deviceScaleFactor: 1,
  reducedMotion: "reduce",
});
const page = await context.newPage();

log(`loading ${url}`);
await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60_000 });
try {
  await page.waitForLoadState("networkidle", { timeout: 15_000 });
} catch {
  log("networkidle timed out — continuing (common on Framer)");
}
await page.waitForTimeout(1200);

log("settling page (scroll pass)…");
await page.evaluate(async () => {
  const step = window.innerHeight * 0.8;
  const max = Math.min(document.body.scrollHeight || 0, 20_000);
  for (let y = 0; y < max; y += step) {
    window.scrollTo(0, y);
    await new Promise((r) => setTimeout(r, 150));
  }
  window.scrollTo(0, max);
  await new Promise((r) => setTimeout(r, 400));
  window.scrollTo(0, 0);
  await new Promise((r) => setTimeout(r, 400));
});
await settlePageLoad(page);
log("settle complete");

const desktop = isDesktopCapture({ width });
const sourceDir = sourceSectionsDirFor(outDir);
const wantSource = !argv.includes("--no-source-sections");
if (wantSource && !hasSourceSectionShots(sourceDir)) {
  const hudSrc = readFileSync(join(__dir, "pre-pesticide.js"), "utf8");
  await page.addScriptTag({ content: detectSrc });
  await page.addScriptTag({ content: hudSrc });
  await page.evaluate(() => window.__xPaperPrePesticide.init());
  const live = await page.evaluate(() => window.__xPaperPrePesticide.inventory());
  const ppPath = join(outDir, "pre-pesticide.json");
  if (!existsSync(ppPath)) {
    writeFileSync(ppPath, JSON.stringify({
      url,
      width,
      capturedAt: new Date().toISOString(),
      hud: { tag: "x-paper-prepesticide", id: "x-paper-prepesticide" },
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
    }, null, 2));
    log(`wrote ${ppPath}`);
  }
  log(`source-section shots (pesticide on) → ${sourceDir}`);
  await captureSourceSectionsOnPage(page, {
    sections: live.sections || [],
    outDir: sourceDir,
    log,
    viewportWidth: width,
  });
}

// Tear down a leftover pre-pesticide HUD. Its pesticide outlines change
// computed styles; the serializer would paint them into Paper. Destroy
// before the Stage P fullpage + serialize so outlines stay in
// source-sections/ only — never in lander HTML.
await page.evaluate(() => window.__xPaperPrePesticide?.destroy?.());

await page.evaluate(() => window.scrollTo(0, 0));
await page.waitForTimeout(250);
const fullpagePath = join(outDir, "fullpage.png");
const fullpagePaperPath = join(outDir, "fullpage-paper.jpg");
try {
  await page.screenshot({ path: fullpagePath, fullPage: true });
  await page.screenshot({
    path: fullpagePaperPath,
    fullPage: true,
    type: "jpeg",
    quality: 62,
  });
  log(`fullpage shot → ${fullpagePath}`);
} catch (err) {
  log(`screenshot failed: ${err.message.split("\n")[0]}`);
}

await page.evaluate(detectSrc);
await page.evaluate(overlaySrc);

const sections = await page.evaluate("window.__xPaperDetectSections()");
log(`detected ${sections.length} section(s): ${sections.map((s) => s.name).join(", ")}`);

await page.evaluate(`window.__xPaperOverlay.init(${sections.length})`);

const manifest = [];
const layerIds = [];
let totalBytes = 0;

const hasChrome = sections.some(
  (s) => s.chrome || /^(header|nav|site-chrome)/i.test(s.name || ""),
);
if (desktop && !hasChrome) {
  const chrome = await serializeChromeBars(page, serializerSrc, { outDir, log });
  for (const entry of chrome.layerIds) {
    const slug = entry.section?.slug || "chrome";
    const file = join(outDir, `00-${slug}.html`);
    const bytes = existsSync(file) ? readFileSync(file, "utf8").length : 0;
    totalBytes += bytes;
    layerIds.push(entry);
    const bar = chrome.bars[chrome.layerIds.indexOf(entry)] || {};
    manifest.push({
      ...bar,
      id: entry.section?.id,
      slug,
      status: "ok",
      file,
      bytes,
      layerIds: (entry.ids || []).length,
    });
  }
}

for (let i = 0; i < sections.length; i++) {
  const s = sections[i];

  await page.evaluate(
    ([sel]) => {
      const el = document.querySelector(sel);
      if (el) el.scrollIntoView({ behavior: "instant", block: "center" });
    },
    [s.selector],
  );
  await settlePainted(page, s.selector);

  await page.evaluate(
    ([sel, idx, name, bytes]) => {
      window.__xPaperOverlay.highlight(sel);
      window.__xPaperOverlay.section(idx, name, bytes);
    },
    [s.selector, i + 1, s.name, totalBytes],
  );
  await page.waitForTimeout(150);

  // Section-scoped prefix so pc paths cannot collide across sections.
  const idPrefix = idPrefixFor(s, i);
  const expr = `(async () => {
    ${serializerSrc}
    return await fe(${JSON.stringify(s.selector)}, ${JSON.stringify({ idPrefix })});
  })()`;

  let result;
  try {
    result = await page.evaluate(expr);
  } catch (err) {
    log(`  ✗ ${s.name}: ${err.message.split("\n")[0]}`);
    manifest.push({ ...s, status: "error", error: err.message.split("\n")[0] });
    continue;
  }

  if (result.status !== "success" || !result.html) {
    log(`  ✗ ${s.name}: ${result.error || "empty"}`);
    manifest.push({ ...s, status: "error", error: result.error || "empty capture" });
    continue;
  }

  const file = join(outDir, `${String(i + 1).padStart(2, "0")}-${s.name}.html`);
  writeFileSync(file, result.html, "utf8");
  totalBytes += result.html.length;

  const shotFile = join(outDir, "shots", `${String(i + 1).padStart(2, "0")}-${s.name}.jpg`);
  try {
    // HUD composites into element screenshots even though serializer skips it.
    await page.evaluate(() => {
      window.__xPaperOverlay.hide();
      window.__xPaperOverlay.clearHighlight();
    });
    const handle = await page.$(s.selector);
    if (handle) {
      await handle.screenshot({ path: shotFile, type: "jpeg", quality: 72 });
      log(`  ✓ ${s.name}  ${(result.html.length / 1024).toFixed(0)} KB  + shot → ${shotFile}`);
    } else {
      log(`  ! ${s.name}: element not found for screenshot`);
    }
  } catch (err) {
    log(`  ! ${s.name} shot: ${err.message.split("\n")[0]}`);
  } finally {
    await page.evaluate(() => window.__xPaperOverlay.show());
  }

  const leaked = (result.html.match(/x-paper-/g) || []).length;
  if (leaked) log(`  ! ${s.name}: ${leaked} x-paper- reference(s) leaked into output`);

  const ids = result.ids || [];
  layerIds.push({ section: { id: sectionId(i), slug: s.name }, ids });

  manifest.push({
    ...s,
    id: sectionId(i),
    slug: s.name,
    status: "ok",
    file,
    shot: existsSync(shotFile) ? shotFile : null,
    bytes: result.html.length,
    warning: result.warning ?? null,
    leaked,
    layerIds: ids.length,
  });
}

await page.evaluate(`window.__xPaperOverlay.finish(${totalBytes})`);
await page.waitForTimeout(400);

const manifestPath = join(outDir, "manifest.json");
const shots = {
  fullpage: existsSync(fullpagePath) ? fullpagePath : null,
  fullpagePaper: existsSync(fullpagePaperPath) ? fullpagePaperPath : null,
};
const sectionsOut = stampSectionIds(manifest, { desktop });
if (desktop) writeSectionIndex(outDir, sectionsOut, { url, width });
const idsOut = writeLayerIds(outDir, layerIds, { url, width, desktop });
log(`optional sidecar ${idsOut.total} → ${idsOut.file}`);
if (desktop) {
  const idsPayload = JSON.parse(readFileSync(idsOut.file, "utf8"));
  const censusPath = join(outDir, "layer-ids-census.json");
  const census = await censusLivePage(page, idsPayload.ids, censusPath);
  log(`layer-ids-census ${census.ok ? "ok" : "note"} · live ${census.live} · sidecar ${census.sidecar} → ${censusPath} (optional, not a 1.2 gate)`);
}
writeFileSync(
  manifestPath,
  JSON.stringify({
    url,
    width,
    capturedAt: new Date().toISOString(),
    totalBytes,
    experiment: "home-section-qa",
    screenshots: shots,
    fullpageScreenshot: shots.fullpage,
    fullpagePaperScreenshot: shots.fullpagePaper,
    sections: sectionsOut,
  }, null, 2),
  "utf8",
);

console.log(JSON.stringify({
  outDir,
  manifest: manifestPath,
  sections: manifest.length,
  ok: manifest.filter((m) => m.status === "ok").length,
  failed: manifest.filter((m) => m.status !== "ok").length,
  totalBytes,
  fullpageScreenshot: shots.fullpage,
}, null, 1));

await browser.close();
