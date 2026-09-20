import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  assignSemanticsNodes,
  buildSemanticWrapMap,
  buildSemanticsDoc,
  groupSemanticsBySection,
  inferSemanticsRoots,
  paperSemanticsName,
  semanticsMarkdown,
  writeSemanticsFiles,
} from "../scripts/source-semantics.mjs";
import { matchPaperNode } from "../scripts/apply-source-semantics.mjs";

const sections = [
  { id: "01", slug: "hero-section", top: 0, height: 800 },
  { id: "02", slug: "feature-section", top: 800, height: 600 },
];

test("paperSemanticsName is tag · clipped label", () => {
  assert.equal(paperSemanticsName("h1", "  The future of design  "), "h1 · The future of design");
  assert.equal(paperSemanticsName("p", ""), "p · p");
});

test("assignSemanticsNodes stamps Paper sections and drops unknown tags", () => {
  const rows = assignSemanticsNodes([
    { tag: "h1", text: "The future of design", y: 120 },
    { tag: "div", text: "nope", y: 140 },
    { tag: "a", text: "Get Started Now", href: "/start", sectionId: "01" },
  ], sections);
  assert.deepEqual(rows.map((r) => `${r.sectionId}:${r.tag}`), ["01:h1", "01:a"]);
  assert.equal(rows[1].href, "/start");
  assert.equal(rows[0].paperName, "h1 · The future of design");
});

test("groupSemanticsBySection keeps empty bands and parks leftovers", () => {
  const grouped = groupSemanticsBySection([
    { tag: "h1", text: "Hero", sectionId: "01" },
    { tag: "p", text: "Orphan", sectionId: null },
  ], sections);
  assert.equal(grouped[0].nodes.length, 1);
  assert.equal(grouped[1].nodes.length, 0);
  assert.equal(grouped.at(-1).id, "00");
  assert.equal(grouped.at(-1).nodes[0].text, "Orphan");
});

test("wrap map and markdown are per section", () => {
  const doc = buildSemanticsDoc({
    url: "https://example.com/",
    page: "home",
    nodes: [
      { tag: "h1", text: "The future of design", y: 80 },
      { tag: "p", text: "A short lead", y: 200 },
      { tag: "a", text: "Get Started Now", href: "https://example.com/start", y: 300 },
    ],
    sections,
  });
  assert.equal(doc.sections[0].id, "01");
  assert.equal(doc.wrapMap.h1[0], "The future of design");
  assert.equal(doc.wrapMap.links["Get Started Now"].href, "https://example.com/start");
  const md = semanticsMarkdown(doc);
  assert.match(md, /## 01 · hero-section/);
  assert.match(md, /<h1>/);
  assert.match(md, /## 02 · feature-section/);
});

test("writeSemanticsFiles writes json + md + wrap map", () => {
  const root = mkdtempSync(join(tmpdir(), "source-sem-"));
  try {
    const doc = buildSemanticsDoc({
      page: "home",
      nodes: [{ tag: "h1", text: "Hello", sectionId: "01" }],
      sections,
    });
    const written = writeSemanticsFiles(doc, {
      qaJson: join(root, "qa", "source-semantics.json"),
      qaMd: join(root, "qa", "source-semantics.md"),
      wrapMap: join(root, "qa", "source-semantics-map.json"),
    });
    assert.equal(written.length, 3);
    const map = JSON.parse(readFileSync(join(root, "qa", "source-semantics-map.json"), "utf8"));
    assert.deepEqual(map.h1, ["Hello"]);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("inferSemanticsRoots walks capture dir and components out", () => {
  const fromManifest = inferSemanticsRoots({
    sectionManifest: "/proj/capture/home-desktop/review-sequence.json",
    outDir: "/proj/source-site/components-human",
  });
  assert.equal(fromManifest.captureDir, "/proj/capture/home-desktop");
  assert.equal(fromManifest.projectRoot, "/proj");
});

test("matchPaperNode prefers exact text and skips numbered sections", () => {
  const nodes = [
    { id: "s", name: "01 · hero-section", textContent: "The future of design" },
    { id: "t", name: "Frame", textContent: "The future of design", childCount: 0 },
  ];
  const hit = matchPaperNode(nodes, { tag: "h1", text: "The future of design" });
  assert.equal(hit.id, "t");
  const already = matchPaperNode(nodes, { tag: "h1", text: "The future of design", paperName: "h1 · The future of design" });
  assert.equal(already.id, "t");
  const named = matchPaperNode(
    [{ id: "n", name: "h1 · The future of design", textContent: "" }],
    { tag: "h1", text: "The future of design" },
  );
  assert.equal(named.id, "n");
});
