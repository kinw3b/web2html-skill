import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  isReviewSection,
  matchReviewRow,
  parsePaperSectionName,
  reviewSequenceSections,
  writeReviewSequence,
} from "../scripts/review-sequence.mjs";
import { overlayRename, sortRenamePlan } from "../scripts/apply-review-sequence.mjs";

const avanta = [
  { id: "01", slug: "nav", chrome: true, top: -150, h: 80 },
  { id: "02", slug: "explore-demos", top: 0, h: 80 },
  { id: "03", slug: "hero-section", top: 0, h: 886 },
  { id: "04", slug: "feature-section", top: 886, h: 919 },
  { id: "12", slug: "footer", top: 7186, h: 653 },
];

test("review sequence is 01 hero (plus nav), then content — not 01 nav / 03 hero", () => {
  assert.equal(isReviewSection(avanta[0]), false);
  assert.equal(isReviewSection(avanta[1]), false);
  const rows = reviewSequenceSections(avanta);
  assert.deepEqual(rows.map((s) => s.paperName), [
    "01 · hero-section",
    "02 · feature-section",
    "03 · footer",
  ]);
  assert.deepEqual(rows[0].includes, ["nav"]);
  assert.equal(rows[0].captureId, "03");
});

test("writeReviewSequence writes hover-ready JSON", () => {
  const dir = mkdtempSync(join(tmpdir(), "review-seq-"));
  const { file, sections } = writeReviewSequence(dir, avanta, { page: "home" });
  const parsed = JSON.parse(readFileSync(file, "utf8"));
  assert.equal(parsed.source, "review");
  assert.equal(parsed.page, "home");
  assert.equal(sections[0].id, "01");
  assert.equal(sections[0].slug, "hero-section");
  assert.match(file, /review-sequence\.json$/);
});

test("overlay explore-demos drops its capture number; nav 01 stays", () => {
  const seq = reviewSequenceSections(avanta);
  assert.equal(overlayRename("02 · explore-demos", seq), "explore-demos");
  assert.equal(overlayRename("01 · nav", seq), null);
  assert.equal(overlayRename("03 · hero-section", seq), null);
});

test("last content section is footer, not heading copy", () => {
  const rows = reviewSequenceSections([
    { id: "01", slug: "hero-section", top: 0, h: 900 },
    { id: "09", slug: "cta-section-02", top: 3200, h: 600 },
    { id: "10", slug: "marketing-solution-that-just", top: 4000, h: 720 },
  ]);
  assert.deepEqual(rows.map((s) => s.paperName), [
    "01 · hero-section",
    "02 · cta-section-02",
    "03 · footer",
  ]);
  assert.equal(rows[2].slug, "footer");
  const detect = readFileSync(new URL("../scripts/detect-sections.js", import.meta.url), "utf8");
  assert.match(detect, /if \(isLast && i > 0\) return "footer"/);
});

test("matchReviewRow prefers slug so 03 · hero-section becomes 01", () => {
  const seq = reviewSequenceSections(avanta);
  assert.equal(matchReviewRow("03 · hero-section", seq).paperName, "01 · hero-section");
  assert.equal(parsePaperSectionName("05 · content-section").id, "05");
});

test("rename plan drops overlay first, then high capture ids", () => {
  const plan = sortRenamePlan([
    { kind: "review", fromId: "03", name: "01 · hero-section" },
    { kind: "review", fromId: "04", name: "02 · feature-section" },
    { kind: "overlay", fromId: "02", name: "explore-demos" },
  ]);
  assert.equal(plan[0].kind, "overlay");
  assert.equal(plan[1].fromId, "04");
  assert.equal(plan[2].fromId, "03");
});
