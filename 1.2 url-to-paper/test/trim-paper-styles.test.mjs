import test from "node:test";
import assert from "node:assert/strict";
import {
  isTransparentColor,
  trimPaperStyles,
} from "../scripts/trim-paper-styles.mjs";

test("drops Framer orphan side width+color with no style", () => {
  const html = `<a style="color: rgb(9, 12, 28); border-top-width: 3px; border-top-color: rgb(0, 0, 0); border-right-width: 3px; border-right-color: rgb(0, 0, 0)">Pricing</a>`;
  const out = trimPaperStyles(html);
  assert.match(out, /Pricing/);
  assert.doesNotMatch(out, /border-top-width/);
  assert.doesNotMatch(out, /border-top-color/);
  assert.match(out, /color: rgb\(9, 12, 28\)/);
});

test("drops transparent hover-outline shorthand Paper would paint as #2A2A2A", () => {
  const html = `<a style="display: flex; border: 1px solid rgba(42, 42, 42, 0)">Contact</a>`;
  const out = trimPaperStyles(html);
  assert.match(out, /display: flex/);
  assert.doesNotMatch(out, /border:/);
});

test("keeps a real designed stroke", () => {
  const html = `<button style="border: 1px solid #090C1C; background-color: #fff">Book a demo</button>`;
  const out = trimPaperStyles(html);
  assert.match(out, /border: 1px solid #090C1C/);
});

test("keeps a side stroke that includes style", () => {
  const html = `<div style="border-bottom-width: 1px; border-bottom-style: solid; border-bottom-color: rgb(234, 237, 240)"></div>`;
  const out = trimPaperStyles(html);
  assert.match(out, /border-bottom-width: 1px/);
  assert.match(out, /border-bottom-style: solid/);
  assert.match(out, /border-bottom-color: rgb\(234, 237, 240\)/);
});

test("isTransparentColor covers rgba / slash / hex alpha", () => {
  assert.equal(isTransparentColor("rgba(42, 42, 42, 0)"), true);
  assert.equal(isTransparentColor("rgba(42 42 42 / 0)"), true);
  assert.equal(isTransparentColor("#2a2a2a00"), true);
  assert.equal(isTransparentColor("transparent"), true);
  assert.equal(isTransparentColor("#2A2A2A"), false);
  assert.equal(isTransparentColor("rgba(42, 42, 42, 0.4)"), false);
});
