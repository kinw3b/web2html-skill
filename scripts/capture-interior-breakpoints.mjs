#!/usr/bin/env node
// 5.4 — live 768 / 390 source-section clips for Phase 4 URLs.
// Disk only. Never create_page / write_html / create_file / list_files.

import fs from "node:fs";
import path from "node:path";
import { importSibling, siblingSkill } from "./skill-paths.mjs";

export const FORBIDDEN_PAPER_TOOLS = [
  "create_page",
  "write_html",
  "create_file",
  "list_files",
];
export const WIDTHS = [768, 390];

const arg = (name, fallback) => {
  const i = process.argv.indexOf(`--${name}`);
  return i > -1 ? process.argv[i + 1] : fallback;
};

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

export function assertNoPaperWrite(name) {
  if (FORBIDDEN_PAPER_TOOLS.includes(name)) {
    throw new Error(`5.4 refuses ${name} — live clips only, no extra Paper frames`);
  }
}

export async function captureInteriorBreakpoints({
  project,
  pages,
  captureRoot,
  log = console.error,
} = {}) {
  if (!Array.isArray(pages) || !pages.length) throw new Error("need Phase 4 pages");
  const { chromium } = await import("playwright-core");
  const {
    contentWalkFromDetect,
    detectRawSections,
    settleLivePage,
  } = await importSibling("url-to-paper", "scripts/paper-walk.mjs");
  const {
    captureSourceSectionsOnPage,
    hideCaptureOverlays,
    hasSourceSectionShots,
    sourceSectionsDirForWidth,
  } = await importSibling("url-to-paper", "scripts/source-sections.mjs");
  const { launchOptions } = await importSibling("url-to-paper", "scripts/chrome-path.mjs");
  const detectSrc = fs.readFileSync(siblingSkill("url-to-paper", "scripts/detect-sections.js"), "utf8");

  const hidden = await chromium.launch(launchOptions({ visible: false }));
  const results = [];
  try {
    for (const row of pages) {
      const slug = row.slug;
      if (!slug || slug === "home") throw new Error("5.4 refuses the homepage slug");
      for (const width of WIDTHS) {
        const srcDir = sourceSectionsDirForWidth(captureRoot, slug, width);
        const ctx = await hidden.newContext({
          viewport: { width, height: 900 },
          deviceScaleFactor: 1,
          reducedMotion: "reduce",
        });
        const page = await ctx.newPage();
        await page.goto(row.url, { waitUntil: "domcontentloaded", timeout: 60000 });
        try { await page.waitForLoadState("networkidle", { timeout: 15000 }); } catch { /* live */ }
        await settleLivePage(page);
        const raw = await detectRawSections(page, detectSrc);
        const walk = contentWalkFromDetect(raw);
        await hideCaptureOverlays(page);
        await captureSourceSectionsOnPage(page, {
          sections: walk.map((s) => ({
            id: s.id,
            slug: s.slug,
            name: s.slug,
            selector: s.selector,
            top: s.top,
            h: s.height || s.h,
            bbox: { x: 0, y: s.top || 0, w: s.w || width, h: s.height || s.h || 200 },
          })),
          outDir: srcDir,
          log,
          viewportWidth: width,
        });
        await ctx.close();
        if (!hasSourceSectionShots(srcDir)) {
          throw new Error(`5.4 live capture needs source-sections at ${width} — missing ${srcDir}`);
        }
        results.push({ slug, width, dir: srcDir, paper: false });
      }
    }
  } finally {
    await hidden.close().catch(() => {});
  }
  return results;
}

async function main() {
  const PROJECT = path.resolve(arg("project", process.cwd()));
  const pagesPath = path.join(PROJECT, "qa", "phase-4-pages.json");
  if (!fs.existsSync(pagesPath)) {
    console.error("need qa/phase-4-pages.json from 4.2");
    process.exit(2);
  }
  const receipt = readJson(pagesPath);
  const captured = await captureInteriorBreakpoints({
    project: PROJECT,
    pages: receipt.pages || [],
    captureRoot: path.join(PROJECT, "capture"),
  });
  const out = path.join(PROJECT, "qa", "phase-5-breakpoint-capture.json");
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, `${JSON.stringify({
    ok: true,
    createdFile: false,
    wrotePaper: false,
    widths: WIDTHS,
    pages: captured,
  }, null, 2)}\n`);
  console.log(JSON.stringify({ ok: true, clips: captured.length, out }, null, 2));
}

const invoked = process.argv[1] && path.resolve(process.argv[1]) === new URL(import.meta.url).pathname;
if (invoked) {
  main().catch((err) => {
    console.error(err.message || err);
    process.exit(2);
  });
}
