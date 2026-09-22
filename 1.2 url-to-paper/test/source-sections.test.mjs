import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, existsSync, readdirSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  collectInventory,
  documentFromHtml,
  HUD_ID,
  HUD_TAG,
  isSerializerSkip,
} from "../scripts/pre-pesticide-core.mjs";
import { paperSectionName } from "../scripts/section-ids.mjs";
import {
  assertNoFullPageShot,
  buildSourceBoardHtml,
  FORBIDDEN_SOURCE_SHOTS,
  CAPTURE_OVERLAY_SELECTOR,
  hasSourceSectionShots,
  hideCaptureOverlaysInDocument,
  isSourceShotViewport,
  landerFolderForWidth,
  missingSourceSectionDirs,
  readSourceSectionsDir,
  requiredSourceSectionDirs,
  SOURCE_SHOT_MAX_WIDTH,
  SOURCE_SHOT_VIEWPORTS,
  SOURCE_BOARD_OPACITY,
  sourceBoardFrameStyles,
  buildSourceRowHtml,
  sourceBoardName,
  sourceSectionStem,
  sourceSectionsDirForWidth,
  stampSourceSections,
  writeSourceSectionArtifacts,
} from "../scripts/source-sections.mjs";
import { detectMissingHover } from "../scripts/missing-elements-lib.mjs";

const __dir = dirname(fileURLToPath(import.meta.url));
const fixture = readFileSync(join(__dir, "fixtures/pre-pesticide.html"), "utf8");
const serializerSrc = readFileSync(join(__dir, "../scripts/serializer.js"), "utf8");
const a6 = readFileSync(join(__dir, "../../1.3 hover-reel/scripts/build-paper-states.mjs"), "utf8");

const PNG_1X1 = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
  "base64",
);

/** A PNG whose IHDR declares WxH — enough for readImageDimensions. */
function pngOfSize(width, height) {
  const png = Buffer.from(PNG_1X1);
  png.writeUInt32BE(width, 16);
  png.writeUInt32BE(height, 20);
  return png;
}

function fixtureSections(n = 3) {
  const inv = collectInventory(documentFromHtml(fixture));
  assert.ok(inv.sections.length >= 2, `need 2+ sections, got ${inv.sections.length}`);
  return inv.sections.slice(0, n);
}

test("fixture emits 01/02 png+json and never a full-page shot", () => {
  const dir = mkdtempSync(join(tmpdir(), "source-sections-"));
  const sections = fixtureSections(3);
  const written = writeSourceSectionArtifacts(dir, sections, { pngBuffer: PNG_1X1 });

  assert.ok(written.length >= 2);
  const names = readdirSync(dir);
  assert.ok(names.some((n) => n.startsWith("01-") && n.endsWith(".png")), names.join(","));
  assert.ok(names.some((n) => n.startsWith("02-") && n.endsWith(".png")), names.join(","));
  assert.ok(names.some((n) => n.startsWith("01-") && n.endsWith(".json")));
  assert.ok(names.some((n) => n.startsWith("02-") && n.endsWith(".json")));
  for (const forbidden of FORBIDDEN_SOURCE_SHOTS) {
    assert.equal(existsSync(join(dir, forbidden)), false, forbidden);
  }
  assert.equal(hasSourceSectionShots(dir), true);
  assert.doesNotThrow(() => assertNoFullPageShot(dir));

  const sidecar = JSON.parse(readFileSync(written[0].json, "utf8"));
  assert.equal(sidecar.id, "01");
  assert.ok(sidecar.slug);
  assert.ok(sidecar.bbox);
  assert.ok(sidecar.childCounts);
  assert.equal(sidecar.paperName, paperSectionName({ id: sidecar.id, slug: sidecar.slug }, { desktop: true }));
});

test("Paper HTML stack has two badges, two images, paperSectionName layers", () => {
  const dir = mkdtempSync(join(tmpdir(), "source-board-"));
  const sections = fixtureSections(2);
  writeSourceSectionArtifacts(dir, sections, { pngBuffer: PNG_1X1 });
  const rows = readSourceSectionsDir(dir);
  const html = buildSourceBoardHtml(rows, { page: "home" });

  assert.equal(sourceBoardName("home"), "Screenshots");
  assert.equal(sourceBoardName("about"), "Screenshots · about");
  assert.match(html, />01</);
  assert.match(html, />02</);
  assert.equal((html.match(/<img /g) || []).length, 2);
  assert.match(html, /data:image\//);
  assert.doesNotMatch(html, /paper-asset:|file:\/\//);
  assert.doesNotMatch(html, /full-page|fullpage/i);
  assert.doesNotMatch(html, /Desktop section IDs/);

  const stamped = stampSourceSections(sections);
  for (const section of stamped) {
    const name = paperSectionName(section, { desktop: true });
    assert.equal(section.paperName, name);
    assert.match(html, new RegExp(`layer-name="${name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}"`));
    assert.equal(sourceSectionStem(section), `${section.id}-${section.slug}`);
  }

  assert.match(html, /background-color: #E11D2E/);
  assert.match(html, /width: 80px; height: 80px; border-radius: 999px/);
  assert.match(html, /layer-name="section-number"/);
  assert.doesNotMatch(html, />Hover States</);
  assert.doesNotMatch(html, /background-color: #E8E8E8/);
  assert.doesNotMatch(html, /background-color: #FF0000/);
  // No title row — the artboard name already reads Screenshots.
  assert.doesNotMatch(html, /layer-name="Headings"/);
  assert.doesNotMatch(html, />Screenshots</);
  const layers = [...html.matchAll(/layer-name="([^"]+)"/g)].map((m) => m[1]);
  assert.equal(layers[0], "Screenshots", "board is the outer layer");
  assert.match(layers[1], /^01 · /, "first child is row 01, not a title row");
  const imgAt = html.indexOf("<img ");
  const numberAt = html.indexOf('layer-name="section-number"');
  assert.ok(numberAt > -1 && numberAt < imgAt, "row: section-number left of the screenshot");
  assert.match(html, /1px solid #000000/);
  assert.match(html, /height: fit-content/);
  assert.match(html, /gap: 16px/);
  assert.match(html, /padding: 24px/);
  assert.match(html, /opacity: 0.5/);
  assert.doesNotMatch(html, /layer-name="01 · nav"/);
  assert.match(a6, /background-color: #E11D2E/);
  assert.match(a6, /width: 36px; height: 36px; border-radius: 999px/);
});

test("a 2x shot lays out at the 1600 desktop frame width, ratio kept", () => {
  const dir = mkdtempSync(join(tmpdir(), "source-scale-"));
  const png = join(dir, "01-hero-area.png");
  // Real kp-frilly geometry: headed Chrome on a Retina Mac wrote 3200x1560.
  writeFileSync(png, pngOfSize(3200, 1560));
  const html = buildSourceRowHtml({ id: "01", slug: "hero-area", paperName: "01 · hero-area", pngPath: png });

  assert.equal(SOURCE_SHOT_MAX_WIDTH, 1600);
  assert.match(html, /width: 1600px; height: 780px/);
  assert.match(html, /width="1600" height="780"/);
  assert.doesNotMatch(html, /3200/);
});

test("a shot narrower than the frame keeps its own width — downscale only", () => {
  const dir = mkdtempSync(join(tmpdir(), "source-narrow-"));
  const png = join(dir, "02-badge.png");
  writeFileSync(png, pngOfSize(640, 320));
  const html = buildSourceRowHtml({ id: "02", slug: "badge", paperName: "02 · badge", pngPath: png });
  assert.match(html, /width: 640px; height: 320px/);
});

test("source clips are taken at CSS scale so disk matches the sidecar bbox", () => {
  const src = readFileSync(join(__dir, "../scripts/source-sections.mjs"), "utf8");
  const shots = src.match(/screenshot\(\{[^}]*\}\)/g) || [];
  assert.ok(shots.length >= 2, "expected the element + clip screenshot calls");
  for (const call of shots) assert.match(call, /scale: "css"/, call);
});

test("Screenshots artboard is 50% opacity so it recedes next to home-desktop", () => {
  assert.equal(SOURCE_BOARD_OPACITY, 0.5);
  const styles = sourceBoardFrameStyles({ stackW: 1600, left: 40, top: 120 });
  assert.equal(styles.opacity, 0.5);
  assert.equal(styles.minWidth, "1600px");
  assert.equal(styles.left, 40);
  assert.equal(styles.top, 120);
  const seed = readFileSync(join(__dir, "../scripts/seed-source-board.mjs"), "utf8");
  assert.match(seed, /sourceBoardFrameStyles\(\{ stackW, left, top \}\)/);
});

test("seed-source-board --html-out writes the stack and does not call Paper", () => {
  const dir = mkdtempSync(join(tmpdir(), "source-seed-"));
  writeSourceSectionArtifacts(dir, fixtureSections(3), { pngBuffer: PNG_1X1 });
  const htmlOut = join(dir, "source-home.html");
  const cli = join(__dir, "../scripts/seed-source-board.mjs");
  const r = spawnSync(process.execPath, [cli, "--dir", dir, "--page", "home", "--html-out", htmlOut], {
    encoding: "utf8",
    env: { ...process.env, PAPER_FILE_ID: "" },
  });
  assert.equal(r.status, 0, r.stderr);
  const html = readFileSync(htmlOut, "utf8");
  assert.match(html, />01</);
  assert.match(html, />02</);
  assert.equal((html.match(/<img /g) || []).length, 2);
  assert.match(r.stdout, /"written": false/);
});

test("source shots hide Capture Tool and section-chip overlays", () => {
  assert.match(CAPTURE_OVERLAY_SELECTOR, /x-paper-human-hud/);
  assert.match(CAPTURE_OVERLAY_SELECTOR, /x-paper-section-chip/);
  assert.match(CAPTURE_OVERLAY_SELECTOR, /x-paper-cursor/);
  const nodes = ["x-paper-human-hud", "x-paper-section-chip"].map((tag) => ({
    tagName: tag.toUpperCase(),
    style: { visibility: "visible" },
    attrs: {},
    getAttribute(name) { return Object.hasOwn(this.attrs, name) ? this.attrs[name] : null; },
    setAttribute(name, value) { this.attrs[name] = value; },
  }));
  const root = {
    querySelectorAll(sel) {
      return nodes.filter((el) => sel.toLowerCase().includes(el.tagName.toLowerCase()));
    },
  };
  const hidden = hideCaptureOverlaysInDocument(root);
  assert.equal(nodes[0].style.visibility, "hidden");
  assert.equal(nodes[1].style.visibility, "hidden");
  assert.ok(hidden.length >= 2);
  const src = readFileSync(join(__dir, "../scripts/source-sections.mjs"), "utf8");
  assert.match(src, /hideCaptureOverlays\(page\)/);
});

test("serializer skip still matches x-paper-", () => {
  assert.equal(isSerializerSkip(HUD_TAG, ""), true);
  assert.equal(isSerializerSkip("div", HUD_ID), true);
  assert.match(
    serializerSrc,
    /L\.startsWith\("x-paper-"\) \|\| (?:e\.id|elementId\(e\))\.startsWith\("x-paper-"\)/,
  );
});

test("assertNoFullPageShot rejects a tall full-page file", () => {
  const dir = mkdtempSync(join(tmpdir(), "source-full-"));
  writeFileSync(join(dir, "full-page.png"), PNG_1X1);
  assert.throws(() => assertNoFullPageShot(dir), /per-section only/);
});

test("detectMissingHover flags captured footer links missing on Hover States", () => {
  const dir = mkdtempSync(join(tmpdir(), "hover-qa-"));
  const comps = join(dir, "source-site/components/home/footer");
  mkdirSync(comps, { recursive: true });
  writeFileSync(join(comps, "manifest.json"), JSON.stringify({
    kind: "footer",
    states: [
      { sectionId: "09", component: "09 · About", token: "footer-link" },
      { sectionId: "09", component: "09 · Appointment", token: "footer-link" },
    ],
  }));
  const captureDir = join(dir, "capture/home-desktop");
  mkdirSync(captureDir, { recursive: true });
  const shotsOnly = detectMissingHover({
    captureDir,
    paperSections: [
      { name: "09 · variant-1-2", sourceRow: true, hasHoverStates: false, id: "row-09" },
      { name: "02 · hero-section", sourceRow: true, hasHoverStates: false, id: "row-02" },
    ],
  });
  assert.equal(shotsOnly.length, 0);
  const hits = detectMissingHover({
    captureDir,
    paperSections: [
      { name: "09 · variant-1-2", sourceRow: true, hasHoverStates: false, id: "row-09" },
      { name: "Component 01", hoverBoard: true, sectionId: "02", hasHoverStates: true, id: "hov-02" },
    ],
  });
  assert.equal(hits.length, 1);
  assert.equal(hits[0].kind, "missing-hover-state");
  assert.match(hits[0].section, /09/);
});

test("disk clips live at 1600 / 768 / 390; Paper Screenshots stays 1600", () => {
  assert.deepEqual(SOURCE_SHOT_VIEWPORTS, [1600, 768, 390]);
  assert.equal(landerFolderForWidth("home", 1600), "home-desktop");
  assert.equal(landerFolderForWidth("home", 768), "home-768");
  assert.equal(landerFolderForWidth("home", 390), "home-390");
  assert.equal(isSourceShotViewport(1600), true);
  assert.equal(isSourceShotViewport(768), true);
  assert.equal(isSourceShotViewport(390), true);
  assert.equal(isSourceShotViewport(1024), false);

  const capture = mkdtempSync(join(tmpdir(), "source-dirs-"));
  assert.equal(requiredSourceSectionDirs(capture, "home").length, 3);
  assert.equal(missingSourceSectionDirs(capture, "home").length, 3);
  for (const width of SOURCE_SHOT_VIEWPORTS) {
    const dir = sourceSectionsDirForWidth(capture, "home", width);
    mkdirSync(dir, { recursive: true });
    writeFileSync(join(dir, "01-hero.png"), PNG_1X1);
  }
  assert.equal(missingSourceSectionDirs(capture, "home").length, 0);

  const stamped = stampSourceSections([{ slug: "hero", name: "hero" }]);
  assert.equal(stamped[0].stem, "01-hero");
  assert.equal(stamped[0].paperName, "01 · hero");
  assert.equal(sourceBoardName("home"), "Screenshots");

  // 1.2 writes the Paper Screenshots board from the 1600 pass only; the 768 /
  // 390 passes clip to disk with no source board.
  const phase = readFileSync(join(__dir, "../../1.3 hover-reel/scripts/run-paper-phase.mjs"), "utf8");
  assert.match(phase, /1\.2 needs source-sections at \$\{widthLabel\}/);
  assert.match(phase, /runWidths\(projectRoot\)/); // widths come from qa/run-config.json (fast = 1600 / 390)
  assert.match(phase, /sourceBoard: true/);
  assert.match(phase, /sourceBoard: false/);
  assert.doesNotMatch(phase, /No 768\/390 source-sections on disk/);
});
