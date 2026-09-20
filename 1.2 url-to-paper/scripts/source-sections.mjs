// Per-section SOURCE shots — disk at 1600 / 768 / 390, pesticide overlays hidden.
//
// Disk:
//   capture/home-desktop/source-sections/01-hero.png
//   capture/home-768/source-sections/01-hero.png
//   capture/home-390/source-sections/01-hero.png
// Paper: one artboard `Screenshots` (or `Screenshots · {page}`):
//   NN · slug rows only from the **1600** clips. No 768/390 source boards.
//   Artboard opacity 50% so the review clips recede next to `home-desktop`.
// Hover pairs live on FRAME Hover States — not on this board.
// Never a full-page screenshot. Never a sibling "Desktop section IDs" legend.

import { spawnSync } from "node:child_process";
import { mkdirSync, readdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, dirname, join, resolve } from "node:path";
import { readImageDimensions, scaledImageDimensions } from "./paper-image-geometry.mjs";
import { paperSectionName, sectionId, stampSectionIds } from "./section-ids.mjs";
import { settlePainted } from "./settle-page.mjs";

export const SOURCE_BOARD_PREFIX = "Source · ";
export const SCREENSHOTS_BOARD = "Screenshots";
export const FORBIDDEN_SOURCE_SHOTS = ["full-page.png", "fullpage.png", "full-page.jpg", "fullpage.jpg"];
export const SOURCE_BADGE_FILL = "#E11D2E";
export const SOURCE_BADGE_SIZE = 80; // one large section-number, not a per-item 36px chip
export const SOURCE_BOARD_GAP = 16;
export const SOURCE_BOARD_PAD = 24; // spacing-6
export const SOURCE_ROW_GAP = 16; // gold D7-0 row — number + shot
export const SOURCE_HOVER_GAP = 8; // retired hover-column helpers
export const SOURCE_STACK_GAP = 16;
export const SOURCE_HOVER_WIDTH = 780;
export const SOURCE_HEADING_FILL = "#E8E8E8";
export const SOURCE_HOVER_PAD = 24;
export const SOURCE_ITEM_RULE_COLOR = "#DDDDDD";
export const SOURCE_ITEM_RULE_HEIGHT = 2;
export const SOURCE_DIVIDER_WIDTH = 9;
export const SOURCE_DIVIDER_COLOR = "#FF0000";
export const SOURCE_SHOT_BORDER = "1px solid #000000";
// Shots are clipped at CSS width 1600, but a headed Chrome on a HiDPI display
// still hands back 2x bytes. Lay every row out at the desktop frame width so
// the board reads next to `home-desktop` instead of towering over it.
export const SOURCE_SHOT_MAX_WIDTH = 1600;
export const SOURCE_SHOT_VIEWPORTS = [1600, 768, 390];
// Review clips recede so `home-desktop` stays the hero on the canvas.
export const SOURCE_BOARD_OPACITY = 0.5;

/** Paper `create_artboard` / `update_styles` payload for FRAME Screenshots. */
export function sourceBoardFrameStyles({ stackW, left, top } = {}) {
  const styles = {
    width: "fit-content",
    height: "fit-content",
    overflow: "visible",
    display: "flex",
    flexDirection: "column",
    gap: `${SOURCE_BOARD_GAP}px`,
    padding: `${SOURCE_BOARD_PAD}px`,
    backgroundColor: "#ffffff",
    opacity: SOURCE_BOARD_OPACITY,
  };
  if (stackW != null) styles.minWidth = `${Math.round(stackW)}px`;
  if (left != null) styles.left = left;
  if (top != null) styles.top = top;
  return styles;
}

export function isSourceShotViewport(width) {
  const w = Number(width);
  return w >= 1400 || w === 768 || w === 390;
}

export function landerFolderForWidth(pageSlug = "home", width = 1600) {
  const slug = String(pageSlug || "home");
  const w = Number(width);
  if (w >= 1400) return `${slug}-desktop`;
  return `${slug}-${w}`;
}

export function sourceSectionsDirForWidth(captureRoot, pageSlug = "home", width = 1600) {
  return join(resolve(captureRoot), landerFolderForWidth(pageSlug, width), "source-sections");
}

export function requiredSourceSectionDirs(captureRoot, pageSlug = "home") {
  return SOURCE_SHOT_VIEWPORTS.map((width) => sourceSectionsDirForWidth(captureRoot, pageSlug, width));
}

export function missingSourceSectionDirs(captureRoot, pageSlug = "home") {
  return requiredSourceSectionDirs(captureRoot, pageSlug).filter((dir) => !hasSourceSectionShots(dir));
}

// Paper write_html cannot load paper-asset:// or file:// — those become
// empty rectangles (badges paint, shots stay white). Embed bytes as a
// data URI and pin width/height (Paper may measure height 0 before decode).
export function sourceImageSrc(absPath) {
  const abs = resolve(absPath);
  if (!abs || !existsSync(abs)) return "";
  let buf = readFileSync(abs);
  let mime = "image/png";
  if (buf[0] === 0xff && buf[1] === 0xd8) mime = "image/jpeg";
  if (buf.length > 120_000) {
    const jpg = jpegBytesForPaper(abs);
    if (jpg && jpg.length && jpg.length < buf.length) {
      buf = jpg;
      mime = "image/jpeg";
    }
  }
  return `data:${mime};base64,${buf.toString("base64")}`;
}

function jpegBytesForPaper(abs) {
  try {
    const out = join(tmpdir(), `web2html-src-${basename(abs).replace(/\W+/g, "-")}.jpg`);
    const r = spawnSync("sips", [
      "-s", "format", "jpeg",
      "-s", "formatOptions", "70",
      abs,
      "--out", out,
    ], { encoding: "utf8" });
    if (r.status !== 0 || !existsSync(out)) return null;
    return readFileSync(out);
  } catch {
    return null;
  }
}

export function isPaintedSourceSrc(src) {
  return typeof src === "string" && src.startsWith("data:image/");
}

export function sourceBoardName(page = "home") {
  const slug = String(page || "home").trim() || "home";
  if (slug === "home") return SCREENSHOTS_BOARD;
  return `${SCREENSHOTS_BOARD} · ${slug}`;
}

export function isSourceBoardName(name = "") {
  return typeof name === "string"
    && (name === SCREENSHOTS_BOARD
      || name.startsWith(`${SCREENSHOTS_BOARD} · `)
      || name.startsWith(SOURCE_BOARD_PREFIX));
}

export function sourceSectionStem(section) {
  const id = section?.id || "00";
  const slug = String(section?.slug || section?.name || "section")
    .toLowerCase()
    .replace(/['’"]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 40) || "section";
  return `${id}-${slug}`;
}

export function stampSourceSections(sections) {
  return stampSectionIds(sections || [], { desktop: true }).map((section, index) => {
    const id = section.id || sectionId(index);
    const slug = section.slug || section.name || `section-${index + 1}`;
    return {
      ...section,
      id,
      slug,
      paperName: paperSectionName({ id, slug, name: section.name }, { desktop: true }),
      stem: sourceSectionStem({ id, slug }),
    };
  });
}

export function sourceSectionSidecar(section, extra = {}) {
  const stamped = stampSourceSections([section])[0];
  return {
    slug: stamped.slug,
    id: stamped.id,
    tag: stamped.tag || "",
    framerName: stamped.framerName || stamped.framer || "",
    bbox: stamped.bbox || {
      x: stamped.x ?? 0,
      y: stamped.top ?? stamped.y ?? 0,
      w: stamped.w ?? stamped.width ?? 0,
      h: stamped.h ?? stamped.height ?? 0,
    },
    childCounts: stamped.childCounts || { img: 0, a: 0, button: 0, form: 0, h: 0, svg: 0 },
    paperName: stamped.paperName,
    png: `${stamped.stem}.png`,
    selector: stamped.selector || "",
    chrome: !!stamped.chrome,
    ...extra,
  };
}

export function sourcePageFromArtboard(name = "home") {
  return String(name || "home").replace(/-(desktop|768|390)$/i, "") || "home";
}

export function sourceSectionsDirFor(outOrDir) {
  const abs = resolve(outOrDir);
  if (basename(abs) === "pre-pesticide.json") return join(dirname(abs), "source-sections");
  if (basename(abs) === "source-sections") return abs;
  return join(abs, "source-sections");
}

export function hasSourceSectionShots(dir) {
  if (!dir || !existsSync(dir)) return false;
  return readdirSync(dir).some((n) => /^\d{2}-.+\.png$/.test(n));
}

/** Playwright clips composite fixed overlays. Serializer skip is not enough. */
export const CAPTURE_OVERLAY_SELECTOR = [
  "x-paper-human-hud",
  "x-paper-section-chip",
  "x-paper-cursor",
  "x-paper-cursor-hud",
  "x-paper-cursor-box",
  "x-paper-prepesticide",
  "x-paper-sem-layer",
  "#x-paper-prepesticide-outline",
].join(",");

export function hideCaptureOverlaysInDocument(root) {
  if (!root?.querySelectorAll) return [];
  const hidden = [];
  for (const el of root.querySelectorAll(CAPTURE_OVERLAY_SELECTOR)) {
    if (el.getAttribute?.("data-x-paper-shot-hide") != null) continue;
    const prev = el.style?.visibility ?? "";
    el.setAttribute?.("data-x-paper-shot-hide", prev);
    if (el.style) el.style.visibility = "hidden";
    hidden.push(String(el.tagName || el.id || "").toLowerCase());
  }
  return hidden;
}

export async function hideCaptureOverlays(page) {
  if (!page?.evaluate) return [];
  return page.evaluate((sel) => {
    const hidden = [];
    for (const el of document.querySelectorAll(sel)) {
      if (el.getAttribute("data-x-paper-shot-hide") != null) continue;
      el.setAttribute("data-x-paper-shot-hide", el.style.visibility || "");
      el.style.visibility = "hidden";
      hidden.push(String(el.tagName || el.id || "").toLowerCase());
    }
    window.__xPaperPrePesticide?.hideCard?.();
    return hidden;
  }, CAPTURE_OVERLAY_SELECTOR);
}

export function assertNoFullPageShot(outDir) {
  for (const name of FORBIDDEN_SOURCE_SHOTS) {
    if (existsSync(join(outDir, name))) {
      throw new Error(`${outDir} must not contain ${name} — source shots are per-section only`);
    }
  }
}

/** Write 01-slug.png + 01-slug.json. `pngFor` returns a Buffer (tests) or a path writer. */
export function writeSourceSectionArtifacts(outDir, sections, { pngBuffer, pngFor } = {}) {
  mkdirSync(outDir, { recursive: true });
  const stamped = stampSourceSections(sections);
  const written = [];
  for (const section of stamped) {
    const stem = section.stem;
    const pngPath = join(outDir, `${stem}.png`);
    const jsonPath = join(outDir, `${stem}.json`);
    const bytes = pngFor ? pngFor(section) : pngBuffer;
    if (Buffer.isBuffer(bytes)) writeFileSync(pngPath, bytes);
    writeFileSync(jsonPath, JSON.stringify(sourceSectionSidecar(section), null, 2));
    written.push({ stem, png: pngPath, json: jsonPath, paperName: section.paperName, id: section.id });
  }
  assertNoFullPageShot(outDir);
  return written;
}

export function readSourceSectionsDir(dir) {
  const abs = resolve(dir);
  if (!existsSync(abs)) return [];
  assertNoFullPageShot(abs);
  const names = readdirSync(abs).filter((n) => /^\d{2}-.+\.json$/.test(n)).sort();
  return names.map((name) => {
    const data = JSON.parse(readFileSync(join(abs, name), "utf8"));
    const png = join(abs, data.png || name.replace(/\.json$/, ".png"));
    return { ...data, json: join(abs, name), pngPath: png };
  });
}

export function sourceSectionNumberHtml(id) {
  const sid = String(id || "").padStart(2, "0").slice(0, 2);
  return `<div layer-name="section-number" style="width: ${SOURCE_BADGE_SIZE}px; height: ${SOURCE_BADGE_SIZE}px; border-radius: 999px; background-color: ${SOURCE_BADGE_FILL}; color: #FFFFFF; font-family: Inter, sans-serif; font-size: 24px; font-weight: 700; line-height: 30px; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">${esc(sid)}</div>`;
}

export function sourceBadgeHtml(id) {
  return sourceSectionNumberHtml(id);
}

export function sourceDividerHtml() {
  return `<div layer-name="Divider" style="width: ${SOURCE_DIVIDER_WIDTH}px; align-self: stretch; flex-shrink: 0; background-color: ${SOURCE_DIVIDER_COLOR};"></div>`;
}

export function sourceHoverSlotHtml(id) {
  const number = id ? sourceSectionNumberHtml(id) : "";
  return `<div layer-name="Hover States" style="display: flex; flex-direction: column; align-items: flex-start; gap: ${SOURCE_HOVER_GAP}px; width: ${SOURCE_HOVER_WIDTH}px; min-width: ${SOURCE_HOVER_WIDTH}px; max-width: ${SOURCE_HOVER_WIDTH}px; flex-shrink: 0; flex-grow: 0; height: fit-content; overflow: visible; padding: ${SOURCE_HOVER_PAD}px; background-color: ${SOURCE_HEADING_FILL};">${number}</div>`;
}

export function buildSourceRowHtml(section) {
  const name = section.paperName || paperSectionName(section, { desktop: true });
  const pngPath = section.pngPath || section.png;
  const abs = pngPath ? resolve(pngPath) : "";
  const raw = abs && existsSync(abs) ? readFileSync(abs) : null;
  const dims = raw ? readImageDimensions(raw) : null;
  let w = dims?.width || section.bbox?.w || section.w || SOURCE_SHOT_MAX_WIDTH;
  let h = dims?.height || section.bbox?.h || section.h || 200;
  // Downscale only — a narrower clip keeps its own width rather than stretching.
  if (raw && dims && dims.width > SOURCE_SHOT_MAX_WIDTH) {
    const fit = scaledImageDimensions(raw, SOURCE_SHOT_MAX_WIDTH);
    if (fit) {
      w = fit.displayWidth;
      h = fit.displayHeight;
    }
  }
  const src = abs ? sourceImageSrc(abs) : "";
  if (src && !isPaintedSourceSrc(src)) {
    throw new Error(`Source shot src must be data:image (not paper-asset:// or file://): ${name}`);
  }
  return `<div layer-name="${esc(name)}" style="display: flex; flex-direction: row; align-items: flex-start; gap: ${SOURCE_ROW_GAP}px; align-self: stretch; width: 100%; height: fit-content; flex-shrink: 0; overflow: visible;">
  ${sourceSectionNumberHtml(section.id)}
  <img src="${esc(src)}" width="${Math.round(w)}" height="${Math.round(h)}" alt="${esc(name)}" style="width: ${Math.round(w)}px; height: ${Math.round(h)}px; flex-shrink: 0; object-fit: cover; border: ${SOURCE_SHOT_BORDER};" />
</div>`;
}

export function buildSourceBoardHtml(sections, { page = "home" } = {}) {
  const stamped = Array.isArray(sections) && sections[0]?.pngPath
    ? sections
    : stampSourceSections(sections);
  const rows = stamped.map((section) => buildSourceRowHtml(section));
  return `<div layer-name="${esc(sourceBoardName(page))}" style="display: flex; flex-direction: column; gap: ${SOURCE_BOARD_GAP}px; padding: ${SOURCE_BOARD_PAD}px; background-color: #ffffff; height: fit-content; overflow: visible; width: fit-content; opacity: ${SOURCE_BOARD_OPACITY};">
${rows.join("\n")}
</div>`;
}

export async function captureSourceSectionsOnPage(page, {
  sections,
  outDir,
  log = () => {},
  viewportWidth = 1600,
} = {}) {
  mkdirSync(outDir, { recursive: true });
  const stamped = stampSourceSections(sections);
  await hideCaptureOverlays(page);

  const written = [];
  for (const section of stamped) {
    const stem = section.stem;
    const pngPath = join(outDir, `${stem}.png`);
    const jsonPath = join(outDir, `${stem}.json`);
    try {
      await shotSection(page, section, pngPath, viewportWidth);
    } catch (err) {
      log(`  ! ${stem} shot: ${String(err.message || err).split("\n")[0]}`);
    }
    writeFileSync(jsonPath, JSON.stringify(sourceSectionSidecar(section, {
      png: `${stem}.png`,
    }), null, 2));
    written.push({
      stem,
      png: existsSync(pngPath) ? pngPath : null,
      json: jsonPath,
      paperName: section.paperName,
      id: section.id,
    });
    log(`  source ${section.paperName} → ${basename(pngPath)}`);
  }
  assertNoFullPageShot(outDir);
  return written;
}

// `scale: "css"` pins one image pixel per CSS pixel. Visible Chrome on a Retina
// Mac renders at DPR 2 and ignores the context `deviceScaleFactor: 1`, so
// without this the clips land at 3200 wide with 4x the bytes, and the sidecar
// bbox (CSS pixels) no longer describes the PNG.
async function shotSection(page, section, pngPath, viewportWidth = 1600) {
  if (section.selector) {
    await page.evaluate((sel) => {
      const el = document.querySelector(sel);
      if (el) el.scrollIntoView({ behavior: "instant", block: "start" });
    }, section.selector);
    await settlePainted(page, section.selector);
    const handle = await page.$(section.selector);
    if (handle) {
      await handle.screenshot({ path: pngPath, type: "png", scale: "css" });
      return;
    }
  }
  const box = section.bbox || {};
  const clip = {
    x: Math.max(0, box.x || 0),
    y: Math.max(0, (box.y || 0) - (await page.evaluate(() => window.scrollY))),
    width: Math.max(1, box.w || viewportWidth || 1600),
    height: Math.max(1, box.h || 200),
  };
  await page.screenshot({ path: pngPath, type: "png", clip, scale: "css" });
}

function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}
