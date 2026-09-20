// Step 1.2 collect — one headless Playwright pass writes the real 1600 / 768 /
// 390 DOM captures to Paper, clips source sections at each width, writes those
// 1600 clips onto the Paper Screenshots board, and parks serializer chrome on
// Navigation. Nothing is authored from desktop.
// No visible window, no HUD: navbar refine / hover / components are 1.4.

import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import { importSibling, siblingSkill } from "./skill-paths.mjs";
import { ensureCaptureReviewBoards } from "./park-capture-boards.mjs";
import { park12ChromeOnNavigation, portChromeOntoDesktopIfMissing } from "./park-12-chrome.mjs";

/** Every required viewport is captured through the same serializer path. */
export function paperAssembleWidths() {
  return [1600, 768, 390];
}

/** Disk shots (and optional --desktop-only skip of 768 / 390). */
export function diskShotWidths({ desktopOnly = false } = {}) {
  return desktopOnly ? [1600] : [1600, 768, 390];
}

/** Paper `Screenshots` is always the 1600 clips. 768 / 390 stay on disk. */
export function paperScreenshotBoardWidth() {
  return 1600;
}

async function writePaperScreenshotsBoard({
  call, fileId, srcDir, pageSlug, log,
}) {
  const { hasSourceSectionShots } = await importSibling(
    "url-to-paper", "scripts/source-sections.mjs",
  );
  if (!hasSourceSectionShots(srcDir)) {
    throw new Error(
      "1.2 needs per-section screenshots at 1600 to write the Paper Screenshots board",
    );
  }
  const { seedSourceBoard } = await importSibling(
    "url-to-paper", "scripts/seed-source-board.mjs",
  );
  const seeded = await seedSourceBoard({
    dir: srcDir, page: pageSlug, fileId, call, log,
  });
  if (!seeded?.id || seeded.written === false) {
    throw new Error("1.2 failed to write the Paper Screenshots board");
  }
  log(`1.2 screenshots → Paper ${seeded.name || "Screenshots"} (${seeded.sections} rows)`);
  return seeded;
}

function spawnNode(script, args, { cwd } = {}) {
  return new Promise((resolve) => {
    const child = spawn(process.execPath, [script, ...args], {
      cwd,
      stdio: ["ignore", "pipe", "pipe"],
    });
    let out = "";
    child.stdout.on("data", (d) => { out += d; });
    child.stderr.on("data", (d) => { process.stderr.write(d); });
    child.on("close", (code) => resolve({ code: code ?? 1, out }));
    child.on("error", () => resolve({ code: 1, out }));
  });
}

async function captureViewport({
  browser,
  url,
  width,
  height,
  detectSrc,
  serializerSrc,
  pageSlug,
  outDir,
  wantShots,
  srcDir,
  log,
  settleLivePage,
  detectRawSections,
  serializeSelector,
  contentWalkFromDetect,
  hideCaptureOverlays,
  captureSourceSectionsOnPage,
  shotsOnly = false,
}) {
  const ctx = await browser.newContext({
    viewport: { width, height: height || (width >= 1600 ? 900 : 1000) },
    deviceScaleFactor: width >= 1600 ? 2 : 1,
    // Always reduce: Framer appear still starts at opacity 0, and desktop
    // no-preference froze FAQ/footer at 0% blending. settlePainted snaps the rest.
    reducedMotion: "reduce",
  });
  const page = await ctx.newPage();
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
  try { await page.waitForLoadState("networkidle", { timeout: 15000 }); } catch { /* framer */ }
  await settleLivePage(page);
  const raw = await detectRawSections(page, detectSrc);
  const walk = contentWalkFromDetect(raw);
  fs.mkdirSync(outDir, { recursive: true });
  const sections = [];
  const layerIds = [];
  if (!shotsOnly) {
    const { idPrefixFor, writeLayerIds } = await importSibling(
      "url-to-paper",
      "scripts/layer-ids.mjs",
    );
    const { serializeChromeBars } = await importSibling(
      "url-to-paper",
      "scripts/chrome-bars.mjs",
    );
    const chrome = await serializeChromeBars(page, serializerSrc, { outDir, log });
    layerIds.push(...chrome.layerIds);
    for (const [index, s] of walk.entries()) {
      const captured = await serializeSelector(page, serializerSrc, s.selector, {
        idPrefix: idPrefixFor(s, index),
      });
      if (captured.status !== "success" || !captured.html) {
        log(`  ✗ ${width} ${s.paperName || s.slug}: ${captured.error || "empty"}`);
        continue;
      }
      const file = path.join(outDir, `${s.id}-${s.slug}.html`);
      fs.writeFileSync(file, captured.html);
      layerIds.push({
        section: { id: s.id, slug: s.slug || s.name },
        ids: captured.ids || [],
      });
      if (!(captured.ids || []).length) {
        log(`  ! ${width} ${s.paperName || s.slug}: no pc-ids — Paper will auto-name this section`);
      }
      sections.push({
        id: s.id, name: s.slug, slug: s.slug, selector: s.selector,
        file, status: "ok", h: s.height || s.h,
      });
    }
    fs.writeFileSync(path.join(outDir, "manifest.json"), JSON.stringify({
      url, width, page: pageSlug, sections,
    }, null, 2));
    const idsOut = writeLayerIds(outDir, layerIds, {
      url,
      width,
      desktop: width >= 1600,
    });
    log(`  pc-ids ${idsOut.total} → ${idsOut.file}`);
    if (idsOut.duplicates.length) log(`  ! ${idsOut.duplicates.length} duplicate pc-id(s)`);
    if (width >= 1600) {
      const { censusLivePage } = await importSibling(
        "url-to-paper",
        "scripts/layer-ids-census.mjs",
      );
      const idsPayload = JSON.parse(fs.readFileSync(idsOut.file, "utf8"));
      const censusPath = path.join(outDir, "layer-ids-census.json");
      const census = await censusLivePage(page, idsPayload.ids, censusPath);
      log(`  layer-ids-census ${census.ok ? "ok" : "warn"} · live ${census.live} · sidecar ${census.sidecar}`);
      if (!census.ok) {
        const miss = (census.missing || []).slice(0, 8).map((m) => m.key).join(", ");
        log(`  ! census sidecar missed ${census.missing.length} live tag(s)${miss ? `: ${miss}` : ""} — capture continues`);
      }
    }
  }
  if (wantShots) {
    try {
      const fullpage = path.join(outDir, "fullpage.png");
      await page.screenshot({ path: fullpage, fullPage: true, scale: "css" });
      log(`  fullpage ${width} → ${fullpage}`);
    } catch (err) {
      log(`  ! fullpage ${width}: ${String(err.message || err).split("\n")[0]}`);
    }
  }
  if (wantShots && walk.length && srcDir) {
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
  }
  await ctx.close();
  return { walk, sections };
}

async function assembleWidth({
  fileId, projectRoot, outDir, pageSlug, width, sourceBoard, log,
}) {
  if (!fileId) return;
  const manifest = path.join(outDir, "manifest.json");
  if (!fs.existsSync(manifest)) return;
  const assemble = siblingSkill("url-to-paper", "scripts/assemble-lander.mjs");
  const args = [
    "--manifest", manifest,
    "--file-id", fileId,
    "--name", `${pageSlug}-${width === 1600 ? "desktop" : String(width)}`,
    "--width", String(width),
    "--pace", "1200",
  ];
  if (!sourceBoard) args.push("--no-source-board");
  log(`assemble ${width} → Paper`);
  const result = await spawnNode(assemble, args, { cwd: projectRoot });
  if (result.code !== 0) {
    throw new Error(`1.2 Paper assemble ${width} failed (exit ${result.code})`);
  }
}

/** Headless: capture all required viewports to Paper. No Chrome window. */
export async function collectHomepageToPaper({
  url,
  fileId,
  captureRoot,
  pageSlug = "home",
  force = false,
  desktopOnly = false,
  log = console.error,
} = {}) {
  const { chromium } = await import("playwright-core");
  const {
    contentWalkFromDetect,
    detectRawSections,
    serializeSelector,
    settleLivePage,
  } = await importSibling("url-to-paper", "scripts/paper-walk.mjs");
  const { writeReviewSequence } = await importSibling("url-to-paper", "scripts/review-sequence.mjs");
  const {
    hasSourceSectionShots,
    sourceSectionsDirFor,
    captureSourceSectionsOnPage,
    hideCaptureOverlays,
    missingSourceSectionDirs,
  } = await importSibling("url-to-paper", "scripts/source-sections.mjs");
  const { launchOptions } = await importSibling("url-to-paper", "scripts/chrome-path.mjs");
  const { call, setFileId } = await importSibling("url-to-paper", "scripts/mcp-client.mjs");
  const { ensurePaper } = await importSibling("url-to-paper", "scripts/ensure-paper.mjs");
  const { ensureRulers } = await importSibling("url-to-paper", "scripts/rulers.mjs");
  const { findArtboard, mcpPayload } = await importSibling("url-to-paper", "scripts/write-paper-section.mjs");

  const detectSrc = fs.readFileSync(siblingSkill("url-to-paper", "scripts/detect-sections.js"), "utf8");
  const serializerSrc = fs.readFileSync(siblingSkill("url-to-paper", "scripts/serializer.js"), "utf8");
  const desktopDir = path.join(captureRoot, `${pageSlug}-desktop`);
  const srcDir = sourceSectionsDirFor(desktopDir);
  fs.mkdirSync(desktopDir, { recursive: true });
  const projectRoot = path.dirname(captureRoot);

  const gates = {
    sectionsOk: false,
    nav: "pending",
    shots: missingSourceSectionDirs(captureRoot, pageSlug).length === 0,
    w768: hasSourceSectionShots(sourceSectionsDirFor(path.join(captureRoot, `${pageSlug}-768`))),
    w390: hasSourceSectionShots(sourceSectionsDirFor(path.join(captureRoot, `${pageSlug}-390`))),
  };

  if (fileId) {
    setFileId(fileId);
    await ensurePaper({ launch: true, log });
    await call("open_file", { fileId });
    const info = mcpPayload(await call("get_basic_info", { fileId }));
    await ensureRulers({ call, fileId, boards: info.artboards || [], init: true, log });
  }

  log(desktopOnly
    ? "collect homepage (hidden) — 1600 desktop-only. No 768/390 capture."
    : "collect homepage (hidden) — serialize 1600 / 768 / 390 to Paper.");
  const hidden = await chromium.launch(launchOptions({ visible: false }));
  let walk = [];
  let lander = null;
  const helpers = {
    settleLivePage,
    detectRawSections,
    serializeSelector,
    contentWalkFromDetect,
    hideCaptureOverlays,
    captureSourceSectionsOnPage,
  };

  try {
    const desktop = await captureViewport({
      browser: hidden,
      url,
      width: 1600,
      height: 900,
      detectSrc,
      serializerSrc,
      pageSlug,
      outDir: desktopDir,
      wantShots: true,
      srcDir,
      log,
      ...helpers,
    });
    walk = desktop.walk;
    writeReviewSequence(desktopDir, walk, { page: pageSlug, url });
    gates.sectionsOk = desktop.sections.length > 0 || walk.length === 0;
    gates.shots = missingSourceSectionDirs(captureRoot, pageSlug).length === 0;

    if (fileId) {
      const existing = await findArtboard(call, `${pageSlug}-desktop`);
      if (existing.board && !force) {
        log("home-desktop already exists — keep layers, refresh Screenshots");
        lander = { id: existing.board.id, name: `${pageSlug}-desktop`, created: false };
      } else {
        if (existing.board && force) {
          log("force: replacing home-desktop layers");
          await call("delete_nodes", { fileId, nodeIds: [existing.board.id] });
        }
        await assembleWidth({
          fileId, projectRoot, outDir: desktopDir, pageSlug, width: 1600,
          sourceBoard: true, log,
        });
        const after = await findArtboard(call, `${pageSlug}-desktop`);
        lander = after.board
          ? { id: after.board.id, name: `${pageSlug}-desktop`, created: true }
          : null;
      }
      await writePaperScreenshotsBoard({
        call, fileId, srcDir, pageSlug, log,
      });
    }

    if (desktopOnly) {
      gates.w768 = true;
      gates.w390 = true;
      log("desktop-only: skip 768/390 capture");
    }
    for (const width of desktopOnly ? [] : [768, 390]) {
      const key = width === 768 ? "w768" : "w390";
      const outDir = path.join(captureRoot, `${pageSlug}-${width}`);
      const srcDirAtWidth = sourceSectionsDirFor(outDir);
      const captured = await captureViewport({
        browser: hidden,
        url,
        width,
        height: width === 768 ? 1024 : 844,
        detectSrc,
        serializerSrc,
        pageSlug,
        outDir,
        wantShots: true,
        srcDir: srcDirAtWidth,
        log,
        ...helpers,
      });
      gates[key] = true;
      if (fileId) {
        const artboardName = `${pageSlug}-${width}`;
        const existing = await findArtboard(call, artboardName);
        if (existing.board && force) {
          await call("delete_nodes", { fileId, nodeIds: [existing.board.id] });
        }
        if (!existing.board || force) {
          await assembleWidth({
            fileId, projectRoot, outDir, pageSlug, width, sourceBoard: false, log,
          });
        }
      }
      log(`${width} captured to Paper (${captured.sections.length} sections)`);
    }
    gates.shots = missingSourceSectionDirs(captureRoot, pageSlug).length === 0;
  } finally {
    await hidden.close().catch(() => {});
  }

  if (fileId && !lander) {
    const found = await findArtboard(call, `${pageSlug}-desktop`);
    if (found.board) lander = { id: found.board.id, name: `${pageSlug}-desktop`, created: false };
  }
  if (fileId) {
    const review = await ensureCaptureReviewBoards({ call, fileId, log });
    if (!review.ready) {
      throw new Error(`Capture Tool cannot open: ${review.reason}`);
    }
    try {
      const parked = await park12ChromeOnNavigation({
        call, fileId, projectRoot,
        captureDirs: [
          { width: 1600, dir: desktopDir },
          { width: 768, dir: path.join(captureRoot, `${pageSlug}-768`) },
          { width: 390, dir: path.join(captureRoot, `${pageSlug}-390`) },
        ],
        log, replace: force,
      });
      if (parked.written !== 3) throw new Error(`1.2 Navigation requires three takes; wrote ${parked.written}`);
      log("1.2 chrome → Navigation (1600 / 768 / 390)");
    } catch (err) {
      throw new Error(`1.2 Navigation capture failed: ${String(err.message || err).split("\n")[0]}`);
    }
    const desktopBoard = lander?.id
      ? { id: lander.id }
      : (await findArtboard(call, `${pageSlug}-desktop`)).board;
    if (desktopBoard?.id) {
      try {
        const ported = await portChromeOntoDesktopIfMissing({
          call, fileId, desktopId: desktopBoard.id, desktopDir, projectRoot, log,
        });
        if (ported.written) log("1.2 chrome → home-desktop (navbar was missing)");
      } catch (err) {
        log(`! desktop chrome port failed: ${String(err.message || err).split("\n")[0]}`);
      }
    }
  }

  log(`desktop sections ${walk.map((s) => s.paperName).join(" → ") || "(none)"}`);
  const missing = desktopOnly
    ? (hasSourceSectionShots(srcDir) ? [] : [srcDir])
    : missingSourceSectionDirs(captureRoot, pageSlug);
  if (missing.length) {
    throw new Error(
      desktopOnly
        ? `1.2 desktop-only needs source-sections at 1600 — missing ${missing.join(", ")}`
        : `1.2 needs source-sections at 1600 / 768 / 390 — missing ${missing.join(", ")}`,
    );
  }
  return { walk, gates, lander, desktopDir, projectRoot, url, pageSlug };
}

/** Phase 4: one extra URL onto its own Paper page. Desktop only. No Navigation / Screenshots / create_file. */
export async function collectInteriorPageToPaper({
  url,
  fileId,
  pageId,
  captureRoot,
  pageSlug,
  force = false,
  log = console.error,
} = {}) {
  if (!fileId) throw new Error("collectInteriorPageToPaper needs fileId from qa/paper-file.json");
  // pageId omitted = the home canvas (4.2 parks every interior lander there,
  // under `Ruler · pages` — never a Paper page per URL).
  if (!pageSlug || pageSlug === "home") throw new Error("collectInteriorPageToPaper refuses the homepage slug");

  const { chromium } = await import("playwright-core");
  const {
    contentWalkFromDetect,
    detectRawSections,
    serializeSelector,
    settleLivePage,
  } = await importSibling("url-to-paper", "scripts/paper-walk.mjs");
  const { writeReviewSequence } = await importSibling("url-to-paper", "scripts/review-sequence.mjs");
  const {
    hasSourceSectionShots,
    sourceSectionsDirFor,
    captureSourceSectionsOnPage,
    hideCaptureOverlays,
  } = await importSibling("url-to-paper", "scripts/source-sections.mjs");
  const { launchOptions } = await importSibling("url-to-paper", "scripts/chrome-path.mjs");
  const { call, setFileId } = await importSibling("url-to-paper", "scripts/mcp-client.mjs");
  const { ensurePaper } = await importSibling("url-to-paper", "scripts/ensure-paper.mjs");
  const { findArtboard } = await importSibling("url-to-paper", "scripts/write-paper-section.mjs");

  const detectSrc = fs.readFileSync(siblingSkill("url-to-paper", "scripts/detect-sections.js"), "utf8");
  const serializerSrc = fs.readFileSync(siblingSkill("url-to-paper", "scripts/serializer.js"), "utf8");
  const desktopDir = path.join(captureRoot, `${pageSlug}-desktop`);
  const srcDir = sourceSectionsDirFor(desktopDir);
  fs.mkdirSync(desktopDir, { recursive: true });
  const projectRoot = path.dirname(captureRoot);

  setFileId(fileId);
  await ensurePaper({ launch: true, log });
  await call("open_file", { fileId, ...(pageId ? { pageId } : {}) });

  log(`collect interior ${pageSlug} (hidden) — 1600 desktop-only. No Navigation / Screenshots.`);
  const hidden = await chromium.launch(launchOptions({ visible: false }));
  let walk = [];
  let lander = null;
  try {
    const desktop = await captureViewport({
      browser: hidden,
      url,
      width: 1600,
      height: 900,
      detectSrc,
      serializerSrc,
      pageSlug,
      outDir: desktopDir,
      wantShots: true,
      srcDir,
      log,
      settleLivePage,
      detectRawSections,
      serializeSelector,
      contentWalkFromDetect,
      hideCaptureOverlays,
      captureSourceSectionsOnPage,
    });
    walk = desktop.walk;
    writeReviewSequence(desktopDir, walk, { page: pageSlug, url });
    const existing = await findArtboard(call, `${pageSlug}-desktop`);
    if (existing.board && !force) {
      lander = { id: existing.board.id, name: `${pageSlug}-desktop`, created: false };
    } else {
      if (existing.board && force) {
        await call("delete_nodes", { fileId, nodeIds: [existing.board.id] });
      }
      await assembleWidth({
        fileId, projectRoot, outDir: desktopDir, pageSlug, width: 1600,
        sourceBoard: false, log,
      });
      const after = await findArtboard(call, `${pageSlug}-desktop`);
      lander = after.board
        ? { id: after.board.id, name: `${pageSlug}-desktop`, created: true }
        : null;
    }
  } finally {
    await hidden.close().catch(() => {});
  }
  if (!hasSourceSectionShots(srcDir)) {
    throw new Error(`4.2 desktop capture needs source-sections at 1600 — missing ${srcDir}`);
  }
  return {
    walk,
    lander,
    desktopDir,
    projectRoot,
    url,
    pageSlug,
    pageId,
    wroteNavigation: false,
    wroteScreenshots: false,
    createdFile: false,
  };
}
