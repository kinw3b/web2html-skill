import test from "node:test";
import assert from "node:assert/strict";
import { ensureAbsoluteOrigin, isOverlayNav, parkNavHtml } from "../scripts/park-nav.mjs";

test("top-pinned full-width wrappers park as overlay, not in-flow", () => {
  assert.equal(isOverlayNav({ position: "relative", top: 0, width: 1600, viewportWidth: 1600 }), true);
  assert.equal(isOverlayNav({ position: "relative", top: 240, width: 1600, viewportWidth: 1600 }), false);
  assert.equal(isOverlayNav({ position: "relative", containsOverlay: true }), true);
  const html = '<div style="position: relative; width: 1600px">nav</div>';
  const parked = parkNavHtml(html, "relative", { top: 0, width: 1600, viewportWidth: 1600 });
  assert.equal(parked.action, "overlay-last");
  assert.match(parked.html, /position: absolute/);
  assert.match(ensureAbsoluteOrigin(html), /left: 0px/);
  const forced = parkNavHtml(html, "static", { force: true });
  assert.equal(forced.action, "overlay-last");
});
