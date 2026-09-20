import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const src = fs.readFileSync(
  path.join(here, "..", "capture-extension", "content", "tag-overlays.js"),
  "utf8",
);
const sandbox = { globalThis: {} };
vm.runInNewContext(src, sandbox);
const api = sandbox.globalThis.PaperCaptureTags;

function el(tag, children = [], extras = {}) {
  return {
    tagName: tag.toUpperCase(),
    children,
    style: { position: extras.position || "" },
    hasAttribute: (name) => Boolean(extras.attrs?.[name]),
    closest: (selector) => extras.closest?.[selector] || null,
    getBoundingClientRect: () => extras.rect || { left: 10, top: 20, width: 100, height: 40 },
    append(node) { this.children.push(node); node.parent = this; },
  };
}

test("pc-id walk matches a plain parent.children path and skips tool chrome without shifting indexes", () => {
  const outline = el("x-paper-semantic-outline", [], { attrs: { "data-paper-tool": "1" } });
  const h1 = el("h1");
  const hidden = el("div");
  const p = el("p");
  const root = el("section", [h1, hidden, p, outline]);
  const rows = api.walkLayerIds(root, "01");
  assert.equal(rows.length, 2);
  assert.equal(rows[0].path, "0.0");
  assert.equal(rows[1].path, "0.2");
  assert.equal(rows[0].pcId, "pc-01-0.0");
  assert.equal(rows[1].pcId, "pc-01-0.2");
  assert.equal(rows[0].tag, "h1");
  assert.equal(rows[1].tag, "p");
});

test("outlines attach to positioned hosts and fall back for images", () => {
  const host = el("h1", [], { position: "relative" });
  const img = el("img", [], { position: "relative" });
  const fallback = el("x-paper-capture-root");
  const hostOutline = { style: {}, dataset: {} };
  const imgOutline = { style: {}, dataset: {} };
  assert.equal(api.canAttach(host), true);
  assert.equal(api.canAttach(img), false);
  assert.equal(api.attachOutline(host, hostOutline, fallback), "host");
  assert.equal(api.attachOutline(img, imgOutline, fallback), "overlay");
  assert.equal(hostOutline.dataset.attached, "host");
  assert.equal(imgOutline.dataset.attached, "overlay");
  assert.equal(host.children.includes(hostOutline), true);
  assert.equal(fallback.children.includes(imgOutline), true);
});

test("overlay boxes use visualViewport offsets instead of leftover layout coords", () => {
  const node = el("p", [], { rect: { left: 40, top: 80, width: 200, height: 24 } });
  const overlay = { style: {} };
  api.applyOverlayBox(overlay, api.viewportRect(node, { offsetLeft: 12, offsetTop: 8 }));
  assert.equal(overlay.style.left, "52px");
  assert.equal(overlay.style.top, "88px");
  assert.equal(overlay.style.width, "200px");
});
