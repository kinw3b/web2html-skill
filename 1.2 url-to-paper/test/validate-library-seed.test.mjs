import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { validateLibrarySeed } from "../scripts/validate-library-seed.mjs";

function text(obj) {
  return { content: [{ type: "text", text: JSON.stringify(obj) }] };
}

function writeRgbPng(path, rgb, w = 64, h = 64) {
  mkdirSync(join(path, ".."), { recursive: true });
  execFileSync("python3", ["-c", `
from PIL import Image
Image.new("RGB", (${w}, ${h}), (${rgb[0]}, ${rgb[1]}, ${rgb[2]})).save(${JSON.stringify(path)})
`]);
}

function writeLanderShot(root, folder, rgb) {
  const capture = join(root, "capture", folder);
  const shots = join(capture, "source-sections");
  mkdirSync(shots, { recursive: true });
  writeRgbPng(join(shots, "01-hero.png"), rgb);
  writeFileSync(
    join(capture, "01-hero.html"),
    '<div style="font-family: Inter, sans-serif">Hero</div>',
  );
}

function projectWithShot(rgb = [239, 75, 60]) {
  const root = mkdtempSync(join(tmpdir(), "library-seed-validate-"));
  for (const folder of ["home-desktop", "home-768", "home-390"]) {
    writeLanderShot(root, folder, rgb);
  }
  return { root };
}

function paperCall({ paperRgb = [239, 75, 60], faces = ["Inter"], extraChildren = [] } = {}) {
  const paperPngs = new Map();
  const band = (id, name) => ({
    id,
    name,
    childCount: 3,
    height: 64,
    worldY: 0,
    position: "relative",
    top: 0,
  });
  return {
    paperPngs,
    call: async (method, args) => {
      if (method === "get_basic_info") {
        return text({
          fileName: "site",
          artboards: [
            { id: "desk", name: "home-desktop" },
            { id: "tab", name: "home-768" },
            { id: "phone", name: "home-390" },
          ],
        });
      }
      if (method === "get_children" && args.nodeId === "desk") {
        return text({
          children: [
            band("s1", "01 · hero"),
            ...extraChildren,
          ],
        });
      }
      if (method === "get_children" && args.nodeId === "tab") {
        return text({ children: [band("t1", "hero")] });
      }
      if (method === "get_children" && args.nodeId === "phone") {
        return text({ children: [band("p1", "hero")] });
      }
      if (method === "get_children") {
        return text({ children: [{ id: `${args.nodeId}-t`, name: "label" }] });
      }
      if (method === "get_computed_styles") {
        const styles = {};
        for (const id of args.nodeIds || []) {
          styles[id] = { fontFamily: faces[0], position: "relative", top: 0 };
        }
        return text({ styles });
      }
      if (method === "get_screenshot") {
        return { content: [] };
      }
      return text({});
    },
    screenshot: async ({ outPath }) => {
      writeRgbPng(outPath, paperRgb);
      paperPngs.set(outPath, paperRgb);
      return outPath;
    },
  };
}

test("validateLibrarySeed fails closed without source-section clips", async () => {
  const root = mkdtempSync(join(tmpdir(), "library-seed-empty-"));
  mkdirSync(join(root, "capture", "home-desktop"), { recursive: true });
  const report = await validateLibrarySeed({
    projectRoot: root,
    fileId: "paper-file",
    paperCall: async () => text({ artboards: [] }),
    screenshot: async () => null,
  });
  assert.equal(report.ok, false);
  assert.equal(report.retryable, false);
  assert.equal(report.failures.length, 3);
  assert.ok(report.failures.every((f) => f.kind === "missing-source-sections"));
});

test("validateLibrarySeed fails closed when 768/390 clips are missing", async () => {
  const root = mkdtempSync(join(tmpdir(), "library-seed-desktop-only-"));
  writeLanderShot(root, "home-desktop", [239, 75, 60]);
  const paper = paperCall();
  const report = await validateLibrarySeed({
    projectRoot: root,
    fileId: "paper-file",
    paperCall: paper.call,
    screenshot: paper.screenshot,
  });
  assert.equal(report.ok, false);
  assert.equal(report.retryable, false);
  assert.ok(report.failures.some((f) => f.kind === "missing-source-sections" && /home-768/.test(f.symptom)));
  assert.ok(report.failures.some((f) => f.kind === "missing-source-sections" && /home-390/.test(f.symptom)));
});

test("validateLibrarySeed is green when Paper matches the source clip", async () => {
  const { root } = projectWithShot();
  const paper = paperCall();
  const report = await validateLibrarySeed({
    projectRoot: root,
    fileId: "paper-file",
    expectFile: "site",
    paperCall: paper.call,
    screenshot: paper.screenshot,
  });
  assert.equal(report.ok, true);
  assert.equal(report.failures.length, 0);
  assert.equal(report.sections.length, 3);
  assert.deepEqual(report.sections.map((s) => s.lander).sort(), ["390", "768", "desktop"]);
  const disk = JSON.parse(readFileSync(join(root, "qa", "library-seed-qa.json"), "utf8"));
  assert.equal(disk.ok, true);
  assert.equal(existsSync(join(root, "qa", "library-seed", "desktop")), true);
  assert.equal(existsSync(join(root, "qa", "library-seed", "768")), true);
  assert.equal(existsSync(join(root, "qa", "library-seed", "390")), true);
});

test("validateLibrarySeed does not retry a saturated spill onto a quiet band", async () => {
  const { root } = projectWithShot([247, 243, 237]);
  const paper = paperCall({ paperRgb: [239, 75, 60] });
  const report = await validateLibrarySeed({
    projectRoot: root,
    fileId: "paper-file",
    paperCall: paper.call,
    screenshot: paper.screenshot,
  });
  assert.equal(report.ok, false);
  assert.equal(report.retryable, false);
  assert.ok(report.failures.some((f) => f.kind === "color-spill"));
});

test("validateLibrarySeed flags a washed Paper band as retryable color-wash", async () => {
  const { root } = projectWithShot([239, 75, 60]);
  const paper = paperCall({ paperRgb: [247, 243, 237] });
  const report = await validateLibrarySeed({
    projectRoot: root,
    fileId: "paper-file",
    paperCall: paper.call,
    screenshot: paper.screenshot,
  });
  assert.equal(report.ok, false);
  assert.equal(report.retryable, true);
  assert.ok(report.failures.some((f) => f.kind === "color-wash"));
});

test("validateLibrarySeed does not retry an unmatched named band", async () => {
  const { root } = projectWithShot();
  const paper = paperCall({ extraChildren: [] });
  const original = paper.call;
  paper.call = async (method, args) => {
    if (method === "get_children" && args.nodeId === "desk") {
      return text({ children: [{ id: "s2", name: "02 · pricing", childCount: 2 }] });
    }
    return original(method, args);
  };
  const report = await validateLibrarySeed({
    projectRoot: root,
    fileId: "paper-file",
    paperCall: paper.call,
    screenshot: paper.screenshot,
  });
  assert.equal(report.ok, false);
  assert.equal(report.retryable, false);
  assert.equal(report.failures[0].kind, "unmatched-section");
});
