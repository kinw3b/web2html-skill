// Paper Snapshot 0.4.13 serializer delta: an <svg> root whose used
// overflow-x / overflow-y is visible emits it explicitly, so Paper does not
// clip geometry that spills past the viewBox. Nested SVG shapes and svgs that
// keep the UA overflow (hidden/clip) are unaffected.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright-core";
import { launchOptions } from "../scripts/chrome-path.mjs";

const __dir = dirname(fileURLToPath(import.meta.url));
const serializerSrc = readFileSync(join(__dir, "../scripts/serializer.js"), "utf8");

const FIXTURE = `<!doctype html><html><body style="margin:0">
<style>.spill-x{overflow-x:visible;overflow-y:hidden}</style>
<section id="root" style="width:400px">
  <svg id="spill" width="20" height="20" viewBox="0 0 20 20" style="overflow:visible">
    <circle id="dot" cx="25" cy="10" r="6" fill="red" />
  </svg>
  <svg id="mixed" class="spill-x" width="20" height="20" viewBox="0 0 20 20">
    <rect width="30" height="10" fill="blue" />
  </svg>
  <svg id="clipped" width="20" height="20" viewBox="0 0 20 20">
    <rect width="30" height="30" fill="green" />
  </svg>
</section>
</body></html>`;

async function capture() {
  const browser = await chromium.launch(launchOptions({ visible: false }));
  try {
    const page = await browser.newPage({ viewport: { width: 800, height: 600 } });
    await page.setContent(FIXTURE, { waitUntil: "load" });
    return await page.evaluate(`(async () => {
      ${serializerSrc}
      return await fe("#root");
    })()`);
  } finally {
    await browser.close();
  }
}

const result = await capture();
const html = String(result.html || "");
const svgs = html.match(/<svg\b[^>]*>/g) || [];
const styleOf = (tag) => (tag.match(/style="([^"]*)"/) || [, ""])[1];

test("capture succeeded with three svg roots", () => {
  assert.equal(result.status, "success");
  assert.equal(svgs.length, 3, html.slice(0, 600));
});

test("svg with overflow:visible emits overflow-x and overflow-y visible", () => {
  const style = styleOf(svgs[0]);
  assert.match(style, /overflow-x:\s*visible/);
  assert.match(style, /overflow-y:\s*visible/);
});

test("mixed axes compute to auto/hidden, so nothing is forced visible", () => {
  // CSS turns visible into auto when the other axis is not visible.
  assert.doesNotMatch(styleOf(svgs[1]), /overflow-[xy]:\s*visible/);
});

test("svg with default (clipped) overflow gets no visible override", () => {
  assert.doesNotMatch(styleOf(svgs[2]), /overflow-[xy]:\s*visible/);
});

test("shapes inside the svg do not get overflow overrides", () => {
  const inner = html.match(/<(circle|rect)\b[^>]*>/g) || [];
  assert.ok(inner.length >= 3);
  for (const t of inner) assert.doesNotMatch(t, /overflow-[xy]/);
});
